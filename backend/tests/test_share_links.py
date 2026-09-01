"""Client-facing share links: minting rights, public sanitized snapshot, revocation."""
import uuid


def _setup_project_with_tasks(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"Share Client {uuid.uuid4().hex[:6]}"})
    p = client.post(
        "/api/v1/projects", headers=auth_headers,
        json={"client_id": c.json()["id"], "name": f"Share Project {uuid.uuid4().hex[:6]}", "status": "active"},
    )
    pid = p.json()["id"]
    for status_val in ("todo", "in_progress", "done", "done"):
        r = client.post(
            "/api/v1/tasks", headers=auth_headers,
            json={"project_id": pid, "title": f"T {uuid.uuid4().hex[:4]}", "status": status_val},
        )
        assert r.status_code == 201
    return pid


def test_share_link_lifecycle_and_sanitization(client, auth_headers):
    pid = _setup_project_with_tasks(client, auth_headers)
    r = client.post(f"/api/v1/projects/{pid}/share-links", headers=auth_headers, json={"label": "For Acme"})
    assert r.status_code == 201
    link = r.json()
    assert link["token"]

    # Public access requires no auth
    pub = client.get(f"/api/v1/public/status/{link['token']}")
    assert pub.status_code == 200
    data = pub.json()
    assert data["total_tasks"] == 4
    assert data["counts"]["done"] == 2
    assert data["percent_done"] == 50
    # Sanitized: no assignees, descriptions, QA notes, or ids in task entries
    for t in data["tasks"]:
        assert set(t.keys()) == {"title", "status", "item_type", "due_date"}

    # Listed for managers, then revoke kills the link
    listed = client.get(f"/api/v1/projects/{pid}/share-links", headers=auth_headers).json()
    assert any(l["id"] == link["id"] for l in listed)
    assert client.delete(f"/api/v1/share-links/{link['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/public/status/{link['token']}").status_code == 404


def test_employee_cannot_mint_share_link(client, auth_headers, employee_headers):
    pid = _setup_project_with_tasks(client, auth_headers)
    r = client.post(f"/api/v1/projects/{pid}/share-links", headers=employee_headers, json={})
    assert r.status_code == 403


def test_invalid_token_404(client):
    assert client.get("/api/v1/public/status/not-a-real-token").status_code == 404


def test_qa_states_masked_for_clients(client, auth_headers):
    pid = _setup_project_with_tasks(client, auth_headers)
    t = client.post(
        "/api/v1/tasks", headers=auth_headers,
        json={"project_id": pid, "title": "In QA", "status": "todo"},
    ).json()
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "in_progress"})
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "review"})
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "qa_failed", "qa_notes": "internal detail"})
    link = client.post(f"/api/v1/projects/{pid}/share-links", headers=auth_headers, json={}).json()
    data = client.get(f"/api/v1/public/status/{link['token']}").json()
    masked = next(x for x in data["tasks"] if x["title"] == "In QA")
    assert masked["status"] == "review"  # qa_failed never shown to clients
