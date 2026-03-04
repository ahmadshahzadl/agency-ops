from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, Token, UserResponse, ProfileUpdate
from app.api.deps import get_current_user
from app.models import User
from app.core.security import verify_password, get_password_hash
from app.services.auth_service import authenticate_user, create_tokens_for_user, refresh_access_token
from app.services.activity_service import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    tokens = create_tokens_for_user(user)
    return Token(**tokens)


@router.post("/refresh", response_model=Token)
def refresh(
    payload: dict = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refresh_token required")
    tokens = refresh_access_token(db, refresh_token)
    return Token(**tokens)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    permissions = []
    role_names = []
    for role in user.roles:
        role_names.append(role.name)
        for perm in role.permissions:
            permissions.append(perm.code)
    report_ids = [r.id for r in user.reports] if getattr(user, "reports", None) else []
    can_manage_tasks = "admin:all" in permissions or len(report_ids) > 0
    can_manage_leads = "admin:all" in permissions or len(report_ids) > 0
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        permissions=permissions,
        roles=role_names,
        can_manage_tasks=can_manage_tasks,
        can_manage_leads=can_manage_leads,
    )


@router.patch("/me", response_model=UserResponse)
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.new_password is not None:
        if not data.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password required to set a new password")
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        user.password_hash = get_password_hash(data.new_password)
    db.flush()
    if data.full_name is not None or data.new_password is not None:
        log_activity(db, user.id, "profile_updated", "profile", user.id, details="Profile updated (name or password)")
    db.commit()
    db.refresh(user)
    permissions = []
    role_names = []
    for role in user.roles:
        role_names.append(role.name)
        for perm in role.permissions:
            permissions.append(perm.code)
    report_ids = [r.id for r in user.reports] if getattr(user, "reports", None) else []
    can_manage_tasks = "admin:all" in permissions or len(report_ids) > 0
    can_manage_leads = "admin:all" in permissions or len(report_ids) > 0
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        permissions=permissions,
        roles=role_names,
        can_manage_tasks=can_manage_tasks,
        can_manage_leads=can_manage_leads,
    )
