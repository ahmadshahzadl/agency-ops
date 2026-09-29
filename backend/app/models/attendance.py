"""One row per employee per working day. Regular staff also leave their IP and browser location;
interns only mark the day (nothing else is captured for them)."""
import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("user_id", "work_date", name="uq_attendance_user_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, index=True)  # in the company timezone
    check_in_at = Column(DateTime(timezone=True), nullable=False)
    check_out_at = Column(DateTime(timezone=True))
    status = Column(String(16), nullable=False, default="present")  # present | late
    ip_address = Column(String(64))
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    location_accuracy_m = Column(Numeric(10, 1))
    user_agent = Column(String(255))
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
