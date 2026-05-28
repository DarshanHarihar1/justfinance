# Phase 3 — PDF Parser (PhonePe, Deterministic)

> Goal: a pure-Python function that takes a PhonePe statement PDF and returns a
> `list[ParsedTransaction]` with zero LLM calls. Robust against the edge cases
> observed in the sample fixture. Fully unit-tested.

## Prerequisites

- Phase 1 complete (pdfplumber installed, fixture PDF committed).
- Phase 2 complete (the parsed shape maps to the `transactions` table cleanly).

## 3.1 PhonePe statement format — observed

After running `pdfplumber.extract_text()` on the sample PDF, every page has this shape:

```
Transaction Statement for +919900475117          ← page 1 only, header
Apr 28, 2026 - May 28, 2026                       ← page 1 only, period
Date Transaction Details Type Amount             ← repeats on every page
<TRANSACTION BLOCK 1>
<TRANSACTION BLOCK 2>
...
Page N of M                                       ← repeats on every page
This is a system generated statement. ...         ← repeats on every page
```

Each **transaction block** is one of these layouts:

### Layout A — standard paid/received

```
Apr 28, 2026
07:30 PM
Paid to S C Naregal
Transaction ID : T2604281930148688800258
UTR No : 376914838281
Debited from XX4200
Debit INR 1000.00
```

7 logical lines:

1. `<Mon DD, YYYY>`
2. `<HH:MM AM|PM>`
3. `Paid to <recipient>` | `Received from <sender>` | `Paid` (anonymous) | `Bill paid - <kind>`
4. `Transaction ID : <ref>`
5. `UTR No : <utr>`
6. `Debited from XX<last4>` | `Credited to XX<last4>` | `Credited to Account`
7. `Debit INR <amount>` | `Credit INR <amount>`

### Layout B — wrapped amount

When the amount has 5+ digits, pdfplumber sometimes breaks line 7 across two lines:

```
Debit INR
70000.00
```

This is treated as one logical "amount" line. The parser must rejoin them.

### Layout C — wrapped recipient

Long recipient strings sometimes wrap:

```
Paid to Sri Vinayaka Sugar cane Juice-Sri Vinayaka Sugar cane Juice
```

This is a single line in the source even though it's long. No special handling needed.

But this case (observed):

```
Paid to Zepto Marketplace Private Limi
```

is **truncated**, not wrapped. The normalizer (Phase 4) collapses
`ZEPTO MARKETPLACE PRIVATE LIMI` and `ZEPTO MARKETPLACE PRIVATE LIMITED` to the same key.

### Layout D — anonymous "Paid"

```
Paid
Transaction ID : OMO2605021450241863539633V
UTR No : 359002496284
Debited from XX4200
Debit INR 2260.00
```

The recipient is literally missing. The parser must accept this: `merchant_raw = None`.
Phase 4 will tag these for manual review.

### Layout E — masked recipient

```
Paid to ******1492
```

Treat the mask itself (`******1492`) as the merchant string. Per your decision (Q12), the user can label it once and the mapping sticks.

### Layout F — self-transfer

```
Paid to XXXXXX8216
```

or

```
Paid to XXXXXXXXXXX4200
```

The recipient is a masked own-account identifier (uppercase `X`s). The parser surfaces this as-is; the categorizer (Phase 4 §4.5) detects it.

### Layout G — bill paid

```
Bill paid - FASTag
Transaction ID : NX26051420183233500812831
UTR No : 999782068643
Debited from XX8216
Debit INR 1003.00
```

Treat `FASTag` as the merchant.

### Layout H — received

```
May 18, 2026
02:53 PM
Received from ANURAG KANDULNA
Transaction ID : T2605181453473438518156
UTR No : 650477259957
Credited to XX4200
Credit INR 266.00
```

`type = credit`, `merchant_raw = "ANURAG KANDULNA"`.

## 3.2 Parser strategy — state machine over normalized lines

The parser proceeds in 3 stages:

```
PDF bytes
   │  pdfplumber.extract_text() per page
   ▼
raw_text (str)                  ← saved into statements.raw_text
   │  scrub headers/footers/pagination
   ▼
clean_lines (list[str])
   │  state machine groups lines into 7-line transaction blocks
   ▼
list[ParsedTransaction]
```

### Stage 1: extract_text per page, concatenated

```python
import pdfplumber

def _extract_raw(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)
```

### Stage 2: scrub

We strip every line that matches one of the **page chrome** patterns:

```python
_NOISE_PATTERNS = [
    re.compile(r"^Transaction Statement for "),
    re.compile(r"^Date Transaction Details Type Amount\s*$"),
    re.compile(r"^Page \d+ of \d+\s*$"),
    re.compile(r"^This is a system generated statement"),
    re.compile(r"^This is an automatically generated statement"),
    re.compile(r"https?://"),
    re.compile(r"^Do not fall prey"),
    re.compile(r"^The contents of this email"),
    re.compile(r"^Visit for PhonePe"),
    re.compile(r"^for Privacy Policy"),
    re.compile(r"^received this message by mistake"),
    re.compile(r"^errors in the statement at"),
    re.compile(r"^the recipient's details are corrected"),
    re.compile(r"^emails and calls"),
    re.compile(r"^-- \d+ of \d+ --\s*$"),       # only present in upload preview, harmless
]

def _scrub(raw: str) -> list[str]:
    out = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if any(p.search(s) for p in _NOISE_PATTERNS):
            continue
        out.append(s)
    return out
```

After scrubbing, we also need to detect & extract the **period header** (only on page 1):

```python
_PERIOD_RE = re.compile(
    r"^(?P<start>[A-Z][a-z]{2} \d{1,2}, \d{4})\s*-\s*(?P<end>[A-Z][a-z]{2} \d{1,2}, \d{4})\s*$"
)
```

If a line matches `_PERIOD_RE`, extract it as the statement period and drop it from `clean_lines`.

### Stage 3: state machine

The state machine consumes lines one at a time, emitting one `ParsedTransaction`
each time it completes a block.

States:

```
INIT
  ├─ line matches DATE_RE  → DATE_SEEN
  └─ else                  → stay (skip)
DATE_SEEN
  ├─ line matches TIME_RE  → TIME_SEEN
  └─ else                  → reset to INIT (don't lose date if next line is another date; handled below)
TIME_SEEN
  ├─ line starts with "Paid to ", "Received from ", "Bill paid - ", or equals "Paid"
                            → RECIPIENT_SEEN
  └─ else                  → reset to INIT (malformed)
RECIPIENT_SEEN
  ├─ line matches TXNID_RE → TXNID_SEEN
  └─ else                  → reset to INIT
TXNID_SEEN
  ├─ line matches UTR_RE   → UTR_SEEN
  └─ else                  → reset to INIT
UTR_SEEN
  ├─ line matches ACCOUNT_RE (Debited from / Credited to)
                            → ACCOUNT_SEEN
  └─ else                  → reset to INIT
ACCOUNT_SEEN
  ├─ line matches AMOUNT_FULL_RE (e.g. "Debit INR 1000.00")
                            → emit ParsedTransaction; back to INIT
  ├─ line matches AMOUNT_HEAD_RE (e.g. "Debit INR")
                            → AMOUNT_HEAD_SEEN
  └─ else                  → reset to INIT
AMOUNT_HEAD_SEEN
  ├─ line matches AMOUNT_NUM_RE (e.g. "70000.00")
                            → emit ParsedTransaction; back to INIT
  └─ else                  → reset to INIT
```

Regexes:

```python
_DATE_RE = re.compile(
    r"^(?P<m>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(?P<d>\d{1,2}), (?P<y>\d{4})$"
)
_TIME_RE  = re.compile(r"^(?P<h>\d{1,2}):(?P<min>\d{2}) (?P<ap>AM|PM)$")

_RECIP_RE = re.compile(
    r"^(?:"
    r"(?P<paid_to>Paid to (?P<paid_name>.+))"
    r"|(?P<received>Received from (?P<recv_name>.+))"
    r"|(?P<billpaid>Bill paid - (?P<bill_kind>.+))"
    r"|(?P<paid_anon>Paid)"
    r")$"
)

_TXNID_RE   = re.compile(r"^Transaction ID\s*:\s*(?P<ref>\S+)$")
_UTR_RE     = re.compile(r"^UTR No\s*:\s*(?P<utr>\S+)$")
_ACCOUNT_RE = re.compile(
    r"^(?P<dir>Debited from|Credited to)\s+(?P<acc>.+)$"
)

# Layout A: "Debit INR 1000.00"
_AMOUNT_FULL_RE = re.compile(
    r"^(?P<type>Debit|Credit) INR\s+(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)$"
)
# Layout B head: "Debit INR" (no number)
_AMOUNT_HEAD_RE = re.compile(r"^(?P<type>Debit|Credit) INR$")
# Layout B tail: the bare number on its own line
_AMOUNT_NUM_RE  = re.compile(r"^(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)$")
```

### Output dataclass

```python
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal

@dataclass(frozen=True)
class ParsedTransaction:
    date: date
    time: time | None
    description: str          # original "Paid to ..." line for traceability
    merchant_raw: str | None  # recipient as printed; None for anonymous "Paid"
    amount: Decimal
    type: str                 # "debit" | "credit"
    transaction_ref: str
    utr_no: str | None
    account_last4: str | None # purely informational; not stored per design decision
```

### Top-level entry point

```python
from io import BytesIO
from datetime import date

@dataclass(frozen=True)
class ParsedStatement:
    period_start: date | None
    period_end: date | None
    raw_text: str
    transactions: list[ParsedTransaction]


def parse_phonepe_pdf(pdf_bytes: bytes) -> ParsedStatement:
    raw = _extract_raw(pdf_bytes)
    period_start, period_end, lines = _split_period_and_lines(raw)
    txns = _state_machine(lines)
    if period_start is None and txns:
        period_start = min(t.date for t in txns)
        period_end   = max(t.date for t in txns)
    return ParsedStatement(
        period_start=period_start,
        period_end=period_end,
        raw_text=raw,
        transactions=txns,
    )
```

## 3.3 Field extraction details

| Field | Source | Notes |
|-------|--------|-------|
| `date` | line 1 (`Apr 28, 2026`) | parsed with `datetime.strptime(..., "%b %d, %Y").date()` |
| `time` | line 2 (`07:30 PM`) | parsed with `datetime.strptime(..., "%I:%M %p").time()`; nullable in theory but always present in observed data |
| `description` | line 3 verbatim | what we store as `transactions.description` |
| `merchant_raw` | derived from line 3 |  see table below |
| `transaction_ref` | line 4 after `:` | trimmed |
| `utr_no` | line 5 after `:` | trimmed; may be missing in future formats — keep nullable |
| `account_last4` | line 6 (`Debited from XX4200` → `4200`) | for self-transfer detection only; not persisted |
| `type` | line 7 head (`Debit` or `Credit`) | lower-cased |
| `amount` | line 7 tail (or layout B's separate line) | strip commas, parse as `Decimal` |

`merchant_raw` derivation:

| Line 3                              | `merchant_raw`         | Notes |
|-------------------------------------|------------------------|-------|
| `Paid to S C Naregal`               | `S C Naregal`          | |
| `Received from ANURAG KANDULNA`     | `ANURAG KANDULNA`      | |
| `Bill paid - FASTag`                | `FASTag`               | |
| `Paid`                              | `None`                 | anonymous |
| `Paid to ******1492`                | `******1492`           | masked phone — kept as-is |
| `Paid to XXXXXX8216`                | `XXXXXX8216`           | self-transfer signal preserved; Phase 4 detects |
| `Paid to XXXXXXXXXXX4200`           | `XXXXXXXXXXX4200`      | same |

## 3.4 Edge cases — handled & tested

| Case | Handling | Test fixture |
|------|---------|--------------|
| Amount wraps across two lines | `AMOUNT_HEAD_SEEN` state stitches them | "70000.00", "30000.00", "14362.00", "29903.00" cases in sample |
| Anonymous `Paid` | `merchant_raw = None`, still extracted | `OMO2605021450241863539633V` |
| Masked phone `******1492` | kept as merchant; will be a stable signature | the ₹85 recurring pattern in sample |
| Self-transfer `XXXXXX8216` | kept as merchant; Phase 4 transforms | sample has several |
| `Credit` direction | `type = "credit"` | `R10252605202029113831893905` Amit K |
| Bill paid (FASTag) | `merchant_raw = "FASTag"` | `NX26051420183233500812831` |
| Recipient names with `-` (e.g., `Indian Oil Petrol Pump - Devaraj Enterprises`) | passes through; dash inside name is fine | sample line |
| Recipient names with `&` | passes through | `KAMAT CAFE & PASTRIES` |
| Recipient names with numbers | passes through | `7988730342ptyes`, `Zomato8759546` |
| Trailing whitespace on lines | stripped in `_scrub` | |
| Multi-page footer noise | filtered by `_NOISE_PATTERNS` | |
| Empty pages | `extract_text()` returns "" → no contribution | |
| Statement period missing (future PhonePe change) | fall back to `min/max(txn.date)` | |
| Duplicate consecutive dates (next txn same day) | state machine resets cleanly after each emit | |

## 3.5 Error handling

The parser is intentionally permissive at the boundary, strict in the middle:

- Lines that don't fit any state transition cause the state machine to **reset to `INIT`**, not raise.
- After parsing, if `len(transactions) == 0`, the upload endpoint returns `422 Unprocessable Entity` with a structured error:

  ```json
  {
    "error": "phonepe_parse_empty",
    "message": "No transactions found. Is this a PhonePe Transaction Statement PDF?"
  }
  ```

- If `len(transactions)` is small but `raw_text` is large (heuristic: `len(raw_text) > 5000 and len(transactions) < 5`), the response includes a soft warning:

  ```json
  { "warning": "phonepe_parse_low_yield", "parsed_count": 3, "raw_text_chars": 12482 }
  ```

  This is logged but not blocking.

- Currency is assumed INR. If line 7 doesn't include `INR`, the parser raises `ValueError` — caught at the router layer and surfaced as a `422`.

## 3.6 Module layout

```
backend/app/services/pdf_parser/
├── __init__.py          # public: parse_phonepe_pdf(...)
├── phonepe.py           # the regexes + state machine
├── types.py             # ParsedTransaction, ParsedStatement
└── scrub.py             # _NOISE_PATTERNS, _scrub, _split_period_and_lines
```

`__init__.py` exposes only:

```python
from .phonepe import parse_phonepe_pdf
from .types import ParsedTransaction, ParsedStatement

__all__ = ["parse_phonepe_pdf", "ParsedTransaction", "ParsedStatement"]
```

## 3.7 Tests

Located in `backend/tests/test_pdf_parser.py`. Uses the committed fixture
`backend/tests/fixtures/phonepe_sample.pdf` (the real sample uploaded by the user).

Required test cases:

```python
def test_parses_known_count():
    # Expected count from the sample fixture, hand-counted from the PDF: 116
    result = parse_phonepe_pdf(_load_fixture())
    assert len(result.transactions) == 116

def test_period_extracted():
    result = parse_phonepe_pdf(_load_fixture())
    assert result.period_start == date(2026, 4, 28)
    assert result.period_end   == date(2026, 5, 28)

def test_wrapped_amount():
    # 70000.00 paid on Apr 30 to XXXXXX8216 must be present at exactly that value
    result = parse_phonepe_pdf(_load_fixture())
    big = [t for t in result.transactions if t.amount == Decimal("70000.00")]
    assert len(big) == 1
    assert big[0].date == date(2026, 4, 30)

def test_anonymous_paid_extracted():
    result = parse_phonepe_pdf(_load_fixture())
    omo = [t for t in result.transactions if t.transaction_ref.startswith("OMO")]
    assert len(omo) >= 2
    assert all(t.merchant_raw is None for t in omo)

def test_credit_direction():
    result = parse_phonepe_pdf(_load_fixture())
    credits = [t for t in result.transactions if t.type == "credit"]
    assert len(credits) >= 3
    assert all(t.amount > 0 for t in credits)

def test_masked_merchant_preserved():
    result = parse_phonepe_pdf(_load_fixture())
    masked = [t for t in result.transactions if t.merchant_raw and t.merchant_raw.startswith("******1492")]
    assert len(masked) >= 5      # appears many times in sample
    assert all(t.amount == Decimal("85.00") for t in masked)

def test_self_transfer_preserved():
    result = parse_phonepe_pdf(_load_fixture())
    selves = [t for t in result.transactions if t.merchant_raw and t.merchant_raw.startswith("XXXXXX")]
    assert len(selves) >= 2

def test_fastag_extracted():
    result = parse_phonepe_pdf(_load_fixture())
    fastags = [t for t in result.transactions if t.merchant_raw == "FASTag"]
    assert len(fastags) == 1
    assert fastags[0].amount == Decimal("1003.00")

def test_transaction_refs_unique():
    result = parse_phonepe_pdf(_load_fixture())
    refs = [t.transaction_ref for t in result.transactions]
    assert len(refs) == len(set(refs))

def test_idempotent_on_reparse():
    # Same bytes → same result
    a = parse_phonepe_pdf(_load_fixture())
    b = parse_phonepe_pdf(_load_fixture())
    assert [astuple(t) for t in a.transactions] == [astuple(t) for t in b.transactions]
```

The exact expected count (116) must be verified once on the real PDF before this test is finalized.

## 3.8 Definition of done

- [ ] `parse_phonepe_pdf(bytes) → ParsedStatement` exists and is exported.
- [ ] Page-chrome scrubbing strips all observed noise patterns.
- [ ] Statement period is extracted from the header; falls back to min/max txn date.
- [ ] All 10 test cases in §3.7 pass against the committed fixture.
- [ ] `pytest -q` runs in < 3 seconds.
- [ ] Manual inspection of the parsed output for the sample PDF reveals no obviously-misparsed merchants.
- [ ] No LLM call is made in this path — verified by network-mock test that fails on any outbound HTTP.

## 3.9 Risks / open questions

- **Format drift.** If PhonePe changes the statement layout (e.g., adds a new line per block, removes UTR No, restyles dates), every test breaks loudly. That's the correct failure mode — the parser is intentionally rigid because deterministic > probabilistic for this use case.
- **Multi-currency.** Hard-codes INR. If a future statement uses USD, we throw. Acceptable.
- **`pdfplumber.extract_text()` ordering.** Some PDFs interleave columns; PhonePe doesn't. If it ever does, switch to `extract_text_lines()` and sort by `(top, x0)` before joining.
- **Future second source.** The `statements.source` enum allows widening to e.g. `'gpay'`, `'paytm'`. Each new source becomes its own parser module under `app/services/pdf_parser/`; the public `parse_statement(source, bytes)` dispatcher is added then. Out of scope now.
