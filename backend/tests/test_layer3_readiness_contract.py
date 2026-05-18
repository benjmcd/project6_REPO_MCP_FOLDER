from __future__ import annotations

from app.services import layer3_workbench
from app.services.layer3_readiness_contract import (
    EXECUTION_READINESS_SCHEMA_ID,
    READINESS_DEFERRED_GATES,
    READINESS_IMPLEMENTED_GATES,
    READINESS_REQUIRED_GATES,
    build_readiness_contract,
)


def test_layer3_readiness_contract_is_shared() -> None:
    state_model = layer3_workbench._workbench_state_model()
    state_action_contract = layer3_workbench._workbench_state_action_contract()
    authority_matrix_contract = layer3_workbench._workbench_authority_matrix_contract()

    direct = build_readiness_contract(
        api_root=layer3_workbench.API_ROOT,
        state_model=state_model,
        state_action_contract=state_action_contract,
        authority_matrix_contract=authority_matrix_contract,
    )
    workbench = layer3_workbench.readiness_contract()

    for response in (direct, workbench):
        assert response["request_id"]
        assert response["server_time"].endswith("Z")
    direct_body = {key: value for key, value in direct.items() if key not in {"request_id", "server_time"}}
    workbench_body = {key: value for key, value in workbench.items() if key not in {"request_id", "server_time"}}

    assert direct_body == workbench_body
    assert direct["schema_id"] == EXECUTION_READINESS_SCHEMA_ID
    assert direct["required_gates"] == list(READINESS_REQUIRED_GATES)
    assert direct["implemented_gates"] == list(READINESS_IMPLEMENTED_GATES)
    assert direct["deferred_gates"] == list(READINESS_DEFERRED_GATES)
    assert direct["state_model"] == state_model
    assert direct["state_action_contract"] == state_action_contract
    assert direct["authority_matrix_contract"] == authority_matrix_contract
    assert direct["execution_enabled"] is False
    assert direct["dispatch_admitted"] is False
    assert direct["plan_revision_recovery_admitted"] is True
    assert direct["plan_revision_recovery_endpoint"] == "/api/v1/layer3/plan/revision/recover"
    assert direct["approved_plan_cancel_admitted"] is True
    assert direct["approved_plan_cancel_endpoint"] == "/api/v1/layer3/plan/approved/cancel"
    assert direct["source_directory_ingestion_scan_admitted"] is True
    assert direct["source_directory_ingestion_scan_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan"
    )
    assert direct["source_directory_ingestion_status_admitted"] is True
    assert direct["source_directory_ingestion_status_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}"
    )
    assert direct["source_directory_material_preview_admitted"] is True
    assert direct["source_directory_material_preview_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview"
    )
    assert direct["source_directory_vector_retrieval_admitted"] is True
    assert direct["source_directory_vector_retrieval_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval"
    )
    assert direct["source_directory_hybrid_context_packet_admitted"] is True
    assert direct["source_directory_hybrid_context_packet_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet"
    )
    assert direct["source_directory_hybrid_context_packet_qualitative_analysis_admitted"] is True
    assert direct["source_directory_hybrid_context_packet_qualitative_analysis_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "hybrid-context-packet/qualitative-analysis"
    )
    assert direct["source_directory_qualitative_hybrid_analysis_admitted"] is True
    assert direct["source_directory_qualitative_hybrid_analysis_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis"
    )
    assert direct["source_directory_package_commit_admitted"] is True
    assert direct["source_directory_package_commit_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/package/commit"
    )
    assert direct["source_directory_package_review_submit_admitted"] is True
    assert direct["source_directory_package_review_submit_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/package/review/submit"
    )
    assert direct["source_directory_package_supersession_preview_admitted"] is True
    assert direct["source_directory_package_supersession_preview_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/package/supersession/preview"
    )
    assert direct["source_directory_handoff_export_prepare_admitted"] is True
    assert direct["source_directory_handoff_export_prepare_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/handoff/export/prepare"
    )
    assert direct["source_directory_external_export_download_prepare_admitted"] is True
    assert direct["source_directory_external_export_download_prepare_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/handoff/export/download/prepare"
    )
    assert direct["source_directory_operator_status_surface"] == (
        "server_configured_operator_directory_text_table_source_family"
    )
    assert direct["idempotency_contract"]["client_request_id_required_for_approved_plan_cancel"] is True
    assert direct["idempotency_contract"]["client_request_id_required_for_source_directory_ingestion_scan"] is True
    assert direct["idempotency_contract"]["client_request_id_required_for_source_directory_material_preview"] is False
    assert direct["idempotency_contract"]["client_request_id_required_for_source_directory_vector_retrieval"] is False
    assert (
        direct["idempotency_contract"]["client_request_id_required_for_source_directory_hybrid_context_packet"]
        is False
    )
    assert (
        direct["idempotency_contract"][
            "client_request_id_required_for_source_directory_hybrid_context_packet_qualitative_analysis"
        ]
        is False
    )
    assert (
        direct["idempotency_contract"][
            "client_request_id_required_for_source_directory_qualitative_hybrid_analysis"
        ]
        is False
    )
    assert direct["idempotency_contract"]["client_request_id_required_for_source_directory_package_commit"] is True
    assert (
        direct["idempotency_contract"]["client_request_id_required_for_source_directory_package_review_submit"]
        is True
    )
    assert (
        direct["idempotency_contract"][
            "client_request_id_required_for_source_directory_package_supersession_preview"
        ]
        is False
    )
    assert (
        direct["idempotency_contract"]["client_request_id_required_for_source_directory_handoff_export_prepare"]
        is True
    )
    assert (
        direct["idempotency_contract"][
            "client_request_id_required_for_source_directory_external_export_download_prepare"
        ]
        is True
    )
    assert direct["concurrency_contract"]["approved_plan_cancel_without_replacement_only"] is True
    assert direct["concurrency_contract"]["source_directory_ingestion_scan_uses_configured_source_root"] is True
    assert direct["concurrency_contract"]["source_directory_status_is_read_only"] is True
    assert direct["concurrency_contract"]["source_directory_material_preview_is_read_only"] is True
    assert direct["concurrency_contract"]["source_directory_vector_retrieval_is_read_only"] is True
    assert direct["concurrency_contract"]["source_directory_hybrid_context_packet_is_read_only"] is True
    assert (
        direct["concurrency_contract"]["source_directory_hybrid_context_packet_qualitative_analysis_is_read_only"]
        is True
    )
    assert direct["concurrency_contract"]["source_directory_qualitative_hybrid_analysis_is_read_only"] is True
    assert (
        direct["concurrency_contract"]["source_directory_package_commit_uses_session_reconciliation_and_package_locks"]
        is True
    )
    assert (
        direct["concurrency_contract"][
            "source_directory_package_review_submit_uses_session_reconciliation_and_package_locks"
        ]
        is True
    )
    assert direct["concurrency_contract"]["source_directory_package_supersession_preview_is_read_only"] is True
    assert (
        direct["concurrency_contract"][
            "source_directory_handoff_export_prepare_uses_session_reconciliation_and_package_locks"
        ]
        is True
    )
    assert (
        direct["concurrency_contract"][
            "source_directory_external_export_download_prepare_uses_session_reconciliation_and_package_locks"
        ]
        is True
    )
    assert direct["deferred_decisions"]["source_breadth"] == (
        "requires later freeze before RAG/vector/upload/local-directory expansion"
    )
    assert direct["deferred_decisions"]["source_directory_operator_status"].startswith(
        "admitted only as backend bootstrap/readiness exposure"
    )
    assert direct["deferred_decisions"]["source_directory_hybrid_context_packet"].startswith(
        "admitted only as a read-only deterministic fusion"
    )
    assert direct["deferred_decisions"]["source_directory_hybrid_context_packet_qualitative_analysis"].startswith(
        "admitted only as a read-only deterministic qualitative-analysis reader"
    )
    assert direct["deferred_decisions"]["source_directory_package_supersession_preview"].startswith(
        "admitted only as a read-only source-directory package mutation"
    )
    assert direct["deferred_decisions"]["source_directory_external_export_download_prepare"].startswith(
        "admitted only as a reference-only readiness descriptor"
    )
    assert direct["deferred_decisions"]["revision_recovery"].startswith("admitted only as preview-refresh recovery")
    assert direct["deferred_decisions"]["approved_plan_correction"].startswith(
        "only approved_plan_cancel_without_replacement is admitted"
    )
