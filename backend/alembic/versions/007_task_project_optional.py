"""task project_id optional (nullable)

Revision ID: 007
Revises: 006
Create Date: 2025-03-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tasks",
        "project_id",
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tasks",
        "project_id",
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=False,
    )
