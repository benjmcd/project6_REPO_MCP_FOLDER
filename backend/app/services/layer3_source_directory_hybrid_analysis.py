from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services.layer3_source_directory_hybrid_context import (
    CONTRACT_ID as HYBRID_CONTEXT_CONTRACT_ID,
    HYBRID_MODE as HYBRID_CONTEXT_MODE,
    SCHEMA_ID as HYBRID_CONTEXT_SCHEMA_ID,
    source_directory_material_hybrid_retrieval_context_packet,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_hybrid_context_packet_qualitative_analysis.v1"
MODE = "source_directory_hybrid_context_packet_qualitative_analysis_authority"
ANALYSIS_CONTRACT_ID = "source_directory_hybrid_context_packet_qualitative_analysis_authority"
ANALYSIS_MODE = "hybrid_context_packet_grounded_qualitative_analysis"
SOURCE_GATE = "824_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_RUNTIME_ENTRY_FREEZE"
PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview.v1"
)
PACKAGE_REVIEW_PREVIEW_MODE = (
    "read_only_source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview"
)
PACKAGE_REVIEW_PREVIEW_SOURCE_GATE = (
    "826_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE"
)
PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

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
    "embedding_index_authority_hash",
    "query_text",
}

_OPTIONAL_FIELDS = {"limit", "offset", "top_k"}

_HYBRID_CONTEXT_FIELDS = (
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


class SourceDirectoryHybridAnalysisError(Exception):
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
            "request_id": "source-directory-hybrid-context-qualitative-analysis-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_hybrid_context_packet_qualitative_analysis(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    analysis_question = _required(fields, "analysis_question")
    analysis_focus = _required(fields, "analysis_focus")

    hybrid_context = source_directory_material_hybrid_retrieval_context_packet(
        db,
        _hybrid_context_payload(fields),
    )
    _assert_hybrid_context_authority(hybrid_context)

    items = list(hybrid_context.get("items") or [])
    supporting_segments = _supporting_segments(items)
    salient_terms = _salient_terms(hybrid_context.get("query_tokens") or [], items)
    evidence_summary = _evidence_summary(
        hybrid_context=hybrid_context,
        supporting_segments=supporting_segments,
        analysis_question=analysis_question,
    )
    coverage_notes = _coverage_notes(
        hybrid_context=hybrid_context,
        supporting_segments=supporting_segments,
    )
    analysis_limits = _analysis_limits()
    row_write_flags = _row_write_flags()
    negative_invariants = _negative_invariants()
    qualitative_analysis_hash = _qualitative_analysis_hash(
        fields=fields,
        hybrid_context=hybrid_context,
        evidence_summary=evidence_summary,
        salient_terms=salient_terms,
        supporting_segments=supporting_segments,
        coverage_notes=coverage_notes,
        analysis_limits=analysis_limits,
        row_write_flags=row_write_flags,
        negative_invariants=negative_invariants,
    )
    package_review_preview = _package_review_preview(
        request_id=request_id,
        fields=fields,
        hybrid_context=hybrid_context,
        qualitative_analysis_hash=qualitative_analysis_hash,
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
        "source_gate": SOURCE_GATE,
        "qualitative_analysis_hash": qualitative_analysis_hash,
        "analysis_question": analysis_question,
        "analysis_focus": analysis_focus,
        "hybrid_context_packet_hash": hybrid_context["hybrid_context_packet_hash"],
        "hybrid_context_contract_id": hybrid_context["hybrid_context_contract_id"],
        "hybrid_context_mode": hybrid_context["hybrid_context_mode"],
        "validated_hybrid_context_schema_id": hybrid_context["schema_id"],
        "validated_hybrid_context_mode": hybrid_context["mode"],
        "lexical_context_packet_hash": hybrid_context["lexical_context_packet_hash"],
        "lexical_context_packet_contract_id": hybrid_context["lexical_context_packet_contract_id"],
        "lexical_context_packet_mode": hybrid_context["lexical_context_packet_mode"],
        "vector_retrieval_contract_id": hybrid_context["vector_retrieval_contract_id"],
        "vector_retrieval_mode": hybrid_context["vector_retrieval_mode"],
        "embedding_contract_id": hybrid_context["embedding_contract_id"],
        "embedding_mode": hybrid_context["embedding_mode"],
        "vector_index_mode": hybrid_context["vector_index_mode"],
        "feature_hash_version": hybrid_context["feature_hash_version"],
        "vector_dimensions": hybrid_context["vector_dimensions"],
        "query_tokens": list(hybrid_context.get("query_tokens") or []),
        "evidence_summary": evidence_summary,
        "salient_terms": salient_terms,
        "supporting_segments": supporting_segments,
        "coverage_notes": coverage_notes,
        "analysis_limits": analysis_limits,
        "lexical_total": int(hybrid_context["lexical_total"]),
        "lexical_limit": int(hybrid_context["lexical_limit"]),
        "lexical_offset": int(hybrid_context["lexical_offset"]),
        "vector_total": int(hybrid_context["vector_total"]),
        "vector_top_k": int(hybrid_context["vector_top_k"]),
        "hybrid_total": int(hybrid_context["hybrid_total"]),
        "index_authority_hash": hybrid_context["index_authority_hash"],
        "embedding_index_authority_hash": hybrid_context["embedding_index_authority_hash"],
        "source_ingestion_batch_id": hybrid_context["source_ingestion_batch_id"],
        "source_ingestion_file_id": hybrid_context["source_ingestion_file_id"],
        "material_snapshot_id": hybrid_context["material_snapshot_id"],
        "source_shape": hybrid_context.get("source_shape"),
        "content_sha256": hybrid_context["content_sha256"],
        "file_identity_hash": hybrid_context["file_identity_hash"],
        "authority_basis_hash": hybrid_context["authority_basis_hash"],
        "payload_hash": hybrid_context["payload_hash"],
        "source_directory_package_review_preview_enabled": True,
        "source_directory_hybrid_package_review_preview_hash": package_review_preview[
            "package_review_preview_hash"
        ],
        "source_directory_hybrid_package_review_preview": package_review_preview,
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        "package_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
        **row_write_flags,
        "negative_invariants": negative_invariants,
        "next_allowed_actions": [],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_forbidden_field_not_admitted",
            "The source-directory hybrid-context qualitative-analysis request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_unknown_field",
            "The source-directory hybrid-context qualitative-analysis request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _hybrid_context_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_HYBRID_CONTEXT_FIELDS) if field in fields}


def _assert_hybrid_context_authority(context: Mapping[str, Any]) -> None:
    mismatches = []
    expected = {
        "schema_id": HYBRID_CONTEXT_SCHEMA_ID,
        "hybrid_context_contract_id": HYBRID_CONTEXT_CONTRACT_ID,
        "hybrid_context_mode": HYBRID_CONTEXT_MODE,
    }
    for field, value in expected.items():
        if str(context.get(field) or "") != value:
            mismatches.append(field)
    if str(context.get("mode") or "") != "source_directory_hybrid_retrieval_context_packet_authority":
        mismatches.append("mode")
    if mismatches:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_authority_mismatch",
            "The qualitative-analysis reader requires admitted source-directory hybrid context-packet authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _package_review_preview(
    *,
    request_id: str,
    fields: Mapping[str, Any],
    hybrid_context: Mapping[str, Any],
    qualitative_analysis_hash: str,
) -> dict[str, Any]:
    source_authority = {
        "source_ingestion_batch_id": hybrid_context["source_ingestion_batch_id"],
        "source_ingestion_file_id": hybrid_context["source_ingestion_file_id"],
        "material_snapshot_id": hybrid_context["material_snapshot_id"],
        "content_sha256": hybrid_context["content_sha256"],
        "file_identity_hash": hybrid_context["file_identity_hash"],
        "authority_basis_hash": hybrid_context["authority_basis_hash"],
        "payload_hash": hybrid_context["payload_hash"],
        "index_authority_hash": hybrid_context["index_authority_hash"],
        "embedding_index_authority_hash": hybrid_context["embedding_index_authority_hash"],
        "lexical_context_packet_hash": hybrid_context["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": hybrid_context["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis_hash,
    }
    candidate_packages = [
        {
            "package_kind": package_kind,
            "preview_only": True,
            "package_commit_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "external_export_download_enabled": False,
            "readiness_reason": (
                "source-directory hybrid qualitative-analysis package construction is not admitted in this boundary"
            ),
        }
        for package_kind in PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS
    ]
    negative_invariants = {
        "read_only_preview": True,
        "package_rows_written": False,
        "package_payload_written": False,
        "package_construction_enabled": False,
        "package_mutation_enabled": False,
        "source_package_row_mutation_enabled": False,
        "handoff_export_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
    }
    package_review_preview_hash = _stable_hash(
        {
            "schema_id": PACKAGE_REVIEW_PREVIEW_SCHEMA_ID,
            "schema_version": 1,
            "mode": PACKAGE_REVIEW_PREVIEW_MODE,
            "source_gate": PACKAGE_REVIEW_PREVIEW_SOURCE_GATE,
            "request_id": request_id,
            "analysis_question": str(fields.get("analysis_question") or ""),
            "analysis_focus": str(fields.get("analysis_focus") or ""),
            "query_text": str(fields.get("query_text") or ""),
            "source_authority": source_authority,
            "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
            "negative_invariants": negative_invariants,
        }
    )
    return {
        "schema_id": PACKAGE_REVIEW_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "mode": PACKAGE_REVIEW_PREVIEW_MODE,
        "source_gate": PACKAGE_REVIEW_PREVIEW_SOURCE_GATE,
        "status": "available",
        "package_review_preview_hash": package_review_preview_hash,
        "source_authority": source_authority,
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        "candidate_packages": candidate_packages,
        "package_review_preview_enabled": True,
        "package_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
        "next_state": "source_directory_hybrid_package_review_preview_available",
        "next_allowed_actions": [],
        "negative_invariants": negative_invariants,
    }


def _supporting_segments(items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for item in items:
        segments.append(
            {
                "segment_id": str(item["segment_id"]),
                "rank_position": int(item["hybrid_rank"]),
                "hybrid_rank": int(item["hybrid_rank"]),
                "lexical_rank": item.get("lexical_rank"),
                "vector_rank": item.get("vector_rank"),
                "hybrid_score": str(item["hybrid_score"]),
                "vector_score": str(item["vector_score"]),
                "included_by_lexical": bool(item["included_by_lexical"]),
                "included_by_vector": bool(item["included_by_vector"]),
                "segment_sequence": int(item["segment_sequence"]),
                "line_range": {
                    "start": int(item["line_start"]),
                    "end": int(item["line_end"]),
                },
                "segment_hash": str(item["segment_hash"]),
                "quote_excerpt": str(item.get("text_excerpt") or ""),
                "matched_unique_query_terms": max(
                    int(item.get("lexical_matched_unique_query_terms") or 0),
                    int(item.get("vector_matched_unique_query_terms") or 0),
                ),
                "summed_term_frequency": (
                    int(item.get("lexical_summed_term_frequency") or 0)
                    + int(item.get("vector_summed_query_term_frequency") or 0)
                ),
                "support_label": (
                    "primary_hybrid_context_segment"
                    if int(item["hybrid_rank"]) == 1
                    else "supporting_hybrid_context_segment"
                ),
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
    hybrid_context: Mapping[str, Any],
    supporting_segments: list[Mapping[str, Any]],
    analysis_question: str,
) -> dict[str, Any]:
    hybrid_total = int(hybrid_context["hybrid_total"])
    considered = len(supporting_segments)
    if hybrid_total == 0:
        coverage_label = "no_hybrid_context_matches"
    elif considered < hybrid_total:
        coverage_label = "paged_hybrid_context_matches"
    else:
        coverage_label = "complete_hybrid_context_matches"
    return {
        "summary_kind": "deterministic_hybrid_context_packet_evidence_summary",
        "analysis_question_token_count": len(normalize_query_tokens(analysis_question)),
        "hybrid_context_total_matches": hybrid_total,
        "lexical_total_matches": int(hybrid_context["lexical_total"]),
        "vector_total_matches": int(hybrid_context["vector_total"]),
        "context_segments_considered": considered,
        "top_rank_position": int(supporting_segments[0]["rank_position"]) if supporting_segments else 0,
        "matched_query_tokens": list(hybrid_context.get("query_tokens") or []),
        "coverage_label": coverage_label,
    }


def _coverage_notes(
    *,
    hybrid_context: Mapping[str, Any],
    supporting_segments: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    lexical_inclusions = sum(1 for item in supporting_segments if item["included_by_lexical"])
    vector_inclusions = sum(1 for item in supporting_segments if item["included_by_vector"])
    notes = [
        {
            "code": "hybrid_context_packet_authority_validated",
            "message": "Hybrid context-packet authority fields were validated before qualitative analysis assembly.",
        },
        {
            "code": "hybrid_context_packet_sources_redacted",
            "message": "The qualitative analysis uses redacted text excerpts and does not expose raw vectors or local paths.",
        },
        {
            "code": "hybrid_context_packet_fusion_observed",
            "message": "Lexical and vector inclusion counts are reported from the validated hybrid context packet.",
            "lexical_inclusion_count": lexical_inclusions,
            "vector_inclusion_count": vector_inclusions,
        },
    ]
    if int(hybrid_context["hybrid_total"]) == 0:
        notes.append(
            {
                "code": "no_hybrid_context_matches",
                "message": "The validated hybrid context packet produced no matching segments.",
            }
        )
    return notes


def _analysis_limits() -> list[dict[str, Any]]:
    return [
        {
            "code": "deterministic_reader_only",
            "message": "This analysis is assembled deterministically from the admitted hybrid context packet.",
        },
        {
            "code": "no_prompt_model_provider_runtime",
            "message": "No prompt, model, provider, RAG execution, network, or qualitative generation runtime is used.",
        },
        {
            "code": "no_package_or_delivery_authority",
            "message": "Package construction, package review, handoff/export, provider delivery, and connector dispatch remain blocked.",
        },
    ]


def _qualitative_analysis_hash(
    *,
    fields: Mapping[str, Any],
    hybrid_context: Mapping[str, Any],
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
            "source_gate": SOURCE_GATE,
            "request_contract": {
                field: str(fields.get(field) or "")
                for field in sorted(_REQUIRED_FIELDS)
            },
            "hybrid_context_packet_hash": hybrid_context["hybrid_context_packet_hash"],
            "hybrid_context_contract_id": hybrid_context["hybrid_context_contract_id"],
            "hybrid_context_mode": hybrid_context["hybrid_context_mode"],
            "lexical_context_packet_hash": hybrid_context["lexical_context_packet_hash"],
            "vector_retrieval_contract_id": hybrid_context["vector_retrieval_contract_id"],
            "vector_retrieval_mode": hybrid_context["vector_retrieval_mode"],
            "embedding_index_authority_hash": hybrid_context["embedding_index_authority_hash"],
            "index_authority_hash": hybrid_context["index_authority_hash"],
            "evidence_refs": [
                {
                    "segment_id": item["segment_id"],
                    "rank_position": item["rank_position"],
                    "hybrid_rank": item["hybrid_rank"],
                    "lexical_rank": item["lexical_rank"],
                    "vector_rank": item["vector_rank"],
                    "hybrid_score": item["hybrid_score"],
                    "segment_sequence": item["segment_sequence"],
                    "line_range": item["line_range"],
                    "segment_hash": item["segment_hash"],
                    "matched_unique_query_terms": item["matched_unique_query_terms"],
                    "summed_term_frequency": item["summed_term_frequency"],
                    "included_by_lexical": item["included_by_lexical"],
                    "included_by_vector": item["included_by_vector"],
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


def _row_write_flags() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "qualitative_generation_rows_written": False,
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
        "package_construction_enabled": False,
        "package_review_submit_enabled": False,
        "package_mutation_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "frontend_durable_authority_enabled": False,
        "network_egress_enabled": False,
        "raw_local_path_exposed": False,
        "raw_vector_exposed": False,
    }


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_required_field_missing",
            "A required source-directory hybrid-context qualitative-analysis field is missing or empty.",
            details={"field": key},
        )
    return value


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
