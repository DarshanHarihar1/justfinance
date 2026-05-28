from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, unprocessable
from app.schemas.analytics import InsightItem, InsightsOut
from app.services.llm.openrouter import OpenRouterClient, OpenRouterError

from .cache import (
    insights_cache_get,
    insights_cache_key_from_summary,
    insights_cache_set,
)
from .summary import build_spend_summary, summary_cache_key

INSIGHTS_SYSTEM = """You are a brief, plain-spoken personal-finance advisor for an Indian user.
You receive an aggregated monthly summary. Return 3–5 short insights.
Each insight has a 4–7 word title, a one-sentence body referencing concrete
numbers, and a severity (info, good, or concern). Avoid generic advice ("save more");
be specific about which category moved and by how much. Return JSON only."""


def _insights_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["insights"],
        "properties": {
            "insights": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "body", "severity"],
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["info", "good", "concern"],
                        },
                    },
                },
            }
        },
    }


async def generate_insights(
    db: AsyncSession,
    *,
    llm: OpenRouterClient,
    month: int,
    year: int,
    force: bool = False,
) -> InsightsOut:
    summary = await build_spend_summary(db, month=month, year=year)
    if summary.totals["expense"] == 0 and summary.totals["income"] == 0:
        return InsightsOut(
            generated_at=dt.datetime.now(dt.UTC).isoformat(),
            model="",
            insights=[],
        )

    summary_json = summary_cache_key(summary)
    cache_key = insights_cache_key_from_summary(summary_json)

    if not force:
        cached = insights_cache_get(cache_key)
        if cached is not None:
            return cached

    settings = get_settings()
    if not llm.enabled:
        raise AppError(
            503,
            "llm_unavailable",
            "Insights require an OpenRouter API key.",
        )

    user_payload = summary.model_dump(mode="json")
    try:
        result = await llm.chat_json(
            system=INSIGHTS_SYSTEM,
            user=json.dumps(user_payload, indent=2),
            schema=_insights_schema(),
            model=settings.openrouter_model_insights,
        )
    except OpenRouterError as exc:
        raise AppError(502, "llm_error", str(exc)) from exc

    items = [
        InsightItem.model_validate(item) for item in result.get("insights", [])
    ]
    if not items:
        raise unprocessable("empty_insights", "The model returned no insights.")

    out = InsightsOut(
        generated_at=dt.datetime.now(dt.UTC).isoformat(),
        model=settings.openrouter_model_insights,
        insights=items,
    )
    insights_cache_set(cache_key, out)
    return out


ASK_SYSTEM = """You are a helpful personal-finance assistant for an Indian user.
Answer using ONLY the aggregated numbers in the JSON context. Do not invent figures.
Keep answers concise (2–4 sentences), plain text, no markdown headings."""


def _ask_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["answer"],
        "properties": {"answer": {"type": "string"}},
    }


async def answer_question(
    db: AsyncSession,
    *,
    llm: OpenRouterClient,
    question: str,
    month: int,
    year: int,
) -> tuple[str, list[str]]:
    summary = await build_spend_summary(db, month=month, year=year)
    if summary.totals["expense"] == 0 and summary.totals["income"] == 0:
        raise unprocessable(
            "no_data",
            "No spending data for this month. Upload a statement first.",
        )

    settings = get_settings()
    if not llm.enabled:
        raise AppError(
            503,
            "llm_unavailable",
            "Ask requires an OpenRouter API key.",
        )

    aggregations = [
        "monthly income and expense totals",
        "expense by category",
        "previous month category comparison",
        "top merchants (business names only)",
    ]
    user = json.dumps(
        {
            "question": question,
            "context": summary.model_dump(mode="json"),
        },
        indent=2,
    )
    try:
        result = await llm.chat_json(
            system=ASK_SYSTEM,
            user=user,
            schema=_ask_schema(),
            model=settings.openrouter_model_insights,
        )
    except OpenRouterError as exc:
        raise AppError(502, "llm_error", str(exc)) from exc

    answer = str(result.get("answer", "")).strip()
    if not answer:
        raise unprocessable("empty_answer", "The model returned an empty answer.")
    return answer, aggregations
