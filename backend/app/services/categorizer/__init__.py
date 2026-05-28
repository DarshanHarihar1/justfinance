"""Categorization service.

Phase 2 ships only the merchant normalizer (used both by the seeded rule-pack
and, eventually, by the runtime categorization pipeline). Phase 4 will add
``categorize()``, ``categorize_batch()``, and the OpenRouter LLM fallback in
this same package.
"""
from .normalize import collapse_trailing_code, normalize

__all__ = ["collapse_trailing_code", "normalize"]
