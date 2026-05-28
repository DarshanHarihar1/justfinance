from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import MoMMonth, MoMOut

from .periods import month_label, trailing_months
from .queries import mom_raw


def _dec_str(value: Decimal) -> str:
    return format(value, "f")


async def get_mom(db: AsyncSession) -> MoMOut:
    today = dt.date.today()
    months = trailing_months(12, anchor=today)
    since = dt.date(months[0][0], months[0][1], 1)

    raw = await mom_raw(db, since=since)
    by_key = {(int(r["year"]), int(r["month"])): r for r in raw}

    out: list[MoMMonth] = []
    for year, month in months:
        row = by_key.get((year, month))
        if row:
            income = Decimal(str(row["income"]))
            expense = Decimal(str(row["expense"]))
        else:
            income = expense = Decimal("0")
        net = income - expense
        out.append(
            MoMMonth(
                month=month,
                year=year,
                label=month_label(year, month),
                income=_dec_str(income),
                expense=_dec_str(expense),
                net=_dec_str(net),
            )
        )
    return MoMOut(months=out)
