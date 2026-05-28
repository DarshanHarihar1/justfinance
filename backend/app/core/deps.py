from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.llm.openrouter import OpenRouterClient


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db():
        yield session


def get_llm(request: Request) -> OpenRouterClient:
    return request.app.state.llm
