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
    user_id: UUID


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
