"""case studies: optional live product URL

Revision ID: 036
Revises: 035
Create Date: 2026-09-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_studies", sa.Column("live_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("case_studies", "live_url")
