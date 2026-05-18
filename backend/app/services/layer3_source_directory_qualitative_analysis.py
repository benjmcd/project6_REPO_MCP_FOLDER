from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_context_packet import (
    CONTEXT_PACKET_CONTRACT_ID,
    CONTEXT_PACKET_MODE,
    SCHEMA_ID as CONTEXT_PACKET_SCHEMA_ID,
    source_directory_material_retrieval_augmented_context_packet,
)
from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_qualitative_analysis.v1"
MODE = "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
ANALYSIS_CONTRACT_ID = "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
ANALYSIS_MODE = "context_packet_grounded_qualitative_hybrid_analysis"

_REQUIRED_FIELDS = {
    "client_request_id",
    "analysis_question",
    "analysis_focus",
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

_CONTEXT_PACKET_FIELDS = (
    _REQUIRED_FIELDS
    - {
        "analysis_question",
        "analysis_focus",
    }
) | _OPTIONAL_FIELDS

_FORBIDDEN_FIELDS = {
    "absolute_path",
    "analysis_run_id",
    "connector_target",
    "destination",
    "durable_write",
    "embedding",
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
    "recursive",
    "rewrite_output",
    "runtime_db_write",
    "semantic_score",
    "url",
    "vector",
    "vector_index",
    "web_connector",
}


class SourceDirectoryQualitativeAnalysisError(Exception):
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
            "request_id": "source-directory-qualitative-analysis-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_material_context_packet_qualitative_hybrid_analysis(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    analysis_question = _required(fields, "analysis_question")
    analysis_focus = _required(fields, "analysis_focus")

    context_packet = source_directory_material_retrieval_augmented_context_packet(
        db,
        _context_packet_payload(fields),
    )
    _assert_context_packet_authority(context_packet)

    items = list(context_packet.get("items") or [])
    supporting_segments = _supporting_segments(items)
    salient_terms = _salient_terms(context_packet.get("query_tokens") or [], items)
    evidence_summary = _evidence_summary(
        context_packet=context_packet,
        supporting_segments=supporting_segments,
        analysis_question=analysis_question,
    )
    coverage_notes = _coverage_notes(context_packet=context_packet, supporting_segments=supporting_segments)
    analysis_limits = _analysis_limits(supporting_segments=supporting_segments)
    negative_invariants = _negative_invariants()
    row_write_flags = {
        "source_index_rows_written": bool(context_packet.get("source_index_rows_written", False)),
        "retrieval_rows_written": bool(context_packet.get("retrieval_rows_written", False)),
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
    }
    qualitative_analysis_hash = _qualitative_analysis_hash(
        fields=fields,
        context_packet=context_packet,
        evidence_summary=evidence_summary,
        salient_terms=salient_terms,
        supporting_segments=supporting_segments,
        coverage_notes=coverage_notes,
        analysis_limits=analysis_limits,
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
        "analysis_contract_id": ANALYSIS_CONTRACT_ID,
        "analysis_mode": ANALYSIS_MODE,
        "qualitative_analysis_hash": qualitative_analysis_hash,
        "context_packet_contract_id": context_packet["context_packet_contract_id"],
        "context_packet_mode": context_packet["context_packet_mode"],
        "context_packet_hash": context_packet["context_packet_hash"],
        "analysis_question": analysis_question,
        "analysis_focus": analysis_focus,
        "query_tokens": list(context_packet.get("query_tokens") or []),
        "evidence_summary": evidence_summary,
        "salient_terms": salient_terms,
        "supporting_segments": supporting_segments,
        "coverage_notes": coverage_notes,
        "analysis_limits": analysis_limits,
        "total": int(context_packet["total"]),
        "limit": int(context_packet["limit"]),
        "offset": int(context_packet["offset"]),
        "index_contract_id": context_packet.get("index_contract_id"),
        "index_mode": context_packet.get("index_mode"),
        "segmentation_version": context_packet.get("segmentation_version"),
        "index_authority_hash": context_packet["index_authority_hash"],
        "source_ingestion_batch_id": context_packet["source_ingestion_batch_id"],
        "source_ingestion_file_id": context_packet["source_ingestion_file_id"],
        "material_snapshot_id": context_packet["material_snapshot_id"],
        "source_shape": context_packet.get("source_shape"),
        "content_sha256": context_packet["content_sha256"],
        "file_identity_hash": context_packet["file_identity_hash"],
        "authority_basis_hash": context_packet["authority_basis_hash"],
        "payload_hash": context_packet["payload_hash"],
        **row_write_flags,
        "negative_invariants": negative_invariants,
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryQualitativeAnalysisError(
            "source_directory_qualitative_analysis_forbidden_field_not_admitted",
            "The source-directory qualitative analysis request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryQualitativeAnalysisError(
            "source_directory_qualitative_analysis_unknown_field",
            "The source-directory qualitative analysis request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _context_packet_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_CONTEXT_PACKET_FIELDS) if field in fields}


def _assert_context_packet_authority(context_packet: Mapping[str, Any]) -> None:
    mismatches = []
    if str(context_packet.get("context_packet_contract_id") or "") != CONTEXT_PACKET_CONTRACT_ID:
        mismatches.append("context_packet_contract_id")
    if str(context_packet.get("context_packet_mode") or "") != CONTEXT_PACKET_MODE:
        mismatches.append("context_packet_mode")
    if str(context_packet.get("schema_id") or "") != CONTEXT_PACKET_SCHEMA_ID:
        mismatches.append("schema_id")
    if mismatches:
        raise SourceDirectoryQualitativeAnalysisError(
            "source_directory_qualitative_analysis_context_packet_authority_mismatch",
            "The source-directory qualitative analysis runtime must be assembled from admitted context-packet authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _supporting_segments(items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        segments.append(
            {
                "segment_id": str(item["segment_id"]),
                "rank_position": int(item["rank_position"]),
                "segment_sequence": int(item["segment_sequence"]),
                "line_range": {
                    "start": int(item["line_start"]),
                    "end": int(item["line_end"]),
                },
                "segment_hash": str(item["segment_hash"]),
                "quote_excerpt": str(item.get("text_excerpt") or ""),
                "matched_unique_query_terms": int(item["matched_unique_query_terms"]),
                "summed_term_frequency": int(item["summed_term_frequency"]),
                "support_label": "primary_context_segment" if index == 0 else "supporting_context_segment",
            }
        )
    return segments


def _salient_terms(query_tokens: list[Any], items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    for token in [str(value) for value in query_tokens]:
        matched_segments = 0
        summed_frequency = 0
        for item in items:
            counts = Counter(normalize_query_tokens(str(item.get("text_excerpt") or "")))
            frequency = int(counts.get(token, 0))
            if frequency > 0:
                matched_segments += 1
                summed_frequency += frequency
        terms.append(
            {
                "term": token,
                "matched_segments": matched_segments,
                "summed_term_frequency": summed_frequency,
            }
        )
    return terms


def _evidence_summary(
    *,
    context_packet: Mapping[str, Any],
    supporting_segments: list[Mapping[str, Any]],
    analysis_question: str,
) -> dict[str, Any]:
    total = int(context_packet["total"])
    considered = len(supporting_segments)
    if total == 0:
        coverage_label = "no_context_matches"
    elif considered < total:
        coverage_label = "paged_context_matches"
    else:
        coverage_label = "complete_context_matches"
    return {
        "summary_kind": "deterministic_context_packet_evidence_summary",
        "analysis_question_token_count": len(normalize_query_tokens(analysis_question)),
        "context_packet_total_matches": total,
        "context_segments_considered": considered,
        "top_rank_position": int(supporting_segments[0]["rank_position"]) if supporting_segments else 0,
        "matched_query_tokens": list(context_packet.get("query_tokens") or []),
        "coverage_label": coverage_label,
    }


def _coverage_notes(
    *,
    context_packet: Mapping[str, Any],
    supporting_segments: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    total = int(context_packet["total"])
    notes = [
        {
            "code": "context_packet_authority_validated",
            "message": "Context packet authority fields were validated before qualitative analysis assembly.",
        }
    ]
    if total == 0:
        notes.append(
            {
                "code": "no_context_matches",
                "message": "No context packet segments matched the normalized query tokens.",
            }
        )
    elif len(supporting_segments) < total:
        notes.append(
            {
                "code": "context_packet_paged",
                "message": "Qualitative analysis used the current bounded context-packet page only.",
            }
        )
    else:
        notes.append(
            {
                "code": "context_packet_complete_page",
                "message": "Qualitative analysis used all matching context-packet segments returned by the request.",
            }
        )
    return notes


def _analysis_limits(*, supporting_segments: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    limits = [
        {
            "code": "deterministic_extractive_only",
            "message": "Analysis uses deterministic extraction over context-packet items only.",
        },
        {
            "code": "no_prompt_model_provider_runtime",
            "message": "No prompt, model, provider, hidden planning, or qualitative generation runtime is admitted.",
        },
        {
            "code": "no_vector_or_embedding_runtime",
            "message": "No vector indexing, embeddings, semantic scoring, or RAG index runtime is admitted.",
        },
        {
            "code": "no_durable_qualitative_rows",
            "message": "No durable qualitative analysis, analysis-run, package, connector, or frontend state is written.",
        },
    ]
    if not supporting_segments:
        limits.append(
            {
                "code": "no_supporting_segments",
                "message": "No deterministic supporting segment was available for extractive analysis.",
            }
        )
    return limits


def _qualitative_analysis_hash(
    *,
    fields: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    evidence_summary: Mapping[str, Any],
    salient_terms: list[Mapping[str, Any]],
    supporting_segments: list[Mapping[str, Any]],
    coverage_notes: list[Mapping[str, Any]],
    analysis_limits: list[Mapping[str, Any]],
    row_write_flags: Mapping[str, bool],
    negative_invariants: Mapping[str, bool],
) -> str:
    return _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "analysis_contract_id": ANALYSIS_CONTRACT_ID,
            "analysis_mode": ANALYSIS_MODE,
            "request_contract": {
                field: str(fields.get(field) or "")
                for field in sorted(_REQUIRED_FIELDS)
            },
            "limit": int(context_packet["limit"]),
            "offset": int(context_packet["offset"]),
            "context_packet_contract_id": context_packet["context_packet_contract_id"],
            "context_packet_mode": context_packet["context_packet_mode"],
            "context_packet_schema_id": context_packet["schema_id"],
            "context_packet_hash": context_packet["context_packet_hash"],
            "query_tokens": list(context_packet.get("query_tokens") or []),
            "source_authority": {
                "index_authority_hash": context_packet["index_authority_hash"],
                "source_ingestion_batch_id": context_packet["source_ingestion_batch_id"],
                "source_ingestion_file_id": context_packet["source_ingestion_file_id"],
                "material_snapshot_id": context_packet["material_snapshot_id"],
                "content_sha256": context_packet["content_sha256"],
                "file_identity_hash": context_packet["file_identity_hash"],
                "authority_basis_hash": context_packet["authority_basis_hash"],
                "payload_hash": context_packet["payload_hash"],
            },
            "evidence_refs": [
                {
                    "segment_id": item["segment_id"],
                    "rank_position": item["rank_position"],
                    "segment_sequence": item["segment_sequence"],
                    "line_range": item["line_range"],
                    "segment_hash": item["segment_hash"],
                    "matched_unique_query_terms": item["matched_unique_query_terms"],
                    "summed_term_frequency": item["summed_term_frequency"],
                }
                for item in supporting_segments
            ],
            "analysis_sections": {
                "evidence_summary": evidence_summary,
                "salient_terms": salient_terms,
                "supporting_segments": supporting_segments,
                "coverage_notes": coverage_notes,
                "analysis_limits": analysis_limits,
            },
            "row_write_flags": row_write_flags,
            "negative_invariants": negative_invariants,
        }
    )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryQualitativeAnalysisError(
            "source_directory_qualitative_analysis_required_field_missing",
            "A required source-directory qualitative analysis field is missing or empty.",
            details={"field": key},
        )
    return value


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
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
