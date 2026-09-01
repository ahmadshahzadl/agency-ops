from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, Token, UserResponse, ProfileUpdate
from app.api.deps import get_current_user, is_super_admin
from app.models import User
from app.core.security import verify_password, get_password_hash
from app.services.auth_service import authenticate_user, create_tokens_for_user, refresh_access_token
from app.services.activity_service import log_activity
from app.core.rate_limit import login_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    limiter_key = data.email.strip().lower()
    retry_after = login_limiter.retry_after(limiter_key)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    user = authenticate_user(db, data.email, data.password)
    if not user:
        login_limiter.record_failure(limiter_key)
        known = db.query(User).filter(User.email == data.email).first()
        if known:
            log_activity(db, known.id, "login_failed", "user", known.id, details="Failed sign-in attempt")
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    login_limiter.reset(limiter_key)
    log_activity(db, user.id, "user_login", "user", user.id, details="Signed in")
    db.commit()
    tokens = create_tokens_for_user(user)
    return Token(**tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sign out everywhere: bumps token_version so every issued token for this user is invalid."""
    user.token_version = (user.token_version or 0) + 1
    log_activity(db, user.id, "user_logout", "user", user.id, details="Signed out (all sessions)")
    db.commit()


@router.post("/refresh", response_model=Token)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    tokens = refresh_access_token(db, data.refresh_token)
    return Token(**tokens)


def _user_response(user: User):
    if is_super_admin(user):
        permissions = ["admin:all"]
        role_names = [r.name for r in user.roles]
        can_manage_tasks = True
        can_manage_leads = True
    else:
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
    can_edit_contact = is_super_admin(user) or "admin:all" in [p.code for r in user.roles for p in r.permissions] or "manager" in role_names

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None or data.job_title is not None:
        if not can_edit_contact:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or manager can update contact details")
        if data.phone is not None:
            user.phone = data.phone
        if data.job_title is not None:
            user.job_title = data.job_title
    password_changed = False
    if data.new_password is not None:
        if not data.current_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password required to set a new password")
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        user.password_hash = get_password_hash(data.new_password)
        # Invalidate every existing token (including any stolen ones)
        user.token_version = (user.token_version or 0) + 1
        password_changed = True
    db.flush()
    if data.full_name is not None or data.new_password is not None or data.phone is not None or data.job_title is not None:
        log_activity(db, user.id, "profile_updated", "profile", user.id, details="Profile updated")
    db.commit()
    db.refresh(user)
    response = _user_response(user)
    if password_changed:
        # Issue fresh tokens so this session survives its own revocation
        tokens = create_tokens_for_user(user)
        response.access_token = tokens["access_token"]
        response.refresh_token = tokens["refresh_token"]
    return response
