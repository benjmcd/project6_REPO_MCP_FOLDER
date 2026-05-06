from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3_ANALYSIS_PLAN_STATUS_CANCELLED,
    L3AnalysisPlan,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3Session,
)
from app.services.layer3_authority_rail import authority_rail
from app.services.layer3_plan_flow_contract import approved_plan_cancel_blocked_fields
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone, stable_id, utcnow_iso_z
from app.services.layer3_workbench_error import Layer3WorkbenchError


APPROVED_PLAN_CANCEL_REQUEST_SCHEMA_ID = "layer3.approved_plan_cancel_request.v1"
APPROVED_PLAN_CANCEL_RESULT_SCHEMA_ID = "layer3.approved_plan_cancel_result.v1"
APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID = "layer3.approved_plan_cancel_state.v1"
APPROVED_PLAN_CANCEL_CONTEXT_KEY = "approved_plan_cancel"
APPROVED_PLAN_CANCEL_DECISION = "cancel_approved_plan_without_replacement"
APPROVED_PLAN_CANCEL_NEXT_STATE = "approved_plan_cancelled"
APPROVED_PLAN_CANCELLED_STATUS = L3_ANALYSIS_PLAN_STATUS_CANCELLED
APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE = ("execution", "results", "package", "handoff")
GATE_B_DECISIONS = ("approved", "denied", "isolated", "flagged")


def _gate_b_summary_from_session(session: L3Session) -> dict[str, int]:
    summary = session.summary_json or {}
    counts = summary.get("gate_b_summary_v1")
    if isinstance(counts, dict):
        return {decision: int(counts.get(decision, 0)) for decision in GATE_B_DECISIONS}
    decisions = ((session.operator_context_json or {}).get("layer3_gate_b_decision_manifest_v1") or {}).get("items") or []
    return {
        decision: sum(1 for item in decisions if isinstance(item, dict) and item.get("decision") == decision)
        for decision in GATE_B_DECISIONS
    }


def approved_plan_cancel_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    cancellation = (session.summary_json or {}).get(APPROVED_PLAN_CANCEL_CONTEXT_KEY)
    if not isinstance(cancellation, dict):
        return None
    if cancellation.get("schema_id") != APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID:
        return None
    return cancellation


def _source_preview_identity(plan: L3AnalysisPlan) -> tuple[str, str]:
    plan_json = plan.plan_json or {}
    return str(plan_json.get("source_preview_id") or "").strip(), str(plan_json.get("source_preview_hash") or "").strip()


def _cancel_response(
    *,
    request_id: str,
    session: L3Session,
    plan: L3AnalysisPlan | None,
    cancellation: dict[str, Any],
) -> dict[str, Any]:
    return {
        **base_response(APPROVED_PLAN_CANCEL_RESULT_SCHEMA_ID, request_id=request_id),
        "session_id": session.session_id,
        "next_state": APPROVED_PLAN_CANCEL_NEXT_STATE,
        "approved_plan_cancelled": True,
        "approval_available": False,
        "execution_started": False,
        "replacement_plan_created": False,
        "analysis_plan_id": cancellation["analysis_plan_id"],
        "plan_status": plan.status if plan is not None else APPROVED_PLAN_CANCELLED_STATUS,
        "previous_plan_status": cancellation["previous_plan_status"],
        "approved_by_operator": bool(plan.approved_by_operator) if plan is not None else True,
        "approved_at": plan.approved_at.isoformat() if plan is not None and plan.approved_at else cancellation.get("approved_at"),
        "source_preview_id": cancellation["source_preview_id"],
        "source_preview_hash": cancellation["source_preview_hash"],
        "operator_decision": cancellation["operator_decision"],
        "operator_note_recorded": bool(cancellation.get("operator_note_recorded")),
        "authority_rail": authority_rail(
            session_id=session.session_id,
            current_gate="plan",
            persistence_mode="approved_plan_cancel",
            counts=_gate_b_summary_from_session(session),
            typing_status="committed",
            downstream_unavailable=APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE,
        ),
        "downstream_unavailable": list(APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE),
        "approved_plan_cancel": json_clone(cancellation),
    }


def _raise_duplicate_conflicts(existing: dict[str, Any], payload: dict[str, Any]) -> None:
    expected = {
        "analysis_plan_id": str(payload.get("analysis_plan_id") or "").strip(),
        "source_preview_id": str(payload.get("source_preview_id") or "").strip(),
        "source_preview_hash": str(payload.get("source_preview_hash") or "").strip(),
        "operator_decision": str(payload.get("operator_decision") or "").strip(),
    }
    mismatched = [field for field, value in expected.items() if value != str(existing.get(field) or "")]
    if mismatched:
        raise Layer3WorkbenchError(
            "idempotency_conflict",
            "client_request_id already cancelled a different approved plan authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched,
        )


def _existing_downstream_state_counts(db: Session, *, session_id: str) -> dict[str, int]:
    counts = {
        "pass_runs": db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count(),
        "reconciliation_records": db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .count(),
        "output_packages": db.query(L3OutputPackage).filter(L3OutputPackage.session_id == session_id).count(),
    }
    return {name: count for name, count in counts.items() if count > 0}


def _raise_if_downstream_state_exists(db: Session, *, session_id: str) -> None:
    counts = _existing_downstream_state_counts(db, session_id=session_id)
    if counts.get("pass_runs", 0) > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )
    if counts:
        raise Layer3WorkbenchError(
            "downstream_state_already_exists",
            f"Layer 3 session '{session_id}' already has downstream package state.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(counts),
            next_allowed_actions=["inspect_existing_downstream_state"],
        )


def cancel_approved_plan_without_replacement(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for approved-plan cancellation.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_approved_plan_cancel"],
        )

    operator_decision = str(payload.get("operator_decision") or "").strip()
    if operator_decision != APPROVED_PLAN_CANCEL_DECISION:
        raise Layer3WorkbenchError(
            "unsupported_approved_plan_cancel_decision",
            f"Unsupported approved-plan cancel decision: {operator_decision or 'missing'}.",
            status="invalid",
            blocked_fields=["operator_decision"],
            next_allowed_actions=["use_supported_approved_plan_cancel_decision"],
        )

    forbidden = approved_plan_cancel_blocked_fields(payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "approved_plan_correction_not_admitted",
            f"Approved-plan cancellation request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_cancel_without_replacement_only_request"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    source_preview_id = str(payload.get("source_preview_id") or "").strip()
    source_preview_hash = str(payload.get("source_preview_hash") or "").strip()
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("source_preview_id", source_preview_id),
            ("source_preview_hash", source_preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_approved_plan_cancel_fields",
            f"Approved-plan cancellation is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_approved_plan_cancel_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)

    _raise_if_downstream_state_exists(db, session_id=session_id)

    plan = (
        db.query(L3AnalysisPlan)
        .filter(L3AnalysisPlan.session_id == session_id, L3AnalysisPlan.analysis_plan_id == analysis_plan_id)
        .with_for_update()
        .one_or_none()
    )
    existing_cancel = approved_plan_cancel_from_session(session)
    if existing_cancel is not None:
        if str(existing_cancel.get("client_request_id") or "") == request_id:
            _raise_duplicate_conflicts(existing_cancel, payload)
            return _cancel_response(request_id=request_id, session=session, plan=plan, cancellation=existing_cancel)
        raise Layer3WorkbenchError(
            "approved_plan_already_cancelled",
            f"Layer 3 session '{session_id}' already has a cancelled approved plan.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == "approved",
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan to cancel.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    plan = approved_plans[0]
    if plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Approved-plan cancellation must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    stored_preview_id, stored_preview_hash = _source_preview_identity(plan)
    if source_preview_id != stored_preview_id or source_preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Approved-plan cancellation must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_preview_id", "source_preview_hash"],
            next_allowed_actions=["refresh_session_summary"],
        )

    created_at = utcnow_iso_z()
    cancellation_id = stable_id(
        "approved-plan-cancel",
        {
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "client_request_id": request_id,
            "source_preview_id": source_preview_id,
            "source_preview_hash": source_preview_hash,
        },
    )
    cancellation = {
        "schema_id": APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID,
        "cancellation_id": cancellation_id,
        "client_request_id": request_id,
        "state": APPROVED_PLAN_CANCEL_NEXT_STATE,
        "analysis_plan_id": analysis_plan_id,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(str(payload.get("operator_note") or "").strip()),
        "previous_plan_status": str(plan.status),
        "plan_status": APPROVED_PLAN_CANCELLED_STATUS,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "approval_available": False,
        "execution_started": False,
        "replacement_plan_created": False,
        "created_at": created_at,
    }
    plan.status = APPROVED_PLAN_CANCELLED_STATUS
    plan.plan_json = {
        **json_clone(plan.plan_json or {}),
        APPROVED_PLAN_CANCEL_CONTEXT_KEY: cancellation,
        "approval_available": False,
        "execution_started": False,
        "approved_plan_cancelled": True,
    }
    session.summary_json = {
        **json_clone(session.summary_json or {}),
        APPROVED_PLAN_CANCEL_CONTEXT_KEY: cancellation,
    }
    db.commit()
    return _cancel_response(request_id=request_id, session=session, plan=plan, cancellation=cancellation)
