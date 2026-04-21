from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_evidence_report_export
from app.services import nrc_aps_evidence_report_export_package
from app.services import nrc_aps_evidence_report_export_package_contract as contract
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_evidence_report_export_package_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _owner_run_id_from_package_payload(payload: dict[str, Any]) -> str | None:
    owner_run_id = str(payload.get("owner_run_id") or "").strip()
    return owner_run_id or None


def _owner_run_id_from_failure_payload(payload: dict[str, Any]) -> str | None:
    owner_run_id = str(payload.get("owner_run_id") or "").strip()
    return owner_run_id or None


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

    candidates: dict[str, float] = {}
    for path in reports_dir.glob("*_aps_evidence_report_export_package_v1.json"):
        run_id = _owner_run_id_from_package_payload(_read_json(path))
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_evidence_report_export_package_failure_v1.json"):
        run_id = _owner_run_id_from_failure_payload(_read_json(path))
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        nrc_aps_evidence_report_export_package._validate_failure_payload_schema(payload)
    except nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)


def _validate_package_payload(package_payload: dict[str, Any], reasons: list[str]) -> None:
    try:
        nrc_aps_evidence_report_export_package._validate_persisted_evidence_report_export_package_payload(package_payload)
    except nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError as exc:
        code = str(exc.code or "")
        if "schema" in code or "invalid" in code:
            reasons.append(contract.APS_GATE_FAILURE_PACKAGE_SCHEMA)
        else:
            reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)
    if str(package_payload.get("composition_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_COMPOSITION_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_COMPOSITION_CONTRACT)
    if str(package_payload.get("package_mode") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_MODE:
        reasons.append(contract.APS_GATE_FAILURE_PACKAGE_MODE)


def validate_evidence_report_export_package_gate(
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
        scope = nrc_aps_evidence_report_export_package.evidence_report_export_package_scope(run_id)
        matched_packages: list[tuple[Path, dict[str, Any]]] = []
        for package_path in sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_report_export_package_v1.json")):
            package_payload = _read_json(package_path)
            if not _payload_matches_requested_run(
                package_payload,
                run_id,
                _owner_run_id_from_package_payload(package_payload),
            ):
                continue
            matched_packages.append((package_path, package_payload))
        matched_failures: list[tuple[Path, dict[str, Any]]] = []
        for failure_path in sorted(
            Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_report_export_package_failure_v1.json")
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
        if not matched_packages and not matched_failures:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path, failure_payload in matched_failures:
            if not failure_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for package_path, package_payload in matched_packages:
            if not package_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            if not package_payload:
                reasons.append(contract.APS_GATE_FAILURE_PACKAGE_SCHEMA)
                continue
            _validate_package_payload(package_payload, reasons)
            source_exports = [dict(item or {}) for item in list(package_payload.get("source_exports") or []) if isinstance(item, dict)]
            loaded_export_payloads: list[dict[str, Any]] = []
            for source_export in source_exports:
                source_export_ref = str(source_export.get("evidence_report_export_ref") or "").strip()
                if not source_export_ref:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_EXPORT_REF)
                    continue
                source_export_path = Path(source_export_ref)
                if not source_export_path.exists():
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_EXPORT_REF)
                    continue
                try:
                    export_payload, _export_path = nrc_aps_evidence_report_export.load_persisted_evidence_report_export_artifact(
                        evidence_report_export_ref=source_export_path
                    )
                except nrc_aps_evidence_report_export.EvidenceReportExportError:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_EXPORT_REF)
                    continue
                loaded_export_payloads.append(export_payload)
                expected_descriptor = contract.export_descriptor_payload(
                    export_payload,
                    export_ordinal=int(source_export.get("export_ordinal") or 0),
                )
                if source_export != expected_descriptor:
                    reasons.append(contract.APS_GATE_FAILURE_SOURCE_EXPORT_MISMATCH)
            if len(loaded_export_payloads) != len(source_exports):
                continue

            expected_owner_run_id = contract.owner_run_id_for_export_payload(loaded_export_payloads[0]) or ""
            expected_package_payload = contract.build_evidence_report_export_package_payload(
                loaded_export_payloads,
                generated_at_utc=str(package_payload.get("generated_at_utc") or ""),
                owner_run_id=expected_owner_run_id,
            )
            expected_package_id = str(expected_package_payload.get("evidence_report_export_package_id") or "")
            if str(package_payload.get("evidence_report_export_package_id") or "").strip() != expected_package_id:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_EXPORT_MISMATCH)
            actual_ordered_digest = str(package_payload.get("ordered_source_exports_sha256") or "").strip()
            expected_ordered_digest = str(expected_package_payload.get("ordered_source_exports_sha256") or "").strip()
            if actual_ordered_digest != expected_ordered_digest:
                reasons.append(contract.APS_GATE_FAILURE_ORDERED_DIGEST)
            actual_checksum = str(package_payload.get("evidence_report_export_package_checksum") or "").strip()
            expected_checksum = contract.compute_evidence_report_export_package_checksum(package_payload)
            if not actual_checksum or actual_checksum != expected_checksum:
                reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)
            if contract.logical_evidence_report_export_package_payload(package_payload) != contract.logical_evidence_report_export_package_payload(
                expected_package_payload
            ):
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "evidence_report_export_package_refs": [str(path) for path, _payload in matched_packages],
                "failure_refs": [str(path) for path, _payload in matched_failures],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_GATE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_EXPORT_PACKAGE_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS evidence report export package artifacts (fail-closed).")
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
    report = validate_evidence_report_export_package_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
