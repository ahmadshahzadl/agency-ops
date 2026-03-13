"""Tests for announcements API. Admin can create/edit/delete; Manager and Employee can only view (announcements:read)."""
import pytest


def test_list_announcements_unauthorized(client):
    resp = client.get("/api/v1/announcements")
    assert resp.status_code == 401


def test_list_announcements_admin(client, auth_headers):
    resp = client.get("/api/v1/announcements", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_announcements_manager(client, manager_headers):
    """Manager has announcements:read -> can view list."""
    resp = client.get("/api/v1/announcements", headers=manager_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_announcements_employee(client, employee_headers):
    """Employee has announcements:read -> can view list."""
    resp = client.get("/api/v1/announcements", headers=employee_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_announcement_admin(client, auth_headers):
    resp = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": "Test announcement",
            "body": "Body text",
            "target_type": "all",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test announcement"
    assert data["body"] == "Body text"
    assert data["target_type"] == "all"


def test_create_announcement_manager_forbidden(client, manager_headers):
    """Manager has announcements:read only -> 403 on create."""
    resp = client.post(
        "/api/v1/announcements",
        headers=manager_headers,
        json={"title": "Manager post", "body": "No", "target_type": "all"},
    )
    assert resp.status_code == 403


def test_create_announcement_employee_forbidden(client, employee_headers):
    """Employee has announcements:read only -> 403 on create."""
    resp = client.post(
        "/api/v1/announcements",
        headers=employee_headers,
        json={"title": "Employee post", "body": "No", "target_type": "all"},
    )
    assert resp.status_code == 403


def test_get_announcement_employee(client, auth_headers, employee_headers):
    """Admin creates; employee can get by id (announcements:read)."""
    create = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={"title": "For get test", "body": "Content", "target_type": "all"},
    )
    assert create.status_code == 201
    ann_id = create.json()["id"]
    resp = client.get(f"/api/v1/announcements/{ann_id}", headers=employee_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "For get test"


def test_update_announcement_manager_forbidden(client, auth_headers, manager_headers):
    """Manager cannot update announcement."""
    create = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={"title": "To update", "body": "X", "target_type": "all"},
    )
    assert create.status_code == 201
    ann_id = create.json()["id"]
    resp = client.patch(
        f"/api/v1/announcements/{ann_id}",
        headers=manager_headers,
        json={"title": "Updated by manager"},
    )
    assert resp.status_code == 403


def test_delete_announcement_admin(client, auth_headers):
    create = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={"title": "To delete", "body": "X", "target_type": "all"},
    )
    assert create.status_code == 201
    ann_id = create.json()["id"]
    resp = client.delete(f"/api/v1/announcements/{ann_id}", headers=auth_headers)
    assert resp.status_code == 204
