"""milestones + tasks.milestone_id

Revision ID: 020
Revises: 019
Create Date: 2026-09-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_milestones_project", "milestones", ["project_id"], unique=False)

    op.add_column("tasks", sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tasks_milestone_id", "tasks", "milestones", ["milestone_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_tasks_milestone", "tasks", ["milestone_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_milestone", table_name="tasks")
    op.drop_constraint("fk_tasks_milestone_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "milestone_id")
    op.drop_index("ix_milestones_project", table_name="milestones")
    op.drop_table("milestones")
