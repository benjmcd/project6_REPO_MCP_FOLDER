from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_evidence_report
from app.services import nrc_aps_evidence_report_export
from app.services import nrc_aps_evidence_report_export_contract as contract
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_evidence_report_export_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _run_id_from_export_payload(payload: dict[str, Any]) -> str | None:
    source_report = dict(payload.get("source_evidence_report") or {})
    source_citation_pack = dict(source_report.get("source_citation_pack") or {})
    source_bundle = dict(source_citation_pack.get("source_bundle") or {})
    run_id = str(source_bundle.get("run_id") or "").strip()
    return run_id or None


def _run_id_from_failure_payload(payload: dict[str, Any]) -> str | None:
    run_id = str(payload.get("run_id") or "").strip()
    return run_id or None


def _fallback_run_id_from_artifact_name(name: str) -> str | None:
    token = "_aps_evidence_report_export_v1.json"
    failure_token = "_aps_evidence_report_export_failure_v1.json"
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


def _payload_matches_requested_run(payload: dict[str, Any], run_id: str, run_id_from_payload: str | None) -> bool:
    if not payload:
        return True
    return run_id_from_payload is None or run_id_from_payload == run_id


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]

    if normalized_run_ids:
        return [{"run_id": run_id} for run_id in normalized_run_ids]

    candidates: dict[str, float] = {}
    for path in reports_dir.glob("*_aps_evidence_report_export_v1.json"):
        payload = _read_json(path)
        run_id = _run_id_from_export_payload(payload) or _fallback_run_id_from_artifact_name(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_evidence_report_export_failure_v1.json"):
        payload = _read_json(path)
        run_id = _run_id_from_failure_payload(payload) or _fallback_run_id_from_artifact_name(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_FAILURE_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if str(payload.get("render_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_RENDER_CONTRACT)
    if str(payload.get("template_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_TEMPLATE_CONTRACT)
    checksum = str(payload.get("evidence_report_export_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_export_checksum(payload)
    if not checksum or checksum != expected_checksum:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def _validate_export_payload(export_payload: dict[str, Any], reasons: list[str]) -> None:
    if str(export_payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_EXPORT_SCHEMA)
    if int(export_payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_EXPORT_SCHEMA)
    if str(export_payload.get("render_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_RENDER_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_RENDER_CONTRACT)
    if str(export_payload.get("template_contract_id") or "") != contract.APS_EVIDENCE_REPORT_EXPORT_MARKDOWN_TEMPLATE_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_TEMPLATE_CONTRACT)
    checksum = str(export_payload.get("evidence_report_export_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_export_checksum(export_payload)
    if not checksum or checksum != expected_checksum:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)
    rendered_markdown_sha256 = str(export_payload.get("rendered_markdown_sha256") or "").strip()
    expected_rendered_markdown_sha256 = contract.compute_rendered_markdown_sha256(str(export_payload.get("rendered_markdown") or ""))
    if not rendered_markdown_sha256 or rendered_markdown_sha256 != expected_rendered_markdown_sha256:
        reasons.append(contract.APS_GATE_FAILURE_RENDERED_MARKDOWN_HASH)


def _validate_source_evidence_report_echo(
    export_payload: dict[str, Any],
    source_report_payload: dict[str, Any],
    reasons: list[str],
) -> None:
    echoed = dict(export_payload.get("source_evidence_report") or {})
    expected = contract.source_evidence_report_summary_payload(source_report_payload)
    if echoed != expected:
        reasons.append(contract.APS_GATE_FAILURE_SOURCE_REPORT_MISMATCH)


def validate_evidence_report_export_gate(
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
        scope = nrc_aps_evidence_report_export.evidence_report_export_scope(run_id)
        matched_exports: list[tuple[Path, dict[str, Any]]] = []
        for export_path in sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_report_export_v1.json")):
            export_payload = _read_json(export_path)
            if not _payload_matches_requested_run(
                export_payload,
                run_id,
                _run_id_from_export_payload(export_payload),
            ):
                continue
            matched_exports.append((export_path, export_payload))
        matched_failures: list[tuple[Path, dict[str, Any]]] = []
        for failure_path in sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_report_export_failure_v1.json")):
            failure_payload = _read_json(failure_path)
            if not _payload_matches_requested_run(
                failure_payload,
                run_id,
                _run_id_from_failure_payload(failure_payload),
            ):
                continue
            matched_failures.append((failure_path, failure_payload))
        reasons: list[str] = []
        if not matched_exports and not matched_failures:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path, failure_payload in matched_failures:
            if not failure_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for export_path, export_payload in matched_exports:
            if not export_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            if not export_payload:
                reasons.append(contract.APS_GATE_FAILURE_EXPORT_SCHEMA)
                continue
            _validate_export_payload(export_payload, reasons)
            source_report_ref = str(dict(export_payload.get("source_evidence_report") or {}).get("evidence_report_ref") or "").strip()
            if not source_report_ref:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_REPORT_REF)
                continue
            source_report_path = Path(source_report_ref)
            if not source_report_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_REPORT_REF)
                continue
            try:
                source_report_payload, _source_path = nrc_aps_evidence_report.load_persisted_evidence_report_artifact(
                    evidence_report_ref=source_report_path
                )
            except nrc_aps_evidence_report.EvidenceReportError:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_REPORT_REF)
                continue
            _validate_source_evidence_report_echo(export_payload, source_report_payload, reasons)
            expected_export_payload = contract.build_evidence_report_export_payload(
                source_report_payload,
                generated_at_utc=str(export_payload.get("generated_at_utc") or ""),
            )
            expected_export_id = contract.derive_evidence_report_export_id(
                evidence_report_id=str(source_report_payload.get("evidence_report_id") or ""),
                evidence_report_checksum=str(source_report_payload.get("evidence_report_checksum") or ""),
            )
            if str(export_payload.get("evidence_report_export_id") or "").strip() != expected_export_id:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_REPORT_MISMATCH)
            actual_body = contract.normalize_rendered_markdown_body(str(export_payload.get("rendered_markdown") or ""))
            expected_body = contract.normalize_rendered_markdown_body(str(expected_export_payload.get("rendered_markdown") or ""))
            if actual_body != expected_body:
                reasons.append(contract.APS_GATE_FAILURE_RENDERED_MARKDOWN_DRIFT)
            if contract.compute_rendered_markdown_sha256(actual_body) != str(export_payload.get("rendered_markdown_sha256") or "").strip():
                reasons.append(contract.APS_GATE_FAILURE_RENDERED_MARKDOWN_HASH)
            if contract.logical_evidence_report_export_payload(export_payload) != contract.logical_evidence_report_export_payload(
                expected_export_payload
            ):
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "evidence_report_export_refs": [str(path) for path, _payload in matched_exports],
                "failure_refs": [str(path) for path, _payload in matched_failures],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_EVIDENCE_REPORT_EXPORT_GATE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_EXPORT_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS evidence report export artifacts (fail-closed).")
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
    report = validate_evidence_report_export_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
