"""Phase 1 tests: QA status pipeline with approval gate, and kanban boards
with member-scoped access."""
import uuid


def _user_id(client, auth_headers, email):
    users = client.get("/api/v1/users", headers=auth_headers).json()
    return next(u["id"] for u in users if u["email"] == email)


def _setup_project(client, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"QA Client {uuid.uuid4().hex[:6]}"})
    assert c.status_code == 201
    p = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": c.json()["id"], "name": f"QA Project {uuid.uuid4().hex[:6]}", "status": "active"},
    )
    assert p.status_code == 201
    return p.json()["id"]


def _make_board(client, auth_headers, project_id, member_emails=()):
    member_ids = [_user_id(client, auth_headers, e) for e in member_emails]
    b = client.post(
        "/api/v1/boards",
        headers=auth_headers,
        json={"project_id": project_id, "name": f"Sprint {uuid.uuid4().hex[:4]}", "member_ids": member_ids},
    )
    assert b.status_code == 201
    return b.json()


def _make_task(client, auth_headers, project_id, board_id=None, assignee_email=None, **extra):
    payload = {"project_id": project_id, "title": f"Task {uuid.uuid4().hex[:6]}", "status": "todo", **extra}
    if board_id:
        payload["board_id"] = board_id
    if assignee_email:
        payload["assignee_id"] = _user_id(client, auth_headers, assignee_email)
    t = client.post("/api/v1/tasks", headers=auth_headers, json=payload)
    assert t.status_code == 201, t.text
    return t.json()


# --- QA pipeline ---

def test_assignee_walks_dev_pipeline_but_cannot_close(client, auth_headers, employee_headers, qa_headers):
    project_id = _setup_project(client, auth_headers)
    board = _make_board(client, auth_headers, project_id, ["employee@test.com", "qa@test.com"])
    task = _make_task(client, auth_headers, project_id, board["id"], "employee@test.com")

    for next_status in ("in_progress", "review"):
        r = client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": next_status})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == next_status

    # Assignee may not self-approve
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": "done"})
    assert r.status_code == 403

    # QA (not the assignee, sees the task via board membership) approves
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=qa_headers, json={"status": "done"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "done"
    assert data["qa_by"] is not None and data["qa_at"] is not None


def test_qa_fail_requires_notes_and_returns_to_dev(client, auth_headers, employee_headers, qa_headers):
    project_id = _setup_project(client, auth_headers)
    board = _make_board(client, auth_headers, project_id, ["employee@test.com", "qa@test.com"])
    task = _make_task(client, auth_headers, project_id, board["id"], "employee@test.com")
    client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": "in_progress"})
    client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": "review"})

    # Failing without notes is rejected
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=qa_headers, json={"status": "qa_failed"})
    assert r.status_code == 400

    r = client.patch(
        f"/api/v1/tasks/{task['id']}", headers=qa_headers,
        json={"status": "qa_failed", "qa_notes": "Crashes on submit"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "qa_failed"
    assert r.json()["qa_notes"] == "Crashes on submit"

    # Assignee reworks: qa_failed -> in_progress
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": "in_progress"})
    assert r.status_code == 200


def test_invalid_transitions_rejected(client, auth_headers, employee_headers):
    project_id = _setup_project(client, auth_headers)
    task = _make_task(client, auth_headers, project_id, assignee_email="employee@test.com")
    # todo -> review skips in_progress
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": "review"})
    assert r.status_code == 403
    # Unknown status
    r = client.patch(f"/api/v1/tasks/{task['id']}", headers=employee_headers, json={"status": "banana"})
    assert r.status_code == 400


def test_non_admin_cannot_create_task_in_done(client, auth_headers, employee_headers):
    project_id = _setup_project(client, auth_headers)
    r = client.post(
        "/api/v1/tasks", headers=employee_headers,
        json={"title": "sneaky", "status": "done"},
    )
    assert r.status_code == 403


def test_bug_fields_roundtrip(client, auth_headers, employee_headers):
    project_id = _setup_project(client, auth_headers)
    task = _make_task(
        client, auth_headers, project_id, assignee_email="employee@test.com",
        item_type="bug", severity="high", steps_to_reproduce="1. open 2. click", environment="prod",
    )
    assert task["item_type"] == "bug"
    assert task["severity"] == "high"
    r = client.post("/api/v1/tasks", headers=auth_headers, json={"title": "bad", "item_type": "bug", "severity": "catastrophic"})
    assert r.status_code == 400


# --- Boards ---

def test_employee_cannot_create_board(client, auth_headers, employee_headers):
    project_id = _setup_project(client, auth_headers)
    r = client.post(
        "/api/v1/boards", headers=employee_headers,
        json={"project_id": project_id, "name": "Nope"},
    )
    assert r.status_code == 403


def test_board_visibility_scoped_to_members(client, auth_headers, employee_headers, qa_headers):
    project_id = _setup_project(client, auth_headers)
    board_with_qa = _make_board(client, auth_headers, project_id, ["qa@test.com"])
    board_without = _make_board(client, auth_headers, project_id, [])

    listed = client.get(f"/api/v1/boards?project_id={project_id}", headers=qa_headers).json()
    listed_ids = {b["id"] for b in listed}
    assert board_with_qa["id"] in listed_ids
    assert board_without["id"] not in listed_ids

    assert client.get(f"/api/v1/boards/{board_with_qa['id']}", headers=qa_headers).status_code == 200
    assert client.get(f"/api/v1/boards/{board_without['id']}", headers=qa_headers).status_code == 404
    # Admin sees everything
    assert client.get(f"/api/v1/boards/{board_without['id']}", headers=auth_headers).status_code == 200


def test_board_membership_grants_task_visibility(client, auth_headers, employee_headers, qa_headers):
    project_id = _setup_project(client, auth_headers)
    board = _make_board(client, auth_headers, project_id, ["qa@test.com"])
    # Task assigned to employee, placed on the board
    task = _make_task(client, auth_headers, project_id, board["id"], "employee@test.com")

    # QA is not assignee but a board member: can fetch it directly and via the board
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=qa_headers).status_code == 200
    board_tasks = client.get(f"/api/v1/boards/{board['id']}/tasks", headers=qa_headers).json()
    assert any(t["id"] == task["id"] for t in board_tasks)

    # Employee (assignee, NOT board member) still sees own task; board itself is hidden
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=employee_headers).status_code == 200
    assert client.get(f"/api/v1/boards/{board['id']}", headers=employee_headers).status_code == 404


def test_delete_board_detaches_tasks(client, auth_headers):
    project_id = _setup_project(client, auth_headers)
    board = _make_board(client, auth_headers, project_id, [])
    task = _make_task(client, auth_headers, project_id, board["id"])
    assert client.delete(f"/api/v1/boards/{board['id']}", headers=auth_headers).status_code == 204
    t = client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers).json()
    assert t["board_id"] is None


def test_member_management(client, auth_headers, employee_headers):
    project_id = _setup_project(client, auth_headers)
    board = _make_board(client, auth_headers, project_id, [])
    emp_id = _user_id(client, auth_headers, "employee@test.com")

    r = client.post(f"/api/v1/boards/{board['id']}/members", headers=auth_headers, json={"user_id": emp_id})
    assert r.status_code == 201
    assert any(m["user_id"] == emp_id for m in r.json()["members"])
    # Now visible to the employee
    assert client.get(f"/api/v1/boards/{board['id']}", headers=employee_headers).status_code == 200

    r = client.delete(f"/api/v1/boards/{board['id']}/members/{emp_id}", headers=auth_headers)
    assert r.status_code == 200
    assert not any(m["user_id"] == emp_id for m in r.json()["members"])
    assert client.get(f"/api/v1/boards/{board['id']}", headers=employee_headers).status_code == 404


def test_task_must_match_board_project(client, auth_headers):
    project_a = _setup_project(client, auth_headers)
    project_b = _setup_project(client, auth_headers)
    board_a = _make_board(client, auth_headers, project_a, [])
    r = client.post(
        "/api/v1/tasks", headers=auth_headers,
        json={"project_id": project_b, "title": "wrong project", "board_id": board_a["id"]},
    )
    assert r.status_code == 400
