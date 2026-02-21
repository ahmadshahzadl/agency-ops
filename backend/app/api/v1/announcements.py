"""Announcements: admin creates; target all or specific users. Creates notifications for each target."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Announcement as AnnouncementModel, Notification as NotificationModel, User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/announcements", tags=["announcements"])


def _deliver_announcement(db: Session, announcement: AnnouncementModel) -> None:
    """Create a Notification for each target user."""
    if announcement.target_type == "all":
        user_ids = [u.id for u in db.query(User).filter(User.is_active == True).all()]
    else:
        user_ids = list(announcement.target_user_ids or [])
    for uid in user_ids:
        n = NotificationModel(
            user_id=uid,
            title=announcement.title,
            message=announcement.body,
            type="announcement",
            reference_id=announcement.id,
        )
        db.add(n)
    db.flush()


@router.get("", response_model=list[AnnouncementResponse])
def list_announcements(
    db: Session = Depends(get_db),
    user=Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    q = db.query(AnnouncementModel).order_by(AnnouncementModel.created_at.desc())
    return q.offset(skip).limit(limit).all()


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
    db.commit()
    db.refresh(ann)
    return ann


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == announcement_id).first()
    if not ann:
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
    db.delete(ann)
    db.commit()
