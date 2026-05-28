from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category


@dataclass(frozen=True)
class CategoryCatalog:
    names: tuple[str, ...]
    name_to_id: dict[str, int]
    transfers_id: int
    others_id: int

    def id_for(self, name: str) -> int | None:
        return self.name_to_id.get(name)


async def load_category_catalog(db: AsyncSession) -> CategoryCatalog:
    rows = (await db.execute(select(Category.id, Category.name).order_by(Category.name))).all()
    name_to_id = {name: category_id for category_id, name in rows}
    if "Transfers" not in name_to_id or "Others" not in name_to_id:
        raise RuntimeError("categories table is missing required system rows Transfers/Others")
    return CategoryCatalog(
        names=tuple(sorted(name_to_id)),
        name_to_id=name_to_id,
        transfers_id=name_to_id["Transfers"],
        others_id=name_to_id["Others"],
    )
