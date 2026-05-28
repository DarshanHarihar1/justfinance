from __future__ import annotations

import re
from datetime import date

from .types import LogicalRow

_PERIOD_RE = re.compile(
    r"^(?P<start>[A-Z][a-z]{2} \d{1,2}, \d{4})\s*-\s*"
    r"(?P<end>[A-Z][a-z]{2} \d{1,2}, \d{4})\s*$"
)

_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^Transaction Statement for "),
    re.compile(r"^Date Transaction Details Type Amount\s*$"),
    re.compile(r"^Page \d+ of \d+\s*$"),
    re.compile(r"^This is a system generated statement"),
    re.compile(r"^This is an automatically generated statement"),
    re.compile(r"https?://"),
    re.compile(r"^Do not fall prey"),
    re.compile(r"^The contents of this email"),
    re.compile(r"^Visit for PhonePe"),
    re.compile(r"^for Privacy Policy"),
    re.compile(r"^received this message by mistake"),
    re.compile(r"^errors in the statement at"),
    re.compile(r"^the recipient's details are corrected"),
    re.compile(r"^emails and calls"),
    re.compile(r"^-- \d+ of \d+ --\s*$"),
)


def _line_text(row: LogicalRow) -> str:
    return " ".join(part for part in (row.date, row.detail, row.amount) if part).strip()


def _is_noise(row: LogicalRow) -> bool:
    text = _line_text(row)
    if not text:
        return True
    return any(pattern.search(text) for pattern in _NOISE_PATTERNS)


def split_period_and_scrub(
    rows: list[LogicalRow],
) -> tuple[date | None, date | None, list[LogicalRow]]:
    """Drop page chrome and pull the statement period from the header."""
    from datetime import datetime

    period_start: date | None = None
    period_end: date | None = None
    clean: list[LogicalRow] = []

    for row in rows:
        if _is_noise(row):
            continue
        for candidate in (row.date, row.detail, _line_text(row)):
            if not candidate:
                continue
            match = _PERIOD_RE.match(candidate.strip())
            if match:
                period_start = datetime.strptime(match.group("start"), "%b %d, %Y").date()
                period_end = datetime.strptime(match.group("end"), "%b %d, %Y").date()
                break
        else:
            clean.append(row)
            continue

    return period_start, period_end, clean
