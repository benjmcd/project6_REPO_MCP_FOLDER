from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from app.services import nrc_aps_content_index


APS_EVIDENCE_BUNDLE_SCHEMA_ID = "aps.evidence_bundle.v1"
APS_EVIDENCE_BUNDLE_FAILURE_SCHEMA_ID = "aps.evidence_bundle_failure.v1"
APS_EVIDENCE_BUNDLE_GATE_SCHEMA_ID = "aps.evidence_bundle_gate.v1"
APS_EVIDENCE_BUNDLE_SCHEMA_VERSION = 1

APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID = "aps_evidence_request_norm_v1"
APS_EVIDENCE_RANKING_CONTRACT_ID = "aps_evidence_ranking_v1"
APS_EVIDENCE_SNIPPET_CONTRACT_ID = "aps_evidence_snippet_v1"
APS_EVIDENCE_SNAPSHOT_CONTRACT_ID = "aps_evidence_snapshot_v1"

APS_CONTENT_CONTRACT_ID = nrc_aps_content_index.APS_CONTENT_CONTRACT_ID
APS_CHUNKING_CONTRACT_ID = nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID
APS_NORMALIZATION_CONTRACT_ID = nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID

APS_MODE_QUERY = "query"
APS_MODE_BROWSE = "browse"

APS_QUERY_DEFAULT_LIMIT = 20
APS_QUERY_MAX_LIMIT = 100
APS_BROWSE_DEFAULT_LIMIT = 50
APS_BROWSE_MAX_LIMIT = 200

APS_MAX_QUERY_CHARS = 512
APS_MAX_QUERY_TOKENS = 32
APS_MAX_BUNDLE_CHUNKS = 5000
APS_MAX_BUNDLE_BYTES = 16 * 1024 * 1024

APS_SNIPPET_PRE_CHARS = 80
APS_SNIPPET_POST_CHARS = 80

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_INVALID_QUERY = "invalid_query"
APS_RUNTIME_FAILURE_UNKNOWN_CONTRACT_ID = "unknown_contract_id"
APS_RUNTIME_FAILURE_SNAPSHOT_UNAVAILABLE = "snapshot_state_unavailable"
APS_RUNTIME_FAILURE_SIZE_LIMIT = "bundle_size_limit_exceeded"
APS_RUNTIME_FAILURE_PROVENANCE_MISSING = "provenance_ref_missing"
APS_RUNTIME_FAILURE_PROVENANCE_UNRESOLVABLE = "provenance_ref_unresolvable"
APS_RUNTIME_FAILURE_ORDERING_VIOLATION = "ordering_contract_violation"
APS_RUNTIME_FAILURE_SNIPPET_BOUNDS = "snippet_bounds_violation"
APS_RUNTIME_FAILURE_WRITE_FAILED = "bundle_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_assembly_error"

APS_RUNTIME_FAILURE_CODES = {
    APS_RUNTIME_FAILURE_INVALID_REQUEST,
    APS_RUNTIME_FAILURE_INVALID_QUERY,
    APS_RUNTIME_FAILURE_UNKNOWN_CONTRACT_ID,
    APS_RUNTIME_FAILURE_SNAPSHOT_UNAVAILABLE,
    APS_RUNTIME_FAILURE_SIZE_LIMIT,
    APS_RUNTIME_FAILURE_PROVENANCE_MISSING,
    APS_RUNTIME_FAILURE_PROVENANCE_UNRESOLVABLE,
    APS_RUNTIME_FAILURE_ORDERING_VIOLATION,
    APS_RUNTIME_FAILURE_SNIPPET_BOUNDS,
    APS_RUNTIME_FAILURE_WRITE_FAILED,
    APS_RUNTIME_FAILURE_INTERNAL,
}

APS_GATE_FAILURE_MISSING_REF = "missing_bundle_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_bundle_ref"
APS_GATE_FAILURE_BUNDLE_SCHEMA = "bundle_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "bundle_failure_schema_mismatch"
APS_GATE_FAILURE_UNKNOWN_CONTRACT = "unknown_contract_id"
APS_GATE_FAILURE_REQUEST_IDENTITY = "request_identity_mismatch"
APS_GATE_FAILURE_MISSING_PROVENANCE = "missing_provenance_ref"
APS_GATE_FAILURE_UNRESOLVABLE_PROVENANCE = "unresolvable_provenance_ref"
APS_GATE_FAILURE_ORDERING_DRIFT = "ordering_drift_detected"
APS_GATE_FAILURE_SNIPPET_BOUNDS = "snippet_out_of_bounds"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE = "artifact_db_divergence"

APS_GATE_FAILURE_CODES = {
    APS_GATE_FAILURE_MISSING_REF,
    APS_GATE_FAILURE_UNRESOLVABLE_REF,
    APS_GATE_FAILURE_BUNDLE_SCHEMA,
    APS_GATE_FAILURE_FAILURE_SCHEMA,
    APS_GATE_FAILURE_UNKNOWN_CONTRACT,
    APS_GATE_FAILURE_REQUEST_IDENTITY,
    APS_GATE_FAILURE_MISSING_PROVENANCE,
    APS_GATE_FAILURE_UNRESOLVABLE_PROVENANCE,
    APS_GATE_FAILURE_ORDERING_DRIFT,
    APS_GATE_FAILURE_SNIPPET_BOUNDS,
    APS_GATE_FAILURE_CHECKSUM,
    APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE,
}

APS_REQUIRED_PROVENANCE_FIELDS = (
    "content_units_ref",
    "normalized_text_ref",
    "blob_ref",
    "download_exchange_ref",
    "discovery_ref",
    "selection_ref",
)


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def compute_bundle_checksum(payload: dict[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("bundle_checksum", None)
    clean.pop("_bundle_ref", None)
    clean.pop("_persisted", None)
    return stable_hash(clean)


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def compact_bundle_file_token(value: str) -> str:
    normalized = safe_path_token(value)
    if len(normalized) <= 32:
        return normalized
    return f"{normalized[:16]}_{normalized[-12:]}"


def expected_bundle_file_name(*, scope: str, bundle_id: str) -> str:
    return f"{safe_path_token(scope)}_{compact_bundle_file_token(str(bundle_id or '').strip())}_aps_evidence_bundle_v1.json"


def expected_failure_file_name(*, scope: str, bundle_id: str) -> str:
    return f"{safe_path_token(scope)}_{compact_bundle_file_token(str(bundle_id or '').strip())}_aps_evidence_bundle_failure_v1.json"


def _normalize_text_for_tokens(value: Any) -> str:
    normalized = unicodedata.normalize("NFC", str(value or "")).lower()
    translated = "".join(char if char.isalnum() else " " for char in normalized)
    return " ".join(translated.split())


def tokenize_query(value: Any) -> list[str]:
    collapsed = _normalize_text_for_tokens(value)
    return collapsed.split(" ") if collapsed else []


def normalize_query_tokens(value: Any) -> list[str]:
    tokens = tokenize_query(value)
    return sorted(list(dict.fromkeys(tokens)))


def token_frequencies(text: str) -> Counter[str]:
    return Counter(tokenize_query(text))


def _normalize_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = [value]
    normalized = sorted(list(dict.fromkeys([str(item).strip() for item in items if str(item).strip()])))
    return normalized or None


def _normalize_contract_id(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _resolve_filters(payload: dict[str, Any]) -> dict[str, Any]:
    raw_filters = payload.get("filters")
    filters = dict(raw_filters) if isinstance(raw_filters, dict) else {}
    return {
        "accession_numbers": _normalize_string_list(filters.get("accession_numbers", payload.get("accession_numbers"))),
        "content_ids": _normalize_string_list(filters.get("content_ids", payload.get("content_ids"))),
        "target_ids": _normalize_string_list(filters.get("target_ids", payload.get("target_ids"))),
        "content_contract_id": _normalize_contract_id(filters.get("content_contract_id", payload.get("content_contract_id"))),
        "chunking_contract_id": _normalize_contract_id(filters.get("chunking_contract_id", payload.get("chunking_contract_id"))),
        "normalization_contract_id": _normalize_contract_id(
            filters.get("normalization_contract_id", payload.get("normalization_contract_id"))
        ),
    }


def resolve_limit_offset(*, mode: str, limit_value: Any, offset_value: Any) -> tuple[int, int]:
    if str(mode or APS_MODE_BROWSE) == APS_MODE_QUERY:
        default_limit = APS_QUERY_DEFAULT_LIMIT
        max_limit = APS_QUERY_MAX_LIMIT
    else:
        default_limit = APS_BROWSE_DEFAULT_LIMIT
        max_limit = APS_BROWSE_MAX_LIMIT

    raw_limit = default_limit if limit_value is None else limit_value
    raw_offset = 0 if offset_value is None else offset_value

    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ValueError("invalid_limit") from None
    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        raise ValueError("invalid_offset") from None

    if limit < 1 or limit > max_limit:
        raise ValueError("invalid_limit")
    if offset < 0:
        raise ValueError("invalid_offset")
    return limit, offset


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)

    query_value = payload.get("query")
    query_text = "" if query_value is None else str(query_value)
    if len(query_text) > APS_MAX_QUERY_CHARS:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_QUERY)

    query_tokens = normalize_query_tokens(query_text)
    if len(query_tokens) > APS_MAX_QUERY_TOKENS:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_QUERY)

    filters = _resolve_filters(payload)
    has_structural_scope = bool(
        run_id
        or filters.get("accession_numbers")
        or filters.get("content_ids")
        or filters.get("target_ids")
        or filters.get("content_contract_id")
        or filters.get("chunking_contract_id")
        or filters.get("normalization_contract_id")
    )

    if query_tokens:
        mode = APS_MODE_QUERY
    elif has_structural_scope:
        mode = APS_MODE_BROWSE
    else:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_QUERY)

    limit, offset = resolve_limit_offset(
        mode=mode,
        limit_value=payload.get("limit"),
        offset_value=payload.get("offset", 0),
    )

    normalized_query = " ".join(query_tokens) if query_tokens else None
    normalized = {
        "mode": mode,
        "run_id": run_id,
        "query": normalized_query,
        "query_tokens": query_tokens,
        "filters": filters,
        "limit": limit,
        "offset": offset,
        "persist_bundle": bool(payload.get("persist_bundle", False)),
        "request_normalization_contract_id": APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID,
    }
    normalized.update(filters)
    return normalized


def request_identity_payload(normalized_request: dict[str, Any]) -> dict[str, Any]:
    filters = dict(normalized_request.get("filters") or {})
    return {
        "mode": str(normalized_request.get("mode") or ""),
        "run_id": str(normalized_request.get("run_id") or ""),
        "query": normalized_request.get("query"),
        "query_tokens": list(normalized_request.get("query_tokens") or []),
        "filters": {
            "accession_numbers": list(filters.get("accession_numbers") or []) or None,
            "content_ids": list(filters.get("content_ids") or []) or None,
            "target_ids": list(filters.get("target_ids") or []) or None,
            "content_contract_id": filters.get("content_contract_id"),
            "chunking_contract_id": filters.get("chunking_contract_id"),
            "normalization_contract_id": filters.get("normalization_contract_id"),
        },
        "request_normalization_contract_id": APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID,
    }


def request_identity_hash(normalized_request: dict[str, Any]) -> str:
    return stable_hash(request_identity_payload(normalized_request))


def derive_bundle_id(*, request_identity_hash_value: str, index_state_hash: str) -> str:
    raw = f"{APS_EVIDENCE_BUNDLE_SCHEMA_ID}:{str(request_identity_hash_value)}:{str(index_state_hash)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_failure_bundle_id(*, request_identity_hash_value: str) -> str:
    raw = f"{APS_EVIDENCE_BUNDLE_FAILURE_SCHEMA_ID}:{str(request_identity_hash_value)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _group_key_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "content_id": str(item.get("content_id") or ""),
        "run_id": str(item.get("run_id") or ""),
        "target_id": str(item.get("target_id") or ""),
        "accession_number": str(item.get("accession_number") or "").strip() or None,
        "content_contract_id": str(item.get("content_contract_id") or ""),
        "chunking_contract_id": str(item.get("chunking_contract_id") or ""),
    }


def group_id_for_item(item: dict[str, Any]) -> str:
    return stable_hash(_group_key_payload(item))


def _query_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -int(item.get("matched_unique_query_terms") or 0),
        -int(item.get("summed_term_frequency") or 0),
        int(item.get("chunk_length") or len(str(item.get("chunk_text") or ""))),
        str(item.get("content_id") or ""),
        int(item.get("chunk_ordinal") or 0),
        str(item.get("run_id") or ""),
        str(item.get("target_id") or ""),
        str(item.get("chunk_id") or ""),
    )


def _browse_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(item.get("content_id") or ""),
        int(item.get("chunk_ordinal") or 0),
        str(item.get("run_id") or ""),
        str(item.get("target_id") or ""),
        str(item.get("chunk_id") or ""),
    )


def ordered_items(items: list[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    key_fn = _query_sort_key if str(mode or APS_MODE_BROWSE) == APS_MODE_QUERY else _browse_sort_key
    return [dict(item) for item in sorted((dict(item) for item in items), key=key_fn)]


def is_ordering_deterministic(items: list[dict[str, Any]], *, mode: str) -> bool:
    actual = [(item.get("content_id"), item.get("chunk_id"), item.get("run_id"), item.get("target_id")) for item in items]
    expected_items = ordered_items(items, mode=mode)
    expected = [
        (item.get("content_id"), item.get("chunk_id"), item.get("run_id"), item.get("target_id"))
        for item in expected_items
    ]
    return actual == expected


def grouped_page(items: list[dict[str, Any]], *, mode: str) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    for item in ordered_items(items, mode=mode):
        group_id = str(item.get("group_id") or group_id_for_item(item))
        if group_id not in seen:
            seed = _group_key_payload(item)
            group = {
                "group_id": group_id,
                "content_id": seed["content_id"],
                "run_id": seed["run_id"],
                "target_id": seed["target_id"],
                "accession_number": seed["accession_number"],
                "content_contract_id": seed["content_contract_id"],
                "chunking_contract_id": seed["chunking_contract_id"],
                "chunk_count": 0,
                "chunks": [],
            }
            seen[group_id] = group
            groups.append(group)
        seen[group_id]["chunks"].append(dict(item))
        seen[group_id]["chunk_count"] = len(seen[group_id]["chunks"])
    return groups


def total_group_count(items: list[dict[str, Any]]) -> int:
    return len({str(item.get("group_id") or group_id_for_item(item)) for item in items})


def missing_provenance_fields(item: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in APS_REQUIRED_PROVENANCE_FIELDS:
        value = str(item.get(field) or "").strip()
        if not value:
            missing.append(field)
    return missing


def unresolvable_provenance_fields(item: dict[str, Any]) -> list[str]:
    unresolved: list[str] = []
    for field in APS_REQUIRED_PROVENANCE_FIELDS:
        value = str(item.get(field) or "").strip()
        if value and not Path(value).exists():
            unresolved.append(field)
    return unresolved


def validate_known_contract_ids(item: dict[str, Any]) -> bool:
    return (
        str(item.get("content_contract_id") or "") == APS_CONTENT_CONTRACT_ID
        and str(item.get("chunking_contract_id") or "") == APS_CHUNKING_CONTRACT_ID
        and str(item.get("normalization_contract_id") or "") == APS_NORMALIZATION_CONTRACT_ID
    )


def _token_spans(text: str) -> list[tuple[str, int, int]]:
    normalized = unicodedata.normalize("NFC", str(text or ""))
    lowered = normalized.lower()
    spans: list[tuple[str, int, int]] = []
    cursor = 0
    while cursor < len(lowered):
        if not lowered[cursor].isalnum():
            cursor += 1
            continue
        end = cursor
        while end < len(lowered) and lowered[end].isalnum():
            end += 1
        spans.append((lowered[cursor:end], cursor, end))
        cursor = end
    return spans


def _merge_highlight_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(spans, key=lambda item: (int(item["chunk_start"]), int(item["chunk_end"])))
    merged: list[dict[str, Any]] = []
    for span in ordered:
        if not merged:
            merged.append(dict(span))
            continue
        current = merged[-1]
        if int(span["chunk_start"]) <= int(current["chunk_end"]):
            current["chunk_end"] = max(int(current["chunk_end"]), int(span["chunk_end"]))
            current["snippet_end"] = max(int(current["snippet_end"]), int(span["snippet_end"]))
            current["snippet_start"] = min(int(current["snippet_start"]), int(span["snippet_start"]))
            continue
        merged.append(dict(span))
    return merged


def build_snippet(
    *,
    chunk_text: str,
    mode: str,
    query_tokens: list[str],
    snippet_pre_chars: int = APS_SNIPPET_PRE_CHARS,
    snippet_post_chars: int = APS_SNIPPET_POST_CHARS,
) -> dict[str, Any]:
    text = unicodedata.normalize("NFC", str(chunk_text or ""))
    text_len = len(text)
    if text_len <= 0:
        return {
            "snippet_text": "",
            "snippet_start_char": 0,
            "snippet_end_char": 0,
            "highlight_spans": [],
        }

    query_mode = str(mode or APS_MODE_BROWSE) == APS_MODE_QUERY
    matching_spans: list[dict[str, Any]] = []
    if query_mode and query_tokens:
        query_set = set(query_tokens)
        for token, start, end in _token_spans(text):
            if token in query_set:
                matching_spans.append({"chunk_start": start, "chunk_end": end})

    if matching_spans:
        anchor = min(matching_spans, key=lambda item: (int(item["chunk_start"]), int(item["chunk_end"])))
        snippet_start = max(0, int(anchor["chunk_start"]) - int(snippet_pre_chars))
        snippet_end = min(text_len, int(anchor["chunk_end"]) + int(snippet_post_chars))
    else:
        snippet_start = 0
        snippet_end = min(text_len, int(snippet_pre_chars) + int(snippet_post_chars))

    snippet_text = text[snippet_start:snippet_end]
    clipped: list[dict[str, Any]] = []
    for span in matching_spans:
        overlap_start = max(int(span["chunk_start"]), int(snippet_start))
        overlap_end = min(int(span["chunk_end"]), int(snippet_end))
        if overlap_start >= overlap_end:
            continue
        clipped.append(
            {
                "chunk_start": overlap_start,
                "chunk_end": overlap_end,
                "snippet_start": overlap_start - int(snippet_start),
                "snippet_end": overlap_end - int(snippet_start),
            }
        )
    merged = _merge_highlight_spans(clipped)
    return {
        "snippet_text": snippet_text,
        "snippet_start_char": int(snippet_start),
        "snippet_end_char": int(snippet_end),
        "highlight_spans": merged,
    }


def validate_snippet_bounds(item: dict[str, Any]) -> bool:
    chunk_text = str(item.get("chunk_text") or "")
    snippet_text = str(item.get("snippet_text") or "")
    snippet_start = int(item.get("snippet_start_char") or 0)
    snippet_end = int(item.get("snippet_end_char") or 0)
    if snippet_start < 0 or snippet_end < snippet_start or snippet_end > len(chunk_text):
        return False
    if snippet_text != chunk_text[snippet_start:snippet_end]:
        return False
    for span in [dict(span or {}) for span in (item.get("highlight_spans") or []) if isinstance(span, dict)]:
        chunk_start = int(span.get("chunk_start") or 0)
        chunk_end = int(span.get("chunk_end") or 0)
        snippet_local_start = int(span.get("snippet_start") or 0)
        snippet_local_end = int(span.get("snippet_end") or 0)
        if chunk_start < snippet_start or chunk_end > snippet_end or chunk_end <= chunk_start:
            return False
        if snippet_local_start < 0 or snippet_local_end > len(snippet_text) or snippet_local_end <= snippet_local_start:
            return False
        if snippet_local_start != (chunk_start - snippet_start):
            return False
        if snippet_local_end != (chunk_end - snippet_start):
            return False
    return True
