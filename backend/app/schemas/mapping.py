from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_pattern: str
    category_id: int
    source: str
    confidence: Decimal | None
    times_used: int
    last_used_at: dt.datetime | None


class MappingCreate(BaseModel):
    merchant_pattern: str = Field(min_length=1)
    category_id: int


class MappingPatch(BaseModel):
    merchant_pattern: str | None = Field(default=None, min_length=1)
    category_id: int | None = None


class PaginatedMappings(BaseModel):
    items: list[MappingOut]
    total: int
