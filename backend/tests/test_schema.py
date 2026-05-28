"""Integration tests for the Phase 2 schema.

These exercise the live Postgres database created and seeded by the
``db_engine`` fixture in ``conftest.py``. Each test runs inside a SAVEPOINT
that gets rolled back at the end, so tests don't see each other's writes.

Coverage maps to ``design/02-database-schema.md`` §2.5 Definition of Done:

* Seed produces the expected category + mapping counts.
* Seed is idempotent (re-applying yields zero new rows).
* SQLAlchemy round-trip insert/read for Category, Statement, Transaction.
* UNIQUE(transaction_ref) prevents duplicate inserts.
* CHECK constraints reject invalid type / amount / period_end.
* ON DELETE CASCADE removes child transactions with their parent statement.
* updated_at trigger fires on row update.
* merchant_mappings.confidence preserves NUMERIC(3,2) precision.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import Category, MerchantMapping, Statement, Transaction
from tests.conftest import SEED_FILE, _apply_sql_script

pytestmark = pytest.mark.asyncio


# ── Seed sanity ────────────────────────────────────────────────────────────


async def test_seed_loads_sixteen_categories(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        select(Category).order_by(Category.sort_order)
    )
    categories = list(result.scalars())
    assert len(categories) == 16

    names = {c.name for c in categories}
    assert {"Groceries", "Food & Dining", "Transfers", "Others", "Income"}.issubset(names)


async def test_transfers_and_others_are_system_categories(db_session: AsyncSession) -> None:
    transfers = (
        await db_session.execute(select(Category).where(Category.name == "Transfers"))
    ).scalar_one()
    others = (
        await db_session.execute(select(Category).where(Category.name == "Others"))
    ).scalar_one()

    assert transfers.is_system is True
    assert transfers.excluded_from_spending is True
    assert others.is_system is True
    assert others.excluded_from_spending is False


async def test_seed_loads_at_least_eighty_merchant_mappings(
    db_session: AsyncSession,
) -> None:
    count = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM merchant_mappings WHERE source = 'seed'")
        )
    ).scalar_one()
    assert count >= 80


async def test_seed_idempotency(db_engine: AsyncEngine) -> None:
    """Re-applying seed.sql produces zero additional rows.

    We use a separate engine connection (not the test session) because the
    seed file contains multiple statements, which only the asyncpg
    simple-query protocol accepts. This test is intentionally outside the
    SAVEPOINT-wrapped ``db_session`` since it commits via that protocol.
    """
    seed_sql = SEED_FILE.read_text(encoding="utf-8")

    async with db_engine.connect() as conn:
        cat_before = (
            await conn.execute(text("SELECT COUNT(*) FROM categories"))
        ).scalar_one()
        map_before = (
            await conn.execute(text("SELECT COUNT(*) FROM merchant_mappings"))
        ).scalar_one()

    await _apply_sql_script(db_engine, seed_sql)

    async with db_engine.connect() as conn:
        cat_after = (
            await conn.execute(text("SELECT COUNT(*) FROM categories"))
        ).scalar_one()
        map_after = (
            await conn.execute(text("SELECT COUNT(*) FROM merchant_mappings"))
        ).scalar_one()

    assert cat_after == cat_before
    assert map_after == map_before


# ── ORM round-trip ─────────────────────────────────────────────────────────


async def _make_statement(session: AsyncSession, **overrides) -> Statement:
    stmt = Statement(
        period_start=dt.date(2026, 4, 28),
        period_end=dt.date(2026, 5, 28),
        filename="phonepe_2026_05.pdf",
        raw_text="(raw extracted text)",
        source="phonepe",
        **overrides,
    )
    session.add(stmt)
    await session.flush()
    return stmt


async def test_orm_round_trip(db_session: AsyncSession) -> None:
    category = (
        await db_session.execute(select(Category).where(Category.name == "Food & Dining"))
    ).scalar_one()

    statement = await _make_statement(db_session)

    txn = Transaction(
        statement_id=statement.id,
        transaction_ref="T2604281930148688800258",
        utr_no="376914838281",
        date=dt.date(2026, 4, 28),
        time=dt.time(19, 30),
        description="Paid to Swiggy",
        merchant_raw="Swiggy Ltd",
        merchant_normalized="SWIGGY",
        amount=Decimal("259.50"),
        type="debit",
        category_id=category.id,
    )
    db_session.add(txn)
    await db_session.flush()

    fetched = (
        await db_session.execute(
            select(Transaction).where(Transaction.transaction_ref == "T2604281930148688800258")
        )
    ).scalar_one()

    assert fetched.statement_id == statement.id
    assert fetched.amount == Decimal("259.50")
    assert fetched.type == "debit"
    assert fetched.merchant_normalized == "SWIGGY"
    assert fetched.category_id == category.id
    assert fetched.needs_review is False
    assert fetched.is_manually_categorized is False


# ── Constraints ─────────────────────────────────────────────────────────────


async def test_unique_transaction_ref(db_session: AsyncSession) -> None:
    statement = await _make_statement(db_session)
    db_session.add(
        Transaction(
            statement_id=statement.id,
            transaction_ref="DUPLICATE_REF",
            date=dt.date(2026, 5, 1),
            description="x",
            amount=Decimal("1.00"),
            type="debit",
        )
    )
    await db_session.flush()

    db_session.add(
        Transaction(
            statement_id=statement.id,
            transaction_ref="DUPLICATE_REF",  # same ref!
            date=dt.date(2026, 5, 2),
            description="y",
            amount=Decimal("2.00"),
            type="debit",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_check_constraint_rejects_invalid_type(db_session: AsyncSession) -> None:
    statement = await _make_statement(db_session)
    db_session.add(
        Transaction(
            statement_id=statement.id,
            transaction_ref="BAD_TYPE",
            date=dt.date(2026, 5, 3),
            description="x",
            amount=Decimal("1.00"),
            type="invalid",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_check_constraint_rejects_negative_amount(db_session: AsyncSession) -> None:
    statement = await _make_statement(db_session)
    db_session.add(
        Transaction(
            statement_id=statement.id,
            transaction_ref="NEG_AMOUNT",
            date=dt.date(2026, 5, 3),
            description="x",
            amount=Decimal("-1.00"),
            type="debit",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_check_constraint_rejects_inverted_period(db_session: AsyncSession) -> None:
    db_session.add(
        Statement(
            period_start=dt.date(2026, 5, 28),
            period_end=dt.date(2026, 4, 28),  # end < start
            source="phonepe",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_merchant_mapping_source_check(db_session: AsyncSession) -> None:
    category = (
        await db_session.execute(select(Category).where(Category.name == "Others"))
    ).scalar_one()
    db_session.add(
        MerchantMapping(
            merchant_pattern="NEW_PATTERN",
            category_id=category.id,
            source="not_a_valid_source",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ── Triggers + cascades ─────────────────────────────────────────────────────


async def test_updated_at_trigger_fires_on_update(db_session: AsyncSession) -> None:
    """The BEFORE UPDATE trigger overwrites ``updated_at`` with ``NOW()``.

    Postgres ``NOW()`` is constant within a transaction (it's
    ``transaction_timestamp()``), so we can't prove the trigger ran by
    comparing pre- and post-update timestamps inside one transaction. Instead
    we plant a clearly-old ``updated_at`` value via direct INSERT (which
    doesn't fire the BEFORE UPDATE trigger), then UPDATE another column and
    verify the trigger overwrote our planted value.
    """
    statement = await _make_statement(db_session)

    planted = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    await db_session.execute(
        text(
            "INSERT INTO transactions "
            "(statement_id, transaction_ref, date, description, amount, type, "
            " created_at, updated_at) "
            "VALUES (:sid, :ref, :d, 'x', 1.00, 'debit', :ts, :ts)"
        ),
        {"sid": statement.id, "ref": "TRIG_TEST", "d": dt.date(2026, 5, 1), "ts": planted},
    )

    await db_session.execute(
        text("UPDATE transactions SET notes = 'note' WHERE transaction_ref = :ref"),
        {"ref": "TRIG_TEST"},
    )

    new_updated_at = (
        await db_session.execute(
            text(
                "SELECT updated_at FROM transactions WHERE transaction_ref = :ref"
            ),
            {"ref": "TRIG_TEST"},
        )
    ).scalar_one()

    assert new_updated_at != planted
    # Trigger sets updated_at = NOW(), which is the current transaction start.
    # We just need to know it's *recent*, not 2020.
    assert new_updated_at.year >= 2025


async def test_cascade_delete_drops_transactions(db_session: AsyncSession) -> None:
    statement = await _make_statement(db_session)
    for i in range(3):
        db_session.add(
            Transaction(
                statement_id=statement.id,
                transaction_ref=f"CASCADE_{i}",
                date=dt.date(2026, 5, 1),
                description=f"x{i}",
                amount=Decimal("1.00"),
                type="debit",
            )
        )
    await db_session.flush()

    count_before = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM transactions WHERE statement_id = :id"),
            {"id": statement.id},
        )
    ).scalar_one()
    assert count_before == 3

    await db_session.delete(statement)
    await db_session.flush()

    count_after = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM transactions WHERE statement_id = :id"),
            {"id": statement.id},
        )
    ).scalar_one()
    assert count_after == 0


# ── Type fidelity ───────────────────────────────────────────────────────────


async def test_merchant_mapping_confidence_precision(db_session: AsyncSession) -> None:
    category = (
        await db_session.execute(select(Category).where(Category.name == "Others"))
    ).scalar_one()
    db_session.add(
        MerchantMapping(
            merchant_pattern="LLM_TEST_PATTERN",
            category_id=category.id,
            source="llm",
            confidence=Decimal("0.85"),
        )
    )
    await db_session.flush()

    fetched = (
        await db_session.execute(
            select(MerchantMapping).where(
                MerchantMapping.merchant_pattern == "LLM_TEST_PATTERN"
            )
        )
    ).scalar_one()
    assert fetched.confidence == Decimal("0.85")
    assert fetched.source == "llm"
