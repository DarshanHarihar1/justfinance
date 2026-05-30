from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, MerchantMapping, Transaction
from app.schemas.category import CategoryOut


async def mapping_counts_by_category(db: AsyncSession) -> dict[int, int]:
    rows = await db.execute(
        select(MerchantMapping.category_id, func.count())
        .group_by(MerchantMapping.category_id)
    )
    return {int(cat_id): int(count) for cat_id, count in rows.all()}


async def transaction_counts_by_category(db: AsyncSession) -> dict[int, int]:
    rows = await db.execute(
        select(Transaction.category_id, func.count())
        .where(Transaction.category_id.is_not(None))
        .group_by(Transaction.category_id)
    )
    return {int(cat_id): int(count) for cat_id, count in rows.all()}


def category_to_out(
    category: Category,
    *,
    mapping_count: int = 0,
    transaction_count: int = 0,
) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        name=category.name,
        color=category.color,
        icon=category.icon,
        is_system=category.is_system,
        excluded_from_spending=category.excluded_from_spending,
        sort_order=category.sort_order,
        mapping_count=mapping_count,
        transaction_count=transaction_count,
    )
