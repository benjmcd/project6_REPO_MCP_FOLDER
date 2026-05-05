from app.services.layer3_mockup_boundary import (
    MOCKUP_AUTHORITY_ROLE,
    MOCKUP_SOURCE_FILES,
    MOCKUP_TRUTH_STATE_CONTRACT_SCHEMA_ID,
    MOCKUP_TRUTH_STATE_MODE,
    mockup_truth_state_contract,
)


def test_mockup_truth_state_contract_keeps_full_mockup_activation_fail_closed() -> None:
    contract = mockup_truth_state_contract()

    assert contract["schema_id"] == MOCKUP_TRUTH_STATE_CONTRACT_SCHEMA_ID
    assert contract["mode"] == MOCKUP_TRUTH_STATE_MODE
    assert contract["authority_role"] == MOCKUP_AUTHORITY_ROLE
    assert contract["source_files"] == list(MOCKUP_SOURCE_FILES)
    assert set(contract["deferred_capabilities"]) >= {
        "full_mockup_activation",
        "frontend_only_durable_state",
        "broad_execution",
        "broad_qualitative_execution",
        "hybrid_execution",
        "rag_vector_retrieval",
        "local_upload_or_directory_source_expansion",
        "provider_public_url",
        "connector_destination_dispatch",
        "package_mutation_reconstruction",
        "hidden_llm_planning",
    }
    assert set(contract["forbidden_runtime_fields"]) >= {
        "mockup_activation",
        "frontend_only_state",
        "browser_local_persistence",
        "rag_plan",
        "vector_plan",
        "source_upload",
        "local_directory",
        "connector_id",
        "destination_id",
        "provider_url",
        "public_url",
        "package_payload",
        "hidden_llm_plan",
    }
    assert set(contract["required_activation_evidence"]) >= {
        "live_source_owner",
        "route_api_contract",
        "server_authority_contract",
        "negative_invariant_proof",
        "headed_browser_proof",
        "headless_browser_proof",
        "progress_check_guard",
    }
    assert contract["mockups_are_runtime_authority"] is False
    assert contract["full_mockup_activation_enabled"] is False
    assert contract["frontend_only_durable_state_enabled"] is False
    assert contract["broad_execution_enabled"] is False
    assert contract["source_widening_enabled"] is False
    assert contract["connector_destination_dispatch_enabled"] is False
    assert contract["package_mutation_reconstruction_enabled"] is False
    assert contract["provider_public_url_enabled"] is False
    assert contract["hidden_llm_planning_enabled"] is False
    assert contract["mutates_runtime_state"] is False
    assert contract["requires_later_freeze"] is True
    assert contract["requires_browser_proof_before_ui_activation"] is True
