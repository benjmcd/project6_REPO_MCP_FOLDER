from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    AnalysisRun,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    uuid_str,
)
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
    PASS_STATUS_RUNNING,
    PASS_STATUS_SELECTED_NOT_STARTED,
    PASS_TYPE_SINGLE_ITEM,
    PLAN_PREVIEW_HASH_SCHEMA_ID,
    Layer3PassEntryError,
    approve_pass_entry_plan,
    execute_selected_pass_run,
    preview_pass_entry,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    Layer3PackageEntryError,
    materialize_workbench_package_commit,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import (
    SUPPORTED_TYPING_RULES,
    Layer3TypingEntryError,
    materialize_typing_entry,
)

SCHEMA_VERSION = 1
ROUTE = "/review/layer3"
API_ROOT = "/api/v1/layer3"
SUPPORTED_SOURCE_CLASSES = ("dataset_version", "aps_content_document")
UNSUPPORTED_SOURCE_CLASSES = (
    "rag_vector_index",
    "arbitrary_local_directory",
    "broad_file_upload",
    "web_connector",
    "unbounded_runtime_db",
)
GATE_LABELS = ("intent", "sources", "gate_b", "gate_c", "plan", "execution", "results", "package")
ACTIVE_GATES = ("intent", "sources", "gate_b", "gate_c")
DOWNSTREAM_UNAVAILABLE = ("plan", "execution", "results", "package")
PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE = ("execution", "results", "package")
GATE_B_DECISIONS = ("approved", "denied", "isolated", "flagged")
PLAN_PREVIEW_SCOPE = "owner_service_default"
PLAN_APPROVAL_SCOPE = "owner_service_default"
PLAN_PREVIEW_IDENTITY_SCHEMA_ID = "layer3.plan_preview_identity.v1"
EXECUTION_READINESS_SCHEMA_ID = "layer3.execution_readiness_contract.v1"
EXECUTION_SELECTION_SCHEMA_ID = "layer3.execution_selection.v1"
EXECUTION_SELECTION_STATE_SCHEMA_ID = "layer3.execution_selection_state.v1"
EXECUTION_SELECTION_STATE = "execution_selected_not_started"
ANALYSIS_EXECUTION_START_SCHEMA_ID = "layer3.analysis_execution_start.v1"
ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID = "layer3.analysis_execution_start_state.v1"
EXECUTION_RESULT_STATUS_SCHEMA_ID = "layer3.execution_result_status.v1"
EXECUTION_RESULT_REVIEW_SCHEMA_ID = "layer3.execution_result_review.v1"
EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID = "layer3.execution_result_review_state.v1"
PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = "layer3.package_review_preview.v1"
PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID = "layer3.package_review_preview_state.v1"
PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = "layer3.package_construction_commit.v1"
PACKAGE_CONSTRUCTION_COMMIT_STATE_SCHEMA_ID = "layer3.package_construction_commit_state.v1"
EXECUTION_PASS_RUNNING_STATE = "execution_pass_running"
EXECUTION_PASS_COMPLETED_STATE = "execution_pass_completed"
EXECUTION_PASS_FAILED_STATE = "execution_pass_failed"
EXECUTION_RESULT_STATUS_AVAILABLE_STATE = "execution_result_status_available"
EXECUTION_RESULT_STATUS_BLOCKED_STATE = "execution_result_status_blocked"
EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE = "execution_result_status_missing_output"
EXECUTION_RESULT_REVIEW_READY_STATE = "execution_result_review_ready"
EXECUTION_RESULT_REVIEW_APPROVED_STATE = "execution_result_review_approved"
EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE = "execution_result_review_changes_requested"
EXECUTION_RESULT_REVIEW_REJECTED_STATE = "execution_result_review_rejected"
EXECUTION_RESULT_REVIEW_BLOCKED_STATE = "execution_result_review_blocked"
PACKAGE_REVIEW_PREVIEW_UNAVAILABLE_STATE = "package_review_preview_unavailable"
PACKAGE_REVIEW_PREVIEW_BLOCKED_STATE = "package_review_preview_blocked"
PACKAGE_REVIEW_PREVIEW_READY_STATE = "package_review_preview_ready"
PACKAGE_REVIEW_PREVIEW_INSPECTED_STATE = "package_review_preview_inspected"
PACKAGE_COMMIT_UNAVAILABLE_STATE = "package_commit_unavailable"
PACKAGE_COMMIT_BLOCKED_STATE = "package_commit_blocked"
PACKAGE_COMMIT_READY_STATE = "package_commit_ready"
PACKAGE_CONSTRUCTED_STATE = "package_constructed"
STATE_MODEL_SCHEMA_ID = "layer3.workbench_state_model.v1"
PLAN_REVISION_DECISIONS = frozenset({"reject_current_preview", "request_revision"})
PLAN_REVISION_STATE_BY_DECISION = {
    "reject_current_preview": "plan_rejected",
    "request_revision": "plan_revision_requested",
}
EXECUTION_RESULT_REVIEW_DECISIONS = frozenset({"approved", "changes_requested", "rejected", "blocked"})
EXECUTION_RESULT_REVIEW_STATE_BY_DECISION = {
    "approved": EXECUTION_RESULT_REVIEW_APPROVED_STATE,
    "changes_requested": EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE,
    "rejected": EXECUTION_RESULT_REVIEW_REJECTED_STATE,
    "blocked": EXECUTION_RESULT_REVIEW_BLOCKED_STATE,
}
EXECUTION_RESULT_REVIEW_ITEM_TYPES = frozenset(
    {
        "datum",
        "fact",
        "finding",
        "insight",
        "caveat",
        "contradiction",
        "unsupported_claim",
        "generated_narrative",
    }
)
PLAN_APPROVAL_FORBIDDEN_FIELDS = frozenset(
    {
        "execute",
        "execution",
        "run",
        "run_analysis",
        "package",
        "package_review",
        "handoff",
        "plan_edits",
        "natural_language_plan",
        "llm_plan",
    }
)
PLAN_REVISION_FORBIDDEN_FIELDS = PLAN_APPROVAL_FORBIDDEN_FIELDS | frozenset(
    {
        "execution_started",
        "create_pass_runs",
        "pass_run_ids",
        "artifact_manifest",
        "result_review",
        "qualitative_plan",
        "hybrid_plan",
        "rag_plan",
        "vector_plan",
    }
)
EXECUTION_SELECTION_FORBIDDEN_FIELDS = frozenset(
    {
        "execute",
        "execution",
        "run",
        "run_analysis",
        "start_execution",
        "analysis_run_id",
        "analysis_run_ids",
        "result_review",
        "results",
        "package",
        "package_review",
        "handoff",
        "artifact_manifest",
        "local_upload",
        "local_directory",
        "rag_plan",
        "vector_plan",
        "qualitative_plan",
        "hybrid_plan",
    }
)
ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS = frozenset(
    {
        "run_all",
        "batch",
        "package",
        "package_review",
        "handoff",
        "result_review",
        "local_upload",
        "local_directory",
        "rag_plan",
        "vector_plan",
        "qualitative_plan",
        "hybrid_plan",
        "approved_plan_supersession",
        "schema_migration",
    }
)
ANALYSIS_EXECUTION_START_ALLOWED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "execution_mode",
        "operator_reason",
    }
)
EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS = frozenset(
    {
        "approve_result",
        "reject_result",
        "result_review",
        "result_decision",
        "edited_findings",
        "package",
        "package_review",
        "handoff",
        "export",
        "rerun",
        "retry",
        "cancel",
        "run_all",
        "batch",
        "local_upload",
        "local_directory",
        "rag_plan",
        "vector_plan",
        "qualitative_plan",
        "hybrid_plan",
        "approved_plan_supersession",
        "schema_migration",
        "runtime_db_write",
    }
)
EXECUTION_RESULT_STATUS_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "operator_view_mode",
        "client_request_id",
    }
)
EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS = frozenset(
    {
        "package",
        "package_review",
        "handoff",
        "export",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
        "runtime_db_write",
        "artifact_manifest",
        "package_variant",
        "aps_handoff",
        "edited_findings",
        "rewrite_output",
    }
)
EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "operator_decision",
        "client_request_id",
        "review_notes",
        "reviewed_output_items",
        "analysis_run_id",
    }
)
PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS = frozenset(
    {
        "package",
        "package_review_decision",
        "create_package",
        "package_variant",
        "output_package_id",
        "reconciliation_record_id",
        "handoff",
        "export",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
        "runtime_db_write",
        "artifact_manifest",
        "aps_handoff",
        "edited_findings",
        "rewrite_output",
    }
)
PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "analysis_run_id",
        "client_request_id",
    }
)
PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS = frozenset(
    {
        "package_review_decision",
        "submit_package_review",
        "approve_package",
        "reject_package",
        "handoff",
        "export",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
        "runtime_db_write",
        "artifact_manifest",
        "analysis_artifact",
        "aps_handoff",
        "edited_findings",
        "rewrite_output",
        "package_payload",
        "package_variant_content",
    }
)
PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "client_request_id",
        "analysis_run_id",
        "expected_package_kinds",
    }
)
EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE = ("results", "package", "handoff")
ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE = ("results", "package", "handoff")
EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE = ("result_review", "package", "handoff")
EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE = ("package", "handoff", "package_review")
PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
)
PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)
PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE = (
    "package_review_submit",
    "handoff",
    "export",
)
EXECUTION_RESULT_STATUS_TERMINAL_PASS_STATUSES = frozenset(
    {PASS_STATUS_COMPLETED, PASS_STATUS_COMPLETED_WITH_WARNINGS, PASS_STATUS_FAILED}
)
PLAN_PREVIEW_HASH_INCLUDED_INPUTS = (
    "session_id",
    "committed_gate_b_material_and_source_ids",
    "committed_gate_c_analysis_set_unit_group_ids",
    "owner_service_plan_version",
    "admissible_and_excluded_set_payloads",
    "planned_pass_payloads",
    "deterministic_warning_codes",
)
PLAN_PREVIEW_HASH_EXCLUDED_INPUTS = (
    "browser_render_order",
    "local_ui_labels",
    "non_semantic_timestamps",
    "collapsed_or_expanded_ui_state",
    "non_authoritative_explanatory_text",
    "unpersisted_generated_alternatives",
)
READINESS_REQUIRED_GATES = (
    "proof-manifest",
    "state-model",
    "preview-hash",
    "idempotency",
    "concurrency",
    "revision-recovery",
    "approved-plan-correction",
    "output-taxonomy",
    "source-breadth",
    "execution-selection",
    "analysis-execution-start",
    "result-status",
    "result-review",
    "package-review-preview",
    "package-construction",
    "browser-proof",
)
READINESS_IMPLEMENTED_GATES = (
    "proof-manifest",
    "state-model",
    "preview-hash",
    "idempotency",
    "concurrency",
    "execution-selection",
    "analysis-execution-start",
    "result-status",
    "result-review",
    "package-review-preview",
    "package-construction",
)
READINESS_DEFERRED_GATES = (
    "revision-recovery",
    "approved-plan-correction",
    "output-taxonomy",
    "source-breadth",
    "browser-proof",
)


@dataclass(frozen=True)
class Layer3WorkbenchError(ValueError):
    error_code: str
    message: str
    status: str = "invalid"
    http_status: int = 400
    recoverable: bool = True
    blocked_fields: list[str] = field(default_factory=list)
    next_allowed_actions: list[str] = field(default_factory=list)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _stable_id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:16]}"


def _base_response(schema_id: str, *, request_id: str | None = None, status: str = "ok") -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id or uuid_str(),
        "server_time": _utcnow_iso(),
        "status": status,
    }


def workbench_error_response(exc: Layer3WorkbenchError, *, request_id: str | None = None) -> dict[str, Any]:
    return {
        **_base_response("layer3.workbench_error.v1", request_id=request_id, status=exc.status),
        "error_code": exc.error_code,
        "message": exc.message,
        "recoverable": exc.recoverable,
        "blocked_fields": list(exc.blocked_fields),
        "next_allowed_actions": list(exc.next_allowed_actions),
    }


def _authority_rail(
    *,
    session_id: str | None = None,
    preflight_id: str | None = None,
    source_set_id: str | None = None,
    current_gate: str = "intent",
    persistence_mode: str = "not_committed",
    source_classes: list[str] | None = None,
    counts: dict[str, int] | None = None,
    typing_status: str = "not_started",
    browser_only_state: list[str] | None = None,
    downstream_unavailable: list[str] | tuple[str, ...] | None = None,
    execution_enabled: bool = False,
    package_review_enabled: bool = False,
) -> dict[str, Any]:
    gate_counts = counts or {}
    return {
        "schema_id": "layer3.authority_rail.v1",
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id or "none",
        "preflight_id": preflight_id or "none",
        "source_set_id": source_set_id or "none",
        "current_gate": current_gate,
        "persistence_mode": persistence_mode,
        "source_authority": {
            "source_classes": list(source_classes or []),
            "runtime_label": None,
            "database_label": None,
            "storage_label": None,
        },
        "approved_material_count": gate_counts.get("approved", 0),
        "denied_material_count": gate_counts.get("denied", 0),
        "isolated_material_count": gate_counts.get("isolated", 0),
        "flagged_material_count": gate_counts.get("flagged", 0),
        "typing_status": typing_status,
        "execution_enabled": execution_enabled,
        "package_review_enabled": package_review_enabled,
        "downstream_unavailable": list(downstream_unavailable or DOWNSTREAM_UNAVAILABLE),
        "browser_only_state": list(browser_only_state or []),
    }


def _workbench_state_model() -> dict[str, Any]:
    return {
        "schema_id": STATE_MODEL_SCHEMA_ID,
        "authority_order": [
            "durable_layer3_session_state",
            "committed_gate_b_and_gate_c_decisions",
            "server_owner_service_preview",
            "persisted_approval_or_revision_control_state",
            "browser_display_cache_only",
        ],
        "states": [
            {
                "state": "intent_preflight_ready",
                "authority_source": "server_preflight_validation",
                "allowed_next_actions": ["source_preview"],
                "forbidden_downstream_actions": ["plan", "execution", "results", "package"],
            },
            {
                "state": "source_preview_ready",
                "authority_source": "server_source_preview",
                "allowed_next_actions": ["material_preview"],
                "forbidden_downstream_actions": ["plan", "execution", "results", "package"],
            },
            {
                "state": "material_preview_ready",
                "authority_source": "server_material_preview",
                "allowed_next_actions": ["gate_b_decision"],
                "forbidden_downstream_actions": ["plan", "execution", "results", "package"],
            },
            {
                "state": "gate_b_committed",
                "authority_source": "l3_session_and_l3_selection_manifest",
                "allowed_next_actions": ["gate_c_preview", "gate_c_commit"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
            {
                "state": "gate_c_typing_committed",
                "authority_source": "l3_typing_record_and_l3_analysis_set",
                "allowed_next_actions": ["plan_preview"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
            {
                "state": "plan_preview_ready",
                "authority_source": "server_owner_service_preview",
                "allowed_next_actions": ["plan_approve", "plan_reject", "plan_request_revision"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
            {
                "state": "plan_approved",
                "authority_source": "l3_analysis_plan_approval_only",
                "allowed_next_actions": ["execution_select"],
                "forbidden_downstream_actions": ["analysis_execution", "results", "package", "handoff"],
            },
            {
                "state": EXECUTION_SELECTION_STATE,
                "authority_source": "server_created_l3_pass_run_shell",
                "allowed_next_actions": ["analysis_execution_start"],
                "forbidden_downstream_actions": ["results", "package", "handoff"],
            },
            {
                "state": EXECUTION_PASS_RUNNING_STATE,
                "authority_source": "server_locked_l3_pass_run_transition",
                "allowed_next_actions": ["complete_or_fail_same_pass"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": EXECUTION_PASS_COMPLETED_STATE,
                "authority_source": "selected_l3_pass_run_and_wrapped_analysis_run",
                "allowed_next_actions": ["execution_result_status"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": EXECUTION_PASS_FAILED_STATE,
                "authority_source": "selected_l3_pass_run_failure_metadata",
                "allowed_next_actions": ["execution_result_status"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": EXECUTION_RESULT_STATUS_AVAILABLE_STATE,
                "authority_source": "terminal_selected_l3_pass_run_and_read_only_output_metadata",
                "allowed_next_actions": ["execution_result_status", "execution_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion"],
            },
            {
                "state": EXECUTION_RESULT_REVIEW_READY_STATE,
                "authority_source": "terminal_selected_l3_pass_run_with_readable_output_metadata",
                "allowed_next_actions": ["execution_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": EXECUTION_RESULT_REVIEW_APPROVED_STATE,
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE,
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": EXECUTION_RESULT_REVIEW_REJECTED_STATE,
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": EXECUTION_RESULT_REVIEW_BLOCKED_STATE,
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": PACKAGE_REVIEW_PREVIEW_UNAVAILABLE_STATE,
                "authority_source": "missing_session_plan_pass_result_status_or_result_review_authority",
                "allowed_next_actions": ["inspect_upstream_state"],
                "forbidden_downstream_actions": ["package_preview", "package_construction", "handoff"],
            },
            {
                "state": PACKAGE_REVIEW_PREVIEW_BLOCKED_STATE,
                "authority_source": "server_fail_closed_package_review_preview_check",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": [
                    "package_construction",
                    "package_review_submit",
                    "handoff",
                    "rerun",
                ],
            },
            {
                "state": PACKAGE_REVIEW_PREVIEW_READY_STATE,
                "authority_source": "approved_selected_pass_result_review_and_read_only_owner_service_assessment",
                "allowed_next_actions": ["inspect_package_candidates", "package_construction_commit"],
                "forbidden_downstream_actions": [
                    "package_review_submit",
                    "handoff",
                    "export",
                ],
            },
            {
                "state": PACKAGE_REVIEW_PREVIEW_INSPECTED_STATE,
                "authority_source": "read_only_package_review_preview_response",
                "allowed_next_actions": ["inspect_package_candidates", "package_construction_commit"],
                "forbidden_downstream_actions": [
                    "package_review_submit",
                    "handoff",
                    "export",
                ],
            },
            {
                "state": PACKAGE_COMMIT_UNAVAILABLE_STATE,
                "authority_source": "missing_package_review_preview_or_existing_incompatible_package_state",
                "allowed_next_actions": ["inspect_upstream_state"],
                "forbidden_downstream_actions": ["package_construction", "package_review_submit", "handoff", "export"],
            },
            {
                "state": PACKAGE_COMMIT_BLOCKED_STATE,
                "authority_source": "server_fail_closed_package_construction_commit_check",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": ["package_construction", "package_review_submit", "handoff", "export"],
            },
            {
                "state": PACKAGE_COMMIT_READY_STATE,
                "authority_source": "approved_result_review_and_matching_package_review_preview_hash",
                "allowed_next_actions": ["package_construction_commit"],
                "forbidden_downstream_actions": ["package_review_submit", "handoff", "export"],
            },
            {
                "state": PACKAGE_CONSTRUCTED_STATE,
                "authority_source": "l3_reconciliation_record_and_three_l3_output_package_rows",
                "allowed_next_actions": ["inspect_package_payloads"],
                "forbidden_downstream_actions": ["package_review_submit", "handoff", "export"],
            },
            {
                "state": EXECUTION_RESULT_STATUS_BLOCKED_STATE,
                "authority_source": "failed_result_status_authority_checks",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE,
                "authority_source": "terminal_selected_l3_pass_run_without_readable_output_metadata",
                "allowed_next_actions": ["execution_result_status"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": "plan_rejected",
                "authority_source": "l3_session_summary_plan_revision_control",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["approval", "execution", "results", "package"],
            },
            {
                "state": "plan_revision_requested",
                "authority_source": "l3_session_summary_plan_revision_control",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["approval", "execution", "results", "package"],
            },
            {
                "state": "execution_readiness_blocked",
                "authority_source": "layer3_execution_readiness_contract",
                "allowed_next_actions": ["resolve_deferred_readiness_gates"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
        ],
    }


def _plan_preview_hash_contract() -> dict[str, Any]:
    return {
        "schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "included_inputs": list(PLAN_PREVIEW_HASH_INCLUDED_INPUTS),
        "excluded_inputs": list(PLAN_PREVIEW_HASH_EXCLUDED_INPUTS),
        "mismatch_error_code": "preview_mismatch",
        "mismatch_rule": "fail_closed_no_execution_or_artifact_writes",
    }


def _preview_identity(*, preview_id: str, preview_hash: str) -> dict[str, Any]:
    return {
        "schema_id": PLAN_PREVIEW_IDENTITY_SCHEMA_ID,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "preview_hash_schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "stale_preview_writes_blocked": True,
        "mismatch_error_code": "preview_mismatch",
    }


def readiness_contract() -> dict[str, Any]:
    return {
        **_base_response(EXECUTION_READINESS_SCHEMA_ID),
        "execution_admitted": False,
        "execution_enabled": False,
        "execution_selection_admitted": True,
        "execution_selection_endpoint": f"{API_ROOT}/execution/select",
        "analysis_execution_admitted": False,
        "analysis_execution_start_admitted": True,
        "analysis_execution_start_endpoint": f"{API_ROOT}/execution/start",
        "execution_result_status_admitted": True,
        "execution_result_status_endpoint": f"{API_ROOT}/execution/result/status",
        "execution_result_review_admitted": True,
        "execution_result_review_endpoint": f"{API_ROOT}/execution/result/review",
        "package_review_preview_admitted": True,
        "package_review_preview_endpoint": f"{API_ROOT}/package/review/preview",
        "package_construction_commit_admitted": True,
        "package_construction_commit_endpoint": f"{API_ROOT}/package/review/commit",
        "package_review_admitted": False,
        "readiness_state": "execution_readiness_blocked",
        "required_gates": list(READINESS_REQUIRED_GATES),
        "implemented_gates": list(READINESS_IMPLEMENTED_GATES),
        "deferred_gates": list(READINESS_DEFERRED_GATES),
        "state_model": _workbench_state_model(),
        "preview_hash_contract": _plan_preview_hash_contract(),
        "idempotency_contract": {
            "schema_id": "layer3.idempotency_contract.v1",
            "client_request_id_supported": True,
            "client_request_id_required_current_slice": False,
            "client_request_id_required_for_execution_selection": True,
            "client_request_id_required_for_analysis_execution_start": True,
            "client_request_id_required_for_execution_result_status": False,
            "client_request_id_required_for_execution_result_review": True,
            "client_request_id_required_for_package_review_preview": False,
            "client_request_id_required_for_package_construction_commit": True,
            "duplicate_plan_approval": "returns existing approved-plan conflict; no duplicate L3AnalysisPlan",
            "duplicate_plan_revision": "returns existing revision-control conflict; no duplicate revision-control state",
            "duplicate_execution_selection": "same client_request_id and same approved plan returns existing selection; conflicts fail closed",
            "duplicate_analysis_execution_start": "same client_request_id and same selected pass returns existing execution state; conflicts fail closed",
            "duplicate_execution_result_status": "read-only status inspection does not create idempotency state",
            "duplicate_execution_result_review": "same client_request_id and same selected pass returns existing review state; conflicts fail closed",
            "duplicate_package_review_preview": "read-only package-review preview inspection does not create idempotency state",
            "duplicate_package_construction_commit": "same client_request_id and same authority basis returns existing package rows; conflicts fail closed",
            "duplicate_without_client_request_id": "server-authoritative state conflicts still prevent duplicate durable approval or revision-control state",
            "analysis_execution": "broad analysis execution remains blocked; selected-pass execution start is admitted separately",
        },
        "concurrency_contract": {
            "schema_id": "layer3.concurrency_contract.v1",
            "approval_revision_mutual_exclusion": True,
            "server_authority": "durable_session_row_lock_or_equivalent_transaction",
            "browser_in_flight_lock_is_authoritative": False,
            "execution_selection_uses_session_and_plan_locks": True,
            "analysis_execution_start_uses_session_plan_and_pass_locks": True,
            "execution_result_review_uses_session_and_pass_locks": True,
            "package_review_preview_is_read_only": True,
            "package_construction_commit_uses_session_plan_and_pass_locks": True,
            "broad_analysis_execution_requires_later_freeze": True,
        },
        "deferred_decisions": {
            "schema_id": "layer3.deferred_execution_decisions.v1",
            "revision_recovery": "requires later freeze",
            "approved_plan_correction": "requires later freeze",
            "output_taxonomy": "requires later freeze before results or package UI",
            "source_breadth": "requires later freeze before RAG/vector/upload/local-directory expansion",
            "package_construction": "admitted only for selected-pass workbench commit; broader package construction still requires later freeze",
            "package_review_submit": "requires later freeze before durable package-review decision state",
        },
    }


def bootstrap() -> dict[str, Any]:
    return {
        **_base_response("layer3.workbench_bootstrap.v1"),
        "route": ROUTE,
        "api_root": API_ROOT,
        "supported_source_classes": list(SUPPORTED_SOURCE_CLASSES),
        "preview_only_source_classes": [],
        "unsupported_source_classes": list(UNSUPPORTED_SOURCE_CLASSES),
        "gate_labels": list(GATE_LABELS),
        "active_gate_labels": list(ACTIVE_GATES),
        "unavailable_gate_labels": list(DOWNSTREAM_UNAVAILABLE),
        "features": {
            "plan_preview": True,
            "plan_approval": True,
            "execution_selection": True,
            "analysis_execution_start": True,
            "execution_result_status": True,
            "execution_result_review": True,
            "package_review_preview": True,
            "package_construction_commit": True,
            "analysis_execution": False,
            "qualitative_execution": False,
            "hybrid_execution": False,
            "rag_vector_retrieval": False,
            "package_review": False,
            "handoff": False,
            "runtime_snapshot_db_writes": False,
            "schema_widening": False,
            "typing_override_enabled": False,
        },
        "execution_readiness": {
            "schema_id": EXECUTION_READINESS_SCHEMA_ID,
            "execution_admitted": False,
            "execution_enabled": False,
            "execution_selection_admitted": True,
            "execution_selection_endpoint": f"{API_ROOT}/execution/select",
            "analysis_execution_admitted": False,
            "analysis_execution_start_admitted": True,
            "analysis_execution_start_endpoint": f"{API_ROOT}/execution/start",
            "execution_result_status_admitted": True,
            "execution_result_status_endpoint": f"{API_ROOT}/execution/result/status",
            "execution_result_review_admitted": True,
            "execution_result_review_endpoint": f"{API_ROOT}/execution/result/review",
            "package_review_preview_admitted": True,
            "package_review_preview_endpoint": f"{API_ROOT}/package/review/preview",
            "package_construction_commit_admitted": True,
            "package_construction_commit_endpoint": f"{API_ROOT}/package/review/commit",
            "package_review_admitted": False,
            "readiness_state": "execution_readiness_blocked",
            "readiness_endpoint": f"{API_ROOT}/readiness",
        },
        "authority_rail": _authority_rail(
            current_gate="intent",
            browser_only_state=["expanded_rows", "hidden_uncommitted_candidates", "selected_tab"],
        ),
    }


def _manual_constraints(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("manual_constraints") or {}
    return value if isinstance(value, dict) else {}


def _requested_source_classes(manual_constraints: dict[str, Any]) -> list[str]:
    source_classes = manual_constraints.get("source_classes") or []
    if not source_classes:
        return list(SUPPORTED_SOURCE_CLASSES)
    return [str(item) for item in source_classes]


def _unsupported_requested(classes: list[str]) -> list[str]:
    return [item for item in classes if item not in SUPPORTED_SOURCE_CLASSES]


def preflight(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    intent = str(payload.get("natural_language_intent") or "").strip()
    manual_constraints = _manual_constraints(payload)
    if not intent:
        raise Layer3WorkbenchError(
            "empty_intent",
            "Natural-language intent is required before source selection.",
            status="blocked",
            blocked_fields=["natural_language_intent"],
            next_allowed_actions=["edit_intent"],
        )
    if manual_constraints.get("conflict") is True or manual_constraints.get("conflicts"):
        raise Layer3WorkbenchError(
            "conflicting_constraints",
            "Manual constraints declare a conflict that must be resolved before source selection.",
            status="blocked",
            blocked_fields=["manual_constraints"],
            next_allowed_actions=["edit_constraints"],
        )
    source_classes = _requested_source_classes(manual_constraints)
    unsupported = _unsupported_requested(source_classes)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_source_class",
            f"Unsupported source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["manual_constraints.source_classes"],
            next_allowed_actions=["choose_supported_sources"],
        )
    normalized = {
        "intent_text": " ".join(intent.split()),
        "manual_constraints": _json_clone(manual_constraints),
    }
    preflight_id = _stable_id("preflight", normalized)
    return {
        **_base_response("layer3.preflight_result.v1", request_id=request_id),
        "preflight_id": preflight_id,
        "normalized_intent": normalized,
        "blockers": [],
        "warnings": [],
        "eligible_for_source_selection": True,
        "authority_rail": _authority_rail(
            preflight_id=preflight_id,
            current_gate="sources",
            persistence_mode="preview_only",
            source_classes=source_classes,
        ),
    }


def source_preview(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    preflight_id = str(payload.get("preflight_id") or "").strip()
    if not preflight_id:
        raise Layer3WorkbenchError("empty_intent", "preflight_id is required for source preview.", status="blocked")
    requested = [str(item) for item in payload.get("selected_source_classes") or SUPPORTED_SOURCE_CLASSES]
    unsupported = _unsupported_requested(requested)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_source_class",
            f"Unsupported source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["selected_source_classes"],
            next_allowed_actions=["choose_supported_sources"],
        )
    candidates = []
    for source_class in requested:
        short_id = _stable_id("src", {"preflight_id": preflight_id, "source_class": source_class}).split("-", 1)[1]
        candidates.append(
            {
                "source_candidate_id": f"src-{source_class}-{short_id}",
                "source_class": source_class,
                "source_label": source_class.replace("_", " ").title(),
                "source_ref": f"{source_class}:preview:{short_id}",
                "source_authority": "repo_supported",
                "eligible_for_material_preview": True,
                "unavailable_reason": None,
            }
        )
    source_set_id = _stable_id("source-set", [item["source_candidate_id"] for item in candidates])
    return {
        **_base_response("layer3.source_preview_result.v1", request_id=request_id),
        "source_set_id": source_set_id,
        "source_candidates": candidates,
        "unsupported_sources": [],
        "authority_rail": _authority_rail(
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            current_gate="gate_b",
            persistence_mode="preview_only",
            source_classes=requested,
        ),
    }


def _source_class_from_source_candidate_id(source_candidate_id: str) -> str | None:
    for source_class in SUPPORTED_SOURCE_CLASSES:
        if source_candidate_id.startswith(f"src-{source_class}-"):
            return source_class
    return None


def _source_class_from_material_candidate_id(candidate_id: str) -> str | None:
    for source_class in SUPPORTED_SOURCE_CLASSES:
        if candidate_id.startswith(f"mat-{source_class}-"):
            return source_class
    return None


def material_preview(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    source_ids = [str(item) for item in payload.get("source_candidate_ids") or []]
    if not source_ids:
        raise Layer3WorkbenchError("no_source_candidates", "At least one source candidate is required.", status="blocked")
    terms = [str(item) for item in (payload.get("query_basis") or {}).get("terms") or []]
    query_label = ", ".join(terms) if terms else "operator_intent"
    candidates = []
    for source_id in source_ids:
        source_class = _source_class_from_source_candidate_id(source_id)
        if source_class is None:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unknown source candidate: {source_id}.")
        short_id = _stable_id("mat", {"source_id": source_id, "query_basis": query_label}).split("-", 1)[1]
        planning_shape = "tabular_numeric" if source_class == "dataset_version" else "document_chunks"
        candidates.append(
            {
                "candidate_id": f"mat-{source_class}-{short_id}",
                "source_label": source_class.replace("_", " ").title(),
                "source_class": source_class,
                "source_ref": f"{source_class}:preview:{short_id}",
                "owner_service_source_shape": source_class,
                "planning_shape_family": planning_shape,
                "query_basis": query_label,
                "validation_status": "valid",
                "duplicate_status": "unique",
                "size_or_unit_count": 1,
                "preview_payload_ref": None,
                "provenance_ref": f"layer3-preview:{short_id}",
                "current_decision_state": "candidate",
            }
        )
    preview_id = _stable_id("material-preview", [item["candidate_id"] for item in candidates])
    return {
        **_base_response("layer3.material_preview_result.v1", request_id=request_id),
        "material_preview_id": preview_id,
        "material_candidates": candidates,
        "partial_retrieval": False,
        "authority_rail": _authority_rail(
            preflight_id=str(payload.get("preflight_id") or "none"),
            source_set_id=str(payload.get("source_set_id") or "none"),
            current_gate="gate_b",
            persistence_mode="preview_only",
            source_classes=sorted({item["source_class"] for item in candidates}),
        ),
    }


def _gate_b_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {decision: sum(1 for item in decisions if item["decision"] == decision) for decision in GATE_B_DECISIONS}


def _candidate_decision_manifest(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_id": "layer3.gate_b_decision_manifest.v1", "schema_version": SCHEMA_VERSION, "items": _json_clone(decisions)}


def gate_b_decision(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    raw_decisions = payload.get("candidate_decisions") or []
    if not isinstance(raw_decisions, list) or not raw_decisions:
        raise Layer3WorkbenchError("no_approved_material", "At least one Gate B decision is required.", status="blocked")

    decisions: list[dict[str, Any]] = []
    for raw in raw_decisions:
        if not isinstance(raw, dict):
            raise Layer3WorkbenchError("invalid_material_candidate", "Gate B decision entries must be objects.")
        candidate_id = str(raw.get("candidate_id") or "").strip()
        source_class = _source_class_from_material_candidate_id(candidate_id)
        decision = str(raw.get("decision") or "").strip()
        reason = str(raw.get("operator_reason") or "").strip()
        if source_class is None:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unknown material candidate: {candidate_id}.")
        if decision not in GATE_B_DECISIONS:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unsupported Gate B decision: {decision}.")
        if decision in {"denied", "isolated", "flagged"} and not reason:
            raise Layer3WorkbenchError(
                "invalid_material_candidate",
                f"Decision '{decision}' requires an operator reason.",
                blocked_fields=["candidate_decisions.operator_reason"],
            )
        decision_basis = raw.get("decision_basis") if isinstance(raw.get("decision_basis"), dict) else {}
        decisions.append(
            {
                "candidate_id": candidate_id,
                "source_class": source_class,
                "decision": decision,
                "operator_reason": reason,
                "decision_basis": _json_clone(decision_basis),
            }
        )

    approved = [item for item in decisions if item["decision"] == "approved"]
    if not approved:
        raise Layer3WorkbenchError(
            "no_approved_material",
            "At least one material candidate must be approved before Gate C.",
            status="blocked",
            next_allowed_actions=["approve_material", "revise_sources"],
        )

    counts = _gate_b_counts(decisions)
    decision_manifest = _candidate_decision_manifest(decisions)
    manifest_items = []
    for item in approved:
        short_id = hashlib.sha256(item["candidate_id"].encode("utf-8")).hexdigest()[:12]
        manifest_items.append(
            {
                "source_plane": f"plane_{item['source_class']}_{short_id}",
                "descriptor_type": item["source_class"],
                "selector_payload": {
                    "candidate_id": item["candidate_id"],
                    "source_ref": item["decision_basis"].get("source_ref", item["candidate_id"]),
                },
                "selection_basis": {
                    "candidate_id": item["candidate_id"],
                    "query_basis": item["decision_basis"].get("query_basis", "operator_intent"),
                    "provenance_ref": item["decision_basis"].get("provenance_ref", "layer3-preview"),
                    "gate_b_decision": "approved",
                },
                "expansion_reason": "gate_b_approved_material",
            }
        )

    session, manifest = commit_selection(
        db,
        SessionEntryRequest(
            manifest_items=manifest_items,
            source_plane_hints={
                "preflight_id": payload.get("preflight_id"),
                "source_set_id": payload.get("source_set_id"),
                "source_classes": sorted({item["source_class"] for item in approved}),
            },
            commit_reason=str(payload.get("commit_reason") or "operator_gate_b_decision"),
            entry_route_context={"route": ROUTE, "api_root": API_ROOT, "slice": "workbench_first_slice"},
            operator_context={"actor": payload.get("actor") or "operator", "layer3_gate_b_decision_manifest_v1": decision_manifest},
            summary={"current_gate": "gate_c", "gate_b_summary_v1": counts},
        ),
    )
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    for descriptor, item in zip(descriptors, approved, strict=True):
        record_retrieval_event(
            db,
            session=session,
            descriptor=descriptor,
            outcome="loaded",
            reason_code="gate_b_approved_preview_material",
            loaded_materials=[
                SnapshotMaterial(
                    source_shape=item["source_class"],
                    source_identity={"candidate_id": item["candidate_id"], "source_class": item["source_class"]},
                    source_provenance=item["decision_basis"],
                    payload={"candidate_id": item["candidate_id"], "source_class": item["source_class"], "decision": "approved"},
                    load_summary={"loaded_records": 1, "failed_records": 0, "preview_material": True},
                )
            ],
        )
    finalize_session(db, session=session)
    db.commit()
    return {
        **_base_response("layer3.gate_b_decision_result.v1", request_id=request_id),
        "session_id": session.session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "gate_b_decision_manifest_id": _stable_id("gate-b", decision_manifest),
        "approved_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "approved"],
        "denied_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "denied"],
        "isolated_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "isolated"],
        "flagged_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "flagged"],
        "next_state": "gate_c_preview_ready",
        "authority_rail": _authority_rail(
            session_id=session.session_id,
            preflight_id=str(payload.get("preflight_id") or "none"),
            source_set_id=str(payload.get("source_set_id") or "none"),
            current_gate="gate_c",
            persistence_mode="durable_layer3_control",
            source_classes=sorted({item["source_class"] for item in approved}),
            counts=counts,
        ),
    }


def _load_session(db: Session, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    return session


def _source_classes_from_latest_manifest(db: Session, session_id: str) -> list[str]:
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session_id)
        .order_by(L3SelectionManifest.committed_at.desc())
        .first()
    )
    if manifest is None:
        return []
    hints = manifest.source_plane_hints_json or {}
    hinted_classes = hints.get("source_classes")
    if isinstance(hinted_classes, list):
        return sorted({str(item) for item in hinted_classes if item is not None and str(item).strip()})
    items = (manifest.manifest_json or {}).get("items") or []
    return sorted(
        {
            str(item.get("descriptor_type"))
            for item in items
            if isinstance(item, dict) and str(item.get("descriptor_type") or "").strip()
        }
    )


def _snapshot_projection(snapshot: L3MaterialSnapshot) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    rule = SUPPORTED_TYPING_RULES.get(snapshot.source_shape)
    if rule is None:
        return None, {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "owner_service_source_shape": snapshot.source_shape,
            "reason": "unsupported_typing_shape",
        }
    return {
        "typing_record_id": None,
        "material_snapshot_id": snapshot.material_snapshot_id,
        "owner_service_source_shape": snapshot.source_shape,
        "planning_shape_family": rule.planning_shape_family,
        "candidate_modalities": list(rule.candidate_modalities),
        "chosen_modality": rule.chosen_modality,
        "confidence": rule.confidence,
        "authoritative": False,
    }, None


def _serialize_typing_record(record: L3TypingRecord) -> dict[str, Any]:
    basis = record.typing_basis_json or {}
    return {
        "typing_record_id": record.typing_record_id,
        "material_snapshot_id": record.material_snapshot_id,
        "owner_service_source_shape": basis.get("source_shape"),
        "planning_shape_family": basis.get("planning_shape_family"),
        "candidate_modalities": list(record.candidate_modalities_json or []),
        "chosen_modality": record.chosen_modality,
        "confidence": record.confidence,
        "authoritative": True,
    }


def _serialize_analysis_unit(unit: L3AnalysisUnit) -> dict[str, Any]:
    return {
        "analysis_unit_id": unit.analysis_unit_id,
        "unit_kind": unit.unit_kind,
        "analysis_modality": unit.analysis_modality,
        "member_snapshot_ids": list(unit.member_snapshot_ids_json or []),
        "typing_record_ids": list(unit.typing_record_ids_json or []),
        "must_remain_intact": unit.must_remain_intact,
        "authoritative": True,
    }


def _serialize_analysis_group(group: L3AnalysisGroup) -> dict[str, Any]:
    return {
        "analysis_group_id": group.analysis_group_id,
        "analysis_modality": group.analysis_modality,
        "analysis_unit_ids": list(group.analysis_unit_ids_json or []),
        "status": group.status,
        "typing_basis": group.typing_basis_json or {},
    }


def _serialize_analysis_set(analysis_set: L3AnalysisSet) -> dict[str, Any]:
    return {
        "analysis_set_id": analysis_set.analysis_set_id,
        "analysis_group_ids": list(analysis_set.analysis_group_ids_json or []),
        "analysis_unit_ids": list(analysis_set.analysis_unit_ids_json or []),
        "set_type": analysis_set.set_type,
        "formation_basis": analysis_set.formation_basis_json or {},
    }


def gate_c_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for Gate C preview.", http_status=404)
    session = _load_session(db, session_id)
    gate_b_counts = _gate_b_summary_from_session(session)
    source_classes = _source_classes_from_latest_manifest(db, session_id)
    commit_typing = bool(payload.get("commit_typing"))
    try:
        if commit_typing:
            result = materialize_typing_entry(db, session_id=session_id)
            db.commit()
            typing_records = [_serialize_typing_record(record) for record in result.typing_records]
            analysis_units = [_serialize_analysis_unit(unit) for unit in result.analysis_units]
            analysis_groups = [_serialize_analysis_group(group) for group in result.analysis_groups]
            analysis_sets = [_serialize_analysis_set(analysis_set) for analysis_set in result.analysis_sets]
            typing_status = "committed"
        else:
            snapshots = (
                db.query(L3MaterialSnapshot)
                .filter(L3MaterialSnapshot.session_id == session_id)
                .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
                .all()
            )
            if not snapshots:
                raise Layer3WorkbenchError(
                    "typing_not_ready",
                    f"Layer 3 session '{session_id}' has no material snapshots to type.",
                    status="blocked",
                )
            typing_records = []
            unsupported_material = []
            for snapshot in snapshots:
                projection, unsupported = _snapshot_projection(snapshot)
                if projection is not None:
                    typing_records.append(projection)
                if unsupported is not None:
                    unsupported_material.append(unsupported)
            analysis_units = [
                {
                    "analysis_unit_id": None,
                    "unit_kind": "atomic",
                    "analysis_modality": record["chosen_modality"],
                    "member_snapshot_ids": [record["material_snapshot_id"]],
                    "typing_record_ids": [],
                    "must_remain_intact": False,
                    "authoritative": False,
                }
                for record in typing_records
            ]
            analysis_groups = []
            analysis_sets = []
            typing_status = "previewed" if typing_records else "unavailable"
            return {
                **_base_response("layer3.gate_c_preview_result.v1", request_id=request_id),
                "session_id": session_id,
                "typing_records": typing_records,
                "analysis_units": analysis_units,
                "analysis_groups": analysis_groups,
                "analysis_sets": analysis_sets,
                "unsupported_material": unsupported_material,
                "override_allowed": False,
                "next_state": "first_slice_complete" if typing_records and not unsupported_material else "blocked_typing_unavailable",
                "authority_rail": _authority_rail(
                    session_id=session_id,
                    current_gate="complete" if typing_records and not unsupported_material else "gate_c",
                    persistence_mode="durable_layer3_control",
                    source_classes=source_classes,
                    counts=gate_b_counts,
                    typing_status=typing_status,
                ),
            }
    except Layer3WorkbenchError:
        raise
    except Layer3TypingEntryError as exc:
        detail = str(exc)
        code = "typing_already_materialized" if "already has" in detail else "typing_not_ready"
        raise Layer3WorkbenchError(code, detail, status="blocked", http_status=409) from exc

    return {
        **_base_response("layer3.gate_c_preview_result.v1", request_id=request_id),
        "session_id": session_id,
        "typing_records": typing_records,
        "analysis_units": analysis_units,
        "analysis_groups": analysis_groups,
        "analysis_sets": analysis_sets,
        "unsupported_material": [],
        "override_allowed": False,
        "next_state": "plan_preview_ready",
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="durable_layer3_control",
            source_classes=source_classes,
            counts=gate_b_counts,
            typing_status=typing_status,
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
    }


def gate_c_override_unavailable(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_response(
            "layer3.typing_override_unavailable.v1",
            request_id=str(payload.get("client_request_id") or uuid_str()),
            status="unavailable",
        ),
        "error_code": "override_unavailable",
        "message": "Typing override is not enabled in this first slice.",
        "recoverable": False,
        "next_allowed_actions": ["review_typing", "finish_first_slice"],
    }


def _gate_b_summary_from_session(session: L3Session) -> dict[str, int]:
    summary = session.summary_json or {}
    counts = summary.get("gate_b_summary_v1")
    if isinstance(counts, dict):
        return {decision: int(counts.get(decision, 0)) for decision in GATE_B_DECISIONS}
    decisions = ((session.operator_context_json or {}).get("layer3_gate_b_decision_manifest_v1") or {}).get("items") or []
    return _gate_b_counts([item for item in decisions if isinstance(item, dict)])


def _plan_preview_readiness(db: Session, *, session_id: str, include_owner_service: bool = False) -> dict[str, Any]:
    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    analysis_plan_count = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).count()
    pass_run_count = db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count()
    blocked_reason = None
    admitted_set_count = None
    excluded_set_count = None
    planned_pass_count = None
    if typing_record_count == 0:
        blocked_reason = "gate_c_not_committed"
    elif analysis_set_count == 0:
        blocked_reason = "no_analysis_sets"
    elif analysis_plan_count > 0 or pass_run_count > 0:
        blocked_reason = "plan_already_materialized"
    elif (revision_control := _plan_revision_control(db, session_id=session_id)) is not None:
        blocked_reason = str(revision_control.get("state") or "plan_revision_recorded")
    elif include_owner_service:
        try:
            owner_preview = preview_pass_entry(db, session_id=session_id)
            admitted_set_count = len(owner_preview.admitted_sets)
            excluded_set_count = len(owner_preview.excluded_sets)
            planned_pass_count = len(owner_preview.planned_passes)
        except Layer3PassEntryError as exc:
            blocked_reason = _plan_preview_error(exc).error_code
    return {
        "schema_id": "layer3.plan_preview_readiness.v1",
        "available": blocked_reason is None,
        "blocked_reason": blocked_reason,
        "typing_record_count": typing_record_count,
        "analysis_set_count": analysis_set_count,
        "analysis_plan_count": analysis_plan_count,
        "pass_run_count": pass_run_count,
        "admitted_set_count": admitted_set_count,
        "excluded_set_count": excluded_set_count,
        "planned_pass_count": planned_pass_count,
    }


def _latest_analysis_plan(db: Session, *, session_id: str) -> L3AnalysisPlan | None:
    return (
        db.query(L3AnalysisPlan)
        .filter(L3AnalysisPlan.session_id == session_id)
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .first()
    )


def _plan_revision_control_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    control = (session.summary_json or {}).get("plan_revision_control")
    if not isinstance(control, dict):
        return None
    if control.get("schema_id") != "layer3.plan_revision_control.v1":
        return None
    return control


def _plan_revision_control(db: Session, *, session_id: str) -> dict[str, Any] | None:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    return _plan_revision_control_from_session(session)


def _plan_approval_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    analysis_plan = _latest_analysis_plan(db, session_id=session_id)
    pass_run_count = db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count()
    if analysis_plan is None:
        preview = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
        return {
            "schema_id": "layer3.plan_approval_readiness.v1",
            "available": preview["available"],
            "approved": False,
            "blocked_reason": preview["blocked_reason"],
            "analysis_plan_id": None,
            "plan_status": None,
            "approved_by_operator": False,
            "approved_at": None,
            "approved_set_count": preview["admitted_set_count"],
            "excluded_set_count": preview["excluded_set_count"],
            "planned_pass_count": preview["planned_pass_count"],
            "pass_run_count": pass_run_count,
        }
    plan_json = analysis_plan.plan_json or {}
    approved = bool(analysis_plan.approved_by_operator)
    return {
        "schema_id": "layer3.plan_approval_readiness.v1",
        "available": False,
        "approved": approved,
        "blocked_reason": "plan_already_approved" if approved else "plan_already_materialized",
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "plan_status": analysis_plan.status,
        "approved_by_operator": approved,
        "approved_at": analysis_plan.approved_at.isoformat() if analysis_plan.approved_at else None,
        "approved_set_count": len(analysis_plan.analysis_set_ids_json or []),
        "excluded_set_count": len(plan_json.get("excluded_sets_json") or []),
        "planned_pass_count": len(plan_json.get("planned_passes_json") or []),
        "pass_run_count": pass_run_count,
        "approval_only": bool(plan_json.get("approval_only")),
        "execution_started": bool(plan_json.get("execution_started")),
    }


def _plan_revision_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    control = _plan_revision_control(db, session_id=session_id)
    if control is None:
        preview = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
        return {
            "schema_id": "layer3.plan_revision_readiness.v1",
            "available": preview["available"],
            "state": None,
            "blocked_reason": preview["blocked_reason"],
            "source_preview_id": None,
            "source_preview_hash": None,
            "operator_decision": None,
            "operator_note_recorded": False,
            "approval_available": preview["available"],
            "execution_started": False,
        }
    return {
        "schema_id": "layer3.plan_revision_readiness.v1",
        "available": False,
        "state": control.get("state"),
        "blocked_reason": control.get("state"),
        "source_preview_id": control.get("source_preview_id"),
        "source_preview_hash": control.get("source_preview_hash"),
        "operator_decision": control.get("operator_decision"),
        "operator_note_recorded": bool(control.get("operator_note_recorded")),
        "approval_available": False,
        "execution_started": False,
        "created_at": control.get("created_at"),
    }


def _source_classes_from_plan_preview(plan_preview: dict[str, Any]) -> list[str]:
    source_classes = set()
    for collection_name in ("admitted_sets", "excluded_sets"):
        for item in plan_preview.get(collection_name) or []:
            source_summary = item.get("source_summary") if isinstance(item, dict) else {}
            for source_class in (source_summary or {}).get("source_classes") or []:
                source_classes.add(str(source_class))
    return sorted(source_classes)


def _plan_preview_error(exc: Layer3PassEntryError) -> Layer3WorkbenchError:
    message = str(exc)
    if "was not found" in message:
        return Layer3WorkbenchError("session_not_found", message, http_status=404)
    if "must be finalized" in message:
        return Layer3WorkbenchError("gate_c_not_committed", message, status="blocked", http_status=409)
    if "already has analysis plans" in message or "already has pass runs" in message:
        return Layer3WorkbenchError("plan_already_materialized", message, status="conflict", http_status=409)
    if "has no analysis sets" in message:
        return Layer3WorkbenchError("no_analysis_sets", message, status="blocked", http_status=409)
    if "has no admissible analysis sets" in message:
        return Layer3WorkbenchError("no_admissible_plan", message, status="blocked", http_status=409)
    return Layer3WorkbenchError(
        "owner_service_error",
        message,
        status="failed",
        http_status=500,
        recoverable=False,
    )


def _plan_approval_error(exc: Layer3PassEntryError) -> Layer3WorkbenchError:
    message = str(exc)
    if "preview hash mismatch" in message:
        return Layer3WorkbenchError("preview_mismatch", message, status="conflict", http_status=409)
    if "operator confirmation" in message:
        return Layer3WorkbenchError(
            "operator_confirmation_required",
            message,
            status="blocked",
            http_status=400,
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_plan_approval"],
        )
    if "already has analysis plans" in message:
        return Layer3WorkbenchError("plan_already_materialized", message, status="conflict", http_status=409)
    if "already has pass runs" in message:
        return Layer3WorkbenchError("pass_runs_already_exist", message, status="conflict", http_status=409)
    return _plan_preview_error(exc)


def plan_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan preview.", http_status=404)

    preview_scope = str(payload.get("preview_scope") or PLAN_PREVIEW_SCOPE).strip()
    if preview_scope != PLAN_PREVIEW_SCOPE:
        raise Layer3WorkbenchError(
            "unsupported_preview_scope",
            f"Unsupported plan preview scope: {preview_scope}.",
            status="invalid",
            blocked_fields=["preview_scope"],
            next_allowed_actions=["use_owner_service_default"],
        )

    session = _load_session(db, session_id)
    gate_b_counts = _gate_b_summary_from_session(session)
    readiness = _plan_preview_readiness(db, session_id=session_id)
    if not readiness["available"]:
        raise Layer3WorkbenchError(
            readiness["blocked_reason"],
            f"Layer 3 session '{session_id}' is not ready for plan preview: {readiness['blocked_reason']}.",
            status="blocked" if readiness["blocked_reason"] != "plan_already_materialized" else "conflict",
            http_status=409,
            next_allowed_actions=["commit_gate_c_typing"] if readiness["blocked_reason"] == "gate_c_not_committed" else [],
        )

    try:
        owner_preview = preview_pass_entry(db, session_id=session_id)
    except Layer3PassEntryError as exc:
        raise _plan_preview_error(exc) from exc

    plan_preview_payload = {
        "schema_id": "layer3.plan_preview_payload.v1",
        "plan_version": PLAN_PREVIEW_SCOPE,
        "owner_plan_version": owner_preview.owner_service_basis["owner_plan_version"],
        "preview_hash": owner_preview.preview_hash,
        "preview_hash_contract": _plan_preview_hash_contract(),
        "approval_ready": True,
        "would_create_analysis_plan": False,
        "would_create_pass_runs": False,
        "would_execute_passes": False,
        "admitted_sets": [dict(item) for item in owner_preview.admitted_sets],
        "excluded_sets": [dict(item) for item in owner_preview.excluded_sets],
        "planned_passes": [dict(item) for item in owner_preview.planned_passes],
        "warnings": [dict(item) for item in owner_preview.warnings],
        "owner_service_basis": dict(owner_preview.owner_service_basis),
    }
    preview_id = _stable_id("plan-preview", {"session_id": session_id, "plan_preview": plan_preview_payload})
    return {
        **_base_response("layer3.plan_preview_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": "plan_preview_ready",
        "preview_id": preview_id,
        "preview_hash": owner_preview.preview_hash,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=owner_preview.preview_hash),
        "preview_only": True,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="preview_only",
            source_classes=_source_classes_from_plan_preview(plan_preview_payload),
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "plan_preview": plan_preview_payload,
    }


def _approved_set_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {**_json_clone(item), "readiness": "approved"}


def _approved_planned_pass_payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = _json_clone(item)
    payload.pop("preview_only", None)
    payload["approval_only"] = True
    payload["execution_status"] = "not_started"
    return payload


def plan_approval(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan approval.", http_status=404)

    if not bool(payload.get("operator_confirmation")):
        raise Layer3WorkbenchError(
            "operator_confirmation_required",
            "operator_confirmation must be true before plan approval is persisted.",
            status="blocked",
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_plan_approval"],
        )
    approval_scope = str(payload.get("approval_scope") or PLAN_APPROVAL_SCOPE).strip()
    if approval_scope != PLAN_APPROVAL_SCOPE:
        raise Layer3WorkbenchError(
            "unsupported_approval_scope",
            f"Unsupported plan approval scope: {approval_scope}.",
            status="invalid",
            blocked_fields=["approval_scope"],
            next_allowed_actions=["use_owner_service_default"],
        )
    forbidden = sorted(key for key in PLAN_APPROVAL_FORBIDDEN_FIELDS if key in payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan approval request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_approval_only_request"],
        )
    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    existing_control = _plan_revision_control_from_session(session)
    if existing_control is not None:
        raise Layer3WorkbenchError(
            str(existing_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )
    existing_plan = _latest_analysis_plan(db, session_id=session_id)
    if existing_plan is not None:
        if bool(existing_plan.approved_by_operator):
            error_code = "plan_already_approved"
            message = f"Layer 3 session '{session_id}' already has an approved analysis plan."
        else:
            error_code = "plan_already_materialized"
            message = f"Layer 3 session '{session_id}' already has a non-approved analysis plan."
        raise Layer3WorkbenchError(
            error_code,
            message,
            status="conflict",
            http_status=409,
        )
    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    expected_preview = plan_preview(
        db,
        {
            "client_request_id": request_id,
            "session_id": session_id,
            "preview_scope": PLAN_PREVIEW_SCOPE,
        },
    )
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    if preview_id != expected_preview["preview_id"] or preview_hash != expected_preview["preview_hash"]:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan approval must reference the current server-recomputed preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    try:
        approved = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview_hash,
            source_preview_id=preview_id,
            approved_by_operator=True,
        )
        db.commit()
    except Layer3PassEntryError as exc:
        db.rollback()
        raise _plan_approval_error(exc) from exc

    session = _load_session(db, session_id)
    gate_b_counts = _gate_b_summary_from_session(session)
    approved_sets = [_approved_set_payload(item) for item in approved.approved_sets]
    planned_passes = [_approved_planned_pass_payload(item) for item in approved.planned_passes]
    approved_plan = {
        "schema_id": "layer3.approved_plan_payload.v1",
        "plan_version": PLAN_APPROVAL_SCOPE,
        "source_preview_id": approved.source_preview_id,
        "source_preview_hash": approved.source_preview_hash,
        "would_create_pass_runs": False,
        "would_execute_passes": False,
        "approved_sets": approved_sets,
        "excluded_sets": [dict(item) for item in approved.excluded_sets],
        "planned_passes": planned_passes,
        "warnings": [dict(item) for item in approved.warnings],
        "owner_service_basis": dict(approved.owner_service_basis),
    }
    return {
        **_base_response("layer3.plan_approval_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": "plan_approved",
        "approval_only": True,
        "execution_started": False,
        "analysis_plan_id": approved.analysis_plan.analysis_plan_id,
        "plan_status": approved.analysis_plan.status,
        "approved_by_operator": bool(approved.analysis_plan.approved_by_operator),
        "approved_at": approved.analysis_plan.approved_at.isoformat() if approved.analysis_plan.approved_at else None,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="approved_plan",
            source_classes=_source_classes_from_plan_preview(
                {
                    "admitted_sets": approved_sets,
                    "excluded_sets": approved_plan["excluded_sets"],
                }
            ),
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "approved_plan": approved_plan,
    }


def plan_revision(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan revision.", http_status=404)

    operator_decision = str(payload.get("operator_decision") or "").strip()
    if operator_decision not in PLAN_REVISION_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_revision_decision",
            f"Unsupported plan revision decision: {operator_decision or 'missing'}.",
            status="invalid",
            blocked_fields=["operator_decision"],
            next_allowed_actions=["use_supported_revision_decision"],
        )

    forbidden = sorted(key for key in PLAN_REVISION_FORBIDDEN_FIELDS if key in payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan revision request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_revision_control_only_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    existing_control = _plan_revision_control_from_session(session)
    if existing_control is not None:
        raise Layer3WorkbenchError(
            str(existing_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    existing_plan = _latest_analysis_plan(db, session_id=session_id)
    if existing_plan is not None:
        if bool(existing_plan.approved_by_operator):
            error_code = "plan_already_approved"
            message = f"Layer 3 session '{session_id}' already has an approved analysis plan."
        else:
            error_code = "plan_already_materialized"
            message = f"Layer 3 session '{session_id}' already has a non-approved analysis plan."
        raise Layer3WorkbenchError(error_code, message, status="conflict", http_status=409)

    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    expected_preview = plan_preview(
        db,
        {
            "client_request_id": request_id,
            "session_id": session_id,
            "preview_scope": PLAN_PREVIEW_SCOPE,
        },
    )
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    if preview_id != expected_preview["preview_id"] or preview_hash != expected_preview["preview_hash"]:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan revision must reference the current server-recomputed preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    next_state = PLAN_REVISION_STATE_BY_DECISION[operator_decision]
    operator_note = str(payload.get("operator_note") or "").strip()
    gate_b_counts = _gate_b_summary_from_session(session)
    source_classes = _source_classes_from_plan_preview(expected_preview.get("plan_preview") or {})
    control = {
        "schema_id": "layer3.plan_revision_control.v1",
        "state": next_state,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "approval_available": False,
        "execution_started": False,
        "created_at": _utcnow_iso(),
    }
    session.summary_json = {
        **_json_clone(session.summary_json),
        "plan_revision_control": control,
    }
    db.commit()

    return {
        **_base_response("layer3.plan_revision_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": next_state,
        "revision_control_only": True,
        "execution_started": False,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="plan_revision_control",
            source_classes=source_classes,
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "downstream_unavailable": list(PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE),
        "plan_revision_control": control,
    }


def _execution_selection_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    selection = (session.summary_json or {}).get("execution_selection")
    if not isinstance(selection, dict):
        return None
    if selection.get("schema_id") != EXECUTION_SELECTION_STATE_SCHEMA_ID:
        return None
    return selection


def _execution_selection_pass_runs(db: Session, *, session_id: str) -> list[L3PassRun]:
    return (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == session_id)
        .order_by(L3PassRun.created_at.asc(), L3PassRun.pass_run_id.asc())
        .all()
    )


def _pass_run_analysis_run_id(pass_run: L3PassRun) -> str | None:
    value = (pass_run.summary_json or {}).get("analysis_run_id")
    return str(value) if value else None


def _pass_run_execution_started(pass_run: L3PassRun) -> bool:
    return bool((pass_run.summary_json or {}).get("execution_started")) or pass_run.status != PASS_STATUS_SELECTED_NOT_STARTED


def _execution_state_for_pass_runs(pass_runs: list[L3PassRun]) -> str:
    statuses = {pass_run.status for pass_run in pass_runs}
    if PASS_STATUS_RUNNING in statuses:
        return EXECUTION_PASS_RUNNING_STATE
    if PASS_STATUS_FAILED in statuses:
        return EXECUTION_PASS_FAILED_STATE
    if pass_runs and statuses <= {PASS_STATUS_COMPLETED, PASS_STATUS_COMPLETED_WITH_WARNINGS}:
        return EXECUTION_PASS_COMPLETED_STATE
    return EXECUTION_SELECTION_STATE


def _analysis_execution_start_from_pass_run(pass_run: L3PassRun) -> dict[str, Any] | None:
    state = (pass_run.summary_json or {}).get("analysis_execution_start")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID:
        return None
    return state


def _analysis_execution_start_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_run: L3PassRun,
) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    return {
        **_base_response(ANALYSIS_EXECUTION_START_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "execution_started": _pass_run_execution_started(pass_run),
        "analysis_run_id": _pass_run_analysis_run_id(pass_run),
        "pass_run_status": pass_run.status,
        "output_payload_ref": pass_run.output_payload_ref,
        "downstream_unavailable": list(ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE),
        "next_state": _execution_state_for_pass_runs([pass_run]),
        "engine_family": pass_run.engine_family,
        "selected_method_name": summary.get("selected_method_name"),
        "dataset_version_id": summary.get("dataset_version_id"),
    }


def _output_metadata_summary(pass_run: L3PassRun) -> tuple[dict[str, Any] | None, str | None]:
    output_ref = str(pass_run.output_payload_ref or "").strip()
    if not output_ref:
        return None, "output_payload_ref_missing"
    output_path = Path(output_ref)
    if not output_path.exists() or not output_path.is_file():
        return None, "output_metadata_file_missing"
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "output_metadata_unreadable"
    if not isinstance(payload, dict):
        return None, "output_metadata_malformed"
    artifact_refs = payload.get("artifact_refs_json")
    artifact_types = payload.get("artifact_types_json")
    return (
        {
            "present": True,
            "readable": True,
            "output_payload_ref": output_ref,
            "analysis_run_id": payload.get("analysis_run_id"),
            "analysis_set_id": payload.get("analysis_set_id"),
            "dataset_version_id": payload.get("dataset_version_id"),
            "selected_method_name": payload.get("selected_method_name"),
            "artifact_count": len(artifact_refs) if isinstance(artifact_refs, list) else 0,
            "artifact_refs": list(artifact_refs or []) if isinstance(artifact_refs, list) else [],
            "artifact_types": list(artifact_types or []) if isinstance(artifact_types, list) else [],
            "source_gate": payload.get("source_gate"),
        },
        None,
    )


def _execution_result_status_response(
    *,
    request_id: str | None,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_run: L3PassRun,
    analysis_run: AnalysisRun | None,
    output_metadata_summary: dict[str, Any] | None,
    output_metadata_error: str | None,
) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    start_state = _analysis_execution_start_from_pass_run(pass_run)
    pass_error = summary.get("error") or ((start_state or {}).get("error"))
    return {
        **_base_response(EXECUTION_RESULT_STATUS_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "execution_started": bool(start_state) or bool(summary.get("execution_started")),
        "analysis_run_id": _pass_run_analysis_run_id(pass_run),
        "analysis_run_status": analysis_run.status if analysis_run is not None else None,
        "pass_run_status": pass_run.status,
        "output_payload_ref": pass_run.output_payload_ref,
        "output_metadata_summary": output_metadata_summary,
        "output_metadata_error": output_metadata_error,
        "warnings_present": pass_run.status == PASS_STATUS_COMPLETED_WITH_WARNINGS,
        "error_present": pass_run.status == PASS_STATUS_FAILED or bool(pass_error),
        "error_message": str(pass_error) if pass_error else None,
        "result_status_available": status == "available",
        "result_review_enabled": False,
        "package_review_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE),
        "next_state": (
            EXECUTION_RESULT_STATUS_AVAILABLE_STATE
            if status == "available"
            else (
                EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE
                if status == "missing_output_metadata"
                else EXECUTION_RESULT_STATUS_BLOCKED_STATE
            )
        ),
        "operator_view_mode": "status_only",
        "engine_family": pass_run.engine_family,
        "selected_method_name": summary.get("selected_method_name"),
        "dataset_version_id": summary.get("dataset_version_id"),
    }


def _execution_result_review_from_pass_run(pass_run: L3PassRun) -> dict[str, Any] | None:
    state = (pass_run.summary_json or {}).get("execution_result_review")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID:
        return None
    return state


def _normalize_result_review_items(
    *,
    items: Any,
    session_id: str,
    analysis_plan_id: str,
    pass_run: L3PassRun,
    analysis_run_id: str | None,
    output_metadata_summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    if items is None:
        return [], 0
    if not isinstance(items, list):
        raise Layer3WorkbenchError(
            "reviewed_output_items_malformed",
            "reviewed_output_items must be a list when supplied.",
            status="invalid",
            blocked_fields=["reviewed_output_items"],
        )
    if len(items) > 50:
        raise Layer3WorkbenchError(
            "reviewed_output_items_too_large",
            "This result-review tranche admits at most 50 reviewed output items.",
            status="invalid",
            blocked_fields=["reviewed_output_items"],
        )

    normalized: list[dict[str, Any]] = []
    unresolved = 0
    required_trace = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "output_payload_ref": output_metadata_summary["output_payload_ref"],
    }
    if analysis_run_id:
        required_trace["analysis_run_id"] = analysis_run_id

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            unresolved += 1
            normalized.append(
                {
                    "index": index,
                    "item_type": None,
                    "trace_status": "unresolved",
                    "missing_trace_fields": ["item"],
                }
            )
            continue
        item_type = str(item.get("item_type") or "").strip()
        trace = item.get("trace") if isinstance(item.get("trace"), dict) else {}
        missing = [
            field
            for field, expected in required_trace.items()
            if str(trace.get(field) or "").strip() != str(expected)
        ]
        if item_type not in EXECUTION_RESULT_REVIEW_ITEM_TYPES:
            missing.append("item_type")
        if missing:
            unresolved += 1
        normalized.append(
            {
                "index": index,
                "item_ref": str(item.get("item_ref") or item.get("output_item_ref") or f"item-{index}"),
                "item_type": item_type or None,
                "trace_status": "resolved" if not missing else "unresolved",
                "missing_trace_fields": sorted(set(missing)),
            }
        )
    return normalized, unresolved


def _result_review_trace_summary(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run: L3PassRun,
    analysis_run_id: str | None,
    output_metadata_summary: dict[str, Any],
    reviewed_items: list[dict[str, Any]],
    unresolved_trace_count: int,
) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    return {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "analysis_run_id": analysis_run_id,
        "output_payload_ref": output_metadata_summary["output_payload_ref"],
        "analysis_set_id": output_metadata_summary.get("analysis_set_id"),
        "dataset_version_id": output_metadata_summary.get("dataset_version_id") or summary.get("dataset_version_id"),
        "selected_method_name": output_metadata_summary.get("selected_method_name") or summary.get("selected_method_name"),
        "artifact_count": output_metadata_summary.get("artifact_count", 0),
        "artifact_types": list(output_metadata_summary.get("artifact_types") or []),
        "source_gate": output_metadata_summary.get("source_gate"),
        "reviewed_item_count": len(reviewed_items),
        "unresolved_trace_count": unresolved_trace_count,
    }


def _execution_result_review_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_run: L3PassRun,
    analysis_run_id: str | None,
    review_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        **_base_response(EXECUTION_RESULT_REVIEW_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": analysis_run_id,
        "result_status_available": True,
        "result_review_enabled": True,
        "review_state": review_state["review_state"],
        "operator_decision": review_state["operator_decision"],
        "review_record_ref": review_state["review_record_ref"],
        "trace_summary": _json_clone(review_state["trace_summary"]),
        "reviewed_output_items": _json_clone(review_state.get("reviewed_output_items") or []),
        "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
        "package_review_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
        "review_notes_recorded": bool(str(review_state.get("review_notes") or "").strip()),
        "engine_family": pass_run.engine_family,
    }


def _execution_selection_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_runs: list[L3PassRun],
) -> dict[str, Any]:
    analysis_run_ids = [value for pass_run in pass_runs if (value := _pass_run_analysis_run_id(pass_run))]
    return {
        **_base_response(EXECUTION_SELECTION_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "pass_run_ids": [pass_run.pass_run_id for pass_run in pass_runs],
        "pass_run_count": len(pass_runs),
        "execution_started": any(_pass_run_execution_started(pass_run) for pass_run in pass_runs),
        "analysis_run_ids": analysis_run_ids,
        "pass_run_statuses": {pass_run.pass_run_id: pass_run.status for pass_run in pass_runs},
        "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        "next_state": _execution_state_for_pass_runs(pass_runs),
    }


def _execution_selection_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    selection = _execution_selection_from_session(session)
    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    if selection is not None:
        analysis_run_ids = [value for pass_run in pass_runs if (value := _pass_run_analysis_run_id(pass_run))]
        return {
            "schema_id": "layer3.execution_selection_readiness.v1",
            "available": False,
            "selected": True,
            "state": selection.get("state") or _execution_state_for_pass_runs(pass_runs),
            "blocked_reason": "execution_selection_already_exists",
            "analysis_plan_id": selection.get("analysis_plan_id"),
            "source_preview_id": selection.get("source_preview_id"),
            "source_preview_hash": selection.get("source_preview_hash"),
            "pass_run_ids": [pass_run.pass_run_id for pass_run in pass_runs],
            "pass_run_count": len(pass_runs),
            "execution_started": any(_pass_run_execution_started(pass_run) for pass_run in pass_runs),
            "analysis_run_ids": analysis_run_ids,
            "pass_run_statuses": {pass_run.pass_run_id: pass_run.status for pass_run in pass_runs},
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
            "selected_at": selection.get("selected_at"),
        }

    analysis_plan_id = None
    source_preview_id = None
    source_preview_hash = None
    if (revision_control := _plan_revision_control(db, session_id=session_id)) is not None:
        blocked_reason = str(revision_control.get("state") or "plan_revision_recorded")
    else:
        approved_plans = (
            db.query(L3AnalysisPlan)
            .filter(
                L3AnalysisPlan.session_id == session_id,
                L3AnalysisPlan.status == "approved",
                L3AnalysisPlan.approved_by_operator.is_(True),
            )
            .all()
        )
        if not approved_plans:
            blocked_reason = "no_approved_plan"
        elif len(approved_plans) > 1:
            blocked_reason = "multiple_approved_plans"
        elif pass_runs:
            blocked_reason = "pass_runs_already_exist"
        else:
            approved_plan = approved_plans[0]
            plan_json = approved_plan.plan_json or {}
            analysis_plan_id = approved_plan.analysis_plan_id
            source_preview_id = plan_json.get("source_preview_id")
            source_preview_hash = plan_json.get("source_preview_hash")
            blocked_reason = None

    return {
        "schema_id": "layer3.execution_selection_readiness.v1",
        "available": blocked_reason is None,
        "selected": False,
        "state": None,
        "blocked_reason": blocked_reason,
        "analysis_plan_id": analysis_plan_id,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "pass_run_ids": [],
        "pass_run_count": len(pass_runs),
        "execution_started": False,
        "analysis_run_ids": [],
        "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        "selected_at": None,
    }


def execution_selection(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for execution selection.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_execution_selection"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_selection_fields",
            f"Execution selection is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_selection_request"],
        )

    forbidden = sorted(key for key in EXECUTION_SELECTION_FORBIDDEN_FIELDS if key in payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "analysis_execution_not_admitted",
            f"Execution selection request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_selection_only_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)

    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == "approved",
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]

    existing_selection = _execution_selection_from_session(session)
    existing_pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    if existing_selection is not None:
        stored_pass_run_ids = list(existing_selection.get("pass_run_ids_json") or [])
        existing_pass_run_ids = [pass_run.pass_run_id for pass_run in existing_pass_runs]
        if stored_pass_run_ids != existing_pass_run_ids:
            raise Layer3WorkbenchError(
                "execution_selection_inconsistent",
                f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
                status="conflict",
                http_status=409,
            )
        if str(existing_selection.get("client_request_id") or "") == request_id:
            if (
                str(existing_selection.get("analysis_plan_id") or "") == analysis_plan_id
                and str(existing_selection.get("source_preview_id") or "") == preview_id
                and str(existing_selection.get("source_preview_hash") or "") == preview_hash
            ):
                return _execution_selection_response(
                    request_id=request_id,
                    status="already_selected",
                    session_id=session_id,
                    analysis_plan_id=analysis_plan_id,
                    preview_id=preview_id,
                    preview_hash=preview_hash,
                    pass_runs=existing_pass_runs,
                )
            raise Layer3WorkbenchError(
                "idempotency_conflict",
                "client_request_id already selected execution for a different approved plan or preview identity.",
                status="conflict",
                http_status=409,
                blocked_fields=["client_request_id"],
            )
        raise Layer3WorkbenchError(
            "execution_selection_already_exists",
            f"Layer 3 session '{session_id}' already has an execution selection.",
            status="conflict",
            http_status=409,
        )
    if existing_pass_runs:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Execution selection must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Execution selection must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    approved_set_ids = [str(item) for item in (approved_plan.analysis_set_ids_json or []) if str(item)]
    planned_passes = [item for item in (plan_json.get("planned_passes_json") or []) if isinstance(item, dict)]
    if not approved_set_ids or not planned_passes:
        raise Layer3WorkbenchError(
            "no_admissible_plan",
            f"Layer 3 session '{session_id}' has no approved analysis sets for execution selection.",
            status="blocked",
            http_status=409,
        )

    planned_by_set_id = {str(item.get("analysis_set_id") or ""): item for item in planned_passes}
    selected_planned_passes: list[dict[str, Any]] = []
    for analysis_set_id in approved_set_ids:
        planned_pass = planned_by_set_id.get(analysis_set_id)
        if planned_pass is None:
            raise Layer3WorkbenchError(
                "approved_plan_malformed",
                f"Approved plan '{analysis_plan_id}' is missing a planned pass for analysis set '{analysis_set_id}'.",
                status="conflict",
                http_status=409,
            )
        if not str(planned_pass.get("pass_type") or "").strip():
            raise Layer3WorkbenchError(
                "approved_plan_malformed",
                f"Approved plan '{analysis_plan_id}' has a planned pass without pass_type.",
                status="conflict",
                http_status=409,
            )
        selected_planned_passes.append(planned_pass)

    selected_at = _utcnow_iso()
    pass_runs: list[L3PassRun] = []
    for planned_pass in selected_planned_passes:
        pass_run_id = uuid_str()
        pass_run = L3PassRun(
            pass_run_id=pass_run_id,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            analysis_set_id=str(planned_pass.get("analysis_set_id")),
            pass_type=str(planned_pass.get("pass_type")),
            engine_family=str(planned_pass.get("engine_family") or "wrapped_quantitative_analysis"),
            status="selected_not_started",
            started_at=None,
            completed_at=None,
            input_payload_ref=f"layer3://execution-selection/{pass_run_id}/input",
            output_payload_ref=None,
            summary_json={
                "schema_id": "layer3.pass_run_shell_summary.v1",
                "execution_selection_schema_id": EXECUTION_SELECTION_SCHEMA_ID,
                "selection_state": EXECUTION_SELECTION_STATE,
                "client_request_id": request_id,
                "analysis_plan_id": analysis_plan_id,
                "source_preview_id": preview_id,
                "source_preview_hash": preview_hash,
                "execution_started": False,
                "analysis_run_id": None,
                "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
                "planned_pass": _json_clone(planned_pass),
                "selected_at": selected_at,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        pass_runs.append(pass_run)

    db.flush()
    session.summary_json = {
        **_json_clone(session.summary_json),
        "execution_selection": {
            "schema_id": EXECUTION_SELECTION_STATE_SCHEMA_ID,
            "state": EXECUTION_SELECTION_STATE,
            "client_request_id": request_id,
            "analysis_plan_id": analysis_plan_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "pass_run_ids_json": [pass_run.pass_run_id for pass_run in pass_runs],
            "pass_run_count": len(pass_runs),
            "execution_started": False,
            "analysis_run_ids_json": [],
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
            "operator_reason_recorded": bool(str(payload.get("operator_reason") or "").strip()),
            "selected_at": selected_at,
        },
    }
    db.commit()

    return _execution_selection_response(
        request_id=request_id,
        status="selected_not_started",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_runs=pass_runs,
    )


def analysis_execution_start(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for analysis execution start.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_analysis_execution_start"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_analysis_execution_start_fields",
            f"Analysis execution start is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_analysis_execution_start_request"],
        )

    unknown = sorted(key for key in payload if key not in ANALYSIS_EXECUTION_START_ALLOWED_FIELDS)
    forbidden = sorted(key for key in ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "analysis_execution_start_scope_not_admitted",
            f"Analysis execution start request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_single_pass_execution_start_request"],
        )
    execution_mode = str(payload.get("execution_mode") or "synchronous_single_pass").strip()
    if execution_mode != "synchronous_single_pass":
        raise Layer3WorkbenchError(
            "unsupported_execution_mode",
            "This Layer 3 tranche admits only synchronous_single_pass execution start.",
            status="invalid",
            blocked_fields=["execution_mode"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == "approved",
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]
    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Analysis execution start must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Analysis execution start must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    selection = _execution_selection_from_session(session)
    if selection is None:
        raise Layer3WorkbenchError(
            "execution_selection_required",
            "Analysis execution start requires a prior execution selection.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["submit_execution_selection"],
        )
    if (
        str(selection.get("analysis_plan_id") or "") != analysis_plan_id
        or str(selection.get("source_preview_id") or "") != preview_id
        or str(selection.get("source_preview_hash") or "") != preview_hash
    ):
        raise Layer3WorkbenchError(
            "execution_selection_mismatch",
            "Execution selection does not match the supplied approved plan preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id", "preview_id", "preview_hash"],
        )

    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    stored_pass_run_ids = [str(item) for item in (selection.get("pass_run_ids_json") or [])]
    actual_pass_run_ids = [pass_run.pass_run_id for pass_run in pass_runs]
    if stored_pass_run_ids != actual_pass_run_ids:
        raise Layer3WorkbenchError(
            "execution_selection_inconsistent",
            f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
            status="conflict",
            http_status=409,
        )
    if pass_run_id not in stored_pass_run_ids:
        raise Layer3WorkbenchError(
            "pass_run_not_selected",
            "Analysis execution start may execute only a pass run from the current execution selection.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    if any(pass_run.status == PASS_STATUS_RUNNING and pass_run.pass_run_id != pass_run_id for pass_run in pass_runs):
        raise Layer3WorkbenchError(
            "analysis_execution_already_running",
            "Another selected pass run is already running for this session.",
            status="conflict",
            http_status=409,
        )

    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if pass_run is None:
        raise Layer3WorkbenchError("pass_run_not_found", f"Layer 3 pass run '{pass_run_id}' was not found.", http_status=404)
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "pass_run_mismatch",
            "Analysis execution start pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    pass_summary = pass_run.summary_json or {}
    if str(pass_summary.get("source_preview_id") or "") != preview_id or str(pass_summary.get("source_preview_hash") or "") != preview_hash:
        raise Layer3WorkbenchError(
            "pass_run_preview_mismatch",
            "Selected pass run does not match the supplied preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
        )
    planned_pass = pass_summary.get("planned_pass")
    if not isinstance(planned_pass, dict):
        raise Layer3WorkbenchError(
            "selected_pass_malformed",
            "Selected pass run is missing its approved planned-pass payload.",
            status="conflict",
            http_status=409,
        )
    if pass_run.engine_family != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS or str(planned_pass.get("engine_family") or "") != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS:
        raise Layer3WorkbenchError(
            "unsupported_analysis_execution_engine",
            "This execution-start slice admits only wrapped quantitative pass runs.",
            status="conflict",
            http_status=409,
        )
    if str(planned_pass.get("pass_type") or pass_run.pass_type) != PASS_TYPE_SINGLE_ITEM:
        raise Layer3WorkbenchError(
            "unsupported_analysis_execution_source_breadth",
            "This execution-start slice admits only selected single-item dataset-version pass runs.",
            status="conflict",
            http_status=409,
        )

    existing_start = _analysis_execution_start_from_pass_run(pass_run)
    if existing_start is not None:
        if str(existing_start.get("client_request_id") or "") == request_id:
            status = "already_completed" if pass_run.status in {PASS_STATUS_COMPLETED, PASS_STATUS_COMPLETED_WITH_WARNINGS} else pass_run.status
            return _analysis_execution_start_response(
                request_id=request_id,
                status=status,
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                pass_run=pass_run,
            )
        raise Layer3WorkbenchError(
            "analysis_execution_already_started",
            "Selected pass run already has analysis execution-start state from a different request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    if pass_run.status != PASS_STATUS_SELECTED_NOT_STARTED or _pass_run_analysis_run_id(pass_run):
        raise Layer3WorkbenchError(
            "pass_run_not_selected_not_started",
            "Analysis execution start requires a selected_not_started pass run with no analysis_run_id.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    try:
        execute_selected_pass_run(
            db,
            pass_run=pass_run,
            planned_pass=planned_pass,
            client_request_id=request_id,
        )
    except Layer3PassEntryError as exc:
        raise Layer3WorkbenchError(
            "analysis_execution_start_not_admitted",
            str(exc),
            status="conflict",
            http_status=409,
        ) from exc

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "analysis_execution_start_inconsistent",
            "Analysis execution start could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )
    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    analysis_run_ids = [value for item in pass_runs if (value := _pass_run_analysis_run_id(item))]
    execution_state = _execution_state_for_pass_runs(pass_runs)
    completed_at = pass_run.completed_at.isoformat() if pass_run.completed_at else None
    started_at = pass_run.started_at.isoformat() if pass_run.started_at else None
    session.summary_json = {
        **_json_clone(session.summary_json),
        "execution_selection": {
            **_json_clone(_execution_selection_from_session(session) or selection),
            "state": execution_state,
            "execution_started": any(_pass_run_execution_started(item) for item in pass_runs),
            "analysis_run_ids_json": analysis_run_ids,
            "pass_run_statuses_json": {item.pass_run_id: item.status for item in pass_runs},
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        },
        "analysis_execution_start": {
            "schema_id": ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
            "client_request_id": request_id,
            "state": execution_state,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "analysis_run_id": _pass_run_analysis_run_id(pass_run),
            "pass_run_status": pass_run.status,
            "output_payload_ref": pass_run.output_payload_ref,
            "downstream_unavailable": list(ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE),
            "operator_reason_recorded": bool(str(payload.get("operator_reason") or "").strip()),
            "started_at": started_at,
            "completed_at": completed_at,
        },
    }
    db.commit()

    return _analysis_execution_start_response(
        request_id=request_id,
        status=pass_run.status,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_run=pass_run,
    )


def execution_result_status(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    request_id = str(payload.get("client_request_id") or "").strip() or None
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    operator_view_mode = str(payload.get("operator_view_mode") or "status_only").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_result_status_fields",
            f"Execution result/status request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_result_status_request"],
        )

    unknown = sorted(key for key in payload if key not in EXECUTION_RESULT_STATUS_ALLOWED_FIELDS)
    forbidden = sorted(key for key in EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "execution_result_status_scope_not_admitted",
            f"Execution result/status request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_status_only_execution_result_status_request"],
        )
    if operator_view_mode != "status_only":
        raise Layer3WorkbenchError(
            "unsupported_execution_result_status_view_mode",
            "This Layer 3 tranche admits only status_only result/status inspection.",
            status="invalid",
            blocked_fields=["operator_view_mode"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == "approved",
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]
    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Execution result/status must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Execution result/status must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    selection = _execution_selection_from_session(session)
    if selection is None:
        raise Layer3WorkbenchError(
            "execution_selection_required",
            "Execution result/status requires a prior execution selection.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["submit_execution_selection"],
        )
    if (
        str(selection.get("analysis_plan_id") or "") != analysis_plan_id
        or str(selection.get("source_preview_id") or "") != preview_id
        or str(selection.get("source_preview_hash") or "") != preview_hash
    ):
        raise Layer3WorkbenchError(
            "execution_selection_mismatch",
            "Execution selection does not match the supplied approved plan preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id", "preview_id", "preview_hash"],
        )

    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    stored_pass_run_ids = [str(item) for item in (selection.get("pass_run_ids_json") or [])]
    actual_pass_run_ids = [pass_run.pass_run_id for pass_run in pass_runs]
    if stored_pass_run_ids != actual_pass_run_ids:
        raise Layer3WorkbenchError(
            "execution_selection_inconsistent",
            f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
            status="conflict",
            http_status=409,
        )
    if pass_run_id not in stored_pass_run_ids:
        raise Layer3WorkbenchError(
            "pass_run_not_selected",
            "Execution result/status may inspect only a pass run from the current execution selection.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).first()
    if pass_run is None:
        raise Layer3WorkbenchError("pass_run_not_found", f"Layer 3 pass run '{pass_run_id}' was not found.", http_status=404)
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "pass_run_mismatch",
            "Execution result/status pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    pass_summary = pass_run.summary_json or {}
    if str(pass_summary.get("source_preview_id") or "") != preview_id or str(pass_summary.get("source_preview_hash") or "") != preview_hash:
        raise Layer3WorkbenchError(
            "pass_run_preview_mismatch",
            "Selected pass run does not match the supplied preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
        )
    planned_pass = pass_summary.get("planned_pass")
    if not isinstance(planned_pass, dict):
        raise Layer3WorkbenchError(
            "selected_pass_malformed",
            "Selected pass run is missing its approved planned-pass payload.",
            status="conflict",
            http_status=409,
        )
    if pass_run.engine_family != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS or str(planned_pass.get("engine_family") or "") != ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS:
        raise Layer3WorkbenchError(
            "unsupported_execution_result_status_engine",
            "This result/status slice admits only wrapped quantitative pass runs.",
            status="conflict",
            http_status=409,
        )
    if str(planned_pass.get("pass_type") or pass_run.pass_type) != PASS_TYPE_SINGLE_ITEM:
        raise Layer3WorkbenchError(
            "unsupported_execution_result_status_source_breadth",
            "This result/status slice admits only selected single-item dataset-version pass runs.",
            status="conflict",
            http_status=409,
        )

    start_state = _analysis_execution_start_from_pass_run(pass_run)
    if start_state is None:
        raise Layer3WorkbenchError(
            "analysis_execution_start_required",
            "Execution result/status requires prior selected-pass analysis execution-start state.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["submit_analysis_execution_start"],
        )
    if pass_run.status not in EXECUTION_RESULT_STATUS_TERMINAL_PASS_STATUSES:
        raise Layer3WorkbenchError(
            "pass_run_not_terminal",
            "Execution result/status requires a terminal selected pass run.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    analysis_run_id = _pass_run_analysis_run_id(pass_run)
    if supplied_analysis_run_id and supplied_analysis_run_id != str(analysis_run_id or ""):
        raise Layer3WorkbenchError(
            "analysis_run_mismatch",
            "Supplied analysis_run_id does not match the selected pass run.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_run_id"],
        )
    analysis_run = db.get(AnalysisRun, analysis_run_id) if analysis_run_id else None
    if analysis_run_id and analysis_run is None:
        raise Layer3WorkbenchError(
            "analysis_run_not_found",
            "Selected pass run references an analysis_run_id that is not present.",
            status="conflict",
            http_status=409,
        )

    output_summary, output_error = _output_metadata_summary(pass_run)
    if pass_run.status == PASS_STATUS_FAILED:
        response_status = "failed"
    elif output_summary is None:
        response_status = "missing_output_metadata"
    else:
        response_status = "available"

    return _execution_result_status_response(
        request_id=request_id,
        status=response_status,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_run=pass_run,
        analysis_run=analysis_run,
        output_metadata_summary=output_summary,
        output_metadata_error=output_error,
    )


def execution_result_review(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    operator_decision = str(payload.get("operator_decision") or "").strip()
    request_id = str(payload.get("client_request_id") or "").strip()
    review_notes = str(payload.get("review_notes") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("operator_decision", operator_decision),
            ("client_request_id", request_id),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_result_review_fields",
            f"Execution result-review request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_result_review_request"],
        )

    unknown = sorted(key for key in payload if key not in EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS)
    forbidden = sorted(key for key in EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "execution_result_review_scope_not_admitted",
            f"Execution result-review request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_execution_result_review_request"],
        )
    if operator_decision not in EXECUTION_RESULT_REVIEW_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_execution_result_review_decision",
            "operator_decision must be approved, changes_requested, rejected, or blocked.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if operator_decision != "approved" and not review_notes:
        raise Layer3WorkbenchError(
            "review_notes_required",
            "review_notes are required for changes_requested, rejected, or blocked result-review decisions.",
            status="invalid",
            blocked_fields=["review_notes"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "execution_result_review_not_available",
            "Execution result-review requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )

    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "output_metadata_required",
            "Execution result-review requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "execution_result_review_inconsistent",
            "Execution result-review could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )

    analysis_run_id = str(status_body.get("analysis_run_id") or "").strip() or None
    reviewed_items, unresolved_trace_count = _normalize_result_review_items(
        items=payload.get("reviewed_output_items"),
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id=analysis_run_id,
        output_metadata_summary=output_metadata_summary,
    )
    if operator_decision == "approved" and unresolved_trace_count:
        raise Layer3WorkbenchError(
            "execution_result_review_trace_unresolved",
            "Approved result-review decisions require resolved trace references for every reviewed output item.",
            status="blocked",
            http_status=409,
            blocked_fields=["reviewed_output_items"],
        )

    trace_summary = _result_review_trace_summary(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id=analysis_run_id,
        output_metadata_summary=output_metadata_summary,
        reviewed_items=reviewed_items,
        unresolved_trace_count=unresolved_trace_count,
    )
    review_record_ref = _stable_id(
        "l3-result-review",
        {
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "preview_id": preview_id,
            "preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "operator_decision": operator_decision,
            "client_request_id": request_id,
            "review_notes": review_notes,
            "reviewed_output_items": reviewed_items,
        },
    )

    existing_review = _execution_result_review_from_pass_run(pass_run)
    if existing_review is not None:
        if (
            existing_review.get("client_request_id") == request_id
            and existing_review.get("review_record_ref") == review_record_ref
        ):
            return _execution_result_review_response(
                request_id=request_id,
                status="already_recorded",
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                preview_id=preview_id,
                preview_hash=preview_hash,
                pass_run=pass_run,
                analysis_run_id=analysis_run_id,
                review_state=existing_review,
            )
        raise Layer3WorkbenchError(
            "execution_result_review_already_recorded",
            "Selected pass run already has a result-review decision.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )

    review_state = {
        "schema_id": EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
        "client_request_id": request_id,
        "review_record_ref": review_record_ref,
        "review_state": EXECUTION_RESULT_REVIEW_STATE_BY_DECISION[operator_decision],
        "operator_decision": operator_decision,
        "review_notes": review_notes or None,
        "reviewed_output_items": reviewed_items,
        "trace_summary": trace_summary,
        "unresolved_trace_count": unresolved_trace_count,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "analysis_run_id": analysis_run_id,
        "recorded_at": _utcnow_iso(),
        "package_review_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
    }
    pass_run.summary_json = {
        **_json_clone(pass_run.summary_json or {}),
        "execution_result_review": review_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "execution_result_review": {
            "schema_id": EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
            "review_record_ref": review_record_ref,
            "review_state": review_state["review_state"],
            "operator_decision": operator_decision,
            "pass_run_id": pass_run_id,
            "analysis_plan_id": analysis_plan_id,
            "analysis_run_id": analysis_run_id,
            "unresolved_trace_count": unresolved_trace_count,
            "package_review_enabled": False,
            "handoff_enabled": False,
            "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _execution_result_review_response(
        request_id=request_id,
        status="recorded",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_run=pass_run,
        analysis_run_id=analysis_run_id,
        review_state=review_state,
    )


def _package_review_preview_summary(review_state: dict[str, Any] | None) -> dict[str, Any]:
    approved = bool(
        isinstance(review_state, dict)
        and review_state.get("review_state") == EXECUTION_RESULT_REVIEW_APPROVED_STATE
        and review_state.get("operator_decision") == "approved"
        and int(review_state.get("unresolved_trace_count") or 0) == 0
    )
    return {
        "schema_id": PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID,
        "available": approved,
        "state": None,
        "result_review_state": review_state.get("review_state") if isinstance(review_state, dict) else None,
        "result_review_record_ref": review_state.get("review_record_ref") if isinstance(review_state, dict) else None,
        "requires_preview_endpoint_validation": True,
        "package_review_preview_enabled": approved,
        "package_review_enabled": False,
        "handoff_enabled": False,
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS) if approved else [],
        "downstream_unavailable": list(PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE),
    }


def _package_owner_compatibility(
    *,
    session: L3Session,
    pass_run: L3PassRun,
    output_metadata_summary: dict[str, Any],
    review_state: dict[str, Any],
) -> dict[str, Any]:
    session_summary = session.summary_json or {}
    pass_summary = pass_run.summary_json or {}
    required_inputs = {
        "phase1a_loading_closure": isinstance(session_summary.get("phase1a_loading_closure"), dict),
        "pass_entry": isinstance(session_summary.get("pass_entry"), dict),
        "selected_pass_output_metadata": output_metadata_summary.get("readable") is True,
        "approved_result_review": review_state.get("review_state") == EXECUTION_RESULT_REVIEW_APPROVED_STATE,
    }
    missing_inputs = sorted(key for key, present in required_inputs.items() if not present)
    construction_compatible = not missing_inputs
    return {
        "schema_id": "layer3.package_owner_compatibility.v1",
        "owner_service": "layer3_package_entry.materialize_package_entry",
        "assessment_basis": [
            "existing_gate_d_package_owner_service_contract",
            "current_workbench_selected_pass_result_review_state",
            "read_only_selected_pass_output_metadata",
        ],
        "materialize_package_entry_callable": False,
        "preview_candidate_projection_compatible": True,
        "construction_compatible_with_current_workbench_state": construction_compatible,
        "missing_owner_service_inputs": missing_inputs,
        "selected_pass_status": pass_run.status,
        "source_preview_id": pass_summary.get("source_preview_id"),
        "source_preview_hash": pass_summary.get("source_preview_hash"),
        "status": (
            "construction_preconditions_satisfied_but_call_deferred"
            if construction_compatible
            else "construction_preconditions_missing"
        ),
        "reason": (
            "Current state can be assessed against the owner service, but this endpoint remains read-only."
            if construction_compatible
            else "Current workbench state lacks full Gate D package-entry inputs; candidate projection remains preview-only."
        ),
    }


def _package_review_candidate_projection() -> list[dict[str, Any]]:
    return [
        {
            "package_kind": package_kind,
            "preview_only": True,
            "package_commit_enabled": True,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "readiness_reason": "candidate family is eligible for bounded package construction commit",
        }
        for package_kind in PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS
    ]


def _package_review_preview_hash(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    preview_id: str,
    preview_hash: str,
    analysis_run_id: str | None,
    result_review_record_ref: str | None,
    output_metadata_summary: dict[str, Any],
) -> str:
    return _stable_id(
        "l3-package-preview",
        {
            "schema_id": "layer3.package_review_preview_hash.v1",
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "preview_id": preview_id,
            "preview_hash": preview_hash,
            "analysis_run_id": analysis_run_id,
            "result_review_record_ref": result_review_record_ref,
            "output_payload_ref": output_metadata_summary.get("output_payload_ref"),
            "artifact_refs": output_metadata_summary.get("artifact_refs") or [],
            "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        },
    )


def _package_construction_summary(
    db: Session,
    *,
    session_id: str,
    package_review_preview_state: dict[str, Any],
) -> dict[str, Any]:
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .one_or_none()
    )
    packages = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    if reconciliation is not None or packages:
        return {
            "schema_id": PACKAGE_CONSTRUCTION_COMMIT_STATE_SCHEMA_ID,
            "available": False,
            "state": PACKAGE_CONSTRUCTED_STATE if reconciliation is not None and len(packages) == 3 else PACKAGE_COMMIT_BLOCKED_STATE,
            "blocked_reason": None if reconciliation is not None and len(packages) == 3 else "partial_package_state",
            "reconciliation_record_id": reconciliation.reconciliation_record_id if reconciliation is not None else None,
            "output_package_ids": [package.output_package_id for package in packages],
            "package_kinds": [package.package_kind for package in packages],
            "package_commit_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "downstream_unavailable": list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE),
        }
    available = bool(package_review_preview_state.get("available"))
    return {
        "schema_id": PACKAGE_CONSTRUCTION_COMMIT_STATE_SCHEMA_ID,
        "available": available,
        "state": PACKAGE_COMMIT_READY_STATE if available else PACKAGE_COMMIT_UNAVAILABLE_STATE,
        "blocked_reason": None if available else "package_review_preview_not_available",
        "reconciliation_record_id": None,
        "output_package_ids": [],
        "package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS) if available else [],
        "package_commit_enabled": available,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE),
    }


def package_review_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    request_id = str(payload.get("client_request_id") or "").strip() or None
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_package_review_preview_fields",
            f"Package-review preview request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_review_preview_request"],
        )

    unknown = sorted(key for key in payload if key not in PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "package_review_preview_scope_not_admitted",
            f"Package-review preview request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_read_only_package_review_preview_request"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
    }
    if request_id:
        status_payload["client_request_id"] = request_id
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "package_review_preview_result_status_unavailable",
            "Package-review preview requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "package_review_preview_output_metadata_required",
            "Package-review preview requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).first()
    if session is None or pass_run is None:
        raise Layer3WorkbenchError(
            "package_review_preview_inconsistent",
            "Package-review preview could not reload the selected session or pass run.",
            status="conflict",
            http_status=409,
        )

    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "package_review_preview_requires_approved_result_review",
            "Package-review preview requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref and supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "package_review_preview_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    review_identity = {
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
    }
    mismatched_review_fields = [
        field
        for field, expected in review_identity.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "package_review_preview_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "package_review_preview_trace_unresolved",
            "Package-review preview requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    reconciliation_count = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .count()
    )
    package_count = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.session_id == session_id)
        .count()
    )
    if reconciliation_count or package_count:
        raise Layer3WorkbenchError(
            "package_review_preview_existing_package_state",
            (
                "Package-review preview is blocked because existing package or reconciliation rows "
                f"already exist for session '{session_id}'."
            ),
            status="conflict",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        )

    compatibility = _package_owner_compatibility(
        session=session,
        pass_run=pass_run,
        output_metadata_summary=output_metadata_summary,
        review_state=review_state,
    )
    package_review_preview_hash = _package_review_preview_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        analysis_run_id=str(status_body.get("analysis_run_id") or "") or None,
        result_review_record_ref=str(review_state.get("review_record_ref") or "") or None,
        output_metadata_summary=output_metadata_summary,
    )
    return {
        **_base_response(PACKAGE_REVIEW_PREVIEW_SCHEMA_ID, request_id=request_id, status="available"),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "package_review_preview_hash": package_review_preview_hash,
        "analysis_run_id": str(status_body.get("analysis_run_id") or "") or None,
        "result_status_available": True,
        "result_review_state": review_state.get("review_state"),
        "result_review_record_ref": review_state.get("review_record_ref"),
        "package_review_preview_enabled": True,
        "package_commit_enabled": True,
        "package_review_enabled": False,
        "candidate_package_kinds": _package_review_candidate_projection(),
        "package_owner_compatibility": compatibility,
        "blocked_reasons": [],
        "downstream_unavailable": list(PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE),
        "next_state": PACKAGE_REVIEW_PREVIEW_READY_STATE,
        "output_metadata_summary": output_metadata_summary,
        "trace_summary": review_state.get("trace_summary"),
        "unresolved_trace_count": int(review_state.get("unresolved_trace_count") or 0),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode="read_only_package_review_preview",
            downstream_unavailable=PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def package_construction_commit(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for package construction commit.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_package_construction_commit"],
        )
    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    pass_run_id = str(payload.get("pass_run_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    supplied_review_ref = str(payload.get("result_review_record_ref") or "").strip()
    supplied_package_preview_hash = str(payload.get("package_review_preview_hash") or "").strip()
    supplied_analysis_run_id = str(payload.get("analysis_run_id") or "").strip()

    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
            ("result_review_record_ref", supplied_review_ref),
            ("package_review_preview_hash", supplied_package_preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_package_construction_commit_fields",
            f"Package construction commit request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_construction_commit_request"],
        )

    unknown = sorted(key for key in payload if key not in PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise Layer3WorkbenchError(
            "package_construction_commit_scope_not_admitted",
            f"Package construction commit request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_package_construction_commit_request"],
        )

    expected_package_kinds = payload.get("expected_package_kinds")
    if expected_package_kinds is not None and expected_package_kinds != list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS):
        raise Layer3WorkbenchError(
            "package_construction_commit_kinds_mismatch",
            "Package construction commit admits exactly the canonical_internal, user_facing, and review_facing package kinds.",
            status="conflict",
            http_status=409,
            blocked_fields=["expected_package_kinds"],
        )

    status_payload = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "operator_view_mode": "status_only",
        "client_request_id": request_id,
    }
    if supplied_analysis_run_id:
        status_payload["analysis_run_id"] = supplied_analysis_run_id
    status_body = execution_result_status(db, status_payload)
    if status_body.get("status") != "available" or status_body.get("result_status_available") is not True:
        raise Layer3WorkbenchError(
            "package_construction_commit_result_status_unavailable",
            "Package construction commit requires available selected-pass result/status with readable output metadata.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["inspect_execution_result_status"],
        )
    output_metadata_summary = status_body.get("output_metadata_summary")
    if not isinstance(output_metadata_summary, dict) or output_metadata_summary.get("readable") is not True:
        raise Layer3WorkbenchError(
            "package_construction_commit_output_metadata_required",
            "Package construction commit requires readable selected-pass output metadata.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    analysis_plan = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.analysis_plan_id == analysis_plan_id,
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == "approved",
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .one_or_none()
    )
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    if analysis_plan is None:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Package construction commit must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )
    if pass_run is None or pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "pass_run_mismatch",
            "Package construction commit pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )
    review_state = _execution_result_review_from_pass_run(pass_run)
    if (
        review_state is None
        or review_state.get("review_state") != EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or review_state.get("operator_decision") != "approved"
    ):
        raise Layer3WorkbenchError(
            "package_construction_commit_requires_approved_result_review",
            "Package construction commit requires an approved selected-pass result-review record.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if supplied_review_ref != str(review_state.get("review_record_ref") or ""):
        raise Layer3WorkbenchError(
            "package_construction_commit_result_review_mismatch",
            "Supplied result_review_record_ref does not match the selected-pass approved result review.",
            status="conflict",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )
    mismatched_review_fields = [
        field
        for field, expected in {
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
        }.items()
        if str(review_state.get(field) or "") != str(expected)
    ]
    if mismatched_review_fields:
        raise Layer3WorkbenchError(
            "package_construction_commit_result_review_mismatch",
            "Stored result-review state does not match the supplied approved plan, pass, and preview identity.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched_review_fields,
        )
    if int(review_state.get("unresolved_trace_count") or 0) != 0:
        raise Layer3WorkbenchError(
            "package_construction_commit_trace_unresolved",
            "Package construction commit requires approved result-review state with no unresolved trace references.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
        )

    expected_package_preview_hash = _package_review_preview_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        analysis_run_id=str(status_body.get("analysis_run_id") or "") or None,
        result_review_record_ref=supplied_review_ref,
        output_metadata_summary=output_metadata_summary,
    )
    if supplied_package_preview_hash != expected_package_preview_hash:
        raise Layer3WorkbenchError(
            "package_review_preview_mismatch",
            "Package construction commit must reference the current server-recomputed package-review preview hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["package_review_preview_hash"],
            next_allowed_actions=["refresh_package_review_preview"],
        )

    try:
        result = materialize_workbench_package_commit(
            db,
            session=session,
            analysis_plan=analysis_plan,
            pass_run=pass_run,
            preview_id=preview_id,
            preview_hash=preview_hash,
            result_review_state=review_state,
            package_review_preview_hash=supplied_package_preview_hash,
            output_metadata_summary=output_metadata_summary,
            client_request_id=request_id,
        )
    except Layer3PackageEntryError as exc:
        raise Layer3WorkbenchError(
            "package_construction_commit_blocked",
            str(exc),
            status="conflict",
            http_status=409,
            next_allowed_actions=["inspect_existing_package_state"],
        ) from exc
    db.commit()

    packages = list(result.output_packages)
    return {
        **_base_response(
            PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID,
            request_id=request_id,
            status="already_committed" if result.replayed else "committed",
        ),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": str(status_body.get("analysis_run_id") or "") or None,
        "result_review_record_ref": supplied_review_ref,
        "package_review_preview_hash": supplied_package_preview_hash,
        "reconciliation_record_id": result.reconciliation_record.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_ref": package.payload_ref,
                "payload_hash": package.payload_hash,
            }
            for package in packages
        ],
        "package_kinds": [package.package_kind for package in packages],
        "payload_refs": [package.payload_ref for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE),
        "next_state": PACKAGE_CONSTRUCTED_STATE,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode="durable_package_construction",
            downstream_unavailable=PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def session_summary(db: Session, session_id: str) -> dict[str, Any]:
    session = _load_session(db, session_id)
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session_id)
        .order_by(L3SelectionManifest.committed_at.desc())
        .first()
    )
    if manifest is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' has no selection manifest.", http_status=404)

    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_unit_count = db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).count()
    analysis_group_count = db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    gate_b_counts = _gate_b_summary_from_session(session)
    typing_committed = typing_record_count > 0
    plan_preview_readiness = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
    plan_approval_readiness = _plan_approval_summary(db, session_id=session_id)
    plan_revision_readiness = _plan_revision_summary(db, session_id=session_id)
    execution_selection_readiness = _execution_selection_summary(db, session_id=session_id)
    analysis_execution_start_state = (session.summary_json or {}).get("analysis_execution_start")
    execution_result_review_state = (session.summary_json or {}).get("execution_result_review")
    if not isinstance(analysis_execution_start_state, dict):
        analysis_execution_start_state = {
            "schema_id": ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
            "available": bool(
                execution_selection_readiness["selected"]
                and not execution_selection_readiness["execution_started"]
            ),
            "state": None,
            "downstream_unavailable": list(ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE),
        }
    if not isinstance(execution_result_review_state, dict):
        execution_result_review_state = {
            "schema_id": EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
            "available": bool(analysis_execution_start_state.get("state") == EXECUTION_PASS_COMPLETED_STATE),
            "state": None,
            "package_review_enabled": False,
            "handoff_enabled": False,
            "downstream_unavailable": list(EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE),
        }
    package_review_preview_state = _package_review_preview_summary(execution_result_review_state)
    package_construction_state = _package_construction_summary(
        db,
        session_id=session_id,
        package_review_preview_state=package_review_preview_state,
    )
    selection_active = bool(execution_selection_readiness["selected"])
    package_active = bool(
        package_review_preview_state.get("available")
        or package_construction_state.get("state") == PACKAGE_CONSTRUCTED_STATE
    )
    current_gate = "package" if package_active else ("execution" if selection_active else ("plan" if typing_committed else "gate_c"))
    downstream_unavailable = (
        PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE
        if package_active
        else (
        EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE
        if selection_active
        else (PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE if typing_committed else DOWNSTREAM_UNAVAILABLE)
        )
    )

    return {
        **_base_response("layer3.workbench_session_summary.v1"),
        "session_id": session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "current_gate": current_gate,
        "gate_b_summary": gate_b_counts,
        "gate_c_summary": {
            "typing_committed": typing_committed,
            "typing_record_count": typing_record_count,
            "analysis_unit_count": analysis_unit_count,
            "analysis_group_count": analysis_group_count,
            "analysis_set_count": analysis_set_count,
        },
        "plan_preview": plan_preview_readiness,
        "plan_approval": plan_approval_readiness,
        "plan_revision": plan_revision_readiness,
        "execution_selection": execution_selection_readiness,
        "analysis_execution_start": analysis_execution_start_state,
        "execution_result_review": execution_result_review_state,
        "package_review_preview": package_review_preview_state,
        "package_construction": package_construction_state,
        "downstream_unavailable": list(downstream_unavailable),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate=current_gate,
            persistence_mode="durable_layer3_control",
            counts=gate_b_counts,
            typing_status="committed" if typing_committed else "previewed",
            downstream_unavailable=downstream_unavailable,
        ),
    }
