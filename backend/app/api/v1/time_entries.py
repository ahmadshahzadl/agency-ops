"""Time tracking: log hours against projects/tasks, review timesheets,
and (finance) generate invoices from unbilled billable time."""
import uuid as uuid_mod
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import TimeEntry as TimeEntryModel, Project as ProjectModel, Task as TaskModel, User as UserModel, Invoice as InvoiceModel
from app.schemas.time_entry import (
    TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse,
    TimeSummaryResponse, TimeSummaryUser, InvoiceFromTimeRequest,
)
from app.schemas.finance import InvoiceResponse
from app.api.deps import require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity

router = APIRouter(tags=["time"])


def _entry_response(e: TimeEntryModel) -> TimeEntryResponse:
    return TimeEntryResponse(
        id=e.id,
        user_id=e.user_id,
        user_name=(e.user.full_name or e.user.email) if e.user else None,
        project_id=e.project_id,
        project_name=e.project.name if e.project else None,
        task_id=e.task_id,
        task_title=e.task.title if e.task else None,
        work_date=e.work_date,
        hours=e.hours,
        description=e.description,
        billable=e.billable,
        hourly_rate=e.hourly_rate,
        invoice_id=e.invoice_id,
        created_at=e.created_at,
    )


def _visible_user_ids(user, permissions, manager_scope) -> set[UUID] | None:
    """None = all users (admin). Else the set of user ids whose entries are visible."""
    if "admin:all" in permissions:
        return None
    if manager_scope is not None:
        return manager_scope
    return {user.id}


def _validate_entry_fields(hours: Decimal | None) -> None:
    if hours is not None and (hours <= 0 or hours > 24):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hours must be between 0 and 24")


@router.get("/time-entries", response_model=list[TimeEntryResponse])
def list_time_entries(
    db: Session = Depends(get_db),
    user=Depends(require_permission("time:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
    project_id: UUID | None = None,
    task_id: UUID | None = None,
    user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    unbilled: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    qry = db.query(TimeEntryModel).options(
        joinedload(TimeEntryModel.user), joinedload(TimeEntryModel.project), joinedload(TimeEntryModel.task)
    )
    visible = _visible_user_ids(user, permissions, manager_scope)
    if visible is not None:
        qry = qry.filter(TimeEntryModel.user_id.in_(visible))
    if user_id:
        if visible is not None and user_id not in visible:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your report")
        qry = qry.filter(TimeEntryModel.user_id == user_id)
    if project_id:
        qry = qry.filter(TimeEntryModel.project_id == project_id)
    if task_id:
        qry = qry.filter(TimeEntryModel.task_id == task_id)
    if date_from:
        qry = qry.filter(TimeEntryModel.work_date >= date_from)
    if date_to:
        qry = qry.filter(TimeEntryModel.work_date <= date_to)
    if unbilled:
        qry = qry.filter(TimeEntryModel.invoice_id.is_(None))
    rows = qry.order_by(TimeEntryModel.work_date.desc(), TimeEntryModel.created_at.desc()).offset(skip).limit(limit).all()
    return [_entry_response(e) for e in rows]


@router.post("/time-entries", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
def create_time_entry(
    data: TimeEntryCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("time:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    _validate_entry_fields(data.hours)
    target_user_id = user.id
    if data.user_id and data.user_id != user.id:
        visible = _visible_user_ids(user, permissions, manager_scope)
        if visible is not None and data.user_id not in visible:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only log time for yourself or your reports")
        target_user_id = data.user_id

    task = None
    project_id = data.project_id
    if data.task_id:
        task = db.query(TaskModel).filter(TaskModel.id == data.task_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if project_id is None:
            project_id = task.project_id
        elif task.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task does not belong to that project")
    if project_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id (or a task with a project) is required")
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    entry = TimeEntryModel(
        user_id=target_user_id,
        project_id=project_id,
        task_id=data.task_id,
        work_date=data.work_date,
        hours=data.hours,
        description=(data.description or "").strip() or None,
        billable=data.billable,
        hourly_rate=data.hourly_rate,
    )
    db.add(entry)
    db.flush()
    log_activity(db, user.id, "time_logged", "project", project_id, details=f"{data.hours}h on {proj.name}")
    db.commit()
    db.refresh(entry)
    entry = db.query(TimeEntryModel).options(
        joinedload(TimeEntryModel.user), joinedload(TimeEntryModel.project), joinedload(TimeEntryModel.task)
    ).filter(TimeEntryModel.id == entry.id).first()
    return _entry_response(entry)


def _get_editable_entry(db, entry_id, user, permissions, manager_scope) -> TimeEntryModel:
    entry = db.query(TimeEntryModel).filter(TimeEntryModel.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found")
    visible = _visible_user_ids(user, permissions, manager_scope)
    if visible is not None and entry.user_id not in visible:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found")
    if entry.invoice_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entry is billed on an invoice and locked; delete the invoice to unlock")
    return entry


@router.patch("/time-entries/{entry_id}", response_model=TimeEntryResponse)
def update_time_entry(
    entry_id: UUID,
    data: TimeEntryUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("time:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    entry = _get_editable_entry(db, entry_id, user, permissions, manager_scope)
    updates = data.model_dump(exclude_unset=True)
    _validate_entry_fields(updates.get("hours"))
    if "task_id" in updates and updates["task_id"] is not None:
        task = db.query(TaskModel).filter(TaskModel.id == updates["task_id"]).first()
        if not task or task.project_id != entry.project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task does not belong to the entry's project")
    for k, v in updates.items():
        setattr(entry, k, v)
    db.commit()
    db.refresh(entry)
    return _entry_response(entry)


@router.delete("/time-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("time:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    entry = _get_editable_entry(db, entry_id, user, permissions, manager_scope)
    db.delete(entry)
    db.commit()


@router.get("/time-entries/summary", response_model=TimeSummaryResponse)
def time_summary(
    db: Session = Depends(get_db),
    user=Depends(require_permission("time:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
    project_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    qry = db.query(TimeEntryModel).options(joinedload(TimeEntryModel.user), joinedload(TimeEntryModel.project))
    visible = _visible_user_ids(user, permissions, manager_scope)
    if visible is not None:
        qry = qry.filter(TimeEntryModel.user_id.in_(visible))
    if project_id:
        qry = qry.filter(TimeEntryModel.project_id == project_id)
    if date_from:
        qry = qry.filter(TimeEntryModel.work_date >= date_from)
    if date_to:
        qry = qry.filter(TimeEntryModel.work_date <= date_to)
    entries = qry.all()

    total = Decimal("0")
    billable = Decimal("0")
    unbilled = Decimal("0")
    unbilled_amount = Decimal("0")
    per_user: dict[UUID, TimeSummaryUser] = {}
    for e in entries:
        total += e.hours
        if e.billable:
            billable += e.hours
            if e.invoice_id is None:
                unbilled += e.hours
                rate = e.hourly_rate if e.hourly_rate is not None else (e.project.hourly_rate if e.project else None)
                if rate is not None:
                    unbilled_amount += e.hours * rate
        if e.user_id not in per_user:
            per_user[e.user_id] = TimeSummaryUser(
                user_id=e.user_id,
                user_name=(e.user.full_name or e.user.email) if e.user else None,
                hours=Decimal("0"),
            )
        per_user[e.user_id].hours += e.hours
    return TimeSummaryResponse(
        total_hours=total,
        billable_hours=billable,
        unbilled_billable_hours=unbilled,
        unbilled_amount=unbilled_amount,
        by_user=sorted(per_user.values(), key=lambda u: -u.hours),
    )


@router.post("/invoices/from-time", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def invoice_from_time(
    data: InvoiceFromTimeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from app.api.v1.finance import _can_access_invoice_client, generate_invoice_number
    from app.core.money import validate_currency
    validate_currency(data.currency)
    proj = db.query(ProjectModel).filter(ProjectModel.id == data.project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_invoice_client(proj.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    qry = db.query(TimeEntryModel).filter(
        TimeEntryModel.project_id == proj.id,
        TimeEntryModel.billable == True,
        TimeEntryModel.invoice_id.is_(None),
    )
    if data.date_from:
        qry = qry.filter(TimeEntryModel.work_date >= data.date_from)
    if data.date_to:
        qry = qry.filter(TimeEntryModel.work_date <= data.date_to)
    entries = qry.all()
    if not entries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No unbilled billable time entries in that range")

    amount = Decimal("0")
    for e in entries:
        rate = e.hourly_rate if e.hourly_rate is not None else (data.hourly_rate if data.hourly_rate is not None else proj.hourly_rate)
        if rate is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hourly rate available: set the project's rate, pass hourly_rate, or set rates on the entries",
            )
        amount += e.hours * rate
    amount = amount.quantize(Decimal("0.01"))

    if data.number:
        number = data.number
        if db.query(InvoiceModel).filter(InvoiceModel.number == number).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice number already exists")
    else:
        number = generate_invoice_number(db)
    invoice = InvoiceModel(
        client_id=proj.client_id,
        project_id=proj.id,
        number=number,
        amount=amount,
        currency=data.currency,
        status="draft",
        due_date=data.due_date,
        issued_at=date.today(),
    )
    db.add(invoice)
    db.flush()
    for e in entries:
        e.invoice_id = invoice.id
    total_hours = sum((e.hours for e in entries), Decimal("0"))
    log_activity(db, user.id, "invoice_generated_from_time", "invoice", invoice.id,
                 details=f"Invoice {number}: {total_hours}h on {proj.name} = {amount} {data.currency}")
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices/{invoice_id}/time-entries", response_model=list[TimeEntryResponse])
def invoice_time_entries(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from app.api.v1.finance import _can_access_invoice_client
    invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if not invoice or not _can_access_invoice_client(invoice.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    rows = (
        db.query(TimeEntryModel)
        .options(joinedload(TimeEntryModel.user), joinedload(TimeEntryModel.project), joinedload(TimeEntryModel.task))
        .filter(TimeEntryModel.invoice_id == invoice_id)
        .order_by(TimeEntryModel.work_date)
        .all()
    )
    return [_entry_response(e) for e in rows]
