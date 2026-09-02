"""Cleanup for hard-deleted entities: purge their notes and attachments
(rows AND files on disk) so nothing orphans silently."""
import os
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import Note, Attachment
from app.config import get_settings

settings = get_settings()


def purge_entity_artifacts(db: Session, entity_type: str, entity_id: UUID) -> None:
    """Delete notes and attachments belonging to an entity being hard-deleted.
    Caller is responsible for the commit."""
    db.query(Note).filter(Note.entity_type == entity_type, Note.entity_id == entity_id).delete()
    attachments = db.query(Attachment).filter(
        Attachment.entity_type == entity_type, Attachment.entity_id == entity_id
    ).all()
    for att in attachments:
        path = os.path.join(settings.upload_dir, att.stored_name)
        db.delete(att)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
