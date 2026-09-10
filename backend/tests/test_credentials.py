"""Credentials vault: encryption at rest, masked responses, audited
reveal, and permission gates."""
import uuid

from tests.test_portal import _make_client_record, _make_project


def _make_credential(client, auth_headers, project_id, **overrides):
    body = {
        "project_id": project_id,
        "label": f"cPanel {uuid.uuid4().hex[:6]}",
        "username": "deploy_user",
        "secret": "S3cret-P@ss!",
        "url": "https://cpanel.example.com",
    }
    body.update(overrides)
    r = client.post("/api/v1/credentials", headers=auth_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _project(client, auth_headers):
    cid = _make_client_record(client, auth_headers)
    return _make_project(client, auth_headers, cid)


def test_secret_never_in_responses_and_encrypted_at_rest(client, auth_headers):
    proj = _project(client, auth_headers)
    cred = _make_credential(client, auth_headers, proj["id"])

    # Create/list responses carry no secret in any form
    assert "secret" not in cred and "secret_encrypted" not in cred
    rows = client.get(f"/api/v1/credentials?project_id={proj['id']}", headers=auth_headers).json()
    assert len(rows) == 1
    assert "secret" not in rows[0] and "S3cret" not in str(rows[0])

    # At rest: the DB column is a Fernet token, not the plaintext
    from app.database import SessionLocal
    from app.models import ProjectCredential
    db = SessionLocal()
    try:
        stored = db.query(ProjectCredential).filter(ProjectCredential.id == cred["id"]).first()
        assert stored.secret_encrypted != "S3cret-P@ss!"
        assert "S3cret" not in stored.secret_encrypted
        assert stored.secret_encrypted.startswith("gAAAA")  # Fernet token prefix
    finally:
        db.close()


def test_reveal_returns_secret_and_is_audited(client, auth_headers):
    proj = _project(client, auth_headers)
    cred = _make_credential(client, auth_headers, proj["id"], secret="TopSecret42")

    r = client.post(f"/api/v1/credentials/{cred['id']}/reveal", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["secret"] == "TopSecret42"

    # The reveal is in the activity log
    from app.database import SessionLocal
    from app.models import ActivityLog
    db = SessionLocal()
    try:
        entry = db.query(ActivityLog).filter(
            ActivityLog.action == "credential_revealed",
            ActivityLog.entity_id == uuid.UUID(cred["id"]),
        ).first()
        assert entry is not None
        assert cred["label"] in (entry.details or "")
    finally:
        db.close()


def test_update_rotate_and_delete(client, auth_headers):
    proj = _project(client, auth_headers)
    cred = _make_credential(client, auth_headers, proj["id"], secret="old-secret")

    # Metadata update without touching the secret
    r = client.patch(f"/api/v1/credentials/{cred['id']}", headers=auth_headers, json={"label": "Renamed", "notes": "prod box"})
    assert r.status_code == 200 and r.json()["label"] == "Renamed"
    r = client.post(f"/api/v1/credentials/{cred['id']}/reveal", headers=auth_headers)
    assert r.json()["secret"] == "old-secret"

    # Rotation re-encrypts
    client.patch(f"/api/v1/credentials/{cred['id']}", headers=auth_headers, json={"secret": "new-secret"})
    r = client.post(f"/api/v1/credentials/{cred['id']}/reveal", headers=auth_headers)
    assert r.json()["secret"] == "new-secret"

    # Empty secret rejected
    assert client.patch(f"/api/v1/credentials/{cred['id']}", headers=auth_headers, json={"secret": ""}).status_code == 400

    assert client.delete(f"/api/v1/credentials/{cred['id']}", headers=auth_headers).status_code == 204
    assert client.post(f"/api/v1/credentials/{cred['id']}/reveal", headers=auth_headers).status_code == 404


def test_credentials_permission_gate(client, auth_headers, employee_headers):
    proj = _project(client, auth_headers)
    cred = _make_credential(client, auth_headers, proj["id"])

    # Employees (no credentials:*) are locked out of everything, reveal included
    assert client.get(f"/api/v1/credentials?project_id={proj['id']}", headers=employee_headers).status_code == 403
    assert client.post(f"/api/v1/credentials/{cred['id']}/reveal", headers=employee_headers).status_code == 403
    assert client.post("/api/v1/credentials", headers=employee_headers, json={
        "project_id": proj["id"], "label": "x", "secret": "y"}).status_code == 403


def test_credential_requires_live_project(client, auth_headers):
    fake = str(uuid.uuid4())
    r = client.post("/api/v1/credentials", headers=auth_headers, json={"project_id": fake, "label": "x", "secret": "y"})
    assert r.status_code == 404
