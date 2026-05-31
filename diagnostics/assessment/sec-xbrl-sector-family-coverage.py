from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from app.services.layer3_sec_xbrl_canonical_concepts import (  # noqa: E402
    SECTOR_FAMILY_DEFINITIONS,
    SIC_RANGE_TO_SECTOR_CLASS,
    UNKNOWN_SECTOR_CLASS,
    classify_sector_family_presence as runtime_classify_sector_family_presence,
    report_redaction_scan_payload,
    sector_class_from_sic as runtime_sector_class_from_sic,
)
from app.services.layer3_sec_xbrl_report_guards import rows_have_unique_required_key  # noqa: E402


REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_sector_family_coverage.v1"
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-sector-family-coverage-report.json")
TARGET = "sec_xbrl_sector_conditioned_canonical_families_deferred_design_v1"
NEXT_SLICE = "sec_xbrl_sector_conditioned_canonical_families_v1_resolution_presence_conditioned"
SIC_RANGE_TABLE_VERSION = "sic_range_to_sector_class_v1"
SECTOR_FAMILY_REGISTRY_VERSION = "sec_xbrl_sector_family_headline_registry_design_v1"

REFERENCE_FAMILY_EVIDENCE: tuple[dict[str, Any], ...] = (
    {
        "family_id": "extractive",
        "reference_issuer_count": 1,
        "concept_counts": {
            "ifrs-full:ExpenseArisingFromExplorationForAndEvaluationOfMineralResources": 1,
            "ifrs-full:CurrentOreStockpiles": 1,
            "us-gaap:ExplorationExpense": 0,
        },
    },
    {
        "family_id": "banking",
        "reference_issuer_count": 1,
        "concept_counts": {
            "ifrs-full:InterestIncomeForFinancialAssetsMeasuredAtAmortisedCost": 1,
            "ifrs-full:GrossLoanCommitments": 1,
            "ifrs-full:CurrentDepositsFromCustomers": 1,
            "us-gaap:InterestAndDividendIncomeOperating": 0,
            "us-gaap:InterestExpense": 0,
            "us-gaap:Deposits": 0,
        },
    },
    {
        "family_id": "insurance",
        "reference_issuer_count": 1,
        "concept_counts": {
            "ifrs-full:InsuranceRevenue": 1,
            "ifrs-full:InsuranceContractsLiabilityAsset": 1,
            "us-gaap:PremiumsEarnedNet": 0,
            "us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense": 0,
        },
    },
)

_RAW_SIC_NUMBER_RE = re.compile(
    r"(?:raw[_-]?sic|primary[_-]?sic|EntityPrimarySicNumber|dei:EntityPrimarySicNumber)[^0-9]{0,20}[0-9]{3,4}",
    re.IGNORECASE,
)
_RAW_VALUE_KEY_RE = re.compile(r'"(?:value|amount|effective_value|val)"\s*:', re.IGNORECASE)
_ISSUER_IDENTITY_TOKENS = ("issuer_ref", "issuer_hash", "issuer_name", "entity_name", "company_name")
_RAW_PATH_KEY_RE = re.compile(r'"(?:source_path|local_path|file_path|resolved_fact_id)"\s*:', re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL sector-family coverage diagnostic. It writes a redacted family/count "
            "summary and does not fetch SEC data, invoke Arelle, reveal values, mutate runtime defaults, "
            "persist runtime artifacts, or implement sector-family resolution."
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
    per_family: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    config_text = (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    selected_families = REFERENCE_FAMILY_EVIDENCE if per_family is None else per_family
    report = _reference_summary_report(
        per_family=list(selected_families),
        config_defaults_off=_config_defaults_off(config_text),
    )
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, config_defaults_off=_config_defaults_off(config_text))
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = (
            "no_sector_family_coverage_evidence"
            if not report.get("per_family")
            else "sector_family_coverage_validate_only_blocked"
        )
        report["next_slice"] = "sec_xbrl_sector_family_coverage_reference_evidence_required"
    return report


def sector_class_from_sic(primary_sic: Any) -> str:
    return runtime_sector_class_from_sic(primary_sic)


def classify_sector_family_presence(*, primary_sic: Any, reported_concepts: Sequence[str]) -> dict[str, Any]:
    return runtime_classify_sector_family_presence(primary_sic=primary_sic, reported_concepts=reported_concepts)


def _reference_summary_report(*, per_family: Sequence[Mapping[str, Any]], config_defaults_off: bool) -> dict[str, Any]:
    family_rows = [_family_summary(item) for item in per_family]
    report: dict[str, Any] = {
        "schema_id": REPORT_SCHEMA_ID,
        "target": TARGET,
        "next_slice": NEXT_SLICE,
        "decision": "sector_family_coverage_validate_only_ready",
        "source_mode": "redacted_reference_family_summary",
        "evidence_scope": "operator_run_reference_summary_covers_three_redacted_filers_not_all_sectors",
        "sector_class_source_concept": "dei:EntityPrimarySicNumber",
        "sector_class_source_fallback_documented": "sec_submissions_metadata",
        "sic_range_table_version": SIC_RANGE_TABLE_VERSION,
        "sector_conditioning": "concept_presence_not_sic_gated",
        "family_registry_version": SECTOR_FAMILY_REGISTRY_VERSION,
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "per_family": family_rows,
        "summary": _summary(family_rows),
        "diversified_filer_guard": classify_sector_family_presence(
            primary_sic="3651",
            reported_concepts=[
                "ifrs-full:InsuranceRevenue",
                "ifrs-full:InsuranceContractsLiabilityAsset",
                "ifrs-full:InterestIncomeForFinancialAssetsMeasuredAtAmortisedCost",
                "ifrs-full:GrossLoanCommitments",
                "ifrs-full:CurrentDepositsFromCustomers",
                "us-gaap:InterestExpense",
            ],
        ),
        "redaction": {},
        "criteria": [],
        "blocking_reasons": [],
        "non_goals_preserved": {
            "sector_conditioned_families_design_complete": True,
            "coverage_diagnostic_runtime_mutation_performed": False,
            "coverage_diagnostic_canonical_model_mutation_performed": False,
            "coverage_diagnostic_sector_resolution_performed": False,
            "runtime_opt_in_sector_family_resolution_available": True,
            "runtime_canonical_concept_family_qualifier_available": True,
            "statement_assembly_claimed": False,
            "dimensional_roll_forward_claimed": False,
            "per_period_projection_claimed": False,
            "persisted_store_claimed": False,
            "value_reveal_performed": False,
            "default_on_readiness_claimed": False,
            "production_readiness_claimed": False,
        },
    }
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, config_defaults_off=config_defaults_off)
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = (
            "no_sector_family_coverage_evidence"
            if not report.get("per_family")
            else "sector_family_coverage_validate_only_blocked"
        )
        report["next_slice"] = "sec_xbrl_sector_family_coverage_reference_evidence_required"
    return report


def _family_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    family_id = str(item.get("family_id") or "")
    definition = _family_definition(family_id)
    concept_counts = dict(item.get("concept_counts") or {})
    concepts = [_concept_summary(concept, concept_counts) for concept in definition["headline_concepts"]]
    defined_count = len(concepts)
    present_count = sum(1 for concept in concepts if concept["reference_present"] is True)
    return {
        "family_id": family_id,
        "sector_class": definition["sector_class"],
        "activation_anchor_count": len(definition["activation_anchor_qnames"]),
        "supporting_concept_count": len(definition["supporting_qnames"]),
        "defined_headline_concept_count": defined_count,
        "reference_present_count": present_count,
        "reference_issuer_count": _int(item.get("reference_issuer_count")),
        "coverage_rate": _rate(present_count, defined_count),
        "reference_present": present_count > 0,
        "concepts": concepts,
    }


def _concept_summary(concept: tuple[str, str, str, str], concept_counts: Mapping[str, Any]) -> dict[str, Any]:
    canonical_concept_id, _basis, _statement, concept_id = concept
    taxonomy = concept_id.split(":", 1)[0]
    present_count = _int(concept_counts.get(concept_id))
    return {
        "canonical_concept_id": canonical_concept_id,
        "concept_id": concept_id,
        "taxonomy": taxonomy,
        "reference_present_count": present_count,
        "coverage_rate": _rate(present_count, 1),
        "reference_present": present_count > 0,
    }


def _summary(families: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    defined_count = sum(_int(item.get("defined_headline_concept_count")) for item in families)
    present_count = sum(_int(item.get("reference_present_count")) for item in families)
    return {
        "families_defined": len(SECTOR_FAMILY_DEFINITIONS),
        "families_with_reference_presence": sum(1 for item in families if item.get("reference_present") is True),
        "sector_class_count": len({definition["sector_class"] for definition in SECTOR_FAMILY_DEFINITIONS}),
        "total_headline_concepts_defined": defined_count,
        "total_reference_present_count": present_count,
        "universal_only_reference_issuer_count": 1,
        "coverage_rate": _rate(present_count, defined_count),
        "contract_passed": bool(families) and _family_counts_consistent(families),
    }


def _criteria(*, report: Mapping[str, Any], config_defaults_off: bool) -> list[dict[str, Any]]:
    redaction = _redaction_scan_payload(report)
    summary = dict(report.get("summary") or {})
    families = list(report.get("per_family") or [])
    guard = dict(report.get("diversified_filer_guard") or {})
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            config_defaults_off,
            {"config_defaults_off": config_defaults_off},
            "sector_family_coverage_defaults_not_off",
        ),
        _criterion(
            "family_coverage_counts_are_consistent",
            _family_counts_consistent(families) and summary.get("contract_passed") is True,
            {
                "families_defined": summary.get("families_defined"),
                "total_headline_concepts_defined": summary.get("total_headline_concepts_defined"),
                "total_reference_present_count": summary.get("total_reference_present_count"),
            },
            "sector_family_coverage_counts_inconsistent",
        ),
        _criterion(
            "concept_presence_conditioning_not_sic_gating",
            report.get("sector_conditioning") == "concept_presence_not_sic_gated"
            and guard.get("presence_conditioned") is True
            and guard.get("sic_used_as_gate") is False
            and set(guard.get("present_family_ids") or []) == {"banking", "insurance"},
            guard,
            "sector_family_conditioning_regressed_to_sic_gate",
        ),
        _criterion(
            "family_activation_requires_anchor_not_support_only",
            guard.get("activation_rule") == "anchor_concepts_activate_supporting_concepts_do_not"
            and classify_sector_family_presence(
                primary_sic="3651",
                reported_concepts=["us-gaap:InterestExpense"],
            ).get("present_family_ids") == []
            and _supporting_only_family_ids(["us-gaap:InterestExpense"]) == ["banking"],
            {
                "activation_rule": guard.get("activation_rule"),
                "interest_expense_only_family_ids": classify_sector_family_presence(
                    primary_sic="3651",
                    reported_concepts=["us-gaap:InterestExpense"],
                ).get("present_family_ids"),
            },
            "sector_family_supporting_concept_activated_family",
        ),
        _criterion(
            "redaction_clean",
            redaction.get("passed") is True,
            redaction,
            "sector_family_coverage_report_redaction_failed",
        ),
        _criterion(
            "validate_only_non_goals_preserved",
            report.get("validate_only") is True
            and report.get("live_network_used") is False
            and report.get("arelle_invoked") is False
            and report.get("value_reveal_performed") is False
            and report.get("runtime_defaults_changed") is False
            and non_goals.get("sector_conditioned_families_design_complete") is True
            and non_goals.get("coverage_diagnostic_runtime_mutation_performed") is False
            and non_goals.get("coverage_diagnostic_canonical_model_mutation_performed") is False
            and non_goals.get("coverage_diagnostic_sector_resolution_performed") is False
            and non_goals.get("runtime_opt_in_sector_family_resolution_available") is True
            and non_goals.get("runtime_canonical_concept_family_qualifier_available") is True
            and non_goals.get("statement_assembly_claimed") is False
            and non_goals.get("dimensional_roll_forward_claimed") is False
            and non_goals.get("persisted_store_claimed") is False,
            {
                "validate_only": report.get("validate_only"),
                "live_network_used": report.get("live_network_used"),
                "arelle_invoked": report.get("arelle_invoked"),
                "value_reveal_performed": report.get("value_reveal_performed"),
                "runtime_defaults_changed": report.get("runtime_defaults_changed"),
                "non_goals_preserved": non_goals,
            },
            "sector_family_coverage_validate_only_boundary_regressed",
        ),
    ]


def _family_counts_consistent(families: Sequence[Mapping[str, Any]]) -> bool:
    if not families:
        return False
    expected_ids = {definition["family_id"] for definition in SECTOR_FAMILY_DEFINITIONS}
    if not rows_have_unique_required_key(
        families,
        key_field="family_id",
        expected_count=len(expected_ids),
        expected_values=expected_ids,
    ):
        return False
    for family in families:
        concepts = list(family.get("concepts") or [])
        defined_count = _int(family.get("defined_headline_concept_count"))
        present_count = _int(family.get("reference_present_count"))
        if defined_count != len(concepts):
            return False
        if present_count != sum(1 for concept in concepts if concept.get("reference_present") is True):
            return False
        if any(_int(concept.get("reference_present_count")) not in {0, 1} for concept in concepts):
            return False
    return True


def _supporting_only_family_ids(reported_concepts: Sequence[str]) -> list[str]:
    presence = classify_sector_family_presence(primary_sic=None, reported_concepts=reported_concepts)
    return [
        str(item.get("family_id") or "")
        for item in presence.get("reported_family_evidence") or []
        if isinstance(item, Mapping) and item.get("supporting_only") is True
    ]


def _family_has_reported_concept(*, definition: Mapping[str, Any], reported_concepts: Sequence[str]) -> bool:
    reported = set(reported_concepts)
    return any(concept_id in reported for _, _, _, concept_id in definition["headline_concepts"])


def _family_definition(family_id: str) -> Mapping[str, Any]:
    for definition in SECTOR_FAMILY_DEFINITIONS:
        if definition["family_id"] == family_id:
            return definition
    raise ValueError(f"unknown sector family: {family_id}")


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


def _redaction_scan_payload(payload: Any) -> dict[str, bool]:
    text = json.dumps(payload, sort_keys=True) if not isinstance(payload, str) else payload
    base = report_redaction_scan_payload(payload)
    raw_sic_found = bool(_RAW_SIC_NUMBER_RE.search(text))
    raw_issuer_identity_found = any(token in text for token in _ISSUER_IDENTITY_TOKENS)
    raw_value_found = bool(_RAW_VALUE_KEY_RE.search(text))
    raw_path_or_accession_found = bool(_RAW_PATH_KEY_RE.search(text))
    return {
        **base,
        "raw_sic_found": raw_sic_found,
        "raw_issuer_identity_found": raw_issuer_identity_found,
        "raw_value_found": raw_value_found,
        "raw_path_or_accession_found": raw_path_or_accession_found,
        "passed": (
            base.get("passed") is True
            and not raw_sic_found
            and not raw_issuer_identity_found
            and not raw_value_found
            and not raw_path_or_accession_found
        ),
    }


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


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
