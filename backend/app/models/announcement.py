"""Announcement: admin creates; target all users or specific users. Delivered as Notifications."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    body = Column(Text)
    target_type = Column(String(16), nullable=False, default="all")  # "all" | "users"
    target_user_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # when target_type=users
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    created_by_user = relationship("User", back_populates="announcements_created", foreign_keys=[created_by_id])
    notifications = relationship("Notification", back_populates="announcement", cascade="all, delete-orphan")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    link = Column(String(512))  # optional route or URL
    type = Column(String(32), default="announcement")
    reference_id = Column(UUID(as_uuid=True), ForeignKey("announcements.id", ondelete="SET NULL"), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
    announcement = relationship("Announcement", back_populates="notifications", foreign_keys=[reference_id])
