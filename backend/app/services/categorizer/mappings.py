from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MerchantMapping


async def load_mapping_index(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(MerchantMapping.merchant_pattern, MerchantMapping.category_id)
    )
    return {pattern: category_id for pattern, category_id in rows.all()}


async def record_mapping_hit(db: AsyncSession, merchant_pattern: str) -> None:
    await db.execute(
        update(MerchantMapping)
        .where(MerchantMapping.merchant_pattern == merchant_pattern)
        .values(
            times_used=MerchantMapping.times_used + 1,
            last_used_at=datetime.now(UTC),
        )
    )


async def insert_llm_mapping(
    db: AsyncSession,
    *,
    merchant_pattern: str,
    category_id: int,
    confidence: Decimal,
) -> None:
    stmt = (
        insert(MerchantMapping)
        .values(
            merchant_pattern=merchant_pattern,
            category_id=category_id,
            source="llm",
            confidence=confidence,
            times_used=1,
            last_used_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["merchant_pattern"])
    )
    await db.execute(stmt)
