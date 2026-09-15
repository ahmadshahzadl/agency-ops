"""Per-user third-party connections. Google Calendar today."""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.config import get_settings
from app.database import get_db
from app.services import google_calendar_service as gcal
from app.services.activity_service import log_activity

router = APIRouter(prefix="/integrations", tags=["integrations"])


class GoogleStatus(BaseModel):
    configured: bool
    connected: bool
    account_email: str | None = None
    connected_at: str | None = None
    last_error: str | None = None


class ConnectResponse(BaseModel):
    url: str


def _profile_redirect(**params: str) -> RedirectResponse:
    base = get_settings().frontend_url.rstrip("/")
    return RedirectResponse(f"{base}/profile?{urlencode(params)}", status_code=302)


@router.get("/google/status", response_model=GoogleStatus)
def google_status(db: Session = Depends(get_db), user=Depends(require_staff)):
    integ = gcal.get_integration(db, user.id)
    return GoogleStatus(
        configured=gcal.is_configured(),
        connected=integ is not None,
        account_email=integ.account_email if integ else None,
        connected_at=integ.connected_at.isoformat() if integ and integ.connected_at else None,
        last_error=integ.last_error if integ else None,
    )


@router.get("/google/connect", response_model=ConnectResponse)
def google_connect(user=Depends(require_staff)):
    """Return the Google consent URL; the browser navigates there and comes back via /callback."""
    try:
        return ConnectResponse(url=gcal.auth_url(user.id))
    except gcal.NotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google integration is not configured on this server")


@router.get("/google/callback")
def google_callback(
    state: str = Query(""),
    code: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """OAuth redirect target (unauthenticated: the signed ``state`` identifies the user)."""
    user_id = gcal.parse_state(state) if state else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state")
    if error or not code:
        return _profile_redirect(google="error", reason=error or "no_code")
    try:
        tokens = gcal.exchange_code(code)
        gcal.save_connection(db, user_id, tokens)
        log_activity(db, user_id, "integration_connected", "user", user_id, details="Google Calendar connected")
        db.commit()
    except gcal.GoogleError as e:
        db.rollback()
        return _profile_redirect(google="error", reason=str(e)[:200])
    return _profile_redirect(google="connected")


@router.delete("/google", status_code=status.HTTP_204_NO_CONTENT)
def google_disconnect(db: Session = Depends(get_db), user=Depends(require_staff)):
    integ = gcal.get_integration(db, user.id)
    if integ is None:
        return
    gcal.disconnect(db, integ)
    log_activity(db, user.id, "integration_disconnected", "user", user.id, details="Google Calendar disconnected")
    db.commit()
