from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class InvoiceItemIn(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")


class InvoiceItemResponse(InvoiceItemIn):
    id: UUID
    position: int

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    client_id: UUID
    project_id: Optional[UUID] = None
    number: str
    amount: Decimal
    currency: str = "USD"
    status: str = "draft"
    due_date: Optional[date] = None
    issued_at: Optional[date] = None
    fx_currency: Optional[str] = None
    fx_rate: Optional[Decimal] = None
    bank_name: Optional[str] = None
    account_title: Optional[str] = None
    account_number: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    number: Optional[str] = None  # auto-generated when empty
    amount: Decimal = Decimal("0")  # optional when items are given (derived)
    items: list[InvoiceItemIn] = []


class InvoiceUpdate(BaseModel):
    number: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    issued_at: Optional[date] = None
    fx_currency: Optional[str] = None
    fx_rate: Optional[Decimal] = None
    bank_name: Optional[str] = None
    account_title: Optional[str] = None
    account_number: Optional[str] = None
    items: Optional[list[InvoiceItemIn]] = None  # full replacement when provided


class InvoiceResponse(InvoiceBase):
    id: UUID
    quote_id: Optional[UUID] = None
    items: list[InvoiceItemResponse] = []
    paid_total: Optional[Decimal] = None  # populated on single-invoice fetch
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentBase(BaseModel):
    invoice_id: UUID
    amount: Decimal
    paid_at: date
    reference: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


EXPENSE_CATEGORIES = ("office", "commission", "salary", "software", "travel", "other")


class ExpenseBase(BaseModel):
    project_id: Optional[UUID] = None
    description: str
    category: str = "other"
    amount: Decimal = Decimal("0")  # optional for commissions (computed from invoice x percent)
    currency: str = "PKR"
    expense_date: Optional[date] = None
    related_invoice_id: Optional[UUID] = None
    payee_user_id: Optional[UUID] = None
    commission_percent: Optional[Decimal] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    expense_date: Optional[date] = None
    payee_user_id: Optional[UUID] = None
    commission_percent: Optional[Decimal] = None


class ExpenseResponse(ExpenseBase):
    id: UUID
    payee_name: Optional[str] = None
    invoice_number: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
