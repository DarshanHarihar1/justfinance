from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import db_session, get_llm
from app.schemas.analytics import (
    AnswerOut,
    AskContext,
    AskIn,
    DashboardOut,
    InsightsIn,
    InsightsOut,
    MoMOut,
    TrendOut,
)
from app.services.analytics.dashboard import get_dashboard
from app.services.analytics.insights import answer_question, generate_insights
from app.services.analytics.mom import get_mom
from app.services.analytics.rate_limit import check_ask_rate_limit
from app.services.analytics.trends import get_trend
from app.services.llm.openrouter import OpenRouterClient

router = APIRouter()


@router.get("/dashboard/{month}/{year}", response_model=DashboardOut)
async def dashboard(
    month: int,
    year: int,
    db: AsyncSession = Depends(db_session),
) -> DashboardOut:
    return await get_dashboard(db, month=month, year=year)


@router.get("/mom", response_model=MoMOut)
async def month_over_month(
    db: AsyncSession = Depends(db_session),
) -> MoMOut:
    return await get_mom(db)


@router.get("/trends/{category_id}", response_model=TrendOut)
async def trends(
    category_id: int,
    from_param: str | None = Query(default=None, alias="from"),
    to_param: str | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(db_session),
) -> TrendOut:
    return await get_trend(
        db,
        category_id=category_id,
        from_param=from_param,
        to_param=to_param,
    )


@router.post("/insights", response_model=InsightsOut)
async def insights(
    body: InsightsIn,
    force: bool = Query(default=False),
    db: AsyncSession = Depends(db_session),
    llm: OpenRouterClient = Depends(get_llm),
) -> InsightsOut:
    return await generate_insights(
        db,
        llm=llm,
        month=body.month,
        year=body.year,
        force=force,
    )


@router.post("/ask", response_model=AnswerOut)
async def ask(
    body: AskIn,
    db: AsyncSession = Depends(db_session),
    llm: OpenRouterClient = Depends(get_llm),
) -> AnswerOut:
    check_ask_rate_limit()
    answer, aggregations = await answer_question(
        db,
        llm=llm,
        question=body.question.strip(),
        month=body.month,
        year=body.year,
    )
    return AnswerOut(
        answer=answer,
        context_used=AskContext(
            month=body.month,
            year=body.year,
            aggregations=aggregations,
        ),
    )
