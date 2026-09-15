from pydantic import BaseModel
from typing import Any, Optional
from uuid import UUID
from datetime import datetime


class MeetingBase(BaseModel):
    project_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    start_at: datetime
    end_at: datetime
    location: Optional[str] = None


class MeetingCreate(MeetingBase):
    attendee_ids: list[UUID] = []


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    attendee_ids: Optional[list[UUID]] = None


class MeetingResponse(MeetingBase):
    id: UUID
    source: str = "manual"
    external_id: Optional[str] = None
    status: str = "scheduled"
    invitee_name: Optional[str] = None
    invitee_email: Optional[str] = None
    cancel_reason: Optional[str] = None
    lead_id: Optional[UUID] = None
    booking_page_id: Optional[UUID] = None
    invitee_timezone: Optional[str] = None
    answers: Optional[dict[str, Any]] = None
    google_event_id: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    attendee_ids: list[UUID] = []

    class Config:
        from_attributes = True
