from __future__ import annotations

from typing import Any, Mapping


STATE_MODEL_SCHEMA_ID = "layer3.workbench_state_model.v1"


def _state(state_names: Mapping[str, str], name: str) -> str:
    try:
        return state_names[name]
    except KeyError as exc:
        raise KeyError(f"missing Layer 3 state model state name: {name}") from exc


def build_workbench_state_model(*, state_names: Mapping[str, str]) -> dict[str, Any]:
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
                "state": _state(state_names, "EXECUTION_SELECTION_STATE"),
                "authority_source": "server_created_l3_pass_run_shell",
                "allowed_next_actions": ["analysis_execution_start"],
                "forbidden_downstream_actions": ["results", "package", "handoff"],
            },
            {
                "state": _state(state_names, "EXECUTION_PASS_RUNNING_STATE"),
                "authority_source": "server_locked_l3_pass_run_transition",
                "allowed_next_actions": ["complete_or_fail_same_pass"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": _state(state_names, "EXECUTION_PASS_COMPLETED_STATE"),
                "authority_source": "selected_l3_pass_run_and_wrapped_analysis_run",
                "allowed_next_actions": ["execution_result_status"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": _state(state_names, "EXECUTION_PASS_FAILED_STATE"),
                "authority_source": "selected_l3_pass_run_failure_metadata",
                "allowed_next_actions": ["execution_result_status"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_STATUS_AVAILABLE_STATE"),
                "authority_source": "terminal_selected_l3_pass_run_and_read_only_output_metadata",
                "allowed_next_actions": ["execution_result_status", "execution_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_REVIEW_READY_STATE"),
                "authority_source": "terminal_selected_l3_pass_run_with_readable_output_metadata",
                "allowed_next_actions": ["execution_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_REVIEW_APPROVED_STATE"),
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_REVIEW_CHANGES_REQUESTED_STATE"),
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_REVIEW_REJECTED_STATE"),
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_REVIEW_BLOCKED_STATE"),
                "authority_source": "bounded_operator_result_review_on_selected_l3_pass_run",
                "allowed_next_actions": ["inspect_result_review"],
                "forbidden_downstream_actions": ["package", "handoff", "source_expansion", "rerun"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_PREVIEW_UNAVAILABLE_STATE"),
                "authority_source": "missing_session_plan_pass_result_status_or_result_review_authority",
                "allowed_next_actions": ["inspect_upstream_state"],
                "forbidden_downstream_actions": ["package_preview", "package_construction", "handoff"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_PREVIEW_BLOCKED_STATE"),
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
                "state": _state(state_names, "PACKAGE_REVIEW_PREVIEW_READY_STATE"),
                "authority_source": "approved_selected_pass_result_review_and_read_only_owner_service_assessment",
                "allowed_next_actions": ["inspect_package_candidates", "package_construction_commit"],
                "forbidden_downstream_actions": [
                    "package_review_submit",
                    "handoff",
                    "export",
                ],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_PREVIEW_INSPECTED_STATE"),
                "authority_source": "read_only_package_review_preview_response",
                "allowed_next_actions": ["inspect_package_candidates", "package_construction_commit"],
                "forbidden_downstream_actions": [
                    "package_review_submit",
                    "handoff",
                    "export",
                ],
            },
            {
                "state": _state(state_names, "PACKAGE_COMMIT_UNAVAILABLE_STATE"),
                "authority_source": "missing_package_review_preview_or_existing_incompatible_package_state",
                "allowed_next_actions": ["inspect_upstream_state"],
                "forbidden_downstream_actions": ["package_construction", "package_review_submit", "handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_COMMIT_BLOCKED_STATE"),
                "authority_source": "server_fail_closed_package_construction_commit_check",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": ["package_construction", "package_review_submit", "handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_COMMIT_READY_STATE"),
                "authority_source": "approved_result_review_and_matching_package_review_preview_hash",
                "allowed_next_actions": ["package_construction_commit"],
                "forbidden_downstream_actions": ["package_review_submit", "handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_CONSTRUCTED_STATE"),
                "authority_source": "l3_reconciliation_record_and_three_l3_output_package_rows",
                "allowed_next_actions": [
                    "inspect_package_payloads",
                    "package_review_submit",
                    "package_supersession_preview",
                    "record_replacement_package_set_authority",
                    "package_supersession_commit",
                    "replacement_package_namespace",
                ],
                "forbidden_downstream_actions": ["handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_SUBMIT_UNAVAILABLE_STATE"),
                "authority_source": "missing_package_construction_state",
                "allowed_next_actions": ["inspect_package_construction_state"],
                "forbidden_downstream_actions": ["package_review_submit", "handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_SUBMIT_BLOCKED_STATE"),
                "authority_source": "server_fail_closed_package_review_submit_check",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": ["handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_SUBMIT_READY_STATE"),
                "authority_source": "l3_reconciliation_record_and_three_verified_l3_output_package_rows",
                "allowed_next_actions": ["package_review_submit"],
                "forbidden_downstream_actions": ["handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_APPROVED_STATE"),
                "authority_source": "bounded_operator_package_review_submit_state",
                "allowed_next_actions": [
                    "inspect_package_review_decision",
                    "handoff_export_prepare",
                    "package_supersession_preview",
                    "record_replacement_package_set_authority",
                    "package_supersession_commit",
                    "replacement_package_namespace",
                ],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "downstream_dispatch"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_CHANGES_REQUESTED_STATE"),
                "authority_source": "bounded_operator_package_review_submit_state",
                "allowed_next_actions": ["inspect_package_review_decision"],
                "forbidden_downstream_actions": ["handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_REJECTED_STATE"),
                "authority_source": "bounded_operator_package_review_submit_state",
                "allowed_next_actions": ["inspect_package_review_decision"],
                "forbidden_downstream_actions": ["handoff", "export"],
            },
            {
                "state": _state(state_names, "PACKAGE_REVIEW_BLOCKED_STATE"),
                "authority_source": "bounded_operator_package_review_submit_state",
                "allowed_next_actions": ["inspect_package_review_decision"],
                "forbidden_downstream_actions": ["handoff", "export"],
            },
            {
                "state": _state(state_names, "HANDOFF_EXPORT_UNAVAILABLE_STATE"),
                "authority_source": "missing_approved_package_review_submit_state_or_upstream_authority",
                "allowed_next_actions": ["inspect_upstream_state"],
                "forbidden_downstream_actions": ["handoff_export_prepare", "aps_handoff", "external_export"],
            },
            {
                "state": _state(state_names, "HANDOFF_EXPORT_READY_STATE"),
                "authority_source": "server_validated_approved_package_review_submit_state",
                "allowed_next_actions": ["handoff_export_prepare"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "downstream_dispatch"],
            },
            {
                "state": _state(state_names, "HANDOFF_EXPORT_PREPARED_STATE"),
                "authority_source": "bounded_operator_internal_export_envelope_preparation",
                "allowed_next_actions": ["inspect_internal_envelope", "aps_handoff_dispatch"],
                "forbidden_downstream_actions": ["external_export", "download", "connector_dispatch", "non_aps_dispatch"],
            },
            {
                "state": _state(state_names, "HANDOFF_EXPORT_HELD_STATE"),
                "authority_source": "bounded_operator_handoff_export_preparation_decision",
                "allowed_next_actions": ["inspect_decision"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "downstream_dispatch"],
            },
            {
                "state": _state(state_names, "HANDOFF_EXPORT_DECLINED_STATE"),
                "authority_source": "bounded_operator_handoff_export_preparation_decision",
                "allowed_next_actions": ["inspect_decision"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "downstream_dispatch", "package_rewrite"],
            },
            {
                "state": _state(state_names, "HANDOFF_EXPORT_BLOCKED_STATE"),
                "authority_source": "stale_authority_partial_package_set_hash_mismatch_or_operator_block",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "downstream_dispatch", "package_rewrite"],
            },
            {
                "state": _state(state_names, "APS_HANDOFF_UNAVAILABLE_STATE"),
                "authority_source": "missing_prepared_internal_handoff_export_envelope_or_upstream_authority",
                "allowed_next_actions": ["inspect_handoff_export_prepare_state"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "download", "connector_dispatch"],
            },
            {
                "state": _state(state_names, "APS_HANDOFF_READY_STATE"),
                "authority_source": "server_validated_handoff_export_prepared_envelope_and_package_authority",
                "allowed_next_actions": ["aps_handoff_dispatch"],
                "forbidden_downstream_actions": ["external_export", "download", "connector_dispatch", "non_aps_dispatch"],
            },
            {
                "state": _state(state_names, "APS_HANDOFF_DISPATCHED_STATE"),
                "authority_source": "existing_aps_evidence_bundle_handoff_owner_service_row_and_artifact",
                "allowed_next_actions": ["inspect_aps_handoff", "external_export_download_prepare"],
                "forbidden_downstream_actions": [
                    "browser_download",
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "APS_HANDOFF_BLOCKED_STATE"),
                "authority_source": "missing_aps_provenance_or_owner_service_validation_failure",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "download", "connector_dispatch", "non_aps_dispatch"],
            },
            {
                "state": _state(state_names, "APS_HANDOFF_CONFLICT_STATE"),
                "authority_source": "existing_or_conflicting_aps_handoff_dispatch_state",
                "allowed_next_actions": ["inspect_existing_aps_handoff_state"],
                "forbidden_downstream_actions": ["aps_handoff", "external_export", "download", "connector_dispatch", "non_aps_dispatch"],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE"),
                "authority_source": "missing_recorded_aps_handoff_dispatch_or_validated_aps_bundle_source",
                "allowed_next_actions": ["inspect_aps_handoff_dispatch_state"],
                "forbidden_downstream_actions": [
                    "external_export_download_prepare",
                    "browser_download",
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_READY_STATE"),
                "authority_source": "server_validated_aps_handoff_dispatch_state_and_existing_bundle_artifact",
                "allowed_next_actions": ["external_export_download_prepare"],
                "forbidden_downstream_actions": [
                    "browser_download",
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE"),
                "authority_source": "reference_only_external_export_download_readiness_descriptor",
                "allowed_next_actions": [
                    "inspect_external_export_download_readiness",
                    "external_export_download_deliver",
                    "internal_connector_dispatch_record",
                ],
                "forbidden_downstream_actions": [
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "CONNECTOR_DISPATCH_RECORDED_STATE"),
                "authority_source": "existing_l3_reconciliation_record_connector_dispatch_record",
                "allowed_next_actions": ["inspect_internal_connector_dispatch_record"],
                "forbidden_downstream_actions": [
                    "external_connector_invocation",
                    "destination_write",
                    "connector_run_creation",
                    "provider_public_url",
                    "package_mutation_reconstruction",
                    "source_upload_expansion",
                    "broad_qualitative_hybrid_rag_execution",
                    "full_mockup_activation",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE"),
                "authority_source": "missing_or_invalid_aps_bundle_artifact_or_stale_authority",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": [
                    "external_export_download_prepare",
                    "browser_download",
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_CONFLICT_STATE"),
                "authority_source": "existing_or_conflicting_external_export_download_prepare_state",
                "allowed_next_actions": ["inspect_existing_external_export_download_readiness"],
                "forbidden_downstream_actions": [
                    "browser_download",
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UNAVAILABLE_STATE"),
                "authority_source": "missing_recorded_external_export_download_readiness_or_validated_artifact_source",
                "allowed_next_actions": ["inspect_external_export_download_readiness"],
                "forbidden_downstream_actions": [
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_READY_STATE"),
                "authority_source": "server_validated_readiness_descriptor_and_existing_bundle_artifact",
                "allowed_next_actions": ["external_export_download_deliver"],
                "forbidden_downstream_actions": [
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE"),
                "authority_source": "same_origin_stream_of_existing_validated_aps_evidence_bundle",
                "allowed_next_actions": ["inspect_external_export_download_readiness"],
                "forbidden_downstream_actions": [
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_BLOCKED_STATE"),
                "authority_source": "missing_or_invalid_readiness_descriptor_or_aps_bundle_artifact",
                "allowed_next_actions": ["inspect_block_reasons"],
                "forbidden_downstream_actions": [
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONFLICT_STATE"),
                "authority_source": "request_conflicts_with_recorded_external_export_download_readiness",
                "allowed_next_actions": ["inspect_existing_external_export_download_readiness"],
                "forbidden_downstream_actions": [
                    "download_url",
                    "connector_dispatch",
                    "destination_selection",
                    "generic_downstream_dispatch",
                ],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_STATUS_BLOCKED_STATE"),
                "authority_source": "failed_result_status_authority_checks",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": _state(state_names, "EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE"),
                "authority_source": "terminal_selected_l3_pass_run_without_readable_output_metadata",
                "allowed_next_actions": ["execution_result_status"],
                "forbidden_downstream_actions": ["result_review", "package", "handoff", "source_expansion"],
            },
            {
                "state": "plan_rejected",
                "authority_source": "l3_session_summary_plan_revision_control",
                "allowed_next_actions": ["plan_revision_recover"],
                "forbidden_downstream_actions": ["approval", "execution", "results", "package"],
            },
            {
                "state": "plan_revision_requested",
                "authority_source": "l3_session_summary_plan_revision_control",
                "allowed_next_actions": ["plan_revision_recover"],
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
