"""Letters: official company documents on the branded letterhead —
offer letters, experience letters, NOCs, completion certificates, and
general correspondence. Drafts are editable; issuing freezes the letter
into a permanent record. A blank letterhead PDF is also available."""
import uuid as uuid_mod
from datetime import datetime, date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Letter as LetterModel, Client as ClientModel
from app.schemas.letter import LetterCreate, LetterUpdate, LetterResponse, LetterTemplateResponse
from app.api.deps import require_permission, get_user_permissions, get_manager_scope_user_ids
from app.services.activity_service import log_activity
from app.services import email_service
from app.services.letter_templates import LETTER_TYPES, TYPE_LABELS, template_for

router = APIRouter(prefix="/letters", tags=["letters"])


def _response(l: LetterModel) -> LetterResponse:
    return LetterResponse(
        id=l.id, number=l.number, letter_type=l.letter_type, subject=l.subject,
        recipient_name=l.recipient_name, recipient_address=l.recipient_address,
        recipient_email=l.recipient_email,
        client_id=l.client_id, client_name=l.client.name if l.client else None,
        body=l.body, letter_date=l.letter_date,
        signatory_name=l.signatory_name, signatory_title=l.signatory_title,
        status=l.status, issued_at=l.issued_at,
        created_by=l.created_by, created_at=l.created_at,
    )


def _get_scoped(db, letter_id, user, permissions, manager_scope) -> LetterModel:
    l = db.query(LetterModel).options(joinedload(LetterModel.client)).filter(LetterModel.id == letter_id).first()
    if not l:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not found")
    if "admin:all" in permissions or l.created_by == user.id:
        return l
    if manager_scope is not None and l.created_by is not None and l.created_by in manager_scope:
        return l
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not found")


def _validate(db, data: dict) -> None:
    if data.get("letter_type") and data["letter_type"] not in LETTER_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"letter_type must be one of: {', '.join(LETTER_TYPES)}")
    if data.get("client_id") and not db.query(ClientModel.id).filter(
        ClientModel.id == data["client_id"], ClientModel.deleted_at.is_(None)
    ).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


@router.get("/types")
def letter_types(user=Depends(require_permission("letters:read"))):
    return [{"value": t, "label": TYPE_LABELS[t]} for t in LETTER_TYPES]


@router.get("/template", response_model=LetterTemplateResponse)
def letter_template(
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:read")),
    letter_type: str = "general",
    recipient_name: str | None = None,
    client_id: UUID | None = None,
):
    if letter_type not in LETTER_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"letter_type must be one of: {', '.join(LETTER_TYPES)}")
    name = recipient_name
    if not name and client_id:
        c = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        name = c.name if c else None
    return LetterTemplateResponse(**template_for(letter_type, name))


@router.get("/blank-pdf")
def blank_letterhead(user=Depends(require_permission("letters:read"))):
    from fastapi.responses import Response
    from app.services.pdf_service import build_blank_letterhead
    return Response(
        content=build_blank_letterhead(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="letterhead.pdf"'},
    )


@router.get("", response_model=list[LetterResponse])
def list_letters(
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
    status_filter: str | None = None,
    letter_type: str | None = None,
    client_id: UUID | None = None,
):
    qry = db.query(LetterModel).options(joinedload(LetterModel.client))
    if "admin:all" not in permissions:
        if manager_scope is not None:
            qry = qry.filter(LetterModel.created_by.in_(manager_scope))
        else:
            qry = qry.filter(LetterModel.created_by == user.id)
    if status_filter:
        qry = qry.filter(LetterModel.status == status_filter)
    if letter_type:
        qry = qry.filter(LetterModel.letter_type == letter_type)
    if client_id:
        qry = qry.filter(LetterModel.client_id == client_id)
    return [_response(l) for l in qry.order_by(LetterModel.created_at.desc()).all()]


@router.post("", response_model=LetterResponse, status_code=status.HTTP_201_CREATED)
def create_letter(
    data: LetterCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:write")),
):
    _validate(db, data.model_dump())
    if not data.subject.strip() or not data.body.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A letter needs a subject and a body")
    l = LetterModel(
        number=f"LTR-{datetime.utcnow():%Y%m}-{uuid_mod.uuid4().hex[:6].upper()}",
        letter_type=data.letter_type,
        subject=data.subject.strip(),
        recipient_name=(data.recipient_name or "").strip() or None,
        recipient_address=(data.recipient_address or "").strip() or None,
        recipient_email=(data.recipient_email or "").strip() or None,
        client_id=data.client_id,
        body=data.body,
        letter_date=data.letter_date or date.today(),
        signatory_name=(data.signatory_name or "").strip() or user.full_name,
        signatory_title=(data.signatory_title or "").strip() or user.job_title,
        created_by=user.id,
    )
    db.add(l)
    db.flush()
    log_activity(db, user.id, "letter_created", "letter", l.id, details=f"Letter {l.number}: {l.subject}")
    db.commit()
    db.refresh(l)
    return _response(l)


@router.get("/{letter_id}", response_model=LetterResponse)
def get_letter(
    letter_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    return _response(_get_scoped(db, letter_id, user, permissions, manager_scope))


@router.patch("/{letter_id}", response_model=LetterResponse)
def update_letter(
    letter_id: UUID,
    data: LetterUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    l = _get_scoped(db, letter_id, user, permissions, manager_scope)
    if l.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An issued letter is a frozen record and cannot be edited")
    updates = data.model_dump(exclude_unset=True)
    _validate(db, updates)
    if "subject" in updates and not (updates["subject"] or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A letter needs a subject")
    if "body" in updates and not (updates["body"] or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A letter needs a body")
    for k, v in updates.items():
        setattr(l, k, v)
    db.commit()
    db.refresh(l)
    return _response(l)


@router.delete("/{letter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_letter(
    letter_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    l = _get_scoped(db, letter_id, user, permissions, manager_scope)
    if l.status == "issued":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Issued letters are permanent records and cannot be deleted")
    log_activity(db, user.id, "letter_deleted", "letter", None, details=f"Letter deleted: {l.number}")
    db.delete(l)
    db.commit()


@router.get("/{letter_id}/pdf")
def letter_pdf(
    letter_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from fastapi.responses import Response
    from app.services.pdf_service import build_letter_pdf
    l = _get_scoped(db, letter_id, user, permissions, manager_scope)
    return Response(
        content=build_letter_pdf(l),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{l.number}.pdf"'},
    )


@router.post("/{letter_id}/issue", response_model=LetterResponse)
def issue_letter(
    letter_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Freeze the letter as officially issued — the record of what went out."""
    l = _get_scoped(db, letter_id, user, permissions, manager_scope)
    if l.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft letters can be issued")
    l.status = "issued"
    l.issued_at = datetime.utcnow()
    log_activity(db, user.id, "letter_issued", "letter", l.id, details=f"Letter issued: {l.number} ({l.subject})")
    db.commit()
    db.refresh(l)
    return _response(l)


@router.post("/{letter_id}/send", response_model=LetterResponse)
def send_letter(
    letter_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("letters:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Email the letterhead PDF to the recipient (issues the letter first if still a draft)."""
    from app.services.pdf_service import build_letter_pdf
    l = _get_scoped(db, letter_id, user, permissions, manager_scope)
    recipient = l.recipient_email or (l.client.contact_email if l.client else None)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No recipient email — set one on the letter or link a client with a contact email")
    if l.status == "draft":
        l.status = "issued"
        l.issued_at = datetime.utcnow()
    body = (
        f"<p>Dear {l.recipient_name or (l.client.name if l.client else 'Sir/Madam')},</p>"
        f"<p>Please find attached our letter <b>{l.subject}</b> ({l.number}).</p>"
        "<p>Kind regards</p>"
    )
    email_service.send_email(
        recipient,
        f"{l.subject} ({l.number})",
        email_service._build_html(l.subject, body),
        f"{l.subject} ({l.number}) — see the attached PDF.",
        attachments=[(f"{l.number}.pdf", build_letter_pdf(l))],
    )
    log_activity(db, user.id, "letter_sent", "letter", l.id, details=f"Letter emailed: {l.number} to {recipient}")
    db.commit()
    db.refresh(l)
    return _response(l)
