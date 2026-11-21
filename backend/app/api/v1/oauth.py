"""OAuth 2.1 authorization server for the Claude connector (remote MCP).

Flow (authorization code + PKCE, public client):
  1. Claude registers itself:            POST /api/v1/oauth/register        (RFC 7591)
  2. Claude sends the user to:           GET  /api/v1/oauth/authorize       -> 302 to <frontend>/oauth/consent
  3. The signed-in user approves there:  POST /api/v1/oauth/authorize/approve (web session token)
  4. Claude exchanges the code:          POST /api/v1/oauth/token           (authorization_code / refresh_token)

Discovery: GET /.well-known/oauth-authorization-server (mounted in main.py).
The issued access token is a normal API JWT plus `via: mcp`, so it is held to the allowlist in
app/core/mcp_policy.py. Revoke from Settings -> Connected apps, or by signing out everywhere.
"""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.models.oauth import OAuthClient, OAuthGrant
from app.services import connector_service as cs
from app.services.activity_service import log_activity

router = APIRouter(prefix="/oauth", tags=["oauth"])

CODE_TTL = timedelta(minutes=5)
TRUSTED_CLIENT_ID_HOSTS = {"claude.ai", "claude.com"}  # client-ID metadata documents (CIMD)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enabled() -> None:
    if not get_settings().mcp_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _oauth_error(error: str, description: str, code: int = 400) -> JSONResponse:
    return JSONResponse({"error": error, "error_description": description}, status_code=code,
                        headers={"Cache-Control": "no-store"})


def authorization_server_metadata() -> dict:
    base = cs.public_url()
    api = f"{base}/api/v1/oauth"
    return {
        "issuer": base,
        "authorization_endpoint": f"{api}/authorize",
        "token_endpoint": f"{api}/token",
        "registration_endpoint": f"{api}/register",
        "revocation_endpoint": f"{api}/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": [cs.SCOPE],
        "client_id_metadata_document_supported": True,
    }


def _resolve_client(db: Session, client_id: str) -> tuple[str, list[str]] | None:
    """(display name, allowed redirect URIs) for a registered or trusted-URL client."""
    if not client_id:
        return None
    row = db.query(OAuthClient).filter(OAuthClient.id == client_id).first()
    if row:
        return row.client_name or "Claude", [u for u in row.redirect_uris.split("\n") if u]
    parsed = urlparse(client_id)
    if parsed.scheme == "https" and parsed.hostname in TRUSTED_CLIENT_ID_HOSTS:
        return "Claude", sorted(cs.allowed_redirect_uris())
    return None


def _validated_request(db: Session, client_id: str, redirect_uri: str) -> str:
    """Return the client name, or raise (never redirect to an unverified URI)."""
    client = _resolve_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=400, detail="Unknown client_id")
    name, uris = client
    if redirect_uri not in uris or redirect_uri not in cs.allowed_redirect_uris():
        raise HTTPException(status_code=400, detail="redirect_uri is not allowed")
    return name


def _redirect_with(redirect_uri: str, params: dict) -> str:
    sep = "&" if "?" in redirect_uri else "?"
    return f"{redirect_uri}{sep}{urlencode({k: v for k, v in params.items() if v is not None})}"


# ---------- 1. registration ----------

@router.post("/register", status_code=201)
async def register(request: Request, db: Session = Depends(get_db)):
    _enabled()
    try:
        body = await request.json()
    except Exception:
        return _oauth_error("invalid_client_metadata", "Body must be JSON")
    uris = body.get("redirect_uris") or []
    if not isinstance(uris, list) or not uris:
        return _oauth_error("invalid_redirect_uri", "redirect_uris is required")
    allowed = cs.allowed_redirect_uris()
    bad = [u for u in uris if u not in allowed]
    if bad:
        return _oauth_error("invalid_redirect_uri", f"redirect_uri not allowed: {bad[0]}")
    name = str(body.get("client_name") or "Claude")[:255]
    client = OAuthClient(id=secrets.token_urlsafe(24), client_name=name, redirect_uris="\n".join(uris))
    db.add(client)
    db.commit()
    return {
        "client_id": client.id,
        "client_id_issued_at": int(_now().timestamp()),
        "client_name": name,
        "redirect_uris": uris,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": cs.SCOPE,
    }


# ---------- 2. authorize -> consent page ----------

@router.get("/authorize")
def authorize(
    request: Request,
    db: Session = Depends(get_db),
    client_id: str = "",
    redirect_uri: str = "",
    response_type: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "",
    state: str | None = None,
):
    _enabled()
    _validated_request(db, client_id, redirect_uri)  # raises 400; never redirects to an unknown URI
    if response_type != "code":
        return RedirectResponse(_redirect_with(redirect_uri, {"error": "unsupported_response_type", "state": state}), 302)
    if not code_challenge or code_challenge_method != "S256":
        return RedirectResponse(_redirect_with(redirect_uri, {"error": "invalid_request", "error_description": "PKCE S256 is required", "state": state}), 302)
    frontend = get_settings().frontend_url.rstrip("/")
    return RedirectResponse(f"{frontend}/oauth/consent?{urlencode(dict(request.query_params))}", 302)


class ConsentRequest(BaseModel):
    client_id: str
    redirect_uri: str
    code_challenge: str = ""
    code_challenge_method: str = ""
    state: str | None = None
    scope: str | None = None
    approve: bool = False


@router.get("/authorize/info")
def authorize_info(
    client_id: str,
    redirect_uri: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """What the consent page shows: who is asking, and whether this account may connect."""
    _enabled()
    name = _validated_request(db, client_id, redirect_uri)
    return {"client_name": name, "account": user.email, "blocked_reason": cs.ineligible_reason(user)}


@router.post("/authorize/approve")
def authorize_approve(
    data: ConsentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Called by the consent page with the user's normal web session (connector tokens can't reach it)."""
    _enabled()
    name = _validated_request(db, data.client_id, data.redirect_uri)
    if not data.approve:
        return {"redirect_to": _redirect_with(data.redirect_uri, {"error": "access_denied", "state": data.state})}
    reason = cs.ineligible_reason(user)
    if reason:
        raise HTTPException(status_code=403, detail=reason)
    if not data.code_challenge or data.code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="PKCE S256 is required")
    code = secrets.token_urlsafe(32)
    grant = OAuthGrant(
        user_id=user.id,
        client_id=data.client_id,
        client_name=name,
        scope=cs.SCOPE,
        redirect_uri=data.redirect_uri,
        token_version=user.token_version or 0,
        code_hash=cs.sha256_hex(code),
        code_challenge=data.code_challenge,
        code_expires_at=_now() + CODE_TTL,
    )
    db.add(grant)
    db.flush()
    log_activity(db, user.id, "connector_authorized", "user", user.id, details=f"Connected {name} (MCP)")
    db.commit()
    return {"redirect_to": _redirect_with(data.redirect_uri, {"code": code, "state": data.state})}


# ---------- 3. token ----------

@router.post("/token")
def token(
    db: Session = Depends(get_db),
    grant_type: str = Form(""),
    code: str = Form(""),
    redirect_uri: str = Form(""),
    client_id: str = Form(""),
    code_verifier: str = Form(""),
    refresh_token: str = Form(""),
):
    _enabled()
    if grant_type == "authorization_code":
        grant = db.query(OAuthGrant).filter(OAuthGrant.code_hash == cs.sha256_hex(code)).first() if code else None
        if not grant or grant.revoked_at is not None or not grant.code_expires_at or grant.code_expires_at < _now():
            return _oauth_error("invalid_grant", "Authorization code is invalid or expired")
        if grant.client_id != client_id or grant.redirect_uri != redirect_uri:
            return _oauth_error("invalid_grant", "client_id or redirect_uri mismatch")
        if not code_verifier or not cs.pkce_matches(code_verifier, grant.code_challenge):
            return _oauth_error("invalid_grant", "PKCE verification failed")
        grant.code_hash = None  # single use
        grant.code_expires_at = None
        # One active Claude connection per user: reconnecting replaces the previous one.
        (db.query(OAuthGrant)
         .filter(OAuthGrant.user_id == grant.user_id, OAuthGrant.id != grant.id,
                 OAuthGrant.redirect_uri == grant.redirect_uri, OAuthGrant.revoked_at.is_(None))
         .update({OAuthGrant.revoked_at: _now()}, synchronize_session=False))
    elif grant_type == "refresh_token":
        grant = db.query(OAuthGrant).filter(OAuthGrant.refresh_token_hash == cs.sha256_hex(refresh_token)).first() if refresh_token else None
        if not grant or grant.revoked_at is not None or not grant.refresh_expires_at or grant.refresh_expires_at < _now():
            return _oauth_error("invalid_grant", "Refresh token is invalid, expired or revoked")
        if client_id and grant.client_id != client_id:
            return _oauth_error("invalid_grant", "client_id mismatch")
    else:
        return _oauth_error("unsupported_grant_type", "Use authorization_code or refresh_token")

    user = db.query(User).filter(User.id == grant.user_id).first()
    reason = cs.ineligible_reason(user)
    if reason or (grant.token_version or 0) != (user.token_version or 0):
        grant.revoked_at = grant.revoked_at or _now()
        db.commit()
        return _oauth_error("invalid_grant", reason or "Signed out everywhere: reconnect Claude")
    body = cs.issue_tokens(db, user, grant)
    return JSONResponse(body, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.post("/revoke")
def revoke(db: Session = Depends(get_db), token: str = Form("")):
    """RFC 7009: revoke by refresh token. Always 200."""
    _enabled()
    grant = db.query(OAuthGrant).filter(OAuthGrant.refresh_token_hash == cs.sha256_hex(token)).first() if token else None
    if grant and grant.revoked_at is None:
        grant.revoked_at = _now()
        db.commit()
    return {}


# ---------- used by the MCP server ----------

@router.get("/connector/whoami")
def connector_whoami(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    """Identity behind a connector token. Refuses normal web tokens, so the MCP server can tell
    a real connector login from someone pasting a browser session token."""
    if db.info.get("via") != "mcp":
        raise HTTPException(status_code=403, detail="Connector tokens only")
    from app.api.v1.auth import _user_response
    me = _user_response(user)
    return {"id": str(me.id), "email": me.email, "full_name": me.full_name, "roles": me.roles, "permissions": me.permissions}


# ---------- Settings -> Connected apps ----------

@router.get("/grants")
def list_my_grants(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    rows = (
        db.query(OAuthGrant)
        .filter(OAuthGrant.user_id == user.id, OAuthGrant.revoked_at.is_(None), OAuthGrant.refresh_token_hash.isnot(None))
        .order_by(OAuthGrant.created_at.desc())
        .all()
    )
    return {
        "enabled": get_settings().mcp_enabled,
        "mcp_url": f"{cs.public_url()}/mcp",
        "can_connect": cs.ineligible_reason(user) is None,
        "grants": [
            {"id": str(g.id), "client_name": g.client_name or "Claude", "created_at": g.created_at, "last_used_at": g.last_used_at}
            for g in rows
        ],
    }


@router.post("/grants/{grant_id}/revoke", status_code=204)
def revoke_my_grant(grant_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    grant = db.query(OAuthGrant).filter(OAuthGrant.id == grant_id, OAuthGrant.user_id == user.id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Not found")
    if grant.revoked_at is None:
        grant.revoked_at = _now()
        log_activity(db, user.id, "connector_revoked", "user", user.id, details=f"Disconnected {grant.client_name or 'Claude'} (MCP)")
        db.commit()
