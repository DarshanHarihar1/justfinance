from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    statement_id: int
    transaction_ref: str
    utr_no: str | None
    date: dt.date
    time: dt.time | None
    description: str
    merchant_raw: str | None
    merchant_normalized: str | None
    amount: Decimal
    type: str
    category_id: int | None
    is_manually_categorized: bool
    needs_review: bool
    notes: str | None


class TransactionPatch(BaseModel):
    category_id: int | None = None
    notes: str | None = None
    remember: bool = False


class BulkCategorizeItem(BaseModel):
    transaction_id: int
    category_id: int
    remember: bool = False


class BulkCategorize(BaseModel):
    items: list[BulkCategorizeItem] = Field(min_length=1)


class PaginatedTransactions(BaseModel):
    items: list[TransactionOut]
    total: int
