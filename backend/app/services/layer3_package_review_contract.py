from __future__ import annotations

from typing import Any, Mapping


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
PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS = frozenset(
    {
        "handoff",
        "export",
        "aps_handoff",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
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
    }
)
PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "operator_decision",
        "client_request_id",
        "decision_notes",
        "analysis_run_id",
        "expected_package_kinds",
    }
)


def package_review_preview_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def package_construction_commit_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(
        key for key in payload if key not in PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS if key in payload
    )
    return sorted(set(unknown) | set(forbidden))


def package_review_submit_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))
