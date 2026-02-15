from pydantic import BaseModel
from typing import Optional
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
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    attendee_ids: list[UUID] = []

    class Config:
        from_attributes = True
