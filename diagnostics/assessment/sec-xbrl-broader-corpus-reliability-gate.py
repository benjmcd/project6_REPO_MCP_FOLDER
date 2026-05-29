from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json")
DEFAULT_DEFAULT_ON_GATE_REPORT = Path("diagnostics/assessment/sec-xbrl-default-on-gate-report.json")
DEFAULT_PRODUCT_PATH_REPORT = Path("diagnostics/assessment/sec-xbrl-product-path-corpus-validation-report.json")
DEFAULT_REAL_PRODUCT_RUNNER_REPORT = Path("diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json")

REQUIRED_FORMS = {"10-K", "10-Q", "20-F", "40-F", "6-K", "8-K"}
MIN_REAL_FILINGS = 12
MIN_ISSUER_HASHES = 6
MIN_COMPANYFACTS_MATCH_RATE = 0.99
MIN_REAL_PRODUCT_FILINGS = 30
MIN_REAL_PRODUCT_ISSUER_HASHES = 15
MIN_REAL_PRODUCT_COMPANYFACTS_MATCH_RATE = 0.98


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL broader corpus reliability gate. This diagnostic reads committed redacted "
            "reports only; it does not acquire filings, run Arelle, mutate runtime, expose values, "
            "or infer product-path reliability from fake-client evidence."
        )
    )
    parser.add_argument("--default-on-gate-report", default=str(DEFAULT_DEFAULT_ON_GATE_REPORT))
    parser.add_argument("--product-path-report", default=str(DEFAULT_PRODUCT_PATH_REPORT))
    parser.add_argument("--real-product-runner-report", default=str(DEFAULT_REAL_PRODUCT_RUNNER_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        default_on_gate_report_path=_resolve_path(args.default_on_gate_report),
        product_path_report_path=_resolve_path(args.product_path_report),
        real_product_runner_report_path=_resolve_path(args.real_product_runner_report),
    )
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    default_on_gate_report_path: Path,
    product_path_report_path: Path,
    real_product_runner_report_path: Path,
) -> dict[str, Any]:
    default_on_gate = _read_json(default_on_gate_report_path)
    product_path = _read_json(product_path_report_path)
    real_product = _read_json(real_product_runner_report_path)

    gate_summary = dict(default_on_gate.get("summary") or {})
    product_corpus = dict(product_path.get("corpus") or {})
    product_proof = dict(product_path.get("proof") or {})
    product_redaction = dict(product_path.get("redaction") or {})
    product_non_admissions = dict(product_path.get("non_admissions") or {})
    product_authority = dict(product_path.get("authority_model") or {})
    real_summary = dict(real_product.get("summary") or {})
    real_redaction = dict(real_product.get("redaction") or {})
    real_non_goals = dict(real_product.get("non_goals_preserved") or {})

    forms = set((gate_summary.get("forms") or {}).keys())
    product_forms = set(product_corpus.get("forms") or [])
    real_forms = set((real_summary.get("forms") or {}).keys())
    criteria = [
        _criterion(
            "inherited_real_extraction_value_gate",
            default_on_gate.get("decision") == "default_on_admitted_candidate"
            and _int(gate_summary.get("real_filing_count")) >= MIN_REAL_FILINGS
            and _int(gate_summary.get("issuer_hash_count")) >= MIN_ISSUER_HASHES
            and REQUIRED_FORMS.issubset(forms)
            and float(gate_summary.get("companyfacts_value_match_rate") or 0) >= MIN_COMPANYFACTS_MATCH_RATE,
            {
                "source_report": _repo_display_path(default_on_gate_report_path),
                "decision": default_on_gate.get("decision"),
                "real_filing_count": gate_summary.get("real_filing_count"),
                "issuer_hash_count": gate_summary.get("issuer_hash_count"),
                "forms": gate_summary.get("forms"),
                "required_forms": sorted(REQUIRED_FORMS),
                "arelle_resolved_fact_count": gate_summary.get("arelle_resolved_fact_count"),
                "bridge_fact_count": gate_summary.get("bridge_fact_count"),
                "value_bridge_fact_count": gate_summary.get("value_bridge_fact_count"),
                "companyfacts_value_match_rate": gate_summary.get("companyfacts_value_match_rate"),
            },
            "broader_reliability_inherited_real_extraction_gate_not_passed",
        ),
        _criterion(
            "focused_product_chain_smoke_proof",
            product_path.get("status") == "focused_runtime_proof_passed"
            and _int(product_proof.get("supported_records")) > 0
            and _int(product_proof.get("supported_records")) == _int(product_corpus.get("filing_count"))
            and product_proof.get("operator_inspection_ready") is True
            and product_proof.get("operator_product_surface_ready") is True
            and product_proof.get("durable_delivery_archive_ready") is True
            and product_authority.get("selected_fact_authority") == "arelle_resolved_fact_authority_sidecar_receipt"
            and product_authority.get("dataset_version_reused") is True
            and product_authority.get("new_layer3_source_shape_created") is False
            and REQUIRED_FORMS.issubset(product_forms),
            {
                "source_report": _repo_display_path(product_path_report_path),
                "status": product_path.get("status"),
                "filing_count": product_corpus.get("filing_count"),
                "forms": sorted(product_forms),
                "supported_records": product_proof.get("supported_records"),
                "selected_fact_authority": product_authority.get("selected_fact_authority"),
                "dataset_version_reused": product_authority.get("dataset_version_reused"),
                "new_layer3_source_shape_created": product_authority.get("new_layer3_source_shape_created"),
                "operator_inspection_ready": product_proof.get("operator_inspection_ready"),
                "operator_product_surface_ready": product_proof.get("operator_product_surface_ready"),
                "durable_delivery_archive_ready": product_proof.get("durable_delivery_archive_ready"),
            },
            "broader_reliability_focused_product_chain_smoke_missing",
        ),
        _criterion(
            "broader_real_product_path_corpus_proof",
            real_product.get("decision") == "real_corpus_default_on_validated"
            and real_product.get("gate_verdict") == "PASS"
            and real_product.get("fake_sec_client_used") is False
            and real_product.get("live_sec_network_used") is True
            and _int(real_summary.get("real_filing_count")) >= MIN_REAL_PRODUCT_FILINGS
            and _int(real_summary.get("issuer_hash_count")) >= MIN_REAL_PRODUCT_ISSUER_HASHES
            and REQUIRED_FORMS.issubset(real_forms)
            and _int(real_summary.get("supported_record_count")) >= MIN_REAL_PRODUCT_FILINGS
            and _int(real_summary.get("records_with_arelle_sidecar_output")) == _int(
                real_summary.get("supported_record_count")
            )
            and _int(real_summary.get("records_with_selected_fact_authority_equal_to_sidecar")) == _int(
                real_summary.get("supported_record_count")
            )
            and _int(real_summary.get("records_with_handoff_export_prepare")) == _int(
                real_summary.get("supported_record_count")
            )
            and _int(real_summary.get("matrix_chunk_count")) > 0
            and _int(real_summary.get("ready_matrix_chunk_count")) == _int(real_summary.get("matrix_chunk_count"))
            and _int(real_summary.get("independent_inline_fact_count")) > 0
            and _int(real_summary.get("resolved_fact_count")) > 0
            and _int(real_summary.get("resolved_fact_count")) >= _int(
                real_summary.get("independent_inline_fact_count")
            )
            and _int(real_summary.get("completeness_guard_failed_count")) == 0
            and _int(real_summary.get("unexpected_blocked_or_degraded_count")) == 0
            and _int(real_summary.get("companyfacts_value_compared_count")) > 0
            and float(real_summary.get("companyfacts_value_match_rate") or 0)
            >= MIN_REAL_PRODUCT_COMPANYFACTS_MATCH_RATE
            and real_summary.get("operator_surface_values_exposed") is False,
            {
                "source_report": _repo_display_path(real_product_runner_report_path),
                "decision": real_product.get("decision"),
                "gate_verdict": real_product.get("gate_verdict"),
                "required_real_filing_count": MIN_REAL_PRODUCT_FILINGS,
                "observed_real_filing_count": real_summary.get("real_filing_count"),
                "required_issuer_hash_count": MIN_REAL_PRODUCT_ISSUER_HASHES,
                "observed_issuer_hash_count": real_summary.get("issuer_hash_count"),
                "fake_sec_client_used": real_product.get("fake_sec_client_used"),
                "live_sec_network_used": real_product.get("live_sec_network_used"),
                "forms": sorted(real_forms),
                "required_forms": sorted(REQUIRED_FORMS),
                "required_supported_record_count": MIN_REAL_PRODUCT_FILINGS,
                "supported_record_count": real_summary.get("supported_record_count"),
                "records_with_arelle_sidecar_output": real_summary.get("records_with_arelle_sidecar_output"),
                "records_with_selected_fact_authority_equal_to_sidecar": real_summary.get(
                    "records_with_selected_fact_authority_equal_to_sidecar"
                ),
                "records_with_handoff_export_prepare": real_summary.get("records_with_handoff_export_prepare"),
                "ready_matrix_chunk_count": real_summary.get("ready_matrix_chunk_count"),
                "matrix_chunk_count": real_summary.get("matrix_chunk_count"),
                "resolved_fact_count": real_summary.get("resolved_fact_count"),
                "independent_inline_fact_count": real_summary.get("independent_inline_fact_count"),
                "companyfacts_value_compared_count": real_summary.get("companyfacts_value_compared_count"),
                "companyfacts_value_match_rate": real_summary.get("companyfacts_value_match_rate"),
                "minimum_companyfacts_value_match_rate": MIN_REAL_PRODUCT_COMPANYFACTS_MATCH_RATE,
                "unexpected_blocked_or_degraded_count": real_summary.get("unexpected_blocked_or_degraded_count"),
                "evidence_grade": "current-main_live_real_product_runner",
            },
            "broader_reliability_real_product_path_corpus_absent",
        ),
        _criterion(
            "product_path_redaction_and_non_admissions",
            product_redaction.get("effective_values_exposed_in_validation_delivery_operator_surface_archive") is False
            and product_redaction.get("raw_sec_urls_exposed") is False
            and product_redaction.get("raw_company_names_exposed") is False
            and product_corpus.get("real_identity_values_redacted_in_outputs") is True
            and product_redaction.get("local_storage_roots_exposed") is False
            and product_proof.get("operator_surface_values_exposed") is False
            and product_non_admissions.get("final_financial_statement_semantics_claimed") is False
            and product_non_admissions.get("cross_company_comparability_admitted") is False
            and product_non_admissions.get("candidate_b_sec_routing_performed") is False
            and product_non_admissions.get("rag_model_provider_auth_added") is False
            and real_redaction.get("identity_hash_only") is True
            and real_redaction.get("raw_accessions_committed") is False
            and real_redaction.get("raw_sec_urls_committed") is False
            and real_redaction.get("raw_tickers_committed") is False
            and real_redaction.get("raw_values_committed") is False
            and real_redaction.get("local_storage_roots_committed") is False
            and real_non_goals.get("operator_value_reveal_enabled") is False
            and real_non_goals.get("final_financial_statement_semantics_claimed") is False
            and real_non_goals.get("cross_company_comparability_claimed") is False
            and real_non_goals.get("candidate_b_sec_routing_performed") is False
            and real_non_goals.get("rag_vector_model_provider_auth_behavior_added") is False,
            {
                "effective_values_exposed": product_redaction.get(
                    "effective_values_exposed_in_validation_delivery_operator_surface_archive"
                ),
                "raw_sec_urls_exposed": product_redaction.get("raw_sec_urls_exposed"),
                "raw_company_names_exposed": product_redaction.get("raw_company_names_exposed"),
                "real_identity_values_redacted_in_outputs": product_corpus.get(
                    "real_identity_values_redacted_in_outputs"
                ),
                "local_storage_roots_exposed": product_redaction.get("local_storage_roots_exposed"),
                "operator_surface_values_exposed": product_proof.get("operator_surface_values_exposed"),
                "final_financial_statement_semantics_claimed": product_non_admissions.get(
                    "final_financial_statement_semantics_claimed"
                ),
                "cross_company_comparability_admitted": product_non_admissions.get(
                    "cross_company_comparability_admitted"
                ),
                "candidate_b_sec_routing_performed": product_non_admissions.get(
                    "candidate_b_sec_routing_performed"
                ),
                "rag_model_provider_auth_added": product_non_admissions.get("rag_model_provider_auth_added"),
                "real_product_identity_hash_only": real_redaction.get("identity_hash_only"),
                "real_product_raw_accessions_committed": real_redaction.get("raw_accessions_committed"),
                "real_product_raw_sec_urls_committed": real_redaction.get("raw_sec_urls_committed"),
                "real_product_raw_tickers_committed": real_redaction.get("raw_tickers_committed"),
                "real_product_raw_values_committed": real_redaction.get("raw_values_committed"),
                "real_product_local_storage_roots_committed": real_redaction.get("local_storage_roots_committed"),
                "real_product_operator_value_reveal_enabled": real_non_goals.get("operator_value_reveal_enabled"),
                "real_product_final_financial_statement_semantics_claimed": real_non_goals.get(
                    "final_financial_statement_semantics_claimed"
                ),
                "real_product_cross_company_comparability_claimed": real_non_goals.get(
                    "cross_company_comparability_claimed"
                ),
                "real_product_candidate_b_sec_routing_performed": real_non_goals.get(
                    "candidate_b_sec_routing_performed"
                ),
                "real_product_rag_vector_model_provider_auth_behavior_added": real_non_goals.get(
                    "rag_vector_model_provider_auth_behavior_added"
                ),
            },
            "broader_reliability_redaction_or_non_admission_regressed",
        ),
    ]
    blockers = [
        {"reason": item["blocked_reason"], "criterion": item["criterion"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    admitted = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_broader_corpus_reliability_gate.v1",
        "target": "sec_edgar_default_on_broader_corpus_reliability_gate_v1",
        "decision": "broader_corpus_reliability_admitted" if admitted else "broader_corpus_reliability_blocked",
        "headline": _headline(admitted=admitted, blockers=blockers),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "source_reports": {
            "default_on_gate": _repo_display_path(default_on_gate_report_path),
            "product_path": _repo_display_path(product_path_report_path),
            "real_product_runner": _repo_display_path(real_product_runner_report_path),
        },
        "summary": {
            "inherited_real_filing_count": gate_summary.get("real_filing_count"),
            "inherited_issuer_hash_count": gate_summary.get("issuer_hash_count"),
            "inherited_forms": gate_summary.get("forms"),
            "inherited_arelle_resolved_fact_count": gate_summary.get("arelle_resolved_fact_count"),
            "inherited_companyfacts_value_match_rate": gate_summary.get("companyfacts_value_match_rate"),
            "focused_product_path_filing_count": product_corpus.get("filing_count"),
            "focused_product_path_fake_sec_client_used": product_corpus.get("fake_sec_client_used"),
            "focused_product_path_live_sec_network_used": product_corpus.get("live_sec_network_used"),
            "product_path_operator_surface_ready": product_proof.get("operator_product_surface_ready"),
            "real_product_path_filing_count": real_summary.get("real_filing_count"),
            "real_product_path_issuer_hash_count": real_summary.get("issuer_hash_count"),
            "real_product_path_forms": real_summary.get("forms"),
            "real_product_path_supported_record_count": real_summary.get("supported_record_count"),
            "real_product_path_companyfacts_value_match_rate": real_summary.get("companyfacts_value_match_rate"),
            "real_product_path_live_sec_network_used": real_product.get("live_sec_network_used"),
            "real_product_path_fake_sec_client_used": real_product.get("fake_sec_client_used"),
            "operator_value_reveal_default_enabled": False,
        },
        "non_goals_preserved": {
            "runtime_default_changed": False,
            "bridge_gate_b_product_package_ui_redesign_performed": False,
            "candidate_b_sec_routing_performed": False,
            "cross_company_comparability_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
            "raw_identity_urls_paths_storage_roots_committed": False,
            "value_unredaction_performed": False,
        },
        "next_slice": (
            "sec_edgar_arelle_default_posture_decision_v1"
            if admitted
            else "sec_edgar_real_corpus_product_path_runner_v1"
        ),
    }


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _headline(*, admitted: bool, blockers: list[dict[str, Any]]) -> str:
    if admitted:
        return "Broader real-corpus product-path reliability is admitted by current evidence."
    reasons = ", ".join(reason["reason"] for reason in blockers)
    return f"Broader real-corpus product-path reliability is blocked: {reasons}."


def _int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object at {_repo_display_path(path)}")
    return value


def _resolve_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return ROOT / path


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"redacted-path-marker:{path.name}"


if __name__ == "__main__":
    raise SystemExit(main())
