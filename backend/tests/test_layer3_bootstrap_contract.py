from app.services import layer3_workbench
from app.services.layer3_bootstrap_contract import (
    BOOTSTRAP_FEATURE_FLAGS,
    BOOTSTRAP_SCHEMA_ID,
    build_bootstrap_contract,
)


def test_layer3_bootstrap_contract_is_shared() -> None:
    workbench_body = layer3_workbench.bootstrap()

    direct_body = build_bootstrap_contract(
        route=layer3_workbench.ROUTE,
        api_root=layer3_workbench.API_ROOT,
        supported_source_classes=layer3_workbench.SUPPORTED_SOURCE_CLASSES,
        unsupported_source_classes=layer3_workbench.UNSUPPORTED_SOURCE_CLASSES,
        gate_labels=layer3_workbench.GATE_LABELS,
        active_gate_labels=layer3_workbench.ACTIVE_GATES,
        unavailable_gate_labels=layer3_workbench.DOWNSTREAM_UNAVAILABLE,
        state_action_contract=workbench_body["state_action_contract"],
        authority_matrix_contract=workbench_body["authority_matrix_contract"],
        mockup_activation_readiness=workbench_body["mockup_activation_readiness"],
        authority_rail=workbench_body["authority_rail"],
    )
    direct_body["request_id"] = workbench_body["request_id"]
    direct_body["server_time"] = workbench_body["server_time"]

    assert direct_body == workbench_body
    assert direct_body["schema_id"] == BOOTSTRAP_SCHEMA_ID
    assert (
        direct_body["authority_matrix_contract"]
        == workbench_body["authority_matrix_contract"]
    )
    assert direct_body["features"] == dict(BOOTSTRAP_FEATURE_FLAGS)
    assert direct_body["features"]["single_aps_doc_qualitative_execution"] is True
    assert direct_body["features"]["plan_revision_recovery"] is True
    assert direct_body["features"]["approved_plan_cancel"] is True
    assert direct_body["features"]["source_directory_ingestion_scan"] is True
    assert direct_body["features"]["source_directory_ingestion_status"] is True
    assert direct_body["features"]["source_directory_material_preview"] is True
    assert direct_body["features"]["source_directory_vector_retrieval"] is True
    assert direct_body["features"]["source_directory_hybrid_context_packet"] is True
    assert direct_body["features"]["source_directory_hybrid_context_packet_qualitative_analysis"] is True
    assert (
        direct_body["features"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview"
        ]
        is True
    )
    assert direct_body["features"][
        "source_directory_hybrid_context_packet_qualitative_analysis_status"
    ] is True
    assert (
        direct_body["features"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit"
        ]
        is True
    )
    assert (
        direct_body["features"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit"
        ]
        is True
    )
    assert (
        direct_body["features"][
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare"
        ]
        is True
    )
    assert direct_body["features"]["source_directory_qualitative_hybrid_analysis"] is True
    assert direct_body["features"]["source_directory_package_commit"] is True
    assert direct_body["features"]["source_directory_package_review_submit"] is True
    assert direct_body["features"]["source_directory_package_supersession_preview"] is True
    assert direct_body["features"]["source_directory_handoff_export_prepare"] is True
    assert direct_body["features"]["source_directory_external_export_download_prepare"] is True
    assert direct_body["features"]["broad_qualitative_execution"] is False
    assert direct_body["features"]["rag_vector_retrieval"] is False
    assert direct_body["features"]["dispatch"] is False
    assert direct_body["execution_readiness"]["dispatch_admitted"] is False
    assert direct_body["execution_readiness"]["plan_revision_recovery_admitted"] is True
    assert direct_body["execution_readiness"]["approved_plan_cancel_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_ingestion_scan_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_ingestion_scan_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan"
    )
    assert direct_body["execution_readiness"]["source_directory_ingestion_status_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_ingestion_status_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}"
    )
    assert direct_body["execution_readiness"]["source_directory_material_preview_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_material_preview_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview"
    )
    assert direct_body["execution_readiness"]["source_directory_vector_retrieval_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_vector_retrieval_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval"
    )
    assert direct_body["execution_readiness"]["source_directory_hybrid_context_packet_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_hybrid_context_packet_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet"
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_admitted"
        ]
        is True
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_endpoint"
        ]
        == (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        )
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_admitted"
        ]
        is True
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_endpoint"
        ]
        == (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        )
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_status_admitted"
        ]
        is True
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_status_endpoint"
        ]
        == (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        )
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_admitted"
        ]
        is True
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_endpoint"
        ]
        == (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        )
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_admitted"
        ]
        is True
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_endpoint"
        ]
        == (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        )
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_admitted"
        ]
        is True
    )
    assert (
        direct_body["execution_readiness"][
            "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_endpoint"
        ]
        == (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        )
    )
    assert direct_body["execution_readiness"]["source_directory_qualitative_hybrid_analysis_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_qualitative_hybrid_analysis_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis"
    )
    assert direct_body["execution_readiness"]["source_directory_package_commit_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_package_commit_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/package/commit"
    )
    assert direct_body["execution_readiness"]["source_directory_package_review_submit_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_package_review_submit_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/package/review/submit"
    )
    assert direct_body["execution_readiness"]["source_directory_package_supersession_preview_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_package_supersession_preview_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/package/supersession/preview"
    )
    assert direct_body["execution_readiness"]["source_directory_handoff_export_prepare_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_handoff_export_prepare_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/handoff/export/prepare"
    )
    assert direct_body["execution_readiness"]["source_directory_external_export_download_prepare_admitted"] is True
    assert direct_body["execution_readiness"]["source_directory_external_export_download_prepare_endpoint"] == (
        "/api/v1/layer3/source/ingestion/server-configured-directory/"
        "qualitative-hybrid-analysis/handoff/export/download/prepare"
    )
    assert (
        direct_body["execution_readiness"]["source_directory_operator_status_surface"]
        == "server_configured_operator_directory_text_table_source_family"
    )
    assert direct_body["execution_readiness"]["readiness_state"] == "execution_readiness_blocked"
