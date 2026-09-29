"""employee attendance records; attendance:manage permission for admins

Revision ID: 037
Revises: 036
Create Date: 2026-09-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "037"
down_revision: Union[str, None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="present"),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("location_accuracy_m", sa.Numeric(10, 1), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "work_date", name="uq_attendance_user_day"),
    )
    op.create_index("ix_attendance_records_user_id", "attendance_records", ["user_id"])
    op.create_index("ix_attendance_records_work_date", "attendance_records", ["work_date"])

    op.execute(
        "INSERT INTO permissions (id, code, description) "
        "SELECT gen_random_uuid(), 'attendance:manage', 'See and correct everyone''s attendance' "
        "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'attendance:manage')"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'admin' AND p.code = 'attendance:manage' "
        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM permissions WHERE code = 'attendance:manage'")
    op.drop_index("ix_attendance_records_work_date", table_name="attendance_records")
    op.drop_index("ix_attendance_records_user_id", table_name="attendance_records")
    op.drop_table("attendance_records")
