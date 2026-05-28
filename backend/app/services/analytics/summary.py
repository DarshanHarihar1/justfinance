from __future__ import annotations

import json
import re
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import SpendSummaryCategory, SpendSummaryPayload

from .periods import month_label, prev_month
from .queries import spend_by_category, spend_totals, top_merchants

_PERSON_NAME = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$")


def _safe_merchant_label(name: str) -> bool:
    if _PERSON_NAME.match(name.strip()):
        return False
    return True


async def build_spend_summary(
    db: AsyncSession,
    *,
    month: int,
    year: int,
) -> SpendSummaryPayload:
    income, expense, _ = await spend_totals(db, year=year, month=month)
    categories = await spend_by_category(db, year=year, month=month)
    expense_f = float(expense) if expense > 0 else 1.0

    by_category = [
        SpendSummaryCategory(
            name=str(row["name"]),
            total=float(Decimal(str(row["total"]))),
            txn_count=int(row["txn_count"]),
            pct=float(Decimal(str(row["total"])) / Decimal(str(expense_f))),
        )
        for row in categories
    ]

    py, pm = prev_month(year, month)
    prev_rows = await spend_by_category(db, year=py, month=pm)
    prev_expense = sum(Decimal(str(r["total"])) for r in prev_rows) or Decimal("1")
    prev_month_by_category = [
        SpendSummaryCategory(
            name=str(row["name"]),
            total=float(Decimal(str(row["total"]))),
            txn_count=int(row["txn_count"]),
            pct=float(Decimal(str(row["total"])) / prev_expense),
        )
        for row in prev_rows
    ]

    merchants = await top_merchants(db, year=year, month=month, limit=8)
    top_merchant_payload: list[dict[str, str | float | int]] = []
    for row in merchants:
        label = str(row["merchant_normalized"])
        if not _safe_merchant_label(label):
            continue
        top_merchant_payload.append(
            {
                "merchant": label,
                "total": float(Decimal(str(row["total"]))),
                "txn_count": int(row["txn_count"]),
            }
        )

    return SpendSummaryPayload(
        month=month_label(year, month),
        totals={
            "income": float(income),
            "expense": float(expense),
        },
        by_category=by_category,
        prev_month_by_category=prev_month_by_category,
        top_merchants=top_merchant_payload,
    )


def summary_cache_key(payload: SpendSummaryPayload) -> str:
    data = payload.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
