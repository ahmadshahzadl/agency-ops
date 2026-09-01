"""QA workflow fields on tasks + kanban boards

Revision ID: 012
Revises: 011
Create Date: 2026-09-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "boards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boards_project", "boards", ["project_id"], unique=False)

    op.create_table(
        "board_members",
        sa.Column("board_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["boards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("board_id", "user_id"),
    )

    # QA workflow + board placement fields on tasks
    op.add_column("tasks", sa.Column("item_type", sa.String(length=16), server_default="task", nullable=False))
    op.add_column("tasks", sa.Column("severity", sa.String(length=16), nullable=True))
    op.add_column("tasks", sa.Column("steps_to_reproduce", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("environment", sa.String(length=255), nullable=True))
    op.add_column("tasks", sa.Column("qa_notes", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("qa_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("qa_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("board_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("column_order", sa.Integer(), server_default="0", nullable=False))
    op.create_foreign_key("fk_tasks_qa_by_users", "tasks", "users", ["qa_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_tasks_board_id_boards", "tasks", "boards", ["board_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_tasks_board", "tasks", ["board_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_board", table_name="tasks")
    op.drop_constraint("fk_tasks_board_id_boards", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_qa_by_users", "tasks", type_="foreignkey")
    for col in ("column_order", "board_id", "qa_at", "qa_by", "qa_notes", "environment", "steps_to_reproduce", "severity", "item_type"):
        op.drop_column("tasks", col)
    op.drop_table("board_members")
    op.drop_index("ix_boards_project", table_name="boards")
    op.drop_table("boards")
