"""Pytest fixtures for API tests. Requires DB to be migrated and seed_db.py run (admin@example.com / admin123)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient):
    """Login as admin and return headers with Bearer token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_role_id(client: TestClient, auth_headers: dict, role_name: str) -> str | None:
    """Get role id by name. Requires admin auth."""
    resp = client.get("/api/v1/roles", headers=auth_headers)
    if resp.status_code != 200:
        return None
    for r in resp.json():
        if r.get("name") == role_name:
            return r["id"]
    return None


def _ensure_user_and_login(client: TestClient, auth_headers: dict, email: str, password: str, role_name: str, full_name: str):
    """Create user with role if not exists, then login. Returns Bearer headers or None if role missing."""
    role_id = _get_role_id(client, auth_headers, role_name)
    if not role_id:
        return None
    create = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role_ids": [role_id],
        },
    )
    if create.status_code not in (200, 201) and create.status_code != 400:
        return None
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if login.status_code != 200:
        return None
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def manager_headers(client: TestClient, auth_headers: dict):
    """Headers for a user with manager role (team-scoped access; no expenses; view announcements)."""
    h = _ensure_user_and_login(
        client, auth_headers,
        "manager@test.com", "test123", "manager", "Test Manager",
    )
    if h is None:
        pytest.skip("Role 'manager' not found or could not create manager user - run seed_db.py")
    return h


@pytest.fixture
def employee_headers(client: TestClient, auth_headers: dict):
    """Headers for a user with employee role (assigned tasks/projects only; no clients, finance, expenses, reports)."""
    h = _ensure_user_and_login(
        client, auth_headers,
        "employee@test.com", "test123", "employee", "Test Employee",
    )
    if h is None:
        pytest.skip("Role 'employee' not found or could not create employee user - run seed_db.py")
    return h
