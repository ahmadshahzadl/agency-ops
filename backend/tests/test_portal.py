"""Client portal: lockout from the internal API, strict client scoping,
quote self-service, and issue reporting."""
import uuid

from tests.conftest import _get_role_id


def _make_client_record(client, auth_headers, email=None):
    body = {"name": f"Portal Client {uuid.uuid4().hex[:6]}"}
    if email:
        body["contact_email"] = email
    return client.post("/api/v1/clients", headers=auth_headers, json=body).json()["id"]


def _make_portal_user(client, auth_headers, client_id):
    email = f"portal-{uuid.uuid4().hex[:8]}@clientmail.com"
    role_id = _get_role_id(client, auth_headers, "client")
    assert role_id, "client role missing - run seed_db.py"
    r = client.post(
        "/api/v1/users", headers=auth_headers,
        json={"email": email, "password": "portalpass1", "full_name": "Portal User",
              "role_ids": [role_id], "client_id": client_id},
    )
    assert r.status_code in (200, 201), r.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "portalpass1"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _make_project(client, auth_headers, client_id, name=None):
    return client.post(
        "/api/v1/projects", headers=auth_headers,
        json={"client_id": client_id, "name": name or f"Portal Proj {uuid.uuid4().hex[:6]}", "status": "active"},
    ).json()


def test_portal_user_locked_out_of_internal_api(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    headers = _make_portal_user(client, auth_headers, cid)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["is_client"] is True
    assert me["permissions"] == []
    # Permission-gated endpoints: 403
    for path in ("/api/v1/tasks", "/api/v1/clients", "/api/v1/invoices", "/api/v1/quotes", "/api/v1/time-entries", "/api/v1/boards"):
        assert client.get(path, headers=headers).status_code == 403, path
    # Login-only internal endpoints: also 403
    for path in ("/api/v1/messages/conversations", "/api/v1/analytics/dashboard", "/api/v1/projects/names", "/api/v1/teams/my"):
        assert client.get(path, headers=headers).status_code == 403, path


def test_staff_cannot_use_portal(client, auth_headers, employee_headers):
    assert client.get("/api/v1/portal/overview", headers=employee_headers).status_code == 403
    assert client.get("/api/v1/portal/overview", headers=auth_headers).status_code == 403


def test_portal_overview_and_project_scoping(client, auth_headers):
    cid_a = _make_client_record(client, auth_headers)
    cid_b = _make_client_record(client, auth_headers)
    proj_a = _make_project(client, auth_headers, cid_a, "Alpha Site")
    proj_b = _make_project(client, auth_headers, cid_b, "Beta Site")
    headers = _make_portal_user(client, auth_headers, cid_a)

    ov = client.get("/api/v1/portal/overview", headers=headers).json()
    names = [p["name"] for p in ov["projects"]]
    assert "Alpha Site" in names and "Beta Site" not in names

    assert client.get(f"/api/v1/portal/projects/{proj_a['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/portal/projects/{proj_b['id']}", headers=headers).status_code == 404


def test_portal_project_detail_sanitized(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    proj = _make_project(client, auth_headers, cid)
    t = client.post("/api/v1/tasks", headers=auth_headers, json={"title": "Internal work", "project_id": proj["id"]}).json()
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "in_progress"})
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "review"})
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "qa_failed", "qa_notes": "secret internal"})
    headers = _make_portal_user(client, auth_headers, cid)
    detail = client.get(f"/api/v1/portal/projects/{proj['id']}", headers=headers).json()
    task = detail["tasks"][0]
    assert task["status"] == "review"  # qa_failed masked
    assert set(task.keys()) == {"title", "status", "item_type", "due_date"}


def test_portal_invoices_hide_drafts_and_scope(client, auth_headers):
    cid_a = _make_client_record(client, auth_headers)
    cid_b = _make_client_record(client, auth_headers)
    inv_sent = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": cid_a, "number": f"INV-PA-{uuid.uuid4().hex[:8]}", "amount": 500, "currency": "USD", "status": "sent"}).json()
    client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": cid_a, "number": f"INV-PD-{uuid.uuid4().hex[:8]}", "amount": 100, "currency": "USD", "status": "draft"})
    inv_b = client.post("/api/v1/invoices", headers=auth_headers, json={
        "client_id": cid_b, "number": f"INV-PB-{uuid.uuid4().hex[:8]}", "amount": 900, "currency": "USD", "status": "sent"}).json()

    headers = _make_portal_user(client, auth_headers, cid_a)
    listed = client.get("/api/v1/portal/invoices", headers=headers).json()
    numbers = [i["number"] for i in listed]
    assert inv_sent["number"] in numbers
    assert all(not n.startswith("INV-PD") for n in numbers)  # draft hidden
    assert inv_b["number"] not in numbers

    assert client.get(f"/api/v1/portal/invoices/{inv_sent['id']}/pdf", headers=headers).status_code == 200
    assert client.get(f"/api/v1/portal/invoices/{inv_b['id']}/pdf", headers=headers).status_code == 404


def test_portal_quote_self_service(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    q = client.post("/api/v1/quotes", headers=auth_headers, json={
        "title": "Portal deal", "client_id": cid,
        "items": [{"description": "Build", "quantity": 1, "unit_price": 3000}]}).json()
    headers = _make_portal_user(client, auth_headers, cid)

    # Draft is invisible to the client
    assert client.get("/api/v1/portal/quotes", headers=headers).json() == []
    client.post(f"/api/v1/quotes/{q['id']}/send", headers=auth_headers)

    listed = client.get("/api/v1/portal/quotes", headers=headers).json()
    assert len(listed) == 1 and listed[0]["status"] == "sent"

    accepted = client.post(f"/api/v1/portal/quotes/{q['id']}/accept", headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    # Cannot decide twice
    assert client.post(f"/api/v1/portal/quotes/{q['id']}/decline", headers=headers).status_code == 400
    # Internal side sees the acceptance
    internal = client.get(f"/api/v1/quotes/{q['id']}", headers=auth_headers).json()
    assert internal["status"] == "accepted"


def test_portal_issue_report_creates_bug(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    proj = _make_project(client, auth_headers, cid)
    headers = _make_portal_user(client, auth_headers, cid)
    r = client.post(
        f"/api/v1/portal/projects/{proj['id']}/issues", headers=headers,
        json={"title": "Login button broken", "description": "Nothing happens", "steps_to_reproduce": "1. click login", "severity": "high"},
    )
    assert r.status_code == 201, r.text
    # Admin sees it as a bug task on the project
    tasks = client.get(f"/api/v1/tasks?project_id={proj['id']}", headers=auth_headers).json()
    bug = next(t for t in tasks if t["title"] == "Login button broken")
    assert bug["item_type"] == "bug"
    assert bug["severity"] == "high"
    assert bug["status"] == "todo"
