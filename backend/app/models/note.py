"""Notes: users can attach notes to leads, tasks, meetings, projects, clients, invoices, expenses, announcements.
Notes can be private (only creator sees) or visible to others who can access the entity."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(32), nullable=False)  # lead, task, meeting, project, client, invoice, expense, announcement
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text, nullable=False)
    is_private = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="notes")
