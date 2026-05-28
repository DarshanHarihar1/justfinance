from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.transaction import TransactionOut


def _decimal_str(value: Decimal) -> str:
    return format(value, "f")


class DashboardTotals(BaseModel):
    income: str
    expense: str
    net: str
    txn_count: int


class CategoryBreakdown(BaseModel):
    category_id: int
    name: str
    color: str
    total: str
    txn_count: int
    pct_of_expense: float


class TopMerchant(BaseModel):
    merchant_normalized: str
    total: str
    txn_count: int
    category_id: int


class DashboardOut(BaseModel):
    month: int
    year: int
    totals: DashboardTotals
    by_category: list[CategoryBreakdown]
    top_merchants: list[TopMerchant]
    recent_transactions: list[TransactionOut]
    needs_review_count: int


class MoMMonth(BaseModel):
    month: int
    year: int
    label: str
    income: str
    expense: str
    net: str


class MoMOut(BaseModel):
    months: list[MoMMonth]


class TrendCategory(BaseModel):
    id: int
    name: str
    color: str


class TrendMonthPoint(BaseModel):
    year: int
    month: int
    total: str
    txn_count: int


class TrendTopMerchant(BaseModel):
    merchant_normalized: str
    total: str


class TrendOut(BaseModel):
    category: TrendCategory
    months: list[TrendMonthPoint]
    top_merchants: list[TrendTopMerchant]


class InsightsIn(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class InsightItem(BaseModel):
    title: str
    body: str
    severity: Literal["info", "good", "concern"]


class InsightsOut(BaseModel):
    generated_at: str
    model: str
    insights: list[InsightItem]


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class AskContext(BaseModel):
    month: int
    year: int
    aggregations: list[str]


class AnswerOut(BaseModel):
    answer: str
    context_used: AskContext


class SpendSummaryCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    total: float
    txn_count: int
    pct: float


class SpendSummaryPayload(BaseModel):
    """PII-free payload sent to the LLM."""

    month: str
    totals: dict[str, float]
    by_category: list[SpendSummaryCategory]
    prev_month_by_category: list[SpendSummaryCategory]
    top_merchants: list[dict[str, str | float | int]]
