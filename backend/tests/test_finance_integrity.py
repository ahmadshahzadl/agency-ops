"""Finance integrity: payment reconciliation, guards, dedup, number collisions."""
import uuid
from datetime import date


def _make_invoice(client, auth_headers, amount=1000, currency="USD", number=None):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Fin Client {uuid.uuid4().hex[:6]}"})
    r = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={
            "client_id": c.json()["id"],
            "number": number or f"INV-FIN-{uuid.uuid4().hex[:8]}",
            "amount": amount,
            "currency": currency,
            "status": "sent",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _pay(client, auth_headers, invoice_id, amount):
    return client.post(
        "/api/v1/payments", headers=auth_headers,
        json={"invoice_id": invoice_id, "amount": amount, "paid_at": str(date.today())},
    )


def test_full_payment_marks_invoice_paid(client, auth_headers):
    inv = _make_invoice(client, auth_headers, amount=500)
    assert _pay(client, auth_headers, inv["id"], 500).status_code == 201
    fetched = client.get(f"/api/v1/invoices/{inv['id']}", headers=auth_headers).json()
    assert fetched["status"] == "paid"
    assert float(fetched["paid_total"]) == 500


def test_partial_payments_then_paid(client, auth_headers):
    inv = _make_invoice(client, auth_headers, amount=1000)
    assert _pay(client, auth_headers, inv["id"], 400).status_code == 201
    mid = client.get(f"/api/v1/invoices/{inv['id']}", headers=auth_headers).json()
    assert mid["status"] == "sent"
    assert float(mid["paid_total"]) == 400
    assert _pay(client, auth_headers, inv["id"], 600).status_code == 201
    assert client.get(f"/api/v1/invoices/{inv['id']}", headers=auth_headers).json()["status"] == "paid"

    payments = client.get(f"/api/v1/invoices/{inv['id']}/payments", headers=auth_headers).json()
    assert len(payments) == 2
    assert sum(float(p["amount"]) for p in payments) == 1000


def test_overpayment_and_nonpositive_rejected(client, auth_headers):
    inv = _make_invoice(client, auth_headers, amount=100)
    assert _pay(client, auth_headers, inv["id"], 150).status_code == 400
    assert _pay(client, auth_headers, inv["id"], 0).status_code == 400
    assert _pay(client, auth_headers, inv["id"], -50).status_code == 400
    # Exact remaining balance still works after a partial
    assert _pay(client, auth_headers, inv["id"], 60).status_code == 201
    assert _pay(client, auth_headers, inv["id"], 41).status_code == 400
    assert _pay(client, auth_headers, inv["id"], 40).status_code == 201


def test_invoice_amount_cannot_drop_below_paid(client, auth_headers):
    inv = _make_invoice(client, auth_headers, amount=1000)
    _pay(client, auth_headers, inv["id"], 700)
    r = client.patch(f"/api/v1/invoices/{inv['id']}", headers=auth_headers, json={"amount": 500})
    assert r.status_code == 400
    assert client.patch(f"/api/v1/invoices/{inv['id']}", headers=auth_headers, json={"amount": 800}).status_code == 200


def test_duplicate_invoice_number_clean_400(client, auth_headers):
    number = f"INV-DUP-{uuid.uuid4().hex[:8]}"
    _make_invoice(client, auth_headers, number=number)
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Dup Client {uuid.uuid4().hex[:6]}"})
    r = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": c.json()["id"], "number": number, "amount": 10, "currency": "USD", "status": "draft"},
    )
    assert r.status_code == 400


def test_invalid_currency_and_amount_rejected(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Cur Client {uuid.uuid4().hex[:6]}"})
    cid = c.json()["id"]
    base = {"client_id": cid, "number": f"INV-C-{uuid.uuid4().hex[:8]}", "status": "draft"}
    assert client.post("/api/v1/invoices", headers=auth_headers, json={**base, "amount": 100, "currency": "100"}).status_code == 400
    assert client.post("/api/v1/invoices", headers=auth_headers, json={**base, "amount": -5, "currency": "USD"}).status_code == 400
    r = client.post("/api/v1/expenses", headers=auth_headers, json={"description": "bad", "amount": -10, "currency": "USD"})
    assert r.status_code == 400
    r = client.post("/api/v1/expenses", headers=auth_headers, json={"description": "bad", "amount": 10, "currency": "12"})
    assert r.status_code == 400


def test_quote_cannot_be_invoiced_twice(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"QInv Client {uuid.uuid4().hex[:6]}"})
    q = client.post(
        "/api/v1/quotes", headers=auth_headers,
        json={"title": "Fixed price job", "client_id": c.json()["id"], "items": [{"description": "Work", "quantity": 1, "unit_price": 2500}]},
    ).json()
    client.post(f"/api/v1/quotes/{q['id']}/accept", headers=auth_headers)
    first = client.post(f"/api/v1/quotes/{q['id']}/invoice", headers=auth_headers)
    assert first.status_code == 201
    assert first.json()["quote_id"] == q["id"]
    second = client.post(f"/api/v1/quotes/{q['id']}/invoice", headers=auth_headers)
    assert second.status_code == 400
    assert first.json()["number"] in second.json()["detail"]


def test_invoice_items_drive_amount(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Items Client {uuid.uuid4().hex[:6]}"})
    r = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": c.json()["id"], "number": f"INV-IT-{uuid.uuid4().hex[:8]}", "currency": "USD", "status": "draft",
        "items": [
            {"description": "Design", "quantity": 1, "unit_price": 500},
            {"description": "Development", "quantity": 10, "unit_price": 60},
        ],
    })
    assert r.status_code == 201, r.text
    inv = r.json()
    assert float(inv["amount"]) == 1100.0
    assert len(inv["items"]) == 2

    # Manual amount edit is blocked while items exist
    r = client.patch(f"/api/v1/invoices/{inv['id']}", headers=auth_headers, json={"amount": 999})
    assert r.status_code == 400
    # Editing items recomputes
    r = client.patch(f"/api/v1/invoices/{inv['id']}", headers=auth_headers,
                     json={"items": [{"description": "Everything", "quantity": 1, "unit_price": 2000}]})
    assert r.status_code == 200
    assert float(r.json()["amount"]) == 2000.0

    # PDF renders the items
    pdf = client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=auth_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_invoice_items_respect_paid_floor(client, auth_headers):
    from datetime import date
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"ItemsPaid {uuid.uuid4().hex[:6]}"})
    inv = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": c.json()["id"], "number": f"INV-IP-{uuid.uuid4().hex[:8]}", "currency": "USD", "status": "sent",
        "items": [{"description": "Work", "quantity": 1, "unit_price": 1000}],
    }).json()
    client.post("/api/v1/payments", headers=auth_headers,
                json={"invoice_id": inv["id"], "amount": 800, "paid_at": str(date.today())})
    r = client.patch(f"/api/v1/invoices/{inv['id']}", headers=auth_headers,
                     json={"items": [{"description": "Cheaper", "quantity": 1, "unit_price": 500}]})
    assert r.status_code == 400


def test_invoice_fx_display(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"FX Client {uuid.uuid4().hex[:6]}"})
    r = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": c.json()["id"], "number": f"INV-FX-{uuid.uuid4().hex[:8]}", "amount": 100,
        "currency": "USD", "status": "draft", "fx_currency": "PKR", "fx_rate": 278.5,
    })
    assert r.status_code == 201, r.text
    assert r.json()["fx_currency"] == "PKR"
    assert float(r.json()["fx_rate"]) == 278.5
    # Bad fx values rejected
    bad = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": c.json()["id"], "number": f"INV-FB-{uuid.uuid4().hex[:8]}", "amount": 100,
        "currency": "USD", "status": "draft", "fx_currency": "123", "fx_rate": 1,
    })
    assert bad.status_code == 400
    bad2 = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": c.json()["id"], "number": f"INV-FB2-{uuid.uuid4().hex[:8]}", "amount": 100,
        "currency": "USD", "status": "draft", "fx_currency": "PKR", "fx_rate": -2,
    })
    assert bad2.status_code == 400
