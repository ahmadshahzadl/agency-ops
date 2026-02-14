from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class LeadBase(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = "new"
    notes: Optional[str] = None
    assigned_team_id: Optional[UUID] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_team_id: Optional[UUID] = None


class LeadResponse(LeadBase):
    id: UUID
    created_by: Optional[UUID] = None
    converted_to_client_id: Optional[UUID] = None
    converted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadConvertRequest(BaseModel):
    """Create client and optional project from lead."""
    client_team_id: Optional[UUID] = None  # team to assign the new client to (e.g. Sales)
    create_project: bool = True
    project_name: Optional[str] = None  # default: same as company_name
    project_pipeline_stage: str = "discovery"
    project_assigned_team_id: Optional[UUID] = None
