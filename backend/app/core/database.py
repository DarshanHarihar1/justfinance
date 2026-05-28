"""SQLAlchemy async engine + session factory.

Phase 1 only constructs the engine; nothing reads from the DB yet. Phase 2 adds
models and migrations, Phase 5 adds request-scoped session dependencies.

The branching on ``DATABASE_IS_POOLED`` is the non-negotiable requirement from
``design/00-architecture-overview.md`` §4: against Supabase's Supavisor pooler
(transaction mode, port 6543) we must use ``NullPool`` and disable both the
SQLAlchemy and asyncpg prepared-statement caches, or asyncpg will raise
``prepared statement does not exist`` once the pooler reuses a backend.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings


def build_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()

    kwargs: dict[str, Any] = {"echo": False, "future": True}

    if settings.database_is_pooled:
        # External pooler (Supavisor): let *it* pool, and disable our caches.
        kwargs["poolclass"] = NullPool
        kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
    else:
        kwargs["pool_pre_ping"] = True

    return create_async_engine(settings.database_url, **kwargs)


engine: AsyncEngine = build_engine()
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)
