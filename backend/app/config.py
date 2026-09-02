from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache

# Resolve .env from backend directory so it works regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

_DEFAULT_JWT_SECRET = "change-me-in-production-use-env"


class Settings(BaseSettings):
    app_name: str = "Fuorix API"
    app_version: str = "0.0.1"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/office_software"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://localhost:5173,app://."

    # File attachments: stored on local disk (override for a mounted volume in production)
    upload_dir: str = str(_BACKEND_DIR / "uploads")
    max_upload_mb: int = 15

    # Email (SMTP). Leave smtp_host empty to disable all outgoing email.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # defaults to smtp_user when empty
    smtp_tls: bool = True
    # Base URL of the web frontend, used for links in emails (reset password, notifications)
    frontend_url: str = "http://localhost:5173"

    # Shown in the footer of generated invoice/quote PDFs (address, tax id, ...)
    company_details: str = ""

    # Super admin (god mode): one email with full access and no activity/audit logs. Empty = disabled.
    super_admin_email: str = ""

    @model_validator(mode="after")
    def _enforce_safe_config(self):
        # The default JWT secret is public (it's in the repo); anyone knowing it can forge
        # tokens for any user. Refuse to start with it outside explicit local debug mode.
        if self.jwt_secret == _DEFAULT_JWT_SECRET and not self.debug:
            raise RuntimeError(
                "Refusing to start: JWT_SECRET is unset (using the insecure built-in default). "
                "Set JWT_SECRET in the environment or backend/.env (generate one with: openssl rand -hex 32), "
                "or set DEBUG=true for local development only."
            )
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # CORSMiddleware runs with allow_credentials=True; a wildcard origin with credentials
        # is rejected by browsers and hides misconfiguration. Require explicit origins.
        if "*" in origins:
            raise RuntimeError(
                "Refusing to start: CORS_ORIGINS must not contain '*'. "
                "List explicit origins, e.g. https://app.example.com,app://."
            )
        return self

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
