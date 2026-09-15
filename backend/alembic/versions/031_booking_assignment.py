"""booking assignment: meetings.assigned_to, bookings:manage permission, solutions_engineer role

Revision ID: 031
Revises: 030
Create Date: 2026-09-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SE_ROLE = "solutions_engineer"
SE_PERMS = (
    "dashboard:read",
    "leads:read", "leads:write",
    "clients:read",
    "projects:read",
    "tasks:read",
    "meetings:read", "meetings:write",
    "bookings:manage",
    "notes:read", "notes:write",
    "attachments:read", "attachments:write",
    "time:read", "time:write",
    "quotes:read",
    "announcements:read",
)


def upgrade() -> None:
    op.add_column("meetings", sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_meetings_assigned_to", "meetings", "users", ["assigned_to"], ["id"], ondelete="SET NULL")
    op.create_index("ix_meetings_assigned_to", "meetings", ["assigned_to"], unique=False)

    op.execute(
        "INSERT INTO permissions (id, code, description) "
        "SELECT gen_random_uuid(), 'bookings:manage', "
        "'See every website/Calendly booking and lead, and assign them to a solutions engineer' "
        "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'bookings:manage')"
    )
    op.execute(
        "INSERT INTO roles (id, name, description, created_at) "
        f"SELECT gen_random_uuid(), '{SE_ROLE}', "
        "'Solutions engineer: sees and claims website bookings and leads, manages the prospects assigned to them', now() "
        f"WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = '{SE_ROLE}')"
    )
    codes = ", ".join(f"'{c}'" for c in SE_PERMS)
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        f"WHERE r.name = '{SE_ROLE}' AND p.code IN ({codes}) "
        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
    )


def downgrade() -> None:
    op.drop_index("ix_meetings_assigned_to", table_name="meetings")
    op.drop_constraint("fk_meetings_assigned_to", "meetings", type_="foreignkey")
    op.drop_column("meetings", "assigned_to")
    op.execute(f"DELETE FROM roles WHERE name = '{SE_ROLE}'")
    op.execute("DELETE FROM permissions WHERE code = 'bookings:manage'")
