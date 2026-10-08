"""Service agreements: contract records built from a minimal editable
clause template, with a lifecycle (draft -> sent -> signed/declined),
branded PDFs, email delivery, and clickwrap acceptance via the client
portal. Signed agreements are immutable — like paid invoices."""
import uuid as uuid_mod
from datetime import datetime, date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    Agreement as AgreementModel, Client as ClientModel, Project as ProjectModel,
    Quote as QuoteModel, Milestone as MilestoneModel,
)
from app.schemas.agreement import (
    AgreementCreate, AgreementUpdate, AgreementResponse, AgreementTemplateResponse, AgreementTypeOut, ClauseIn,
)
from app.api.deps import require_permission, get_user_permissions, get_manager_scope_user_ids
from app.services.activity_service import log_activity
from app.services import email_service
from app.services.agreement_template import (
    AGREEMENT_TYPES, HAS_VALUE, TYPE_DESCRIPTIONS, TYPE_LABELS, TYPE_SHORT,
    clauses_for, label_for, prefix_for, scope_from_quote, timeline_from_milestones, title_for,
)
from app.services import agreement_signing as signing
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


def _validate_type(agreement_type: str | None) -> None:
    if agreement_type is not None and agreement_type not in AGREEMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"agreement_type must be one of: {', '.join(AGREEMENT_TYPES)}")


def _response(a: AgreementModel) -> AgreementResponse:
    live_link = a.status == "sent" and a.sign_token and not signing.link_expired(a)
    return AgreementResponse(
        id=a.id, number=a.number, title=a.title,
        agreement_type=a.agreement_type or "service", type_label=label_for(a.agreement_type),
        sign_url=signing.sign_url(a) if live_link else None,
        signer_email=a.signer_email, signer_title=a.signer_title, accepted_user_agent=a.accepted_user_agent,
        acceptance_hash=a.acceptance_hash, countersigned_by_name=a.countersigned_by_name, countersigned_at=a.countersigned_at,
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
    if _client_visible(a.client, user, manager_scope):
        return a
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found")


def _client_visible(client, user, manager_scope) -> bool:
    """Same rule as the Clients page: the client's team, the manager who owns its creator, or the
    solutions engineer who brought the lead in. Anyone who can see the client can see its agreements."""
    if client is None:
        return False
    team_ids = {t.id for t in (user.teams or [])}
    if client.source_lead is not None and client.source_lead.assigned_to == user.id:
        return True
    if manager_scope is not None and client.created_by is not None and client.created_by in manager_scope:
        return True
    return client.team_id is not None and client.team_id in team_ids


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


@router.get("/types", response_model=list[AgreementTypeOut])
def agreement_types(user=Depends(require_permission("agreements:read"))):
    return [
        AgreementTypeOut(key=k, label=TYPE_LABELS[k], short_label=TYPE_SHORT[k], description=TYPE_DESCRIPTIONS[k], has_value=k in HAS_VALUE)
        for k in AGREEMENT_TYPES
    ]


@router.get("/template", response_model=AgreementTemplateResponse)
def agreement_template(
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:read")),
    agreement_type: str = "service",
    client_id: UUID | None = None,
    quote_id: UUID | None = None,
    project_id: UUID | None = None,
):
    """The pre-saved clause set for a type, prefilled from a client/quote/project when given."""
    _validate_type(agreement_type)
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
        agreement_type=agreement_type,
        title_suggestion=title_for(agreement_type, client_name),
        clauses=[ClauseIn(**c) for c in clauses_for(agreement_type, client_name, scope_lines, payment, timeline_lines)],
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
    if status_filter:
        qry = qry.filter(AgreementModel.status == status_filter)
    if client_id:
        qry = qry.filter(AgreementModel.client_id == client_id)
    rows = qry.order_by(AgreementModel.created_at.desc()).all()
    if "admin:all" not in permissions:
        rows = [
            a for a in rows
            if a.created_by == user.id
            or (manager_scope is not None and a.created_by is not None and a.created_by in manager_scope)
            or _client_visible(a.client, user, manager_scope)
        ]
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
    _validate_type(data.agreement_type)
    if not data.clauses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An agreement needs at least one clause")
    a = AgreementModel(
        number=f"{prefix_for(data.agreement_type)}-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}",
        title=data.title.strip(),
        agreement_type=data.agreement_type,
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
    _validate_type(updates.get("agreement_type"))
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
    if a.status in ("signed", "terminated") and "admin:all" not in permissions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signed agreements are permanent records; only an admin can delete one")
    details = f"Agreement deleted: {a.number} ({a.status})"
    if a.status in ("signed", "terminated"):
        details += f" - signed record removed by admin; was signed by {a.accepted_by_name or '-'} on {a.accepted_at:%Y-%m-%d}" if a.accepted_at else " - signed record removed by admin"
    log_activity(db, user.id, "agreement_deleted", "agreement", None, details=details)
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


class SendIn(BaseModel):
    to: EmailStr | None = None  # override the client's contact email (e.g. the founder who will sign)
    sign_for_company: bool = True  # place the sender's saved signature on the document before it goes out


@router.post("/{agreement_id}/send", response_model=AgreementResponse)
def send_agreement(
    agreement_id: UUID,
    data: SendIn | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Mark sent, mint the signing link and email it (with the PDF) to the signer."""
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A {a.status} agreement cannot be sent")
    a.status = "sent"
    signing.ensure_sign_token(a)
    want_sign = data.sign_for_company if data else True
    if want_sign and not a.countersigned_at and getattr(user, "signature_file", None):
        a.countersigned_by = user.id
        a.countersigned_by_name = (user.full_name or user.email).strip()
        a.countersigned_at = datetime.utcnow()
    recipient = (str(data.to) if data and data.to else None) or a.signer_email or (a.client.contact_email if a.client else None)
    if recipient:
        a.signer_email = recipient
    log_activity(db, user.id, "agreement_sent", "agreement", a.id, details=f"{a.number} sent" + (f" to {recipient}" if recipient else " (no email on file)"))
    db.commit()
    db.refresh(a)
    if recipient:
        signing.send_for_signature(a, recipient)
    return _response(a)


@router.get("/{agreement_id}/sign-link")
def sign_link(
    agreement_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """The signing URL, for pasting into WhatsApp or a message. Minted on first request; sent agreements only."""
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Send the agreement first; only sent agreements have a signing link")
    if not a.sign_token or signing.link_expired(a):
        a.sign_token = None
        signing.ensure_sign_token(a)
        db.commit()
    return {"url": signing.sign_url(a), "expires_at": a.sign_token_expires_at}


class CountersignIn(BaseModel):
    name: str | None = None


@router.post("/{agreement_id}/countersign", response_model=AgreementResponse)
def countersign(
    agreement_id: UUID,
    data: CountersignIn | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("agreements:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Our side of the signature, recorded after the client signs. Emails the client the fully executed copy."""
    a = _get_scoped_current(db, agreement_id, user, permissions, manager_scope)
    if a.status != "signed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a signed agreement can be countersigned")
    if a.countersigned_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This agreement is already countersigned")
    a.countersigned_by = user.id
    a.countersigned_by_name = ((data.name if data else None) or user.full_name or user.email).strip()
    a.countersigned_at = datetime.utcnow()
    log_activity(db, user.id, "agreement_countersigned", "agreement", a.id, details=f"{a.number} countersigned by {a.countersigned_by_name}")
    db.commit()
    db.refresh(a)
    signing.send_executed_copy(a)
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
        number=f"{prefix_for(src.agreement_type)}-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}",
        title=src.title,
        agreement_type=src.agreement_type or "service",
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
