"""PDF generation for invoices and quotes: content type, scope, send guard."""
import uuid


def _make_client(client, auth_headers, email=None):
    body = {"name": f"PDF Client {uuid.uuid4().hex[:6]}"}
    if email:
        body["contact_email"] = email
    return client.post("/api/v1/clients", headers=auth_headers, json=body).json()["id"]


def test_invoice_pdf_renders(client, auth_headers):
    cid = _make_client(client, auth_headers)
    inv = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": cid, "number": f"INV-PDF-{uuid.uuid4().hex[:8]}", "amount": 1234.56, "currency": "USD", "status": "draft"},
    ).json()
    r = client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_quote_pdf_renders_with_items(client, auth_headers):
    cid = _make_client(client, auth_headers)
    q = client.post(
        "/api/v1/quotes", headers=auth_headers,
        json={"title": "PDF Quote", "client_id": cid, "terms": "Net 15",
              "items": [{"description": "Design", "quantity": 2, "unit_price": 300}]},
    ).json()
    r = client.get(f"/api/v1/quotes/{q['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


def test_invoice_pdf_scope_denied_for_employee(client, auth_headers, employee_headers):
    cid = _make_client(client, auth_headers)
    inv = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": cid, "number": f"INV-PS-{uuid.uuid4().hex[:8]}", "amount": 10, "currency": "USD", "status": "draft"},
    ).json()
    assert client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=employee_headers).status_code == 403


def test_send_invoice_requires_email_setup(client, auth_headers):
    cid = _make_client(client, auth_headers, email="billing@acme.test")
    inv = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": cid, "number": f"INV-SND-{uuid.uuid4().hex[:8]}", "amount": 10, "currency": "USD", "status": "draft"},
    ).json()
    # SMTP unset in tests -> clean 400, not a silent no-op that flips status
    r = client.post(f"/api/v1/invoices/{inv['id']}/send", headers=auth_headers)
    assert r.status_code == 400
    assert "SMTP" in r.json()["detail"]


def test_send_invoice_requires_client_email(client, auth_headers):
    cid = _make_client(client, auth_headers)  # no contact email
    inv = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": cid, "number": f"INV-NE-{uuid.uuid4().hex[:8]}", "amount": 10, "currency": "USD", "status": "draft"},
    ).json()
    r = client.post(f"/api/v1/invoices/{inv['id']}/send", headers=auth_headers)
    assert r.status_code == 400
    assert "email" in r.json()["detail"].lower()
