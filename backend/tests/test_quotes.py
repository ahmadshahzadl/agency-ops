"""Quotes: lifecycle, totals, conversion to project, fixed-price invoicing, permissions."""
import uuid


def _make_client(client, auth_headers):
    r = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Quote Client {uuid.uuid4().hex[:6]}"})
    assert r.status_code == 201
    return r.json()["id"]


def _make_quote(client, auth_headers, client_id=None, lead_id=None, items=None):
    body = {
        "title": f"Website build {uuid.uuid4().hex[:4]}",
        "client_id": client_id,
        "lead_id": lead_id,
        "items": items if items is not None else [
            {"description": "Design", "quantity": 1, "unit_price": 1500},
            {"description": "Development", "quantity": 40, "unit_price": 50},
        ],
    }
    return client.post("/api/v1/quotes", headers=auth_headers, json=body)


def test_quote_lifecycle_and_totals(client, auth_headers):
    cid = _make_client(client, auth_headers)
    r = _make_quote(client, auth_headers, client_id=cid)
    assert r.status_code == 201, r.text
    quote = r.json()
    assert quote["status"] == "draft"
    assert float(quote["total"]) == 1500 + 40 * 50
    assert len(quote["items"]) == 2
    assert quote["number"].startswith("QUO-")

    # Edit items in draft
    r = client.patch(
        f"/api/v1/quotes/{quote['id']}", headers=auth_headers,
        json={"items": [{"description": "Everything", "quantity": 1, "unit_price": 5000}]},
    )
    assert r.status_code == 200
    assert float(r.json()["total"]) == 5000

    # Send then accept
    assert client.post(f"/api/v1/quotes/{quote['id']}/send", headers=auth_headers).status_code == 200
    r = client.post(f"/api/v1/quotes/{quote['id']}/accept", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    assert r.json()["accepted_at"]

    # Locked after acceptance
    assert client.patch(f"/api/v1/quotes/{quote['id']}", headers=auth_headers, json={"title": "New"}).status_code == 400
    assert client.delete(f"/api/v1/quotes/{quote['id']}", headers=auth_headers).status_code == 400

    # Convert to project
    r = client.post(f"/api/v1/quotes/{quote['id']}/convert", headers=auth_headers)
    assert r.status_code == 200, r.text
    project = r.json()
    assert project["client_id"] == cid
    # Double conversion blocked
    assert client.post(f"/api/v1/quotes/{quote['id']}/convert", headers=auth_headers).status_code == 400

    # Fixed-price invoice from the quote
    r = client.post(f"/api/v1/quotes/{quote['id']}/invoice", headers=auth_headers)
    assert r.status_code == 201, r.text
    inv = r.json()
    assert float(inv["amount"]) == 5000
    assert inv["project_id"] == project["id"]


def test_quote_requires_target(client, auth_headers):
    r = _make_quote(client, auth_headers)  # no client, no lead
    assert r.status_code == 400


def test_quote_on_lead_needs_client_to_convert(client, auth_headers):
    lead = client.post(
        "/api/v1/leads", headers=auth_headers,
        json={"company_name": f"Lead Co {uuid.uuid4().hex[:6]}", "contact_email": "lead@example.com"},
    )
    assert lead.status_code == 201, lead.text
    r = _make_quote(client, auth_headers, lead_id=lead.json()["id"])
    assert r.status_code == 201
    qid = r.json()["id"]
    client.post(f"/api/v1/quotes/{qid}/accept", headers=auth_headers)
    # Lead not converted to a client yet
    assert client.post(f"/api/v1/quotes/{qid}/convert", headers=auth_headers).status_code == 400


def test_rejected_quote_cannot_be_accepted(client, auth_headers):
    cid = _make_client(client, auth_headers)
    qid = _make_quote(client, auth_headers, client_id=cid).json()["id"]
    assert client.post(f"/api/v1/quotes/{qid}/reject", headers=auth_headers).status_code == 200
    assert client.post(f"/api/v1/quotes/{qid}/accept", headers=auth_headers).status_code == 400


def test_employee_has_no_quote_access(client, auth_headers, employee_headers):
    cid = _make_client(client, auth_headers)
    assert _make_quote(client, employee_headers, client_id=cid).status_code == 403
    assert client.get("/api/v1/quotes", headers=employee_headers).status_code == 403
