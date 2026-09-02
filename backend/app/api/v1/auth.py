import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, Token, UserResponse, ProfileUpdate, ForgotPasswordRequest, ResetPasswordRequest
from app.api.deps import get_current_user, is_super_admin
from app.models import User, PasswordResetToken
from app.core.security import verify_password, get_password_hash
from app.services.auth_service import authenticate_user, create_tokens_for_user, refresh_access_token
from app.services.activity_service import log_activity
from app.services import email_service
from app.core.rate_limit import login_limiter, FailureRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])

# Every forgot-password request counts (not just failures): 3 per email per 15 min.
forgot_limiter = FailureRateLimiter(max_failures=3, window_seconds=900)


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


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Always returns 200 to prevent user enumeration; emails a reset link when the account exists."""
    email = data.email.strip().lower()
    response = {"message": "If that email is registered, a reset link has been sent."}
    if forgot_limiter.retry_after(f"forgot:{email}"):
        return response  # silently drop when rate-limited
    forgot_limiter.record_failure(f"forgot:{email}")
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if user:
        token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        log_activity(db, user.id, "password_reset_requested", "user", user.id, details="Password reset requested")
        db.commit()
        email_service.send_password_reset(user.email, user.full_name or "", token)
    return response


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(data.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    prt = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)
    if not prt or prt.used_at is not None or prt.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link")
    user = db.query(User).filter(User.id == prt.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link")
    user.password_hash = get_password_hash(data.new_password)
    # Revoke every existing session/token, including whoever prompted the reset
    user.token_version = (user.token_version or 0) + 1
    prt.used_at = now
    log_activity(db, user.id, "password_reset_completed", "user", user.id, details="Password reset via email link")
    db.commit()
    return {"message": "Password updated. You can sign in with your new password."}


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
    client_name = None
    if user.client_id is not None:
        from app.models import Client
        from app.database import SessionLocal
        _db = SessionLocal()
        try:
            c = _db.query(Client).filter(Client.id == user.client_id).first()
            client_name = c.name if c else None
        finally:
            _db.close()
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
        is_client=user.client_id is not None,
        client_name=client_name,
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
