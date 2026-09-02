"""Announcements: admin creates; target all or specific users. Creates notifications for each target."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Announcement as AnnouncementModel, Notification as NotificationModel, User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.api.deps import get_current_user, require_admin, require_any_permission, get_user_permissions
from app.services.activity_service import log_activity, notifications_updated_this_request
from app.services import email_service

router = APIRouter(prefix="/announcements", tags=["announcements"])


def _deliver_announcement(db: Session, announcement: AnnouncementModel) -> None:
    """Create a Notification (and send an email) for each target user."""
    if announcement.target_type == "all":
        users = db.query(User).filter(User.is_active == True).all()
    else:
        ids = list(announcement.target_user_ids or [])
        users = db.query(User).filter(User.id.in_(ids), User.is_active == True).all() if ids else []
    for u in users:
        n = NotificationModel(
            user_id=u.id,
            title=announcement.title,
            message=announcement.body,
            type="announcement",
            reference_id=announcement.id,
        )
        db.add(n)
        email_service.send_notification(u.email, f"Announcement: {announcement.title}", announcement.body, "/announcements")
    db.flush()


def _can_see_announcement(ann: AnnouncementModel, user, is_admin: bool) -> bool:
    """Broadcast announcements are visible to all; targeted ones only to their targets (and admins/author)."""
    if is_admin or ann.target_type == "all" or ann.created_by_id == user.id:
        return True
    return user.id in (ann.target_user_ids or [])


@router.get("", response_model=list[AnnouncementResponse])
def list_announcements(
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("announcements:read")),
    permissions=Depends(get_user_permissions),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    is_admin = "admin:all" in permissions
    q = db.query(AnnouncementModel).order_by(AnnouncementModel.created_at.desc())
    visible = [a for a in q.all() if _can_see_announcement(a, user, is_admin)]
    return visible[skip:skip + limit]


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if data.target_type == "users" and (not data.target_user_ids or len(data.target_user_ids) == 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_user_ids required when target_type is 'users'")
    ann = AnnouncementModel(
        title=data.title,
        body=data.body,
        target_type=data.target_type,
        target_user_ids=data.target_user_ids,
        created_by_id=user.id,
    )
    db.add(ann)
    db.flush()
    _deliver_announcement(db, ann)
    notifications_updated_this_request.set(True)
    log_activity(db, user.id, "announcement_created", "announcement", ann.id, details=f"Announcement: {ann.title}")
    db.commit()
    db.refresh(ann)
    return ann


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("announcements:read")),
    permissions=Depends(get_user_permissions),
):
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == announcement_id).first()
    if not ann or not _can_see_announcement(ann, user, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return ann


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: UUID,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(ann, k, v)
    db.commit()
    db.refresh(ann)
    return ann


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    log_activity(db, user.id, "announcement_deleted", "announcement", announcement_id, details=f"Announcement deleted: {ann.title}")
    db.delete(ann)
    db.commit()
