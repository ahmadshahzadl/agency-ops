"""Native booking: slot generation, booking creation, cancel/reschedule, calendar invites.

All times are handled as timezone-aware datetimes. Slots are generated in the booking page's
timezone (so daylight-saving shifts move with the host's wall clock) and returned in UTC.
"""
import logging
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Client as ClientModel,
    Lead as LeadModel,
    Meeting as MeetingModel,
    MeetingAttendee,
    Notification as NotificationModel,
    Role as RoleModel,
    User as UserModel,
)
from app.models.booking import BookingPage
from app.services import email_service
from app.services import google_calendar_service as gcal

logger = logging.getLogger(__name__)

DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MAX_RANGE_DAYS = 62


class SlotUnavailable(Exception):
    """The requested start is not (or no longer) a free slot."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------------

def _windows_for_day(page: BookingPage, d: date, tz: ZoneInfo) -> list[tuple[datetime, datetime]]:
    key = DAY_KEYS[d.weekday()]
    out = []
    for start_s, end_s in (page.hours or {}).get(key, []) or []:
        sh, sm = (int(x) for x in start_s.split(":"))
        eh, em = (int(x) for x in end_s.split(":"))
        start = datetime.combine(d, time(sh, sm), tzinfo=tz)
        end = datetime.combine(d, time(eh, em), tzinfo=tz)
        if end > start:
            out.append((start, end))
    return out


def host_busy_intervals(
    db: Session,
    page: BookingPage,
    range_start: datetime,
    range_end: datetime,
    exclude_meeting_id: uuid.UUID | None = None,
) -> list[tuple[datetime, datetime]]:
    """Existing non-canceled meetings on the host's calendar, padded by the page's buffers."""
    if not page.host_user_id:
        return []
    attendee_exists = (
        db.query(MeetingAttendee.meeting_id)
        .filter(MeetingAttendee.meeting_id == MeetingModel.id, MeetingAttendee.user_id == page.host_user_id)
        .exists()
    )
    qry = db.query(MeetingModel.id, MeetingModel.start_at, MeetingModel.end_at).filter(
        MeetingModel.status != "canceled",
        MeetingModel.start_at < range_end,
        MeetingModel.end_at > range_start,
        or_(MeetingModel.created_by == page.host_user_id, attendee_exists),
    )
    if exclude_meeting_id:
        qry = qry.filter(MeetingModel.id != exclude_meeting_id)
    before = timedelta(minutes=page.buffer_before_minutes or 0)
    after = timedelta(minutes=page.buffer_after_minutes or 0)
    # A booked meeting blocks [start - buffer_before, end + buffer_after] for *new* meetings:
    # the new one needs its own before-buffer clear and the existing one its after-buffer.
    busy = [(_as_utc(s) - before, _as_utc(e) + after) for _, s, e in qry.all()]
    # Host's Google Calendar (personal appointments, other clients' calls) also blocks slots.
    integ = gcal.get_integration(db, page.host_user_id)
    if integ is not None:
        try:
            for s, e in gcal.busy_intervals(db, integ, _as_utc(range_start), _as_utc(range_end)):
                busy.append((s - before, e + after))
        except gcal.GoogleError as e:
            # Fail open: offer the portal's own view rather than an empty page. Logged + surfaced
            # on the integration so the host notices.
            logger.warning("google free/busy failed for host %s: %s", page.host_user_id, e)
            integ.last_error = f"free/busy: {str(e)[:300]}"
            db.flush()
    return busy


def compute_slots(
    db: Session,
    page: BookingPage,
    start_date: date,
    end_date: date,
    now: datetime | None = None,
    exclude_meeting_id: uuid.UUID | None = None,
) -> list[datetime]:
    """Free slot start times (UTC) for [start_date, end_date] inclusive, in the page's timezone days."""
    now = _as_utc(now or utcnow())
    tz = ZoneInfo(page.timezone or "UTC")
    duration = timedelta(minutes=page.duration_minutes)
    earliest = now + timedelta(minutes=page.min_notice_minutes or 0)
    latest = now + timedelta(days=page.max_days_ahead or 30)

    range_start = datetime.combine(start_date, time.min, tzinfo=tz)
    range_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    busy = host_busy_intervals(db, page, _as_utc(range_start), _as_utc(range_end), exclude_meeting_id)

    slots: list[datetime] = []
    d = start_date
    while d <= end_date:
        for w_start, w_end in _windows_for_day(page, d, tz):
            cursor = w_start
            while cursor + duration <= w_end:
                s = _as_utc(cursor)
                e = s + duration
                if s >= earliest and s <= latest and not any(bs < e and be > s for bs, be in busy):
                    slots.append(s)
                cursor += duration
        d += timedelta(days=1)
    return slots


def is_slot_available(
    db: Session,
    page: BookingPage,
    start: datetime,
    now: datetime | None = None,
    exclude_meeting_id: uuid.UUID | None = None,
) -> bool:
    start = _as_utc(start)
    tz = ZoneInfo(page.timezone or "UTC")
    local_day = start.astimezone(tz).date()
    # Slots near midnight can belong to the previous local day; check both.
    candidates = compute_slots(db, page, local_day - timedelta(days=1), local_day, now, exclude_meeting_id)
    return any(s == start for s in candidates)


# ---------------------------------------------------------------------------
# Booking lifecycle
# ---------------------------------------------------------------------------

def _clean_answers(page: BookingPage, answers: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for q in page.questions or []:
        qid = q.get("id")
        val = answers.get(qid)
        text = ("" if val is None else str(val)).strip()
        if q.get("required") and not text:
            raise ValueError(f"'{q.get('label', qid)}' is required")
        if text:
            out[qid] = text[:2000]
    return out


def _description(page: BookingPage, name: str, email: str, tz: str | None, answers: dict[str, str]) -> str:
    lines = ["Booked on the website.", f"Invitee: {name} <{email}>"]
    if tz:
        lines.append(f"Invitee timezone: {tz}")
    labels = {q.get("id"): q.get("label", q.get("id")) for q in (page.questions or [])}
    if answers:
        lines.append("")
        lines.append("Answers:")
        lines.extend(f"- {labels.get(k, k)}: {v}" for k, v in answers.items())
    return "\n".join(lines)


def _guess_company(page: BookingPage, answers: dict[str, str]) -> str | None:
    for q in page.questions or []:
        label = (q.get("label") or "").lower()
        qid = (q.get("id") or "").lower()
        if any(k in label or k in qid for k in ("company", "business", "organisation", "organization")):
            v = answers.get(q.get("id"))
            if v:
                return v[:255]
    return None


def _find_or_create_lead(db: Session, page: BookingPage, name: str, email: str, notes: str, answers: dict[str, str]) -> LeadModel | None:
    email_l = email.strip().lower()
    lead = (
        db.query(LeadModel)
        .filter(func.lower(LeadModel.contact_email) == email_l)
        .order_by(LeadModel.created_at.desc())
        .first()
    )
    if lead:
        return lead
    if db.query(ClientModel).filter(func.lower(ClientModel.contact_email) == email_l, ClientModel.deleted_at.is_(None)).first():
        return None
    lead = LeadModel(
        company_name=_guess_company(page, answers) or name,
        contact_name=name,
        contact_email=email_l,
        source="website",
        status="new",
        notes=notes,
    )
    db.add(lead)
    db.flush()
    return lead


def _admins(db: Session) -> list[UserModel]:
    return db.query(UserModel).join(UserModel.roles).filter(RoleModel.name == "admin", UserModel.is_active.is_(True)).all()


def _notify(db: Session, users: Iterable[UserModel], title: str, message: str, link: str) -> None:
    seen = set()
    for u in users:
        if u is None or u.id in seen:
            continue
        seen.add(u.id)
        db.add(NotificationModel(user_id=u.id, title=title, message=message, link=link, type="meeting"))
    db.flush()


def create_booking(
    db: Session,
    page: BookingPage,
    start: datetime,
    name: str,
    email: str,
    invitee_tz: str | None,
    answers: dict[str, Any],
    now: datetime | None = None,
) -> MeetingModel:
    """Create a Meeting for a public booking. Caller commits. Raises SlotUnavailable / ValueError."""
    start = _as_utc(start)
    clean = _clean_answers(page, answers or {})
    # Serialize concurrent bookings on this page: the row lock holds until the caller commits,
    # so two requests for the same slot cannot both pass the availability check.
    db.query(BookingPage).filter(BookingPage.id == page.id).with_for_update().one()
    if not is_slot_available(db, page, start, now):
        raise SlotUnavailable("That time was just taken. Please pick another slot.")

    name = name.strip()
    email = email.strip()
    end = start + timedelta(minutes=page.duration_minutes)
    desc = _description(page, name, email, invitee_tz, clean)
    meeting = MeetingModel(
        title=f"{page.name} with {name}"[:255],
        description=desc,
        start_at=start,
        end_at=end,
        location=page.location_text,
        source="website",
        status="scheduled",
        invitee_name=name[:255],
        invitee_email=email[:255],
        invitee_timezone=invitee_tz,
        answers=clean,
        booking_page_id=page.id,
        manage_token=secrets.token_urlsafe(32),
        created_by=None,
    )
    db.add(meeting)
    db.flush()
    lead = _find_or_create_lead(db, page, name, email, desc, clean)
    if lead:
        meeting.lead_id = lead.id
    host = page.host
    if host:
        db.add(MeetingAttendee(meeting_id=meeting.id, user_id=host.id))
    db.flush()

    google_ok = _google_create(db, page, meeting)
    when = _fmt_dt(start, page.timezone)
    _notify(db, [host, *_admins(db)], f"New booking: {meeting.title}", f"{name} booked {page.name} for {when}.", f"/meetings/{meeting.id}")
    send_confirmation(page, meeting, host, attach_ics=not google_ok)
    return meeting


def _google_create(db: Session, page: BookingPage, meeting: MeetingModel) -> bool:
    """Create the Google Calendar event (+ Meet link) on the host's calendar. False if not connected/failed."""
    integ = gcal.get_integration(db, page.host_user_id)
    if integ is None:
        return False
    try:
        event_id, link = gcal.create_event(db, integ, meeting, page)
    except gcal.GoogleError as e:
        logger.warning("google event create failed for meeting %s: %s", meeting.id, e)
        integ.last_error = f"create event: {str(e)[:300]}"
        db.flush()
        return False
    meeting.google_event_id = event_id
    meeting.google_calendar_user_id = integ.user_id
    if link:
        meeting.location = link[:255]
    integ.last_error = None
    db.flush()
    return True


def _google_update(db: Session, page: BookingPage | None, meeting: MeetingModel) -> bool:
    if not meeting.google_event_id:
        return False
    integ = gcal.get_integration(db, meeting.google_calendar_user_id or (page.host_user_id if page else None))
    if integ is None:
        return False
    try:
        link = gcal.update_event(db, integ, meeting, page)
    except gcal.GoogleError as e:
        logger.warning("google event update failed for meeting %s: %s", meeting.id, e)
        integ.last_error = f"update event: {str(e)[:300]}"
        db.flush()
        return False
    if link:
        meeting.location = link[:255]
    return True


def _google_delete(db: Session, page: BookingPage | None, meeting: MeetingModel) -> bool:
    if not meeting.google_event_id:
        return False
    integ = gcal.get_integration(db, meeting.google_calendar_user_id or (page.host_user_id if page else None))
    if integ is None:
        return False
    try:
        gcal.delete_event(db, integ, meeting)
    except gcal.GoogleError as e:
        logger.warning("google event delete failed for meeting %s: %s", meeting.id, e)
        integ.last_error = f"delete event: {str(e)[:300]}"
        db.flush()
        return False
    return True


def cancel_booking(db: Session, meeting: MeetingModel, reason: str | None, by: str = "invitee") -> MeetingModel:
    if meeting.status == "canceled":
        return meeting
    meeting.status = "canceled"
    text = f"Canceled by {by}."
    if reason:
        text += f" Reason: {reason.strip()[:500]}"
    meeting.cancel_reason = text
    meeting.ics_sequence = (meeting.ics_sequence or 0) + 1
    db.flush()
    page = _page_of(db, meeting)
    host = page.host if page else None
    google_ok = _google_delete(db, page, meeting)
    _notify(db, [host, *_admins(db)], f"Booking canceled: {meeting.title}", text, f"/meetings/{meeting.id}")
    send_cancellation(page, meeting, host, attach_ics=not google_ok)
    return meeting


def reschedule_booking(db: Session, meeting: MeetingModel, new_start: datetime, invitee_tz: str | None = None, now: datetime | None = None) -> MeetingModel:
    page = _page_of(db, meeting)
    if page is None:
        raise ValueError("This booking can no longer be rescheduled online.")
    new_start = _as_utc(new_start)
    if meeting.status == "canceled":
        raise ValueError("This booking was canceled. Please make a new booking.")
    db.query(BookingPage).filter(BookingPage.id == page.id).with_for_update().one()
    if not is_slot_available(db, page, new_start, now, exclude_meeting_id=meeting.id):
        raise SlotUnavailable("That time is not available. Please pick another slot.")
    old = meeting.start_at
    meeting.start_at = new_start
    meeting.end_at = new_start + timedelta(minutes=page.duration_minutes)
    if invitee_tz:
        meeting.invitee_timezone = invitee_tz
    meeting.ics_sequence = (meeting.ics_sequence or 0) + 1
    db.flush()
    host = page.host
    google_ok = _google_update(db, page, meeting)
    _notify(
        db,
        [host, *_admins(db)],
        f"Booking rescheduled: {meeting.title}",
        f"Moved from {_fmt_dt(old, page.timezone)} to {_fmt_dt(new_start, page.timezone)}.",
        f"/meetings/{meeting.id}",
    )
    send_confirmation(page, meeting, host, rescheduled=True, attach_ics=not google_ok)
    return meeting


def _page_of(db: Session, meeting: MeetingModel) -> BookingPage | None:
    if not meeting.booking_page_id:
        return None
    return db.query(BookingPage).filter(BookingPage.id == meeting.booking_page_id).first()


# ---------------------------------------------------------------------------
# Emails + ICS
# ---------------------------------------------------------------------------

def _fmt_dt(dt: datetime, tz_name: str | None) -> str:
    try:
        tz = ZoneInfo(tz_name or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    local = _as_utc(dt).astimezone(tz)
    return f"{local.strftime('%a %d %b %Y, %H:%M')} ({tz.key})"


def _ics_dt(dt: datetime) -> str:
    return _as_utc(dt).strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(meeting: MeetingModel, page: BookingPage | None, method: str = "REQUEST") -> bytes:
    settings = get_settings()
    org_name = settings.app_name.replace(" API", "")
    organizer = settings.smtp_from or settings.smtp_user or "no-reply@example.com"
    if "<" in organizer:
        organizer = organizer.split("<", 1)[1].rstrip(">").strip()
    status = "CANCELLED" if method == "CANCEL" else "CONFIRMED"
    desc = meeting.description or ""
    manage = manage_url(meeting)
    if manage:
        desc += f"\n\nManage this booking: {manage}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{org_name}//Booking//EN",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method}",
        "BEGIN:VEVENT",
        f"UID:{meeting.id}@{org_name.lower().replace(' ', '-')}",
        f"SEQUENCE:{meeting.ics_sequence or 0}",
        f"DTSTAMP:{_ics_dt(utcnow())}",
        f"DTSTART:{_ics_dt(meeting.start_at)}",
        f"DTEND:{_ics_dt(meeting.end_at)}",
        f"SUMMARY:{_ics_escape(meeting.title)}",
        f"DESCRIPTION:{_ics_escape(desc)}",
        f"STATUS:{status}",
        f"ORGANIZER;CN={_ics_escape(org_name)}:mailto:{organizer}",
    ]
    if meeting.location:
        lines.append(f"LOCATION:{_ics_escape(meeting.location)}")
    if meeting.invitee_email:
        cn = _ics_escape(meeting.invitee_name or meeting.invitee_email)
        lines.append(f"ATTENDEE;CN={cn};ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{meeting.invitee_email}")
    if page and page.host and page.host.email:
        cn = _ics_escape(page.host.full_name or page.host.email)
        lines.append(f"ATTENDEE;CN={cn};ROLE=REQ-PARTICIPANT:mailto:{page.host.email}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def manage_url(meeting: MeetingModel) -> str | None:
    base = (get_settings().booking_public_url or "").rstrip("/")
    if not base or not meeting.manage_token:
        return None
    return f"{base}/book/manage/{meeting.manage_token}"


def send_confirmation(page: BookingPage, meeting: MeetingModel, host: UserModel | None, rescheduled: bool = False, attach_ics: bool = True) -> None:
    if not email_service.email_enabled():
        return
    # When Google Calendar created the event, Google already emailed a proper invitation;
    # attaching our own .ics would create a duplicate entry in the invitee's calendar.
    attachments = [("invite.ics", build_ics(meeting, page, "REQUEST"), "text", "calendar")] if attach_ics else []
    invitee_tz = meeting.invitee_timezone or page.timezone
    when_invitee = _fmt_dt(meeting.start_at, invitee_tz)
    manage = manage_url(meeting)
    title = "Your booking is rescheduled" if rescheduled else "Your booking is confirmed"
    body = (
        f"<p>Hi {meeting.invitee_name or ''},</p>"
        f"<p><strong>{page.name}</strong> · {page.duration_minutes} minutes<br>"
        f"<strong>{when_invitee}</strong></p>"
        + (f"<p>Where: <a href=\"{meeting.location}\">{meeting.location}</a></p>" if (meeting.location or "").startswith("http") else (f"<p>Where: {meeting.location}</p>" if meeting.location else ""))
        + ("<p>A calendar invite is attached. Need to change it? Use the link below.</p>" if attach_ics else "<p>A Google Calendar invitation with the Meet link has been sent to you separately. Need to change it? Use the link below.</p>")
    )
    text = (
        f"{title}\n\n{page.name} - {page.duration_minutes} minutes\n{when_invitee}\n"
        + (f"Where: {meeting.location}\n" if meeting.location else "")
        + (f"\nManage your booking: {manage}\n" if manage else "")
    )
    email_service.send_email(
        meeting.invitee_email,
        f"{title}: {page.name} on {when_invitee}",
        email_service._build_html(title, body, "Manage booking" if manage else None, manage),
        text,
        attachments,
    )
    if host and host.email:
        when_host = _fmt_dt(meeting.start_at, page.timezone)
        htitle = ("Rescheduled: " if rescheduled else "New booking: ") + meeting.title
        hbody = (
            f"<p><strong>{when_host}</strong></p>"
            f"<p>{meeting.invitee_name} &lt;{meeting.invitee_email}&gt;</p>"
            f"<pre style='white-space:pre-wrap;font-family:inherit'>{(meeting.description or '')}</pre>"
        )
        link = f"{get_settings().frontend_url.rstrip('/')}/meetings"
        email_service.send_email(host.email, htitle, email_service._build_html(htitle, hbody, "Open in app", link), f"{htitle}\n{when_host}\n\n{meeting.description or ''}", attachments)


def send_cancellation(page: BookingPage | None, meeting: MeetingModel, host: UserModel | None, attach_ics: bool = True) -> None:
    if not email_service.email_enabled():
        return
    attachments = [("cancel.ics", build_ics(meeting, page, "CANCEL"), "text", "calendar")] if attach_ics else []
    name = page.name if page else meeting.title
    tz = meeting.invitee_timezone or (page.timezone if page else "UTC")
    when = _fmt_dt(meeting.start_at, tz)
    title = "Your booking was canceled"
    body = f"<p>Hi {meeting.invitee_name or ''},</p><p><strong>{name}</strong> on <strong>{when}</strong> has been canceled.</p>"
    base = (get_settings().booking_public_url or "").rstrip("/")
    cta = f"{base}/book" if base else None
    email_service.send_email(meeting.invitee_email, f"Canceled: {name} on {when}", email_service._build_html(title, body + "<p>You can book a new time whenever suits you.</p>", "Book again" if cta else None, cta), f"{title}\n{name} on {when}", attachments)
    if host and host.email:
        htitle = f"Canceled: {meeting.title}"
        email_service.send_email(host.email, htitle, email_service._build_html(htitle, f"<p>{when}</p><p>{meeting.cancel_reason or ''}</p>"), f"{htitle}\n{when}\n{meeting.cancel_reason or ''}", attachments)
