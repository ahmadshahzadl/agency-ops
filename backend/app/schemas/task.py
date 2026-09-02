from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date

VALID_STATUSES = ("todo", "in_progress", "review", "qa_failed", "done")
VALID_ITEM_TYPES = ("task", "bug")
VALID_SEVERITIES = ("low", "medium", "high", "critical")


class TaskBase(BaseModel):
    project_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None
    order_index: int = 0
    item_type: str = "task"
    severity: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    board_id: Optional[UUID] = None
    column_order: int = 0
    milestone_id: Optional[UUID] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    project_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[date] = None
    order_index: Optional[int] = None
    item_type: Optional[str] = None
    severity: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    qa_notes: Optional[str] = None
    board_id: Optional[UUID] = None
    column_order: Optional[int] = None
    milestone_id: Optional[UUID] = None


class TaskResponse(TaskBase):
    id: UUID
    qa_notes: Optional[str] = None
    qa_by: Optional[UUID] = None
    qa_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
