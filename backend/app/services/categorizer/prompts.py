from __future__ import annotations

from typing import Any

LLM_BATCH_SIZE = 10
CONFIDENCE_THRESHOLD = 0.85


def build_system_prompt(category_names: tuple[str, ...]) -> str:
    allowed = ", ".join(category_names)
    return (
        "You are a personal-finance transaction categorizer for an Indian user. "
        "You receive a list of merchant names extracted from UPI bank statements. "
        "For each merchant, return the single best-fit category from this fixed list:\n"
        f"{allowed}.\n"
        "Use 'Others' if you are unsure. Use 'Transfers' only for inter-account transfers "
        "(never just because a name looks like a person). Be concise. Return JSON only."
    )


def build_user_prompt(merchants: list[str]) -> str:
    lines = "\n".join(f"- {merchant}" for merchant in merchants)
    return (
        "Categorize the following merchants. Return a JSON object with one entry per merchant "
        "in the same order. Each entry must have:\n"
        '- "merchant": the merchant string as given,\n'
        '- "category": one of the allowed categories,\n'
        '- "confidence": float between 0 and 1.\n\n'
        f"Merchants:\n{lines}"
    )


def build_response_schema(category_names: tuple[str, ...]) -> dict[str, Any]:
    count = len(category_names)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["results"],
        "properties": {
            "results": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["merchant", "category", "confidence"],
                    "properties": {
                        "merchant": {"type": "string"},
                        "category": {"type": "string", "enum": list(category_names)},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            }
        },
    }
