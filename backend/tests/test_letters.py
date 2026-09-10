"""Letters: type templates, lifecycle (draft -> issued freeze),
letterhead PDFs, and permission gates."""
import uuid

from tests.test_portal import _make_client_record


def _make_letter(client, auth_headers, **overrides):
    body = {
        "letter_type": "general",
        "subject": f"Test letter {uuid.uuid4().hex[:6]}",
        "body": "Dear Sir/Madam,\n\nThis is a test letter.\n\nSincerely,",
        "recipient_name": "John Recipient",
    }
    body.update(overrides)
    r = client.post("/api/v1/letters", headers=auth_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_letter_types_and_templates(client, auth_headers):
    types = client.get("/api/v1/letters/types", headers=auth_headers).json()
    values = [t["value"] for t in types]
    for expected in ("general", "offer_letter", "experience_letter", "noc", "completion_certificate"):
        assert expected in values

    t = client.get("/api/v1/letters/template?letter_type=experience_letter&recipient_name=Jane%20Dev", headers=auth_headers).json()
    assert "Jane Dev" in t["body"]
    assert t["subject"] == "Experience Letter"

    # Client name fills in when only a client is given
    cid = _make_client_record(client, auth_headers)
    cname = client.get(f"/api/v1/clients/{cid}", headers=auth_headers).json()["name"]
    t = client.get(f"/api/v1/letters/template?letter_type=completion_certificate&client_id={cid}", headers=auth_headers).json()
    assert cname in t["body"]

    assert client.get("/api/v1/letters/template?letter_type=banana", headers=auth_headers).status_code == 400


def test_letter_lifecycle_and_freeze(client, auth_headers):
    l = _make_letter(client, auth_headers)
    assert l["status"] == "draft"
    assert l["number"].startswith("LTR-")
    assert l["letter_date"]  # defaults to today
    assert l["signatory_name"]  # defaults to the author

    # Editable while draft
    r = client.patch(f"/api/v1/letters/{l['id']}", headers=auth_headers, json={"subject": "Updated subject"})
    assert r.status_code == 200 and r.json()["subject"] == "Updated subject"

    # Validation
    assert client.patch(f"/api/v1/letters/{l['id']}", headers=auth_headers, json={"body": "  "}).status_code == 400
    assert client.post("/api/v1/letters", headers=auth_headers, json={"letter_type": "banana", "subject": "x", "body": "y"}).status_code == 400

    # Issue freezes the record
    r = client.post(f"/api/v1/letters/{l['id']}/issue", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "issued"
    assert client.patch(f"/api/v1/letters/{l['id']}", headers=auth_headers, json={"subject": "Nope"}).status_code == 400
    assert client.delete(f"/api/v1/letters/{l['id']}", headers=auth_headers).status_code == 400
    assert client.post(f"/api/v1/letters/{l['id']}/issue", headers=auth_headers).status_code == 400

    # Drafts can be deleted
    l2 = _make_letter(client, auth_headers)
    assert client.delete(f"/api/v1/letters/{l2['id']}", headers=auth_headers).status_code == 204


def test_letter_pdf_and_blank_letterhead(client, auth_headers):
    l = _make_letter(client, auth_headers, recipient_address="Street 1\nLahore")
    r = client.get(f"/api/v1/letters/{l['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert f'{l["number"]}.pdf' in r.headers["content-disposition"]
    assert r.content[:5] == b"%PDF-"

    r = client.get("/api/v1/letters/blank-pdf", headers=auth_headers)
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"


def test_letter_send_requires_recipient_email(client, auth_headers):
    l = _make_letter(client, auth_headers)  # no email, no client
    assert client.post(f"/api/v1/letters/{l['id']}/send", headers=auth_headers).status_code == 400

    l2 = _make_letter(client, auth_headers, recipient_email="jane@clientmail.com")
    r = client.post(f"/api/v1/letters/{l2['id']}/send", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "issued"  # sending a draft issues it


def test_letter_permission_gate(client, auth_headers, employee_headers):
    assert client.get("/api/v1/letters", headers=employee_headers).status_code == 403
    assert client.get("/api/v1/letters/blank-pdf", headers=employee_headers).status_code == 403
    r = client.post("/api/v1/letters", headers=employee_headers, json={"subject": "x", "body": "y"})
    assert r.status_code == 403
