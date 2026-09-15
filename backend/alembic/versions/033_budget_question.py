"""add a required budget question to every booking page that lacks one

Revision ID: 033
Revises: 032
Create Date: 2026-09-15

"""
import json
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUDGET_QUESTION = {
    "id": "budget",
    "label": "Estimated budget",
    "type": "select",
    "required": True,
    "options": ["Less than $500", "$500 – $2,000", "$2,000 – $5,000", "$5,000 – $10,000", "$10,000+", "Not sure yet"],
}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, questions FROM booking_pages")).fetchall()
    for page_id, questions in rows:
        qs = questions if isinstance(questions, list) else json.loads(questions or "[]")
        if any((q or {}).get("id") == "budget" for q in qs):
            continue
        qs.append(BUDGET_QUESTION)
        conn.execute(
            sa.text("UPDATE booking_pages SET questions = CAST(:q AS jsonb) WHERE id = :id"),
            {"q": json.dumps(qs), "id": page_id},
        )


def downgrade() -> None:
    # Leave the question in place; it is plain page data the admin can remove in the UI.
    pass
