"""Lead model: sales lead before conversion to Client + Project."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(64))
    source = Column(String(64))  # website, referral, cold_outreach, etc.
    status = Column(String(32), default="new")  # new, contacted, qualified, converted, lost
    notes = Column(Text)
    assigned_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    converted_to_client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))
    converted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_team = relationship("Team", back_populates="leads")
    created_by_user = relationship("User", back_populates="leads_created", foreign_keys=[created_by])
    converted_to_client = relationship("Client", back_populates="source_lead", foreign_keys=[converted_to_client_id])
