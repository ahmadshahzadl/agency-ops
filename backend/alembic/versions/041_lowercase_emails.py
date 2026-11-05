"""normalise user emails to lower case and enforce it

Sign-in used to be case-sensitive: the account was stored with whatever casing the
admin typed when creating the user, and login matched it exactly. This lower-cases
every existing address and adds a unique index on lower(email) so two accounts can
never differ by case alone.

Revision ID: 041
Revises: 040
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "041"
down_revision: Union[str, None] = "040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Refuse to merge two real accounts that differ only by case - a human has to
    # decide which one survives. Nothing is changed when this raises.
    clashes = conn.execute(
        sa.text(
            "SELECT lower(trim(email)) AS norm, count(*) AS n, string_agg(email, ', ') AS addresses "
            "FROM users GROUP BY 1 HAVING count(*) > 1"
        )
    ).fetchall()
    if clashes:
        detail = "; ".join(f"{row.norm} <- {row.addresses}" for row in clashes)
        raise RuntimeError(
            "Cannot lower-case user emails: these addresses collide once case is ignored. "
            "Deactivate or delete the duplicates, then re-run the migration. " + detail
        )

    conn.execute(sa.text("UPDATE users SET email = lower(trim(email)) WHERE email <> lower(trim(email))"))
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    # The original casing is not recoverable; only the constraint is reversible.
    op.drop_index("uq_users_email_lower", table_name="users")
