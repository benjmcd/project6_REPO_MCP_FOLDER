from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-default-posture-decision-report.json")
DEFAULT_BROADER_RELIABILITY_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json"
)
DEFAULT_REAL_PRODUCT_RUNNER_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json"
)
DEFAULT_VALUE_REVEAL_LIVE_PROOF_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json"
)
DEFAULT_RUNTIME_REPORT = Path("diagnostics/assessment/sec-xbrl-default-on-runtime-report.json")
DEFAULT_ADMISSION_REVIEW_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json"
)

FEATURE_FLAG_DISABLED_REASON = "sec_edgar_arelle_value_reveal_feature_flag_disabled"
NEXT_SLICE = "sec_edgar_operator_readiness_runbook_and_stratified_matrix_selection_v1"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL default-posture decision. This validate-only diagnostic reads committed "
            "redacted reports and source defaults; it does not run Arelle, fetch SEC data, expose "
            "values, or mutate runtime defaults."
        )
    )
    parser.add_argument("--broader-reliability-report", default=str(DEFAULT_BROADER_RELIABILITY_REPORT))
    parser.add_argument("--real-product-runner-report", default=str(DEFAULT_REAL_PRODUCT_RUNNER_REPORT))
    parser.add_argument("--value-reveal-live-proof-report", default=str(DEFAULT_VALUE_REVEAL_LIVE_PROOF_REPORT))
    parser.add_argument("--runtime-report", default=str(DEFAULT_RUNTIME_REPORT))
    parser.add_argument("--admission-review-report", default=str(DEFAULT_ADMISSION_REVIEW_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        source_root=ROOT,
        broader_reliability_report_path=_resolve_path(args.broader_reliability_report),
        real_product_runner_report_path=_resolve_path(args.real_product_runner_report),
        value_reveal_live_proof_report_path=_resolve_path(args.value_reveal_live_proof_report),
        runtime_report_path=_resolve_path(args.runtime_report),
        admission_review_report_path=_resolve_path(args.admission_review_report),
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
    broader_reliability_report_path: Path,
    real_product_runner_report_path: Path,
    value_reveal_live_proof_report_path: Path,
    runtime_report_path: Path,
    admission_review_report_path: Path,
) -> dict[str, Any]:
    config_text = _read_config(source_root)
    broader = _read_json(broader_reliability_report_path)
    real_product = _read_json(real_product_runner_report_path)
    live_proof = _read_json(value_reveal_live_proof_report_path)
    runtime = _read_json(runtime_report_path)
    admission = _read_json(admission_review_report_path)

    real_summary = dict(real_product.get("summary") or {})
    real_redaction = dict(real_product.get("redaction") or {})
    real_non_goals = dict(real_product.get("non_goals_preserved") or {})
    live_attempts = live_proof.get("attempts") if isinstance(live_proof.get("attempts"), list) else []
    live_defaults = dict(live_proof.get("committed_default_posture") or {})
    live_redaction = dict(live_proof.get("redaction_scan") or {})
    live_non_admissions = dict(live_proof.get("non_admissions_preserved") or {})
    runtime_posture = dict(runtime.get("runtime_posture") or {})
    broader_non_goals = dict(broader.get("non_goals_preserved") or {})
    runtime_non_goals = dict(runtime.get("non_goals_preserved") or {})

    config_defaults_off = _config_defaults_off(config_text)
    config_safety_defaults_off = _config_safety_defaults_off(config_text)
    live_proof_defaults_off = (
        live_defaults.get("sec_live_network_default_enabled") is False
        and live_defaults.get("arelle_fact_authority_cutover_default_enabled") is False
        and live_defaults.get("arelle_value_reveal_default_enabled") is False
    )
    live_proof_safety_defaults_off = (
        live_defaults.get("sec_live_network_default_enabled") is False
        and live_defaults.get("arelle_value_reveal_default_enabled") is False
    )
    broader_passed = (
        broader.get("decision") == "broader_corpus_reliability_admitted"
        and not broader.get("blocking_reasons")
        and broader.get("next_slice") == "sec_edgar_arelle_default_posture_decision_v1"
    )
    real_product_passed = (
        real_product.get("decision") == "real_corpus_default_on_validated"
        and real_product.get("gate_verdict") == "PASS"
        and real_product.get("fake_sec_client_used") is False
        and real_product.get("live_sec_network_used") is True
        and _int(real_summary.get("real_filing_count")) >= 30
        and _int(real_summary.get("issuer_hash_count")) >= 15
        and _int(real_summary.get("supported_record_count")) >= 30
        and _int(real_summary.get("records_with_arelle_sidecar_output")) == _int(
            real_summary.get("supported_record_count")
        )
        and _int(real_summary.get("records_with_selected_fact_authority_equal_to_sidecar")) == _int(
            real_summary.get("supported_record_count")
        )
        and _int(real_summary.get("records_with_handoff_export_prepare")) == _int(
            real_summary.get("supported_record_count")
        )
        and _int(real_summary.get("resolved_fact_count")) >= _int(real_summary.get("independent_inline_fact_count"))
        and _int(real_summary.get("independent_inline_fact_count")) > 0
        and float(real_summary.get("companyfacts_value_match_rate") or 0) >= 0.98
        and real_summary.get("operator_surface_values_exposed") is False
    )
    reveal_passed = (
        live_proof.get("decision")
        == "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings"
        and len(live_attempts) >= 2
        and all(_attempt_proves_gated_reveal(attempt) for attempt in live_attempts)
    )
    redaction_passed = (
        _real_product_redaction_ok(real_redaction, real_non_goals)
        and _live_proof_redaction_ok(live_redaction, live_non_admissions, live_attempts)
        and broader_non_goals.get("raw_identity_urls_paths_storage_roots_committed") is False
        and broader_non_goals.get("value_unredaction_performed") is False
        and runtime_non_goals.get("candidate_b_sec_routing_performed") is False
        and runtime_non_goals.get("final_financial_statement_semantics_claimed") is False
        and runtime_non_goals.get("cross_company_comparability_claimed") is False
    )
    runtime_default_off = (
        runtime.get("decision") == "default_on_runtime_disabled_by_governance_remediation"
        and runtime_posture.get("default_cutover_enabled") is False
        and runtime_posture.get("operator_value_reveal_default_enabled") is False
    )
    runtime_default_enabled = (
        runtime.get("decision") == "default_on_runtime_enabled"
        and runtime_posture.get("default_cutover_enabled") is True
        and runtime_posture.get("operator_value_reveal_default_enabled") is False
    )
    default_on_not_ready = (
        admission.get("ready_for_default_on_runtime_slice") is False
        and admission.get("decision")
        not in {
            "admission_review_passed",
            "admission_review_superseded_by_default_on_runtime",
        }
        and runtime_default_off
    )
    default_on_superseded_by_runtime = (
        admission.get("decision") == "admission_review_superseded_by_default_on_runtime"
        and runtime_default_enabled
    )

    criteria = [
        _criterion(
            "committed_safety_defaults_preserved",
            (config_defaults_off or config_safety_defaults_off) and live_proof_safety_defaults_off,
            {
                "config_file": "backend/app/core/config.py",
                "config_defaults_off": config_defaults_off,
                "config_safety_defaults_off": config_safety_defaults_off,
                "live_proof_defaults_off": live_proof_defaults_off,
                "live_proof_safety_defaults_off": live_proof_safety_defaults_off,
                "live_proof_report": _repo_display_path(value_reveal_live_proof_report_path),
            },
            "default_posture_committed_defaults_not_off",
        ),
        _criterion(
            "broader_real_product_reliability_admitted",
            broader_passed,
            {
                "source_report": _repo_display_path(broader_reliability_report_path),
                "decision": broader.get("decision"),
                "blocking_reason_count": len(broader.get("blocking_reasons") or []),
                "next_slice": broader.get("next_slice"),
            },
            "default_posture_broader_reliability_not_admitted",
        ),
        _criterion(
            "live_real_product_runner_proves_product_path",
            real_product_passed,
            {
                "source_report": _repo_display_path(real_product_runner_report_path),
                "decision": real_product.get("decision"),
                "gate_verdict": real_product.get("gate_verdict"),
                "real_filing_count": real_summary.get("real_filing_count"),
                "issuer_hash_count": real_summary.get("issuer_hash_count"),
                "supported_record_count": real_summary.get("supported_record_count"),
                "resolved_fact_count": real_summary.get("resolved_fact_count"),
                "independent_inline_fact_count": real_summary.get("independent_inline_fact_count"),
                "companyfacts_value_match_rate": real_summary.get("companyfacts_value_match_rate"),
                "operator_surface_values_exposed": real_summary.get("operator_surface_values_exposed"),
            },
            "default_posture_real_product_runner_not_proven",
        ),
        _criterion(
            "bounded_governed_value_reveal_proven",
            reveal_passed,
            {
                "source_report": _repo_display_path(value_reveal_live_proof_report_path),
                "decision": live_proof.get("decision"),
                "attempt_count": len(live_attempts),
                "forms": [
                    dict(attempt.get("selected_filing") or {}).get("form")
                    for attempt in live_attempts
                ],
            },
            "default_posture_bounded_value_reveal_not_proven",
        ),
        _criterion(
            "runtime_default_authority_posture_recognized",
            runtime_default_off or runtime_default_enabled,
            {
                "source_report": _repo_display_path(runtime_report_path),
                "decision": runtime.get("decision"),
                "default_cutover_enabled": runtime_posture.get("default_cutover_enabled"),
                "operator_value_reveal_default_enabled": runtime_posture.get(
                    "operator_value_reveal_default_enabled"
                ),
            },
            "default_posture_runtime_default_authority_not_default_off",
        ),
        _criterion(
            "default_on_admission_state_recognized",
            default_on_not_ready or default_on_superseded_by_runtime,
            {
                "source_report": _repo_display_path(admission_review_report_path),
                "admission_decision": admission.get("decision"),
                "ready_for_default_on_runtime_slice": admission.get("ready_for_default_on_runtime_slice"),
                "runtime_default_enabled": runtime_default_enabled,
            },
            "default_posture_default_on_currently_admitted_or_unreviewed",
        ),
        _criterion(
            "redaction_and_non_admissions_preserved",
            redaction_passed,
            {
                "real_product_redaction": _redaction_summary(real_redaction),
                "value_reveal_redaction_scan": live_redaction,
                "non_admissions": {
                    "default_on_arelle_cutover_claimed": live_non_admissions.get(
                        "default_on_arelle_cutover_claimed"
                    ),
                    "default_on_value_reveal_claimed": live_non_admissions.get(
                        "default_on_value_reveal_claimed"
                    ),
                    "production_readiness_claimed": live_non_admissions.get("production_readiness_claimed"),
                    "final_financial_statement_semantics_claimed": live_non_admissions.get(
                        "final_financial_statement_semantics_claimed"
                    ),
                    "cross_company_comparability_claimed": live_non_admissions.get(
                        "cross_company_comparability_claimed"
                    ),
                },
            },
            "default_posture_redaction_or_non_admission_regressed",
        ),
    ]
    blockers = [
        {"reason": item["blocked_reason"], "criterion": item["criterion"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    selected = not blockers
    superseded = selected and runtime_default_enabled
    return {
        "schema_id": "diagnostics.sec_xbrl_default_posture_decision.v1",
        "target": "sec_edgar_arelle_default_posture_decision_v1",
        "decision": (
            "explicit_operator_only_default_off_superseded_by_default_on_runtime"
            if superseded
            else "explicit_operator_only_default_off_selected"
            if selected
            else "default_posture_decision_blocked"
        ),
        "headline": _headline(selected=selected, superseded=superseded, blockers=blockers),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "selected_posture": {
            "posture": "explicit_operator_only_default_off" if selected else None,
            "arelle_fact_authority_cutover_default_enabled": False,
            "arelle_fact_authority_cutover_default_on_supersedes_selected_posture": superseded,
            "arelle_value_reveal_default_enabled": False,
            "sec_live_network_default_enabled": False,
            "operator_value_reveal_available_only_by_explicit_gated_action": selected,
            "broader_reliability_admission_converted_to_runtime_default": False,
        },
        "deferred_postures": {
            "default_on_arelle_fact_authority_cutover": "requires separate reviewed admission gate and rollback",
            "default_on_value_reveal": "requires separate operator policy, auth, retention, and audit review",
            "staged_default_on_experiment": "requires bounded operator cohort and rollback plan before execution",
        },
        "source_reports": {
            "broader_reliability": _repo_display_path(broader_reliability_report_path),
            "real_product_runner": _repo_display_path(real_product_runner_report_path),
            "value_reveal_live_proof": _repo_display_path(value_reveal_live_proof_report_path),
            "runtime_default": _repo_display_path(runtime_report_path),
            "admission_review": _repo_display_path(admission_review_report_path),
        },
        "next_slice": (
            "sec_xbrl_next_downstream_gate_design_selection_before_any_default_on_export_or_production_implementation"
            if superseded
            else NEXT_SLICE
            if selected
            else "sec_edgar_arelle_default_posture_decision_v1"
        ),
        "non_goals_preserved": {
            "runtime_default_changed_by_decision": False,
            "runtime_default_enabled_by_follow_on_runtime_slice": superseded,
            "live_sec_network_run_performed_by_decision": False,
            "arelle_subprocess_invoked_by_decision": False,
            "value_reveal_request_performed_by_decision": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "production_readiness_claimed": False,
        },
    }


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


def _config_safety_defaults_off(config_text: str) -> bool:
    return (
        _contains(config_text, 'layer3_sec_edgar_live_network_enabled: bool = Field(\n        default=False,')
        and _contains(
            config_text,
            'layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False,',
        )
    )


def _real_product_redaction_ok(redaction: Mapping[str, Any], non_goals: Mapping[str, Any]) -> bool:
    return (
        redaction.get("identity_hash_only") is True
        and redaction.get("raw_accessions_committed") is False
        and redaction.get("raw_sec_urls_committed") is False
        and redaction.get("raw_tickers_committed") is False
        and redaction.get("raw_values_committed") is False
        and redaction.get("local_storage_roots_committed") is False
        and non_goals.get("operator_value_reveal_enabled") is False
        and non_goals.get("final_financial_statement_semantics_claimed") is False
        and non_goals.get("cross_company_comparability_claimed") is False
        and non_goals.get("candidate_b_sec_routing_performed") is False
    )


def _live_proof_redaction_ok(
    redaction: Mapping[str, Any],
    non_admissions: Mapping[str, Any],
    attempts: list[Any],
) -> bool:
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
        and all(_attempt_redaction_ok(attempt) for attempt in attempts if isinstance(attempt, Mapping))
    )


def _attempt_redaction_ok(attempt: Mapping[str, Any]) -> bool:
    filing = dict(attempt.get("selected_filing") or {})
    audit = dict(attempt.get("audit_receipt_redaction") or {})
    return (
        filing.get("issuer_identity_redacted") is True
        and filing.get("accession_redacted") is True
        and filing.get("sec_url_redacted") is True
        and audit.get("raw_values_persisted") is False
        and audit.get("raw_identity_persisted") is False
    )


def _redaction_summary(redaction: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity_hash_only": redaction.get("identity_hash_only"),
        "raw_accessions_committed": redaction.get("raw_accessions_committed"),
        "raw_sec_urls_committed": redaction.get("raw_sec_urls_committed"),
        "raw_tickers_committed": redaction.get("raw_tickers_committed"),
        "raw_values_committed": redaction.get("raw_values_committed"),
        "local_storage_roots_committed": redaction.get("local_storage_roots_committed"),
    }


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _headline(*, selected: bool, superseded: bool, blockers: list[dict[str, Any]]) -> str:
    if superseded:
        return (
            "Default posture selected explicit-operator-only default-off as a pre-runtime posture and is now "
            "superseded by the reviewed default-on fact-authority runtime; value reveal remains separately gated "
            "and default-off."
        )
    if selected:
        return (
            "Default posture selected: keep SEC/Arelle explicit-operator-only and default-off while "
            "moving to operator runbook and stratified matrix selection."
        )
    reasons = ", ".join(reason["reason"] for reason in blockers)
    return f"SEC/Arelle default-posture decision is blocked: {reasons}."


def _read_config(source_root: Path) -> str:
    return (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")


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
