"""Shared pytest fixtures.

Two flavors of fixture live here:

* The synchronous ``client`` fixture used by ``test_healthz``.
* A set of async DB fixtures (``db_engine``, ``db_session``) that apply
  ``supabase/migrations/`` and ``supabase/seed.sql`` to a real Postgres
  reachable at ``TEST_DATABASE_URL``. Tests that don't need a DB pay
  nothing for these.

If Postgres isn't reachable at the URL, the DB-using tests are skipped — not
failed — so the normalizer and healthz suites stay green on machines without
a database. The default URL points at the local cluster set up in the README.
"""
from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

os.environ.setdefault("SESSION_SECRET", "test-session-secret-with-sufficient-length")
os.environ.setdefault("APP_PASSWORD_HASH", bcrypt.hash("test-password"))

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://finance_test:finance_test@127.0.0.1:5432/finance_test"
)


def _postgres_reachable(url: str) -> bool:
    parsed = urlparse(url.replace("postgresql+asyncpg", "postgresql"))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


if _postgres_reachable(DEFAULT_TEST_DATABASE_URL):
    os.environ["DATABASE_URL"] = DEFAULT_TEST_DATABASE_URL

from app.main import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"
SEED_FILE = REPO_ROOT / "supabase" / "seed.sql"

TEST_PASSWORD = "test-password"


def _test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


async def _apply_sql_script(engine: AsyncEngine, sql: str) -> None:
    """Execute a multi-statement SQL script.

    asyncpg's prepared-statement API rejects multi-statement input; we need to
    use the simple-query protocol via ``asyncpg.Connection.execute()`` on the
    raw driver connection. Each script runs in its own transaction.
    """
    async with engine.connect() as conn:
        raw = await conn.get_raw_connection()
        driver_conn = raw.driver_connection  # asyncpg.Connection
        async with driver_conn.transaction():
            await driver_conn.execute(sql)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client: TestClient) -> TestClient:
    response = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 204
    return client


@pytest.fixture()
def requires_postgres() -> None:
    if not _postgres_reachable(_test_database_url()):
        pytest.skip(
            f"Postgres not reachable at {_test_database_url()}; "
            "set TEST_DATABASE_URL or start the local cluster."
        )


# ── DB fixtures ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """Session-scoped engine. Drops & rebuilds the schema once per pytest run.

    The fixture executes every ``supabase/migrations/000N_*.sql`` in order,
    then ``seed.sql``. We don't drop on teardown so that ``psql`` against the
    test DB after a run is useful for diagnostics.
    """
    url = _test_database_url()
    if not _postgres_reachable(url):
        pytest.skip(
            f"Postgres not reachable at {url}; "
            "set TEST_DATABASE_URL or start the local cluster."
        )

    engine = create_async_engine(url, future=True)

    await _apply_sql_script(
        engine,
        "DROP TABLE IF EXISTS transactions, statements, "
        "merchant_mappings, categories CASCADE;"
        "DROP FUNCTION IF EXISTS set_updated_at() CASCADE;",
    )
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        await _apply_sql_script(engine, migration.read_text(encoding="utf-8"))
    await _apply_sql_script(engine, SEED_FILE.read_text(encoding="utf-8"))

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Function-scoped session whose writes are rolled back at the end of the test.

    Implementation: open a fresh connection, ``BEGIN`` an outer transaction,
    bind an ``AsyncSession`` with ``join_transaction_mode='create_savepoint'``
    so the session's own commit/rollback only releases/rolls a SAVEPOINT.
    The outer transaction's rollback at teardown reverts everything regardless
    of what the test did.
    """
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()
