from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESTATEMENT_PATH = (
    ROOT / "diagnostics" / "assessment" / "sec-xbrl-default-on-admission-restatement.py"
)


def _restatement_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_default_on_admission_restatement", RESTATEMENT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_source_tree(root: Path, *, runtime_default_on: bool = False) -> None:
    (root / "diagnostics" / "assessment").mkdir(parents=True, exist_ok=True)
    (root / "diagnostics" / "assessment" / "sec-xbrl-real-corpus-product-runner.py").write_text(
        "# runner source marker\n",
        encoding="utf-8",
    )
    config_default = "True" if runtime_default_on else "False"
    config_text = f"""
layer3_sec_edgar_live_network_enabled: bool = Field(
        default=False,
)
layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(
        default={config_default},
)
layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(
        default=False,
)
"""
    (root / "backend" / "app" / "core").mkdir(parents=True, exist_ok=True)
    (root / "backend" / "app" / "core" / "config.py").write_text(config_text, encoding="utf-8")
    bridge_text = "\n".join(
        [
            "arelle_sidecar_receipt_required",
            "sec_edgar_html_inline_xbrl_fact_material_bridge_arelle_sidecar_lineage_mismatch",
            "sec_edgar_arelle_sidecar_internal_value_store_missing",
            "sec_edgar_arelle_sidecar_internal_value_store_hash_mismatch",
            "sec_edgar_arelle_sidecar_internal_value_store_lineage_mismatch",
            "taxonomy_package_unavailable",
            "raw_authority_exposed",
        ]
    )
    service_dir = root / "backend" / "app" / "services"
    service_dir.mkdir(parents=True, exist_ok=True)
    (service_dir / "layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py").write_text(
        bridge_text,
        encoding="utf-8",
    )
    (service_dir / "layer3_sec_xbrl_sidecar.py").write_text("# sidecar source\n", encoding="utf-8")
    tests_dir = root / "backend" / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_layer3_api.py").write_text("# api tests\n", encoding="utf-8")
    (tests_dir / "test_sec_xbrl_sidecar.py").write_text("# sidecar tests\n", encoding="utf-8")


def _report_paths(root: Path) -> dict[str, Path]:
    base = root / "diagnostics" / "assessment"
    return {
        "default_on_gate": base / "sec-xbrl-default-on-gate-report.json",
        "broader_reliability": base / "sec-xbrl-broader-corpus-reliability-gate-report.json",
        "historical_real_product_runner": base / "sec-xbrl-real-corpus-product-runner-report.json",
        "sector_family_validation": base / "sec-xbrl-sector-family-real-filer-validation-report.json",
        "value_reveal_live_proof": base / "sec-xbrl-value-reveal-live-proof-report.json",
        "admission_review": base / "sec-xbrl-default-on-admission-review-report.json",
        "runtime_default": base / "sec-xbrl-default-on-runtime-report.json",
        "default_posture": base / "sec-xbrl-default-posture-decision-report.json",
        "operator_runbook": base / "sec-xbrl-operator-runbook-matrix-selection-report.json",
    }


def _write_valid_reports(root: Path, *, runtime_default_on: bool = False) -> None:
    paths = _report_paths(root)
    forms = {"10-K": 13, "10-Q": 4, "20-F": 1, "40-F": 1, "6-K": 2, "8-K": 10}
    _write_json(
        paths["default_on_gate"],
        {
            "schema_id": "diagnostics.sec_xbrl_default_on_corpus_expansion_gate.v1",
            "decision": "default_on_admitted_candidate",
            "ready_for_default_on": True,
            "source_reports": {},
            "summary": {
                "companyfacts_value_compared_count": 3790,
                "companyfacts_value_match_rate": 0.9923,
                "forms": {"10-K": 4, "10-Q": 1, "20-F": 1, "40-F": 1, "6-K": 2, "8-K": 3},
            },
            "criteria": [
                {"criterion": "independent_count_and_dts_completeness", "state": "passed"},
                {"criterion": "bridge_cutover_parity", "state": "passed"},
            ],
        },
    )
    _write_json(
        paths["broader_reliability"],
        {
            "schema_id": "diagnostics.sec_xbrl_broader_corpus_reliability_gate.v1",
            "decision": "broader_corpus_reliability_admitted",
            "source_reports": {
                "historical_real_product_runner": "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json"
            },
            "summary": {
                "real_product_path_companyfacts_value_match_rate": 0.99,
                "real_product_path_filing_count": 32,
                "real_product_path_supported_record_count": 30,
            },
        },
    )
    _write_json(
        paths["historical_real_product_runner"],
        {
            "schema_id": "diagnostics.sec_xbrl_real_corpus_product_runner.v1",
            "decision": "real_corpus_default_on_validated",
            "gate_verdict": "PASS",
            "fake_sec_client_used": False,
            "live_sec_network_used": True,
            "current_run_live_sec_network_used": False,
            "offline_redacted_product_report_import": {
                "state": "passed",
                "used": True,
                "blocked_reasons": [],
                "evidence": {
                    "inherited_live_sec_network_used": True,
                    "current_run_live_sec_network_used": False,
                    "current_run_arelle_subprocess_invoked": False,
                    "storage_marker_matches_supplied_storage": True,
                    "summary_mismatches": [],
                    "redaction_scan": {
                        "passed": True,
                        "raw_accession_found": False,
                        "raw_cik_found": False,
                        "raw_sec_url_found": False,
                        "raw_local_path_found": False,
                        "raw_operator_contact_found": False,
                        "raw_value_magnitude_found": False,
                    },
                },
            },
            "source_reports": {},
            "summary": {
                "real_filing_count": 32,
                "issuer_hash_count": 16,
                "supported_record_count": 30,
                "records_with_handoff_export_prepare": 30,
                "records_with_arelle_sidecar_output": 30,
                "records_with_selected_fact_authority_equal_to_sidecar": 30,
                "resolved_fact_count": 52558,
                "independent_inline_fact_count": 52558,
                "completeness_guard_failed_count": 0,
                "unexpected_blocked_or_degraded_count": 0,
                "companyfacts_value_compared_count": 9131,
                "companyfacts_value_match_rate": 0.99,
                "forms": forms,
            },
            "redaction": {
                "identity_hash_only": True,
                "raw_accessions_committed": False,
                "raw_sec_urls_committed": False,
                "raw_values_committed": False,
                "local_storage_roots_committed": False,
            },
            "non_goals_preserved": {
                "operator_value_reveal_enabled": False,
                "final_financial_statement_semantics_claimed": False,
                "cross_company_comparability_claimed": False,
            },
        },
    )
    _write_json(
        paths["sector_family_validation"],
        {
            "schema_id": "diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1",
            "target": "sec_xbrl_sector_family_real_filer_validation_v1",
            "decision": "sector_family_real_filer_validation_satisfied",
            "gate_verdict": "PASS",
            "source_reports": {},
            "report_scope": {
                "broader_live_matrix_product_gate_in_scope": False,
                "historical_live_matrix_reproducible_offline_from_available_inputs": False,
            },
        },
    )
    _write_json(
        paths["value_reveal_live_proof"],
        {
            "schema_id": "diagnostics.sec_xbrl_value_reveal_live_proof.v1",
            "decision": "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings",
            "source_reports": {},
            "committed_default_posture": {
                "sec_live_network_default_enabled": False,
                "arelle_fact_authority_cutover_default_enabled": False,
                "arelle_value_reveal_default_enabled": False,
            },
            "redaction_scan": {
                "raw_issuer_identity_found": False,
                "raw_accession_found": False,
                "raw_sec_url_found": False,
                "raw_local_path_found": False,
                "raw_value_record_collection_found": False,
            },
            "non_admissions_preserved": {
                "default_on_value_reveal_claimed": False,
                "production_readiness_claimed": False,
                "final_financial_statement_semantics_claimed": False,
                "cross_company_comparability_claimed": False,
            },
        },
    )
    _write_json(
        paths["admission_review"],
        {
            "schema_id": "diagnostics.sec_xbrl_default_on_admission_review.v1",
            "decision": (
                "admission_review_superseded_by_default_on_runtime"
                if runtime_default_on
                else "admission_review_requires_post_1966_governance_followup"
            ),
            "ready_for_default_on_runtime_slice": False,
            "source_reports": {},
        },
    )
    _write_json(
        paths["runtime_default"],
        {
            "schema_id": "diagnostics.sec_xbrl_default_on_runtime.v1",
            "decision": (
                "default_on_runtime_enabled"
                if runtime_default_on
                else "default_on_runtime_disabled_by_governance_remediation"
            ),
            "source_reports": {},
            "runtime_posture": {
                "default_cutover_enabled": runtime_default_on,
                "operator_value_reveal_default_enabled": False,
                "persisted_sidecar_required": True,
                "regex_rollback_env_supported": True,
                "synchronous_arelle_in_bridge": False,
            },
        },
    )
    _write_json(
        paths["default_posture"],
        {
            "schema_id": "diagnostics.sec_xbrl_default_posture_decision.v1",
            "decision": (
                "explicit_operator_only_default_off_superseded_by_default_on_runtime"
                if runtime_default_on
                else "explicit_operator_only_default_off_selected"
            ),
            "source_reports": {},
            "selected_posture": {
                "posture": "explicit_operator_only_default_off",
                "arelle_fact_authority_cutover_default_enabled": False,
                "arelle_fact_authority_cutover_default_on_supersedes_selected_posture": runtime_default_on,
                "arelle_value_reveal_default_enabled": False,
                "operator_value_reveal_available_only_by_explicit_gated_action": True,
                "broader_reliability_admission_converted_to_runtime_default": False,
            },
            "deferred_postures": {
                "default_on_value_reveal": "requires separate operator policy"
            },
            "non_goals_preserved": {"production_readiness_claimed": False},
        },
    )
    _write_json(
        paths["operator_runbook"],
        {
            "schema_id": "diagnostics.sec_xbrl_operator_runbook_matrix_selection.v1",
            "decision": "operator_runbook_and_stratified_matrix_selection_ready",
            "source_reports": {},
            "operator_policy": {
                "runtime_default_change_allowed": False,
                "value_reveal_requires_explicit_operator_confirmation": True,
                "raw_values_committed": False,
            },
            "non_goals_preserved": {
                "production_readiness_claimed": False,
                "source_acquisition_performed": False,
                "arelle_subprocess_invoked": False,
                "live_sec_network_run_performed": False,
            },
        },
    )


def _build_report(root: Path) -> dict[str, Any]:
    module = _restatement_module()
    return module.build_report(source_root=root, report_paths=_report_paths(root))


def _blocked_reasons(report: dict[str, Any]) -> set[str]:
    return {str(item["reason"]) for item in report["blocking_reasons"]}


def _criterion_by_name(report: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in report["criteria"] if item["criterion"] == name)


def test_sec_xbrl_default_on_admission_restatement_can_admit_runtime_design_from_current_authority(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_ready_for_runtime_design"
    assert report["ready_for_default_on_runtime_design"] is True
    assert report["blocking_reasons"] == []
    assert report["non_goals_preserved"]["runtime_default_on_enabled_by_restatement"] is False
    assert report["non_goals_preserved"]["source_acquisition_performed_by_restatement"] is False
    assert report["redaction"]["passed"] is True


def test_sec_xbrl_default_on_admission_restatement_is_superseded_after_runtime_default_on(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path, runtime_default_on=True)
    _write_valid_reports(tmp_path, runtime_default_on=True)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_superseded_by_default_on_runtime"
    assert report["ready_for_default_on_runtime_design"] is False
    assert report["superseded_by_default_on_runtime"] is True
    assert report["blocking_reasons"] == []
    assert report["conflicting_reasons"] == []
    assert report["restated_evidence"]["runtime_enablement"]["runtime_default_on_enabled"] is True
    assert report["non_goals_preserved"]["value_reveal_default_enabled_by_restatement"] is False
    assert report["next_slice"] == (
        "sec_xbrl_default_on_nonlocal_production_readiness_design_v1"
    )


def test_sec_xbrl_default_on_admission_restatement_fails_closed_when_required_report_missing(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    _report_paths(tmp_path)["historical_real_product_runner"].unlink()

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_required_report_missing_or_malformed" in _blocked_reasons(report)
    assert "default_on_admission_restatement_stale_or_missing_source_report_reference" in _blocked_reasons(report)
    assert report["ready_for_default_on_runtime_design"] is False


def test_sec_xbrl_default_on_admission_restatement_preserves_runtime_default_off(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path, runtime_default_on=True)
    _write_valid_reports(tmp_path)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_runtime_default_posture_regressed" in _blocked_reasons(report)


def test_sec_xbrl_default_on_admission_restatement_blocks_raw_source_report_residual(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    real_path = _report_paths(tmp_path)["historical_real_product_runner"]
    real = json.loads(real_path.read_text(encoding="utf-8"))
    real["debug_raw_accession"] = "0000000000-26-000001"
    _write_json(real_path, real)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_source_report_redaction_failed" in _blocked_reasons(report)
    assert report["criteria"][-2]["evidence"]["raw_accession_found"] is True


def test_sec_xbrl_default_on_admission_restatement_rejects_source_report_refs_outside_repo(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    outside_report = tmp_path.parent / "outside-source-report.json"
    _write_json(outside_report, {"schema_id": "outside.v1"})
    broader_path = _report_paths(tmp_path)["broader_reliability"]
    broader = json.loads(broader_path.read_text(encoding="utf-8"))
    broader["source_reports"] = {
        "absolute": str(outside_report),
        "parent": "../outside-source-report.json",
    }
    _write_json(broader_path, broader)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_stale_or_missing_source_report_reference" in _blocked_reasons(report)
    refs = _criterion_by_name(report, "required_source_report_references_current")["evidence"]["references"]
    assert {item["status"] for item in refs} == {"outside_repo"}


def test_sec_xbrl_default_on_admission_restatement_blocks_malformed_source_report_ref(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    broader_path = _report_paths(tmp_path)["broader_reliability"]
    broader = json.loads(broader_path.read_text(encoding="utf-8"))
    broader["source_reports"] = {"malformed": "bad\u0000.json"}
    _write_json(broader_path, broader)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_stale_or_missing_source_report_reference" in _blocked_reasons(report)
    refs = _criterion_by_name(report, "required_source_report_references_current")["evidence"]["references"]
    assert refs[0]["status"] == "malformed_path"


def test_sec_xbrl_default_on_admission_restatement_detects_common_local_paths_and_unpadded_cik(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    real_path = _report_paths(tmp_path)["historical_real_product_runner"]
    real = json.loads(real_path.read_text(encoding="utf-8"))
    real["debug_path"] = "/workspace/raw"
    real["debug_tmp_path"] = "/tmp/raw"
    real["raw_cik"] = 320193
    _write_json(real_path, real)

    report = _build_report(tmp_path)
    evidence = _criterion_by_name(report, "source_reports_redaction_clean")["evidence"]

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_source_report_redaction_failed" in _blocked_reasons(report)
    assert evidence["raw_local_path_found"] is True
    assert evidence["raw_cik_found"] is True


def test_sec_xbrl_default_on_admission_restatement_fails_closed_on_non_numeric_match_rate(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    gate_path = _report_paths(tmp_path)["default_on_gate"]
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["summary"]["companyfacts_value_match_rate"] = "n/a"
    _write_json(gate_path, gate)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_companyfacts_value_correctness_not_reproven" in _blocked_reasons(report)


def test_sec_xbrl_default_on_admission_restatement_scans_malformed_report_text_for_redaction(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    real_path = _report_paths(tmp_path)["historical_real_product_runner"]
    real_path.write_text('{"raw_cik": 320193, "path": "/tmp/raw", ', encoding="utf-8")

    report = _build_report(tmp_path)
    evidence = _criterion_by_name(report, "source_reports_redaction_clean")["evidence"]

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_required_report_missing_or_malformed" in _blocked_reasons(report)
    assert "default_on_admission_restatement_source_report_redaction_failed" in _blocked_reasons(report)
    assert evidence["raw_local_path_found"] is True
    assert evidence["raw_cik_found"] is True


def test_sec_xbrl_default_on_admission_restatement_preserves_value_reveal_default_off(
    tmp_path: Path,
) -> None:
    _write_source_tree(tmp_path)
    _write_valid_reports(tmp_path)
    posture_path = _report_paths(tmp_path)["default_posture"]
    posture = json.loads(posture_path.read_text(encoding="utf-8"))
    posture["selected_posture"]["arelle_value_reveal_default_enabled"] = True
    _write_json(posture_path, posture)

    report = _build_report(tmp_path)

    assert report["decision"] == "default_on_admission_restatement_still_blocked"
    assert "default_on_admission_restatement_value_reveal_default_posture_regressed" in _blocked_reasons(report)
