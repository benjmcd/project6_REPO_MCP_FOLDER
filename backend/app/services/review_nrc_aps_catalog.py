from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import ConnectorRun
from app.schemas.review_nrc_aps import (
    NrcApsReviewRunSelectorItemOut,
    NrcApsReviewRunSelectorOut,
    NrcApsReviewRunSummaryCountersOut,
)
from app.services.review_nrc_aps_runtime import discover_review_roots, load_summary


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _summary_counters(summary: dict) -> NrcApsReviewRunSummaryCountersOut:
    run_detail = summary.get("run_detail") or {}
    return NrcApsReviewRunSummaryCountersOut(
        selected_count=int(run_detail.get("selected_count") or 0),
        downloaded_count=int(run_detail.get("downloaded_count") or 0),
        failed_count=int(run_detail.get("failed_count") or 0),
    )


def _reviewability(summary: dict) -> tuple[bool, str | None]:
    if not summary:
        return False, "missing_review_summary_root"
    report_refs = (summary.get("run_detail") or {}).get("report_refs") or {}
    if not report_refs.get("aps_artifact_ingestion"):
        return False, "missing_core_stage_artifacts"
    if not report_refs.get("aps_content_index"):
        return False, "missing_core_stage_artifacts"
    return True, None


def _display_label(run_id: str, root: Path, status: str, counters: NrcApsReviewRunSummaryCountersOut) -> str:
    return f"{run_id} | {root.name} | {status} | {counters.selected_count} selected / {counters.failed_count} failed"


def discover_candidate_runs(db: Session) -> NrcApsReviewRunSelectorOut:
    roots = discover_review_roots()
    root_by_run_id: dict[str, tuple[Path, dict]] = {}
    for root in roots:
        try:
            summary = load_summary(root)
        except Exception:
            continue
        run_id = str(summary.get("run_id") or "").strip()
        if run_id:
            root_by_run_id[run_id] = (root, summary)

    out_runs: list[NrcApsReviewRunSelectorItemOut] = []
    default_run_id: str | None = None
    latest_completed_value: tuple[datetime, str] | None = None

    for run in db.query(ConnectorRun).filter(ConnectorRun.connector_key == "nrc_adams_aps").all():
        root, summary = root_by_run_id.get(run.connector_run_id, (None, None))
        reviewable, disabled_reason = _reviewability(summary) if summary else (False, "missing_review_summary_root")
        counters = _summary_counters(summary or {})
        status = str(run.status or "unknown")
        item = NrcApsReviewRunSelectorItemOut(
            run_id=run.connector_run_id,
            display_label=_display_label(run.connector_run_id, root, status, counters) if root else run.connector_run_id,
            status=status,
            submitted_at=_iso(run.submitted_at) or datetime.now(timezone.utc).isoformat(),
            completed_at=_iso(run.completed_at),
            reviewable=reviewable and status == "completed",
            disabled_reason_code=None if reviewable and status == "completed" else disabled_reason or "run_not_completed",
            summary_counters=counters,
        )
        out_runs.append(item)
        if item.reviewable and run.completed_at:
            completed_at = run.completed_at
            if latest_completed_value is None or completed_at > latest_completed_value[0]:
                latest_completed_value = (completed_at, item.run_id)

    known_run_ids = {item.run_id for item in out_runs}
    for run_id, (root, summary) in root_by_run_id.items():
        if run_id in known_run_ids:
            continue
        reviewable, disabled_reason = _reviewability(summary)
        counters = _summary_counters(summary)
        submitted_at = ((summary.get("submission") or {}).get("submitted_at")) or summary.get("generated_at_utc")
        completed_at = ((summary.get("run_detail") or {}).get("completed_at")) or summary.get("generated_at_utc")
        item = NrcApsReviewRunSelectorItemOut(
            run_id=run_id,
            display_label=_display_label(run_id, root, "completed", counters),
            status="completed",
            submitted_at=str(submitted_at),
            completed_at=str(completed_at) if completed_at else None,
            reviewable=reviewable,
            disabled_reason_code=disabled_reason,
            summary_counters=counters,
        )
        out_runs.append(item)
        if item.reviewable and completed_at:
            completed_dt = datetime.fromisoformat(str(completed_at).replace("Z", "+00:00"))
            if latest_completed_value is None or completed_dt > latest_completed_value[0]:
                latest_completed_value = (completed_dt, item.run_id)

    out_runs.sort(key=lambda item: (item.completed_at or item.submitted_at or "", item.run_id), reverse=True)
    if latest_completed_value:
        default_run_id = latest_completed_value[1]

    return NrcApsReviewRunSelectorOut(default_run_id=default_run_id, runs=out_runs)
