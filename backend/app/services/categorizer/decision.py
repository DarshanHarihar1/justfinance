from __future__ import annotations

import re

from app.services.pdf_parser.types import ParsedTransaction

from .catalog import CategoryCatalog
from .normalize import collapse_trailing_code, normalize
from .types import CategorizationResult

_SELF_TRANSFER_RE = re.compile(r"^X{4,}(\d{4})$")


def lookup_keys(merchant_raw: str) -> tuple[str, str]:
    primary = normalize(merchant_raw)
    collapsed = collapse_trailing_code(primary)
    return primary, collapsed


def is_self_transfer(merchant_raw: str | None, own_account_last4s: set[str]) -> bool:
    if not merchant_raw:
        return False
    match = _SELF_TRANSFER_RE.match(merchant_raw)
    if not match:
        return False
    return match.group(1) in own_account_last4s


def resolve_without_llm(
    txn: ParsedTransaction,
    *,
    own_account_last4s: set[str],
    catalog: CategoryCatalog,
    mapping_index: dict[str, int],
) -> CategorizationResult | None:
    """Return a result when steps 1–5 finish; ``None`` means queue for LLM."""
    if is_self_transfer(txn.merchant_raw, own_account_last4s):
        return CategorizationResult(
            category_id=catalog.transfers_id,
            merchant_normalized=_normalized_or_none(txn.merchant_raw),
            is_manually_categorized=False,
            needs_review=False,
            source="transfer",
        )

    if txn.type == "credit":
        return CategorizationResult(
            category_id=catalog.others_id,
            merchant_normalized=_normalized_or_none(txn.merchant_raw),
            is_manually_categorized=False,
            needs_review=True,
            source="credit",
        )

    if txn.merchant_raw is None:
        return CategorizationResult(
            category_id=catalog.others_id,
            merchant_normalized=None,
            is_manually_categorized=False,
            needs_review=True,
            source="fallback",
        )

    primary, collapsed = lookup_keys(txn.merchant_raw)
    hit_pattern = _mapping_hit(primary, collapsed, mapping_index)
    if hit_pattern is not None:
        return CategorizationResult(
            category_id=mapping_index[hit_pattern],
            merchant_normalized=primary,
            is_manually_categorized=False,
            needs_review=False,
            source="mapping",
        )

    return None


def _mapping_hit(
    primary: str,
    collapsed: str,
    mapping_index: dict[str, int],
) -> str | None:
    if primary in mapping_index:
        return primary
    if collapsed != primary and collapsed in mapping_index:
        return collapsed
    return None


def _normalized_or_none(merchant_raw: str | None) -> str | None:
    if merchant_raw is None:
        return None
    return normalize(merchant_raw)
