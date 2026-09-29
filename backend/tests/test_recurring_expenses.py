"""Recurring bills and salaries: scheduling, mark-paid, reminders, payroll."""
import uuid
from datetime import date, timedelta

from app.database import SessionLocal
from app.models import Notification, RecurringExpense
from app.services import recurring_expense_service as svc


def _create(client, auth_headers, **overrides):
    payload = {
        "description": f"Office rent {uuid.uuid4().hex[:6]}",
        "category": "office",
        "amount": 50000,
        "currency": "PKR",
        "frequency": "monthly",
        "due_day": 5,
    }
    payload.update(overrides)
    r = client.post("/api/v1/recurring-expenses", headers=auth_headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _set_due(rec_id: str, due: date) -> None:
    db = SessionLocal()
    try:
        rec = db.query(RecurringExpense).filter(RecurringExpense.id == uuid.UUID(rec_id)).first()
        rec.next_due_date = due
        rec.reminders_sent = []
        db.commit()
    finally:
        db.close()


def _admin_notifications(client, auth_headers, title_prefix: str) -> list[dict]:
    r = client.get("/api/v1/notifications?limit=200", headers=auth_headers)
    assert r.status_code == 200
    return [n for n in r.json() if n["title"].startswith(title_prefix)]


# --- date maths ---

def test_month_end_clamping():
    assert svc.add_months(date(2026, 1, 31), 1, 31) == date(2026, 2, 28)
    assert svc.add_months(date(2026, 2, 28), 1, 31) == date(2026, 3, 31)
    assert svc.next_occurrence(date(2026, 11, 30), "quarterly", 30) == date(2027, 2, 28)
    assert svc.next_occurrence(date(2024, 2, 29), "yearly", 29) == date(2025, 2, 28)
    assert svc.next_occurrence(date(2026, 9, 1), "weekly", 1) == date(2026, 9, 8)


def test_first_due_date_is_on_or_after_today():
    assert svc.first_due_date(date(2026, 9, 29), "monthly", 5) == date(2026, 10, 5)
    assert svc.first_due_date(date(2026, 9, 3), "monthly", 5) == date(2026, 9, 5)
    assert svc.first_due_date(date(2026, 9, 5), "monthly", 5) == date(2026, 9, 5)


# --- API ---

def test_create_pay_and_roll_forward(client, auth_headers):
    rec = _create(client, auth_headers, due_day=31, next_due_date="2026-01-31")
    assert rec["status"] in ("overdue", "scheduled", "due_soon", "due_today")

    r = client.post(f"/api/v1/recurring-expenses/{rec['id']}/pay", headers=auth_headers, json={"paid_on": "2026-01-30"})
    assert r.status_code == 201, r.text
    exp = r.json()
    assert exp["category"] == "office"
    assert float(exp["amount"]) == 50000
    assert exp["recurring_expense_id"] == rec["id"]
    assert "January 2026" in exp["description"]

    r = client.get(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)
    assert r.json()["next_due_date"] == "2026-02-28"
    assert r.json()["last_paid_on"] == "2026-01-30"

    # The payment shows in the ordinary expenses list and in the bill's history
    r = client.get(f"/api/v1/recurring-expenses/{rec['id']}/history", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) == 1
    r = client.get("/api/v1/expenses?limit=100", headers=auth_headers)
    assert any(e["id"] == exp["id"] for e in r.json())

    # Skip moves on without an expense
    r = client.post(f"/api/v1/recurring-expenses/{rec['id']}/skip", headers=auth_headers)
    assert r.status_code == 200 and r.json()["next_due_date"] == "2026-03-31"
    r = client.get(f"/api/v1/recurring-expenses/{rec['id']}/history", headers=auth_headers)
    assert len(r.json()) == 1

    client.delete(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)


def test_pay_with_override_amount(client, auth_headers):
    rec = _create(client, auth_headers, amount=1200, currency="USD", category="software")
    r = client.post(f"/api/v1/recurring-expenses/{rec['id']}/pay", headers=auth_headers, json={"amount": 1150.5, "note": "discount"})
    assert r.status_code == 201, r.text
    assert float(r.json()["amount"]) == 1150.5
    client.delete(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)


def test_validation(client, auth_headers):
    r = client.post("/api/v1/recurring-expenses", headers=auth_headers, json={"description": "x", "amount": 10, "frequency": "fortnightly"})
    assert r.status_code == 400
    r = client.post("/api/v1/recurring-expenses", headers=auth_headers, json={"description": "x", "amount": 10, "category": "bribes"})
    assert r.status_code == 400
    r = client.post("/api/v1/recurring-expenses", headers=auth_headers, json={"description": "x", "amount": 0})
    assert r.status_code == 400


def test_non_admin_forbidden(client, manager_headers, employee_headers):
    for h in (manager_headers, employee_headers):
        assert client.get("/api/v1/recurring-expenses", headers=h).status_code == 403
        assert client.get("/api/v1/payroll", headers=h).status_code == 403
        assert client.post("/api/v1/recurring-expenses", headers=h, json={"description": "x", "amount": 10}).status_code == 403


# --- reminders ---

def test_reminders_fire_at_two_one_zero_and_overdue_without_duplicates(client, auth_headers):
    rec = _create(client, auth_headers, description=f"Reminder bill {uuid.uuid4().hex[:6]}")
    today = date(2026, 10, 10)
    _set_due(rec["id"], today + timedelta(days=2))

    db = SessionLocal()
    try:
        assert svc.send_due_reminders(db, today) >= 1          # 2 days before
        assert svc.send_due_reminders(db, today) == 0          # same day again: nothing new
        assert svc.send_due_reminders(db, today + timedelta(days=1)) >= 1   # 1 day before
        assert svc.send_due_reminders(db, today + timedelta(days=2)) >= 1   # due today
        assert svc.send_due_reminders(db, today + timedelta(days=3)) >= 1   # overdue, once
        assert svc.send_due_reminders(db, today + timedelta(days=4)) == 0   # not nagged daily
        assert svc.send_due_reminders(db, today + timedelta(days=9)) == 0

        titles = [
            n.title for n in db.query(Notification).filter(Notification.type == "expense", Notification.message.like(f"%{rec['currency']}%")).all()
            if rec["description"] in n.title
        ]
        assert any(t.startswith("Due in 2 days") for t in titles)
        assert any(t.startswith("Due tomorrow") for t in titles)
        assert any(t.startswith("Due today") for t in titles)
        assert any(t.startswith("Overdue") for t in titles)
        # Marking paid clears the ledger so next month reminds again
        row = db.query(RecurringExpense).filter(RecurringExpense.id == uuid.UUID(rec["id"])).first()
        assert len(row.reminders_sent) == 4
    finally:
        db.close()

    r = client.post(f"/api/v1/recurring-expenses/{rec['id']}/pay", headers=auth_headers, json={})
    assert r.status_code == 201
    r = client.get(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)
    assert r.status_code == 200
    client.delete(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)


def test_missed_days_collapse_to_one_reminder(client, auth_headers):
    """If the scheduler was down for the 2-day and 1-day marks, only the closest reminder goes out."""
    rec = _create(client, auth_headers)
    today = date(2026, 11, 3)
    _set_due(rec["id"], today)  # first pass happens on the due day itself
    db = SessionLocal()
    try:
        assert svc.send_due_reminders(db, today) == 1
        row = db.query(RecurringExpense).filter(RecurringExpense.id == uuid.UUID(rec["id"])).first()
        assert sorted(row.reminders_sent) == sorted([f"{today.isoformat()}:2", f"{today.isoformat()}:1", f"{today.isoformat()}:0"])
    finally:
        db.close()
    client.delete(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)


def test_paused_bills_do_not_remind(client, auth_headers):
    rec = _create(client, auth_headers, is_active=False)
    _set_due(rec["id"], date(2026, 12, 1))
    db = SessionLocal()
    try:
        assert svc.send_due_reminders(db, date(2026, 11, 30)) == 0
    finally:
        db.close()
    client.delete(f"/api/v1/recurring-expenses/{rec['id']}", headers=auth_headers)


def test_run_reminders_endpoint_admin_only(client, auth_headers, employee_headers):
    assert client.post("/api/v1/recurring-expenses/run-reminders", headers=employee_headers).status_code == 403
    r = client.post("/api/v1/recurring-expenses/run-reminders", headers=auth_headers)
    assert r.status_code == 200 and "sent" in r.json()


# --- payroll ---

def test_payroll_set_pay_and_list(client, auth_headers, employee_headers):
    users = client.get("/api/v1/users", headers=auth_headers).json()
    emp = next(u for u in users if u["email"] == "employee@test.com")

    r = client.patch(f"/api/v1/payroll/{emp['id']}", headers=auth_headers, json={
        "amount": 80000, "currency": "PKR", "due_day": 1, "employment_type": "full_time", "joined_on": "2026-03-01",
    })
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["salary_id"] and float(row["amount"]) == 80000 and row["due_day"] == 1
    assert row["employment_type"] == "full_time" and row["joined_on"] == "2026-03-01"
    assert row["status"] in ("scheduled", "due_soon", "due_today")

    # Same employee again updates the one salary record rather than adding a second
    r = client.patch(f"/api/v1/payroll/{emp['id']}", headers=auth_headers, json={"amount": 85000})
    assert r.status_code == 200 and r.json()["salary_id"] == row["salary_id"] and float(r.json()["amount"]) == 85000

    listing = client.get("/api/v1/payroll", headers=auth_headers).json()
    mine = next(x for x in listing if x["user_id"] == emp["id"])
    assert mine["salary_id"] == row["salary_id"]
    # Client-portal users never appear
    assert all(x["email"] != "client@test.com" for x in listing)

    # Paying the salary writes a salary expense to that payee
    r = client.post(f"/api/v1/recurring-expenses/{row['salary_id']}/pay", headers=auth_headers, json={})
    assert r.status_code == 201, r.text
    assert r.json()["category"] == "salary" and r.json()["payee_user_id"] == emp["id"]
    assert r.json()["payee_name"]

    # Employment type is validated
    r = client.patch(f"/api/v1/payroll/{emp['id']}", headers=auth_headers, json={"employment_type": "volunteer"})
    assert r.status_code == 400

    # Employee cannot see or edit payroll
    assert client.patch(f"/api/v1/payroll/{emp['id']}", headers=employee_headers, json={"amount": 1}).status_code == 403

    client.delete(f"/api/v1/recurring-expenses/{row['salary_id']}", headers=auth_headers)


def test_users_api_exposes_employment_fields(client, auth_headers):
    users = client.get("/api/v1/users", headers=auth_headers).json()
    emp = next(u for u in users if u["email"] == "employee@test.com")
    r = client.patch(f"/api/v1/users/{emp['id']}", headers=auth_headers, json={"employment_type": "intern", "joined_on": "2026-09-01"})
    assert r.status_code == 200, r.text
    assert r.json()["employment_type"] == "intern" and r.json()["joined_on"] == "2026-09-01"
