from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import unprocessable
from app.models import Statement, Transaction
from app.services.categorizer import categorize_batch, detect_own_account_last4s
from app.services.llm.openrouter import OpenRouterClient
from app.services.pdf_parser import parse_phonepe_pdf


@dataclass(frozen=True)
class ParsedSummary:
    statement_id: int
    period_start: dt.date
    period_end: dt.date
    parsed_count: int
    new_count: int
    needs_review_count: int
    warnings: list[str]


async def ingest_statement(
    *,
    pdf_bytes: bytes,
    filename: str,
    db: AsyncSession,
    llm: OpenRouterClient,
) -> ParsedSummary:
    warnings: list[str] = []
    parsed = parse_phonepe_pdf(pdf_bytes)
    if not parsed.transactions:
        raise unprocessable(
            "phonepe_parse_empty",
            "No transactions found. Is this a PhonePe Transaction Statement PDF?",
        )

    if len(parsed.raw_text) > 5000 and len(parsed.transactions) < 5:
        warnings.append("phonepe_parse_low_yield")

    period_start = parsed.period_start
    period_end = parsed.period_end
    if period_start is None or period_end is None:
        period_start = min(t.date for t in parsed.transactions)
        period_end = max(t.date for t in parsed.transactions)

    statement = await get_or_create_statement(
        db,
        period_start=period_start,
        period_end=period_end,
        filename=filename,
        raw_text=parsed.raw_text,
    )

    refs = [t.transaction_ref for t in parsed.transactions]
    existing = set(
        (
            await db.scalars(
                select(Transaction.transaction_ref).where(
                    Transaction.transaction_ref.in_(refs)
                )
            )
        ).all()
    )
    new_txns = [t for t in parsed.transactions if t.transaction_ref not in existing]

    own_last4s = detect_own_account_last4s(parsed.raw_text)

    results: list = []
    if new_txns:
        if not llm.enabled:
            warnings.append("llm_disabled")
        results = await categorize_batch(
            new_txns,
            own_account_last4s=own_last4s,
            db=db,
            llm=llm,
        )

        rows = [
            Transaction(
                statement_id=statement.id,
                transaction_ref=t.transaction_ref,
                utr_no=t.utr_no,
                date=t.date,
                time=t.time,
                description=t.description,
                merchant_raw=t.merchant_raw,
                merchant_normalized=r.merchant_normalized,
                amount=t.amount,
                type=t.type,
                category_id=r.category_id,
                is_manually_categorized=False,
                needs_review=r.needs_review,
            )
            for t, r in zip(new_txns, results, strict=True)
        ]
        db.add_all(rows)

    await db.commit()

    return ParsedSummary(
        statement_id=statement.id,
        period_start=period_start,
        period_end=period_end,
        parsed_count=len(parsed.transactions),
        new_count=len(new_txns),
        needs_review_count=sum(1 for r in results if r.needs_review),
        warnings=warnings,
    )


async def get_or_create_statement(
    db: AsyncSession,
    *,
    period_start: dt.date,
    period_end: dt.date,
    filename: str,
    raw_text: str,
) -> Statement:
    existing = (
        await db.execute(
            select(Statement).where(
                Statement.period_start == period_start,
                Statement.period_end == period_end,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.filename = filename
        existing.raw_text = raw_text
        await db.flush()
        return existing

    statement = Statement(
        period_start=period_start,
        period_end=period_end,
        filename=filename,
        raw_text=raw_text,
        source="phonepe",
    )
    db.add(statement)
    await db.flush()
    return statement
