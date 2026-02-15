"""team_type, Lead model, project pipeline_stage and assigned_team_id

Revision ID: 003
Revises: 002
Create Date: 2025-03-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("team_type", sa.String(64), nullable=True))

    op.add_column("projects", sa.Column("pipeline_stage", sa.String(64), nullable=True))
    op.add_column("projects", sa.Column("assigned_team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE projects SET pipeline_stage = 'lead' WHERE pipeline_stage IS NULL")
    op.alter_column("projects", "pipeline_stage", nullable=False, server_default="lead")
    op.create_foreign_key(
        "fk_projects_assigned_team_id", "projects", "teams", ["assigned_team_id"], ["id"], ondelete="SET NULL"
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(64), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=True, server_default="new"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_to_client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_to_client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("leads")
    op.drop_constraint("fk_projects_assigned_team_id", "projects", type_="foreignkey")
    op.drop_column("projects", "assigned_team_id")
    op.drop_column("projects", "pipeline_stage")
    op.drop_column("teams", "team_type")
