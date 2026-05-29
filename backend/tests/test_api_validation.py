"""API validation tests that do not require Postgres."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_rejects_invalid_month(auth_client: TestClient) -> None:
    response = auth_client.get("/api/analytics/dashboard/13/2025")
    assert response.status_code == 422


def test_transactions_reject_partial_month_filter(auth_client: TestClient) -> None:
    response = auth_client.get("/api/transactions", params={"month": 5})
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_month_filter"
