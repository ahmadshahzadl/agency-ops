"""Audit remainder: quote expiry, invoice overdue, budget carry, board detach."""
import uuid
from datetime import date, timedelta


def _make_client(client, auth_headers):
    r = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"AR Client {uuid.uuid4().hex[:6]}"})
    return r.json()["id"]


def test_quote_expires_lazily_and_can_be_revived(client, auth_headers):
    cid = _make_client(client, auth_headers)
    yesterday = str(date.today() - timedelta(days=1))
    q = client.post(
        "/api/v1/quotes", headers=auth_headers,
        json={"title": "Expiring", "client_id": cid, "valid_until": yesterday,
              "items": [{"description": "x", "quantity": 1, "unit_price": 100}]},
    ).json()
    # Reading it flips it to expired
    fetched = client.get(f"/api/v1/quotes/{q['id']}", headers=auth_headers).json()
    assert fetched["status"] == "expired"
    # Expired quotes cannot be accepted or sent
    assert client.post(f"/api/v1/quotes/{q['id']}/accept", headers=auth_headers).status_code == 400
    assert client.post(f"/api/v1/quotes/{q['id']}/send", headers=auth_headers).status_code == 400
    # Extending validity revives it as a draft
    tomorrow = str(date.today() + timedelta(days=7))
    r = client.patch(f"/api/v1/quotes/{q['id']}", headers=auth_headers, json={"valid_until": tomorrow})
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
    assert client.post(f"/api/v1/quotes/{q['id']}/accept", headers=auth_headers).status_code == 200


def test_invoice_goes_overdue_lazily(client, auth_headers):
    cid = _make_client(client, auth_headers)
    yesterday = str(date.today() - timedelta(days=1))
    inv = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": cid, "number": f"INV-OD-{uuid.uuid4().hex[:8]}", "amount": 100,
              "currency": "USD", "status": "sent", "due_date": yesterday},
    ).json()
    fetched = client.get(f"/api/v1/invoices/{inv['id']}", headers=auth_headers).json()
    assert fetched["status"] == "overdue"
    # Paying it still settles it
    client.post("/api/v1/payments", headers=auth_headers,
                json={"invoice_id": inv["id"], "amount": 100, "paid_at": str(date.today())})
    assert client.get(f"/api/v1/invoices/{inv['id']}", headers=auth_headers).json()["status"] == "paid"


def test_quote_convert_carries_budget(client, auth_headers):
    cid = _make_client(client, auth_headers)
    q = client.post(
        "/api/v1/quotes", headers=auth_headers,
        json={"title": "Budget carry", "client_id": cid,
              "items": [{"description": "Build", "quantity": 1, "unit_price": 7500}]},
    ).json()
    client.post(f"/api/v1/quotes/{q['id']}/accept", headers=auth_headers)
    project = client.post(f"/api/v1/quotes/{q['id']}/convert", headers=auth_headers).json()
    assert float(project["budget"]) == 7500
    detail = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers).json()
    assert float(detail["budget"]) == 7500


def test_project_change_detaches_task_from_board(client, auth_headers):
    cid = _make_client(client, auth_headers)
    p1 = client.post("/api/v1/projects", headers=auth_headers, json={"client_id": cid, "name": "P1", "status": "active"}).json()
    p2 = client.post("/api/v1/projects", headers=auth_headers, json={"client_id": cid, "name": "P2", "status": "active"}).json()
    board = client.post("/api/v1/boards", headers=auth_headers, json={"project_id": p1["id"], "name": "B1"}).json()
    task = client.post("/api/v1/tasks", headers=auth_headers,
                       json={"title": "movable", "project_id": p1["id"], "board_id": board["id"]}).json()
    assert task["board_id"] == board["id"]
    moved = client.patch(f"/api/v1/tasks/{task['id']}", headers=auth_headers, json={"project_id": p2["id"]}).json()
    assert moved["project_id"] == p2["id"]
    assert moved["board_id"] is None
