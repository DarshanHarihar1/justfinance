"""Categorization service — rule-pack, structural rules, and OpenRouter fallback."""
from .batch import categorize, categorize_batch
from .normalize import collapse_trailing_code, normalize
from .own_accounts import detect_own_account_last4s
from .types import CategorizationResult

__all__ = [
    "CategorizationResult",
    "categorize",
    "categorize_batch",
    "collapse_trailing_code",
    "detect_own_account_last4s",
    "normalize",
]
