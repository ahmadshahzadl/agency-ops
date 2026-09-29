"""Attendance: every internal user marks their own day; admins (attendance:manage) see the board,
the period summary, every record, and can correct a record."""
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_permission
from app.database import get_db
from app.models import AttendanceRecord, User
from app.schemas.attendance import (
    AttendanceMe, AttendanceRecordOut, AttendanceSummary, CheckInRequest, CheckOutRequest, RecordCorrection, TodayBoard,
)
from app.services import attendance_service as svc
from app.services.activity_service import log_activity

router = APIRouter(prefix="/attendance", tags=["attendance"])
MANAGE = "attendance:manage"


def _internal(user: User) -> User:
    if user.client_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance is for internal staff")
    return user


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return (request.client.host if request.client else None)


# ------------------------------ self ------------------------------

@router.get("/me", response_model=AttendanceMe)
def my_attendance(db: Session = Depends(get_db), user: User = Depends(get_current_user), days: int = Query(30, ge=1, le=120)):
    _internal(user)
    now = svc.now_utc()
    today = svc.today_local(now)
    since = today - timedelta(days=days)
    recent = (
        db.query(AttendanceRecord).options(joinedload(AttendanceRecord.user))
        .filter(AttendanceRecord.user_id == user.id, AttendanceRecord.work_date >= since)
        .order_by(AttendanceRecord.work_date.desc()).all()
    )
    today_rec = next((r for r in recent if r.work_date == today), None)
    s = svc.get_settings()
    return AttendanceMe(
        today=svc.to_out(today_rec, now) if today_rec else None,
        work_date=today,
        captures_location=svc.captures_location(user),
        start_time=s.attendance_start_time,
        timezone=s.company_timezone,
        recent=[svc.to_out(r, now) for r in recent],
        present_days_30=len([r for r in recent if r.status == "present"]),
        late_days_30=len([r for r in recent if r.status == "late"]),
    )


@router.post("/check-in", response_model=AttendanceRecordOut, status_code=status.HTTP_201_CREATED)
def check_in(data: CheckInRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _internal(user)
    try:
        rec = svc.check_in(
            db, user, ip=_client_ip(request), user_agent=request.headers.get("user-agent"),
            latitude=data.latitude, longitude=data.longitude, accuracy_m=data.accuracy_m, note=data.note,
        )
    except svc.AttendanceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    db.commit()
    return svc.to_out(svc.record_for(db, user.id, rec.work_date))


@router.post("/check-out", response_model=AttendanceRecordOut)
def check_out(data: CheckOutRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _internal(user)
    try:
        rec = svc.check_out(db, user, data.note)
    except svc.AttendanceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    db.commit()
    return svc.to_out(svc.record_for(db, user.id, rec.work_date))


# ------------------------------ admin ------------------------------

@router.get("/today", response_model=TodayBoard)
def today(db: Session = Depends(get_db), user=Depends(require_permission(MANAGE))):
    return svc.today_board(db)


@router.get("/summary", response_model=AttendanceSummary)
def period_summary(
    db: Session = Depends(get_db), user=Depends(require_permission(MANAGE)),
    from_date: date | None = Query(None, alias="from"), to_date: date | None = Query(None, alias="to"),
    include_inactive: bool = Query(False),
):
    today = svc.today_local()
    to_date = to_date or today
    from_date = from_date or (to_date - timedelta(days=29))
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from must be on or before to")
    if (to_date - from_date).days > 366:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Range must be a year or less")
    return svc.summary(db, from_date, to_date, include_inactive=include_inactive)


@router.get("/records", response_model=list[AttendanceRecordOut])
def list_records(
    db: Session = Depends(get_db), user=Depends(require_permission(MANAGE)),
    from_date: date | None = Query(None, alias="from"), to_date: date | None = Query(None, alias="to"),
    user_id: UUID | None = None, limit: int = Query(200, ge=1, le=1000),
):
    today = svc.today_local()
    to_date = to_date or today
    from_date = from_date or (to_date - timedelta(days=29))
    q = (
        db.query(AttendanceRecord).options(joinedload(AttendanceRecord.user))
        .filter(AttendanceRecord.work_date >= from_date, AttendanceRecord.work_date <= to_date)
    )
    if user_id:
        q = q.filter(AttendanceRecord.user_id == user_id)
    rows = q.order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.check_in_at.desc()).limit(limit).all()
    now = svc.now_utc()
    return [svc.to_out(r, now) for r in rows]


@router.patch("/records/{record_id}", response_model=AttendanceRecordOut)
def correct_record(record_id: UUID, data: RecordCorrection, db: Session = Depends(get_db), user=Depends(require_permission(MANAGE))):
    rec = db.query(AttendanceRecord).options(joinedload(AttendanceRecord.user)).filter(AttendanceRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in svc.STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"status must be one of: {', '.join(svc.STATUSES)}")
    for k, v in updates.items():
        setattr(rec, k, v)
    if rec.check_out_at and rec.check_out_at < rec.check_in_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="check_out_at must be after check_in_at")
    db.flush()
    log_activity(db, user.id, "attendance_corrected", "attendance", rec.id, details=f"{rec.user.email if rec.user else rec.user_id} {rec.work_date}: {', '.join(sorted(updates))}")
    db.commit()
    db.refresh(rec)
    return svc.to_out(rec)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(MANAGE))):
    rec = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    log_activity(db, user.id, "attendance_deleted", "attendance", rec.id, details=f"{rec.user_id} {rec.work_date}")
    db.delete(rec)
    db.commit()
