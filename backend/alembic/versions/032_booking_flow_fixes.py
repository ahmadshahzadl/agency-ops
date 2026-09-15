"""booking flow: host on meeting, reminders, tracking, outcome notes, co-hosts, date overrides

Revision ID: 032
Revises: 031
Create Date: 2026-09-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_meetings_host_user", "meetings", "users", ["host_user_id"], ["id"], ondelete="SET NULL")
    op.add_column("meetings", sa.Column("reminder_24h_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("meetings", sa.Column("reminder_1h_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("meetings", sa.Column("tracking", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("meetings", sa.Column("outcome_note", sa.Text(), nullable=True))
    op.create_index("ix_meetings_reminders", "meetings", ["status", "start_at"], unique=False)

    op.add_column("booking_pages", sa.Column("co_host_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"))
    op.add_column("booking_pages", sa.Column("overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"))

    # Backfill host on existing website bookings from the page's host.
    op.execute(
        "UPDATE meetings m SET host_user_id = p.host_user_id FROM booking_pages p "
        "WHERE m.booking_page_id = p.id AND m.host_user_id IS NULL"
    )


def downgrade() -> None:
    op.drop_column("booking_pages", "overrides")
    op.drop_column("booking_pages", "co_host_ids")
    op.drop_index("ix_meetings_reminders", table_name="meetings")
    for col in ("outcome_note", "tracking", "reminder_1h_sent_at", "reminder_24h_sent_at"):
        op.drop_column("meetings", col)
    op.drop_constraint("fk_meetings_host_user", "meetings", type_="foreignkey")
    op.drop_column("meetings", "host_user_id")
