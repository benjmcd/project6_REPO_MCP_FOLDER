from app.services.layer3_mockup_activation_readiness import (
    MOCKUP_ACTIVATION_READINESS_SCHEMA_ID,
    MOCKUP_FIRST_ADMITTED_SLICE,
    MOCKUP_NEXT_ADMITTED_SLICE,
    mockup_activation_readiness_contract,
)


def test_mockup_activation_readiness_classifies_first_slice_without_full_activation() -> None:
    contract = mockup_activation_readiness_contract()

    assert contract["schema_id"] == MOCKUP_ACTIVATION_READINESS_SCHEMA_ID
    assert contract["selected_first_slice"] == MOCKUP_FIRST_ADMITTED_SLICE
    assert contract["selected_next_slice"] == MOCKUP_NEXT_ADMITTED_SLICE
    assert contract["journey_counts"] == {
        "interactive_live": 2,
        "read_only": 3,
        "intentionally_excluded": 0,
        "blocked": 1,
    }
    journeys = {row["journey_id"]: row for row in contract["journeys"]}
    assert journeys["query_source_setup"]["classification"] == "interactive_live"
    assert journeys["query_source_setup"]["activation_slice"] == MOCKUP_FIRST_ADMITTED_SLICE
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
