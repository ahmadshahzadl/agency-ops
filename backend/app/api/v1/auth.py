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


def _user_response(user: User):
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
        phone=getattr(user, "phone", None),
        job_title=getattr(user, "job_title", None),
        is_active=user.is_active,
        permissions=permissions,
        roles=role_names,
        can_manage_tasks=can_manage_tasks,
        can_manage_leads=can_manage_leads,
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.patch("/me", response_model=UserResponse)
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    role_names = [r.name for r in user.roles]
    can_edit_contact = "admin:all" in [p.code for r in user.roles for p in r.permissions] or "manager" in role_names

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None or data.job_title is not None:
        if not can_edit_contact:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or manager can update contact details")
        if data.phone is not None:
            user.phone = data.phone
        if data.job_title is not None:
            user.job_title = data.job_title
    if data.new_password is not None:
        if not data.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password required to set a new password")
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        user.password_hash = get_password_hash(data.new_password)
    db.flush()
    if data.full_name is not None or data.new_password is not None or data.phone is not None or data.job_title is not None:
        log_activity(db, user.id, "profile_updated", "profile", user.id, details="Profile updated")
    db.commit()
    db.refresh(user)
    return _user_response(user)
