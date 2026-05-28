from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import MerchantMapping, Transaction
from tests.test_upload_pipeline import _upload_pdf


@pytest.mark.asyncio
@pytest.mark.usefixtures("requires_postgres")
async def test_bulk_categorize_remember_cascades_review(
    auth_client: TestClient,
    db_engine: AsyncEngine,
) -> None:
    _upload_pdf(auth_client)
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    # Pick any needs_review txn and normalize a synthetic group by patching
    async with session_factory() as session:
        txns = (
            await session.execute(
                select(Transaction).where(Transaction.needs_review.is_(True)).limit(3)
            )
        ).scalars().all()
        assert len(txns) >= 1
        pattern = "CASCADE TEST MERCHANT"
        for txn in txns:
            txn.merchant_normalized = pattern
        await session.commit()

    async with session_factory() as session:
        txns = (
            await session.execute(
                select(Transaction).where(Transaction.merchant_normalized == pattern)
            )
        ).scalars().all()
        target = txns[0]
        categories = auth_client.get("/api/categories").json()
        food_id = next(c["id"] for c in categories if c["name"] == "Food & Dining")

    response = auth_client.post(
        "/api/transactions/categorize",
        json={
            "items": [
                {
                    "transaction_id": target.id,
                    "category_id": food_id,
                    "remember": True,
                }
            ]
        },
    )
    assert response.status_code == 204

    async with session_factory() as session:
        mapping = (
            await session.execute(
                select(MerchantMapping).where(MerchantMapping.merchant_pattern == pattern)
            )
        ).scalar_one_or_none()
        assert mapping is not None
        assert mapping.source == "manual"

        still_review = (
            await session.execute(
                select(Transaction).where(
                    Transaction.merchant_normalized == pattern,
                    Transaction.needs_review.is_(True),
                )
            )
        ).scalars().all()
        assert still_review == []
