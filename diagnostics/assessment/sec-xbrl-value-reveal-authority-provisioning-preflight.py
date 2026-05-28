from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-value-reveal-authority-provisioning-preflight-report.json")
RUN_REPORT = Path("diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-run-report.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only preflight for SEC XBRL value-reveal authority provisioning. "
            "This does not fetch SEC data, invoke Arelle, create sidecars, or reveal values."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--run-report", default=str(RUN_REPORT))
    args = parser.parse_args()
    report = build_report(source_root=ROOT, run_report_path=_resolve_path(args.run_report))
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(*, source_root: Path, run_report_path: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    current_env = dict(os.environ if env is None else env)
    run_report = _read_json(run_report_path)
    config_text = (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    arelle = _arelle_env(current_env)
    live_network = {
        "committed_default_off": _contains(
            config_text,
            'layer3_sec_edgar_live_network_enabled: bool = Field(\n        default=False,',
        ),
        "runtime_env_enabled_for_this_preflight": _truthy(current_env.get("LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED")),
        "user_agent_env_present": bool(str(current_env.get("LAYER3_SEC_EDGAR_USER_AGENT") or "").strip()),
    }
    authority_blocked = run_report.get("decision") == "value_reveal_operator_exercise_blocked_missing_authority"
    criteria = [
        _criterion(
            "operator_exercise_currently_missing_authority",
            authority_blocked,
            {
                "run_report": _repo_display_path(run_report_path),
                "run_report_decision": run_report.get("decision"),
                "ready_to_run_operator_exercise": run_report.get("ready_to_run_operator_exercise"),
            },
            "authority_provisioning_preflight_run_report_not_blocked",
        ),
        _criterion(
            "live_network_not_enabled_by_committed_default",
            live_network["committed_default_off"],
            live_network,
            "authority_provisioning_preflight_live_network_default_changed",
        ),
        _criterion(
            "arelle_environment_available_for_future_granted_run",
            arelle["python_exists"] and arelle["taxonomy_packages_all_exist"] and arelle["cache_dir_exists"],
            arelle,
            "authority_provisioning_preflight_arelle_environment_missing",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    env_ready = not blockers and live_network["runtime_env_enabled_for_this_preflight"] and live_network["user_agent_env_present"]
    return {
        "schema_id": "diagnostics.sec_xbrl_value_reveal_authority_provisioning_preflight.v1",
        "target": "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1",
        "decision": (
            "authority_provisioning_preflight_ready_for_explicit_granted_run"
            if env_ready
            else "authority_provisioning_preflight_requires_explicit_grant_or_environment"
        ),
        "headline": (
            "Authority provisioning can proceed only in a separately granted live run with network, user-agent, and Arelle environment enabled."
        ),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "live_network_preflight": live_network,
        "arelle_environment_preflight": arelle,
        "operator_exercise_run_report_summary": {
            "decision": run_report.get("decision"),
            "ready_to_run_operator_exercise": run_report.get("ready_to_run_operator_exercise"),
            "redacted_inventory": run_report.get("redacted_inventory"),
        },
        "required_next_action": (
            "run_authority_provisioning_with_explicit_operator_grant"
            if env_ready
            else "obtain_explicit_operator_grant_and_arelle_network_environment_then_rerun_preflight"
        ),
        "non_goals_preserved": {
            "sec_network_fetch_performed": False,
            "arelle_subprocess_invoked": False,
            "sidecar_receipt_created": False,
            "dataset_version_created": False,
            "audit_receipt_created": False,
            "raw_values_returned": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "cutover_default_enabled": False,
            "value_reveal_default_enabled": False,
            "candidate_b_sec_routing_performed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "next_slice": "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1",
    }


def _arelle_env(env: Mapping[str, str]) -> dict[str, Any]:
    python_path = str(env.get("SEC_XBRL_ARELLE_PYTHON") or env.get("ARELLE_PYTHON") or "").strip()
    packages = [
        item.strip()
        for item in str(env.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES") or "").split(os.pathsep)
        if item.strip()
    ]
    cache_dir = str(env.get("SEC_XBRL_ARELLE_CACHE_DIR") or "").strip()
    python_exists = Path(python_path).is_file() if python_path else False
    package_exists = [Path(item).is_file() for item in packages]
    cache_exists = Path(cache_dir).is_dir() if cache_dir else False
    return {
        "python_present": bool(python_path),
        "python_exists": python_exists,
        "python_marker": _marker(python_path) if python_path else None,
        "taxonomy_packages_present": bool(packages),
        "taxonomy_package_count": len(packages),
        "taxonomy_package_existing_count": sum(1 for item in package_exists if item),
        "taxonomy_package_markers": [_marker(item) for item in packages],
        "taxonomy_packages_all_exist": bool(packages) and all(package_exists),
        "cache_dir_present": bool(cache_dir),
        "cache_dir_exists": cache_exists,
        "cache_dir_marker": _marker(cache_dir) if cache_dir else None,
        "internet_connectivity_mode": str(env.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY") or "offline").strip().lower(),
    }


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _marker(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _repo_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
