from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class TaskBase(BaseModel):
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None
    order_index: int = 0


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None
    order_index: Optional[int] = None


class TaskResponse(TaskBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
