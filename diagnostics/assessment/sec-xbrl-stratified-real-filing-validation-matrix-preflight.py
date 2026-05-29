from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path(
    "diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight-report.json"
)
DEFAULT_RUNBOOK_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json"
)
DEFAULT_DEFAULT_POSTURE_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-default-posture-decision-report.json"
)
DEFAULT_REAL_PRODUCT_RUNNER_REPORT = Path(
    "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json"
)

NEXT_MATRIX_SLICE = "sec_edgar_stratified_real_filing_validation_matrix_v1"
TARGET = "sec_edgar_stratified_real_filing_validation_matrix_preflight_v1"
LIVE_AUTH_ENV = "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED"
STORAGE_ENV = "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR"

REQUIRED_STRATA = {
    "large_domestic_us_gaap",
    "small_mid_domestic_us_gaap",
    "foreign_private_ifrs_20f",
    "canadian_40f",
    "current_report_8k_sparse",
    "foreign_6k_sparse",
    "amendment_restatement",
    "no_inline_or_zero_fact_diagnostic",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only preflight for the SEC XBRL stratified real-filing validation "
            "matrix. This does not fetch SEC data, invoke Arelle, create sidecars, reveal "
            "values, or mutate defaults."
        )
    )
    parser.add_argument("--runbook-report", default=str(DEFAULT_RUNBOOK_REPORT))
    parser.add_argument("--default-posture-report", default=str(DEFAULT_DEFAULT_POSTURE_REPORT))
    parser.add_argument("--real-product-runner-report", default=str(DEFAULT_REAL_PRODUCT_RUNNER_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = build_report(
        source_root=ROOT,
        runbook_report_path=_resolve_path(args.runbook_report),
        default_posture_report_path=_resolve_path(args.default_posture_report),
        real_product_runner_report_path=_resolve_path(args.real_product_runner_report),
    )
    output = _resolve_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_display_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    source_root: Path,
    runbook_report_path: Path,
    default_posture_report_path: Path,
    real_product_runner_report_path: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    current_env = dict(os.environ if env is None else env)
    runbook = _read_json(runbook_report_path)
    default_posture = _read_json(default_posture_report_path)
    real_product = _read_json(real_product_runner_report_path)
    config_text = (source_root / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")

    defaults = _default_posture_projection(config_text=config_text, default_posture=default_posture)
    matrix = runbook.get("selected_stratified_matrix")
    selected_matrix = matrix if isinstance(matrix, list) else []
    matrix_projection = _matrix_projection(selected_matrix)
    runtime = _runtime_preflight(source_root=source_root, env=current_env)
    real_summary = dict(real_product.get("summary") or {})

    criteria = [
        _criterion(
            "operator_runbook_selected_matrix_ready",
            runbook.get("decision") == "operator_runbook_and_stratified_matrix_selection_ready"
            and runbook.get("next_slice") == NEXT_MATRIX_SLICE,
            {
                "runbook_report": _repo_display_path(runbook_report_path),
                "decision": runbook.get("decision"),
                "next_slice": runbook.get("next_slice"),
            },
            "stratified_matrix_preflight_runbook_not_ready",
        ),
        _criterion(
            "committed_defaults_and_selected_posture_remain_default_off",
            defaults["all_defaults_off"] and defaults["selected_posture"] == "explicit_operator_only_default_off",
            defaults,
            "stratified_matrix_preflight_defaults_not_default_off",
        ),
        _criterion(
            "selected_matrix_covers_required_strata_without_raw_identity",
            matrix_projection["covers_required_strata"]
            and matrix_projection["raw_issuer_examples_committed"] is False
            and matrix_projection["all_strata_have_forms"]
            and matrix_projection["minimum_issuer_hash_total"] >= 18,
            matrix_projection,
            "stratified_matrix_preflight_selected_matrix_incomplete",
        ),
        _criterion(
            "real_product_runner_baseline_supports_matrix_expansion",
            real_product.get("decision") == "real_corpus_default_on_validated"
            and real_product.get("gate_verdict") == "PASS"
            and _int(real_summary.get("supported_record_count")) >= 30,
            {
                "real_product_runner_report": _repo_display_path(real_product_runner_report_path),
                "decision": real_product.get("decision"),
                "gate_verdict": real_product.get("gate_verdict"),
                "supported_record_count": real_summary.get("supported_record_count"),
            },
            "stratified_matrix_preflight_real_product_baseline_not_ready",
        ),
        _criterion(
            "explicit_live_authorization_recorded_for_future_matrix_execution",
            runtime["live_authorization_present"],
            runtime,
            "stratified_matrix_preflight_explicit_live_authorization_missing",
        ),
        _criterion(
            "sec_user_agent_present_for_future_matrix_execution",
            runtime["sec_user_agent_present"],
            runtime,
            "stratified_matrix_preflight_user_agent_missing",
        ),
        _criterion(
            "arelle_environment_available_for_future_matrix_execution",
            runtime["arelle"]["python_exists"]
            and runtime["arelle"]["taxonomy_packages_all_exist"]
            and runtime["arelle"]["cache_dir_exists"],
            runtime["arelle"],
            "stratified_matrix_preflight_arelle_environment_missing",
        ),
        _criterion(
            "isolated_runtime_storage_ready_outside_repo",
            runtime["storage"]["storage_dir_exists"] and runtime["storage"]["storage_dir_inside_repo"] is False,
            runtime["storage"],
            "stratified_matrix_preflight_isolated_storage_missing_or_inside_repo",
        ),
    ]
    blockers = [
        {"criterion": item["criterion"], "reason": item["blocked_reason"], "evidence": item["evidence"]}
        for item in criteria
        if item["state"] != "passed"
    ]
    ready = not blockers
    return {
        "schema_id": "diagnostics.sec_xbrl_stratified_real_filing_validation_matrix_preflight.v1",
        "target": TARGET,
        "decision": (
            "stratified_matrix_preflight_ready_for_explicit_live_execution"
            if ready
            else "stratified_matrix_preflight_requires_authorization_or_environment"
        ),
        "headline": _headline(ready=ready, blockers=blockers),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "selected_matrix_summary": matrix_projection,
        "runtime_preflight": runtime,
        "source_reports": {
            "operator_runbook_matrix_selection": _repo_display_path(runbook_report_path),
            "default_posture": _repo_display_path(default_posture_report_path),
            "real_product_runner": _repo_display_path(real_product_runner_report_path),
        },
        "required_next_action": (
            "execute_stratified_matrix_live_run_under_runbook_controls"
            if ready
            else "obtain_explicit_live_authorization_and_isolated_arelle_runtime_then_rerun_preflight"
        ),
        "non_goals_preserved": {
            "sec_network_fetch_performed": False,
            "arelle_subprocess_invoked": False,
            "source_acquisition_performed": False,
            "sidecar_receipt_created": False,
            "dataset_version_created": False,
            "audit_receipt_created": False,
            "value_reveal_request_performed": False,
            "raw_values_returned": False,
            "raw_values_committed": False,
            "raw_identity_committed": False,
            "local_storage_roots_committed": False,
            "runtime_default_changed": False,
            "production_readiness_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "next_slice": (
            "sec_edgar_stratified_real_filing_validation_matrix_live_execution_v1"
            if ready
            else NEXT_MATRIX_SLICE
        ),
    }


def _default_posture_projection(*, config_text: str, default_posture: Mapping[str, Any]) -> dict[str, Any]:
    selected = dict(default_posture.get("selected_posture") or {})
    sec_live_default_off = _contains(
        config_text,
        "layer3_sec_edgar_live_network_enabled: bool = Field(\n        default=False,",
    )
    cutover_default_off = _contains(
        config_text,
        "layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=False,",
    )
    reveal_default_off = _contains(
        config_text,
        "layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False,",
    )
    return {
        "decision": default_posture.get("decision"),
        "selected_posture": selected.get("posture"),
        "sec_live_network_default_off": sec_live_default_off,
        "arelle_fact_authority_cutover_default_off": cutover_default_off,
        "arelle_value_reveal_default_off": reveal_default_off,
        "all_defaults_off": sec_live_default_off and cutover_default_off and reveal_default_off,
    }


def _matrix_projection(matrix: list[Any]) -> dict[str, Any]:
    rows = [dict(item) for item in matrix if isinstance(item, Mapping)]
    selected = [str(item.get("stratum") or "") for item in rows if item.get("stratum")]
    minimum_total = sum(_int(item.get("minimum_issuer_hashes")) for item in rows)
    raw_examples = any(item.get("raw_issuer_examples_committed") is not False for item in rows)
    missing = sorted(REQUIRED_STRATA - set(selected))
    return {
        "required_strata": sorted(REQUIRED_STRATA),
        "selected_strata": selected,
        "missing_required_strata": missing,
        "covers_required_strata": not missing,
        "matrix_row_count": len(rows),
        "minimum_issuer_hash_total": minimum_total,
        "raw_issuer_examples_committed": raw_examples,
        "all_strata_have_forms": all(bool(item.get("forms")) for item in rows) and bool(rows),
        "forms_by_stratum": {
            str(item.get("stratum")): [str(form) for form in item.get("forms", [])]
            for item in rows
            if item.get("stratum")
        },
    }


def _runtime_preflight(*, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    user_agent = str(env.get("LAYER3_SEC_EDGAR_USER_AGENT") or "").strip()
    return {
        "live_authorization_env_var": LIVE_AUTH_ENV,
        "live_authorization_present": _truthy(env.get(LIVE_AUTH_ENV)),
        "sec_user_agent_present": bool(user_agent),
        "sec_user_agent_marker": _marker(user_agent) if user_agent else None,
        "arelle": _arelle_env(env),
        "storage": _storage_env(source_root=source_root, env=env),
    }


def _arelle_env(env: Mapping[str, str]) -> dict[str, Any]:
    python_path = str(env.get("SEC_XBRL_ARELLE_PYTHON") or env.get("ARELLE_PYTHON") or "").strip()
    packages = [
        item.strip()
        for item in str(env.get("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES") or "").split(os.pathsep)
        if item.strip()
    ]
    cache_dir = str(env.get("SEC_XBRL_ARELLE_CACHE_DIR") or "").strip()
    package_exists = [Path(item).is_file() for item in packages]
    return {
        "python_present": bool(python_path),
        "python_exists": Path(python_path).is_file() if python_path else False,
        "python_marker": _marker(python_path) if python_path else None,
        "taxonomy_packages_present": bool(packages),
        "taxonomy_package_count": len(packages),
        "taxonomy_package_existing_count": sum(1 for item in package_exists if item),
        "taxonomy_package_markers": [_marker(item) for item in packages],
        "taxonomy_packages_all_exist": bool(packages) and all(package_exists),
        "cache_dir_present": bool(cache_dir),
        "cache_dir_exists": Path(cache_dir).is_dir() if cache_dir else False,
        "cache_dir_marker": _marker(cache_dir) if cache_dir else None,
        "internet_connectivity_mode": str(env.get("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY") or "offline")
        .strip()
        .lower(),
    }


def _storage_env(*, source_root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    raw = str(env.get(STORAGE_ENV) or "").strip()
    storage = Path(raw) if raw else None
    resolved_root = source_root.resolve()
    resolved_storage = storage.resolve(strict=False) if storage is not None else None
    inside_repo = _is_relative_to(resolved_storage, resolved_root) if resolved_storage is not None else False
    return {
        "storage_env_var": STORAGE_ENV,
        "storage_dir_present": bool(raw),
        "storage_dir_exists": resolved_storage.is_dir() if resolved_storage is not None else False,
        "storage_dir_marker": _marker(str(resolved_storage)) if resolved_storage is not None else None,
        "storage_dir_inside_repo": inside_repo,
        "storage_dir_paths_redacted": True,
    }


def _criterion(criterion: str, passed: bool, evidence: Mapping[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": dict(evidence),
    }


def _headline(*, ready: bool, blockers: list[dict[str, Any]]) -> str:
    if ready:
        return (
            "Stratified real-filing validation matrix preflight is ready for a separately "
            "authorized live run under explicit-operator-only default-off controls."
        )
    reasons = ", ".join(str(item["reason"]) for item in blockers)
    return f"Stratified real-filing validation matrix preflight is blocked: {reasons}."


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _marker(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _is_relative_to(path: Path | None, root: Path) -> bool:
    if path is None:
        return False
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


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
