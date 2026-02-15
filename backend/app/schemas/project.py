from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class ProjectBase(BaseModel):
    client_id: UUID
    name: str
    description: Optional[str] = None
    status: str = "draft"
    pipeline_stage: Optional[str] = "lead"
    assigned_team_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
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
    owner_id: Optional[UUID] = None


class ProjectResponse(ProjectBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
