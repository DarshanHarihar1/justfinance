from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .periods import month_bounds


async def spend_totals(
    db: AsyncSession,
    *,
    year: int,
    month: int,
) -> tuple[Decimal, Decimal, int]:
    start, end = month_bounds(year, month)
    row = (
        await db.execute(
            text(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN type = 'credit' THEN amount END), 0) AS income,
                  COALESCE(SUM(CASE WHEN type = 'debit' THEN amount END), 0) AS expense,
                  COUNT(*) AS txn_count
                FROM v_spend
                WHERE date >= :start AND date <= :end
                """
            ),
            {"start": start, "end": end},
        )
    ).one()
    return Decimal(str(row.income)), Decimal(str(row.expense)), int(row.txn_count)


async def spend_by_category(
    db: AsyncSession,
    *,
    year: int,
    month: int,
) -> list[dict[str, Any]]:
    start, end = month_bounds(year, month)
    rows = (
        await db.execute(
            text(
                """
                SELECT
                  category_id,
                  category_name AS name,
                  category_color AS color,
                  SUM(amount) AS total,
                  COUNT(*) AS txn_count
                FROM v_spend
                WHERE type = 'debit'
                  AND date >= :start AND date <= :end
                GROUP BY category_id, category_name, category_color
                ORDER BY total DESC
                """
            ),
            {"start": start, "end": end},
        )
    ).mappings()
    return [dict(r) for r in rows]


async def top_merchants(
    db: AsyncSession,
    *,
    year: int,
    month: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    start, end = month_bounds(year, month)
    rows = (
        await db.execute(
            text(
                """
                SELECT
                  merchant_normalized,
                  category_id,
                  SUM(amount) AS total,
                  COUNT(*) AS txn_count
                FROM v_spend
                WHERE type = 'debit'
                  AND date >= :start AND date <= :end
                  AND merchant_normalized IS NOT NULL
                GROUP BY merchant_normalized, category_id
                ORDER BY total DESC
                LIMIT :limit
                """
            ),
            {"start": start, "end": end, "limit": limit},
        )
    ).mappings()
    return [dict(r) for r in rows]


async def mom_raw(
    db: AsyncSession,
    *,
    since: dt.date,
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT
                  date_part('year', date)::int AS year,
                  date_part('month', date)::int AS month,
                  COALESCE(SUM(CASE WHEN type = 'credit' THEN amount END), 0) AS income,
                  COALESCE(SUM(CASE WHEN type = 'debit' THEN amount END), 0) AS expense
                FROM v_spend
                WHERE date >= :since
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            ),
            {"since": since},
        )
    ).mappings()
    return [dict(r) for r in rows]


async def trend_months(
    db: AsyncSession,
    *,
    category_id: int,
    start: dt.date,
    end: dt.date,
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT
                  date_part('year', date)::int AS year,
                  date_part('month', date)::int AS month,
                  COALESCE(SUM(amount), 0) AS total,
                  COUNT(*) AS txn_count
                FROM v_spend
                WHERE type = 'debit'
                  AND category_id = :category_id
                  AND date >= :start AND date <= :end
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            ),
            {"category_id": category_id, "start": start, "end": end},
        )
    ).mappings()
    return [dict(r) for r in rows]


async def trend_top_merchants(
    db: AsyncSession,
    *,
    category_id: int,
    start: dt.date,
    end: dt.date,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT merchant_normalized, SUM(amount) AS total
                FROM v_spend
                WHERE type = 'debit'
                  AND category_id = :category_id
                  AND date >= :start AND date <= :end
                  AND merchant_normalized IS NOT NULL
                GROUP BY merchant_normalized
                ORDER BY total DESC
                LIMIT :limit
                """
            ),
            {
                "category_id": category_id,
                "start": start,
                "end": end,
                "limit": limit,
            },
        )
    ).mappings()
    return [dict(r) for r in rows]
