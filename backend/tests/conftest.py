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
