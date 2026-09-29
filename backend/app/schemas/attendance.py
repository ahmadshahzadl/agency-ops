from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    accuracy_m: Optional[Decimal] = Field(None, ge=0)
    note: Optional[str] = Field(None, max_length=500)


class CheckOutRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=500)


class AttendanceRecordOut(BaseModel):
    id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    employment_type: Optional[str] = None
    work_date: date
    check_in_at: datetime
    check_out_at: Optional[datetime] = None
    status: str
    hours: Optional[float] = None  # worked hours when checked out, else hours so far
    ip_address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    location_accuracy_m: Optional[Decimal] = None
    user_agent: Optional[str] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceMe(BaseModel):
    today: Optional[AttendanceRecordOut] = None
    work_date: date
    captures_location: bool  # false for interns: nothing but the mark is stored
    start_time: str  # HH:MM, company time; later than this counts as late
    timezone: str
    recent: list[AttendanceRecordOut] = []
    present_days_30: int = 0
    late_days_30: int = 0


class TodayRow(BaseModel):
    user_id: UUID
    full_name: Optional[str] = None
    email: str
    job_title: Optional[str] = None
    employment_type: Optional[str] = None
    status: str  # present | late | absent | off (not a working day / not employed yet)
    record: Optional[AttendanceRecordOut] = None


class TodayBoard(BaseModel):
    work_date: date
    is_working_day: bool
    present: int
    late: int
    absent: int
    rows: list[TodayRow] = []


class SummaryRow(BaseModel):
    user_id: UUID
    full_name: Optional[str] = None
    email: str
    employment_type: Optional[str] = None
    working_days: int
    present_days: int
    late_days: int
    absent_days: int
    total_hours: float
    avg_hours: Optional[float] = None
    attendance_rate: Optional[float] = None  # present / working_days


class AttendanceSummary(BaseModel):
    from_date: date
    to_date: date
    working_days: int
    rows: list[SummaryRow] = []


class RecordCorrection(BaseModel):
    check_in_at: Optional[datetime] = None
    check_out_at: Optional[datetime] = None
    status: Optional[str] = None  # present | late
    note: Optional[str] = Field(None, max_length=500)
