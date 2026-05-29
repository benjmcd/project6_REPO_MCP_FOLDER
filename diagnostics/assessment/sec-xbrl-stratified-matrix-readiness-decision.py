from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-stratified-matrix-readiness-decision-report.json")
DEFAULT_MATRIX_LIVE_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-live-report.json"
)
DEFAULT_DEFAULT_POSTURE_REPORT = Path("diagnostics/assessment/sec-xbrl-default-posture-decision-report.json")
DEFAULT_VALUE_REVEAL_LIVE_PROOF_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json"
)

REQUIRED_FORMS = ("10-K", "10-Q", "20-F", "40-F", "6-K", "8-K")
REQUIRED_STRATA = (
    "large_domestic_us_gaap",
    "small_mid_domestic_us_gaap",
    "foreign_private_ifrs_20f",
    "canadian_40f",
    "current_report_8k_sparse",
    "foreign_6k_sparse",
    "amendment_restatement",
    "no_inline_or_zero_fact_diagnostic",
)
FEATURE_FLAG_DISABLED_REASON = "sec_edgar_arelle_value_reveal_feature_flag_disabled"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL stratified matrix readiness decision. This reads committed "
            "redacted reports and source defaults; it does not fetch SEC data, invoke Arelle, "
            "reveal values, or mutate runtime defaults."
        )
    )
    parser.add_argument("--matrix-live-report", default=str(DEFAULT_MATRIX_LIVE_REPORT))
    parser.add_argument("--default-posture-report", default=str(DEFAULT_DEFAULT_POSTURE_REPORT))
    parser.add_argument("--value-reveal-live-proof-report", default=str(DEFAULT_VALUE_REVEAL_LIVE_PROOF_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        source_root=ROOT,
        matrix_live_report_path=_resolve_path(args.matrix_live_report),
        default_posture_report_path=_resolve_path(args.default_posture_report),
        value_reveal_live_proof_report_path=_resolve_path(args.value_reveal_live_proof_report),
    )
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    source_root: Path,
    matrix_live_report_path: Path,
    default_posture_report_path: Path,
    value_reveal_live_proof_report_path: Path,
) -> dict[str, Any]:
    config_text = (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    matrix = _read_json(matrix_live_report_path)
    default_posture = _read_json(default_posture_report_path)
    value_reveal = _read_json(value_reveal_live_proof_report_path)

    matrix_summary = dict(matrix.get("summary") or {})
    matrix_plan = dict(matrix.get("matrix_execution_plan") or {})
    matrix_redaction = dict(matrix.get("redaction") or {})
    matrix_defaults = dict(matrix.get("runtime_default_posture") or {})
    matrix_non_goals = dict(matrix.get("non_goals_preserved") or {})
    selected_posture = dict(default_posture.get("selected_posture") or {})
    value_attempts = value_reveal.get("attempts") if isinstance(value_reveal.get("attempts"), list) else []

    config_defaults_off = _config_defaults_off(config_text)
    default_posture_selected = (
        default_posture.get("decision") == "explicit_operator_only_default_off_selected"
        and selected_posture.get("posture") == "explicit_operator_only_default_off"
        and selected_posture.get("sec_live_network_default_enabled") is False
        and selected_posture.get("arelle_fact_authority_cutover_default_enabled") is False
        and selected_posture.get("arelle_value_reveal_default_enabled") is False
        and selected_posture.get("broader_reliability_admission_converted_to_runtime_default") is False
    )
    matrix_product_ready = _matrix_product_ready(matrix=matrix, summary=matrix_summary)
    matrix_strata_ready = _matrix_strata_ready(matrix_plan=matrix_plan, summary=matrix_summary)
    matrix_default_boundary = (
        matrix_defaults.get("committed_defaults_remain_off") is True
        and matrix_defaults.get("runner_default_decision_applied_to_config") is False
        and matrix_defaults.get("default_on_not_claimed_or_applied_by_this_report") is True
        and matrix_defaults.get("selected_operating_posture") == "explicit_operator_only_default_off"
    )
    value_reveal_still_ready = (
        value_reveal.get("decision")
        == "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings"
        and len(value_attempts) >= 2
        and all(_attempt_proves_gated_reveal(attempt) for attempt in value_attempts)
    )
    redaction_and_non_goals = (
        _matrix_redaction_ok(matrix_redaction)
        and _matrix_non_goals_ok(matrix_non_goals)
        and _value_reveal_redaction_ok(value_reveal)
    )

    criteria = [
        _criterion(
            "committed_defaults_remain_off",
            config_defaults_off and default_posture_selected,
            {
                "config_file": "backend/app/core/config.py",
                "config_defaults_off": config_defaults_off,
                "default_posture_report": _repo_display_path(default_posture_report_path),
                "default_posture_decision": default_posture.get("decision"),
                "selected_posture": selected_posture.get("posture"),
            },
            "stratified_matrix_readiness_defaults_not_off",
        ),
        _criterion(
            "live_stratified_matrix_product_gate_passed",
            matrix_product_ready,
            {
                "source_report": _repo_display_path(matrix_live_report_path),
                "decision": matrix.get("decision"),
                "gate_verdict": (matrix.get("product_runner") or {}).get("gate_verdict"),
                "real_filing_count": matrix_summary.get("real_filing_count"),
                "issuer_hash_count": matrix_summary.get("issuer_hash_count"),
                "supported_record_count": matrix_summary.get("supported_record_count"),
                "companyfacts_value_match_rate": matrix_summary.get("companyfacts_value_match_rate"),
            },
            "stratified_matrix_live_product_gate_not_ready",
        ),
        _criterion(
            "required_forms_and_strata_ready",
            matrix_strata_ready,
            {
                "forms": matrix_summary.get("forms"),
                "required_forms": list(REQUIRED_FORMS),
                "matrix_plan_state": matrix_plan.get("state"),
                "matrix_plan_mode": matrix_plan.get("mode"),
                "covered_strata": matrix_plan.get("covered_strata"),
                "strata_readiness": matrix_summary.get("strata_readiness"),
            },
            "stratified_matrix_required_forms_or_strata_not_ready",
        ),
        _criterion(
            "default_on_boundary_not_admitted",
            matrix_default_boundary,
            {
                "runtime_default_posture": matrix_defaults,
                "diagnostic_runner_default_action": matrix_defaults.get("runner_default_decision_action"),
                "diagnostic_runner_default_action_applied": matrix_defaults.get(
                    "runner_default_decision_applied_to_config"
                ),
            },
            "stratified_matrix_default_on_boundary_regressed",
        ),
        _criterion(
            "governed_value_reveal_still_proven",
            value_reveal_still_ready,
            {
                "source_report": _repo_display_path(value_reveal_live_proof_report_path),
                "decision": value_reveal.get("decision"),
                "attempt_count": len(value_attempts),
            },
            "stratified_matrix_value_reveal_authority_not_proven",
        ),
        _criterion(
            "redaction_and_non_admissions_preserved",
            redaction_and_non_goals,
            {
                "matrix_redaction": matrix_redaction,
                "matrix_non_goals": matrix_non_goals,
                "value_reveal_redaction_scan": value_reveal.get("redaction_scan"),
                "value_reveal_non_admissions": value_reveal.get("non_admissions_preserved"),
            },
            "stratified_matrix_readiness_redaction_or_non_admission_regressed",
        ),
    ]
    blockers = [
        {"criterion": item["criterion"], "reason": item["blocked_reason"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    ready = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_stratified_matrix_readiness_decision.v1",
        "target": "sec_edgar_stratified_matrix_result_reconciliation_and_default_off_operator_readiness_decision_v1",
        "decision": (
            "explicit_operator_default_off_readiness_selected"
            if ready
            else "explicit_operator_default_off_readiness_blocked"
        ),
        "headline": _headline(ready=ready, blockers=blockers),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "selected_readiness": {
            "posture": "explicit_operator_default_off_broader_use" if ready else None,
            "operator_value_reveal_available_only_by_explicit_gated_action": ready,
            "stratified_matrix_live_evidence_admitted": ready,
            "default_on_arelle_cutover_admitted": False,
            "default_on_value_reveal_admitted": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "source_reports": {
            "matrix_live": _repo_display_path(matrix_live_report_path),
            "default_posture": _repo_display_path(default_posture_report_path),
            "value_reveal_live_proof": _repo_display_path(value_reveal_live_proof_report_path),
        },
        "matrix_summary": _public_matrix_summary(matrix_summary=matrix_summary, matrix_plan=matrix_plan),
        "next_slice": (
            "sec_edgar_explicit_operator_default_off_runbook_refresh_v1"
            if ready
            else "sec_edgar_stratified_matrix_result_reconciliation_and_remediation_v1"
        ),
        "non_goals_preserved": {
            "runtime_default_changed_by_decision": False,
            "live_sec_network_run_performed_by_decision": False,
            "arelle_subprocess_invoked_by_decision": False,
            "value_reveal_request_performed_by_decision": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "raw_runtime_artifacts_committed": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "production_readiness_claimed": False,
        },
    }


def _matrix_product_ready(*, matrix: Mapping[str, Any], summary: Mapping[str, Any]) -> bool:
    product = dict(matrix.get("product_runner") or {})
    return (
        matrix.get("decision") == "stratified_matrix_live_execution_ready"
        and product.get("decision") == "real_corpus_default_on_validated"
        and product.get("gate_verdict") == "PASS"
        and product.get("live_sec_network_used") is True
        and not product.get("blocking_reasons")
        and _int(summary.get("real_filing_count")) >= 30
        and _int(summary.get("issuer_hash_count")) >= 15
        and _int(summary.get("supported_record_count")) >= 30
        and _int(summary.get("records_with_arelle_sidecar_output")) == _int(summary.get("supported_record_count"))
        and _int(summary.get("records_with_selected_fact_authority_equal_to_sidecar"))
        == _int(summary.get("supported_record_count"))
        and _int(summary.get("records_with_handoff_export_prepare")) == _int(summary.get("supported_record_count"))
        and _int(summary.get("completeness_guard_failed_count")) == 0
        and _int(summary.get("unexpected_zero_inline_xbrl_count")) == 0
        and _int(summary.get("unexpected_blocked_or_degraded_count")) == 0
        and float(summary.get("companyfacts_value_match_rate") or 0) >= 0.98
        and _int(summary.get("companyfacts_oracle_unavailable_count")) == 0
    )


def _matrix_strata_ready(*, matrix_plan: Mapping[str, Any], summary: Mapping[str, Any]) -> bool:
    forms = dict(summary.get("forms") or {})
    strata = dict(summary.get("strata_readiness") or {})
    return (
        matrix_plan.get("mode") == "external_stratified_matrix_plan"
        and matrix_plan.get("state") == "passed"
        and matrix_plan.get("off_repo_plan_used") is True
        and matrix_plan.get("raw_identity_redacted") is True
        and not matrix_plan.get("missing_required_strata")
        and set(matrix_plan.get("covered_strata") or []) == set(REQUIRED_STRATA)
        and summary.get("required_forms_present") is True
        and all(_int(forms.get(form)) > 0 for form in REQUIRED_FORMS)
        and strata.get("all_required_strata_ready") is True
        and set(strata.get("ready_strata") or []) == set(REQUIRED_STRATA)
        and not strata.get("missing_strata")
        and not strata.get("blocked_strata")
        and not strata.get("unknown_strata")
    )


def _attempt_proves_gated_reveal(attempt: Mapping[str, Any]) -> bool:
    filing = dict(attempt.get("selected_filing") or {})
    bundle = dict(attempt.get("authority_bundle") or {})
    reveal = dict(attempt.get("operator_reveal") or {})
    audit = dict(attempt.get("audit_receipt_redaction") or {})
    return (
        filing.get("issuer_identity_redacted") is True
        and filing.get("accession_redacted") is True
        and filing.get("sec_url_redacted") is True
        and _int(bundle.get("coherent_bundle_count")) == 1
        and bundle.get("runtime_dataset_and_provenance_bound") is True
        and reveal.get("reveal_state") == "ready"
        and _int(reveal.get("revealed_fact_count")) > 0
        and reveal.get("idempotent_replay_same_receipt_id") is True
        and reveal.get("idempotent_replay_same_receipt_hash") is True
        and reveal.get("idempotent_replay_no_second_receipt") is True
        and reveal.get("status_projection_raw_values_returned") is False
        and reveal.get("status_projection_revealed_fact_count") == 0
        and reveal.get("flag_off_reveal_blocked_reason") == FEATURE_FLAG_DISABLED_REASON
        and reveal.get("flag_off_status_blocked_reason") == FEATURE_FLAG_DISABLED_REASON
        and audit.get("receipt_present") is True
        and audit.get("effective_field_present") is False
        and audit.get("value_record_collection_present") is False
        and audit.get("raw_values_persisted") is False
        and audit.get("raw_identity_persisted") is False
    )


def _matrix_redaction_ok(redaction: Mapping[str, Any]) -> bool:
    return (
        redaction.get("identity_hash_only") is True
        and redaction.get("raw_accessions_committed") is False
        and redaction.get("raw_sec_urls_committed") is False
        and redaction.get("raw_tickers_committed") is False
        and redaction.get("raw_values_committed") is False
        and redaction.get("local_storage_roots_committed") is False
        and redaction.get("local_paths_committed") is False
        and redaction.get("operator_contact_committed") is False
        and redaction.get("raw_runtime_artifacts_committed") is False
        and redaction.get("raw_operator_plan_committed") is False
        and redaction.get("redaction_scan_passed") is True
    )


def _matrix_non_goals_ok(non_goals: Mapping[str, Any]) -> bool:
    return (
        non_goals.get("runtime_default_changed") is False
        and non_goals.get("default_on_arelle_cutover_enabled") is False
        and non_goals.get("default_on_value_reveal_enabled") is False
        and non_goals.get("raw_issuer_identity_committed") is False
        and non_goals.get("raw_values_committed") is False
        and non_goals.get("production_readiness_claimed") is False
        and non_goals.get("final_financial_statement_semantics_claimed") is False
        and non_goals.get("cross_company_comparability_claimed") is False
        and non_goals.get("candidate_b_sec_routing_performed") is False
    )


def _value_reveal_redaction_ok(report: Mapping[str, Any]) -> bool:
    redaction = dict(report.get("redaction_scan") or {})
    non_admissions = dict(report.get("non_admissions_preserved") or {})
    return (
        redaction.get("reportable_bundle_refs_and_reveal_receipts_scanned") is True
        and redaction.get("raw_issuer_identity_found") is False
        and redaction.get("raw_accession_found") is False
        and redaction.get("raw_sec_url_found") is False
        and redaction.get("raw_local_path_found") is False
        and redaction.get("raw_contact_found") is False
        and redaction.get("raw_value_record_collection_found") is False
        and non_admissions.get("default_on_arelle_cutover_claimed") is False
        and non_admissions.get("default_on_value_reveal_claimed") is False
        and non_admissions.get("production_readiness_claimed") is False
        and non_admissions.get("final_financial_statement_semantics_claimed") is False
        and non_admissions.get("cross_company_comparability_claimed") is False
        and non_admissions.get("candidate_b_sec_routing_performed") is False
        and non_admissions.get("rag_vector_model_provider_auth_behavior_added") is False
    )


def _config_defaults_off(config_text: str) -> bool:
    return (
        _contains(config_text, 'layer3_sec_edgar_live_network_enabled: bool = Field(\n        default=False,')
        and _contains(
            config_text,
            'layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=False,',
        )
        and _contains(
            config_text,
            'layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False,',
        )
    )


def _public_matrix_summary(*, matrix_summary: Mapping[str, Any], matrix_plan: Mapping[str, Any]) -> dict[str, Any]:
    strata = dict(matrix_summary.get("strata_readiness") or {})
    return {
        "matrix_plan_mode": matrix_plan.get("mode"),
        "matrix_plan_state": matrix_plan.get("state"),
        "matrix_chunk_count": matrix_summary.get("matrix_chunk_count"),
        "ready_matrix_chunk_count": matrix_summary.get("ready_matrix_chunk_count"),
        "blocked_matrix_chunk_count": matrix_summary.get("blocked_matrix_chunk_count"),
        "real_filing_count": matrix_summary.get("real_filing_count"),
        "issuer_hash_count": matrix_summary.get("issuer_hash_count"),
        "supported_record_count": matrix_summary.get("supported_record_count"),
        "forms": matrix_summary.get("forms"),
        "required_forms": list(REQUIRED_FORMS),
        "required_forms_present": matrix_summary.get("required_forms_present"),
        "companyfacts_value_match_rate": matrix_summary.get("companyfacts_value_match_rate"),
        "all_required_strata_ready": strata.get("all_required_strata_ready"),
        "ready_strata": strata.get("ready_strata"),
        "missing_strata": strata.get("missing_strata"),
        "blocked_strata": strata.get("blocked_strata"),
        "unknown_strata": strata.get("unknown_strata"),
    }


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _headline(*, ready: bool, blockers: list[dict[str, Any]]) -> str:
    if ready:
        return (
            "Explicit-operator default-off readiness selected after live stratified matrix proof; "
            "default-on and production-readiness remain deferred."
        )
    reasons = ", ".join(str(item["reason"]) for item in blockers)
    return f"SEC/Arelle stratified matrix readiness decision is blocked: {reasons}."


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object at {_repo_display_path(path)}")
    return value


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"redacted-path-marker:{path.name}"


if __name__ == "__main__":
    raise SystemExit(main())
