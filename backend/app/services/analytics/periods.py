from __future__ import annotations

import calendar
import datetime as dt


def month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    start = dt.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = dt.date(year, month, last_day)
    return start, end


def month_label(year: int, month: int) -> str:
    return dt.date(year, month, 1).strftime("%b %Y")


def prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def trailing_months(count: int, *, anchor: dt.date | None = None) -> list[tuple[int, int]]:
    today = anchor or dt.date.today()
    y, m = today.year, today.month
    out: list[tuple[int, int]] = []
    for _ in range(count):
        out.append((y, m))
        y, m = prev_month(y, m)
    out.reverse()
    return out
