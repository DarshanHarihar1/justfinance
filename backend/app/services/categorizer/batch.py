from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm.openrouter import OpenRouterClient, OpenRouterError
from app.services.pdf_parser.types import ParsedTransaction

from .catalog import CategoryCatalog, load_category_catalog
from .decision import _mapping_hit, lookup_keys, resolve_without_llm
from .mappings import insert_llm_mapping, load_mapping_index, record_mapping_hit
from .prompts import (
    CONFIDENCE_THRESHOLD,
    LLM_BATCH_SIZE,
    build_response_schema,
    build_system_prompt,
    build_user_prompt,
)
from .types import CategorizationResult

log = logging.getLogger(__name__)


async def categorize(
    txn: ParsedTransaction,
    *,
    own_account_last4s: set[str],
    db: AsyncSession,
    llm: OpenRouterClient,
) -> CategorizationResult:
    results = await categorize_batch(
        [txn],
        own_account_last4s=own_account_last4s,
        db=db,
        llm=llm,
    )
    return results[0]


async def categorize_batch(
    txns: list[ParsedTransaction],
    *,
    own_account_last4s: set[str],
    db: AsyncSession,
    llm: OpenRouterClient,
) -> list[CategorizationResult]:
    if not txns:
        return []

    catalog = await load_category_catalog(db)
    mapping_index = await load_mapping_index(db)

    results: list[CategorizationResult | None] = [None] * len(txns)
    llm_queue: dict[str, list[int]] = {}

    for index, txn in enumerate(txns):
        resolved = resolve_without_llm(
            txn,
            own_account_last4s=own_account_last4s,
            catalog=catalog,
            mapping_index=mapping_index,
        )
        if resolved is not None:
            results[index] = resolved
            if resolved.source == "mapping" and txn.merchant_raw is not None:
                primary, collapsed = lookup_keys(txn.merchant_raw)
                hit = _mapping_hit(primary, collapsed, mapping_index)
                if hit is not None:
                    await record_mapping_hit(db, hit)
            continue

        primary, _ = lookup_keys(txn.merchant_raw)  # merchant_raw set when LLM needed
        llm_queue.setdefault(primary, []).append(index)

    if llm_queue:
        await _run_llm_batches(
            llm_queue,
            results=results,
            catalog=catalog,
            mapping_index=mapping_index,
            db=db,
            llm=llm,
        )

    finalized: list[CategorizationResult] = []
    for index, item in enumerate(results):
        if item is not None:
            finalized.append(item)
            continue
        finalized.append(
            CategorizationResult(
                category_id=catalog.others_id,
                merchant_normalized=lookup_keys(txns[index].merchant_raw or "")[0]
                if txns[index].merchant_raw
                else None,
                is_manually_categorized=False,
                needs_review=True,
                source="llm",
            )
        )
    return finalized


async def _run_llm_batches(
    llm_queue: dict[str, list[int]],
    *,
    results: list[CategorizationResult | None],
    catalog: CategoryCatalog,
    mapping_index: dict[str, int],
    db: AsyncSession,
    llm: OpenRouterClient,
) -> None:
    merchants = list(llm_queue.keys())
    if not llm.enabled:
        log.warning("openrouter_api_key_missing", merchant_count=len(merchants))
        return

    system = build_system_prompt(catalog.names)
    schema = build_response_schema(catalog.names)

    for offset in range(0, len(merchants), LLM_BATCH_SIZE):
        chunk = merchants[offset : offset + LLM_BATCH_SIZE]
        try:
            response = await llm.chat_json(
                system=system,
                user=build_user_prompt(chunk),
                schema=schema,
            )
        except OpenRouterError:
            log.exception("openrouter_batch_failed", merchants=chunk)
            continue

        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            log.warning("openrouter_invalid_results", merchants=chunk)
            continue

        by_merchant = {
            item["merchant"]: item
            for item in raw_results
            if isinstance(item, dict) and isinstance(item.get("merchant"), str)
        }

        for merchant in chunk:
            item = by_merchant.get(merchant)
            if item is None:
                log.warning("openrouter_merchant_mismatch", merchant=merchant)
                continue

            category_name = item.get("category")
            confidence_raw = item.get("confidence")
            if not isinstance(category_name, str) or not isinstance(
                confidence_raw, (int, float)
            ):
                continue

            confidence = Decimal(str(confidence_raw))
            category_id = catalog.id_for(category_name) or catalog.others_id
            high_confidence = float(confidence_raw) >= CONFIDENCE_THRESHOLD

            if high_confidence and catalog.id_for(category_name) is not None:
                await insert_llm_mapping(
                    db,
                    merchant_pattern=merchant,
                    category_id=category_id,
                    confidence=confidence.quantize(Decimal("0.01")),
                )
                mapping_index[merchant] = category_id

            result = CategorizationResult(
                category_id=category_id,
                merchant_normalized=merchant,
                is_manually_categorized=False,
                needs_review=not high_confidence,
                source="llm",
            )
            for index in llm_queue[merchant]:
                results[index] = result

    await db.flush()
