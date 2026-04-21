from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_deterministic_challenge_artifact as challenge
from app.services import nrc_aps_deterministic_challenge_artifact_contract as contract
from app.services import nrc_aps_deterministic_insight_artifact
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _owner_run_id_from_artifact_payload(payload: dict[str, Any]) -> str | None:
    source_insight = dict(payload.get("source_deterministic_insight_artifact") or {})
    owner_run_id = str(source_insight.get("owner_run_id") or "").strip()
    return owner_run_id or None


def _owner_run_id_from_failure_payload(payload: dict[str, Any]) -> str | None:
    owner_run_id = str(payload.get("owner_run_id") or "").strip()
    return owner_run_id or None


def _fallback_run_id_from_artifact_name(name: str) -> str | None:
    token = "_aps_deterministic_challenge_artifact_v1.json"
    failure_token = "_aps_deterministic_challenge_artifact_failure_v1.json"
    suffix = token if name.endswith(token) else failure_token if name.endswith(failure_token) else None
    if suffix is None:
        return None
    stem = name[: -len(suffix)]
    if not stem.startswith("run_"):
        return None
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    return "_".join(parts[1:-1]).strip() or None


def _artifact_scope_for_run_id(run_id: str) -> str:
    return f"run_{challenge._safe_scope_token(run_id)}"


def _payload_matches_requested_run(payload: dict[str, Any], run_id: str, owner_run_id: str | None) -> bool:
    if not payload:
        return True
    return owner_run_id is None or owner_run_id == run_id


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]

    if normalized_run_ids:
        return [{"run_id": run_id} for run_id in normalized_run_ids]

    payload_candidates: dict[str, float] = {}
    payload_scopes: set[str] = set()
    fallback_candidates: dict[str, float] = {}
    for path in reports_dir.glob("*_aps_deterministic_challenge_artifact_v1.json"):
        payload = _read_json(path)
        run_id = _owner_run_id_from_artifact_payload(payload)
        if run_id:
            payload_candidates[run_id] = max(
                float(path.stat().st_mtime),
                float(payload_candidates.get(run_id, 0.0)),
            )
            payload_scopes.add(_artifact_scope_for_run_id(run_id))
            continue
        fallback_run_id = _fallback_run_id_from_artifact_name(path.name)
        if fallback_run_id:
            fallback_candidates[fallback_run_id] = max(
                float(path.stat().st_mtime),
                float(fallback_candidates.get(fallback_run_id, 0.0)),
            )
    for path in reports_dir.glob("*_aps_deterministic_challenge_artifact_failure_v1.json"):
        payload = _read_json(path)
        run_id = _owner_run_id_from_failure_payload(payload)
        if run_id:
            payload_candidates[run_id] = max(
                float(path.stat().st_mtime),
                float(payload_candidates.get(run_id, 0.0)),
            )
            payload_scopes.add(_artifact_scope_for_run_id(run_id))
            continue
        fallback_run_id = _fallback_run_id_from_artifact_name(path.name)
        if fallback_run_id:
            fallback_candidates[fallback_run_id] = max(
                float(path.stat().st_mtime),
                float(fallback_candidates.get(fallback_run_id, 0.0)),
            )

    candidates = dict(payload_candidates)
    for fallback_run_id, mtime in fallback_candidates.items():
        if _artifact_scope_for_run_id(fallback_run_id) in payload_scopes:
            continue
        candidates[fallback_run_id] = max(float(mtime), float(candidates.get(fallback_run_id, 0.0)))
    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        challenge._validate_failure_payload_schema(payload)
    except challenge.DeterministicChallengeArtifactError:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)


def _validate_artifact_payload(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        challenge._validate_persisted_deterministic_challenge_artifact_payload(payload)
    except challenge.DeterministicChallengeArtifactError:
        reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_SCHEMA)
    for field_name, expected_value in contract.ruleset_identity_payload().items():
        if payload.get(field_name) != expected_value:
            reasons.append(contract.APS_GATE_FAILURE_RULESET)
    if str(payload.get("challenge_mode") or "") != contract.APS_DETERMINISTIC_CHALLENGE_MODE:
        reasons.append(contract.APS_GATE_FAILURE_CHALLENGE_MODE)


def validate_deterministic_challenge_artifact_gate(*, run_ids: list[str] | None = None, limit: int = 50, report_path: str | Path = DEFAULT_REPORT_PATH, require_runs: bool = True) -> dict[str, Any]:
    run_rows = _load_candidate_runs(run_ids=run_ids, limit=limit)
    checks: list[dict[str, Any]] = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        scope = _artifact_scope_for_run_id(run_id)
        matched_artifacts: list[tuple[Path, dict[str, Any]]] = []
        for artifact_path in sorted(
            Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_deterministic_challenge_artifact_v1.json")
        ):
            artifact_payload = _read_json(artifact_path)
            if not _payload_matches_requested_run(
                artifact_payload,
                run_id,
                _owner_run_id_from_artifact_payload(artifact_payload),
            ):
                continue
            matched_artifacts.append((artifact_path, artifact_payload))
        matched_failures: list[tuple[Path, dict[str, Any]]] = []
        for failure_path in sorted(
            Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_deterministic_challenge_artifact_failure_v1.json")
        ):
            failure_payload = _read_json(failure_path)
            if not _payload_matches_requested_run(
                failure_payload,
                run_id,
                _owner_run_id_from_failure_payload(failure_payload),
            ):
                continue
            matched_failures.append((failure_path, failure_payload))
        reasons: list[str] = []
        if not matched_artifacts and not matched_failures:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path, failure_payload in matched_failures:
            if not failure_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for artifact_path, artifact_payload in matched_artifacts:
            if not artifact_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            if not artifact_payload:
                reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_SCHEMA)
                continue
            _validate_artifact_payload(artifact_payload, reasons)
            source_summary = dict(artifact_payload.get("source_deterministic_insight_artifact") or {})
            source_ref = str(source_summary.get("deterministic_insight_artifact_ref") or "").strip()
            if not source_ref:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_INSIGHT_REF)
                continue
            source_path = Path(source_ref)
            if not source_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_INSIGHT_REF)
                continue
            try:
                source_payload, _source_payload_path = nrc_aps_deterministic_insight_artifact.load_persisted_deterministic_insight_artifact(
                    deterministic_insight_artifact_ref=source_path
                )
            except nrc_aps_deterministic_insight_artifact.DeterministicInsightArtifactError:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_INSIGHT_REF)
                continue

            expected_payload = contract.build_deterministic_challenge_artifact_payload(
                source_payload,
                generated_at_utc=str(artifact_payload.get("generated_at_utc") or ""),
            )
            if source_summary != dict(expected_payload.get("source_deterministic_insight_artifact") or {}):
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_INSIGHT_SUMMARY)
            if int(artifact_payload.get("total_challenges") or 0) != int(expected_payload.get("total_challenges") or 0):
                reasons.append(contract.APS_GATE_FAILURE_TOTAL_CHALLENGES)
            actual_challenge_counts = {severity: int(dict(artifact_payload.get("challenge_counts") or {}).get(severity, 0) or 0) for severity in contract.APS_CHALLENGE_SEVERITIES}
            expected_challenge_counts = {severity: int(dict(expected_payload.get("challenge_counts") or {}).get(severity, 0) or 0) for severity in contract.APS_CHALLENGE_SEVERITIES}
            if actual_challenge_counts != expected_challenge_counts:
                reasons.append(contract.APS_GATE_FAILURE_CHALLENGE_COUNTS)
            actual_disposition_counts = {disposition: int(dict(artifact_payload.get("disposition_counts") or {}).get(disposition, 0) or 0) for disposition in contract.APS_CHALLENGE_DISPOSITIONS}
            expected_disposition_counts = {disposition: int(dict(expected_payload.get("disposition_counts") or {}).get(disposition, 0) or 0) for disposition in contract.APS_CHALLENGE_DISPOSITIONS}
            if actual_disposition_counts != expected_disposition_counts:
                reasons.append(contract.APS_GATE_FAILURE_DISPOSITION_COUNTS)
            if [dict(item or {}) for item in list(artifact_payload.get("challenges") or []) if isinstance(item, dict)] != [dict(item or {}) for item in list(expected_payload.get("challenges") or []) if isinstance(item, dict)]:
                reasons.append(contract.APS_GATE_FAILURE_CHALLENGES)
            actual_checksum = str(artifact_payload.get("deterministic_challenge_artifact_checksum") or "").strip()
            expected_checksum = contract.compute_deterministic_challenge_artifact_checksum(artifact_payload)
            if not actual_checksum or actual_checksum != expected_checksum:
                reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)
            if contract.logical_deterministic_challenge_artifact_payload(artifact_payload) != contract.logical_deterministic_challenge_artifact_payload(expected_payload):
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "deterministic_challenge_artifact_refs": [str(path) for path, _payload in matched_artifacts],
                "failure_refs": [str(path) for path, _payload in matched_failures],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_GATE_SCHEMA_ID,
        "schema_version": contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": passed,
        "checked_runs": len(checks),
        "failed_runs": len([item for item in checks if not bool(item.get("passed"))]),
        "checks": checks,
        "reports_dir": str(Path(settings.connector_reports_dir)),
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
    parser = argparse.ArgumentParser(description="Validate NRC APS deterministic challenge artifacts (fail-closed).")
    parser.add_argument("--run-id", action="append", default=[], help="Optional specific run id(s) to validate.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of latest NRC APS runs to evaluate when --run-id is not supplied.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow no matching runs (default fail-closed when no runs are found).")
    args = parser.parse_args(argv)
    report = validate_deterministic_challenge_artifact_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
