"""Solutions engineers: see inbound bookings/leads, assign a prospect, attribution follows to the client."""
import uuid
from datetime import datetime, timedelta

import pytest

from app.api.v1 import booking_public
from tests.conftest import _ensure_user_and_login
from tests.test_booking import _host_user_id, _slots, _book, _find_meeting  # noqa: F401

PUB = "/api/v1/public/booking"
ADMIN = "/api/v1/booking-pages"


@pytest.fixture(autouse=True)
def _reset_limiters():
    booking_public.book_limiter.reset("testclient")
    yield
    booking_public.book_limiter.reset("testclient")


@pytest.fixture
def se_headers(client, auth_headers):
    h = _ensure_user_and_login(client, auth_headers, "se@test.com", "test123", "solutions_engineer", "Test SE")
    if h is None:
        pytest.skip("Role 'solutions_engineer' missing - run migrations")
    return h


def _me(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()


def _all_ids(client, headers, **params) -> set:
    """Every meeting id the caller can list (walks the paginated endpoint)."""
    ids, skip = set(), 0
    while skip < 5000:
        batch = client.get("/api/v1/meetings", headers=headers, params={"skip": skip, "limit": 100, **params}).json()
        ids.update(m["id"] for m in batch)
        if len(batch) < 100:
            break
        skip += 100
    return ids


@pytest.fixture
def booking(client, auth_headers):
    """A live website booking (meeting + lead) on a page hosted by a throwaway user."""
    slug = f"se-{uuid.uuid4().hex[:8]}"
    page = client.post(
        ADMIN,
        headers=auth_headers,
        json={
            "slug": slug, "name": "Discovery call", "duration_minutes": 30, "buffer_after_minutes": 0,
            "min_notice_minutes": 60, "max_days_ahead": 30, "timezone": "Asia/Karachi",
            "hours": {d: [["10:00", "12:00"]] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")},
            "questions": [{"id": "company", "label": "Company name", "type": "text", "required": True}],
            "host_user_id": _host_user_id(client, auth_headers),
        },
    ).json()
    email = f"prospect-{uuid.uuid4().hex[:8]}@example.com"
    r = _book(client, slug, _slots(client, slug, 1, 5)[0], email=email, answers={"company": "Prospect Co"})
    assert r.status_code == 201, r.text
    meeting = _find_meeting(client, auth_headers, lambda x: x.get("invitee_email") == email)
    yield {"page": page, "meeting": meeting, "email": email}
    client.delete(f"{ADMIN}/{page['id']}", headers=auth_headers)


def test_se_sees_inbound_bookings_but_not_manual_meetings(client, auth_headers, se_headers, booking):
    m = booking["meeting"]
    assert m["company_name"] == "Prospect Co"
    assert m["assigned_to"] is None

    assert m["id"] in _all_ids(client, se_headers, source="external")
    assert client.get(f"/api/v1/meetings/{m['id']}", headers=se_headers).status_code == 200

    start = datetime.utcnow() + timedelta(days=3)
    manual = client.post(
        "/api/v1/meetings", headers=auth_headers,
        json={"title": "Internal sync", "start_at": start.isoformat(), "end_at": (start + timedelta(hours=1)).isoformat()},
    ).json()
    assert client.get(f"/api/v1/meetings/{manual['id']}", headers=se_headers).status_code == 404
    assert manual["id"] not in _all_ids(client, se_headers)
    client.delete(f"/api/v1/meetings/{manual['id']}", headers=auth_headers)


def test_se_sees_inbound_lead_and_assignment_flows_to_lead(client, auth_headers, se_headers, booking):
    m = booking["meeting"]
    se_id = _me(client, se_headers)["id"]

    leads = client.get("/api/v1/leads", headers=se_headers, params={"limit": 100}).json()
    lead = next((l for l in leads if l["id"] == m["lead_id"]), None)
    assert lead is not None and lead["source"] == "website" and lead["assigned_to"] is None

    assignees = client.get("/api/v1/meetings/booking-assignees", headers=se_headers).json()
    assert any(a["id"] == se_id for a in assignees)

    r = client.patch(f"/api/v1/meetings/{m['id']}/assign", headers=se_headers, json={"assigned_to": se_id})
    assert r.status_code == 200, r.text
    assert r.json()["assigned_to"] == se_id and r.json()["assigned_to_name"] == "Test SE"

    lead = client.get(f"/api/v1/leads/{m['lead_id']}", headers=se_headers).json()
    assert lead["assigned_to"] == se_id

    assert m["id"] in _all_ids(client, se_headers, assigned="me")
    assert m["id"] not in _all_ids(client, auth_headers, assigned="unassigned")

    # Unassign clears both
    r = client.patch(f"/api/v1/meetings/{m['id']}/assign", headers=auth_headers, json={"assigned_to": None})
    assert r.status_code == 200 and r.json()["assigned_to"] is None
    assert client.get(f"/api/v1/leads/{m['lead_id']}", headers=auth_headers).json()["assigned_to"] is None


def test_attribution_reaches_the_client(client, auth_headers, se_headers, booking):
    m = booking["meeting"]
    se_id = _me(client, se_headers)["id"]
    client.patch(f"/api/v1/meetings/{m['id']}/assign", headers=se_headers, json={"assigned_to": se_id})

    r = client.post(f"/api/v1/leads/{m['lead_id']}/convert", headers=auth_headers, json={"create_project": False})
    assert r.status_code in (200, 201), r.text
    body = r.json()
    client_id = body.get("client_id") or (body.get("client") or {}).get("id") or body.get("id")
    assert client_id

    c = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers).json()
    assert c["source"] == "website"
    assert c["solutions_engineer_id"] == se_id
    assert c["solutions_engineer_name"] == "Test SE"

    # The SE keeps access to the client they brought in, even without a team.
    assert client.get(f"/api/v1/clients/{client_id}", headers=se_headers).status_code == 200
    listed = client.get("/api/v1/clients", headers=se_headers, params={"limit": 100}).json()
    assert any(x["id"] == client_id for x in listed), "SE should see the client they brought in"

    # Once converted, re-assigning the meeting no longer rewrites the lead's owner.
    admin_id = _me(client, auth_headers)["id"]
    client.patch(f"/api/v1/meetings/{m['id']}/assign", headers=auth_headers, json={"assigned_to": admin_id})
    assert client.get(f"/api/v1/leads/{m['lead_id']}", headers=auth_headers).json()["assigned_to"] == se_id


def test_employee_cannot_assign_or_see_bookings(client, auth_headers, employee_headers, booking):
    m = booking["meeting"]
    assert client.patch(f"/api/v1/meetings/{m['id']}/assign", headers=employee_headers, json={"assigned_to": None}).status_code == 403
    assert client.get(f"/api/v1/meetings/{m['id']}", headers=employee_headers).status_code == 404
