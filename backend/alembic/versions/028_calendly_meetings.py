"""meetings: external booking source (Calendly)

Revision ID: 028
Revises: 027
Create Date: 2026-09-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"))
    op.add_column("meetings", sa.Column("external_id", sa.String(length=512), nullable=True))
    op.add_column("meetings", sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"))
    op.add_column("meetings", sa.Column("invitee_name", sa.String(length=255), nullable=True))
    op.add_column("meetings", sa.Column("invitee_email", sa.String(length=255), nullable=True))
    op.add_column("meetings", sa.Column("cancel_reason", sa.Text(), nullable=True))
    op.add_column("meetings", sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_meetings_lead", "meetings", "leads", ["lead_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_meetings_external_id", "meetings", ["external_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_meetings_external_id", table_name="meetings")
    op.drop_constraint("fk_meetings_lead", "meetings", type_="foreignkey")
    for col in ("lead_id", "cancel_reason", "invitee_email", "invitee_name", "status", "external_id", "source"):
        op.drop_column("meetings", col)
