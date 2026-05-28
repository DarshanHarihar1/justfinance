from __future__ import annotations

import calendar
import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import db_session
from app.core.exceptions import not_found
from app.models import MerchantMapping, Transaction
from app.schemas.transaction import (
    BulkCategorize,
    PaginatedTransactions,
    TransactionOut,
    TransactionPatch,
)

router = APIRouter()


def _month_bounds(month: int, year: int) -> tuple[dt.date, dt.date]:
    last_day = calendar.monthrange(year, month)[1]
    return dt.date(year, month, 1), dt.date(year, month, last_day)


@router.get("/transactions", response_model=PaginatedTransactions)
async def list_transactions(
    month: int | None = None,
    year: int | None = None,
    category_id: int | None = None,
    needs_review: bool | None = None,
    type: str | None = Query(default=None, alias="type"),
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(db_session),
) -> PaginatedTransactions:
    query = select(Transaction)
    if month is not None and year is not None:
        start, end = _month_bounds(month, year)
        query = query.where(Transaction.date >= start, Transaction.date <= end)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if needs_review is not None:
        query = query.where(Transaction.needs_review.is_(needs_review))
    if type is not None:
        query = query.where(Transaction.type == type)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Transaction.description.ilike(pattern),
                Transaction.merchant_raw.ilike(pattern),
                Transaction.merchant_normalized.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = int((await db.execute(count_query)).scalar_one())

    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            query.order_by(Transaction.date.desc(), Transaction.id.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedTransactions(
        items=[TransactionOut.model_validate(r) for r in rows],
        total=total,
    )


@router.post("/transactions/categorize", status_code=204)
async def bulk_categorize(
    body: BulkCategorize,
    db: AsyncSession = Depends(db_session),
) -> None:
    for item in body.items:
        txn = await db.get(Transaction, item.transaction_id)
        if txn is None:
            raise not_found("transaction")

        txn.category_id = item.category_id
        txn.is_manually_categorized = True
        txn.needs_review = False

        if item.remember and txn.merchant_normalized:
            stmt = (
                insert(MerchantMapping)
                .values(
                    merchant_pattern=txn.merchant_normalized,
                    category_id=item.category_id,
                    source="manual",
                    confidence=None,
                    times_used=1,
                )
                .on_conflict_do_update(
                    index_elements=["merchant_pattern"],
                    set_={
                        "category_id": item.category_id,
                        "source": "manual",
                        "confidence": None,
                    },
                )
            )
            await db.execute(stmt)

            await db.execute(
                update(Transaction)
                .where(
                    Transaction.merchant_normalized == txn.merchant_normalized,
                    Transaction.needs_review.is_(True),
                    Transaction.id != txn.id,
                )
                .values(
                    category_id=item.category_id,
                    is_manually_categorized=True,
                    needs_review=False,
                )
            )

    await db.commit()


@router.patch("/transactions/{transaction_id}", response_model=TransactionOut)
async def patch_transaction(
    transaction_id: int,
    body: TransactionPatch,
    db: AsyncSession = Depends(db_session),
) -> Transaction:
    txn = await db.get(Transaction, transaction_id)
    if txn is None:
        raise not_found("transaction")

    if body.category_id is not None:
        txn.category_id = body.category_id
        txn.is_manually_categorized = True
        txn.needs_review = False
    if body.notes is not None:
        txn.notes = body.notes

    if body.remember and txn.merchant_normalized and txn.category_id is not None:
        stmt = (
            insert(MerchantMapping)
            .values(
                merchant_pattern=txn.merchant_normalized,
                category_id=txn.category_id,
                source="manual",
                confidence=None,
                times_used=1,
            )
            .on_conflict_do_update(
                index_elements=["merchant_pattern"],
                set_={
                    "category_id": txn.category_id,
                    "source": "manual",
                    "confidence": None,
                },
            )
        )
        await db.execute(stmt)

    await db.commit()
    await db.refresh(txn)
    return txn
