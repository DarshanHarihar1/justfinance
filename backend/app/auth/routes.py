from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.auth.bruteforce import (
    LOCKOUT_WINDOW_SECONDS,
    clear_attempts,
    is_locked_out,
    record_failed_attempt,
)
from app.core.config import get_settings
from app.core.exceptions import too_many_requests, unauthorized
from app.core.security import create_session_token, validate_session_token, verify_password

router = APIRouter()


class LoginBody(BaseModel):
    password: str


class MeOut(BaseModel):
    authenticated: bool = True


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _set_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(),
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/login", status_code=204)
async def login(body: LoginBody, request: Request, response: Response) -> None:
    ip = _client_ip(request)
    if is_locked_out(ip):
        raise too_many_requests(
            "Too many failed login attempts. Try again later.",
            retry_after=LOCKOUT_WINDOW_SECONDS,
        )
    settings = get_settings()
    if not verify_password(body.password, settings.app_password_hash):
        record_failed_attempt(ip)
        raise unauthorized()
    clear_attempts(ip)
    _set_session_cookie(response)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.get("/me", response_model=MeOut)
async def me(request: Request) -> MeOut:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token or not validate_session_token(token):
        raise unauthorized()
    return MeOut()
