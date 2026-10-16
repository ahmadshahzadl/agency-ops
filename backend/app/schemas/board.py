from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class BoardCreate(BaseModel):
    project_id: UUID
    name: str
    position: int = 0
    member_ids: list[UUID] = []


class BoardUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None


class BoardMemberAdd(BaseModel):
    """Add one user (user_id) or several at once (user_ids); at least one is required."""
    user_id: Optional[UUID] = None
    user_ids: list[UUID] = []

    def all_user_ids(self) -> list[UUID]:
        ids: list[UUID] = []
        for uid in ([self.user_id] if self.user_id else []) + list(self.user_ids):
            if uid not in ids:
                ids.append(uid)
        return ids


class BoardMemberResponse(BaseModel):
    user_id: UUID
    full_name: Optional[str] = None
    email: Optional[str] = None


class BoardResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    position: int
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    members: list[BoardMemberResponse] = []
    task_count: int = 0

    class Config:
        from_attributes = True
