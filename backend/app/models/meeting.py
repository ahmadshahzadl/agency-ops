import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255))
    # Where the meeting came from: "manual" (created in the app) or "calendly" (webhook).
    source = Column(String(32), nullable=False, default="manual", server_default="manual")
    # Stable id in the external system (Calendly invitee URI); unique so webhook retries are idempotent.
    external_id = Column(String(512), unique=True, index=True)
    status = Column(String(32), nullable=False, default="scheduled", server_default="scheduled")  # scheduled | canceled
    invitee_name = Column(String(255))
    invitee_email = Column(String(255))
    cancel_reason = Column(Text)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="meetings")
    created_by_user = relationship("User", back_populates="meetings_created", foreign_keys=[created_by])
    lead = relationship("Lead", foreign_keys=[lead_id])
    attendee_links = relationship("MeetingAttendee", back_populates="meeting", cascade="all, delete-orphan")


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"

    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    meeting = relationship("Meeting", back_populates="attendee_links")
