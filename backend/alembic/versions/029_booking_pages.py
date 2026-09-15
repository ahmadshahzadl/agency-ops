"""native booking: booking pages + meeting manage tokens

Revision ID: 029
Revises: 028
Create Date: 2026-09-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("buffer_before_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("buffer_after_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("min_notice_minutes", sa.Integer(), nullable=False, server_default="240"),
        sa.Column("max_days_ahead", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("hours", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("location_text", sa.String(length=255), nullable=True),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["host_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_booking_pages_slug", "booking_pages", ["slug"], unique=True)

    op.add_column("meetings", sa.Column("booking_page_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("meetings", sa.Column("manage_token", sa.String(length=64), nullable=True))
    op.add_column("meetings", sa.Column("invitee_timezone", sa.String(length=64), nullable=True))
    op.add_column("meetings", sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("meetings", sa.Column("ics_sequence", sa.Integer(), nullable=False, server_default="0"))
    op.create_foreign_key("fk_meetings_booking_page", "meetings", "booking_pages", ["booking_page_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_meetings_manage_token", "meetings", ["manage_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_meetings_manage_token", table_name="meetings")
    op.drop_constraint("fk_meetings_booking_page", "meetings", type_="foreignkey")
    for col in ("ics_sequence", "answers", "invitee_timezone", "manage_token", "booking_page_id"):
        op.drop_column("meetings", col)
    op.drop_index("ix_booking_pages_slug", table_name="booking_pages")
    op.drop_table("booking_pages")
