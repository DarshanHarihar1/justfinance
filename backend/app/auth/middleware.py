from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings
from app.core.security import validate_session_token

_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/healthz"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
    }
)


class SessionAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:
        super().__init__(app)
        self._cookie_name = settings.session_cookie_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        if (request.method, request.url.path) in _ALLOWLIST:
            return await call_next(request)
        if request.url.path in ("/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        token = request.cookies.get(self._cookie_name)
        if not token or not validate_session_token(token):
            return JSONResponse(
                {"error": "unauthenticated"},
                status_code=401,
            )
        return await call_next(request)
