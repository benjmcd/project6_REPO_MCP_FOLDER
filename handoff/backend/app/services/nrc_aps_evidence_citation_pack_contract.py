from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_evidence_bundle_contract as bundle_contract


APS_EVIDENCE_CITATION_PACK_SCHEMA_ID = "aps.evidence_citation_pack.v1"
APS_EVIDENCE_CITATION_PACK_FAILURE_SCHEMA_ID = "aps.evidence_citation_pack_failure.v1"
APS_EVIDENCE_CITATION_PACK_GATE_SCHEMA_ID = "aps.evidence_citation_pack_gate.v1"
APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION = 1

APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID = "aps_evidence_citation_derivation_v1"

APS_CITATION_DEFAULT_LIMIT = 50
APS_CITATION_MAX_LIMIT = 200
APS_CITATION_LABEL_PREFIX = "APS-CIT-"
APS_CITATION_LABEL_WIDTH = 5
APS_CITATION_ARTIFACT_ID_TOKEN_LEN = 24

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_SOURCE_BUNDLE_NOT_FOUND = "source_bundle_not_found"
APS_RUNTIME_FAILURE_SOURCE_BUNDLE_INVALID = "source_bundle_invalid"
APS_RUNTIME_FAILURE_SOURCE_BUNDLE_UNKNOWN_CONTRACT = "unknown_contract_id"
APS_RUNTIME_FAILURE_SOURCE_BUNDLE_PROVENANCE_MISSING = "provenance_ref_missing"
APS_RUNTIME_FAILURE_SOURCE_BUNDLE_PROVENANCE_UNRESOLVABLE = "provenance_ref_unresolvable"
APS_RUNTIME_FAILURE_WRITE_FAILED = "citation_pack_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_citation_pack_error"

APS_GATE_FAILURE_MISSING_REF = "missing_citation_pack_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_citation_pack_ref"
APS_GATE_FAILURE_PACK_SCHEMA = "citation_pack_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "citation_pack_failure_schema_mismatch"
APS_GATE_FAILURE_DERIVATION_CONTRACT = "derivation_contract_mismatch"
APS_GATE_FAILURE_SOURCE_BUNDLE_REF = "source_bundle_ref_mismatch"
APS_GATE_FAILURE_SOURCE_BUNDLE_MISMATCH = "source_bundle_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_UNKNOWN_CONTRACT = "unknown_contract_id"
APS_GATE_FAILURE_MISSING_PROVENANCE = "missing_provenance_ref"
APS_GATE_FAILURE_UNRESOLVABLE_PROVENANCE = "unresolvable_provenance_ref"
APS_GATE_FAILURE_DERIVATION_DRIFT = "citation_derivation_drift"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def compute_citation_pack_checksum(payload: dict[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("citation_pack_checksum", None)
    clean.pop("_citation_pack_ref", None)
    clean.pop("_persisted", None)
    source_bundle = dict(clean.get("source_bundle") or {})
    source_bundle.pop("_bundle_ref", None)
    source_bundle.pop("_persisted", None)
    clean["source_bundle"] = source_bundle
    return stable_hash(clean)


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_CITATION_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_citation_pack_file_name(*, scope: str, citation_pack_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(citation_pack_id)}_aps_evidence_citation_pack_v1.json"


def expected_failure_file_name(*, scope: str, citation_pack_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(citation_pack_id)}_aps_evidence_citation_pack_failure_v1.json"


def resolve_limit_offset(*, limit_value: Any, offset_value: Any) -> tuple[int, int]:
    raw_limit = APS_CITATION_DEFAULT_LIMIT if limit_value is None else limit_value
    raw_offset = 0 if offset_value is None else offset_value

    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ValueError("invalid_limit") from None
    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        raise ValueError("invalid_offset") from None

    if limit < 1 or limit > APS_CITATION_MAX_LIMIT:
        raise ValueError("invalid_limit")
    if offset < 0:
        raise ValueError("invalid_offset")
    return limit, offset


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    bundle_id = str(payload.get("bundle_id") or "").strip() or None
    bundle_ref = str(payload.get("bundle_ref") or "").strip() or None
    if bool(bundle_id) == bool(bundle_ref):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)

    try:
        limit, offset = resolve_limit_offset(limit_value=payload.get("limit"), offset_value=payload.get("offset", 0))
    except ValueError as exc:
        raise ValueError(str(exc)) from None

    return {
        "bundle_id": bundle_id,
        "bundle_ref": bundle_ref,
        "limit": limit,
        "offset": offset,
        "persist_pack": bool(payload.get("persist_pack", False)),
    }


def derive_citation_pack_id(*, source_bundle_id: str, source_bundle_checksum: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
            APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
            str(source_bundle_id or ""),
            str(source_bundle_checksum or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_failure_pack_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_EVIDENCE_CITATION_PACK_FAILURE_SCHEMA_ID,
            APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def citation_label_for_ordinal(citation_ordinal: int) -> str:
    ordinal = max(1, int(citation_ordinal or 0))
    return f"{APS_CITATION_LABEL_PREFIX}{ordinal:0{APS_CITATION_LABEL_WIDTH}d}"


def derive_citation_id(
    *,
    source_bundle_id: str,
    source_bundle_checksum: str,
    citation_ordinal: int,
    group_id: str,
    chunk_id: str,
) -> str:
    return stable_hash(
        {
            "schema_id": APS_EVIDENCE_CITATION_PACK_SCHEMA_ID,
            "derivation_contract_id": APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID,
            "source_bundle_id": str(source_bundle_id or ""),
            "source_bundle_checksum": str(source_bundle_checksum or ""),
            "citation_ordinal": int(citation_ordinal or 0),
            "group_id": str(group_id or ""),
            "chunk_id": str(chunk_id or ""),
        }
    )


def source_bundle_summary_payload(source_bundle_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": str(source_bundle_payload.get("schema_id") or bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID),
        "schema_version": int(source_bundle_payload.get("schema_version") or bundle_contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION),
        "bundle_id": str(source_bundle_payload.get("bundle_id") or ""),
        "bundle_checksum": str(source_bundle_payload.get("bundle_checksum") or ""),
        "bundle_ref": str(source_bundle_payload.get("_bundle_ref") or source_bundle_payload.get("bundle_ref") or "") or None,
        "request_identity_hash": str(source_bundle_payload.get("request_identity_hash") or ""),
        "mode": str(source_bundle_payload.get("mode") or bundle_contract.APS_MODE_BROWSE),
        "run_id": str(source_bundle_payload.get("run_id") or ""),
        "query": source_bundle_payload.get("query"),
        "query_tokens": list(source_bundle_payload.get("query_tokens") or []),
        "snapshot": dict(source_bundle_payload.get("snapshot") or {}),
        "total_hits": int(source_bundle_payload.get("total_hits") or 0),
        "total_groups": int(source_bundle_payload.get("total_groups") or 0),
    }


def build_citation(
    *,
    source_bundle_payload: dict[str, Any],
    source_row: dict[str, Any],
    citation_ordinal: int,
) -> dict[str, Any]:
    source_bundle_id = str(source_bundle_payload.get("bundle_id") or "")
    source_bundle_checksum = str(source_bundle_payload.get("bundle_checksum") or "")
    group_id = str(source_row.get("group_id") or bundle_contract.group_id_for_item(source_row))
    chunk_id = str(source_row.get("chunk_id") or "")
    return {
        "citation_id": derive_citation_id(
            source_bundle_id=source_bundle_id,
            source_bundle_checksum=source_bundle_checksum,
            citation_ordinal=citation_ordinal,
            group_id=group_id,
            chunk_id=chunk_id,
        ),
        "citation_ordinal": int(citation_ordinal),
        "citation_label": citation_label_for_ordinal(citation_ordinal),
        "group_id": group_id,
        "chunk_id": chunk_id,
        "content_id": str(source_row.get("content_id") or ""),
        "run_id": str(source_row.get("run_id") or ""),
        "target_id": str(source_row.get("target_id") or ""),
        "accession_number": str(source_row.get("accession_number") or "").strip() or None,
        "content_contract_id": str(source_row.get("content_contract_id") or ""),
        "chunking_contract_id": str(source_row.get("chunking_contract_id") or ""),
        "normalization_contract_id": str(source_row.get("normalization_contract_id") or ""),
        "chunk_ordinal": int(source_row.get("chunk_ordinal") or 0),
        "start_char": int(source_row.get("start_char") or 0),
        "end_char": int(source_row.get("end_char") or 0),
        "snippet_text": str(source_row.get("snippet_text") or ""),
        "snippet_start_char": int(source_row.get("snippet_start_char") or 0),
        "snippet_end_char": int(source_row.get("snippet_end_char") or 0),
        "highlight_spans": [dict(item or {}) for item in (source_row.get("highlight_spans") or []) if isinstance(item, dict)],
        "matched_unique_query_terms": int(source_row.get("matched_unique_query_terms") or 0),
        "summed_term_frequency": int(source_row.get("summed_term_frequency") or 0),
        "chunk_text_sha256": str(source_row.get("chunk_text_sha256") or ""),
        "normalized_text_sha256": str(source_row.get("normalized_text_sha256") or "").strip() or None,
        "blob_sha256": str(source_row.get("blob_sha256") or "").strip() or None,
        "content_units_ref": str(source_row.get("content_units_ref") or "").strip() or None,
        "normalized_text_ref": str(source_row.get("normalized_text_ref") or "").strip() or None,
        "blob_ref": str(source_row.get("blob_ref") or "").strip() or None,
        "download_exchange_ref": str(source_row.get("download_exchange_ref") or "").strip() or None,
        "discovery_ref": str(source_row.get("discovery_ref") or "").strip() or None,
        "selection_ref": str(source_row.get("selection_ref") or "").strip() or None,
    }


def build_citations_from_bundle(source_bundle_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(item or {}) for item in (source_bundle_payload.get("results") or []) if isinstance(item, dict)]
    return [
        build_citation(
            source_bundle_payload=source_bundle_payload,
            source_row=row,
            citation_ordinal=index + 1,
        )
        for index, row in enumerate(rows)
    ]
