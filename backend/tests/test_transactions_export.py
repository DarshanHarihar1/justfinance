from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "phonepe_sample.pdf"


def _upload_pdf(client: TestClient) -> None:
    with FIXTURE.open("rb") as handle:
        response = client.post(
            "/api/statements/upload",
            files={"file": ("phonepe_sample.pdf", handle, "application/pdf")},
        )
    assert response.status_code == 200, response.text


@pytest.mark.usefixtures("requires_postgres")
def test_export_csv_all_rows(auth_client: TestClient) -> None:
    _upload_pdf(auth_client)
    response = auth_client.get("/api/transactions/export.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "")

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 139
    assert reader.fieldnames
    assert "description" in reader.fieldnames
    assert "category" in reader.fieldnames


@pytest.mark.usefixtures("requires_postgres")
def test_export_csv_date_filter(auth_client: TestClient) -> None:
    _upload_pdf(auth_client)
    response = auth_client.get(
        "/api/transactions/export.csv",
        params={"from": "2099-01-01", "to": "2099-12-31"},
    )
    assert response.status_code == 200
    reader = csv.DictReader(io.StringIO(response.text))
    assert len(list(reader)) == 0
