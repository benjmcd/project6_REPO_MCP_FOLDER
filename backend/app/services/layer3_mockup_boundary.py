from __future__ import annotations

from typing import Any


MOCKUP_TRUTH_STATE_CONTRACT_SCHEMA_ID = "layer3.mockup_truth_state_contract.v1"
MOCKUP_TRUTH_STATE_MODE = "mockups_target_state_only"
MOCKUP_AUTHORITY_ROLE = "target_state_design_specification"
MOCKUP_SOURCE_FILES = (
    "next_milestone_plans/layer3-mockups/assets.md",
    "next_milestone_plans/layer3-mockups/mockup-spec.txt",
)
MOCKUP_DEFERRED_CAPABILITIES = (
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
)
MOCKUP_FORBIDDEN_RUNTIME_FIELDS = (
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
)
MOCKUP_REQUIRED_ACTIVATION_EVIDENCE = (
    "live_source_owner",
    "route_api_contract",
    "server_authority_contract",
    "negative_invariant_proof",
    "headed_browser_proof",
    "headless_browser_proof",
    "progress_check_guard",
)


def mockup_truth_state_contract() -> dict[str, Any]:
    return {
        "schema_id": MOCKUP_TRUTH_STATE_CONTRACT_SCHEMA_ID,
        "mode": MOCKUP_TRUTH_STATE_MODE,
        "authority_role": MOCKUP_AUTHORITY_ROLE,
        "source_files": list(MOCKUP_SOURCE_FILES),
        "deferred_capabilities": list(MOCKUP_DEFERRED_CAPABILITIES),
        "forbidden_runtime_fields": list(MOCKUP_FORBIDDEN_RUNTIME_FIELDS),
        "required_activation_evidence": list(MOCKUP_REQUIRED_ACTIVATION_EVIDENCE),
        "mockups_are_runtime_authority": False,
        "full_mockup_activation_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "broad_execution_enabled": False,
        "source_widening_enabled": False,
        "connector_destination_dispatch_enabled": False,
        "package_mutation_reconstruction_enabled": False,
        "provider_public_url_enabled": False,
        "hidden_llm_planning_enabled": False,
        "mutates_runtime_state": False,
        "requires_later_freeze": True,
        "requires_browser_proof_before_ui_activation": True,
    }
