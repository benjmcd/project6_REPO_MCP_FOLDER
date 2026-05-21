from app.services.layer3_mockup_activation_readiness import (
    MOCKUP_ACTIVATION_READINESS_SCHEMA_ID,
    MOCKUP_ANALYSIS_ENVIRONMENT_PROJECTION_SLICE,
    MOCKUP_FIRST_ADMITTED_SLICE,
    MOCKUP_NEXT_ADMITTED_SLICE,
    MOCKUP_PDF_LOCATION_PROJECTION_SLICE,
    MOCKUP_SUBLAYER_3C_PROJECTION_SLICE,
    MOCKUP_SUBLAYERS_AB_PROJECTION_SLICE,
    mockup_activation_readiness_contract,
)


def test_mockup_activation_readiness_classifies_first_slice_without_full_activation() -> None:
    contract = mockup_activation_readiness_contract()

    assert contract["schema_id"] == MOCKUP_ACTIVATION_READINESS_SCHEMA_ID
    assert contract["selected_first_slice"] == MOCKUP_FIRST_ADMITTED_SLICE
    assert contract["selected_next_slice"] == MOCKUP_NEXT_ADMITTED_SLICE
    assert contract["selected_projection_slice"] == MOCKUP_ANALYSIS_ENVIRONMENT_PROJECTION_SLICE
    assert contract["selected_projection_slices"] == [
        MOCKUP_PDF_LOCATION_PROJECTION_SLICE,
        MOCKUP_SUBLAYERS_AB_PROJECTION_SLICE,
        MOCKUP_SUBLAYER_3C_PROJECTION_SLICE,
        MOCKUP_ANALYSIS_ENVIRONMENT_PROJECTION_SLICE,
    ]
    assert contract["journey_counts"] == {
        "interactive_live": 2,
        "read_only": 4,
        "intentionally_excluded": 0,
        "blocked": 1,
    }
    journeys = {row["journey_id"]: row for row in contract["journeys"]}
    assert journeys["query_source_setup"]["classification"] == "interactive_live"
    assert journeys["query_source_setup"]["activation_slice"] == MOCKUP_FIRST_ADMITTED_SLICE
    pdf_location = journeys["pdf_location"]
    assert pdf_location["classification"] == "read_only"
    assert pdf_location["activation_slice"] is None
    assert pdf_location["projection_slice"] == MOCKUP_PDF_LOCATION_PROJECTION_SLICE
    assert pdf_location["projection_contract"]["contract_id"] == MOCKUP_PDF_LOCATION_PROJECTION_SLICE
    assert pdf_location["projection_contract"]["schema_id"] == "layer3.pdf_location_projection.v1"
    assert (
        pdf_location["projection_contract"]["server_authority_contract"]
        == "aps_content_document_chunk_page_refs_and_citation_highlight_spans"
    )
    assert "State.sessionSummary.pdf_location_projection" in pdf_location["projection_contract"]["status_projection"]
    assert "#mockup-pdf-location-projection" == pdf_location["projection_contract"]["rendered_surface"]
    assert "a[href]" in pdf_location["projection_contract"]["read_only_controls_absent"]
    assert "browser_owned_authoritative_pdf_location" in pdf_location["projection_contract"]["negative_boundaries"]
    assert "provider_or_object_store_url_exposure" in pdf_location["projection_contract"]["negative_boundaries"]
    sublayers_ab = journeys["sublayers_3a_3b"]
    assert sublayers_ab["classification"] == "read_only"
    assert sublayers_ab["activation_slice"] is None
    assert sublayers_ab["projection_slice"] == MOCKUP_SUBLAYERS_AB_PROJECTION_SLICE
    assert sublayers_ab["projection_contract"]["contract_id"] == MOCKUP_SUBLAYERS_AB_PROJECTION_SLICE
    assert sublayers_ab["projection_contract"]["schema_id"] == "layer3.sublayer_visualization_state.v1"
    assert (
        sublayers_ab["projection_contract"]["server_authority_contract"]
        == "read_only_persisted_layer3_rows_and_gate_state_projection"
    )
    assert "State.sessionSummary.sublayer_visualization" in sublayers_ab["projection_contract"]["status_projection"]
    assert "State.materialPreview" in sublayers_ab["projection_contract"]["status_projection"]
    assert "#mockup-sublayers-ab-projection" == sublayers_ab["projection_contract"]["rendered_surface"]
    assert "a[href]" in sublayers_ab["projection_contract"]["read_only_controls_absent"]
    assert "raw_local_file_path_exposure" in sublayers_ab["projection_contract"]["negative_boundaries"]
    assert "runtime_request_widening" in sublayers_ab["projection_contract"]["negative_boundaries"]
    sublayer_3c = journeys["sublayer_3c_execution_lanes"]
    assert sublayer_3c["classification"] == "read_only"
    assert sublayer_3c["activation_slice"] is None
    assert sublayer_3c["projection_slice"] == MOCKUP_SUBLAYER_3C_PROJECTION_SLICE
    assert sublayer_3c["projection_contract"]["contract_id"] == MOCKUP_SUBLAYER_3C_PROJECTION_SLICE
    assert sublayer_3c["projection_contract"]["schema_id"] == "layer3.analysis_environment_projection.v1"
    assert (
        sublayer_3c["projection_contract"]["server_authority_contract"]
        == "read_only_session_summary_analysis_environment_execution_projection"
    )
    assert (
        "State.sessionSummary.analysis_environment_projection"
        in sublayer_3c["projection_contract"]["status_projection"]
    )
    assert "State.resultStatus" in sublayer_3c["projection_contract"]["status_projection"]
    assert "#mockup-execution-lanes-projection" == sublayer_3c["projection_contract"]["rendered_surface"]
    assert "a[href]" in sublayer_3c["projection_contract"]["read_only_controls_absent"]
    assert "execution_start_side_effect" in sublayer_3c["projection_contract"]["negative_boundaries"]
    assert "package_construction_or_mutation" in sublayer_3c["projection_contract"]["negative_boundaries"]
    analysis_environment = journeys["analysis_environment_projection"]
    assert analysis_environment["classification"] == "read_only"
    assert analysis_environment["activation_slice"] is None
    assert analysis_environment["projection_slice"] == MOCKUP_ANALYSIS_ENVIRONMENT_PROJECTION_SLICE
    assert (
        analysis_environment["projection_contract"]["contract_id"]
        == MOCKUP_ANALYSIS_ENVIRONMENT_PROJECTION_SLICE
    )
    assert analysis_environment["projection_contract"]["schema_id"] == "layer3.analysis_environment_projection.v1"
    assert (
        analysis_environment["projection_contract"]["server_authority_contract"]
        == "read_only_session_summary_analysis_environment_plane_projection"
    )
    assert (
        "State.sessionSummary.analysis_environment_projection"
        in analysis_environment["projection_contract"]["status_projection"]
    )
    assert "State.resultReview" in analysis_environment["projection_contract"]["status_projection"]
    assert ".analysis-environment-projection" == analysis_environment["projection_contract"]["rendered_surface"]
    assert "a[href]" in analysis_environment["projection_contract"]["read_only_controls_absent"]
    assert "analysis_run_mutation" in analysis_environment["projection_contract"]["negative_boundaries"]
    assert "full_mockup_program_activation" in analysis_environment["projection_contract"]["negative_boundaries"]
    output_handoff = journeys["output_review_package_handoff"]
    assert output_handoff["classification"] == "interactive_live"
    assert output_handoff["activation_slice"] == MOCKUP_NEXT_ADMITTED_SLICE
    assert output_handoff["interaction_contract"]["contract_id"] == MOCKUP_NEXT_ADMITTED_SLICE
    assert "/api/v1/layer3/package/review/commit" in output_handoff["interaction_contract"]["route_authority"]
    assert "/api/v1/layer3/handoff/export/prepare" in output_handoff["interaction_contract"]["route_authority"]
    assert (
        "/api/v1/layer3/handoff/export/internal-webhook/dispatch"
        in output_handoff["interaction_contract"]["route_authority"]
    )
    assert "#internal-webhook-dispatch-panel" in output_handoff["interaction_contract"]["rendered_controls"]
    assert "raw_provider_token_exposure" in output_handoff["interaction_contract"]["negative_boundaries"]
    assert journeys["full_mockup_program"]["classification"] == "blocked"
    assert contract["full_mockup_activation_enabled"] is False
    assert contract["frontend_only_durable_authority_enabled"] is False
    assert contract["raw_provider_exposure_enabled"] is False
    assert contract["connector_provider_write_enabled"] is False
    assert contract["broad_source_model_rag_expansion_enabled"] is False
    assert contract["mutates_runtime_state"] is False
    assert set(contract["required_activation_evidence"]) >= {
        "live_source_owner",
        "route_api_contract",
        "server_authority_contract",
        "headed_browser_proof",
        "headless_browser_proof",
    }
