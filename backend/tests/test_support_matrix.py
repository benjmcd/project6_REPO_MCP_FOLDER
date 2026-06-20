from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"
RELEASE_READINESS_PATH = REPO_ROOT / "config" / "release_readiness.yaml"
CHECKER_PATH = REPO_ROOT / "scripts" / "support_matrix_check.py"

STATUS_VOCABULARY = {
    "supported",
    "experimental_default_off",
    "simulation",
    "unsupported",
}

EXPECTED_CAPABILITY_STATUSES = {
    "method_aware_analytics_vertical": "supported",
    "sciencebase_public_connector_slice": "supported",
    "senate_lda_anonymous_connector_slice": "supported",
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
    "sec_offline_replay_path": "simulation",
    "nrc_aps_replay_corpus_gate": "simulation",
    "offline_staged_redaction_value_store_resolution": "simulation",
    "sec_live_network_egress": "unsupported",
    "real_provider_delivery": "unsupported",
    "model_agent_egress": "unsupported",
    "nonlocal_multi_trust_multi_identity": "unsupported",
    "high_availability": "unsupported",
    "keyed_connectors": "unsupported",
    "signed_reference_export": "unsupported",
}


def _load_json_compatible_yaml(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_checker():
    spec = importlib.util.spec_from_file_location("support_matrix_check", CHECKER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_support_matrix_declares_local_expert_capability_boundary() -> None:
    matrix = _load_json_compatible_yaml(MATRIX_PATH)

    assert matrix["schema_id"] == "project6.support_matrix.v1"
    assert matrix["profile"] == "local_expert"
    assert matrix["overlays"] == "none"
    assert "single-operator local" in matrix["boundary_note"]
    assert "no auth boundary" in matrix["boundary_note"]

    capabilities = matrix["capabilities"]
    by_id = {item["id"]: item for item in capabilities}

    assert {item["status"] for item in capabilities} <= STATUS_VOCABULARY
    assert {item["id"]: item["status"] for item in capabilities} == EXPECTED_CAPABILITY_STATUSES
    assert all(set(item) == {"id", "status", "evidence"} for item in capabilities)
    assert all(isinstance(item["evidence"], str) and item["evidence"].strip() for item in capabilities)
    assert all(item["evidence"].startswith(("./", "README.md", "backend/", "tests/")) for item in capabilities)

    assert by_id["sec_live_network_egress"]["status"] == "unsupported"
    assert by_id["model_agent_egress"]["status"] == "unsupported"


def test_support_matrix_pins_local_expert_flags_without_release_manifest_profile_gates() -> None:
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    release_manifest = _load_json_compatible_yaml(RELEASE_READINESS_PATH)

    assert release_manifest["owner_selected_profile_specific_gates"] == []
    assert matrix["release_readiness_manifest"] == "profile-neutral; do not populate owner_selected_profile_specific_gates"
    assert matrix["pinned_false_flags"] == [
        "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
        "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
        "LAYER3_MODEL_EGRESS_ENABLED",
        "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
        "LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
    ]


def test_support_matrix_checker_passes_against_current_config_defaults() -> None:
    checker = _load_checker()
    report = checker.run_support_matrix_check(MATRIX_PATH, repo_root=REPO_ROOT)

    assert report["schema_id"] == "project6.support_matrix_check.v1"
    assert report["status"] == "pass"
    assert report["profile"] == "local_expert"
    assert report["overlays"] == "none"
    assert report["release_readiness_owner_selected_profile_specific_gates"] == []
    assert report["default_profile"] == {
        "deployment_mode": "local",
        "auth_owner": "none",
        "route_authorization_mode": "identity_presence",
        "database": "sqlite",
    }
    assert report["pinned_false_flags_status"] == "pass"
