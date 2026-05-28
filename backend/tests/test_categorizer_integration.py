"""Integration tests for categorize_batch (real DB, mocked LLM)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, MerchantMapping
from app.services.categorizer import categorize_batch
from app.services.llm.openrouter import OpenRouterClient
from app.services.pdf_parser.types import ParsedTransaction


def _txn(merchant_raw: str, *, ref: str = "T1") -> ParsedTransaction:
    return ParsedTransaction(
        date=date(2026, 5, 1),
        time=None,
        description=f"Paid to {merchant_raw}",
        merchant_raw=merchant_raw,
        amount=Decimal("10.00"),
        type="debit",
        transaction_ref=ref,
        utr_no=None,
        account_last4="4200",
    )


def _llm_client() -> OpenRouterClient:
    return OpenRouterClient(
        api_key="test",
        base_url="https://openrouter.test",
        model="test/model",
        app_name="app",
        app_url="http://localhost",
    )


@pytest.mark.asyncio
async def test_seed_mapping_hit_without_llm(db_session: AsyncSession) -> None:
    llm = _llm_client()
    llm.chat_json = AsyncMock()  # type: ignore[method-assign]

    results = await categorize_batch(
        [_txn("Swiggy Ltd", ref="T-swiggy")],
        own_account_last4s=set(),
        db=db_session,
        llm=llm,
    )

    assert len(results) == 1
    assert results[0].source == "mapping"
    assert results[0].needs_review is False
    assert results[0].merchant_normalized == "SWIGGY"
    food_id = (
        await db_session.execute(select(Category.id).where(Category.name == "Food & Dining"))
    ).scalar_one()
    assert results[0].category_id == food_id
    llm.chat_json.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_low_confidence_does_not_persist_mapping(db_session: AsyncSession) -> None:
    llm = _llm_client()
    llm.chat_json = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "results": [
                {
                    "merchant": "MYSTERY MART",
                    "category": "Shopping",
                    "confidence": 0.40,
                }
            ]
        }
    )

    results = await categorize_batch(
        [_txn("Mystery Mart", ref="T-mystery")],
        own_account_last4s=set(),
        db=db_session,
        llm=llm,
    )

    assert results[0].needs_review is True
    assert results[0].source == "llm"
    rows = (
        await db_session.execute(
            select(MerchantMapping).where(MerchantMapping.merchant_pattern == "MYSTERY MART")
        )
    ).all()
    assert rows == []


@pytest.mark.asyncio
async def test_high_confidence_persists_mapping(db_session: AsyncSession) -> None:
    llm = _llm_client()
    llm.chat_json = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "results": [
                {
                    "merchant": "BRAND NEW SHOP",
                    "category": "Shopping",
                    "confidence": 0.92,
                }
            ]
        }
    )

    results = await categorize_batch(
        [_txn("Brand New Shop", ref="T-new")],
        own_account_last4s=set(),
        db=db_session,
        llm=llm,
    )

    assert results[0].needs_review is False
    assert results[0].source == "llm"
    row = (
        await db_session.execute(
            select(MerchantMapping).where(MerchantMapping.merchant_pattern == "BRAND NEW SHOP")
        )
    ).scalar_one()
    assert row.source == "llm"
    assert float(row.confidence) == pytest.approx(0.92)


@pytest.mark.asyncio
async def test_batch_issues_one_llm_call_for_many_unknowns(db_session: AsyncSession) -> None:
    llm = _llm_client()
    llm.chat_json = AsyncMock(  # type: ignore[method-assign]
        side_effect=lambda **kwargs: {
            "results": [
                {
                    "merchant": m.removeprefix("- ").strip(),
                    "category": "Others",
                    "confidence": 0.5,
                }
                for m in kwargs["user"].splitlines()
                if m.startswith("- ")
            ]
        }
    )

    merchants = [f"Unknown Merchant {i}" for i in range(15)]
    txns = [_txn(m, ref=f"T-{i}") for i, m in enumerate(merchants)]

    await categorize_batch(txns, own_account_last4s=set(), db=db_session, llm=llm)

    assert llm.chat_json.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_missing_api_key_skips_llm(db_session: AsyncSession) -> None:
    llm = OpenRouterClient(
        api_key="",
        base_url="https://openrouter.test",
        model="m",
        app_name="app",
        app_url="http://x",
    )
    llm.chat_json = AsyncMock()  # type: ignore[method-assign]

    results = await categorize_batch(
        [_txn("Totally Unknown Place", ref="T-skip")],
        own_account_last4s=set(),
        db=db_session,
        llm=llm,
    )

    assert results[0].needs_review is True
    llm.chat_json.assert_not_called()  # type: ignore[attr-defined]
