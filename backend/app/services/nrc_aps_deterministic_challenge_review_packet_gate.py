from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_deterministic_challenge_review_packet as review_packet
from app.services import nrc_aps_deterministic_challenge_review_packet_contract as contract
from app.services import nrc_aps_deterministic_challenge_artifact
from app.services import nrc_aps_deterministic_challenge_artifact_contract as challenge_contract
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_deterministic_challenge_review_packet_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]

    def _extract_run_id(name: str) -> str | None:
        token = "_aps_deterministic_challenge_review_packet_v1.json"
        failure_token = "_aps_deterministic_challenge_review_packet_failure_v1.json"
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

    if normalized_run_ids:
        return [{"run_id": run_id} for run_id in normalized_run_ids]

    candidates: dict[str, float] = {}
    for path in reports_dir.glob("*_aps_deterministic_challenge_review_packet_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_deterministic_challenge_review_packet_failure_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        review_packet._validate_failure_payload_schema(payload)
    except review_packet.DeterministicChallengeReviewPacketError:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)


def _validate_artifact_payload(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        review_packet._validate_persisted_deterministic_challenge_review_packet_payload(payload)
    except review_packet.DeterministicChallengeReviewPacketError:
        reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_SCHEMA)
    for field_name, expected_value in contract.projection_identity_payload().items():
        if payload.get(field_name) != expected_value:
            reasons.append(contract.APS_GATE_FAILURE_PROJECTION_CONTRACT if field_name == "projection_contract_id" else contract.APS_GATE_FAILURE_PROJECTION_MODE)


def validate_deterministic_challenge_review_packet_gate(*, run_ids: list[str] | None = None, limit: int = 50, report_path: str | Path = DEFAULT_REPORT_PATH, require_runs: bool = True) -> dict[str, Any]:
    run_rows = _load_candidate_runs(run_ids=run_ids, limit=limit)
    checks: list[dict[str, Any]] = []
    for row in run_rows:
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        scope = f"run_{run_id}"
        artifact_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_deterministic_challenge_review_packet_v1.json"))
        failure_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_deterministic_challenge_review_packet_failure_v1.json"))
        reasons: list[str] = []
        if not artifact_paths and not failure_paths:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path in failure_paths:
            failure_payload = _read_json(failure_path)
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for artifact_path in artifact_paths:
            if not artifact_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            artifact_payload = _read_json(artifact_path)
            if not artifact_payload:
                reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_SCHEMA)
                continue
            _validate_artifact_payload(artifact_payload, reasons)
            source_summary = dict(artifact_payload.get("source_deterministic_challenge_artifact") or {})
            source_ref = str(source_summary.get("deterministic_challenge_artifact_ref") or "").strip()
            if not source_ref:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CHALLENGE_REF)
                continue
            source_path = Path(source_ref)
            if not source_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CHALLENGE_REF)
                continue
            try:
                source_payload, _source_payload_path = nrc_aps_deterministic_challenge_artifact.load_persisted_deterministic_challenge_artifact(
                    deterministic_challenge_artifact_ref=source_path
                )
            except nrc_aps_deterministic_challenge_artifact.DeterministicChallengeArtifactError:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CHALLENGE_REF)
                continue

            expected_payload = contract.build_deterministic_challenge_review_packet_payload(
                source_payload,
                generated_at_utc=str(artifact_payload.get("generated_at_utc") or ""),
            )
            if source_summary != dict(expected_payload.get("source_deterministic_challenge_artifact") or {}):
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CHALLENGE_SUMMARY)
            if int(artifact_payload.get("total_challenges") or 0) != int(expected_payload.get("total_challenges") or 0):
                reasons.append(contract.APS_GATE_FAILURE_TOTAL_CHALLENGES)
            actual_bucket_counts = {
                "blocker_count": int(artifact_payload.get("blocker_count") or 0),
                "review_item_count": int(artifact_payload.get("review_item_count") or 0),
                "acknowledgement_count": int(artifact_payload.get("acknowledgement_count") or 0),
            }
            expected_bucket_counts = {
                "blocker_count": int(expected_payload.get("blocker_count") or 0),
                "review_item_count": int(expected_payload.get("review_item_count") or 0),
                "acknowledgement_count": int(expected_payload.get("acknowledgement_count") or 0),
            }
            if actual_bucket_counts != expected_bucket_counts:
                reasons.append(contract.APS_GATE_FAILURE_BUCKET_COUNTS)
            if [dict(item or {}) for item in list(artifact_payload.get("blockers") or []) if isinstance(item, dict)] != [dict(item or {}) for item in list(expected_payload.get("blockers") or []) if isinstance(item, dict)]:
                reasons.append(contract.APS_GATE_FAILURE_BLOCKERS)
            if [dict(item or {}) for item in list(artifact_payload.get("review_items") or []) if isinstance(item, dict)] != [dict(item or {}) for item in list(expected_payload.get("review_items") or []) if isinstance(item, dict)]:
                reasons.append(contract.APS_GATE_FAILURE_REVIEW_ITEMS)
            if [dict(item or {}) for item in list(artifact_payload.get("acknowledgements") or []) if isinstance(item, dict)] != [dict(item or {}) for item in list(expected_payload.get("acknowledgements") or []) if isinstance(item, dict)]:
                reasons.append(contract.APS_GATE_FAILURE_ACKNOWLEDGEMENTS)
            actual_checksum = str(artifact_payload.get("deterministic_challenge_review_packet_checksum") or "").strip()
            expected_checksum = contract.compute_deterministic_challenge_review_packet_checksum(artifact_payload)
            if not actual_checksum or actual_checksum != expected_checksum:
                reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)
            if contract.logical_deterministic_challenge_review_packet_payload(artifact_payload) != contract.logical_deterministic_challenge_review_packet_payload(expected_payload):
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "deterministic_challenge_review_packet_refs": [str(path) for path in artifact_paths],
                "failure_refs": [str(path) for path in failure_paths],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_GATE_SCHEMA_ID,
        "schema_version": contract.APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS deterministic challenge review packets (fail-closed).")
    parser.add_argument("--run-id", action="append", default=[], help="Optional specific run id(s) to validate.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of latest NRC APS runs to evaluate when --run-id is not supplied.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow no matching runs (default fail-closed when no runs are found).")
    args = parser.parse_args(argv)
    report = validate_deterministic_challenge_review_packet_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
