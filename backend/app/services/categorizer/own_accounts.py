from __future__ import annotations

import re

_DEBITED_FROM_RE = re.compile(r"Debited from XX(\d{4})")


def detect_own_account_last4s(raw_text: str) -> set[str]:
    """Last-4 digits of accounts the user paid from in this statement."""
    return set(_DEBITED_FROM_RE.findall(raw_text))
