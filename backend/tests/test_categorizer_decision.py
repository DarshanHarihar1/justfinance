"""Unit tests for categorizer decision steps 1–5 (no DB, no LLM)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.categorizer.catalog import CategoryCatalog
from app.services.categorizer.decision import is_self_transfer, resolve_without_llm
from app.services.pdf_parser.types import ParsedTransaction


def _catalog() -> CategoryCatalog:
    return CategoryCatalog(
        names=("Food & Dining", "Others", "Transfers"),
        name_to_id={"Food & Dining": 2, "Others": 99, "Transfers": 100},
        transfers_id=100,
        others_id=99,
    )


def _txn(**overrides: object) -> ParsedTransaction:
    base = {
        "date": date(2026, 5, 1),
        "time": None,
        "description": "Paid to Swiggy Ltd",
        "merchant_raw": "Swiggy Ltd",
        "amount": Decimal("100.00"),
        "type": "debit",
        "transaction_ref": "T123",
        "utr_no": None,
        "account_last4": "4200",
    }
    base.update(overrides)
    return ParsedTransaction(**base)  # type: ignore[arg-type]


def test_self_transfer_detection() -> None:
    assert is_self_transfer("XXXXXX8216", {"8216", "4200"})
    assert not is_self_transfer("XXXXXX8216", {"4200"})
    assert not is_self_transfer("Swiggy Ltd", {"8216"})


def test_self_transfer_before_credit() -> None:
    txn = _txn(merchant_raw="XXXXXX8216", type="credit", description="Received from X")
    result = resolve_without_llm(
        txn,
        own_account_last4s={"8216"},
        catalog=_catalog(),
        mapping_index={},
    )
    assert result is not None
    assert result.source == "transfer"
    assert result.category_id == 100
    assert result.needs_review is False


def test_credit_goes_to_others_with_review() -> None:
    txn = _txn(type="credit", description="Received from ANURAG", merchant_raw="ANURAG KANDULNA")
    result = resolve_without_llm(
        txn,
        own_account_last4s=set(),
        catalog=_catalog(),
        mapping_index={},
    )
    assert result is not None
    assert result.source == "credit"
    assert result.category_id == 99
    assert result.needs_review is True
    assert result.merchant_normalized == "ANURAG KANDULNA"


def test_anonymous_paid_fallback() -> None:
    txn = _txn(merchant_raw=None, description="Paid")
    result = resolve_without_llm(
        txn,
        own_account_last4s=set(),
        catalog=_catalog(),
        mapping_index={},
    )
    assert result is not None
    assert result.source == "fallback"
    assert result.merchant_normalized is None


def test_mapping_hit_primary() -> None:
    txn = _txn(merchant_raw="Swiggy Ltd")
    result = resolve_without_llm(
        txn,
        own_account_last4s=set(),
        catalog=_catalog(),
        mapping_index={"SWIGGY": 2},
    )
    assert result is not None
    assert result.source == "mapping"
    assert result.category_id == 2
    assert result.merchant_normalized == "SWIGGY"


def test_mapping_hit_collapsed() -> None:
    txn = _txn(merchant_raw="Zomato8759546", description="Paid to Zomato8759546")
    result = resolve_without_llm(
        txn,
        own_account_last4s=set(),
        catalog=_catalog(),
        mapping_index={"ZOMATO": 2},
    )
    assert result is not None
    assert result.source == "mapping"
    assert result.category_id == 2


def test_mapping_miss_returns_none_for_llm() -> None:
    txn = _txn(merchant_raw="Mystery Mart")
    result = resolve_without_llm(
        txn,
        own_account_last4s=set(),
        catalog=_catalog(),
        mapping_index={"SWIGGY": 2},
    )
    assert result is None
