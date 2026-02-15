from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.security import decode_token

security = HTTPBearer(auto_error=False)


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
    return user


def get_user_permissions(user: Annotated[User, Depends(get_current_user)]) -> set[str]:
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


def require_admin(
    user: Annotated[User, Depends(get_current_user)],
    permissions: Annotated[set[str], Depends(get_user_permissions)],
) -> User:
    if "admin:all" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_user_team_ids(user: Annotated[User, Depends(get_current_user)]) -> set[UUID]:
    return {t.id for t in user.teams}
