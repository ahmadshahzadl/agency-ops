from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

AGREEMENT_STATUSES = ("draft", "sent", "signed", "declined", "expired", "terminated")


class ClauseIn(BaseModel):
    heading: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)


class AgreementCreate(BaseModel):
    title: str
    client_id: UUID
    project_id: Optional[UUID] = None
    quote_id: Optional[UUID] = None
    effective_date: Optional[date] = None
    valid_until: Optional[date] = None
    contract_value: Optional[Decimal] = None
    currency: str = "USD"
    clauses: list[ClauseIn] = []


class AgreementUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    quote_id: Optional[UUID] = None
    effective_date: Optional[date] = None
    valid_until: Optional[date] = None
    contract_value: Optional[Decimal] = None
    currency: Optional[str] = None
    clauses: Optional[list[ClauseIn]] = None  # full replacement when provided


class AgreementResponse(BaseModel):
    id: UUID
    number: str
    title: str
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    quote_id: Optional[UUID] = None
    quote_number: Optional[str] = None
    status: str
    effective_date: Optional[date] = None
    valid_until: Optional[date] = None
    contract_value: Optional[Decimal] = None
    currency: str
    clauses: list[ClauseIn] = []
    accepted_at: Optional[datetime] = None
    accepted_by_name: Optional[str] = None
    accepted_ip: Optional[str] = None
    acceptance_method: Optional[str] = None
    decline_reason: Optional[str] = None
    terminated_at: Optional[datetime] = None
    termination_reason: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgreementTemplateResponse(BaseModel):
    clauses: list[ClauseIn]
