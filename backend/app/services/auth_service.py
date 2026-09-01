from sqlalchemy.orm import Session
from app.models import User
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token, token_version_matches
from fastapi import HTTPException, status


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_tokens_for_user(user: User) -> dict:
    tv = user.token_version or 0
    return {
        "access_token": create_access_token(str(user.id), tv),
        "refresh_token": create_refresh_token(str(user.id), tv),
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    from uuid import UUID
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == UUID(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not token_version_matches(payload, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    return {
        "access_token": create_access_token(str(user.id), user.token_version or 0),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
