"""projects.budget (carried from accepted quotes)

Revision ID: 019
Revises: 018
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("budget", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "budget")
