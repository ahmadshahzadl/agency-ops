from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class NoteCreate(BaseModel):
    entity_type: str  # lead, task, meeting, project, client, invoice, expense, announcement
    entity_id: UUID
    content: str
    is_private: bool = True


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    is_private: Optional[bool] = None


class NoteResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    content: str
    is_private: bool
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True
