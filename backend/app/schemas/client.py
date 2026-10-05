from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


CLIENT_STATUSES = ("prospect", "active", "archived")


class ClientBase(BaseModel):
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    team_id: Optional[UUID] = None
    status: str = "active"  # prospect | active | archived


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    team_id: Optional[UUID] = None
    status: Optional[str] = None


class ClientResponse(ClientBase):
    id: UUID
    team_id: Optional[UUID] = None
    nda_status: str = "none"  # none | draft | sent | signed | declined | expired | terminated
    nda_signed_at: Optional[datetime] = None
    source: Optional[str] = None  # from the converted lead (website, calendly, referral, ...)
    solutions_engineer_id: Optional[UUID] = None
    solutions_engineer_name: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
