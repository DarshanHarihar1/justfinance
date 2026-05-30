from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found, unprocessable
from app.models import Category
from app.schemas.analytics import (
    TrendCategory,
    TrendMonthPoint,
    TrendOut,
    TrendTopMerchant,
)

from .periods import month_bounds, trailing_months
from .queries import trend_months, trend_top_merchants


def _dec_str(value: Decimal) -> str:
    return format(value, "f")


def _parse_month_param(value: str) -> tuple[int, int]:
    try:
        parsed = dt.date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise unprocessable(
            "invalid_date_range",
            f"Invalid month parameter: {value!r} (expected YYYY-MM)",
        ) from exc
    return parsed.year, parsed.month


async def get_trend(
    db: AsyncSession,
    *,
    category_id: int,
    from_param: str | None = None,
    to_param: str | None = None,
) -> TrendOut:
    category = await db.get(Category, category_id)
    if category is None:
        raise not_found("category")

    if from_param and to_param:
        y0, m0 = _parse_month_param(from_param)
        y1, m1 = _parse_month_param(to_param)
        start, _ = month_bounds(y0, m0)
        _, end = month_bounds(y1, m1)
        month_keys = []
        y, m = y0, m0
        while (y, m) <= (y1, m1):
            month_keys.append((y, m))
            if m == 12:
                y, m = y + 1, 1
            else:
                m += 1
    else:
        month_keys = trailing_months(12)
        start, _ = month_bounds(month_keys[0][0], month_keys[0][1])
        _, end = month_bounds(month_keys[-1][0], month_keys[-1][1])

    raw = await trend_months(
        db, category_id=category_id, start=start, end=end
    )
    by_key = {(int(r["year"]), int(r["month"])): r for r in raw}

    points = []
    for year, month in month_keys:
        row = by_key.get((year, month))
        if row:
            total = Decimal(str(row["total"]))
            txn_count = int(row["txn_count"])
        else:
            total = Decimal("0")
            txn_count = 0
        points.append(
            TrendMonthPoint(
                year=year,
                month=month,
                total=_dec_str(total),
                txn_count=txn_count,
            )
        )

    merchants = await trend_top_merchants(
        db, category_id=category_id, start=start, end=end, limit=10
    )
    top = [
        TrendTopMerchant(
            merchant_normalized=str(row["merchant_normalized"]),
            total=_dec_str(Decimal(str(row["total"]))),
        )
        for row in merchants
    ]

    return TrendOut(
        category=TrendCategory(
            id=category.id,
            name=category.name,
            color=category.color,
        ),
        months=points,
        top_merchants=top,
    )
