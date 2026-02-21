"""Log user activity so managers can see their team members' actions and progress."""
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import ActivityLog


def log_activity(
    db: Session,
    user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    details: str | None = None,
) -> None:
    """Append an activity record for the given user (visible to their manager)."""
    log = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(log)
