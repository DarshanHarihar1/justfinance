from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class MerchantMapping(Base, TimestampMixin):
    __tablename__ = "merchant_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_pattern: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
