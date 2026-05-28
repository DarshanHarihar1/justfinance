from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import Category, MerchantMapping


@pytest.mark.usefixtures("requires_postgres")
def test_cannot_delete_system_category(auth_client: TestClient) -> None:
    categories = auth_client.get("/api/categories")
    transfers = next(c for c in categories.json() if c["name"] == "Transfers")
    response = auth_client.delete(f"/api/categories/{transfers['id']}")
    assert response.status_code == 409
    assert response.json()["error"] == "system_category"


@pytest.mark.asyncio
@pytest.mark.usefixtures("requires_postgres")
async def test_delete_category_with_move_to(
    auth_client: TestClient,
    db_engine: AsyncEngine,
) -> None:
    created = auth_client.post(
        "/api/categories",
        json={"name": "Temp Category", "color": "#000000", "icon": "🧪"},
    )
    assert created.status_code == 201
    temp_id = created.json()["id"]

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        others = (
            await session.execute(select(Category).where(Category.name == "Others"))
        ).scalar_one()
        session.add(
            MerchantMapping(
                merchant_pattern="TEMP TEST PATTERN",
                category_id=temp_id,
                source="manual",
            )
        )
        await session.commit()

    response = auth_client.delete(f"/api/categories/{temp_id}?move_to={others.id}")
    assert response.status_code == 204

    async with session_factory() as session:
        mapping = (
            await session.execute(
                select(MerchantMapping).where(
                    MerchantMapping.merchant_pattern == "TEMP TEST PATTERN"
                )
            )
        ).scalar_one()
        assert mapping.category_id == others.id
