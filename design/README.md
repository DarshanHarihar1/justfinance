# Personal Finance Tracker — Design

This directory contains the implementation design for the personal finance tracker.

It is the **source of truth** for what will be built. The original brainstorm lives in
`uploads/finance-tracker-plan_5d31.md`; the docs here are the refined, decision-locked
version after analyzing the sample PhonePe statement and verifying the current state of
the Supabase / OpenRouter free tiers (May 2026).

## Decisions locked in this design

| # | Topic | Decision |
|---|-------|---------|
| 1 | PDF parsing | **Deterministic PhonePe regex/state-machine parser.** No LLM in the extraction path. |
| 2 | Statement period | `period_start` / `period_end` on `statements`. Transactions are bucketed into months by their own date. |
| 3 | Multi-account | Ignore the source account (`XX4200`, `XX8216`); treat as one wallet. |
| 4 | Self-transfers | Detected from masked own-account suffixes; auto-assigned to a `Transfers` category and excluded from spending charts. |
| 5 | Credits | Default to `Others` with `needs_review = TRUE` so the user explicitly labels them. |
| 6 | Dedup | `UNIQUE(transaction_ref)` on transactions. Re-uploads are upserts. |
| 7 | Auth | Single shared password gate, FastAPI middleware, signed `httpOnly` cookie. |
| 8 | Frontend | React + Vite + **TypeScript** + Tailwind + shadcn/ui. Minimalist aesthetic. |
| 9 | Local dev DB | Docker Compose Postgres. Supabase used only for production. |
| 10 | PDF binary | Not stored; only the extracted text in `statements.raw_text`. |
| 11 | Categorization | Built-in rule-pack of common Indian merchants seeded into `merchant_mappings`. LLM is the last-resort fallback. |
| 12 | Masked merchants | Mask strings like `******1492` are valid merchant signatures and can be labeled once. |

## Index

| # | File | Phase | Builds |
|---|------|------|--------|
| 0 | [`00-architecture-overview.md`](./00-architecture-overview.md) | Reference | High-level architecture, data flow, tech stack, integration notes (Supabase, OpenRouter) |
| 1 | [`01-infrastructure-setup.md`](./01-infrastructure-setup.md) | Phase 1 | Monorepo, Docker Compose, Supabase project, env files, OpenRouter key |
| 2 | [`02-database-schema.md`](./02-database-schema.md) | Phase 2 | SQL schema, migrations, seed data, indexes, dedup constraints |
| 3 | [`03-pdf-parser.md`](./03-pdf-parser.md) | Phase 3 | PhonePe deterministic parser, edge cases, fixture testing |
| 4 | [`04-categorization-engine.md`](./04-categorization-engine.md) | Phase 4 | Normalizer, merchant rule-pack, transfer detection, LLM fallback |
| 5 | [`05-backend-api.md`](./05-backend-api.md) | Phase 5 | FastAPI app, password auth, endpoints, upload pipeline |
| 6 | [`06-frontend.md`](./06-frontend.md) | Phase 6 | React + TS + Tailwind, design system, Upload + Review pages |
| 7 | [`07-analytics-dashboard.md`](./07-analytics-dashboard.md) | Phase 7 | Dashboard + Analytics pages, aggregations, charts, LLM insights |
| 8 | [`08-deployment-polish.md`](./08-deployment-polish.md) | Phase 8 | Render + Vercel deploy, settings page, CSV export, polish |

Each phase doc has the same structure:

- **Goal** — what this phase delivers
- **Prerequisites** — what must be done before starting
- **Design** — detailed design, contracts, examples
- **Definition of done** — checklist to mark the phase complete
- **Risks / open questions** — anything to revisit

## How to use this design

- Phases 1 → 8 are **sequential**. Each phase produces a working slice that the next builds on.
- A phase is "done" when every item in its Definition of Done is checked.
- Do not skip phases. If something needs to move earlier (e.g., deployment before analytics), open an issue and update the affected docs first.
