"""users.phone and users.job_title (contact info)

Revision ID: 008
Revises: 007
Create Date: 2025-03-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "job_title")
    op.drop_column("users", "phone")
