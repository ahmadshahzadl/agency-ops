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
    assert float(data["expenses_this_month"]) == 0


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
