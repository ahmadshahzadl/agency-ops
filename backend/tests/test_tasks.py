def test_list_tasks_unauthorized(client):
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 401


def test_list_tasks(client, auth_headers):
    resp = client.get("/api/v1/tasks", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_task(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    p_resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": c_resp.json()["id"], "name": "P"},
    )
    project_id = p_resp.json()["id"]
    resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "title": "New task",
            "status": "todo",
            "priority": "high",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New task"
    assert data["project_id"] == project_id


def test_update_task(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    p_resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": c_resp.json()["id"], "name": "P"},
    )
    t_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"project_id": p_resp.json()["id"], "title": "T", "status": "todo"},
    )
    task_id = t_resp.json()["id"]
    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "done", "title": "Done task"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["title"] == "Done task"


def test_delete_task(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    p_resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": c_resp.json()["id"], "name": "P"},
    )
    t_resp = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"project_id": p_resp.json()["id"], "title": "To delete"},
    )
    task_id = t_resp.json()["id"]
    resp = client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert resp.status_code == 204
