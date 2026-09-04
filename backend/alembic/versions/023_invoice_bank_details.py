"""invoice bank/payment details

Revision ID: 023
Revises: 022
Create Date: 2026-09-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("bank_name", sa.String(length=128), nullable=True))
    op.add_column("invoices", sa.Column("account_title", sa.String(length=128), nullable=True))
    op.add_column("invoices", sa.Column("account_number", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "account_number")
    op.drop_column("invoices", "account_title")
    op.drop_column("invoices", "bank_name")
