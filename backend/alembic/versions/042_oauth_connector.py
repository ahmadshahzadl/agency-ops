"""OAuth clients and grants for the Claude connector (remote MCP)

Revision ID: 042
Revises: 041
Create Date: 2026-11-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "042"
down_revision: Union[str, None] = "041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("client_name", sa.String(255)),
        sa.Column("redirect_uris", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "oauth_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_name", sa.String(255)),
        sa.Column("scope", sa.String(255)),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("code_hash", sa.String(64), unique=True),
        sa.Column("code_challenge", sa.String(128)),
        sa.Column("code_expires_at", sa.DateTime(timezone=True)),
        sa.Column("refresh_token_hash", sa.String(64), unique=True),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_oauth_grants_user_id", "oauth_grants", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_oauth_grants_user_id", table_name="oauth_grants")
    op.drop_table("oauth_grants")
    op.drop_table("oauth_clients")
