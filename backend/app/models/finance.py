import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    # Set when this expense was recorded as one occurrence of a recurring bill or salary
    recurring_expense_id = Column(UUID(as_uuid=True), ForeignKey("recurring_expenses.id", ondelete="SET NULL"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    project = relationship("Project", backref="expenses")
    payee = relationship("User", foreign_keys=[payee_user_id])
    related_invoice = relationship("Invoice", foreign_keys=[related_invoice_id])
    recurring = relationship("RecurringExpense", back_populates="occurrences", foreign_keys=[recurring_expense_id])


RECURRING_FREQUENCIES = ("weekly", "monthly", "quarterly", "yearly")


class RecurringExpense(Base):
    """A bill that comes back on a schedule: rent, a subscription, a salary. Each time it is paid an
    ordinary Expense row is written and next_due_date moves forward one period. The reminder loop
    notifies finance users a few days ahead (remind_days_before) and once when it goes overdue."""
    __tablename__ = "recurring_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(String(255), nullable=False)
    category = Column(String(32), nullable=False, default="other", server_default="other")
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="PKR")
    frequency = Column(String(16), nullable=False, default="monthly", server_default="monthly")
    # Day of month the bill falls due (clamped to shorter months). Weekly bills ignore it.
    due_day = Column(Integer, nullable=False, default=1, server_default="1")
    next_due_date = Column(Date, nullable=False)
    last_paid_on = Column(Date)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    payee_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))  # salaries
    notes = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    remind_days_before = Column(JSONB, nullable=False, default=lambda: [2, 1, 0])
    reminders_sent = Column(JSONB, nullable=False, default=list)  # ["2026-10-01:2", "2026-10-01:overdue"]
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
    payee = relationship("User", foreign_keys=[payee_user_id])
    occurrences = relationship("Expense", back_populates="recurring", foreign_keys="Expense.recurring_expense_id")
