from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json")
DEFAULT_GATE_REPORT = Path("diagnostics/assessment/sec-xbrl-default-on-gate-report.json")

REQUIRED_ROLLBACK_SIGNALS = {
    "missing_sidecar": "arelle_sidecar_receipt_required",
    "lineage_mismatch": "sec_edgar_html_inline_xbrl_fact_material_bridge_arelle_sidecar_lineage_mismatch",
    "value_store_missing": "sec_edgar_arelle_sidecar_internal_value_store_missing",
    "value_store_not_persisted": "sec_edgar_arelle_sidecar_internal_value_store_not_persisted",
    "value_store_lineage_mismatch": "sec_edgar_arelle_sidecar_internal_value_store_lineage_mismatch",
    "value_store_hash_mismatch": "sec_edgar_arelle_sidecar_internal_value_store_hash_mismatch",
    "taxonomy_unavailable": "taxonomy_package_unavailable",
    "redaction_violation": "raw_authority_exposed",
}

REQUIRED_TEST_SIGNALS = {
    "arelle_absent": "test_sec_xbrl_sidecar_fails_closed_when_arelle_is_absent",
    "missing_sidecar": "test_layer3_api_blocks_sec_edgar_html_inline_xbrl_fact_material_arelle_cutover_without_sidecar",
    "lineage_mismatch": "test_layer3_api_rejects_sec_edgar_html_inline_xbrl_fact_material_arelle_cutover_lineage_mismatch",
    "operator_value_gate": "test_layer3_api_reveals_sec_edgar_arelle_values_only_through_governed_sibling_endpoint",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL default-on admission review. Produces an evidence packet for the "
            "default-on candidate without changing runtime defaults."
        )
    )
    parser.add_argument("--gate-report", default=str(DEFAULT_GATE_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    report = build_report(gate_report_path=_resolve_path(args.gate_report), source_root=ROOT)
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(*, gate_report_path: Path, source_root: Path) -> dict[str, Any]:
    gate = _read_json(gate_report_path)
    sources = _source_text(source_root)
    default_off = _contains(
        sources["config"],
        'layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=False,',
    )
    default_on = _contains(
        sources["config"],
        'layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=True,',
    )
    runtime_default_already_enabled = default_on and not default_off
    rollback = {
        name: {
            "signal": signal,
            "present": _contains_any(sources, signal),
        }
        for name, signal in REQUIRED_ROLLBACK_SIGNALS.items()
    }
    tests = {
        name: {
            "test_signal": signal,
            "present": _contains_any(sources, signal),
        }
        for name, signal in REQUIRED_TEST_SIGNALS.items()
    }
    operator_gate = {
        "policy_id_present": _contains_any(sources, "sec_edgar_operator_surface_gated_value_reveal_v1"),
        "max_records_cap_present": _contains_any(sources, "VALUE_REVEAL_MAX_RECORDS_LIMIT = 50"),
        "confirmation_required": _contains_any(sources, "sec_edgar_arelle_value_reveal_operator_confirmation_required"),
        "feature_flag_required": _contains_any(sources, "sec_edgar_arelle_value_reveal_feature_flag_disabled"),
    }
    non_admissions = {
        "candidate_b_sec_routing_not_admitted": _contains_any(
            sources,
            '"candidate_b_pdf_only_routing_performed": False',
        )
        or _contains_any(sources, '"candidate_b_default_scope_changed": False'),
        "final_financial_statement_semantics_not_admitted": _contains_any(
            sources,
            '"final_financial_statement_semantics_claimed": False',
        )
        or _contains_any(sources, '"financial_statement_semantics_enabled": False'),
        "cross_company_comparability_not_admitted": _contains_any(
            sources,
            '"cross_company_comparability_claimed": False',
        )
        or _contains_any(sources, '"cross_company_comparability_enabled": False'),
    }
    criteria = [
        _criterion(
            "default_on_candidate_gate_passed",
            gate.get("decision") == "default_on_admitted_candidate" and gate.get("ready_for_default_on") is True,
            {
                "gate_report": _repo_display_path(gate_report_path),
                "decision": gate.get("decision"),
                "summary": gate.get("summary"),
            },
            "admission_review_gate_not_admitted",
        ),
        _criterion(
            "runtime_default_posture_recorded",
            default_off or runtime_default_already_enabled,
            {
                "config_file": "backend/app/core/config.py",
                "flag_default_false": default_off,
                "flag_default_true": runtime_default_already_enabled,
                "posture": (
                    "default_on_runtime_enabled_by_follow_on_slice"
                    if runtime_default_already_enabled
                    else "default_off_admission_candidate"
                ),
            },
            "admission_review_runtime_default_posture_unrecognized",
        ),
        _criterion(
            "rollback_fail_closed_signals_present",
            all(item["present"] for item in rollback.values()),
            rollback,
            "admission_review_rollback_signals_missing",
        ),
        _criterion(
            "focused_fail_closed_tests_present",
            all(item["present"] for item in tests.values()),
            tests,
            "admission_review_focused_tests_missing",
        ),
        _criterion(
            "operator_value_reveal_remains_gated",
            all(operator_gate.values()),
            operator_gate,
            "admission_review_operator_value_reveal_gate_missing",
        ),
        _criterion(
            "standing_non_admissions_preserved",
            all(non_admissions.values()),
            non_admissions,
            "admission_review_non_admission_signal_missing",
        ),
    ]
    blockers = [
        {"reason": item["blocked_reason"], "criterion": item["criterion"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    admitted = not blockers and not runtime_default_already_enabled
    superseded = not blockers and runtime_default_already_enabled
    return {
        "schema_id": "diagnostics.sec_xbrl_default_on_admission_review.v1",
        "target": "sec_edgar_arelle_default_off_to_default_on_admission_review_v1",
        "decision": (
            "admission_review_superseded_by_default_on_runtime"
            if superseded
            else "admission_review_passed" if admitted else "admission_review_blocked"
        ),
        "ready_for_default_on_runtime_slice": admitted,
        "headline": _headline(admitted=admitted, superseded=superseded, blockers=blockers),
        "source_reports": {"default_on_gate": _repo_display_path(gate_report_path)},
        "criteria": criteria,
        "blocking_reasons": blockers,
        "rollback_criteria": [
            "missing or stale Arelle sidecar receipt blocks; no regex fallback while cutover is enabled",
            "sidecar, parser, source artifact, and regex authority lineage mismatch blocks",
            "missing, stale, or lineage-mismatched internal value store blocks",
            "taxonomy/cache/Arelle extraction unavailability blocks sidecar creation",
            "redaction violation blocks response/report projection",
        ],
        "non_goals_preserved": {
            "runtime_default_changed_by_admission_review": False,
            "runtime_default_enabled_by_follow_on_runtime_slice": runtime_default_already_enabled,
            "bridge_gate_b_product_package_ui_mutated": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
            "operator_value_reveal_default_enabled": False,
            "rag_vector_model_provider_auth_behavior_added": False,
        },
        "next_slice": (
            "sec_edgar_operator_surface_gated_value_reveal_v1"
            if superseded
            else
            "sec_edgar_arelle_fact_authority_default_on_runtime_v1"
            if admitted
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


def _source_text(source_root: Path) -> dict[str, str]:
    files = {
        "config": source_root / "backend" / "app" / "core" / "config.py",
        "bridge": source_root / "backend" / "app" / "services" / "layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py",
        "sidecar": source_root / "backend" / "app" / "services" / "layer3_sec_xbrl_sidecar.py",
        "operator_surface": source_root / "backend" / "app" / "services" / "layer3_sec_edgar_operator_product_surface.py",
        "api_tests": source_root / "backend" / "tests" / "test_layer3_api.py",
        "sidecar_tests": source_root / "backend" / "tests" / "test_sec_xbrl_sidecar.py",
    }
    return {name: path.read_text(encoding="utf-8") for name, path in files.items()}


def _contains_any(sources: Mapping[str, str], text: str) -> bool:
    return any(_contains(value, text) for value in sources.values())


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _headline(*, admitted: bool, superseded: bool, blockers: list[dict[str, Any]]) -> str:
    if superseded:
        return (
            "Default-on admission evidence is recorded, and the runtime default has already been enabled by the "
            "follow-on runtime slice; this report is no longer a pre-cutover PASS packet."
        )
    if admitted:
        return "Default-on Arelle cutover passed admission review as a candidate for the runtime-default slice."
    reasons = ", ".join(reason["reason"] for reason in blockers)
    return f"Default-on Arelle admission review is blocked: {reasons}."


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
