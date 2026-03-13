def test_list_clients_unauthorized(client):
    resp = client.get("/api/v1/clients")
    assert resp.status_code == 401


def test_list_clients_employee_forbidden(client, employee_headers):
    """Employee has no clients:read -> 403 (per roles-permissions-flow)."""
    resp = client.get("/api/v1/clients", headers=employee_headers)
    assert resp.status_code == 403


def test_list_clients(client, auth_headers):
    resp = client.get("/api/v1/clients", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_client(client, auth_headers):
    resp = client.post(
        "/api/v1/clients",
        headers=auth_headers,
        json={
            "name": "Test Client",
            "contact_email": "test@client.example",
            "contact_phone": "+1-555-9999",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Client"
    assert data["contact_email"] == "test@client.example"
    client_id = data["id"]

    # Get by id
    get_resp = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Test Client"


def test_update_client(client, auth_headers):
    create_resp = client.post(
        "/api/v1/clients",
        headers=auth_headers,
        json={"name": "Update Me", "contact_email": "old@example.com"},
    )
    assert create_resp.status_code == 201
    client_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/clients/{client_id}",
        headers=auth_headers,
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_delete_client(client, auth_headers):
    create_resp = client.post(
        "/api/v1/clients",
        headers=auth_headers,
        json={"name": "To Delete"},
    )
    assert create_resp.status_code == 201
    client_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert resp.status_code == 204
