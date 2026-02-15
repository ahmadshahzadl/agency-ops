from datetime import date, timedelta
import uuid


def test_list_invoices_unauthorized(client):
    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 401


def test_list_invoices(client, auth_headers):
    resp = client.get("/api/v1/invoices", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_invoice(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "Invoice Client"})
    client_id = c_resp.json()["id"]
    number = f"INV-TEST-{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/invoices",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "number": number,
            "amount": 1000.50,
            "currency": "USD",
            "status": "draft",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"] == number
    assert float(data["amount"]) == 1000.50


def test_get_invoice(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    number = f"INV-{uuid.uuid4().hex[:8]}"
    inv_resp = client.post(
        "/api/v1/invoices",
        headers=auth_headers,
        json={"client_id": c_resp.json()["id"], "number": number, "amount": 500},
    )
    inv_id = inv_resp.json()["id"]
    resp = client.get(f"/api/v1/invoices/{inv_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["number"] == number


def test_create_payment(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    number = f"INV-PAY-{uuid.uuid4().hex[:8]}"
    inv_resp = client.post(
        "/api/v1/invoices",
        headers=auth_headers,
        json={"client_id": c_resp.json()["id"], "number": number, "amount": 200},
    )
    invoice_id = inv_resp.json()["id"]
    paid_at = (date.today() - timedelta(days=1)).isoformat()
    resp = client.post(
        "/api/v1/payments",
        headers=auth_headers,
        json={"invoice_id": invoice_id, "amount": 200, "paid_at": paid_at},
    )
    assert resp.status_code == 201
    assert resp.json()["invoice_id"] == invoice_id


def test_list_expenses(client, auth_headers):
    resp = client.get("/api/v1/expenses", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_expense(client, auth_headers):
    resp = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "description": "Office supplies",
            "amount": 75.99,
            "currency": "USD",
            "expense_date": date.today().isoformat(),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Office supplies"
    assert float(data["amount"]) == 75.99


def test_update_expense(client, auth_headers):
    create_resp = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={"description": "Old", "amount": 10},
    )
    exp_id = create_resp.json()["id"]
    resp = client.patch(
        f"/api/v1/expenses/{exp_id}",
        headers=auth_headers,
        json={"description": "Updated", "amount": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"
    assert float(resp.json()["amount"]) == 20


def test_delete_expense(client, auth_headers):
    create_resp = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={"description": "To delete", "amount": 5},
    )
    exp_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/expenses/{exp_id}", headers=auth_headers)
    assert resp.status_code == 204
