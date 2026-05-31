from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from app.services.layer3_sec_xbrl_canonical_concepts import (  # noqa: E402
    COVERAGE_BREADTH_REPORT_SCHEMA_ID,
    canonical_concept_inventory,
    report_redaction_scan_payload,
)
from app.services.layer3_sec_xbrl_report_guards import rows_have_unique_required_key  # noqa: E402


DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-canonical-coverage-breadth-report.json")
TARGET = "sec_xbrl_canonical_coverage_breadth_validate_only_v1"
NEXT_SLICE = "sec_xbrl_sector_conditioned_canonical_families_deferred_design_v1"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL canonical coverage-breadth diagnostic. It does not fetch SEC data, "
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


def build_report(*, source_root: Path, sector_results: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    config_text = (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    report = _reference_summary_report(
        sector_results=list(sector_results or _reference_sector_results()),
        config_defaults_off=_config_defaults_off(config_text),
    )
    report["redaction"] = report_redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, config_defaults_off=_config_defaults_off(config_text))
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = "canonical_coverage_breadth_validate_only_blocked"
        report["next_slice"] = "canonical_coverage_breadth_remediation_v1"
    return report


def _reference_summary_report(
    *,
    sector_results: Sequence[Mapping[str, Any]],
    config_defaults_off: bool,
) -> dict[str, Any]:
    concept_inventory = canonical_concept_inventory()
    sectors = [_sector_summary(item) for item in sector_results]
    total_cells = sum(int(item["headline_canonical_cell_count"]) for item in sectors)
    total_direct = sum(int(item["direct_resolved_count"]) for item in sectors)
    total_derived = sum(int(item["derived_count"]) for item in sectors)
    total_absent = sum(int(item["legitimately_absent_count"]) for item in sectors)
    report: dict[str, Any] = {
        "schema_id": COVERAGE_BREADTH_REPORT_SCHEMA_ID,
        "target": TARGET,
        "decision": "canonical_coverage_breadth_validate_only_ready",
        "source_mode": "redacted_reference_sector_summary_plus_committed_registry",
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "coverage_framing": "headline_canonical_coverage_by_sector_class_not_filing_wide",
        "canonical_concept_defined_count": len(concept_inventory),
        "sector_class_count": len(sectors),
        "summary": {
            "headline_canonical_cell_count": total_cells,
            "direct_resolved_count": total_direct,
            "derived_count": total_derived,
            "covered_count_including_derived": total_direct + total_derived,
            "legitimately_absent_count": total_absent,
            "coverage_rate_including_derived": _rate(total_direct + total_derived, total_cells),
        },
        "canonical_concepts": concept_inventory,
        "sector_classes": sectors,
        "sector_structure_limitation": {
            "status": "known_limitation",
            "limitation": (
                "The current 22-concept headline industrial schema does not represent financial sector "
                "statement structures such as bank, insurer, or REIT statements."
            ),
            "deferred_design": "sector_conditioned_canonical_families_selected_by_sic_or_industry",
            "implementation_in_this_slice": False,
        },
        "criteria": [],
        "blocking_reasons": [],
        "redaction": {},
        "next_slice": NEXT_SLICE,
        "non_goals_preserved": {
            "default_on_readiness_claimed": False,
            "production_readiness_claimed": False,
            "filing_wide_canonicalization_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_currency_conversion_claimed": False,
            "sector_conditioned_families_implemented": False,
            "statement_assembly_claimed": False,
            "linkbase_relationships_required_or_consumed": False,
        },
    }
    report["criteria"] = _criteria(report=report, config_defaults_off=config_defaults_off)
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = "canonical_coverage_breadth_validate_only_blocked"
        report["next_slice"] = "canonical_coverage_breadth_remediation_v1"
    return report


def _reference_sector_results() -> tuple[dict[str, Any], ...]:
    return (
        {
            "sector_class": "industrial_commercial",
            "issuer_count": 10,
            "concept_counts": _industrial_concept_counts(),
        },
        {
            "sector_class": "financial_structure_limited",
            "issuer_count": 3,
            "concept_counts": _financial_concept_counts(),
        },
    )


def _industrial_concept_counts() -> list[dict[str, Any]]:
    return _concept_rows(
        issuer_count=10,
        counts={
            "Revenue[total]": (10, 0, 0),
            "CostOfSales[total]": (7, 0, 3),
            "GrossProfit[total]": (6, 0, 4),
            "OperatingIncome[total]": (9, 0, 1),
            "ProfitBeforeTax[total]": (9, 0, 1),
            "IncomeTaxExpense[total]": (10, 0, 0),
            "ProfitLoss[total]": (10, 0, 0),
            "ProfitLoss[parent]": (8, 0, 2),
            "EpsBasic[total]": (9, 0, 1),
            "EpsDiluted[total]": (9, 0, 1),
            "CashAndEquivalents[total]": (10, 0, 0),
            "CurrentAssets[total]": (10, 0, 0),
            "NoncurrentAssets[total]": (3, 7, 0),
            "TotalAssets[total]": (10, 0, 0),
            "CurrentLiabilities[total]": (10, 0, 0),
            "NoncurrentLiabilities[total]": (3, 7, 0),
            "TotalLiabilities[total]": (10, 0, 0),
            "Equity[total]": (10, 0, 0),
            "Equity[parent]": (10, 0, 0),
            "OperatingCashFlow[total]": (9, 0, 1),
            "InvestingCashFlow[total]": (8, 0, 2),
            "FinancingCashFlow[total]": (9, 0, 1),
        },
    )


def _financial_concept_counts() -> list[dict[str, Any]]:
    return _concept_rows(
        issuer_count=3,
        counts={
            "Revenue[total]": (3, 0, 0),
            "CostOfSales[total]": (0, 0, 3),
            "GrossProfit[total]": (0, 0, 3),
            "OperatingIncome[total]": (2, 0, 1),
            "ProfitBeforeTax[total]": (2, 0, 1),
            "IncomeTaxExpense[total]": (3, 0, 0),
            "ProfitLoss[total]": (3, 0, 0),
            "ProfitLoss[parent]": (3, 0, 0),
            "EpsBasic[total]": (3, 0, 0),
            "EpsDiluted[total]": (3, 0, 0),
            "CashAndEquivalents[total]": (3, 0, 0),
            "CurrentAssets[total]": (0, 0, 3),
            "NoncurrentAssets[total]": (0, 0, 3),
            "TotalAssets[total]": (3, 0, 0),
            "CurrentLiabilities[total]": (0, 0, 3),
            "NoncurrentLiabilities[total]": (0, 0, 3),
            "TotalLiabilities[total]": (3, 0, 0),
            "Equity[total]": (3, 0, 0),
            "Equity[parent]": (3, 0, 0),
            "OperatingCashFlow[total]": (2, 0, 1),
            "InvestingCashFlow[total]": (3, 0, 0),
            "FinancingCashFlow[total]": (3, 0, 0),
        },
    )


def _concept_rows(
    *,
    issuer_count: int,
    counts: Mapping[str, tuple[int, int, int]],
) -> list[dict[str, Any]]:
    rows = []
    for concept in canonical_concept_inventory():
        key = f"{concept['canonical_id']}[{concept['basis']}]"
        direct, derived, absent = counts[key]
        if direct + derived + absent != issuer_count:
            raise ValueError(f"inconsistent coverage counts for {key}")
        rows.append(
            {
                "canonical_id": concept["canonical_id"],
                "basis": concept["basis"],
                "direct_resolved_count": direct,
                "derived_count": derived,
                "legitimately_absent_count": absent,
                "coverage_rate_including_derived": _rate(direct + derived, issuer_count),
            }
        )
    return rows


def _sector_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    concepts = [dict(row) for row in item["concept_counts"]]
    issuer_count = int(item["issuer_count"])
    direct = sum(int(row["direct_resolved_count"]) for row in concepts)
    derived = sum(int(row["derived_count"]) for row in concepts)
    absent = sum(int(row["legitimately_absent_count"]) for row in concepts)
    cells = issuer_count * len(concepts)
    return {
        "sector_class": str(item["sector_class"]),
        "issuer_count": issuer_count,
        "headline_canonical_defined_count": len(concepts),
        "headline_canonical_cell_count": cells,
        "direct_resolved_count": direct,
        "derived_count": derived,
        "covered_count_including_derived": direct + derived,
        "legitimately_absent_count": absent,
        "coverage_rate_including_derived": _rate(direct + derived, cells),
        "concepts": concepts,
    }


def _criteria(*, report: Mapping[str, Any], config_defaults_off: bool) -> list[dict[str, Any]]:
    redaction = report_redaction_scan_payload(report)
    summary = dict(report.get("summary") or {})
    sectors = list(report.get("sector_classes") or [])
    limitation = dict(report.get("sector_structure_limitation") or {})
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            config_defaults_off,
            {"config_defaults_off": config_defaults_off},
            "canonical_coverage_breadth_defaults_not_off",
        ),
        _criterion(
            "sector_aggregate_counts_are_consistent",
            _sector_counts_consistent(sectors=sectors, summary=summary),
            {
                "sector_class_count": report.get("sector_class_count"),
                "headline_canonical_cell_count": summary.get("headline_canonical_cell_count"),
                "covered_count_including_derived": summary.get("covered_count_including_derived"),
                "legitimately_absent_count": summary.get("legitimately_absent_count"),
            },
            "canonical_coverage_breadth_counts_inconsistent",
        ),
        _criterion(
            "noncurrent_derivation_recorded_as_distinct_coverage",
            int(summary.get("derived_count") or 0) > 0
            and any(
                row.get("canonical_id") in {"NoncurrentAssets", "NoncurrentLiabilities"}
                and int(row.get("derived_count") or 0) > 0
                for sector in sectors
                for row in sector.get("concepts", [])
                if isinstance(row, Mapping)
            ),
            {"derived_count": summary.get("derived_count")},
            "canonical_coverage_breadth_derivation_not_recorded",
        ),
        _criterion(
            "sector_structure_limitation_preserved",
            limitation.get("status") == "known_limitation"
            and limitation.get("implementation_in_this_slice") is False
            and limitation.get("deferred_design") == "sector_conditioned_canonical_families_selected_by_sic_or_industry",
            limitation,
            "canonical_coverage_breadth_sector_limitation_missing",
        ),
        _criterion(
            "redaction_clean",
            redaction.get("passed") is True,
            redaction,
            "canonical_coverage_breadth_report_redaction_failed",
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
            and non_goals.get("sector_conditioned_families_implemented") is False
            and non_goals.get("statement_assembly_claimed") is False,
            {
                "validate_only": report.get("validate_only"),
                "live_network_used": report.get("live_network_used"),
                "arelle_invoked": report.get("arelle_invoked"),
                "value_reveal_performed": report.get("value_reveal_performed"),
                "runtime_defaults_changed": report.get("runtime_defaults_changed"),
                "non_goals_preserved": non_goals,
            },
            "canonical_coverage_breadth_validate_only_boundary_regressed",
        ),
    ]


def _sector_counts_consistent(*, sectors: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> bool:
    if not rows_have_unique_required_key(sectors, key_field="sector_class"):
        return False
    total_cells = sum(int(sector.get("headline_canonical_cell_count") or 0) for sector in sectors)
    total_direct = sum(int(sector.get("direct_resolved_count") or 0) for sector in sectors)
    total_derived = sum(int(sector.get("derived_count") or 0) for sector in sectors)
    total_absent = sum(int(sector.get("legitimately_absent_count") or 0) for sector in sectors)
    if total_cells == 0:
        return False
    for sector in sectors:
        issuer_count = int(sector.get("issuer_count") or 0)
        for row in sector.get("concepts", []):
            if not isinstance(row, Mapping):
                return False
            if (
                int(row.get("direct_resolved_count") or 0)
                + int(row.get("derived_count") or 0)
                + int(row.get("legitimately_absent_count") or 0)
                != issuer_count
            ):
                return False
    return (
        total_cells == int(summary.get("headline_canonical_cell_count") or 0)
        and total_direct == int(summary.get("direct_resolved_count") or 0)
        and total_derived == int(summary.get("derived_count") or 0)
        and total_absent == int(summary.get("legitimately_absent_count") or 0)
        and total_direct + total_derived + total_absent == total_cells
    )


def _criterion(
    criterion: str,
    passed: bool,
    evidence: Mapping[str, Any],
    blocked_reason: str,
) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _blocking_reasons(criteria: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "criterion": str(item.get("criterion") or ""),
            "reason": str(item.get("blocked_reason") or ""),
            "evidence": item.get("evidence") if isinstance(item.get("evidence"), Mapping) else {},
        }
        for item in criteria
        if item.get("state") != "passed"
    ]


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _config_defaults_off(config_text: str) -> bool:
    return (
        "layer3_sec_edgar_live_network_enabled: bool = Field(\n        default=False," in config_text
        and "layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=False,"
        in config_text
        and "layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False," in config_text
    )


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
