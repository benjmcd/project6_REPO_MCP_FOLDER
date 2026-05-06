from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3PassRun, L3Session
from app.services.layer3_pass_entry import (
    PASS_STATUS_COMPLETED,
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
    PASS_STATUS_RUNNING,
    PASS_STATUS_SELECTED_NOT_STARTED,
)

EXECUTION_SELECTION_STATE_SCHEMA_ID = "layer3.execution_selection_state.v1"
EXECUTION_SELECTION_STATE = "execution_selected_not_started"
ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID = "layer3.analysis_execution_start_state.v1"
EXECUTION_PASS_RUNNING_STATE = "execution_pass_running"
EXECUTION_PASS_COMPLETED_STATE = "execution_pass_completed"
EXECUTION_PASS_FAILED_STATE = "execution_pass_failed"


def execution_selection_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    selection = (session.summary_json or {}).get("execution_selection")
    if not isinstance(selection, dict):
        return None
    if selection.get("schema_id") != EXECUTION_SELECTION_STATE_SCHEMA_ID:
        return None
    return selection


def execution_selection_pass_runs(db: Session, *, session_id: str) -> list[L3PassRun]:
    return (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == session_id)
        .order_by(L3PassRun.created_at.asc(), L3PassRun.pass_run_id.asc())
        .all()
    )


def pass_run_analysis_run_id(pass_run: L3PassRun) -> str | None:
    value = (pass_run.summary_json or {}).get("analysis_run_id")
    return str(value) if value else None


def pass_run_execution_started(pass_run: L3PassRun) -> bool:
    return (
        bool((pass_run.summary_json or {}).get("execution_started"))
        or pass_run.status != PASS_STATUS_SELECTED_NOT_STARTED
    )


def execution_state_for_pass_runs(pass_runs: list[L3PassRun]) -> str:
    statuses = {pass_run.status for pass_run in pass_runs}
    if PASS_STATUS_RUNNING in statuses:
        return EXECUTION_PASS_RUNNING_STATE
    if PASS_STATUS_FAILED in statuses:
        return EXECUTION_PASS_FAILED_STATE
    if pass_runs and statuses <= {
        PASS_STATUS_COMPLETED,
        PASS_STATUS_COMPLETED_WITH_WARNINGS,
    }:
        return EXECUTION_PASS_COMPLETED_STATE
    return EXECUTION_SELECTION_STATE


def analysis_execution_start_from_pass_run(pass_run: L3PassRun) -> dict[str, Any] | None:
    state = (pass_run.summary_json or {}).get("analysis_execution_start")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID:
        return None
    return state
