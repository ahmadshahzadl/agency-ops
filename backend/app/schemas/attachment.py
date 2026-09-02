from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AttachmentResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    filename: str
    content_type: Optional[str] = None
    size_bytes: int
    uploaded_by: Optional[UUID] = None
    uploaded_by_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
