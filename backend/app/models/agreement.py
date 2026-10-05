import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Agreement(Base):
    __tablename__ = "agreements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(String(64), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="SET NULL"))
    status = Column(String(32), nullable=False, default="draft", server_default="draft")  # draft, sent, signed, declined, expired, terminated
    agreement_type = Column(String(32), nullable=False, default="service", server_default="service")  # nda | service | retainer | maintenance
    # Public signing link (prospects have no portal account). Expires with the signature deadline.
    sign_token = Column(String(64), unique=True, index=True)
    sign_token_expires_at = Column(DateTime(timezone=True))
    effective_date = Column(Date)
    valid_until = Column(Date)  # signature deadline while sent
    contract_value = Column(Numeric(14, 2))
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    clauses = Column(JSONB, nullable=False, default=list, server_default="[]")  # [{heading, body}] — snapshot, template edits never touch existing agreements
    accepted_at = Column(DateTime(timezone=True))
    accepted_by_name = Column(String(255))
    accepted_ip = Column(String(64))
    acceptance_method = Column(String(32))  # link (signing link) | portal (clickwrap record) | manual (wet signature)
    signer_email = Column(String(255))
    signer_title = Column(String(128))
    accepted_user_agent = Column(String(255))
    acceptance_hash = Column(String(64))  # sha256 over number + clauses + signer + time: ties the signature to this exact text
    countersigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    countersigned_by_name = Column(String(255))
    countersigned_at = Column(DateTime(timezone=True))
    decline_reason = Column(Text)
    terminated_at = Column(DateTime(timezone=True))
    termination_reason = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="agreements")
    project = relationship("Project")
    quote = relationship("Quote")
