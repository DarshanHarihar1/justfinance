"""Tests for ``app.services.categorizer.normalize``.

These tests pin the normalization contract described in
``design/04-categorization-engine.md`` §4.3 and enforce the Phase 2 invariant
that every seeded ``merchant_pattern`` survives the normalization round-trip.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.categorizer.normalize import collapse_trailing_code, normalize

SEED_SQL = Path(__file__).resolve().parents[2] / "supabase" / "seed.sql"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Plain casing + company suffix.
        ("Swiggy Ltd", "SWIGGY"),
        ("SWIGGY", "SWIGGY"),
        ("SWIGGY INSTAMART PRIVATE LIMITED", "SWIGGY INSTAMART"),
        # The truncation observed in the PhonePe sample fixture.
        ("Zepto Marketplace Private Limited", "ZEPTO MARKETPLACE"),
        ("Zepto Marketplace Private Limi", "ZEPTO MARKETPLACE"),
        ("ZEPTO MARKETPLACE PRIVATE LIMITED", "ZEPTO MARKETPLACE"),
        # No-op for already-canonical inputs.
        ("ZEPTONOW", "ZEPTONOW"),
        ("KAMAT CAFE & PASTRIES", "KAMAT CAFE & PASTRIES"),
        # Trailing branch qualifier dropped after " - ".
        ("Indian Oil Petrol Pump - Devaraj Enterprises", "INDIAN OIL PETROL PUMP"),
        # Embedded digit codes are preserved by ``normalize`` itself; the
        # follow-up ``collapse_trailing_code`` strips them.
        ("Zomato8759546", "ZOMATO8759546"),
        ("BMTC BUS KA57F3003", "BMTC BUS KA57F3003"),
        # Masked merchant strings (the structural transfer case) survive.
        ("******1492", "******1492"),
        ("XXXXXX8216", "XXXXXX8216"),
    ],
)
def test_normalize_examples(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("normalized", "expected"),
    [
        # Digits glued onto the end of a word.
        ("ZOMATO8759546", "ZOMATO"),
        # Separated alphanumeric code token.
        ("BMTC BUS KA57F3003", "BMTC BUS"),
        ("BMTC BUS KA41D2675", "BMTC BUS"),
        # Trailing digit-run only.
        ("UBER 99887766", "UBER"),
        # Digits in the middle of a word aren't trailing — leave alone.
        ("7988730342PTYES", "7988730342PTYES"),
        # Masked merchant: collapse would erase all letters → keep original.
        ("******1492", "******1492"),
        # Already-clean string is unchanged.
        ("SWIGGY", "SWIGGY"),
    ],
)
def test_collapse_trailing_code(normalized: str, expected: str) -> None:
    assert collapse_trailing_code(normalized) == expected


# ── Phase 2 round-trip property ─────────────────────────────────────────────

_VALUES_BLOCK_RE = re.compile(
    r"INSERT INTO merchant_mappings.*?FROM \(VALUES(?P<block>.*?)\) AS v",
    re.DOTALL,
)
_PATTERN_RE = re.compile(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")


def _extract_seed_patterns() -> list[str]:
    text = SEED_SQL.read_text(encoding="utf-8")
    match = _VALUES_BLOCK_RE.search(text)
    assert match is not None, (
        "Could not locate the merchant_mappings VALUES block in seed.sql"
    )
    return [m.group(1) for m in _PATTERN_RE.finditer(match.group("block"))]


def test_seed_has_minimum_rule_pack_size() -> None:
    patterns = _extract_seed_patterns()
    assert len(patterns) >= 80, (
        f"Phase 2 DoD requires >=80 seeded merchant mappings; found {len(patterns)}."
    )


def test_seed_patterns_are_unique() -> None:
    patterns = _extract_seed_patterns()
    duplicates = sorted({p for p in patterns if patterns.count(p) > 1})
    assert not duplicates, f"Duplicate seed patterns: {duplicates}"


def test_seed_patterns_round_trip() -> None:
    """Every seeded pattern must equal ``normalize(pattern)``.

    Without this, a runtime normalize() of the same merchant would produce a
    different string than the seeded row and the lookup would silently miss.
    """
    patterns = _extract_seed_patterns()
    mismatches = [(p, normalize(p)) for p in patterns if normalize(p) != p]
    assert not mismatches, (
        "These seeded patterns don't round-trip through normalize():\n"
        + "\n".join(f"  {raw!r} -> {norm!r}" for raw, norm in mismatches)
    )
