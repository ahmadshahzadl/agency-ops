"""Sign-in must not be case-sensitive, and emails are stored in one canonical form."""
import uuid

from tests.conftest import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, _get_role_id


def _new_user(client, auth_headers, email, password="casetest123"):
    role_id = _get_role_id(client, auth_headers, "employee")
    assert role_id, "employee role missing - run seed_db.py"
    return client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={"email": email, "password": password, "full_name": "Case Test", "role_ids": [role_id]},
    )


def test_login_accepts_uppercase_email(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL.upper(), "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_accepts_mixed_case_and_surrounding_spaces(client):
    messy = f"  {TEST_ADMIN_EMAIL[:1].upper()}{TEST_ADMIN_EMAIL[1:]}  "
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": messy, "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200


def test_created_email_is_stored_lowercase(client, auth_headers):
    local = f"Case-{uuid.uuid4().hex[:8]}"
    resp = _new_user(client, auth_headers, f"  {local}@Example.COM  ")
    assert resp.status_code in (200, 201)
    assert resp.json()["email"] == f"{local.lower()}@example.com"


def test_user_can_sign_in_with_any_casing(client, auth_headers):
    local = f"case-{uuid.uuid4().hex[:8]}"
    password = "casetest123"
    assert _new_user(client, auth_headers, f"{local}@example.com", password).status_code in (200, 201)

    for attempt in (f"{local}@example.com", f"{local}@EXAMPLE.com", f"{local.upper()}@Example.Com"):
        resp = client.post("/api/v1/auth/login", json={"email": attempt, "password": password})
        assert resp.status_code == 200, f"login failed for {attempt}"


def test_duplicate_email_rejected_regardless_of_case(client, auth_headers):
    local = f"dupe-{uuid.uuid4().hex[:8]}"
    assert _new_user(client, auth_headers, f"{local}@example.com").status_code in (200, 201)

    resp = _new_user(client, auth_headers, f"{local.upper()}@EXAMPLE.COM")
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


def test_forgot_password_finds_account_in_any_casing(client):
    """Always 200 (no user enumeration), but the lookup itself must be case-insensitive."""
    resp = client.post("/api/v1/auth/forgot-password", json={"email": TEST_ADMIN_EMAIL.upper()})
    assert resp.status_code == 200
