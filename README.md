# Finance Tracker

Self-hosted, single-user personal finance tracker. Upload PhonePe monthly
statement PDFs, auto-categorize transactions with a rule-pack + LLM fallback,
and browse monthly dashboards and trends.

The design is the source of truth — start at [`design/README.md`](./design/README.md)
and read [`design/00-architecture-overview.md`](./design/00-architecture-overview.md)
before touching code.

## Status

Phase 6 (frontend) — done. Login, upload, review flows with React Router and
TanStack Query. Dashboard, analytics, and settings are placeholders for later phases.

| Phase | Doc | Status |
|------:|------|--------|
| 1 | [`01-infrastructure-setup.md`](./design/01-infrastructure-setup.md) | done |
| 2 | [`02-database-schema.md`](./design/02-database-schema.md) | done |
| 3 | [`03-pdf-parser.md`](./design/03-pdf-parser.md) | done |
| 4 | [`04-categorization-engine.md`](./design/04-categorization-engine.md) | done |
| 5 | [`05-backend-api.md`](./design/05-backend-api.md) | done |
| 6 | [`06-frontend.md`](./design/06-frontend.md) | done |
| 7 | [`07-analytics-dashboard.md`](./design/07-analytics-dashboard.md) | not started |
| 8 | [`08-deployment-polish.md`](./design/08-deployment-polish.md) | not started |

## Local development

Prerequisites: Docker + Docker Compose.

```bash
cp .env.example .env

# Generate real values for the two secrets:
python -c "import secrets; print(secrets.token_urlsafe(48))"      # SESSION_SECRET
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"  # APP_PASSWORD_HASH

docker compose up --build
```

Then:

- Backend health: <http://localhost:8000/healthz>
- Frontend: <http://localhost:5173>
- Postgres: `localhost:5432` (user `postgres` / pw `postgres` / db `finance`)

To reset the database (drops the volume, re-runs migrations + seed):

```bash
docker compose down -v && docker compose up
```

### Running the backend without Docker

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Requires a Postgres reachable via `DATABASE_URL`.

### Running the frontend without Docker

```bash
cd frontend
pnpm install
pnpm dev
```

### Running the tests

The parser and categorizer unit suites run with no setup:

```bash
cd backend
uv run pytest tests/test_pdf_parser.py tests/test_categorizer_decision.py tests/test_openrouter.py -q
```

The remaining non-DB suites (`test_healthz`, `test_config`, `test_normalize`) also run with
no setup:

```bash
cd backend
uv run pytest -k "not test_schema"
```

The schema integration tests in `tests/test_schema.py` need a reachable
Postgres. They look for `TEST_DATABASE_URL`, falling back to
`postgresql+asyncpg://finance_test:finance_test@127.0.0.1:5432/finance_test`.
If nothing is listening at that URL, the tests are skipped (not failed).

One-time local setup (Ubuntu):

```bash
sudo apt-get install -y postgresql postgresql-contrib
sudo pg_ctlcluster 16 main start
sudo -u postgres psql -c "CREATE USER finance_test WITH PASSWORD 'finance_test' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE finance_test OWNER finance_test;"
```

Then `uv run pytest` runs the full suite. The `db_engine` fixture drops and
rebuilds the schema once per pytest session, so reruns are idempotent.

## Repository layout

```
finance-tracker/
├── backend/           FastAPI app (Python 3.12, SQLAlchemy async, asyncpg)
├── frontend/          React 18 + Vite 5 + TypeScript + Tailwind v4
├── supabase/
│   ├── migrations/    plain-SQL migrations, applied alphabetically on first DB boot
│   └── seed.sql       categories + merchant rule-pack
├── design/            decision-locked design docs — source of truth
├── docker-compose.yml dev-only stack (db + backend + frontend)
└── .env.example       every required env var documented
```

## Production setup

These steps are run **once** against the live Supabase + Render + Vercel + OpenRouter
accounts. None of the resulting values are committed; they live in dashboard envs
and (locally) a password manager.

### Supabase (Postgres)

1. In the Supabase dashboard, **New project**. Note the project ref and database password.
2. Open **Project Settings → Database → Connection Pooling**.
3. Copy the **Transaction** mode connection string (port `6543`, not direct `5432`).
4. Convert the scheme: replace `postgresql://` with `postgresql+asyncpg://`. The
   final URL looks like
   `postgresql+asyncpg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:6543/postgres`.
5. In Render, set `DATABASE_URL` to that URL and `DATABASE_IS_POOLED=true`.
   The backend's engine factory uses this flag to switch to `NullPool` and
   disable prepared statements — required against Supavisor.
6. Apply migrations: open the Supabase SQL editor and paste each
   `supabase/migrations/000N_*.sql` in order, then `supabase/seed.sql`.
   (Alternative: `supabase db push` if you wire up the CLI.)

Free-tier quirk: projects auto-pause after 7 days of inactivity. The first request
after a pause cold-starts the project; subsequent requests are normal.

### OpenRouter (LLM)

1. Sign up at <https://openrouter.ai>. Free tier needs no credit card.
2. **Keys → Create Key.** Store as `OPENROUTER_API_KEY` in Render.
3. **Settings → Privacy** — decide whether to opt into prompt logging by free
   providers. Phase 4 only sends merchant strings to the LLM (no amounts, no
   full transaction descriptions), but a one-time review here is sensible.

Free-tier limits in effect (May 2026): 20 req/min, 50 req/day under $10
lifetime credits. The categorization design (Phase 4) is built around these caps.

### Render (backend)

1. New **Web Service** → connect this repo → root directory `backend/`.
2. Set environment variables from `.env.example` (notably `DATABASE_URL`,
   `DATABASE_IS_POOLED=true`, `APP_PASSWORD_HASH`, `SESSION_SECRET`,
   `OPENROUTER_*`, `CORS_ORIGINS=https://<your-vercel-domain>`).
3. Build & run commands are baked into `backend/Dockerfile`.

### Vercel (frontend)

1. New project → import this repo → root directory `frontend/`.
2. Set `VITE_API_URL` to the Render backend URL.
3. Framework preset: **Vite**.

## License

See [`LICENSE`](./LICENSE).
