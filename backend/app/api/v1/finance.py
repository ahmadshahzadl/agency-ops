from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Invoice as InvoiceModel,
    Payment as PaymentModel,
    Expense as ExpenseModel,
    Client as ClientModel,
    Project as ProjectModel,
)
from app.schemas.finance import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    PaymentCreate, PaymentResponse,
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
)
import uuid as uuid_mod
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import func
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.cleanup_service import purge_entity_artifacts
from app.services.activity_service import log_activity
from app.core.money import validate_currency, validate_positive_amount

router = APIRouter(tags=["finance"])


def paid_total_for(db: Session, invoice_id: UUID) -> Decimal:
    return db.query(func.coalesce(func.sum(PaymentModel.amount), 0)).filter(
        PaymentModel.invoice_id == invoice_id
    ).scalar() or Decimal("0")


def _apply_overdue(db: Session, invoices: list) -> None:
    """Lazily persist 'overdue' on sent invoices past their due date."""
    today = date.today()
    changed = False
    for inv in invoices:
        if inv.status == "sent" and inv.due_date and inv.due_date < today:
            inv.status = "overdue"
            changed = True
    if changed:
        db.commit()


def generate_invoice_number(db: Session) -> str:
    """Unique INV-YYYYMM-XXXXXX; retries on the unlikely collision."""
    for _ in range(5):
        number = f"INV-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}"
        if not db.query(InvoiceModel.id).filter(InvoiceModel.number == number).first():
            return number
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate a unique invoice number")


def _can_access_invoice_client(
    client_id: UUID,
    db: Session,
    team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
) -> bool:
    if is_admin:
        return True
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        return False
    if manager_scope is not None:
        return client.created_by is not None and client.created_by in manager_scope
    return client.team_id and client.team_id in team_ids


def _can_access_expense_project(
    expense: ExpenseModel,
    team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
) -> bool:
    if is_admin:
        return True
    if manager_scope is not None:
        return expense.project_id and expense.project and expense.project.owner_id in manager_scope
    if not expense.project_id or not expense.project or not expense.project.client:
        return False
    return expense.project.client.team_id in team_ids


# --- Invoices ---
@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    client_id: UUID | None = None,
    status_filter: str | None = None,
):
    qry = db.query(InvoiceModel).join(ClientModel)
    if "admin:all" not in permissions:
        if manager_scope is not None:
            qry = qry.filter(ClientModel.created_by.in_(manager_scope))
        elif not team_ids:
            return []
        else:
            qry = qry.filter(ClientModel.team_id.in_(team_ids))
    if client_id:
        qry = qry.filter(InvoiceModel.client_id == client_id)
    if status_filter:
        qry = qry.filter(InvoiceModel.status == status_filter)
    rows = qry.offset(skip).limit(limit).all()
    _apply_overdue(db, rows)
    return rows


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    if not _can_access_invoice_client(data.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create invoice for this client")
    if not db.query(ClientModel.id).filter(ClientModel.id == data.client_id, ClientModel.deleted_at.is_(None)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client is deleted; cannot create new invoices for it")
    validate_currency(data.currency)
    validate_positive_amount(data.amount)
    if db.query(InvoiceModel.id).filter(InvoiceModel.number == data.number).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invoice number {data.number} already exists")
    inv = InvoiceModel(
        client_id=data.client_id,
        project_id=data.project_id,
        number=data.number,
        amount=data.amount,
        currency=data.currency,
        status=data.status,
        due_date=data.due_date,
        issued_at=data.issued_at,
    )
    db.add(inv)
    db.flush()
    log_activity(db, user.id, "invoice_created", "invoice", inv.id, details=f"Invoice #{inv.number}: {inv.currency} {inv.amount}")
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    inv = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if not _can_access_invoice_client(inv.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    _apply_overdue(db, [inv])
    inv.paid_total = paid_total_for(db, inv.id)
    return inv


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    inv = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if not _can_access_invoice_client(inv.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    updates = data.model_dump(exclude_unset=True)
    if "amount" in updates:
        validate_positive_amount(updates["amount"])
        paid = paid_total_for(db, inv.id)
        if updates["amount"] < paid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Amount cannot be below the {paid} already paid")
    if "number" in updates and updates["number"] != inv.number:
        if db.query(InvoiceModel.id).filter(InvoiceModel.number == updates["number"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invoice number {updates['number']} already exists")
    for k, v in updates.items():
        setattr(inv, k, v)
    db.flush()
    log_activity(db, user.id, "invoice_updated", "invoice", invoice_id, details=f"Invoice #{inv.number}: {inv.currency} {inv.amount}")
    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    inv = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if not _can_access_invoice_client(inv.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    purge_entity_artifacts(db, "invoice", inv.id)
    db.delete(inv)
    db.commit()


# --- Payments ---
@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    invoice = db.query(InvoiceModel).filter(InvoiceModel.id == data.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if not _can_access_invoice_client(invoice.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    validate_positive_amount(data.amount)
    already_paid = paid_total_for(db, invoice.id)
    remaining = invoice.amount - already_paid
    if data.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment exceeds the remaining balance ({remaining} {invoice.currency})",
        )
    pay = PaymentModel(
        invoice_id=data.invoice_id,
        amount=data.amount,
        paid_at=data.paid_at,
        reference=data.reference,
    )
    db.add(pay)
    db.flush()
    # Reconcile invoice status with its payments
    if already_paid + data.amount >= invoice.amount:
        invoice.status = "paid"
    elif invoice.status == "draft":
        invoice.status = "sent"
    log_activity(db, user.id, "payment_created", "payment", pay.id, details=f"Payment: {pay.amount} {invoice.currency} on invoice #{invoice.number}")
    db.commit()
    db.refresh(pay)
    return pay


@router.get("/invoices/{invoice_id}/payments", response_model=list[PaymentResponse])
def list_invoice_payments(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if not invoice or not _can_access_invoice_client(invoice.client_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return db.query(PaymentModel).filter(PaymentModel.invoice_id == invoice_id).order_by(PaymentModel.paid_at).all()


# --- Expenses (Admin only per roles-permissions-flow: Manager and Employee have no access) ---
@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    db: Session = Depends(get_db),
    user=Depends(require_permission("expenses:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: UUID | None = None,
):
    qry = db.query(ExpenseModel)
    if "admin:all" not in permissions:
        if manager_scope is not None:
            qry = qry.join(ProjectModel).filter(ProjectModel.owner_id.in_(manager_scope))
        elif not team_ids:
            return []
        else:
            qry = qry.join(ProjectModel).join(ClientModel).filter(ClientModel.team_id.in_(team_ids))
    if project_id:
        qry = qry.filter(ExpenseModel.project_id == project_id)
    return qry.offset(skip).limit(limit).all()


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("expenses:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    if data.project_id and "admin:all" not in permissions:
        proj = db.query(ProjectModel).filter(ProjectModel.id == data.project_id).first()
        if proj:
            if manager_scope is not None:
                if proj.owner_id not in manager_scope:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create expense for this project")
            elif not proj.client or proj.client.team_id not in team_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create expense for this project")
    validate_currency(data.currency)
    validate_positive_amount(data.amount)
    exp = ExpenseModel(
        project_id=data.project_id,
        description=data.description,
        amount=data.amount,
        currency=data.currency,
        expense_date=data.expense_date,
        created_by=user.id,
    )
    db.add(exp)
    db.flush()
    log_activity(db, user.id, "expense_created", "expense", exp.id, details=f"Expense: {exp.description or '—'} {exp.currency} {exp.amount}")
    db.commit()
    db.refresh(exp)
    return exp


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("expenses:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if not _can_access_expense_project(exp, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    validate_positive_amount(data.amount)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(exp, k, v)
    db.flush()
    log_activity(db, user.id, "expense_updated", "expense", expense_id, details=f"Expense: {exp.description or '—'} {exp.currency} {exp.amount}")
    db.commit()
    db.refresh(exp)
    return exp


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("expenses:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if not _can_access_expense_project(exp, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    log_activity(db, user.id, "expense_deleted", "expense", expense_id, details=f"Expense deleted: {exp.description or '—'} {exp.currency} {exp.amount}")
    purge_entity_artifacts(db, "expense", exp.id)
    db.delete(exp)
    db.commit()
