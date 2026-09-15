"""Native booking: admin pages, public slots, booking, double-booking, cancel, reschedule."""
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.api.v1 import booking_public

PUB = "/api/v1/public/booking"
ADMIN = "/api/v1/booking-pages"


@pytest.fixture(autouse=True)
def _no_rate_limit():
    booking_public.book_limiter.reset("testclient")
    booking_public.manage_limiter.reset("testclient")
    yield
    booking_public.book_limiter.reset("testclient")
    booking_public.manage_limiter.reset("testclient")


def _host_user_id(client, auth_headers) -> str:
    """A dedicated host per test run so meetings left behind by other tests never block slots."""
    roles = client.get("/api/v1/roles", headers=auth_headers).json()
    role_id = next(r["id"] for r in roles if r["name"] == "employee")
    email = f"host-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={"email": email, "password": "HostPass123!", "full_name": "Sam Host", "role_ids": [role_id]},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


@pytest.fixture
def page(client, auth_headers):
    slug = f"call-{uuid.uuid4().hex[:8]}"
    resp = client.post(
        ADMIN,
        headers=auth_headers,
        json={
            "slug": slug,
            "name": "Discovery call",
            "description": "30 minutes, no commitment.",
            "duration_minutes": 30,
            "buffer_after_minutes": 15,
            "min_notice_minutes": 60,
            "max_days_ahead": 30,
            "timezone": "Asia/Karachi",
            "hours": {d: [["10:00", "12:00"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")},
            "questions": [
                {"id": "company", "label": "Company name", "type": "text", "required": True},
                {"id": "notes", "label": "What are you building?", "type": "textarea", "required": False},
            ],
            "location_text": "Google Meet (link in your invite)",
            "host_user_id": _host_user_id(client, auth_headers),
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    yield data
    client.delete(f"{ADMIN}/{data['id']}", headers=auth_headers)


def _find_meeting(client, auth_headers, pred):
    """The internal meetings list is paginated (50/page); walk it until the booking shows up."""
    skip = 0
    seen = 0
    sample: list = []
    while skip < 5000:
        resp = client.get("/api/v1/meetings", headers=auth_headers, params={"skip": skip, "limit": 100})
        assert resp.status_code == 200, f"meetings list failed: {resp.status_code} {resp.text[:200]}"
        batch = resp.json()
        seen += len(batch)
        if not sample:
            sample = [(m.get("title"), m.get("invitee_email"), m.get("source"), m.get("start_at")) for m in batch[:4]]
        for m in batch:
            if pred(m):
                return m
        if len(batch) < 100:
            break
        skip += 100
    raise AssertionError(f"meeting not found in internal list ({seen} meetings scanned; newest: {sample})")


def _iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _slots(client, slug, days_from=1, days_to=8, **params):
    start = (datetime.now(timezone.utc) + timedelta(days=days_from)).date()
    end = (datetime.now(timezone.utc) + timedelta(days=days_to)).date()
    r = client.get(f"{PUB}/{slug}/slots", params={"start": start.isoformat(), "end": end.isoformat(), **params})
    assert r.status_code == 200, r.text
    return r.json()["slots"]


def _book(client, slug, start, email=None, answers=None, **extra):
    return client.post(
        f"{PUB}/{slug}/book",
        json={
            "start": start,
            "name": "Jane Client",
            "email": email or f"jane-{uuid.uuid4().hex[:8]}@example.com",
            "timezone": "Europe/London",
            "answers": answers if answers is not None else {"company": "Acme Ltd", "notes": "An ERP"},
            **extra,
        },
    )


# ---------------- admin ----------------

def test_admin_requires_permission(client, page):
    assert client.get(ADMIN).status_code == 401


def test_admin_validation(client, auth_headers):
    bad = client.post(ADMIN, headers=auth_headers, json={"slug": "Bad Slug", "name": "x"})
    assert bad.status_code == 422
    bad_tz = client.post(ADMIN, headers=auth_headers, json={"slug": "ok-slug", "name": "x", "timezone": "Mars/Olympus"})
    assert bad_tz.status_code == 422
    bad_hours = client.post(ADMIN, headers=auth_headers, json={"slug": "ok-slug", "name": "x", "hours": {"mon": [["12:00", "09:00"]]}})
    assert bad_hours.status_code == 422


def test_admin_slug_conflict(client, auth_headers, page):
    dup = client.post(ADMIN, headers=auth_headers, json={"slug": page["slug"], "name": "Dup"})
    assert dup.status_code == 409


# ---------------- public ----------------

def test_public_page_and_hidden_when_inactive(client, auth_headers, page):
    r = client.get(f"{PUB}/{page['slug']}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Discovery call"
    assert [q["id"] for q in body["questions"]] == ["company", "notes"]
    assert "host_user_id" not in body

    client.patch(f"{ADMIN}/{page['id']}", headers=auth_headers, json={"is_active": False})
    assert client.get(f"{PUB}/{page['slug']}").status_code == 404
    assert client.get(f"{PUB}/{page['slug']}/slots", params={"start": "2030-01-01", "end": "2030-01-02"}).status_code == 404


def test_slots_follow_hours_and_timezone(client, page):
    slots = _slots(client, page["slug"], 1, 3)
    assert slots, "expected slots inside 10:00-12:00 windows"
    tz = ZoneInfo("Asia/Karachi")
    for s in slots:
        local = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(tz)
        assert 10 <= local.hour < 12
        assert local.minute in (0, 30)
    # 4 slots per day (10:00, 10:30, 11:00, 11:30) for 3 days
    assert len(slots) == 12


def test_slots_respect_min_notice_and_max_days(client, auth_headers, page):
    # A day beyond max_days_ahead offers nothing.
    far = (datetime.now(timezone.utc) + timedelta(days=40)).date()
    r = client.get(f"{PUB}/{page['slug']}/slots", params={"start": far.isoformat(), "end": far.isoformat()})
    assert r.json()["slots"] == []
    # Everything returned is at least min_notice in the future.
    earliest = datetime.now(timezone.utc) + timedelta(minutes=60)
    for s in _slots(client, page["slug"], 0, 2):
        assert datetime.fromisoformat(s.replace("Z", "+00:00")) >= earliest


def test_book_creates_meeting_lead_and_removes_slot(client, auth_headers, page):
    slots = _slots(client, page["slug"])
    start = slots[0]
    email = f"new-{uuid.uuid4().hex[:8]}@example.com"
    r = _book(client, page["slug"], start, email=email)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "scheduled"
    assert b["invitee_email"] == email
    assert len(b["manage_token"]) >= 32

    # The slot is gone, and so is the next one (30 min meeting + 15 min buffer swallows 10:30).
    after = _slots(client, page["slug"])
    assert start not in after
    assert len(after) == len(slots) - 2

    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    assert m["source"] == "website"
    assert m["title"] == "Discovery call with Jane Client"
    assert m["answers"] == {"company": "Acme Ltd", "notes": "An ERP"}
    assert m["location"] == "Google Meet (link in your invite)"
    assert m["lead_id"]
    assert m["booking_page_id"] == page["id"]
    assert "manage_token" not in m  # internal API never leaks the self-service token

    leads = client.get("/api/v1/leads", headers=auth_headers).json()
    lead = next(l for l in leads if l["id"] == m["lead_id"])
    assert lead["source"] == "website"
    assert lead["company_name"] == "Acme Ltd"


def test_double_booking_rejected(client, page):
    start = _slots(client, page["slug"])[0]
    assert _book(client, page["slug"], start).status_code == 201
    assert _book(client, page["slug"], start).status_code == 409


def test_required_answer_enforced(client, page):
    start = _slots(client, page["slug"])[0]
    r = _book(client, page["slug"], start, answers={"notes": "no company given"})
    assert r.status_code == 400
    assert "Company name" in r.json()["detail"]


def test_off_hours_and_honeypot_rejected(client, page):
    off = (datetime.now(timezone.utc) + timedelta(days=2)).replace(hour=1, minute=0, second=0, microsecond=0)
    assert _book(client, page["slug"], off.isoformat()).status_code == 409
    start = _slots(client, page["slug"])[0]
    assert _book(client, page["slug"], start, website="http://spam").status_code == 400


def test_manage_cancel_and_reschedule(client, auth_headers, page):
    slots = _slots(client, page["slug"])
    start, other = slots[0], slots[-1]
    email = f"jane-{uuid.uuid4().hex[:8]}@example.com"
    token = _book(client, page["slug"], start, email=email).json()["manage_token"]

    got = client.get(f"{PUB}/manage/{token}")
    assert got.status_code == 200
    assert _iso(got.json()["start"]) == _iso(start)
    assert client.get(f"{PUB}/manage/{'x' * 40}").status_code == 404

    # Reschedule: excluding own booking makes the original slot visible again.
    excl = client.get(
        f"{PUB}/{page['slug']}/slots",
        params={"start": start[:10], "end": start[:10], "exclude": token},
    ).json()["slots"]
    assert start in excl
    r = client.post(f"{PUB}/manage/{token}/reschedule", json={"start": other, "timezone": "Asia/Dubai"})
    assert r.status_code == 200, r.text
    assert _iso(r.json()["start"]) == _iso(other)
    assert r.json()["invitee_timezone"] == "Asia/Dubai"
    assert start in _slots(client, page["slug"])  # freed

    # Cancel
    r = client.post(f"{PUB}/manage/{token}/cancel", json={"reason": "Schedule conflict"})
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"
    assert "Schedule conflict" in r.json()["cancel_reason"]
    assert other in _slots(client, page["slug"])  # freed
    # Cannot reschedule a canceled booking
    assert client.post(f"{PUB}/manage/{token}/reschedule", json={"start": other}).status_code == 400

    m = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email and x.get("invitee_timezone") == "Asia/Dubai")
    assert m["status"] == "canceled"


def test_booking_rate_limit(client, page):
    # Every other slot: a 30 min booking plus the 15 min buffer swallows the following slot.
    slots = _slots(client, page["slug"], 1, 10)[::2]
    booking_public.book_limiter.reset("testclient")
    codes = [_book(client, page["slug"], s).status_code for s in slots[:6]]
    assert codes[:5] == [201] * 5
    assert codes[5] == 429
