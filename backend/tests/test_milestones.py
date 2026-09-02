"""Milestones: CRUD, task linkage + progress, states, public share page."""
import uuid
from datetime import date, timedelta


def _setup_project(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"MS Client {uuid.uuid4().hex[:6]}"})
    p = client.post(
        "/api/v1/projects", headers=auth_headers,
        json={"client_id": c.json()["id"], "name": f"MS Project {uuid.uuid4().hex[:6]}", "status": "active"},
    )
    return p.json()["id"]


def test_milestone_lifecycle_and_progress(client, auth_headers):
    pid = _setup_project(client, auth_headers)
    m = client.post(
        f"/api/v1/projects/{pid}/milestones", headers=auth_headers,
        json={"name": "Phase 1", "due_date": str(date.today() + timedelta(days=30))},
    )
    assert m.status_code == 201, m.text
    mid = m.json()["id"]
    assert m.json()["state"] == "upcoming"

    # Link tasks: 1 done of 2
    t1 = client.post("/api/v1/tasks", headers=auth_headers, json={"title": "A", "project_id": pid, "milestone_id": mid}).json()
    client.post("/api/v1/tasks", headers=auth_headers, json={"title": "B", "project_id": pid, "milestone_id": mid})
    client.patch(f"/api/v1/tasks/{t1['id']}", headers=auth_headers, json={"status": "done"})

    listed = client.get(f"/api/v1/projects/{pid}/milestones", headers=auth_headers).json()
    ms = next(x for x in listed if x["id"] == mid)
    assert ms["task_total"] == 2 and ms["task_done"] == 1

    # Complete / reopen
    done = client.post(f"/api/v1/milestones/{mid}/complete", headers=auth_headers).json()
    assert done["state"] == "completed"
    reopened = client.post(f"/api/v1/milestones/{mid}/reopen", headers=auth_headers).json()
    assert reopened["state"] == "upcoming"

    # Delete detaches tasks
    assert client.delete(f"/api/v1/milestones/{mid}", headers=auth_headers).status_code == 204
    t = client.get(f"/api/v1/tasks/{t1['id']}", headers=auth_headers).json()
    assert t["milestone_id"] is None


def test_overdue_state(client, auth_headers):
    pid = _setup_project(client, auth_headers)
    m = client.post(
        f"/api/v1/projects/{pid}/milestones", headers=auth_headers,
        json={"name": "Late phase", "due_date": str(date.today() - timedelta(days=1))},
    ).json()
    assert m["state"] == "overdue"


def test_milestone_must_match_task_project(client, auth_headers):
    pid_a = _setup_project(client, auth_headers)
    pid_b = _setup_project(client, auth_headers)
    m = client.post(f"/api/v1/projects/{pid_a}/milestones", headers=auth_headers, json={"name": "A phase"}).json()
    r = client.post("/api/v1/tasks", headers=auth_headers, json={"title": "X", "project_id": pid_b, "milestone_id": m["id"]})
    assert r.status_code == 400
    # Moving a linked task to another project detaches the milestone
    t = client.post("/api/v1/tasks", headers=auth_headers, json={"title": "Y", "project_id": pid_a, "milestone_id": m["id"]}).json()
    moved = client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"project_id": pid_b}).json()
    assert moved["milestone_id"] is None


def test_employee_cannot_manage_milestones(client, auth_headers, employee_headers):
    pid = _setup_project(client, auth_headers)
    r = client.post(f"/api/v1/projects/{pid}/milestones", headers=employee_headers, json={"name": "Nope"})
    assert r.status_code == 403


def test_milestones_on_public_share_page(client, auth_headers):
    pid = _setup_project(client, auth_headers)
    m = client.post(
        f"/api/v1/projects/{pid}/milestones", headers=auth_headers,
        json={"name": "Design phase", "due_date": str(date.today() + timedelta(days=10))},
    ).json()
    t = client.post("/api/v1/tasks", headers=auth_headers, json={"title": "Mock", "project_id": pid, "milestone_id": m["id"]}).json()
    client.patch(f"/api/v1/tasks/{t['id']}", headers=auth_headers, json={"status": "done"})
    link = client.post(f"/api/v1/projects/{pid}/share-links", headers=auth_headers, json={}).json()
    pub = client.get(f"/api/v1/public/status/{link['token']}").json()
    assert len(pub["milestones"]) == 1
    ms = pub["milestones"][0]
    assert ms["name"] == "Design phase"
    assert ms["task_total"] == 1 and ms["task_done"] == 1
    assert set(ms.keys()) == {"name", "due_date", "completed", "task_total", "task_done"}
