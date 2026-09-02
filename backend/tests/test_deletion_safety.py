"""Deletion safety: guards against destroying billing history, deleted-client
zombies, soft-delete leakage, and orphaned attachments."""
import io
import uuid
from datetime import date

from tests.conftest import _get_role_id

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _make_client_project(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Del Client {uuid.uuid4().hex[:6]}"})
    p = client.post(
        "/api/v1/projects", headers=auth_headers,
        json={"client_id": c.json()["id"], "name": f"Del Project {uuid.uuid4().hex[:6]}", "status": "active"},
    )
    return c.json()["id"], p.json()["id"]


def test_user_with_time_entries_cannot_be_hard_deleted(client, auth_headers):
    _, pid = _make_client_project(client, auth_headers)
    email = f"deltest-{uuid.uuid4().hex[:8]}@test.com"
    role_id = _get_role_id(client, auth_headers, "employee")
    u = client.post(
        "/api/v1/users", headers=auth_headers,
        json={"email": email, "password": "delpass123", "full_name": "Del Test", "role_ids": [role_id]},
    ).json()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "delpass123"})
    their = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client.post(
        "/api/v1/time-entries", headers=their,
        json={"project_id": pid, "work_date": str(date.today()), "hours": 2},
    )
    assert r.status_code == 201

    resp = client.delete(f"/api/v1/users/{u['id']}", headers=auth_headers)
    assert resp.status_code == 400
    assert "deactivate" in resp.json()["detail"].lower()
    # Deactivation still works
    assert client.patch(f"/api/v1/users/{u['id']}", headers=auth_headers, json={"is_active": False}).status_code == 200


def test_client_with_active_projects_cannot_be_deleted(client, auth_headers):
    cid, pid = _make_client_project(client, auth_headers)
    r = client.delete(f"/api/v1/clients/{cid}", headers=auth_headers)
    assert r.status_code == 400
    assert "project" in r.json()["detail"].lower()
    # After deleting the project, the client can go
    assert client.delete(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/v1/clients/{cid}", headers=auth_headers).status_code == 204


def test_no_new_work_for_deleted_client(client, auth_headers):
    cid, pid = _make_client_project(client, auth_headers)
    client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
    client.delete(f"/api/v1/clients/{cid}", headers=auth_headers)
    # New project blocked
    r = client.post("/api/v1/projects", headers=auth_headers, json={"client_id": cid, "name": "zombie", "status": "active"})
    assert r.status_code == 404
    # New invoice blocked
    r = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": cid, "number": f"INV-Z-{uuid.uuid4().hex[:8]}", "amount": 10, "currency": "USD", "status": "draft"},
    )
    assert r.status_code == 400
    # Quote conversion blocked
    q = client.post(
        "/api/v1/quotes", headers=auth_headers,
        json={"title": "zombie quote", "client_id": cid, "items": [{"description": "x", "quantity": 1, "unit_price": 100}]},
    )
    # (quote creation against deleted client is itself blocked by _validate_target)
    assert q.status_code == 404


def test_soft_deleted_project_hides_time_and_boards(client, auth_headers):
    _, pid = _make_client_project(client, auth_headers)
    b = client.post("/api/v1/boards", headers=auth_headers, json={"project_id": pid, "name": "Del Board"}).json()
    client.post(
        "/api/v1/time-entries", headers=auth_headers,
        json={"project_id": pid, "work_date": str(date.today()), "hours": 3},
    )
    assert client.delete(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 204

    entries = client.get(f"/api/v1/time-entries?project_id={pid}", headers=auth_headers).json()
    assert entries == []
    summary = client.get(f"/api/v1/time-entries/summary?project_id={pid}", headers=auth_headers).json()
    assert float(summary["total_hours"]) == 0
    boards = client.get(f"/api/v1/boards?project_id={pid}", headers=auth_headers).json()
    assert boards == []
    assert client.get(f"/api/v1/boards/{b['id']}", headers=auth_headers).status_code == 404


def test_task_delete_purges_attachments(client, auth_headers):
    t = client.post("/api/v1/tasks", headers=auth_headers, json={"title": f"Purge {uuid.uuid4().hex[:6]}"}).json()
    up = client.post(
        "/api/v1/attachments", headers=auth_headers,
        data={"entity_type": "task", "entity_id": t["id"]},
        files={"file": ("evidence.png", io.BytesIO(PNG), "image/png")},
    )
    assert up.status_code == 201
    att_id = up.json()["id"]
    assert client.delete(f"/api/v1/tasks/{t['id']}", headers=auth_headers).status_code == 204
    # Attachment gone with its parent
    assert client.get(f"/api/v1/attachments/{att_id}/download", headers=auth_headers).status_code == 404
