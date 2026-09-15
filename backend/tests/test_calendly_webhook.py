"""Calendly webhook: signature enforcement, booking -> Meeting (+Lead), cancel, idempotent retries."""
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.config import get_settings
from app.services.calendly_service import sign_payload

URL = "/api/v1/webhooks/calendly"
KEY = "test-signing-key"


@pytest.fixture
def signing_key():
    settings = get_settings()
    old = settings.calendly_webhook_signing_key
    settings.calendly_webhook_signing_key = KEY
    yield KEY
    settings.calendly_webhook_signing_key = old


def _booking(event: str = "invitee.created", *, invitee_uri: str | None = None, email: str | None = None,
             status: str = "active", cancellation: dict | None = None, rescheduled: bool = False,
             host_email: str | None = None) -> dict:
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(minutes=30)
    uid = uuid.uuid4().hex
    invitee_uri = invitee_uri or f"https://api.calendly.com/scheduled_events/EV{uid}/invitees/IN{uid}"
    payload = {
        "uri": invitee_uri,
        "name": "Jane Client",
        "email": email or f"jane-{uid[:8]}@example.com",
        "status": status,
        "timezone": "Asia/Dubai",
        "rescheduled": rescheduled,
        "cancel_url": "https://calendly.com/cancellations/abc",
        "reschedule_url": "https://calendly.com/reschedulings/abc",
        "questions_and_answers": [
            {"question": "Company name", "answer": "Acme Trading LLC", "position": 0},
            {"question": "What do you need?", "answer": "An ERP for our warehouse", "position": 1},
        ],
        "tracking": {"utm_source": "website", "utm_medium": None},
        "scheduled_event": {
            "uri": f"https://api.calendly.com/scheduled_events/EV{uid}",
            "name": "Discovery call",
            "status": "active",
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "end_time": end.isoformat().replace("+00:00", "Z"),
            "location": {"type": "google_conference", "join_url": "https://meet.google.com/abc-defg-hij"},
            "event_memberships": [{"user_email": host_email or "nobody@example.com", "user_name": "Host"}],
        },
    }
    if cancellation:
        payload["cancellation"] = cancellation
    return {"event": event, "created_at": datetime.now(timezone.utc).isoformat(), "payload": payload}


def _post(client, body: dict, key: str = KEY, ts: int | None = None, header: str | None = "auto"):
    raw = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if header == "auto":
        headers["Calendly-Webhook-Signature"] = sign_payload(raw, key, ts)
    elif header:
        headers["Calendly-Webhook-Signature"] = header
    return client.post(URL, content=raw, headers=headers)


def test_disabled_without_signing_key(client):
    settings = get_settings()
    old = settings.calendly_webhook_signing_key
    settings.calendly_webhook_signing_key = ""
    try:
        assert _post(client, _booking()).status_code == 404
    finally:
        settings.calendly_webhook_signing_key = old


def test_rejects_missing_or_bad_signature(client, signing_key):
    assert _post(client, _booking(), header=None).status_code == 401
    assert _post(client, _booking(), key="wrong-key").status_code == 401
    assert _post(client, _booking(), header="t=1,v1=deadbeef").status_code == 401
    stale = int(time.time()) - 3600
    assert _post(client, _booking(), ts=stale).status_code == 401


def test_booking_creates_meeting_and_lead(client, auth_headers, signing_key):
    body = _booking(email=f"new-{uuid.uuid4().hex[:8]}@example.com", host_email="admin@example.com")
    resp = _post(client, body)
    assert resp.status_code == 200, resp.text
    meeting_id = resp.json()["meeting_id"]

    m = client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers).json()
    assert m["source"] == "calendly"
    assert m["status"] == "scheduled"
    assert m["title"] == "Discovery call with Jane Client"
    assert m["invitee_email"] == body["payload"]["email"]
    assert m["location"] == "https://meet.google.com/abc-defg-hij"
    assert "Acme Trading LLC" in (m["description"] or "")
    assert m["external_id"] == body["payload"]["uri"]
    assert m["lead_id"], "a new contact should open a lead"

    leads = client.get("/api/v1/leads", headers=auth_headers).json()
    items = leads if isinstance(leads, list) else leads.get("items", [])
    lead = next(l for l in items if l["id"] == m["lead_id"])
    assert lead["source"] == "calendly"
    assert lead["company_name"] == "Acme Trading LLC"
    assert lead["contact_email"] == body["payload"]["email"]

    # Secrets never leak: the endpoint needs no auth but still must not be listable without it.
    assert client.get(f"/api/v1/meetings/{meeting_id}").status_code == 401


def test_redelivery_is_idempotent(client, auth_headers, signing_key):
    body = _booking()
    first = _post(client, body).json()["meeting_id"]
    second = _post(client, body).json()["meeting_id"]
    assert first == second
    same_email = [
        m for m in client.get("/api/v1/meetings", headers=auth_headers).json()
        if m.get("external_id") == body["payload"]["uri"]
    ]
    assert len(same_email) == 1


def test_cancel_marks_meeting_canceled(client, auth_headers, signing_key):
    body = _booking()
    meeting_id = _post(client, body).json()["meeting_id"]
    cancel = _booking(
        "invitee.canceled",
        invitee_uri=body["payload"]["uri"],
        email=body["payload"]["email"],
        status="canceled",
        cancellation={"canceled_by": "Jane Client", "reason": "Conflict", "canceler_type": "invitee"},
    )
    resp = _post(client, cancel)
    assert resp.status_code == 200
    assert resp.json()["meeting_id"] == meeting_id
    m = client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers).json()
    assert m["status"] == "canceled"
    assert "Conflict" in m["cancel_reason"]


def test_cancel_unknown_booking_is_acknowledged(client, signing_key):
    resp = _post(client, _booking("invitee.canceled", status="canceled"))
    assert resp.status_code == 200
    assert resp.json()["meeting_id"] is None


def test_unknown_event_is_ignored(client, signing_key):
    resp = _post(client, {"event": "routing_form_submission.created", "payload": {}})
    assert resp.status_code == 200
    assert resp.json()["ignored"] is True
