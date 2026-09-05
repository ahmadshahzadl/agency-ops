import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    number = Column(String(64), unique=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(32), default="draft")  # draft, sent, paid, overdue
    due_date = Column(Date)
    issued_at = Column(Date)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="SET NULL"))  # set when generated from a quote
    # Optional display conversion (e.g. USD invoice shown with PKR equivalent at a manual rate)
    fx_currency = Column(String(3))
    fx_rate = Column(Numeric(14, 6))
    # Where the client should pay (printed on the PDF)
    bank_name = Column(String(128))
    account_title = Column(String(128))
    account_number = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", backref="invoices")
    project = relationship("Project", backref="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.position")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1, server_default="1")
    unit_price = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    position = Column(Integer, nullable=False, default=0, server_default="0")

    invoice = relationship("Invoice", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    paid_at = Column(Date, nullable=False)
    reference = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    description = Column(String(255), nullable=False)
    category = Column(String(32), nullable=False, default="other", server_default="other")  # office, commission, salary, software, travel, other
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="PKR")
    expense_date = Column(Date)
    # Commission expenses: % of an invoice paid to whoever brought/did BD for the project
    related_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"))
    payee_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    commission_percent = Column(Numeric(5, 2))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    project = relationship("Project", backref="expenses")
    payee = relationship("User", foreign_keys=[payee_user_id])
    related_invoice = relationship("Invoice", foreign_keys=[related_invoice_id])
