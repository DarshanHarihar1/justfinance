from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("transaction_ref", name="uq_transactions_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), nullable=False
    )

    transaction_ref: Mapped[str] = mapped_column(String, nullable=False)
    utr_no: Mapped[str | None] = mapped_column(String, nullable=True)

    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    time: Mapped[dt.time | None] = mapped_column(Time, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    merchant_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    merchant_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    is_manually_categorized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[str | None] = mapped_column(String, nullable=True)
