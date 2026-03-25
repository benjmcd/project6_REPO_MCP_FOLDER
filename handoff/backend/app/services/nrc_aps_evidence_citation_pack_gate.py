from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_evidence_bundle
from app.services import nrc_aps_evidence_bundle_contract as bundle_contract
from app.services import nrc_aps_evidence_citation_pack_contract as contract
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_evidence_citation_pack_validation_report.json")


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
        token = "_aps_evidence_citation_pack_v1.json"
        failure_token = "_aps_evidence_citation_pack_failure_v1.json"
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
    for path in reports_dir.glob("*_aps_evidence_citation_pack_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_evidence_citation_pack_failure_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_CITATION_PACK_FAILURE_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if str(payload.get("derivation_contract_id") or "") != contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_CONTRACT)
    checksum = str(payload.get("citation_pack_checksum") or "").strip()
    expected_checksum = contract.compute_citation_pack_checksum(payload)
    if not checksum or checksum != expected_checksum:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def _validate_source_bundle_rows(source_bundle_payload: dict[str, Any], reasons: list[str]) -> None:
    rows = [dict(item or {}) for item in (source_bundle_payload.get("results") or []) if isinstance(item, dict)]
    mode = str(source_bundle_payload.get("mode") or bundle_contract.APS_MODE_BROWSE)
    if not bundle_contract.is_ordering_deterministic(rows, mode=mode):
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)
    for row in rows:
        if not bundle_contract.validate_known_contract_ids(row):
            reasons.append(contract.APS_GATE_FAILURE_UNKNOWN_CONTRACT)
        if bundle_contract.missing_provenance_fields(row):
            reasons.append(contract.APS_GATE_FAILURE_MISSING_PROVENANCE)
        if bundle_contract.unresolvable_provenance_fields(row):
            reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_PROVENANCE)
        if not bundle_contract.validate_snippet_bounds(row):
            reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)


def _validate_source_bundle_echo(pack_payload: dict[str, Any], source_bundle_payload: dict[str, Any], reasons: list[str]) -> None:
    echoed = dict(pack_payload.get("source_bundle") or {})
    expected = contract.source_bundle_summary_payload(source_bundle_payload)
    if echoed != expected:
        reasons.append(contract.APS_GATE_FAILURE_SOURCE_BUNDLE_MISMATCH)


def _validate_pack_payload(pack_payload: dict[str, Any], reasons: list[str]) -> None:
    if str(pack_payload.get("schema_id") or "") != contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_PACK_SCHEMA)
    if int(pack_payload.get("schema_version") or 0) != contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_PACK_SCHEMA)
    if str(pack_payload.get("derivation_contract_id") or "") != contract.APS_EVIDENCE_CITATION_DERIVATION_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_CONTRACT)
    checksum = str(pack_payload.get("citation_pack_checksum") or "").strip()
    expected_checksum = contract.compute_citation_pack_checksum(pack_payload)
    if not checksum or checksum != expected_checksum:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def validate_evidence_citation_pack_gate(
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
        pack_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_citation_pack_v1.json"))
        failure_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_citation_pack_failure_v1.json"))
        reasons: list[str] = []
        if not pack_paths and not failure_paths:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path in failure_paths:
            failure_payload = _read_json(failure_path)
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for pack_path in pack_paths:
            if not pack_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            pack_payload = _read_json(pack_path)
            if not pack_payload:
                reasons.append(contract.APS_GATE_FAILURE_PACK_SCHEMA)
                continue
            _validate_pack_payload(pack_payload, reasons)
            source_bundle_ref = str(dict(pack_payload.get("source_bundle") or {}).get("bundle_ref") or "").strip()
            if not source_bundle_ref:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_BUNDLE_REF)
                continue
            source_bundle_path = Path(source_bundle_ref)
            if not source_bundle_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_BUNDLE_REF)
                continue
            try:
                source_bundle_payload, _source_path = nrc_aps_evidence_bundle.load_persisted_bundle_artifact(bundle_ref=source_bundle_path)
            except nrc_aps_evidence_bundle.EvidenceBundleError:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_BUNDLE_REF)
                continue
            _validate_source_bundle_rows(source_bundle_payload, reasons)
            _validate_source_bundle_echo(pack_payload, source_bundle_payload, reasons)
            expected_pack_id = contract.derive_citation_pack_id(
                source_bundle_id=str(source_bundle_payload.get("bundle_id") or ""),
                source_bundle_checksum=str(source_bundle_payload.get("bundle_checksum") or ""),
            )
            if str(pack_payload.get("citation_pack_id") or "").strip() != expected_pack_id:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_BUNDLE_MISMATCH)
            expected_citations = contract.build_citations_from_bundle(source_bundle_payload)
            actual_citations = [dict(item or {}) for item in (pack_payload.get("citations") or []) if isinstance(item, dict)]
            if actual_citations != expected_citations:
                reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "citation_pack_refs": [str(path) for path in pack_paths],
                "failure_refs": [str(path) for path in failure_paths],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_EVIDENCE_CITATION_PACK_GATE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_CITATION_PACK_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS evidence citation pack artifacts (fail-closed).")
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
    report = validate_evidence_citation_pack_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
