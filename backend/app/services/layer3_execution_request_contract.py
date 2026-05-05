from __future__ import annotations

from typing import Any, Mapping


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


def analysis_execution_start_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in ANALYSIS_EXECUTION_START_ALLOWED_FIELDS)
    forbidden = sorted(key for key in ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def execution_result_status_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in EXECUTION_RESULT_STATUS_ALLOWED_FIELDS)
    forbidden = sorted(key for key in EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def execution_result_review_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS)
    forbidden = sorted(key for key in EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))
