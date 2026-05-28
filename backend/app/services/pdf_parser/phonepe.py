from __future__ import annotations

import io
import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

import pdfplumber

from .extract import logical_rows_from_pdf, raw_text_from_pdf
from .scrub import split_period_and_scrub
from .types import LogicalRow, ParsedStatement, ParsedTransaction

_DATE_RE = re.compile(
    r"^(?P<m>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(?P<d>\d{1,2}), (?P<y>\d{4})$"
)
_TIME_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<min>\d{2}) (?P<ap>AM|PM)$")

_DESC_RE = re.compile(
    r"^(?:"
    r"Paid to (?P<paid_name>.+)"
    r"|Received from (?P<recv_name>.+)"
    r"|Bill paid - (?P<bill_kind>.+)"
    r"|Paid$"
    r")$"
)

_TXNID_RE = re.compile(
    r"^Transaction ID\s*:\s*(?P<ref>\S+)"
    r"(?:\s+(?P<trailing_amount>[0-9][0-9,]*(?:\.\d{1,2})?))?\s*$"
)
_UTR_RE = re.compile(r"^UTR No\s*:\s*(?P<utr>\S+)$")
_ACCOUNT_RE = re.compile(r"^(?P<dir>Debited from|Credited to)\s+(?P<acc>.+)$")

_AMOUNT_FULL_RE = re.compile(
    r"^(?P<type>Debit|Credit) INR\s+(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)$"
)
_AMOUNT_HEAD_RE = re.compile(r"^(?P<type>Debit|Credit) INR$")
_AMOUNT_NUM_RE = re.compile(r"^(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)$")


def parse_phonepe_pdf(pdf_bytes: bytes) -> ParsedStatement:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        raw = raw_text_from_pdf(pdf)
        rows = logical_rows_from_pdf(pdf)
    period_start, period_end, lines = split_period_and_scrub(rows)
    transactions = _parse_transactions(lines)

    if period_start is None and transactions:
        period_start = min(txn.date for txn in transactions)
        period_end = max(txn.date for txn in transactions)

    return ParsedStatement(
        period_start=period_start,
        period_end=period_end,
        raw_text=raw,
        transactions=transactions,
    )


def _parse_transactions(rows: list[LogicalRow]) -> list[ParsedTransaction]:
    blocks = _group_blocks(rows)
    transactions: list[ParsedTransaction] = []
    for block in blocks:
        parsed = _parse_block(block)
        if parsed is not None:
            transactions.append(parsed)
    return transactions


def _group_blocks(rows: list[LogicalRow]) -> list[list[LogicalRow]]:
    blocks: list[list[LogicalRow]] = []
    current: list[LogicalRow] = []

    for row in rows:
        if row.date and _DATE_RE.match(row.date):
            if current:
                blocks.append(current)
            current = [row]
        elif current:
            current.append(row)

    if current:
        blocks.append(current)
    return blocks


def _parse_block(block: list[LogicalRow]) -> ParsedTransaction | None:
    txn_date: date | None = None
    txn_time: time | None = None
    description: str | None = None
    transaction_ref: str | None = None
    utr_no: str | None = None
    account_last4: str | None = None
    amount_type: str | None = None
    amount_value: Decimal | None = None

    for row in block:
        if row.date:
            if match := _DATE_RE.match(row.date):
                txn_date = datetime.strptime(
                    f"{match.group('m')} {match.group('d')}, {match.group('y')}",
                    "%b %d, %Y",
                ).date()
            elif match := _TIME_RE.match(row.date):
                txn_time = datetime.strptime(
                    f"{match.group('h')}:{match.group('min')} {match.group('ap')}",
                    "%I:%M %p",
                ).time()

        if row.detail:
            if _DESC_RE.match(row.detail):
                description = row.detail
            elif txn_match := _TXNID_RE.match(row.detail):
                transaction_ref = txn_match.group("ref")
                if txn_match.group("trailing_amount") and amount_value is None:
                    amount_value = _parse_amount(txn_match.group("trailing_amount"))
            elif utr_match := _UTR_RE.match(row.detail):
                utr_no = utr_match.group("utr")
            elif acct_match := _ACCOUNT_RE.match(row.detail):
                account_last4 = _account_last4(acct_match.group("acc"))

        if row.amount:
            if full := _AMOUNT_FULL_RE.match(row.amount):
                amount_type = full.group("type")
                amount_value = _parse_amount(full.group("amount"))
            elif head := _AMOUNT_HEAD_RE.match(row.amount):
                amount_type = head.group("type")
            elif num := _AMOUNT_NUM_RE.match(row.amount):
                amount_value = _parse_amount(num.group("amount"))

    if txn_date is None or description is None or transaction_ref is None:
        return None
    if amount_type not in ("Debit", "Credit") or amount_value is None:
        return None

    return ParsedTransaction(
        date=txn_date,
        time=txn_time,
        description=description,
        merchant_raw=_merchant_raw(description),
        amount=amount_value,
        type=amount_type.lower(),
        transaction_ref=transaction_ref,
        utr_no=utr_no,
        account_last4=account_last4,
    )


def _merchant_raw(description: str) -> str | None:
    match = _DESC_RE.match(description)
    if not match:
        return None
    if match.group("paid_name"):
        return match.group("paid_name")
    if match.group("recv_name"):
        return match.group("recv_name")
    if match.group("bill_kind"):
        return match.group("bill_kind")
    return None


def _account_last4(account: str) -> str | None:
    digits = re.sub(r"\D", "", account)
    return digits[-4:] if len(digits) >= 4 else None


def _parse_amount(raw: str) -> Decimal:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {raw!r}") from exc
