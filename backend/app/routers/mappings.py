from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import db_session
from app.core.exceptions import conflict, not_found
from app.models import Category, MerchantMapping
from app.schemas.mapping import MappingCreate, MappingOut, MappingPatch, PaginatedMappings
from app.services.categorizer.normalize import normalize

router = APIRouter()


@router.get("", response_model=PaginatedMappings)
async def list_mappings(
    source: str | None = None,
    category_id: int | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(db_session),
) -> PaginatedMappings:
    query = select(MerchantMapping)
    if source is not None:
        query = query.where(MerchantMapping.source == source)
    if category_id is not None:
        query = query.where(MerchantMapping.category_id == category_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(MerchantMapping.merchant_pattern.ilike(pattern))

    total = int((await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one())
    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            query.order_by(MerchantMapping.merchant_pattern).offset(offset).limit(page_size)
        )
    ).scalars().all()
    return PaginatedMappings(
        items=[MappingOut.model_validate(r) for r in rows],
        total=total,
    )


@router.post("", response_model=MappingOut, status_code=201)
async def create_mapping(
    body: MappingCreate,
    db: AsyncSession = Depends(db_session),
) -> MerchantMapping:
    pattern = normalize(body.merchant_pattern)
    category = await db.get(Category, body.category_id)
    if category is None:
        raise not_found("category")

    existing = await db.execute(
        select(MerchantMapping).where(MerchantMapping.merchant_pattern == pattern)
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("duplicate_pattern")

    mapping = MerchantMapping(
        merchant_pattern=pattern,
        category_id=body.category_id,
        source="manual",
        confidence=None,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return mapping


@router.patch("/{mapping_id}", response_model=MappingOut)
async def patch_mapping(
    mapping_id: int,
    body: MappingPatch,
    db: AsyncSession = Depends(db_session),
) -> MerchantMapping:
    mapping = await db.get(MerchantMapping, mapping_id)
    if mapping is None:
        raise not_found("mapping")
    if body.merchant_pattern is not None:
        mapping.merchant_pattern = normalize(body.merchant_pattern)
    if body.category_id is not None:
        category = await db.get(Category, body.category_id)
        if category is None:
            raise not_found("category")
        mapping.category_id = body.category_id
    mapping.source = "manual"
    mapping.confidence = None
    await db.commit()
    await db.refresh(mapping)
    return mapping


@router.delete("/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(db_session),
) -> None:
    mapping = await db.get(MerchantMapping, mapping_id)
    if mapping is None:
        raise not_found("mapping")
    await db.delete(mapping)
    await db.commit()
