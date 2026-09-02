import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    work_date = Column(Date, nullable=False)
    hours = Column(Numeric(6, 2), nullable=False)
    description = Column(String(500))
    billable = Column(Boolean, nullable=False, default=True, server_default="true")
    # Rate snapshot/override for this entry; billing falls back to project.hourly_rate
    hourly_rate = Column(Numeric(10, 2))
    # Set when the entry is billed; entry becomes read-only until the invoice is deleted
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    project = relationship("Project", backref="time_entries")
    task = relationship("Task")
