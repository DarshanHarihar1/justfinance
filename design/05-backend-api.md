# Phase 5 — Backend API & Password Auth

> Goal: a complete, runnable FastAPI app with password-gated endpoints, the statement
> upload pipeline wired end-to-end, and CRUD routes for the entities the frontend needs.

## Prerequisites

- Phases 1–4 complete (infra, schema, parser, categorizer).

## 5.1 Auth — single shared password

Decision: cookie-based session, signed with `itsdangerous`, `httpOnly` + `Secure` +
`SameSite=Lax`. No DB-backed sessions; the cookie *is* the session.

### Flow

```
POST /api/auth/login  { "password": "..." }
  │
  ├─ password matches APP_PASSWORD_HASH (bcrypt)
  │     → Set-Cookie: session=<signed_token>; HttpOnly; SameSite=Lax; Max-Age=<SESSION_MAX_AGE>
  │     → 204 No Content
  └─ no  → 401 Unauthorized

POST /api/auth/logout  → clears cookie, 204
GET  /api/auth/me      → 200 if cookie valid, else 401
```

### Cookie contents

The signed token payload is intentionally trivial — just a constant + issued-at timestamp:

```python
{"v": 1, "iat": <unix-ts>}
```

We sign with `URLSafeTimedSerializer(secret=SESSION_SECRET)` and validate with
`max_age=SESSION_MAX_AGE`. There's nothing user-specific to carry; this is a single-user
system. We sign rather than encrypt because there's no secret data in the payload.

### Middleware

A single ASGI middleware checks the cookie on every request except a small allowlist:

- `GET /healthz`
- `POST /api/auth/login`
- `OPTIONS /*` (CORS preflight)

Anything else without a valid cookie returns `401`. The frontend treats `401` as a redirect-to-login signal.

```python
# backend/app/auth/middleware.py

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_ALLOW = {("GET", "/healthz"), ("POST", "/api/auth/login")}

class SessionAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, secret: str, cookie_name: str, max_age: int):
        super().__init__(app)
        self._ser = URLSafeTimedSerializer(secret, salt="ft-session")
        self._cookie = cookie_name
        self._max_age = max_age

    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if (request.method, request.url.path) in _ALLOW:
            return await call_next(request)
        token = request.cookies.get(self._cookie)
        if not token:
            return JSONResponse({"error": "unauthenticated"}, status_code=401)
        try:
            self._ser.loads(token, max_age=self._max_age)
        except (BadSignature, SignatureExpired):
            return JSONResponse({"error": "unauthenticated"}, status_code=401)
        return await call_next(request)
```

### Brute-force protection

Light-touch: a per-IP rolling counter (in-process dict, no Redis). 10 wrong attempts in 5 minutes → 429 with `Retry-After: 300`. Acceptable for single-user; we're not running an auth service.

## 5.2 App structure

```
backend/app/
├── main.py                # FastAPI app, lifespan, middleware, router includes
├── core/
│   ├── config.py          # Settings (BaseSettings)
│   ├── database.py        # engine, AsyncSession factory, get_db dependency
│   ├── security.py        # password hash/verify, cookie serializer
│   └── logging.py         # structlog
├── auth/
│   ├── middleware.py
│   └── routes.py          # /api/auth/*
├── routers/
│   ├── statements.py
│   ├── transactions.py
│   ├── categories.py
│   ├── mappings.py
│   └── analytics.py       # full impl in Phase 7
├── services/
│   ├── pdf_parser/        # Phase 3
│   ├── categorizer/       # Phase 4
│   ├── llm/               # Phase 4
│   └── upload_pipeline.py # orchestrates parse → dedup → categorize → insert
├── schemas/               # Pydantic request/response models
│   ├── auth.py
│   ├── statement.py
│   ├── transaction.py
│   ├── category.py
│   └── mapping.py
└── models/                # Phase 2 SQLAlchemy models
```

## 5.3 Configuration

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str
    database_is_pooled: bool = False

    app_password_hash: str
    session_secret: str
    session_max_age: int = 60 * 60 * 24 * 30
    session_cookie_name: str = "ft_session"

    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model_categorize: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_model_insights: str   = "deepseek/deepseek-r1:free"
    openrouter_app_name: str = "finance-tracker"
    openrouter_app_url: str  = "http://localhost:5173"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
```

## 5.4 Database wiring

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from .config import settings

def _engine_kwargs():
    if settings.database_is_pooled:
        # Supabase Supavisor → transaction mode → disable prepared statements
        return dict(
            poolclass=NullPool,
            connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
        )
    return dict(poolclass=AsyncAdaptedQueuePool, pool_size=5, max_overflow=5)

engine = create_async_engine(settings.database_url, **_engine_kwargs())
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session
```

## 5.5 Endpoints — full surface

### Auth

```
POST   /api/auth/login                       body: { password } → 204 + Set-Cookie
POST   /api/auth/logout                      → 204 + clear cookie
GET    /api/auth/me                          → 200 { authenticated: true } | 401
```

### Statements

```
POST   /api/statements/upload                multipart, field "file" → ParsedSummary
GET    /api/statements                       → list[StatementOut]
GET    /api/statements/{id}                  → StatementOut
DELETE /api/statements/{id}                  → 204 (cascade deletes transactions)
```

`ParsedSummary` response shape:

```typescript
{
  statement_id: number,
  period_start: string,        // ISO date
  period_end:   string,
  parsed_count: number,        // total transactions in the PDF
  new_count:    number,        // newly inserted (after dedup)
  needs_review_count: number,  // among new, how many need user input
  warnings: string[]           // e.g. ["llm_rate_limited"]
}
```

### Transactions

```
GET    /api/transactions                     filters: month, year, category_id,
                                                      needs_review, type, search,
                                                      page, page_size
GET    /api/statements/{id}/review           → list[TransactionOut] WHERE needs_review = TRUE
POST   /api/transactions/categorize          body: BulkCategorize → 200
PATCH  /api/transactions/{id}                body: TransactionPatch → TransactionOut
```

`BulkCategorize`:

```typescript
{
  items: Array<{
    transaction_id: number,
    category_id: number,
    remember: boolean          // if true, upsert merchant_mappings(source='manual')
  }>
}
```

Behavior of `POST /api/transactions/categorize`:

1. For each item, set `transactions.category_id`, `is_manually_categorized = TRUE`, `needs_review = FALSE`.
2. If `remember = true` **and** the txn has a `merchant_normalized` value (i.e., not anonymous "Paid"):
   - Upsert into `merchant_mappings`: `INSERT (pattern, category_id, source='manual') ON CONFLICT (merchant_pattern) DO UPDATE SET category_id = EXCLUDED.category_id, source = 'manual', updated_at = NOW()`.
   - **Also**: cascade — update every other transaction with the same `merchant_normalized` that is currently `needs_review = TRUE` to apply this category and clear review.

   The cascade is what makes "learn once, apply everywhere" feel magical to the user.

### Categories

```
GET    /api/categories                       → list[CategoryOut]
POST   /api/categories                       body: CategoryCreate → CategoryOut
PATCH  /api/categories/{id}                  body: CategoryPatch → CategoryOut
DELETE /api/categories/{id}                  query: ?move_to=<id> → 204
```

- `DELETE` is blocked (`409`) if the category has any `merchant_mappings` or
  `transactions` referencing it, unless `move_to` is provided. With `move_to`, we
  reassign both tables atomically, then delete.
- System categories (`is_system = TRUE`) cannot be deleted (`409 system_category`).

### Merchant mappings

```
GET    /api/mappings                         filters: source, category_id, search, page
POST   /api/mappings                         body: MappingCreate → MappingOut
PATCH  /api/mappings/{id}                    body: MappingPatch → MappingOut
DELETE /api/mappings/{id}                    → 204
```

`POST` and `PATCH` always set `source = 'manual'` and clear `confidence`.

### Analytics (skeleton here, full design in Phase 7)

```
GET    /api/analytics/dashboard/{month}/{year}     → DashboardOut
GET    /api/analytics/mom                          → MoMOut (last 12 months)
GET    /api/analytics/trends/{category_id}         → TrendOut
POST   /api/analytics/insights                     body: { month, year } → InsightsOut
POST   /api/analytics/ask                          body: { question, month, year } → AnswerOut
```

### Misc

```
GET    /healthz                              → { "status": "ok" }
```

## 5.6 Upload pipeline — orchestration

```python
# backend/app/services/upload_pipeline.py

async def ingest_statement(
    *,
    pdf_bytes: bytes,
    filename: str,
    db: AsyncSession,
    llm: OpenRouterClient,
) -> ParsedSummary:

    # 1. Parse (deterministic, no LLM)
    parsed = parse_phonepe_pdf(pdf_bytes)
    if not parsed.transactions:
        raise UnprocessableEntity("phonepe_parse_empty")

    # 2. Create or fetch the Statement row keyed by (period_start, period_end)
    stmt = await get_or_create_statement(
        db,
        period_start=parsed.period_start,
        period_end=parsed.period_end,
        filename=filename,
        raw_text=parsed.raw_text,
    )

    # 3. Dedup against transactions.transaction_ref
    existing_refs = await db.scalars(
        select(Transaction.transaction_ref).where(
            Transaction.transaction_ref.in_([t.transaction_ref for t in parsed.transactions])
        )
    )
    existing = set(existing_refs)
    new_txns = [t for t in parsed.transactions if t.transaction_ref not in existing]

    # 4. Detect own accounts from this statement (set of last-4s of "Debited from XX****")
    own_last4s = _detect_own_account_last4s(parsed.raw_text)

    # 5. Categorize new transactions
    results = await categorize_batch(
        new_txns,
        own_account_last4s=own_last4s,
        db=db,
        llm=llm,
    )

    # 6. Bulk insert
    rows = [
        Transaction(
            statement_id=stmt.id,
            transaction_ref=t.transaction_ref,
            utr_no=t.utr_no,
            date=t.date,
            time=t.time,
            description=t.description,
            merchant_raw=t.merchant_raw,
            merchant_normalized=r.merchant_normalized,
            amount=t.amount,
            type=t.type,
            category_id=r.category_id,
            is_manually_categorized=False,
            needs_review=r.needs_review,
        )
        for t, r in zip(new_txns, results)
    ]
    db.add_all(rows)
    await db.commit()

    return ParsedSummary(
        statement_id=stmt.id,
        period_start=parsed.period_start,
        period_end=parsed.period_end,
        parsed_count=len(parsed.transactions),
        new_count=len(new_txns),
        needs_review_count=sum(1 for r in results if r.needs_review),
        warnings=[],
    )
```

### `get_or_create_statement`

Idempotency:

- Same `(period_start, period_end)` → reuse existing row, update `filename` and `raw_text`.
- Different period overlapping an existing one → create new row. We don't try to be clever about partial overlaps; if a user uploads two statements covering overlapping periods, the dedup constraint on `transaction_ref` handles the actual deduplication.

## 5.7 Schemas (Pydantic)

Single example shown; the rest are mechanical.

```python
# backend/app/schemas/transaction.py
from datetime import date, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    statement_id: int
    transaction_ref: str
    date: date
    time: time | None
    description: str
    merchant_raw: str | None
    merchant_normalized: str | None
    amount: Decimal
    type: str
    category_id: int | None
    is_manually_categorized: bool
    needs_review: bool
    notes: str | None

class TransactionPatch(BaseModel):
    category_id: int | None = None
    notes: str | None = None
    remember: bool = Field(default=False, description="If true, persist the merchant→category mapping")
```

## 5.8 CORS

`fastapi.middleware.cors.CORSMiddleware` with:

- `allow_origins = settings.cors_origins`
- `allow_credentials = True` (required for cookies)
- `allow_methods = ["*"]`
- `allow_headers = ["*"]`

The frontend must call `fetch(..., { credentials: "include" })` for every request.

## 5.9 Lifespan

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.llm = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=settings.openrouter_model_categorize,
        app_name=settings.openrouter_app_name,
        app_url=settings.openrouter_app_url,
    )
    app.state.categories_cache = await load_categories_cache()
    yield
    await app.state.llm.aclose()
    await engine.dispose()

app = FastAPI(lifespan=lifespan, title="Finance Tracker API")
app.add_middleware(SessionAuthMiddleware, secret=settings.session_secret,
                   cookie_name=settings.session_cookie_name, max_age=settings.session_max_age)
app.add_middleware(CORSMiddleware, ...)

app.include_router(auth_router,    prefix="/api/auth")
app.include_router(statements_r,   prefix="/api/statements")
app.include_router(transactions_r, prefix="/api")     # mixed paths
app.include_router(categories_r,   prefix="/api/categories")
app.include_router(mappings_r,     prefix="/api/mappings")
app.include_router(analytics_r,    prefix="/api/analytics")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
```

## 5.10 Tests

- `tests/test_auth.py` — login with right/wrong password, cookie set, middleware blocks unauthenticated requests, brute-force lockout after 10 failed tries.
- `tests/test_upload_pipeline.py` — POST the sample PDF, assert response counts; POST it again, assert `new_count = 0`.
- `tests/test_transactions_categorize.py` — bulk categorize 3 transactions with `remember=True`, assert merchant_mappings has the rows and that other `needs_review` transactions with the same `merchant_normalized` got auto-resolved.
- `tests/test_categories.py` — delete a category with mappings without `move_to` → 409; with `move_to` → cascade move works.
- `tests/test_dedup.py` — uploading two PDFs with overlapping transactions produces a single row per `transaction_ref`.

All tests run against a temporary Postgres instance (the same Docker `db` service in CI).

## 5.11 Definition of done

- [ ] `docker compose up` → `curl -i http://localhost:8000/healthz` returns 200.
- [ ] `POST /api/auth/login` with the configured password sets a cookie; without it returns 401.
- [ ] Every protected endpoint returns 401 with no cookie.
- [ ] `POST /api/statements/upload` with the sample PhonePe PDF returns a `ParsedSummary` with `parsed_count` matching the parser's known count.
- [ ] Re-uploading the same PDF returns `new_count: 0`.
- [ ] All 5 test files in §5.10 pass.
- [ ] OpenAPI docs at `/docs` show every endpoint with full schemas.
- [ ] Structured JSON logs on stdout (structlog) with the request method, path, status, duration.

## 5.12 Risks / open questions

- **Cookie cross-site in prod.** Backend at `*.onrender.com`, frontend at `*.vercel.app`. We must set `SameSite=None; Secure` in prod for the cookie to travel. In dev (both localhost) `SameSite=Lax` is fine. Config switches on `settings.cors_origins[0].startswith("https")` or an explicit `COOKIE_SAMESITE` env var.
- **Render cold start during upload.** A 60s cold start mid-upload could time the request out. The frontend should retry the upload once on 502/504 (Phase 6 §6.7).
- **No DB migration tool.** We're applying SQL files manually to Supabase. If schema churn happens, add Alembic in a follow-up. Document the migration order in `supabase/migrations/README.md`.
- **In-process brute-force counter.** Lost on restart. Acceptable for a single-user app.
