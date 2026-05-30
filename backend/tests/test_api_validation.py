"""API validation tests that do not require Postgres."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_dashboard_rejects_invalid_month(auth_client: TestClient) -> None:
    response = auth_client.get("/api/analytics/dashboard/13/2025")
    assert response.status_code == 422


def test_transactions_reject_partial_month_filter(auth_client: TestClient) -> None:
    response = auth_client.get("/api/transactions", params={"month": 5})
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_month_filter"


def test_export_rejects_invalid_date(auth_client: TestClient) -> None:
    response = auth_client.get(
        "/api/transactions/export.csv",
        params={"from": "not-a-date"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_date"


@pytest.mark.usefixtures("requires_postgres")
def test_trends_reject_invalid_month_range(auth_client: TestClient) -> None:
    categories = auth_client.get("/api/categories")
    assert categories.status_code == 200
    cat_id = categories.json()[0]["id"]
    response = auth_client.get(
        f"/api/analytics/trends/{cat_id}",
        params={"from": "bad", "to": "2025-06"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_date_range"
