from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisPlan, L3PassRun, L3Session
from app.services.layer3_execution_state import (
    execution_selection_from_session,
    execution_selection_pass_runs,
    execution_state_for_pass_runs,
    pass_run_analysis_run_id,
    pass_run_execution_started,
)
from app.services.layer3_pass_entry import PLAN_STATUS_APPROVED
from app.services.layer3_plan_flow_state import plan_revision_control_for_session
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_response_contract import base_response

EXECUTION_SELECTION_SCHEMA_ID = "layer3.execution_selection.v1"
EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE = ("results", "package", "handoff")


def execution_selection_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    selection = execution_selection_from_session(session)
    pass_runs = execution_selection_pass_runs(db, session_id=session_id)
    if selection is not None:
        analysis_run_ids = [
            value for pass_run in pass_runs if (value := pass_run_analysis_run_id(pass_run))
        ]
        return {
            "schema_id": "layer3.execution_selection_readiness.v1",
            "available": False,
            "selected": True,
            "state": selection.get("state") or execution_state_for_pass_runs(pass_runs),
            "blocked_reason": "execution_selection_already_exists",
            "analysis_plan_id": selection.get("analysis_plan_id"),
            "source_preview_id": selection.get("source_preview_id"),
            "source_preview_hash": selection.get("source_preview_hash"),
            "pass_run_ids": [pass_run.pass_run_id for pass_run in pass_runs],
            "pass_run_count": len(pass_runs),
            "execution_started": any(pass_run_execution_started(pass_run) for pass_run in pass_runs),
            "analysis_run_ids": analysis_run_ids,
            "pass_run_statuses": {pass_run.pass_run_id: pass_run.status for pass_run in pass_runs},
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
            "selected_at": selection.get("selected_at"),
        }

    analysis_plan_id = None
    source_preview_id = None
    source_preview_hash = None
    if (revision_control := plan_revision_control_for_session(db, session_id=session_id)) is not None:
        blocked_reason = str(revision_control.get("state") or "plan_revision_recorded")
    else:
        approved_plans = (
            db.query(L3AnalysisPlan)
            .filter(
                L3AnalysisPlan.session_id == session_id,
                L3AnalysisPlan.status == PLAN_STATUS_APPROVED,
                L3AnalysisPlan.approved_by_operator.is_(True),
            )
            .all()
        )
        if not approved_plans:
            blocked_reason = "no_approved_plan"
        elif len(approved_plans) > 1:
            blocked_reason = "multiple_approved_plans"
        elif pass_runs:
            blocked_reason = "pass_runs_already_exist"
        else:
            approved_plan = approved_plans[0]
            plan_json = approved_plan.plan_json or {}
            analysis_plan_id = approved_plan.analysis_plan_id
            source_preview_id = plan_json.get("source_preview_id")
            source_preview_hash = plan_json.get("source_preview_hash")
            blocked_reason = None

    return {
        "schema_id": "layer3.execution_selection_readiness.v1",
        "available": blocked_reason is None,
        "selected": False,
        "state": None,
        "blocked_reason": blocked_reason,
        "analysis_plan_id": analysis_plan_id,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "pass_run_ids": [],
        "pass_run_count": len(pass_runs),
        "execution_started": False,
        "analysis_run_ids": [],
        "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        "selected_at": None,
    }


def execution_selection_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_runs: list[L3PassRun],
) -> dict[str, Any]:
    analysis_run_ids = [
        value for pass_run in pass_runs if (value := pass_run_analysis_run_id(pass_run))
    ]
    return {
        **base_response(EXECUTION_SELECTION_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "preview_identity": preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "pass_run_ids": [pass_run.pass_run_id for pass_run in pass_runs],
        "pass_run_count": len(pass_runs),
        "execution_started": any(pass_run_execution_started(pass_run) for pass_run in pass_runs),
        "analysis_run_ids": analysis_run_ids,
        "pass_run_statuses": {pass_run.pass_run_id: pass_run.status for pass_run in pass_runs},
        "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        "next_state": execution_state_for_pass_runs(pass_runs),
    }
