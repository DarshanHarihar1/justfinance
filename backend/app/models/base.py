"""SQLAlchemy declarative base + shared mixins.

The schema in ``supabase/migrations/0001_initial.sql`` is authoritative.
These models exist so the Python layer can talk to the same shape using
the SQLAlchemy 2.x typed mapper, but they intentionally do not own DDL —
no ``Base.metadata.create_all`` is ever called in production.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base. All models must inherit from this."""


class CreatedAtMixin:
    """``created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`` — shared by every table."""

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin):
    """Adds ``updated_at`` for tables whose rows mutate after insert.

    The actual update is driven by the Postgres trigger ``set_updated_at()``
    defined in the initial migration; ``server_onupdate`` tells SQLAlchemy to
    refresh the column after an UPDATE so model instances see the new value
    without a manual refresh.
    """

    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )
