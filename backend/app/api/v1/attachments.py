"""File attachments on tasks, projects, clients, leads, meetings, invoices, expenses.
Stored on local disk under settings.upload_dir with random names; object-level
access reuses the same per-entity scoping as notes (can_access_entity)."""
import os
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.config import get_settings
from app.models import Attachment as AttachmentModel, User
from app.schemas.attachment import AttachmentResponse
from app.api.deps import require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.note_service import entity_exists, can_access_entity
from app.services.activity_service import log_activity

router = APIRouter(prefix="/attachments", tags=["attachments"])

settings = get_settings()

VALID_ENTITY_TYPES = frozenset({"task", "project", "client", "lead", "meeting", "invoice", "expense"})

# Whitelist: bug evidence, docs, exports. No executables or HTML (stored-XSS vector).
ALLOWED_EXTENSIONS = frozenset({
    "png", "jpg", "jpeg", "gif", "webp", "svg", "pdf", "txt", "log", "md", "csv", "json", "har",
    "zip", "7z", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "mp4", "mov", "webm",
})

# Content types safe to render inline in the browser; everything else downloads.
INLINE_CONTENT_TYPES = frozenset({
    "image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf",
})


def _attachment_response(a: AttachmentModel) -> AttachmentResponse:
    return AttachmentResponse(
        id=a.id,
        entity_type=a.entity_type,
        entity_id=a.entity_id,
        filename=a.filename,
        content_type=a.content_type,
        size_bytes=a.size_bytes,
        uploaded_by=a.uploaded_by,
        uploaded_by_name=(a.uploader.full_name or a.uploader.email) if a.uploader else None,
        created_at=a.created_at,
    )


def _check_entity_access(db, entity_type, entity_id, user, permissions, team_ids, manager_scope):
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type")
    if not entity_exists(db, entity_type, entity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    if not can_access_entity(db, entity_type, entity_id, user, permissions, team_ids, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")


@router.get("", response_model=list[AttachmentResponse])
def list_attachments(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attachments:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    _check_entity_access(db, entity_type, entity_id, user, permissions, team_ids, manager_scope)
    rows = (
        db.query(AttachmentModel)
        .options(joinedload(AttachmentModel.uploader))
        .filter(AttachmentModel.entity_type == entity_type, AttachmentModel.entity_id == entity_id)
        .order_by(AttachmentModel.created_at.desc())
        .all()
    )
    return [_attachment_response(a) for a in rows]


@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    entity_type: str = Form(...),
    entity_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attachments:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    _check_entity_access(db, entity_type, entity_id, user, permissions, team_ids, manager_scope)
    original = (file.filename or "file").strip().replace("\\", "/").split("/")[-1][:255] or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{ext or '?'} not allowed",
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File exceeds {settings.max_upload_mb} MB limit")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    stored_name = f"{secrets.token_hex(16)}.{ext}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(os.path.join(settings.upload_dir, stored_name), "wb") as f:
        f.write(content)

    att = AttachmentModel(
        entity_type=entity_type,
        entity_id=entity_id,
        filename=original,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        uploaded_by=user.id,
    )
    db.add(att)
    db.flush()
    log_activity(db, user.id, "attachment_uploaded", entity_type, entity_id, details=f"Attached: {original}")
    db.commit()
    db.refresh(att)
    att = db.query(AttachmentModel).options(joinedload(AttachmentModel.uploader)).filter(AttachmentModel.id == att.id).first()
    return _attachment_response(att)


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attachments:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    att = db.query(AttachmentModel).filter(AttachmentModel.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    _check_entity_access(db, att.entity_type, att.entity_id, user, permissions, team_ids, manager_scope)
    path = os.path.join(settings.upload_dir, att.stored_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing from storage")
    # Only whitelisted types render inline; everything else forces download
    inline = (att.content_type or "") in INLINE_CONTENT_TYPES
    media_type = att.content_type if inline else "application/octet-stream"
    disposition = "inline" if inline else "attachment"
    return FileResponse(
        path,
        media_type=media_type,
        filename=att.filename,
        content_disposition_type=disposition,
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attachments:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    att = db.query(AttachmentModel).filter(AttachmentModel.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    is_admin = "admin:all" in permissions
    if att.uploaded_by != user.id and not is_admin and manager_scope is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the uploader, a manager, or an admin can delete this attachment")
    _check_entity_access(db, att.entity_type, att.entity_id, user, permissions, team_ids, manager_scope)
    path = os.path.join(settings.upload_dir, att.stored_name)
    filename, entity_type, entity_id = att.filename, att.entity_type, att.entity_id
    db.delete(att)
    db.flush()
    log_activity(db, user.id, "attachment_deleted", entity_type, entity_id, details=f"Attachment deleted: {filename}")
    db.commit()
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
