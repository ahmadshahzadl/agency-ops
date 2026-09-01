from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.models.user import User, UserRole
from app.models.role import Role
from app.core.security import decode_token, token_version_matches

security = HTTPBearer(auto_error=False)


def is_super_admin(user: User) -> bool:
    """True if this user is the configured super admin (god mode): full access, no audit logs."""
    email = (get_settings().super_admin_email or "").strip().lower()
    if not email:
        return False
    return (user.email or "").strip().lower() == email


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    from app.models import User as UserModel
    user = db.query(UserModel).filter(UserModel.id == UUID(user_id), UserModel.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    if not token_version_matches(payload, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    return user


def get_user_permissions(user: Annotated[User, Depends(get_current_user)]) -> set[str]:
    if is_super_admin(user):
        return {"admin:all"}  # Full access; no need to enumerate every permission
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.code)
    return perms


def require_permission(permission: str):
    def _check(
        user: Annotated[User, Depends(get_current_user)],
        permissions: Annotated[set[str], Depends(get_user_permissions)],
    ) -> User:
        if permission not in permissions and "admin:all" not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {permission}")
        return user
    return _check


def require_any_permission(*permissions: str):
    """Require at least one of the given permissions (or admin:all)."""
    def _check(
        user: Annotated[User, Depends(get_current_user)],
        user_perms: Annotated[set[str], Depends(get_user_permissions)],
    ) -> User:
        if "admin:all" in user_perms:
            return user
        if any(p in user_perms for p in permissions):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required")
    return _check


def require_admin(
    user: Annotated[User, Depends(get_current_user)],
    permissions: Annotated[set[str], Depends(get_user_permissions)],
) -> User:
    if "admin:all" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_user_team_ids(user: Annotated[User, Depends(get_current_user)]) -> set[UUID]:
    return {t.id for t in user.teams}


def get_manager_scope_user_ids(user: Annotated[User, Depends(get_current_user)]) -> set[UUID] | None:
    """If user has direct reports (is a manager), return {self} ∪ report ids for scoping. Else None (use team_ids)."""
    report_ids = [r.id for r in user.reports] if getattr(user, "reports", None) else []
    if not report_ids:
        return None
    return {user.id} | set(report_ids)


def get_is_sales_member(
    user: Annotated[User, Depends(get_current_user)],
    manager_scope: Annotated[set[UUID] | None, Depends(get_manager_scope_user_ids)],
) -> bool:
    """True when user has role 'sales' and no direct reports → restrict to own data only (leads, tasks, meetings)."""
    role_names = [r.name for r in user.roles] if getattr(user, "roles", None) else []
    return "sales" in role_names and manager_scope is None


def get_sales_team_user_ids(
    db: Annotated[Session, Depends(get_db)],
) -> set[UUID]:
    """All user IDs that have the 'sales' role (for new-lead visibility: all sales see new leads)."""
    rows = (
        db.query(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.name == "sales")
        .all()
    )
    return {r[0] for r in rows}
