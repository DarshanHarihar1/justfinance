# Phase 1 — Infrastructure Setup

> Goal: a working monorepo where `docker compose up` boots Postgres, the FastAPI
> backend, and the React frontend, and where the prod Supabase + OpenRouter credentials
> are configured. No business logic yet; this is plumbing only.

## Prerequisites

- A GitHub repo (this one).
- A Supabase account (free tier).
- An OpenRouter account (free tier; no credit card required to start).

## 1.1 Repository layout

```
finance-tracker/
├── README.md
├── .editorconfig
├── .gitignore
├── docker-compose.yml             # Postgres + backend + frontend, dev only
├── .env.example                   # Single source of truth for required env vars
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml             # uv/poetry-managed
│   ├── uv.lock                    # or poetry.lock
│   ├── alembic.ini                # optional, only if migrations grow
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app, lifespan, middleware wiring
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings, reads from env
│   │   │   ├── database.py        # SQLAlchemy engine + session factory
│   │   │   ├── security.py        # password hashing + cookie signing
│   │   │   └── logging.py         # structlog config
│   │   ├── auth/                  # populated in Phase 5
│   │   ├── routers/               # populated in Phase 5
│   │   ├── services/              # populated in Phases 3–4
│   │   ├── models/                # populated in Phase 2
│   │   └── schemas/               # populated in Phase 5
│   └── tests/
│       ├── conftest.py
│       └── fixtures/
│           └── phonepe_sample.pdf # the uploaded PhonePe statement (read-only)
│
├── frontend/
│   ├── Dockerfile.dev
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/                 # populated in Phases 6–7
│       ├── components/
│       ├── lib/
│       │   └── api.ts             # typed fetch client (later in Phase 5/6)
│       └── styles/
│           └── globals.css
│
├── supabase/
│   ├── migrations/
│   │   └── 0001_initial.sql       # built in Phase 2
│   └── seed.sql                   # categories + merchant rule-pack
│
└── design/                         # this directory
```

Notes on tooling choices:

- **`uv`** (Astral) for the Python project. Faster than poetry, lockfile-friendly, works offline. Drop to plain `pip` + `requirements.txt` if `uv` is unavailable.
- **`pnpm`** for the frontend. Smaller install, content-addressed store.
- **`shadcn/ui`** is consumed via CLI (`pnpm dlx shadcn@latest add ...`) into `frontend/src/components/ui/`. It generates source files directly into the repo (no npm dependency on shadcn itself).

## 1.2 Environment variables

Single `.env.example` at the repo root. Both backend and frontend read from `.env` in dev (compose mounts only what each needs).

```bash
# ────────────────────────────────────────────────────────────────
# Database — Postgres (Docker in dev, Supabase Supavisor in prod)
# ────────────────────────────────────────────────────────────────
# Dev (docker-compose):
#   postgresql+asyncpg://postgres:postgres@db:5432/finance
# Prod (Supabase Supavisor, transaction mode, port 6543):
#   postgresql+asyncpg://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:6543/postgres
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/finance

# Set to "true" in prod to enable NullPool + disabled prepared statements.
DATABASE_IS_POOLED=false

# ────────────────────────────────────────────────────────────────
# Auth — single shared password gate
# ────────────────────────────────────────────────────────────────
# bcrypt hash of the shared password. Generate with:
#   python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"
APP_PASSWORD_HASH=$2b$12$replace_this_with_a_real_hash

# Long random string. Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
SESSION_SECRET=replace_with_secrets_token_urlsafe_48

# 30 days in seconds.
SESSION_MAX_AGE=2592000

# ────────────────────────────────────────────────────────────────
# OpenRouter
# ────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-v1-replace
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL_CATEGORIZE=meta-llama/llama-3.3-70b-instruct:free
OPENROUTER_MODEL_INSIGHTS=deepseek/deepseek-r1:free
# Optional but recommended — OpenRouter shows these in your dashboard.
OPENROUTER_APP_NAME=finance-tracker
OPENROUTER_APP_URL=http://localhost:5173

# ────────────────────────────────────────────────────────────────
# CORS — comma-separated list of allowed origins
# ────────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173

# ────────────────────────────────────────────────────────────────
# Frontend
# ────────────────────────────────────────────────────────────────
VITE_API_URL=http://localhost:8000
```

`.gitignore` must include `.env`, `.env.local`, `*.local.env`, `__pycache__/`, `node_modules/`, `dist/`, `.venv/`, `coverage/`.

## 1.3 Docker Compose (dev)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: finance
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./supabase/migrations:/docker-entrypoint-initdb.d/migrations:ro
      - ./supabase/seed.sql:/docker-entrypoint-initdb.d/zz_seed.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d finance"]
      interval: 3s
      timeout: 3s
      retries: 10

  backend:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/finance
      DATABASE_IS_POOLED: "false"
      CORS_ORIGINS: http://localhost:5173
    ports: ["8000:8000"]
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    env_file: .env
    environment:
      VITE_API_URL: http://localhost:8000
    ports: ["5173:5173"]
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: pnpm dev --host 0.0.0.0

volumes:
  pgdata:
```

Postgres-side migration loading:

- Files in `supabase/migrations/` are copied into `/docker-entrypoint-initdb.d/migrations/` on first DB boot.
- Postgres runs `*.sql` in `/docker-entrypoint-initdb.d/` alphabetically. The migration runner is intentionally simple: name files `0001_*.sql`, `0002_*.sql` etc.
- `zz_seed.sql` runs after all migrations because of the `zz_` prefix.
- The same migration files are applied to Supabase via the Supabase dashboard's SQL editor (or `supabase db push` if the CLI is set up).

## 1.4 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, reproducible installs.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/pyproject.toml` initial deps:

```toml
[project]
name = "finance-tracker-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.4",
  "sqlalchemy>=2.0.30",
  "asyncpg>=0.29",
  "pdfplumber>=0.11",
  "httpx>=0.27",
  "itsdangerous>=2.2",
  "passlib[bcrypt]>=1.7",
  "python-multipart>=0.0.9",
  "structlog>=24.1",
]

[dependency-groups]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "ruff>=0.5",
  "mypy>=1.10",
]
```

## 1.5 Frontend Dockerfile.dev

```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine
RUN corepack enable && corepack prepare pnpm@9 --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]
```

`frontend/package.json` initial deps (full list refined in Phase 6):

```json
{
  "name": "finance-tracker-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "@tanstack/react-query": "^5.51.0",
    "recharts": "^2.13.0",
    "lucide-react": "^0.430.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.2"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.4",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.4.41",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.9.0",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "@typescript-eslint/parser": "^8.0.0"
  }
}
```

## 1.6 Supabase project setup (prod only)

One-time setup steps, documented for the future-you:

1. In Supabase dashboard, create a new project. Note the project ref and database password.
2. From **Project Settings → Database**, copy the **Connection string** under "Connection Pooling → Transaction" (port 6543).
3. Convert it to asyncpg form: replace `postgresql://` with `postgresql+asyncpg://`.
4. Set `DATABASE_URL` and `DATABASE_IS_POOLED=true` in the Render environment.
5. Apply migrations: open the SQL editor in Supabase, paste contents of each `supabase/migrations/000N_*.sql` in order, then `supabase/seed.sql`.

## 1.7 OpenRouter setup (prod only)

1. Sign up at openrouter.ai. Free tier requires no card.
2. Create an API key from **Keys → Create Key**. Store as `OPENROUTER_API_KEY`.
3. From **Settings → Privacy**, decide whether to opt into prompt logging by free providers. For a personal finance tool, we keep prompts narrowly scoped to merchant names only (never transaction amounts or descriptions full text) — see Phase 4 for the prompt contract.

## 1.8 Definition of done

- [ ] Repo has the directory structure in §1.1.
- [ ] `.env.example` exists with every variable in §1.2.
- [ ] `.env` is in `.gitignore`.
- [ ] `docker compose up` brings up `db`, `backend`, `frontend`.
- [ ] `http://localhost:8000/healthz` returns `{"status":"ok"}` (minimal FastAPI route).
- [ ] `http://localhost:5173` shows a Vite default page (or our placeholder).
- [ ] `docker compose down -v && docker compose up` re-creates the DB from scratch with migrations + seed applied automatically.
- [ ] A Supabase project exists; its Supavisor pooler URL is recorded in a password manager (not committed).
- [ ] An OpenRouter API key exists and is recorded in a password manager.
- [ ] `backend/tests/fixtures/phonepe_sample.pdf` is committed (the uploaded sample is checked in as the canonical fixture for parser tests).

## 1.9 Risks / open questions

- **Supabase project pausing.** Free tier pauses after 7 days idle. The first request after pause will see a cold start. We accept this — monthly use case.
- **Render cold start.** ~60s on first request after 15-minute idle. Frontend should show an explicit "Waking up backend…" state on the first request after page load (handled in Phase 6).
- **bcrypt in `passlib`.** Newer passlib + bcrypt 4.x have an `AttributeError` issue around `__about__`. Pin `bcrypt<4.1` in `pyproject.toml` if it bites.
- **Tailwind v4** is in active development; if the CSS-first config is unstable, fall back to v3.
