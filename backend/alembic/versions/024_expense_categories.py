"""expense categories + commission links

Revision ID: 024
Revises: 023
Create Date: 2026-09-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("category", sa.String(length=32), server_default="other", nullable=False))
    op.add_column("expenses", sa.Column("related_invoice_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("expenses", sa.Column("payee_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("expenses", sa.Column("commission_percent", sa.Numeric(5, 2), nullable=True))
    op.create_foreign_key("fk_expenses_invoice", "expenses", "invoices", ["related_invoice_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_expenses_payee", "expenses", "users", ["payee_user_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_expenses_payee", "expenses", type_="foreignkey")
    op.drop_constraint("fk_expenses_invoice", "expenses", type_="foreignkey")
    op.drop_column("expenses", "commission_percent")
    op.drop_column("expenses", "payee_user_id")
    op.drop_column("expenses", "related_invoice_id")
    op.drop_column("expenses", "category")
