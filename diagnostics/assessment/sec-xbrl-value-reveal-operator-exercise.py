from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-report.json")


REQUIRED_TEST_SIGNALS = {
    "flag_off_endpoint_blocks": "sec_edgar_arelle_value_reveal_feature_flag_disabled",
    "flag_off_surface_blocks_legacy_fields": "sec_edgar_operator_product_surface_value_reveal_flag_disabled",
    "flag_on_sibling_endpoint_ready": "test_layer3_api_reveals_sec_edgar_arelle_values_only_through_governed_sibling_endpoint",
    "audit_receipt_redacted_status": "layer3.sec_edgar_arelle_value_reveal_status.v1",
    "idempotent_replay": '"idempotent_replay"] is True',
    "identity_like_value_redaction": "sec_edgar_arelle_value_reveal_raw_identity_value_redacted",
    "legacy_receipt_status_compatibility": "test_layer3_api_reads_legacy_sec_edgar_arelle_value_reveal_audit_receipt",
    "corrupted_receipt_blocks": "test_layer3_api_rejects_corrupted_sec_edgar_arelle_value_reveal_audit_receipt",
    "fail_closed_inputs": "test_layer3_api_blocks_sec_edgar_arelle_value_reveal_fail_closed_inputs",
    "lineage_and_write_fail_closed": "test_layer3_api_blocks_sec_edgar_arelle_value_reveal_lineage_and_redaction_guards",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SEC XBRL governed value-reveal operator-exercise readiness check. "
            "This is validate-only and does not enable flags, fetch SEC data, or create receipts."
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


def build_report(*, source_root: Path) -> dict[str, Any]:
    sources = _source_text(source_root)
    defaults = {
        "arelle_cutover_default_enabled": _contains(
            sources["config"],
            'layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=True,',
        ),
        "value_reveal_default_off": _contains(
            sources["config"],
            'layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False,',
        ),
        "controlled_value_reveal_submit_default_off": _contains(
            sources["config"],
            'layer3_sec_xbrl_controlled_value_reveal_submit_enabled: bool = Field(\n        default=False,',
        ),
    }
    endpoint = {
        "post_reveal_route_present": _contains(
            sources["api"],
            '"/source/sec-edgar/real-company-corpus/operator-value-reveal"',
        )
        and _contains(sources["api"], "reveal_sec_edgar_arelle_values"),
        "status_route_present": _contains(
            sources["api"],
            '"/source/sec-edgar/real-company-corpus/operator-value-reveal/status/{reveal_receipt_id}"',
        )
        and _contains(sources["api"], "inspect_sec_edgar_arelle_value_reveal_status"),
        "request_schema_present": _contains(
            sources["api"],
            "Layer3SecEdgarArelleValueRevealRequest",
        ),
    }
    audit = {
        "receipt_dir_separate": _contains(
            sources["service"],
            'RECEIPT_DIR = "layer3-sec-edgar-arelle-value-reveal"',
        ),
        "actor_hash_used": _contains(sources["service"], '"actor_hash"'),
        "idempotency_key_hash_used": _contains(sources["service"], '"idempotency_key_hash"'),
        "lineage_hashes_projected": _contains(sources["service"], '"lineage_hashes"'),
        "status_projection_hashes_only": _contains(sources["service"], '"revealed_facts": []')
        and _contains(sources["service"], '"raw_values_returned": False'),
        "write_failure_blocks": _contains(
            sources["service"],
            "sec_edgar_arelle_value_reveal_receipt_write_failed",
        ),
        "current_and_legacy_hash_basis": _contains(
            sources["service"],
            "post_1966_value_reveal_receipt_hash_basis_v2",
        )
        and _contains(sources["service"], "pre_1966_value_reveal_receipt_hash_basis_v1"),
    }
    surface = {
        "legacy_surface_fields_fail_closed": _contains(
            sources["operator_surface"],
            "sec_edgar_operator_product_surface_value_reveal_requires_sibling_endpoint",
        ),
        "surface_flag_check_reason": _contains(
            sources["operator_surface"],
            "sec_edgar_operator_product_surface_value_reveal_flag_disabled",
        ),
        "default_surface_not_requested": _contains(sources["tests"], 'default_surface["value_reveal_state"] == "not_requested"'),
    }
    tests = {
        name: {"test_signal": signal, "present": _contains(sources["tests"], signal)}
        for name, signal in REQUIRED_TEST_SIGNALS.items()
    }
    planning = {
        "operator_exercise_named_next": _contains(
            sources["value_reveal_doc"],
            "sec_edgar_arelle_value_reveal_operator_exercise_v1",
        ),
        "default_on_followup_separate": _contains(
            sources["value_reveal_doc"],
            "sec_edgar_arelle_governance_remediation_followups_v1",
        ),
        "default_enablement_gate_separate": _contains(
            sources["value_reveal_doc"],
            "sec_edgar_arelle_value_reveal_default_enablement_gate_v1",
        ),
    }
    non_goals = {
        "fact_authority_cutover_default_enabled": defaults["arelle_cutover_default_enabled"],
        "value_reveal_default_enabled": False,
        "controlled_value_reveal_submit_default_enabled": False,
        "operator_exercise_performed_by_this_check": False,
        "sec_network_fetch_performed": False,
        "sidecar_receipt_created": False,
        "raw_values_committed": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
        "candidate_b_sec_routing_performed": False,
    }
    criteria = [
        _criterion(
            "value_reveal_defaults_remain_off",
            defaults["value_reveal_default_off"] and defaults["controlled_value_reveal_submit_default_off"],
            defaults,
            "value_reveal_operator_exercise_value_reveal_defaults_not_off",
        ),
        _criterion("sibling_endpoint_available", all(endpoint.values()), endpoint, "value_reveal_operator_exercise_endpoint_missing"),
        _criterion("audit_receipt_governance_available", all(audit.values()), audit, "value_reveal_operator_exercise_audit_receipt_gap"),
        _criterion("default_surface_boundary_preserved", all(surface.values()), surface, "value_reveal_operator_exercise_surface_boundary_gap"),
        _criterion(
            "focused_operator_exercise_tests_present",
            all(item["present"] for item in tests.values()),
            tests,
            "value_reveal_operator_exercise_tests_missing",
        ),
        _criterion(
            "planning_names_operator_exercise_before_default_enablement",
            all(planning.values()),
            planning,
            "value_reveal_operator_exercise_planning_gap",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    ready = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_value_reveal_operator_exercise.v1",
        "target": "sec_edgar_arelle_value_reveal_operator_exercise_v1",
        "decision": "value_reveal_operator_exercise_ready" if ready else "value_reveal_operator_exercise_blocked",
        "headline": (
            "Governed value reveal is ready for an isolated operator exercise; this check did not perform the exercise."
            if ready
            else "Governed value reveal is not ready for operator exercise; see blocking reasons."
        ),
        "ready_for_operator_exercise": ready,
        "operator_exercise_performed": False,
        "criteria": criteria,
        "blocking_reasons": blockers,
        "operator_exercise_requirements": [
            "enable LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED only in isolated local/operator runtime",
            "bind a persisted READY Arelle sidecar receipt id/hash and matching dataset_version id/hash",
            "submit an explicit actor self-attestation and operator_reveal_confirmation=true",
            "verify returned values are effective Arelle values and identity-like values stay redacted",
            "verify audit receipt status projection is hashes-only and idempotent replay returns the same receipt",
            "verify the default product surface over the same filing still returns no raw values",
            "turn the reveal flag back off after the exercise",
        ],
        "non_goals_preserved": non_goals,
        "next_slice": "sec_edgar_arelle_value_reveal_operator_exercise_v1" if ready else "sec_edgar_arelle_governed_value_reveal_v1",
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
        "api": source_root / "backend" / "app" / "api" / "layer3.py",
        "service": source_root / "backend" / "app" / "services" / "layer3_sec_edgar_arelle_value_reveal.py",
        "operator_surface": source_root / "backend" / "app" / "services" / "layer3_sec_edgar_operator_product_surface.py",
        "tests": source_root / "backend" / "tests" / "test_layer3_api.py",
        "value_reveal_doc": source_root
        / "next_milestone_plans"
        / "Layer3_planning_docs"
        / "1260-sec-xbrl-operator-value-reveal.md",
    }
    return {name: path.read_text(encoding="utf-8") for name, path in files.items()}


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
