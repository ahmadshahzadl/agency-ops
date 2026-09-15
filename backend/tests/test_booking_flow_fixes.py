"""Booking flow hardening: host-side sync, reminders, outcomes, attribution, overrides, co-hosts,
email hygiene, reschedule notice."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1 import booking_public
from app.database import SessionLocal
from app.models import Meeting
from app.services import booking_service
from app.services import google_calendar_service as gcal
from tests.test_booking import _host_user_id, _slots, _book, _find_meeting, _iso  # noqa: F401
from tests.test_google_integration import FakeGoogle, _connect_host

PUB = "/api/v1/public/booking"
ADMIN = "/api/v1/booking-pages"


@pytest.fixture(autouse=True)
def _reset():
    booking_public.book_limiter.reset("testclient")
    booking_public.manage_limiter.reset("testclient")
    gcal.invalidate_busy_cache()
    booking_service._alert_last.clear()
    yield
    booking_public.book_limiter.reset("testclient")
    booking_public.manage_limiter.reset("testclient")


def _make_page(client, auth_headers, host_id, **extra):
    body = {
        "slug": f"fx-{uuid.uuid4().hex[:8]}", "name": "Discovery call", "duration_minutes": 30, "buffer_after_minutes": 0,
        "min_notice_minutes": 60, "max_days_ahead": 30, "timezone": "Asia/Karachi",
        "hours": {d: [["10:00", "12:00"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")},
        "questions": [], "location_text": "Video call", "host_user_id": host_id,
    }
    body.update(extra)
    r = client.post(ADMIN, headers=auth_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def gpage(client, auth_headers, monkeypatch):
    """Page whose host has (fake) Google connected."""
    host_id = _host_user_id(client, auth_headers)
    _connect_host(host_id)
    fake = FakeGoogle()
    fake.install(monkeypatch)
    page = _make_page(client, auth_headers, host_id)
    yield page, fake, host_id
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


# 1. host-side edits/deletes sync ------------------------------------------------

def test_host_move_updates_google_and_reminders(client, auth_headers, gpage):
    page, fake, _ = gpage
    slots = _slots(client, page["slug"], 1, 5)
    email = f"fx-{uuid.uuid4().hex[:8]}@example.com"
    assert _book(client, page["slug"], slots[0], email=email, answers={}).status_code == 201
    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    assert m["host_user_id"] and m["host_name"]
    new_start = _iso(slots[-1])
    r = client.patch(f"/api/v1/meetings/{m['id']}", headers=auth_headers, json={"start_at": new_start.isoformat(), "end_at": (new_start + timedelta(minutes=30)).isoformat()})
    assert r.status_code == 200, r.text
    assert _iso(r.json()["start_at"]) == new_start
    assert fake.updated == [fake.created[0]["id"]]


def test_host_delete_cancels_google_event(client, auth_headers, gpage):
    page, fake, _ = gpage
    email = f"fx-{uuid.uuid4().hex[:8]}@example.com"
    _book(client, page["slug"], _slots(client, page["slug"], 1, 5)[0], email=email, answers={})
    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    assert client.delete(f"/api/v1/meetings/{m['id']}", headers=auth_headers).status_code == 204
    assert fake.deleted == [fake.created[0]["id"]]
    assert client.get(f"/api/v1/meetings/{m['id']}", headers=auth_headers).status_code == 404


# 3. silent failures alert admins ---------------------------------------------------

def test_google_failure_alerts_admins_once(client, auth_headers, gpage, monkeypatch):
    page, fake, host_id = gpage

    def boom(*a, **k):
        raise gcal.GoogleError("simulated outage")

    monkeypatch.setattr(gcal, "create_event", boom)
    before = client.get("/api/v1/notifications", headers=auth_headers, params={"limit": 100}).json()
    before_ids = {n["id"] for n in (before if isinstance(before, list) else before.get("items", []))}
    for _ in range(2):
        slots = _slots(client, page["slug"], 1, 5)
        assert _book(client, page["slug"], slots[0], answers={}).status_code == 201
    after = client.get("/api/v1/notifications", headers=auth_headers, params={"limit": 100}).json()
    alerts = [n for n in (after if isinstance(after, list) else after.get("items", [])) if n["id"] not in before_ids and "Google Calendar problem" in n["title"]]
    assert len(alerts) == 1, "one alert per host per hour, not per booking"


# 4. outcome tracking + assign moves lead ------------------------------------------

def test_outcome_and_lead_stage(client, auth_headers):
    host_id = _host_user_id(client, auth_headers)
    page = _make_page(client, auth_headers, host_id, questions=[{"id": "company", "label": "Company", "type": "text", "required": True}])
    email = f"fx-{uuid.uuid4().hex[:8]}@example.com"
    _book(client, page["slug"], _slots(client, page["slug"], 1, 5)[0], email=email, answers={"company": "Outcome Ltd"})
    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    admin_id = client.get("/api/v1/auth/me", headers=auth_headers).json()["id"]
    client.patch(f"/api/v1/meetings/{m['id']}/assign", headers=auth_headers, json={"assigned_to": admin_id})
    assert client.get(f"/api/v1/leads/{m['lead_id']}", headers=auth_headers).json()["status"] == "contacted"

    r = client.patch(f"/api/v1/meetings/{m['id']}/outcome", headers=auth_headers, json={"status": "completed", "note": "Wants an ERP, budget ok", "lead_status": "qualified"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed" and r.json()["outcome_note"].startswith("Wants")
    assert client.get(f"/api/v1/leads/{m['lead_id']}", headers=auth_headers).json()["status"] == "qualified"
    r = client.patch(f"/api/v1/meetings/{m['id']}/outcome", headers=auth_headers, json={"status": "no_show"})
    assert r.json()["status"] == "no_show"
    assert client.patch(f"/api/v1/meetings/{m['id']}/outcome", headers=auth_headers, json={"status": "bogus"}).status_code == 400
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


# 5. attribution --------------------------------------------------------------------

def test_tracking_captured_on_booking_and_lead(client, auth_headers):
    page = _make_page(client, auth_headers, _host_user_id(client, auth_headers))
    email = f"fx-{uuid.uuid4().hex[:8]}@example.com"
    r = _book(client, page["slug"], _slots(client, page["slug"], 1, 5)[0], email=email, answers={},
              tracking={"utm_source": "linkedin", "utm_campaign": "q4", "referrer": "https://www.linkedin.com/", "junk": "x"})
    assert r.status_code == 201, r.text
    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    assert m["tracking"] == {"utm_source": "linkedin", "utm_campaign": "q4", "referrer": "https://www.linkedin.com/"}
    lead = client.get(f"/api/v1/leads/{m['lead_id']}", headers=auth_headers).json()
    assert "utm_source=linkedin" in (lead["notes"] or "")
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


# 6. overrides + co-hosts ---------------------------------------------------------------

def test_date_overrides_close_and_open_days(client, auth_headers):
    host_id = _host_user_id(client, auth_headers)
    day = (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat()
    page = _make_page(client, auth_headers, host_id)
    assert client.get(f"{PUB}/{page['slug']}/slots", params={"start": day, "end": day}).json()["slots"]
    # Close the day
    r = client.patch(f"{ADMIN}/{page['id']}", headers=auth_headers, json={"overrides": {day: []}})
    assert r.status_code == 200, r.text
    assert client.get(f"{PUB}/{page['slug']}/slots", params={"start": day, "end": day}).json()["slots"] == []
    # Special hours 15:00-16:00 -> exactly two 30-min slots
    client.patch(f"{ADMIN}/{page['id']}", headers=auth_headers, json={"overrides": {day: [["15:00", "16:00"]]}})
    slots = client.get(f"{PUB}/{page['slug']}/slots", params={"start": day, "end": day}).json()["slots"]
    assert len(slots) == 2
    assert client.patch(f"{ADMIN}/{page['id']}", headers=auth_headers, json={"overrides": {"not-a-date": []}}).status_code == 422
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


def test_co_hosts_round_robin(client, auth_headers):
    a = _host_user_id(client, auth_headers)
    b = _host_user_id(client, auth_headers)
    page = _make_page(client, auth_headers, a, co_host_ids=[b])
    assert {h["id"] for h in page["hosts"]} == {a, b}
    start = _slots(client, page["slug"], 1, 5)[0]
    m1 = _book(client, page["slug"], start, answers={})
    m2 = _book(client, page["slug"], start, answers={})  # other host still free
    assert m1.status_code == 201 and m2.status_code == 201, (m1.text, m2.text)
    assert _book(client, page["slug"], start, answers={}).status_code == 409  # both taken
    h1 = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == m1.json()["invitee_email"])["host_user_id"]
    h2 = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == m2.json()["invitee_email"])["host_user_id"]
    assert {h1, h2} == {a, b}
    assert start not in _slots(client, page["slug"], 1, 5)
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


# 7. email hygiene ----------------------------------------------------------------------

def test_disposable_and_dead_domains_rejected(client, auth_headers, monkeypatch):
    page = _make_page(client, auth_headers, _host_user_id(client, auth_headers))
    start = _slots(client, page["slug"], 1, 5)[0]
    r = _book(client, page["slug"], start, email="x@mailinator.com", answers={})
    assert r.status_code == 400 and "disposable" in r.json()["detail"]
    monkeypatch.setattr(booking_service, "domain_accepts_mail", lambda d: False)
    r = _book(client, page["slug"], start, email="x@no-such-domain-xyz-4821.com", answers={})
    assert r.status_code == 400 and "receive email" in r.json()["detail"]
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


# 8. reschedule notice + reminders ---------------------------------------------------------

def test_invitee_cannot_reschedule_at_the_last_minute(client, auth_headers):
    page = _make_page(client, auth_headers, _host_user_id(client, auth_headers), min_notice_minutes=240)
    slots = _slots(client, page["slug"], 1, 5)
    token = _book(client, page["slug"], slots[0], answers={}).json()["manage_token"]
    db = SessionLocal()
    try:
        m = db.query(Meeting).filter(Meeting.manage_token == token).one()
        m.start_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        m.end_at = m.start_at + timedelta(minutes=30)
        db.commit()
    finally:
        db.close()
    r = client.post(f"{PUB}/manage/{token}/reschedule", json={"start": slots[-1]})
    assert r.status_code == 400 and "too soon" in r.json()["detail"]
    # Cancel is still allowed, but flagged as late.
    r = client.post(f"{PUB}/manage/{token}/cancel", json={"reason": "sorry"})
    assert r.status_code == 200 and r.json()["cancel_reason"].startswith("Late cancellation")
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


def test_reminders_sent_once_per_window(client, auth_headers, monkeypatch):
    from app.services import email_service
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(email_service, "email_enabled", lambda: True)
    monkeypatch.setattr(email_service, "send_email", lambda to, subject, html, text, attachments=None: sent.append((to, subject)))

    page = _make_page(client, auth_headers, _host_user_id(client, auth_headers))
    email = f"rem-{uuid.uuid4().hex[:8]}@example.com"
    token = _book(client, page["slug"], _slots(client, page["slug"], 2, 6)[0], email=email, answers={}).json()["manage_token"]
    db = SessionLocal()
    try:
        m = db.query(Meeting).filter(Meeting.manage_token == token).one()
        start = m.start_at
        m.created_at = start - timedelta(days=3)  # booked well in advance
        db.commit()
        sent.clear()
        assert booking_service.send_due_reminders(db, now=start - timedelta(hours=30)) == 0
        assert booking_service.send_due_reminders(db, now=start - timedelta(hours=23)) >= 1
        assert any(to == email and "tomorrow" in subj for to, subj in sent)
        n_before = len(sent)
        assert booking_service.send_due_reminders(db, now=start - timedelta(hours=22)) == 0  # not twice
        assert len(sent) == n_before
        assert booking_service.send_due_reminders(db, now=start - timedelta(minutes=45)) >= 1
        assert any(to == email and "hour" in subj for to, subj in sent)
        db.refresh(m)
        assert m.reminder_24h_sent_at and m.reminder_1h_sent_at
        # Canceled bookings never get reminders
        m.status = "canceled"
        m.reminder_1h_sent_at = None
        db.commit()
        n_before = len(sent)
        booking_service.send_due_reminders(db, now=start - timedelta(minutes=30))
        assert len(sent) == n_before
    finally:
        db.close()
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)
