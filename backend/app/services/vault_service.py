"""Encryption at rest for the credentials vault (Fernet / AES-128-CBC + HMAC).

The key comes from VAULT_KEY in the environment. When unset, a key is
derived from JWT_SECRET so the vault works out of the box — but then
rotating JWT_SECRET would orphan stored secrets, so production should
set an explicit VAULT_KEY (generate with:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
) and never change it once credentials exist."""
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from app.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    key = (settings.vault_key or "").strip()
    if key:
        return Fernet(key.encode())
    derived = base64.urlsafe_b64encode(hashlib.sha256(f"vault:{settings.jwt_secret}".encode()).digest())
    return Fernet(derived)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Raises ValueError when the stored token cannot be decrypted with the
    current key (VAULT_KEY changed, or JWT_SECRET rotated without one)."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Cannot decrypt: the vault key has changed since this secret was stored") from e
