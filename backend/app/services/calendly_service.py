"""Calendly webhook handling: signature verification and turning bookings into Meetings/Leads.

Calendly sends `invitee.created` when someone books and `invitee.canceled` when a booking is
canceled. A reschedule arrives as a cancel of the old invitee (``rescheduled: true``) followed by
a fresh ``invitee.created``. The invitee URI is unique per booking and is stored as
``Meeting.external_id`` so redelivered webhooks are idempotent.

Docs: https://developer.calendly.com/api-docs/ZG9jOjM2MzE2MDM4-webhook-signatures
"""
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.permission_service import users_with_permission, BOOKINGS_MANAGE
from app.models import (
    Client as ClientModel,
    Lead as LeadModel,
    Meeting as MeetingModel,
    MeetingAttendee,
    Notification as NotificationModel,
    Role as RoleModel,
    User as UserModel,
)


class InvalidSignature(Exception):
    pass


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------

def verify_signature(raw_body: bytes, header: str | None, signing_key: str, tolerance_seconds: int = 300) -> None:
    """Raise InvalidSignature unless ``header`` (``t=<unix>,v1=<hex>``) signs ``raw_body``.

    The signed payload is ``"<t>.<body>"`` with HMAC-SHA256 over the signing key.
    """
    if not header or not signing_key:
        raise InvalidSignature("missing signature")
    parts: dict[str, str] = {}
    for chunk in header.split(","):
        if "=" in chunk:
            k, v = chunk.strip().split("=", 1)
            parts[k] = v
    ts, sig = parts.get("t"), parts.get("v1")
    if not ts or not sig:
        raise InvalidSignature("malformed signature header")
    try:
        ts_int = int(ts)
    except ValueError as e:
        raise InvalidSignature("bad timestamp") from e
    if tolerance_seconds and abs(time.time() - ts_int) > tolerance_seconds:
        raise InvalidSignature("timestamp outside tolerance")
    expected = hmac.new(signing_key.encode(), ts.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise InvalidSignature("signature mismatch")


def sign_payload(raw_body: bytes, signing_key: str, ts: int | None = None) -> str:
    """Build a ``Calendly-Webhook-Signature`` header value (used by tests and local tooling)."""
    ts = ts or int(time.time())
    digest = hmac.new(signing_key.encode(), str(ts).encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _location_text(loc: dict[str, Any] | None) -> str | None:
    if not loc:
        return None
    join = loc.get("join_url")
    if join:
        return str(join)[:255]
    text = loc.get("location")
    kind = loc.get("type")
    if text:
        return str(text)[:255]
    if kind:
        return {
            "outbound_call": "Phone call (we call the invitee)",
            "inbound_call": "Phone call (invitee calls us)",
            "ask_invitee": "Location to be confirmed",
        }.get(kind, str(kind))[:255]
    return None


def _qa_lines(invitee: dict[str, Any]) -> list[str]:
    lines = []
    for qa in invitee.get("questions_and_answers") or []:
        q = (qa.get("question") or "").strip()
        a = (qa.get("answer") or "").strip()
        if q or a:
            lines.append(f"{q}: {a}" if q else a)
    return lines


def _guess_company(invitee: dict[str, Any]) -> str | None:
    for qa in invitee.get("questions_and_answers") or []:
        q = (qa.get("question") or "").lower()
        a = (qa.get("answer") or "").strip()
        if a and ("company" in q or "business" in q or "organisation" in q or "organization" in q):
            return a[:255]
    return None


def build_description(invitee: dict[str, Any], event: dict[str, Any]) -> str:
    lines = ["Booked via Calendly."]
    name = invitee.get("name") or ""
    email = invitee.get("email") or ""
    if name or email:
        lines.append(f"Invitee: {name} <{email}>".replace(" <>", ""))
    tz = invitee.get("timezone")
    if tz:
        lines.append(f"Invitee timezone: {tz}")
    et = event.get("name")
    if et:
        lines.append(f"Event type: {et}")
    qa = _qa_lines(invitee)
    if qa:
        lines.append("")
        lines.append("Answers:")
        lines.extend(f"- {line}" for line in qa)
    tracking = invitee.get("tracking") or {}
    utm = {k: v for k, v in tracking.items() if v and k.startswith("utm_")}
    if utm:
        lines.append("")
        lines.append("Tracking: " + ", ".join(f"{k}={v}" for k, v in utm.items()))
    links = []
    if invitee.get("reschedule_url"):
        links.append(f"Reschedule: {invitee['reschedule_url']}")
    if invitee.get("cancel_url"):
        links.append(f"Cancel: {invitee['cancel_url']}")
    if links:
        lines.append("")
        lines.extend(links)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _match_host_users(db: Session, event: dict[str, Any]) -> list[UserModel]:
    emails = {
        (m.get("user_email") or "").strip().lower()
        for m in (event.get("event_memberships") or [])
    }
    emails.discard("")
    if not emails:
        return []
    return (
        db.query(UserModel)
        .filter(func.lower(UserModel.email).in_(emails), UserModel.is_active.is_(True))
        .all()
    )


def _admin_users(db: Session) -> list[UserModel]:
    return (
        db.query(UserModel)
        .join(UserModel.roles)
        .filter(RoleModel.name == "admin", UserModel.is_active.is_(True))
        .all()
    )


def _notify(db: Session, users: list[UserModel], title: str, message: str, link: str) -> None:
    seen: set = set()
    for u in users:
        if u.id in seen:
            continue
        seen.add(u.id)
        db.add(NotificationModel(user_id=u.id, title=title, message=message, link=link, type="meeting"))
    db.flush()


def _find_or_create_lead(db: Session, invitee: dict[str, Any], event: dict[str, Any]) -> LeadModel | None:
    """Link the booking to an existing lead/client by email, else open a new Lead (source=calendly)."""
    email = (invitee.get("email") or "").strip().lower()
    if not email:
        return None
    lead = (
        db.query(LeadModel)
        .filter(func.lower(LeadModel.contact_email) == email)
        .order_by(LeadModel.created_at.desc())
        .first()
    )
    if lead:
        return lead
    existing_client = (
        db.query(ClientModel)
        .filter(func.lower(ClientModel.contact_email) == email, ClientModel.deleted_at.is_(None))
        .first()
    )
    if existing_client:
        # Already a client: don't open a duplicate lead for them.
        return None
    name = (invitee.get("name") or "").strip() or email
    lead = LeadModel(
        company_name=_guess_company(invitee) or name,
        contact_name=name,
        contact_email=email,
        source="calendly",
        status="new",
        notes=build_description(invitee, event),
    )
    db.add(lead)
    db.flush()
    return lead


def handle_invitee_created(db: Session, body: dict[str, Any]) -> MeetingModel:
    invitee = body.get("payload") or {}
    event = invitee.get("scheduled_event") or {}
    external_id = invitee.get("uri")
    if not external_id:
        raise ValueError("payload.uri missing")
    start = _parse_dt(event.get("start_time"))
    end = _parse_dt(event.get("end_time"))
    if not start or not end:
        raise ValueError("scheduled_event start_time/end_time missing")

    invitee_name = (invitee.get("name") or "").strip() or None
    invitee_email = (invitee.get("email") or "").strip() or None
    event_name = (event.get("name") or "Calendly meeting").strip()
    title = f"{event_name} with {invitee_name}" if invitee_name else event_name

    meeting = db.query(MeetingModel).filter(MeetingModel.external_id == external_id).first()
    is_new = meeting is None
    if is_new:
        meeting = MeetingModel(external_id=external_id, source="calendly")
        db.add(meeting)

    meeting.title = title[:255]
    meeting.description = build_description(invitee, event)
    meeting.start_at = start
    meeting.end_at = end
    meeting.location = _location_text(event.get("location"))
    meeting.status = "canceled" if invitee.get("status") == "canceled" else "scheduled"
    meeting.invitee_name = invitee_name
    meeting.invitee_email = invitee_email
    if meeting.lead_id is None:
        lead = _find_or_create_lead(db, invitee, event)
        if lead:
            meeting.lead_id = lead.id
    db.flush()

    hosts = _match_host_users(db, event)
    if is_new:
        existing = {a.user_id for a in meeting.attendee_links}
        for u in hosts:
            if u.id not in existing:
                db.add(MeetingAttendee(meeting_id=meeting.id, user_id=u.id))
        db.flush()
        when = start.strftime("%Y-%m-%d %H:%M UTC")
        _notify(
            db,
            hosts + _admin_users(db) + users_with_permission(db, BOOKINGS_MANAGE),
            f"New booking: {meeting.title}",
            f"{invitee_name or invitee_email or 'Someone'} booked via Calendly for {when}.",
            f"/meetings/{meeting.id}",
        )
    return meeting


def handle_invitee_canceled(db: Session, body: dict[str, Any]) -> MeetingModel | None:
    invitee = body.get("payload") or {}
    external_id = invitee.get("uri")
    if not external_id:
        raise ValueError("payload.uri missing")
    meeting = db.query(MeetingModel).filter(MeetingModel.external_id == external_id).first()
    if meeting is None:
        # Cancel for a booking we never saw (e.g. made before the webhook existed): nothing to do.
        return None
    cancellation = invitee.get("cancellation") or {}
    reason = (cancellation.get("reason") or "").strip()
    who = cancellation.get("canceler_type") or cancellation.get("canceled_by")
    if invitee.get("rescheduled"):
        text = "Rescheduled by invitee (a new booking replaces this one)."
    else:
        text = f"Canceled by {who}." if who else "Canceled."
    if reason:
        text += f" Reason: {reason}"
    already = meeting.status == "canceled"
    meeting.status = "canceled"
    meeting.cancel_reason = text
    db.flush()
    if not already:
        attendees = [a.user for a in meeting.attendee_links if getattr(a, "user", None)]
        if not attendees:
            attendee_ids = [a.user_id for a in meeting.attendee_links]
            attendees = db.query(UserModel).filter(UserModel.id.in_(attendee_ids)).all() if attendee_ids else []
        _notify(
            db,
            attendees + _admin_users(db),
            f"Booking canceled: {meeting.title}",
            text,
            f"/meetings/{meeting.id}",
        )
    return meeting
