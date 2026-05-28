from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategorizationResult:
    category_id: int
    merchant_normalized: str | None
    is_manually_categorized: bool
    needs_review: bool
    source: str  # transfer | credit | mapping | llm | fallback
