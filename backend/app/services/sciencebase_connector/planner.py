from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_mcs_query(payload: dict[str, Any]) -> str:
    years = payload.get("years") or []
    base = payload.get("q") or "Mineral Commodity Summaries"
    if years:
        yr = " ".join(str(y) for y in years)
        base = f"{base} {yr}"
    commodity_keywords = [str(v).strip() for v in payload.get("commodity_keywords", []) if str(v).strip()]
    if commodity_keywords:
        base = f"{base} {' '.join(commodity_keywords)}"
    return base.strip()


def build_query_fingerprint(config: dict[str, Any]) -> str:
    payload = {
        "q": config.get("q"),
        "filters": config.get("filters", []),
        "scope_mode": config.get("scope_mode", "keyword_search"),
        "scope_values": config.get("scope_values", []),
        "configured_slices": config.get("configured_slices", []),
        "sort": config.get("sort", "title"),
        "order": config.get("order", "asc"),
        "page_size": config.get("page_size", 100),
        "partition_strategy": config.get("partition_strategy", "none"),
        "ordering_strategy": config.get("ordering_strategy", "item_id"),
        "conditional_request_policy": config.get("conditional_request_policy", "etag_then_last_modified"),
    }
    return stable_json_hash(payload)
