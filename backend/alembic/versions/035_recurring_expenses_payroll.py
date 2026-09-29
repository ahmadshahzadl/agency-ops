"""recurring expenses (bills, subscriptions, salaries) with reminders; employment fields on users

Revision ID: 035
Revises: 034
Create Date: 2026-09-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recurring_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PKR"),
        sa.Column("frequency", sa.String(length=16), nullable=False, server_default="monthly"),
        sa.Column("due_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("last_paid_on", sa.Date(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payee_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remind_days_before", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[2, 1, 0]"),
        sa.Column("reminders_sent", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recurring_expenses_next_due", "recurring_expenses", ["next_due_date"])
    op.create_index("ix_recurring_expenses_payee", "recurring_expenses", ["payee_user_id"])

    op.add_column("expenses", sa.Column("recurring_expense_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recurring_expenses.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_expenses_recurring", "expenses", ["recurring_expense_id"])

    op.add_column("users", sa.Column("employment_type", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("joined_on", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("left_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "left_on")
    op.drop_column("users", "joined_on")
    op.drop_column("users", "employment_type")
    op.drop_index("ix_expenses_recurring", table_name="expenses")
    op.drop_column("expenses", "recurring_expense_id")
    op.drop_index("ix_recurring_expenses_payee", table_name="recurring_expenses")
    op.drop_index("ix_recurring_expenses_next_due", table_name="recurring_expenses")
    op.drop_table("recurring_expenses")
