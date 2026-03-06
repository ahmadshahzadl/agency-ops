import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    phone = Column(String(64))
    job_title = Column(String(128))
    is_active = Column(Boolean, default=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    manager = relationship("User", remote_side=[id], back_populates="reports", foreign_keys=[manager_id])
    reports = relationship("User", back_populates="manager", foreign_keys=[manager_id])
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    teams = relationship("Team", secondary="team_members", back_populates="users")
    clients_created = relationship("Client", back_populates="created_by_user", foreign_keys="Client.created_by")
    leads_created = relationship("Lead", back_populates="created_by_user", foreign_keys="Lead.created_by")
    leads_assigned = relationship("Lead", back_populates="assigned_to_user", foreign_keys="Lead.assigned_to")
    projects_owned = relationship("Project", back_populates="owner")
    tasks_assigned = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    meetings_created = relationship("Meeting", back_populates="created_by_user", foreign_keys="Meeting.created_by")
    announcements_created = relationship("Announcement", back_populates="created_by_user", foreign_keys="Announcement.created_by_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
