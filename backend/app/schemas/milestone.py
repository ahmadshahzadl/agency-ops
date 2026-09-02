from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class MilestoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    position: int = 0


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    position: Optional[int] = None


class MilestoneResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    position: int
    completed_at: Optional[datetime] = None
    state: str = "upcoming"  # upcoming | overdue | completed
    task_total: int = 0
    task_done: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
