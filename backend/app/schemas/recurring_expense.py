from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

FREQUENCIES = ("weekly", "monthly", "quarterly", "yearly")
EMPLOYMENT_TYPES = ("full_time", "part_time", "contractor", "intern")


class RecurringExpenseBase(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    category: str = "other"
    amount: Decimal
    currency: str = "PKR"
    frequency: str = "monthly"
    due_day: int = Field(1, ge=1, le=31)
    project_id: Optional[UUID] = None
    payee_user_id: Optional[UUID] = None
    notes: Optional[str] = None
    remind_days_before: list[int] = Field(default_factory=lambda: [2, 1, 0])


class RecurringExpenseCreate(RecurringExpenseBase):
    # Optional: start from a specific date instead of the next matching day
    next_due_date: Optional[date] = None
    is_active: bool = True


class RecurringExpenseUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    frequency: Optional[str] = None
    due_day: Optional[int] = Field(None, ge=1, le=31)
    next_due_date: Optional[date] = None
    project_id: Optional[UUID] = None
    payee_user_id: Optional[UUID] = None
    notes: Optional[str] = None
    remind_days_before: Optional[list[int]] = None
    is_active: Optional[bool] = None


class RecurringExpenseResponse(RecurringExpenseBase):
    id: UUID
    next_due_date: date
    last_paid_on: Optional[date] = None
    is_active: bool
    status: str  # scheduled | due_soon | due_today | overdue | paused
    days_until_due: int
    payee_name: Optional[str] = None
    project_name: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecurringPayIn(BaseModel):
    paid_on: Optional[date] = None
    amount: Optional[Decimal] = None  # override when the bill differed this period
    note: Optional[str] = Field(None, max_length=500)


# ---------------- payroll ----------------

class PayrollRow(BaseModel):
    user_id: UUID
    full_name: Optional[str] = None
    email: str
    job_title: Optional[str] = None
    employment_type: Optional[str] = None
    joined_on: Optional[date] = None
    left_on: Optional[date] = None
    is_active: bool
    salary_id: Optional[UUID] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    frequency: Optional[str] = None
    due_day: Optional[int] = None
    next_due_date: Optional[date] = None
    last_paid_on: Optional[date] = None
    salary_active: bool = False
    status: str  # not_set | scheduled | due_soon | due_today | overdue | paused
    days_until_due: Optional[int] = None
    paid_this_period: bool = False


class PayrollUpdate(BaseModel):
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    due_day: Optional[int] = Field(None, ge=1, le=31)
    frequency: Optional[str] = None
    salary_active: Optional[bool] = None
    employment_type: Optional[str] = None
    joined_on: Optional[date] = None
    left_on: Optional[date] = None
    job_title: Optional[str] = None
