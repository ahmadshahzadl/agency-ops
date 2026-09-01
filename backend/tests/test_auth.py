from tests.conftest import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD


def test_login_success(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_invalid_email(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 401


def test_login_rate_limited_after_repeated_failures(client):
    """After max_failures wrong attempts on one email, login returns 429 until the window passes."""
    email = "ratelimit-target@example.com"  # nonexistent user; limiter keys per email
    for _ in range(10):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong"},
        )
        assert resp.status_code == 401
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong"},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_me_unauthorized(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_success(client, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == TEST_ADMIN_EMAIL
    assert "permissions" in data
    assert "admin:all" in data["permissions"]


def test_refresh_token(client, auth_headers):
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    refresh_token = login_resp.json()["refresh_token"]
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_activity_websocket_rejects_missing_token(client):
    """The activity socket must not accept unauthenticated connections."""
    from starlette.websockets import WebSocketDisconnect
    import pytest

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/activity"):
            pass
    assert exc_info.value.code == 4001


def test_activity_websocket_accepts_valid_token(client, auth_headers):
    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/api/v1/ws/activity?token={token}"):
        pass
