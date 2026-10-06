"""Agreement types and templates, public signing links, countersignature, NDA-gated client acceptance."""
import uuid

from tests.test_portal import _make_client_record


def _nda(client, auth_headers, client_id, **overrides):
    tpl = client.get("/api/v1/agreements/template?agreement_type=nda&client_id=" + client_id, headers=auth_headers).json()
    body = {"title": tpl["title_suggestion"], "client_id": client_id, "agreement_type": "nda", "clauses": tpl["clauses"], "valid_until": "2099-01-01"}
    body.update(overrides)
    r = client.post("/api/v1/agreements", headers=auth_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_types_and_templates(client, auth_headers):
    types = client.get("/api/v1/agreements/types", headers=auth_headers).json()
    keys = [t["key"] for t in types]
    assert keys == ["nda", "service", "retainer", "maintenance"]
    for key in keys:
        tpl = client.get(f"/api/v1/agreements/template?agreement_type={key}", headers=auth_headers).json()
        assert tpl["agreement_type"] == key and len(tpl["clauses"]) >= 8
        assert tpl["title_suggestion"]
    nda = client.get("/api/v1/agreements/template?agreement_type=nda", headers=auth_headers).json()
    assert nda["clauses"][0]["heading"] == "Parties" and "Non-Disclosure" in nda["clauses"][0]["body"]
    assert client.get("/api/v1/agreements/template?agreement_type=lease", headers=auth_headers).status_code == 400


def test_nda_number_prefix_and_type_on_record(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    a = _nda(client, auth_headers, cid)
    assert a["number"].startswith("NDA-") and a["agreement_type"] == "nda" and a["type_label"].startswith("Mutual")
    assert a["sign_url"] is None  # not sent yet


def test_public_signing_link_flow(client, auth_headers):
    cid = _make_client_record(client, auth_headers, email="prospect@example.com")
    # New clients created with a status
    client.patch(f"/api/v1/clients/{cid}", headers=auth_headers, json={"status": "prospect"})
    a = _nda(client, auth_headers, cid)

    # Sending creates the link
    r = client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    sent = r.json()
    assert sent["status"] == "sent" and sent["sign_url"] and "/sign/" in sent["sign_url"]
    token = sent["sign_url"].rsplit("/", 1)[1]

    # The staff-side link endpoint returns the same URL
    r = client.get(f"/api/v1/agreements/{a['id']}/sign-link", headers=auth_headers)
    assert r.status_code == 200 and r.json()["url"] == sent["sign_url"]

    # Anyone with the link can read it and fetch the PDF, no login
    r = client.get(f"/api/v1/public/agreements/{token}")
    assert r.status_code == 200, r.text
    pub = r.json()
    assert pub["can_sign"] is True and pub["number"] == a["number"] and len(pub["clauses"]) >= 8
    assert client.get(f"/api/v1/public/agreements/{token}/pdf").content[:5] == b"%PDF-"
    assert client.get("/api/v1/public/agreements/not-a-real-token-at-all").status_code == 404

    # Guards: must agree, must give a full name
    r = client.post(f"/api/v1/public/agreements/{token}/accept", json={"signer_name": "Jane Doe", "agreed": False})
    assert r.status_code == 400
    r = client.post(f"/api/v1/public/agreements/{token}/accept", json={"signer_name": "Jane", "agreed": True})
    assert r.status_code == 400

    # Sign
    r = client.post(
        f"/api/v1/public/agreements/{token}/accept",
        headers={"x-forwarded-for": "203.0.113.7", "user-agent": "pytest-browser"},
        json={"signer_name": "Jane Doe", "signer_email": "jane@example.com", "signer_title": "Founder", "agreed": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "signed" and r.json()["accepted_by_name"] == "Jane Doe" and r.json()["can_sign"] is False

    internal = client.get(f"/api/v1/agreements/{a['id']}", headers=auth_headers).json()
    assert internal["acceptance_method"] == "link"
    assert internal["signer_email"] == "jane@example.com" and internal["signer_title"] == "Founder"
    assert internal["accepted_ip"] == "203.0.113.7" and internal["acceptance_hash"] and len(internal["acceptance_hash"]) == 64
    assert internal["countersigned_at"] is None

    # Cannot sign twice or decline after signing; link still serves the executed PDF
    assert client.post(f"/api/v1/public/agreements/{token}/accept", json={"signer_name": "Jane Doe", "agreed": True}).status_code == 400
    assert client.post(f"/api/v1/public/agreements/{token}/decline", json={}).status_code == 400
    assert client.get(f"/api/v1/public/agreements/{token}/pdf").status_code == 200

    # Countersign for the company, then the record is complete
    r = client.post(f"/api/v1/agreements/{a['id']}/countersign", headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    assert r.json()["countersigned_at"] and r.json()["countersigned_by_name"]
    assert client.post(f"/api/v1/agreements/{a['id']}/countersign", headers=auth_headers, json={}).status_code == 400

    # The client now shows the NDA as signed and can be accepted
    c = client.get(f"/api/v1/clients/{cid}", headers=auth_headers).json()
    assert c["status"] == "prospect" and c["nda_status"] == "signed" and c["nda_signed_at"]
    r = client.patch(f"/api/v1/clients/{cid}", headers=auth_headers, json={"status": "active"})
    assert r.status_code == 200 and r.json()["status"] == "active"
    rows = client.get(f"/api/v1/clients?status=active&q={c['name']}", headers=auth_headers).json()
    assert any(x["id"] == cid for x in rows)
    rows = client.get(f"/api/v1/clients?status=prospect&q={c['name']}", headers=auth_headers).json()
    assert all(x["id"] != cid for x in rows)


def test_decline_via_link(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    a = _nda(client, auth_headers, cid)
    token = client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers, json={}).json()["sign_url"].rsplit("/", 1)[1]
    r = client.post(f"/api/v1/public/agreements/{token}/decline", json={"reason": "Clause 9 too long"})
    assert r.status_code == 200 and r.json()["status"] == "declined"
    internal = client.get(f"/api/v1/agreements/{a['id']}", headers=auth_headers).json()
    assert internal["status"] == "declined" and internal["decline_reason"] == "Clause 9 too long"
    assert client.get(f"/api/v1/clients/{cid}", headers=auth_headers).json()["nda_status"] == "declined"


def test_expired_link_cannot_sign(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    a = _nda(client, auth_headers, cid, valid_until="2020-01-01")
    # Sending an already-past-deadline agreement: expiry is applied lazily on read
    client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers, json={})
    internal = client.get(f"/api/v1/agreements/{a['id']}", headers=auth_headers).json()
    assert internal["status"] == "expired"
    assert internal["sign_url"] is None


def test_send_to_override_address(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    a = _nda(client, auth_headers, cid)
    r = client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers, json={"to": "signer@partner.example"})
    assert r.status_code == 200, r.text
    assert r.json()["signer_email"] == "signer@partner.example"
    r = client.post(f"/api/v1/agreements/{a['id']}/send", headers=auth_headers, json={"to": "not-an-email"})
    assert r.status_code == 422


def test_pdf_handles_unicode_punctuation():
    from app.services.pdf_service import _txt
    assert _txt("Agreement — BLIND POINT") == "Agreement - BLIND POINT"
    assert _txt("it’s “quoted”…") == "it's \"quoted\"..."
    assert "?" not in _txt("Mutual Non-Disclosure Agreement — Acme")


def test_public_endpoints_need_no_auth_but_staff_endpoints_do(client, auth_headers, employee_headers):
    cid = _make_client_record(client, auth_headers)
    a = _nda(client, auth_headers, cid)
    assert client.get(f"/api/v1/agreements/{a['id']}/sign-link", headers=employee_headers).status_code == 403
    assert client.post(f"/api/v1/agreements/{a['id']}/countersign", headers=employee_headers, json={}).status_code == 403
    assert client.get("/api/v1/agreements/types", headers=employee_headers).status_code == 403


def test_only_admin_can_delete_signed(client, auth_headers, employee_headers):
    cid = _make_client_record(client, auth_headers)
    a = _nda(client, auth_headers, cid)
    client.post(f"/api/v1/agreements/{a['id']}/mark-signed", headers=auth_headers, json={"signer_name": "Test Signer"})
    assert client.get(f"/api/v1/agreements/{a['id']}", headers=auth_headers).json()["status"] == "signed"
    # employee has no agreements:write at all
    assert client.delete(f"/api/v1/agreements/{a['id']}", headers=employee_headers).status_code == 403
    assert client.delete(f"/api/v1/agreements/{a['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/agreements/{a['id']}", headers=auth_headers).status_code == 404
