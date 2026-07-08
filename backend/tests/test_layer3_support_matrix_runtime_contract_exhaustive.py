from __future__ import annotations

import functools
import importlib.util
import json
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"
AUDIT_PATH = REPO_ROOT / "scripts" / "support_matrix_runtime_contract_audit.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("support_matrix_runtime_contract_audit", AUDIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def _audit():
    return _load_audit_module()


@functools.lru_cache(maxsize=1)
def _report() -> dict:
    return _audit().build_report(MATRIX_PATH, repo_root=REPO_ROOT)


def _matrix_capability_ids() -> list[str]:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    return [str(item["id"]) for item in matrix["capabilities"]]


def test_support_matrix_runtime_contract_audit_reports_clean_pass() -> None:
    report = _report()

    assert report["schema_id"] == "project6.support_matrix_runtime_contract_audit.v1"
    assert report["status"] == "pass", report["errors"]
    assert report["capability_count"] == 32
    assert report["errors"] == []
    assert {item["status"] for item in report["pinned_false_flags"]} == {"pass"}
    assert report["coverage_by_status"] == {
        "experimental_default_off": [
            "analysis_product_package_inventory",
            "arelle_corpus_validation",
            "arelle_internal_value_store",
            "ocr_external_engine",
            "sec_controlled_value_reveal_submit",
            "sec_live_network_egress",
            "sec_value_reveal",
            "sec_xbrl_production_admission_evaluator",
        ],
        "simulation": [
            "layer3_sec_xbrl_e2e_offline_orchestrator",
            "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
            "layer3_sec_xbrl_offline_companyfacts_stage",
            "layer3_sec_xbrl_offline_evidence_loader",
            "layer3_sec_xbrl_offline_evidence_proof_capability",
            "nrc_aps_replay_corpus_gate",
            "offline_staged_redaction_value_store_resolution",
            "sec_offline_replay_path",
        ],
        "supported": [
            "bls_v1_anonymous_connector_slice",
            "cftc_cot_anonymous_connector_slice",
            "connector_run_observability",
            "health_readiness_openapi",
            "layer3_workbench_ui",
            "method_aware_analytics_vertical",
            "oecd_sdmx_anonymous_connector_slice",
            "sciencebase_public_connector_slice",
            "senate_lda_anonymous_connector_slice",
            "worldbank_indicators_anonymous_connector_slice",
        ],
        "unsupported": [
            "high_availability",
            "keyed_connectors",
            "model_agent_egress",
            "nonlocal_multi_trust_multi_identity",
            "real_provider_delivery",
            "signed_reference_export",
        ],
    }


@pytest.mark.parametrize("capability_id", _matrix_capability_ids())
def test_support_matrix_runtime_contract_exhaustive_for_each_capability(capability_id: str) -> None:
    report = _report()
    result_by_id = {item["id"]: item for item in report["capabilities"]}
    result = result_by_id[capability_id]

    assert result["status"] == "pass", result["errors"]
    assert result["declared_status"] == result["expected_status"]
    assert result["evidence"]["passed"] is True
    assert result["runtime_probe"] != {}


def test_support_matrix_runtime_contract_cli_rejects_synthetic_status_drift(tmp_path, capsys) -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for capability in matrix["capabilities"]:
        if capability["id"] == "method_aware_analytics_vertical":
            capability["status"] = "unsupported"
            break
    mutated = tmp_path / "support_matrix.json"
    mutated.write_text(json.dumps(matrix), encoding="utf-8")

    exit_code = _audit().main(["--matrix", str(mutated)])
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 1
    assert report["status"] == "fail"
    assert any(
        "status drift for method_aware_analytics_vertical" in error
        for error in report["errors"]
    )


def test_support_matrix_runtime_contract_restores_db_init_env(monkeypatch) -> None:
    monkeypatch.delenv("DB_INIT_MODE", raising=False)

    report = _audit().build_report(MATRIX_PATH, repo_root=REPO_ROOT)

    assert report["status"] == "pass", report["errors"]
    assert "DB_INIT_MODE" not in os.environ


def test_support_matrix_runtime_contract_redacts_keyed_connector_secret() -> None:
    from app.core.config import settings

    old_key = settings.senate_lda_api_key
    settings.senate_lda_api_key = "runtime-secret"
    try:
        payload = _audit()._probe_keyed_connectors_unsupported()
    finally:
        settings.senate_lda_api_key = old_key

    serialized = json.dumps(payload, sort_keys=True)
    assert payload["senate_key_configured"] is True
    assert "runtime-secret" not in serialized
    assert "senate_key_default" not in payload


def test_support_matrix_runtime_contract_sec_live_probe_forces_default_off_guard() -> None:
    from app.core.config import settings

    old_value = settings.layer3_sec_edgar_live_network_enabled
    settings.layer3_sec_edgar_live_network_enabled = True
    try:
        payload = _audit()._probe_sec_live_network_default_off()
        assert settings.layer3_sec_edgar_live_network_enabled is True
    finally:
        settings.layer3_sec_edgar_live_network_enabled = old_value

    assert "network_disabled" in payload["default_off_error_code"]
    assert payload["explicit_enabled_status"] == "available"
    assert payload["explicit_enabled_network_request_made"] is True
    assert payload["explicit_enabled_raw_url_exposed"] is False
    assert payload["explicit_enabled_artifact_bytes_exposed"] is False


def test_support_matrix_runtime_contract_sec_live_probe_restores_request_counter() -> None:
    from app.services import layer3_sec_edgar_live_source_artifact as live

    with live._SEC_LIVE_REQUEST_COUNT_LOCK:
        old_count = live._SEC_LIVE_REQUEST_COUNT
        live._SEC_LIVE_REQUEST_COUNT = 7
    try:
        payload = _audit()._probe_sec_live_network_default_off()
        with live._SEC_LIVE_REQUEST_COUNT_LOCK:
            restored_count = live._SEC_LIVE_REQUEST_COUNT
    finally:
        with live._SEC_LIVE_REQUEST_COUNT_LOCK:
            live._SEC_LIVE_REQUEST_COUNT = old_count

    assert payload["explicit_enabled_network_request_made"] is True
    assert restored_count == 7
