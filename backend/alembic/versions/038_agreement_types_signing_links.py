"""agreement types + templates, public signing links, countersignature; client status (prospect/active)

Revision ID: 038
Revises: 037
Create Date: 2026-10-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "038"
down_revision: Union[str, None] = "037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agreements", sa.Column("agreement_type", sa.String(length=32), nullable=False, server_default="service"))
    op.add_column("agreements", sa.Column("sign_token", sa.String(length=64), nullable=True))
    op.add_column("agreements", sa.Column("sign_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agreements", sa.Column("signer_email", sa.String(length=255), nullable=True))
    op.add_column("agreements", sa.Column("signer_title", sa.String(length=128), nullable=True))
    op.add_column("agreements", sa.Column("accepted_user_agent", sa.String(length=255), nullable=True))
    op.add_column("agreements", sa.Column("acceptance_hash", sa.String(length=64), nullable=True))
    op.add_column("agreements", sa.Column("countersigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("agreements", sa.Column("countersigned_by_name", sa.String(length=255), nullable=True))
    op.add_column("agreements", sa.Column("countersigned_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agreements_sign_token", "agreements", ["sign_token"], unique=True)
    op.create_index("ix_agreements_client_type", "agreements", ["client_id", "agreement_type"])

    op.add_column("clients", sa.Column("status", sa.String(length=16), nullable=False, server_default="active"))


def downgrade() -> None:
    op.drop_column("clients", "status")
    op.drop_index("ix_agreements_client_type", table_name="agreements")
    op.drop_index("ix_agreements_sign_token", table_name="agreements")
    for col in ("countersigned_at", "countersigned_by_name", "countersigned_by", "acceptance_hash", "accepted_user_agent", "signer_title", "signer_email", "sign_token_expires_at", "sign_token", "agreement_type"):
        op.drop_column("agreements", col)
