"""Helpers for notes: entity existence check (no access control - that is enforced by notes:read/write and UI)."""
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import (
    Lead, Client, Project, Task, Meeting, Invoice, Expense, Announcement,
)


def entity_exists(db: Session, entity_type: str, entity_id: UUID) -> bool:
    """Return True if the given entity exists. Used to avoid creating notes for invalid IDs."""
    model_map = {
        "lead": Lead,
        "client": Client,
        "project": Project,
        "task": Task,
        "meeting": Meeting,
        "invoice": Invoice,
        "expense": Expense,
        "announcement": Announcement,
    }
    model = model_map.get(entity_type)
    if not model:
        return False
    if entity_type == "client":
        return db.query(model).filter(model.id == entity_id, model.deleted_at.is_(None)).first() is not None
    if entity_type == "project":
        return db.query(model).filter(model.id == entity_id, model.deleted_at.is_(None)).first() is not None
    return db.query(model).filter(model.id == entity_id).first() is not None
