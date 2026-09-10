from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date

LETTER_STATUSES = ("draft", "issued")


class LetterCreate(BaseModel):
    letter_type: str = "general"
    subject: str
    body: str
    recipient_name: Optional[str] = None
    recipient_address: Optional[str] = None
    recipient_email: Optional[str] = None
    client_id: Optional[UUID] = None
    letter_date: Optional[date] = None
    signatory_name: Optional[str] = None
    signatory_title: Optional[str] = None


class LetterUpdate(BaseModel):
    letter_type: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_address: Optional[str] = None
    recipient_email: Optional[str] = None
    client_id: Optional[UUID] = None
    letter_date: Optional[date] = None
    signatory_name: Optional[str] = None
    signatory_title: Optional[str] = None


class LetterResponse(BaseModel):
    id: UUID
    number: str
    letter_type: str
    subject: str
    recipient_name: Optional[str] = None
    recipient_address: Optional[str] = None
    recipient_email: Optional[str] = None
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    body: str
    letter_date: Optional[date] = None
    signatory_name: Optional[str] = None
    signatory_title: Optional[str] = None
    status: str
    issued_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LetterTemplateResponse(BaseModel):
    letter_type: str
    subject: str
    body: str
