"""users.client_id - portal users linked to a client record

Revision ID: 021
Revises: 020
Create Date: 2026-09-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_users_client_id", "users", "clients", ["client_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_users_client", "users", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_client", table_name="users")
    op.drop_constraint("fk_users_client_id", "users", type_="foreignkey")
    op.drop_column("users", "client_id")
