from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_context_dossier
from app.services import nrc_aps_context_dossier_contract as contract
from app.services import nrc_aps_context_packet
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_context_dossier_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]

    def _extract_run_id(name: str) -> str | None:
        token = "_aps_context_dossier_v1.json"
        failure_token = "_aps_context_dossier_failure_v1.json"
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
    for path in reports_dir.glob("*_aps_context_dossier_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_context_dossier_failure_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        nrc_aps_context_dossier._validate_failure_payload_schema(payload)
    except nrc_aps_context_dossier.ContextDossierError:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)


def _validate_dossier_payload(dossier_payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        nrc_aps_context_dossier._validate_persisted_context_dossier_payload(dossier_payload)
    except nrc_aps_context_dossier.ContextDossierError:
        reasons.append(contract.APS_GATE_FAILURE_DOSSIER_SCHEMA)
    if str(dossier_payload.get("composition_contract_id") or "") != contract.APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_COMPOSITION_CONTRACT)
    if str(dossier_payload.get("dossier_mode") or "") != contract.APS_CONTEXT_DOSSIER_MODE:
        reasons.append(contract.APS_GATE_FAILURE_DOSSIER_MODE)


def validate_context_dossier_gate(
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
        scope = f"run_{run_id}"
        dossier_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_context_dossier_v1.json"))
        failure_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_context_dossier_failure_v1.json"))
        reasons: list[str] = []
        if not dossier_paths and not failure_paths:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path in failure_paths:
            failure_payload = _read_json(failure_path)
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for dossier_path in dossier_paths:
            if not dossier_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            dossier_payload = _read_json(dossier_path)
            if not dossier_payload:
                reasons.append(contract.APS_GATE_FAILURE_DOSSIER_SCHEMA)
                continue
            _validate_dossier_payload(dossier_payload, reasons)
            source_packets = [dict(item or {}) for item in list(dossier_payload.get("source_packets") or []) if isinstance(item, dict)]
            loaded_context_packet_payloads: list[dict[str, Any]] = []
            for source_packet in source_packets:
                context_packet_ref = str(source_packet.get("context_packet_ref") or "").strip()
                if not context_packet_ref:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_PACKET_REF)
                    continue
                source_path = Path(context_packet_ref)
                if not source_path.exists():
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_PACKET_REF)
                    continue
                try:
                    context_packet_payload, _context_packet_path = nrc_aps_context_packet.load_persisted_context_packet_artifact(
                        context_packet_ref=source_path
                    )
                except nrc_aps_context_packet.ContextPacketError:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_PACKET_REF)
                    continue
                loaded_context_packet_payloads.append(context_packet_payload)
                expected_descriptor = contract.source_packet_descriptor_payload(
                    context_packet_payload,
                    packet_ordinal=int(source_packet.get("packet_ordinal") or 0),
                )
                if source_packet != expected_descriptor:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_PACKET_MISMATCH)
            if len(loaded_context_packet_payloads) != len(source_packets):
                continue

            try:
                expected_dossier_payload = contract.build_context_dossier_payload(
                    loaded_context_packet_payloads,
                    generated_at_utc=str(dossier_payload.get("generated_at_utc") or ""),
                )
            except ValueError:
                reasons.append(contract.APS_GATE_FAILURE_COMPATIBILITY)
                continue

            expected_dossier_id = str(expected_dossier_payload.get("context_dossier_id") or "")
            if str(dossier_payload.get("context_dossier_id") or "").strip() != expected_dossier_id:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_PACKET_MISMATCH)
            actual_ordered_digest = str(dossier_payload.get("ordered_source_packets_sha256") or "").strip()
            expected_ordered_digest = str(expected_dossier_payload.get("ordered_source_packets_sha256") or "").strip()
            if actual_ordered_digest != expected_ordered_digest:
                reasons.append(contract.APS_GATE_FAILURE_ORDERED_DIGEST)
            if int(dossier_payload.get("total_facts") or 0) != int(expected_dossier_payload.get("total_facts") or 0):
                reasons.append(contract.APS_GATE_FAILURE_COUNTERS)
            if int(dossier_payload.get("total_caveats") or 0) != int(expected_dossier_payload.get("total_caveats") or 0):
                reasons.append(contract.APS_GATE_FAILURE_COUNTERS)
            if int(dossier_payload.get("total_constraints") or 0) != int(expected_dossier_payload.get("total_constraints") or 0):
                reasons.append(contract.APS_GATE_FAILURE_COUNTERS)
            if int(dossier_payload.get("total_unresolved_questions") or 0) != int(
                expected_dossier_payload.get("total_unresolved_questions") or 0
            ):
                reasons.append(contract.APS_GATE_FAILURE_COUNTERS)
            actual_checksum = str(dossier_payload.get("context_dossier_checksum") or "").strip()
            expected_checksum = contract.compute_context_dossier_checksum(dossier_payload)
            if not actual_checksum or actual_checksum != expected_checksum:
                reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)
            if contract.logical_context_dossier_payload(dossier_payload) != contract.logical_context_dossier_payload(
                expected_dossier_payload
            ):
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "context_dossier_refs": [str(path) for path in dossier_paths],
                "failure_refs": [str(path) for path in failure_paths],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_CONTEXT_DOSSIER_GATE_SCHEMA_ID,
        "schema_version": contract.APS_CONTEXT_DOSSIER_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS context dossier artifacts (fail-closed).")
    parser.add_argument("--run-id", action="append", default=[], help="Optional specific run id(s) to validate.")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of latest NRC APS runs to evaluate when --run-id is not supplied.",
    )
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow no matching runs (default fail-closed when no runs are found).",
    )
    args = parser.parse_args(argv)
    report = validate_context_dossier_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
