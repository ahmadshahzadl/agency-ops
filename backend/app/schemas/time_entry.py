from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class TimeEntryCreate(BaseModel):
    project_id: Optional[UUID] = None  # derived from task when omitted
    task_id: Optional[UUID] = None
    work_date: date
    hours: Decimal
    description: Optional[str] = None
    billable: bool = True
    hourly_rate: Optional[Decimal] = None
    user_id: Optional[UUID] = None  # managers/admins may log for others


class TimeEntryUpdate(BaseModel):
    work_date: Optional[date] = None
    hours: Optional[Decimal] = None
    description: Optional[str] = None
    billable: Optional[bool] = None
    hourly_rate: Optional[Decimal] = None
    task_id: Optional[UUID] = None


class TimeEntryResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    project_id: UUID
    project_name: Optional[str] = None
    task_id: Optional[UUID] = None
    task_title: Optional[str] = None
    work_date: date
    hours: Decimal
    description: Optional[str] = None
    billable: bool
    hourly_rate: Optional[Decimal] = None
    invoice_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeSummaryUser(BaseModel):
    user_id: UUID
    user_name: Optional[str] = None
    hours: Decimal


class TimeSummaryResponse(BaseModel):
    total_hours: Decimal
    billable_hours: Decimal
    unbilled_billable_hours: Decimal
    unbilled_amount: Decimal  # using entry rate, else project rate, else 0 for that entry
    by_user: list[TimeSummaryUser]


class InvoiceFromTimeRequest(BaseModel):
    project_id: UUID
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    hourly_rate: Optional[Decimal] = None  # fallback when entries and project define none
    number: Optional[str] = None
    currency: str = "USD"
    due_date: Optional[date] = None
