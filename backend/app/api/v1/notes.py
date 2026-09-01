"""Notes API: attach notes to leads, tasks, meetings, projects, clients, invoices, expenses, announcements.
Notes can be private (only creator sees) or visible to others."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Note as NoteModel, User
from app.schemas.note import NoteCreate, NoteUpdate, NoteResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.note_service import entity_exists, can_access_entity

router = APIRouter(prefix="/notes", tags=["notes"])

VALID_ENTITY_TYPES = frozenset({"lead", "task", "meeting", "project", "client", "invoice", "expense", "announcement"})


@router.get("", response_model=list[NoteResponse])
def list_notes(
    entity_type: str = Query(..., description="Entity type"),
    entity_id: UUID = Query(..., description="Entity ID"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notes:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type")
    if not entity_exists(db, entity_type, entity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    if not can_access_entity(db, entity_type, entity_id, user, permissions, team_ids, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    qry = (
        db.query(NoteModel)
        .options(joinedload(NoteModel.creator))
        .filter(NoteModel.entity_type == entity_type, NoteModel.entity_id == entity_id)
    )
    notes = qry.order_by(NoteModel.created_at.desc()).all()
    out = []
    for n in notes:
        if n.is_private and n.created_by != user.id:
            continue
        created_by_name = (n.creator.full_name or n.creator.email) if n.creator else None
        out.append(NoteResponse(
            id=n.id,
            entity_type=n.entity_type,
            entity_id=n.entity_id,
            content=n.content,
            is_private=n.is_private,
            created_by=n.created_by,
            created_at=n.created_at,
            updated_at=n.updated_at,
            created_by_name=created_by_name,
        ))
    return out


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    data: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notes:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    if data.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity_type")
    if not entity_exists(db, data.entity_type, data.entity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    if not can_access_entity(db, data.entity_type, data.entity_id, user, permissions, team_ids, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    note = NoteModel(
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        content=data.content.strip(),
        is_private=data.is_private,
        created_by=user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    note = db.query(NoteModel).options(joinedload(NoteModel.creator)).filter(NoteModel.id == note.id).first()
    return NoteResponse(
        id=note.id,
        entity_type=note.entity_type,
        entity_id=note.entity_id,
        content=note.content,
        is_private=note.is_private,
        created_by=note.created_by,
        created_at=note.created_at,
        updated_at=note.updated_at,
        created_by_name=note.creator.full_name or note.creator.email if note.creator else None,
    )


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: UUID,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notes:write")),
):
    note = db.query(NoteModel).options(joinedload(NoteModel.creator)).filter(NoteModel.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if note.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can update this note")
    if data.content is not None:
        note.content = data.content.strip()
    if data.is_private is not None:
        note.is_private = data.is_private
    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=note.id,
        entity_type=note.entity_type,
        entity_id=note.entity_id,
        content=note.content,
        is_private=note.is_private,
        created_by=note.created_by,
        created_at=note.created_at,
        updated_at=note.updated_at,
        created_by_name=note.creator.full_name or note.creator.email if note.creator else None,
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("notes:write")),
):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if note.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can delete this note")
    db.delete(note)
    db.commit()
