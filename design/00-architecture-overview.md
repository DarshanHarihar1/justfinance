# 00 — Architecture Overview

> Reference doc. Not a build phase. Read this first; every other doc assumes you have.

## 1. Product summary

A self-hosted, single-user personal finance tracker.

- Upload PhonePe monthly statement PDFs.
- Auto-categorize transactions using a rule-pack + learned mappings + LLM fallback.
- Manually categorize anything that's still ambiguous; the system never asks twice.
- Browse monthly dashboards, month-on-month trends, and LLM-generated insights.

## 2. High-level architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              Frontend — React + Vite + TypeScript                 │
│  Vercel       Login │ Upload │ Review │ Dashboard │ Analytics    │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ HTTPS · cookie auth · JSON
┌─────────────────────────────────▼────────────────────────────────┐
│                    Backend — FastAPI (Python 3.12)                │
│                              Render                              │
│                                                                  │
│  Auth middleware ─►  Router layer  ─►  Services layer  ─►  DB    │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │ PDF parser  │ │Categorizer  │ │ Merchant     │ │ Analytics │ │
│  │ (regex,     │ │(rule-pack + │ │ normalizer   │ │ (SQL agg) │ │
│  │  no LLM)    │ │   LLM)      │ │              │ │           │ │
│  └─────────────┘ └──────┬──────┘ └──────────────┘ └─────┬─────┘ │
│                         │                                │       │
└─────────────────────────┼────────────────────────────────┼──────┘
                          │                                │
                          ▼                                ▼
                 ┌─────────────────┐              ┌─────────────────┐
                 │   OpenRouter    │              │    Supabase     │
                 │ (free models)   │              │ (Postgres 15)   │
                 │ — categoriz.    │              │  via Supavisor  │
                 │ — insights      │              │   port 6543     │
                 └─────────────────┘              └─────────────────┘
```

### Request flow — statement upload

```
POST /api/statements/upload  (PDF body, cookie auth)
     │
     ▼
PhonePe parser (deterministic, in-process)
     │  list[ParsedTxn]
     ▼
Dedup against transactions.transaction_ref
     │  new[] + existing[]
     ▼
For each new ParsedTxn:
   ├── Is self-transfer (recipient is XXXXXX<own-account-last4>)?
   │     → category = Transfers, needs_review = FALSE
   ├── Is credit (type == "credit")?
   │     → category = Others, needs_review = TRUE
   └── Else (debit, external merchant):
         ├── Normalize merchant
         ├── Lookup merchant_mappings  →  HIT? auto-assign
         └── MISS → enqueue for LLM batch  →  high conf? assign + save mapping
                                                low conf? needs_review = TRUE
     │
     ▼
Bulk insert/upsert transactions
     │
     ▼
Response: { statement_id, parsed_count, new_count, needs_review_count }
```

## 3. Tech stack — final

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend framework | React 18 + Vite 5 | |
| Frontend language | **TypeScript** (strict) | |
| Styling | Tailwind CSS v4 + shadcn/ui (Radix primitives) | Minimalist design system, see `06-frontend.md` |
| Charts | Recharts | |
| State / data fetching | TanStack Query v5 | |
| Backend framework | FastAPI 0.115+ | |
| Backend language | Python 3.12 | |
| PDF text extraction | `pdfplumber` 0.11+ | Extracts raw text; structure parsed by our own regex |
| ORM | SQLAlchemy 2.x async + asyncpg | `NullPool` against Supavisor |
| Migrations | Plain SQL files in `supabase/migrations/` + Alembic optional | Start with plain SQL; only add Alembic if schema churns |
| LLM client | `httpx` against OpenRouter `chat/completions` | Structured outputs (`json_schema`) |
| Auth | FastAPI middleware + `itsdangerous` signed cookie | Single shared password |
| Local DB | Postgres 16 via Docker Compose | |
| Prod DB | Supabase free tier | Connect via Supavisor transaction-mode pooler |
| Backend host | Render free tier | |
| Frontend host | Vercel free tier | |

## 4. Supabase integration notes (verified, May 2026)

Free tier:

- 500 MB DB, 5 GB egress, 1 GB file storage.
- 2 active projects max. **Projects auto-pause after 7 days of inactivity** → since the app is used once a month, the prod project will pause. First request after a pause will reconnect (Supabase docs say the project resumes automatically on the first API request).
- 60 direct connections, 200 pooler connections.

Connection rules for FastAPI (non-negotiable):

- Use the **Supavisor transaction-mode** pooler at port `6543`, not direct `5432`.
- With SQLAlchemy + asyncpg, **must** disable prepared statements or you'll hit `prepared statement does not exist`:

  ```python
  from sqlalchemy.ext.asyncio import create_async_engine
  from sqlalchemy.pool import NullPool

  engine = create_async_engine(
      settings.database_url,                # postgresql+asyncpg://...:6543/postgres
      poolclass=NullPool,                   # let Supavisor pool, not us
      connect_args={
          "statement_cache_size": 0,
          "prepared_statement_cache_size": 0,
      },
  )
  ```

- Direct `5432` connection is reserved for one-off migration scripts (`scripts/migrate.py`).

## 5. OpenRouter integration notes (verified, May 2026)

Free tier:

- 20 requests / minute.
- 50 requests / day if account has < $10 lifetime credits, 1000 / day if ≥ $10.
- Free model variants end in `:free`. Current usable free models:
  - `meta-llama/llama-3.3-70b-instruct:free`
  - `deepseek/deepseek-r1:free`
  - `google/gemma-3-12b:free`
  - `qwen/qwen3-coder:free`
- `google/gemma-3-27b-it:free` from the original plan is **not** currently in the free catalog.

Structured outputs:

- Supported via `response_format: { type: "json_schema", json_schema: {...} }`.
- Set `provider.require_parameters: true` so OpenRouter routes only to providers that
  honor `json_schema` (and don't silently degrade to `json_object`).
- Sample request:

  ```python
  payload = {
      "model": "meta-llama/llama-3.3-70b-instruct:free",
      "messages": [
          {"role": "system", "content": SYSTEM_PROMPT},
          {"role": "user",   "content": user_prompt},
      ],
      "provider": {"require_parameters": True},
      "response_format": {
          "type": "json_schema",
          "json_schema": {
              "name": "categorization",
              "strict": True,
              "schema": {
                  "type": "object",
                  "additionalProperties": False,
                  "required": ["category", "confidence"],
                  "properties": {
                      "category":   {"type": "string", "enum": ALL_CATEGORY_NAMES},
                      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                  },
              },
          },
      },
  }
  ```

LLM budget consequences:

- 50 req/day is the realistic ceiling. The architecture compensates by:
  1. Pre-seeding `merchant_mappings` with a built-in rule-pack of 80+ common Indian merchants.
  2. Bucket-LLM-calls: batch up to 10 unknown merchants in a single prompt that returns an array.
  3. Aggressive merchant normalization to maximize cache hit rate.
  4. Persisting every LLM verdict into `merchant_mappings` (with `is_manual = FALSE`) so the same merchant never costs a second call.

## 6. Core data flow invariants

These hold across the whole system:

- **Idempotent uploads.** Re-uploading the same PDF produces zero new transactions; `transactions.transaction_ref` is `UNIQUE`.
- **No silent categorization changes.** Once a merchant is mapped, we never overwrite the mapping unless the user explicitly does so from the Settings page. The LLM cannot overwrite an existing mapping.
- **`needs_review = TRUE` is the only thing the user is ever asked about.** Everything else is invisible to them on the review screen.
- **Transfers are a structural category.** They exist in the DB but are filtered out of every spending aggregate. They never count against income either.

## 7. Out of scope (for this build)

These are deferred to a future iteration and explicitly not designed for here:

- Multiple bank accounts as a first-class concept (we collapse to one wallet).
- Budgets / alerts.
- Recurring transaction detection.
- Multi-currency.
- Offline LLM via Ollama.
- Email reports.
- Mobile PWA install (the responsive web UI is enough).

## 8. Glossary

| Term | Meaning |
|------|--------|
| **Statement** | A single uploaded PhonePe PDF, identified by `(period_start, period_end)`. |
| **Transaction** | A single line item parsed from a statement. Unique by `transaction_ref` (PhonePe Transaction ID). |
| **Merchant** | The normalized recipient string, derived from the raw `Paid to ...` line. |
| **Merchant mapping** | A row in `merchant_mappings` linking a normalized merchant pattern to a category. May be seeded, LLM-learned, or user-set. |
| **Rule-pack** | The seeded set of common Indian merchant mappings shipped with the app. |
| **Needs review** | A transaction flag indicating the user must explicitly categorize it before it's counted in analytics. |
| **Self-transfer** | A transaction where the recipient masked suffix matches one of the user's own account last-4s. Auto-categorized as `Transfers`. |
