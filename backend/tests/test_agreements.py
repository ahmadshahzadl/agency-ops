"""Service agreements: template, lifecycle, signed-immutability, portal
clickwrap acceptance with an audit record, and permission gates."""
import uuid

from tests.test_portal import _make_client_record, _make_portal_user


def _make_agreement(client, auth_headers, client_id, **overrides):
    template = client.get("/api/v1/agreements/template", headers=auth_headers).json()
    body = {
        "title": f"Services for {uuid.uuid4().hex[:6]}",
        "client_id": client_id,
        "currency": "USD",
        "contract_value": 5000,
        "clauses": template["clauses"],
    }
    body.update(overrides)
    r = client.post("/api/v1/agreements", headers=auth_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_template_has_minimal_clause_set(client, auth_headers):
    t = client.get("/api/v1/agreements/template", headers=auth_headers).json()
    headings = [c["heading"] for c in t["clauses"]]
    for expected in ("Parties", "Scope of Services", "Fees & Payment", "Intellectual Property",
                     "Confidentiality", "Warranties & Liability", "Termination"):
        assert expected in headings, headings
    assert all(c["body"].strip() for c in t["clauses"])


def test_template_prefills_from_quote(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    q = client.post("/api/v1/quotes", headers=auth_headers, json={
        "title": "Ecommerce build", "client_id": cid, "currency": "USD",
        "items": [{"description": "Storefront implementation", "quantity": 1, "unit_price": 4000}],
    }).json()
    t = client.get(f"/api/v1/agreements/template?quote_id={q['id']}", headers=auth_headers).json()
    scope = next(c for c in t["clauses"] if c["heading"] == "Scope of Services")
    fees = next(c for c in t["clauses"] if c["heading"] == "Fees & Payment")
    assert "Storefront implementation" in scope["body"]
    assert q["number"] in fees["body"]


def test_agreement_lifecycle_and_editing(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    a = _make_agreement(client, auth_headers, cid)
    assert a["status"] == "draft"
    assert a["number"].startswith("AGR-")

    # Editable while draft
    r = client.patch(f"/api/v1/agreements/{a['id']}", headers=auth_headers, json={"title": "Renamed"})
    assert r.status_code == 200 and r.json()["title"] == "Renamed"

    # Needs at least one clause
    assert client.patch(f"/api/v1/agreements/{a['id']}", headers=auth_headers, json={"clauses": []}).status_code == 400

    # Send, then mark signed manually
    assert client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers).status_code == 200
    r = client.post(f"/api/v1/agreements/{a['id']}/mark-signed", headers=auth_headers, json={"signer_name": "Jane Client"})
    assert r.status_code == 200
    signed = r.json()
    assert signed["status"] == "signed"
    assert signed["accepted_by_name"] == "Jane Client"
    assert signed["acceptance_method"] == "manual"

    # Signed = frozen: no edit, no delete, no re-send
    assert client.patch(f"/api/v1/agreements/{a['id']}", headers=auth_headers, json={"title": "Nope"}).status_code == 400
    assert client.delete(f"/api/v1/agreements/{a['id']}", headers=auth_headers).status_code == 400
    assert client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers).status_code == 400

    # Terminate requires a reason and freezes the record
    assert client.post(f"/api/v1/agreements/{a['id']}/terminate", headers=auth_headers, json={"reason": "  "}).status_code == 400
    r = client.post(f"/api/v1/agreements/{a['id']}/terminate", headers=auth_headers, json={"reason": "Client pivoted"})
    assert r.status_code == 200 and r.json()["status"] == "terminated"
    assert client.delete(f"/api/v1/agreements/{a['id']}", headers=auth_headers).status_code == 400

    # Renew: duplicate makes a fresh draft with the same terms
    r = client.post(f"/api/v1/agreements/{a['id']}/duplicate", headers=auth_headers)
    assert r.status_code == 201
    dup = r.json()
    assert dup["status"] == "draft" and dup["number"] != a["number"]
    assert len(dup["clauses"]) == len(signed["clauses"])


def test_agreement_pdf(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    a = _make_agreement(client, auth_headers, cid)
    r = client.get(f"/api/v1/agreements/{a['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert f'{a["number"]}.pdf' in r.headers["content-disposition"]
    assert r.content[:5] == b"%PDF-"


def test_agreement_permission_gate(client, auth_headers, employee_headers):
    assert client.get("/api/v1/agreements", headers=employee_headers).status_code == 403
    cid = _make_client_record(client, auth_headers)
    template = client.get("/api/v1/agreements/template", headers=auth_headers).json()
    r = client.post("/api/v1/agreements", headers=employee_headers, json={
        "title": "Nope", "client_id": cid, "clauses": template["clauses"]})
    assert r.status_code == 403


def test_portal_agreement_visibility_and_clickwrap(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    other_cid = _make_client_record(client, auth_headers)
    headers = _make_portal_user(client, auth_headers, cid)

    draft = _make_agreement(client, auth_headers, cid)
    sent = _make_agreement(client, auth_headers, cid)
    foreign = _make_agreement(client, auth_headers, other_cid)
    client.post(f"/api/v1/agreements/{sent['id']}/send", headers=auth_headers)
    client.post(f"/api/v1/agreements/{foreign['id']}/send", headers=auth_headers)

    # Drafts and other clients' agreements are invisible
    rows = client.get("/api/v1/portal/agreements", headers=headers).json()
    numbers = [r["number"] for r in rows]
    assert sent["number"] in numbers
    assert draft["number"] not in numbers and foreign["number"] not in numbers

    # Overview counts pending signatures
    ov = client.get("/api/v1/portal/overview", headers=headers).json()
    assert ov["pending_agreements"] == 1

    # Signing requires a typed name
    r = client.post(f"/api/v1/portal/agreements/{sent['id']}/accept", headers=headers, json={"signer_name": "  "})
    assert r.status_code == 400

    # Clickwrap acceptance records who/when and freezes the agreement
    r = client.post(f"/api/v1/portal/agreements/{sent['id']}/accept", headers=headers, json={"signer_name": "Jane Doe"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "signed"
    assert body["accepted_by_name"] == "Jane Doe"
    assert body["accepted_at"]

    internal = client.get(f"/api/v1/agreements/{sent['id']}", headers=auth_headers).json()
    assert internal["acceptance_method"] == "portal"

    # Can't sign twice, can't sign someone else's, can't decline after signing
    assert client.post(f"/api/v1/portal/agreements/{sent['id']}/accept", headers=headers, json={"signer_name": "Jane Doe"}).status_code == 400
    assert client.post(f"/api/v1/portal/agreements/{foreign['id']}/accept", headers=headers, json={"signer_name": "Jane Doe"}).status_code == 404
    assert client.post(f"/api/v1/portal/agreements/{sent['id']}/decline", headers=headers, json={}).status_code == 400

    # Portal PDF works for own signed agreement
    r = client.get(f"/api/v1/portal/agreements/{sent['id']}/pdf", headers=headers)
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"


def test_portal_agreement_decline(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    headers = _make_portal_user(client, auth_headers, cid)
    a = _make_agreement(client, auth_headers, cid)
    client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers)
    r = client.post(f"/api/v1/portal/agreements/{a['id']}/decline", headers=headers, json={"reason": "Budget changed"})
    assert r.status_code == 200 and r.json()["status"] == "declined"
    internal = client.get(f"/api/v1/agreements/{a['id']}", headers=auth_headers).json()
    assert internal["decline_reason"] == "Budget changed"
    # Declined is terminal for the client, but the agency can still delete the record
    assert client.delete(f"/api/v1/agreements/{a['id']}", headers=auth_headers).status_code == 204
