"""BookingPage: a publicly bookable event type (e.g. "Discovery call") hosted by one user.

Slots are generated from ``hours`` (weekly windows in the page's timezone) minus the host's
existing meetings, then offered on the public website. A booking becomes a Meeting with
source="website" plus a Lead for unknown contacts.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class BookingPage(Base):
    __tablename__ = "booking_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False, default=30)
    buffer_before_minutes = Column(Integer, nullable=False, default=0)
    buffer_after_minutes = Column(Integer, nullable=False, default=15)
    min_notice_minutes = Column(Integer, nullable=False, default=240)
    max_days_ahead = Column(Integer, nullable=False, default=30)
    timezone = Column(String(64), nullable=False, default="UTC")
    # {"mon": [["11:00", "19:00"]], "tue": [...], ...} — windows in `timezone`; missing/empty day = closed
    hours = Column(JSONB, nullable=False, default=dict)
    # [{"id": "company", "label": "Company name", "type": "text"|"textarea", "required": true}, ...]
    questions = Column(JSONB, nullable=False, default=list)
    # Shown to the invitee as the meeting location (e.g. "Google Meet — link in your invite")
    location_text = Column(String(255))
    host_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    # Extra hosts (user ids as strings). Slots = union of all hosts' free time; bookings go
    # to the least-loaded host who is free.
    co_host_ids = Column(JSONB, nullable=False, default=list)
    # Per-date exceptions in `timezone`: {"2026-12-25": [], "2026-12-27": [["10:00","13:00"]]}
    # An empty list closes the day; windows replace the weekly hours for that date.
    overrides = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    host = relationship("User", foreign_keys=[host_user_id])
