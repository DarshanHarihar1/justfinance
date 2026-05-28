from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction
from app.schemas.analytics import (
    CategoryBreakdown,
    DashboardOut,
    DashboardTotals,
    TopMerchant,
)
from app.schemas.transaction import TransactionOut

from .periods import month_bounds
from .queries import spend_by_category, spend_totals, top_merchants


def _dec_str(value: Decimal) -> str:
    return format(value, "f")


async def get_dashboard(
    db: AsyncSession,
    *,
    month: int,
    year: int,
) -> DashboardOut:
    income, expense, txn_count = await spend_totals(db, year=year, month=month)
    net = income - expense

    categories = await spend_by_category(db, year=year, month=month)
    expense_total = expense if expense > 0 else Decimal("1")

    by_category = [
        CategoryBreakdown(
            category_id=int(row["category_id"]),
            name=str(row["name"]),
            color=str(row["color"]),
            total=_dec_str(Decimal(str(row["total"]))),
            txn_count=int(row["txn_count"]),
            pct_of_expense=float(Decimal(str(row["total"])) / expense_total),
        )
        for row in categories
    ]

    merchants = await top_merchants(db, year=year, month=month, limit=10)
    top = [
        TopMerchant(
            merchant_normalized=str(row["merchant_normalized"]),
            total=_dec_str(Decimal(str(row["total"]))),
            txn_count=int(row["txn_count"]),
            category_id=int(row["category_id"]),
        )
        for row in merchants
    ]

    start, end = month_bounds(year, month)
    recent = (
        (
            await db.execute(
                select(Transaction)
                .where(Transaction.date >= start, Transaction.date <= end)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )

    review_count = (
        await db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.needs_review.is_(True),
            )
        )
    ).scalar_one()

    return DashboardOut(
        month=month,
        year=year,
        totals=DashboardTotals(
            income=_dec_str(income),
            expense=_dec_str(expense),
            net=_dec_str(net),
            txn_count=txn_count,
        ),
        by_category=by_category,
        top_merchants=top,
        recent_transactions=[TransactionOut.model_validate(t) for t in recent],
        needs_review_count=review_count,
    )
