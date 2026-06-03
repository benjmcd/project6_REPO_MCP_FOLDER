from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
ASSESSMENT = Path(__file__).resolve().parent
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from app.services.layer3_sec_xbrl_canonical_concepts import (  # noqa: E402
    REPORT_SCHEMA_ID,
    build_redacted_comparability_report,
    canonical_concept_inventory,
    report_redaction_scan_payload,
)
from app.services.layer3_utils import stable_hash  # noqa: E402
from sec_xbrl_diagnostic_framework import blocking_reasons as _blocking_reasons  # noqa: E402
from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import report_envelope as _report_envelope  # noqa: E402
from sec_xbrl_report_redaction import strip_residual_magnitude_fields  # noqa: E402
from sec_xbrl_runtime_posture import (  # noqa: E402
    committed_runtime_posture,
    runtime_posture_criterion_evidence,
    runtime_posture_criterion_passed,
)


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-canonical-comparability-report.json")
TARGET = "sec_xbrl_canonical_cross_company_comparability_validate_only_v1"
NEXT_SLICE = "sec_xbrl_canonical_projection_artifact_design_after_prerequisites_v1"
REFERENCE_ISSUER_RESULTS = (
    {"issuer_ref": "redacted-reference-issuer-a", "primary_taxonomy": "ifrs-full", "resolved": 21, "absent": 1},
    {"issuer_ref": "redacted-reference-issuer-b", "primary_taxonomy": "ifrs-full", "resolved": 21, "absent": 1},
    {"issuer_ref": "redacted-reference-issuer-c", "primary_taxonomy": "us-gaap", "resolved": 19, "absent": 3},
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL canonical comparability diagnostic. It does not fetch SEC data, "
            "invoke Arelle, reveal values, mutate runtime defaults, or write runtime artifacts."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(source_root=ROOT)
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    source_root: Path,
    issuer_bundles: Sequence[Mapping[str, Any]] | None = None,
    fiscal_year: int | str | None = None,
) -> dict[str, Any]:
    runtime_posture = committed_runtime_posture(source_root=source_root)
    if issuer_bundles is None:
        report = _reference_summary_report(runtime_posture=runtime_posture)
    else:
        report = build_redacted_comparability_report(issuer_bundles=issuer_bundles, fiscal_year=fiscal_year)
        report["source_mode"] = "supplied_governed_source_bundles"
        report["criteria"] = _criteria(
            report=report,
            runtime_posture=runtime_posture,
            reference_summary_mode=False,
        )
        report["blocking_reasons"] = _blocking_reasons(report["criteria"])
        report["decision"] = (
            "canonical_comparability_validate_only_ready"
            if not report["blocking_reasons"]
            else "canonical_comparability_validate_only_blocked"
        )
        report["next_slice"] = NEXT_SLICE if not report["blocking_reasons"] else "canonical_comparability_remediation_v1"
    _mark_residual_magnitudes_redacted(report)
    report = strip_residual_magnitude_fields(report)
    report["redaction"] = report_redaction_scan_payload(report)
    return report


def _mark_residual_magnitudes_redacted(report: dict[str, Any]) -> None:
    summary = report.get("summary")
    if isinstance(summary, dict):
        summary.pop("statement_identity_residuals_committed_as_magnitudes_only", None)
        summary["statement_identity_residual_magnitudes_redacted"] = True


def _reference_summary_report(*, runtime_posture: Mapping[str, Any]) -> dict[str, Any]:
    concept_inventory = canonical_concept_inventory()
    issuer_summaries = [
        {
            "issuer_hash": stable_hash({"issuer_ref": item["issuer_ref"]})[:24],
            "primary_taxonomy": item["primary_taxonomy"],
            "period_class": "FY",
            "headline_canonical_defined": len(concept_inventory),
            "headline_canonical_resolved": item["resolved"],
            "headline_canonical_legitimately_absent": item["absent"],
        }
        for item in REFERENCE_ISSUER_RESULTS
    ]
    resolved = sum(int(item["headline_canonical_resolved"]) for item in issuer_summaries)
    absent = sum(int(item["headline_canonical_legitimately_absent"]) for item in issuer_summaries)
    cell_count = len(concept_inventory) * len(issuer_summaries)
    report: dict[str, Any] = _report_envelope(
        schema_id=REPORT_SCHEMA_ID,
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision="canonical_comparability_validate_only_ready",
        source_mode="redacted_reference_summary_plus_committed_registry",
        validate_only=True,
        live_network_used=False,
        arelle_invoked=False,
        value_reveal_performed=False,
        runtime_defaults_changed=False,
        coverage_framing="headline_canonical_resolved_over_defined_only_not_filing_wide",
        canonical_concept_defined_count=len(concept_inventory),
        issuer_hash_count=len(issuer_summaries),
        summary={
            "headline_canonical_cell_count": cell_count,
            "headline_canonical_resolved_count": resolved,
            "headline_canonical_legitimately_absent_count": absent,
            "headline_canonical_unexplained_gap_count": cell_count - resolved - absent,
            "statement_identity_residuals_reference_within_tolerance": True,
            "statement_identity_residual_magnitudes_redacted": True,
        },
        canonical_concepts=concept_inventory,
        per_issuer=issuer_summaries,
        statement_identity_residuals=_reference_identity_residuals(),
        criteria=[],
        blocking_reasons=[],
        non_goals_preserved={
            "default_on_readiness_claimed": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_currency_conversion_claimed": False,
            "statement_assembly_claimed": False,
            "linkbase_relationships_required_or_consumed": False,
        },
    )
    report["criteria"] = _criteria(
        report=report,
        runtime_posture=runtime_posture,
        reference_summary_mode=True,
    )
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = "canonical_comparability_validate_only_blocked"
        report["next_slice"] = "canonical_comparability_remediation_v1"
    return report


def _reference_identity_residuals() -> list[dict[str, Any]]:
    return [
        _reference_identity("current_assets_plus_noncurrent_assets_equals_total_assets"),
        _reference_identity("total_liabilities_plus_equity_equals_total_assets"),
        _reference_identity("derived_total_liabilities_equals_assets_minus_equity_and_split"),
        _reference_identity("revenue_minus_cost_of_sales_equals_gross_profit"),
        _reference_identity("current_liabilities_plus_noncurrent_liabilities_equals_total_liabilities"),
    ]


def _reference_identity(identity_id: str) -> dict[str, Any]:
    return {
        "identity_id": identity_id,
        "source_mode": "redacted_reference_summary",
        "residual_abs": "0",
        "relative_magnitude": "0E+2",
        "within_tolerance": True,
    }


def _criteria(
    *,
    report: Mapping[str, Any],
    runtime_posture: Mapping[str, Any],
    reference_summary_mode: bool,
) -> list[dict[str, Any]]:
    redaction = report_redaction_scan_payload(report)
    summary = dict(report.get("summary") or {})
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            runtime_posture_criterion_passed(runtime_posture),
            runtime_posture_criterion_evidence(runtime_posture),
            "canonical_comparability_defaults_not_off",
        ),
        _criterion(
            "canonical_registry_is_statement_organized_and_bounded",
            int(report.get("canonical_concept_defined_count") or 0) == 22,
            {
                "canonical_concept_defined_count": report.get("canonical_concept_defined_count"),
                "coverage_framing": report.get("coverage_framing"),
            },
            "canonical_comparability_registry_not_bounded",
        ),
        _criterion(
            "headline_coverage_is_honestly_framed",
            summary.get("headline_canonical_unexplained_gap_count") == 0
            and report.get("coverage_framing") == "headline_canonical_resolved_over_defined_only_not_filing_wide",
            {
                "headline_canonical_cell_count": summary.get("headline_canonical_cell_count"),
                "headline_canonical_resolved_count": summary.get("headline_canonical_resolved_count"),
                "headline_canonical_legitimately_absent_count": summary.get(
                    "headline_canonical_legitimately_absent_count"
                ),
                "reference_summary_mode": reference_summary_mode,
            },
            "canonical_comparability_coverage_overclaimed_or_incomplete",
        ),
        _criterion(
            "redaction_clean",
            redaction.get("passed") is True,
            redaction,
            "canonical_comparability_report_redaction_failed",
        ),
        _criterion(
            "validate_only_non_goals_preserved",
            report.get("validate_only") is True
            and report.get("live_network_used") is False
            and report.get("arelle_invoked") is False
            and report.get("value_reveal_performed") is False
            and report.get("runtime_defaults_changed") is False
            and non_goals.get("production_readiness_claimed") is False
            and non_goals.get("final_financial_statement_semantics_claimed") is False
            and non_goals.get("cross_company_currency_conversion_claimed") is False
            and non_goals.get("statement_assembly_claimed") is False,
            {
                "validate_only": report.get("validate_only"),
                "live_network_used": report.get("live_network_used"),
                "arelle_invoked": report.get("arelle_invoked"),
                "value_reveal_performed": report.get("value_reveal_performed"),
                "runtime_defaults_changed": report.get("runtime_defaults_changed"),
                "non_goals_preserved": non_goals,
            },
            "canonical_comparability_validate_only_boundary_regressed",
        ),
    ]


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return "<redacted-output-path>"


if __name__ == "__main__":
    raise SystemExit(main())
