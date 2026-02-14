def test_list_projects_unauthorized(client):
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 401


def test_list_projects(client, auth_headers):
    resp = client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_project(client, auth_headers):
    # Need a client first
    c_resp = client.post(
        "/api/v1/clients",
        headers=auth_headers,
        json={"name": "Project Parent Client"},
    )
    assert c_resp.status_code == 201
    client_id = c_resp.json()["id"]

    resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert data["client_id"] == client_id


def test_get_project(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    client_id = c_resp.json()["id"]
    p_resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": client_id, "name": "P"},
    )
    project_id = p_resp.json()["id"]
    resp = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "P"


def test_update_project(client, auth_headers):
    c_resp = client.post("/api/v1/clients", headers=auth_headers, json={"name": "C"})
    p_resp = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": c_resp.json()["id"], "name": "Old"},
    )
    project_id = p_resp.json()["id"]
    resp = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"name": "New Name", "status": "completed"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["status"] == "completed"
