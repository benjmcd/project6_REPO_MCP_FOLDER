from __future__ import annotations

from typing import Any

from app.services.layer3_candidate_b_default_readiness import ELIGIBLE_CORPUS_SCOPE
from app.services.layer3_preview_contract import (
    material_preview_hash_contract,
    plan_preview_hash_contract,
)
from app.services.layer3_response_contract import base_response


EXECUTION_READINESS_SCHEMA_ID = "layer3.execution_readiness_contract.v1"

READINESS_REQUIRED_GATES = (
    "proof-manifest",
    "state-model",
    "preview-hash",
    "idempotency",
    "concurrency",
    "revision-recovery",
    "approved-plan-cancel",
    "approved-plan-correction",
    "output-taxonomy",
    "source-breadth",
    "execution-selection",
    "analysis-execution-start",
    "result-status",
    "result-review",
    "package-review-preview",
    "package-construction",
    "package-review-submit",
    "handoff-export-prepare",
    "aps-handoff-dispatch",
    "external-export-download-prepare",
    "external-export-download-deliver",
    "source-directory-qualitative-hybrid-analysis-status",
    "source-directory-package-supersession-preview",
    "source-directory-hybrid-context-packet",
    "source-directory-hybrid-context-packet-qualitative-analysis",
    "source-directory-hybrid-context-packet-qualitative-analysis-package-review-preview",
    "source-directory-hybrid-context-packet-qualitative-analysis-status",
    "source-directory-hybrid-context-packet-qualitative-analysis-package-commit",
    "source-directory-hybrid-context-packet-qualitative-analysis-package-review-submit",
    "source-directory-hybrid-context-packet-qualitative-analysis-handoff-export-prepare",
    "source-directory-hybrid-context-packet-qualitative-analysis-external-export-download-prepare",
    "source-directory-hybrid-context-packet-qualitative-analysis-external-export-download-deliver",
    "source-directory-hybrid-context-packet-qualitative-analysis-external-export-download-delivery-status",
    "source-directory-hybrid-context-packet-qualitative-analysis-provider-private-signed-url-prepare",
    "source-directory-hybrid-context-packet-qualitative-analysis-internal-webhook-dispatch",
    "source-directory-hybrid-context-packet-qualitative-analysis-internal-webhook-status",
    "candidate-b-artifact-family-status",
    "candidate-b-visual-lane-status",
    "candidate-b-bundle-downstream-proof",
    "candidate-b-runtime-downstream-proof",
    "candidate-b-default-promotion-operator-status",
    "candidate-b-default-promotion-closure-evidence",
    "candidate-b-default-promotion-readiness-audit",
    "source-directory-external-export-download-prepare",
    "source-directory-external-export-download-deliver",
    "source-directory-external-export-download-delivery-status",
    "connector-local-destination-receipt",
    "source-directory-operator-status",
    "browser-proof",
)
READINESS_IMPLEMENTED_GATES = (
    "proof-manifest",
    "state-model",
    "preview-hash",
    "idempotency",
    "concurrency",
    "revision-recovery",
    "approved-plan-cancel",
    "execution-selection",
    "analysis-execution-start",
    "result-status",
    "result-review",
    "package-review-preview",
    "package-construction",
    "package-review-submit",
    "handoff-export-prepare",
    "aps-handoff-dispatch",
    "external-export-download-prepare",
    "external-export-download-deliver",
    "source-directory-qualitative-hybrid-analysis-status",
    "source-directory-package-supersession-preview",
    "source-directory-hybrid-context-packet",
    "source-directory-hybrid-context-packet-qualitative-analysis",
    "source-directory-hybrid-context-packet-qualitative-analysis-package-review-preview",
    "source-directory-hybrid-context-packet-qualitative-analysis-status",
    "source-directory-hybrid-context-packet-qualitative-analysis-package-commit",
    "source-directory-hybrid-context-packet-qualitative-analysis-package-review-submit",
    "source-directory-hybrid-context-packet-qualitative-analysis-handoff-export-prepare",
    "source-directory-hybrid-context-packet-qualitative-analysis-external-export-download-prepare",
    "source-directory-hybrid-context-packet-qualitative-analysis-external-export-download-deliver",
    "source-directory-hybrid-context-packet-qualitative-analysis-external-export-download-delivery-status",
    "source-directory-hybrid-context-packet-qualitative-analysis-provider-private-signed-url-prepare",
    "source-directory-hybrid-context-packet-qualitative-analysis-internal-webhook-dispatch",
    "source-directory-hybrid-context-packet-qualitative-analysis-internal-webhook-status",
    "candidate-b-artifact-family-status",
    "candidate-b-visual-lane-status",
    "candidate-b-bundle-downstream-proof",
    "candidate-b-runtime-downstream-proof",
    "candidate-b-default-promotion-operator-status",
    "candidate-b-default-promotion-closure-evidence",
    "candidate-b-default-promotion-readiness-audit",
    "source-directory-external-export-download-prepare",
    "source-directory-external-export-download-deliver",
    "source-directory-external-export-download-delivery-status",
    "connector-local-destination-receipt",
    "source-directory-operator-status",
)
READINESS_DEFERRED_GATES = (
    "approved-plan-correction",
    "output-taxonomy",
    "source-breadth",
    "browser-proof",
)


def build_readiness_contract(
    *,
    api_root: str,
    state_model: dict[str, Any],
    state_action_contract: dict[str, Any],
    authority_matrix_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        **base_response(EXECUTION_READINESS_SCHEMA_ID),
        "execution_admitted": False,
        "execution_enabled": False,
        "execution_selection_admitted": True,
        "execution_selection_endpoint": f"{api_root}/execution/select",
        "analysis_execution_admitted": False,
        "analysis_execution_start_admitted": True,
        "analysis_execution_start_endpoint": f"{api_root}/execution/start",
        "single_aps_doc_qualitative_execution_admitted": True,
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
        "internal_fake_local_destination_receipt_endpoint": f"{api_root}/handoff/connector/local-destination/receipt",
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
        "replacement_package_artifact_manifest_endpoint": f"{api_root}/package/replacement-artifact/manifest/record",
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
        "candidate_b_default_promotion_closure_evidence_admitted": True,
        "candidate_b_default_promotion_closure_evidence_endpoint": (
            f"{api_root}/source/ingestion/candidate-b/default-promotion/closure-evidence"
        ),
        "candidate_b_default_promotion_readiness_audit_admitted": True,
        "candidate_b_default_promotion_readiness_audit_endpoint": (
            f"{api_root}/source/ingestion/candidate-b/default-promotion/readiness-audit"
        ),
        "candidate_b_default_promotion_selector_switch_admitted": True,
        "candidate_b_default_promotion_selector_scope": ELIGIBLE_CORPUS_SCOPE,
        "source_directory_ingestion_scan_admitted": True,
        "source_directory_ingestion_scan_endpoint": f"{api_root}/source/ingestion/server-configured-directory/scan",
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
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare_admitted": True,
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare_endpoint": (
            f"{api_root}/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver_admitted": True,
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver_endpoint": (
            f"{api_root}/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver"
        ),
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status_admitted": True,
        "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status_endpoint": (
            f"{api_root}/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status"
        ),
        "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare_admitted": True,
        "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare_endpoint": (
            f"{api_root}/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/prepare"
        ),
        "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch_admitted": True,
        "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch_endpoint": (
            f"{api_root}/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch"
        ),
        "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status_admitted": True,
        "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status_endpoint": (
            f"{api_root}/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/status/"
            "{source_directory_internal_webhook_dispatch_receipt_id}"
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
        "required_gates": list(READINESS_REQUIRED_GATES),
        "implemented_gates": list(READINESS_IMPLEMENTED_GATES),
        "deferred_gates": list(READINESS_DEFERRED_GATES),
        "state_model": state_model,
        "state_action_contract": state_action_contract,
        "authority_matrix_contract": authority_matrix_contract,
        "preview_hash_contract": plan_preview_hash_contract(),
        "material_preview_hash_contract": material_preview_hash_contract(),
        "idempotency_contract": {
            "schema_id": "layer3.idempotency_contract.v1",
            "client_request_id_supported": True,
            "client_request_id_required_current_slice": False,
            "client_request_id_required_for_gate_b_decision": True,
            "client_request_id_required_for_execution_selection": True,
            "client_request_id_required_for_analysis_execution_start": True,
            "client_request_id_required_for_execution_result_status": False,
            "client_request_id_required_for_execution_result_review": True,
            "client_request_id_required_for_package_review_preview": False,
            "client_request_id_required_for_package_construction_commit": True,
            "client_request_id_required_for_package_review_submit": True,
            "client_request_id_required_for_handoff_export_prepare": True,
            "client_request_id_required_for_aps_handoff_dispatch": True,
            "client_request_id_required_for_external_export_download_prepare": True,
            "client_request_id_required_for_external_export_download_deliver": True,
            "client_request_id_required_for_internal_fake_local_destination_receipt": True,
            "client_request_id_required_for_package_supersession_preview": True,
            "client_request_id_required_for_replacement_package_set_authority": True,
            "client_request_id_required_for_package_supersession_commit": True,
            "client_request_id_required_for_replacement_package_artifact_manifest": True,
            "client_request_id_required_for_replacement_package_namespace": True,
            "client_request_id_required_for_plan_revision_recovery": True,
            "client_request_id_required_for_approved_plan_cancel": True,
            "client_request_id_required_for_source_directory_ingestion_scan": True,
            "client_request_id_required_for_source_directory_material_preview": False,
            "client_request_id_required_for_source_directory_vector_retrieval": False,
            "client_request_id_required_for_source_directory_hybrid_context_packet": False,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis": False,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview": False,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_status": False,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_package_commit": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch": True,
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status": False,
            "client_request_id_required_for_source_directory_qualitative_hybrid_analysis": False,
            "client_request_id_required_for_source_directory_qualitative_hybrid_analysis_status": False,
            "client_request_id_required_for_source_directory_package_commit": True,
            "client_request_id_required_for_source_directory_package_review_submit": True,
            "client_request_id_required_for_source_directory_package_supersession_preview": False,
            "client_request_id_required_for_source_directory_handoff_export_prepare": True,
            "client_request_id_required_for_source_directory_external_export_download_prepare": True,
            "client_request_id_required_for_source_directory_external_export_download_deliver": True,
            "client_request_id_required_for_source_directory_external_export_download_delivery_status": True,
            "duplicate_gate_b_decision": "same required client_request_id, provided source context, provided material_preview_id, and decision manifest uses a durable Gate B idempotency claim and returns existing Gate B session; conflicts fail closed",
            "gate_b_decision_idempotency_scope": "durable_claim_and_post_commit_retry",
            "gate_b_decision_concurrent_duplicate_lock": True,
            "duplicate_plan_approval": "returns existing approved-plan conflict; no duplicate L3AnalysisPlan",
            "duplicate_plan_revision": "returns existing revision-control conflict; no duplicate revision-control state",
            "duplicate_execution_selection": "same client_request_id and same approved plan returns existing selection; conflicts fail closed",
            "duplicate_analysis_execution_start": "same client_request_id and same selected pass returns existing execution state; conflicts fail closed",
            "duplicate_execution_result_status": "read-only status inspection does not create idempotency state",
            "duplicate_execution_result_review": "same client_request_id and same selected pass returns existing review state; conflicts fail closed",
            "duplicate_package_review_preview": "read-only package-review preview inspection does not create idempotency state",
            "duplicate_package_construction_commit": "same client_request_id and same authority basis returns existing package rows; conflicts fail closed",
            "duplicate_package_review_submit": "same authority basis and same operator decision returns existing package-review state; conflicts fail closed",
            "duplicate_handoff_export_prepare": "same authority basis and same operator decision returns existing preparation state; conflicts fail closed",
            "duplicate_aps_handoff_dispatch": "same client_request_id and same prepared-envelope authority returns existing APS handoff state; conflicts fail closed",
            "duplicate_external_export_download_prepare": "same client_request_id and same APS handoff authority returns existing readiness state; conflicts fail closed",
            "duplicate_external_export_download_deliver": "read-only delivery revalidates the recorded readiness descriptor and may re-stream the same existing artifact",
            "duplicate_internal_fake_local_destination_receipt": "same client_request_id and same connector dispatch authority basis returns existing local destination receipt; same basis with a different request conflicts fail closed",
            "duplicate_package_supersession_preview": "read-only package supersession preview recomputes the same package-set and downstream-dependency hash without persistence",
            "duplicate_replacement_package_set_authority": "same client_request_id or authority basis returns existing replacement package-set authority; conflicts fail closed",
            "duplicate_package_supersession_commit": "same client_request_id or commit basis returns existing immutable supersession lineage record; conflicts fail closed",
            "duplicate_replacement_package_artifact_manifest": "same client_request_id or authority basis returns existing verified replacement artifact manifest; conflicts fail closed",
            "duplicate_replacement_package_namespace": "same client_request_id and authority basis returns existing replacement namespace row; conflicts fail closed",
            "duplicate_plan_revision_recovery": "same client_request_id and same recorded revision-control authority returns existing recovery state; conflicts fail closed",
            "duplicate_approved_plan_cancel": "same client_request_id and same approved-plan authority basis returns existing cancellation state; conflicts fail closed",
            "duplicate_source_directory_ingestion_scan": "same client_request_id and same server-configured directory basis returns existing source-directory batch state; conflicts fail closed",
            "duplicate_source_directory_material_preview": "read-only material preview revalidates recorded source-directory material authority",
            "duplicate_source_directory_vector_retrieval": "read-only deterministic vector retrieval revalidates source-directory material, text-index, vector-index, and embedding-index authority",
            "duplicate_source_directory_hybrid_context_packet": "read-only deterministic hybrid context packet revalidates source-directory lexical context-packet and vector-retrieval authority without durable retrieval rows",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis": "read-only deterministic qualitative analysis revalidates source-directory hybrid context-packet authority without package, provider, connector, network, or durable analysis rows",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview": "read-only deterministic package-review preview revalidates source-directory hybrid qualitative-analysis authority without package rows or package payload writes",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_status": "read-only status revalidates source-directory hybrid context-packet qualitative-analysis authority and existing package/review/handoff state without evidence payloads, package payloads, or durable rows",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_package_commit": "same client_request_id and same source-directory hybrid qualitative-analysis package authority returns existing package rows; conflicts fail closed",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit": "same authority basis and same source-directory hybrid operator decision returns existing package-review state; conflicts fail closed",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare": "same authority basis and same source-directory hybrid operator decision returns existing handoff/export prepare state; conflicts fail closed",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare": "same authority basis and same source-directory hybrid export/download readiness decision returns existing readiness state; conflicts fail closed",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver": "read-only delivery revalidates the prepared source-directory hybrid package authority and may re-stream the same existing package artifact",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status": "read-only status revalidates the prepared source-directory hybrid package delivery authority without streaming the package artifact",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare": "same client_request_id or provider-private authority basis returns existing redacted provider-private receipt; conflicts fail closed",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch": "same client_request_id or source-directory hybrid external export/download authority basis returns existing internal webhook receipt; conflicts fail closed",
            "duplicate_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status": "read-only status revalidates the durable source-directory internal webhook dispatch receipt",
            "duplicate_source_directory_qualitative_hybrid_analysis": "read-only deterministic qualitative-hybrid analysis revalidates source-directory material, retrieval, and context-packet authority",
            "duplicate_source_directory_qualitative_hybrid_analysis_status": "read-only status revalidates source-directory qualitative-hybrid analysis authority without returning full evidence segments or package-preview payloads",
            "duplicate_source_directory_package_commit": "same client_request_id and same source-directory qualitative-analysis package authority returns existing package rows; conflicts fail closed",
            "duplicate_source_directory_package_review_submit": "same authority basis and same source-directory operator decision returns existing package-review state; conflicts fail closed",
            "duplicate_source_directory_package_supersession_preview": "read-only preview recomputes the source-directory package set hash and downstream dependency hash without package row mutation or payload rewrite",
            "duplicate_source_directory_handoff_export_prepare": "same authority basis and same source-directory operator decision returns existing handoff/export prepare state; conflicts fail closed",
            "duplicate_source_directory_external_export_download_prepare": "same authority basis and same source-directory export/download readiness decision returns existing readiness state; conflicts fail closed",
            "duplicate_source_directory_external_export_download_deliver": "read-only delivery revalidates the prepared source-directory package authority and may re-stream the same existing package artifact",
            "duplicate_source_directory_external_export_download_delivery_status": "read-only status revalidates the prepared source-directory package delivery authority without streaming the package artifact",
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
            "package_review_submit_uses_session_reconciliation_and_package_locks": True,
            "handoff_export_prepare_uses_session_reconciliation_and_package_locks": True,
            "aps_handoff_dispatch_uses_session_reconciliation_and_package_locks": True,
            "external_export_download_prepare_uses_session_reconciliation_and_package_locks": True,
            "external_export_download_deliver_uses_session_reconciliation_and_package_locks": True,
            "internal_fake_local_destination_receipt_uses_unique_request_and_basis": True,
            "package_supersession_preview_is_read_only": True,
            "replacement_package_set_authority_uses_unique_request_and_basis": True,
            "package_supersession_commit_uses_unique_request_and_basis": True,
            "replacement_package_artifact_manifest_uses_unique_request_and_basis": True,
            "replacement_package_artifact_manifest_is_manifest_only": True,
            "replacement_package_namespace_uses_unique_request_basis_and_manifest_kind": True,
            "replacement_package_namespace_uses_separate_replacement_table": True,
            "plan_revision_recovery_uses_session_lock": True,
            "plan_revision_recovery_is_preview_refresh_only": True,
            "approved_plan_cancel_uses_session_and_plan_locks": True,
            "approved_plan_cancel_without_replacement_only": True,
            "source_directory_ingestion_scan_uses_configured_source_root": True,
            "source_directory_status_is_read_only": True,
            "source_directory_material_preview_is_read_only": True,
            "source_directory_vector_retrieval_is_read_only": True,
            "source_directory_hybrid_context_packet_is_read_only": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_is_read_only": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_is_read_only": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_status_is_read_only": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_uses_session_reconciliation_and_package_locks": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_uses_session_reconciliation_and_package_locks": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_uses_session_reconciliation_and_package_locks": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare_uses_session_reconciliation_and_package_locks": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver_uses_session_reconciliation_and_package_locks": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status_is_read_only": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare_uses_provider_private_durable_state_authority": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch_uses_unique_request_and_basis": True,
            "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status_is_read_only": True,
            "source_directory_qualitative_hybrid_analysis_is_read_only": True,
            "source_directory_qualitative_hybrid_analysis_status_is_read_only": True,
            "source_directory_package_commit_uses_session_reconciliation_and_package_locks": True,
            "source_directory_package_review_submit_uses_session_reconciliation_and_package_locks": True,
            "source_directory_package_supersession_preview_is_read_only": True,
            "source_directory_handoff_export_prepare_uses_session_reconciliation_and_package_locks": True,
            "source_directory_external_export_download_prepare_uses_session_reconciliation_and_package_locks": True,
            "source_directory_external_export_download_deliver_uses_session_reconciliation_and_package_locks": True,
            "source_directory_external_export_download_delivery_status_is_read_only": True,
            "broad_analysis_execution_requires_later_freeze": True,
        },
        "deferred_decisions": {
            "schema_id": "layer3.deferred_execution_decisions.v1",
            "revision_recovery": "admitted only as preview-refresh recovery from terminal pre-approval revision-control state",
            "approved_plan_cancel": "admitted only as cancellation without replacement of the current approved plan before pass-run creation",
            "approved_plan_correction": "only approved_plan_cancel_without_replacement is admitted; approved-plan supersession, replacement, reopening, and deletion still require later freezes",
            "output_taxonomy": "requires later freeze before results or package UI",
            "source_breadth": "requires later freeze before RAG/vector/upload/local-directory expansion",
            "package_construction": "admitted only for selected-pass workbench commit; broader package construction still requires later freeze",
            "package_review_submit": "admitted only for bounded decision recording over an already constructed workbench package set",
            "aps_handoff_dispatch": "admitted only for server-side APS evidence-bundle handoff after handoff_export_prepared",
            "external_export_download_prepare": "admitted only as a reference-only readiness descriptor after aps_handoff_dispatched; browser download remains disabled",
            "external_export_download_deliver": "admitted only as same-origin streaming of the already validated APS evidence-bundle artifact after recorded readiness; public or signed URLs remain disabled",
            "internal_connector_dispatch_record": "admitted only as response-safe internal dispatch intent record after associated-cohort external export/download readiness; external invocation and destination writes remain blocked",
            "internal_fake_local_destination_receipt": "admitted only as a durable fake/local receipt over an existing internal connector dispatch record; external connector invocation, destination writes, credentials, network writes, and real destination integration remain blocked",
            "package_supersession_preview": "admitted only as read-only immutable package supersession preview; package row mutation, payload rewrite, and supersession commit remain blocked",
            "replacement_package_set_authority": "admitted only as a durable metadata authority record; package row mutation, payload writes, and broad package mutation remain blocked",
            "package_supersession_commit": "admitted only as a durable immutable lineage record; package row mutation, payload writes, and broad package mutation remain blocked",
            "replacement_package_artifact_manifest": "admitted only as server-side manifest verification of existing replacement refs and hashes; artifact generation, package row mutation, payload writes, and broad package mutation remain blocked",
            "replacement_package_namespace": "admitted only as separate replacement output-package namespace rows over verified manifest artifacts; source L3OutputPackage rows, payload writes, and broad package mutation remain blocked",
            "external_handoff_export_dispatch": "browser download, public/signed URL generation, connector dispatch, destination selection, and non-APS dispatch still require later freezes",
            "source_directory_operator_status": "admitted only as backend bootstrap/readiness exposure for the already-admitted server-configured local directory scan, status, material-preview, vector-retrieval, qualitative-hybrid analysis, source-directory hybrid package/review/handoff/download/redacted-provider/internal-webhook routes, and legacy source-directory handoff routes",
            "source_directory_hybrid_context_packet": "admitted only as a read-only deterministic fusion of existing source-directory lexical context-packet and vector-retrieval authority; persistent vector stores, RAG execution, provider/model runtime, package mutation, connector dispatch, network egress, and frontend controls remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis": "admitted only as a read-only deterministic qualitative-analysis reader over the source-directory hybrid context packet; package construction, package-review submit, handoff/export, provider/model runtime, RAG execution, connector dispatch, network egress, frontend controls, and durable analysis rows remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview": "admitted only as a read-only package-review preview over the source-directory hybrid context-packet qualitative-analysis authority; package construction, package-review submit, handoff/export, payload writes, package mutation, provider/model runtime, connector dispatch, network egress, and frontend controls remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_status": "admitted only as a read-only operator-visible status reader over the source-directory hybrid context-packet qualitative-analysis chain; evidence payloads, package payloads, package mutation, provider/model runtime, connector dispatch, network egress, frontend controls, and raw path exposure remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit": "admitted only as bounded package construction over source-directory hybrid context-packet qualitative-analysis package-preview authority; package-review submit, handoff/export, package mutation, provider/model runtime, connector dispatch, network egress, frontend controls, and new source families remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit": "admitted only as bounded decision recording over constructed source-directory hybrid context-packet qualitative-analysis packages; handoff/export, package mutation, provider/model runtime, connector dispatch, network egress, frontend controls, and new source families remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare": "admitted only as prepare-only internal export envelope recording after approved source-directory hybrid package-review submit; external export/download is admitted only by the separate source-directory hybrid download routes, provider URL bridges are admitted only by their separate redacted-provider routes, and connector dispatch, network egress, package mutation, and new source families remain disabled for this endpoint",
            "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare": "admitted only as a reference-only readiness descriptor after source-directory hybrid handoff_export_prepared; same-origin delivery/status and redacted provider-private prepare are separate admitted routes, while raw provider URLs, connector dispatch, provider network/object writes, frontend durable authority, package mutation, and new source families remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver": "admitted only as same-origin streaming of one already constructed source-directory hybrid package payload after recorded readiness; raw provider URLs, signed URL direct use, connector dispatch, provider network/object writes, frontend durable authority, package mutation, and raw path exposure remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status": "admitted only as a read-only operator-visible status reader over the existing source-directory hybrid delivery authority; byte streaming, raw provider URLs, signed URL direct use, connector dispatch, provider network/object writes, frontend durable authority, package mutation, and raw path exposure remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare": "admitted only as a redacted provider-private receipt prepare over validated source-directory hybrid delivery/package authority; direct provider-private use, raw provider URLs or tokens, provider network/object writes, connector dispatch, package mutation, source expansion, frontend durable authority, and full mockup activation remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch": "admitted only as a server-configured allowlisted internal-webhook dispatch over validated source-directory hybrid external export/download readiness using a redacted envelope; operator-supplied URLs, raw headers or tokens, generic connector dispatch, destination writes, raw package exposure, package mutation, source expansion, frontend durable authority, and full mockup activation remain disabled",
            "source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status": "admitted only as a read-only status reader over the durable source-directory internal webhook dispatch receipt; redispatch, destination writes, raw target URLs, raw headers or tokens, package mutation, source expansion, frontend durable authority, and full mockup activation remain disabled",
            "source_directory_qualitative_hybrid_analysis_status": "admitted only as a read-only operator-visible status reader over the existing deterministic source-directory qualitative-hybrid analysis authority; full supporting segments, package-preview payloads, prompt/model runtime, package writes, connector dispatch, network egress, frontend controls, and raw path exposure remain disabled",
            "source_directory_package_supersession_preview": "admitted only as a read-only source-directory package mutation/reconstruction preview over an approved package-review submit; replacement authority, supersession commit, package row mutation, payload writes or rewrite, provider delivery, connector dispatch, network egress, and frontend controls remain disabled",
            "source_directory_external_export_download_prepare": "admitted only as a reference-only readiness descriptor after source-directory handoff_export_prepared; provider URLs, connector dispatch, network egress, frontend controls, and package mutation remain disabled",
            "source_directory_external_export_download_deliver": "admitted only as same-origin streaming of one already constructed source-directory package payload after source-directory external export/download prepare; provider URLs, signed URLs, connector dispatch, network egress, frontend controls, package mutation, and raw path exposure remain disabled",
            "source_directory_external_export_download_delivery_status": "admitted only as a read-only operator-visible status reader over the existing source-directory delivery authority; byte streaming, provider URLs, signed URLs, connector dispatch, network egress, frontend controls, package mutation, and raw path exposure remain disabled",
        },
    }
