from __future__ import annotations

import time

from app.core.exceptions import too_many_requests

_ASK_TIMESTAMPS: list[float] = []
_ASK_LIMIT = 5
_ASK_WINDOW_SECONDS = 60


def check_ask_rate_limit() -> None:
    now = time.time()
    cutoff = now - _ASK_WINDOW_SECONDS
    while _ASK_TIMESTAMPS and _ASK_TIMESTAMPS[0] < cutoff:
        _ASK_TIMESTAMPS.pop(0)
    if len(_ASK_TIMESTAMPS) >= _ASK_LIMIT:
        raise too_many_requests(
            "Too many questions. Try again in a minute.",
            retry_after=_ASK_WINDOW_SECONDS,
        )
    _ASK_TIMESTAMPS.append(now)
