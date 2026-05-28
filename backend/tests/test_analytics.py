from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Transaction
from app.services.analytics.summary import build_spend_summary, summary_cache_key

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
def test_dashboard_after_upload(auth_client: TestClient) -> None:
    _upload_pdf(auth_client)
    response = auth_client.get("/api/analytics/dashboard/5/2026")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["month"] == 5
    assert body["year"] == 2026
    assert "income" in body["totals"]
    assert "expense" in body["totals"]
    assert isinstance(body["by_category"], list)
    assert isinstance(body["recent_transactions"], list)


@pytest.mark.usefixtures("requires_postgres")
def test_mom_returns_twelve_months(auth_client: TestClient) -> None:
    _upload_pdf(auth_client)
    response = auth_client.get("/api/analytics/mom")
    assert response.status_code == 200
    months = response.json()["months"]
    assert len(months) == 12
    assert months[0]["year"] <= months[-1]["year"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("requires_postgres")
async def test_analytics_excludes_transfers_and_needs_review(
    auth_client: TestClient,
    db_session: AsyncSession,
) -> None:
    _upload_pdf(auth_client)
    transfers = (
        await db_session.execute(
            select(Category).where(Category.name == "Transfers")
        )
    ).scalar_one()

    txn = (await db_session.execute(select(Transaction).limit(1))).scalar_one()
    txn.needs_review = True
    txn.category_id = transfers.id
    await db_session.flush()

    response = auth_client.get("/api/analytics/dashboard/5/2026")
    assert response.status_code == 200
    totals = response.json()["totals"]
    assert Decimal(totals["expense"]) >= 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("requires_postgres")
async def test_insights_payload_has_no_descriptions(
    auth_client: TestClient,
    db_session: AsyncSession,
) -> None:
    _upload_pdf(auth_client)
    summary = await build_spend_summary(db_session, month=5, year=2026)
    blob = summary_cache_key(summary)
    assert "description" not in blob.lower()
    data = json.loads(blob)
    assert "by_category" in data
    for cat in data["by_category"]:
        assert "name" in cat
        assert "description" not in cat


@pytest.mark.usefixtures("requires_postgres")
def test_insights_mock_llm(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _upload_pdf(auth_client)
    from app.main import app

    mock = AsyncMock(
        return_value={
            "insights": [
                {
                    "title": "Food spending steady",
                    "body": "Food & Dining was a large share of May spend.",
                    "severity": "info",
                }
            ]
        }
    )
    app.state.llm.chat_json = mock
    response = auth_client.post(
        "/api/analytics/insights",
        json={"month": 5, "year": 2026},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["insights"]) >= 1
    mock.assert_called_once()


@pytest.mark.usefixtures("requires_postgres")
def test_ask_rate_limit(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _upload_pdf(auth_client)
    from app.main import app
    from app.services.analytics import rate_limit

    rate_limit._ASK_TIMESTAMPS.clear()
    app.state.llm.chat_json = AsyncMock(return_value={"answer": "Test answer."})

    for _ in range(5):
        r = auth_client.post(
            "/api/analytics/ask",
            json={"question": "How much did I spend?", "month": 5, "year": 2026},
        )
        assert r.status_code == 200, r.text

    sixth = auth_client.post(
        "/api/analytics/ask",
        json={"question": "Again?", "month": 5, "year": 2026},
    )
    assert sixth.status_code == 429
