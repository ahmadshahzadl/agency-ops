"""saved signature image per user, placed on agreements and letters

Revision ID: 039
Revises: 038
Create Date: 2026-10-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "039"
down_revision: Union[str, None] = "038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("signature_file", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "signature_file")
