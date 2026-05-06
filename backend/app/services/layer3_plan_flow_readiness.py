from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisPlan, L3AnalysisSet, L3PassRun, L3Session, L3TypingRecord
from app.services.layer3_approved_plan_correction import APPROVED_PLAN_CANCELLED_STATUS
from app.services.layer3_pass_entry import Layer3PassEntryError, preview_pass_entry
from app.services.layer3_plan_errors import plan_preview_workbench_error
from app.services.layer3_plan_flow_state import latest_analysis_plan, plan_revision_control_for_session
from app.services.layer3_plan_revision_state import (
    plan_revision_control_from_session,
    plan_revision_recovery_from_session,
)
from app.services.layer3_utils import json_clone


def plan_preview_readiness(
    db: Session,
    *,
    session_id: str,
    include_owner_service: bool = False,
) -> dict[str, Any]:
    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    analysis_plan_count = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).count()
    pass_run_count = db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count()
    blocked_reason = None
    admitted_set_count = None
    excluded_set_count = None
    planned_pass_count = None
    if typing_record_count == 0:
        blocked_reason = "gate_c_not_committed"
    elif analysis_set_count == 0:
        blocked_reason = "no_analysis_sets"
    elif analysis_plan_count > 0 or pass_run_count > 0:
        latest_plan = latest_analysis_plan(db, session_id=session_id)
        blocked_reason = (
            "approved_plan_cancelled"
            if latest_plan is not None and latest_plan.status == APPROVED_PLAN_CANCELLED_STATUS
            else "plan_already_materialized"
        )
    elif (revision_control := plan_revision_control_for_session(db, session_id=session_id)) is not None:
        blocked_reason = str(revision_control.get("state") or "plan_revision_recorded")
    elif include_owner_service:
        try:
            owner_preview = preview_pass_entry(db, session_id=session_id)
            admitted_set_count = len(owner_preview.admitted_sets)
            excluded_set_count = len(owner_preview.excluded_sets)
            planned_pass_count = len(owner_preview.planned_passes)
        except Layer3PassEntryError as exc:
            blocked_reason = plan_preview_workbench_error(exc).error_code
    return {
        "schema_id": "layer3.plan_preview_readiness.v1",
        "available": blocked_reason is None,
        "blocked_reason": blocked_reason,
        "typing_record_count": typing_record_count,
        "analysis_set_count": analysis_set_count,
        "analysis_plan_count": analysis_plan_count,
        "pass_run_count": pass_run_count,
        "admitted_set_count": admitted_set_count,
        "excluded_set_count": excluded_set_count,
        "planned_pass_count": planned_pass_count,
    }


def plan_approval_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    analysis_plan = latest_analysis_plan(db, session_id=session_id)
    pass_run_count = db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count()
    if analysis_plan is None:
        session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
        recovery = plan_revision_recovery_from_session(session)
        preview = plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
        if recovery is not None:
            return {
                "schema_id": "layer3.plan_approval_readiness.v1",
                "available": False,
                "approved": False,
                "blocked_reason": "plan_preview_refresh_required",
                "analysis_plan_id": None,
                "plan_status": None,
                "approved_by_operator": False,
                "approved_at": None,
                "approved_set_count": preview["admitted_set_count"],
                "excluded_set_count": preview["excluded_set_count"],
                "planned_pass_count": preview["planned_pass_count"],
                "pass_run_count": pass_run_count,
                "preview_refresh_required": True,
                "plan_revision_recovery_id": recovery.get("recovery_id"),
            }
        return {
            "schema_id": "layer3.plan_approval_readiness.v1",
            "available": preview["available"],
            "approved": False,
            "blocked_reason": preview["blocked_reason"],
            "analysis_plan_id": None,
            "plan_status": None,
            "approved_by_operator": False,
            "approved_at": None,
            "approved_set_count": preview["admitted_set_count"],
            "excluded_set_count": preview["excluded_set_count"],
            "planned_pass_count": preview["planned_pass_count"],
            "pass_run_count": pass_run_count,
        }
    plan_json = analysis_plan.plan_json or {}
    approved = bool(analysis_plan.approved_by_operator)
    cancelled = analysis_plan.status == APPROVED_PLAN_CANCELLED_STATUS
    if cancelled:
        cancellation = plan_json.get("approved_plan_cancel") if isinstance(plan_json.get("approved_plan_cancel"), dict) else None
        return {
            "schema_id": "layer3.plan_approval_readiness.v1",
            "available": False,
            "approved": False,
            "blocked_reason": "approved_plan_cancelled",
            "analysis_plan_id": analysis_plan.analysis_plan_id,
            "plan_status": analysis_plan.status,
            "approved_by_operator": approved,
            "approved_at": analysis_plan.approved_at.isoformat() if analysis_plan.approved_at else None,
            "approved_set_count": len(analysis_plan.analysis_set_ids_json or []),
            "excluded_set_count": len(plan_json.get("excluded_sets_json") or []),
            "planned_pass_count": len(plan_json.get("planned_passes_json") or []),
            "pass_run_count": pass_run_count,
            "approval_only": bool(plan_json.get("approval_only")),
            "execution_started": bool(plan_json.get("execution_started")),
            "approved_plan_cancelled": True,
            "approval_available": False,
            "approved_plan_cancel": json_clone(cancellation) if cancellation is not None else None,
        }
    return {
        "schema_id": "layer3.plan_approval_readiness.v1",
        "available": False,
        "approved": approved,
        "blocked_reason": "plan_already_approved" if approved else "plan_already_materialized",
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "plan_status": analysis_plan.status,
        "approved_by_operator": approved,
        "approved_at": analysis_plan.approved_at.isoformat() if analysis_plan.approved_at else None,
        "approved_set_count": len(analysis_plan.analysis_set_ids_json or []),
        "excluded_set_count": len(plan_json.get("excluded_sets_json") or []),
        "planned_pass_count": len(plan_json.get("planned_passes_json") or []),
        "pass_run_count": pass_run_count,
        "approval_only": bool(plan_json.get("approval_only")),
        "execution_started": bool(plan_json.get("execution_started")),
    }


def plan_revision_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    control = plan_revision_control_from_session(session)
    if control is None:
        recovery = plan_revision_recovery_from_session(session)
        preview = plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
        if recovery is not None:
            return {
                "schema_id": "layer3.plan_revision_readiness.v1",
                "available": preview["available"],
                "state": recovery.get("state"),
                "blocked_reason": preview["blocked_reason"],
                "source_revision_state": recovery.get("source_revision_state"),
                "source_preview_id": recovery.get("source_preview_id"),
                "source_preview_hash": recovery.get("source_preview_hash"),
                "operator_decision": recovery.get("operator_decision"),
                "operator_note_recorded": bool(recovery.get("operator_note_recorded")),
                "approval_available": False,
                "execution_started": False,
                "preview_refresh_required": True,
                "recovered": True,
                "recovery_id": recovery.get("recovery_id"),
                "created_at": recovery.get("created_at"),
            }
        return {
            "schema_id": "layer3.plan_revision_readiness.v1",
            "available": preview["available"],
            "state": None,
            "blocked_reason": preview["blocked_reason"],
            "source_preview_id": None,
            "source_preview_hash": None,
            "operator_decision": None,
            "operator_note_recorded": False,
            "approval_available": preview["available"],
            "execution_started": False,
        }
    return {
        "schema_id": "layer3.plan_revision_readiness.v1",
        "available": False,
        "state": control.get("state"),
        "blocked_reason": control.get("state"),
        "source_preview_id": control.get("source_preview_id"),
        "source_preview_hash": control.get("source_preview_hash"),
        "operator_decision": control.get("operator_decision"),
        "operator_note_recorded": bool(control.get("operator_note_recorded")),
        "approval_available": False,
        "execution_started": False,
        "created_at": control.get("created_at"),
    }
