from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import Transaction

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "phonepe_sample.pdf"


def _upload_pdf(client: TestClient) -> dict:
    with FIXTURE.open("rb") as handle:
        response = client.post(
            "/api/statements/upload",
            files={"file": ("phonepe_sample.pdf", handle, "application/pdf")},
        )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.usefixtures("requires_postgres")
def test_upload_statement_parses_fixture(auth_client: TestClient) -> None:
    body = _upload_pdf(auth_client)
    assert body["parsed_count"] == 139
    assert body["new_count"] == 139
    assert body["needs_review_count"] >= 0


@pytest.mark.usefixtures("requires_postgres")
def test_reupload_same_pdf_is_idempotent(auth_client: TestClient) -> None:
    _upload_pdf(auth_client)
    second = _upload_pdf(auth_client)
    assert second["parsed_count"] == 139
    assert second["new_count"] == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("requires_postgres")
async def test_dedup_is_global_by_transaction_ref(
    auth_client: TestClient,
    db_engine: AsyncEngine,
) -> None:
    _upload_pdf(auth_client)
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        total = (await session.execute(select(func.count(Transaction.id)))).scalar_one()
        refs = (
            await session.execute(
                select(func.count(func.distinct(Transaction.transaction_ref)))
            )
        ).scalar_one()
    assert total == 139
    assert refs == 139
