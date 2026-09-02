from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

QUOTE_STATUSES = ("draft", "sent", "accepted", "rejected", "expired")


class QuoteItemIn(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")


class QuoteItemResponse(QuoteItemIn):
    id: UUID
    position: int
    line_total: Decimal

    class Config:
        from_attributes = True


class QuoteCreate(BaseModel):
    title: str
    client_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    currency: str = "USD"
    valid_until: Optional[date] = None
    terms: Optional[str] = None
    items: list[QuoteItemIn] = []


class QuoteUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    currency: Optional[str] = None
    valid_until: Optional[date] = None
    terms: Optional[str] = None
    items: Optional[list[QuoteItemIn]] = None  # full replacement when provided


class QuoteResponse(BaseModel):
    id: UUID
    number: str
    title: str
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    lead_id: Optional[UUID] = None
    lead_company: Optional[str] = None
    status: str
    currency: str
    total: Decimal
    valid_until: Optional[date] = None
    terms: Optional[str] = None
    project_id: Optional[UUID] = None
    accepted_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    items: list[QuoteItemResponse] = []

    class Config:
        from_attributes = True
