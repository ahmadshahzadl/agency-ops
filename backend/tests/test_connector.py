"""Claude connector (remote MCP): OAuth flow, the route allowlist, and that the app's own rules
(RBAC, QA gate, audit trail) still apply to everything Claude does."""
import base64
import hashlib
import secrets
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

from app.config import get_settings
from app.core import mcp_policy
from app.database import SessionLocal
from app.main import app
from app.models import ActivityLog
from tests.test_qa_boards import _make_board, _make_task, _setup_project

REDIRECT = "https://claude.ai/api/mcp/auth_callback"


@pytest.fixture(autouse=True)
def connector_on(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "mcp_enabled", True)
    monkeypatch.setattr(s, "mcp_public_url", "https://app.example.com")
    monkeypatch.setattr(s, "mcp_allowed_emails", "")
    yield s


def _pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _register(client):
    r = client.post("/api/v1/oauth/register", json={"client_name": "Claude", "redirect_uris": [REDIRECT]})
    assert r.status_code == 201, r.text
    return r.json()["client_id"]


def _connect(client, web_headers):
    """Run the whole authorization-code + PKCE flow; return (client_id, token response)."""
    client_id = _register(client)
    verifier, challenge = _pkce()
    q = {"client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
         "code_challenge": challenge, "code_challenge_method": "S256", "state": "xyz", "scope": "fuorix"}
    r = client.get("/api/v1/oauth/authorize", params=q, follow_redirects=False)
    assert r.status_code == 302 and "/oauth/consent?" in r.headers["location"]
    r = client.post("/api/v1/oauth/authorize/approve", headers=web_headers, json={**q, "approve": True})
    assert r.status_code == 200, r.text
    back = urlparse(r.json()["redirect_to"])
    params = parse_qs(back.query)
    assert back.geturl().startswith(REDIRECT) and params["state"] == ["xyz"]
    r = client.post("/api/v1/oauth/token", data={
        "grant_type": "authorization_code", "code": params["code"][0], "redirect_uri": REDIRECT,
        "client_id": client_id, "code_verifier": verifier,
    })
    assert r.status_code == 200, r.text
    return client_id, r.json()


def _bearer(tok):
    return {"Authorization": f"Bearer {tok['access_token']}"}


# ---------- the allowlist itself ----------

def test_every_allowlisted_route_exists_and_none_is_dangerous():
    real = {(m, r.path) for r in app.routes for m in (getattr(r, "methods", None) or set())}
    missing = [e for e in mcp_policy.ALLOWED if e not in real]
    assert not missing, f"allowlist entries with no matching route: {missing}"
    forbidden_words = ("/send", "/issue", "/countersign", "/mark-signed", "/terminate", "/sign-link",
                       "/accept", "/reject", "/reveal", "/credentials", "/expenses", "/payroll",
                       "/recurring-expenses", "/messages", "/roles", "/integrations", "/attendance",
                       "/payments", "/from-time", "/invoice")
    for method, path in mcp_policy.ALLOWED:
        assert method != "DELETE", path
        if method != "GET":
            assert not any(w in path for w in forbidden_words), (method, path)
            assert "/invoices" not in path and "/content" not in path, (method, path)
    assert ("GET", "/api/v1/invoices") in mcp_policy.ALLOWED  # owner decision: invoices readable


# ---------- discovery / registration ----------

def test_metadata_and_disabled(client, connector_on, monkeypatch):
    md = client.get("/.well-known/oauth-authorization-server").json()
    assert md["issuer"] == "https://app.example.com"
    assert md["code_challenge_methods_supported"] == ["S256"]
    monkeypatch.setattr(connector_on, "mcp_enabled", False)
    assert client.get("/.well-known/oauth-authorization-server").status_code == 404
    assert client.post("/api/v1/oauth/register", json={"redirect_uris": [REDIRECT]}).status_code == 404


def test_register_rejects_foreign_redirect_and_authorize_never_redirects_there(client):
    r = client.post("/api/v1/oauth/register", json={"redirect_uris": ["https://evil.example/cb"]})
    assert r.status_code == 400 and r.json()["error"] == "invalid_redirect_uri"
    cid = _register(client)
    r = client.get("/api/v1/oauth/authorize", params={
        "client_id": cid, "redirect_uri": "https://evil.example/cb", "response_type": "code",
        "code_challenge": "x", "code_challenge_method": "S256"}, follow_redirects=False)
    assert r.status_code == 400


# ---------- token exchange ----------

def test_code_is_single_use_and_pkce_checked(client, auth_headers):
    cid = _register(client)
    verifier, challenge = _pkce()
    q = {"client_id": cid, "redirect_uri": REDIRECT, "code_challenge": challenge, "code_challenge_method": "S256", "approve": True}
    code = parse_qs(urlparse(client.post("/api/v1/oauth/authorize/approve", headers=auth_headers, json=q).json()["redirect_to"]).query)["code"][0]
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "client_id": cid}
    assert client.post("/api/v1/oauth/token", data={**form, "code_verifier": "wrong"}).json()["error"] == "invalid_grant"
    assert client.post("/api/v1/oauth/token", data={**form, "code_verifier": verifier}).status_code == 200
    assert client.post("/api/v1/oauth/token", data={**form, "code_verifier": verifier}).json()["error"] == "invalid_grant"


def test_refresh_rotates(client, auth_headers):
    cid, tok = _connect(client, auth_headers)
    r = client.post("/api/v1/oauth/token", data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": cid})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != tok["refresh_token"]
    old = client.post("/api/v1/oauth/token", data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": cid})
    assert old.json()["error"] == "invalid_grant"
    assert client.get("/api/v1/leads", headers=_bearer(new)).status_code == 200


def test_denied_consent_returns_access_denied(client, auth_headers):
    cid = _register(client)
    r = client.post("/api/v1/oauth/authorize/approve", headers=auth_headers, json={
        "client_id": cid, "redirect_uri": REDIRECT, "state": "s", "approve": False})
    assert "error=access_denied" in r.json()["redirect_to"]


# ---------- what a connector token can and cannot do ----------

def test_connector_token_reads_allowed_routes_and_nothing_else(client, auth_headers):
    _, tok = _connect(client, auth_headers)
    h = _bearer(tok)
    for path in ("/api/v1/leads", "/api/v1/projects", "/api/v1/tasks", "/api/v1/quotes",
                 "/api/v1/agreements", "/api/v1/letters", "/api/v1/boards", "/api/v1/invoices",
                 "/api/v1/oauth/connector/whoami"):
        assert client.get(path, headers=h).status_code == 200, path
    for method, path in (("GET", "/api/v1/credentials"), ("GET", "/api/v1/expenses"), ("GET", "/api/v1/payroll"),
                         ("GET", "/api/v1/messages"), ("GET", "/api/v1/users"), ("GET", "/api/v1/roles"),
                         ("POST", "/api/v1/invoices"), ("POST", "/api/v1/auth/logout"),
                         ("GET", "/api/v1/oauth/grants"), ("POST", "/api/v1/oauth/authorize/approve")):
        r = client.request(method, path, headers=h, json={})
        assert r.status_code == 403 and "Claude connector" in r.json()["detail"], (method, path, r.status_code)


def test_connector_cannot_delete_or_send(client, auth_headers):
    _, tok = _connect(client, auth_headers)
    h = _bearer(tok)
    lead = client.post("/api/v1/leads", headers=h, json={"company_name": "Via Claude Ltd", "contact_name": "X"})
    assert lead.status_code in (200, 201), lead.text
    lead_id = lead.json()["id"]
    assert client.delete(f"/api/v1/leads/{lead_id}", headers=h).status_code == 403
    q = client.post("/api/v1/quotes", headers=h, json={"title": "Draft by Claude", "lead_id": lead_id, "items": [{"description": "Work", "quantity": 1, "unit_price": 100}]})
    assert q.status_code in (200, 201), q.text
    for action in ("send", "accept", "reject", "invoice"):
        assert client.post(f"/api/v1/quotes/{q.json()['id']}/{action}", headers=h, json={}).status_code == 403, action
    # The same actions still work for the human in the app
    assert client.get(f"/api/v1/quotes/{q.json()['id']}", headers=auth_headers).json()["status"] == "draft"


def test_writes_are_marked_via_claude_in_activity_log(client, auth_headers):
    _, tok = _connect(client, auth_headers)
    lead = client.post("/api/v1/leads", headers=_bearer(tok), json={"company_name": f"Audit {uuid.uuid4().hex[:6]}", "contact_name": "Y"}).json()
    db = SessionLocal()
    try:
        row = db.query(ActivityLog).filter(ActivityLog.entity_id == uuid.UUID(lead["id"])).order_by(ActivityLog.created_at.desc()).first()
        assert row is not None and "via Claude" in (row.details or "")
    finally:
        db.close()


def test_web_token_is_not_a_connector_token(client, auth_headers):
    assert client.get("/api/v1/oauth/connector/whoami", headers=auth_headers).status_code == 403


# ---------- the app's own rules still hold ----------

def test_rbac_still_applies_manager_cannot_read_invoices(client, auth_headers, manager_headers):
    _, tok = _connect(client, manager_headers)
    assert client.get("/api/v1/leads", headers=_bearer(tok)).status_code == 200
    assert client.get("/api/v1/invoices", headers=_bearer(tok)).status_code == 403  # no finance:read


def test_qa_gate_still_enforced_through_connector(client, auth_headers, employee_headers, qa_headers):
    project_id = _setup_project(client, auth_headers)
    board = _make_board(client, auth_headers, project_id, ["employee@test.com", "qa@test.com"])
    task = _make_task(client, auth_headers, project_id, board["id"], "employee@test.com")
    _, emp = _connect(client, employee_headers)
    for st in ("in_progress", "review"):
        assert client.patch(f"/api/v1/tasks/{task['id']}", headers=_bearer(emp), json={"status": st}).status_code == 200
    assert client.patch(f"/api/v1/tasks/{task['id']}", headers=_bearer(emp), json={"status": "done"}).status_code == 403
    _, qa = _connect(client, qa_headers)
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=_bearer(qa), json={"status": "done"})
    assert r.status_code == 200 and r.json()["status"] == "done"


# ---------- cutting it off ----------

def test_revoking_grant_cuts_off_access_and_refresh(client, auth_headers):
    cid, tok = _connect(client, auth_headers)
    grants = client.get("/api/v1/oauth/grants", headers=auth_headers).json()["grants"]
    assert grants
    for g in grants:
        assert client.post(f"/api/v1/oauth/grants/{g['id']}/revoke", headers=auth_headers).status_code == 204
    assert client.get("/api/v1/leads", headers=_bearer(tok)).status_code == 401
    r = client.post("/api/v1/oauth/token", data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": cid})
    assert r.json()["error"] == "invalid_grant"


def test_sign_out_everywhere_kills_connector(client, auth_headers, qa_headers):
    cid, tok = _connect(client, qa_headers)
    assert client.post("/api/v1/auth/logout", headers=qa_headers).status_code == 204
    assert client.get("/api/v1/tasks", headers=_bearer(tok)).status_code == 401
    r = client.post("/api/v1/oauth/token", data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": cid})
    assert r.json()["error"] == "invalid_grant"


def test_allowed_emails_restricts_who_can_connect(client, auth_headers, manager_headers, connector_on, monkeypatch):
    _, tok = _connect(client, manager_headers)
    monkeypatch.setattr(connector_on, "mcp_allowed_emails", "ahmad.shahzad@fuorix.com")
    # Existing connection stops working, and new approvals are refused
    assert client.get("/api/v1/leads", headers=_bearer(tok)).status_code == 401
    cid = _register(client)
    _, challenge = _pkce()
    r = client.post("/api/v1/oauth/authorize/approve", headers=manager_headers, json={
        "client_id": cid, "redirect_uri": REDIRECT, "code_challenge": challenge, "code_challenge_method": "S256", "approve": True})
    assert r.status_code == 403
    info = client.get("/api/v1/oauth/authorize/info", headers=manager_headers, params={"client_id": cid, "redirect_uri": REDIRECT}).json()
    assert info["blocked_reason"]


def test_trusted_client_id_url_accepted(client, auth_headers):
    """Client-ID metadata documents: Claude may use an https://claude.ai/... URL as client_id."""
    cid = "https://claude.ai/oauth/mcp-oauth-client-metadata"
    r = client.get("/api/v1/oauth/authorize/info", headers=auth_headers, params={"client_id": cid, "redirect_uri": REDIRECT})
    assert r.status_code == 200
    r = client.get("/api/v1/oauth/authorize/info", headers=auth_headers, params={"client_id": "https://evil.example/meta", "redirect_uri": REDIRECT})
    assert r.status_code == 400


def test_reconnecting_replaces_previous_connection(client, employee_headers):
    _, first = _connect(client, employee_headers)
    _, second = _connect(client, employee_headers)
    assert client.get("/api/v1/tasks", headers=_bearer(first)).status_code == 401
    assert client.get("/api/v1/tasks", headers=_bearer(second)).status_code == 200
    assert len(client.get("/api/v1/oauth/grants", headers=employee_headers).json()["grants"]) == 1
