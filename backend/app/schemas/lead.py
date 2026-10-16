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
    assigned_to: Optional[UUID] = None  # user working on lead (set when leaving "new" or assigned)


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
    assigned_to: Optional[UUID] = None


class LeadResponse(LeadBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_by_name: Optional[str] = None  # submitter display name for tracking
    assigned_to_name: Optional[str] = None  # assignee display name
    converted_to_client_id: Optional[UUID] = None
    converted_at: Optional[datetime] = None
    last_contact_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
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


# --- Interactions (contact history) and the merged timeline ---------------------------------

INTERACTION_TYPES = ("call", "email", "meeting", "whatsapp", "linkedin", "other")


class LeadInteractionCreate(BaseModel):
    type: str = "call"  # one of INTERACTION_TYPES
    summary: str
    occurred_at: Optional[datetime] = None  # defaults to now
    next_follow_up_at: Optional[datetime] = None
    status: Optional[str] = None  # optionally move the lead to a new stage in the same step


class LeadInteractionResponse(BaseModel):
    id: UUID
    lead_id: UUID
    type: str
    summary: str
    occurred_at: datetime
    next_follow_up_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadTimelineItem(BaseModel):
    """One row of a lead's history: a logged interaction, a status change or other audit entry,
    a meeting booked with the prospect, or a quote sent to them."""
    id: str
    kind: str  # interaction | activity | meeting | quote
    type: str  # interaction type, activity action, meeting status or quote status
    title: str
    details: Optional[str] = None
    by_name: Optional[str] = None
    occurred_at: datetime
    next_follow_up_at: Optional[datetime] = None
    reference_id: Optional[UUID] = None
