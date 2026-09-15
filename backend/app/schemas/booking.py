from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
Hours = dict[str, list[list[str]]]


def _validate_timezone(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        raise ValueError(f"Unknown timezone: {tz}")
    return tz


def _validate_overrides(overrides: dict) -> dict:
    clean: dict = {}
    for day, windows in (overrides or {}).items():
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Override key must be YYYY-MM-DD, got {day!r}")
        clean[day] = _validate_hours({"mon": windows or []}).get("mon", [])
    return clean


def _validate_hours(hours: Hours) -> Hours:
    clean: Hours = {}
    for day, windows in (hours or {}).items():
        if day not in DAYS:
            raise ValueError(f"Unknown weekday key: {day}")
        out = []
        for w in windows or []:
            if len(w) != 2:
                raise ValueError("Each window must be [start, end]")
            start, end = w
            for t in (start, end):
                try:
                    h, m = t.split(":")
                    if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                        raise ValueError
                except Exception:
                    raise ValueError(f"Bad time '{t}', expected HH:MM")
            if start >= end:
                raise ValueError(f"Window {start}-{end} on {day} ends before it starts")
            out.append([start, end])
        if out:
            clean[day] = sorted(out)
    return clean


class BookingQuestion(BaseModel):
    id: str = Field(min_length=1, max_length=48, pattern=r"^[a-z0-9_\-]+$")
    label: str = Field(min_length=1, max_length=200)
    type: Literal["text", "textarea"] = "text"
    required: bool = False


# ---------------- admin ----------------

class BookingPageBase(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(30, ge=5, le=480)
    buffer_before_minutes: int = Field(0, ge=0, le=240)
    buffer_after_minutes: int = Field(15, ge=0, le=240)
    min_notice_minutes: int = Field(240, ge=0, le=20160)
    max_days_ahead: int = Field(30, ge=1, le=365)
    timezone: str = "UTC"
    hours: Hours = {}
    questions: list[BookingQuestion] = []
    location_text: Optional[str] = Field(None, max_length=255)
    host_user_id: Optional[UUID] = None
    co_host_ids: list[UUID] = []
    overrides: dict[str, list[list[str]]] = {}
    is_active: bool = True

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        return _validate_timezone(v)

    @field_validator("overrides")
    @classmethod
    def _ov(cls, v: dict) -> dict:
        return _validate_overrides(v)

    @field_validator("hours")
    @classmethod
    def _hours(cls, v: Hours) -> Hours:
        return _validate_hours(v)

    @field_validator("questions")
    @classmethod
    def _unique_question_ids(cls, v: list[BookingQuestion]) -> list[BookingQuestion]:
        ids = [q.id for q in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Question ids must be unique")
        return v


class BookingPageCreate(BookingPageBase):
    pass


class BookingPageUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    buffer_before_minutes: Optional[int] = Field(None, ge=0, le=240)
    buffer_after_minutes: Optional[int] = Field(None, ge=0, le=240)
    min_notice_minutes: Optional[int] = Field(None, ge=0, le=20160)
    max_days_ahead: Optional[int] = Field(None, ge=1, le=365)
    timezone: Optional[str] = None
    hours: Optional[Hours] = None
    questions: Optional[list[BookingQuestion]] = None
    location_text: Optional[str] = Field(None, max_length=255)
    host_user_id: Optional[UUID] = None
    co_host_ids: Optional[list[UUID]] = None
    overrides: Optional[dict[str, list[list[str]]]] = None
    is_active: Optional[bool] = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: Optional[str]) -> Optional[str]:
        return _validate_timezone(v) if v is not None else v

    @field_validator("overrides")
    @classmethod
    def _ov(cls, v: Optional[dict]) -> Optional[dict]:
        return _validate_overrides(v) if v is not None else v

    @field_validator("hours")
    @classmethod
    def _hours(cls, v: Optional[Hours]) -> Optional[Hours]:
        return _validate_hours(v) if v is not None else v


class BookingHostInfo(BaseModel):
    id: UUID
    name: str
    google_connected: bool = False


class BookingPageResponse(BookingPageBase):
    id: UUID
    host_name: Optional[str] = None
    host_google_connected: bool = False
    hosts: list[BookingHostInfo] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------- public ----------------

class PublicBookingPage(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    duration_minutes: int
    timezone: str
    questions: list[BookingQuestion]
    location_text: Optional[str] = None
    host_name: Optional[str] = None
    min_notice_minutes: int
    max_days_ahead: int


class PublicSlots(BaseModel):
    slug: str
    timezone: str
    start: str
    end: str
    slots: list[datetime]


class PublicBookRequest(BaseModel):
    start: datetime
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    timezone: str = "UTC"
    answers: dict[str, Any] = {}
    # utm_* / referrer / landing_page captured on the website
    tracking: dict[str, Any] = {}
    # Honeypot: real users never fill it; bots often do.
    website: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        return _validate_timezone(v)


class PublicBooking(BaseModel):
    manage_token: str
    status: str
    page: PublicBookingPage
    start: datetime
    end: datetime
    invitee_name: str
    invitee_email: str
    invitee_timezone: Optional[str] = None
    location: Optional[str] = None
    cancel_reason: Optional[str] = None


class PublicCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class PublicRescheduleRequest(BaseModel):
    start: datetime
    timezone: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: Optional[str]) -> Optional[str]:
        return _validate_timezone(v) if v else v
