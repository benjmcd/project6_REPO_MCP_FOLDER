from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


APS_RETRIEVAL_CONTRACT_ID = "aps_retrieval_chunk_v1"

APS_RETRIEVAL_IDENTITY_FIELDS = (
    "retrieval_contract_id",
    "run_id",
    "target_id",
    "content_id",
    "chunk_id",
)

APS_RETRIEVAL_SOURCE_SIGNATURE_FIELDS = (
    "retrieval_contract_id",
    "run_id",
    "target_id",
    "content_id",
    "chunk_id",
    "content_contract_id",
    "chunking_contract_id",
    "normalization_contract_id",
    "accession_number",
    "chunk_ordinal",
    "start_char",
    "end_char",
    "page_start",
    "page_end",
    "chunk_text",
    "chunk_text_sha256",
    "search_text",
    "content_status",
    "quality_status",
    "document_class",
    "media_type",
    "page_count",
    "content_units_ref",
    "normalized_text_ref",
    "blob_ref",
    "download_exchange_ref",
    "discovery_ref",
    "selection_ref",
    "diagnostics_ref",
    "visual_page_refs_json",
)

APS_RETRIEVAL_PERSISTED_FIELDS = (
    "aps_retrieval_chunk_id",
    "retrieval_contract_id",
    "run_id",
    "target_id",
    "content_id",
    "chunk_id",
    "content_contract_id",
    "chunking_contract_id",
    "normalization_contract_id",
    "accession_number",
    "chunk_ordinal",
    "start_char",
    "end_char",
    "page_start",
    "page_end",
    "chunk_text",
    "chunk_text_sha256",
    "search_text",
    "content_status",
    "quality_status",
    "document_class",
    "media_type",
    "page_count",
    "content_units_ref",
    "normalized_text_ref",
    "blob_ref",
    "download_exchange_ref",
    "discovery_ref",
    "selection_ref",
    "diagnostics_ref",
    "visual_page_refs_json",
    "source_signature_sha256",
    "source_updated_at",
    "rebuilt_at",
    "created_at",
)

APS_RETRIEVAL_COMPARISON_FIELDS = (
    "aps_retrieval_chunk_id",
    *APS_RETRIEVAL_SOURCE_SIGNATURE_FIELDS,
    "source_signature_sha256",
    "source_updated_at",
)


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def normalize_optional_string(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def canonicalize_visual_page_refs(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return raw
    else:
        parsed = value
    if not isinstance(parsed, list):
        return normalize_optional_string(parsed)
    normalized = [dict(item) for item in parsed if isinstance(item, dict)]
    if not normalized:
        return None
    return json.dumps(normalized, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def row_identity_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in APS_RETRIEVAL_IDENTITY_FIELDS}


def row_identity_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in APS_RETRIEVAL_IDENTITY_FIELDS)


def derive_retrieval_chunk_id(row: dict[str, Any]) -> str:
    return stable_hash(row_identity_payload(row))


def source_signature_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in APS_RETRIEVAL_SOURCE_SIGNATURE_FIELDS}


def compute_source_signature(row: dict[str, Any]) -> str:
    return stable_hash(source_signature_payload(row))


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value
