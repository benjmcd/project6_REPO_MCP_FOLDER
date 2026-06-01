from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-default-posture-decision.py"


def _load_decision():
    spec = importlib.util.spec_from_file_location("sec_xbrl_default_posture_decision", DECISION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_default_posture_selects_explicit_operator_only_default_off(tmp_path: Path) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)

    report = decision.build_report(
        source_root=paths["source_root"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
        runtime_report_path=paths["runtime"],
        admission_review_report_path=paths["admission"],
    )

    assert report["decision"] == "explicit_operator_only_default_off_selected"
    assert report["blocking_reasons"] == []
    assert report["selected_posture"]["posture"] == "explicit_operator_only_default_off"
    assert report["selected_posture"]["broader_reliability_admission_converted_to_runtime_default"] is False
    assert report["next_slice"] == "sec_edgar_operator_readiness_runbook_and_stratified_matrix_selection_v1"
    assert all(item["state"] == "passed" for item in report["criteria"])


def test_sec_xbrl_default_posture_marks_pre_runtime_posture_superseded_after_runtime_default_on(
    tmp_path: Path,
) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path, config_defaults_off=False, value_reveal_default_off=True, runtime_default_on=True)

    report = decision.build_report(
        source_root=paths["source_root"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
        runtime_report_path=paths["runtime"],
        admission_review_report_path=paths["admission"],
    )

    assert report["decision"] == "explicit_operator_only_default_off_superseded_by_default_on_runtime"
    assert report["blocking_reasons"] == []
    assert report["selected_posture"]["posture"] == "explicit_operator_only_default_off"
    assert report["selected_posture"]["arelle_fact_authority_cutover_default_on_supersedes_selected_posture"] is True
    assert report["selected_posture"]["arelle_value_reveal_default_enabled"] is False
    assert report["non_goals_preserved"]["runtime_default_enabled_by_follow_on_runtime_slice"] is True
    assert report["next_slice"] == (
        "sec_xbrl_default_on_nonlocal_production_readiness_design_v1"
    )


def test_sec_xbrl_default_posture_blocks_when_committed_defaults_are_not_off(tmp_path: Path) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path, config_defaults_off=False)

    report = decision.build_report(
        source_root=paths["source_root"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
        runtime_report_path=paths["runtime"],
        admission_review_report_path=paths["admission"],
    )

    assert report["decision"] == "default_posture_decision_blocked"
    assert any(
        item["reason"] == "default_posture_committed_defaults_not_off"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_default_posture_blocks_when_flag_off_reveal_is_not_proven(tmp_path: Path) -> None:
    decision = _load_decision()
    paths = _write_inputs(tmp_path)
    live_proof = json.loads(paths["live_proof"].read_text(encoding="utf-8"))
    live_proof["attempts"][0]["operator_reveal"]["flag_off_reveal_blocked_reason"] = "wrong_reason"
    paths["live_proof"].write_text(json.dumps(live_proof), encoding="utf-8")

    report = decision.build_report(
        source_root=paths["source_root"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
        runtime_report_path=paths["runtime"],
        admission_review_report_path=paths["admission"],
    )

    assert report["decision"] == "default_posture_decision_blocked"
    assert any(
        item["reason"] == "default_posture_bounded_value_reveal_not_proven"
        for item in report["blocking_reasons"]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    config_defaults_off: bool = True,
    value_reveal_default_off: bool | None = None,
    runtime_default_on: bool = False,
) -> dict[str, Path]:
    source_root = tmp_path / "source"
    config_path = source_root / "backend" / "app" / "core" / "config.py"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        _config_text(
            defaults_off=config_defaults_off,
            value_reveal_default_off=(
                config_defaults_off if value_reveal_default_off is None else value_reveal_default_off
            ),
        ),
        encoding="utf-8",
    )

    broader = _write_json(tmp_path / "broader.json", _broader_report())
    real_product = _write_json(tmp_path / "real-product.json", _real_product_report())
    live_proof = _write_json(tmp_path / "live-proof.json", _live_proof_report())
    runtime = _write_json(tmp_path / "runtime.json", _runtime_report(default_on=runtime_default_on))
    admission = _write_json(tmp_path / "admission.json", _admission_report(superseded=runtime_default_on))
    return {
        "source_root": source_root,
        "broader": broader,
        "real_product": real_product,
        "live_proof": live_proof,
        "runtime": runtime,
        "admission": admission,
    }


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _config_text(*, defaults_off: bool, value_reveal_default_off: bool) -> str:
    cutover_default = "False" if defaults_off else "True"
    reveal_default = "False" if value_reveal_default_off else "True"
    return f'''
class Settings:
    layer3_sec_edgar_live_network_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    )
    layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(
        default={cutover_default},
        alias="LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED",
    )
    layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(
        default={reveal_default},
        alias="LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    )
'''


def _broader_report() -> dict:
    return {
        "decision": "broader_corpus_reliability_admitted",
        "blocking_reasons": [],
        "next_slice": "sec_edgar_arelle_default_posture_decision_v1",
        "non_goals_preserved": {
            "raw_identity_urls_paths_storage_roots_committed": False,
            "value_unredaction_performed": False,
        },
    }


def _real_product_report() -> dict:
    return {
        "decision": "real_corpus_default_on_validated",
        "gate_verdict": "PASS",
        "fake_sec_client_used": False,
        "live_sec_network_used": True,
        "summary": {
            "real_filing_count": 32,
            "issuer_hash_count": 16,
            "supported_record_count": 30,
            "records_with_arelle_sidecar_output": 30,
            "records_with_selected_fact_authority_equal_to_sidecar": 30,
            "records_with_handoff_export_prepare": 30,
            "resolved_fact_count": 52558,
            "independent_inline_fact_count": 52558,
            "companyfacts_value_match_rate": 0.99,
            "operator_surface_values_exposed": False,
        },
        "redaction": {
            "identity_hash_only": True,
            "raw_accessions_committed": False,
            "raw_sec_urls_committed": False,
            "raw_tickers_committed": False,
            "raw_values_committed": False,
            "local_storage_roots_committed": False,
        },
        "non_goals_preserved": {
            "operator_value_reveal_enabled": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "candidate_b_sec_routing_performed": False,
        },
    }


def _live_proof_report() -> dict:
    return {
        "decision": "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings",
        "committed_default_posture": {
            "sec_live_network_default_enabled": False,
            "arelle_fact_authority_cutover_default_enabled": False,
            "arelle_value_reveal_default_enabled": False,
        },
        "attempts": [_attempt("10-K", 643), _attempt("10-Q", 483)],
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
        },
    }


def _attempt(form: str, fact_count: int) -> dict:
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
            "revealed_fact_count": fact_count,
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


def _runtime_report(*, default_on: bool = False) -> dict:
    return {
        "decision": "default_on_runtime_enabled" if default_on else "default_on_runtime_disabled_by_governance_remediation",
        "runtime_posture": {
            "default_cutover_enabled": default_on,
            "operator_value_reveal_default_enabled": False,
        },
        "non_goals_preserved": {
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
    }


def _admission_report(*, superseded: bool = False) -> dict:
    return {
        "decision": (
            "admission_review_superseded_by_default_on_runtime"
            if superseded
            else "admission_review_requires_post_1966_governance_followup"
        ),
        "ready_for_default_on_runtime_slice": False,
    }
