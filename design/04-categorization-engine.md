# Phase 4 — Categorization Engine

> Goal: a service that takes a `ParsedTransaction` and returns a `(category_id, needs_review)`
> decision, using (in order): self-transfer detection, credit handling, merchant
> normalization, merchant_mappings lookup, and an OpenRouter LLM fallback. Persists
> learned mappings so the same merchant is never asked about twice.

## Prerequisites

- Phases 1–3 complete.
- OpenRouter API key set in env.

## 4.1 Public contract

```python
# backend/app/services/categorizer/__init__.py

@dataclass(frozen=True)
class CategorizationResult:
    category_id: int
    merchant_normalized: str | None
    is_manually_categorized: bool      # always False here; manual flips it in the review router
    needs_review: bool
    source: str                         # 'transfer' | 'credit' | 'mapping' | 'llm' | 'fallback'

async def categorize(
    txn: ParsedTransaction,
    *,
    own_account_last4s: set[str],
    db: AsyncSession,
    llm: OpenRouterClient,
) -> CategorizationResult: ...

async def categorize_batch(
    txns: list[ParsedTransaction],
    *,
    own_account_last4s: set[str],
    db: AsyncSession,
    llm: OpenRouterClient,
) -> list[CategorizationResult]: ...
```

`categorize_batch` is the production entry point. It batches all unknown merchants into
**one** LLM call per batch of up to 10 merchants, dramatically reducing rate-limit risk.

## 4.2 Decision flow (the order matters)

```
ParsedTransaction
       │
       ▼
1. Is it a self-transfer?
   merchant_raw matches ^X{4,}\d{4}$ AND last4 ∈ own_account_last4s
       │ yes →  Transfers, needs_review=FALSE, source='transfer'    ──► done
       │ no
       ▼
2. Is it a credit?
   txn.type == 'credit'
       │ yes →  Others,    needs_review=TRUE,  source='credit'      ──► done
       │ no
       ▼
3. Is merchant_raw None? (anonymous "Paid")
       │ yes →  Others,    needs_review=TRUE,  source='fallback'    ──► done
       │ no
       ▼
4. Normalize merchant_raw → merchant_normalized
       │
       ▼
5. Lookup merchant_mappings by merchant_pattern = merchant_normalized
       │ HIT →  mapped category, needs_review=FALSE, source='mapping'
       │       (increment times_used, update last_used_at)
       │       ──► done
       │ MISS
       ▼
6. Queue for LLM batch.
   After the batch returns:
     confidence >= 0.85 →  mapped category, save merchant_mappings(source='llm'),
                            needs_review=FALSE, source='llm'
     confidence <  0.85 →  Others, needs_review=TRUE, source='llm'
                            (NO mapping persisted — manual confirmation will create it)
```

Notes on the rules:

- Step 1 must run **before** the credit check. A "received from XXXXXX8216" line is technically a credit but it's still a transfer.
- Step 2 explicitly avoids LLM for credits. P2P receives are noisy and the LLM would
  often confidently mislabel them as `Income`. We keep them safe with `Others + needs_review`.
- In step 6, we **do not save** a mapping for low-confidence LLM results. The mapping is
  written only when the user manually confirms it on the Review page (Phase 5).
- The credit branch (step 2) does store the normalized merchant for the txn (so the user
  can later confirm "Anurag Kandulna → Reimbursements" and have it learned), but no
  mapping row is created until the user does so.

### `own_account_last4s`

A small set, derived from the parsed statement at upload time:

```python
own_account_last4s = {
    a.split("XX")[-1] for a in account_strings_in_statement
    if a.startswith("XX") and a[2:].isdigit()
}
```

In practice, every `Debited from XX4200` line in the statement contributes its last-4 to
the set. The user's own accounts are exactly the set of accounts they pay *from*. Any
"Paid to" recipient whose masked last-4 is in this set is therefore a self-transfer.

## 4.3 Merchant normalization

Single function, single source of truth. Used both during seed match and during runtime.

```python
# backend/app/services/categorizer/normalize.py

import re

# Order of operations matters.
def normalize(merchant_raw: str) -> str:
    s = merchant_raw

    # Strip Transaction IDs of the form #ABC123
    s = re.sub(r"#\S+", "", s)

    # Strip UPI handles like @icici, @ybl
    s = re.sub(r"@\w+", "", s)

    # Strip embedded dates dd-mm-yyyy / dd/mm/yy
    s = re.sub(r"\d{2}[-/]\d{2}[-/]\d{2,4}", "", s)

    # Strip explicit "Txn-XXXX" suffixes
    s = re.sub(r"\bTXN[-_]\S+", "", s, flags=re.IGNORECASE)

    # Strip common company suffixes  (longest first)
    company_suffixes = [
        "PRIVATE LIMITED",
        "PVT LTD",
        "PVT. LTD.",
        "PVT. LTD",
        "LIMITED",
        "PRIVATE LIMI",       # observed truncation in PhonePe sample
        "LTD",
        "LLP",
        "INC",
        "CORP",
        "CORPORATION",
        "COMPANY",
        "CO",
    ]
    UP = s.upper()
    for suf in company_suffixes:
        if UP.endswith(" " + suf):
            UP = UP[: -(len(suf) + 1)]
        elif UP == suf:
            UP = ""

    # Strip trailing branch/location qualifiers after " - "
    # "Indian Oil Petrol Pump - Devaraj Enterprises" → "INDIAN OIL PETROL PUMP"
    # "Meghana Foods Sarjapura"                       → "MEGHANA FOODS SARJAPURA"
    #   (we don't strip suffixes that aren't separated by " - ")
    UP = UP.split(" - ", 1)[0]

    # Collapse repeated whitespace, trim, drop trailing punctuation
    UP = re.sub(r"[^\w \-\*\.\&]", "", UP)
    UP = re.sub(r"\s+", " ", UP).strip(" .-&")

    return UP
```

**Round-trip property:** every seeded `merchant_pattern` must satisfy
`normalize(pattern) == pattern`. A test in Phase 2 enforces this.

### Examples (verified against the sample fixture)

| `merchant_raw` | `normalize(...)` |
|---|---|
| `Swiggy Ltd` | `SWIGGY` |
| `SWIGGY` | `SWIGGY` |
| `Swiggy Ltd` | `SWIGGY` |
| `SWIGGY INSTAMART PRIVATE LIMITED` | `SWIGGY INSTAMART` |
| `Zepto Marketplace Private Limited` | `ZEPTO MARKETPLACE` |
| `Zepto Marketplace Private Limi` (truncated) | `ZEPTO MARKETPLACE` |
| `ZEPTO MARKETPLACE PRIVATE LIMITED` | `ZEPTO MARKETPLACE` |
| `ZEPTONOW` | `ZEPTONOW` |
| `KAMAT CAFE & PASTRIES` | `KAMAT CAFE & PASTRIES` |
| `Zomato8759546` | `ZOMATO8759546` *(see below)* |
| `Indian Oil Petrol Pump - Devaraj Enterprises` | `INDIAN OIL PETROL PUMP` |
| `BMTC BUS KA57F3003` | `BMTC BUS KA57F3003` *(see below)* |
| `******1492` | `******1492` |
| `XXXXXX8216` | `XXXXXX8216` *(handled before normalize via step 1)* |

#### Trailing-digit collapse problem

`Zomato8759546`, `BMTC BUS KA57F3003`, `7988730342ptyes` all carry an embedded code that
makes each occurrence a fresh "unknown merchant" unless we strip the code.

To handle this, after the basic normalization above we apply a **second pass** when the
result contains a long digit run:

```python
_TRAILING_CODE_RE = re.compile(r"\s*\b[A-Z0-9]*\d{4,}\b\s*$")

def collapse_trailing_code(normalized: str) -> str:
    return _TRAILING_CODE_RE.sub("", normalized).strip()
```

So:

| Input | After collapse |
|---|---|
| `ZOMATO8759546` | `ZOMATO` |
| `BMTC BUS KA57F3003` | `BMTC BUS` |
| `BMTC BUS KA41D2675` | `BMTC BUS` |
| `7988730342PTYES` | *(stays as-is — the digits aren't trailing)* |

But: we don't want this to collapse `***1492` since the `*` prefix isn't `\b`. Verified safe.

The collapse is applied **after** trying a direct lookup. So both lookups happen:

```python
def normalize_for_lookup(s: str) -> tuple[str, str]:
    primary = normalize(s)
    collapsed = collapse_trailing_code(primary)
    return primary, collapsed
```

The categorizer tries `primary` first, then `collapsed`. The seeded patterns are written
in their *collapsed* form (`ZOMATO`, `BMTC BUS`) so the rule-pack catches both layouts.

## 4.4 OpenRouter client

```python
# backend/app/services/llm/openrouter.py

import httpx
from typing import Any

class OpenRouterClient:
    def __init__(self, *, api_key: str, base_url: str, model: str,
                 app_name: str, app_url: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": app_url,    # OpenRouter convention
                "X-Title": app_name,
            },
        )
        self._model = model

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        resp = await self._client.post(
            "/chat/completions",
            json={
                "model": model or self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "provider": {"require_parameters": True},
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "result", "strict": True, "schema": schema},
                },
                "temperature": 0,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
```

Retry policy:

- HTTP 429 (rate limited): exponential backoff at 4s, 8s, 16s, up to 3 retries. If still failing, the affected merchants fall to `Others + needs_review` and the batch endpoint includes a `warning: "llm_rate_limited"` field.
- HTTP 5xx: 2 retries with 2s, 4s backoff.
- Network errors: same as 5xx.
- Any other failure: log + treat as "no answer" for the affected merchants.

## 4.5 LLM batch prompt

We send up to 10 unknown merchants per call to amortize the 50/day quota.

```python
SYSTEM = (
  "You are a personal-finance transaction categorizer for an Indian user. "
  "You receive a list of merchant names extracted from UPI bank statements. "
  "For each merchant, return the single best-fit category from this fixed list:\n"
  f"{', '.join(ALL_CATEGORY_NAMES)}.\n"
  "Use 'Others' if you are unsure. Use 'Transfers' only for inter-account transfers "
  "(never just because a name looks like a person). Be concise. Return JSON only."
)

USER_TEMPLATE = """\
Categorize the following merchants. Return a JSON object with one entry per merchant
in the same order. Each entry must have:
- "merchant": the merchant string as given,
- "category": one of the allowed categories,
- "confidence": float between 0 and 1.

Merchants:
{merchant_list}
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["results"],
    "properties": {
        "results": {
            "type": "array",
            "minItems": 1,
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["merchant", "category", "confidence"],
                "properties": {
                    "merchant":   {"type": "string"},
                    "category":   {"type": "string", "enum": ALL_CATEGORY_NAMES},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}
```

After the call returns:

- For each result, sanity-check `result["merchant"]` matches the input (model-misalignment guard). If not, drop it and fall to `Others + needs_review`.
- Apply the 0.85 confidence threshold.
- For high-confidence results: `INSERT INTO merchant_mappings (..., source='llm', confidence=X) ON CONFLICT (merchant_pattern) DO NOTHING`.

  The `ON CONFLICT DO NOTHING` guard ensures we never overwrite a seeded or user-set mapping with an LLM verdict.

## 4.6 Persistence rules

| Action | DB write |
|--------|----------|
| Step 5 HIT (mapping match) | `UPDATE merchant_mappings SET times_used = times_used + 1, last_used_at = NOW() WHERE merchant_pattern = $1` |
| Step 6 high-conf LLM | `INSERT ... ON CONFLICT (merchant_pattern) DO NOTHING` with `source='llm'`, `confidence=X` |
| Step 6 low-conf LLM | no mapping write; `needs_review = TRUE` |
| User confirms via Review page (Phase 5) | upsert with `source='manual'`, `confidence=NULL`, `times_used = 1` |
| User edits a mapping in Settings (Phase 8) | update `category_id`, set `source='manual'` |

## 4.7 Module layout

```
backend/app/services/
├── categorizer/
│   ├── __init__.py            # categorize, categorize_batch
│   ├── decision.py            # the step 1-6 flow
│   ├── normalize.py           # normalize() + collapse_trailing_code()
│   └── prompts.py             # SYSTEM, USER_TEMPLATE, SCHEMA, ALL_CATEGORY_NAMES const
└── llm/
    ├── __init__.py
    └── openrouter.py          # OpenRouterClient
```

`ALL_CATEGORY_NAMES` is **not** hard-coded. It's loaded once at app startup from the
`categories` table (so adding a category in Settings just works). The list is cached in
the app state and refreshed when categories CRUD endpoints run (Phase 5).

## 4.8 Tests

### Pure (no LLM, no DB)

```python
def test_normalize_table():
    cases = [
        ("Swiggy Ltd",                                "SWIGGY"),
        ("SWIGGY INSTAMART PRIVATE LIMITED",          "SWIGGY INSTAMART"),
        ("Zepto Marketplace Private Limi",            "ZEPTO MARKETPLACE"),
        ("ZEPTONOW",                                  "ZEPTONOW"),
        ("Indian Oil Petrol Pump - Devaraj Enterp.",  "INDIAN OIL PETROL PUMP"),
        ("KAMAT CAFE & PASTRIES",                     "KAMAT CAFE & PASTRIES"),
        ("******1492",                                "******1492"),
    ]
    for raw, expected in cases:
        assert normalize(raw) == expected

def test_collapse_trailing_code():
    assert collapse_trailing_code("ZOMATO8759546") == "ZOMATO"
    assert collapse_trailing_code("BMTC BUS KA57F3003") == "BMTC BUS"
    assert collapse_trailing_code("SWIGGY") == "SWIGGY"

def test_self_transfer_detection():
    txn = make_txn(merchant_raw="XXXXXX8216", type_="debit")
    result = decide(txn, own={"4200", "8216"}, mappings={})
    assert result.category_name == "Transfers"
    assert result.needs_review is False
```

### Round-trip seed integrity

```python
def test_all_seed_patterns_are_normalized_idempotently(db):
    patterns = db.execute("SELECT merchant_pattern FROM merchant_mappings WHERE source='seed'").scalars().all()
    for p in patterns:
        assert normalize(p) == p, f"seed pattern '{p}' is not in normalized form"
```

### Integration (mocked LLM)

```python
async def test_low_confidence_does_not_persist_mapping(db, monkeypatch):
    monkeypatch.setattr(OpenRouterClient, "chat_json", _stub_returning({"results": [{
        "merchant": "MYSTERY MART", "category": "Shopping", "confidence": 0.40
    }]}))
    txn = make_txn(merchant_raw="Mystery Mart")
    [result] = await categorize_batch([txn], own=set(), db=db, llm=client)
    assert result.needs_review is True
    rows = db.execute("SELECT * FROM merchant_mappings WHERE merchant_pattern='MYSTERY MART'").all()
    assert rows == []

async def test_high_confidence_persists_mapping(db, monkeypatch):
    ...
```

### Live-LLM smoke (skipped in CI by default)

A single `@pytest.mark.live_llm` test that hits OpenRouter with one merchant and asserts the response schema parses. Runs only when `RUN_LIVE_LLM=1` is set.

## 4.9 Definition of done

- [ ] `normalize()` + `collapse_trailing_code()` implemented and unit-tested for the table in §4.3.
- [ ] Seed round-trip test passes (every seeded pattern is its own normalize output).
- [ ] `categorize(txn, ...)` returns correct results for the 4 scripted scenarios: self-transfer, credit, mapping hit, mapping miss + LLM.
- [ ] `categorize_batch(...)` issues exactly **one** OpenRouter call for N unknown merchants (verified by mock counter).
- [ ] `OpenRouterClient` includes the `provider.require_parameters` and `response_format.json_schema` payload, and sends the OpenRouter `HTTP-Referer` + `X-Title` headers.
- [ ] Rate-limit retry (429 backoff) is implemented and tested via mocked transport.
- [ ] LLM mapping insert uses `ON CONFLICT (merchant_pattern) DO NOTHING`.
- [ ] No mapping is persisted for low-confidence verdicts.

## 4.10 Risks / open questions

- **`provider.require_parameters` may exclude free providers** that don't implement `json_schema` strictly, forcing the request to a paid provider (which would fail since the model is `:free`). If we hit this, fall back to `response_format: {type: "json_object"}` and validate the response against our schema manually with `pydantic`.
- **20 RPM cap.** If a batch ever sends 30 calls in a minute (unlikely with batching), we'll hit 429. Backoff handles it; in the worst case those merchants fall to `needs_review`.
- **Category drift.** If the user renames a category, `merchant_mappings.category_id` still points correctly (FK). If they delete a category, the seed/LLM mappings become orphans — the FK is `RESTRICT` by default; Settings page (Phase 8) must require a "move mappings to ..." choice before allowing delete of a category that has mappings.
- **LLM lies about merchant name.** Mitigated by string-equality post-check in §4.5.
