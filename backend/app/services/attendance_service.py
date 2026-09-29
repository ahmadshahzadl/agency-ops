"""Attendance: check-in / check-out, the day board and the period summary.

Days are reckoned in the company timezone (COMPANY_TIMEZONE). A check-in later than
ATTENDANCE_START_TIME counts as late. Working days come from ATTENDANCE_WORKING_DAYS (ISO
weekday numbers, Monday = 1). Interns are marked present and nothing else is stored; everyone
else also leaves their request IP and, when the browser shares it, a location.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import AttendanceRecord, User
from app.schemas.attendance import AttendanceRecordOut, AttendanceSummary, SummaryRow, TodayBoard, TodayRow
from app.services.activity_service import log_activity

STATUSES = ("present", "late")


class AttendanceError(Exception):
    pass


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def tz() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().company_timezone or "Asia/Karachi")
    except Exception:
        return ZoneInfo("Asia/Karachi")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def local_now(now: datetime | None = None) -> datetime:
    return (now or now_utc()).astimezone(tz())


def today_local(now: datetime | None = None) -> date:
    return local_now(now).date()


def start_time() -> time:
    raw = (get_settings().attendance_start_time or "10:00").strip()
    try:
        h, m = raw.split(":")
        return time(int(h), int(m))
    except Exception:
        return time(10, 0)


def working_days() -> set[int]:
    raw = get_settings().attendance_working_days or "1,2,3,4,5"
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= 7:
            out.add(int(part))
    return out or {1, 2, 3, 4, 5}


def is_working_day(d: date) -> bool:
    return d.isoweekday() in working_days()


def captures_location(user: User) -> bool:
    return (user.employment_type or "") != "intern"


def _employed_on(user: User, d: date) -> bool:
    if user.joined_on and d < user.joined_on:
        return False
    if user.left_on and d > user.left_on:
        return False
    return True


def _hours(rec: AttendanceRecord, now: datetime | None = None) -> float:
    end = rec.check_out_at or (now or now_utc())
    start = rec.check_in_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return round(max(0.0, (end - start).total_seconds() / 3600), 2)


def to_out(rec: AttendanceRecord, now: datetime | None = None) -> AttendanceRecordOut:
    u = rec.user
    return AttendanceRecordOut(
        id=rec.id, user_id=rec.user_id, user_name=(u.full_name if u else None), user_email=(u.email if u else None),
        employment_type=(u.employment_type if u else None), work_date=rec.work_date, check_in_at=rec.check_in_at,
        check_out_at=rec.check_out_at, status=rec.status, hours=_hours(rec, now), ip_address=rec.ip_address,
        latitude=rec.latitude, longitude=rec.longitude, location_accuracy_m=rec.location_accuracy_m,
        user_agent=rec.user_agent, note=rec.note,
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def record_for(db: Session, user_id: UUID, d: date) -> AttendanceRecord | None:
    return (
        db.query(AttendanceRecord).options(joinedload(AttendanceRecord.user))
        .filter(AttendanceRecord.user_id == user_id, AttendanceRecord.work_date == d).first()
    )


def check_in(
    db: Session, user: User, *, ip: str | None, user_agent: str | None,
    latitude: Decimal | None, longitude: Decimal | None, accuracy_m: Decimal | None, note: str | None,
    now: datetime | None = None,
) -> AttendanceRecord:
    now = now or now_utc()
    d = today_local(now)
    if record_for(db, user.id, d):
        raise AttendanceError("You have already checked in today")
    late = local_now(now).time() > start_time()
    keep = captures_location(user)
    rec = AttendanceRecord(
        user_id=user.id, work_date=d, check_in_at=now, status="late" if late else "present",
        ip_address=(ip or None) if keep else None,
        latitude=latitude if keep else None, longitude=longitude if keep else None,
        location_accuracy_m=accuracy_m if keep else None,
        user_agent=((user_agent or "")[:255] or None) if keep else None,
        note=(note or None),
    )
    db.add(rec)
    db.flush()
    log_activity(db, user.id, "attendance_check_in", "attendance", rec.id, details=f"Checked in {'late ' if late else ''}at {local_now(now).strftime('%H:%M')}")
    return rec


def check_out(db: Session, user: User, note: str | None, now: datetime | None = None) -> AttendanceRecord:
    now = now or now_utc()
    rec = record_for(db, user.id, today_local(now))
    if not rec:
        raise AttendanceError("Check in first")
    if rec.check_out_at:
        raise AttendanceError("You have already checked out today")
    rec.check_out_at = now
    if note:
        rec.note = f"{rec.note}\n{note}".strip() if rec.note else note
    db.flush()
    log_activity(db, user.id, "attendance_check_out", "attendance", rec.id, details=f"Checked out at {local_now(now).strftime('%H:%M')} ({_hours(rec, now)} h)")
    return rec


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def _staff(db: Session, include_inactive: bool = False) -> list[User]:
    q = db.query(User).filter(User.client_id.is_(None))
    if not include_inactive:
        q = q.filter(User.is_active.is_(True))
    return q.order_by(User.full_name.asc().nullslast(), User.email.asc()).all()


def today_board(db: Session, now: datetime | None = None) -> TodayBoard:
    now = now or now_utc()
    d = today_local(now)
    working = is_working_day(d)
    recs = {
        r.user_id: r for r in db.query(AttendanceRecord).options(joinedload(AttendanceRecord.user)).filter(AttendanceRecord.work_date == d).all()
    }
    rows: list[TodayRow] = []
    present = late = absent = 0
    for u in _staff(db):
        rec = recs.get(u.id)
        if rec:
            status = rec.status
            if status == "late":
                late += 1
            else:
                present += 1
        elif not working or not _employed_on(u, d):
            status = "off"
        else:
            status = "absent"
            absent += 1
        rows.append(TodayRow(user_id=u.id, full_name=u.full_name, email=u.email, job_title=u.job_title, employment_type=u.employment_type, status=status, record=to_out(rec, now) if rec else None))
    order = {"late": 0, "present": 1, "absent": 2, "off": 3}
    rows.sort(key=lambda r: (order[r.status], (r.full_name or r.email).lower()))
    return TodayBoard(work_date=d, is_working_day=working, present=present, late=late, absent=absent, rows=rows)


def summary(db: Session, from_date: date, to_date: date, now: datetime | None = None, include_inactive: bool = False) -> AttendanceSummary:
    now = now or now_utc()
    today = today_local(now)
    end = min(to_date, today)
    days = [from_date + timedelta(days=i) for i in range((end - from_date).days + 1)] if end >= from_date else []
    wdays = [d for d in days if is_working_day(d)]
    recs = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.work_date >= from_date, AttendanceRecord.work_date <= to_date)
        .all()
    )
    by_user: dict[UUID, list[AttendanceRecord]] = {}
    for r in recs:
        by_user.setdefault(r.user_id, []).append(r)
    rows: list[SummaryRow] = []
    for u in _staff(db, include_inactive):
        mine = by_user.get(u.id, [])
        employed_wdays = [d for d in wdays if _employed_on(u, d)]
        present_days = len([r for r in mine if r.status == "present"])
        late_days = len([r for r in mine if r.status == "late"])
        logged = {r.work_date for r in mine}
        absent_days = len([d for d in employed_wdays if d not in logged])
        total_hours = round(sum(_hours(r, now) for r in mine if r.check_out_at), 2)
        completed = [r for r in mine if r.check_out_at]
        attended = present_days + late_days
        rows.append(SummaryRow(
            user_id=u.id, full_name=u.full_name, email=u.email, employment_type=u.employment_type,
            working_days=len(employed_wdays), present_days=present_days, late_days=late_days, absent_days=absent_days,
            total_hours=total_hours, avg_hours=(round(total_hours / len(completed), 2) if completed else None),
            attendance_rate=(round(attended / len(employed_wdays), 3) if employed_wdays else None),
        ))
    rows.sort(key=lambda r: (-(r.absent_days), -(r.late_days), (r.full_name or r.email).lower()))
    return AttendanceSummary(from_date=from_date, to_date=to_date, working_days=len(wdays), rows=rows)
