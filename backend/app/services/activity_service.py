"""Log user activity so managers can see their team members' actions and progress."""
import contextvars
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import ActivityLog
from app.models.user import User
from app.config import get_settings

# Set when any activity is logged this request; middleware broadcasts and clears after response.
activity_logged_this_request: contextvars.ContextVar[bool] = contextvars.ContextVar("activity_logged", default=False)

# Set when tasks/meetings/notifications change this request; middleware broadcasts so clients can refetch.
tasks_updated_this_request: contextvars.ContextVar[bool] = contextvars.ContextVar("tasks_updated", default=False)
meetings_updated_this_request: contextvars.ContextVar[bool] = contextvars.ContextVar("meetings_updated", default=False)
notifications_updated_this_request: contextvars.ContextVar[bool] = contextvars.ContextVar("notifications_updated", default=False)


def log_activity(
    db: Session,
    user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    details: str | None = None,
) -> None:
    """Append an activity record for the given user (visible to their manager). No log for super admin (ghost)."""
    super_email = (get_settings().super_admin_email or "").strip().lower()
    if super_email:
        user = db.query(User).filter(User.id == user_id).first()
        if user and (user.email or "").strip().lower() == super_email:
            return
    log = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(log)
    activity_logged_this_request.set(True)
