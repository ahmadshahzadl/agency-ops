"""OAuth for the Claude connector (remote MCP).

OAuthClient: an app that registered itself (RFC 7591 dynamic registration), e.g. Claude.
OAuthGrant:  one user's approval of one client. Holds the short-lived authorization code while
             the login is in flight, then the (hashed, rotating) refresh token. Revoking the grant,
             or bumping the user's token_version (logout everywhere / password change), cuts the
             connector off on its next request.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(String(255), primary_key=True)  # client_id
    client_name = Column(String(255))
    redirect_uris = Column(Text, nullable=False)  # newline-separated
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class OAuthGrant(Base):
    __tablename__ = "oauth_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(String(255), nullable=False)
    client_name = Column(String(255))
    scope = Column(String(255))
    redirect_uri = Column(Text, nullable=False)
    token_version = Column(Integer, nullable=False, default=0)  # user's token_version at approval

    # Authorization code (single use, minutes-long); cleared when exchanged
    code_hash = Column(String(64), unique=True)
    code_challenge = Column(String(128))
    code_expires_at = Column(DateTime(timezone=True))

    # Refresh token (sha256 of the raw value; rotated on every use)
    refresh_token_hash = Column(String(64), unique=True)
    refresh_expires_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_used_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))

    user = relationship("User")
