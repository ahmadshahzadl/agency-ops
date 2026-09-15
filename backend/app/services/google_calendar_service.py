"""Google Calendar + Meet for booking hosts.

A host connects their Google account once (OAuth, offline access). From then on:
- free/busy on their primary calendar blocks booking slots (``busy_intervals``),
- each booking becomes a Google Calendar event with a Meet link and the invitee as a guest
  (Google sends/updates the invitation emails), and reschedules/cancels are pushed through.

Every network call is isolated behind ``GoogleError``; callers decide whether to fail open.
"""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.integration import UserIntegration
from app.services.vault_service import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

PROVIDER = "google"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
CAL_API = "https://www.googleapis.com/calendar/v3"
SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]
TIMEOUT = 12.0


class GoogleError(Exception):
    pass


class NotConfigured(GoogleError):
    pass


# ---------------------------------------------------------------------------
# Configuration / OAuth
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def redirect_uri() -> str:
    s = get_settings()
    if s.google_redirect_uri:
        return s.google_redirect_uri
    return f"{s.frontend_url.rstrip('/')}/api/v1/integrations/google/callback"


def make_state(user_id: uuid.UUID) -> str:
    s = get_settings()
    payload = {"sub": str(user_id), "type": "gcal_state", "exp": datetime.now(timezone.utc) + timedelta(minutes=10), "n": uuid.uuid4().hex}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def parse_state(state: str) -> uuid.UUID | None:
    s = get_settings()
    try:
        data = jwt.decode(state, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError:
        return None
    if data.get("type") != "gcal_state" or not data.get("sub"):
        return None
    try:
        return uuid.UUID(data["sub"])
    except ValueError:
        return None


def auth_url(user_id: uuid.UUID) -> str:
    if not is_configured():
        raise NotConfigured("Google integration is not configured")
    s = get_settings()
    params = {
        "client_id": s.google_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # always return a refresh token
        "include_granted_scopes": "true",
        "state": make_state(user_id),
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    try:
        r = httpx.post(url, data=data, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise GoogleError(f"network error: {e}") from e
    if r.status_code >= 400:
        raise GoogleError(f"{url} -> {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def exchange_code(code: str) -> dict[str, Any]:
    """Authorization code -> {access_token, refresh_token, expires_in, email}."""
    s = get_settings()
    tokens = _post_form(
        TOKEN_URL,
        {
            "code": code,
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
    )
    if not tokens.get("refresh_token"):
        raise GoogleError("Google did not return a refresh token; remove the app's access in your Google account and connect again.")
    email = None
    try:
        r = httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {tokens['access_token']}"}, timeout=TIMEOUT)
        if r.status_code < 400:
            email = r.json().get("email")
    except httpx.HTTPError:
        pass
    tokens["email"] = email
    return tokens


def save_connection(db: Session, user_id: uuid.UUID, tokens: dict[str, Any]) -> UserIntegration:
    integ = db.query(UserIntegration).filter(UserIntegration.user_id == user_id, UserIntegration.provider == PROVIDER).first()
    if integ is None:
        integ = UserIntegration(user_id=user_id, provider=PROVIDER, refresh_token_encrypted="")
        db.add(integ)
    integ.refresh_token_encrypted = encrypt_secret(tokens["refresh_token"])
    integ.access_token_encrypted = encrypt_secret(tokens["access_token"]) if tokens.get("access_token") else None
    integ.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 3600)) - 60)
    integ.scopes = tokens.get("scope") or " ".join(SCOPES)
    integ.account_email = tokens.get("email")
    integ.calendar_id = "primary"
    integ.last_error = None
    integ.connected_at = datetime.now(timezone.utc)
    db.flush()
    return integ


def get_integration(db: Session, user_id: uuid.UUID | None) -> UserIntegration | None:
    if not user_id:
        return None
    return db.query(UserIntegration).filter(UserIntegration.user_id == user_id, UserIntegration.provider == PROVIDER).first()


def disconnect(db: Session, integ: UserIntegration) -> None:
    try:
        token = decrypt_secret(integ.refresh_token_encrypted)
        httpx.post(REVOKE_URL, params={"token": token}, timeout=TIMEOUT)
    except Exception:  # revoke is best-effort
        logger.info("google revoke failed for user %s", integ.user_id, exc_info=True)
    db.delete(integ)
    db.flush()


def _access_token(db: Session, integ: UserIntegration) -> str:
    now = datetime.now(timezone.utc)
    if integ.access_token_encrypted and integ.token_expires_at and integ.token_expires_at.astimezone(timezone.utc) > now:
        return decrypt_secret(integ.access_token_encrypted)
    s = get_settings()
    tokens = _post_form(
        TOKEN_URL,
        {
            "refresh_token": decrypt_secret(integ.refresh_token_encrypted),
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "grant_type": "refresh_token",
        },
    )
    integ.access_token_encrypted = encrypt_secret(tokens["access_token"])
    integ.token_expires_at = now + timedelta(seconds=int(tokens.get("expires_in", 3600)) - 60)
    integ.last_error = None
    db.flush()
    return tokens["access_token"]


def _api(db: Session, integ: UserIntegration, method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict[str, Any]:
    token = _access_token(db, integ)
    try:
        r = httpx.request(method, f"{CAL_API}{path}", params=params, json=json, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise GoogleError(f"network error: {e}") from e
    if r.status_code == 401:
        # Access token rejected although not expired: force a refresh once.
        integ.access_token_encrypted = None
        token = _access_token(db, integ)
        r = httpx.request(method, f"{CAL_API}{path}", params=params, json=json, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    if r.status_code == 404 and method == "DELETE":
        return {}
    if r.status_code == 410:
        return {}
    if r.status_code >= 400:
        raise GoogleError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


# ---------------------------------------------------------------------------
# Free/busy (small TTL cache so a slots request per calendar month is one API call)
# ---------------------------------------------------------------------------

_FB_TTL = 15.0  # short: a slot taken on Google in this window could still be offered
_fb_cache: dict[tuple, tuple[float, list[tuple[datetime, datetime]]]] = {}


def invalidate_busy_cache(user_id: uuid.UUID | None = None) -> None:
    if user_id is None:
        _fb_cache.clear()
        return
    for k in [k for k in _fb_cache if k[0] == user_id]:
        _fb_cache.pop(k, None)


def busy_intervals(db: Session, integ: UserIntegration, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    key = (integ.user_id, start.isoformat(), end.isoformat())
    hit = _fb_cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    data = _api(
        db,
        integ,
        "POST",
        "/freeBusy",
        json={
            "timeMin": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "timeMax": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "items": [{"id": integ.calendar_id or "primary"}],
        },
    )
    out: list[tuple[datetime, datetime]] = []
    for cal in (data.get("calendars") or {}).values():
        for b in cal.get("busy") or []:
            try:
                out.append((_parse(b["start"]), _parse(b["end"])))
            except (KeyError, ValueError):
                continue
    _fb_cache[key] = (time.monotonic() + _FB_TTL, out)
    return out


def _parse(v: str) -> datetime:
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Events (Meet link created by Google; Google emails the guests)
# ---------------------------------------------------------------------------

def _event_body(meeting, page, tz_name: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "summary": meeting.title,
        "description": (meeting.description or "") + ("\n\nManage: " + _manage_url(meeting) if _manage_url(meeting) else ""),
        "start": {"dateTime": meeting.start_at.astimezone(timezone.utc).isoformat(), "timeZone": tz_name},
        "end": {"dateTime": meeting.end_at.astimezone(timezone.utc).isoformat(), "timeZone": tz_name},
        "guestsCanModify": False,
        "guestsCanInviteOthers": False,
        "reminders": {"useDefault": False, "overrides": [{"method": "email", "minutes": 60}, {"method": "popup", "minutes": 10}]},
        "extendedProperties": {"private": {"fuorix_meeting_id": str(meeting.id), "fuorix_source": meeting.source or "website"}},
    }
    if meeting.invitee_email:
        body["attendees"] = [{"email": meeting.invitee_email, "displayName": meeting.invitee_name or meeting.invitee_email, "responseStatus": "needsAction"}]
    return body


def _manage_url(meeting) -> str | None:
    base = (get_settings().booking_public_url or "").rstrip("/")
    return f"{base}/book/manage/{meeting.manage_token}" if base and getattr(meeting, "manage_token", None) else None


def create_event(db: Session, integ: UserIntegration, meeting, page) -> tuple[str, str | None]:
    """Create the calendar event with a Meet room. Returns (event_id, meet_link)."""
    body = _event_body(meeting, page, page.timezone if page else "UTC")
    body["conferenceData"] = {"createRequest": {"requestId": uuid.uuid4().hex, "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    ev = _api(
        db,
        integ,
        "POST",
        f"/calendars/{integ.calendar_id or 'primary'}/events",
        params={"conferenceDataVersion": 1, "sendUpdates": "all"},
        json=body,
    )
    invalidate_busy_cache(integ.user_id)
    return ev["id"], _meet_link(ev)


def update_event(db: Session, integ: UserIntegration, meeting, page) -> str | None:
    body = _event_body(meeting, page, page.timezone if page else "UTC")
    ev = _api(
        db,
        integ,
        "PATCH",
        f"/calendars/{integ.calendar_id or 'primary'}/events/{meeting.google_event_id}",
        params={"conferenceDataVersion": 1, "sendUpdates": "all"},
        json={"start": body["start"], "end": body["end"], "description": body["description"], "summary": body["summary"]},
    )
    invalidate_busy_cache(integ.user_id)
    return _meet_link(ev)


def delete_event(db: Session, integ: UserIntegration, meeting) -> None:
    _api(
        db,
        integ,
        "DELETE",
        f"/calendars/{integ.calendar_id or 'primary'}/events/{meeting.google_event_id}",
        params={"sendUpdates": "all"},
    )
    invalidate_busy_cache(integ.user_id)


def _meet_link(ev: dict[str, Any]) -> str | None:
    if ev.get("hangoutLink"):
        return ev["hangoutLink"]
    for ep in ((ev.get("conferenceData") or {}).get("entryPoints") or []):
        if ep.get("entryPointType") == "video" and ep.get("uri"):
            return ep["uri"]
    return None
