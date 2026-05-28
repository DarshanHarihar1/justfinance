from __future__ import annotations

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application HTTP error."""

    def __init__(self, status_code: int, error: str, message: str | None = None) -> None:
        detail: dict[str, str] = {"error": error}
        if message:
            detail["message"] = message
        super().__init__(status_code=status_code, detail=detail)


def unauthenticated() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "unauthenticated")


def unauthorized() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "unauthorized")


def not_found(resource: str = "resource") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{resource} not found")


def conflict(error: str, message: str | None = None) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, error, message)


def unprocessable(error: str, message: str | None = None) -> AppError:
    return AppError(status.HTTP_422_UNPROCESSABLE_ENTITY, error, message)


def too_many_requests(message: str, *, retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"error": "too_many_requests", "message": message},
        headers={"Retry-After": str(retry_after)},
    )
