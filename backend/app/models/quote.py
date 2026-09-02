import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Integer, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(String(64), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"))
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"))
    status = Column(String(32), nullable=False, default="draft", server_default="draft")  # draft, sent, accepted, rejected, expired
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    total = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")  # derived from items on write
    valid_until = Column(Date)
    terms = Column(Text)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))  # set on conversion
    accepted_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client")
    lead = relationship("Lead")
    project = relationship("Project")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan", order_by="QuoteItem.position")


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1, server_default="1")
    unit_price = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    position = Column(Integer, nullable=False, default=0, server_default="0")

    quote = relationship("Quote", back_populates="items")
