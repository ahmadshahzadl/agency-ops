from datetime import datetime, timedelta
import bcrypt
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, token_version: int = 0) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": str(subject), "exp": expire, "type": "access", "tv": token_version}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, token_version: int = 0) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh", "tv": token_version}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def token_version_matches(payload: dict, user) -> bool:
    """True if the token's version claim matches the user's current token_version."""
    return payload.get("tv", -1) == (getattr(user, "token_version", 0) or 0)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
