-- ════════════════════════════════════════════════════════════════════
-- 0001_initial.sql — Personal Finance Tracker initial schema
-- ════════════════════════════════════════════════════════════════════
-- See design/02-database-schema.md for the full rationale behind every
-- table, column, index, and constraint in this file.

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
-- updated_at trigger function + triggers
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
