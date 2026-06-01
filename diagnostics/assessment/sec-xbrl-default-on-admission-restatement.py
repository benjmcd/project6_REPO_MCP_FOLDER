from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json")
NEXT_AFTER_DEFAULT_ON_RUNTIME = "sec_xbrl_default_on_nonlocal_production_readiness_design_v1"

DEFAULT_REQUIRED_REPORTS = {
    "default_on_gate": Path("diagnostics/assessment/sec-xbrl-default-on-gate-report.json"),
    "broader_reliability": Path("diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json"),
    "historical_real_product_runner": Path(
        "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json"
    ),
    "sector_family_validation": Path("diagnostics/assessment/sec-xbrl-sector-family-real-filer-validation-report.json"),
    "value_reveal_live_proof": Path("diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json"),
    "admission_review": Path("diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json"),
    "runtime_default": Path("diagnostics/assessment/sec-xbrl-default-on-runtime-report.json"),
    "default_posture": Path("diagnostics/assessment/sec-xbrl-default-posture-decision-report.json"),
    "operator_runbook": Path("diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json"),
}

REAL_CORPUS_RUNNER_SOURCE = Path("diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py")
REQUIRED_FORMS = {"10-K", "10-Q", "20-F", "40-F", "6-K", "8-K"}
MIN_REAL_FILINGS = 30
MIN_ISSUER_HASHES = 15
MIN_COMPANYFACTS_MATCH_RATE = 0.98

REQUIRED_ROLLBACK_SIGNALS = {
    "missing_or_stale_sidecar": "arelle_sidecar_receipt_required",
    "parser_source_lineage_mismatch": (
        "sec_edgar_html_inline_xbrl_fact_material_bridge_arelle_sidecar_lineage_mismatch"
    ),
    "value_store_missing": "sec_edgar_arelle_sidecar_internal_value_store_missing",
    "value_store_hash_mismatch": "sec_edgar_arelle_sidecar_internal_value_store_hash_mismatch",
    "value_store_lineage_mismatch": "sec_edgar_arelle_sidecar_internal_value_store_lineage_mismatch",
    "taxonomy_or_arelle_unavailable": "taxonomy_package_unavailable",
    "redaction_violation": "raw_authority_exposed",
}

RAW_ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
RAW_CIK_FIELD_RE = re.compile(r'"(?:cik|raw_cik)"\s*:\s*"?\d{1,10}"?', re.IGNORECASE)
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(
    r"[A-Za-z]:\\|\\\\|file://|/(?:Users|home|tmp|workspace)(?:/|$)|/var/tmp(?:/|$)|/private/tmp(?:/|$)"
)
OPERATOR_CONTACT_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
RAW_DECIMAL_MAGNITUDE_RE = re.compile(r"(?<![A-Za-z0-9_])-?\d{4,}\.\d+(?![A-Za-z0-9_])")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL default-on admission evidence restatement. This validate-only "
            "diagnostic reads committed reports and source files only; it does not run "
            "Arelle, acquire SEC sources, expose values, or change runtime defaults."
        )
    )
    parser.add_argument("--default-on-gate-report", default=str(DEFAULT_REQUIRED_REPORTS["default_on_gate"]))
    parser.add_argument("--broader-reliability-report", default=str(DEFAULT_REQUIRED_REPORTS["broader_reliability"]))
    parser.add_argument(
        "--real-product-runner-report",
        "--historical-real-product-runner-report",
        dest="historical_real_product_runner_report",
        default=str(DEFAULT_REQUIRED_REPORTS["historical_real_product_runner"]),
    )
    parser.add_argument("--sector-family-report", default=str(DEFAULT_REQUIRED_REPORTS["sector_family_validation"]))
    parser.add_argument("--value-reveal-live-proof-report", default=str(DEFAULT_REQUIRED_REPORTS["value_reveal_live_proof"]))
    parser.add_argument("--admission-review-report", default=str(DEFAULT_REQUIRED_REPORTS["admission_review"]))
    parser.add_argument("--runtime-default-report", default=str(DEFAULT_REQUIRED_REPORTS["runtime_default"]))
    parser.add_argument("--default-posture-report", default=str(DEFAULT_REQUIRED_REPORTS["default_posture"]))
    parser.add_argument("--operator-runbook-report", default=str(DEFAULT_REQUIRED_REPORTS["operator_runbook"]))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        source_root=ROOT,
        report_paths={
            "default_on_gate": _resolve_path(args.default_on_gate_report),
            "broader_reliability": _resolve_path(args.broader_reliability_report),
            "historical_real_product_runner": _resolve_path(args.historical_real_product_runner_report),
            "sector_family_validation": _resolve_path(args.sector_family_report),
            "value_reveal_live_proof": _resolve_path(args.value_reveal_live_proof_report),
            "admission_review": _resolve_path(args.admission_review_report),
            "runtime_default": _resolve_path(args.runtime_default_report),
            "default_posture": _resolve_path(args.default_posture_report),
            "operator_runbook": _resolve_path(args.operator_runbook_report),
        },
    )
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(*, source_root: Path, report_paths: Mapping[str, Path]) -> dict[str, Any]:
    loaded = {name: _read_report(path) for name, path in report_paths.items()}
    reports = {name: state.get("report") or {} for name, state in loaded.items()}
    report_texts = {name: str(state.get("text") or "") for name, state in loaded.items()}
    sources = _source_texts(source_root)

    default_on_gate = reports["default_on_gate"]
    broader = reports["broader_reliability"]
    real_product = reports["historical_real_product_runner"]
    sector_family = reports["sector_family_validation"]
    live_proof = reports["value_reveal_live_proof"]
    admission = reports["admission_review"]
    runtime = reports["runtime_default"]
    posture = reports["default_posture"]
    runbook = reports["operator_runbook"]

    gate_summary = dict(default_on_gate.get("summary") or {})
    broader_summary = dict(broader.get("summary") or {})
    real_summary = dict(real_product.get("summary") or {})
    real_redaction = dict(real_product.get("redaction") or {})
    real_non_goals = dict(real_product.get("non_goals_preserved") or {})
    live_defaults = dict(live_proof.get("committed_default_posture") or {})
    live_redaction = dict(live_proof.get("redaction_scan") or {})
    live_non_admissions = dict(live_proof.get("non_admissions_preserved") or {})
    runtime_posture = dict(runtime.get("runtime_posture") or {})
    selected_posture = dict(posture.get("selected_posture") or {})
    deferred_postures = dict(posture.get("deferred_postures") or {})
    operator_policy = dict(runbook.get("operator_policy") or {})

    criteria = [
        _criterion(
            "required_committed_reports_parseable",
            all(state["status"] == "loaded" for state in loaded.values()),
            {
                name: {
                    "path": _repo_display_path(path),
                    "status": loaded[name]["status"],
                    "schema_id": loaded[name].get("schema_id"),
                    "decision": loaded[name].get("decision"),
                }
                for name, path in report_paths.items()
            },
            "default_on_admission_restatement_required_report_missing_or_malformed",
        ),
        _criterion(
            "required_source_report_references_current",
            _source_report_refs_current(loaded, source_root),
            _source_report_ref_evidence(loaded, source_root),
            "default_on_admission_restatement_stale_or_missing_source_report_reference",
        ),
        _criterion(
            "real_corpus_runner_source_present",
            (source_root / REAL_CORPUS_RUNNER_SOURCE).exists(),
            {"source_file": REAL_CORPUS_RUNNER_SOURCE.as_posix()},
            "default_on_admission_restatement_real_corpus_runner_source_missing",
        ),
        _criterion(
            "active_reproducible_sector_family_scope_recorded",
            sector_family.get("decision") == "sector_family_real_filer_validation_satisfied"
            and sector_family.get("gate_verdict") == "PASS"
            and dict(sector_family.get("report_scope") or {}).get("broader_live_matrix_product_gate_in_scope")
            is False
            and dict(sector_family.get("report_scope") or {}).get(
                "historical_live_matrix_reproducible_offline_from_available_inputs"
            )
            is False,
            {
                "source_report": _repo_display_path(report_paths["sector_family_validation"]),
                "decision": sector_family.get("decision"),
                "gate_verdict": sector_family.get("gate_verdict"),
                "report_scope": sector_family.get("report_scope"),
            },
            "default_on_admission_restatement_active_reproducible_scope_not_recorded",
        ),
        _criterion(
            "current_broader_real_product_runner_authority",
            _current_broader_real_product_runner_authority(
                real_product,
                report_paths["historical_real_product_runner"],
            ),
            {
                "real_product_report": _repo_display_path(report_paths["historical_real_product_runner"]),
                "real_product_report_archived": _is_historical_archive_path(
                    report_paths["historical_real_product_runner"]
                ),
                "real_product_report_decision": real_product.get("decision"),
                "real_product_report_gate_verdict": real_product.get("gate_verdict"),
                "current_run_live_sec_network_used": real_product.get("current_run_live_sec_network_used"),
                "inherited_live_sec_network_used": real_product.get("live_sec_network_used"),
                "offline_redacted_product_report_import": real_product.get("offline_redacted_product_report_import"),
                "active_reproducible_report": _repo_display_path(report_paths["sector_family_validation"]),
                "active_reproducible_report_target": sector_family.get("target"),
            },
            "default_on_admission_restatement_broader_real_product_runner_not_current_authority",
        ),
        _criterion(
            "companyfacts_value_correctness_restated",
            _companyfacts_value_correctness_restated(default_on_gate, broader, real_product),
            {
                "default_on_gate_decision": default_on_gate.get("decision"),
                "default_on_gate_match_rate": gate_summary.get("companyfacts_value_match_rate"),
                "default_on_gate_compared_count": gate_summary.get("companyfacts_value_compared_count"),
                "broader_real_product_match_rate": broader_summary.get(
                    "real_product_path_companyfacts_value_match_rate"
                ),
                "real_product_decision": real_product.get("decision"),
                "real_product_match_rate": real_summary.get("companyfacts_value_match_rate"),
                "real_product_compared_count": real_summary.get("companyfacts_value_compared_count"),
                "minimum_match_rate": MIN_COMPANYFACTS_MATCH_RATE,
            },
            "default_on_admission_restatement_companyfacts_value_correctness_not_reproven",
        ),
        _criterion(
            "completeness_and_dts_coverage_restated",
            _completeness_restated(default_on_gate, real_product),
            {
                "default_on_independent_count_and_dts_state": _criterion_state(
                    default_on_gate, "independent_count_and_dts_completeness"
                ),
                "real_product_gate_verdict": real_product.get("gate_verdict"),
                "real_product_resolved_fact_count": real_summary.get("resolved_fact_count"),
                "real_product_independent_inline_fact_count": real_summary.get("independent_inline_fact_count"),
                "real_product_completeness_guard_failed_count": real_summary.get(
                    "completeness_guard_failed_count"
                ),
                "real_product_unexpected_blocked_or_degraded_count": real_summary.get(
                    "unexpected_blocked_or_degraded_count"
                ),
            },
            "default_on_admission_restatement_completeness_or_dts_not_reproven",
        ),
        _criterion(
            "product_path_readiness_restated",
            _product_path_readiness_restated(broader, real_product),
            {
                "broader_decision": broader.get("decision"),
                "broader_real_product_filing_count": broader_summary.get("real_product_path_filing_count"),
                "broader_real_product_supported_record_count": broader_summary.get(
                    "real_product_path_supported_record_count"
                ),
                "real_product_decision": real_product.get("decision"),
                "real_product_gate_verdict": real_product.get("gate_verdict"),
                "real_product_filing_count": real_summary.get("real_filing_count"),
                "real_product_supported_record_count": real_summary.get("supported_record_count"),
                "real_product_handoff_export_prepare_count": real_summary.get("records_with_handoff_export_prepare"),
            },
            "default_on_admission_restatement_product_path_readiness_not_reproven",
        ),
        _criterion(
            "sidecar_selection_restated",
            _sidecar_selection_restated(default_on_gate, real_product, runtime_posture),
            {
                "default_on_bridge_cutover_parity_state": _criterion_state(default_on_gate, "bridge_cutover_parity"),
                "runtime_persisted_sidecar_required": runtime_posture.get("persisted_sidecar_required"),
                "real_product_supported_record_count": real_summary.get("supported_record_count"),
                "real_product_records_with_arelle_sidecar_output": real_summary.get(
                    "records_with_arelle_sidecar_output"
                ),
                "real_product_records_with_selected_fact_authority_equal_to_sidecar": real_summary.get(
                    "records_with_selected_fact_authority_equal_to_sidecar"
                ),
            },
            "default_on_admission_restatement_sidecar_selection_not_reproven",
        ),
        _criterion(
            "runtime_default_enablement_posture_recognized",
            _runtime_default_posture_recognized(
                sources,
                live_defaults,
                runtime,
                runtime_posture,
                selected_posture,
                operator_policy,
            ),
            {
                "config_defaults_off": _config_defaults_off(sources.get("config", "")),
                "config_safety_defaults_off": _config_safety_defaults_off(sources.get("config", "")),
                "live_proof_defaults_off": _live_proof_defaults_off(live_defaults),
                "live_proof_safety_defaults_off": _live_proof_safety_defaults_off(live_defaults),
                "runtime_decision": runtime.get("decision"),
                "runtime_default_cutover_enabled": runtime_posture.get("default_cutover_enabled"),
                "default_posture": selected_posture.get("posture"),
                "selected_arelle_fact_authority_cutover_default_enabled": selected_posture.get(
                    "arelle_fact_authority_cutover_default_enabled"
                ),
                "operator_policy_runtime_default_change_allowed": operator_policy.get(
                    "runtime_default_change_allowed"
                ),
            },
            "default_on_admission_restatement_runtime_default_posture_regressed",
        ),
        _criterion(
            "explicit_operator_value_reveal_remains_default_off",
            _value_reveal_default_off(live_defaults, live_redaction, live_non_admissions, selected_posture, operator_policy),
            {
                "live_value_reveal_default_enabled": live_defaults.get("arelle_value_reveal_default_enabled"),
                "selected_value_reveal_default_enabled": selected_posture.get("arelle_value_reveal_default_enabled"),
                "operator_policy_value_reveal_requires_confirmation": operator_policy.get(
                    "value_reveal_requires_explicit_operator_confirmation"
                ),
                "operator_policy_raw_values_committed": operator_policy.get("raw_values_committed"),
                "live_non_admissions_default_on_value_reveal_claimed": live_non_admissions.get(
                    "default_on_value_reveal_claimed"
                ),
                "deferred_default_on_value_reveal": deferred_postures.get("default_on_value_reveal"),
            },
            "default_on_admission_restatement_value_reveal_default_posture_regressed",
        ),
        _criterion(
            "rollback_and_containment_signals_preserved",
            _rollback_signals_present(sources, runtime_posture),
            {
                name: {
                    "signal": signal,
                    "present": _contains_any(sources, signal),
                }
                for name, signal in REQUIRED_ROLLBACK_SIGNALS.items()
            }
            | {
                "runtime_regex_rollback_env_supported": runtime_posture.get("regex_rollback_env_supported"),
                "runtime_synchronous_arelle_in_bridge": runtime_posture.get("synchronous_arelle_in_bridge"),
            },
            "default_on_admission_restatement_rollback_or_containment_signal_missing",
        ),
        _criterion(
            "standing_non_admissions_preserved",
            _non_admissions_preserved(
                real_redaction,
                real_non_goals,
                live_redaction,
                live_non_admissions,
                posture,
                runbook,
            ),
            {
                "real_product_redaction": _redaction_summary(real_redaction),
                "real_product_non_goals": _non_goal_summary(real_non_goals),
                "live_redaction_scan": live_redaction,
                "live_non_admissions": _non_goal_summary(live_non_admissions),
                "posture_non_goals": _non_goal_summary(dict(posture.get("non_goals_preserved") or {})),
                "runbook_non_goals": _non_goal_summary(dict(runbook.get("non_goals_preserved") or {})),
            },
            "default_on_admission_restatement_non_admission_or_redaction_regressed",
        ),
    ]

    conflicts = _conflicting_reasons(
        default_on_gate=default_on_gate,
        broader=broader,
        admission=admission,
        runtime=runtime,
        runtime_posture=runtime_posture,
        selected_posture=selected_posture,
        operator_policy=operator_policy,
        live_defaults=live_defaults,
    )
    report = {
        "schema_id": "diagnostics.sec_xbrl_default_on_admission_restatement.v1",
        "target": "sec_xbrl_default_on_admission_restatement_v1",
        "source_reports": {
            name: _repo_display_path(path)
            for name, path in report_paths.items()
        },
        "source_files": {
            "real_corpus_runner": REAL_CORPUS_RUNNER_SOURCE.as_posix(),
            "config": "backend/app/core/config.py",
        },
        "criteria": criteria,
        "blocking_reasons": _blocking_reasons(criteria),
        "conflicting_reasons": conflicts,
        "restated_evidence": {
            "companyfacts_value_correctness": {
                "default_on_gate_match_rate": gate_summary.get("companyfacts_value_match_rate"),
                "broader_real_product_match_rate": broader_summary.get(
                    "real_product_path_companyfacts_value_match_rate"
                ),
                "real_product_match_rate": real_summary.get("companyfacts_value_match_rate"),
                "minimum_match_rate": MIN_COMPANYFACTS_MATCH_RATE,
            },
            "completeness_and_dts": {
                "default_on_gate_state": _criterion_state(default_on_gate, "independent_count_and_dts_completeness"),
                "real_product_resolved_fact_count": real_summary.get("resolved_fact_count"),
                "real_product_independent_inline_fact_count": real_summary.get("independent_inline_fact_count"),
            },
            "product_path_readiness": {
                "broader_decision": broader.get("decision"),
                "real_product_decision": real_product.get("decision"),
                "real_product_report_archived": _is_historical_archive_path(
                    report_paths["historical_real_product_runner"]
                ),
                "real_product_supported_record_count": real_summary.get("supported_record_count"),
                "real_product_handoff_export_prepare_count": real_summary.get("records_with_handoff_export_prepare"),
            },
            "sidecar_selection": {
                "default_on_bridge_cutover_parity_state": _criterion_state(default_on_gate, "bridge_cutover_parity"),
                "real_product_sidecar_output_count": real_summary.get("records_with_arelle_sidecar_output"),
                "real_product_selected_sidecar_count": real_summary.get(
                    "records_with_selected_fact_authority_equal_to_sidecar"
                ),
            },
            "runtime_enablement": {
                "ready_for_default_on_may_be_true": default_on_gate.get("ready_for_default_on"),
                "runtime_default_on_enabled": _runtime_default_enabled(runtime, runtime_posture),
                "runtime_decision": runtime.get("decision"),
                "default_posture": selected_posture.get("posture"),
                "current_broader_real_product_runner_authority": _current_broader_real_product_runner_authority(
                    real_product,
                    report_paths["historical_real_product_runner"],
                ),
            },
        },
        "rollback_criteria": [
            "missing or stale governed Arelle sidecar receipt blocks future runtime cutover",
            "parser, source-artifact, dataset, and sidecar lineage mismatch blocks future runtime cutover",
            "missing, stale, hash-mismatched, or lineage-mismatched value store blocks future runtime cutover",
            "Arelle/taxonomy/cache unavailability blocks source acquisition or runtime cutover",
            "redaction violation blocks report projection, status projection, and future runtime cutover",
        ],
        "non_goals_preserved": {
            "runtime_default_changed_by_restatement": False,
            "runtime_default_on_enabled_by_restatement": False,
            "value_reveal_default_enabled_by_restatement": False,
            "value_reveal_request_performed_by_restatement": False,
            "live_sec_network_run_performed_by_restatement": False,
            "source_acquisition_performed_by_restatement": False,
            "arelle_subprocess_invoked_by_restatement": False,
            "schema_or_persistence_changed_by_restatement": False,
            "api_or_ui_changed_by_restatement": False,
            "export_or_delivery_performed_by_restatement": False,
            "operator_authentication_claimed": False,
            "production_readiness_claimed": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "cross_company_comparability_claimed": False,
            "final_financial_statement_semantics_claimed": False,
        },
    }
    source_report_redaction = _redaction_scan(report_texts.values())
    report["criteria"].append(
        _criterion(
            "source_reports_redaction_clean",
            source_report_redaction["passed"],
            source_report_redaction,
            "default_on_admission_restatement_source_report_redaction_failed",
        )
    )
    report["redaction"] = _redaction_scan([json.dumps(report, sort_keys=True)])
    report["criteria"].append(
        _criterion(
            "restatement_report_redaction_clean",
            report["redaction"]["passed"],
            report["redaction"],
            "default_on_admission_restatement_report_redaction_failed",
        )
    )
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    runtime_default_enabled = _runtime_default_enabled(runtime, runtime_posture)
    report["decision"] = _decision(
        report["blocking_reasons"],
        report["conflicting_reasons"],
        runtime_default_enabled=runtime_default_enabled,
    )
    report["ready_for_default_on_runtime_design"] = report["decision"] == (
        "default_on_admission_restatement_ready_for_runtime_design"
    )
    report["superseded_by_default_on_runtime"] = report["decision"] == (
        "default_on_admission_restatement_superseded_by_default_on_runtime"
    )
    report["headline"] = _headline(report["decision"], report["blocking_reasons"], report["conflicting_reasons"])
    report["next_slice"] = (
        NEXT_AFTER_DEFAULT_ON_RUNTIME
        if report["superseded_by_default_on_runtime"]
        else
        "sec_xbrl_default_on_runtime_design_v1"
        if report["ready_for_default_on_runtime_design"]
        else "sec_xbrl_default_on_admission_restatement_v1"
        if report["decision"] == "default_on_admission_restatement_still_blocked"
        else "sec_xbrl_default_on_admission_restatement_conflict_audit_v1"
    )
    return report


def _companyfacts_value_correctness_restated(
    default_on_gate: Mapping[str, Any],
    broader: Mapping[str, Any],
    real_product: Mapping[str, Any],
) -> bool:
    gate_summary = dict(default_on_gate.get("summary") or {})
    broader_summary = dict(broader.get("summary") or {})
    real_summary = dict(real_product.get("summary") or {})
    return (
        default_on_gate.get("decision") == "default_on_admitted_candidate"
        and default_on_gate.get("ready_for_default_on") is True
        and _int(gate_summary.get("companyfacts_value_compared_count")) > 0
        and _float(gate_summary.get("companyfacts_value_match_rate")) >= 0.99
        and broader.get("decision") == "broader_corpus_reliability_admitted"
        and _float(broader_summary.get("real_product_path_companyfacts_value_match_rate"))
        >= MIN_COMPANYFACTS_MATCH_RATE
        and real_product.get("decision") == "real_corpus_default_on_validated"
        and _int(real_summary.get("companyfacts_value_compared_count")) > 0
        and _float(real_summary.get("companyfacts_value_match_rate")) >= MIN_COMPANYFACTS_MATCH_RATE
    )


def _completeness_restated(default_on_gate: Mapping[str, Any], real_product: Mapping[str, Any]) -> bool:
    summary = dict(real_product.get("summary") or {})
    return (
        _criterion_state(default_on_gate, "independent_count_and_dts_completeness") == "passed"
        and real_product.get("decision") == "real_corpus_default_on_validated"
        and real_product.get("gate_verdict") == "PASS"
        and _int(summary.get("resolved_fact_count")) > 0
        and _int(summary.get("independent_inline_fact_count")) > 0
        and _int(summary.get("resolved_fact_count")) >= _int(summary.get("independent_inline_fact_count"))
        and _int(summary.get("completeness_guard_failed_count")) == 0
        and _int(summary.get("unexpected_blocked_or_degraded_count")) == 0
    )


def _product_path_readiness_restated(broader: Mapping[str, Any], real_product: Mapping[str, Any]) -> bool:
    broader_summary = dict(broader.get("summary") or {})
    real_summary = dict(real_product.get("summary") or {})
    forms = set((real_summary.get("forms") or {}).keys())
    supported = _int(real_summary.get("supported_record_count"))
    return (
        broader.get("decision") == "broader_corpus_reliability_admitted"
        and _int(broader_summary.get("real_product_path_filing_count")) >= MIN_REAL_FILINGS
        and real_product.get("decision") == "real_corpus_default_on_validated"
        and real_product.get("gate_verdict") == "PASS"
        and real_product.get("fake_sec_client_used") is False
        and real_product.get("live_sec_network_used") is True
        and _int(real_summary.get("real_filing_count")) >= MIN_REAL_FILINGS
        and _int(real_summary.get("issuer_hash_count")) >= MIN_ISSUER_HASHES
        and supported >= MIN_REAL_FILINGS
        and _int(real_summary.get("records_with_handoff_export_prepare")) == supported
        and REQUIRED_FORMS.issubset(forms)
    )


def _sidecar_selection_restated(
    default_on_gate: Mapping[str, Any],
    real_product: Mapping[str, Any],
    runtime_posture: Mapping[str, Any],
) -> bool:
    summary = dict(real_product.get("summary") or {})
    supported = _int(summary.get("supported_record_count"))
    return (
        _criterion_state(default_on_gate, "bridge_cutover_parity") == "passed"
        and runtime_posture.get("persisted_sidecar_required") is True
        and supported >= MIN_REAL_FILINGS
        and _int(summary.get("records_with_arelle_sidecar_output")) == supported
        and _int(summary.get("records_with_selected_fact_authority_equal_to_sidecar")) == supported
    )


def _runtime_default_posture_recognized(
    sources: Mapping[str, str],
    live_defaults: Mapping[str, Any],
    runtime: Mapping[str, Any],
    runtime_posture: Mapping[str, Any],
    selected_posture: Mapping[str, Any],
    operator_policy: Mapping[str, Any],
) -> bool:
    default_off = (
        _config_defaults_off(sources.get("config", ""))
        and _live_proof_defaults_off(live_defaults)
        and runtime.get("decision") == "default_on_runtime_disabled_by_governance_remediation"
        and runtime_posture.get("default_cutover_enabled") is False
        and runtime_posture.get("operator_value_reveal_default_enabled") is False
        and selected_posture.get("posture") == "explicit_operator_only_default_off"
        and selected_posture.get("arelle_fact_authority_cutover_default_enabled") is False
        and selected_posture.get("broader_reliability_admission_converted_to_runtime_default") is False
        and operator_policy.get("runtime_default_change_allowed") is False
    )
    default_on = (
        _config_safety_defaults_off(sources.get("config", ""))
        and _live_proof_safety_defaults_off(live_defaults)
        and _runtime_default_enabled(runtime, runtime_posture)
        and selected_posture.get("posture") == "explicit_operator_only_default_off"
        and selected_posture.get("arelle_fact_authority_cutover_default_on_supersedes_selected_posture") is True
        and selected_posture.get("arelle_value_reveal_default_enabled") is False
        and operator_policy.get("runtime_default_change_allowed") is False
    )
    return default_off or default_on


def _runtime_default_enabled(runtime: Mapping[str, Any], runtime_posture: Mapping[str, Any]) -> bool:
    return (
        runtime.get("decision") == "default_on_runtime_enabled"
        and runtime_posture.get("default_cutover_enabled") is True
        and runtime_posture.get("operator_value_reveal_default_enabled") is False
    )


def _value_reveal_default_off(
    live_defaults: Mapping[str, Any],
    live_redaction: Mapping[str, Any],
    live_non_admissions: Mapping[str, Any],
    selected_posture: Mapping[str, Any],
    operator_policy: Mapping[str, Any],
) -> bool:
    return (
        live_defaults.get("arelle_value_reveal_default_enabled") is False
        and selected_posture.get("arelle_value_reveal_default_enabled") is False
        and selected_posture.get("operator_value_reveal_available_only_by_explicit_gated_action") is True
        and operator_policy.get("value_reveal_requires_explicit_operator_confirmation") is True
        and operator_policy.get("raw_values_committed") is False
        and live_redaction.get("raw_value_record_collection_found") is False
        and live_non_admissions.get("default_on_value_reveal_claimed") is False
    )


def _rollback_signals_present(sources: Mapping[str, str], runtime_posture: Mapping[str, Any]) -> bool:
    return (
        all(_contains_any(sources, signal) for signal in REQUIRED_ROLLBACK_SIGNALS.values())
        and runtime_posture.get("regex_rollback_env_supported") is True
        and runtime_posture.get("synchronous_arelle_in_bridge") is False
    )


def _non_admissions_preserved(
    real_redaction: Mapping[str, Any],
    real_non_goals: Mapping[str, Any],
    live_redaction: Mapping[str, Any],
    live_non_admissions: Mapping[str, Any],
    posture: Mapping[str, Any],
    runbook: Mapping[str, Any],
) -> bool:
    posture_non_goals = dict(posture.get("non_goals_preserved") or {})
    runbook_non_goals = dict(runbook.get("non_goals_preserved") or {})
    return (
        real_redaction.get("identity_hash_only") is True
        and real_redaction.get("raw_accessions_committed") is False
        and real_redaction.get("raw_sec_urls_committed") is False
        and real_redaction.get("raw_values_committed") is False
        and real_redaction.get("local_storage_roots_committed") is False
        and real_non_goals.get("operator_value_reveal_enabled") is False
        and real_non_goals.get("final_financial_statement_semantics_claimed") is False
        and real_non_goals.get("cross_company_comparability_claimed") is False
        and live_redaction.get("raw_issuer_identity_found") is False
        and live_redaction.get("raw_accession_found") is False
        and live_redaction.get("raw_sec_url_found") is False
        and live_redaction.get("raw_local_path_found") is False
        and live_redaction.get("raw_value_record_collection_found") is False
        and live_non_admissions.get("production_readiness_claimed") is False
        and live_non_admissions.get("final_financial_statement_semantics_claimed") is False
        and live_non_admissions.get("cross_company_comparability_claimed") is False
        and posture_non_goals.get("production_readiness_claimed") is False
        and runbook_non_goals.get("production_readiness_claimed") is False
        and runbook_non_goals.get("source_acquisition_performed") is False
        and runbook_non_goals.get("arelle_subprocess_invoked") is False
        and runbook_non_goals.get("live_sec_network_run_performed") is False
    )


def _conflicting_reasons(
    *,
    default_on_gate: Mapping[str, Any],
    broader: Mapping[str, Any],
    admission: Mapping[str, Any],
    runtime: Mapping[str, Any],
    runtime_posture: Mapping[str, Any],
    selected_posture: Mapping[str, Any],
    operator_policy: Mapping[str, Any],
    live_defaults: Mapping[str, Any],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    if (
        broader.get("decision") == "broader_corpus_reliability_admitted"
        and default_on_gate.get("ready_for_default_on") is False
    ):
        conflicts.append(
            {
                "reason": "broader_reliability_admitted_while_default_on_gate_not_ready",
                "evidence": {
                    "broader_decision": broader.get("decision"),
                    "default_on_gate_ready": default_on_gate.get("ready_for_default_on"),
                },
            }
        )
    if (
        runtime_posture.get("default_cutover_enabled") is True
        and selected_posture.get("arelle_fact_authority_cutover_default_enabled") is False
        and runtime.get("decision") != "default_on_runtime_enabled"
    ):
        conflicts.append(
            {
                "reason": "runtime_cutover_enabled_while_default_posture_selected_off",
                "evidence": {
                    "runtime_default_cutover_enabled": runtime_posture.get("default_cutover_enabled"),
                    "selected_default_cutover_enabled": selected_posture.get(
                        "arelle_fact_authority_cutover_default_enabled"
                    ),
                },
            }
        )
    if (
        live_defaults.get("arelle_value_reveal_default_enabled") is True
        and operator_policy.get("value_reveal_requires_explicit_operator_confirmation") is True
    ):
        conflicts.append(
            {
                "reason": "value_reveal_default_enabled_while_policy_requires_explicit_confirmation",
                "evidence": {
                    "live_value_reveal_default_enabled": live_defaults.get("arelle_value_reveal_default_enabled"),
                    "value_reveal_requires_explicit_operator_confirmation": operator_policy.get(
                        "value_reveal_requires_explicit_operator_confirmation"
                    ),
                },
            }
        )
    if (
        admission.get("ready_for_default_on_runtime_slice") is True
        and runtime.get("decision") == "default_on_runtime_disabled_by_governance_remediation"
    ):
        conflicts.append(
            {
                "reason": "admission_review_ready_while_runtime_report_disabled_by_governance",
                "evidence": {
                    "admission_decision": admission.get("decision"),
                    "runtime_decision": runtime.get("decision"),
                },
            }
        )
    return conflicts


def _source_report_refs_current(loaded: Mapping[str, Mapping[str, Any]], source_root: Path) -> bool:
    return all(item["status"] == "present_json_object" for item in _source_report_ref_states(loaded, source_root))


def _current_broader_real_product_runner_authority(real_product: Mapping[str, Any], report_path: Path) -> bool:
    summary = dict(real_product.get("summary") or {})
    offline_import = dict(real_product.get("offline_redacted_product_report_import") or {})
    import_evidence = dict(offline_import.get("evidence") or {})
    redaction_scan = dict(import_evidence.get("redaction_scan") or {})
    return (
        not _is_historical_archive_path(report_path)
        and real_product.get("decision") == "real_corpus_default_on_validated"
        and real_product.get("gate_verdict") == "PASS"
        and real_product.get("fake_sec_client_used") is False
        and real_product.get("live_sec_network_used") is True
        and real_product.get("current_run_live_sec_network_used") is False
        and offline_import.get("state") == "passed"
        and offline_import.get("used") is True
        and import_evidence.get("inherited_live_sec_network_used") is True
        and import_evidence.get("current_run_live_sec_network_used") is False
        and import_evidence.get("current_run_arelle_subprocess_invoked") is False
        and import_evidence.get("storage_marker_matches_supplied_storage") is True
        and import_evidence.get("summary_mismatches") == []
        and redaction_scan.get("passed") is True
        and _int(summary.get("real_filing_count")) >= MIN_REAL_FILINGS
        and _int(summary.get("issuer_hash_count")) >= MIN_ISSUER_HASHES
        and _int(summary.get("companyfacts_value_compared_count")) > 0
        and _float(summary.get("companyfacts_value_match_rate")) >= MIN_COMPANYFACTS_MATCH_RATE
        and _int(summary.get("completeness_guard_failed_count")) == 0
        and _int(summary.get("unexpected_blocked_or_degraded_count")) == 0
    )


def _is_historical_archive_path(path: Path) -> bool:
    return "archive/files_to_be_trashed/2026-05-31-secxbrl" in path.as_posix().replace("\\", "/")


def _source_report_ref_evidence(loaded: Mapping[str, Mapping[str, Any]], source_root: Path) -> dict[str, Any]:
    states = _source_report_ref_states(loaded, source_root)
    return {
        "checked_reference_count": len(states),
        "references": states,
    }


def _source_report_ref_states(loaded: Mapping[str, Mapping[str, Any]], source_root: Path) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for report_name, state in loaded.items():
        report = state.get("report")
        if not isinstance(report, Mapping):
            continue
        for ref in _iter_source_report_refs(report.get("source_reports")):
            if not ref.endswith(".json"):
                continue
            path, containment_status = _source_report_path(source_root, ref)
            ref_state = "present_json_object"
            schema_id: str | None = None
            if containment_status is not None:
                ref_state = containment_status
            elif not path.exists():
                ref_state = "missing"
            else:
                try:
                    value = json.loads(path.read_text(encoding="utf-8-sig"))
                    if not isinstance(value, dict):
                        ref_state = "not_json_object"
                    else:
                        schema_id = value.get("schema_id")
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    ref_state = "malformed_json"
            states.append(
                {
                    "report": report_name,
                    "source_report": ref,
                    "status": ref_state,
                    "schema_id": schema_id,
                }
            )
    return states


def _source_report_path(source_root: Path, ref: str) -> tuple[Path, str | None]:
    root = source_root.resolve()
    try:
        raw_path = Path(ref)
    except (TypeError, ValueError):
        return root, "malformed_path"
    if raw_path.is_absolute():
        return raw_path, "outside_repo"
    try:
        candidate = (root / raw_path).resolve()
    except (OSError, RuntimeError, ValueError):
        return root / raw_path, "malformed_path"
    try:
        candidate.relative_to(root)
    except ValueError:
        return candidate, "outside_repo"
    return candidate, None


def _iter_source_report_refs(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_source_report_refs(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_source_report_refs(nested)


def _criterion_state(report: Mapping[str, Any], criterion: str) -> str | None:
    criteria = report.get("criteria")
    if not isinstance(criteria, list):
        return None
    for item in criteria:
        if isinstance(item, Mapping) and item.get("criterion") == criterion:
            return item.get("state")
    return None


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _blocking_reasons(criteria: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "reason": item.get("blocked_reason"),
            "criterion": item.get("criterion"),
            "evidence": item.get("evidence"),
        }
        for item in criteria
        if item.get("state") != "passed"
    ]


def _decision(
    blockers: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    *,
    runtime_default_enabled: bool = False,
) -> str:
    if conflicts:
        return "default_on_admission_restatement_conflicting_evidence"
    if blockers:
        return "default_on_admission_restatement_still_blocked"
    if runtime_default_enabled:
        return "default_on_admission_restatement_superseded_by_default_on_runtime"
    return "default_on_admission_restatement_ready_for_runtime_design"


def _headline(decision: str, blockers: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> str:
    if decision == "default_on_admission_restatement_ready_for_runtime_design":
        return (
            "Default-on admission evidence is restated from committed authority and is ready for a "
            "separate runtime-design gate; runtime defaults remain off."
        )
    if decision == "default_on_admission_restatement_superseded_by_default_on_runtime":
        return (
            "Default-on admission evidence is restated from committed authority and has been superseded by "
            "the default-on fact-authority runtime; value reveal remains separately gated and default-off."
        )
    if decision == "default_on_admission_restatement_conflicting_evidence":
        reasons = ", ".join(item["reason"] for item in conflicts)
        return f"Default-on admission restatement found conflicting committed evidence: {reasons}."
    reasons = ", ".join(str(item["reason"]) for item in blockers)
    return f"Default-on admission restatement remains blocked: {reasons}."


def _read_report(path: Path) -> dict[str, Any]:
    display = _repo_display_path(path)
    if not path.exists():
        return {"status": "missing", "path": display}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return {"status": "unreadable", "path": display}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "malformed_json", "path": display, "text": text}
    if not isinstance(value, dict):
        return {"status": "not_json_object", "path": display, "text": text}
    return {
        "status": "loaded",
        "path": display,
        "text": text,
        "report": value,
        "schema_id": value.get("schema_id"),
        "decision": value.get("decision"),
    }


def _source_texts(source_root: Path) -> dict[str, str]:
    files = {
        "config": source_root / "backend" / "app" / "core" / "config.py",
        "bridge": (
            source_root
            / "backend"
            / "app"
            / "services"
            / "layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py"
        ),
        "sidecar": source_root / "backend" / "app" / "services" / "layer3_sec_xbrl_sidecar.py",
        "api_tests": source_root / "backend" / "tests" / "test_layer3_api.py",
        "sidecar_tests": source_root / "backend" / "tests" / "test_sec_xbrl_sidecar.py",
    }
    result = {}
    for name, path in files.items():
        try:
            result[name] = path.read_text(encoding="utf-8")
        except OSError:
            result[name] = ""
    return result


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


def _live_proof_defaults_off(live_defaults: Mapping[str, Any]) -> bool:
    return (
        live_defaults.get("sec_live_network_default_enabled") is False
        and live_defaults.get("arelle_fact_authority_cutover_default_enabled") is False
        and live_defaults.get("arelle_value_reveal_default_enabled") is False
    )


def _live_proof_safety_defaults_off(live_defaults: Mapping[str, Any]) -> bool:
    return (
        live_defaults.get("sec_live_network_default_enabled") is False
        and live_defaults.get("arelle_value_reveal_default_enabled") is False
    )


def _redaction_scan(texts: Iterable[str]) -> dict[str, Any]:
    hits = {
        "raw_accession_found": False,
        "raw_cik_found": False,
        "raw_sec_url_found": False,
        "raw_local_path_found": False,
        "raw_operator_contact_found": False,
        "raw_value_magnitude_found": False,
    }
    for text in texts:
        hits["raw_accession_found"] = hits["raw_accession_found"] or bool(RAW_ACCESSION_RE.search(text))
        hits["raw_cik_found"] = hits["raw_cik_found"] or bool(RAW_CIK_FIELD_RE.search(text))
        hits["raw_sec_url_found"] = hits["raw_sec_url_found"] or bool(SEC_URL_RE.search(text))
        hits["raw_local_path_found"] = hits["raw_local_path_found"] or bool(LOCAL_PATH_RE.search(text))
        hits["raw_operator_contact_found"] = hits["raw_operator_contact_found"] or bool(
            OPERATOR_CONTACT_RE.search(text)
        )
        hits["raw_value_magnitude_found"] = hits["raw_value_magnitude_found"] or bool(
            RAW_DECIMAL_MAGNITUDE_RE.search(text)
        )
    return {"passed": not any(hits.values()), **hits}


def _redaction_summary(redaction: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity_hash_only": redaction.get("identity_hash_only"),
        "raw_accessions_committed": redaction.get("raw_accessions_committed"),
        "raw_sec_urls_committed": redaction.get("raw_sec_urls_committed"),
        "raw_values_committed": redaction.get("raw_values_committed"),
        "local_storage_roots_committed": redaction.get("local_storage_roots_committed"),
    }


def _non_goal_summary(non_goals: Mapping[str, Any]) -> dict[str, Any]:
    keys = [
        "operator_value_reveal_enabled",
        "default_on_value_reveal_claimed",
        "runtime_default_changed",
        "live_sec_network_run_performed",
        "source_acquisition_performed",
        "arelle_subprocess_invoked",
        "production_readiness_claimed",
        "final_financial_statement_semantics_claimed",
        "cross_company_comparability_claimed",
        "raw_values_committed",
        "raw_identity_committed",
    ]
    return {key: non_goals.get(key) for key in keys if key in non_goals}


def _contains_any(sources: Mapping[str, str], text: str) -> bool:
    return any(_contains(value, text) for value in sources.values())


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
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
