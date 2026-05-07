from __future__ import annotations

from typing import Any, Mapping


HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS = frozenset(
    {
        "aps_handoff",
        "dispatch",
        "send",
        "external_export",
        "external_target",
        "download",
        "connector_run_id",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
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
    }
)
HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "package_review_submit_schema_id",
        "handoff_target",
        "export_mode",
        "operator_decision",
        "client_request_id",
        "decision_notes",
        "analysis_run_id",
        "expected_package_kinds",
    }
)
APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS = frozenset(
    {
        "external_export",
        "external_target",
        "download",
        "download_url",
        "destination",
        "destination_selector",
        "connector_run_id",
        "connector_dispatch",
        "dispatch",
        "send",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
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
    }
)
APS_HANDOFF_DISPATCH_ALLOWED_FIELDS = frozenset(
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
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "operator_decision",
        "client_request_id",
        "decision_notes",
        "analysis_run_id",
    }
)


def handoff_export_prepare_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS)
    forbidden = sorted(key for key in HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def aps_handoff_dispatch_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in APS_HANDOFF_DISPATCH_ALLOWED_FIELDS)
    forbidden = sorted(key for key in APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))
