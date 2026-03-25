from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_evidence_citation_pack
from app.services import nrc_aps_evidence_report_contract as contract
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_evidence_report_validation_report.json")


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
        token = "_aps_evidence_report_v1.json"
        failure_token = "_aps_evidence_report_failure_v1.json"
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
    for path in reports_dir.glob("*_aps_evidence_report_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))
    for path in reports_dir.glob("*_aps_evidence_report_failure_v1.json"):
        run_id = _extract_run_id(path.name)
        if run_id:
            candidates[run_id] = max(float(path.stat().st_mtime), float(candidates.get(run_id, 0.0)))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[: int(limit)]
    return [{"run_id": run_id} for run_id, _mtime in ordered]


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_FAILURE_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if str(payload.get("assembly_contract_id") or "") != contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_ASSEMBLY_CONTRACT)
    if str(payload.get("sectioning_contract_id") or "") != contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_SECTIONING_CONTRACT)
    checksum = str(payload.get("evidence_report_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_checksum(payload)
    if not checksum or checksum != expected_checksum:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def _validate_report_payload(report_payload: dict[str, Any], reasons: list[str]) -> None:
    if str(report_payload.get("schema_id") or "") != contract.APS_EVIDENCE_REPORT_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_REPORT_SCHEMA)
    if int(report_payload.get("schema_version") or 0) != contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_REPORT_SCHEMA)
    if str(report_payload.get("assembly_contract_id") or "") != contract.APS_EVIDENCE_REPORT_ASSEMBLY_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_ASSEMBLY_CONTRACT)
    if str(report_payload.get("sectioning_contract_id") or "") != contract.APS_EVIDENCE_REPORT_SECTIONING_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_SECTIONING_CONTRACT)
    checksum = str(report_payload.get("evidence_report_checksum") or "").strip()
    expected_checksum = contract.compute_evidence_report_checksum(report_payload)
    if not checksum or checksum != expected_checksum:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def _validate_source_citation_pack_echo(report_payload: dict[str, Any], source_pack_payload: dict[str, Any], reasons: list[str]) -> None:
    echoed = dict(report_payload.get("source_citation_pack") or {})
    expected = contract.source_citation_pack_summary_payload(source_pack_payload)
    if echoed != expected:
        reasons.append(contract.APS_GATE_FAILURE_SOURCE_CITATION_PACK_MISMATCH)


def _validate_sections_against_source(report_payload: dict[str, Any], source_pack_payload: dict[str, Any], reasons: list[str]) -> None:
    actual_sections = [dict(item or {}) for item in list(report_payload.get("sections") or []) if isinstance(item, dict)]
    expected_sections = contract.build_sections_from_citation_pack(source_pack_payload)
    expected_total_sections = len(expected_sections)
    expected_total_groups = int(source_pack_payload.get("total_groups") or 0)
    expected_total_citations = int(source_pack_payload.get("total_citations") or 0)

    if int(report_payload.get("total_sections") or 0) != expected_total_sections:
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)
    if int(report_payload.get("total_groups") or 0) != expected_total_groups:
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)
    if int(report_payload.get("total_citations") or 0) != expected_total_citations:
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)

    actual_order = [(int(item.get("section_ordinal") or 0), str(item.get("group_id") or "")) for item in actual_sections]
    expected_order = [(int(item.get("section_ordinal") or 0), str(item.get("group_id") or "")) for item in expected_sections]
    if actual_order != expected_order:
        reasons.append(contract.APS_GATE_FAILURE_SECTION_ORDER_DRIFT)

    actual_titles = [str(item.get("title") or "") for item in actual_sections]
    expected_titles = [str(item.get("title") or "") for item in expected_sections]
    if actual_titles != expected_titles:
        reasons.append(contract.APS_GATE_FAILURE_SECTION_TITLE_DRIFT)

    actual_citations = [list(section.get("citations") or []) for section in actual_sections]
    expected_citations = [list(section.get("citations") or []) for section in expected_sections]
    if actual_citations != expected_citations:
        reasons.append(contract.APS_GATE_FAILURE_CITATION_LINKAGE_DRIFT)

    if actual_sections != expected_sections:
        reasons.append(contract.APS_GATE_FAILURE_DERIVATION_DRIFT)


def validate_evidence_report_gate(
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
        report_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_report_v1.json"))
        failure_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_report_failure_v1.json"))
        reasons: list[str] = []
        if not report_paths and not failure_paths:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

        for failure_path in failure_paths:
            failure_payload = _read_json(failure_path)
            if not failure_payload:
                reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                continue
            _validate_failure_payload_schema(failure_payload, reasons)

        for evidence_report_path in report_paths:
            if not evidence_report_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                continue
            report_payload = _read_json(evidence_report_path)
            if not report_payload:
                reasons.append(contract.APS_GATE_FAILURE_REPORT_SCHEMA)
                continue
            _validate_report_payload(report_payload, reasons)
            source_pack_ref = str(dict(report_payload.get("source_citation_pack") or {}).get("citation_pack_ref") or "").strip()
            if not source_pack_ref:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CITATION_PACK_REF)
                continue
            source_pack_path = Path(source_pack_ref)
            if not source_pack_path.exists():
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CITATION_PACK_REF)
                continue
            try:
                source_pack_payload, _source_path = nrc_aps_evidence_citation_pack.load_persisted_citation_pack_artifact(citation_pack_ref=source_pack_path)
            except nrc_aps_evidence_citation_pack.EvidenceCitationPackError:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CITATION_PACK_REF)
                continue
            _validate_source_citation_pack_echo(report_payload, source_pack_payload, reasons)
            expected_report_id = contract.derive_evidence_report_id(
                citation_pack_id=str(source_pack_payload.get("citation_pack_id") or ""),
                citation_pack_checksum=str(source_pack_payload.get("citation_pack_checksum") or ""),
            )
            if str(report_payload.get("evidence_report_id") or "").strip() != expected_report_id:
                reasons.append(contract.APS_GATE_FAILURE_SOURCE_CITATION_PACK_MISMATCH)
            _validate_sections_against_source(report_payload, source_pack_payload, reasons)

        deduped = sorted(list(dict.fromkeys(reasons)))
        checks.append(
            {
                "run_id": run_id,
                "evidence_report_refs": [str(path) for path in report_paths],
                "failure_refs": [str(path) for path in failure_paths],
                "passed": len(deduped) == 0,
                "reasons": deduped,
            }
        )

    passed = all(bool(item.get("passed")) for item in checks) if checks else False
    report = {
        "schema_id": contract.APS_EVIDENCE_REPORT_GATE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_REPORT_SCHEMA_VERSION,
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
    parser = argparse.ArgumentParser(description="Validate NRC APS evidence report artifacts (fail-closed).")
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
    report = validate_evidence_report_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
