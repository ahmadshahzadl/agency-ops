"""Native booking: slot generation, booking lifecycle, calendar invites, reminders.

All times are timezone-aware. Slots are generated in the booking page's timezone (so
daylight-saving shifts move with the host's wall clock) and returned in UTC.

Hosts: a page has a primary host plus optional co-hosts. Slots are the union of every host's
free time; a booking goes to a host who is free at that time, preferring the one with the
fewest upcoming bookings (round-robin by load). The chosen host is stored on the meeting.
"""
import logging
import secrets
import time as _time
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
from app.services.permission_service import users_with_permission, BOOKINGS_MANAGE

logger = logging.getLogger(__name__)

DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MAX_RANGE_DAYS = 62
INBOUND_SOURCES = ("website", "calendly")
TRACKING_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "referrer", "landing_page")
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com", "temp-mail.org", "yopmail.com",
    "trashmail.com", "sharklasers.com", "getnada.com", "dispostable.com", "fakeinbox.com", "throwawaymail.com",
}


class SlotUnavailable(Exception):
    """The requested start is not (or no longer) a free slot."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------

def page_hosts(db: Session, page: BookingPage) -> list[UserModel]:
    """Primary host first, then co-hosts; inactive/missing users dropped."""
    ids: list[uuid.UUID] = []
    if page.host_user_id:
        ids.append(page.host_user_id)
    for raw in page.co_host_ids or []:
        try:
            u = uuid.UUID(str(raw))
        except ValueError:
            continue
        if u not in ids:
            ids.append(u)
    if not ids:
        return []
    users = {u.id: u for u in db.query(UserModel).filter(UserModel.id.in_(ids), UserModel.is_active.is_(True)).all()}
    return [users[i] for i in ids if i in users]


def meeting_host(db: Session, meeting: MeetingModel, page: BookingPage | None) -> UserModel | None:
    hid = meeting.host_user_id or meeting.google_calendar_user_id or (page.host_user_id if page else None)
    if not hid:
        return None
    return db.query(UserModel).filter(UserModel.id == hid).first()


# ---------------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------------

def _windows_for_day(page: BookingPage, d: date, tz: ZoneInfo) -> list[tuple[datetime, datetime]]:
    overrides = page.overrides or {}
    key = d.isoformat()
    if key in overrides:
        raw = overrides.get(key) or []  # [] = closed that day
    else:
        raw = (page.hours or {}).get(DAY_KEYS[d.weekday()], []) or []
    out = []
    for start_s, end_s in raw:
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
    host_user_id: uuid.UUID | None = None,
) -> list[tuple[datetime, datetime]]:
    """Existing non-canceled meetings on a host's calendar (portal + Google), padded by the page's buffers."""
    host_id = host_user_id or page.host_user_id
    if not host_id:
        return []
    attendee_exists = (
        db.query(MeetingAttendee.meeting_id)
        .filter(MeetingAttendee.meeting_id == MeetingModel.id, MeetingAttendee.user_id == host_id)
        .exists()
    )
    qry = db.query(MeetingModel.id, MeetingModel.start_at, MeetingModel.end_at).filter(
        MeetingModel.status.notin_(["canceled", "no_show"]),
        MeetingModel.start_at < range_end,
        MeetingModel.end_at > range_start,
        or_(MeetingModel.created_by == host_id, MeetingModel.host_user_id == host_id, attendee_exists),
    )
    if exclude_meeting_id:
        qry = qry.filter(MeetingModel.id != exclude_meeting_id)
    before = timedelta(minutes=page.buffer_before_minutes or 0)
    after = timedelta(minutes=page.buffer_after_minutes or 0)
    busy = [(_as_utc(s) - before, _as_utc(e) + after) for _, s, e in qry.all()]
    integ = gcal.get_integration(db, host_id)
    if integ is not None:
        try:
            for s, e in gcal.busy_intervals(db, integ, _as_utc(range_start), _as_utc(range_end)):
                busy.append((s - before, e + after))
        except gcal.GoogleError as e:
            # Fail open (offer the portal's own view) but make noise: admins are alerted.
            _alert_google_failure(db, integ, "free/busy lookup", e)
    return busy


def _free_starts_for_host(page: BookingPage, days: Iterable[date], tz: ZoneInfo, busy, earliest, latest) -> list[datetime]:
    duration = timedelta(minutes=page.duration_minutes)
    out = []
    for d in days:
        for w_start, w_end in _windows_for_day(page, d, tz):
            cursor = w_start
            while cursor + duration <= w_end:
                s = _as_utc(cursor)
                e = s + duration
                if earliest <= s <= latest and not any(bs < e and be > s for bs, be in busy):
                    out.append(s)
                cursor += duration
    return out


def compute_slots(
    db: Session,
    page: BookingPage,
    start_date: date,
    end_date: date,
    now: datetime | None = None,
    exclude_meeting_id: uuid.UUID | None = None,
) -> list[datetime]:
    """Free slot starts (UTC) across all hosts for [start_date, end_date] in the page's timezone."""
    now = _as_utc(now or utcnow())
    tz = ZoneInfo(page.timezone or "UTC")
    earliest = now + timedelta(minutes=page.min_notice_minutes or 0)
    latest = now + timedelta(days=page.max_days_ahead or 30)
    range_start = _as_utc(datetime.combine(start_date, time.min, tzinfo=tz))
    range_end = _as_utc(datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz))
    days = []
    d = start_date
    while d <= end_date:
        days.append(d)
        d += timedelta(days=1)

    hosts = page_hosts(db, page)
    if not hosts:
        return []
    slots: set[datetime] = set()
    for h in hosts:
        busy = host_busy_intervals(db, page, range_start, range_end, exclude_meeting_id, host_user_id=h.id)
        slots.update(_free_starts_for_host(page, days, tz, busy, earliest, latest))
    return sorted(slots)


def free_hosts_at(
    db: Session,
    page: BookingPage,
    start: datetime,
    now: datetime | None = None,
    exclude_meeting_id: uuid.UUID | None = None,
    only_host_id: uuid.UUID | None = None,
) -> list[UserModel]:
    """Hosts of the page who can take a slot starting at ``start``."""
    start = _as_utc(start)
    now = _as_utc(now or utcnow())
    tz = ZoneInfo(page.timezone or "UTC")
    local_day = start.astimezone(tz).date()
    days = [local_day - timedelta(days=1), local_day]
    earliest = now + timedelta(minutes=page.min_notice_minutes or 0)
    latest = now + timedelta(days=page.max_days_ahead or 30)
    range_start = _as_utc(datetime.combine(days[0], time.min, tzinfo=tz))
    range_end = _as_utc(datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=tz))
    out = []
    for h in page_hosts(db, page):
        if only_host_id and h.id != only_host_id:
            continue
        busy = host_busy_intervals(db, page, range_start, range_end, exclude_meeting_id, host_user_id=h.id)
        if start in _free_starts_for_host(page, days, tz, busy, earliest, latest):
            out.append(h)
    return out


def is_slot_available(db: Session, page: BookingPage, start: datetime, now: datetime | None = None, exclude_meeting_id: uuid.UUID | None = None) -> bool:
    return bool(free_hosts_at(db, page, start, now, exclude_meeting_id))


def pick_host(db: Session, page: BookingPage, candidates: list[UserModel]) -> UserModel:
    """Least-loaded host wins: fewest upcoming inbound bookings; ties go to page order."""
    if len(candidates) == 1:
        return candidates[0]
    now = utcnow()
    loads = {}
    for h in candidates:
        loads[h.id] = (
            db.query(func.count(MeetingModel.id))
            .filter(MeetingModel.host_user_id == h.id, MeetingModel.status == "scheduled", MeetingModel.start_at >= now)
            .scalar()
            or 0
        )
    return min(candidates, key=lambda h: (loads[h.id], candidates.index(h)))


# ---------------------------------------------------------------------------
# Input hygiene
# ---------------------------------------------------------------------------

def _clean_answers(page: BookingPage, answers: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for q in page.questions or []:
        qid = q.get("id")
        val = answers.get(qid)
        text = ("" if val is None else str(val)).strip()
        if q.get("required") and not text:
            raise ValueError(f"'{q.get('label', qid)}' is required")
        if text and q.get("type") == "select":
            options = [str(o) for o in (q.get("options") or [])]
            if text not in options:
                raise ValueError(f"'{q.get('label', qid)}' must be one of the offered choices")
        if text:
            out[qid] = text[:2000]
    return out


def clean_tracking(tracking: dict[str, Any] | None) -> dict[str, str]:
    out = {}
    for k in TRACKING_KEYS:
        v = (tracking or {}).get(k)
        if v is None:
            continue
        v = str(v).strip()
        if v:
            out[k] = v[:500]
    return out


def domain_accepts_mail(domain: str) -> bool:
    """True unless DNS positively says the domain has neither MX nor A/AAAA records.
    DNS errors/timeouts fail open so a flaky resolver never blocks bookings."""
    try:
        import dns.resolver  # provided by email-validator
    except ImportError:  # pragma: no cover
        return True
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 3.0
    for rtype in ("MX", "A", "AAAA"):
        try:
            if resolver.resolve(domain, rtype):
                return True
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            continue
        except Exception:
            return True
    return False


def validate_invitee_email(email: str) -> None:
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in DISPOSABLE_DOMAINS:
        raise ValueError("Please use a work or personal email address, not a disposable one.")
    if not domain_accepts_mail(domain):
        raise ValueError(f"'{domain}' doesn't look like it can receive email. Please check the address.")


# ---------------------------------------------------------------------------
# Lead / notifications
# ---------------------------------------------------------------------------

def _description(page: BookingPage, name: str, email: str, tz: str | None, answers: dict[str, str], tracking: dict[str, str]) -> str:
    lines = ["Booked on the website.", f"Invitee: {name} <{email}>"]
    if tz:
        lines.append(f"Invitee timezone: {tz}")
    labels = {q.get("id"): q.get("label", q.get("id")) for q in (page.questions or [])}
    if answers:
        lines.append("")
        lines.append("Answers:")
        lines.extend(f"- {labels.get(k, k)}: {v}" for k, v in answers.items())
    if tracking:
        lines.append("")
        lines.append("Tracking: " + ", ".join(f"{k}={v}" for k, v in tracking.items()))
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
    lead = db.query(LeadModel).filter(func.lower(LeadModel.contact_email) == email_l).order_by(LeadModel.created_at.desc()).first()
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


def _watchers(db: Session, meeting: MeetingModel) -> list[UserModel]:
    """Who follows this prospect besides host/admins: its assignee, or every solutions engineer while unassigned."""
    if meeting.assigned_to:
        u = db.query(UserModel).filter(UserModel.id == meeting.assigned_to).first()
        return [u] if u else []
    return users_with_permission(db, BOOKINGS_MANAGE)


def _notify(db: Session, users: Iterable[UserModel], title: str, message: str, link: str) -> None:
    seen = set()
    for u in users:
        if u is None or u.id in seen:
            continue
        seen.add(u.id)
        db.add(NotificationModel(user_id=u.id, title=title, message=message, link=link, type="meeting"))
    db.flush()


# Google failure alerts: at most one per host per hour so an outage doesn't spam.
_alert_last: dict[uuid.UUID, float] = {}
_ALERT_EVERY = 3600.0


def _alert_google_failure(db: Session, integ, context: str, err: Exception) -> None:
    logger.warning("google %s failed for host %s: %s", context, integ.user_id, err)
    integ.last_error = f"{context}: {str(err)[:300]}"
    db.flush()
    last = _alert_last.get(integ.user_id, 0.0)
    if _time.monotonic() - last < _ALERT_EVERY:
        return
    _alert_last[integ.user_id] = _time.monotonic()
    host = db.query(UserModel).filter(UserModel.id == integ.user_id).first()
    who = (host.full_name or host.email) if host else str(integ.user_id)
    title = f"Google Calendar problem for {who}"
    msg = f"{context} failed: {str(err)[:200]}. Bookings continue without Meet links until this is fixed (reconnect Google in Profile)."
    recipients = _admins(db) + ([host] if host else [])
    _notify(db, recipients, title, msg, "/profile")
    for u in recipients:
        if u and u.email:
            email_service.send_email(u.email, title, email_service._build_html(title, f"<p>{msg}</p>", "Open Profile", f"{get_settings().frontend_url.rstrip('/')}/profile"), f"{title}\n\n{msg}")


# ---------------------------------------------------------------------------
# Booking lifecycle
# ---------------------------------------------------------------------------

def create_booking(
    db: Session,
    page: BookingPage,
    start: datetime,
    name: str,
    email: str,
    invitee_tz: str | None,
    answers: dict[str, Any],
    tracking: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> MeetingModel:
    """Create a Meeting for a public booking. Caller commits. Raises SlotUnavailable / ValueError."""
    start = _as_utc(start)
    name = name.strip()
    email = email.strip()
    clean = _clean_answers(page, answers or {})
    track = clean_tracking(tracking)
    validate_invitee_email(email)
    # Serialize concurrent bookings on this page: the row lock holds until the caller commits.
    db.query(BookingPage).filter(BookingPage.id == page.id).with_for_update().one()
    candidates = free_hosts_at(db, page, start, now)
    if not candidates:
        raise SlotUnavailable("That time was just taken. Please pick another slot.")
    host = pick_host(db, page, candidates)

    end = start + timedelta(minutes=page.duration_minutes)
    desc = _description(page, name, email, invitee_tz, clean, track)
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
        tracking=track or None,
        booking_page_id=page.id,
        host_user_id=host.id,
        manage_token=secrets.token_urlsafe(32),
        created_by=None,
    )
    db.add(meeting)
    db.flush()
    lead = _find_or_create_lead(db, page, name, email, desc, clean)
    if lead:
        meeting.lead_id = lead.id
    db.add(MeetingAttendee(meeting_id=meeting.id, user_id=host.id))
    db.flush()

    google_ok = _google_create(db, meeting, page, host)
    when = _fmt_dt(start, page.timezone)
    _notify(db, [host, *_admins(db), *_watchers(db, meeting)], f"New booking: {meeting.title}", f"{name} booked {page.name} for {when} with {host.full_name or host.email}.", f"/meetings/{meeting.id}")
    send_confirmation(page, meeting, host, attach_ics=not google_ok)
    return meeting


def cancel_booking(db: Session, meeting: MeetingModel, reason: str | None, by: str = "invitee") -> MeetingModel:
    if meeting.status == "canceled":
        return meeting
    page = _page_of(db, meeting)
    late = bool(page and meeting.start_at and _as_utc(meeting.start_at) - utcnow() < timedelta(minutes=page.min_notice_minutes or 0))
    meeting.status = "canceled"
    text = ("Late cancellation by " if late and by == "invitee" else "Canceled by ") + by + "."
    if reason:
        text += f" Reason: {reason.strip()[:500]}"
    meeting.cancel_reason = text
    meeting.ics_sequence = (meeting.ics_sequence or 0) + 1
    db.flush()
    host = meeting_host(db, meeting, page)
    google_ok = _google_delete(db, page, meeting)
    _notify(db, [host, *_admins(db), *_watchers(db, meeting)], f"Booking canceled: {meeting.title}", text, f"/meetings/{meeting.id}")
    send_cancellation(page, meeting, host, attach_ics=not google_ok, by_host=(by != "invitee"))
    return meeting


def reschedule_booking(
    db: Session,
    meeting: MeetingModel,
    new_start: datetime,
    invitee_tz: str | None = None,
    now: datetime | None = None,
    by_host: bool = False,
    new_end: datetime | None = None,
) -> MeetingModel:
    """Move a booking. Invitee moves must respect availability and the page's notice; host moves are free-form."""
    page = _page_of(db, meeting)
    if page is None:
        raise ValueError("This booking can no longer be rescheduled online.")
    new_start = _as_utc(new_start)
    if meeting.status == "canceled":
        raise ValueError("This booking was canceled. Please make a new booking.")
    now_ = _as_utc(now or utcnow())
    host = meeting_host(db, meeting, page)
    if not by_host:
        notice = timedelta(minutes=page.min_notice_minutes or 0)
        if _as_utc(meeting.start_at) - now_ < notice:
            hours = max(1, int(notice.total_seconds() // 3600))
            raise ValueError(f"This call starts too soon to reschedule online (less than {hours}h away). Email us and we'll sort it out.")
        db.query(BookingPage).filter(BookingPage.id == page.id).with_for_update().one()
        if not free_hosts_at(db, page, new_start, now_, exclude_meeting_id=meeting.id, only_host_id=host.id if host else None):
            raise SlotUnavailable("That time is not available. Please pick another slot.")
    old = meeting.start_at
    meeting.start_at = new_start
    meeting.end_at = _as_utc(new_end) if new_end else new_start + timedelta(minutes=page.duration_minutes)
    if invitee_tz:
        meeting.invitee_timezone = invitee_tz
    meeting.ics_sequence = (meeting.ics_sequence or 0) + 1
    # A moved call gets fresh reminders.
    meeting.reminder_24h_sent_at = None
    meeting.reminder_1h_sent_at = None
    db.flush()
    google_ok = _google_update(db, page, meeting)
    _notify(
        db,
        [host, *_admins(db), *_watchers(db, meeting)],
        f"Booking rescheduled: {meeting.title}",
        f"Moved from {_fmt_dt(old, page.timezone)} to {_fmt_dt(new_start, page.timezone)}" + (" by Fuorix." if by_host else " by the invitee."),
        f"/meetings/{meeting.id}",
    )
    send_confirmation(page, meeting, host, rescheduled=True, attach_ics=not google_ok, by_host=by_host)
    return meeting


def set_outcome(db: Session, meeting: MeetingModel, status_: str, note: str | None, lead_status: str | None) -> MeetingModel:
    if status_ not in ("completed", "no_show", "scheduled"):
        raise ValueError("status must be completed, no_show or scheduled")
    meeting.status = status_
    if note is not None:
        meeting.outcome_note = note.strip()[:2000] or None
    if lead_status and meeting.lead_id:
        lead = db.query(LeadModel).filter(LeadModel.id == meeting.lead_id).first()
        if lead and not lead.converted_to_client_id:
            if lead_status not in ("new", "contacted", "qualified", "lost", "closed", "dead"):
                raise ValueError("Unknown lead status")
            lead.status = lead_status
            if lead.assigned_to is None and meeting.assigned_to:
                lead.assigned_to = meeting.assigned_to
    db.flush()
    return meeting


def _page_of(db: Session, meeting: MeetingModel) -> BookingPage | None:
    if not meeting.booking_page_id:
        return None
    return db.query(BookingPage).filter(BookingPage.id == meeting.booking_page_id).first()


# ---------------------------------------------------------------------------
# Google Calendar hooks
# ---------------------------------------------------------------------------

def _google_create(db: Session, meeting: MeetingModel, page: BookingPage, host: UserModel | None) -> bool:
    integ = gcal.get_integration(db, host.id if host else None)
    if integ is None:
        return False
    try:
        event_id, link = gcal.create_event(db, integ, meeting, page)
    except gcal.GoogleError as e:
        _alert_google_failure(db, integ, "event creation", e)
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
    integ = gcal.get_integration(db, meeting.google_calendar_user_id)
    if integ is None:
        return False
    try:
        link = gcal.update_event(db, integ, meeting, page)
    except gcal.GoogleError as e:
        _alert_google_failure(db, integ, "event update", e)
        return False
    if link:
        meeting.location = link[:255]
    return True


def _google_delete(db: Session, page: BookingPage | None, meeting: MeetingModel) -> bool:
    if not meeting.google_event_id:
        return False
    integ = gcal.get_integration(db, meeting.google_calendar_user_id)
    if integ is None:
        return False
    try:
        gcal.delete_event(db, integ, meeting)
    except gcal.GoogleError as e:
        _alert_google_failure(db, integ, "event deletion", e)
        return False
    return True


# ---------------------------------------------------------------------------
# Reminders (called by the scheduler thread every minute)
# ---------------------------------------------------------------------------

def send_due_reminders(db: Session, now: datetime | None = None) -> int:
    """Email invitees 24h and 1h before inbound bookings. Returns number of reminders sent.

    A reminder is only sent if the booking existed before that window opened, so a call booked
    two hours ahead gets the 1h reminder but not a nonsensical '24h' one.
    """
    if not email_service.email_enabled():
        return 0
    now = _as_utc(now or utcnow())
    base = db.query(MeetingModel).filter(
        MeetingModel.source.in_(INBOUND_SOURCES),
        MeetingModel.status == "scheduled",
        MeetingModel.invitee_email.isnot(None),
        MeetingModel.start_at > now,
    )
    sent = 0
    day = base.filter(
        MeetingModel.start_at <= now + timedelta(hours=24),
        MeetingModel.reminder_24h_sent_at.is_(None),
        MeetingModel.created_at <= MeetingModel.start_at - timedelta(hours=24),
    ).all()
    for m in day:
        if _as_utc(m.start_at) - now <= timedelta(hours=1):
            continue  # too close: the 1h reminder covers it
        _send_reminder(db, m, "24h")
        m.reminder_24h_sent_at = now
        sent += 1
    hour = base.filter(
        MeetingModel.start_at <= now + timedelta(hours=1),
        MeetingModel.reminder_1h_sent_at.is_(None),
        MeetingModel.created_at <= MeetingModel.start_at - timedelta(hours=1),
    ).all()
    for m in hour:
        _send_reminder(db, m, "1h")
        m.reminder_1h_sent_at = now
        sent += 1
    db.commit()
    return sent


def _send_reminder(db: Session, meeting: MeetingModel, which: str) -> None:
    page = _page_of(db, meeting)
    tz = meeting.invitee_timezone or (page.timezone if page else "UTC")
    when = _fmt_dt(meeting.start_at, tz)
    name = page.name if page else meeting.title
    lead_in = "tomorrow" if which == "24h" else "in about an hour"
    title = f"Reminder: your call with Fuorix is {lead_in}"
    link = meeting.location if (meeting.location or "").startswith("http") else None
    manage = manage_url(meeting)
    body = (
        f"<p>Hi {meeting.invitee_name or ''},</p>"
        f"<p>Just a reminder that <strong>{name}</strong> is {lead_in}:<br><strong>{when}</strong></p>"
        + (f"<p>Join here: <a href=\"{link}\">{link}</a></p>" if link else (f"<p>Where: {meeting.location}</p>" if meeting.location else ""))
        + "<p>Can't make it? Use the link below to pick another time.</p>"
    )
    text = f"{title}\n\n{name}\n{when}\n" + (f"Join: {link}\n" if link else "") + (f"\nReschedule or cancel: {manage}\n" if manage else "")
    email_service.send_email(meeting.invitee_email, f"{title} · {when}", email_service._build_html(title, body, "Reschedule or cancel" if manage else None, manage), text)


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
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def manage_url(meeting: MeetingModel) -> str | None:
    base = (get_settings().booking_public_url or "").rstrip("/")
    if not base or not meeting.manage_token:
        return None
    return f"{base}/book/manage/{meeting.manage_token}"


def send_confirmation(page: BookingPage, meeting: MeetingModel, host: UserModel | None, rescheduled: bool = False, attach_ics: bool = True, by_host: bool = False) -> None:
    if not email_service.email_enabled():
        return
    # When Google Calendar created the event, Google already emailed a proper invitation;
    # attaching our own .ics would create a duplicate entry in the invitee's calendar.
    attachments = [("invite.ics", build_ics(meeting, page, "REQUEST"), "text", "calendar")] if attach_ics else []
    invitee_tz = meeting.invitee_timezone or page.timezone
    when_invitee = _fmt_dt(meeting.start_at, invitee_tz)
    manage = manage_url(meeting)
    if rescheduled and by_host:
        title = "Your call has been moved"
        intro = "<p>We had to move your call. The new time is:</p>"
    elif rescheduled:
        title = "Your booking is rescheduled"
        intro = ""
    else:
        title = "Your booking is confirmed"
        intro = ""
    link = meeting.location if (meeting.location or "").startswith("http") else None
    body = (
        f"<p>Hi {meeting.invitee_name or ''},</p>{intro}"
        f"<p><strong>{page.name}</strong> · {page.duration_minutes} minutes<br>"
        f"<strong>{when_invitee}</strong></p>"
        + (f"<p>Join here: <a href=\"{link}\">{link}</a></p>" if link else (f"<p>Where: {meeting.location}</p>" if meeting.location else ""))
        + ("<p>A calendar invite is attached. Need to change it? Use the link below.</p>" if attach_ics else "<p>A Google Calendar invitation with the Meet link has been sent to you separately. Need to change it? Use the link below.</p>")
        + "<p style='color:#6b7280;font-size:13px'>We'll send a reminder the day before and an hour before the call.</p>"
    )
    text = (
        f"{title}\n\n{page.name} - {page.duration_minutes} minutes\n{when_invitee}\n"
        + (f"Join: {link}\n" if link else (f"Where: {meeting.location}\n" if meeting.location else ""))
        + (f"\nManage your booking: {manage}\n" if manage else "")
    )
    email_service.send_email(
        meeting.invitee_email,
        f"{title}: {page.name} on {when_invitee}",
        email_service._build_html(title, body, "Manage booking" if manage else None, manage),
        text,
        attachments,
    )
    if host and host.email and not by_host:
        when_host = _fmt_dt(meeting.start_at, page.timezone)
        htitle = ("Rescheduled: " if rescheduled else "New booking: ") + meeting.title
        hbody = (
            f"<p><strong>{when_host}</strong></p>"
            f"<p>{meeting.invitee_name} &lt;{meeting.invitee_email}&gt;</p>"
            f"<pre style='white-space:pre-wrap;font-family:inherit'>{(meeting.description or '')}</pre>"
        )
        link_app = f"{get_settings().frontend_url.rstrip('/')}/meetings"
        email_service.send_email(host.email, htitle, email_service._build_html(htitle, hbody, "Open in app", link_app), f"{htitle}\n{when_host}\n\n{meeting.description or ''}", attachments)


def send_cancellation(page: BookingPage | None, meeting: MeetingModel, host: UserModel | None, attach_ics: bool = True, by_host: bool = False) -> None:
    if not email_service.email_enabled():
        return
    attachments = [("cancel.ics", build_ics(meeting, page, "CANCEL"), "text", "calendar")] if attach_ics else []
    name = page.name if page else meeting.title
    tz = meeting.invitee_timezone or (page.timezone if page else "UTC")
    when = _fmt_dt(meeting.start_at, tz)
    title = "Your call has been canceled" if by_host else "Your booking was canceled"
    body = f"<p>Hi {meeting.invitee_name or ''},</p><p><strong>{name}</strong> on <strong>{when}</strong> has been canceled" + (" by our team. Sorry about that." if by_host else ".") + "</p>"
    base = (get_settings().booking_public_url or "").rstrip("/")
    cta = f"{base}/book" if base else None
    email_service.send_email(meeting.invitee_email, f"Canceled: {name} on {when}", email_service._build_html(title, body + "<p>You can book a new time whenever suits you.</p>", "Book again" if cta else None, cta), f"{title}\n{name} on {when}", attachments)
    if host and host.email and not by_host:
        htitle = f"Canceled: {meeting.title}"
        email_service.send_email(host.email, htitle, email_service._build_html(htitle, f"<p>{when}</p><p>{meeting.cancel_reason or ''}</p>"), f"{htitle}\n{when}\n{meeting.cancel_reason or ''}", attachments)
