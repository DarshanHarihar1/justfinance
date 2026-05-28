from __future__ import annotations

import csv
import datetime as dt
import io
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Transaction

CSV_HEADER = [
    "id",
    "statement_id",
    "date",
    "time",
    "description",
    "merchant_raw",
    "merchant_normalized",
    "amount",
    "type",
    "category",
    "is_manually_categorized",
    "needs_review",
    "notes",
    "transaction_ref",
    "utr_no",
]


async def iter_transactions_csv(
    db: AsyncSession,
    *,
    from_date: dt.date | None = None,
    to_date: dt.date | None = None,
) -> AsyncIterator[bytes]:
    """Stream CSV rows for all matching transactions."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    yield buffer.getvalue().encode("utf-8")
    buffer.seek(0)
    buffer.truncate(0)

    query = (
        select(Transaction, Category.name)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    if from_date is not None:
        query = query.where(Transaction.date >= from_date)
    if to_date is not None:
        query = query.where(Transaction.date <= to_date)

    stream = await db.stream(query)
    async for row in stream:
        txn: Transaction = row[0]
        category_name: str | None = row[1]
        writer.writerow(
            [
                txn.id,
                txn.statement_id,
                txn.date.isoformat(),
                txn.time.isoformat() if txn.time else "",
                txn.description,
                txn.merchant_raw or "",
                txn.merchant_normalized or "",
                format(txn.amount, "f"),
                txn.type,
                category_name or "",
                txn.is_manually_categorized,
                txn.needs_review,
                txn.notes or "",
                txn.transaction_ref,
                txn.utr_no or "",
            ]
        )
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)
