"""Admin-only: list, create, update users; assign roles and teams. Assignable users for task assignment."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User as UserModel, UserRole, TeamMember
from app.schemas.user import UserCreateAdmin, UserUpdateAdmin, UserListResponse
from app.api.deps import get_current_user, require_admin, require_permission, require_any_permission, get_manager_scope_user_ids, get_user_permissions
from app.core.security import get_password_hash
from app.services.activity_service import log_activity

router = APIRouter(prefix="/users", tags=["users"])


class AssignableUserResponse(UserListResponse):
    """Minimal user info for assignee dropdowns."""

    pass


@router.get("/assignable", response_model=list[AssignableUserResponse])
def list_assignable_users(
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("tasks:write", "meetings:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """Users the current user can assign tasks to: admin=all, manager=self+reports, member=self only."""
    if "admin:all" in permissions:
        users = db.query(UserModel).filter(UserModel.is_active == True).all()
        return [_user_to_response(u) for u in users]
    if manager_scope is not None:
        users = db.query(UserModel).filter(UserModel.id.in_(manager_scope), UserModel.is_active == True).all()
        return [_user_to_response(u) for u in users]
    # Member: only self
    return [_user_to_response(user)]


def _user_to_response(user: UserModel) -> UserListResponse:
    role_ids = [r.id for r in user.roles]
    team_ids = [t.id for t in user.teams]
    return UserListResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        manager_id=getattr(user, "manager_id", None),
        role_ids=role_ids,
        team_ids=team_ids,
    )


@router.get("", response_model=list[UserListResponse])
def list_users(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = None,
):
    qry = db.query(UserModel)
    if q:
        qry = qry.filter(
            UserModel.email.ilike(f"%{q}%") | UserModel.full_name.ilike(f"%{q}%")
        )
    users = qry.offset(skip).limit(limit).all()
    return [_user_to_response(u) for u in users]


@router.post("", response_model=UserListResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreateAdmin,
    db: Session = Depends(get_db),
    admin_user=Depends(require_admin),
):
    if db.query(UserModel).filter(UserModel.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = UserModel(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        is_active=data.is_active,
        manager_id=getattr(data, "manager_id", None),
    )
    db.add(user)
    db.flush()
    for role_id in data.role_ids or []:
        db.add(UserRole(user_id=user.id, role_id=role_id))
    for team_id in data.team_ids or []:
        db.add(TeamMember(team_id=team_id, user_id=user.id))
    log_activity(db, admin_user.id, "user_created", "user", user.id, details=f"User created: {user.email}")
    db.commit()
    db.refresh(user)
    return _user_to_response(user)


@router.get("/{user_id}", response_model=UserListResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserListResponse)
def update_user(
    user_id: UUID,
    data: UserUpdateAdmin,
    db: Session = Depends(get_db),
    admin_user=Depends(require_admin),
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.manager_id is not None:
        user.manager_id = data.manager_id
    if data.role_ids is not None:
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        for role_id in data.role_ids:
            db.add(UserRole(user_id=user.id, role_id=role_id))
    if data.team_ids is not None:
        db.query(TeamMember).filter(TeamMember.user_id == user_id).delete()
        for team_id in data.team_ids:
            db.add(TeamMember(team_id=team_id, user_id=user.id))
    db.flush()
    log_activity(db, admin_user.id, "user_updated", "user", user.id, details=f"User updated: {user.email}")
    db.commit()
    db.refresh(user)
    return _user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    log_activity(db, current_user.id, "user_deleted", "user", user_id, details=f"User deleted: {user.email}")
    db.delete(user)
    db.commit()
