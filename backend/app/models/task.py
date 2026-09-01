import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, Integer, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(32), default="todo")  # todo, in_progress, review, qa_failed, done
    priority = Column(String(16), default="medium")  # low, medium, high
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    due_date = Column(Date)
    order_index = Column(Integer, default=0)
    # QA workflow
    item_type = Column(String(16), nullable=False, default="task", server_default="task")  # task, bug
    severity = Column(String(16))  # low, medium, high, critical (bugs)
    steps_to_reproduce = Column(Text)
    environment = Column(String(255))
    qa_notes = Column(Text)
    qa_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    qa_at = Column(DateTime(timezone=True))
    # Kanban board placement
    board_id = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="SET NULL"))
    column_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks_assigned", foreign_keys=[assignee_id])
    board = relationship("Board", back_populates="tasks")
