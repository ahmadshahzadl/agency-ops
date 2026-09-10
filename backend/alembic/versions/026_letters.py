"""letters (letterhead documents)

Revision ID: 026
Revises: 025
Create Date: 2026-09-10

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("letter_type", sa.String(length=32), server_default="general", nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("recipient_address", sa.Text(), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("letter_date", sa.Date(), nullable=True),
        sa.Column("signatory_name", sa.String(length=255), nullable=True),
        sa.Column("signatory_title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_letters_number"),
    )
    op.create_index("ix_letters_client", "letters", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_letters_client", table_name="letters")
    op.drop_table("letters")
