from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import db_session
from app.core.exceptions import conflict, not_found
from app.models import Category, MerchantMapping, Transaction
from app.schemas.category import CategoryCreate, CategoryOut, CategoryPatch
from app.services.category_counts import category_to_out, mapping_counts_by_category

router = APIRouter()


@router.get("", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(db_session)) -> list[CategoryOut]:
    result = await db.execute(select(Category).order_by(Category.sort_order, Category.name))
    categories = list(result.scalars().all())
    counts = await mapping_counts_by_category(db)
    return [category_to_out(c, mapping_count=counts.get(c.id, 0)) for c in categories]


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(db_session),
) -> Category:
    existing = await db.execute(select(Category).where(Category.name == body.name))
    if existing.scalar_one_or_none() is not None:
        raise conflict("duplicate_category", f"Category '{body.name}' already exists.")
    category = Category(
        name=body.name,
        color=body.color,
        icon=body.icon,
        excluded_from_spending=body.excluded_from_spending,
        sort_order=body.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category_to_out(category, mapping_count=0)


@router.patch("/{category_id}", response_model=CategoryOut)
async def patch_category(
    category_id: int,
    body: CategoryPatch,
    db: AsyncSession = Depends(db_session),
) -> Category:
    category = await db.get(Category, category_id)
    if category is None:
        raise not_found("category")
    if body.name is not None:
        category.name = body.name
    if body.color is not None:
        category.color = body.color
    if body.icon is not None:
        category.icon = body.icon
    if body.excluded_from_spending is not None:
        category.excluded_from_spending = body.excluded_from_spending
    if body.sort_order is not None:
        category.sort_order = body.sort_order
    await db.commit()
    await db.refresh(category)
    counts = await mapping_counts_by_category(db)
    return category_to_out(category, mapping_count=counts.get(category.id, 0))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    move_to: int | None = Query(default=None),
    db: AsyncSession = Depends(db_session),
) -> None:
    category = await db.get(Category, category_id)
    if category is None:
        raise not_found("category")
    if category.is_system:
        raise conflict("system_category", "System categories cannot be deleted.")

    txn_count = (
        await db.execute(
            select(func.count()).where(Transaction.category_id == category_id)
        )
    ).scalar_one()
    mapping_count = (
        await db.execute(
            select(func.count()).where(MerchantMapping.category_id == category_id)
        )
    ).scalar_one()

    if (txn_count or mapping_count) and move_to is None:
        raise conflict(
            "category_in_use",
            "Provide move_to=<category_id> to reassign transactions and mappings.",
        )

    if move_to is not None:
        target = await db.get(Category, move_to)
        if target is None:
            raise not_found("target category")
        await db.execute(
            update(Transaction)
            .where(Transaction.category_id == category_id)
            .values(category_id=move_to)
        )
        await db.execute(
            update(MerchantMapping)
            .where(MerchantMapping.category_id == category_id)
            .values(category_id=move_to)
        )

    await db.delete(category)
    await db.commit()
