"""Lead contact history: logging interactions, the merged timeline, and the
denormalised last_contact_at / next_follow_up_at fields on the lead."""
import uuid
from datetime import datetime, timedelta, timezone


def _make_lead(client, headers, **extra):
    r = client.post(
        "/api/v1/leads",
        headers=headers,
        json={"company_name": f"Acme {uuid.uuid4().hex[:6]}", "contact_email": "buyer@example.com", **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_log_interaction_updates_lead_and_timeline(client, auth_headers):
    lead = _make_lead(client, auth_headers)
    assert lead["last_contact_at"] is None and lead["next_follow_up_at"] is None

    follow_up = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
    r = client.post(
        f"/api/v1/leads/{lead['id']}/interactions",
        headers=auth_headers,
        json={"type": "call", "summary": "Intro call, wants a CRM demo", "next_follow_up_at": follow_up.isoformat()},
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["type"] == "call"
    assert row["summary"] == "Intro call, wants a CRM demo"
    assert row["created_by_name"]

    fresh = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()
    assert fresh["last_contact_at"] is not None
    assert datetime.fromisoformat(fresh["next_follow_up_at"]) == follow_up
    # Logging contact on an unclaimed lead assigns it to the person doing the work.
    assert fresh["assigned_to"] is not None

    listed = client.get(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers).json()
    assert [i["id"] for i in listed] == [row["id"]]

    timeline = client.get(f"/api/v1/leads/{lead['id']}/timeline", headers=auth_headers).json()
    kinds = {(t["kind"], t["type"]) for t in timeline}
    assert ("interaction", "call") in kinds
    assert ("activity", "lead_created") in kinds
    # The interaction's own audit row is not duplicated as a separate activity entry.
    assert ("activity", "lead_interaction_logged") not in kinds
    assert timeline[0]["kind"] == "interaction"  # newest first


def test_interaction_can_move_stage_and_validates_input(client, auth_headers):
    lead = _make_lead(client, auth_headers)
    r = client.post(
        f"/api/v1/leads/{lead['id']}/interactions",
        headers=auth_headers,
        json={"type": "email", "summary": "Sent pricing", "status": "contacted"},
    )
    assert r.status_code == 201, r.text
    assert client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()["status"] == "contacted"

    bad_type = client.post(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers, json={"type": "fax", "summary": "x"})
    assert bad_type.status_code == 400
    empty = client.post(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers, json={"type": "call", "summary": "   "})
    assert empty.status_code == 400
    bad_status = client.post(
        f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers, json={"type": "call", "summary": "x", "status": "won"}
    )
    assert bad_status.status_code == 400


def test_delete_interaction_recomputes_contact_fields(client, auth_headers):
    lead = _make_lead(client, auth_headers)
    older = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    newer = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    a = client.post(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers, json={"type": "call", "summary": "first", "occurred_at": older}).json()
    b = client.post(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers, json={"type": "whatsapp", "summary": "second", "occurred_at": newer}).json()

    fresh = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()
    assert datetime.fromisoformat(fresh["last_contact_at"]) == datetime.fromisoformat(newer)

    r = client.delete(f"/api/v1/leads/{lead['id']}/interactions/{b['id']}", headers=auth_headers)
    assert r.status_code == 204
    fresh = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()
    assert datetime.fromisoformat(fresh["last_contact_at"]) == datetime.fromisoformat(older)

    r = client.delete(f"/api/v1/leads/{lead['id']}/interactions/{a['id']}", headers=auth_headers)
    assert r.status_code == 204
    fresh = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()
    assert fresh["last_contact_at"] is None

    missing = client.delete(f"/api/v1/leads/{lead['id']}/interactions/{uuid.uuid4()}", headers=auth_headers)
    assert missing.status_code == 404


def test_interactions_follow_lead_access_rules(client, auth_headers, employee_headers):
    """An employee who is not on the sales team and not the assignee cannot see or log contact."""
    lead = _make_lead(client, auth_headers, status="contacted")
    r = client.get(f"/api/v1/leads/{lead['id']}/timeline", headers=employee_headers)
    assert r.status_code in (403, 404)
    r = client.post(f"/api/v1/leads/{lead['id']}/interactions", headers=employee_headers, json={"type": "call", "summary": "x"})
    assert r.status_code in (403, 404)


def test_deleting_lead_removes_its_interactions(client, auth_headers):
    lead = _make_lead(client, auth_headers)
    client.post(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers, json={"type": "call", "summary": "x"})
    assert client.delete(f"/api/v1/leads/{lead['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/leads/{lead['id']}/interactions", headers=auth_headers).status_code == 404
