from datetime import datetime, timedelta


def test_list_meetings_unauthorized(client):
    resp = client.get("/api/v1/meetings")
    assert resp.status_code == 401


def test_list_meetings(client, auth_headers):
    resp = client.get("/api/v1/meetings", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_meeting(client, auth_headers):
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=1)
    resp = client.post(
        "/api/v1/meetings",
        headers=auth_headers,
        json={
            "title": "Test Meeting",
            "description": "A test",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "location": "Room 1",
            "attendee_ids": [],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Meeting"
    assert data["location"] == "Room 1"


def test_get_meeting(client, auth_headers):
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=1)
    create_resp = client.post(
        "/api/v1/meetings",
        headers=auth_headers,
        json={"title": "Get Me", "start_at": start.isoformat(), "end_at": end.isoformat()},
    )
    meeting_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get Me"


def test_update_meeting(client, auth_headers):
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=1)
    create_resp = client.post(
        "/api/v1/meetings",
        headers=auth_headers,
        json={"title": "Original", "start_at": start.isoformat(), "end_at": end.isoformat()},
    )
    meeting_id = create_resp.json()["id"]
    resp = client.patch(
        f"/api/v1/meetings/{meeting_id}",
        headers=auth_headers,
        json={"title": "Updated title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated title"


def test_delete_meeting(client, auth_headers):
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=1)
    create_resp = client.post(
        "/api/v1/meetings",
        headers=auth_headers,
        json={"title": "To delete", "start_at": start.isoformat(), "end_at": end.isoformat()},
    )
    meeting_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert resp.status_code == 204
