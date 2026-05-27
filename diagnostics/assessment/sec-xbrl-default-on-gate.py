from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-default-on-gate-report.json")
DEFAULT_SIDECAR_REPORT = Path("diagnostics/assessment/sec-xbrl-sidecar-report.json")
DEFAULT_COMPLETENESS_REPORT = Path("diagnostics/assessment/sec-xbrl-completeness-report.json")
DEFAULT_BRIDGE_REPORT = Path("diagnostics/assessment/sec-xbrl-bridge-cutover-report.json")
DEFAULT_VALUE_REPORT = Path("diagnostics/assessment/sec-xbrl-value-reveal-report.json")
DEFAULT_EXPANDED_VALUE_REPORT = Path("diagnostics/assessment/sec-xbrl-expanded-value-report.json")
DEFAULT_VALUE_BRIDGE_REPORT = Path("diagnostics/assessment/sec-xbrl-expanded-value-bridge-report.json")

REQUIRED_FORMS = {"10-K", "10-Q", "20-F", "40-F", "6-K", "8-K"}
VALUE_CORRECTNESS_FORMS = {"10-K", "10-Q"}
MIN_REAL_FILINGS = 12
MIN_ISSUER_HASHES = 6
MIN_COMPANYFACTS_MATCH_RATE = 0.99


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL default-on corpus expansion gate. This diagnostic reads committed "
            "redacted reports only; it does not acquire filings, run Arelle, mutate runtime, "
            "or admit default-on behavior."
        )
    )
    parser.add_argument("--sidecar-report", default=str(DEFAULT_SIDECAR_REPORT))
    parser.add_argument("--completeness-report", default=str(DEFAULT_COMPLETENESS_REPORT))
    parser.add_argument("--bridge-report", default=str(DEFAULT_BRIDGE_REPORT))
    parser.add_argument(
        "--value-report",
        action="append",
        default=[str(DEFAULT_VALUE_REPORT), str(DEFAULT_EXPANDED_VALUE_REPORT)],
    )
    parser.add_argument("--value-bridge-report", default=str(DEFAULT_VALUE_BRIDGE_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        sidecar_report_path=_resolve_path(args.sidecar_report),
        completeness_report_path=_resolve_path(args.completeness_report),
        bridge_report_path=_resolve_path(args.bridge_report),
        value_report_paths=[_resolve_path(item) for item in args.value_report],
        value_bridge_report_path=_resolve_path(args.value_bridge_report),
    )
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    sidecar_report_path: Path,
    completeness_report_path: Path,
    bridge_report_path: Path,
    value_report_paths: list[Path],
    value_bridge_report_path: Path,
) -> dict[str, Any]:
    sidecar = _read_json(sidecar_report_path)
    completeness = _read_json(completeness_report_path)
    bridge = _read_json(bridge_report_path)
    values = [_read_json(path) for path in value_report_paths]
    value_bridge = _read_json(value_bridge_report_path)

    sidecar_corpus = dict(sidecar.get("corpus_summary") or {})
    completeness_summary = dict(completeness.get("summary") or {})
    bridge_summary = dict(bridge.get("summary") or {})
    value_summary = _combined_companyfacts_value_summary(values)
    value_bridge_summary = dict(value_bridge.get("summary") or {})

    forms = set((sidecar_corpus.get("forms") or {}).keys())
    value_forms_with_oracle = _forms_with_companyfacts_value_oracle(
        row for value in values for row in (value.get("per_fixture") or [])
    )
    value_bridge_forms = _forms_from_rows(value_bridge.get("per_fixture") or [])
    criteria = [
        _criterion(
            "corpus_breadth",
            _int(sidecar_corpus.get("real_filing_count")) >= MIN_REAL_FILINGS
            and _int(sidecar_corpus.get("issuer_hash_count")) >= MIN_ISSUER_HASHES
            and REQUIRED_FORMS.issubset(forms),
            {
                "real_filing_count": sidecar_corpus.get("real_filing_count"),
                "issuer_hash_count": sidecar_corpus.get("issuer_hash_count"),
                "forms": sidecar_corpus.get("forms"),
                "required_forms": sorted(REQUIRED_FORMS),
            },
            "default_on_gate_corpus_breadth_missing",
        ),
        _criterion(
            "independent_count_and_dts_completeness",
            completeness_summary.get("independent_count_all_reconciled") is True
            and _int(completeness_summary.get("concept_unresolved_from_dts_count"), default=-1) == 0
            and completeness_summary.get("taxonomy_package_loaded_all_ready_rows") is True,
            {
                "real_filing_count": completeness_summary.get("real_filing_count"),
                "arelle_resolved_fact_count": completeness_summary.get("arelle_resolved_fact_count"),
                "independent_inline_fact_count": completeness_summary.get("independent_inline_fact_count"),
                "independent_count_all_reconciled": completeness_summary.get("independent_count_all_reconciled"),
                "concept_unresolved_from_dts_count": completeness_summary.get("concept_unresolved_from_dts_count"),
                "taxonomy_package_loaded_all_ready_rows": completeness_summary.get(
                    "taxonomy_package_loaded_all_ready_rows"
                ),
            },
            "default_on_gate_completeness_or_dts_unproven",
        ),
        _criterion(
            "bridge_cutover_parity",
            bridge.get("verdict") == "trustworthy_for_gated_cutover"
            and bridge_summary.get("bridge_matches_sidecar_all_ready_rows") is True
            and _int(bridge_summary.get("blocked_count"), default=-1) == 0
            and _int(bridge_summary.get("sidecar_resolved_fact_count"), default=-1)
            == _int(completeness_summary.get("arelle_resolved_fact_count"), default=-2),
            {
                "verdict": bridge.get("verdict"),
                "real_filing_count": bridge_summary.get("real_filing_count"),
                "inline_bridge_ready_count": bridge_summary.get("inline_bridge_ready_count"),
                "zero_inline_not_applicable_count": bridge_summary.get("zero_inline_not_applicable_count"),
                "blocked_count": bridge_summary.get("blocked_count"),
                "bridge_fact_count": bridge_summary.get("bridge_fact_count"),
                "sidecar_resolved_fact_count": bridge_summary.get("sidecar_resolved_fact_count"),
                "required_typed_fields_present_all_ready_rows": bridge_summary.get(
                    "required_typed_fields_present_all_ready_rows"
                ),
            },
            "default_on_gate_bridge_parity_unproven",
        ),
        _criterion(
            "internal_value_materialization_full_corpus",
            value_bridge.get("verdict") == "trustworthy_for_gated_cutover"
            and _int(value_bridge_summary.get("real_filing_count"), default=-1)
            >= _int(sidecar_corpus.get("real_filing_count"), default=MIN_REAL_FILINGS)
            and _int(value_bridge_summary.get("sidecar_resolved_fact_count"), default=-1)
            >= _int(completeness_summary.get("arelle_resolved_fact_count"), default=-2)
            and _int(value_bridge_summary.get("blocked_count"), default=-1) == 0
            and value_bridge_summary.get("bridge_matches_sidecar_all_ready_rows") is True
            and _int(value_bridge_summary.get("effective_value_nonempty_count")) > 0
            and REQUIRED_FORMS.issubset(value_bridge_forms),
            {
                "verdict": value_bridge.get("verdict"),
                "real_filing_count": value_bridge_summary.get("real_filing_count"),
                "minimum_real_filing_count": sidecar_corpus.get("real_filing_count"),
                "sidecar_resolved_fact_count": value_bridge_summary.get("sidecar_resolved_fact_count"),
                "minimum_sidecar_resolved_fact_count": completeness_summary.get("arelle_resolved_fact_count"),
                "bridge_matches_sidecar_all_ready_rows": value_bridge_summary.get(
                    "bridge_matches_sidecar_all_ready_rows"
                ),
                "blocked_count": value_bridge_summary.get("blocked_count"),
                "forms": sorted(value_bridge_forms),
                "required_forms": sorted(REQUIRED_FORMS),
                "effective_value_nonempty_count": value_bridge_summary.get("effective_value_nonempty_count"),
                "effective_value_empty_count": value_bridge_summary.get("effective_value_empty_count"),
            },
            "default_on_gate_internal_values_not_proven_on_expanded_corpus",
        ),
        _criterion(
            "companyfacts_effective_value_correctness",
            float(value_summary.get("match_rate") or 0) >= MIN_COMPANYFACTS_MATCH_RATE
            and VALUE_CORRECTNESS_FORMS.issubset(value_forms_with_oracle),
            {
                "oracle": value_summary.get("oracle"),
                "match_count": value_summary.get("match_count"),
                "compared_count": value_summary.get("compared_count"),
                "match_rate": value_summary.get("match_rate"),
                "forms_with_value_oracle": sorted(value_forms_with_oracle),
                "required_forms_with_value_oracle": sorted(VALUE_CORRECTNESS_FORMS),
            },
            "default_on_gate_companyfacts_value_correctness_incomplete",
        ),
    ]
    blockers = [
        {"reason": item["blocked_reason"], "criterion": item["criterion"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    admitted = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_default_on_corpus_expansion_gate.v1",
        "target": "sec_edgar_arelle_default_on_corpus_expansion_gate_v1",
        "decision": "default_on_admitted_candidate" if admitted else "default_on_not_admitted",
        "ready_for_default_on": admitted,
        "headline": _headline(admitted=admitted, blockers=blockers),
        "source_reports": {
            "sidecar": _repo_display_path(sidecar_report_path),
            "completeness": _repo_display_path(completeness_report_path),
            "bridge": _repo_display_path(bridge_report_path),
            "value": [_repo_display_path(path) for path in value_report_paths],
            "value_bridge": _repo_display_path(value_bridge_report_path),
        },
        "criteria": criteria,
        "blocking_reasons": blockers,
        "summary": {
            "real_filing_count": sidecar_corpus.get("real_filing_count"),
            "issuer_hash_count": sidecar_corpus.get("issuer_hash_count"),
            "forms": sidecar_corpus.get("forms"),
            "arelle_resolved_fact_count": completeness_summary.get("arelle_resolved_fact_count"),
            "bridge_fact_count": bridge_summary.get("bridge_fact_count"),
            "value_bridge_fact_count": value_bridge_summary.get("bridge_fact_count"),
            "companyfacts_value_match_rate": value_summary.get("match_rate"),
            "companyfacts_value_compared_count": value_summary.get("compared_count"),
            "companyfacts_value_match_count": value_summary.get("match_count"),
        },
        "non_goals_preserved": {
            "runtime_default_changed": False,
            "bridge_gate_b_product_package_ui_mutated": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "raw_identity_urls_paths_storage_roots_committed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
        },
        "next_slice": (
            "sec_edgar_arelle_expanded_value_materialization_and_companyfacts_gate_v1"
            if not admitted
            else "sec_edgar_arelle_default_off_to_default_on_admission_review_v1"
        ),
    }


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _combined_companyfacts_value_summary(reports: list[Mapping[str, Any]]) -> dict[str, Any]:
    compared = 0
    matched = 0
    oracles: set[str] = set()
    for report in reports:
        summary = dict(report.get("companyfacts_effective_value_correctness") or {})
        compared += _int(summary.get("compared_count"))
        matched += _int(summary.get("match_count"))
        if summary.get("oracle"):
            oracles.add(str(summary["oracle"]))
    return {
        "oracle": sorted(oracles),
        "match_count": matched,
        "compared_count": compared,
        "match_rate": round(matched / compared, 4) if compared else None,
        "values_redacted_in_report": True,
        "identity_redacted": True,
    }


def _forms_with_companyfacts_value_oracle(rows: Any) -> set[str]:
    forms: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if _int(row.get("companyfacts_effective_value_compared_count")) > 0:
            forms.add(str(row.get("form") or "unknown"))
    return forms


def _forms_from_rows(rows: list[Any]) -> set[str]:
    return {str(row.get("form") or "unknown") for row in rows if isinstance(row, Mapping)}


def _int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _headline(*, admitted: bool, blockers: list[dict[str, Any]]) -> str:
    if admitted:
        return "Default-on Arelle cutover is admitted as a candidate by the current corpus gate."
    reasons = ", ".join(reason["reason"] for reason in blockers)
    return f"Default-on Arelle cutover is not admitted by the current corpus gate: {reasons}."


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
