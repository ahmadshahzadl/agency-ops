"""Proposals/quotes: line-item quotes against a lead or client, with a
lifecycle (draft -> sent -> accepted/rejected), conversion to a project,
and fixed-price invoice generation from an accepted quote."""
import uuid as uuid_mod
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Quote as QuoteModel, QuoteItem as QuoteItemModel, Client as ClientModel, Lead as LeadModel, Project as ProjectModel, Invoice as InvoiceModel
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteResponse, QuoteItemResponse
from app.schemas.finance import InvoiceResponse
from app.schemas.project import ProjectResponse
from app.api.deps import require_permission, get_user_permissions, get_manager_scope_user_ids
from app.services.activity_service import log_activity
from app.services import email_service

router = APIRouter(prefix="/quotes", tags=["quotes"])

EDITABLE_STATUSES = ("draft", "sent")


def _quote_response(q: QuoteModel) -> QuoteResponse:
    return QuoteResponse(
        id=q.id,
        number=q.number,
        title=q.title,
        client_id=q.client_id,
        client_name=q.client.name if q.client else None,
        lead_id=q.lead_id,
        lead_company=q.lead.company_name if q.lead else None,
        status=q.status,
        currency=q.currency,
        total=q.total,
        valid_until=q.valid_until,
        terms=q.terms,
        project_id=q.project_id,
        accepted_at=q.accepted_at,
        created_by=q.created_by,
        created_at=q.created_at,
        items=[
            QuoteItemResponse(
                id=i.id, description=i.description, quantity=i.quantity,
                unit_price=i.unit_price, position=i.position,
                line_total=(i.quantity * i.unit_price).quantize(Decimal("0.01")),
            )
            for i in q.items
        ],
    )


def _get_scoped_quote(db, quote_id, user, permissions, manager_scope) -> QuoteModel:
    q = db.query(QuoteModel).options(
        joinedload(QuoteModel.items), joinedload(QuoteModel.client), joinedload(QuoteModel.lead)
    ).filter(QuoteModel.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    if "admin:all" in permissions:
        return q
    if q.created_by == user.id:
        return q
    if manager_scope is not None and q.created_by is not None and q.created_by in manager_scope:
        return q
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")


def _apply_items(db, quote: QuoteModel, items) -> None:
    for old in list(quote.items):
        db.delete(old)
    db.flush()
    total = Decimal("0")
    for pos, item in enumerate(items):
        if item.quantity <= 0 or item.unit_price < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item quantity must be positive and price non-negative")
        db.add(QuoteItemModel(
            quote_id=quote.id,
            description=item.description.strip(),
            quantity=item.quantity,
            unit_price=item.unit_price,
            position=pos,
        ))
        total += item.quantity * item.unit_price
    quote.total = total.quantize(Decimal("0.01"))


def _validate_currency(currency: str | None) -> None:
    if currency is not None and (len(currency) != 3 or not currency.isalpha()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="currency must be a 3-letter code, e.g. USD")


def _validate_target(db, client_id, lead_id) -> None:
    if not client_id and not lead_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A quote needs a client_id or a lead_id")
    if client_id and not db.query(ClientModel).filter(ClientModel.id == client_id, ClientModel.deleted_at.is_(None)).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if lead_id and not db.query(LeadModel).filter(LeadModel.id == lead_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")


@router.get("", response_model=list[QuoteResponse])
def list_quotes(
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
    status_filter: str | None = None,
    client_id: UUID | None = None,
    lead_id: UUID | None = None,
):
    qry = db.query(QuoteModel).options(
        joinedload(QuoteModel.items), joinedload(QuoteModel.client), joinedload(QuoteModel.lead)
    )
    if "admin:all" not in permissions:
        if manager_scope is not None:
            qry = qry.filter(QuoteModel.created_by.in_(manager_scope))
        else:
            qry = qry.filter(QuoteModel.created_by == user.id)
    if status_filter:
        qry = qry.filter(QuoteModel.status == status_filter)
    if client_id:
        qry = qry.filter(QuoteModel.client_id == client_id)
    if lead_id:
        qry = qry.filter(QuoteModel.lead_id == lead_id)
    return [_quote_response(q) for q in qry.order_by(QuoteModel.created_at.desc()).all()]


@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
def create_quote(
    data: QuoteCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
):
    _validate_target(db, data.client_id, data.lead_id)
    _validate_currency(data.currency)
    quote = QuoteModel(
        number=f"QUO-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}",
        title=data.title.strip(),
        client_id=data.client_id,
        lead_id=data.lead_id,
        currency=data.currency,
        valid_until=data.valid_until,
        terms=data.terms,
        created_by=user.id,
    )
    db.add(quote)
    db.flush()
    _apply_items(db, quote, data.items)
    log_activity(db, user.id, "quote_created", "quote", quote.id, details=f"Quote {quote.number}: {quote.title}")
    db.commit()
    db.refresh(quote)
    return _quote_response(quote)


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    return _quote_response(_get_scoped_quote(db, quote_id, user, permissions, manager_scope))


@router.patch("/{quote_id}", response_model=QuoteResponse)
def update_quote(
    quote_id: UUID,
    data: QuoteUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {quote.status} quote cannot be edited")
    updates = data.model_dump(exclude_unset=True)
    items = updates.pop("items", None)
    _validate_currency(updates.get("currency"))
    if "client_id" in updates or "lead_id" in updates:
        _validate_target(db, updates.get("client_id", quote.client_id), updates.get("lead_id", quote.lead_id))
    for k, v in updates.items():
        setattr(quote, k, v)
    if items is not None:
        _apply_items(db, quote, data.items)
    db.commit()
    db.refresh(quote)
    return _quote_response(quote)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status == "accepted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Accepted quotes cannot be deleted")
    log_activity(db, user.id, "quote_deleted", "quote", None, details=f"Quote deleted: {quote.number}")
    db.delete(quote)
    db.commit()


@router.post("/{quote_id}/send", response_model=QuoteResponse)
def send_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {quote.status} quote cannot be sent")
    quote.status = "sent"
    log_activity(db, user.id, "quote_sent", "quote", quote.id, details=f"Quote sent: {quote.number}")
    db.commit()
    db.refresh(quote)
    recipient = (quote.client.contact_email if quote.client else None) or (quote.lead.contact_email if quote.lead else None)
    if recipient:
        lines = "".join(
            f"<tr><td style='padding:6px 12px 6px 0;'>{i.description}</td>"
            f"<td style='padding:6px 12px;text-align:right;'>{i.quantity}</td>"
            f"<td style='padding:6px 0;text-align:right;'>{(i.quantity * i.unit_price).quantize(Decimal('0.01'))} {quote.currency}</td></tr>"
            for i in quote.items
        )
        body = (
            f"<p>Please find our proposal <b>{quote.title}</b> ({quote.number}) below.</p>"
            f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>{lines}</table>"
            f"<p style='margin-top:16px;font-weight:700;'>Total: {quote.total} {quote.currency}</p>"
            + (f"<p>Valid until: {quote.valid_until}</p>" if quote.valid_until else "")
            + (f"<p style='color:#6b7280;font-size:13px;'>{quote.terms}</p>" if quote.terms else "")
        )
        email_service.send_email(
            recipient,
            f"Proposal {quote.number}: {quote.title}",
            email_service._build_html(f"Proposal: {quote.title}", body),
            f"Proposal {quote.number}: {quote.title}\nTotal: {quote.total} {quote.currency}",
        )
    return _quote_response(quote)


@router.post("/{quote_id}/accept", response_model=QuoteResponse)
def accept_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {quote.status} quote cannot be accepted")
    quote.status = "accepted"
    quote.accepted_at = datetime.utcnow()
    log_activity(db, user.id, "quote_accepted", "quote", quote.id, details=f"Quote accepted: {quote.number} ({quote.total} {quote.currency})")
    db.commit()
    db.refresh(quote)
    return _quote_response(quote)


@router.post("/{quote_id}/reject", response_model=QuoteResponse)
def reject_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {quote.status} quote cannot be rejected")
    quote.status = "rejected"
    log_activity(db, user.id, "quote_rejected", "quote", quote.id, details=f"Quote rejected: {quote.number}")
    db.commit()
    db.refresh(quote)
    return _quote_response(quote)


@router.post("/{quote_id}/convert", response_model=ProjectResponse)
def convert_quote_to_project(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("quotes:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Create a project from an accepted quote. Requires a client (convert the lead first if needed)."""
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status != "accepted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only accepted quotes can be converted")
    if quote.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quote is already converted")
    client_id = quote.client_id
    if not client_id and quote.lead is not None:
        client_id = quote.lead.converted_to_client_id
    if not client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quote has no client; convert the lead to a client first")
    project = ProjectModel(
        client_id=client_id,
        name=quote.title,
        description=f"Created from quote {quote.number}",
        status="active",
        pipeline_stage="development",
        owner_id=user.id,
    )
    db.add(project)
    db.flush()
    quote.project_id = project.id
    if not quote.client_id:
        quote.client_id = client_id
    log_activity(db, user.id, "quote_converted", "project", project.id, details=f"Project from quote {quote.number}: {project.name}")
    db.commit()
    db.refresh(project)
    return project


@router.post("/{quote_id}/invoice", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def invoice_from_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("finance:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Fixed-price billing: draft invoice for the full total of an accepted quote."""
    quote = _get_scoped_quote(db, quote_id, user, permissions, manager_scope)
    if quote.status != "accepted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only accepted quotes can be invoiced")
    client_id = quote.client_id or (quote.lead.converted_to_client_id if quote.lead else None)
    if not client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quote has no client; convert the lead to a client first")
    number = f"INV-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}"
    invoice = InvoiceModel(
        client_id=client_id,
        project_id=quote.project_id,
        number=number,
        amount=quote.total,
        currency=quote.currency,
        status="draft",
        issued_at=date.today(),
    )
    db.add(invoice)
    db.flush()
    log_activity(db, user.id, "invoice_generated_from_quote", "invoice", invoice.id, details=f"Invoice {number} from quote {quote.number}: {quote.total} {quote.currency}")
    db.commit()
    db.refresh(invoice)
    return invoice
