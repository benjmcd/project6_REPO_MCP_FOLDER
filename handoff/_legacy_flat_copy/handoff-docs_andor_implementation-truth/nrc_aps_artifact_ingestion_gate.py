from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_sync_drift


DEFAULT_REPORT_PATH = Path("tests/reports/nrc_aps_artifact_ingestion_validation_report.json")


def _load_candidate_runs(*, run_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    reports_dir = Path(settings.connector_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    normalized_run_ids = [str(item).strip() for item in (run_ids or []) if str(item).strip()]

    def _run_row_from_summary(run_id: str, summary_path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        if str(payload.get("connector_key") or "").strip() != "nrc_adams_aps":
            return None
        status = str(payload.get("status") or "").strip()
        if status not in {"completed", "completed_with_errors", "failed"}:
            return None
        return {"run_id": run_id, "status": status, "_summary_mtime": summary_path.stat().st_mtime}

    rows: list[dict[str, Any]] = []
    if normalized_run_ids:
        for run_id in normalized_run_ids:
            summary_path = reports_dir / f"{run_id}_run_summary.json"
            if not summary_path.exists():
                continue
            row = _run_row_from_summary(run_id, summary_path)
            if row:
                rows.append(row)
    else:
        summary_paths = sorted(
            reports_dir.glob("*_run_summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for summary_path in summary_paths:
            run_id = summary_path.name.rsplit("_run_summary.json", 1)[0]
            row = _run_row_from_summary(run_id, summary_path)
            if row:
                rows.append(row)
            if limit and limit > 0 and len(rows) >= int(limit):
                break

    for row in rows:
        row.pop("_summary_mtime", None)
    return rows


def validate_artifact_ingestion_gate(
    *,
    run_ids: list[str] | None = None,
    limit: int = 50,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    require_runs: bool = True,
) -> dict[str, Any]:
    run_rows = _load_candidate_runs(run_ids=run_ids, limit=limit)
    report = nrc_aps_artifact_ingestion.validate_artifact_ingestion_artifact_presence(
        run_rows=run_rows,
        reports_dir=settings.connector_reports_dir,
    )
    report["validated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report["reports_dir"] = str(Path(settings.connector_reports_dir))
    report["evaluated_run_rows"] = len(run_rows)
    report["require_runs"] = bool(require_runs)
    if len(run_rows) == 0:
        report["passed"] = not bool(require_runs)
        if require_runs:
            report["no_runs_failure"] = True
    nrc_aps_sync_drift.write_json_deterministic(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate NRC APS artifact-ingestion artifacts (fail-closed).")
    parser.add_argument(
        "--run-id",
        action="append",
        default=[],
        help="Optional specific run id(s) to validate; repeat for multiple values.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of latest NRC APS runs to validate when --run-id is not used.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow no matching runs (default is fail-closed when no runs are found).",
    )
    args = parser.parse_args(argv)
    report = validate_artifact_ingestion_gate(
        run_ids=list(args.run_id or []),
        limit=int(args.limit),
        report_path=args.report,
        require_runs=not bool(args.allow_empty),
    )
    return 0 if bool(report.get("passed")) else 1

