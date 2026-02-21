from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AnnouncementCreate(BaseModel):
    title: str
    body: Optional[str] = None
    target_type: str = "all"  # "all" | "users"
    target_user_ids: Optional[list[UUID]] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    target_type: Optional[str] = None
    target_user_ids: Optional[list[UUID]] = None


class AnnouncementResponse(BaseModel):
    id: UUID
    title: str
    body: Optional[str] = None
    target_type: str
    target_user_ids: Optional[list[UUID]] = None
    created_by_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: Optional[str] = None
    link: Optional[str] = None
    type: str
    reference_id: Optional[UUID] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID]
