from pydantic import BaseModel, field_serializer
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone


def _serialize_datetime_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


class MessageCreate(BaseModel):
    recipient_id: UUID
    content: str


class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    content: str
    read_at: Optional[datetime] = None
    created_at: datetime
    sender_name: Optional[str] = None

    @field_serializer("created_at", "read_at")
    def _serialize_dt(self, dt: datetime | None) -> str | None:
        return _serialize_datetime_utc(dt)

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    other_user_id: UUID
    other_user_name: str
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    unread_count: int = 0

    @field_serializer("last_message_at")
    def _serialize_dt(self, dt: datetime | None) -> str | None:
        return _serialize_datetime_utc(dt)
