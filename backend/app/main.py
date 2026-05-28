"""FastAPI application entrypoint."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import auth_router
from app.auth.middleware import SessionAuthMiddleware
from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.core.logging import configure_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import analytics, categories, mappings, statements, transactions
from app.services.llm.openrouter import OpenRouterClient

configure_logging()
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.llm = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=settings.openrouter_model_categorize,
        app_name=settings.openrouter_app_name,
        app_url=settings.openrouter_app_url,
    )
    log.info(
        "startup",
        cors_origins=settings.cors_origins,
        database_is_pooled=settings.database_is_pooled,
    )
    try:
        yield
    finally:
        await app.state.llm.aclose()
        await engine.dispose()
        log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Finance Tracker API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        SessionAuthMiddleware,
        settings=settings,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(statements.router, prefix="/api/statements", tags=["statements"])
    app.include_router(transactions.router, prefix="/api", tags=["transactions"])
    app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
    app.include_router(mappings.router, prefix="/api/mappings", tags=["mappings"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            return {"status": "degraded"}
        return {"status": "ok"}

    return app


app = create_app()
