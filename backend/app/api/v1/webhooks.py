"""Inbound webhooks from third-party services. No user auth: each endpoint verifies its own
provider signature and is disabled (404) until the matching secret is configured."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.services import calendly_service
from app.services.activity_service import meetings_updated_this_request, notifications_updated_this_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/calendly", status_code=status.HTTP_200_OK)
async def calendly_webhook(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    key = (settings.calendly_webhook_signing_key or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    raw = await request.body()
    try:
        calendly_service.verify_signature(
            raw,
            request.headers.get("Calendly-Webhook-Signature"),
            key,
            settings.calendly_webhook_tolerance_seconds,
        )
    except calendly_service.InvalidSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event = body.get("event")
    try:
        if event == "invitee.created":
            meeting = calendly_service.handle_invitee_created(db, body)
            result = {"ok": True, "event": event, "meeting_id": str(meeting.id)}
        elif event == "invitee.canceled":
            meeting = calendly_service.handle_invitee_canceled(db, body)
            result = {"ok": True, "event": event, "meeting_id": str(meeting.id) if meeting else None}
        else:
            # Unknown/unsubscribed event types are acknowledged so Calendly stops retrying.
            return {"ok": True, "event": event, "ignored": True}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    db.commit()
    meetings_updated_this_request.set(True)
    notifications_updated_this_request.set(True)
    logger.info("calendly webhook %s -> meeting %s", event, result.get("meeting_id"))
    return result
