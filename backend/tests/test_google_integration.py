"""Google Calendar integration: OAuth plumbing + booking hooks (Google API faked)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1 import booking_public
from app.config import get_settings
from app.database import SessionLocal
from app.models.integration import UserIntegration
from app.services import booking_service
from app.services import google_calendar_service as gcal
from app.services.vault_service import encrypt_secret
from tests.test_booking import _host_user_id, _slots, _book, _find_meeting, _iso  # noqa: F401

PUB = "/api/v1/public/booking"
ADMIN = "/api/v1/booking-pages"
INTEG = "/api/v1/integrations"


@pytest.fixture(autouse=True)
def _reset_limiters():
    booking_public.book_limiter.reset("testclient")
    booking_public.manage_limiter.reset("testclient")
    gcal.invalidate_busy_cache()
    yield
    booking_public.book_limiter.reset("testclient")
    booking_public.manage_limiter.reset("testclient")
    gcal.invalidate_busy_cache()


@pytest.fixture
def configured():
    s = get_settings()
    old = (s.google_client_id, s.google_client_secret)
    s.google_client_id, s.google_client_secret = "test-client-id.apps.googleusercontent.com", "test-secret"
    yield
    s.google_client_id, s.google_client_secret = old


# ---------------- OAuth plumbing ----------------

def test_state_round_trip():
    uid = uuid.uuid4()
    assert gcal.parse_state(gcal.make_state(uid)) == uid
    assert gcal.parse_state("garbage") is None


def test_status_and_connect_when_not_configured(client, auth_headers):
    s = get_settings()
    old = (s.google_client_id, s.google_client_secret)
    s.google_client_id, s.google_client_secret = "", ""
    try:
        st = client.get(f"{INTEG}/google/status", headers=auth_headers).json()
        assert st["configured"] is False
        assert client.get(f"{INTEG}/google/connect", headers=auth_headers).status_code == 503
    finally:
        s.google_client_id, s.google_client_secret = old


def test_connect_url_and_callback_rejects_bad_state(client, auth_headers, configured):
    r = client.get(f"{INTEG}/google/connect", headers=auth_headers)
    assert r.status_code == 200
    url = r.json()["url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "access_type=offline" in url and "calendar.events" in url and "state=" in url
    assert client.get(f"{INTEG}/google/callback", params={"state": "nope", "code": "x"}).status_code == 400
    assert client.get(f"{INTEG}/google/connect").status_code == 401


def test_callback_saves_connection_with_fake_google(client, auth_headers, configured, monkeypatch):
    me = client.get("/api/v1/auth/me", headers=auth_headers).json()
    monkeypatch.setattr(gcal, "exchange_code", lambda code: {"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "email": "host@gmail.com", "scope": "x"})
    r = client.get(f"{INTEG}/google/callback", params={"state": gcal.make_state(uuid.UUID(me["id"])), "code": "abc"}, follow_redirects=False)
    assert r.status_code == 302 and "google=connected" in r.headers["location"]
    st = client.get(f"{INTEG}/google/status", headers=auth_headers).json()
    assert st["connected"] is True and st["account_email"] == "host@gmail.com"
    monkeypatch.setattr(gcal, "disconnect", lambda db, integ: db.delete(integ))
    assert client.delete(f"{INTEG}/google", headers=auth_headers).status_code == 204
    assert client.get(f"{INTEG}/google/status", headers=auth_headers).json()["connected"] is False


# ---------------- booking hooks (fake Calendar API) ----------------

class FakeGoogle:
    """Stands in for the Calendar API: records calls, serves busy blocks, mints Meet links."""

    def __init__(self):
        self.busy: list[tuple[datetime, datetime]] = []
        self.created: list[dict] = []
        self.updated: list[str] = []
        self.deleted: list[str] = []

    def install(self, monkeypatch):
        monkeypatch.setattr(gcal, "busy_intervals", lambda db, integ, start, end: list(self.busy))

        def create(db, integ, meeting, page):
            ev = {"id": f"gev-{uuid.uuid4().hex[:8]}", "meeting": str(meeting.id)}
            self.created.append(ev)
            return ev["id"], f"https://meet.google.com/{ev['id']}"

        def update(db, integ, meeting, page):
            self.updated.append(meeting.google_event_id)
            return f"https://meet.google.com/{meeting.google_event_id}"

        def delete(db, integ, meeting):
            self.deleted.append(meeting.google_event_id)

        monkeypatch.setattr(gcal, "create_event", create)
        monkeypatch.setattr(gcal, "update_event", update)
        monkeypatch.setattr(gcal, "delete_event", delete)


def _connect_host(host_id: str) -> None:
    db = SessionLocal()
    try:
        db.add(UserIntegration(user_id=uuid.UUID(host_id), provider="google", account_email="host@gmail.com", refresh_token_encrypted=encrypt_secret("rt")))
        db.commit()
    finally:
        db.close()


@pytest.fixture
def page(client, auth_headers):
    host_id = _host_user_id(client, auth_headers)
    _connect_host(host_id)
    slug = f"gcal-{uuid.uuid4().hex[:8]}"
    r = client.post(
        ADMIN,
        headers=auth_headers,
        json={
            "slug": slug, "name": "Discovery call", "duration_minutes": 30, "buffer_after_minutes": 0,
            "min_notice_minutes": 60, "max_days_ahead": 30, "timezone": "Asia/Karachi",
            "hours": {d: [["10:00", "12:00"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")},
            "questions": [], "location_text": "Video call", "host_user_id": host_id,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    yield data
    client.delete(f"{ADMIN}/{data['id']}", headers=auth_headers)


def test_admin_sees_host_google_state(client, auth_headers, page):
    assert page["host_google_connected"] is True


def test_google_busy_blocks_slots(client, page, monkeypatch):
    fake = FakeGoogle()
    fake.install(monkeypatch)
    before = _slots(client, page["slug"], 1, 3)
    assert len(before) == 12
    # Block the whole first day's window on the host's Google calendar.
    first = _iso(before[0])
    fake.busy = [(first, first + timedelta(hours=2))]
    gcal.invalidate_busy_cache()
    after = _slots(client, page["slug"], 1, 3)
    assert len(after) == 8
    assert before[0] not in after


def test_booking_creates_meet_link_and_syncs_changes(client, auth_headers, page, monkeypatch):
    fake = FakeGoogle()
    fake.install(monkeypatch)
    slots = _slots(client, page["slug"], 1, 5)
    email = f"g-{uuid.uuid4().hex[:8]}@example.com"
    r = _book(client, page["slug"], slots[0], email=email, answers={})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["location"].startswith("https://meet.google.com/")
    assert len(fake.created) == 1

    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    assert m["google_event_id"] == fake.created[0]["id"]
    assert m["location"] == b["location"]

    token = b["manage_token"]
    r = client.post(f"{PUB}/manage/{token}/reschedule", json={"start": slots[-1]})
    assert r.status_code == 200, r.text
    assert fake.updated == [fake.created[0]["id"]]

    r = client.post(f"{PUB}/manage/{token}/cancel", json={"reason": "bye"})
    assert r.status_code == 200
    assert fake.deleted == [fake.created[0]["id"]]


def test_google_failure_does_not_block_booking(client, auth_headers, page, monkeypatch):
    def boom(*a, **k):
        raise gcal.GoogleError("simulated outage")

    monkeypatch.setattr(gcal, "busy_intervals", boom)
    monkeypatch.setattr(gcal, "create_event", boom)
    slots = _slots(client, page["slug"], 1, 3)
    assert slots, "free/busy failure must fail open"
    email = f"g-{uuid.uuid4().hex[:8]}@example.com"
    r = _book(client, page["slug"], slots[0], email=email, answers={})
    assert r.status_code == 201, r.text
    assert r.json()["location"] == "Video call"  # fell back to the page's location text + .ics invite
    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    assert m["google_event_id"] is None
