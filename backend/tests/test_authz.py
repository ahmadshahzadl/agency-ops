"""Object-level authorization regression tests: notes must not leak entities the
caller cannot access through the entity's own API, and targeted announcements
must only be visible to their targets."""
import uuid


def _make_client_and_invoice(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "Authz Test Client"})
    assert c_resp.status_code == 201
    client_id = c_resp.json()["id"]
    resp = client.post(
        "/api/v1/invoices",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "number": f"INV-AUTHZ-{uuid.uuid4().hex[:8]}",
            "amount": 500,
            "currency": "USD",
            "status": "draft",
        },
    )
    assert resp.status_code == 201
    return client_id, resp.json()["id"]


def test_employee_cannot_read_invoice_notes(client, auth_headers, employee_headers):
    """Employee has notes:read but no finance scope; invoice notes must 404, not leak."""
    _, invoice_id = _make_client_and_invoice(client, auth_headers)
    admin_note = client.post(
        "/api/v1/notes",
        headers=auth_headers,
        json={"entity_type": "invoice", "entity_id": invoice_id, "content": "secret finance note", "is_private": False},
    )
    assert admin_note.status_code == 201
    resp = client.get(
        f"/api/v1/notes?entity_type=invoice&entity_id={invoice_id}",
        headers=employee_headers,
    )
    assert resp.status_code == 404


def test_employee_cannot_attach_note_to_unscoped_client(client, auth_headers, employee_headers):
    """Employee has notes:write but no access to the client entity -> create must 404."""
    client_id, _ = _make_client_and_invoice(client, auth_headers)
    resp = client.post(
        "/api/v1/notes",
        headers=employee_headers,
        json={"entity_type": "client", "entity_id": client_id, "content": "should not be allowed", "is_private": False},
    )
    assert resp.status_code == 404


def test_admin_can_still_read_invoice_notes(client, auth_headers):
    _, invoice_id = _make_client_and_invoice(client, auth_headers)
    note = client.post(
        "/api/v1/notes",
        headers=auth_headers,
        json={"entity_type": "invoice", "entity_id": invoice_id, "content": "admin note", "is_private": False},
    )
    assert note.status_code == 201
    resp = client.get(
        f"/api/v1/notes?entity_type=invoice&entity_id={invoice_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert any(n["content"] == "admin note" for n in resp.json())


def test_targeted_announcement_hidden_from_non_target(client, auth_headers, employee_headers, manager_headers):
    """Announcement targeted at the manager must not be listed or fetched by the employee."""
    users = client.get("/api/v1/users", headers=auth_headers).json()
    manager_id = next(u["id"] for u in users if u["email"] == "manager@test.com")
    ann = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": f"Targeted {uuid.uuid4().hex[:6]}",
            "body": "for manager only",
            "target_type": "users",
            "target_user_ids": [manager_id],
        },
    )
    assert ann.status_code == 201
    ann_id = ann.json()["id"]

    listed_for_employee = client.get("/api/v1/announcements", headers=employee_headers).json()
    assert all(a["id"] != ann_id for a in listed_for_employee)
    assert client.get(f"/api/v1/announcements/{ann_id}", headers=employee_headers).status_code == 404

    listed_for_manager = client.get("/api/v1/announcements?limit=100", headers=manager_headers).json()
    assert any(a["id"] == ann_id for a in listed_for_manager)
    assert client.get(f"/api/v1/announcements/{ann_id}", headers=manager_headers).status_code == 200
