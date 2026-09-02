from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal


class InvoiceBase(BaseModel):
    client_id: UUID
    project_id: Optional[UUID] = None
    number: str
    amount: Decimal
    currency: str = "USD"
    status: str = "draft"
    due_date: Optional[date] = None
    issued_at: Optional[date] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    number: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    issued_at: Optional[date] = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    quote_id: Optional[UUID] = None
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


class ExpenseBase(BaseModel):
    project_id: Optional[UUID] = None
    description: str
    amount: Decimal
    currency: str = "USD"
    expense_date: Optional[date] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    expense_date: Optional[date] = None


class ExpenseResponse(ExpenseBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
