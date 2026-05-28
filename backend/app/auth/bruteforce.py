from __future__ import annotations

import time
from collections import defaultdict

LOCKOUT_WINDOW_SECONDS = 300
_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = LOCKOUT_WINDOW_SECONDS

# In-process only — acceptable for single-user deployment.
_failures: dict[str, list[float]] = defaultdict(list)


def record_failed_attempt(client_ip: str) -> None:
    now = time.time()
    attempts = _failures[client_ip]
    attempts.append(now)
    _failures[client_ip] = [t for t in attempts if now - t < _WINDOW_SECONDS]


def is_locked_out(client_ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _failures.get(client_ip, []) if now - t < _WINDOW_SECONDS]
    _failures[client_ip] = attempts
    return len(attempts) >= _MAX_ATTEMPTS


def clear_attempts(client_ip: str) -> None:
    _failures.pop(client_ip, None)


def reset_all() -> None:
    """Test helper — clear in-process counters."""
    _failures.clear()
