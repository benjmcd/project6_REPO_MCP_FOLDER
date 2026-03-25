from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_context_packet
from app.services import nrc_aps_context_packet_contract as contract
from app.services import nrc_aps_evidence_report
from app.services import nrc_aps_evidence_report_export
from app.services import nrc_aps_evidence_report_export_package
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_context_packet_validation_report.json")


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
        token = "_aps_context_packet_v1.json"
        failure_token = "_aps_context_packet_failure_v1.json"
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
    for path in reports_dir.glob("*_aps_context_packet_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_context_packet_failure_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        nrc_aps_context_packet._validate_failure_payload_schema(payload)
    except nrc_aps_context_packet.ContextPacketError:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)


def _validate_context_payload(context_payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        nrc_aps_context_packet._validate_persisted_context_packet_payload(context_payload)
    except nrc_aps_context_packet.ContextPacketError:
        reasons.append(contract.APS_GATE_FAILURE_CONTEXT_SCHEMA)
    if str(context_payload.get("projection_contract_id") or "") != contract.APS_CONTEXT_PACKET_PROJECTION_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_PROJECTION_CONTRACT)
    if str(context_payload.get("fact_grammar_contract_id") or "") != contract.APS_CONTEXT_PACKET_FACT_GRAMMAR_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_FACT_GRAMMAR_CONTRACT)


def _load_source_payload_for_context(
    source_family: str,
    source_ref: str | Path,
) -> dict[str, Any] | None:
    source_path = Path(source_ref)
    if not source_path.exists():
        return None
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_REPORT:
        try:
            payload, _source_path = nrc_aps_evidence_report.load_persisted_evidence_report_artifact(
                evidence_report_ref=source_path
            )
            return payload
        except nrc_aps_evidence_report.EvidenceReportError:
            return None
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_EXPORT:
        try:
            payload, _source_path = nrc_aps_evidence_report_export.load_persisted_evidence_report_export_artifact(
                evidence_report_export_ref=source_path
            )
            return payload
        except nrc_aps_evidence_report_export.EvidenceReportExportError:
            return None
    if source_family == contract.APS_CONTEXT_PACKET_SOURCE_FAMILY_PACKAGE:
        try:
            payload, _source_path = nrc_aps_evidence_report_export_package.load_persisted_evidence_report_export_package_artifact(
                evidence_report_export_package_ref=source_path
            )
            return payload
        except nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError:
            return None
    return None


def validate_context_packet_gate(
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
        context_packet_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_context_packet_v1.json"))
        failure_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_context_packet_failure_v1.json"))
        reasons: list[str] = []
        if not context_packet_paths and not failure_paths:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path in failure_paths:
            failure_payload = _read_json(failure_path)
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for context_packet_path in context_packet_paths:
            if not context_packet_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            context_payload = _read_json(context_packet_path)
            if not context_payload:
                reasons.append(contract.APS_GATE_FAILURE_CONTEXT_SCHEMA)
                continue
            _validate_context_payload(context_payload, reasons)
            source_family = str(context_payload.get("source_family") or "")
            source_descriptor = dict(context_payload.get("source_descriptor") or {})
            source_ref = str(source_descriptor.get("source_ref") or "").strip()
            if not source_ref:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_REF)
                continue
            source_payload = _load_source_payload_for_context(source_family, source_ref)
            if source_payload is None:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_REF)
                continue
            expected_source_descriptor = contract.source_descriptor_payload(source_family, source_payload)
            if source_descriptor != expected_source_descriptor:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_DESCRIPTOR)
            expected_context_payload = contract.build_context_packet_payload(
                source_family=source_family,
                source_payload=source_payload,
                generated_at_utc=str(context_payload.get("generated_at_utc") or ""),
            )
            expected_context_packet_id = str(expected_context_payload.get("context_packet_id") or "")
            if str(context_payload.get("context_packet_id") or "").strip() != expected_context_packet_id:
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)
            actual_checksum = str(context_payload.get("context_packet_checksum") or "").strip()
            expected_checksum = contract.compute_context_packet_checksum(context_payload)
            if not actual_checksum or actual_checksum != expected_checksum:
                reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)
            if list(context_payload.get("facts") or []) != list(expected_context_payload.get("facts") or []):
                reasons.append(contract.APS_GATE_FAILURE_FACT_DRIFT)
            if list(context_payload.get("caveats") or []) != list(expected_context_payload.get("caveats") or []):
                reasons.append(contract.APS_GATE_FAILURE_CAVEAT_DRIFT)
            if list(context_payload.get("constraints") or []) != list(expected_context_payload.get("constraints") or []):
                reasons.append(contract.APS_GATE_FAILURE_CONSTRAINT_DRIFT)
            if list(context_payload.get("unresolved_questions") or []) != list(expected_context_payload.get("unresolved_questions") or []):
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVED_QUESTION_DRIFT)
            if contract.logical_context_packet_payload(context_payload) != contract.logical_context_packet_payload(
                expected_context_payload
            ):
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "context_packet_refs": [str(path) for path in context_packet_paths],
                "failure_refs": [str(path) for path in failure_paths],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_CONTEXT_PACKET_GATE_SCHEMA_ID,
        "schema_version": contract.APS_CONTEXT_PACKET_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS context packet artifacts (fail-closed).")
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
    report = validate_context_packet_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
