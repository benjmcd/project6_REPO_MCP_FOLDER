from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import math
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.layer3_source_directory_text_index import (
    INDEX_CONTRACT_ID,
    INDEX_MODE,
    SCHEMA_ID as TEXT_INDEX_SCHEMA_ID,
    SEGMENTATION_VERSION,
    SOURCE_CLASS,
    source_directory_material_text_index,
)
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_embedding_vector_index.v1"
MODE = "source_directory_material_deterministic_embedding_vector_index_authority"
EMBEDDING_CONTRACT_ID = "source_directory_material_deterministic_embedding_vector_index_authority"
EMBEDDING_MODE = "deterministic_local_hashing_vector_embedding"
VECTOR_INDEX_MODE = "deterministic_source_directory_segment_vector_index"
FEATURE_HASH_VERSION = "source-directory-hash-vector-v1"
VECTOR_DIMENSIONS = 4096

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
}

_TEXT_INDEX_FIELDS = _REQUIRED_FIELDS - {"index_authority_hash"}

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
    "query_text",
    "rag_index",
    "recursive",
    "rewrite_output",
    "runtime_db_write",
    "semantic_score",
    "url",
    "vector",
    "vector_index",
    "web_connector",
}


class SourceDirectoryVectorIndexError(Exception):
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
            "request_id": "source-directory-vector-index-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_embedding_vector_index(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    expected_index_authority_hash = _required(fields, "index_authority_hash")

    text_index = source_directory_material_text_index(db, _text_index_payload(fields))
    _assert_text_index_authority(text_index)
    if str(text_index.get("index_authority_hash") or "") != expected_index_authority_hash:
        raise SourceDirectoryVectorIndexError(
            "source_directory_vector_index_stale_index_authority",
            "The deterministic embedding/vector-index request does not match current text-index authority.",
            http_status=409,
            details={"blocked_fields": ["index_authority_hash"]},
        )

    vector_descriptors = _vector_descriptors(text_index.get("segments") or [])
    row_write_flags = _row_write_flags(text_index)
    negative_invariants = _negative_invariants()
    embedding_index_authority_hash = _embedding_index_authority_hash(
        text_index=text_index,
        vector_descriptors=vector_descriptors,
        row_write_flags=row_write_flags,
        negative_invariants=negative_invariants,
    )

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "embedding_contract_id": EMBEDDING_CONTRACT_ID,
        "embedding_mode": EMBEDDING_MODE,
        "vector_index_mode": VECTOR_INDEX_MODE,
        "feature_hash_version": FEATURE_HASH_VERSION,
        "vector_dimensions": VECTOR_DIMENSIONS,
        "embedding_index_authority_hash": embedding_index_authority_hash,
        "index_contract_id": text_index.get("index_contract_id") or INDEX_CONTRACT_ID,
        "index_mode": text_index.get("index_mode") or INDEX_MODE,
        "segmentation_version": text_index.get("segmentation_version") or SEGMENTATION_VERSION,
        "index_authority_hash": text_index["index_authority_hash"],
        "source_ingestion_batch_id": text_index["source_ingestion_batch_id"],
        "source_ingestion_file_id": text_index["source_ingestion_file_id"],
        "material_snapshot_id": text_index["material_snapshot_id"],
        "source_shape": text_index.get("source_shape") or SOURCE_CLASS,
        "content_sha256": text_index["content_sha256"],
        "file_identity_hash": text_index["file_identity_hash"],
        "authority_basis_hash": text_index["authority_basis_hash"],
        "payload_hash": text_index["payload_hash"],
        "segment_count": int(text_index["segment_count"]),
        "vector_descriptors": vector_descriptors,
        **row_write_flags,
        "negative_invariants": negative_invariants,
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryVectorIndexError(
            "source_directory_vector_index_forbidden_field_not_admitted",
            "The deterministic embedding/vector-index request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS)
    if unknown:
        raise SourceDirectoryVectorIndexError(
            "source_directory_vector_index_unknown_field",
            "The deterministic embedding/vector-index request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _text_index_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_TEXT_INDEX_FIELDS)}


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
        raise SourceDirectoryVectorIndexError(
            "source_directory_vector_index_text_index_authority_mismatch",
            "The deterministic embedding/vector-index runtime must be assembled from text-index authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _vector_descriptors(segments: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for segment in segments:
        features = _hashed_features(str(segment.get("text") or ""))
        descriptors.append(
            {
                "segment_id": str(segment["segment_id"]),
                "segment_sequence": int(segment["segment_sequence"]),
                "line_start": int(segment["line_start"]),
                "line_end": int(segment["line_end"]),
                "char_start": int(segment["char_start"]),
                "char_end": int(segment["char_end"]),
                "segment_hash": str(segment["segment_hash"]),
                "embedding_vector_hash": _embedding_vector_hash(features),
                "nonzero_feature_count": len(features["normalized_features"]),
                "token_count": int(features["token_count"]),
                "vector_l2_norm": features["vector_l2_norm"],
            }
        )
    return descriptors


def _hashed_features(text: str) -> dict[str, Any]:
    token_frequencies = Counter(normalize_query_tokens(text))
    bucket_weights: Counter[int] = Counter()
    for token, frequency in token_frequencies.items():
        bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIMENSIONS
        bucket_weights[bucket] += int(frequency)

    norm = math.sqrt(sum(weight * weight for weight in bucket_weights.values()))
    normalized_features = []
    for bucket in sorted(bucket_weights):
        weight = int(bucket_weights[bucket])
        normalized_weight = "0.000000000000" if norm == 0 else f"{weight / norm:.12f}"
        normalized_features.append(
            {
                "bucket": bucket,
                "term_frequency_weight": weight,
                "normalized_weight": normalized_weight,
            }
        )
    return {
        "token_count": sum(token_frequencies.values()),
        "vector_l2_norm": round(norm, 12),
        "normalized_features": normalized_features,
    }


def _embedding_vector_hash(features: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "embedding_contract_id": EMBEDDING_CONTRACT_ID,
            "embedding_mode": EMBEDDING_MODE,
            "vector_index_mode": VECTOR_INDEX_MODE,
            "feature_hash_version": FEATURE_HASH_VERSION,
            "vector_dimensions": VECTOR_DIMENSIONS,
            "normalized_features": list(features.get("normalized_features") or []),
        }
    )


def _embedding_index_authority_hash(
    *,
    text_index: Mapping[str, Any],
    vector_descriptors: list[Mapping[str, Any]],
    row_write_flags: Mapping[str, bool],
    negative_invariants: Mapping[str, bool],
) -> str:
    return _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "embedding_contract_id": EMBEDDING_CONTRACT_ID,
            "embedding_mode": EMBEDDING_MODE,
            "vector_index_mode": VECTOR_INDEX_MODE,
            "feature_hash_version": FEATURE_HASH_VERSION,
            "vector_dimensions": VECTOR_DIMENSIONS,
            "index_contract_id": text_index.get("index_contract_id"),
            "index_mode": text_index.get("index_mode"),
            "segmentation_version": text_index.get("segmentation_version"),
            "index_authority_hash": text_index["index_authority_hash"],
            "source_ingestion_batch_id": text_index["source_ingestion_batch_id"],
            "source_ingestion_file_id": text_index["source_ingestion_file_id"],
            "material_snapshot_id": text_index["material_snapshot_id"],
            "content_sha256": text_index["content_sha256"],
            "file_identity_hash": text_index["file_identity_hash"],
            "authority_basis_hash": text_index["authority_basis_hash"],
            "payload_hash": text_index["payload_hash"],
            "segment_count": int(text_index["segment_count"]),
            "vector_descriptors": vector_descriptors,
            "row_write_flags": row_write_flags,
            "negative_invariants": negative_invariants,
        }
    )


def _row_write_flags(text_index: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "source_index_rows_written": bool(text_index.get("source_index_rows_written", False)),
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
        raise SourceDirectoryVectorIndexError(
            "source_directory_vector_index_required_field_missing",
            "A required deterministic embedding/vector-index field is missing or empty.",
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
        "vector_query_enabled": False,
        "semantic_scoring_enabled": False,
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
