"""time entries + project hourly rate

Revision ID: 016
Revises: 015
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True))

    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(6, 2), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("billable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_time_entries_user", "time_entries", ["user_id"], unique=False)
    op.create_index("ix_time_entries_project", "time_entries", ["project_id"], unique=False)
    op.create_index("ix_time_entries_invoice", "time_entries", ["invoice_id"], unique=False)
    op.create_index("ix_time_entries_date", "time_entries", ["work_date"], unique=False)


def downgrade() -> None:
    for ix in ("ix_time_entries_date", "ix_time_entries_invoice", "ix_time_entries_project", "ix_time_entries_user"):
        op.drop_index(ix, table_name="time_entries")
    op.drop_table("time_entries")
    op.drop_column("projects", "hourly_rate")
