"""invoice line items + fx conversion display

Revision ID: 022
Revises: 021
Create Date: 2026-09-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_items_invoice", "invoice_items", ["invoice_id"], unique=False)

    op.add_column("invoices", sa.Column("fx_currency", sa.String(length=3), nullable=True))
    op.add_column("invoices", sa.Column("fx_rate", sa.Numeric(14, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "fx_rate")
    op.drop_column("invoices", "fx_currency")
    op.drop_index("ix_invoice_items_invoice", table_name="invoice_items")
    op.drop_table("invoice_items")
