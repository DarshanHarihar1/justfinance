-- Seed data — categories + merchant rule-pack.
-- This file is intentionally a stub for Phase 1. It is mounted into the local
-- Postgres container at /docker-entrypoint-initdb.d/zz_seed.sql so it runs
-- alphabetically *after* every migration in supabase/migrations/.
--
-- Phase 2 (database-schema) populates the categories.
-- Phase 4 (categorization-engine) populates merchant_mappings with the rule-pack.

-- No-op for Phase 1 so the local DB boots cleanly.
SELECT 1;
