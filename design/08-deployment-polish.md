# Phase 8 — Settings, Polish, Deployment

> Goal: ship it. Settings page (categories + mappings + CSV export + theme), final
> polish (loading/empty/error states across the app), and the production deploy to
> Render + Vercel + Supabase.

## Prerequisites

- Phases 1–7 complete and working locally.

## 8.1 Settings page

A single route, three sections side-by-side on desktop, stacked on mobile.

```
┌──────────────────────────────────────────────────────────────────┐
│ Settings                                                          │
│                                                                   │
│ Categories                                                        │
│ ───────────                                                       │
│ 🛒 Groceries        #4CAF50    18 mappings    [Edit] [Delete]    │
│ 🍔 Food & Dining    #FF9800    24 mappings    [Edit] [Delete]    │
│ ...                                                               │
│ [ + New category ]                                                │
│                                                                   │
│ Merchant mappings                                                 │
│ ────────────────                                                  │
│ Filter: [ All ▼ ]  [ source: any ▼ ]  [ search: ____ ]            │
│                                                                   │
│ SWIGGY              Food & Dining   seed     [Edit] [Delete]      │
│ ZEPTO MARKETPLACE   Groceries       seed     [Edit] [Delete]      │
│ ******1492          Transport       manual   [Edit] [Delete]      │
│ ...                                                               │
│                                                                   │
│ Export                                                            │
│ ──────                                                            │
│ [ Download all transactions (CSV) ]                               │
│                                                                   │
│ Appearance                                                        │
│ ──────────                                                        │
│ Theme:  ○ Light   ● Dark   ○ System                              │
└──────────────────────────────────────────────────────────────────┘
```

### Categories block

- Lists all categories from `GET /api/categories`, sorted by `sort_order`.
- The "N mappings" count comes from a join (`COUNT(mm.id) FROM categories LEFT JOIN merchant_mappings`), exposed as a `mapping_count` field on `CategoryOut`.
- `[Edit]` opens a dialog with: name, color (color picker → free-text hex), icon (emoji input), sort_order.
- `[Delete]` opens a confirmation dialog. If the category has any mappings or transactions, the dialog shows a "Move to" picker (required). Backend enforces this anyway (Phase 5 §5.5).
- `is_system = TRUE` categories show a small "System" label and the delete button is disabled.

### Merchant mappings block

- Paginated (50 per page).
- Filters: source (`all` / `seed` / `llm` / `manual`), category, free-text search on `merchant_pattern`.
- `[Edit]`: change the category. Editing flips `source` to `manual`.
- `[Delete]`: removes the row. The next time a matching merchant appears, it will go through the categorization flow again (LLM or manual review).
- A small "+ Add mapping" button opens a dialog where the user types a pattern and picks a category — useful for proactive learning.

### Export block

`[Download all transactions (CSV)]` calls a new endpoint:

```
GET /api/transactions/export.csv?from=YYYY-MM-DD&to=YYYY-MM-DD
```

CSV columns:

```
id, statement_id, date, time, description, merchant_raw, merchant_normalized,
amount, type, category, is_manually_categorized, needs_review, notes,
transaction_ref, utr_no
```

Streamed (`StreamingResponse`) with `text/csv` and `Content-Disposition: attachment; filename="transactions-YYYY-MM-DD.csv"`. Default range is "all time" if no query params.

### Appearance

A simple radio between Light / Dark / System. Theme is persisted in `localStorage`.
Implementation: a `<html class="dark" />` toggle plus `prefers-color-scheme` media query for "System". The dark token set in §6.1 covers everything.

## 8.2 Polish pass

A checklist applied across every screen before deploy:

### Loading

- [ ] Every page mount shows a skeleton, never a spinner on a full screen.
- [ ] Buttons that trigger network requests show an inline spinner inside the button (Lucide `Loader2 className="animate-spin"`).
- [ ] Tables use a single skeleton row template repeated 5×.

### Empty

- [ ] `/upload` with no prior statements: friendly first-time copy.
- [ ] `/review` with no needs_review: "You're all caught up. 🎉" (only emoji allowed in copy, per design language exception).
- [ ] `/dashboard` for a month with no data: prompt to upload.
- [ ] `/analytics` with no data: hidden, message "Upload a statement to see insights."
- [ ] `/settings` Mappings with empty filter results: "No mappings match your filter."

### Error

- [ ] Network errors surface a Sonner toast with a `Retry` action.
- [ ] 401 errors silently redirect to `/login`.
- [ ] 4xx errors from validation show the server's `message` if present, generic copy otherwise.
- [ ] An app-wide React error boundary renders a minimal "Something went wrong. [Reload]" card.

### Accessibility

- [ ] All interactive elements have an accessible name (icon-only buttons use `aria-label`).
- [ ] Focus rings are visible (`ring-2 ring-[--color-accent] ring-offset-2`).
- [ ] Color contrast meets WCAG AA against `--color-bg` for `--color-text` and `--color-text-muted`.
- [ ] The Review page is fully keyboard-operable.

### Performance

- [ ] Initial JS bundle ≤ 250 KB gzipped.
- [ ] Lighthouse mobile Performance ≥ 90 on `/dashboard`.
- [ ] Recharts is imported per-chart, not as the whole library (`import { PieChart, Pie } from "recharts"` is fine — it tree-shakes).
- [ ] React Query devtools removed from prod build (only included via `import.meta.env.DEV`).

### Copy

- [ ] No "transaction" jargon where "spending" or "money" works.
- [ ] Currency formatted via `formatINR` everywhere.
- [ ] Dates in user-readable form (`May 28`, not `2026-05-28`) except in tables where ISO is briefer.

## 8.3 Deployment — backend (Render)

Render free tier, web service from this repo.

### Build & start commands

- **Build**: `pip install -e .` (or `uv sync --frozen`)
- **Start**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`

Free tier only has 512 MB RAM so a single worker is right. `--workers 1` plus `--lifespan on` ensures the OpenRouter client and engine are reused.

### Environment variables (set in Render dashboard)

```
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:6543/postgres
DATABASE_IS_POOLED=true
APP_PASSWORD_HASH=$2b$12$...
SESSION_SECRET=<48 random bytes b64url>
SESSION_MAX_AGE=2592000
SESSION_COOKIE_SAMESITE=none
SESSION_COOKIE_SECURE=true
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL_CATEGORIZE=meta-llama/llama-3.3-70b-instruct:free
OPENROUTER_MODEL_INSIGHTS=deepseek/deepseek-r1:free
OPENROUTER_APP_NAME=finance-tracker
OPENROUTER_APP_URL=https://<your-frontend>.vercel.app
CORS_ORIGINS=https://<your-frontend>.vercel.app
LOG_LEVEL=INFO
```

### Health check

Render's health check path: `/healthz`.

### Cold-start mitigation

Free tier spins down after 15 min idle. There's no built-in cron on the free tier; we accept the cold start. Document the ~60s first-request behavior in the frontend's Upload page (Phase 6 §6.7).

If we ever want to keep it warm, a free GitHub Actions cron hitting `/healthz` every 14 minutes does the job — but that defeats the free-tier compute budget. Don't.

## 8.4 Deployment — frontend (Vercel)

Vercel project from this repo, root directory `frontend/`.

### Build

- **Install command**: `pnpm install --frozen-lockfile`
- **Build command**: `pnpm build`
- **Output directory**: `dist`

### Environment variables (Vercel project settings)

```
VITE_API_URL=https://<your-backend>.onrender.com
```

### `vercel.json`

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

(SPA fallback so direct navigation to `/dashboard` works.)

## 8.5 Deployment — database (Supabase)

One-time setup, in this order:

1. Create the Supabase project (note region — match Render region if possible).
2. From the SQL editor:
   - Apply `supabase/migrations/0001_initial.sql`.
   - Apply `supabase/migrations/0002_views.sql` (the `v_spend` view from Phase 7).
   - Apply `supabase/seed.sql`.
3. Verify with:
   ```sql
   SELECT count(*) FROM categories;            -- expect 16
   SELECT count(*) FROM merchant_mappings;     -- expect 80+
   ```
4. From **Project Settings → Database → Connection Pooling (Transaction)**, copy the connection string, convert to asyncpg form, set as `DATABASE_URL` in Render.

### Backups

Free tier has no PITR. The data is recoverable by re-uploading the source PDFs, so this is acceptable. If we ever care, the export-CSV path provides a manual full backup.

## 8.6 Post-deploy smoke test

Run through this manually after every deploy:

1. Visit the Vercel URL → redirects to `/login`.
2. Log in with the configured password.
3. Upload the sample PhonePe PDF. Wait for the categorization to complete.
4. Check `/review` — confirm any flagged transactions look reasonable.
5. Categorize one, with **Remember** on. Reload `/settings` → confirm the mapping appears.
6. Navigate to `/dashboard` — confirm totals render and the donut + bar chart appear.
7. Navigate to `/analytics` — confirm 3-5 insights render and "Ask" returns an answer.
8. Log out → confirm cookie is cleared and routes redirect to `/login`.

If any step fails, roll back to the prior Render and Vercel deploys (both keep deploy history).

## 8.7 README contents (for the repo)

The top-level README should cover:

1. One-paragraph description of the app.
2. Tech stack bullets (link to `design/00-architecture-overview.md`).
3. **Local development**: `cp .env.example .env`, set OpenRouter key, generate password hash + session secret, `docker compose up`.
4. **Production deploy**: link to `design/08-deployment-polish.md`.
5. **Project layout**: 5-line tree pointing to `backend/`, `frontend/`, `supabase/`, `design/`.

Keep it short. The design docs are the long-form spec.

## 8.8 Definition of done

- [ ] Settings page implements categories CRUD, mappings CRUD, CSV export, theme toggle.
- [ ] CSV export endpoint streams; tested with > 1 K rows.
- [ ] All polish checklist items in §8.2 are green.
- [ ] Render service is live, health check passing, accessible at the assigned URL.
- [ ] Vercel deploy is live; visiting it without a cookie redirects to login.
- [ ] Supabase prod DB has the migrations + seed applied; row counts match §8.5.
- [ ] End-to-end smoke test in §8.6 passes against prod.
- [ ] README is committed at the repo root.

## 8.9 Risks / open questions

- **Cross-site cookie compatibility.** Mobile Safari and other strict-cookie browsers can drop `SameSite=None` cookies in some flows. If observed, switch to a custom subdomain CNAME (e.g., `api.finance.example.com` for backend, `finance.example.com` for frontend) so cookies are first-party — out of scope but documented.
- **Supabase 1-week pause.** Monthly-use app will pause. First request after pause incurs ~5–10s wake-up in addition to Render's cold start. Communicated to user via the Upload page's pre-flight ping.
- **OpenRouter free model availability.** Free models rotate. Both `OPENROUTER_MODEL_CATEGORIZE` and `OPENROUTER_MODEL_INSIGHTS` are env vars so swapping requires only a Render env update. Maintain a short list of known-good substitutes in this file going forward.
- **Vercel free tier bandwidth.** 100 GB/month — fine for personal use. The app is mostly static after first load.
- **No CI in scope.** A GitHub Actions workflow that runs `pytest` + `pnpm build` on PRs is a nice-to-have but explicitly deferred to keep this phase shippable.
