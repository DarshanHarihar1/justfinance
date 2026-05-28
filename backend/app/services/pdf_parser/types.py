from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal


@dataclass(frozen=True)
class LogicalRow:
    """One visual row from the PhonePe statement table (three columns)."""

    date: str
    detail: str
    amount: str


@dataclass(frozen=True)
class ParsedTransaction:
    date: date
    time: time | None
    description: str
    merchant_raw: str | None
    amount: Decimal
    type: str  # "debit" | "credit"
    transaction_ref: str
    utr_no: str | None
    account_last4: str | None


@dataclass(frozen=True)
class ParsedStatement:
    period_start: date | None
    period_end: date | None
    raw_text: str
    transactions: list[ParsedTransaction]
