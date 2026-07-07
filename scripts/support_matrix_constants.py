from __future__ import annotations

STATUS_VOCABULARY = {
    "supported",
    "experimental_default_off",
    "simulation",
    "unsupported",
}

PINNED_FALSE_FLAGS = [
    "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "LAYER3_MODEL_EGRESS_ENABLED",
    "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
    "LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
]

EXPECTED_STATUS_BY_ID = {
    "method_aware_analytics_vertical": "supported",
    "sciencebase_public_connector_slice": "supported",
    "senate_lda_anonymous_connector_slice": "supported",
    "worldbank_indicators_anonymous_connector_slice": "supported",
    "connector_run_observability": "supported",
    "layer3_workbench_ui": "supported",
    "health_readiness_openapi": "supported",
    "sec_value_reveal": "experimental_default_off",
    "sec_controlled_value_reveal_submit": "experimental_default_off",
    "arelle_internal_value_store": "experimental_default_off",
    "arelle_corpus_validation": "experimental_default_off",
    "sec_xbrl_production_admission_evaluator": "experimental_default_off",
    "analysis_product_package_inventory": "experimental_default_off",
    "ocr_external_engine": "experimental_default_off",
    "sec_live_network_egress": "experimental_default_off",
    "sec_offline_replay_path": "simulation",
    "layer3_sec_xbrl_offline_evidence_loader": "simulation",
    "layer3_sec_xbrl_offline_companyfacts_stage": "simulation",
    "layer3_sec_xbrl_offline_companyfacts_oracle_packet": "simulation",
    "layer3_sec_xbrl_e2e_offline_orchestrator": "simulation",
    "layer3_sec_xbrl_offline_evidence_proof_capability": "simulation",
    "nrc_aps_replay_corpus_gate": "simulation",
    "offline_staged_redaction_value_store_resolution": "simulation",
    "real_provider_delivery": "unsupported",
    "model_agent_egress": "unsupported",
    "nonlocal_multi_trust_multi_identity": "unsupported",
    "high_availability": "unsupported",
    "keyed_connectors": "unsupported",
    "signed_reference_export": "unsupported",
}

SUPPORTED_CAPABILITIES = {
    capability_id
    for capability_id, status in EXPECTED_STATUS_BY_ID.items()
    if status == "supported"
}
EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES = {
    capability_id
    for capability_id, status in EXPECTED_STATUS_BY_ID.items()
    if status == "experimental_default_off"
}
SEC_XBRL_OFFLINE_SIMULATION_CAPABILITIES = {
    capability_id
    for capability_id, status in EXPECTED_STATUS_BY_ID.items()
    if status == "simulation"
}
SIMULATION_CAPABILITIES = SEC_XBRL_OFFLINE_SIMULATION_CAPABILITIES
UNSUPPORTED_CAPABILITIES = {
    capability_id
    for capability_id, status in EXPECTED_STATUS_BY_ID.items()
    if status == "unsupported"
}

BASE_SUPPORTED_CAPABILITIES = {
    "method_aware_analytics_vertical",
    "layer3_workbench_ui",
    "health_readiness_openapi",
}
PUBLIC_CONNECTOR_CAPABILITIES = SUPPORTED_CAPABILITIES - BASE_SUPPORTED_CAPABILITIES
PUBLIC_CONNECTOR_DEFERRAL_CAPABILITIES = PUBLIC_CONNECTOR_CAPABILITIES
FORBIDDEN_SUPPORTED_CAPABILITIES = (
    UNSUPPORTED_CAPABILITIES | EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES
)

PUBLIC_CONNECTORS_OVERLAY = ["public_connectors"]
RC3_SEC_XBRL_OFFLINE_OVERLAY = ["public_connectors", "sec_xbrl_offline"]
RC3_OVERLAYS = RC3_SEC_XBRL_OFFLINE_OVERLAY
PUBLIC_CONNECTORS_REQUIRED_EVIDENCE = ["PR-1", "PR-2", "PR-3", "PR-4", "PR-5"]
RC3_BOUNDARY_TOKENS = [
    "live SEC egress explicit default-off",
    "no value-reveal default-on",
    "no agent egress",
    "no nonlocal",
]

SEC_XBRL_ONLY_SIMULATION_CAPABILITIES = (
    SEC_XBRL_OFFLINE_SIMULATION_CAPABILITIES - {"nrc_aps_replay_corpus_gate"}
)
