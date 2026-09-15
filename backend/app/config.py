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
    vault_key: str = ""  # Fernet key for the credentials vault; derived from jwt_secret when empty
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

    # Used only by scripts/seed_db.py for the initial admin user
    admin_email: str = "admin@example.com"
    admin_password: str = ""

    # Super admin (god mode): one email with full access and no activity/audit logs. Empty = disabled.
    super_admin_email: str = ""

    # Public website base URL (no trailing slash) used in booking emails for the invitee's
    # cancel/reschedule link, e.g. https://fuorix.com -> https://fuorix.com/book/manage/<token>
    booking_public_url: str = ""

    # Google Calendar + Meet for booking hosts (OAuth client from Google Cloud Console).
    # Redirect URI registered there must be <FRONTEND_URL>/api/v1/integrations/google/callback
    # unless GOOGLE_REDIRECT_URI overrides it. Empty client id = feature hidden.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # Calendly webhook signing key (shown once when the webhook subscription is created, see
    # scripts/register_calendly_webhook.py). Empty = POST /api/v1/webhooks/calendly is disabled (404).
    calendly_webhook_signing_key: str = ""
    # Seconds a webhook timestamp may lag before it is rejected as a replay.
    calendly_webhook_tolerance_seconds: int = 300

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
        extra = "ignore"  # unknown keys in .env must not crash startup


@lru_cache
def get_settings() -> Settings:
    return Settings()
