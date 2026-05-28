from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAtMixin


class Category(Base, CreatedAtMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False, default="#9E9E9E")
    icon: Mapped[str] = mapped_column(String, nullable=False, default="📦")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluded_from_spending: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
