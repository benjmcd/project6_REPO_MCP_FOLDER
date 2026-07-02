from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


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
    assert matrix["overlays"] == ["public_connectors", "sec_xbrl_offline"]
    assert "single-operator local" in matrix["boundary_note"]
    assert "no auth boundary" in matrix["boundary_note"]
    assert "public_connectors and sec_xbrl_offline overlays" in matrix["boundary_note"]
    assert "operator-workflow + local-deployment" in matrix["boundary_note"]
    assert "simulation/offline-replay only" in matrix["boundary_note"]
    for token in (
        "live SEC egress explicit default-off",
        "no value-reveal default-on",
        "no agent egress",
        "no nonlocal",
    ):
        assert token in matrix["boundary_note"]

    capabilities = matrix["capabilities"]
    by_id = {item["id"]: item for item in capabilities}

    assert {item["status"] for item in capabilities} <= STATUS_VOCABULARY
    assert {item["id"]: item["status"] for item in capabilities} == EXPECTED_CAPABILITY_STATUSES
    assert all(set(item) == {"id", "status", "evidence"} for item in capabilities)
    assert all(isinstance(item["evidence"], str) and item["evidence"].strip() for item in capabilities)
    assert all(item["evidence"].startswith(("./", "README.md", "backend/", "tests/")) for item in capabilities)

    assert by_id["sec_live_network_egress"]["status"] == "experimental_default_off"
    assert by_id["model_agent_egress"]["status"] == "unsupported"
    for capability_id in (
        "sec_value_reveal",
        "sec_controlled_value_reveal_submit",
        "arelle_internal_value_store",
        "arelle_corpus_validation",
        "sec_xbrl_production_admission_evaluator",
        "sec_live_network_egress",
    ):
        assert by_id[capability_id]["status"] == "experimental_default_off"
    for capability_id in (
        "layer3_sec_xbrl_offline_evidence_loader",
        "layer3_sec_xbrl_offline_companyfacts_stage",
        "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
        "layer3_sec_xbrl_e2e_offline_orchestrator",
        "layer3_sec_xbrl_offline_evidence_proof_capability",
    ):
        assert by_id[capability_id]["status"] == "simulation"
    assert "nrc_aps_document_processing.py" in by_id["ocr_external_engine"]["evidence"]
    for connector_id in (
        "sciencebase_public_connector_slice",
        "senate_lda_anonymous_connector_slice",
        "connector_run_observability",
    ):
        connector = by_id[connector_id]
        assert connector["status"] == "supported"
        for marker in ("PR-1", "PR-2", "PR-3", "PR-4", "PR-5"):
            assert marker in connector["evidence"]


def test_support_matrix_connector_evidence_points_to_actual_config_aliases() -> None:
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    config_lines = (REPO_ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8").splitlines()

    def line_number_for(alias: str) -> int:
        return next(index for index, line in enumerate(config_lines, start=1) if alias in line)

    sciencebase_line = line_number_for("SCIENCEBASE_API_BASE_URL")
    senate_base_line = line_number_for("SENATE_LDA_API_BASE_URL")
    senate_key_line = line_number_for("SENATE_LDA_API_KEY")

    assert f"backend/app/core/config.py:{sciencebase_line}" in by_id["sciencebase_public_connector_slice"]["evidence"]
    assert (
        f"backend/app/core/config.py:{senate_base_line}-{senate_key_line}"
        in by_id["senate_lda_anonymous_connector_slice"]["evidence"]
    )


def test_front_door_names_selected_local_expert_profile_without_old_unselected_claim() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "base=local_expert" in readme
    assert 'overlays=["public_connectors","sec_xbrl_offline"]' in readme
    assert "simulation/offline-replay only" in readme
    assert "No release profile is selected yet" not in readme


def test_ocr_support_matrix_doc_acknowledges_installed_tesseract_runtime() -> None:
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    doc = (REPO_ROOT / "docs" / "support-matrix-local-expert.md").read_text(encoding="utf-8")
    by_id = {item["id"]: item for item in matrix["capabilities"]}

    assert by_id["ocr_external_engine"]["status"] == "experimental_default_off"
    assert "installed Tesseract" in doc
    assert "not part of the selected public_connectors overlay" in doc


def test_support_matrix_doc_lists_rc3_offline_simulation_capabilities() -> None:
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    doc = (REPO_ROOT / "docs" / "support-matrix-local-expert.md").read_text(encoding="utf-8")
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    expected_rows = {
        "layer3_sec_xbrl_offline_evidence_loader": "SEC XBRL offline evidence loader",
        "layer3_sec_xbrl_offline_companyfacts_stage": "SEC XBRL offline companyfacts stage",
        "layer3_sec_xbrl_offline_companyfacts_oracle_packet": "SEC XBRL offline companyfacts oracle packet",
        "layer3_sec_xbrl_e2e_offline_orchestrator": "SEC XBRL offline E2E orchestrator",
        "layer3_sec_xbrl_offline_evidence_proof_capability": "SEC XBRL offline evidence proof capability",
    }

    for capability_id, label in expected_rows.items():
        assert by_id[capability_id]["status"] == "simulation"
        assert f"| {label} | `simulation` |" in doc


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
    assert report["overlays"] == ["public_connectors", "sec_xbrl_offline"]
    assert report["release_readiness_owner_selected_profile_specific_gates"] == []
    assert report["default_profile"] == {
        "deployment_mode": "local",
        "auth_owner": "none",
        "route_authorization_mode": "identity_presence",
        "database": "sqlite",
    }
    assert report["pinned_false_flags_status"] == "pass"


def test_support_matrix_checker_rejects_supported_public_connector_without_overlay(tmp_path) -> None:
    checker = _load_checker()
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    matrix["overlays"] = "none"
    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix), encoding="utf-8")

    report = checker.run_support_matrix_check(mutated, repo_root=REPO_ROOT)

    assert report["status"] == "fail"
    assert any("sciencebase_public_connector_slice" in error for error in report["errors"])


def test_support_matrix_checker_accepts_analytics_only_connector_deferrals(tmp_path) -> None:
    checker = _load_checker()
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    matrix["overlays"] = "none"
    matrix["boundary_note"] = (
        "Selected local_expert analytics-only profile with public connector capabilities "
        "held as RC2-targeted connector deferral and no sec_xbrl_offline overlay."
    )
    by_id = {item["id"]: item for item in matrix["capabilities"]}
    for capability_id in (
        "sciencebase_public_connector_slice",
        "senate_lda_anonymous_connector_slice",
        "connector_run_observability",
    ):
        by_id[capability_id]["status"] = "experimental_default_off"
        by_id[capability_id]["evidence"] += "; RC2-targeted connector deferral"
    for capability_id in checker.SIMULATION_CAPABILITIES:
        by_id[capability_id]["status"] = "experimental_default_off"
        by_id[capability_id]["evidence"] += "; deferred without sec_xbrl_offline overlay"
    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix), encoding="utf-8")

    report = checker.run_support_matrix_check(mutated, repo_root=REPO_ROOT)

    assert report["status"] == "pass", report["errors"]


def test_support_matrix_checker_rejects_sec_simulation_without_offline_overlay(tmp_path) -> None:
    checker = _load_checker()
    matrix = _load_json_compatible_yaml(MATRIX_PATH)
    matrix["overlays"] = ["public_connectors"]
    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix), encoding="utf-8")

    report = checker.run_support_matrix_check(mutated, repo_root=REPO_ROOT)

    assert report["status"] == "fail"
    assert any(
        "layer3_sec_xbrl_offline_evidence_loader" in error
        and "without sec_xbrl_offline overlay" in error
        for error in report["errors"]
    )


def test_support_matrix_checker_uses_source_defaults_not_process_environment(tmp_path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED": "true",
            "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED": "true",
            "LAYER3_MODEL_EGRESS_ENABLED": "true",
            "AUTH_OWNER": "proxy",
            "DEPLOYMENT_MODE": "nonlocal",
        }
    )

    completed = subprocess.run(
        [sys.executable, str(CHECKER_PATH)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "pass"
    assert report["default_profile"] == {
        "deployment_mode": "local",
        "auth_owner": "none",
        "route_authorization_mode": "identity_presence",
        "database": "sqlite",
    }
