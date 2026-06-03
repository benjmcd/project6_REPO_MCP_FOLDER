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
ASSESSMENT = Path(__file__).resolve().parent
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DB_INIT_MODE", "none")

from app.services.layer3_sec_xbrl_canonical_concepts import (  # noqa: E402
    project_issuer_canonical_facts_by_periods,
    report_redaction_scan_payload,
)
from app.services.layer3_utils import stable_hash  # noqa: E402
from sec_xbrl_diagnostic_framework import blocking_reasons as _blocking_reasons  # noqa: E402
from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_runtime_posture import (  # noqa: E402
    committed_runtime_posture,
    runtime_posture_criterion_evidence,
    runtime_posture_criterion_passed,
)


REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_multi_period_projection.v1"
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-multi-period-projection-report.json")
TARGET = "sec_xbrl_multi_period_projection_design_v1"
NEXT_SLICE = "sec_xbrl_sector_family_real_filer_validation_v1"
_RAW_VALUE_KEY_RE = re.compile(r'"(?:_value|value|effective_value|amount)"\s*:', re.IGNORECASE)
_RAW_AUTHORITY_KEY_RE = re.compile(r'"(?:resolved_fact_id|fact_id_or_order_key)"\s*:', re.IGNORECASE)
_ISSUER_IDENTITY_TOKENS = ("issuer_ref", "issuer_hash", "issuer_name", "entity_name", "company_name")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL multi-period canonical projection diagnostic. It projects comparative "
            "FY periods from governed sidecar/value-store authority and writes a redacted period summary."
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
    issuer_bundle: Mapping[str, Any] | None = None,
    period_limit: int = 2,
) -> dict[str, Any]:
    runtime_posture = committed_runtime_posture(source_root=source_root)
    bundle = dict(issuer_bundle or _reference_bundle())
    result = project_issuer_canonical_facts_by_periods(
        companyfacts=dict(bundle.get("companyfacts") or {}),
        sidecar_records=list(bundle.get("sidecar_records") or []),
        value_records=list(bundle.get("value_records") or []),
        sidecar_receipt_id=str(bundle.get("sidecar_receipt_id") or ""),
        sidecar_receipt_hash=str(bundle.get("sidecar_receipt_hash") or ""),
        value_store_hash=str(bundle.get("value_store_hash") or ""),
        dataset_version_id=str(bundle.get("dataset_version_id") or ""),
        period_limit=period_limit,
        include_sector_families=bool(bundle.get("include_sector_families") is True),
    )
    report: dict[str, Any] = {
        "schema_id": REPORT_SCHEMA_ID,
        "target": TARGET,
        "next_slice": NEXT_SLICE,
        "decision": "sec_xbrl_multi_period_projection_validate_only_ready",
        "source_mode": "governed_sidecar_value_store_reference_bundle",
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "value_authority": "governed_arelle_sidecar_value_store",
        "oracle_authority": "companyfacts_period_key_validation_only",
        "period_selection_rule": "document_period_end_first_then_comparative_fy_periods",
        "summary": _summary(result),
        "periods": [_public_period(item) for item in result.get("periods") or []],
        "blocking_reasons": list(result.get("blocking_reasons") or []),
        "redaction": {},
        "criteria": [],
        "non_goals_preserved": {
            "value_reveal_performed": False,
            "persisted_store_claimed": False,
            "statement_assembly_changed": False,
            "linkbase_emission_claimed": False,
            "production_readiness_claimed": False,
            "runtime_default_enabled": False,
            "final_financial_statement_semantics_claimed": False,
        },
    }
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, runtime_posture=runtime_posture)
    report["blocking_reasons"] = list(report["blocking_reasons"]) + _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = (
            "no_multi_period_projection_evidence"
            if int(report["summary"].get("period_count") or 0) == 0
            else "sec_xbrl_multi_period_projection_validate_only_blocked"
        )
        report["next_slice"] = "sec_xbrl_multi_period_projection_remediation_v1"
    return report


def _summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "projection_status": result.get("status"),
        "primary_taxonomy": result.get("primary_taxonomy"),
        "period_class": result.get("period_class"),
        "period_count": result.get("period_count"),
        "ready_period_count": result.get("ready_period_count"),
        "defined_cell_count": result.get("defined_cell_count"),
        "projected_count": result.get("projected_count"),
        "provenance_complete_count": result.get("provenance_complete_count"),
        "include_sector_families": result.get("include_sector_families") is True,
    }


def _public_period(period_item: Mapping[str, Any]) -> dict[str, Any]:
    projection = dict(period_item.get("projection") or {})
    concepts = [item for item in projection.get("concepts") or [] if isinstance(item, Mapping)]
    projected = [item for item in concepts if item.get("status") != "legitimately_absent"]
    per_statement: dict[str, int] = {"income": 0, "balance": 0, "cashflow": 0}
    for item in projected:
        statement = str(item.get("statement") or "")
        if statement in per_statement:
            per_statement[statement] += 1
    return {
        "period_ref": str(period_item.get("period_ref") or ""),
        "period_index": int(period_item.get("period_index") or 0),
        "matches_document_period_end_date": period_item.get("matches_document_period_end_date") is True,
        "status": projection.get("status"),
        "defined_count": projection.get("defined_count"),
        "projected_count": projection.get("projected_count"),
        "oracle_confirmed_count": projection.get("oracle_confirmed_count"),
        "oracle_absent_count": projection.get("oracle_absent_count"),
        "provenance_complete_count": projection.get("provenance_complete_count"),
        "per_statement_projected": per_statement,
        "statement_identity_evaluated_count": sum(
            1 for item in projection.get("statement_identity_residuals") or [] if item.get("status") == "evaluated"
        ),
    }


def _criteria(*, report: Mapping[str, Any], runtime_posture: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = dict(report.get("summary") or {})
    periods = list(report.get("periods") or [])
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            runtime_posture_criterion_passed(runtime_posture),
            runtime_posture_criterion_evidence(runtime_posture),
            "multi_period_projection_defaults_not_off",
        ),
        _criterion(
            "multi_period_projection_ready_fail_closed",
            summary.get("projection_status") == "canonical_multi_period_projection_ready"
            and int(summary.get("period_count") or 0) >= 2
            and summary.get("period_count") == summary.get("ready_period_count")
            and int(summary.get("projected_count") or 0) > 0,
            summary,
            "multi_period_projection_not_ready",
        ),
        _criterion(
            "period_summaries_are_consistent",
            _period_summaries_consistent(periods=periods, summary=summary),
            {"period_count": summary.get("period_count"), "period_summary_count": len(periods)},
            "multi_period_projection_period_summaries_inconsistent",
        ),
        _criterion(
            "redaction_clean",
            report.get("redaction", {}).get("passed") is True,
            dict(report.get("redaction") or {}),
            "multi_period_projection_report_redaction_failed",
        ),
        _criterion(
            "validate_only_non_goals_preserved",
            report.get("validate_only") is True
            and report.get("live_network_used") is False
            and report.get("arelle_invoked") is False
            and report.get("value_reveal_performed") is False
            and report.get("runtime_defaults_changed") is False
            and non_goals.get("value_reveal_performed") is False
            and non_goals.get("persisted_store_claimed") is False
            and non_goals.get("statement_assembly_changed") is False
            and non_goals.get("production_readiness_claimed") is False
            and non_goals.get("final_financial_statement_semantics_claimed") is False,
            {"validate_only": report.get("validate_only"), "non_goals_preserved": non_goals},
            "multi_period_projection_validate_only_boundary_regressed",
        ),
    ]


def _period_summaries_consistent(*, periods: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> bool:
    return (
        len(periods) == int(summary.get("period_count") or 0)
        and len(periods) >= 2
        and sum(int(item.get("projected_count") or 0) for item in periods) == int(summary.get("projected_count") or 0)
        and periods[0].get("matches_document_period_end_date") is True
        and any(item.get("matches_document_period_end_date") is False for item in periods[1:])
    )


def _redaction_scan_payload(report: Mapping[str, Any]) -> dict[str, bool]:
    base = report_redaction_scan_payload(report)
    text = json.dumps(report, sort_keys=True)
    raw_value_key_found = bool(_RAW_VALUE_KEY_RE.search(text))
    raw_authority_key_found = bool(_RAW_AUTHORITY_KEY_RE.search(text))
    issuer_identity_found = any(token in text for token in _ISSUER_IDENTITY_TOKENS)
    return {
        **base,
        "raw_value_key_found": raw_value_key_found,
        "raw_resolved_fact_authority_key_found": raw_authority_key_found,
        "raw_issuer_identity_found": issuer_identity_found,
        "passed": base["passed"]
        and not raw_value_key_found
        and not raw_authority_key_found
        and not issuer_identity_found,
    }


def _reference_bundle() -> dict[str, Any]:
    sidecar_records = [
        _record("rf-revenue-old", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-1", end="end-1"),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", end="end-1", instant=True),
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-2", end="end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-revenue-old", "90"),
        _value("rf-assets-old", "180"),
        _value("rf-revenue-fy", "100"),
        _value("rf-assets-fy", "200"),
        _value("rf-period-end", "end-2"),
    ]
    return {
        "companyfacts": _companyfacts_periods(
            [
                ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
                ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
                ("us-gaap", "Assets", "180", "USD", "", "end-1", True),
                ("us-gaap", "Assets", "200", "USD", "", "end-2", True),
            ]
        ),
        "sidecar_records": sidecar_records,
        "value_records": value_records,
        "sidecar_receipt_id": "sidecar-ref",
        "sidecar_receipt_hash": "sidecar-hash",
        "value_store_hash": stable_hash(value_records),
        "dataset_version_id": "dataset-ref",
    }


def _record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    start: str = "start-2",
    end: str = "end-2",
    instant: bool = False,
) -> dict[str, Any]:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    return {
        "resolved_fact_id": fact_id,
        "concept": {"namespace": _namespace(taxonomy), "local_name": local_name, "standard": True},
        "unit": _unit(unit_name),
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _value(fact_id: str, effective_value: str) -> dict[str, str]:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _companyfacts_periods(entries: list[tuple[str, str, str, str, str, str, bool]]) -> dict[str, Any]:
    facts: dict[str, dict[str, Any]] = {}
    for taxonomy, local_name, value, unit, start, end, instant in entries:
        facts.setdefault(taxonomy, {}).setdefault(local_name, {"units": {}})
        fact = {"fp": "FY", "fy": "", "val": value, "end": end}
        if not instant:
            fact["start"] = start
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _namespace(taxonomy: str) -> str:
    if taxonomy == "ifrs-full":
        return "xbrl.ifrs.org/test"
    if taxonomy == "dei":
        return "xbrl.sec.gov/dei/test"
    return "fasb.org/us-gaap/test"


def _unit(unit_name: str) -> dict[str, Any]:
    if unit_name == "unitless":
        return {"measures": []}
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _repo_display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
