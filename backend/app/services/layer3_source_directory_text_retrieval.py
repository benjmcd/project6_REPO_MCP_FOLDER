from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_text_index import (
    INDEX_CONTRACT_ID,
    INDEX_MODE,
    SEGMENTATION_VERSION,
    SOURCE_CLASS,
    source_directory_material_text_index,
)
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_text_retrieval.v1"
MODE = "source_directory_material_deterministic_lexical_retrieval_authority"
RETRIEVAL_CONTRACT_ID = "source_directory_material_deterministic_lexical_retrieval_authority"
RETRIEVAL_MODE = "deterministic_lexical_segment_retrieval"
DEFAULT_LIMIT = 20
MAX_LIMIT = 50

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
    "query_text",
}

_OPTIONAL_FIELDS = {"limit", "offset"}

_FORBIDDEN_FIELDS = {
    "absolute_path",
    "connector_target",
    "destination",
    "embedding",
    "embedding_model",
    "embedding_options",
    "file_bytes",
    "frontend_state",
    "glob",
    "local_path",
    "model",
    "package_payload",
    "path",
    "prompt",
    "provider_model",
    "provider_url",
    "public_url",
    "rag_index",
    "recursive",
    "retrieval_query",
    "retrieval_query_text",
    "semantic_score",
    "url",
    "vector",
    "vector_index",
    "web_connector",
}


class SourceDirectoryTextRetrievalError(Exception):
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
            "request_id": "source-directory-text-retrieval-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_text_retrieval(db: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    expected_index_authority_hash = _required(fields, "index_authority_hash")
    query_tokens = _unique_query_tokens(_required(fields, "query_text"))
    limit = _parse_limit(fields.get("limit", DEFAULT_LIMIT))
    offset = _parse_offset(fields.get("offset", 0))

    index_response = source_directory_material_text_index(db, _index_payload(fields))
    if str(index_response.get("index_authority_hash") or "") != expected_index_authority_hash:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_stale_index_authority",
            "The deterministic text retrieval request does not match current text-index authority.",
            http_status=409,
            details={"blocked_fields": ["index_authority_hash"]},
        )

    ranked = _rank_segments(index_response.get("segments") or [], query_tokens=query_tokens)
    total = len(ranked)
    page = ranked[offset : offset + limit]
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
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": page,
        "index_contract_id": index_response.get("index_contract_id") or INDEX_CONTRACT_ID,
        "index_mode": index_response.get("index_mode") or INDEX_MODE,
        "segmentation_version": index_response.get("segmentation_version") or SEGMENTATION_VERSION,
        "index_authority_hash": index_response["index_authority_hash"],
        "source_ingestion_batch_id": index_response["source_ingestion_batch_id"],
        "source_ingestion_file_id": index_response["source_ingestion_file_id"],
        "material_snapshot_id": index_response["material_snapshot_id"],
        "source_shape": index_response.get("source_shape") or SOURCE_CLASS,
        "content_sha256": index_response["content_sha256"],
        "file_identity_hash": index_response["file_identity_hash"],
        "authority_basis_hash": index_response["authority_basis_hash"],
        "payload_hash": index_response["payload_hash"],
        "source_index_rows_written": False,
        "retrieval_rows_written": False,
        "negative_invariants": _negative_invariants(),
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_forbidden_field_not_admitted",
            "The deterministic text retrieval request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_unknown_field",
            "The deterministic text retrieval request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _index_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "client_request_id": fields["client_request_id"],
        "material_snapshot_id": fields["material_snapshot_id"],
        "source_ingestion_batch_id": fields["source_ingestion_batch_id"],
        "source_ingestion_file_id": fields["source_ingestion_file_id"],
        "content_sha256": fields["content_sha256"],
        "file_identity_hash": fields["file_identity_hash"],
        "authority_basis_hash": fields["authority_basis_hash"],
        "payload_hash": fields["payload_hash"],
    }


def _unique_query_tokens(value: str) -> list[str]:
    tokens = sorted(dict.fromkeys(normalize_query_tokens(value)))
    if not tokens:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_empty_query",
            "The deterministic text retrieval query has no normalized lexical tokens.",
            details={"field": "query_text"},
        )
    return tokens


def _parse_limit(value: Any) -> int:
    limit = _parse_int(value, field="limit")
    if limit < 1 or limit > MAX_LIMIT:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_limit_out_of_bounds",
            "The deterministic text retrieval limit must be between 1 and 50.",
            details={"field": "limit", "minimum": 1, "maximum": MAX_LIMIT},
        )
    return limit


def _parse_offset(value: Any) -> int:
    offset = _parse_int(value, field="offset")
    if offset < 0:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_offset_out_of_bounds",
            "The deterministic text retrieval offset must be greater than or equal to 0.",
            details={"field": "offset", "minimum": 0},
        )
    return offset


def _parse_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_integer_field_invalid",
            "The deterministic text retrieval numeric field must be an integer.",
            details={"field": field},
        )
    text = str(value).strip()
    try:
        parsed = int(text)
    except (TypeError, ValueError) as exc:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_integer_field_invalid",
            "The deterministic text retrieval numeric field must be an integer.",
            details={"field": field},
        ) from exc
    if text != str(parsed):
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_integer_field_invalid",
            "The deterministic text retrieval numeric field must be an integer.",
            details={"field": field},
        )
    return parsed


def _rank_segments(segments: list[Mapping[str, Any]], *, query_tokens: list[str]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text") or "")
        frequencies = Counter(normalize_query_tokens(text))
        if any(int(frequencies.get(token, 0)) <= 0 for token in query_tokens):
            continue
        item = {
            "segment_id": str(segment["segment_id"]),
            "segment_sequence": int(segment["segment_sequence"]),
            "line_start": int(segment["line_start"]),
            "line_end": int(segment["line_end"]),
            "char_start": int(segment["char_start"]),
            "char_end": int(segment["char_end"]),
            "segment_hash": str(segment["segment_hash"]),
            "text": text,
            "matched_unique_query_terms": len(query_tokens),
            "summed_term_frequency": sum(int(frequencies.get(token, 0)) for token in query_tokens),
        }
        ranked.append(item)
    ranked.sort(
        key=lambda item: (
            -int(item["matched_unique_query_terms"]),
            -int(item["summed_term_frequency"]),
            len(str(item["text"])),
            int(item["segment_sequence"]),
            str(item["segment_id"]),
        )
    )
    return ranked


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryTextRetrievalError(
            "source_directory_text_retrieval_required_field_missing",
            "A required deterministic text retrieval field is missing or empty.",
            details={"field": key},
        )
    return value


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "retrieval_rows_written": False,
        "route_admitted": False,
        "vector_index_enabled": False,
        "embedding_generation_enabled": False,
        "qualitative_hybrid_runtime_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "package_construction_enabled": False,
        "package_mutation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "network_egress_enabled": False,
    }


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
