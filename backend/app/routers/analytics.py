from __future__ import annotations

from fastapi import APIRouter, status

from app.core.exceptions import AppError

router = APIRouter()


def _not_implemented() -> AppError:
    return AppError(
        status.HTTP_501_NOT_IMPLEMENTED,
        "not_implemented",
        "Analytics endpoints are implemented in Phase 7.",
    )


@router.get("/dashboard/{month}/{year}")
async def dashboard(month: int, year: int) -> None:
    raise _not_implemented()


@router.get("/mom")
async def month_over_month() -> None:
    raise _not_implemented()


@router.get("/trends/{category_id}")
async def trends(category_id: int) -> None:
    raise _not_implemented()


@router.post("/insights")
async def insights() -> None:
    raise _not_implemented()


@router.post("/ask")
async def ask() -> None:
    raise _not_implemented()
