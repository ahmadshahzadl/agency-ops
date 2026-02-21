"""Activity log for team members: managers can see their reports' actions and progress."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(64), nullable=False)  # task_created, task_updated, task_completed, project_created, etc.
    entity_type = Column(String(32), nullable=False)  # task, project, client, meeting, lead, invoice, expense
    entity_id = Column(UUID(as_uuid=True))
    details = Column(Text)  # human-readable summary for manager
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="activity_logs")
