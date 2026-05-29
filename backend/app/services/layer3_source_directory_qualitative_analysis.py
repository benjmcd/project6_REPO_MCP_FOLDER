from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import L3MaterialSnapshot, L3OutputPackage, L3ReconciliationRecord, L3Session
from app.services.layer3_external_export_contract import ExternalExportDownloadDelivery
from app.services.layer3_source_directory_context_packet import (
    CONTEXT_PACKET_CONTRACT_ID,
    CONTEXT_PACKET_MODE,
    SCHEMA_ID as CONTEXT_PACKET_SCHEMA_ID,
    source_directory_material_retrieval_augmented_context_packet,
)
from app.services.layer3_package_entry import (
    FINALIZED_PACKAGE_SESSION_STATUSES,
    Layer3PackageEntryError,
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
    SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
    materialize_source_directory_qualitative_analysis_package_commit,
)
from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.layer3_utils import json_clone as _json_clone, stable_id as _stable_id
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_qualitative_analysis.v1"
MODE = "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
ANALYSIS_CONTRACT_ID = "source_directory_material_context_packet_qualitative_hybrid_analysis_authority"
ANALYSIS_MODE = "context_packet_grounded_qualitative_hybrid_analysis"
ANALYSIS_STATUS_SCHEMA_ID = "layer3.source_directory_qualitative_analysis_status.v1"
ANALYSIS_STATUS_MODE = "source_directory_qualitative_hybrid_analysis_status_authority"
ANALYSIS_STATUS_SOURCE_GATE = "818_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_STATUS_RUNTIME_ENTRY_FREEZE"
PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = "layer3.source_directory_qualitative_analysis_package_review_preview.v1"
PACKAGE_REVIEW_PREVIEW_MODE = "read_only_source_directory_qualitative_analysis_package_review_preview"
PACKAGE_REVIEW_PREVIEW_SOURCE_GATE = "802_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE"
PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)
PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = "layer3.source_directory_qualitative_analysis_package_commit.v1"
PACKAGE_CONSTRUCTION_COMMIT_MODE = "source_directory_qualitative_analysis_package_commit_authority"
PACKAGE_CONSTRUCTION_OPERATOR_DECISION = "commit_source_directory_qualitative_analysis_package"
PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = "layer3.source_directory_qualitative_analysis_package_review_submit.v1"
PACKAGE_REVIEW_SUBMIT_MODE = "source_directory_qualitative_analysis_package_review_submit_authority"
PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID = "layer3.package_review_submit_state.v1"
PACKAGE_REVIEW_SUBMIT_SOURCE_GATE = "806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID = "layer3.source_directory_qualitative_analysis_package_supersession_preview.v1"
PACKAGE_SUPERSESSION_PREVIEW_MODE = "source_directory_qualitative_analysis_package_supersession_preview_authority"
PACKAGE_SUPERSESSION_PREVIEW_SOURCE_GATE = (
    "820_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_ENTRY_FREEZE"
)
PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = "preview_source_directory_package_supersession"
HANDOFF_EXPORT_PREPARE_SCHEMA_ID = "layer3.source_directory_qualitative_analysis_handoff_export_prepare.v1"
HANDOFF_EXPORT_PREPARE_MODE = "source_directory_qualitative_analysis_handoff_export_prepare_authority"
HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID = "layer3.handoff_export_prepare_state.v1"
HANDOFF_EXPORT_PREPARE_SOURCE_GATE = "808_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE"
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = (
    "layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1"
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_MODE = (
    "source_directory_qualitative_analysis_external_export_download_prepare_authority"
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID = "layer3.external_export_download_prepare_state.v1"
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE = (
    "812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = (
    "layer3.source_directory_qualitative_analysis_external_export_download_delivery.v1"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID = (
    "layer3.source_directory_qualitative_analysis_external_export_download_delivery_status.v1"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE = (
    "source_directory_qualitative_analysis_external_export_download_delivery_authority"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_MODE = (
    "source_directory_qualitative_analysis_external_export_download_delivery_status_authority"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SOURCE_GATE = (
    "814_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SOURCE_GATE = (
    "816_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_RUNTIME_ENTRY_FREEZE"
)
EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION = "prepare_source_directory_external_export_download"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION = "deliver_source_directory_external_export_download"
EXTERNAL_EXPORT_DOWNLOAD_TARGET = "source_directory_qualitative_analysis_package_download_reference"
EXTERNAL_EXPORT_DOWNLOAD_MODE = "reference_only_prepare"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE = "same_origin_artifact_stream"
EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE = "external_export_download_prepared"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE = "external_export_download_delivered"
PACKAGE_REVIEW_APPROVED_STATE = "package_review_approved"
PACKAGE_REVIEW_CHANGES_REQUESTED_STATE = "package_review_changes_requested"
PACKAGE_REVIEW_REJECTED_STATE = "package_review_rejected"
PACKAGE_REVIEW_BLOCKED_STATE = "package_review_blocked"
PACKAGE_REVIEW_SUBMIT_DECISIONS = frozenset({"approved", "changes_requested", "rejected", "blocked"})
PACKAGE_REVIEW_SUBMIT_STATE_BY_DECISION = {
    "approved": PACKAGE_REVIEW_APPROVED_STATE,
    "changes_requested": PACKAGE_REVIEW_CHANGES_REQUESTED_STATE,
    "rejected": PACKAGE_REVIEW_REJECTED_STATE,
    "blocked": PACKAGE_REVIEW_BLOCKED_STATE,
}
PACKAGE_REVIEW_SUBMIT_NOTE_REQUIRED_DECISIONS = frozenset({"changes_requested", "rejected", "blocked"})
PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE = (
    "handoff",
    "export",
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_delivery",
)
HANDOFF_EXPORT_PREPARED_STATE = "handoff_export_prepared"
HANDOFF_EXPORT_HELD_STATE = "handoff_export_held"
HANDOFF_EXPORT_DECLINED_STATE = "handoff_export_declined"
HANDOFF_EXPORT_BLOCKED_STATE = "handoff_export_blocked"
HANDOFF_EXPORT_PREPARE_DECISIONS = frozenset({"authorize_prepare", "hold", "decline", "blocked"})
HANDOFF_EXPORT_PREPARE_STATE_BY_DECISION = {
    "authorize_prepare": HANDOFF_EXPORT_PREPARED_STATE,
    "hold": HANDOFF_EXPORT_HELD_STATE,
    "decline": HANDOFF_EXPORT_DECLINED_STATE,
    "blocked": HANDOFF_EXPORT_BLOCKED_STATE,
}
HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION = {
    "authorize_prepare": "prepared",
    "hold": "held",
    "decline": "declined",
    "blocked": "blocked",
}
HANDOFF_EXPORT_PREPARE_NOTE_REQUIRED_DECISIONS = frozenset({"hold", "decline", "blocked"})
HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE = (
    "aps_handoff",
    "external_export_download",
    "connector_dispatch",
    "provider_public_delivery",
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE = (
    "same_origin_delivery",
    "provider_public_delivery",
    "provider_private_signed_url",
    "connector_dispatch",
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
    "query_text",
}

_OPTIONAL_FIELDS = {"limit", "offset"}

_PACKAGE_COMMIT_REQUIRED_FIELDS = _REQUIRED_FIELDS | {
    "qualitative_analysis_hash",
    "source_directory_package_review_preview_hash",
    "operator_decision",
}

_PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS = _REQUIRED_FIELDS | {
    "qualitative_analysis_hash",
    "source_directory_package_review_preview_hash",
    "construction_basis_hash",
    "reconciliation_record_id",
    "output_package_ids",
    "package_kinds",
    "payload_hashes",
    "operator_decision",
}

_HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS = _PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS | {
    "package_review_submit_record_ref",
    "package_review_state",
    "handoff_target",
    "export_mode",
}
_PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS = _PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS | {
    "package_review_submit_record_ref",
    "package_review_state",
}

_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS = _HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS | {
    "prepare_record_ref",
    "handoff_export_state",
    "handoff_export_envelope_ref",
    "external_export_download_target",
    "download_mode",
}
_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS = _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS | {
    "external_export_download_record_ref",
    "export_download_descriptor_ref",
    "external_export_download_state",
    "delivery_mode",
    "output_package_id",
    "package_kind",
    "package_payload_hash",
}

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

_HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS = _FORBIDDEN_FIELDS | {
    "aps_handoff",
    "connector_dispatch",
    "connector_payload",
    "dispatch",
    "download",
    "external_export",
    "provider_private_signed_url",
    "send",
    "signed_url",
}

_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS = _HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS | {
    "delivery",
    "delivery_mode",
    "download_url",
    "external_local_export",
    "local_outbox",
    "network_egress",
    "provider_public_url",
    "raw_payload_ref",
}
_PACKAGE_SUPERSESSION_PREVIEW_FORBIDDEN_FIELDS = _FORBIDDEN_FIELDS | {
    "artifact_manifest",
    "corrected_package_payloads",
    "delete_package",
    "edited_package_content",
    "mutate_package",
    "package_payload",
    "package_payload_rewrite",
    "package_variant_content",
    "rebuild_package",
    "replace_package",
    "replacement_package_payloads",
    "source_package_row_mutation",
    "update_package_row",
}
_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS = (
    _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS - {"delivery_mode", "output_package_id"}
) | {
    "bucket",
    "connector_run_id",
    "connector_secret",
    "destination",
    "destination_id",
    "download_token",
    "external_target",
    "local_file_path",
    "object_key",
    "provider_secret",
    "provider_token",
    "provider_url",
    "public_url",
    "signed_url",
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


class SourceDirectoryPackageCommitError(Exception):
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
            "schema_id": PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-package-commit-error",
            "server_time": _server_time(),
            "mode": PACKAGE_CONSTRUCTION_COMMIT_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryPackageReviewSubmitError(Exception):
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
            "schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-package-review-submit-error",
            "server_time": _server_time(),
            "mode": PACKAGE_REVIEW_SUBMIT_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryPackageSupersessionPreviewError(Exception):
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
            "schema_id": PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-package-supersession-preview-error",
            "server_time": _server_time(),
            "mode": PACKAGE_SUPERSESSION_PREVIEW_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHandoffExportPrepareError(Exception):
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
            "schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-handoff-export-prepare-error",
            "server_time": _server_time(),
            "mode": HANDOFF_EXPORT_PREPARE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryExternalExportDownloadPrepareError(Exception):
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
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-external-export-download-prepare-error",
            "server_time": _server_time(),
            "mode": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryExternalExportDownloadDeliveryError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = dict(details or {})

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-external-export-download-delivery-error",
            "server_time": _server_time(),
            "mode": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE,
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
    package_review_preview = _source_directory_package_review_preview(
        request_id=request_id,
        fields=fields,
        context_packet=context_packet,
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
        "qualitative_analysis_hash": qualitative_analysis_hash,
        "source_directory_package_review_preview_enabled": True,
        "source_directory_package_review_preview_hash": package_review_preview["package_review_preview_hash"],
        "source_directory_package_review_preview": package_review_preview,
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        "package_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
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


def source_directory_qualitative_hybrid_analysis_status(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(db, payload)
    negative_invariants = dict(analysis["negative_invariants"])
    return {
        "schema_id": ANALYSIS_STATUS_SCHEMA_ID,
        "schema_version": 1,
        "request_id": analysis["request_id"],
        "server_time": _server_time(),
        "mode": ANALYSIS_STATUS_MODE,
        "status": "available",
        "analysis_status": "source_directory_qualitative_hybrid_analysis_available",
        "source_gate": ANALYSIS_STATUS_SOURCE_GATE,
        "validated_analysis_schema_id": analysis["schema_id"],
        "validated_analysis_mode": analysis["mode"],
        "analysis_contract_id": analysis["analysis_contract_id"],
        "analysis_mode": analysis["analysis_mode"],
        "qualitative_analysis_hash": analysis["qualitative_analysis_hash"],
        "context_packet_contract_id": analysis["context_packet_contract_id"],
        "context_packet_mode": analysis["context_packet_mode"],
        "context_packet_hash": analysis["context_packet_hash"],
        "source_directory_package_review_preview_available": True,
        "source_directory_package_review_preview_hash": analysis[
            "source_directory_package_review_preview_hash"
        ],
        "source_directory_package_review_preview_payload_redacted": True,
        "supporting_segments_redacted": True,
        "analysis_result_redacted": True,
        "query_tokens": list(analysis["query_tokens"]),
        "coverage_label": str(analysis["evidence_summary"].get("coverage_label") or ""),
        "supporting_segment_count": len(analysis["supporting_segments"]),
        "salient_term_count": len(analysis["salient_terms"]),
        "coverage_note_count": len(analysis["coverage_notes"]),
        "analysis_limit_count": len(analysis["analysis_limits"]),
        "total": int(analysis["total"]),
        "limit": int(analysis["limit"]),
        "offset": int(analysis["offset"]),
        "index_contract_id": analysis.get("index_contract_id"),
        "index_mode": analysis.get("index_mode"),
        "segmentation_version": analysis.get("segmentation_version"),
        "index_authority_hash": analysis["index_authority_hash"],
        "source_ingestion_batch_id": analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": analysis["source_ingestion_file_id"],
        "material_snapshot_id": analysis["material_snapshot_id"],
        "source_shape": analysis.get("source_shape"),
        "content_sha256": analysis["content_sha256"],
        "file_identity_hash": analysis["file_identity_hash"],
        "authority_basis_hash": analysis["authority_basis_hash"],
        "payload_hash": analysis["payload_hash"],
        "source_index_rows_written": bool(analysis["source_index_rows_written"]),
        "retrieval_rows_written": bool(analysis["retrieval_rows_written"]),
        "context_packet_rows_written": bool(analysis["context_packet_rows_written"]),
        "qualitative_analysis_rows_written": bool(analysis["qualitative_analysis_rows_written"]),
        "qualitative_generation_rows_written": bool(analysis["qualitative_generation_rows_written"]),
        "analysis_run_rows_written": bool(analysis["analysis_run_rows_written"]),
        "package_rows_written": bool(analysis["package_rows_written"]),
        "connector_rows_written": bool(analysis["connector_rows_written"]),
        "negative_invariants": negative_invariants,
        "next_allowed_actions": ["inspect_source_directory_qualitative_hybrid_analysis"],
    }


def source_directory_qualitative_analysis_package_commit(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_package_commit_payload(payload)
    request_id = _required(fields, "client_request_id")
    if str(fields.get("operator_decision") or "") != PACKAGE_CONSTRUCTION_OPERATOR_DECISION:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_operator_decision_not_admitted",
            "The source-directory package commit requires the admitted package-construction operator decision.",
            http_status=409,
            details={
                "field": "operator_decision",
                "expected": PACKAGE_CONSTRUCTION_OPERATOR_DECISION,
            },
        )

    qualitative_analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_qualitative_analysis_hash_mismatch",
            "Package construction commit must reference the current server-recomputed qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_preview_hash_mismatch",
            "Package construction commit must reference the current server-recomputed source-directory package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_commit(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_package_commit_session(db, material_snapshot=material_snapshot)
    try:
        result = materialize_source_directory_qualitative_analysis_package_commit(
            db,
            session=session,
            material_snapshot=material_snapshot,
            client_request_id=request_id,
            package_review_preview_hash=expected_preview_hash,
            qualitative_analysis=qualitative_analysis,
            source_authority=preview["source_authority"],
        )
    except Layer3PackageEntryError as exc:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_existing_package_state",
            str(exc),
            http_status=409,
            details={"next_allowed_actions": ["inspect_existing_package_state"]},
        ) from exc
    db.commit()

    reconciliation_summary = result.reconciliation_record.summary_json or {}
    commit_summary = reconciliation_summary.get("source_directory_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        commit_summary = {}
    packages = list(result.output_packages)
    return {
        "schema_id": PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": PACKAGE_CONSTRUCTION_COMMIT_MODE,
        "status": "committed",
        "operator_decision": PACKAGE_CONSTRUCTION_OPERATOR_DECISION,
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "source_directory_package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": commit_summary.get("construction_basis_hash")
        or commit_summary.get("authority_basis_hash"),
        "reconciliation_record_id": result.reconciliation_record.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_rows_written": True,
        "package_payloads_written": True,
        "source_package_row_mutation_enabled": False,
        "package_payload_rewrite_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "next_state": "source_directory_qualitative_analysis_package_constructed",
        "next_allowed_actions": [],
        "negative_invariants": {
            "source_package_row_mutation_enabled": False,
            "package_payload_rewrite_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_export_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def source_directory_qualitative_analysis_package_review_submit(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_package_review_submit_payload(payload)
    request_id = _require_submit_field(fields, "client_request_id")
    operator_decision = str(fields.get("operator_decision") or "").strip()
    decision_notes = str(fields.get("decision_notes") or "").strip()
    if operator_decision not in PACKAGE_REVIEW_SUBMIT_DECISIONS:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_decision_not_admitted",
            "operator_decision must be approved, changes_requested, rejected, or blocked.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if operator_decision in PACKAGE_REVIEW_SUBMIT_NOTE_REQUIRED_DECISIONS and not decision_notes:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_decision_notes_required",
            "decision_notes are required for changes_requested, rejected, or blocked package-review decisions.",
            details={"field": "decision_notes"},
        )

    qualitative_analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_qualitative_analysis_hash_mismatch",
            "Package-review submit must reference the current server-recomputed qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_preview_hash_mismatch",
            "Package-review submit must reference the current server-recomputed source-directory package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_submit(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_package_review_submit_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_submit_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_reconciliation_not_found",
            "No source-directory package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_requires_package_commit",
            "Package-review submit requires source-directory qualitative package-commit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    if str(reconciliation_summary.get("source_gate") or "") != SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_source_gate_mismatch",
            "Package-review submit requires the source-directory qualitative package-construction source gate.",
            http_status=409,
            details={"blocked_fields": ["reconciliation_record_id"]},
        )

    supplied_construction_basis_hash = _require_submit_field(fields, "construction_basis_hash")
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash") or commit_summary.get("authority_basis_hash") or ""
    )
    commit_authority_basis = commit_summary.get("authority_basis")
    if not isinstance(commit_authority_basis, dict):
        commit_authority_basis = {}
    commit_mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": expected_preview_hash,
            "qualitative_analysis_hash": expected_analysis_hash,
        }.items()
        if str(commit_summary.get(field) or commit_authority_basis.get(field) or "") != str(expected)
    ]
    if commit_mismatches or supplied_construction_basis_hash != expected_construction_basis_hash:
        blocked_fields = sorted(
            set(
                commit_mismatches
                + (
                    ["construction_basis_hash"]
                    if supplied_construction_basis_hash != expected_construction_basis_hash
                    else []
                )
            )
        )
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_construction_mismatch",
            "Stored package-construction provenance does not match the supplied package-review submit authority.",
            http_status=409,
            details={"blocked_fields": blocked_fields},
        )

    packages = _source_directory_review_packages(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_package_ids = _submit_string_list(fields.get("output_package_ids"), field="output_package_ids")
    supplied_package_kinds = _submit_string_list(fields.get("package_kinds"), field="package_kinds")
    supplied_payload_hashes = _submit_string_list(fields.get("payload_hashes"), field="payload_hashes")
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    if supplied_package_ids != expected_package_ids:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_package_ids_mismatch",
            "Supplied output_package_ids do not match the constructed source-directory package set.",
            http_status=409,
            details={"blocked_fields": ["output_package_ids"]},
        )
    if supplied_package_kinds != expected_package_kinds:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_package_kinds_mismatch",
            "Supplied package_kinds must match canonical_internal, user_facing, and review_facing in review order.",
            http_status=409,
            details={"blocked_fields": ["package_kinds"]},
        )
    if supplied_payload_hashes != expected_payload_hashes:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the constructed source-directory package payload hashes.",
            http_status=409,
            details={"blocked_fields": ["payload_hashes"]},
        )

    package_review_state = PACKAGE_REVIEW_SUBMIT_STATE_BY_DECISION[operator_decision]
    submit_basis = {
        "schema_id": "layer3.source_directory_qualitative_analysis_package_review_submit_authority_basis.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "package_review_state": package_review_state,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
    }
    submit_record_ref = _stable_id("l3-source-directory-package-review-submit", submit_basis)
    existing_submit = reconciliation_summary.get("package_review_submit")
    if isinstance(existing_submit, dict):
        if str(existing_submit.get("submit_record_ref") or "") == submit_record_ref:
            return _package_review_submit_response(
                request_id=request_id,
                status="already_submitted",
                session=session,
                material_snapshot=material_snapshot,
                qualitative_analysis=qualitative_analysis,
                reconciliation=reconciliation,
                packages=packages,
                submit_state=existing_submit,
            )
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_already_recorded",
            "This source-directory package set already has a package-review submit decision.",
            http_status=409,
            details={"blocked_fields": ["operator_decision", "decision_notes"]},
        )

    submit_state = {
        "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
        "package_review_submit_schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
        "client_request_id": request_id,
        "submit_record_ref": submit_record_ref,
        "authority_basis": submit_basis,
        "state": package_review_state,
        "package_review_state": package_review_state,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
        "recorded_at": _server_time(),
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "export_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE),
    }
    reconciliation.summary_json = {
        **reconciliation_summary,
        "source_directory_qualitative_package_commit": {
            **commit_summary,
            "package_review_submit_enabled": False,
        },
        "package_review_submit": submit_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "package_review_submit": {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "package_review_submit_schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            "submit_record_ref": submit_record_ref,
            "state": package_review_state,
            "package_review_state": package_review_state,
            "operator_decision": operator_decision,
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": expected_package_ids,
            "package_kinds": expected_package_kinds,
            "payload_hashes": expected_payload_hashes,
            "payload_refs": None,
            "payload_refs_redacted": True,
            "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
            "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
            "source_shape": material_snapshot.source_shape,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _package_review_submit_response(
        request_id=request_id,
        status="submitted",
        session=session,
        material_snapshot=material_snapshot,
        qualitative_analysis=qualitative_analysis,
        reconciliation=reconciliation,
        packages=packages,
        submit_state=submit_state,
    )


def source_directory_qualitative_analysis_package_supersession_preview(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_package_supersession_preview_payload(payload)
    request_id = _require_supersession_preview_field(fields, "client_request_id")
    if str(fields.get("operator_decision") or "").strip() != PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_operator_decision_not_admitted",
            "The source-directory package supersession preview requires the admitted preview operator decision.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if str(fields.get("package_review_state") or "").strip() != "package_review_approved":
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_requires_approved_submit",
            "Package supersession preview requires an approved source-directory package-review submit state.",
            http_status=409,
            details={"blocked_fields": ["package_review_state"]},
        )

    hybrid_preview = _source_directory_hybrid_package_supersession_preview(
        db,
        fields,
        request_id=request_id,
    )
    if hybrid_preview is not None:
        return hybrid_preview

    qualitative_analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_qualitative_analysis_hash_mismatch",
            "Package supersession preview must reference the current server-recomputed qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_preview_hash_mismatch",
            "Package supersession preview must reference the current server-recomputed package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_supersession_preview(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_package_supersession_preview_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_supersession_preview_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_reconciliation_not_found",
            "No source-directory package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_qualitative_package_commit")
    submit_state = reconciliation_summary.get("package_review_submit")
    if not isinstance(commit_summary, dict) or not isinstance(submit_state, dict):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_requires_package_review_submit",
            "Package supersession preview requires existing source-directory package commit and review-submit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    if str(submit_state.get("submit_record_ref") or "") != str(fields.get("package_review_submit_record_ref") or ""):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_submit_record_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match existing package-review submit authority.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("package_review_state") or "") != "package_review_approved":
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_submit_not_approved",
            "Package supersession preview requires an approved source-directory package-review submit record.",
            http_status=409,
            details={"blocked_fields": ["package_review_state"]},
        )
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash") or commit_summary.get("authority_basis_hash") or ""
    )
    if expected_construction_basis_hash != str(fields.get("construction_basis_hash") or ""):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_construction_basis_hash_mismatch",
            "Package supersession preview must reference the existing source-directory construction basis.",
            http_status=409,
            details={"blocked_fields": ["construction_basis_hash"]},
        )
    if str(submit_state.get("package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_submit_preview_hash_mismatch",
            "Existing package-review submit authority does not match the current package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    packages = _source_directory_review_packages_for_supersession_preview(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_package_ids = _preview_string_list(fields.get("output_package_ids"), field="output_package_ids")
    supplied_package_kinds = _preview_string_list(fields.get("package_kinds"), field="package_kinds")
    supplied_payload_hashes = _preview_string_list(fields.get("payload_hashes"), field="payload_hashes")
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    mismatches = [
        field
        for field, supplied, expected in (
            ("output_package_ids", supplied_package_ids, expected_package_ids),
            ("package_kinds", supplied_package_kinds, expected_package_kinds),
            ("payload_hashes", supplied_payload_hashes, expected_payload_hashes),
        )
        if supplied != expected
    ]
    if mismatches:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_package_set_mismatch",
            "Supplied package set fields do not match existing source-directory packages.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )

    source_package_set = {
        "schema_id": "layer3.source_directory_package_supersession_source_package_set.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs_redacted": True,
        "source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
    }
    source_package_set_hash = _stable_hash(source_package_set)
    downstream_dependencies = _source_directory_package_downstream_dependencies(reconciliation_summary)
    downstream_dependency_hash = _stable_hash(
        {
            "schema_id": "layer3.source_directory_package_supersession_downstream_dependencies.v1",
            "reconciliation_record_id": reconciliation_record_id,
            "dependencies": downstream_dependencies,
        }
    )
    preview_basis = {
        "schema_id": "layer3.source_directory_package_supersession_preview_basis.v1",
        "source_package_set_hash": source_package_set_hash,
        "downstream_dependency_hash": downstream_dependency_hash,
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "package_review_submit_record_ref": submit_state["submit_record_ref"],
        "source_gate": PACKAGE_SUPERSESSION_PREVIEW_SOURCE_GATE,
    }
    package_supersession_preview_hash = _stable_hash(preview_basis)
    return {
        "schema_id": PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": PACKAGE_SUPERSESSION_PREVIEW_MODE,
        "status": "previewed",
        "operator_decision": PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION,
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "source_directory_package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": fields["construction_basis_hash"],
        "reconciliation_record_id": reconciliation_record_id,
        "package_review_submit_record_ref": submit_state["submit_record_ref"],
        "package_review_state": submit_state["package_review_state"],
        "source_package_set_hash": source_package_set_hash,
        "package_supersession_preview_hash": package_supersession_preview_hash,
        "downstream_dependency_hash": downstream_dependency_hash,
        "downstream_dependencies": downstream_dependencies,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs_redacted": True,
        "replacement_package_set_authority_enabled": False,
        "package_supersession_commit_enabled": False,
        "package_row_mutation_enabled": False,
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "source_gate": PACKAGE_SUPERSESSION_PREVIEW_SOURCE_GATE,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "next_state": "source_directory_package_supersession_previewed",
        "next_allowed_actions": [],
        "negative_invariants": {
            "package_row_mutation_enabled": False,
            "package_payload_rewrite_enabled": False,
            "source_package_row_mutation_enabled": False,
            "replacement_package_set_authority_enabled": False,
            "package_supersession_commit_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
    }


def _source_directory_hybrid_package_supersession_preview(
    db: Session,
    fields: Mapping[str, Any],
    *,
    request_id: str,
) -> dict[str, Any] | None:
    reconciliation_record_id = _require_supersession_preview_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id)
        .one_or_none()
    )
    if reconciliation is None:
        return None

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_hybrid_context_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        return None

    submit_state = reconciliation_summary.get("package_review_submit")
    if not isinstance(submit_state, dict):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_requires_package_review_submit",
            "Package supersession preview requires existing source-directory hybrid package commit and review-submit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    if (
        str(reconciliation_summary.get("source_gate") or "")
        != SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE
    ):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_source_gate_mismatch",
            "Package supersession preview requires the source-directory hybrid package-construction source gate.",
            http_status=409,
            details={"blocked_fields": ["reconciliation_record_id"]},
        )

    session = db.query(L3Session).filter(L3Session.session_id == reconciliation.session_id).one_or_none()
    material_snapshot = db.get(
        L3MaterialSnapshot,
        _require_supersession_preview_field(fields, "material_snapshot_id"),
    )
    if session is None or material_snapshot is None:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_requires_existing_hybrid_authority",
            "Package supersession preview requires existing source-directory hybrid session and material authority.",
            http_status=404,
            details={"blocked_fields": ["material_snapshot_id", "reconciliation_record_id"]},
        )
    if material_snapshot.session_id != session.session_id:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_material_session_mismatch",
            "Package supersession preview material snapshot does not match the package lifecycle session.",
            http_status=409,
            details={"blocked_fields": ["material_snapshot_id", "reconciliation_record_id"]},
        )

    authority_basis = commit_summary.get("authority_basis")
    if not isinstance(authority_basis, dict):
        authority_basis = {}
    source_authority = authority_basis.get("source_authority")
    if not isinstance(source_authority, dict):
        source_authority = {}

    expected_analysis_hash = str(
        authority_basis.get("qualitative_analysis_hash")
        or source_authority.get("qualitative_analysis_hash")
        or ""
    )
    expected_preview_hash = str(
        commit_summary.get("package_review_preview_hash")
        or authority_basis.get("package_review_preview_hash")
        or ""
    )
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_qualitative_analysis_hash_mismatch",
            "Package supersession preview must reference the current server-owned hybrid qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_preview_hash_mismatch",
            "Package supersession preview must reference the current server-owned hybrid package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    if str(submit_state.get("submit_record_ref") or "") != str(fields.get("package_review_submit_record_ref") or ""):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_submit_record_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match existing package-review submit authority.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("package_review_state") or "") != "package_review_approved":
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_submit_not_approved",
            "Package supersession preview requires an approved source-directory package-review submit record.",
            http_status=409,
            details={"blocked_fields": ["package_review_state"]},
        )

    packages = _source_directory_review_packages_for_supersession_preview(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash")
        or next(
            (
                str((package.summary_json or {}).get("construction_basis_hash") or "")
                for package in packages
                if str((package.summary_json or {}).get("construction_basis_hash") or "")
            ),
            "",
        )
        or commit_summary.get("authority_basis_hash")
        or ""
    )
    if expected_construction_basis_hash != str(fields.get("construction_basis_hash") or ""):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_construction_basis_hash_mismatch",
            "Package supersession preview must reference the existing source-directory hybrid construction basis.",
            http_status=409,
            details={"blocked_fields": ["construction_basis_hash"]},
        )
    if str(submit_state.get("package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_submit_preview_hash_mismatch",
            "Existing package-review submit authority does not match the current hybrid package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    field_expectations = {
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": source_authority.get("source_ingestion_batch_id"),
        "source_ingestion_file_id": source_authority.get("source_ingestion_file_id"),
        "content_sha256": source_authority.get("content_sha256"),
        "file_identity_hash": source_authority.get("file_identity_hash"),
        "authority_basis_hash": source_authority.get("authority_basis_hash"),
        "payload_hash": source_authority.get("payload_hash"),
        "index_authority_hash": source_authority.get("index_authority_hash"),
    }
    source_mismatches = [
        field
        for field, expected in field_expectations.items()
        if str(expected or "") and str(fields.get(field) or "") != str(expected)
    ]
    if source_mismatches:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_source_authority_mismatch",
            "Supplied source-directory fields do not match the stored hybrid package lifecycle authority.",
            http_status=409,
            details={"blocked_fields": source_mismatches},
        )

    supplied_package_ids = _preview_string_list(fields.get("output_package_ids"), field="output_package_ids")
    supplied_package_kinds = _preview_string_list(fields.get("package_kinds"), field="package_kinds")
    supplied_payload_hashes = _preview_string_list(fields.get("payload_hashes"), field="payload_hashes")
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    mismatches = [
        field
        for field, supplied, expected in (
            ("output_package_ids", supplied_package_ids, expected_package_ids),
            ("package_kinds", supplied_package_kinds, expected_package_kinds),
            ("payload_hashes", supplied_payload_hashes, expected_payload_hashes),
        )
        if supplied != expected
    ]
    if mismatches:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_package_set_mismatch",
            "Supplied package set fields do not match existing source-directory hybrid packages.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )

    package_construction_source_gate = str(
        commit_summary.get("package_construction_source_gate")
        or authority_basis.get("source_gate")
        or SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE
    )
    source_package_set = {
        "schema_id": "layer3.source_directory_package_supersession_source_package_set.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs_redacted": True,
        "source_gate": package_construction_source_gate,
    }
    source_package_set_hash = _stable_hash(source_package_set)
    downstream_dependencies = _source_directory_package_downstream_dependencies(reconciliation_summary)
    downstream_dependency_hash = _stable_hash(
        {
            "schema_id": "layer3.source_directory_package_supersession_downstream_dependencies.v1",
            "reconciliation_record_id": reconciliation_record_id,
            "dependencies": downstream_dependencies,
        }
    )
    preview_basis = {
        "schema_id": "layer3.source_directory_package_supersession_preview_basis.v1",
        "source_package_set_hash": source_package_set_hash,
        "downstream_dependency_hash": downstream_dependency_hash,
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "package_review_submit_record_ref": submit_state["submit_record_ref"],
        "source_gate": PACKAGE_SUPERSESSION_PREVIEW_SOURCE_GATE,
    }
    package_supersession_preview_hash = _stable_hash(preview_basis)
    return {
        "schema_id": PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": PACKAGE_SUPERSESSION_PREVIEW_MODE,
        "status": "previewed",
        "operator_decision": PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION,
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": str(source_authority.get("source_ingestion_batch_id") or ""),
        "source_ingestion_file_id": str(source_authority.get("source_ingestion_file_id") or ""),
        "content_sha256": str(source_authority.get("content_sha256") or ""),
        "file_identity_hash": str(source_authority.get("file_identity_hash") or ""),
        "authority_basis_hash": str(source_authority.get("authority_basis_hash") or ""),
        "payload_hash": str(source_authority.get("payload_hash") or ""),
        "index_authority_hash": str(source_authority.get("index_authority_hash") or ""),
        "context_packet_hash": str(source_authority.get("hybrid_context_packet_hash") or ""),
        "qualitative_analysis_hash": expected_analysis_hash,
        "source_directory_package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": fields["construction_basis_hash"],
        "reconciliation_record_id": reconciliation_record_id,
        "package_review_submit_record_ref": submit_state["submit_record_ref"],
        "package_review_state": submit_state["package_review_state"],
        "source_package_set_hash": source_package_set_hash,
        "package_supersession_preview_hash": package_supersession_preview_hash,
        "downstream_dependency_hash": downstream_dependency_hash,
        "downstream_dependencies": downstream_dependencies,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs_redacted": True,
        "replacement_package_set_authority_enabled": False,
        "package_supersession_commit_enabled": False,
        "package_row_mutation_enabled": False,
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "source_gate": PACKAGE_SUPERSESSION_PREVIEW_SOURCE_GATE,
        "package_review_submit_source_gate": submit_state["source_gate"],
        "package_construction_source_gate": package_construction_source_gate,
        "next_state": "source_directory_package_supersession_previewed",
        "next_allowed_actions": [],
        "negative_invariants": {
            "package_row_mutation_enabled": False,
            "package_payload_rewrite_enabled": False,
            "source_package_row_mutation_enabled": False,
            "replacement_package_set_authority_enabled": False,
            "package_supersession_commit_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
    }


def source_directory_qualitative_analysis_handoff_export_prepare(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_handoff_export_prepare_payload(payload)
    request_id = _require_handoff_field(fields, "client_request_id")
    operator_decision = str(fields.get("operator_decision") or "").strip()
    decision_notes = str(fields.get("decision_notes") or "").strip()
    if operator_decision not in HANDOFF_EXPORT_PREPARE_DECISIONS:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_decision_not_admitted",
            "operator_decision must be authorize_prepare, hold, decline, or blocked.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if operator_decision in HANDOFF_EXPORT_PREPARE_NOTE_REQUIRED_DECISIONS and not decision_notes:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_decision_notes_required",
            "decision_notes are required for hold, decline, or blocked handoff/export decisions.",
            details={"field": "decision_notes"},
        )
    if str(fields.get("handoff_target") or "").strip() != "internal_export_envelope":
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_target_not_admitted",
            "handoff_target must be internal_export_envelope for this tranche.",
            http_status=409,
            details={"blocked_fields": ["handoff_target"]},
        )
    if str(fields.get("export_mode") or "").strip() != "prepare_only":
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_mode_not_admitted",
            "export_mode must be prepare_only for this tranche.",
            http_status=409,
            details={"blocked_fields": ["export_mode"]},
        )
    if str(fields.get("package_review_state") or "").strip() != PACKAGE_REVIEW_APPROVED_STATE:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_requires_approved_package_review",
            "Handoff/export preparation requires package_review_state to be package_review_approved.",
            http_status=409,
            details={"blocked_fields": ["package_review_state"]},
        )

    qualitative_analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_qualitative_analysis_hash_mismatch",
            "Handoff/export prepare must reference the current server-recomputed qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_preview_hash_mismatch",
            "Handoff/export prepare must reference the current server-recomputed package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_handoff_export_prepare(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_handoff_export_prepare_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_handoff_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_reconciliation_not_found",
            "No source-directory package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_requires_package_commit",
            "Handoff/export prepare requires source-directory qualitative package-commit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    if str(reconciliation_summary.get("source_gate") or "") != SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_source_gate_mismatch",
            "Handoff/export prepare requires the source-directory qualitative package-construction source gate.",
            http_status=409,
            details={"blocked_fields": ["reconciliation_record_id"]},
        )
    submit_state = reconciliation_summary.get("package_review_submit")
    if not isinstance(submit_state, dict):
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_requires_package_review_submit",
            "Handoff/export prepare requires existing package-review submit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    supplied_submit_ref = _require_handoff_field(fields, "package_review_submit_record_ref")
    if str(submit_state.get("schema_id") or "") != PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_submit_schema_mismatch",
            "Stored package-review submit state does not match the admitted state schema.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("package_review_submit_schema_id") or "") != PACKAGE_REVIEW_SUBMIT_SCHEMA_ID:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_submit_contract_mismatch",
            "Stored package-review submit state does not match the source-directory submit contract.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("submit_record_ref") or "") != supplied_submit_ref:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_submit_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match stored package-review submit authority.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("package_review_state") or "") != PACKAGE_REVIEW_APPROVED_STATE:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_submit_not_approved",
            "Handoff/export prepare requires stored package-review submit state to be approved.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )

    supplied_construction_basis_hash = _require_handoff_field(fields, "construction_basis_hash")
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash") or commit_summary.get("authority_basis_hash") or ""
    )
    submit_authority_basis = submit_state.get("authority_basis")
    if not isinstance(submit_authority_basis, dict):
        submit_authority_basis = {}
    mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": expected_preview_hash,
            "qualitative_analysis_hash": expected_analysis_hash,
            "construction_basis_hash": expected_construction_basis_hash,
        }.items()
        if str(submit_state.get(field) or submit_authority_basis.get(field) or "") != str(expected)
    ]
    if supplied_construction_basis_hash != expected_construction_basis_hash:
        mismatches.append("construction_basis_hash")
    if mismatches:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_authority_mismatch",
            "Stored package-review submit provenance does not match the supplied handoff/export prepare authority.",
            http_status=409,
            details={"blocked_fields": sorted(set(mismatches))},
        )

    packages = _source_directory_review_packages_for_handoff_export_prepare(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_package_ids = _handoff_string_list(fields.get("output_package_ids"), field="output_package_ids")
    supplied_package_kinds = _handoff_string_list(fields.get("package_kinds"), field="package_kinds")
    supplied_payload_hashes = _handoff_string_list(fields.get("payload_hashes"), field="payload_hashes")
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    if supplied_package_ids != expected_package_ids:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_package_ids_mismatch",
            "Supplied output_package_ids do not match the constructed source-directory package set.",
            http_status=409,
            details={"blocked_fields": ["output_package_ids"]},
        )
    if supplied_package_kinds != expected_package_kinds:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_package_kinds_mismatch",
            "Supplied package_kinds must match canonical_internal, user_facing, and review_facing in review order.",
            http_status=409,
            details={"blocked_fields": ["package_kinds"]},
        )
    if supplied_payload_hashes != expected_payload_hashes:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the constructed source-directory package payload hashes.",
            http_status=409,
            details={"blocked_fields": ["payload_hashes"]},
        )

    handoff_export_state = HANDOFF_EXPORT_PREPARE_STATE_BY_DECISION[operator_decision]
    prepare_basis = {
        "schema_id": "layer3.source_directory_qualitative_analysis_handoff_export_prepare_authority_basis.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "handoff_export_state": handoff_export_state,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
    }
    prepare_record_ref = _stable_id("l3-source-directory-handoff-export-prepare", prepare_basis)
    envelope = {
        "schema_id": "layer3.source_directory_internal_export_envelope.v1",
        "envelope_ref": _stable_id(
            "l3-source-directory-internal-export-envelope",
            {
                "prepare_record_ref": prepare_record_ref,
                "package_review_submit_record_ref": supplied_submit_ref,
                "output_package_ids": expected_package_ids,
                "payload_hashes": expected_payload_hashes,
            },
        ),
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "payload_refs": None,
        "payload_refs_redacted": True,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
    }
    existing_prepare = reconciliation_summary.get("handoff_export_prepare")
    if isinstance(existing_prepare, dict):
        if str(existing_prepare.get("prepare_record_ref") or "") == prepare_record_ref:
            return _handoff_export_prepare_response(
                request_id=request_id,
                status="already_prepared",
                session=session,
                material_snapshot=material_snapshot,
                qualitative_analysis=qualitative_analysis,
                reconciliation=reconciliation,
                packages=packages,
                prepare_state=existing_prepare,
            )
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_already_recorded",
            "This source-directory package set already has a handoff/export prepare decision.",
            http_status=409,
            details={"blocked_fields": ["operator_decision", "decision_notes"]},
        )

    prepare_state = {
        "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
        "handoff_export_prepare_schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
        "client_request_id": request_id,
        "prepare_record_ref": prepare_record_ref,
        "authority_basis": prepare_basis,
        "state": handoff_export_state,
        "handoff_export_state": handoff_export_state,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "handoff_export_envelope": envelope,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
        "recorded_at": _server_time(),
        "handoff_enabled": False,
        "export_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    reconciliation.summary_json = {
        **reconciliation_summary,
        "handoff_export_prepare": prepare_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "handoff_export_prepare": {
            "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
            "handoff_export_prepare_schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
            "prepare_record_ref": prepare_record_ref,
            "state": handoff_export_state,
            "handoff_export_state": handoff_export_state,
            "operator_decision": operator_decision,
            "reconciliation_record_id": reconciliation_record_id,
            "package_review_submit_record_ref": supplied_submit_ref,
            "output_package_ids": expected_package_ids,
            "package_kinds": expected_package_kinds,
            "payload_hashes": expected_payload_hashes,
            "payload_refs": None,
            "payload_refs_redacted": True,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
            "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
            "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
            "source_shape": material_snapshot.source_shape,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _handoff_export_prepare_response(
        request_id=request_id,
        status=HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION[operator_decision],
        session=session,
        material_snapshot=material_snapshot,
        qualitative_analysis=qualitative_analysis,
        reconciliation=reconciliation,
        packages=packages,
        prepare_state=prepare_state,
    )


def source_directory_qualitative_analysis_external_export_download_prepare(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_external_export_download_prepare_payload(payload)
    request_id = _require_external_export_download_prepare_field(fields, "client_request_id")
    if str(fields.get("operator_decision") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_decision_not_admitted",
            "operator_decision must be prepare_source_directory_external_export_download.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if str(fields.get("external_export_download_target") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_TARGET:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_target_not_admitted",
            "external_export_download_target must be source_directory_qualitative_analysis_package_download_reference.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_target"]},
        )
    if str(fields.get("download_mode") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_MODE:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_mode_not_admitted",
            "download_mode must be reference_only_prepare for this tranche.",
            http_status=409,
            details={"blocked_fields": ["download_mode"]},
        )
    if str(fields.get("handoff_export_state") or "").strip() != HANDOFF_EXPORT_PREPARED_STATE:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_requires_prepared_handoff",
            "External export/download readiness requires handoff_export_state to be handoff_export_prepared.",
            http_status=409,
            details={"blocked_fields": ["handoff_export_state"]},
        )

    qualitative_analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_qualitative_analysis_hash_mismatch",
            "External export/download prepare must reference the current server-recomputed qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_preview_hash_mismatch",
            "External export/download prepare must reference the current server-recomputed package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_external_export_download_prepare(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_external_export_download_prepare_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_external_export_download_prepare_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_reconciliation_not_found",
            "No source-directory package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    prepare_state = reconciliation_summary.get("handoff_export_prepare")
    if not isinstance(prepare_state, dict):
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_requires_handoff_prepare",
            "External export/download readiness requires existing source-directory handoff/export prepare authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    supplied_prepare_ref = _require_external_export_download_prepare_field(fields, "prepare_record_ref")
    supplied_envelope_ref = _require_external_export_download_prepare_field(fields, "handoff_export_envelope_ref")
    if str(prepare_state.get("schema_id") or "") != HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_state_schema_mismatch",
            "Stored handoff/export prepare state does not match the admitted state schema.",
            http_status=409,
            details={"blocked_fields": ["prepare_record_ref"]},
        )
    if str(prepare_state.get("handoff_export_prepare_schema_id") or "") != HANDOFF_EXPORT_PREPARE_SCHEMA_ID:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_contract_mismatch",
            "Stored handoff/export prepare state does not match the source-directory prepare contract.",
            http_status=409,
            details={"blocked_fields": ["prepare_record_ref"]},
        )
    envelope = prepare_state.get("handoff_export_envelope")
    if not isinstance(envelope, dict):
        envelope = {}
    mismatches = [
        field
        for field, expected in {
            "prepare_record_ref": supplied_prepare_ref,
            "package_review_submit_record_ref": str(fields.get("package_review_submit_record_ref") or ""),
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "package_review_preview_hash": expected_preview_hash,
            "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
        }.items()
        if str(prepare_state.get(field) or "") != str(expected)
    ]
    if str(envelope.get("envelope_ref") or "") != supplied_envelope_ref:
        mismatches.append("handoff_export_envelope_ref")
    if mismatches:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_authority_mismatch",
            "Stored source-directory handoff/export prepare authority does not match the supplied readiness basis.",
            http_status=409,
            details={"blocked_fields": sorted(set(mismatches))},
        )

    packages = _source_directory_review_packages_for_external_export_download_prepare(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_package_ids = _external_export_download_prepare_string_list(
        fields.get("output_package_ids"), field="output_package_ids"
    )
    supplied_package_kinds = _external_export_download_prepare_string_list(
        fields.get("package_kinds"), field="package_kinds"
    )
    supplied_payload_hashes = _external_export_download_prepare_string_list(
        fields.get("payload_hashes"), field="payload_hashes"
    )
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    list_mismatches = []
    if supplied_package_ids != expected_package_ids:
        list_mismatches.append("output_package_ids")
    if supplied_package_kinds != expected_package_kinds:
        list_mismatches.append("package_kinds")
    if supplied_payload_hashes != expected_payload_hashes:
        list_mismatches.append("payload_hashes")
    if list_mismatches:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_package_authority_mismatch",
            "Supplied package identity does not match the constructed source-directory package set.",
            http_status=409,
            details={"blocked_fields": list_mismatches},
        )

    readiness_basis = {
        "schema_id": "layer3.source_directory_external_export_download_prepare_authority_basis.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "package_review_submit_record_ref": str(fields.get("package_review_submit_record_ref") or ""),
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_envelope_ref": supplied_envelope_ref,
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
    }
    record_ref = _stable_id("l3-source-directory-external-export-download-prepare", readiness_basis)
    existing_readiness = reconciliation_summary.get("external_export_download_prepare")
    if isinstance(existing_readiness, dict):
        if str(existing_readiness.get("external_export_download_record_ref") or "") == record_ref:
            return _external_export_download_prepare_response(
                request_id=request_id,
                status="already_prepared",
                session=session,
                material_snapshot=material_snapshot,
                qualitative_analysis=qualitative_analysis,
                reconciliation=reconciliation,
                packages=packages,
                readiness_state=existing_readiness,
            )
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_already_recorded",
            "This source-directory package set already has external export/download readiness.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_record_ref"]},
        )

    descriptor_ref = _stable_id(
        "l3-source-directory-external-export-download-descriptor",
        {**readiness_basis, "schema_id": "layer3.source_directory_external_export_download_descriptor_authority.v1"},
    )
    descriptor = {
        "schema_id": "layer3.source_directory_external_export_download_descriptor.v1",
        "descriptor_ref": descriptor_ref,
        "session_id": session.session_id,
        "reconciliation_record_id": reconciliation_record_id,
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_envelope_ref": supplied_envelope_ref,
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "browser_download_enabled": False,
        "same_origin_delivery_enabled": False,
        "provider_public_url_enabled": False,
        "connector_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    readiness_state = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "external_export_download_prepare_schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
        "client_request_id": request_id,
        "external_export_download_record_ref": record_ref,
        "export_download_descriptor_ref": descriptor_ref,
        "external_export_download_descriptor": descriptor,
        "authority_basis": readiness_basis,
        "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "decision_notes": str(fields.get("decision_notes") or "").strip() or None,
        "reconciliation_record_id": reconciliation_record_id,
        "package_review_submit_record_ref": str(fields.get("package_review_submit_record_ref") or ""),
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_envelope_ref": supplied_envelope_ref,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_shape": material_snapshot.source_shape,
        "recorded_at": _server_time(),
        "same_origin_delivery_enabled": False,
        "browser_download_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    reconciliation.summary_json = {
        **reconciliation_summary,
        "external_export_download_prepare": readiness_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "external_export_download_prepare": {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "external_export_download_prepare_schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
            "external_export_download_record_ref": record_ref,
            "export_download_descriptor_ref": descriptor_ref,
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "reconciliation_record_id": reconciliation_record_id,
            "prepare_record_ref": supplied_prepare_ref,
            "payload_refs": None,
            "payload_refs_redacted": True,
            "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _external_export_download_prepare_response(
        request_id=request_id,
        status="prepared",
        session=session,
        material_snapshot=material_snapshot,
        qualitative_analysis=qualitative_analysis,
        reconciliation=reconciliation,
        packages=packages,
        readiness_state=readiness_state,
    )


def source_directory_qualitative_analysis_external_export_download_deliver(
    db: Session,
    payload: Mapping[str, Any],
) -> ExternalExportDownloadDelivery:
    fields = _normalise_external_export_download_delivery_payload(payload)
    request_id = _require_external_export_download_delivery_field(fields, "client_request_id")
    if str(fields.get("operator_decision") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_decision_not_admitted",
            "operator_decision must be deliver_source_directory_external_export_download.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if str(fields.get("external_export_download_target") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_TARGET:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_target_not_admitted",
            "external_export_download_target must be source_directory_qualitative_analysis_package_download_reference.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_target"]},
        )
    if str(fields.get("download_mode") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_MODE:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_download_mode_not_admitted",
            "download_mode must be reference_only_prepare for this tranche.",
            http_status=409,
            details={"blocked_fields": ["download_mode"]},
        )
    if str(fields.get("delivery_mode") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_mode_not_admitted",
            "delivery_mode must be same_origin_artifact_stream.",
            http_status=409,
            details={"blocked_fields": ["delivery_mode"]},
        )
    if str(fields.get("external_export_download_state") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_requires_prepared_state",
            "Source-directory external export/download delivery requires external_export_download_prepared state.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_state"]},
        )

    qualitative_analysis = source_directory_material_context_packet_qualitative_hybrid_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_qualitative_analysis_hash_mismatch",
            "External export/download delivery must reference the current server-recomputed qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_preview_hash_mismatch",
            "External export/download delivery must reference the current server-recomputed package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_external_export_download_delivery(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_external_export_download_delivery_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_external_export_download_delivery_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_reconciliation_not_found",
            "No source-directory package reconciliation record exists for the supplied delivery authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    readiness_state = reconciliation_summary.get("external_export_download_prepare")
    if not isinstance(readiness_state, dict):
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_requires_prepare",
            "Delivery requires existing source-directory external export/download prepare authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    descriptor = readiness_state.get("external_export_download_descriptor")
    if not isinstance(descriptor, dict):
        descriptor = {}
    stored_mismatches = [
        field
        for field, expected in {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "external_export_download_prepare_schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
            "external_export_download_record_ref": str(fields.get("external_export_download_record_ref") or ""),
            "export_download_descriptor_ref": str(fields.get("export_download_descriptor_ref") or ""),
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
            "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "package_review_preview_hash": expected_preview_hash,
            "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
            "prepare_record_ref": str(fields.get("prepare_record_ref") or ""),
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "handoff_export_envelope_ref": str(fields.get("handoff_export_envelope_ref") or ""),
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
        }.items()
        if str(readiness_state.get(field) or "") != str(expected)
    ]
    if str(descriptor.get("descriptor_ref") or "") != str(fields.get("export_download_descriptor_ref") or ""):
        stored_mismatches.append("export_download_descriptor_ref")
    if stored_mismatches:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_authority_mismatch",
            "Stored source-directory external export/download prepare authority does not match the delivery basis.",
            http_status=409,
            details={"blocked_fields": sorted(set(stored_mismatches))},
        )

    packages = _source_directory_review_packages_for_external_export_download_delivery(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_package_ids = _external_export_download_delivery_string_list(
        fields.get("output_package_ids"), field="output_package_ids"
    )
    supplied_package_kinds = _external_export_download_delivery_string_list(
        fields.get("package_kinds"), field="package_kinds"
    )
    supplied_payload_hashes = _external_export_download_delivery_string_list(
        fields.get("payload_hashes"), field="payload_hashes"
    )
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    list_mismatches = []
    if supplied_package_ids != expected_package_ids:
        list_mismatches.append("output_package_ids")
    if supplied_package_kinds != expected_package_kinds:
        list_mismatches.append("package_kinds")
    if supplied_payload_hashes != expected_payload_hashes:
        list_mismatches.append("payload_hashes")
    if list_mismatches:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_package_authority_mismatch",
            "Supplied package identity does not match the prepared source-directory package set.",
            http_status=409,
            details={"blocked_fields": list_mismatches},
        )

    selected_package_id = _require_external_export_download_delivery_field(fields, "output_package_id")
    selected_package = next(
        (package for package in packages if package.output_package_id == selected_package_id),
        None,
    )
    if selected_package is None:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_package_not_found",
            "Requested source-directory package is not part of the prepared package set.",
            http_status=404,
            details={"blocked_fields": ["output_package_id"]},
        )
    if selected_package.package_kind != str(fields.get("package_kind") or ""):
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_package_kind_mismatch",
            "Requested source-directory package kind does not match the selected package row.",
            http_status=409,
            details={"blocked_fields": ["package_kind"]},
        )
    if selected_package.payload_hash != str(fields.get("package_payload_hash") or ""):
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_payload_hash_mismatch",
            "Requested source-directory package payload hash does not match the selected package row.",
            http_status=409,
            details={"blocked_fields": ["package_payload_hash"]},
        )

    artifact_path = _source_directory_package_payload_path(selected_package)
    artifact_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if artifact_hash != selected_package.payload_hash:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_artifact_hash_mismatch",
            "Stored source-directory package artifact hash does not match the selected package row.",
            http_status=409,
            details={"blocked_fields": ["output_package_id", "package_payload_hash"]},
        )

    authority = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "mode": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE,
        "delivery_state": EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SOURCE_GATE,
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "reconciliation_record_id": reconciliation_record_id,
        "external_export_download_record_ref": readiness_state["external_export_download_record_ref"],
        "export_download_descriptor_ref": readiness_state["export_download_descriptor_ref"],
        "output_package_id": selected_package.output_package_id,
        "package_kind": selected_package.package_kind,
        "package_payload_hash": selected_package.payload_hash,
        "payload_ref_redacted": True,
        "same_origin_delivery_enabled": True,
        "browser_managed_same_origin_attachment_enabled": True,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
    }
    db.rollback()
    return ExternalExportDownloadDelivery(
        artifact_path=artifact_path,
        media_type="application/json",
        filename=_source_directory_delivery_filename(
            session_id=session.session_id,
            package_kind=selected_package.package_kind,
        ),
        headers={
            "X-Layer3-Schema-Id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
            "X-Layer3-Delivery-State": EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE,
            "X-Layer3-Source-Artifact-Hash": artifact_hash,
            "X-Layer3-External-Export-Download-Record-Ref": str(
                readiness_state["external_export_download_record_ref"]
            ),
            "X-Layer3-Source-Directory-Package-Kind": selected_package.package_kind,
        },
        authority=authority,
    )


def source_directory_qualitative_analysis_external_export_download_delivery_status(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    delivery = source_directory_qualitative_analysis_external_export_download_deliver(db, payload)
    authority = _json_clone(delivery.authority)
    request_id = str(authority.get("request_id") or "")
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_MODE,
        "status": "ready",
        "delivery_status": "source_directory_external_export_download_delivery_ready",
        "delivery_available": True,
        "delivery_streaming_performed": False,
        "delivery_state": authority.get("delivery_state"),
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SOURCE_GATE,
        "validated_delivery_source_gate": authority.get("source_gate"),
        "external_export_download_record_ref": authority.get("external_export_download_record_ref"),
        "export_download_descriptor_ref": authority.get("export_download_descriptor_ref"),
        "output_package_id": authority.get("output_package_id"),
        "package_kind": authority.get("package_kind"),
        "package_payload_hash": authority.get("package_payload_hash"),
        "payload_ref_redacted": True,
        "raw_local_path_exposed": False,
        "same_origin_delivery_enabled": True,
        "browser_managed_same_origin_attachment_enabled": True,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
        "delivery_headers": dict(delivery.headers),
        "delivery_authority": authority,
        "next_allowed_actions": ["deliver_source_directory_external_export_download"],
    }


def _source_directory_package_review_preview(
    *,
    request_id: str,
    fields: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    qualitative_analysis_hash: str,
) -> dict[str, Any]:
    candidate_packages = [
        {
            "package_kind": package_kind,
            "preview_only": True,
            "package_commit_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "external_export_download_enabled": False,
            "readiness_reason": (
                "source-directory qualitative-analysis package construction is not admitted in this boundary"
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
    source_authority = {
        "source_ingestion_batch_id": context_packet["source_ingestion_batch_id"],
        "source_ingestion_file_id": context_packet["source_ingestion_file_id"],
        "material_snapshot_id": context_packet["material_snapshot_id"],
        "content_sha256": context_packet["content_sha256"],
        "file_identity_hash": context_packet["file_identity_hash"],
        "authority_basis_hash": context_packet["authority_basis_hash"],
        "payload_hash": context_packet["payload_hash"],
        "index_authority_hash": context_packet["index_authority_hash"],
        "context_packet_hash": context_packet["context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis_hash,
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
        "next_state": "source_directory_package_review_preview_available",
        "next_allowed_actions": [],
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


def _normalise_package_commit_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_forbidden_field_not_admitted",
            "The source-directory package commit request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _PACKAGE_COMMIT_REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_unknown_field",
            "The source-directory package commit request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_PACKAGE_COMMIT_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _normalise_package_review_submit_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_forbidden_field_not_admitted",
            "The source-directory package-review submit request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_unknown_field",
            "The source-directory package-review submit request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS):
        _require_submit_field(fields, field)
    return fields


def _normalise_package_supersession_preview_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _PACKAGE_SUPERSESSION_PREVIEW_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_forbidden_field_not_admitted",
            "The source-directory package supersession preview request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_unknown_field",
            "The source-directory package supersession preview request includes unknown fields.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS):
        _require_supersession_preview_field(fields, field)
    return fields


def _normalise_handoff_export_prepare_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_forbidden_field_not_admitted",
            "The source-directory handoff/export prepare request includes fields from a deferred or forbidden mode.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_unknown_field",
            "The source-directory handoff/export prepare request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS):
        _require_handoff_field(fields, field)
    return fields


def _normalise_external_export_download_prepare_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_forbidden_field_not_admitted",
            "The source-directory external export/download prepare request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_unknown_field",
            "The source-directory external export/download prepare request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS):
        _require_external_export_download_prepare_field(fields, field)
    return fields


def _normalise_external_export_download_delivery_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_forbidden_field_not_admitted",
            "The source-directory external export/download delivery request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_unknown_field",
            "The source-directory external export/download delivery request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS):
        _require_external_export_download_delivery_field(fields, field)
    return fields


def _qualitative_analysis_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_REQUIRED_FIELDS | _OPTIONAL_FIELDS) if field in fields}


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
                "query_term_frequencies": _query_term_frequencies(item),
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
            frequency = _query_term_frequency(item, token)
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


def _query_term_frequencies(item: Mapping[str, Any]) -> dict[str, int]:
    raw_frequencies = item.get("query_term_frequencies")
    if not isinstance(raw_frequencies, Mapping):
        raise SourceDirectoryQualitativeAnalysisError(
            "source_directory_qualitative_analysis_query_term_frequencies_missing",
            "The context-packet item is missing producer-owned query term frequencies.",
            http_status=409,
            details={"segment_id": item.get("segment_id")},
        )
    frequencies: dict[str, int] = {}
    for raw_token, raw_count in raw_frequencies.items():
        token = str(raw_token)
        try:
            count = int(raw_count)
        except (TypeError, ValueError) as exc:
            raise SourceDirectoryQualitativeAnalysisError(
                "source_directory_qualitative_analysis_query_term_frequency_invalid",
                "The context-packet item has an invalid query term frequency.",
                http_status=409,
                details={"segment_id": item.get("segment_id"), "term": token},
            ) from exc
        if isinstance(raw_count, bool) or count < 0:
            raise SourceDirectoryQualitativeAnalysisError(
                "source_directory_qualitative_analysis_query_term_frequency_invalid",
                "The context-packet item has an invalid query term frequency.",
                http_status=409,
                details={"segment_id": item.get("segment_id"), "term": token},
            )
        frequencies[token] = count
    return frequencies


def _query_term_frequency(item: Mapping[str, Any], token: str) -> int:
    return int(_query_term_frequencies(item).get(token, 0))


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


def _require_submit_field(fields: Mapping[str, Any], key: str) -> str:
    value = fields.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_required_field_missing",
            "A required source-directory package-review submit field is missing or empty.",
            details={"field": key},
        )
    return str(value).strip()


def _require_supersession_preview_field(fields: Mapping[str, Any], key: str) -> str:
    value = fields.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_required_field_missing",
            "A required source-directory package supersession preview field is missing or empty.",
            details={"field": key},
        )
    return str(value).strip()


def _require_handoff_field(fields: Mapping[str, Any], key: str) -> str:
    value = fields.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_required_field_missing",
            "A required source-directory handoff/export prepare field is missing or empty.",
            details={"field": key},
        )
    return str(value).strip()


def _require_external_export_download_prepare_field(fields: Mapping[str, Any], key: str) -> str:
    value = fields.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_required_field_missing",
            "A required source-directory external export/download prepare field is missing or empty.",
            details={"field": key},
        )
    return str(value).strip()


def _require_external_export_download_delivery_field(fields: Mapping[str, Any], key: str) -> str:
    value = fields.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_required_field_missing",
            "A required source-directory external export/download delivery field is missing or empty.",
            details={"field": key},
        )
    return str(value).strip()


def _submit_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_list_field_invalid",
            "Package-review submit list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_list_field_invalid",
            "Package-review submit list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _preview_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_list_field_invalid",
            "Package supersession preview list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryPackageSupersessionPreviewError(
            "source_directory_package_supersession_preview_list_field_invalid",
            "Package supersession preview list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _handoff_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_list_field_invalid",
            "Handoff/export prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryHandoffExportPrepareError(
            "source_directory_handoff_export_prepare_list_field_invalid",
            "Handoff/export prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _external_export_download_prepare_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_list_field_invalid",
            "External export/download prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryExternalExportDownloadPrepareError(
            "source_directory_external_export_download_prepare_list_field_invalid",
            "External export/download prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _external_export_download_delivery_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_list_field_invalid",
            "External export/download delivery list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_list_field_invalid",
            "External export/download delivery list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _source_directory_review_packages(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .with_for_update()
        .all()
    )
    if (
        len(packages) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    ):
        raise SourceDirectoryPackageReviewSubmitError(
            "source_directory_package_review_submit_requires_complete_package_set",
            "Package-review submit requires exactly the constructed canonical_internal, user_facing, and review_facing packages.",
            http_status=409,
            details={"blocked_fields": ["output_package_ids"]},
        )
    review_order = {kind: index for index, kind in enumerate(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)}
    return sorted(packages, key=lambda package: review_order[package.package_kind])


def _source_directory_review_packages_for_supersession_preview(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryPackageReviewSubmitError as exc:
        raise SourceDirectoryPackageSupersessionPreviewError(
            exc.code.replace("package_review_submit", "package_supersession_preview"),
            exc.message.replace("Package-review submit", "Package supersession preview"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_review_packages_for_handoff_export_prepare(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryPackageReviewSubmitError as exc:
        raise SourceDirectoryHandoffExportPrepareError(
            exc.code.replace("package_review_submit", "handoff_export_prepare"),
            exc.message.replace("Package-review submit", "Handoff/export prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_review_packages_for_external_export_download_prepare(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryPackageReviewSubmitError as exc:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            exc.code.replace("package_review_submit", "external_export_download_prepare"),
            exc.message.replace("Package-review submit", "External export/download prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_review_packages_for_external_export_download_delivery(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryPackageReviewSubmitError as exc:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            exc.code.replace("package_review_submit", "external_export_download_delivery"),
            exc.message.replace("Package-review submit", "External export/download delivery"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_submit(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryPackageReviewSubmitError(
            exc.code.replace("package_commit", "package_review_submit"),
            exc.message.replace("package commit", "package-review submit"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_supersession_preview(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryPackageSupersessionPreviewError(
            exc.code.replace("package_commit", "package_supersession_preview"),
            exc.message.replace("package commit", "package supersession preview"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_handoff_export_prepare(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryHandoffExportPrepareError(
            exc.code.replace("package_commit", "handoff_export_prepare"),
            exc.message.replace("package commit", "handoff/export prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_external_export_download_prepare(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            exc.code.replace("package_commit", "external_export_download_prepare"),
            exc.message.replace("package commit", "external export/download prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_external_export_download_delivery(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            exc.code.replace("package_commit", "external_export_download_delivery"),
            exc.message.replace("package commit", "external export/download delivery"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_package_review_submit_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryPackageReviewSubmitError(
            exc.code.replace("package_commit", "package_review_submit"),
            exc.message.replace("package construction", "package-review submit"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_package_supersession_preview_session(
    db: Session,
    *,
    material_snapshot: L3MaterialSnapshot,
) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryPackageSupersessionPreviewError(
            exc.code.replace("package_commit", "package_supersession_preview"),
            exc.message.replace("package construction", "package supersession preview"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_handoff_export_prepare_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryHandoffExportPrepareError(
            exc.code.replace("package_commit", "handoff_export_prepare"),
            exc.message.replace("package construction", "handoff/export prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_external_export_download_prepare_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryExternalExportDownloadPrepareError(
            exc.code.replace("package_commit", "external_export_download_prepare"),
            exc.message.replace("package construction", "external export/download prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_external_export_download_delivery_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryPackageCommitError as exc:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            exc.code.replace("package_commit", "external_export_download_delivery"),
            exc.message.replace("package construction", "external export/download delivery"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_package_payload_path(package: L3OutputPackage) -> Path:
    payload_ref = str(package.payload_ref or "").strip()
    if not payload_ref:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_payload_ref_missing",
            "Selected source-directory package row is missing its server-owned payload reference.",
            http_status=409,
            details={"blocked_fields": ["output_package_id"]},
        )
    artifact_root = Path(settings.artifact_storage_dir).resolve(strict=False)
    payload_path = Path(payload_ref).resolve(strict=False)
    try:
        payload_path.relative_to(artifact_root)
    except ValueError as exc:
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_payload_ref_not_server_owned",
            "Selected source-directory package payload is not under the server-owned artifact storage root.",
            http_status=409,
            details={"blocked_fields": ["output_package_id"]},
        ) from exc
    if not payload_path.is_file():
        raise SourceDirectoryExternalExportDownloadDeliveryError(
            "source_directory_external_export_download_delivery_payload_ref_not_found",
            "Selected source-directory package payload artifact was not found.",
            http_status=404,
            details={"blocked_fields": ["output_package_id"]},
        )
    return payload_path


def _source_directory_delivery_filename(*, session_id: str, package_kind: str) -> str:
    session_token = _safe_delivery_token(session_id, fallback="session")
    kind_token = _safe_delivery_token(package_kind, fallback="package")
    return f"layer3-source-directory-{session_token}-{kind_token}.json"


def _safe_delivery_token(value: str, *, fallback: str) -> str:
    token = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in str(value or "").strip())
    token = token.strip(".-")
    return (token or fallback)[:96]


def _source_directory_package_downstream_dependencies(
    reconciliation_summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    dependency_specs = (
        (
            "package_review_submit",
            {
                "schema_id",
                "submit_record_ref",
                "package_review_state",
                "source_gate",
            },
        ),
        (
            "handoff_export_prepare",
            {
                "schema_id",
                "prepare_record_ref",
                "handoff_export_state",
                "source_gate",
            },
        ),
        (
            "external_export_download_prepare",
            {
                "schema_id",
                "external_export_download_record_ref",
                "external_export_download_state",
                "source_gate",
            },
        ),
    )
    for state_key, field_names in dependency_specs:
        state = reconciliation_summary.get(state_key)
        if not isinstance(state, dict):
            continue
        dependency = {"state_key": state_key}
        for field_name in sorted(field_names):
            if field_name in state:
                dependency[field_name] = state[field_name]
        if "payload_refs" in state or "payload_ref" in state:
            dependency["payload_refs_redacted"] = True
        dependencies.append(dependency)
    return dependencies


def _package_review_submit_response(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    qualitative_analysis: Mapping[str, Any],
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    submit_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "status": status,
        "operator_decision": submit_state["operator_decision"],
        "decision_notes": submit_state.get("decision_notes"),
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": submit_state["package_review_preview_hash"],
        "construction_basis_hash": submit_state["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_review_state": submit_state["package_review_state"],
        "submit_record_ref": submit_state["submit_record_ref"],
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "export_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "downstream_unavailable": list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE),
        "next_state": submit_state["package_review_state"],
        "next_allowed_actions": [],
        "negative_invariants": {
            "package_payload_rewrite_enabled": False,
            "handoff_export_enabled": False,
            "aps_handoff_enabled": False,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def _handoff_export_prepare_response(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    qualitative_analysis: Mapping[str, Any],
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    prepare_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": HANDOFF_EXPORT_PREPARE_MODE,
        "status": status,
        "operator_decision": prepare_state["operator_decision"],
        "decision_notes": prepare_state.get("decision_notes"),
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": prepare_state["package_review_preview_hash"],
        "construction_basis_hash": prepare_state["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_review_state": prepare_state["package_review_state"],
        "package_review_submit_record_ref": prepare_state["package_review_submit_record_ref"],
        "handoff_export_state": prepare_state["handoff_export_state"],
        "prepare_record_ref": prepare_state["prepare_record_ref"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "handoff_export_envelope": _json_clone(prepare_state["handoff_export_envelope"]),
        "handoff_enabled": False,
        "export_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_state": prepare_state["handoff_export_state"],
        "next_allowed_actions": [],
        "negative_invariants": {
            "aps_handoff_enabled": False,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def _external_export_download_prepare_response(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    qualitative_analysis: Mapping[str, Any],
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    readiness_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_MODE,
        "status": status,
        "operator_decision": readiness_state["operator_decision"],
        "decision_notes": readiness_state.get("decision_notes"),
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "context_packet_hash": qualitative_analysis["context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis["qualitative_analysis_hash"],
        "source_directory_package_review_preview_hash": readiness_state["package_review_preview_hash"],
        "construction_basis_hash": readiness_state["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_review_state": readiness_state["package_review_state"],
        "package_review_submit_record_ref": readiness_state["package_review_submit_record_ref"],
        "handoff_export_state": readiness_state["handoff_export_state"],
        "prepare_record_ref": readiness_state["prepare_record_ref"],
        "handoff_export_envelope_ref": readiness_state["handoff_export_envelope_ref"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "external_export_download_state": readiness_state["external_export_download_state"],
        "external_export_download_record_ref": readiness_state["external_export_download_record_ref"],
        "export_download_descriptor_ref": readiness_state["export_download_descriptor_ref"],
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "external_export_download_descriptor": _json_clone(
            readiness_state["external_export_download_descriptor"]
        ),
        "same_origin_delivery_enabled": False,
        "browser_download_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_state": readiness_state["external_export_download_state"],
        "next_allowed_actions": [],
        "negative_invariants": {
            "same_origin_delivery_enabled": False,
            "provider_public_delivery_enabled": False,
            "provider_private_signed_url_enabled": False,
            "connector_dispatch_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def _load_material_snapshot_for_commit(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    snapshot = db.get(L3MaterialSnapshot, material_snapshot_id)
    if snapshot is None:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_material_snapshot_not_found",
            "No material snapshot exists for the source-directory package commit.",
            http_status=404,
            details={"material_snapshot_id": material_snapshot_id},
        )
    mismatches = [
        field
        for field, expected in {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "payload_hash": snapshot.payload_hash,
        }.items()
        if str(source_authority.get(field) or "") != str(expected)
    ]
    if mismatches:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_material_authority_mismatch",
            "The source-directory package commit source authority does not match the material snapshot.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )
    return snapshot


def _load_package_commit_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    session = db.get(L3Session, material_snapshot.session_id)
    if session is None:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_session_not_found",
            "No Layer 3 session owns the source-directory material snapshot.",
            http_status=404,
            details={"session_id": material_snapshot.session_id},
        )
    if session.status not in FINALIZED_PACKAGE_SESSION_STATUSES or session.completed_at is None:
        raise SourceDirectoryPackageCommitError(
            "source_directory_package_commit_session_not_terminal",
            "Source-directory package construction requires a finalized Layer 3 material session.",
            http_status=409,
            details={"session_id": session.session_id, "status": session.status},
        )
    return session


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
