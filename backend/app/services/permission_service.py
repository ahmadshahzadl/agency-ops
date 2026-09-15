"""Lookups by permission code (who should be notified / may be assigned)."""
from sqlalchemy.orm import Session

from app.models import Permission, Role, User

BOOKINGS_MANAGE = "bookings:manage"


def users_with_permission(db: Session, *codes: str, include_admins: bool = False) -> list[User]:
    """Active, non-client users holding any of ``codes`` through a role."""
    wanted = set(codes)
    if include_admins:
        wanted.add("admin:all")
    if not wanted:
        return []
    return (
        db.query(User)
        .join(User.roles)
        .join(Role.permissions)
        .filter(Permission.code.in_(wanted), User.is_active.is_(True), User.client_id.is_(None))
        .distinct()
        .all()
    )
