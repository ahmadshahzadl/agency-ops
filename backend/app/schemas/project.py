from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class ProjectBase(BaseModel):
    client_id: UUID
    name: str
    description: Optional[str] = None
    status: str = "draft"
    pipeline_stage: Optional[str] = "lead"
    assigned_team_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    hourly_rate: Optional[Decimal] = None
    owner_id: Optional[UUID] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    pipeline_stage: Optional[str] = None
    assigned_team_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    hourly_rate: Optional[Decimal] = None
    owner_id: Optional[UUID] = None


class ProjectResponse(ProjectBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    client_name: Optional[str] = None  # populated in list for display without clients:read
    task_count: Optional[int] = None  # total tasks (for progress)
    task_done_count: Optional[int] = None  # completed tasks (for progress)

    class Config:
        from_attributes = True


class ProjectNameResponse(BaseModel):
    """Minimal project info (id, name) for display; allowed for all authenticated users."""
    id: UUID
    name: str

    class Config:
        from_attributes = True
