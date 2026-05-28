"""Password verification + session-cookie signing primitives.

Phase 1 only ships the building blocks; the actual auth middleware and login
routes are wired in Phase 5 (``05-backend-api.md``). Keeping this module pure
(no FastAPI imports) lets us unit-test it in isolation later.
"""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time bcrypt comparison. Returns False on any verification error."""
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False


def _signer() -> TimestampSigner:
    return TimestampSigner(get_settings().session_secret)


def sign_session(value: str) -> str:
    """Sign a payload (e.g. a user id sentinel) into an opaque cookie value."""
    return _signer().sign(value.encode()).decode()


def unsign_session(token: str) -> str | None:
    """Return the original payload, or ``None`` if invalid/expired."""
    settings = get_settings()
    try:
        return _signer().unsign(token, max_age=settings.session_max_age).decode()
    except (BadSignature, SignatureExpired):
        return None
