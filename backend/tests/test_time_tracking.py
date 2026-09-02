"""Time tracking and invoice generation: scoping, validation, billing lifecycle."""
import uuid
from datetime import date


def _setup_project(client, auth_headers, hourly_rate=None):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Time Client {uuid.uuid4().hex[:6]}"})
    body = {"client_id": c.json()["id"], "name": f"Time Project {uuid.uuid4().hex[:6]}", "status": "active"}
    if hourly_rate is not None:
        body["hourly_rate"] = hourly_rate
    p = client.post("/api/v1/projects", headers=auth_headers, json=body)
    assert p.status_code == 201
    return p.json()["id"]


def _log(client, headers, project_id, hours, **extra):
    return client.post(
        "/api/v1/time-entries", headers=headers,
        json={"project_id": project_id, "work_date": str(date.today()), "hours": hours, **extra},
    )


def test_log_and_list_own_time(client, auth_headers, employee_headers):
    pid = _setup_project(client, auth_headers)
    r = _log(client, employee_headers, pid, 2.5, description="API work")
    assert r.status_code == 201, r.text
    entry = r.json()
    assert float(entry["hours"]) == 2.5
    assert entry["project_name"]

    listed = client.get("/api/v1/time-entries", headers=employee_headers).json()
    assert any(e["id"] == entry["id"] for e in listed)
    # Employee sees only own entries
    assert all(e["user_id"] == entry["user_id"] for e in listed)


def test_hours_validation(client, auth_headers):
    pid = _setup_project(client, auth_headers)
    assert _log(client, auth_headers, pid, 0).status_code == 400
    assert _log(client, auth_headers, pid, 25).status_code == 400


def test_employee_cannot_log_for_others(client, auth_headers, employee_headers):
    pid = _setup_project(client, auth_headers)
    users = client.get("/api/v1/users", headers=auth_headers).json()
    admin_id = next(u["id"] for u in users if u["email"] == "admin@example.com")
    r = _log(client, employee_headers, pid, 1, user_id=admin_id)
    assert r.status_code == 403


def test_invoice_from_time_lifecycle(client, auth_headers):
    pid = _setup_project(client, auth_headers, hourly_rate=100)
    assert _log(client, auth_headers, pid, 3).status_code == 201
    assert _log(client, auth_headers, pid, 2, billable=False).status_code == 201  # not billed
    assert _log(client, auth_headers, pid, 1.5, hourly_rate=200).status_code == 201  # entry rate wins

    summary = client.get(f"/api/v1/time-entries/summary?project_id={pid}", headers=auth_headers).json()
    assert float(summary["total_hours"]) == 6.5
    assert float(summary["unbilled_billable_hours"]) == 4.5
    assert float(summary["unbilled_amount"]) == 3 * 100 + 1.5 * 200

    r = client.post("/api/v1/invoices/from-time", headers=auth_headers, json={"project_id": pid})
    assert r.status_code == 201, r.text
    invoice = r.json()
    assert float(invoice["amount"]) == 600.0
    assert invoice["status"] == "draft"

    # Entries linked and locked
    linked = client.get(f"/api/v1/invoices/{invoice['id']}/time-entries", headers=auth_headers).json()
    assert len(linked) == 2
    locked_id = linked[0]["id"]
    assert client.patch(f"/api/v1/time-entries/{locked_id}", headers=auth_headers, json={"hours": 9}).status_code == 400
    assert client.delete(f"/api/v1/time-entries/{locked_id}", headers=auth_headers).status_code == 400

    # Nothing left to bill
    assert client.post("/api/v1/invoices/from-time", headers=auth_headers, json={"project_id": pid}).status_code == 400

    # Deleting the invoice frees the entries
    assert client.delete(f"/api/v1/invoices/{invoice['id']}", headers=auth_headers).status_code == 204
    entries = client.get(f"/api/v1/time-entries?project_id={pid}&unbilled=true", headers=auth_headers).json()
    assert len([e for e in entries if e["billable"]]) == 2


def test_invoice_from_time_requires_rate(client, auth_headers):
    pid = _setup_project(client, auth_headers)  # no project rate
    assert _log(client, auth_headers, pid, 2).status_code == 201
    r = client.post("/api/v1/invoices/from-time", headers=auth_headers, json={"project_id": pid})
    assert r.status_code == 400
    # Explicit rate at generation time works
    r = client.post("/api/v1/invoices/from-time", headers=auth_headers, json={"project_id": pid, "hourly_rate": 50})
    assert r.status_code == 201
    assert float(r.json()["amount"]) == 100.0


def test_employee_cannot_generate_invoice(client, auth_headers, employee_headers):
    pid = _setup_project(client, auth_headers, hourly_rate=100)
    _log(client, auth_headers, pid, 1)
    r = client.post("/api/v1/invoices/from-time", headers=employee_headers, json={"project_id": pid})
    assert r.status_code == 403
