"""Recurring bills, subscriptions and salaries, plus the payroll view. Admin-only via expenses:*."""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.core.money import validate_currency, validate_positive_amount
from app.database import get_db
from app.models import Expense as ExpenseModel, Project as ProjectModel, RecurringExpense as RecModel, User as UserModel
from app.schemas.finance import EXPENSE_CATEGORIES, ExpenseResponse
from app.schemas.recurring_expense import (
    EMPLOYMENT_TYPES, FREQUENCIES,
    PayrollRow, PayrollUpdate,
    RecurringExpenseCreate, RecurringExpenseResponse, RecurringExpenseUpdate, RecurringPayIn,
)
from app.services import recurring_expense_service as svc
from app.services.activity_service import log_activity, notifications_updated_this_request

router = APIRouter(tags=["recurring-expenses"])
READ = "expenses:read"
WRITE = "expenses:write"


def _out(rec: RecModel, today: date | None = None) -> RecurringExpenseResponse:
    return RecurringExpenseResponse(
        id=rec.id, description=rec.description, category=rec.category, amount=rec.amount, currency=rec.currency,
        frequency=rec.frequency, due_day=rec.due_day, project_id=rec.project_id, payee_user_id=rec.payee_user_id,
        notes=rec.notes, remind_days_before=list(rec.remind_days_before or []), next_due_date=rec.next_due_date,
        last_paid_on=rec.last_paid_on, is_active=rec.is_active, status=svc.status_of(rec, today), days_until_due=svc.days_until(rec, today),
        payee_name=((rec.payee.full_name or rec.payee.email) if rec.payee else None),
        project_name=(rec.project.name if rec.project else None),
        created_by=rec.created_by, created_at=rec.created_at, updated_at=rec.updated_at,
    )


def _validate(category: str | None, frequency: str | None, currency: str | None, remind: list[int] | None) -> None:
    if category is not None and category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"category must be one of: {', '.join(EXPENSE_CATEGORIES)}")
    if frequency is not None and frequency not in FREQUENCIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"frequency must be one of: {', '.join(FREQUENCIES)}")
    if currency is not None:
        validate_currency(currency)
    if remind is not None:
        if any(d < 0 or d > 30 for d in remind):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="remind_days_before values must be between 0 and 30")


def _get(db: Session, rec_id: UUID) -> RecModel:
    rec = db.query(RecModel).options(joinedload(RecModel.payee), joinedload(RecModel.project)).filter(RecModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring expense not found")
    return rec


def _project_exists(db: Session, project_id: UUID | None) -> None:
    if project_id and not db.query(ProjectModel.id).filter(ProjectModel.id == project_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


# ============================ recurring expenses ============================

@router.get("/recurring-expenses", response_model=list[RecurringExpenseResponse])
def list_recurring(
    db: Session = Depends(get_db),
    user=Depends(require_permission(READ)),
    include_inactive: bool = Query(False),
    category: str | None = None,
    due_within_days: int | None = Query(None, ge=0, le=365, description="Only bills due within N days (overdue included)"),
):
    qry = db.query(RecModel).options(joinedload(RecModel.payee), joinedload(RecModel.project))
    if not include_inactive:
        qry = qry.filter(RecModel.is_active.is_(True))
    if category:
        qry = qry.filter(RecModel.category == category)
    if due_within_days is not None:
        from datetime import timedelta
        qry = qry.filter(RecModel.next_due_date <= date.today() + timedelta(days=due_within_days))
    rows = qry.order_by(RecModel.next_due_date.asc(), RecModel.description.asc()).all()
    today = date.today()
    return [_out(r, today) for r in rows]


@router.post("/recurring-expenses", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_recurring(data: RecurringExpenseCreate, db: Session = Depends(get_db), user=Depends(require_permission(WRITE))):
    _validate(data.category, data.frequency, data.currency, data.remind_days_before)
    validate_positive_amount(data.amount)
    _project_exists(db, data.project_id)
    rec = RecModel(
        description=data.description.strip(), category=data.category, amount=data.amount, currency=data.currency,
        frequency=data.frequency, due_day=data.due_day,
        next_due_date=data.next_due_date or svc.first_due_date(date.today(), data.frequency, data.due_day),
        project_id=data.project_id, payee_user_id=data.payee_user_id, notes=data.notes, is_active=data.is_active,
        remind_days_before=sorted(set(data.remind_days_before), reverse=True), reminders_sent=[], created_by=user.id,
    )
    db.add(rec)
    db.flush()
    log_activity(db, user.id, "recurring_expense_created", "recurring_expense", rec.id, details=f"{rec.description}: {rec.currency} {rec.amount} {rec.frequency}")
    db.commit()
    return _out(_get(db, rec.id))


@router.get("/recurring-expenses/{rec_id}", response_model=RecurringExpenseResponse)
def get_recurring(rec_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(READ))):
    return _out(_get(db, rec_id))


@router.patch("/recurring-expenses/{rec_id}", response_model=RecurringExpenseResponse)
def update_recurring(rec_id: UUID, data: RecurringExpenseUpdate, db: Session = Depends(get_db), user=Depends(require_permission(WRITE))):
    rec = _get(db, rec_id)
    updates = data.model_dump(exclude_unset=True)
    _validate(updates.get("category"), updates.get("frequency"), updates.get("currency"), updates.get("remind_days_before"))
    if "amount" in updates:
        validate_positive_amount(updates["amount"])
    if "project_id" in updates:
        _project_exists(db, updates["project_id"])
    if "remind_days_before" in updates and updates["remind_days_before"] is not None:
        updates["remind_days_before"] = sorted(set(updates["remind_days_before"]), reverse=True)
    reschedule = ("due_day" in updates and updates["due_day"] != rec.due_day) or ("frequency" in updates and updates["frequency"] != rec.frequency)
    for k, v in updates.items():
        setattr(rec, k, v.strip() if k == "description" and isinstance(v, str) else v)
    if reschedule and "next_due_date" not in updates:
        rec.next_due_date = svc.first_due_date(date.today(), rec.frequency, rec.due_day)
    if reschedule or "next_due_date" in updates:
        rec.reminders_sent = []
    db.flush()
    log_activity(db, user.id, "recurring_expense_updated", "recurring_expense", rec.id, details=f"{rec.description}: {', '.join(sorted(updates))}")
    db.commit()
    return _out(_get(db, rec.id))


@router.delete("/recurring-expenses/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(rec_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(WRITE))):
    rec = _get(db, rec_id)
    log_activity(db, user.id, "recurring_expense_deleted", "recurring_expense", rec.id, details=rec.description)
    db.delete(rec)  # past Expense rows keep their data; the FK is SET NULL
    db.commit()


@router.post("/recurring-expenses/{rec_id}/pay", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def pay_recurring(rec_id: UUID, data: RecurringPayIn, db: Session = Depends(get_db), user=Depends(require_permission(WRITE))):
    rec = _get(db, rec_id)
    if data.amount is not None:
        validate_positive_amount(data.amount)
    exp = svc.record_payment(db, rec, user, paid_on=data.paid_on, amount=data.amount, note=data.note)
    db.commit()
    db.refresh(exp)
    out = ExpenseResponse.model_validate(exp)
    out.payee_name = (rec.payee.full_name or rec.payee.email) if rec.payee else None
    return out


@router.post("/recurring-expenses/{rec_id}/skip", response_model=RecurringExpenseResponse)
def skip_recurring(rec_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(WRITE))):
    rec = _get(db, rec_id)
    svc.skip_period(db, rec, user)
    db.commit()
    return _out(_get(db, rec.id))


@router.get("/recurring-expenses/{rec_id}/history", response_model=list[ExpenseResponse])
def recurring_history(rec_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission(READ)), limit: int = Query(24, ge=1, le=200)):
    rec = _get(db, rec_id)
    rows = (
        db.query(ExpenseModel).options(joinedload(ExpenseModel.payee))
        .filter(ExpenseModel.recurring_expense_id == rec.id)
        .order_by(ExpenseModel.expense_date.desc().nullslast(), ExpenseModel.created_at.desc())
        .limit(limit).all()
    )
    out = []
    for e in rows:
        r = ExpenseResponse.model_validate(e)
        r.payee_name = (e.payee.full_name or e.payee.email) if e.payee else None
        out.append(r)
    return out


@router.post("/recurring-expenses/run-reminders", status_code=status.HTTP_200_OK)
def run_reminders_now(db: Session = Depends(get_db), user=Depends(require_permission("admin:all"))):
    """Manual trigger (the scheduler does this hourly). Handy right after setting bills up."""
    n = svc.send_due_reminders(db)
    if n:
        notifications_updated_this_request.set(True)
    return {"sent": n}


# ============================ payroll ============================

def _paid_this_period(rec: RecModel) -> bool:
    """True if the most recent payment covered the period that ends at next_due_date."""
    if not rec.last_paid_on:
        return False
    prev_due = svc.next_occurrence(rec.next_due_date, rec.frequency, rec.due_day)
    # Length of one period, measured forward from next_due_date
    period = (prev_due - rec.next_due_date).days
    return (rec.next_due_date - rec.last_paid_on).days <= period


def _payroll_row(u: UserModel, rec: RecModel | None, today: date) -> PayrollRow:
    base = dict(
        user_id=u.id, full_name=u.full_name, email=u.email, job_title=u.job_title, employment_type=u.employment_type,
        joined_on=u.joined_on, left_on=u.left_on, is_active=u.is_active,
    )
    if rec is None:
        return PayrollRow(**base, status="not_set")
    return PayrollRow(
        **base, salary_id=rec.id, amount=rec.amount, currency=rec.currency, frequency=rec.frequency, due_day=rec.due_day,
        next_due_date=rec.next_due_date, last_paid_on=rec.last_paid_on, salary_active=rec.is_active,
        status=svc.status_of(rec, today), days_until_due=svc.days_until(rec, today), paid_this_period=_paid_this_period(rec),
    )


@router.get("/payroll", response_model=list[PayrollRow])
def list_payroll(db: Session = Depends(get_db), user=Depends(require_permission(READ)), include_inactive: bool = Query(False)):
    qry = db.query(UserModel).filter(UserModel.client_id.is_(None))
    if not include_inactive:
        qry = qry.filter(UserModel.is_active.is_(True))
    users = qry.order_by(UserModel.full_name.asc().nullslast(), UserModel.email.asc()).all()
    salaries = {
        r.payee_user_id: r
        for r in db.query(RecModel).filter(RecModel.category == "salary", RecModel.payee_user_id.isnot(None)).order_by(RecModel.created_at.asc()).all()
    }
    today = date.today()
    rows = [_payroll_row(u, salaries.get(u.id), today) for u in users]
    order = {"overdue": 0, "due_today": 1, "due_soon": 2, "scheduled": 3, "paused": 4, "not_set": 5}
    rows.sort(key=lambda r: (order.get(r.status, 9), r.next_due_date or date.max, (r.full_name or r.email).lower()))
    return rows


@router.patch("/payroll/{user_id}", response_model=PayrollRow)
def update_payroll(user_id: UUID, data: PayrollUpdate, db: Session = Depends(get_db), user=Depends(require_permission(WRITE))):
    emp = db.query(UserModel).filter(UserModel.id == user_id, UserModel.client_id.is_(None)).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    updates = data.model_dump(exclude_unset=True)
    if "employment_type" in updates and updates["employment_type"] is not None and updates["employment_type"] not in EMPLOYMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"employment_type must be one of: {', '.join(EMPLOYMENT_TYPES)}")
    for k in ("employment_type", "joined_on", "left_on", "job_title"):
        if k in updates:
            setattr(emp, k, updates[k])

    rec = svc.salary_for(db, emp.id)
    salary_fields = {k for k in ("amount", "currency", "due_day", "frequency", "salary_active") if k in updates}
    if salary_fields:
        amount = updates.get("amount", rec.amount if rec else None)
        currency = updates.get("currency", rec.currency if rec else "PKR")
        due_day = updates.get("due_day", rec.due_day if rec else 1)
        frequency = updates.get("frequency", rec.frequency if rec else "monthly")
        active = updates.get("salary_active", rec.is_active if rec else True)
        if amount is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount is required to set a salary")
        validate_positive_amount(Decimal(amount))
        _validate(None, frequency, currency, None)
        rec = svc.upsert_salary(db, emp, user, Decimal(amount), currency, int(due_day), frequency, bool(active))
    else:
        log_activity(db, user.id, "user_updated", "user", emp.id, details=f"Employment record updated: {emp.email}")
    db.commit()
    db.refresh(emp)
    if rec:
        db.refresh(rec)
    return _payroll_row(emp, rec, date.today())
