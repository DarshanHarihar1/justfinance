# Phase 7 — Analytics: Dashboard, Trends, Insights

> Goal: monthly Dashboard, deep Analytics page with LLM-powered insights and a free-form
> "ask about your spending" chat, plus the backend SQL/aggregation layer that feeds them.

## Prerequisites

- Phases 1–6 complete. Real data is flowing into `transactions`.

## 7.1 Aggregation rules — the universal filter

Every analytics query starts from the same filter base:

```sql
WHERE t.needs_review = FALSE
  AND c.excluded_from_spending = FALSE     -- excludes Transfers
  AND t.category_id IS NOT NULL
```

Plus a per-query date filter. This single rule is why we added `excluded_from_spending`
to the schema — analytics never special-cases category IDs.

A small SQL helper view makes downstream queries cleaner:

```sql
-- backend/app/services/analytics/_view.sql (applied as a one-off migration or as raw SQL on app boot)
CREATE OR REPLACE VIEW v_spend AS
SELECT
    t.id, t.date, t.amount, t.type, t.category_id,
    t.merchant_normalized, t.statement_id,
    c.name AS category_name,
    c.color AS category_color
FROM transactions t
JOIN categories c ON c.id = t.category_id
WHERE t.needs_review = FALSE
  AND c.excluded_from_spending = FALSE
  AND t.category_id IS NOT NULL;
```

Income is `type = 'credit'` (and not excluded). Expenses are `type = 'debit'`.

## 7.2 Endpoints

### `GET /api/analytics/dashboard/{month}/{year}` → `DashboardOut`

```typescript
type DashboardOut = {
  month: number;
  year: number;
  totals: {
    income:   string;   // Decimal as string to avoid float drift
    expense:  string;
    net:      string;   // income - expense
    txn_count: number;
  };
  by_category: Array<{
    category_id: number;
    name: string;
    color: string;
    total: string;
    txn_count: number;
    pct_of_expense: number;     // 0..1
  }>;
  top_merchants: Array<{
    merchant_normalized: string;
    total: string;
    txn_count: number;
    category_id: number;
  }>;                            // top 10 by total amount
  recent_transactions: TransactionOut[];   // 10 most recent
  needs_review_count: number;    // banner if > 0
};
```

SQL sketch:

```sql
-- totals
SELECT
  COALESCE(SUM(CASE WHEN type='credit' THEN amount END), 0) AS income,
  COALESCE(SUM(CASE WHEN type='debit'  THEN amount END), 0) AS expense,
  COUNT(*) AS txn_count
FROM v_spend
WHERE date_trunc('month', date) = make_date(:year, :month, 1);

-- by_category
SELECT category_id, category_name AS name, category_color AS color,
       SUM(amount) AS total, COUNT(*) AS txn_count
FROM v_spend
WHERE type = 'debit'
  AND date_trunc('month', date) = make_date(:year, :month, 1)
GROUP BY 1, 2, 3
ORDER BY total DESC;
```

### `GET /api/analytics/mom` → `MoMOut`

```typescript
type MoMOut = {
  months: Array<{
    month: number;        // 1..12
    year: number;
    label: string;        // "May 2026"
    income: string;
    expense: string;
    net: string;
  }>;                     // last 12 months in chronological order; missing months filled with zeros
};
```

```sql
SELECT
  date_part('year',  date)::int  AS year,
  date_part('month', date)::int  AS month,
  COALESCE(SUM(CASE WHEN type='credit' THEN amount END), 0) AS income,
  COALESCE(SUM(CASE WHEN type='debit'  THEN amount END), 0) AS expense
FROM v_spend
WHERE date >= (CURRENT_DATE - INTERVAL '12 months')
GROUP BY 1, 2
ORDER BY 1, 2;
```

Backend fills any missing months with zeros so the chart can render a continuous 12-bar series.

### `GET /api/analytics/trends/{category_id}` → `TrendOut`

```typescript
type TrendOut = {
  category: { id: number; name: string; color: string };
  months: Array<{ year: number; month: number; total: string; txn_count: number }>;
  top_merchants: Array<{ merchant_normalized: string; total: string }>;
};
```

Default range: trailing 12 months. Optional `?from=YYYY-MM&to=YYYY-MM` to override.

### `POST /api/analytics/insights` body `{ month, year }` → `InsightsOut`

```typescript
type InsightsOut = {
  generated_at: string;
  model: string;           // e.g. "deepseek/deepseek-r1:free"
  insights: Array<{
    title: string;         // short headline
    body:  string;         // 1-2 sentences
    severity: "info" | "good" | "concern";
  }>;
};
```

The backend assembles a compact, **PII-free summary** payload locally and sends it to the LLM. The LLM never sees individual transaction descriptions or merchant names that look like personal names. Only the aggregated structure:

```json
{
  "month": "May 2026",
  "totals": { "income": 2066.0, "expense": 175342.5 },
  "by_category": [
    {"name": "Food & Dining", "total": 8742.10, "txn_count": 28, "pct": 0.34},
    {"name": "Groceries", "total": 5102.70, "txn_count": 22, "pct": 0.20},
    ...
  ],
  "prev_month_by_category": [...],     // for delta context
  "top_merchant_categories": [...]
}
```

Prompt (system):

```
You are a brief, plain-spoken personal-finance advisor for an Indian user.
You receive an aggregated monthly summary. Return 3–5 short insights.
Each insight has a 4–7 word title, a one-sentence body referencing concrete
numbers, and a severity. Avoid generic advice ("save more"); be specific
about which category moved and by how much. Return JSON only.
```

Schema enforced via `response_format`.

Caching: `InsightsOut` for a (month, year) is cached in-process for 24 hours, keyed by a hash of the underlying summary payload. The frontend's `[Regenerate]` button passes `?force=true` to bypass the cache.

### `POST /api/analytics/ask` body `{ question, month, year }` → `AnswerOut`

```typescript
type AnswerOut = {
  answer: string;          // markdown-safe plain text
  context_used: {
    month: number;
    year:  number;
    aggregations: string[]; // human-readable list, e.g. ["expense by category", "top merchants"]
  };
};
```

The same aggregated summary is sent along with the user's question. We **do not** allow
the LLM to query the DB directly. It only sees the pre-aggregated payload, plus optionally
a trailing 6-month MoM series.

Rate-limit guard: this endpoint is throttled to 5 requests / minute in app memory. The
frontend disables the input while one request is in flight.

## 7.3 Frontend — Dashboard page

```
┌─────────────────────────────────────────────────────────────────┐
│ May 2026                              [ ‹ Apr ]  [ Jun › ]      │
│                                                                  │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│ │ Income     │ │ Expense    │ │ Net        │ │ Top cat.   │    │
│ │ ₹2,066     │ │ ₹1,75,342  │ │ -₹1,73,276 │ │ Food       │    │
│ │            │ │            │ │            │ │ ₹8,742     │    │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                  │
│ Spending by category               │ Last 6 months                │
│ ┌──────────────────────────┐       │ ┌────────────────────────┐  │
│ │   donut chart            │       │ │   stacked bar chart    │  │
│ │   34% Food               │       │ │   income / expense     │  │
│ │   20% Groceries          │       │ └────────────────────────┘  │
│ │   ...                    │       │                              │
│ └──────────────────────────┘       │                              │
│                                                                  │
│ Recent transactions                                              │
│ Date    Merchant                Category        Amount           │
│ May 28  Blinkit                 Groceries       ₹305             │
│ May 27  Mr Nabin Rai            Others          ₹70   needs rev. │
│ ...                                                              │
└─────────────────────────────────────────────────────────────────┘
```

Components:

- `<SummaryCards />` — four numeric cards (Recharts not needed).
- `<CategoryDonut />` — Recharts `<PieChart>` with `cy="50%"`, inner radius 60%, neutral stroke between slices. Hover reveals total + count.
- `<MoMBar />` — Recharts `<BarChart>` with two bars per month (income up, expense down) or stacked variant.
- `<RecentTransactions />` — flat list, links to `/transactions` (future).

Month selector: a left/right arrow pair + month label. Clicking the label opens a small menu with year jump.

If `needs_review_count > 0` for the displayed month, an inline banner appears above the cards:
`<span>4 transactions need review.</span>  <a>Review them →</a>`

Dashboard fetches one endpoint (`/api/analytics/dashboard/{month}/{year}`) and one secondary (`/api/analytics/mom`).

## 7.4 Frontend — Analytics page

Two sections in a single page (no tabs — keep it linear):

### Insights

3–5 cards, generated by `POST /api/analytics/insights` for the current month:

```
┌────────────────────────────────────────────────────────┐
│ Insights — May 2026          [↻ Regenerate]           │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Food & Dining is up 28%                           ●│ │
│ │ ₹8,742 across 28 transactions vs ₹6,830 in April. │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Quick-commerce is a steady ~₹5k                   ○│ │
│ │ Zepto and Blinkit combined for ₹5,102 in 22 orders.│ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

Severity rendering: a small colored dot at the top-right of each card.
`good` → success, `concern` → danger, `info` → neutral gray.

### Ask

A single text input + send button + transcript area below. Conversations are not persisted — refresh clears them. (Persistence is a future enhancement, not in scope.)

```
┌────────────────────────────────────────────────────────┐
│ Ask about your spending                                │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Where did most of my food spend go this month?     │ │
│ └────────────────────────────────────────────────────┘ │
│                                              [ Ask ]   │
│                                                        │
│ ▸ Where did most of my food spend go this month?       │
│   You spent ₹8,742 on Food & Dining in May. The...     │
└────────────────────────────────────────────────────────┘
```

### Per-category trend

Below Insights and Ask, a section listing categories with mini sparklines:

```
Groceries           ₹5,102      ▁▁▂▃▄▅▆▇▇▆▅▄  ↑ 12%
Food & Dining       ₹8,742      ▂▃▄▅▆▇▅▄▃▄▅▆  ↑ 28%
Transport           ₹492        ▁▂▃▂▁▂▃▄▃▂▁▁  ↓ 4%
```

Clicking a row drills into a full trend page (`/analytics/category/:id`) with the larger chart and the top-merchants breakdown. (Drill-down route is built only if there's time; otherwise inline expandable rows.)

## 7.5 Performance considerations

- Aggregations use the `v_spend` view; indexes on `transactions(date)` and `transactions(category_id)` handle the workload comfortably.
- Each analytics endpoint should respond in < 100 ms for a year of typical usage (~3 K rows).
- `InsightsOut` is cached server-side for 24 h to preserve the 50/day OpenRouter budget; if the user hits **Regenerate** more than 5×/day, surface a friendly toast.
- The frontend prefetches `/api/analytics/dashboard/{currentMonth}` on `/upload` and `/review` mount, so navigating to the dashboard feels instant.

## 7.6 Definition of done

- [ ] `v_spend` view exists in Postgres (created in a follow-on migration `0002_views.sql`).
- [ ] All five analytics endpoints return correct results against the sample data set (verified by tests against a seeded DB fixture).
- [ ] Dashboard page renders all four summary cards, donut, bar chart, recent transactions, in under 1s on a primed backend.
- [ ] Month selector navigates without full page reload (uses React Router + query keys).
- [ ] Analytics page renders 3–5 insight cards within ~5s on a primed backend after the LLM call.
- [ ] "Ask" works for a basic question and returns a coherent answer referencing actual numbers from the user's data.
- [ ] Transfers and `needs_review` transactions are excluded from every numeric aggregate; this is asserted by a backend test that inserts both kinds and verifies they don't appear.
- [ ] Insights endpoint **never** sends raw `description` strings to the LLM (verified by a unit test inspecting the assembled payload).

## 7.7 Risks / open questions

- **Empty month.** If a month has zero spend (no statements uploaded), dashboard shows the empty state with a CTA back to Upload, and `insights` is skipped (no LLM call).
- **LLM hallucination of numbers.** Mitigated by giving the LLM only aggregated numbers as input; we ask it to "reference concrete numbers" but only ones we've already provided. Tests verify the prompt contains the expected numbers verbatim so the LLM has a fact base to draw from.
- **Insights cache key.** Includes a SHA of the summary payload, so any new transaction (or recategorization) invalidates the cache automatically.
- **DeepSeek-R1 token cost.** R1 is a reasoning model with hidden chain-of-thought tokens, slower than Llama 3.3 70B. If insights feel sluggish, swap `OPENROUTER_MODEL_INSIGHTS` to the same Llama 3.3 70B used for categorization. No code change needed beyond the env var.
