from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


_insights_cache: dict[str, _CacheEntry] = {}
_INSIGHTS_TTL_SECONDS = 24 * 60 * 60


def insights_cache_get(key: str) -> Any | None:
    entry = _insights_cache.get(key)
    if entry is None:
        return None
    if time.time() >= entry.expires_at:
        _insights_cache.pop(key, None)
        return None
    return entry.value


def insights_cache_set(key: str, value: Any) -> None:
    _insights_cache[key] = _CacheEntry(
        expires_at=time.time() + _INSIGHTS_TTL_SECONDS,
        value=value,
    )


def insights_cache_key_from_summary(summary_json: str) -> str:
    return hashlib.sha256(summary_json.encode()).hexdigest()
