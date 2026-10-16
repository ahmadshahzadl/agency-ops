"""Lead interactions: the contact history for a sales lead.

Every call, email, meeting or message with a prospect is logged here so the
whole team can see what was done with a lead and when to follow up next.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

INTERACTION_TYPES = ("call", "email", "meeting", "whatsapp", "linkedin", "other")


class LeadInteraction(Base):
    __tablename__ = "lead_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False, default="call")  # see INTERACTION_TYPES
    summary = Column(Text, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    next_follow_up_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    lead = relationship("Lead", back_populates="interactions")
    created_by_user = relationship("User", foreign_keys=[created_by])

    @property
    def created_by_name(self) -> str | None:
        if not self.created_by_user:
            return None
        return self.created_by_user.full_name or self.created_by_user.email
