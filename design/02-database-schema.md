# Phase 2 — Database Schema & Seeds

> Goal: a single migration file that creates every table, index, and constraint, plus
> a seed file that loads default categories and the merchant rule-pack. This is the
> only phase that touches DDL until a future schema change is needed.

## Prerequisites

- Phase 1 complete (`docker compose up` brings Postgres up; migrations auto-apply).

## 2.1 Design changes vs. the original plan

| Change | Why |
|--------|-----|
| `statements.month` + `statements.year` → `period_start DATE` + `period_end DATE` | PhonePe statements span date ranges, not calendar months. |
| Drop `UNIQUE(month, year)` on `statements` | A range can overlap; uniqueness is enforced at the transaction level. |
| Add `transactions.transaction_ref TEXT UNIQUE NOT NULL` | Idempotent uploads. |
| Add `transactions.utr_no TEXT` | Useful for cross-checking with bank statements later. |
| Add `transactions.time TIME` | PhonePe gives time; nice for "9pm Zomato" pattern detection later. |
| Add `Transfers` as a seeded category | Self-transfers go here and are excluded from spending aggregates. |
| Seed `merchant_mappings` with a 80+ row rule-pack | Burns through OpenRouter quota otherwise. |
| Add `categories.is_system BOOLEAN` | `Transfers` and other essentials cannot be deleted from Settings. |
| Add `categories.excluded_from_spending BOOLEAN` | Lets analytics filter without hard-coding category IDs. |
| Add `merchant_mappings.source TEXT CHECK (source IN ('seed','llm','manual'))` | Replaces the `is_manual` boolean; we need to distinguish seeded vs LLM-learned for "reset to defaults" UX. |
| Add `merchant_mappings.last_used_at TIMESTAMP` | Helpful for the Settings page sorting. |

## 2.2 Migration — `supabase/migrations/0001_initial.sql`

```sql
-- ════════════════════════════════════════════════════════════════════
-- 0001_initial.sql — Personal Finance Tracker initial schema
-- ════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────
-- categories
-- ─────────────────────────────────────────
CREATE TABLE categories (
    id                       SERIAL PRIMARY KEY,
    name                     TEXT NOT NULL UNIQUE,
    color                    TEXT NOT NULL DEFAULT '#9E9E9E',
    icon                     TEXT NOT NULL DEFAULT '📦',
    is_system                BOOLEAN NOT NULL DEFAULT FALSE,
    excluded_from_spending   BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order               INTEGER NOT NULL DEFAULT 100,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- statements
-- ─────────────────────────────────────────
CREATE TABLE statements (
    id           SERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    filename     TEXT,
    raw_text     TEXT,
    source       TEXT NOT NULL DEFAULT 'phonepe'
                  CHECK (source IN ('phonepe')),   -- enum widens later
    uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (period_end >= period_start)
);

CREATE INDEX idx_statements_period ON statements (period_start, period_end);

-- ─────────────────────────────────────────
-- transactions
-- ─────────────────────────────────────────
CREATE TABLE transactions (
    id                       SERIAL PRIMARY KEY,
    statement_id             INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,

    -- Natural identity from PhonePe.
    transaction_ref          TEXT NOT NULL,         -- "T2604281930148688800258"
    utr_no                   TEXT,                  -- "376914838281"

    -- Core fields.
    date                     DATE NOT NULL,
    time                     TIME,
    description              TEXT NOT NULL,         -- raw "Paid to ..." line
    merchant_raw             TEXT,                  -- the recipient as printed
    merchant_normalized      TEXT,                  -- normalized lookup key
    amount                   NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    type                     TEXT NOT NULL CHECK (type IN ('debit', 'credit')),

    -- Classification.
    category_id              INTEGER REFERENCES categories(id),
    is_manually_categorized  BOOLEAN NOT NULL DEFAULT FALSE,
    needs_review             BOOLEAN NOT NULL DEFAULT FALSE,

    notes                    TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_transactions_ref UNIQUE (transaction_ref)
);

CREATE INDEX idx_transactions_statement      ON transactions (statement_id);
CREATE INDEX idx_transactions_date           ON transactions (date);
CREATE INDEX idx_transactions_category       ON transactions (category_id);
CREATE INDEX idx_transactions_needs_review   ON transactions (needs_review) WHERE needs_review = TRUE;
CREATE INDEX idx_transactions_merchant_norm  ON transactions (merchant_normalized);

-- ─────────────────────────────────────────
-- merchant_mappings (the learning layer)
-- ─────────────────────────────────────────
CREATE TABLE merchant_mappings (
    id                  SERIAL PRIMARY KEY,
    merchant_pattern    TEXT NOT NULL UNIQUE,       -- normalized; matches merchant_normalized exactly
    category_id         INTEGER NOT NULL REFERENCES categories(id),
    source              TEXT NOT NULL DEFAULT 'manual'
                         CHECK (source IN ('seed', 'llm', 'manual')),
    confidence          NUMERIC(3, 2),              -- nullable; only set when source='llm'
    times_used          INTEGER NOT NULL DEFAULT 0,
    last_used_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_merchant_mappings_category  ON merchant_mappings (category_id);

-- ─────────────────────────────────────────
-- updated_at triggers
-- ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_merchant_mappings_updated_at
BEFORE UPDATE ON merchant_mappings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

## 2.3 Seed — `supabase/seed.sql`

The seed is idempotent (`ON CONFLICT DO NOTHING`) so it can be re-run safely.

```sql
-- ════════════════════════════════════════════════════════════════════
-- seed.sql — default categories + merchant rule-pack
-- ════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────
-- Categories
-- ──────────────────────────────────────────────
INSERT INTO categories (name, color, icon, is_system, excluded_from_spending, sort_order) VALUES
    ('Groceries',     '#4CAF50', '🛒', FALSE, FALSE, 10),
    ('Food & Dining', '#FF9800', '🍔', FALSE, FALSE, 20),
    ('Transport',     '#2196F3', '🚌', FALSE, FALSE, 30),
    ('Utilities',     '#9C27B0', '⚡', FALSE, FALSE, 40),
    ('Entertainment', '#E91E63', '🎬', FALSE, FALSE, 50),
    ('Subscriptions', '#673AB7', '📺', FALSE, FALSE, 55),
    ('Healthcare',    '#00BCD4', '🏥', FALSE, FALSE, 60),
    ('Shopping',      '#FF5722', '🛍️', FALSE, FALSE, 70),
    ('Personal Care', '#F06292', '💇', FALSE, FALSE, 75),
    ('Fuel',          '#795548', '⛽', FALSE, FALSE, 80),
    ('Rent & Bills',  '#3F51B5', '🏠', FALSE, FALSE, 85),
    ('Investments',   '#607D8B', '📈', FALSE, FALSE, 90),
    ('Income',        '#8BC34A', '💰', FALSE, FALSE, 95),
    ('Transfers',     '#9E9E9E', '↔️',  TRUE,  TRUE,  100),
    ('Cash Withdrawal','#BDBDBD','🏧', FALSE, FALSE, 105),
    ('Others',        '#9E9E9E', '📦', TRUE,  FALSE, 110)
ON CONFLICT (name) DO NOTHING;

-- ──────────────────────────────────────────────
-- Merchant rule-pack (India-focused)
-- Patterns must be in the exact form produced by merchant_normalizer.normalize().
-- See design/04-categorization-engine.md §4.3 for the normalizer contract.
-- ──────────────────────────────────────────────
WITH cat AS (
    SELECT name, id FROM categories
)
INSERT INTO merchant_mappings (merchant_pattern, category_id, source, confidence)
SELECT pattern, cat.id, 'seed', NULL
FROM (VALUES
    -- Food delivery
    ('SWIGGY',                          'Food & Dining'),
    ('SWIGGY INSTAMART',                'Groceries'),
    ('ZOMATO',                          'Food & Dining'),
    ('EATSURE',                         'Food & Dining'),
    ('FAASOS',                          'Food & Dining'),
    ('BOX8',                            'Food & Dining'),
    ('FRESHMENU',                       'Food & Dining'),

    -- Quick commerce / groceries
    ('ZEPTO',                           'Groceries'),
    ('ZEPTO MARKETPLACE',               'Groceries'),
    ('ZEPTONOW',                        'Groceries'),
    ('BLINKIT',                         'Groceries'),
    ('BIGBASKET',                       'Groceries'),
    ('BB DAILY',                        'Groceries'),
    ('DUNZO',                           'Groceries'),
    ('SWIGGY GENIE',                    'Others'),
    ('LICIOUS',                         'Groceries'),
    ('FRESHTOHOME',                     'Groceries'),
    ('COUNTRY DELIGHT',                 'Groceries'),
    ('MILKBASKET',                      'Groceries'),

    -- Cafes & food chains
    ('STARBUCKS',                       'Food & Dining'),
    ('BLUE TOKAI',                      'Food & Dining'),
    ('THIRD WAVE COFFEE',               'Food & Dining'),
    ('CHAI POINT',                      'Food & Dining'),
    ('KAMAT',                           'Food & Dining'),
    ('UDUPI VEG RESTAURANT',            'Food & Dining'),
    ('MEGHANA FOODS',                   'Food & Dining'),
    ('NATURALS',                        'Food & Dining'),
    ('PIZZA 4PS',                       'Food & Dining'),
    ('DOMINOS',                         'Food & Dining'),
    ('MCDONALDS',                       'Food & Dining'),
    ('KFC',                             'Food & Dining'),
    ('BURGER KING',                     'Food & Dining'),
    ('SUBWAY',                          'Food & Dining'),
    ('A1 FOODS',                        'Food & Dining'),
    ('MTR',                             'Food & Dining'),
    ('SAMOSA',                          'Food & Dining'),

    -- Transport
    ('BMTC',                            'Transport'),
    ('BMTC BUS',                        'Transport'),
    ('UBER',                            'Transport'),
    ('OLA',                             'Transport'),
    ('RAPIDO',                          'Transport'),
    ('IRCTC',                           'Transport'),
    ('NAMMA YATRI',                     'Transport'),
    ('YULU',                            'Transport'),

    -- Fuel
    ('INDIAN OIL',                      'Fuel'),
    ('HP PETROL PUMP',                  'Fuel'),
    ('BHARAT PETROLEUM',                'Fuel'),
    ('SHELL',                           'Fuel'),

    -- Bills / FASTag
    ('FASTAG',                          'Transport'),
    ('AIRTEL',                          'Utilities'),
    ('JIO',                             'Utilities'),
    ('VI',                              'Utilities'),
    ('BSNL',                            'Utilities'),
    ('TATA POWER',                      'Utilities'),
    ('BESCOM',                          'Utilities'),
    ('BWSSB',                           'Utilities'),

    -- Subscriptions / digital
    ('NETFLIX',                         'Subscriptions'),
    ('NETFLIX COM',                     'Subscriptions'),
    ('APPLE MEDIA SERVICES',            'Subscriptions'),
    ('APPLE',                           'Subscriptions'),
    ('GOOGLE',                          'Subscriptions'),
    ('SPOTIFY',                         'Subscriptions'),
    ('YOUTUBE',                         'Subscriptions'),
    ('PRIME VIDEO',                     'Subscriptions'),
    ('HOTSTAR',                         'Subscriptions'),
    ('JIOCINEMA',                       'Subscriptions'),
    ('OPENAI',                          'Subscriptions'),
    ('ANTHROPIC',                       'Subscriptions'),
    ('CURSOR',                          'Subscriptions'),
    ('GITHUB',                          'Subscriptions'),

    -- Cloud / dev
    ('AWS INDIA',                       'Subscriptions'),
    ('AWS',                             'Subscriptions'),

    -- Shopping
    ('AMAZON',                          'Shopping'),
    ('FLIPKART',                        'Shopping'),
    ('MYNTRA',                          'Shopping'),
    ('AJIO',                            'Shopping'),
    ('NYKAA',                           'Personal Care'),
    ('MEESHO',                          'Shopping'),

    -- Healthcare
    ('PHARMEASY',                       'Healthcare'),
    ('1MG',                             'Healthcare'),
    ('TATA 1MG',                        'Healthcare'),
    ('APOLLO',                          'Healthcare'),
    ('PRACTO',                          'Healthcare'),
    ('CULT FIT',                        'Personal Care'),
    ('CULTFIT',                         'Personal Care'),

    -- Personal services
    ('URBANCOMPANY',                    'Personal Care'),
    ('RENTOMOJO',                       'Rent & Bills'),
    ('FURLENCO',                        'Rent & Bills'),

    -- Cash withdrawal / banking
    ('SBI ATM',                         'Cash Withdrawal'),
    ('SBI ATM CASH WITHDRAWAL',         'Cash Withdrawal'),

    -- Investments
    ('ZERODHA',                         'Investments'),
    ('GROWW',                           'Investments'),
    ('UPSTOX',                          'Investments'),
    ('COIN BY ZERODHA',                 'Investments'),
    ('INDMONEY',                        'Investments'),

    -- Insurance
    ('HDFC ERGO',                       'Rent & Bills'),
    ('HDFC ERGO GENERAL INSURANCE',     'Rent & Bills'),
    ('ACKO',                            'Rent & Bills'),
    ('LIC',                             'Rent & Bills')
) AS v(pattern, category_name)
JOIN cat ON cat.name = v.category_name
ON CONFLICT (merchant_pattern) DO NOTHING;
```

Notes on the rule-pack:

- It's narrow on purpose. Generic words like `STORE`, `MART` etc. are intentionally not seeded — they'd over-match and surprise the user.
- Patterns are the **fully normalized** form. The normalizer (Phase 4) is responsible for converting `Swiggy Ltd`, `SWIGGY INSTAMART PRIVATE LIMITED`, `ZEPTO MARKETPLACE PRIVATE LIMI` (truncated), etc. into one of these canonical keys.
- The `Transfers` category does **not** appear in the rule-pack — self-transfers are detected structurally (see Phase 4 §4.5), not by merchant name.

## 2.4 SQLAlchemy models — `backend/app/models/`

One model per table. Style: declarative, async-friendly, no business logic.

```python
# backend/app/models/base.py
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

```python
# backend/app/models/category.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer
from .base import Base, TimestampMixin

class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False, default="#9E9E9E")
    icon: Mapped[str] = mapped_column(String, nullable=False, default="📦")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluded_from_spending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
```

```python
# backend/app/models/statement.py
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, String, Integer
from .base import Base, TimestampMixin

class Statement(Base, TimestampMixin):
    __tablename__ = "statements"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end:   Mapped[date] = mapped_column(Date, nullable=False)
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="phonepe")
```

```python
# backend/app/models/transaction.py
from datetime import date, time
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Date, Time, String, Integer, Boolean, ForeignKey, Numeric, UniqueConstraint,
)
from .base import Base, TimestampMixin

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), nullable=False
    )

    transaction_ref: Mapped[str] = mapped_column(String, nullable=False)
    utr_no: Mapped[str | None] = mapped_column(String, nullable=True)

    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time | None] = mapped_column(Time, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    merchant_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    merchant_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    is_manually_categorized: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (UniqueConstraint("transaction_ref", name="uq_transactions_ref"),)
```

```python
# backend/app/models/merchant_mapping.py
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey, Numeric, DateTime
from .base import Base, TimestampMixin

class MerchantMapping(Base, TimestampMixin):
    __tablename__ = "merchant_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_pattern: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

## 2.5 Definition of done

- [ ] `supabase/migrations/0001_initial.sql` creates every table, index, constraint, and trigger.
- [ ] `supabase/seed.sql` inserts categories and ≥ 80 merchant mappings, idempotently.
- [ ] SQLAlchemy models in `backend/app/models/` mirror the schema.
- [ ] After `docker compose down -v && docker compose up`, `psql` shows the seeded categories and mappings.
- [ ] Same SQL applied successfully to the prod Supabase project from the SQL editor.
- [ ] A round-trip unit test inserts a `Category`, `Statement`, and `Transaction` via SQLAlchemy and reads them back.
- [ ] Re-running the seed produces zero new rows (no duplicates).

## 2.6 Risks / open questions

- The rule-pack pattern strings must exactly match what the normalizer produces. Any divergence is a silent miss. Phase 4 includes a test that asserts every seeded pattern survives `normalize(pattern) == pattern` round-trip.
- If `Transfers` ever needs sub-categories (e.g., to-savings vs. to-checking), promote `Transfers` from a category to a `transfer_kind` column on `transactions`. Not in scope now.
- Postgres `SERIAL` is fine; we don't need `IDENTITY` portability concerns here.
