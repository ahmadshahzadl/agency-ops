"""Third-party account connections owned by a user (currently: Google Calendar).

Tokens are encrypted at rest with the same Fernet key as the credentials vault and never
leave the server; the API only ever reports the connected account's email."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class UserIntegration(Base):
    __tablename__ = "user_integrations"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_integrations_user_provider"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), nullable=False)  # "google"
    account_email = Column(String(255))
    refresh_token_encrypted = Column(Text, nullable=False)
    access_token_encrypted = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    scopes = Column(Text)
    calendar_id = Column(String(255), nullable=False, default="primary", server_default="primary")
    last_error = Column(Text)
    connected_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
