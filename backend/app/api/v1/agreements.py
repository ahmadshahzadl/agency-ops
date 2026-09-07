"""Service agreements: contract records built from a minimal editable
clause template, with a lifecycle (draft -> sent -> signed/declined),
branded PDFs, email delivery, and clickwrap acceptance via the client
portal. Signed agreements are immutable — like paid invoices."""
import uuid as uuid_mod
from datetime import datetime, date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    Agreement as AgreementModel, Client as ClientModel, Project as ProjectModel,
    Quote as QuoteModel, Milestone as MilestoneModel,
)
from app.schemas.agreement import (
    AgreementCreate, AgreementUpdate, AgreementResponse, AgreementTemplateResponse, ClauseIn,
)
from app.api.deps import require_permission, get_user_permissions, get_manager_scope_user_ids
from app.services.activity_service import log_activity
from app.services import email_service
from app.services.agreement_template import default_clauses, scope_from_quote, timeline_from_milestones
from app.core.money import validate_currency as _validate_currency

router = APIRouter(prefix="/agreements", tags=["agreements"])

EDITABLE_STATUSES = ("draft", "sent", "expired")  # signed/declined/terminated are frozen records


def _apply_expiry(db: Session, agreements: list[AgreementModel]) -> None:
    """Lazily persist 'expired' on unsigned agreements past their signature deadline."""
    today = date.today()
    changed = False
    for a in agreements:
        if a.status in ("draft", "sent") and a.valid_until and a.valid_until < today:
            a.status = "expired"
            changed = True
    if changed:
        db.commit()


def _response(a: AgreementModel) -> AgreementResponse:
    return AgreementResponse(
        id=a.id, number=a.number, title=a.title,
        client_id=a.client_id, client_name=a.client.name if a.client else None,
        project_id=a.project_id, project_name=a.project.name if a.project else None,
        quote_id=a.quote_id, quote_number=a.quote.number if a.quote else None,
        status=a.status, effective_date=a.effective_date, valid_until=a.valid_until,
        contract_value=a.contract_value, currency=a.currency,
        clauses=[ClauseIn(**c) for c in (a.clauses or [])],
        accepted_at=a.accepted_at, accepted_by_name=a.accepted_by_name,
        accepted_ip=a.accepted_ip, acceptance_method=a.acceptance_method,
        decline_reason=a.decline_reason,
        terminated_at=a.terminated_at, termination_reason=a.termination_reason,
        created_by=a.created_by, created_at=a.created_at,
    )


def _get_scoped(db, agreement_id, user, permissions, manager_scope) -> AgreementModel:
    a = db.query(AgreementModel).options(
        joinedload(AgreementModel.client), joinedload(AgreementModel.project), joinedload(AgreementModel.quote)
    ).filter(AgreementModel.id == agreement_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found")
    if "admin:all" in permissions or a.created_by == user.id:
        return a
    if manager_scope is not None and a.created_by is not None and a.created_by in manager_scope:
        return a
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found")


def _get_scoped_current(db, agreement_id, user, permissions, manager_scope) -> AgreementModel:
    a = _get_scoped(db, agreement_id, user, permissions, manager_scope)
    _apply_expiry(db, [a])
    return a


def _validate_links(db, data: dict) -> None:
    if data.get("client_id") and not db.query(ClientModel.id).filter(
        ClientModel.id == data["client_id"], ClientModel.deleted_at.is_(None)
    ).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if data.get("project_id") and not db.query(ProjectModel.id).filter(
        ProjectModel.id == data["project_id"], ProjectModel.deleted_at.is_(None)
    ).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if data.get("quote_id") and not db.query(QuoteModel.id).filter(QuoteModel.id == data["quote_id"]).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")


def _require_editable(a: AgreementModel) -> None:
    if a.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A {a.status} agreement is a frozen record and cannot be modified",
        )


@router.get("/template", response_model=AgreementTemplateResponse)
def agreement_template(
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:read")),
    client_id: UUID | None = None,
    quote_id: UUID | None = None,
    project_id: UUID | None = None,
):
    """The default clause set, prefilled from a client/quote/project when given."""
    client_name = None
    scope_lines = None
    payment = None
    timeline_lines = None
    if client_id:
        c = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        client_name = c.name if c else None
    if quote_id:
        q = db.query(QuoteModel).options(joinedload(QuoteModel.items)).filter(QuoteModel.id == quote_id).first()
        if q:
            scope_lines, payment = scope_from_quote(q)
            if not client_name and q.client:
                client_name = q.client.name
    if project_id:
        ms = db.query(MilestoneModel).filter(MilestoneModel.project_id == project_id).order_by(
            MilestoneModel.position, MilestoneModel.due_date.nulls_last()
        ).all()
        if ms:
            timeline_lines = timeline_from_milestones(ms)
    return AgreementTemplateResponse(
        clauses=[ClauseIn(**c) for c in default_clauses(client_name, scope_lines, payment, timeline_lines)]
    )


@router.get("", response_model=list[AgreementResponse])
def list_agreements(
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
    status_filter: str | None = None,
    client_id: UUID | None = None,
):
    qry = db.query(AgreementModel).options(
        joinedload(AgreementModel.client), joinedload(AgreementModel.project), joinedload(AgreementModel.quote)
    )
    if "admin:all" not in permissions:
        if manager_scope is not None:
            qry = qry.filter(AgreementModel.created_by.in_(manager_scope))
        else:
            qry = qry.filter(AgreementModel.created_by == user.id)
    if status_filter:
        qry = qry.filter(AgreementModel.status == status_filter)
    if client_id:
        qry = qry.filter(AgreementModel.client_id == client_id)
    rows = qry.order_by(AgreementModel.created_at.desc()).all()
    _apply_expiry(db, rows)
    return [_response(a) for a in rows]


@router.post("", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
def create_agreement(
    data: AgreementCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
):
    _validate_links(db, data.model_dump())
    _validate_currency(data.currency)
    if not data.clauses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An agreement needs at least one clause")
    a = AgreementModel(
        number=f"AGR-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}",
        title=data.title.strip(),
        client_id=data.client_id,
        project_id=data.project_id,
        quote_id=data.quote_id,
        effective_date=data.effective_date,
        valid_until=data.valid_until,
        contract_value=data.contract_value,
        currency=data.currency,
        clauses=[c.model_dump() for c in data.clauses],
        created_by=user.id,
    )
    db.add(a)
    db.flush()
    log_activity(db, user.id, "agreement_created", "agreement", a.id, details=f"Agreement {a.number}: {a.title}")
    db.commit()
    db.refresh(a)
    return _response(a)


@router.get("/{agreement_id}", response_model=AgreementResponse)
def get_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    return _response(_get_scoped_current(db, agreement_id, user, permissions, manager_scope))


@router.patch("/{agreement_id}", response_model=AgreementResponse)
def update_agreement(
    agreement_id: UUID,
    data: AgreementUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    _require_editable(a)
    updates = data.model_dump(exclude_unset=True)
    clauses = updates.pop("clauses", None)
    _validate_currency(updates.get("currency"))
    _validate_links(db, updates)
    for k, v in updates.items():
        setattr(a, k, v)
    if clauses is not None:
        if not clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An agreement needs at least one clause")
        a.clauses = clauses
    # Extending the deadline on an expired agreement revives it as a draft
    if a.status == "expired" and a.valid_until and a.valid_until >= date.today():
        a.status = "draft"
    db.commit()
    db.refresh(a)
    return _response(a)


@router.delete("/{agreement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status in ("signed", "terminated"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signed agreements are permanent records and cannot be deleted")
    log_activity(db, user.id, "agreement_deleted", "agreement", None, details=f"Agreement deleted: {a.number}")
    db.delete(a)
    db.commit()


@router.get("/{agreement_id}/pdf")
def agreement_pdf(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from fastapi.responses import Response
    from app.services.pdf_service import build_agreement_pdf
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    return Response(
        content=build_agreement_pdf(a),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{a.number}.pdf"'},
    )


@router.post("/{agreement_id}/send", response_model=AgreementResponse)
def send_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {a.status} agreement cannot be sent")
    a.status = "sent"
    log_activity(db, user.id, "agreement_sent", "agreement", a.id, details=f"Agreement sent: {a.number}")
    db.commit()
    db.refresh(a)
    recipient = a.client.contact_email if a.client else None
    if recipient:
        from app.services.pdf_service import build_agreement_pdf
        body = (
            f"<p>Please find our service agreement <b>{a.title}</b> ({a.number}) attached.</p>"
            "<p>You can review the full terms and sign it electronically in your client portal, "
            "or reply to this email with any questions.</p>"
            + (f"<p>Please sign by: <b>{a.valid_until}</b></p>" if a.valid_until else "")
        )
        email_service.send_email(
            recipient,
            f"Service agreement {a.number}: {a.title}",
            email_service._build_html(f"Service agreement: {a.title}", body),
            f"Service agreement {a.number}: {a.title}\nPlease review and sign in your client portal.",
            attachments=[(f"{a.number}.pdf", build_agreement_pdf(a))],
        )
    return _response(a)


class MarkSignedIn(BaseModel):
    signer_name: str | None = None


@router.post("/{agreement_id}/mark-signed", response_model=AgreementResponse)
def mark_signed(
    agreement_id: UUID,
    data: MarkSignedIn,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Record an out-of-band (wet/emailed) signature. Attach the countersigned scan via attachments."""
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status not in ("draft", "sent", "expired"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {a.status} agreement cannot be marked signed")
    a.status = "signed"
    a.accepted_at = datetime.utcnow()
    a.accepted_by_name = (data.signer_name or "").strip() or (a.client.name if a.client else None)
    a.acceptance_method = "manual"
    log_activity(db, user.id, "agreement_signed", "agreement", a.id, details=f"Agreement {a.number} marked signed ({a.accepted_by_name})")
    db.commit()
    db.refresh(a)
    return _response(a)


class TerminateIn(BaseModel):
    reason: str


@router.post("/{agreement_id}/terminate", response_model=AgreementResponse)
def terminate_agreement(
    agreement_id: UUID,
    data: TerminateIn,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status != "signed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only signed agreements can be terminated")
    if not data.reason.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A termination reason is required")
    a.status = "terminated"
    a.terminated_at = datetime.utcnow()
    a.termination_reason = data.reason.strip()
    log_activity(db, user.id, "agreement_terminated", "agreement", a.id, details=f"Agreement {a.number} terminated: {a.termination_reason[:100]}")
    db.commit()
    db.refresh(a)
    return _response(a)


@router.post("/{agreement_id}/duplicate", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
def duplicate_agreement(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Renewal helper: a fresh draft copying the terms of an existing agreement."""
    src = _get_scoped(db, agreement_id, user, permissions, manager_scope)
    a = AgreementModel(
        number=f"AGR-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}",
        title=src.title,
        client_id=src.client_id,
        project_id=src.project_id,
        quote_id=src.quote_id,
        contract_value=src.contract_value,
        currency=src.currency,
        clauses=list(src.clauses or []),
        created_by=user.id,
    )
    db.add(a)
    db.flush()
    log_activity(db, user.id, "agreement_created", "agreement", a.id, details=f"Agreement {a.number} duplicated from {src.number}")
    db.commit()
    db.refresh(a)
    return _response(a)
