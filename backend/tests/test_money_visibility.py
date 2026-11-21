"""Project rate/budget and time-entry rates are finance data.

Only finance:read (or admin:all) holders see them, and only they can change them. This guards
two things: the leak (employees/QA/managers reading rates and budgets through projects:read /
time:read), and the edit-form bug (a non-finance user saving the project form must not wipe the
stored rate that invoice-from-time depends on).
"""
from datetime import date


def _me(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()


def _project_owned_by(client, auth_headers, owner_id):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"name": "Money Client"}).json()
    p = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"client_id": c["id"], "name": "Money Project", "hourly_rate": 40, "budget": 5000, "owner_id": owner_id},
    )
    assert p.status_code == 201, p.text
    return p.json()


def test_admin_sees_money_in_list_and_detail(client, auth_headers):
    me = _me(client, auth_headers)
    p = _project_owned_by(client, auth_headers, me["id"])
    assert float(p["budget"]) == 5000
    detail = client.get(f"/api/v1/projects/{p['id']}", headers=auth_headers).json()
    assert float(detail["hourly_rate"]) == 40
    listed = [x for x in client.get(f"/api/v1/projects?client_id={p['client_id']}", headers=auth_headers).json() if x["id"] == p["id"]]
    # The list now carries the money fields too, so the edit form loads real values.
    assert listed and float(listed[0]["budget"]) == 5000


def test_manager_without_finance_cannot_see_or_wipe_money(client, auth_headers, manager_headers):
    mgr = _me(client, manager_headers)
    p = _project_owned_by(client, auth_headers, mgr["id"])

    detail = client.get(f"/api/v1/projects/{p['id']}", headers=manager_headers)
    assert detail.status_code == 200
    assert detail.json()["budget"] is None and detail.json()["hourly_rate"] is None
    listed = [x for x in client.get(f"/api/v1/projects?client_id={p['client_id']}", headers=manager_headers).json() if x["id"] == p["id"]]
    assert listed and listed[0]["budget"] is None

    # What the old edit form sent: money fields as null. The stored values must survive.
    upd = client.patch(
        f"/api/v1/projects/{p['id']}", headers=manager_headers,
        json={"name": "Renamed by manager", "hourly_rate": None, "budget": None},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["budget"] is None  # still hidden in the response
    admin_view = client.get(f"/api/v1/projects/{p['id']}", headers=auth_headers).json()
    assert admin_view["name"] == "Renamed by manager"
    assert float(admin_view["hourly_rate"]) == 40 and float(admin_view["budget"]) == 5000


def test_time_entry_rate_and_unbilled_value_hidden_without_finance(client, auth_headers, manager_headers):
    mgr = _me(client, manager_headers)
    p = _project_owned_by(client, auth_headers, mgr["id"])
    e = client.post(
        "/api/v1/time-entries", headers=manager_headers,
        json={"project_id": p["id"], "work_date": str(date.today()), "hours": 2, "billable": True, "hourly_rate": 999},
    )
    assert e.status_code in (200, 201), e.text
    assert e.json()["hourly_rate"] is None

    summary = client.get(f"/api/v1/time-entries/summary?project_id={p['id']}", headers=manager_headers).json()
    assert summary["unbilled_amount"] is None
    assert float(summary["unbilled_billable_hours"]) >= 2

    admin_summary = client.get(f"/api/v1/time-entries/summary?project_id={p['id']}", headers=auth_headers).json()
    # The manager's 999 rate was ignored, so the project rate (40) applies: 2h x 40.
    assert float(admin_summary["unbilled_amount"]) == 80
