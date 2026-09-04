"""Analytics tests. Overview requires analytics:read or dashboard:read. Dashboard is visible to all authenticated users (filtered by role)."""


def test_analytics_overview_unauthorized(client):
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 401


def test_analytics_overview_admin(client, auth_headers):
    resp = client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clients" in data
    assert "active_projects" in data
    assert "tasks_todo" in data
    assert "tasks_in_progress" in data
    assert "tasks_done" in data
    assert "revenue_total" in data
    assert "outstanding_total" in data
    assert isinstance(data["total_clients"], int)
    assert isinstance(data["active_projects"], int)


def test_analytics_overview_employee_finance_zeroed(client, employee_headers):
    """Employee has dashboard:read so overview loads, but without finance:read all finance figures are zeroed."""
    resp = client.get("/api/v1/analytics/overview", headers=employee_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["revenue_total"]) == 0
    assert float(data["outstanding_total"]) == 0
    assert float(data["revenue_this_month"]) == 0
    assert data["expenses_this_month"] is None  # expenses:read required, stricter than finance


def test_overview_includes_qa_and_business_metrics(client, auth_headers):
    data = client.get("/api/v1/analytics/overview", headers=auth_headers).json()
    for key in ("tasks_review", "tasks_qa_failed", "hours_this_month", "billable_hours_this_month",
                "unbilled_value", "quote_pipeline_value", "quote_win_rate", "quotes_open"):
        assert key in data
    assert isinstance(data["tasks_review"], int)


def test_dashboard_tasks_by_status_has_all_pipeline_states(client, auth_headers):
    data = client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()
    statuses = {s["status"] for s in data["tasks_by_status"]}
    assert {"todo", "in_progress", "review", "qa_failed", "done"} <= statuses


def test_employee_gets_no_commercial_metrics(client, employee_headers):
    data = client.get("/api/v1/analytics/dashboard", headers=employee_headers).json()
    assert data["quote_pipeline_value"] is None  # no quotes:read
    assert data["unbilled_value"] is None  # no finance:read
    # But their own hours are visible
    assert "hours_this_month" in data


def test_dashboard_unauthorized(client):
    resp = client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 401


def test_dashboard_admin(client, auth_headers):
    """Dashboard is available to all authenticated users; admin sees full metrics."""
    resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clients" in data
    assert "active_projects" in data
    assert "total_users" in data
    assert "tasks_todo" in data
    assert "tasks_by_status" in data
    assert "revenue_this_month" in data
    assert "expenses_this_month" in data


def test_dashboard_employee(client, employee_headers):
    """Employee can load dashboard; sees only personal/assigned data (filtered in response)."""
    resp = client.get("/api/v1/analytics/dashboard", headers=employee_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "tasks_todo" in data
    assert "tasks_by_status" in data
    assert "total_users" in data
    # Employee has no clients/expenses/revenue scope
    assert data.get("total_clients") == 0
    assert data.get("active_projects") == 0


def test_manager_cannot_see_expenses_figure(client, manager_headers, auth_headers):
    """Managers have finance:read (invoices) but not expenses:read - expenses stay hidden."""
    data = client.get("/api/v1/analytics/dashboard", headers=manager_headers).json()
    assert data["expenses_this_month"] is None
    # Revenue figures still visible to managers
    assert data["revenue_this_month"] is not None
    # Admin still sees expenses
    assert client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()["expenses_this_month"] is not None


def test_qa_dashboard_shows_review_queue(client, auth_headers, qa_headers, employee_headers):
    import uuid as _uuid
    # Project + board with QA as member; one task in review, one qa_failed
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"QAOv {_uuid.uuid4().hex[:6]}"})
    p = client.post("/api/v1/projects", headers=auth_headers,
                    json={"client_id": c.json()["id"], "name": f"QAOv P {_uuid.uuid4().hex[:6]}", "status": "active"}).json()
    users = client.get("/api/v1/users", headers=auth_headers).json()
    qa_id = next(u["id"] for u in users if u["email"] == "qa@test.com")
    b = client.post("/api/v1/boards", headers=auth_headers,
                    json={"project_id": p["id"], "name": "QAOv Board", "member_ids": [qa_id]}).json()
    t = client.post("/api/v1/tasks", headers=auth_headers,
                    json={"title": "review me", "project_id": p["id"], "board_id": b["id"]}).json()
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "in_progress"})
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "review"})

    qa_dash = client.get("/api/v1/analytics/dashboard", headers=qa_headers).json()
    assert qa_dash["qa_review_queue"] is not None and qa_dash["qa_review_queue"] >= 1
    assert qa_dash["qa_failed_awaiting"] is not None

    # Employees (no qa_approve) get no QA tiles
    emp_dash = client.get("/api/v1/analytics/dashboard", headers=employee_headers).json()
    assert emp_dash["qa_review_queue"] is None
    assert emp_dash["qa_failed_awaiting"] is None


def test_client_reported_issue_counted(client, auth_headers):
    import uuid as _uuid
    from tests.conftest import _get_role_id
    # Client + portal user reports an issue
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"CROv {_uuid.uuid4().hex[:6]}"})
    p = client.post("/api/v1/projects", headers=auth_headers,
                    json={"client_id": c.json()["id"], "name": f"CROv P {_uuid.uuid4().hex[:6]}", "status": "active"}).json()
    role_id = _get_role_id(client, auth_headers, "client")
    email = f"crov-{_uuid.uuid4().hex[:8]}@clientmail.com"
    client.post("/api/v1/users", headers=auth_headers,
                json={"email": email, "password": "crovpass1", "role_ids": [role_id], "client_id": c.json()["id"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "crovpass1"})
    ph = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(f"/api/v1/portal/projects/{p['id']}/issues", headers=ph, json={"title": "broken", "severity": "high"})

    before = client.get("/api/v1/analytics/dashboard", headers=auth_headers).json()
    assert before["client_reported_open"] >= 1
