from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Resolve .env from backend directory so it works regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "AgencyOps API"
    app_version: str = "0.0.1"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/office_software"
    jwt_secret: str = "change-me-in-production-use-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://localhost:5173,app://."

    # Super admin (god mode): one email with full access and no activity/audit logs. Empty = disabled.
    super_admin_email: str = ""

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
