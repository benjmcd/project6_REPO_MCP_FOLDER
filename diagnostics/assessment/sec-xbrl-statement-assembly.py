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

from app.services.layer3_sec_xbrl_canonical_concepts import report_redaction_scan_payload  # noqa: E402
from app.services.layer3_sec_xbrl_statement_assembly import (  # noqa: E402
    STATEMENT_ASSEMBLY_SCHEMA_ID,
    assemble_reviewable_statement_packet,
)
from sec_xbrl_report_redaction import strip_residual_magnitude_fields  # noqa: E402
from sec_xbrl_runtime_posture import (  # noqa: E402
    committed_runtime_posture,
    runtime_posture_criterion_evidence,
    runtime_posture_criterion_passed,
)


REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_statement_assembly.v1"
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-statement-assembly-report.json")
TARGET = "sec_xbrl_statement_assembly_deferred_pending_linkbase_emission_v1"
NEXT_SLICE = "sec_xbrl_multi_period_projection_design_v1"
_RAW_VALUE_KEY_RE = re.compile(r'"(?:_value|value|effective_value|amount)"\s*:', re.IGNORECASE)
_RAW_AUTHORITY_KEY_RE = re.compile(r'"(?:resolved_fact_id|fact_id_or_order_key)"\s*:', re.IGNORECASE)
_ISSUER_IDENTITY_TOKENS = ("issuer_ref", "issuer_hash", "issuer_name", "entity_name", "company_name")


REFERENCE_PROJECTION_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "canonical_id": "Revenue",
        "basis": "total",
        "requested_basis": "total",
        "statement": "income",
        "family": "universal",
        "status": "projected_oracle_confirmed",
        "source_qname": "ifrs-full:Revenue",
        "period_class": "FY",
        "oracle_confirmed": True,
        "mapping_method": "redacted_reference_projection",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "provenance_complete": True,
        "unit_class": "currency",
    },
    {
        "canonical_id": "BankingInterestExpense",
        "basis": "total",
        "requested_basis": "total",
        "statement": "income",
        "family": "banking",
        "status": "projected_oracle_absent",
        "source_qname": "us-gaap:InterestExpense",
        "period_class": "FY",
        "oracle_confirmed": "oracle_absent",
        "mapping_method": "presence_conditioned_sector_family_crosswalk",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "provenance_complete": True,
        "unit_class": "currency",
    },
    {
        "canonical_id": "TotalAssets",
        "basis": "total",
        "requested_basis": "total",
        "statement": "balance",
        "family": "universal",
        "status": "projected_oracle_confirmed",
        "source_qname": "ifrs-full:Assets",
        "period_class": "FY",
        "oracle_confirmed": True,
        "mapping_method": "redacted_reference_projection",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "provenance_complete": True,
        "unit_class": "currency",
    },
    {
        "canonical_id": "BankingGrossLoanCommitments",
        "basis": "total",
        "requested_basis": "total",
        "statement": "balance",
        "family": "banking",
        "status": "projected_oracle_absent",
        "source_qname": "ifrs-full:GrossLoanCommitments",
        "period_class": "FY",
        "oracle_confirmed": "oracle_absent",
        "mapping_method": "presence_conditioned_sector_family_crosswalk",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "provenance_complete": True,
        "unit_class": "currency",
    },
    {
        "canonical_id": "OperatingCashFlow",
        "basis": "total",
        "requested_basis": "total",
        "statement": "cashflow",
        "family": "universal",
        "status": "projected_oracle_confirmed",
        "source_qname": "ifrs-full:CashFlowsFromUsedInOperatingActivities",
        "period_class": "FY",
        "oracle_confirmed": True,
        "mapping_method": "redacted_reference_projection",
        "mapping_confidence": "reviewed_high_value_headline_statement_crosswalk",
        "provenance_complete": True,
        "unit_class": "currency",
    },
)

REFERENCE_ORGANIZATION_RESULT = {
    "contract_passed": True,
    "contract_b_authoritative_organization": True,
    "contract_every_fact_id_bound": True,
    "contract_derived_inputs_bound_and_corroborated": True,
    "normalized_fact_count": 5,
    "organized_count": 5,
    "unjoined_count": 0,
    "a_divergent_count": 0,
    "a_role_unknown_count": 0,
}

REFERENCE_IDENTITY_RESIDUALS = (
    {
        "identity_id": "current_assets_plus_noncurrent_assets_equals_total_assets",
        "status": "evaluated",
        "within_tolerance": True,
        "relative_magnitude": "0E+2",
        "residual_abs": "0",
    },
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL reviewable statement packet diagnostic. It groups redacted canonical "
            "projection rows by authoritative B statement role and does not reveal values, persist runtime "
            "artifacts, fetch SEC data, invoke Arelle, or claim final financial-statement semantics."
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
    projection_items: Sequence[Mapping[str, Any]] | None = None,
    organization_result: Mapping[str, Any] | None = None,
    identity_residuals: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    runtime_posture = committed_runtime_posture(source_root=source_root)
    packet = assemble_reviewable_statement_packet(
        projection_items=list(REFERENCE_PROJECTION_ITEMS if projection_items is None else projection_items),
        organization_result=dict(REFERENCE_ORGANIZATION_RESULT if organization_result is None else organization_result),
        identity_residuals=list(REFERENCE_IDENTITY_RESIDUALS if identity_residuals is None else identity_residuals),
    )
    report: dict[str, Any] = {
        "schema_id": REPORT_SCHEMA_ID,
        "target": TARGET,
        "next_slice": NEXT_SLICE,
        "decision": "sec_xbrl_statement_assembly_validate_only_ready",
        "source_mode": "redacted_reference_projection_and_statement_organization_summary",
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "runtime_schema_id": STATEMENT_ASSEMBLY_SCHEMA_ID,
        "value_policy": packet["value_policy"],
        "canonical_projection_authority": packet["canonical_projection_authority"],
        "statement_organization_authority": packet["statement_organization_authority"],
        "linkbase_required_for_review_packet": False,
        "summary": _summary(packet),
        "statements": packet["statements"],
        "identity_rollup": packet["identity_rollup"],
        "organization_contract": packet["organization_contract"],
        "blocking_reasons": list(packet["blocking_reasons"]),
        "redaction": {},
        "criteria": [],
        "non_goals_preserved": {
            "final_financial_statement_semantics_claimed": False,
            "linkbase_emission_claimed": False,
            "per_period_projection_claimed": False,
            "value_reveal_performed": False,
            "persisted_store_claimed": False,
            "runtime_default_enabled": False,
            "production_readiness_claimed": False,
            "provider_or_connector_dispatch_performed": False,
        },
    }
    report = strip_residual_magnitude_fields(report)
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, runtime_posture=runtime_posture)
    report["blocking_reasons"] = list(report["blocking_reasons"]) + _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = (
            "no_statement_assembly_evidence"
            if report["summary"]["total_review_rows"] == 0
            else "sec_xbrl_statement_assembly_validate_only_blocked"
        )
        report["next_slice"] = "sec_xbrl_statement_assembly_remediation_v1"
    return report


def _summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    statements = list(packet.get("statements") or [])
    return {
        "packet_status": packet.get("status"),
        "review_ready": packet.get("review_ready") is True,
        "statement_count": packet.get("statement_count"),
        "statements_with_rows": sum(1 for item in statements if int(item.get("line_count") or 0) > 0),
        "total_review_rows": packet.get("total_review_rows"),
        "provenance_complete_count": packet.get("provenance_complete_count"),
        "review_exception_count": packet.get("review_exception_count"),
        "identity_residuals_within_tolerance": packet.get("identity_rollup", {}).get(
            "identity_residuals_within_tolerance"
        ),
    }


def _criteria(*, report: Mapping[str, Any], runtime_posture: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = dict(report.get("summary") or {})
    statements = list(report.get("statements") or [])
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            runtime_posture_criterion_passed(runtime_posture),
            runtime_posture_criterion_evidence(runtime_posture),
            "statement_assembly_defaults_not_off",
        ),
        _criterion(
            "statement_packet_ready_fail_closed",
            summary.get("packet_status") == "statement_assembly_ready"
            and int(summary.get("total_review_rows") or 0) > 0
            and summary.get("review_ready") is True,
            summary,
            "statement_assembly_packet_not_ready",
        ),
        _criterion(
            "statement_rows_are_consistent",
            _statement_rows_consistent(statements=statements, summary=summary),
            {
                "statement_count": summary.get("statement_count"),
                "total_review_rows": summary.get("total_review_rows"),
            },
            "statement_assembly_rows_inconsistent",
        ),
        _criterion(
            "redaction_clean",
            report.get("redaction", {}).get("passed") is True,
            dict(report.get("redaction") or {}),
            "statement_assembly_report_redaction_failed",
        ),
        _criterion(
            "validate_only_non_goals_preserved",
            report.get("validate_only") is True
            and report.get("live_network_used") is False
            and report.get("arelle_invoked") is False
            and report.get("value_reveal_performed") is False
            and report.get("runtime_defaults_changed") is False
            and non_goals.get("final_financial_statement_semantics_claimed") is False
            and non_goals.get("linkbase_emission_claimed") is False
            and non_goals.get("per_period_projection_claimed") is False
            and non_goals.get("persisted_store_claimed") is False
            and non_goals.get("production_readiness_claimed") is False,
            {
                "validate_only": report.get("validate_only"),
                "non_goals_preserved": non_goals,
            },
            "statement_assembly_validate_only_boundary_regressed",
        ),
    ]


def _statement_rows_consistent(*, statements: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> bool:
    total_rows = sum(int(item.get("line_count") or 0) for item in statements)
    return (
        len(statements) == 3
        and [item.get("statement") for item in statements] == ["income", "balance", "cashflow"]
        and total_rows == int(summary.get("total_review_rows") or 0)
        and total_rows > 0
        and all(len(list(item.get("rows") or [])) == int(item.get("line_count") or 0) for item in statements)
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


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
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

