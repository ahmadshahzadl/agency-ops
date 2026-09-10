import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Letter(Base):
    __tablename__ = "letters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(String(64), unique=True, nullable=False)
    letter_type = Column(String(32), nullable=False, default="general", server_default="general")  # general, offer_letter, experience_letter, noc, completion_certificate
    subject = Column(String(255), nullable=False)
    recipient_name = Column(String(255))  # a person or organization; letters aren't always to clients
    recipient_address = Column(Text)
    recipient_email = Column(String(255))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))
    body = Column(Text, nullable=False)
    letter_date = Column(Date)
    signatory_name = Column(String(255))
    signatory_title = Column(String(255))
    status = Column(String(32), nullable=False, default="draft", server_default="draft")  # draft, issued
    issued_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client")
