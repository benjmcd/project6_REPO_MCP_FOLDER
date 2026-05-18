from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_text_index import (
    INDEX_CONTRACT_ID,
    INDEX_MODE,
    SCHEMA_ID as TEXT_INDEX_SCHEMA_ID,
    SEGMENTATION_VERSION,
    SOURCE_CLASS,
    source_directory_material_text_index,
)
from app.services.layer3_source_directory_vector_index import (
    EMBEDDING_CONTRACT_ID,
    EMBEDDING_MODE,
    FEATURE_HASH_VERSION,
    SCHEMA_ID as VECTOR_INDEX_SCHEMA_ID,
    VECTOR_DIMENSIONS,
    VECTOR_INDEX_MODE,
    _embedding_vector_hash,
    _hashed_features,
    source_directory_material_embedding_vector_index,
)
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_vector_retrieval.v1"
MODE = "source_directory_material_deterministic_vector_retrieval_authority"
RETRIEVAL_CONTRACT_ID = "source_directory_material_deterministic_vector_retrieval_authority"
RETRIEVAL_MODE = "deterministic_local_hash_vector_similarity_retrieval"
DEFAULT_TOP_K = 10
MAX_TOP_K = 20

_REQUIRED_FIELDS = {
    "client_request_id",
    "material_snapshot_id",
    "source_ingestion_batch_id",
    "source_ingestion_file_id",
    "content_sha256",
    "file_identity_hash",
    "authority_basis_hash",
    "payload_hash",
    "index_authority_hash",
    "embedding_index_authority_hash",
    "query_text",
}

_OPTIONAL_FIELDS = {"top_k"}

_VECTOR_INDEX_FIELDS = _REQUIRED_FIELDS - {"embedding_index_authority_hash", "query_text"}
_TEXT_INDEX_FIELDS = _VECTOR_INDEX_FIELDS - {"index_authority_hash"}

_FORBIDDEN_FIELDS = {
    "absolute_path",
    "analysis_run_id",
    "connector_target",
    "destination",
    "durable_write",
    "embedding_model",
    "embedding_options",
    "file_bytes",
    "frontend_state",
    "glob",
    "local_path",
    "model",
    "output_package_id",
    "package_payload",
    "pass_run_id",
    "path",
    "prompt",
    "provider_model",
    "provider_url",
    "public_url",
    "rag_index",
    "rag_prompt",
    "recursive",
    "rewrite_output",
    "runtime_db_write",
    "semantic_score",
    "url",
    "vector",
    "vector_index",
    "web_connector",
}


class SourceDirectoryVectorRetrievalError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-vector-retrieval-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_vector_retrieval(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    expected_embedding_index_authority_hash = _required(fields, "embedding_index_authority_hash")
    query_text = _required(fields, "query_text")
    query_tokens = _unique_query_tokens(query_text)
    top_k = _parse_top_k(fields.get("top_k", DEFAULT_TOP_K))

    vector_index = source_directory_material_embedding_vector_index(db, _vector_index_payload(fields))
    _assert_vector_index_authority(vector_index)
    if str(vector_index.get("embedding_index_authority_hash") or "") != expected_embedding_index_authority_hash:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_stale_embedding_index_authority",
            "The deterministic vector retrieval request does not match current embedding/vector-index authority.",
            http_status=409,
            details={"blocked_fields": ["embedding_index_authority_hash"]},
        )

    text_index = source_directory_material_text_index(db, _text_index_payload(fields))
    _assert_text_index_authority(text_index)
    if str(text_index.get("index_authority_hash") or "") != str(vector_index.get("index_authority_hash") or ""):
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_text_index_authority_mismatch",
            "The deterministic vector retrieval runtime must score the same text-index authority used by vector index.",
            http_status=409,
            details={"blocked_fields": ["index_authority_hash"]},
        )

    ranked = _rank_segments(
        text_index.get("segments") or [],
        query_text=query_text,
        query_tokens=query_tokens,
    )
    page = ranked[:top_k]
    row_write_flags = _row_write_flags()
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "retrieval_contract_id": RETRIEVAL_CONTRACT_ID,
        "retrieval_mode": RETRIEVAL_MODE,
        "query_tokens": query_tokens,
        "top_k": top_k,
        "total": len(ranked),
        "items": page,
        "embedding_contract_id": vector_index.get("embedding_contract_id") or EMBEDDING_CONTRACT_ID,
        "embedding_mode": vector_index.get("embedding_mode") or EMBEDDING_MODE,
        "vector_index_mode": vector_index.get("vector_index_mode") or VECTOR_INDEX_MODE,
        "feature_hash_version": vector_index.get("feature_hash_version") or FEATURE_HASH_VERSION,
        "vector_dimensions": int(vector_index.get("vector_dimensions") or VECTOR_DIMENSIONS),
        "embedding_index_authority_hash": vector_index["embedding_index_authority_hash"],
        "index_contract_id": vector_index.get("index_contract_id") or INDEX_CONTRACT_ID,
        "index_mode": vector_index.get("index_mode") or INDEX_MODE,
        "segmentation_version": vector_index.get("segmentation_version") or SEGMENTATION_VERSION,
        "index_authority_hash": vector_index["index_authority_hash"],
        "source_ingestion_batch_id": vector_index["source_ingestion_batch_id"],
        "source_ingestion_file_id": vector_index["source_ingestion_file_id"],
        "material_snapshot_id": vector_index["material_snapshot_id"],
        "source_shape": vector_index.get("source_shape") or SOURCE_CLASS,
        "content_sha256": vector_index["content_sha256"],
        "file_identity_hash": vector_index["file_identity_hash"],
        "authority_basis_hash": vector_index["authority_basis_hash"],
        "payload_hash": vector_index["payload_hash"],
        **row_write_flags,
        "negative_invariants": _negative_invariants(),
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_forbidden_field_not_admitted",
            "The deterministic vector retrieval request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_unknown_field",
            "The deterministic vector retrieval request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _vector_index_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_VECTOR_INDEX_FIELDS)}


def _text_index_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_TEXT_INDEX_FIELDS)}


def _assert_vector_index_authority(vector_index: Mapping[str, Any]) -> None:
    mismatches = []
    if str(vector_index.get("schema_id") or "") != VECTOR_INDEX_SCHEMA_ID:
        mismatches.append("schema_id")
    if str(vector_index.get("embedding_contract_id") or "") != EMBEDDING_CONTRACT_ID:
        mismatches.append("embedding_contract_id")
    if str(vector_index.get("embedding_mode") or "") != EMBEDDING_MODE:
        mismatches.append("embedding_mode")
    if str(vector_index.get("vector_index_mode") or "") != VECTOR_INDEX_MODE:
        mismatches.append("vector_index_mode")
    if str(vector_index.get("feature_hash_version") or "") != FEATURE_HASH_VERSION:
        mismatches.append("feature_hash_version")
    if int(vector_index.get("vector_dimensions") or 0) != VECTOR_DIMENSIONS:
        mismatches.append("vector_dimensions")
    if mismatches:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_vector_index_authority_mismatch",
            "The deterministic vector retrieval runtime must be assembled from embedding/vector-index authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _assert_text_index_authority(text_index: Mapping[str, Any]) -> None:
    mismatches = []
    if str(text_index.get("schema_id") or "") != TEXT_INDEX_SCHEMA_ID:
        mismatches.append("schema_id")
    if str(text_index.get("index_contract_id") or "") != INDEX_CONTRACT_ID:
        mismatches.append("index_contract_id")
    if str(text_index.get("index_mode") or "") != INDEX_MODE:
        mismatches.append("index_mode")
    if str(text_index.get("segmentation_version") or "") != SEGMENTATION_VERSION:
        mismatches.append("segmentation_version")
    if mismatches:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_text_index_authority_mismatch",
            "The deterministic vector retrieval runtime must score deterministic text-index authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _unique_query_tokens(value: str) -> list[str]:
    tokens = sorted(dict.fromkeys(normalize_query_tokens(value)))
    if not tokens:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_empty_query",
            "The deterministic vector retrieval query has no normalized tokens.",
            details={"field": "query_text"},
        )
    return tokens


def _parse_top_k(value: Any) -> int:
    top_k = _parse_int(value, field="top_k")
    if top_k < 1 or top_k > MAX_TOP_K:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_top_k_out_of_bounds",
            "The deterministic vector retrieval top_k must be between 1 and 20.",
            details={"field": "top_k", "minimum": 1, "maximum": MAX_TOP_K},
        )
    return top_k


def _parse_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_integer_field_invalid",
            "The deterministic vector retrieval numeric field must be an integer.",
            details={"field": field},
        )
    text = str(value).strip()
    try:
        parsed = int(text)
    except (TypeError, ValueError) as exc:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_integer_field_invalid",
            "The deterministic vector retrieval numeric field must be an integer.",
            details={"field": field},
        ) from exc
    if text != str(parsed):
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_integer_field_invalid",
            "The deterministic vector retrieval numeric field must be an integer.",
            details={"field": field},
        )
    return parsed


def _rank_segments(
    segments: list[Mapping[str, Any]],
    *,
    query_text: str,
    query_tokens: list[str],
) -> list[dict[str, Any]]:
    query_features = _feature_map(_hashed_features(query_text))
    ranked: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text") or "")
        segment_features = _hashed_features(text)
        score = _dot_product(query_features, _feature_map(segment_features))
        if score <= Decimal("0"):
            continue
        frequencies = Counter(normalize_query_tokens(text))
        item = {
            "segment_id": str(segment["segment_id"]),
            "segment_sequence": int(segment["segment_sequence"]),
            "line_start": int(segment["line_start"]),
            "line_end": int(segment["line_end"]),
            "char_start": int(segment["char_start"]),
            "char_end": int(segment["char_end"]),
            "segment_hash": str(segment["segment_hash"]),
            "embedding_vector_hash": _embedding_vector_hash(segment_features),
            "text": text,
            "vector_score": f"{score:.12f}",
            "matched_unique_query_terms": sum(1 for token in query_tokens if int(frequencies.get(token, 0)) > 0),
            "summed_query_term_frequency": sum(int(frequencies.get(token, 0)) for token in query_tokens),
        }
        ranked.append(item)
    ranked.sort(
        key=lambda item: (
            -Decimal(str(item["vector_score"])),
            -int(item["matched_unique_query_terms"]),
            -int(item["summed_query_term_frequency"]),
            int(item["segment_sequence"]),
            str(item["segment_id"]),
        )
    )
    return ranked


def _feature_map(features: Mapping[str, Any]) -> dict[int, Decimal]:
    return {
        int(feature["bucket"]): Decimal(str(feature["normalized_weight"]))
        for feature in list(features.get("normalized_features") or [])
    }


def _dot_product(left: Mapping[int, Decimal], right: Mapping[int, Decimal]) -> Decimal:
    common = set(left) & set(right)
    return sum((left[bucket] * right[bucket] for bucket in common), Decimal("0"))


def _row_write_flags() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
    }


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryVectorRetrievalError(
            "source_directory_vector_retrieval_required_field_missing",
            "A required deterministic vector retrieval field is missing or empty.",
            details={"field": key},
        )
    return value


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
        "route_admitted": False,
        "persistent_vector_store_enabled": False,
        "durable_embedding_rows_enabled": False,
        "durable_retrieval_rows_enabled": False,
        "rag_execution_enabled": False,
        "embedding_model_provider_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "qualitative_generation_runtime_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "package_construction_enabled": False,
        "package_mutation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "network_egress_enabled": False,
        "raw_local_path_exposed": False,
    }


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
