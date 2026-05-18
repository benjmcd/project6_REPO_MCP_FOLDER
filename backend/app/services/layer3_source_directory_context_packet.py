from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.layer3_source_directory_text_retrieval import (
    RETRIEVAL_CONTRACT_ID,
    RETRIEVAL_MODE,
    source_directory_material_text_retrieval,
)

SCHEMA_ID = "layer3.source_directory_context_packet.v1"
MODE = "source_directory_material_retrieval_augmented_context_packet_authority"
CONTEXT_PACKET_CONTRACT_ID = "source_directory_material_retrieval_augmented_context_packet_authority"
CONTEXT_PACKET_MODE = "retrieval_augmented_qualitative_context_packet"
MAX_TEXT_EXCERPT_CHARS = 800

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
    "runtime_db_write",
    "semantic_score",
    "url",
    "vector",
    "vector_index",
    "web_connector",
}


class SourceDirectoryContextPacketError(Exception):
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
            "request_id": "source-directory-context-packet-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_retrieval_augmented_context_packet(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    retrieval_response = source_directory_material_text_retrieval(db, fields)
    _assert_retrieval_authority(retrieval_response)

    offset = int(retrieval_response["offset"])
    items = _context_items(retrieval_response.get("items") or [], offset=offset)
    context_packet_hash = _context_packet_hash(retrieval_response, items)
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "context_packet_contract_id": CONTEXT_PACKET_CONTRACT_ID,
        "context_packet_mode": CONTEXT_PACKET_MODE,
        "retrieval_contract_id": retrieval_response["retrieval_contract_id"],
        "retrieval_mode": retrieval_response["retrieval_mode"],
        "context_packet_hash": context_packet_hash,
        "query_tokens": retrieval_response["query_tokens"],
        "total": retrieval_response["total"],
        "limit": retrieval_response["limit"],
        "offset": offset,
        "items": items,
        "index_contract_id": retrieval_response.get("index_contract_id"),
        "index_mode": retrieval_response.get("index_mode"),
        "segmentation_version": retrieval_response.get("segmentation_version"),
        "index_authority_hash": retrieval_response["index_authority_hash"],
        "source_ingestion_batch_id": retrieval_response["source_ingestion_batch_id"],
        "source_ingestion_file_id": retrieval_response["source_ingestion_file_id"],
        "material_snapshot_id": retrieval_response["material_snapshot_id"],
        "source_shape": retrieval_response.get("source_shape"),
        "content_sha256": retrieval_response["content_sha256"],
        "file_identity_hash": retrieval_response["file_identity_hash"],
        "authority_basis_hash": retrieval_response["authority_basis_hash"],
        "payload_hash": retrieval_response["payload_hash"],
        "source_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "negative_invariants": _negative_invariants(),
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryContextPacketError(
            "source_directory_context_packet_forbidden_field_not_admitted",
            "The source-directory context-packet request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryContextPacketError(
            "source_directory_context_packet_unknown_field",
            "The source-directory context-packet request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _assert_retrieval_authority(retrieval_response: Mapping[str, Any]) -> None:
    mismatches = []
    if str(retrieval_response.get("retrieval_contract_id") or "") != RETRIEVAL_CONTRACT_ID:
        mismatches.append("retrieval_contract_id")
    if str(retrieval_response.get("retrieval_mode") or "") != RETRIEVAL_MODE:
        mismatches.append("retrieval_mode")
    if mismatches:
        raise SourceDirectoryContextPacketError(
            "source_directory_context_packet_retrieval_authority_mismatch",
            "The source-directory context packet must be assembled from deterministic lexical retrieval authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _context_items(items: list[Mapping[str, Any]], *, offset: int) -> list[dict[str, Any]]:
    packet_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        packet_items.append(
            {
                "rank_position": offset + index + 1,
                "segment_id": str(item["segment_id"]),
                "segment_sequence": int(item["segment_sequence"]),
                "line_start": int(item["line_start"]),
                "line_end": int(item["line_end"]),
                "char_start": int(item["char_start"]),
                "char_end": int(item["char_end"]),
                "segment_hash": str(item["segment_hash"]),
                "text_excerpt": str(item.get("text") or "")[:MAX_TEXT_EXCERPT_CHARS],
                "matched_unique_query_terms": int(item["matched_unique_query_terms"]),
                "summed_term_frequency": int(item["summed_term_frequency"]),
            }
        )
    return packet_items


def _context_packet_hash(retrieval_response: Mapping[str, Any], items: list[Mapping[str, Any]]) -> str:
    return _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "context_packet_contract_id": CONTEXT_PACKET_CONTRACT_ID,
            "context_packet_mode": CONTEXT_PACKET_MODE,
            "retrieval_contract_id": retrieval_response["retrieval_contract_id"],
            "retrieval_mode": retrieval_response["retrieval_mode"],
            "query_tokens": retrieval_response["query_tokens"],
            "total": retrieval_response["total"],
            "limit": retrieval_response["limit"],
            "offset": retrieval_response["offset"],
            "index_authority_hash": retrieval_response["index_authority_hash"],
            "source_ingestion_batch_id": retrieval_response["source_ingestion_batch_id"],
            "source_ingestion_file_id": retrieval_response["source_ingestion_file_id"],
            "material_snapshot_id": retrieval_response["material_snapshot_id"],
            "content_sha256": retrieval_response["content_sha256"],
            "file_identity_hash": retrieval_response["file_identity_hash"],
            "authority_basis_hash": retrieval_response["authority_basis_hash"],
            "payload_hash": retrieval_response["payload_hash"],
            "items": [
                {
                    "rank_position": item["rank_position"],
                    "segment_id": item["segment_id"],
                    "segment_sequence": item["segment_sequence"],
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                    "char_start": item["char_start"],
                    "char_end": item["char_end"],
                    "segment_hash": item["segment_hash"],
                    "matched_unique_query_terms": item["matched_unique_query_terms"],
                    "summed_term_frequency": item["summed_term_frequency"],
                }
                for item in items
            ],
        }
    )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryContextPacketError(
            "source_directory_context_packet_required_field_missing",
            "A required source-directory context-packet field is missing or empty.",
            details={"field": key},
        )
    return value


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "route_admitted": False,
        "vector_index_enabled": False,
        "embedding_generation_enabled": False,
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
