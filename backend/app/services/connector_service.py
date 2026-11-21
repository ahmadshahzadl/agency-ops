"""Claude connector (remote MCP): who may connect, token issuing, and request checks."""
import base64
import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import UUID

from jose import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.models.oauth import OAuthGrant

SCOPE = "fuorix"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def public_url() -> str:
    s = get_settings()
    return (s.mcp_public_url or s.frontend_url).rstrip("/")


def allowed_redirect_uris() -> set[str]:
    return {u.strip() for u in get_settings().mcp_redirect_uris.split(",") if u.strip()}


def allowed_emails() -> set[str]:
    return {e.strip().lower() for e in get_settings().mcp_allowed_emails.split(",") if e.strip()}


def ineligible_reason(user: User | None) -> str | None:
    """None when this account may use the connector, else a human-readable reason."""
    s = get_settings()
    if not s.mcp_enabled:
        return "The Claude connector is turned off on this server."
    if user is None or not user.is_active:
        return "This account is inactive."
    if user.client_id is not None:
        return "Client portal accounts cannot connect Claude."
    allow = allowed_emails()
    if allow and (user.email or "").strip().lower() not in allow:
        return "This account is not allowed to connect Claude yet. Ask an admin to add it to MCP_ALLOWED_EMAILS."
    return None


def pkce_matches(code_verifier: str, code_challenge: str) -> bool:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(expected, code_challenge or "")


def create_access_token(user: User, grant: OAuthGrant) -> tuple[str, int]:
    """Short-lived JWT the connector forwards to the API. `via: mcp` puts it on the allowlist."""
    s = get_settings()
    seconds = s.mcp_access_token_minutes * 60
    claims = {
        "sub": str(user.id),
        "type": "access",
        "via": "mcp",
        "gid": str(grant.id),
        "tv": user.token_version or 0,
        "exp": datetime.utcnow() + timedelta(seconds=seconds),
    }
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm), seconds


def issue_tokens(db: Session, user: User, grant: OAuthGrant) -> dict:
    """Access token plus a fresh refresh token (the previous one, if any, stops working)."""
    access, expires_in = create_access_token(user, grant)
    refresh = secrets.token_urlsafe(48)
    grant.refresh_token_hash = sha256_hex(refresh)
    grant.refresh_expires_at = _now() + timedelta(days=get_settings().mcp_refresh_token_days)
    grant.last_used_at = _now()
    db.commit()
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": refresh,
        "scope": grant.scope or SCOPE,
    }


class _SlidingWindow:
    """Per-key request cap. In-process, like the login limiter (the API runs one worker)."""

    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] < now - window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


connector_limiter = _SlidingWindow()


def check_connector_request(db: Session, payload: dict, user: User) -> str | None:
    """Validate a connector token beyond its signature. None = ok, else the refusal reason."""
    reason = ineligible_reason(user)
    if reason:
        return reason
    try:
        grant_id = UUID(payload.get("gid") or "")
    except ValueError:
        return "Invalid connector token"
    grant = db.query(OAuthGrant).filter(OAuthGrant.id == grant_id).first()
    if not grant or grant.revoked_at is not None or grant.user_id != user.id:
        return "This Claude connection was revoked. Reconnect it from Claude."
    if (grant.token_version or 0) != (user.token_version or 0):
        return "Signed out everywhere: reconnect Claude."
    if not connector_limiter.hit(str(grant.id), get_settings().mcp_requests_per_minute):
        return "RATE_LIMIT"
    now = _now()
    if grant.last_used_at is None or now - grant.last_used_at > timedelta(minutes=1):
        grant.last_used_at = now
        db.commit()
    return None
