from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-stratified-matrix-readiness-decision.py"


def _load_decision():
    spec = importlib.util.spec_from_file_location("sec_xbrl_stratified_matrix_readiness_decision", DECISION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_stratified_matrix_readiness_selects_explicit_operator_default_off(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_selected"
    assert report["blocking_reasons"] == []
    assert report["selected_readiness"]["posture"] == "explicit_operator_default_off_broader_use"
    assert report["selected_readiness"]["default_on_arelle_cutover_admitted"] is False
    assert report["selected_readiness"]["default_on_value_reveal_admitted"] is False
    assert report["next_slice"] == "sec_edgar_explicit_operator_default_off_runbook_refresh_v1"
    assert all(item["state"] == "passed" for item in report["criteria"])


def test_sec_xbrl_stratified_matrix_readiness_accepts_superseded_default_on_runtime_posture(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(
        tmp_path,
        fact_authority_default_on=True,
        default_posture=_default_posture_report(superseded=True),
    )

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_selected"
    assert report["blocking_reasons"] == []
    assert report["criteria"][0]["evidence"]["config_defaults_off"] is False
    assert report["criteria"][0]["evidence"]["config_safety_defaults_off"] is True
    assert report["criteria"][0]["evidence"]["superseded_by_default_on_runtime"] is True
    assert report["selected_readiness"]["default_on_value_reveal_admitted"] is False
    assert report["non_goals_preserved"]["runtime_default_changed_by_decision"] is False


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_stratum_missing(tmp_path: Path) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
    matrix["summary"]["strata_readiness"]["ready_strata"] = matrix["summary"]["strata_readiness"]["ready_strata"][:-1]
    matrix["summary"]["strata_readiness"]["missing_strata"] = ["no_inline_or_zero_fact_diagnostic"]
    matrix["summary"]["strata_readiness"]["all_required_strata_ready"] = False
    paths["matrix"].write_text(json.dumps(matrix), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_required_forms_or_strata_not_ready"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_required_form_has_zero_count(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
    matrix["summary"]["forms"]["20-F"] = 0
    paths["matrix"].write_text(json.dumps(matrix), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_required_forms_or_strata_not_ready"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_default_action_applied(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
    matrix["runtime_default_posture"]["runner_default_decision_applied_to_config"] = True
    paths["matrix"].write_text(json.dumps(matrix), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_default_on_boundary_regressed"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_value_reveal_regresses(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    value_reveal = json.loads(paths["value_reveal"].read_text(encoding="utf-8"))
    value_reveal["attempts"][0]["operator_reveal"]["flag_off_status_blocked_reason"] = "wrong_reason"
    paths["value_reveal"].write_text(json.dumps(value_reveal), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_value_reveal_authority_not_proven"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_value_reveal_defaults_turn_on(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    value_reveal = json.loads(paths["value_reveal"].read_text(encoding="utf-8"))
    value_reveal["committed_default_posture"]["arelle_value_reveal_default_enabled"] = True
    paths["value_reveal"].write_text(json.dumps(value_reveal), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_value_reveal_authority_not_proven"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_chunk_counts_regress(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
    matrix["summary"]["ready_matrix_chunk_count"] = 5
    matrix["summary"]["blocked_matrix_chunk_count"] = 1
    paths["matrix"].write_text(json.dumps(matrix), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_live_product_gate_not_ready"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_readiness_blocks_when_value_reveal_non_admission_regresses(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    value_reveal = json.loads(paths["value_reveal"].read_text(encoding="utf-8"))
    value_reveal["non_admissions_preserved"]["candidate_b_sec_routing_performed"] = True
    paths["value_reveal"].write_text(json.dumps(value_reveal), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        matrix_live_report_path=paths["matrix"],
        default_posture_report_path=paths["default_posture"],
        value_reveal_live_proof_report_path=paths["value_reveal"],
    )

    assert report["decision"] == "explicit_operator_default_off_readiness_blocked"
    assert any(
        item["reason"] == "stratified_matrix_readiness_redaction_or_non_admission_regressed"
        for item in report["blocking_reasons"]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    fact_authority_default_on: bool = False,
    value_reveal_default_on: bool = False,
    default_posture: dict | None = None,
) -> dict[str, Path]:
    source_root = tmp_path / "source"
    config_path = source_root / "backend" / "app" / "core" / "config.py"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        _config_text(
            fact_authority_default_on=fact_authority_default_on,
            value_reveal_default_on=value_reveal_default_on,
        ),
        encoding="utf-8",
    )
    return {
        "source_root": source_root,
        "matrix": _write_json(tmp_path / "matrix.json", _matrix_live_report()),
        "default_posture": _write_json(
            tmp_path / "default-posture.json",
            default_posture or _default_posture_report(),
        ),
        "value_reveal": _write_json(tmp_path / "value-reveal.json", _value_reveal_report()),
    }


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _config_text(*, fact_authority_default_on: bool = False, value_reveal_default_on: bool = False) -> str:
    fact_authority_default = "True" if fact_authority_default_on else "False"
    value_reveal_default = "True" if value_reveal_default_on else "False"
    return f'''
class Settings:
    layer3_sec_edgar_live_network_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    )
    layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(
        default={fact_authority_default},
        alias="LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED",
    )
    layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(
        default={value_reveal_default},
        alias="LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    )
'''


def _matrix_live_report() -> dict:
    required_strata = [
        "large_domestic_us_gaap",
        "small_mid_domestic_us_gaap",
        "foreign_private_ifrs_20f",
        "canadian_40f",
        "current_report_8k_sparse",
        "foreign_6k_sparse",
        "amendment_restatement",
        "no_inline_or_zero_fact_diagnostic",
    ]
    return {
        "decision": "stratified_matrix_live_execution_ready",
        "matrix_execution_plan": {
            "mode": "external_stratified_matrix_plan",
            "state": "passed",
            "off_repo_plan_used": True,
            "raw_identity_redacted": True,
            "missing_required_strata": [],
            "covered_strata": required_strata,
        },
        "product_runner": {
            "decision": "real_corpus_default_on_validated",
            "gate_verdict": "PASS",
            "live_sec_network_used": True,
            "blocking_reasons": [],
        },
        "summary": {
            "matrix_chunk_count": 6,
            "ready_matrix_chunk_count": 6,
            "blocked_matrix_chunk_count": 0,
            "real_filing_count": 32,
            "issuer_hash_count": 16,
            "supported_record_count": 30,
            "forms": {"10-K": 13, "10-Q": 4, "20-F": 1, "40-F": 1, "6-K": 2, "8-K": 10},
            "required_forms_present": True,
            "records_with_arelle_sidecar_output": 30,
            "records_with_selected_fact_authority_equal_to_sidecar": 30,
            "records_with_handoff_export_prepare": 30,
            "completeness_guard_failed_count": 0,
            "unexpected_zero_inline_xbrl_count": 0,
            "unexpected_blocked_or_degraded_count": 0,
            "companyfacts_value_match_rate": 0.9897,
            "companyfacts_oracle_unavailable_count": 0,
            "strata_readiness": {
                "all_required_strata_ready": True,
                "ready_strata": required_strata,
                "missing_strata": [],
                "blocked_strata": [],
                "unknown_strata": [],
            },
        },
        "runtime_default_posture": {
            "committed_defaults_remain_off": True,
            "runner_default_decision_action": "set_default_true",
            "runner_default_decision_applied_to_config": False,
            "default_on_not_claimed_or_applied_by_this_report": True,
            "selected_operating_posture": "explicit_operator_only_default_off",
        },
        "redaction": {
            "identity_hash_only": True,
            "raw_accessions_committed": False,
            "raw_sec_urls_committed": False,
            "raw_tickers_committed": False,
            "raw_values_committed": False,
            "local_storage_roots_committed": False,
            "local_paths_committed": False,
            "operator_contact_committed": False,
            "raw_runtime_artifacts_committed": False,
            "raw_operator_plan_committed": False,
            "redaction_scan_passed": True,
        },
        "non_goals_preserved": {
            "runtime_default_changed": False,
            "default_on_arelle_cutover_enabled": False,
            "default_on_value_reveal_enabled": False,
            "raw_issuer_identity_committed": False,
            "raw_values_committed": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "candidate_b_sec_routing_performed": False,
        },
    }


def _default_posture_report(*, superseded: bool = False) -> dict:
    return {
        "decision": (
            "explicit_operator_only_default_off_superseded_by_default_on_runtime"
            if superseded
            else "explicit_operator_only_default_off_selected"
        ),
        "selected_posture": {
            "posture": "explicit_operator_only_default_off",
            "sec_live_network_default_enabled": False,
            "arelle_fact_authority_cutover_default_enabled": False,
            "arelle_fact_authority_cutover_default_on_supersedes_selected_posture": superseded,
            "arelle_value_reveal_default_enabled": False,
            "broader_reliability_admission_converted_to_runtime_default": False,
        },
    }


def _value_reveal_report() -> dict:
    return {
        "decision": "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings",
        "committed_default_posture": {
            "sec_live_network_default_enabled": False,
            "arelle_fact_authority_cutover_default_enabled": False,
            "arelle_value_reveal_default_enabled": False,
        },
        "attempts": [_attempt("10-K"), _attempt("10-Q")],
        "redaction_scan": {
            "reportable_bundle_refs_and_reveal_receipts_scanned": True,
            "raw_issuer_identity_found": False,
            "raw_accession_found": False,
            "raw_sec_url_found": False,
            "raw_local_path_found": False,
            "raw_contact_found": False,
            "raw_value_record_collection_found": False,
        },
        "non_admissions_preserved": {
            "default_on_arelle_cutover_claimed": False,
            "default_on_value_reveal_claimed": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "candidate_b_sec_routing_performed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
        },
    }


def _attempt(form: str) -> dict:
    return {
        "selected_filing": {
            "form": form,
            "issuer_identity_redacted": True,
            "accession_redacted": True,
            "sec_url_redacted": True,
        },
        "authority_bundle": {
            "coherent_bundle_count": 1,
            "runtime_dataset_and_provenance_bound": True,
        },
        "operator_reveal": {
            "reveal_state": "ready",
            "revealed_fact_count": 10,
            "idempotent_replay_same_receipt_id": True,
            "idempotent_replay_same_receipt_hash": True,
            "idempotent_replay_no_second_receipt": True,
            "status_projection_raw_values_returned": False,
            "status_projection_revealed_fact_count": 0,
            "flag_off_reveal_blocked_reason": "sec_edgar_arelle_value_reveal_feature_flag_disabled",
            "flag_off_status_blocked_reason": "sec_edgar_arelle_value_reveal_feature_flag_disabled",
        },
        "audit_receipt_redaction": {
            "receipt_present": True,
            "effective_field_present": False,
            "value_record_collection_present": False,
            "raw_values_persisted": False,
            "raw_identity_persisted": False,
        },
    }
