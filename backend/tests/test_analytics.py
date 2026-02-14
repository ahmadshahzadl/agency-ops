def test_analytics_unauthorized(client):
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 401


def test_analytics_overview(client, auth_headers):
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
