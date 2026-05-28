# Supabase / Postgres migrations and seed

This directory is the source of truth for the database schema. It contains:

| File | Purpose |
|------|---------|
| `migrations/0001_initial.sql` | Phase 2 schema. Tables, indexes, CHECK constraints, FKs, the `set_updated_at()` plpgsql function, and the two `BEFORE UPDATE` triggers that depend on it. |
| `seed.sql` | Default categories (16) and merchant rule-pack (100 patterns). Idempotent — every insert uses `ON CONFLICT DO NOTHING`. |

## Local dev

The dev `docker-compose.yml` mounts `migrations/` and `seed.sql` into the
Postgres container's `/docker-entrypoint-initdb.d/` directory. Postgres runs
`*.sql` files there alphabetically **on first boot only**, which is why:

- Migration files are named `000N_<slug>.sql` so they apply in order.
- `seed.sql` is mounted as `zz_seed.sql` so it runs *after* every migration.

To re-apply on a clean DB:

```bash
docker compose down -v && docker compose up
```

`down -v` drops the `pgdata` volume, which is the only way to trigger the
init scripts again.

## Production (Supabase)

There is no automated migration runner for prod in this phase. To apply:

1. Open the Supabase SQL editor for the project.
2. Paste the contents of each `migrations/000N_*.sql` in order.
3. Paste `seed.sql`.

Phase 8 (deployment) will revisit whether to wire up `supabase db push` or a
direct-`5432` `scripts/migrate.py`. For now, the design (architecture
overview §4) explicitly accepts manual SQL-editor application here.

## Adding a new migration

1. Pick the next number: `0002`, `0003`, …
2. Name it `000N_<short_slug>.sql` (lowercase, snake_case slug).
3. Make it idempotent **only if you can**: use `IF NOT EXISTS` for `CREATE`
   and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for column adds. Triggers
   and functions should use `CREATE OR REPLACE`. Otherwise rely on the fact
   that `docker compose down -v` is the only re-application path in dev.
4. Commit alongside the matching SQLAlchemy model change in
   `backend/app/models/`.

## Adding to the rule-pack

Every `merchant_pattern` in `seed.sql` must round-trip through
`app.services.categorizer.normalize.normalize()` — i.e.,
`normalize(pattern) == pattern`. The Phase 2 test
`backend/tests/test_normalize.py::test_seed_patterns_round_trip` enforces
this and will fail loudly on any new typo.

If you need to seed a pattern that the current normalizer would mangle, the
fix is to update the normalizer (in `04-categorization-engine.md` territory),
not to bend the seed file.
