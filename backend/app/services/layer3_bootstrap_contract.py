"""Shared Layer 3 workbench bootstrap contract builder."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.core.config import settings
from app.services.layer3_candidate_b_default_readiness import ELIGIBLE_CORPUS_SCOPE
from app.services.layer3_readiness_contract import EXECUTION_READINESS_SCHEMA_ID
from app.services.layer3_response_contract import base_response

BOOTSTRAP_SCHEMA_ID = "layer3.workbench_bootstrap.v1"

BOOTSTRAP_FEATURE_FLAGS: Mapping[str, bool] = {
    "plan_preview": True,
    "plan_approval": True,
    "execution_selection": True,
    "analysis_execution_start": True,
    "execution_result_status": True,
    "execution_result_review": True,
    "package_review_preview": True,
    "package_construction_commit": True,
    "package_review_submit": True,
    "handoff_export_prepare": True,
    "aps_handoff_dispatch": True,
    "external_export_download_prepare": True,
    "external_export_download_deliver": True,
    "internal_connector_dispatch_record": True,
    "internal_fake_local_destination_receipt": True,
    "package_supersession_preview": True,
    "replacement_package_set_authority": True,
    "package_supersession_commit": True,
    "replacement_package_artifact_manifest": True,
    "replacement_package_namespace": True,
    "plan_revision_recovery": True,
    "approved_plan_cancel": True,
    "candidate_b_bundle_material_bridge": True,
    "candidate_b_runtime_material_bridge": True,
    "candidate_b_default_promotion_operator_status": True,
    "candidate_b_default_promotion_closure_evidence": True,
    "candidate_b_default_promotion_readiness_audit": True,
    "candidate_b_broader_eligible_corpus_scope_readiness_audit": True,
    "candidate_b_broader_eligible_corpus_default_scope_runtime": True,
    "candidate_b_broader_eligible_corpus_default_scope_selector_use": True,
    "candidate_b_broader_eligible_corpus_default_scope_selector_use_status": True,
    "candidate_b_broader_eligible_corpus_default_scope_selector_activation": True,
    "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption": True,
    "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use": True,
    "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status": True,
    "candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial": True,
    "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness": True,
    "candidate_b_broader_eligible_corpus_default_scope_default_promotion": True,
    "candidate_b_default_promotion_final_proof": True,
    "candidate_b_default_promotion_final_proof_status": True,
    "candidate_b_full_corpus_operator_workflow_status": True,
    "candidate_b_full_corpus_operator_workflow_run": True,
    "candidate_b_full_corpus_operator_workflow_history": True,
    "candidate_b_full_corpus_operator_workflow_lifecycle_expire": True,
    "candidate_b_full_corpus_operator_workflow_queue_state": True,
    "candidate_b_full_corpus_operator_workflow_execution_boundary": True,
    "candidate_b_full_corpus_operator_workflow_process_execution": True,
    "candidate_b_full_corpus_operator_workflow_process_completion_result": True,
    "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof": True,
    "candidate_b_full_corpus_operator_workflow_completion_monitor": True,
    "candidate_b_full_corpus_operator_repeatability_checkpoint": True,
    "candidate_b_full_corpus_repeatability_rerun_trial": True,
    "candidate_b_full_corpus_repeatability_acceptance_closeout": True,
    "candidate_b_full_corpus_repeatability_acceptance_closeout_status": True,
    "candidate_b_full_corpus_operator_workflow_scheduler_lease": True,
    "candidate_b_full_corpus_operator_workflow_worker_attempt": True,
    "candidate_b_full_corpus_operator_workflow_progress_checkpoint": True,
    "candidate_b_full_corpus_operator_workflow_completion_failure": True,
    "candidate_b_full_corpus_operator_workflow_retry_policy": True,
    "candidate_b_full_corpus_operator_workflow_retry_queue_state": True,
    "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease": True,
    "candidate_b_full_corpus_operator_workflow_retry_worker_attempt": True,
    "candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint": True,
    "candidate_b_full_corpus_operator_workflow_retry_completion_failure": True,
    "sec_edgar_text_table_downstream_operator_status": True,
    "sec_edgar_text_table_live_source_artifact_downstream_proof": True,
    "sec_edgar_text_table_live_source_artifact_downstream_operator_status": True,
    "sec_edgar_html_inline_xbrl_downstream_operator_status": True,
    "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status": True,
    "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial": True,
    "sec_edgar_text_table_downstream_operator_repeatability_trial": True,
    "source_directory_ingestion_scan": True,
    "source_directory_ingestion_status": True,
    "source_directory_material_preview": True,
    "source_directory_vector_retrieval": True,
    "source_directory_hybrid_context_packet": True,
    "source_directory_hybrid_context_packet_qualitative_analysis": True,
    "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview": True,
    "source_directory_hybrid_context_packet_qualitative_analysis_status": True,
    "source_directory_hybrid_context_packet_qualitative_analysis_package_commit": True,
    "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit": True,
    "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare": True,
    "source_directory_qualitative_hybrid_analysis": True,
    "source_directory_qualitative_hybrid_analysis_status": True,
    "source_directory_package_commit": True,
    "source_directory_package_review_submit": True,
    "source_directory_package_supersession_preview": True,
    "source_directory_handoff_export_prepare": True,
    "source_directory_external_export_download_prepare": True,
    "source_directory_external_export_download_deliver": True,
    "source_directory_external_export_download_delivery_status": True,
    "analysis_execution": False,
    "single_aps_doc_qualitative_execution": True,
    "broad_qualitative_execution": False,
    "hybrid_execution": False,
    "rag_vector_retrieval": False,
    "package_review": False,
    "handoff": False,
    "external_export": False,
    "dispatch": False,
    "runtime_snapshot_db_writes": False,
    "schema_widening": False,
    "typing_override_enabled": False,
}


def build_bootstrap_contract(
    *,
    route: str,
    api_root: str,
    supported_source_classes: Sequence[str],
    unsupported_source_classes: Sequence[str],
    gate_labels: Sequence[str],
    active_gate_labels: Sequence[str],
    unavailable_gate_labels: Sequence[str],
    state_action_contract: Mapping[str, Any],
    authority_matrix_contract: Mapping[str, Any],
    mockup_activation_readiness: Mapping[str, Any],
    authority_rail: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **base_response(BOOTSTRAP_SCHEMA_ID),
        "route": route,
        "api_root": api_root,
        "supported_source_classes": list(supported_source_classes),
        "preview_only_source_classes": [],
        "unsupported_source_classes": list(unsupported_source_classes),
        "gate_labels": list(gate_labels),
        "active_gate_labels": list(active_gate_labels),
        "unavailable_gate_labels": list(unavailable_gate_labels),
        "state_action_contract": dict(state_action_contract),
        "authority_matrix_contract": dict(authority_matrix_contract),
        "mockup_activation_readiness": dict(mockup_activation_readiness),
        "features": dict(BOOTSTRAP_FEATURE_FLAGS),
        # Top-level (not inside the static `features` constant) because this is a
        # runtime settings-derived flag read from `settings`; BOOTSTRAP_FEATURE_FLAGS
        # is a module-level constant of static compile-time flags and cannot read settings.
        "analysis_product_package_inventory_enabled": bool(settings.layer3_analysis_product_package_inventory_enabled),
        "layer3_public_dataset_analysis_enabled": bool(settings.layer3_public_dataset_analysis_enabled),
        "layer3_public_connector_value_reveal_enabled": bool(settings.layer3_public_connector_value_reveal_enabled),
        "layer3_operator_method_selection_enabled": bool(settings.layer3_operator_method_selection_enabled),
        "execution_readiness": {
            "schema_id": EXECUTION_READINESS_SCHEMA_ID,
            "execution_admitted": False,
            "execution_enabled": False,
            "execution_selection_admitted": True,
            "execution_selection_endpoint": f"{api_root}/execution/select",
            "analysis_execution_admitted": False,
            "analysis_execution_start_admitted": True,
            "analysis_execution_start_endpoint": f"{api_root}/execution/start",
            "execution_result_status_admitted": True,
            "execution_result_status_endpoint": f"{api_root}/execution/result/status",
            "execution_result_review_admitted": True,
            "execution_result_review_endpoint": f"{api_root}/execution/result/review",
            "package_review_preview_admitted": True,
            "package_review_preview_endpoint": f"{api_root}/package/review/preview",
            "package_construction_commit_admitted": True,
            "package_construction_commit_endpoint": f"{api_root}/package/review/commit",
            "package_review_submit_admitted": True,
            "package_review_submit_endpoint": f"{api_root}/package/review/submit",
            "handoff_export_prepare_admitted": True,
            "handoff_export_prepare_endpoint": f"{api_root}/handoff/export/prepare",
            "aps_handoff_dispatch_admitted": True,
            "aps_handoff_dispatch_endpoint": f"{api_root}/handoff/aps/dispatch",
            "external_export_download_prepare_admitted": True,
            "external_export_download_prepare_endpoint": f"{api_root}/handoff/export/download/prepare",
            "external_export_download_deliver_admitted": True,
            "external_export_download_deliver_endpoint": f"{api_root}/handoff/export/download/deliver",
            "internal_connector_dispatch_record_admitted": True,
            "internal_connector_dispatch_record_endpoint": f"{api_root}/handoff/connector/record",
            "internal_fake_local_destination_receipt_admitted": True,
            "internal_fake_local_destination_receipt_endpoint": (
                f"{api_root}/handoff/connector/local-destination/receipt"
            ),
            "package_supersession_preview_admitted": True,
            "package_supersession_preview_endpoint": f"{api_root}/package/mutation/preview",
            "replacement_package_artifact_materialization_admitted": True,
            "replacement_package_artifact_materialization_endpoint": (
                f"{api_root}/package/replacement-artifact/materialize"
            ),
            "replacement_package_set_authority_admitted": True,
            "replacement_package_set_authority_endpoint": f"{api_root}/package/replacement-set/record",
            "package_supersession_commit_admitted": True,
            "package_supersession_commit_endpoint": f"{api_root}/package/supersession/commit",
            "replacement_package_artifact_manifest_admitted": True,
            "replacement_package_artifact_manifest_endpoint": (
                f"{api_root}/package/replacement-artifact/manifest/record"
            ),
            "replacement_package_namespace_admitted": True,
            "replacement_package_namespace_endpoint": f"{api_root}/package/replacement-namespace/record",
            "plan_revision_recovery_admitted": True,
            "plan_revision_recovery_endpoint": f"{api_root}/plan/revision/recover",
            "approved_plan_cancel_admitted": True,
            "approved_plan_cancel_endpoint": f"{api_root}/plan/approved/cancel",
            "candidate_b_bundle_material_bridge_admitted": True,
            "candidate_b_bundle_material_bridge_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/bundle/material-bridge"
            ),
            "candidate_b_runtime_material_bridge_admitted": True,
            "candidate_b_runtime_material_bridge_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/runtime/material-bridge"
            ),
            "candidate_b_runtime_bridge_source_scan_admitted": True,
            "candidate_b_runtime_bridge_source_scan_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/runtime/material-bridge/source-scan"
            ),
            "candidate_b_artifact_family_status_admitted": True,
            "candidate_b_artifact_family_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/artifact-family/status"
            ),
            "candidate_b_visual_lane_status_admitted": True,
            "candidate_b_visual_lane_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/visual-lane/status"
            ),
            "candidate_b_bundle_downstream_proof_admitted": True,
            "candidate_b_bundle_downstream_proof_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/bundle/downstream-proof"
            ),
            "candidate_b_runtime_downstream_proof_admitted": True,
            "candidate_b_runtime_downstream_proof_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/runtime/downstream-proof"
            ),
            "candidate_b_default_promotion_operator_status_admitted": True,
            "candidate_b_default_promotion_operator_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/default-promotion/operator-status"
            ),
            "sec_edgar_text_table_downstream_operator_status_admitted": True,
            "sec_edgar_text_table_downstream_operator_status_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/downstream-proof/status"
            ),
            "sec_edgar_text_table_source_acquisition_authority_admitted": True,
            "sec_edgar_text_table_source_acquisition_authority_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/source-acquisition/authority"
            ),
            "sec_edgar_text_table_live_source_artifact_acquisition_admitted": True,
            "sec_edgar_text_table_live_source_artifact_acquisition_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/live-source-artifact/acquire"
            ),
            "sec_edgar_text_table_live_source_artifact_acquisition_status_admitted": True,
            "sec_edgar_text_table_live_source_artifact_acquisition_status_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/live-source-artifact/status/"
                "{live_source_artifact_receipt_id}"
            ),
            "sec_edgar_text_table_live_source_artifact_material_authority_bridge_admitted": True,
            "sec_edgar_text_table_live_source_artifact_material_authority_bridge_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/live-source-artifact/material-authority/bridge"
            ),
            "sec_edgar_text_table_live_source_artifact_downstream_proof_admitted": True,
            "sec_edgar_text_table_live_source_artifact_downstream_proof_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/live-source-artifact/downstream-proof"
            ),
            "sec_edgar_text_table_live_source_artifact_downstream_operator_status_admitted": True,
            "sec_edgar_text_table_live_source_artifact_downstream_operator_status_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/live-source-artifact/downstream-proof/status"
            ),
            "sec_edgar_html_inline_xbrl_downstream_operator_status_admitted": True,
            "sec_edgar_html_inline_xbrl_downstream_operator_status_endpoint": (
                f"{api_root}/source/sec-edgar/html-inline-xbrl/downstream-proof/status"
            ),
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_admitted": True,
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_endpoint": (
                f"{api_root}/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status"
            ),
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_admitted": True,
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_endpoint": (
                f"{api_root}/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/operator-repeatability/trial"
            ),
            "sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial_admitted": True,
            "sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/live-source-artifact/downstream/operator-repeatability/trial"
            ),
            "sec_edgar_text_table_downstream_operator_repeatability_trial_admitted": True,
            "sec_edgar_text_table_downstream_operator_repeatability_trial_endpoint": (
                f"{api_root}/source/sec-edgar/text-table/downstream/operator-repeatability/trial"
            ),
            "candidate_b_default_promotion_closure_evidence_admitted": True,
            "candidate_b_default_promotion_closure_evidence_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/default-promotion/closure-evidence"
            ),
            "candidate_b_default_promotion_readiness_audit_admitted": True,
            "candidate_b_default_promotion_readiness_audit_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/default-promotion/readiness-audit"
            ),
            "candidate_b_broader_eligible_corpus_scope_readiness_audit_admitted": True,
            "candidate_b_broader_eligible_corpus_scope_readiness_audit_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_runtime_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_runtime_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_selector_use_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_selector_use_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_selector_use_status_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_selector_use_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use/status"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_selector_activation_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_selector_activation_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-activation"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/activation-receipt/consume"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use/status"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/operator-repeatability/trial"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/promotion-readiness"
            ),
            "candidate_b_broader_eligible_corpus_default_scope_default_promotion_admitted": True,
            "candidate_b_broader_eligible_corpus_default_scope_default_promotion_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/default-promotion"
            ),
            "candidate_b_default_promotion_final_proof_admitted": True,
            "candidate_b_default_promotion_final_proof_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/default-promotion/final-proof"
            ),
            "candidate_b_default_promotion_final_proof_status_admitted": True,
            "candidate_b_default_promotion_final_proof_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/default-promotion/final-proof/status"
            ),
            "candidate_b_full_corpus_operator_workflow_status_admitted": True,
            "candidate_b_full_corpus_operator_workflow_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/status"
            ),
            "candidate_b_full_corpus_operator_workflow_run_admitted": True,
            "candidate_b_full_corpus_operator_workflow_run_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/run"
            ),
            "candidate_b_full_corpus_operator_workflow_history_admitted": True,
            "candidate_b_full_corpus_operator_workflow_history_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
            ),
            "candidate_b_full_corpus_operator_workflow_lifecycle_expire_admitted": True,
            "candidate_b_full_corpus_operator_workflow_lifecycle_expire_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire"
            ),
            "candidate_b_full_corpus_operator_workflow_queue_state_admitted": True,
            "candidate_b_full_corpus_operator_workflow_queue_state_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state"
            ),
            "candidate_b_full_corpus_operator_workflow_execution_boundary_admitted": True,
            "candidate_b_full_corpus_operator_workflow_execution_boundary_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary"
            ),
            "candidate_b_full_corpus_operator_workflow_process_execution_admitted": True,
            "candidate_b_full_corpus_operator_workflow_process_execution_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution"
            ),
            "candidate_b_full_corpus_operator_workflow_process_completion_result_admitted": True,
            "candidate_b_full_corpus_operator_workflow_process_completion_result_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result"
            ),
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_admitted": True,
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof"
            ),
            "candidate_b_full_corpus_operator_workflow_completion_monitor_admitted": True,
            "candidate_b_full_corpus_operator_workflow_completion_monitor_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor"
            ),
            "candidate_b_full_corpus_operator_repeatability_checkpoint_admitted": True,
            "candidate_b_full_corpus_operator_repeatability_checkpoint_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint"
            ),
            "candidate_b_full_corpus_repeatability_rerun_trial_admitted": True,
            "candidate_b_full_corpus_repeatability_rerun_trial_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial"
            ),
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_admitted": True,
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint"
            ),
            "candidate_b_full_corpus_repeatability_acceptance_closeout_admitted": True,
            "candidate_b_full_corpus_repeatability_acceptance_closeout_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout"
            ),
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_admitted": True,
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status"
            ),
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_admitted": True,
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease"
            ),
            "candidate_b_full_corpus_operator_workflow_worker_attempt_admitted": True,
            "candidate_b_full_corpus_operator_workflow_worker_attempt_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt"
            ),
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_admitted": True,
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint"
            ),
            "candidate_b_full_corpus_operator_workflow_completion_failure_admitted": True,
            "candidate_b_full_corpus_operator_workflow_completion_failure_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure"
            ),
            "candidate_b_full_corpus_operator_workflow_retry_policy_admitted": True,
            "candidate_b_full_corpus_operator_workflow_retry_policy_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy"
            ),
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_admitted": True,
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state"
            ),
            "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_admitted": True,
            "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease"
            ),
            "candidate_b_full_corpus_operator_workflow_retry_worker_attempt_admitted": True,
            "candidate_b_full_corpus_operator_workflow_retry_worker_attempt_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt"
            ),
            "candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_admitted": True,
            "candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint"
            ),
            "candidate_b_full_corpus_operator_workflow_retry_completion_failure_admitted": True,
            "candidate_b_full_corpus_operator_workflow_retry_completion_failure_endpoint": (
                f"{api_root}/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure"
            ),
            "candidate_b_default_promotion_selector_switch_admitted": True,
            "candidate_b_default_promotion_selector_scope": ELIGIBLE_CORPUS_SCOPE,
            "source_directory_ingestion_scan_admitted": True,
            "source_directory_ingestion_scan_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/scan"
            ),
            "source_directory_ingestion_status_admitted": True,
            "source_directory_ingestion_status_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/status/{{source_ingestion_batch_id}}"
            ),
            "source_directory_material_preview_admitted": True,
            "source_directory_material_preview_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/material-preview"
            ),
            "source_directory_vector_retrieval_admitted": True,
            "source_directory_vector_retrieval_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/vector-retrieval"
            ),
            "source_directory_hybrid_context_packet_admitted": True,
            "source_directory_hybrid_context_packet_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/hybrid-context-packet"
            ),
            "source_directory_hybrid_context_packet_qualitative_analysis_admitted": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis"
            ),
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_admitted": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis"
            ),
            "source_directory_hybrid_context_packet_qualitative_analysis_status_admitted": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_status_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis/status"
            ),
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_admitted": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis/package/commit"
            ),
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_admitted": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis/package/review/submit"
            ),
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_admitted": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
            ),
            "source_directory_qualitative_hybrid_analysis_admitted": True,
            "source_directory_qualitative_hybrid_analysis_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/qualitative-hybrid-analysis"
            ),
            "source_directory_qualitative_hybrid_analysis_status_admitted": True,
            "source_directory_qualitative_hybrid_analysis_status_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/status"
            ),
            "source_directory_package_commit_admitted": True,
            "source_directory_package_commit_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/package/commit"
            ),
            "source_directory_package_review_submit_admitted": True,
            "source_directory_package_review_submit_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/package/review/submit"
            ),
            "source_directory_package_supersession_preview_admitted": True,
            "source_directory_package_supersession_preview_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/package/supersession/preview"
            ),
            "source_directory_handoff_export_prepare_admitted": True,
            "source_directory_handoff_export_prepare_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/handoff/export/prepare"
            ),
            "source_directory_external_export_download_prepare_admitted": True,
            "source_directory_external_export_download_prepare_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/handoff/export/download/prepare"
            ),
            "source_directory_external_export_download_deliver_admitted": True,
            "source_directory_external_export_download_deliver_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/handoff/export/download/deliver"
            ),
            "source_directory_external_export_download_delivery_status_admitted": True,
            "source_directory_external_export_download_delivery_status_endpoint": (
                f"{api_root}/source/ingestion/server-configured-directory/"
                "qualitative-hybrid-analysis/handoff/export/download/deliver/status"
            ),
            "source_directory_operator_status_surface": "server_configured_operator_directory_text_table_source_family",
            "package_review_admitted": False,
            "external_handoff_admitted": False,
            "external_export_admitted": False,
            "dispatch_admitted": False,
            "readiness_state": "execution_readiness_blocked",
            "readiness_endpoint": f"{api_root}/readiness",
        },
        "authority_rail": dict(authority_rail),
    }
