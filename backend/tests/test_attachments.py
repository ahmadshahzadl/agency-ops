"""Attachments: upload/list/download/delete, entity scoping, type and size limits."""
import io
import uuid

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _make_task(client, auth_headers):
    r = client.post("/api/v1/tasks", headers=auth_headers, json={"title": f"Att {uuid.uuid4().hex[:6]}"})
    assert r.status_code == 201
    return r.json()["id"]


def _upload(client, headers, entity_type, entity_id, filename="shot.png", content=PNG_BYTES):
    return client.post(
        "/api/v1/attachments",
        headers=headers,
        data={"entity_type": entity_type, "entity_id": str(entity_id)},
        files={"file": (filename, io.BytesIO(content), "image/png")},
    )


def test_attachment_lifecycle(client, auth_headers):
    task_id = _make_task(client, auth_headers)
    up = _upload(client, auth_headers, "task", task_id)
    assert up.status_code == 201, up.text
    att = up.json()
    assert att["filename"] == "shot.png"
    assert att["size_bytes"] == len(PNG_BYTES)
    assert att["uploaded_by_name"]

    listed = client.get(f"/api/v1/attachments?entity_type=task&entity_id={task_id}", headers=auth_headers).json()
    assert any(a["id"] == att["id"] for a in listed)

    dl = client.get(f"/api/v1/attachments/{att['id']}/download", headers=auth_headers)
    assert dl.status_code == 200
    assert dl.content == PNG_BYTES
    assert dl.headers["content-type"].startswith("image/png")

    assert client.delete(f"/api/v1/attachments/{att['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/attachments/{att['id']}/download", headers=auth_headers).status_code == 404


def test_download_requires_auth(client, auth_headers):
    task_id = _make_task(client, auth_headers)
    att = _upload(client, auth_headers, "task", task_id).json()
    assert client.get(f"/api/v1/attachments/{att['id']}/download").status_code == 401


def test_disallowed_extension_rejected(client, auth_headers):
    task_id = _make_task(client, auth_headers)
    r = _upload(client, auth_headers, "task", task_id, filename="evil.exe", content=b"MZ...")
    assert r.status_code == 400


def test_html_not_inline(client, auth_headers):
    """Non-whitelisted content types must download as octet-stream, never render inline."""
    task_id = _make_task(client, auth_headers)
    r = client.post(
        "/api/v1/attachments",
        headers=auth_headers,
        data={"entity_type": "task", "entity_id": str(task_id)},
        files={"file": ("notes.txt", io.BytesIO(b"<script>alert(1)</script>"), "text/html")},
    )
    assert r.status_code == 201
    dl = client.get(f"/api/v1/attachments/{r.json()['id']}/download", headers=auth_headers)
    assert dl.headers["content-type"].startswith("application/octet-stream")
    assert "attachment" in dl.headers.get("content-disposition", "")


def test_employee_cannot_touch_unscoped_invoice_attachments(client, auth_headers, employee_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": f"AttCli {uuid.uuid4().hex[:6]}"})
    inv = client.post(
        "/api/v1/invoices", headers=auth_headers,
        json={"client_id": c.json()["id"], "number": f"INV-A-{uuid.uuid4().hex[:6]}", "amount": 10, "currency": "USD", "status": "draft"},
    ).json()
    att = _upload(client, auth_headers, "invoice", inv["id"], filename="contract.pdf").json()

    assert client.get(f"/api/v1/attachments?entity_type=invoice&entity_id={inv['id']}", headers=employee_headers).status_code == 404
    assert client.get(f"/api/v1/attachments/{att['id']}/download", headers=employee_headers).status_code == 404
    assert _upload(client, employee_headers, "invoice", inv["id"]).status_code == 404


def test_only_uploader_manager_or_admin_deletes(client, auth_headers, employee_headers, qa_headers):
    task_id = _make_task(client, auth_headers)
    # employee needs access to the task: assign it to them
    users = client.get("/api/v1/users", headers=auth_headers).json()
    emp_id = next(u["id"] for u in users if u["email"] == "employee@test.com")
    client.patch(f"/api/v1/tasks/{task_id}", headers=auth_headers, json={"assignee_id": emp_id})

    att = _upload(client, employee_headers, "task", task_id).json()
    # QA (not uploader, no reports) cannot delete even if they could see the task
    assert client.delete(f"/api/v1/attachments/{att['id']}", headers=qa_headers).status_code == 403
    # Uploader can
    assert client.delete(f"/api/v1/attachments/{att['id']}", headers=employee_headers).status_code == 204
