"""Unit tests for LLM prompt/schema helpers."""

from __future__ import annotations

from app.services.categorizer.prompts import LLM_BATCH_SIZE, build_response_schema


def test_response_schema_matches_merchant_batch_size() -> None:
    categories = ("Food & Dining", "Others", "Transfers")
    schema = build_response_schema(categories, merchant_count=3)
    results = schema["properties"]["results"]
    assert results["minItems"] == 3
    assert results["maxItems"] == 3


def test_response_schema_does_not_use_category_count() -> None:
    categories = tuple(f"Category {i}" for i in range(18))
    schema = build_response_schema(categories, merchant_count=5)
    results = schema["properties"]["results"]
    assert results["minItems"] == 5
    assert results["maxItems"] == 5
    assert results["maxItems"] != len(categories)


def test_response_schema_caps_at_llm_batch_size() -> None:
    categories = ("Others",)
    schema = build_response_schema(categories, merchant_count=99)
    results = schema["properties"]["results"]
    assert results["maxItems"] == LLM_BATCH_SIZE
    assert results["minItems"] == LLM_BATCH_SIZE
