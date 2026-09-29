"""Recurring bills and salaries: scheduling, marking paid, and the due-date reminders.

A RecurringExpense is the template (rent on the 5th, a subscription on the 20th, Ahmed's salary on
the 1st). Marking it paid writes a normal Expense row, so reports and month totals keep working,
and moves next_due_date forward one period. The reminder pass runs from the background scheduler
and notifies everyone with expenses:write (or admin:all) 2 days before, 1 day before, on the day,
and once more when a bill is overdue. Each reminder is recorded on the row so it is sent once.
"""
import calendar
import logging
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import Expense, Notification, RecurringExpense, User
from app.models.finance import RECURRING_FREQUENCIES
from app.services import email_service
from app.services.activity_service import log_activity
from app.services.permission_service import users_with_permission

logger = logging.getLogger(__name__)

EXPENSES_WRITE = "expenses:write"
REMINDER_LINK = "/expenses?tab=recurring"
DEFAULT_REMIND_DAYS = [2, 1, 0]


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def clamp_day(year: int, month: int, day: int) -> date:
    """The given day of that month, or the last day if the month is shorter (31 Jan -> 28 Feb)."""
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(day, 1), last))


def add_months(d: date, months: int, due_day: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    return clamp_day(total // 12, total % 12 + 1, due_day)


def next_occurrence(after: date, frequency: str, due_day: int) -> date:
    """The first due date strictly after ``after``."""
    if frequency == "weekly":
        return after + timedelta(days=7)
    step = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
    return add_months(after, step, due_day)


def first_due_date(today: date, frequency: str, due_day: int) -> date:
    """Where a new bill starts: the next date on or after today that matches its schedule."""
    if frequency == "weekly":
        return today
    candidate = clamp_day(today.year, today.month, due_day)
    if candidate < today:
        candidate = add_months(candidate, 1, due_day)
    return candidate


def validate_frequency(frequency: str) -> None:
    if frequency not in RECURRING_FREQUENCIES:
        raise ValueError(f"frequency must be one of: {', '.join(RECURRING_FREQUENCIES)}")


# ---------------------------------------------------------------------------
# Status helpers (shared by the API and the UI)
# ---------------------------------------------------------------------------

def days_until(rec: RecurringExpense, today: date | None = None) -> int:
    return (rec.next_due_date - (today or date.today())).days


def status_of(rec: RecurringExpense, today: date | None = None) -> str:
    if not rec.is_active:
        return "paused"
    d = days_until(rec, today)
    if d < 0:
        return "overdue"
    if d == 0:
        return "due_today"
    if d <= 7:
        return "due_soon"
    return "scheduled"


def period_label(rec: RecurringExpense, due: date) -> str:
    if rec.frequency == "weekly":
        return f"week of {due.isoformat()}"
    if rec.frequency == "yearly":
        return str(due.year)
    if rec.frequency == "quarterly":
        return f"Q{(due.month - 1) // 3 + 1} {due.year}"
    return due.strftime("%B %Y")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def record_payment(
    db: Session,
    rec: RecurringExpense,
    user: User,
    paid_on: date | None = None,
    amount: Decimal | None = None,
    note: str | None = None,
) -> Expense:
    """Write the Expense for the current period and roll the schedule forward."""
    paid_on = paid_on or date.today()
    due = rec.next_due_date
    exp = Expense(
        project_id=rec.project_id,
        description=f"{rec.description} — {period_label(rec, due)}",
        category=rec.category,
        amount=(amount if amount is not None else rec.amount),
        currency=rec.currency,
        expense_date=paid_on,
        payee_user_id=rec.payee_user_id,
        recurring_expense_id=rec.id,
        created_by=user.id,
    )
    db.add(exp)
    rec.last_paid_on = paid_on
    rec.next_due_date = next_occurrence(due, rec.frequency, rec.due_day)
    rec.reminders_sent = []
    flag_modified(rec, "reminders_sent")
    db.flush()
    details = f"{rec.description}: {rec.currency} {exp.amount} paid {paid_on.isoformat()} (next due {rec.next_due_date.isoformat()})"
    if note:
        details += f" — {note}"
    log_activity(db, user.id, "recurring_expense_paid", "recurring_expense", rec.id, details=details)
    return exp


def skip_period(db: Session, rec: RecurringExpense, user: User) -> None:
    """Move to the next period without recording a payment (bill waived, salary not due this month)."""
    skipped = rec.next_due_date
    rec.next_due_date = next_occurrence(skipped, rec.frequency, rec.due_day)
    rec.reminders_sent = []
    flag_modified(rec, "reminders_sent")
    db.flush()
    log_activity(db, user.id, "recurring_expense_skipped", "recurring_expense", rec.id, details=f"{rec.description}: skipped {period_label(rec, skipped)}")


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

def _recipients(db: Session) -> list[User]:
    return users_with_permission(db, EXPENSES_WRITE, include_admins=True)


def _reminder_text(rec: RecurringExpense, kind: str) -> tuple[str, str]:
    amount = f"{rec.currency} {rec.amount:,.2f}"
    payee = f" to {rec.payee.full_name or rec.payee.email}" if rec.payee_user_id and rec.payee else ""
    due = rec.next_due_date.strftime("%a %d %b")
    if kind == "overdue":
        return (f"Overdue: {rec.description}", f"{amount}{payee} was due on {due} and has not been marked paid.")
    days = int(kind)
    if days == 0:
        return (f"Due today: {rec.description}", f"{amount}{payee} is due today ({due}).")
    when = "tomorrow" if days == 1 else f"in {days} days"
    return (f"Due {when}: {rec.description}", f"{amount}{payee} is due {when}, on {due}.")


def _notify(db: Session, recipients: list[User], title: str, message: str) -> None:
    for u in recipients:
        db.add(Notification(user_id=u.id, title=title, message=message, link=REMINDER_LINK, type="expense"))
    db.flush()
    for u in recipients:
        try:
            email_service.send_notification(u.email, title, message, REMINDER_LINK)
        except Exception:
            logger.exception("expense reminder email failed for %s", u.email)


def send_due_reminders(db: Session, today: date | None = None) -> int:
    """One pass over active bills. Returns how many reminders were created."""
    today = today or date.today()
    horizon = today + timedelta(days=31)
    rows = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.is_active.is_(True), RecurringExpense.next_due_date <= horizon)
        .all()
    )
    if not rows:
        return 0
    recipients = _recipients(db)
    if not recipients:
        return 0
    sent = 0
    for rec in rows:
        due_key = rec.next_due_date.isoformat()
        already = set(rec.reminders_sent or [])
        pending: list[str] = []
        gap = (rec.next_due_date - today).days
        for d in (rec.remind_days_before if rec.remind_days_before is not None else DEFAULT_REMIND_DAYS):
            # Send the "N days before" reminder on that day, or late if the scheduler missed it,
            # but never after the bill is already due (the overdue notice covers that).
            if 0 <= gap <= int(d) and f"{due_key}:{d}" not in already:
                pending.append(str(d))
        if gap < 0 and f"{due_key}:overdue" not in already:
            pending.append("overdue")
        if not pending:
            continue
        # Collapse: if several thresholds are hit at once (missed days), send only the closest one.
        kinds = ["overdue"] if "overdue" in pending else [min(pending, key=int)]
        for kind in kinds:
            title, message = _reminder_text(rec, kind)
            _notify(db, recipients, title, message)
            sent += 1
        for k in pending:
            already.add(f"{due_key}:{k}")
        rec.reminders_sent = sorted(already)
        flag_modified(rec, "reminders_sent")
    db.commit()
    return sent


# ---------------------------------------------------------------------------
# Payroll: one salary bill per employee
# ---------------------------------------------------------------------------

def salary_for(db: Session, user_id: UUID) -> RecurringExpense | None:
    return (
        db.query(RecurringExpense)
        .filter(RecurringExpense.payee_user_id == user_id, RecurringExpense.category == "salary")
        .order_by(RecurringExpense.created_at.desc())
        .first()
    )


def upsert_salary(
    db: Session,
    employee: User,
    actor: User,
    amount: Decimal,
    currency: str,
    due_day: int,
    frequency: str = "monthly",
    is_active: bool = True,
) -> RecurringExpense:
    rec = salary_for(db, employee.id)
    name = employee.full_name or employee.email
    if rec is None:
        rec = RecurringExpense(
            description=f"Salary — {name}",
            category="salary",
            amount=amount,
            currency=currency,
            frequency=frequency,
            due_day=due_day,
            next_due_date=first_due_date(date.today(), frequency, due_day),
            payee_user_id=employee.id,
            is_active=is_active,
            remind_days_before=list(DEFAULT_REMIND_DAYS),
            reminders_sent=[],
            created_by=actor.id,
        )
        db.add(rec)
        db.flush()
        log_activity(db, actor.id, "salary_set", "recurring_expense", rec.id, details=f"{name}: {currency} {amount} on day {due_day}")
        return rec
    changed = rec.amount != amount or rec.currency != currency or rec.due_day != due_day or rec.frequency != frequency or rec.is_active != is_active
    rec.description = f"Salary — {name}"
    rec.amount = amount
    rec.currency = currency
    rec.frequency = frequency
    if rec.due_day != due_day:
        rec.due_day = due_day
        # Re-anchor the upcoming date to the new pay day without skipping a period.
        rec.next_due_date = first_due_date(max(date.today(), rec.last_paid_on + timedelta(days=1) if rec.last_paid_on else date.today()), frequency, due_day)
        rec.reminders_sent = []
        flag_modified(rec, "reminders_sent")
    rec.is_active = is_active
    db.flush()
    if changed:
        log_activity(db, actor.id, "salary_updated", "recurring_expense", rec.id, details=f"{name}: {currency} {amount} on day {due_day}")
    return rec
