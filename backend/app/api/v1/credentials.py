"""Project credentials vault: encrypted-at-rest secrets scoped to
projects. Secrets are never returned in list/detail responses — only
the explicit reveal endpoint decrypts, and every reveal is written to
the activity log. Gated by dedicated credentials:read/write permissions
(seeded to admin only; grant deliberately)."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import ProjectCredential as CredModel, Project as ProjectModel
from app.api.deps import require_permission
from app.services.activity_service import log_activity
from app.services.vault_service import encrypt_secret, decrypt_secret

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialCreate(BaseModel):
    project_id: UUID
    label: str
    secret: str
    username: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class CredentialUpdate(BaseModel):
    label: Optional[str] = None
    secret: Optional[str] = None  # provided -> re-encrypted; omitted -> unchanged
    username: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class CredentialResponse(BaseModel):
    id: UUID
    project_id: UUID
    project_name: Optional[str] = None
    label: str
    username: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    # deliberately no secret field: reveal is a separate, audited call


class RevealResponse(BaseModel):
    id: UUID
    secret: str


def _response(c: CredModel) -> CredentialResponse:
    return CredentialResponse(
        id=c.id, project_id=c.project_id,
        project_name=c.project.name if c.project else None,
        label=c.label, username=c.username, url=c.url, notes=c.notes,
        created_by=c.created_by, created_at=c.created_at,
    )


def _get(db, credential_id) -> CredModel:
    c = db.query(CredModel).options(joinedload(CredModel.project)).filter(CredModel.id == credential_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return c


@router.get("", response_model=list[CredentialResponse])
def list_credentials(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("credentials:read")),
):
    return [
        _response(c)
        for c in db.query(CredModel).options(joinedload(CredModel.project)).filter(
            CredModel.project_id == project_id
        ).order_by(CredModel.created_at).all()
    ]


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    data: CredentialCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("credentials:write")),
):
    if not data.label.strip() or not data.secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A credential needs a label and a secret")
    if not db.query(ProjectModel.id).filter(ProjectModel.id == data.project_id, ProjectModel.deleted_at.is_(None)).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    c = CredModel(
        project_id=data.project_id,
        label=data.label.strip(),
        username=(data.username or "").strip() or None,
        secret_encrypted=encrypt_secret(data.secret),
        url=(data.url or "").strip() or None,
        notes=(data.notes or "").strip() or None,
        created_by=user.id,
    )
    db.add(c)
    db.flush()
    log_activity(db, user.id, "credential_created", "credential", c.id, details=f"Credential added: {c.label}")
    db.commit()
    db.refresh(c)
    return _response(c)


@router.patch("/{credential_id}", response_model=CredentialResponse)
def update_credential(
    credential_id: UUID,
    data: CredentialUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("credentials:write")),
):
    c = _get(db, credential_id)
    updates = data.model_dump(exclude_unset=True)
    secret = updates.pop("secret", None)
    if "label" in updates and not (updates["label"] or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A credential needs a label")
    for k, v in updates.items():
        setattr(c, k, v)
    if secret is not None:
        if not secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Secret cannot be empty")
        c.secret_encrypted = encrypt_secret(secret)
        log_activity(db, user.id, "credential_rotated", "credential", c.id, details=f"Credential secret changed: {c.label}")
    db.commit()
    db.refresh(c)
    return _response(c)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("credentials:write")),
):
    c = _get(db, credential_id)
    log_activity(db, user.id, "credential_deleted", "credential", None, details=f"Credential deleted: {c.label}")
    db.delete(c)
    db.commit()


@router.post("/{credential_id}/reveal", response_model=RevealResponse)
def reveal_credential(
    credential_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("credentials:read")),
):
    """Decrypt one secret. Every call lands in the activity log — who
    viewed which credential, when."""
    c = _get(db, credential_id)
    try:
        secret = decrypt_secret(c.secret_encrypted)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    log_activity(db, user.id, "credential_revealed", "credential", c.id,
                 details=f"Credential revealed: {c.label} ({c.project.name if c.project else ''})")
    db.commit()
    return RevealResponse(id=c.id, secret=secret)
