from __future__ import annotations

import argparse
from functools import partial
import json
import os
from pathlib import Path
import re
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

from app.services.layer3_sec_xbrl_canonical_statement_organization import ALIGNMENT_MAP_VERSION  # noqa: E402
from app.services.layer3_sec_xbrl_report_leak_guard import diagnostic_resolved_fact_redaction_scan_payload  # noqa: E402
from app.services.layer3_sec_xbrl_report_guards import rows_have_unique_required_key  # noqa: E402

from sec_xbrl_diagnostic_framework import blocking_reasons as _blocking_reasons  # noqa: E402
from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_diagnostic_framework import report_envelope as _report_envelope  # noqa: E402
from sec_xbrl_runtime_posture import (  # noqa: E402
    committed_runtime_posture,
    runtime_posture_criterion_evidence,
    runtime_posture_criterion_passed,
)

REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_canonical_statement_organization.v1"
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-canonical-statement-organization-report.json")
TARGET = "sec_xbrl_canonical_statement_organization_validate_only_v1"
NEXT_SLICE = "sec_xbrl_sector_conditioned_canonical_families_deferred_design_v1"
_RAW_RESOLVED_FACT_ID_RE = re.compile(r"\b(?:rf|fact)[-_][A-Za-z0-9]")

_redaction_scan_payload = partial(
    diagnostic_resolved_fact_redaction_scan_payload,
    raw_resolved_fact_id_pattern=_RAW_RESOLVED_FACT_ID_RE,
)


REFERENCE_TAXONOMY_RESULTS = (
    {
        "taxonomy": "us-gaap",
        "issuer_count": 1,
        "normalized_fact_count": 22,
        "organized_count": 22,
        "a_corroborated_count": 22,
        "a_divergent_count": 0,
        "a_role_unknown_count": 0,
        "unjoined_count": 0,
        "derived_count": 2,
        "derived_inputs_corroborated_count": 2,
        "per_statement": {"income": 10, "balance": 9, "cashflow": 3},
        "a_full_corroboration": True,
        "contract_passed": True,
        "contract_b_authoritative_organization": True,
        "contract_every_fact_id_bound": True,
        "contract_derived_inputs_bound_and_corroborated": True,
    },
    {
        "taxonomy": "ifrs-full",
        "issuer_count": 2,
        "normalized_fact_count": 42,
        "organized_count": 42,
        "a_corroborated_count": 36,
        "a_divergent_count": 2,
        "a_role_unknown_count": 4,
        "unjoined_count": 0,
        "derived_count": 0,
        "derived_inputs_corroborated_count": 0,
        "per_statement": {"income": 19, "balance": 17, "cashflow": 6},
        "a_full_corroboration": False,
        "contract_passed": True,
        "contract_b_authoritative_organization": True,
        "contract_every_fact_id_bound": True,
        "contract_derived_inputs_bound_and_corroborated": True,
    },
)

REFERENCE_A_DIVERGENT = (
    {
        "canonical_id": "OperatingIncome",
        "basis": "total",
        "statement": "income",
        "a_role": "cash_flow_statement",
        "taxonomy": "ifrs-full",
    },
)
REFERENCE_A_ROLE_UNKNOWN = (
    {
        "canonical_id": "Equity",
        "basis": "total",
        "statement": "balance",
        "a_role": "unknown_or_unclassified",
        "taxonomy": "ifrs-full",
    },
    {
        "canonical_id": "Equity",
        "basis": "parent",
        "statement": "balance",
        "a_role": "unknown_or_unclassified",
        "taxonomy": "ifrs-full",
    },
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL canonical statement-organization diagnostic. It writes a redacted "
            "taxonomy aggregate summary and does not fetch SEC data, invoke Arelle, reveal values, mutate "
            "runtime defaults, persist runtime artifacts, or assemble financial statements."
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
    taxonomy_results: Sequence[Mapping[str, Any]] | None = None,
    a_divergent: Sequence[Mapping[str, Any]] | None = None,
    a_role_unknown: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    runtime_posture = committed_runtime_posture(source_root=source_root)
    selected_results = REFERENCE_TAXONOMY_RESULTS if taxonomy_results is None else taxonomy_results
    selected_divergent = REFERENCE_A_DIVERGENT if a_divergent is None else a_divergent
    selected_unknown = REFERENCE_A_ROLE_UNKNOWN if a_role_unknown is None else a_role_unknown
    report = _reference_summary_report(
        taxonomy_results=list(selected_results),
        a_divergent=list(selected_divergent),
        a_role_unknown=list(selected_unknown),
        runtime_posture=runtime_posture,
    )
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, runtime_posture=runtime_posture)
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = (
            "no_statement_organization_evidence"
            if not report.get("per_taxonomy")
            else "canonical_statement_organization_validate_only_blocked"
        )
        report["next_slice"] = "sec_xbrl_canonical_statement_organization_remediation_v1"
    return report


def _reference_summary_report(
    *,
    taxonomy_results: Sequence[Mapping[str, Any]],
    a_divergent: Sequence[Mapping[str, Any]],
    a_role_unknown: Sequence[Mapping[str, Any]],
    runtime_posture: Mapping[str, Any],
) -> dict[str, Any]:
    per_taxonomy = [_taxonomy_summary(item) for item in taxonomy_results]
    summary = _summary(per_taxonomy)
    report: dict[str, Any] = _report_envelope(
        schema_id=REPORT_SCHEMA_ID,
        target=TARGET,
        next_slice=NEXT_SLICE,
        decision="canonical_statement_organization_validate_only_ready",
        source_mode="redacted_reference_taxonomy_summary",
        validate_only=True,
        alignment_map_version=ALIGNMENT_MAP_VERSION,
        evidence_scope="operator_run_reference_summary_covers_three_issuers_not_all_taxonomies",
        live_network_used=False,
        arelle_invoked=False,
        value_reveal_performed=False,
        runtime_defaults_changed=False,
        canonical_statement_authority="canonical_projection_reviewed_statement_crosswalk",
        a_role_authority="statement_classification_candidate_role_heuristic",
        a_role_used_as_pass_gate=False,
        summary=summary,
        per_taxonomy=per_taxonomy,
        a_divergent=_public_concept_set(a_divergent),
        a_role_unknown=_public_concept_set(a_role_unknown),
        redaction={},
        criteria=[],
        blocking_reasons=[],
        non_goals_preserved={
            "statement_assembly_claimed": False,
            "statement_role_semantics_finalized": False,
            "final_financial_statement_semantics_claimed": False,
            "a_classifier_modified": False,
            "sector_families_implemented": False,
            "per_period_projection_claimed": False,
            "linkbase_emission_claimed": False,
            "persisted_store_claimed": False,
            "value_reveal_performed": False,
            "default_on_readiness_claimed": False,
            "production_readiness_claimed": False,
        },
    )
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, runtime_posture=runtime_posture)
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = (
            "no_statement_organization_evidence"
            if not report.get("per_taxonomy")
            else "canonical_statement_organization_validate_only_blocked"
        )
        report["next_slice"] = "sec_xbrl_canonical_statement_organization_remediation_v1"
    return report


def _taxonomy_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "taxonomy",
        "issuer_count",
        "normalized_fact_count",
        "organized_count",
        "a_corroborated_count",
        "a_divergent_count",
        "a_role_unknown_count",
        "unjoined_count",
        "derived_count",
        "derived_inputs_corroborated_count",
        "per_statement",
        "contract_b_authoritative_organization",
        "contract_every_fact_id_bound",
        "contract_derived_inputs_bound_and_corroborated",
        "contract_passed",
    }
    missing = sorted(field for field in required if field not in item)
    per_statement = item.get("per_statement") if isinstance(item.get("per_statement"), Mapping) else {}
    normalized = _int(item.get("normalized_fact_count"))
    organized = _int(item.get("organized_count"))
    unjoined = _int(item.get("unjoined_count"))
    divergent = _int(item.get("a_divergent_count"))
    unknown = _int(item.get("a_role_unknown_count"))
    contract_b = item.get("contract_b_authoritative_organization") is True
    contract_bound = item.get("contract_every_fact_id_bound") is True
    contract_derived = item.get("contract_derived_inputs_bound_and_corroborated") is True
    contract_passed = (
        not missing
        and normalized > 0
        and item.get("contract_passed") is True
        and contract_b
        and contract_bound
        and contract_derived
    )
    return {
        "taxonomy": str(item.get("taxonomy") or ""),
        "issuer_count": _int(item.get("issuer_count")),
        "normalized_fact_count": normalized,
        "organized_count": organized,
        "a_corroborated_count": _int(item.get("a_corroborated_count")),
        "a_divergent_count": divergent,
        "a_role_unknown_count": unknown,
        "unjoined_count": unjoined,
        "derived_count": _int(item.get("derived_count")),
        "derived_inputs_corroborated_count": _int(item.get("derived_inputs_corroborated_count")),
        "per_statement": {
            "income": _int(per_statement.get("income")),
            "balance": _int(per_statement.get("balance")),
            "cashflow": _int(per_statement.get("cashflow")),
        },
        "a_full_corroboration": divergent == 0 and unknown == 0,
        "contract_b_authoritative_organization": contract_b,
        "contract_every_fact_id_bound": contract_bound and unjoined == 0,
        "contract_derived_inputs_bound_and_corroborated": contract_derived,
        "contract_passed": contract_passed,
        "missing_required_fields": missing,
    }


def _summary(per_taxonomy: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total_normalized = sum(_int(item.get("normalized_fact_count")) for item in per_taxonomy)
    total_organized = sum(_int(item.get("organized_count")) for item in per_taxonomy)
    total_a_corroborated = sum(_int(item.get("a_corroborated_count")) for item in per_taxonomy)
    total_a_divergent = sum(_int(item.get("a_divergent_count")) for item in per_taxonomy)
    total_a_role_unknown = sum(_int(item.get("a_role_unknown_count")) for item in per_taxonomy)
    total_unjoined = sum(_int(item.get("unjoined_count")) for item in per_taxonomy)
    contract_passed = (
        total_normalized > 0
        and total_organized == total_normalized
        and total_unjoined == 0
        and all(item.get("contract_passed") is True for item in per_taxonomy)
    )
    return {
        "contract_passed": contract_passed,
        "total_normalized": total_normalized,
        "total_organized": total_organized,
        "total_a_corroborated": total_a_corroborated,
        "total_a_divergent": total_a_divergent,
        "total_a_role_unknown": total_a_role_unknown,
        "total_unjoined": total_unjoined,
    }


def _criteria(*, report: Mapping[str, Any], runtime_posture: Mapping[str, Any]) -> list[dict[str, Any]]:
    redaction = _redaction_scan_payload(report)
    summary = dict(report.get("summary") or {})
    per_taxonomy = list(report.get("per_taxonomy") or [])
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            runtime_posture_criterion_passed(runtime_posture),
            runtime_posture_criterion_evidence(runtime_posture),
            "canonical_statement_organization_defaults_not_off",
        ),
        _criterion(
            "statement_organization_contract_passes_fail_closed",
            summary.get("contract_passed") is True and _int(summary.get("total_unjoined")) == 0,
            {
                "contract_passed": summary.get("contract_passed"),
                "total_unjoined": summary.get("total_unjoined"),
                "total_normalized": summary.get("total_normalized"),
            },
            "canonical_statement_organization_contract_failed",
        ),
        _criterion(
            "taxonomy_aggregate_counts_are_consistent",
            _taxonomy_counts_consistent(per_taxonomy=per_taxonomy, summary=summary),
            {
                "taxonomy_count": len(per_taxonomy),
                "total_normalized": summary.get("total_normalized"),
                "total_organized": summary.get("total_organized"),
                "total_unjoined": summary.get("total_unjoined"),
            },
            "canonical_statement_organization_counts_inconsistent",
        ),
        _criterion(
            "known_ifrs_a_divergence_is_documented_not_gated",
            _known_ifrs_drift_guard(report),
            {
                "a_divergent": report.get("a_divergent"),
                "a_role_unknown": report.get("a_role_unknown"),
                "a_role_used_as_pass_gate": report.get("a_role_used_as_pass_gate"),
            },
            "canonical_statement_organization_ifrs_drift_guard_failed",
        ),
        _criterion(
            "redaction_clean",
            redaction.get("passed") is True,
            redaction,
            "canonical_statement_organization_report_redaction_failed",
        ),
        _criterion(
            "validate_only_non_goals_preserved",
            report.get("validate_only") is True
            and report.get("live_network_used") is False
            and report.get("arelle_invoked") is False
            and report.get("value_reveal_performed") is False
            and report.get("runtime_defaults_changed") is False
            and non_goals.get("statement_assembly_claimed") is False
            and non_goals.get("statement_role_semantics_finalized") is False
            and non_goals.get("final_financial_statement_semantics_claimed") is False
            and non_goals.get("a_classifier_modified") is False
            and non_goals.get("sector_families_implemented") is False
            and non_goals.get("per_period_projection_claimed") is False
            and non_goals.get("linkbase_emission_claimed") is False
            and non_goals.get("persisted_store_claimed") is False,
            {
                "validate_only": report.get("validate_only"),
                "live_network_used": report.get("live_network_used"),
                "arelle_invoked": report.get("arelle_invoked"),
                "value_reveal_performed": report.get("value_reveal_performed"),
                "runtime_defaults_changed": report.get("runtime_defaults_changed"),
                "non_goals_preserved": non_goals,
            },
            "canonical_statement_organization_validate_only_boundary_regressed",
        ),
    ]


def _taxonomy_counts_consistent(
    *,
    per_taxonomy: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> bool:
    if not rows_have_unique_required_key(per_taxonomy, key_field="taxonomy"):
        return False
    total_normalized = sum(_int(item.get("normalized_fact_count")) for item in per_taxonomy)
    total_organized = sum(_int(item.get("organized_count")) for item in per_taxonomy)
    total_a_corroborated = sum(_int(item.get("a_corroborated_count")) for item in per_taxonomy)
    total_a_divergent = sum(_int(item.get("a_divergent_count")) for item in per_taxonomy)
    total_a_role_unknown = sum(_int(item.get("a_role_unknown_count")) for item in per_taxonomy)
    total_unjoined = sum(_int(item.get("unjoined_count")) for item in per_taxonomy)
    return (
        bool(per_taxonomy)
        and total_normalized == _int(summary.get("total_normalized"))
        and total_organized == _int(summary.get("total_organized"))
        and total_a_corroborated == _int(summary.get("total_a_corroborated"))
        and total_a_divergent == _int(summary.get("total_a_divergent"))
        and total_a_role_unknown == _int(summary.get("total_a_role_unknown"))
        and total_unjoined == _int(summary.get("total_unjoined"))
        and all(not item.get("missing_required_fields") for item in per_taxonomy)
        and all(
            sum(_int(value) for value in dict(item.get("per_statement") or {}).values())
            == _int(item.get("organized_count"))
            for item in per_taxonomy
        )
    )


def _known_ifrs_drift_guard(report: Mapping[str, Any]) -> bool:
    expected_divergent = {
        (
            "OperatingIncome",
            "total",
            "income",
            "cash_flow_statement",
            "ifrs-full",
        )
    }
    expected_unknown = {
        (
            "Equity",
            "total",
            "balance",
            "unknown_or_unclassified",
            "ifrs-full",
        ),
        (
            "Equity",
            "parent",
            "balance",
            "unknown_or_unclassified",
            "ifrs-full",
        ),
    }
    return (
        report.get("a_role_used_as_pass_gate") is False
        and _concept_set(report.get("a_divergent")) == expected_divergent
        and _concept_set(report.get("a_role_unknown")) == expected_unknown
    )


def _concept_set(records: Any) -> set[tuple[str, str, str, str, str]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return set()
    return {
        (
            str(record.get("canonical_id") or ""),
            str(record.get("basis") or ""),
            str(record.get("statement") or ""),
            str(record.get("a_role") or ""),
            str(record.get("taxonomy") or ""),
        )
        for record in records
        if isinstance(record, Mapping)
    }


def _public_concept_set(records: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    public_records: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for record in records:
        public = {
            "canonical_id": str(record.get("canonical_id") or ""),
            "basis": str(record.get("basis") or ""),
            "statement": str(record.get("statement") or ""),
            "a_role": str(record.get("a_role") or ""),
            "taxonomy": str(record.get("taxonomy") or ""),
        }
        marker = (
            public["canonical_id"],
            public["basis"],
            public["statement"],
            public["a_role"],
            public["taxonomy"],
        )
        if marker not in seen:
            seen.add(marker)
            public_records.append(public)
    return public_records


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return "<redacted-output-path>"


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
