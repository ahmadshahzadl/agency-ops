"""invoices.quote_id for quote-billing dedup

Revision ID: 018
Revises: 017
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_invoices_quote_id_quotes", "invoices", "quotes", ["quote_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_invoices_quote", "invoices", ["quote_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invoices_quote", table_name="invoices")
    op.drop_constraint("fk_invoices_quote_id_quotes", "invoices", type_="foreignkey")
    op.drop_column("invoices", "quote_id")
