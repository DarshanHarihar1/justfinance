"""Password verification + session-cookie signing primitives."""
from __future__ import annotations

import json
import time

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
    return TimestampSigner(get_settings().session_secret, salt="ft-session")


def create_session_token() -> str:
    """Sign a trivial session payload ``{v, iat}`` for the auth cookie."""
    payload = json.dumps({"v": 1, "iat": int(time.time())})
    return _signer().sign(payload.encode()).decode()


def validate_session_token(token: str) -> bool:
    settings = get_settings()
    try:
        raw = _signer().unsign(token, max_age=settings.session_max_age).decode()
    except (BadSignature, SignatureExpired):
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return data.get("v") == 1
