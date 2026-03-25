from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage
from app.services import nrc_aps_evidence_bundle_contract as contract
from app.services import nrc_aps_sync_drift

DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_evidence_bundle_validation_report.json")


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file and return a dict (or empty dict on failure)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    """Find recent run ids that have bundle or failure artifacts.
    Returns a list of dicts like {"run_id": "<id>"}.
    """
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]

    def _extract_run_id(name: str) -> str | None:
        token = "_aps_evidence_bundle_v2.json"
        failure_token = "_aps_evidence_bundle_failure_v2.json"
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
        return [{"run_id": rid} for rid in normalized_run_ids]

    candidates: dict[str, float] = {}
    for path in reports_dir.glob("*_aps_evidence_bundle_v2.json"):
        rid = _extract_run_id(path.name)
        if rid:
            candidates[rid] = max(float(path.stat().st_mtime), candidates.get(rid, 0.0))
    for path in reports_dir.glob("*_aps_evidence_bundle_failure_v2.json"):
        rid = _extract_run_id(path.name)
        if rid:
            candidates[rid] = max(float(path.stat().st_mtime), candidates.get(rid, 0.0))

    ordered = sorted(candidates.items(), key=lambda i: i[1], reverse=True)
    if limit and limit > 0:
        ordered = ordered[:limit]
    return [{"run_id": rid} for rid, _ in ordered]


def _validate_bundle_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_BUNDLE_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_BUNDLE_SCHEMA)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_BUNDLE_SCHEMA)
    if str(payload.get("request_contract_id") or "") != contract.APS_EVIDENCE_REQUEST_NORM_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_UNKNOWN_CONTRACT)
    if str(payload.get("ranking_contract_id") or "") != contract.APS_EVIDENCE_RANKING_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_UNKNOWN_CONTRACT)
    if str(payload.get("snippet_contract_id") or "") != contract.APS_EVIDENCE_SNIPPET_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_UNKNOWN_CONTRACT)
    if str(payload.get("snapshot_contract_id") or "") != contract.APS_EVIDENCE_SNAPSHOT_CONTRACT_ID:
        reasons.append(contract.APS_GATE_FAILURE_UNKNOWN_CONTRACT)


def _validate_failure_payload_schema(payload: dict[str, Any], reasons: list[str]) -> None:
    if str(payload.get("schema_id") or "") != contract.APS_EVIDENCE_BUNDLE_FAILURE_SCHEMA_ID:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
    if int(payload.get("schema_version") or 0) != contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION:
        reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)


def _validate_bundle_checksum(payload: dict[str, Any], reasons: list[str]) -> None:
    checksum = str(payload.get("bundle_checksum") or "").strip()
    without = dict(payload)
    without.pop("bundle_checksum", None)
    expected = contract.compute_bundle_checksum(without)
    if not checksum or checksum != expected:
        reasons.append(contract.APS_GATE_FAILURE_CHECKSUM)


def _validate_request_identity(payload: dict[str, Any], reasons: list[str]) -> None:
    normalized_request = dict(payload.get("normalized_request") or {})
    expected = contract.request_identity_hash(normalized_request)
    actual = str(payload.get("request_identity_hash") or "").strip()
    if not actual or actual != expected:
        reasons.append(contract.APS_GATE_FAILURE_REQUEST_IDENTITY)
        return
    snapshot = dict(payload.get("snapshot") or {})
    index_state_hash = str(snapshot.get("index_state_hash") or "").strip()
    expected_bundle_id = contract.derive_bundle_id(
        request_identity_hash_value=actual,
        index_state_hash=index_state_hash,
    )
    if str(payload.get("bundle_id") or "").strip() != expected_bundle_id:
        reasons.append(contract.APS_GATE_FAILURE_REQUEST_IDENTITY)


def _validate_provenance_and_snippets(payload: dict[str, Any], reasons: list[str]) -> None:
    mode = str(payload.get("mode") or contract.APS_MODE_BROWSE)
    rows = [dict(item or {}) for item in (payload.get("results") or []) if isinstance(item, dict)]
    if not contract.is_ordering_deterministic(rows, mode=mode):
        reasons.append(contract.APS_GATE_FAILURE_ORDERING_DRIFT)
    for row in rows:
        if not contract.validate_known_contract_ids(row):
            reasons.append(contract.APS_GATE_FAILURE_UNKNOWN_CONTRACT)
        missing = contract.missing_provenance_fields(row)
        if missing:
            reasons.append(contract.APS_GATE_FAILURE_MISSING_PROVENANCE)
        unresolved = contract.unresolvable_provenance_fields(row)
        if unresolved:
            reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_PROVENANCE)
        if not contract.validate_snippet_bounds(row):
            reasons.append(contract.APS_GATE_FAILURE_SNIPPET_BOUNDS)


def _validate_artifact_db_parity(payload: dict[str, Any], db, reasons: list[str]) -> None:
    rows = [dict(item or {}) for item in (payload.get("results") or []) if isinstance(item, dict)]
    for row in rows:
        linkage = (
            db.query(ApsContentLinkage)
            .filter(
                and_(
                    ApsContentLinkage.content_id == str(row.get("content_id") or ""),
                    ApsContentLinkage.run_id == str(row.get("run_id") or ""),
                    ApsContentLinkage.target_id == str(row.get("target_id") or ""),
                    ApsContentLinkage.content_contract_id == str(row.get("content_contract_id") or ""),
                    ApsContentLinkage.chunking_contract_id == str(row.get("chunking_contract_id") or ""),
                )
            )
            .first()
        )
        if not linkage:
            reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE)
            continue
        document = (
            db.query(ApsContentDocument)
            .filter(
                and_(
                    ApsContentDocument.content_id == str(row.get("content_id") or ""),
                    ApsContentDocument.content_contract_id == str(row.get("content_contract_id") or ""),
                    ApsContentDocument.chunking_contract_id == str(row.get("chunking_contract_id") or ""),
                )
            )
            .first()
        )
        chunk = (
            db.query(ApsContentChunk)
            .filter(
                and_(
                    ApsContentChunk.content_id == str(row.get("content_id") or ""),
                    ApsContentChunk.chunk_id == str(row.get("chunk_id") or ""),
                    ApsContentChunk.content_contract_id == str(row.get("content_contract_id") or ""),
                    ApsContentChunk.chunking_contract_id == str(row.get("chunking_contract_id") or ""),
                )
            )
            .first()
        )
        if not document or not chunk:
            reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE)
            continue
        # Core structural parity checks (unchanged).
        if (
            int(chunk.chunk_ordinal or 0) != int(row.get("chunk_ordinal") or 0)
            or int(chunk.start_char or 0) != int(row.get("start_char") or 0)
            or int(chunk.end_char or 0) != int(row.get("end_char") or 0)
            or str(chunk.chunk_text_sha256 or "") != str(row.get("chunk_text_sha256") or "")
            or str(document.normalized_text_sha256 or "") != str(row.get("normalized_text_sha256") or "")
            or (chunk.page_start if chunk.page_start is not None else None) != row.get("page_start")
            or (chunk.page_end if chunk.page_end is not None else None) != row.get("page_end")
            or (str(chunk.unit_kind or "").strip() or None) != row.get("unit_kind")
            or (str(chunk.quality_status or "").strip() or None) != row.get("quality_status")
        ):
            reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE)
            continue

        # Required provenance fields – must always match the contract list.
        required = getattr(contract, "APS_REQUIRED_PROVENANCE_FIELDS", ("content_units_ref",))
        for field in required:
            linkage_val = str(getattr(linkage, field, "") or "")
            row_val = str(row.get(field) or "")
            if linkage_val != row_val:
                reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE)
                break
        else:
            # Optional provenance fields – compare only when either side is non‑empty.
            all_fields = [
                "content_units_ref",
                "normalized_text_ref",
                "blob_ref",
                "download_exchange_ref",
                "discovery_ref",
                "selection_ref",
            ]
            optional = [f for f in all_fields if f not in required]
            for field in optional:
                linkage_val = str(getattr(linkage, field, "") or "")
                row_val = str(row.get(field) or "")
                if (linkage_val.strip() or row_val.strip()) and linkage_val != row_val:
                    reasons.append(contract.APS_GATE_FAILURE_ARTIFACT_DB_DIVERGENCE)
                    break


def validate_evidence_bundle_gate(
    *,
    run_ids: list[str] | None = None,
    limit: int = 50,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    require_runs: bool = True,
) -> dict[str, Any]:
    run_rows = _load_candidate_runs(run_ids=run_ids, limit=limit)
    checks: list[dict[str, Any]] = []
    db = SessionLocal()
    try:
        for row in run_rows:
            run_id = str(row.get("run_id") or "").strip()
            if not run_id:
                continue
            scope = f"run_{run_id}"
            bundle_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_bundle_v2.json"))
            failure_paths = sorted(Path(settings.connector_reports_dir).glob(f"{scope}_*_aps_evidence_bundle_failure_v2.json"))
            reasons: list[str] = []
            if not bundle_paths and not failure_paths:
                reasons.append(contract.APS_GATE_FAILURE_MISSING_REF)

            for failure_path in failure_paths:
                failure_payload = _read_json(failure_path)
                if not failure_payload:
                    reasons.append(contract.APS_GATE_FAILURE_FAILURE_SCHEMA)
                    continue
                _validate_failure_payload_schema(failure_payload, reasons)

            for bundle_path in bundle_paths:
                if not bundle_path.exists():
                    reasons.append(contract.APS_GATE_FAILURE_UNRESOLVABLE_REF)
                    continue
                bundle_payload = _read_json(bundle_path)
                if not bundle_payload:
                    reasons.append(contract.APS_GATE_FAILURE_BUNDLE_SCHEMA)
                    continue
                _validate_bundle_payload_schema(bundle_payload, reasons)
                _validate_bundle_checksum(bundle_payload, reasons)
                _validate_request_identity(bundle_payload, reasons)
                _validate_provenance_and_snippets(bundle_payload, reasons)
                _validate_artifact_db_parity(bundle_payload, db, reasons)

            deduped = sorted(list(dict.fromkeys(reasons)))
            checks.append(
                {
                    "run_id": run_id,
                    "bundle_refs": [str(p) for p in bundle_paths],
                    "failure_refs": [str(p) for p in failure_paths],
                    "passed": len(deduped) == 0,
                    "reasons": deduped,
                }
            )
    finally:
        db.close()

    passed = all(bool(c.get("passed")) for c in checks) if checks else False
    report = {
        "schema_id": contract.APS_EVIDENCE_BUNDLE_GATE_SCHEMA_ID,
        "schema_version": contract.APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": passed,
        "checked_runs": len(checks),
        "failed_runs": len([c for c in checks if not bool(c.get("passed"))]),
        "checks": checks,
        "reports_dir": str(Path(settings.connector_reports_dir)),
        "evaluated_run_rows": len(run_rows),
        "require_runs": bool(require_runs),
    }
    if not checks:
        report["passed"] = not bool(require_runs)
        if require_runs:
            report["no_runs_failure"] = True
    nrc_aps_sync_drift.write_json_deterministic(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate NRC APS evidence bundle artifacts (fail-closed).")
    parser.add_argument("--run-id", action="append", default=[], help="Optional specific run id(s) to validate.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of latest NRC APS runs to evaluate when --run-id is not supplied.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Output JSON report path.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow no matching runs (default fail-closed when no runs are found).")
    args = parser.parse_args(argv)
    report = validate_evidence_bundle_gate(
        run_ids=list(args.run_id or []),
        limit=args.limit,
        report_path=args.report,
        require_runs=not args.allow_empty,
    )
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
