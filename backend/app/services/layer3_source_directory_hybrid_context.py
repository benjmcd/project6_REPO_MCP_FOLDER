from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_context_packet import (
    CONTEXT_PACKET_CONTRACT_ID as LEXICAL_CONTEXT_PACKET_CONTRACT_ID,
    CONTEXT_PACKET_MODE as LEXICAL_CONTEXT_PACKET_MODE,
    source_directory_material_retrieval_augmented_context_packet,
)
from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.layer3_source_directory_vector_index import (
    EMBEDDING_CONTRACT_ID,
    EMBEDDING_MODE,
    FEATURE_HASH_VERSION,
    VECTOR_DIMENSIONS,
    VECTOR_INDEX_MODE,
)
from app.services.layer3_source_directory_vector_retrieval import (
    RETRIEVAL_CONTRACT_ID as VECTOR_RETRIEVAL_CONTRACT_ID,
    RETRIEVAL_MODE as VECTOR_RETRIEVAL_MODE,
    source_directory_material_vector_retrieval,
)

SCHEMA_ID = "layer3.source_directory_hybrid_retrieval_context_packet.v1"
MODE = "source_directory_hybrid_retrieval_context_packet_authority"
CONTRACT_ID = "source_directory_hybrid_retrieval_context_packet_authority"
HYBRID_MODE = "deterministic_lexical_and_vector_context_packet"
SOURCE_GATE = "822_SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_RUNTIME_ENTRY_FREEZE"
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
    "embedding_index_authority_hash",
    "query_text",
}

_OPTIONAL_FIELDS = {"limit", "offset", "top_k"}

_LEXICAL_FIELDS = _REQUIRED_FIELDS - {"embedding_index_authority_hash"} | {"limit", "offset"}
_VECTOR_FIELDS = _REQUIRED_FIELDS | {"top_k"}

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
    "rag_execution",
    "rag_index",
    "rag_plan",
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


class SourceDirectoryHybridContextError(Exception):
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
            "request_id": "source-directory-hybrid-context-packet-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_hybrid_retrieval_context_packet(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")

    lexical_packet = source_directory_material_retrieval_augmented_context_packet(db, _lexical_payload(fields))
    _assert_lexical_context_authority(lexical_packet)
    vector_retrieval = source_directory_material_vector_retrieval(db, _vector_payload(fields))
    _assert_vector_retrieval_authority(vector_retrieval)

    hybrid_items = _hybrid_items(
        lexical_items=list(lexical_packet.get("items") or []),
        vector_items=list(vector_retrieval.get("items") or []),
    )
    hybrid_context_packet_hash = _hybrid_context_packet_hash(
        lexical_packet=lexical_packet,
        vector_retrieval=vector_retrieval,
        hybrid_items=hybrid_items,
    )
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "hybrid_context_contract_id": CONTRACT_ID,
        "hybrid_context_mode": HYBRID_MODE,
        "source_gate": SOURCE_GATE,
        "hybrid_context_packet_hash": hybrid_context_packet_hash,
        "lexical_context_packet_hash": lexical_packet["context_packet_hash"],
        "lexical_context_packet_contract_id": lexical_packet["context_packet_contract_id"],
        "lexical_context_packet_mode": lexical_packet["context_packet_mode"],
        "vector_retrieval_contract_id": vector_retrieval["retrieval_contract_id"],
        "vector_retrieval_mode": vector_retrieval["retrieval_mode"],
        "embedding_contract_id": vector_retrieval["embedding_contract_id"],
        "embedding_mode": vector_retrieval["embedding_mode"],
        "vector_index_mode": vector_retrieval["vector_index_mode"],
        "feature_hash_version": vector_retrieval["feature_hash_version"],
        "vector_dimensions": vector_retrieval["vector_dimensions"],
        "query_tokens": lexical_packet["query_tokens"],
        "lexical_total": lexical_packet["total"],
        "lexical_limit": lexical_packet["limit"],
        "lexical_offset": lexical_packet["offset"],
        "vector_total": vector_retrieval["total"],
        "vector_top_k": vector_retrieval["top_k"],
        "hybrid_total": len(hybrid_items),
        "items": hybrid_items,
        "index_authority_hash": lexical_packet["index_authority_hash"],
        "embedding_index_authority_hash": vector_retrieval["embedding_index_authority_hash"],
        "source_ingestion_batch_id": lexical_packet["source_ingestion_batch_id"],
        "source_ingestion_file_id": lexical_packet["source_ingestion_file_id"],
        "material_snapshot_id": lexical_packet["material_snapshot_id"],
        "source_shape": lexical_packet.get("source_shape"),
        "content_sha256": lexical_packet["content_sha256"],
        "file_identity_hash": lexical_packet["file_identity_hash"],
        "authority_basis_hash": lexical_packet["authority_basis_hash"],
        "payload_hash": lexical_packet["payload_hash"],
        **_row_write_flags(),
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridContextError(
            "source_directory_hybrid_context_forbidden_field_not_admitted",
            "The source-directory hybrid context request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryHybridContextError(
            "source_directory_hybrid_context_unknown_field",
            "The source-directory hybrid context request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _lexical_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_LEXICAL_FIELDS) if field in fields}


def _vector_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_VECTOR_FIELDS) if field in fields}


def _assert_lexical_context_authority(packet: Mapping[str, Any]) -> None:
    mismatches = []
    if str(packet.get("context_packet_contract_id") or "") != LEXICAL_CONTEXT_PACKET_CONTRACT_ID:
        mismatches.append("context_packet_contract_id")
    if str(packet.get("context_packet_mode") or "") != LEXICAL_CONTEXT_PACKET_MODE:
        mismatches.append("context_packet_mode")
    if mismatches:
        raise SourceDirectoryHybridContextError(
            "source_directory_hybrid_context_lexical_authority_mismatch",
            "The hybrid context packet must include admitted lexical context-packet authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _assert_vector_retrieval_authority(retrieval: Mapping[str, Any]) -> None:
    mismatches = []
    expected = {
        "retrieval_contract_id": VECTOR_RETRIEVAL_CONTRACT_ID,
        "retrieval_mode": VECTOR_RETRIEVAL_MODE,
        "embedding_contract_id": EMBEDDING_CONTRACT_ID,
        "embedding_mode": EMBEDDING_MODE,
        "vector_index_mode": VECTOR_INDEX_MODE,
        "feature_hash_version": FEATURE_HASH_VERSION,
    }
    for field, value in expected.items():
        if str(retrieval.get(field) or "") != value:
            mismatches.append(field)
    if int(retrieval.get("vector_dimensions") or 0) != VECTOR_DIMENSIONS:
        mismatches.append("vector_dimensions")
    if mismatches:
        raise SourceDirectoryHybridContextError(
            "source_directory_hybrid_context_vector_authority_mismatch",
            "The hybrid context packet must include admitted deterministic vector-retrieval authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _hybrid_items(
    *,
    lexical_items: list[Mapping[str, Any]],
    vector_items: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_segment: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(lexical_items):
        segment_id = str(item["segment_id"])
        by_segment[segment_id] = {
            "segment_id": segment_id,
            "segment_sequence": int(item["segment_sequence"]),
            "line_start": int(item["line_start"]),
            "line_end": int(item["line_end"]),
            "char_start": int(item["char_start"]),
            "char_end": int(item["char_end"]),
            "segment_hash": str(item["segment_hash"]),
            "text_excerpt": str(item.get("text_excerpt") or "")[:MAX_TEXT_EXCERPT_CHARS],
            "lexical_rank": int(item.get("rank_position") or index + 1),
            "lexical_matched_unique_query_terms": int(item.get("matched_unique_query_terms") or 0),
            "lexical_summed_term_frequency": int(item.get("summed_term_frequency") or 0),
            "vector_rank": None,
            "vector_score": "0.000000000000",
            "embedding_vector_hash": None,
            "vector_matched_unique_query_terms": 0,
            "vector_summed_query_term_frequency": 0,
        }
    for index, item in enumerate(vector_items):
        segment_id = str(item["segment_id"])
        target = by_segment.setdefault(
            segment_id,
            {
                "segment_id": segment_id,
                "segment_sequence": int(item["segment_sequence"]),
                "line_start": int(item["line_start"]),
                "line_end": int(item["line_end"]),
                "char_start": int(item["char_start"]),
                "char_end": int(item["char_end"]),
                "segment_hash": str(item["segment_hash"]),
                "text_excerpt": str(item.get("text") or "")[:MAX_TEXT_EXCERPT_CHARS],
                "lexical_rank": None,
                "lexical_matched_unique_query_terms": 0,
                "lexical_summed_term_frequency": 0,
                "vector_rank": None,
                "vector_score": "0.000000000000",
                "embedding_vector_hash": None,
                "vector_matched_unique_query_terms": 0,
                "vector_summed_query_term_frequency": 0,
            },
        )
        target["vector_rank"] = index + 1
        target["vector_score"] = str(item["vector_score"])
        target["embedding_vector_hash"] = str(item["embedding_vector_hash"])
        target["vector_matched_unique_query_terms"] = int(item.get("matched_unique_query_terms") or 0)
        target["vector_summed_query_term_frequency"] = int(item.get("summed_query_term_frequency") or 0)
    items = []
    for item in by_segment.values():
        lexical_component = Decimal("0")
        if item["lexical_rank"] is not None:
            lexical_component = Decimal("1") / Decimal(int(item["lexical_rank"]))
        vector_component = Decimal(str(item["vector_score"]))
        hybrid_score = lexical_component + vector_component
        items.append(
            {
                **item,
                "hybrid_score": f"{hybrid_score:.12f}",
                "included_by_lexical": item["lexical_rank"] is not None,
                "included_by_vector": item["vector_rank"] is not None,
            }
        )
    items.sort(
        key=lambda item: (
            -Decimal(str(item["hybrid_score"])),
            int(item["lexical_rank"] or 1_000_000),
            int(item["vector_rank"] or 1_000_000),
            int(item["segment_sequence"]),
            str(item["segment_id"]),
        )
    )
    for index, item in enumerate(items, start=1):
        item["hybrid_rank"] = index
    return items


def _hybrid_context_packet_hash(
    *,
    lexical_packet: Mapping[str, Any],
    vector_retrieval: Mapping[str, Any],
    hybrid_items: list[Mapping[str, Any]],
) -> str:
    return _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "hybrid_context_contract_id": CONTRACT_ID,
            "hybrid_context_mode": HYBRID_MODE,
            "source_gate": SOURCE_GATE,
            "lexical_context_packet_hash": lexical_packet["context_packet_hash"],
            "vector_retrieval_contract_id": vector_retrieval["retrieval_contract_id"],
            "vector_retrieval_mode": vector_retrieval["retrieval_mode"],
            "embedding_index_authority_hash": vector_retrieval["embedding_index_authority_hash"],
            "index_authority_hash": lexical_packet["index_authority_hash"],
            "source_ingestion_batch_id": lexical_packet["source_ingestion_batch_id"],
            "source_ingestion_file_id": lexical_packet["source_ingestion_file_id"],
            "material_snapshot_id": lexical_packet["material_snapshot_id"],
            "content_sha256": lexical_packet["content_sha256"],
            "file_identity_hash": lexical_packet["file_identity_hash"],
            "authority_basis_hash": lexical_packet["authority_basis_hash"],
            "payload_hash": lexical_packet["payload_hash"],
            "items": [
                {
                    "hybrid_rank": item["hybrid_rank"],
                    "segment_id": item["segment_id"],
                    "segment_sequence": item["segment_sequence"],
                    "segment_hash": item["segment_hash"],
                    "lexical_rank": item["lexical_rank"],
                    "vector_rank": item["vector_rank"],
                    "vector_score": item["vector_score"],
                    "hybrid_score": item["hybrid_score"],
                    "embedding_vector_hash": item["embedding_vector_hash"],
                    "included_by_lexical": item["included_by_lexical"],
                    "included_by_vector": item["included_by_vector"],
                }
                for item in hybrid_items
            ],
        }
    )


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
        raise SourceDirectoryHybridContextError(
            "source_directory_hybrid_context_required_field_missing",
            "A required source-directory hybrid context field is missing or empty.",
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
