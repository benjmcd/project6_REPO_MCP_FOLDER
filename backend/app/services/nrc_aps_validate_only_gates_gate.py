from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import nrc_aps_sync_drift
from app.services import nrc_aps_validate_only_gates as validate_only_runtime
from app.services import nrc_aps_validate_only_gates_contract as contract
from app.services import review_nrc_aps_runtime


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_validate_only_gates_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]
    if normalized_run_ids:
        return [{"run_id": run_id} for run_id in normalized_run_ids]
    bindings = review_nrc_aps_runtime.discover_runtime_bindings()
    ordered = sorted(
        bindings,
        key=lambda binding: review_nrc_aps_runtime._binding_sort_key(binding.summary),
        reverse=True,
    )
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": binding.run_id} for binding in ordered]


def _failure_paths(binding: review_nrc_aps_runtime.ReviewRuntimeBinding) -> list[Path]:
    scope = contract.safe_path_token(f"run_{validate_only_runtime._safe_scope_token(binding.run_id)}")
    pattern = f"{scope}_*_aps_validate_only_gates_failure_v1.json"
    return sorted((binding.review_root / "gate_reports").glob(pattern), key=lambda path: path.name)


def _load_runtime_query_plan(database_path: Path, run_id: str) -> dict[str, Any]:
    database_uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(database_uri, uri=True, check_same_thread=False)
    except sqlite3.DatabaseError:
        return {}
    try:
        row = connection.execute(
            """
            SELECT query_plan_json
            FROM connector_run
            WHERE connector_run_id = ?
              AND connector_key = ?
            LIMIT 1
            """,
            (run_id, "nrc_adams_aps"),
        ).fetchone()
    except sqlite3.DatabaseError:
        return {}
    finally:
        connection.close()
    if row is None:
        return {}
    raw_query_plan = row[0]
    if isinstance(raw_query_plan, dict):
        return dict(raw_query_plan)
    if isinstance(raw_query_plan, str) and raw_query_plan.strip():
        try:
            payload = json.loads(raw_query_plan)
        except json.JSONDecodeError:
            return {}
        return dict(payload) if isinstance(payload, dict) else {}
    return {}


def _validate_failure_payload(payload: dict[str, Any], reasons: list[str]) -> None:
    if str(payload.get("schema_id") or "") != contract.APS_VALIDATE_ONLY_GATES_FAILURE_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
        return
    if int(payload.get("schema_version") or 0) != contract.APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    for field_name, expected_value in contract.projection_identity_payload().items():
        if payload.get(field_name) != expected_value:
            reasons.append(
                contract.APS_GATE_FAILURE_PROJECTION_CONTRACT
                if field_name == "projection_contract_id"
                else contract.APS_GATE_FAILURE_PROJECTION_MODE
            )
    checksum = str(payload.get("validate_only_gates_checksum") or "").strip()
    if not checksum or checksum != contract.compute_validate_only_gates_checksum(payload):
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def validate_validate_only_gates_gate(
    *,
    run_ids: list[str] | None = None,
    limit: int = 50,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    require_runs: bool = True,
) -> dict[str, Any]:
    run_rows = _load_candidate_runs(run_ids=run_ids, limit=limit)
    checks: list[dict[str, Any]] = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        reasons: list[str] = []
        try:
            binding = review_nrc_aps_runtime.resolve_runtime_binding_for_run(run_id=run_id)
        except (FileNotFoundError, ValueError):
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)
            checks.append(
                {
                    "run_id": run_id,
                    "validate_only_gates_refs": [],
                    "failure_refs": [],
                    "passed": False,
                    "reasons": sorted(list(dict.fromkeys(reasons))),
                }
            )
            continue

        artifact_refs: list[str] = []
        failure_refs: list[str] = []
        try:
            artifact_payload, artifact_path = validate_only_runtime.load_persisted_validate_only_gates_artifact(
                run_id=run_id,
                review_root=binding.review_root,
            )
            artifact_refs = [str(artifact_path)]
        except validate_only_runtime.ValidateOnlyGatesError:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)
            artifact_payload = {}
            artifact_path = None

        failure_paths = _failure_paths(binding)
        failure_refs = [str(path.resolve()) for path in failure_paths]
        for failure_path in failure_paths:
            failure_payload = _read_json(failure_path)
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload(failure_payload, reasons)

        if artifact_path is not None:
            try:
                summary_path, summary, gate_report_refs, _normalized = validate_only_runtime._collect_runtime_inputs(binding)
                expected_payload = contract.build_validate_only_gates_payload(
                    run_id=run_id,
                    summary_ref=str(summary_path),
                    summary_payload=summary,
                    gate_report_refs=gate_report_refs,
                    generated_at_utc=str(artifact_payload.get("generated_at_utc") or ""),
                )
                source_runtime = dict(artifact_payload.get("source_review_runtime") or {})
                if str(source_runtime.get("summary_ref") or "").strip() != str(summary_path.resolve()):
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_SUMMARY)
                if [str(item) for item in list(artifact_payload.get("gate_report_refs") or [])] != gate_report_refs:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_GATE_REPORTS)
                if dict(artifact_payload.get("gate_results") or {}) != dict(expected_payload.get("gate_results") or {}):
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_GATE_RESULTS)
                actual_counts = {
                    "gate_total": int(artifact_payload.get("gate_total") or 0),
                    "gate_passed": int(artifact_payload.get("gate_passed") or 0),
                    "gate_failed": int(artifact_payload.get("gate_failed") or 0),
                }
                expected_counts = {
                    "gate_total": int(expected_payload.get("gate_total") or 0),
                    "gate_passed": int(expected_payload.get("gate_passed") or 0),
                    "gate_failed": int(expected_payload.get("gate_failed") or 0),
                }
                if actual_counts != expected_counts:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_COUNTS)
                if contract.logical_validate_only_gates_payload(artifact_payload) != contract.logical_validate_only_gates_payload(expected_payload):
                    reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

                query_plan = _load_runtime_query_plan(binding.database_path, run_id) if binding.database_path else {}
                registry_refs = dict(query_plan.get("aps_validate_only_gates_report_refs") or {})
                artifact_registry = [str(item).strip() for item in list(registry_refs.get("aps_validate_only_gates_artifacts") or []) if str(item).strip()]
                if str(artifact_path) not in artifact_registry:
                    reasons.append(contract.APS_GATE_FAILURE_REGISTRY_REFS)
                summaries = [dict(item or {}) for item in list(query_plan.get("aps_validate_only_gates_summaries") or []) if isinstance(item, dict)]
                matching_summary = next(
                    (
                        item
                        for item in summaries
                        if str(item.get("validate_only_gates_id") or "").strip()
                        == str(artifact_payload.get("validate_only_gates_id") or "").strip()
                    ),
                    None,
                )
                if matching_summary is None:
                    reasons.append(contract.APS_GATE_FAILURE_REGISTRY_SUMMARY)
                else:
                    expected_summary = {
                        "validate_only_gates_id": str(artifact_payload.get("validate_only_gates_id") or ""),
                        "validate_only_gates_checksum": str(artifact_payload.get("validate_only_gates_checksum") or ""),
                        "owner_run_id": run_id,
                        "source_summary_ref": str(summary_path.resolve()),
                        "gate_total": int(artifact_payload.get("gate_total") or 0),
                        "gate_passed": int(artifact_payload.get("gate_passed") or 0),
                        "gate_failed": int(artifact_payload.get("gate_failed") or 0),
                        "ref": str(artifact_path),
                    }
                    if matching_summary != expected_summary:
                        reasons.append(contract.APS_GATE_FAILURE_REGISTRY_SUMMARY)
            except validate_only_runtime.ValidateOnlyGatesError:
                reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_SCHEMA)

        checks.append(
            {
                "run_id": run_id,
                "validate_only_gates_refs": artifact_refs,
                "failure_refs": failure_refs,
                "passed": len(set(reasons)) == 0,
                "reasons": sorted(list(dict.fromkeys(reasons))),
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_VALIDATE_ONLY_GATES_GATE_SCHEMA_ID,
        "schema_version": contract.APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": passed,
        "checked_runs": len(checks),
        "failed_runs": len([item for item in checks if not bool(item.get("passed"))]),
        "checks": checks,
        "evaluated_run_rows": len(run_rows),
        "require_runs": bool(require_runs),
    }
    if len(checks) == 0:
        report["passed"] = not bool(require_runs)
        if require_runs:
            report["no_runs_failure"] = True
    nrc_aps_sync_drift.write_json_deterministic(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate NRC APS validate-only runtime/report-ref artifacts (fail-closed).")
    parser.add_argument("--run-id", action="append", default=[], help="Optional specific run id(s) to validate.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of latest NRC APS runs to evaluate when --run-id is not supplied.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow no matching runs (default fail-closed when no runs are found).")
    args = parser.parse_args(argv)
    report = validate_validate_only_gates_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
