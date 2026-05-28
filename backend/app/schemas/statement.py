from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class StatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_start: dt.date
    period_end: dt.date
    filename: str | None
    source: str
    uploaded_at: dt.datetime


class ParsedSummary(BaseModel):
    statement_id: int
    period_start: dt.date
    period_end: dt.date
    parsed_count: int
    new_count: int
    needs_review_count: int
    warnings: list[str]
