"""Attendance: self check-in/out, intern privacy, admin board, summary and corrections."""
import uuid
from datetime import date, datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import AttendanceRecord, User
from app.services import attendance_service as svc


def _user_id(client, auth_headers, email):
    return next(u["id"] for u in client.get("/api/v1/users", headers=auth_headers).json() if u["email"] == email)


def _clear(email: str) -> None:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if u:
            db.query(AttendanceRecord).filter(AttendanceRecord.user_id == u.id).delete()
            db.commit()
    finally:
        db.close()


def _set_type(client, auth_headers, email, employment_type):
    uid = _user_id(client, auth_headers, email)
    r = client.patch(f"/api/v1/payroll/{uid}", headers=auth_headers, json={"employment_type": employment_type})
    assert r.status_code == 200, r.text
    return uid


# --- helpers ---

def test_working_days_and_start_time_parse():
    assert svc.is_working_day(date(2026, 9, 28)) is True   # Monday
    assert svc.is_working_day(date(2026, 9, 27)) is False  # Sunday
    assert svc.start_time().hour == 10


# --- self ---

def test_employee_checks_in_with_ip_and_location_then_out(client, auth_headers, employee_headers):
    _set_type(client, auth_headers, "employee@test.com", "full_time")
    _clear("employee@test.com")

    r = client.get("/api/v1/attendance/me", headers=employee_headers)
    assert r.status_code == 200 and r.json()["today"] is None and r.json()["captures_location"] is True

    r = client.post("/api/v1/attendance/check-in", headers={**employee_headers, "x-forwarded-for": "203.0.113.9, 10.0.0.1"},
                    json={"latitude": 31.5204, "longitude": 74.3587, "accuracy_m": 25})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["ip_address"] == "203.0.113.9"
    assert float(rec["latitude"]) == 31.5204 and float(rec["longitude"]) == 74.3587
    assert rec["status"] in ("present", "late") and rec["check_out_at"] is None

    # Twice in a day is refused
    r = client.post("/api/v1/attendance/check-in", headers=employee_headers, json={})
    assert r.status_code == 409

    r = client.post("/api/v1/attendance/check-out", headers=employee_headers, json={"note": "done"})
    assert r.status_code == 200 and r.json()["check_out_at"] is not None and r.json()["hours"] is not None
    r = client.post("/api/v1/attendance/check-out", headers=employee_headers, json={})
    assert r.status_code == 409

    me = client.get("/api/v1/attendance/me", headers=employee_headers).json()
    assert me["today"]["check_out_at"] is not None and len(me["recent"]) >= 1


def test_intern_is_only_marked(client, auth_headers, employee_headers):
    _set_type(client, auth_headers, "employee@test.com", "intern")
    _clear("employee@test.com")
    me = client.get("/api/v1/attendance/me", headers=employee_headers).json()
    assert me["captures_location"] is False
    r = client.post("/api/v1/attendance/check-in", headers={**employee_headers, "x-forwarded-for": "198.51.100.4"},
                    json={"latitude": 31.5, "longitude": 74.3, "accuracy_m": 10})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["ip_address"] is None and rec["latitude"] is None and rec["longitude"] is None and rec["user_agent"] is None
    assert rec["status"] in ("present", "late")
    _set_type(client, auth_headers, "employee@test.com", "full_time")


def test_late_is_after_start_time():
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "employee@test.com").first()
        assert u is not None
        db.query(AttendanceRecord).filter(AttendanceRecord.user_id == u.id).delete()
        db.commit()
        # 06:00 UTC on a Monday = 11:00 in Asia/Karachi -> late; 04:00 UTC = 09:00 -> present
        late_now = datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)
        rec = svc.check_in(db, u, ip="1.1.1.1", user_agent="t", latitude=None, longitude=None, accuracy_m=None, note=None, now=late_now)
        assert rec.status == "late" and rec.work_date == date(2026, 9, 28)
        db.rollback()
        early_now = datetime(2026, 9, 29, 4, 0, tzinfo=timezone.utc)
        rec = svc.check_in(db, u, ip="1.1.1.1", user_agent="t", latitude=None, longitude=None, accuracy_m=None, note=None, now=early_now)
        assert rec.status == "present"
        db.rollback()
    finally:
        db.close()


def test_client_users_and_non_admins_are_scoped(client, employee_headers, manager_headers):
    for h in (employee_headers, manager_headers):
        assert client.get("/api/v1/attendance/today", headers=h).status_code == 403
        assert client.get("/api/v1/attendance/summary", headers=h).status_code == 403
        assert client.get("/api/v1/attendance/records", headers=h).status_code == 403


# --- admin ---

def test_board_summary_and_correction(client, auth_headers, employee_headers):
    _set_type(client, auth_headers, "employee@test.com", "full_time")
    _clear("employee@test.com")
    emp_id = _user_id(client, auth_headers, "employee@test.com")

    board = client.get("/api/v1/attendance/today", headers=auth_headers).json()
    mine = next(r for r in board["rows"] if r["user_id"] == emp_id)
    assert mine["status"] in ("absent", "off")
    assert all(r["email"] != "client@test.com" for r in board["rows"])

    r = client.post("/api/v1/attendance/check-in", headers=employee_headers, json={})
    assert r.status_code == 201
    rec_id = r.json()["id"]
    board = client.get("/api/v1/attendance/today", headers=auth_headers).json()
    mine = next(r for r in board["rows"] if r["user_id"] == emp_id)
    assert mine["status"] in ("present", "late") and mine["record"]["id"] == rec_id
    assert board["present"] + board["late"] >= 1

    # Summary over the last 30 days counts the day
    today = svc.today_local()
    r = client.get(f"/api/v1/attendance/summary?from={(today - timedelta(days=29)).isoformat()}&to={today.isoformat()}", headers=auth_headers)
    assert r.status_code == 200, r.text
    row = next(x for x in r.json()["rows"] if x["user_id"] == emp_id)
    assert row["present_days"] + row["late_days"] >= 1
    assert row["working_days"] >= row["present_days"] + row["late_days"] + row["absent_days"] - 1

    # Correction: set an explicit check-out and force status present
    check_in = r_in = client.get("/api/v1/attendance/records?user_id=" + emp_id, headers=auth_headers).json()[0]
    out_at = (datetime.fromisoformat(check_in["check_in_at"].replace("Z", "+00:00")) + timedelta(hours=8)).isoformat()
    r = client.patch(f"/api/v1/attendance/records/{rec_id}", headers=auth_headers, json={"check_out_at": out_at, "status": "present", "note": "forgot to check out"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "present" and abs(r.json()["hours"] - 8.0) < 0.01
    r = client.patch(f"/api/v1/attendance/records/{rec_id}", headers=auth_headers, json={"status": "holiday"})
    assert r.status_code == 400
    assert r_in["user_id"] == emp_id

    assert client.delete(f"/api/v1/attendance/records/{rec_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/v1/attendance/me", headers=employee_headers).json()["today"] is None


def test_summary_range_validation(client, auth_headers):
    r = client.get("/api/v1/attendance/summary?from=2026-09-10&to=2026-09-01", headers=auth_headers)
    assert r.status_code == 400
    r = client.get("/api/v1/attendance/summary?from=2024-01-01&to=2026-09-01", headers=auth_headers)
    assert r.status_code == 400


def test_me_exposes_employment_type(client, auth_headers, employee_headers):
    _set_type(client, auth_headers, "employee@test.com", "intern")
    me = client.get("/api/v1/auth/me", headers=employee_headers).json()
    assert me["employment_type"] == "intern"
    _set_type(client, auth_headers, "employee@test.com", "full_time")
    _clear("employee@test.com")
