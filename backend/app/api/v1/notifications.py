"""Notifications: list current user's notifications, mark as read."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification as NotificationModel
from app.schemas.announcement import NotificationResponse, MarkReadRequest
from app.api.deps import get_current_user
from app.services.activity_service import notifications_updated_this_request

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    unread_only: bool = Query(False, description="Only unread"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    q = db.query(NotificationModel).filter(NotificationModel.user_id == user.id)
    if unread_only:
        q = q.filter(NotificationModel.read_at.is_(None))
    q = q.order_by(NotificationModel.created_at.desc())
    return q.offset(skip).limit(limit).all()


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    n = db.query(NotificationModel).filter(
        NotificationModel.user_id == user.id,
        NotificationModel.read_at.is_(None),
    ).count()
    return {"count": n}


@router.post("/mark-read", status_code=204)
def mark_read(
    data: MarkReadRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not data.notification_ids:
        return
    now = datetime.now(timezone.utc)
    db.query(NotificationModel).filter(
        NotificationModel.id.in_(data.notification_ids),
        NotificationModel.user_id == user.id,
    ).update({NotificationModel.read_at: now}, synchronize_session=False)
    notifications_updated_this_request.set(True)
    db.commit()


@router.post("/{notification_id}/mark-read", status_code=204)
def mark_one_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    n = db.query(NotificationModel).filter(
        NotificationModel.id == notification_id,
        NotificationModel.user_id == user.id,
    ).first()
    if n:
        n.read_at = datetime.now(timezone.utc)
        notifications_updated_this_request.set(True)
        db.commit()


@router.post("/mark-all-read", status_code=204)
def mark_all_read(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    db.query(NotificationModel).filter(
        NotificationModel.user_id == user.id,
        NotificationModel.read_at.is_(None),
    ).update({NotificationModel.read_at: now}, synchronize_session=False)
    notifications_updated_this_request.set(True)
    db.commit()
