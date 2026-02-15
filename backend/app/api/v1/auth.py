from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, Token, UserResponse
from app.api.deps import get_current_user
from app.models import User
from app.services.auth_service import authenticate_user, create_tokens_for_user, refresh_access_token

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
    for role in user.roles:
        for perm in role.permissions:
            permissions.append(perm.code)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        permissions=permissions,
    )
