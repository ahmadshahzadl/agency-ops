"""Public signing links: a prospect who has no portal account opens the emailed link, reads the
agreement and signs it with their name. The link is a long random token tied to one agreement,
valid until the signature deadline (or 30 days). After signing, the same link keeps serving the
executed PDF so the client always has their copy."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import Agreement as AgreementModel
from app.services import agreement_signing as signing
from app.services.agreement_template import label_for

router = APIRouter(prefix="/public/agreements", tags=["agreements-public"])


class PublicClause(BaseModel):
    heading: str
    body: str


class PublicAgreementOut(BaseModel):
    number: str
    title: str
    agreement_type: str
    type_label: str
    status: str  # sent | signed | declined | expired | terminated | link_expired
    company_name: str
    client_name: Optional[str] = None
    effective_date: Optional[str] = None
    valid_until: Optional[str] = None
    contract_value: Optional[str] = None
    currency: str
    clauses: list[PublicClause] = []
    accepted_at: Optional[datetime] = None
    accepted_by_name: Optional[str] = None
    countersigned_at: Optional[datetime] = None
    countersigned_by_name: Optional[str] = None
    can_sign: bool = False


class PublicAcceptIn(BaseModel):
    signer_name: str = Field(min_length=2, max_length=255)
    signer_email: Optional[EmailStr] = None
    signer_title: Optional[str] = Field(None, max_length=128)
    agreed: bool = False


class PublicDeclineIn(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)


def _load(db: Session, token: str) -> AgreementModel:
    if not token or len(token) < 16:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    a = (
        db.query(AgreementModel).options(joinedload(AgreementModel.client))
        .filter(AgreementModel.sign_token == token, AgreementModel.status != "draft").first()
    )
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    from app.api.v1.agreements import _apply_expiry
    _apply_expiry(db, [a])
    return a


def _link_expired(a: AgreementModel) -> bool:
    return signing.link_expired(a)


def _out(a: AgreementModel) -> PublicAgreementOut:
    status_out = a.status
    can_sign = a.status == "sent" and not _link_expired(a)
    if a.status == "sent" and _link_expired(a):
        status_out = "link_expired"
    return PublicAgreementOut(
        number=a.number, title=a.title, agreement_type=a.agreement_type or "service", type_label=label_for(a.agreement_type),
        status=status_out, company_name=get_settings().app_name.replace(" API", ""),
        client_name=a.client.name if a.client else None,
        effective_date=str(a.effective_date) if a.effective_date else None,
        valid_until=str(a.valid_until) if a.valid_until else None,
        contract_value=(f"{a.contract_value:,.2f}" if a.contract_value is not None else None), currency=a.currency,
        clauses=[PublicClause(**c) for c in (a.clauses or [])],
        accepted_at=a.accepted_at, accepted_by_name=a.accepted_by_name,
        countersigned_at=a.countersigned_at, countersigned_by_name=a.countersigned_by_name,
        can_sign=can_sign,
    )


@router.get("/{token}", response_model=PublicAgreementOut)
def view(token: str, db: Session = Depends(get_db)):
    return _out(_load(db, token))


@router.get("/{token}/pdf")
def pdf(token: str, db: Session = Depends(get_db)):
    from app.services.pdf_service import build_agreement_pdf
    a = _load(db, token)
    return Response(content=build_agreement_pdf(a), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{a.number}.pdf"'})


@router.post("/{token}/accept", response_model=PublicAgreementOut)
def accept(token: str, data: PublicAcceptIn, request: Request, db: Session = Depends(get_db)):
    a = _load(db, token)
    if a.status != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"This agreement is already {a.status}")
    if _link_expired(a):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This signing link has expired. Ask us for a new one.")
    if not data.agreed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please confirm you have read and agree to the terms")
    signer = data.signer_name.strip()
    if len(signer.split()) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please type your full name as it should appear on the agreement")
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    signing.record_acceptance(
        db, a, signer_name=signer, signer_email=(str(data.signer_email) if data.signer_email else None),
        signer_title=(data.signer_title or "").strip() or None, ip=ip, user_agent=request.headers.get("user-agent"),
        method="link",
    )
    db.commit()
    db.refresh(a)
    signing.send_executed_copy(a)
    return _out(a)


@router.post("/{token}/decline", response_model=PublicAgreementOut)
def decline(token: str, data: PublicDeclineIn, db: Session = Depends(get_db)):
    a = _load(db, token)
    if a.status != "sent":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"This agreement is already {a.status}")
    signing.record_decline(db, a, (data.reason or "").strip() or None, actor_label="via the signing link")
    db.commit()
    db.refresh(a)
    return _out(a)
