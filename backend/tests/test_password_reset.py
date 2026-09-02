"""Password reset flow: no user enumeration, single-use expiring tokens,
session revocation on reset, rate limiting."""
import uuid

import pytest

from app.services import email_service
from tests.conftest import _get_role_id


@pytest.fixture
def captured_reset(monkeypatch):
    """Capture the reset token instead of sending email."""
    captured = {}

    def fake_send(to, user_name, token):
        captured["to"] = to
        captured["token"] = token

    monkeypatch.setattr(email_service, "send_password_reset", fake_send)
    return captured


def _make_user(client, auth_headers, password="origpass123"):
    email = f"reset-{uuid.uuid4().hex[:10]}@test.com"
    role_id = _get_role_id(client, auth_headers, "employee")
    r = client.post(
        "/api/v1/users", headers=auth_headers,
        json={"email": email, "password": password, "full_name": "Reset Test", "role_ids": [role_id]},
    )
    assert r.status_code in (200, 201)
    return email, password


def test_forgot_password_no_enumeration(client):
    r = client.post("/api/v1/auth/forgot-password", json={"email": f"ghost-{uuid.uuid4().hex}@nowhere.com"})
    assert r.status_code == 200
    assert "message" in r.json()


def test_full_reset_flow_revokes_sessions(client, auth_headers, captured_reset):
    email, password = _make_user(client, auth_headers)
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    old_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    assert captured_reset["to"] == email
    token = captured_reset["token"]

    # Weak password rejected
    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "short"})
    assert r.status_code == 400

    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnewpass1"})
    assert r.status_code == 200

    # Old password dead, new works
    assert client.post("/api/v1/auth/login", json={"email": email, "password": password}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "brandnewpass1"}).status_code == 200

    # Pre-reset session revoked (token_version bumped)
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401

    # Token is single-use
    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "anotherpass1"})
    assert r.status_code == 400


def test_reset_with_garbage_token(client):
    r = client.post("/api/v1/auth/reset-password", json={"token": "garbage", "new_password": "validpass123"})
    assert r.status_code == 400


def test_forgot_password_rate_limited(client, auth_headers, captured_reset):
    email, _ = _make_user(client, auth_headers)
    for _ in range(3):
        assert client.post("/api/v1/auth/forgot-password", json={"email": email}).status_code == 200
    captured_reset.clear()
    # 4th request still returns 200 (no signal to attackers) but sends nothing
    assert client.post("/api/v1/auth/forgot-password", json={"email": email}).status_code == 200
    assert "token" not in captured_reset
