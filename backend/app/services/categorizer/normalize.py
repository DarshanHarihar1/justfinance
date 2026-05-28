"""Merchant string normalization.

Single source of truth for the canonical form a merchant name is stored under.

Contract (design/04-categorization-engine.md §4.3):

- ``normalize(raw)`` returns an uppercased, stripped, suffix-free key.
- Every ``merchant_pattern`` in ``supabase/seed.sql`` is already in this form;
  the test ``test_seed_patterns_round_trip`` asserts ``normalize(p) == p``.
- ``collapse_trailing_code(normalized)`` is a *second-pass* helper applied only
  when an initial lookup miss happens, to catch merchants like
  ``ZOMATO8759546`` → ``ZOMATO`` without permanently destroying the embedded
  code (which the caller may still want for traceability).

This module is intentionally pure: no DB, no network, no logging. Phase 4
wires the categorization pipeline on top of these helpers.
"""
from __future__ import annotations

import re

_TXN_REF_RE = re.compile(r"#\S+")
_UPI_HANDLE_RE = re.compile(r"@\w+")
_EMBEDDED_DATE_RE = re.compile(r"\d{2}[-/]\d{2}[-/]\d{2,4}")
_TXN_SUFFIX_RE = re.compile(r"\bTXN[-_]\S+", flags=re.IGNORECASE)
_DISALLOWED_CHARS_RE = re.compile(r"[^\w \-\*\.\&]")
_WHITESPACE_RE = re.compile(r"\s+")
_LETTER_RE = re.compile(r"[A-Z]")

# Order matters: longest first, so "PRIVATE LIMITED" wins over "LIMITED".
_COMPANY_SUFFIXES: tuple[str, ...] = (
    "PRIVATE LIMITED",
    "PVT LTD",
    "PVT. LTD.",
    "PVT. LTD",
    "LIMITED",
    "PRIVATE LIMI",  # observed truncation in the PhonePe sample
    "LTD",
    "LLP",
    "INC",
    "CORP",
    "CORPORATION",
    "COMPANY",
    "CO",
)


def normalize(merchant_raw: str) -> str:
    """Return the canonical lookup key for a raw merchant string."""
    s = merchant_raw

    s = _TXN_REF_RE.sub("", s)
    s = _UPI_HANDLE_RE.sub("", s)
    s = _EMBEDDED_DATE_RE.sub("", s)
    s = _TXN_SUFFIX_RE.sub("", s)

    up = s.upper()
    for suf in _COMPANY_SUFFIXES:
        if up.endswith(" " + suf):
            up = up[: -(len(suf) + 1)]
        elif up == suf:
            up = ""

    # Drop trailing branch/location qualifiers separated by " - ".
    up = up.split(" - ", 1)[0]

    up = _DISALLOWED_CHARS_RE.sub("", up)
    up = _WHITESPACE_RE.sub(" ", up).strip(" .-&")
    return up


# Matches a trailing alphanumeric "code" in two structural forms:
#   (a) a separate token after whitespace:  "... KA57F3003"  → strip " KA57F3003"
#   (b) digits glued onto the end of a word: "ZOMATO8759546" → strip "8759546"
# Both branches require >=4 trailing digits, which is the design's threshold.
_TRAILING_CODE_RE = re.compile(
    r"(?:\s+\b[A-Z0-9]*\d{4,}\b|(?<=[A-Z])\d{4,})\s*$"
)


def collapse_trailing_code(normalized: str) -> str:
    """Strip a trailing alphanumeric code (>=4 digits) from a normalized key.

    Use after a primary ``merchant_mappings`` lookup misses, never destructively:
    callers must keep the un-collapsed form in the ``merchant_normalized``
    column so the user can still see what was on the statement.

    Guard: if stripping would erase every letter (e.g. masked merchants like
    ``******1492``), we return the original unchanged. The design treats
    masked strings as valid merchant signatures the user labels once — see
    ``design/00-architecture-overview.md`` decision #12.

    Note: this function will *not* preserve ``XXXXXX1234``-style strings,
    because they're self-transfer markers caught by step 1 of the
    categorization flow *before* ``collapse_trailing_code`` is ever called.
    """
    candidate = _TRAILING_CODE_RE.sub("", normalized).strip()
    if not candidate or not _LETTER_RE.search(candidate):
        return normalized
    return candidate
