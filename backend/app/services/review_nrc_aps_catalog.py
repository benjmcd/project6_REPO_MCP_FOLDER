from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.review_nrc_aps import (
    NrcApsReviewRunSelectorItemOut,
    NrcApsReviewRunSelectorOut,
    NrcApsReviewRunSummaryCountersOut,
)
from app.services.nrc_aps_contract import parse_iso_datetime
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding, discover_runtime_bindings
from app.services.review_nrc_aps_runtime_db import runtime_db_session_for_binding
from app.models import ConnectorRun


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _sortable_dt(value: object) -> tuple[datetime, str]:
    parsed = parse_iso_datetime(value)
    if parsed is None:
        return datetime.min, str(value or "")
    return parsed, str(value or "")


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


def _display_label(run_id: str, binding: ReviewRuntimeBinding, status: str, counters: NrcApsReviewRunSummaryCountersOut) -> str:
    return f"{run_id} | {binding.review_root.name} | {status} | {counters.selected_count} selected / {counters.failed_count} failed"


def _summary_status(summary: dict) -> str:
    run_detail = summary.get("run_detail") or {}
    status = str(run_detail.get("status") or "").strip()
    if status:
        return status
    if run_detail.get("completed_at"):
        return "completed"
    if summary.get("passed") is True:
        return "completed"
    if summary.get("passed") is False:
        return "failed"
    return "unknown"


def _summary_submitted_at(summary: dict) -> str:
    submitted_at = (summary.get("submission") or {}).get("submitted_at")
    if submitted_at:
        return str(submitted_at)
    return str(summary.get("generated_at_utc") or datetime.now(timezone.utc).isoformat())


def _summary_completed_at(summary: dict) -> str | None:
    completed_at = (summary.get("run_detail") or {}).get("completed_at")
    if completed_at:
        return str(completed_at)
    if summary.get("passed") is True:
        generated_at = summary.get("generated_at_utc")
        if generated_at:
            return str(generated_at)
    return None


def _load_connector_run(binding: ReviewRuntimeBinding) -> ConnectorRun | None:
    try:
        with runtime_db_session_for_binding(binding) as session:
            return (
                session.query(ConnectorRun)
                .filter(
                    ConnectorRun.connector_key == "nrc_adams_aps",
                    ConnectorRun.connector_run_id == binding.run_id,
                )
                .first()
            )
    except Exception:
        return None


def discover_candidate_runs(_db: object | None = None) -> NrcApsReviewRunSelectorOut:
    out_runs: list[NrcApsReviewRunSelectorItemOut] = []
    default_run_id: str | None = None
    latest_completed_value: tuple[datetime, str] | None = None

    for binding in discover_runtime_bindings():
        summary = binding.summary
        reviewable, disabled_reason = _reviewability(summary) if summary else (False, "missing_review_summary_root")
        counters = _summary_counters(summary)
        run = _load_connector_run(binding)
        status = str(run.status or _summary_status(summary) or "unknown") if run is not None else _summary_status(summary)
        submitted_at = _iso(run.submitted_at) if run is not None else _summary_submitted_at(summary)
        completed_at = _iso(run.completed_at) if run is not None else _summary_completed_at(summary)
        item = NrcApsReviewRunSelectorItemOut(
            run_id=binding.run_id,
            display_label=_display_label(binding.run_id, binding, status, counters),
            status=status,
            submitted_at=submitted_at or datetime.now(timezone.utc).isoformat(),
            completed_at=completed_at,
            reviewable=reviewable and status == "completed",
            disabled_reason_code=None if reviewable and status == "completed" else disabled_reason or "run_not_completed",
            summary_counters=counters,
        )
        out_runs.append(item)
        if item.reviewable and item.completed_at:
            completed_dt = parse_iso_datetime(item.completed_at)
            if completed_dt and (latest_completed_value is None or completed_dt > latest_completed_value[0]):
                latest_completed_value = (completed_dt, item.run_id)

    out_runs.sort(
        key=lambda item: (*_sortable_dt(item.completed_at or item.submitted_at), item.run_id),
        reverse=True,
    )
    if latest_completed_value:
        default_run_id = latest_completed_value[1]

    return NrcApsReviewRunSelectorOut(default_run_id=default_run_id, runs=out_runs)
