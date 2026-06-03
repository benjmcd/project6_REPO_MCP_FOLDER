from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402

DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json")
DEFAULT_DEFAULT_POSTURE_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-default-posture-decision-report.json"
)
DEFAULT_BROADER_RELIABILITY_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json"
)
DEFAULT_REAL_PRODUCT_RUNNER_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json"
)
DEFAULT_VALUE_REVEAL_LIVE_PROOF_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json"
)

NEXT_SLICE = "sec_edgar_stratified_real_filing_validation_matrix_v1"
REQUIRED_STRATA = {
    "large_domestic_us_gaap",
    "small_mid_domestic_us_gaap",
    "foreign_private_ifrs_20f",
    "canadian_40f",
    "current_report_8k_sparse",
    "foreign_6k_sparse",
    "amendment_restatement",
    "no_inline_or_zero_fact_diagnostic",
}

RUNBOOK_CONTROLS = [
    "start_from_clean_project6_origin_main_worktree",
    "preserve_committed_safety_defaults",
    "require_explicit_live_sec_authorization",
    "use_isolated_off_repo_arelle_environment",
    "run_validate_only_preflight_before_live_work",
    "use_governed_sec_connector_and_source_artifacts",
    "require_coherent_sidecar_value_store_bridge_dataset_provenance_bundle",
    "use_explicit_operator_confirmation_for_value_reveal",
    "preserve_status_and_default_surface_redaction",
    "run_redaction_scan_before_reporting",
    "record_hashes_counts_forms_and_reason_codes_only",
    "stop_on_arelle_or_taxonomy_unavailability",
    "stop_on_redaction_or_identity_leak",
    "do_not_change_runtime_defaults_by_this_diagnostic",
]

STRATIFIED_MATRIX = [
    {
        "stratum": "large_domestic_us_gaap",
        "forms": ["10-K", "10-Q"],
        "minimum_issuer_hashes": 3,
        "purpose": "stress high-volume current-taxonomy domestic filers without making them the whole corpus",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "small_mid_domestic_us_gaap",
        "forms": ["10-K", "10-Q"],
        "minimum_issuer_hashes": 3,
        "purpose": "catch scale and disclosure-shape variance outside mega-cap domestic filers",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "foreign_private_ifrs_20f",
        "forms": ["20-F"],
        "minimum_issuer_hashes": 2,
        "purpose": "preserve IFRS and foreign-private-issuer coverage",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "canadian_40f",
        "forms": ["40-F"],
        "minimum_issuer_hashes": 1,
        "purpose": "preserve Canadian 40-F handling and cross-border taxonomy variance",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "current_report_8k_sparse",
        "forms": ["8-K"],
        "minimum_issuer_hashes": 3,
        "purpose": "exercise sparse current-report fact and product-path behavior",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "foreign_6k_sparse",
        "forms": ["6-K"],
        "minimum_issuer_hashes": 2,
        "purpose": "exercise sparse foreign report behavior without treating 20-F as sufficient",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "amendment_restatement",
        "forms": ["10-K/A", "10-Q/A", "20-F/A"],
        "minimum_issuer_hashes": 2,
        "purpose": "exercise amended filing lineage and restatement-like document shapes",
        "raw_issuer_examples_committed": False,
    },
    {
        "stratum": "no_inline_or_zero_fact_diagnostic",
        "forms": ["10-K", "10-Q", "8-K", "6-K"],
        "minimum_issuer_hashes": 2,
        "purpose": "keep genuine no-inline-marker diagnostics explicit and non-silent",
        "raw_issuer_examples_committed": False,
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL operator runbook and stratified matrix selection. This validate-only "
            "diagnostic reads committed redacted reports; it does not fetch SEC data, run Arelle, "
            "reveal values, or mutate defaults."
        )
    )
    parser.add_argument("--default-posture-report", default=str(DEFAULT_DEFAULT_POSTURE_REPORT))
    parser.add_argument("--broader-reliability-report", default=str(DEFAULT_BROADER_RELIABILITY_REPORT))
    parser.add_argument("--real-product-runner-report", default=str(DEFAULT_REAL_PRODUCT_RUNNER_REPORT))
    parser.add_argument("--value-reveal-live-proof-report", default=str(DEFAULT_VALUE_REVEAL_LIVE_PROOF_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        default_posture_report_path=_resolve_path(args.default_posture_report),
        broader_reliability_report_path=_resolve_path(args.broader_reliability_report),
        real_product_runner_report_path=_resolve_path(args.real_product_runner_report),
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
    default_posture_report_path: Path,
    broader_reliability_report_path: Path,
    real_product_runner_report_path: Path,
    value_reveal_live_proof_report_path: Path,
) -> dict[str, Any]:
    default_posture = _read_json(default_posture_report_path)
    broader = _read_json(broader_reliability_report_path)
    real_product = _read_json(real_product_runner_report_path)
    live_proof = _read_json(value_reveal_live_proof_report_path)

    selected_posture = dict(default_posture.get("selected_posture") or {})
    default_posture_recognized = _default_posture_recognized(
        default_posture=default_posture,
        selected_posture=selected_posture,
    )
    real_summary = dict(real_product.get("summary") or {})
    live_attempts = live_proof.get("attempts") if isinstance(live_proof.get("attempts"), list) else []
    strata = list(STRATIFIED_MATRIX)
    criteria = [
        _criterion(
            "explicit_operator_default_posture_recognized",
            default_posture_recognized,
            {
                "source_report": _repo_display_path(default_posture_report_path),
                "decision": default_posture.get("decision"),
                "selected_posture": selected_posture.get("posture"),
                "superseded_by_default_on_runtime": selected_posture.get(
                    "arelle_fact_authority_cutover_default_on_supersedes_selected_posture"
                )
                is True,
            },
            "operator_runbook_default_posture_not_selected",
        ),
        _criterion(
            "current_evidence_supports_operator_runbook",
            broader.get("decision") == "broader_corpus_reliability_admitted"
            and real_product.get("decision") == "real_corpus_default_on_validated"
            and real_product.get("gate_verdict") == "PASS"
            and _int(real_summary.get("supported_record_count")) >= 30
            and live_proof.get("decision")
            == "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings"
            and len(live_attempts) >= 2,
            {
                "broader_reliability_decision": broader.get("decision"),
                "real_product_decision": real_product.get("decision"),
                "real_product_supported_record_count": real_summary.get("supported_record_count"),
                "value_reveal_live_proof_decision": live_proof.get("decision"),
                "value_reveal_attempt_count": len(live_attempts),
            },
            "operator_runbook_current_evidence_not_ready",
        ),
        _criterion(
            "runbook_controls_are_defined",
            len(RUNBOOK_CONTROLS) >= 12
            and "preserve_committed_safety_defaults" in RUNBOOK_CONTROLS
            and "run_redaction_scan_before_reporting" in RUNBOOK_CONTROLS
            and "do_not_change_runtime_defaults_by_this_diagnostic" in RUNBOOK_CONTROLS,
            {"control_count": len(RUNBOOK_CONTROLS), "controls": RUNBOOK_CONTROLS},
            "operator_runbook_controls_incomplete",
        ),
        _criterion(
            "stratified_matrix_covers_required_axes",
            REQUIRED_STRATA.issubset({item["stratum"] for item in strata})
            and all(item.get("raw_issuer_examples_committed") is False for item in strata),
            {
                "required_strata": sorted(REQUIRED_STRATA),
                "selected_strata": [item["stratum"] for item in strata],
                "raw_issuer_examples_committed": False,
            },
            "operator_runbook_stratified_matrix_incomplete",
        ),
    ]
    blockers = [
        {"reason": item["blocked_reason"], "criterion": item["criterion"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    ready = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_operator_runbook_matrix_selection.v1",
        "target": "sec_edgar_operator_readiness_runbook_and_stratified_matrix_selection_v1",
        "decision": (
            "operator_runbook_and_stratified_matrix_selection_ready"
            if ready
            else "operator_runbook_and_stratified_matrix_selection_blocked"
        ),
        "headline": _headline(ready=ready, blockers=blockers),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "runbook_controls": RUNBOOK_CONTROLS,
        "selected_stratified_matrix": strata,
        "source_reports": {
            "default_posture": _repo_display_path(default_posture_report_path),
            "broader_reliability": _repo_display_path(broader_reliability_report_path),
            "real_product_runner": _repo_display_path(real_product_runner_report_path),
            "value_reveal_live_proof": _repo_display_path(value_reveal_live_proof_report_path),
        },
        "operator_policy": {
            "posture": "explicit_operator_only_default_off",
            "live_network_requires_explicit_authorization": True,
            "value_reveal_requires_explicit_operator_confirmation": True,
            "committed_reports_use_hashes_counts_forms_and_reason_codes_only": True,
            "raw_issuer_examples_committed": False,
            "raw_values_committed": False,
            "runtime_default_change_allowed": False,
        },
        "non_goals_preserved": {
            "live_sec_network_run_performed": False,
            "arelle_subprocess_invoked": False,
            "value_reveal_request_performed": False,
            "runtime_default_changed": False,
            "source_acquisition_performed": False,
            "dataset_created": False,
            "audit_receipt_created": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "next_slice": NEXT_SLICE if ready else "sec_edgar_operator_readiness_runbook_and_stratified_matrix_selection_v1",
    }


def _headline(*, ready: bool, blockers: list[dict[str, Any]]) -> str:
    if ready:
        return (
            "Operator runbook controls and the next stratified SEC XBRL validation matrix are selected "
            "for the explicit-operator-only default-off posture."
        )
    reasons = ", ".join(reason["reason"] for reason in blockers)
    return f"Operator runbook and stratified matrix selection is blocked: {reasons}."


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object at {_repo_display_path(path)}")
    return value


def _default_posture_recognized(
    *,
    default_posture: Mapping[str, Any],
    selected_posture: Mapping[str, Any],
) -> bool:
    pre_runtime_selected = (
        default_posture.get("decision") == "explicit_operator_only_default_off_selected"
        and selected_posture.get("arelle_fact_authority_cutover_default_enabled") is False
    )
    superseded_by_runtime_default_on = (
        default_posture.get("decision") == "explicit_operator_only_default_off_superseded_by_default_on_runtime"
        and selected_posture.get("arelle_fact_authority_cutover_default_enabled") is False
        and selected_posture.get("arelle_fact_authority_cutover_default_on_supersedes_selected_posture") is True
    )
    return (
        selected_posture.get("posture") == "explicit_operator_only_default_off"
        and selected_posture.get("arelle_value_reveal_default_enabled") is False
        and selected_posture.get("sec_live_network_default_enabled") is False
        and (pre_runtime_selected or superseded_by_runtime_default_on)
    )


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
