from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-broader-corpus-reliability-gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("sec_xbrl_broader_corpus_reliability_gate", GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_broader_corpus_gate_admits_real_product_runner(tmp_path: Path) -> None:
    gate = _load_gate()
    default_on_path, product_path, real_runner_path = _write_reports(tmp_path)

    report = gate.build_report(
        default_on_gate_report_path=default_on_path,
        product_path_report_path=product_path,
        real_product_runner_report_path=real_runner_path,
    )

    assert report["decision"] == "broader_corpus_reliability_admitted"
    assert report["blocking_reasons"] == []
    assert report["next_slice"] == "sec_edgar_arelle_default_posture_decision_v1"
    assert report["source_reports"]["real_product_runner"].endswith("real-product-runner.json")
    broader = next(item for item in report["criteria"] if item["criterion"] == "broader_real_product_path_corpus_proof")
    assert broader["state"] == "passed"
    assert broader["evidence"]["evidence_grade"] == "current-main_live_real_product_runner"


def test_sec_xbrl_broader_corpus_gate_blocks_without_live_real_product_runner(tmp_path: Path) -> None:
    gate = _load_gate()
    default_on_path, product_path, real_runner_path = _write_reports(tmp_path)
    real_runner = json.loads(real_runner_path.read_text(encoding="utf-8"))
    real_runner["decision"] = "real_corpus_default_on_blocked"
    real_runner["fake_sec_client_used"] = True
    real_runner_path.write_text(json.dumps(real_runner), encoding="utf-8")

    report = gate.build_report(
        default_on_gate_report_path=default_on_path,
        product_path_report_path=product_path,
        real_product_runner_report_path=real_runner_path,
    )

    assert report["decision"] == "broader_corpus_reliability_blocked"
    assert any(
        item["reason"] == "broader_reliability_real_product_path_corpus_absent"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_broader_corpus_gate_blocks_metadata_only_real_runner(tmp_path: Path) -> None:
    gate = _load_gate()
    default_on_path, product_path, real_runner_path = _write_reports(tmp_path)
    real_runner = json.loads(real_runner_path.read_text(encoding="utf-8"))
    real_runner["summary"].update(
        {
            "supported_record_count": 0,
            "records_with_arelle_sidecar_output": 0,
            "records_with_selected_fact_authority_equal_to_sidecar": 0,
            "records_with_handoff_export_prepare": 0,
            "matrix_chunk_count": 0,
            "ready_matrix_chunk_count": 0,
            "resolved_fact_count": 0,
            "independent_inline_fact_count": 0,
            "companyfacts_value_compared_count": 0,
        }
    )
    real_runner_path.write_text(json.dumps(real_runner), encoding="utf-8")

    report = gate.build_report(
        default_on_gate_report_path=default_on_path,
        product_path_report_path=product_path,
        real_product_runner_report_path=real_runner_path,
    )

    assert report["decision"] == "broader_corpus_reliability_blocked"
    broader = next(item for item in report["criteria"] if item["criterion"] == "broader_real_product_path_corpus_proof")
    assert broader["state"] == "blocked"


def _write_reports(tmp_path: Path) -> tuple[Path, Path, Path]:
    default_on_path = tmp_path / "default-on.json"
    product_path = tmp_path / "product-path.json"
    real_runner_path = tmp_path / "real-product-runner.json"
    default_on_path.write_text(json.dumps(_default_on_gate_report()), encoding="utf-8")
    product_path.write_text(json.dumps(_focused_product_path_report()), encoding="utf-8")
    real_runner_path.write_text(json.dumps(_real_product_runner_report()), encoding="utf-8")
    return default_on_path, product_path, real_runner_path


def _default_on_gate_report() -> dict:
    return {
        "decision": "default_on_admitted_candidate",
        "summary": {
            "real_filing_count": 12,
            "issuer_hash_count": 6,
            "forms": {"10-K": 4, "10-Q": 1, "20-F": 1, "40-F": 1, "6-K": 2, "8-K": 3},
            "arelle_resolved_fact_count": 18156,
            "bridge_fact_count": 18156,
            "value_bridge_fact_count": 23102,
            "companyfacts_value_match_rate": 0.9923,
        },
    }


def _focused_product_path_report() -> dict:
    return {
        "status": "focused_runtime_proof_passed",
        "corpus": {
            "filing_count": 8,
            "forms": ["10-K", "10-Q", "20-F", "40-F", "6-K", "8-K"],
            "fake_sec_client_used": True,
            "live_sec_network_used": False,
            "real_identity_values_redacted_in_outputs": True,
        },
        "proof": {
            "supported_records": 8,
            "operator_inspection_ready": True,
            "operator_product_surface_ready": True,
            "durable_delivery_archive_ready": True,
            "operator_surface_values_exposed": False,
        },
        "redaction": {
            "effective_values_exposed_in_validation_delivery_operator_surface_archive": False,
            "raw_sec_urls_exposed": False,
            "raw_company_names_exposed": False,
            "local_storage_roots_exposed": False,
        },
        "non_admissions": {
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_admitted": False,
            "candidate_b_sec_routing_performed": False,
            "rag_model_provider_auth_added": False,
        },
        "authority_model": {
            "selected_fact_authority": "arelle_resolved_fact_authority_sidecar_receipt",
            "dataset_version_reused": True,
            "new_layer3_source_shape_created": False,
        },
    }


def _real_product_runner_report() -> dict:
    return {
        "decision": "real_corpus_default_on_validated",
        "gate_verdict": "PASS",
        "fake_sec_client_used": False,
        "live_sec_network_used": True,
        "summary": {
            "real_filing_count": 32,
            "issuer_hash_count": 16,
            "forms": {"10-K": 13, "10-K/A": 1, "10-Q": 4, "20-F": 1, "40-F": 1, "6-K": 2, "8-K": 10},
            "supported_record_count": 30,
            "records_with_arelle_sidecar_output": 30,
            "records_with_selected_fact_authority_equal_to_sidecar": 30,
            "records_with_handoff_export_prepare": 30,
            "ready_matrix_chunk_count": 4,
            "matrix_chunk_count": 4,
            "resolved_fact_count": 52558,
            "independent_inline_fact_count": 52558,
            "completeness_guard_failed_count": 0,
            "unexpected_blocked_or_degraded_count": 0,
            "companyfacts_value_compared_count": 9131,
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
            "rag_vector_model_provider_auth_behavior_added": False,
        },
    }
