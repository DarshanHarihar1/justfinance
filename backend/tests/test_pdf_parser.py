"""Tests for the PhonePe deterministic PDF parser (design/03-pdf-parser.md)."""
from __future__ import annotations

import socket
from dataclasses import astuple
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.pdf_parser import parse_phonepe_pdf

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "phonepe_sample.pdf"


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return FIXTURE.read_bytes()


@pytest.fixture(scope="module")
def parsed(fixture_bytes: bytes):
    return parse_phonepe_pdf(fixture_bytes)


def _load_fixture() -> bytes:
    return FIXTURE.read_bytes()


def test_parses_known_count(parsed) -> None:
    assert len(parsed.transactions) == 139


def test_period_extracted(parsed) -> None:
    assert parsed.period_start == date(2026, 4, 28)
    assert parsed.period_end == date(2026, 5, 28)


def test_wrapped_amount(parsed) -> None:
    result = parsed
    big = [t for t in result.transactions if t.amount == Decimal("70000.00")]
    assert len(big) == 1
    assert big[0].date == date(2026, 4, 30)
    assert big[0].merchant_raw == "XXXXXX8216"


def test_wrapped_amount_on_txn_id_line(parsed) -> None:
    for amount in (Decimal("30000.00"), Decimal("14362.00"), Decimal("29903.00")):
        matches = [t for t in parsed.transactions if t.amount == amount]
        assert len(matches) == 1, f"expected one txn at {amount}"


def test_anonymous_paid_extracted(parsed) -> None:
    omo = [t for t in parsed.transactions if t.transaction_ref.startswith("OMO")]
    assert len(omo) >= 2
    assert all(t.merchant_raw is None for t in omo)


def test_credit_direction(parsed) -> None:
    credits = [t for t in parsed.transactions if t.type == "credit"]
    assert len(credits) >= 3
    assert all(t.amount > 0 for t in credits)


def test_masked_merchant_preserved(parsed) -> None:
    masked = [
        t
        for t in parsed.transactions
        if t.merchant_raw and t.merchant_raw.startswith("******1492")
    ]
    assert len(masked) >= 5
    assert all(t.amount == Decimal("85.00") for t in masked)


def test_self_transfer_preserved(parsed) -> None:
    selves = [
        t for t in parsed.transactions if t.merchant_raw and t.merchant_raw.startswith("XXXXXX")
    ]
    assert len(selves) >= 2


def test_fastag_extracted(parsed) -> None:
    fastags = [t for t in parsed.transactions if t.merchant_raw == "FASTag"]
    assert len(fastags) == 1
    assert fastags[0].amount == Decimal("1003.00")


def test_transaction_refs_unique(parsed) -> None:
    refs = [t.transaction_ref for t in parsed.transactions]
    assert len(refs) == len(set(refs))


def test_idempotent_on_reparse() -> None:
    a = parse_phonepe_pdf(_load_fixture())
    b = parse_phonepe_pdf(_load_fixture())
    assert [astuple(t) for t in a.transactions] == [astuple(t) for t in b.transactions]


def test_truncated_merchant(parsed) -> None:
    limi = [t for t in parsed.transactions if t.merchant_raw == "Zepto Marketplace Private Limi"]
    assert len(limi) == 1


def test_no_outbound_http() -> None:
    """Parser must not call the network (design §3.8)."""
    real_socket = socket.socket

    def guarded(*args: object, **kwargs: object) -> socket.socket:
        raise AssertionError("pdf parser must not open network sockets")

    with patch("socket.socket", side_effect=guarded):
        result = parse_phonepe_pdf(_load_fixture())
    assert len(result.transactions) == 139
