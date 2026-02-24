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
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids

router = APIRouter(tags=["finance"])


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
    return qry.offset(skip).limit(limit).all()


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
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(inv, k, v)
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
    db.delete(inv)
    db.commit()


# --- Payments ---
@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("finance:write")),
):
    pay = PaymentModel(
        invoice_id=data.invoice_id,
        amount=data.amount,
        paid_at=data.paid_at,
        reference=data.reference,
    )
    db.add(pay)
    db.commit()
    db.refresh(pay)
    return pay


# --- Expenses ---
@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:read")),
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
    user=Depends(require_permission("finance:write")),
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
    exp = ExpenseModel(
        project_id=data.project_id,
        description=data.description,
        amount=data.amount,
        currency=data.currency,
        expense_date=data.expense_date,
        created_by=user.id,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if not _can_access_expense_project(exp, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(exp, k, v)
    db.commit()
    db.refresh(exp)
    return exp


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if not _can_access_expense_project(exp, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    db.delete(exp)
    db.commit()
