from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ActivityLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityLogWithUserResponse(ActivityLogResponse):
    """Activity log with reporter's email and name for manager view."""
    user_email: str = ""
    user_full_name: Optional[str] = None


class ReportSummary(BaseModel):
    """User who reports to the current user (manager's direct report)."""
    id: UUID
    email: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True
