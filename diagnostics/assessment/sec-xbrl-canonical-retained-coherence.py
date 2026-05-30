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
    report_redaction_scan_payload,
)


REPORT_SCHEMA_ID = "diagnostics.sec_xbrl_canonical_retained_coherence.v1"
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-canonical-retained-coherence-report.json")
TARGET = "sec_xbrl_canonical_retained_coherence_validate_only_v1"
NEXT_SLICE = "sec_xbrl_sector_conditioned_canonical_families_deferred_design_v1"
_RAW_RESOLVED_FACT_ID_RE = re.compile(r"\brf[-_][A-Za-z0-9]")
_RAW_TOTAL_FACT_COUNT_KEY_RE = re.compile(r'"(?:retained_fact_count|total_fact_count)"')


REFERENCE_SECTOR_CLASS_RESULTS = (
    {
        "sector_class": "industrial_commercial",
        "issuer_count": 3,
        "normalized_fact_count": 66,
        "bound_count": 66,
        "missing_count": 0,
        "qname_consistent_count": 66,
        "value_reconciled_count": 66,
        "retains_dimensional": True,
        "retains_extension": True,
        "contract_b_subset_of_a": True,
        "contract_a_strict_superset": True,
        "derived_dual_input_binding_proven": True,
    },
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL canonical-to-retained coherence diagnostic. It writes a redacted "
            "sector-class aggregate summary and does not fetch SEC data, invoke Arelle, reveal values, "
            "mutate runtime defaults, or persist runtime artifacts."
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
    sector_results: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    config_text = (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    report = _reference_summary_report(
        sector_results=list(sector_results or REFERENCE_SECTOR_CLASS_RESULTS),
        config_defaults_off=_config_defaults_off(config_text),
    )
    report["redaction"] = _redaction_scan_payload(report)
    report["criteria"] = _criteria(report=report, config_defaults_off=_config_defaults_off(config_text))
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = "canonical_retained_coherence_validate_only_blocked"
        report["next_slice"] = "sec_xbrl_canonical_retained_coherence_remediation_v1"
    return report


def _reference_summary_report(
    *,
    sector_results: Sequence[Mapping[str, Any]],
    config_defaults_off: bool,
) -> dict[str, Any]:
    sectors = [_sector_summary(item) for item in sector_results]
    total_normalized = sum(int(item["normalized_fact_count"]) for item in sectors)
    total_bound = sum(int(item["bound_count"]) for item in sectors)
    total_missing = sum(int(item["missing_count"]) for item in sectors)
    total_qname = sum(int(item["qname_consistent_count"]) for item in sectors)
    total_value = sum(int(item["value_reconciled_count"]) for item in sectors)
    contract_passed = (
        total_normalized > 0
        and total_missing == 0
        and total_bound == total_normalized
        and total_qname == total_normalized
        and total_value == total_normalized
        and all(item["contract_b_subset_of_a"] for item in sectors)
        and all(item["contract_a_strict_superset"] for item in sectors)
    )
    report: dict[str, Any] = {
        "schema_id": REPORT_SCHEMA_ID,
        "target": TARGET,
        "decision": "canonical_retained_coherence_validate_only_ready",
        "source_mode": "redacted_reference_sector_class_summary",
        "evidence_scope": "operator_run_reference_summary_covers_three_issuers_not_all_sectors",
        "validate_only": True,
        "live_network_used": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "runtime_defaults_changed": False,
        "value_authority": "governed_arelle_sidecar_value_store",
        "retained_view_authority": "statement_classification_sidecar_fact_projection",
        "canonical_view_authority": "canonical_projection_resolved_fact_ids",
        "summary": {
            "contract_passed": contract_passed,
            "total_normalized": total_normalized,
            "total_bound": total_bound,
            "total_missing": total_missing,
        },
        "per_sector_class": sectors,
        "redaction": {},
        "criteria": [],
        "blocking_reasons": [],
        "next_slice": NEXT_SLICE,
        "non_goals_preserved": {
            "sector_families_implemented": False,
            "statement_assembly_claimed": False,
            "per_period_projection_claimed": False,
            "persisted_store_claimed": False,
            "default_on_readiness_claimed": False,
            "production_readiness_claimed": False,
            "value_reveal_performed": False,
            "live_network_or_arelle_required": False,
        },
    }
    report["criteria"] = _criteria(report=report, config_defaults_off=config_defaults_off)
    report["blocking_reasons"] = _blocking_reasons(report["criteria"])
    if report["blocking_reasons"]:
        report["decision"] = "canonical_retained_coherence_validate_only_blocked"
        report["next_slice"] = "sec_xbrl_canonical_retained_coherence_remediation_v1"
    return report


def _sector_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    normalized = int(item["normalized_fact_count"])
    bound = int(item["bound_count"])
    missing = int(item["missing_count"])
    qname = int(item["qname_consistent_count"])
    value = int(item["value_reconciled_count"])
    return {
        "sector_class": str(item["sector_class"]),
        "issuer_count": int(item["issuer_count"]),
        "normalized_fact_count": normalized,
        "bound_count": bound,
        "missing_count": missing,
        "qname_consistent_count": qname,
        "value_reconciled_count": value,
        "retains_dimensional": item.get("retains_dimensional") is True,
        "retains_extension": item.get("retains_extension") is True,
        "contract_b_subset_of_a": item.get("contract_b_subset_of_a") is True,
        "contract_qname_consistent": qname == normalized,
        "contract_value_single_authority": value == normalized,
        "contract_a_strict_superset": item.get("contract_a_strict_superset") is True,
        "contract_passed": (
            normalized > 0
            and bound == normalized
            and missing == 0
            and qname == normalized
            and value == normalized
            and item.get("contract_b_subset_of_a") is True
            and item.get("contract_a_strict_superset") is True
        ),
        "derived_dual_input_binding_proven": item.get("derived_dual_input_binding_proven") is True,
    }


def _criteria(*, report: Mapping[str, Any], config_defaults_off: bool) -> list[dict[str, Any]]:
    redaction = _redaction_scan_payload(report)
    summary = dict(report.get("summary") or {})
    sectors = list(report.get("per_sector_class") or [])
    non_goals = dict(report.get("non_goals_preserved") or {})
    return [
        _criterion(
            "committed_runtime_defaults_remain_off",
            config_defaults_off,
            {"config_defaults_off": config_defaults_off},
            "canonical_retained_coherence_defaults_not_off",
        ),
        _criterion(
            "coherence_contract_passes_fail_closed",
            summary.get("contract_passed") is True and int(summary.get("total_missing") or 0) == 0,
            {
                "contract_passed": summary.get("contract_passed"),
                "total_missing": summary.get("total_missing"),
            },
            "canonical_retained_coherence_contract_failed",
        ),
        _criterion(
            "sector_aggregate_counts_are_consistent",
            _sector_counts_consistent(sectors=sectors, summary=summary),
            {
                "sector_class_count": len(sectors),
                "total_normalized": summary.get("total_normalized"),
                "total_bound": summary.get("total_bound"),
                "total_missing": summary.get("total_missing"),
            },
            "canonical_retained_coherence_counts_inconsistent",
        ),
        _criterion(
            "retained_view_is_strict_superset",
            all(
                item.get("contract_a_strict_superset") is True
                and item.get("retains_dimensional") is True
                and item.get("retains_extension") is True
                for item in sectors
            ),
            {
                "retains_dimensional_all": all(item.get("retains_dimensional") is True for item in sectors),
                "retains_extension_all": all(item.get("retains_extension") is True for item in sectors),
            },
            "canonical_retained_coherence_retained_view_not_strict_superset",
        ),
        _criterion(
            "redaction_clean",
            redaction.get("passed") is True,
            redaction,
            "canonical_retained_coherence_report_redaction_failed",
        ),
        _criterion(
            "validate_only_non_goals_preserved",
            report.get("validate_only") is True
            and report.get("live_network_used") is False
            and report.get("arelle_invoked") is False
            and report.get("value_reveal_performed") is False
            and report.get("runtime_defaults_changed") is False
            and non_goals.get("sector_families_implemented") is False
            and non_goals.get("statement_assembly_claimed") is False
            and non_goals.get("per_period_projection_claimed") is False
            and non_goals.get("persisted_store_claimed") is False,
            {
                "validate_only": report.get("validate_only"),
                "live_network_used": report.get("live_network_used"),
                "arelle_invoked": report.get("arelle_invoked"),
                "value_reveal_performed": report.get("value_reveal_performed"),
                "runtime_defaults_changed": report.get("runtime_defaults_changed"),
                "non_goals_preserved": non_goals,
            },
            "canonical_retained_coherence_validate_only_boundary_regressed",
        ),
    ]


def _sector_counts_consistent(*, sectors: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> bool:
    total_normalized = sum(int(item.get("normalized_fact_count") or 0) for item in sectors)
    total_bound = sum(int(item.get("bound_count") or 0) for item in sectors)
    total_missing = sum(int(item.get("missing_count") or 0) for item in sectors)
    return (
        bool(sectors)
        and total_normalized == int(summary.get("total_normalized") or 0)
        and total_bound == int(summary.get("total_bound") or 0)
        and total_missing == int(summary.get("total_missing") or 0)
        and total_bound + total_missing == total_normalized
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


def _redaction_scan_payload(payload: Any) -> dict[str, bool]:
    text = json.dumps(payload, sort_keys=True) if not isinstance(payload, str) else payload
    base = report_redaction_scan_payload(payload)
    raw_resolved_fact_ids_found = bool(_RAW_RESOLVED_FACT_ID_RE.search(text))
    raw_issuer_identity_found = any(token in text for token in ("issuer_ref", "issuer_hash", "issuer_name"))
    raw_total_fact_counts_found = bool(_RAW_TOTAL_FACT_COUNT_KEY_RE.search(text))
    return {
        **base,
        "raw_resolved_fact_ids_found": raw_resolved_fact_ids_found,
        "raw_issuer_identity_found": raw_issuer_identity_found,
        "raw_total_fact_counts_found": raw_total_fact_counts_found,
        "passed": (
            base.get("passed") is True
            and not raw_resolved_fact_ids_found
            and not raw_issuer_identity_found
            and not raw_total_fact_counts_found
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


if __name__ == "__main__":
    raise SystemExit(main())
