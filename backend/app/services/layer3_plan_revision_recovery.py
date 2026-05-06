from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
    L3AnalysisSet,
    L3PassRun,
    L3Session,
    L3TypingRecord,
)
from app.services.layer3_authority_rail import authority_rail
from app.services.layer3_plan_flow_contract import plan_revision_recovery_blocked_fields
from app.services.layer3_plan_revision_state import (
    PLAN_REVISION_CONTROL_CONTEXT_KEY,
    PLAN_REVISION_RECOVERABLE_STATES,
    PLAN_REVISION_RECOVERY_CONTEXT_KEY,
    PLAN_REVISION_RECOVERY_DECISION,
    PLAN_REVISION_RECOVERY_STATE,
    plan_revision_recovery_from_session,
    plan_revision_recovery_record,
    raw_plan_revision_control_from_session,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone, stable_id, utcnow_iso_z
from app.services.layer3_workbench_error import Layer3WorkbenchError


PLAN_REVISION_RECOVERY_RESULT_SCHEMA_ID = "layer3.plan_revision_recovery_result.v1"
PLAN_REVISION_RECOVERY_PREVIEW_MARKER_SCHEMA_ID = "layer3.plan_revision_recovery_preview_refresh.v1"
PLAN_REVISION_RECOVERY_NEXT_STATE = "gate_c_typing_committed"
PLAN_REVISION_RECOVERY_DOWNSTREAM_UNAVAILABLE = ("execution", "results", "package", "handoff")
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


def plan_revision_recovery_preview_marker(recovery: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(recovery, dict):
        return None
    if recovery.get("state") != PLAN_REVISION_RECOVERY_STATE:
        return None
    return {
        "schema_id": PLAN_REVISION_RECOVERY_PREVIEW_MARKER_SCHEMA_ID,
        "recovery_id": recovery.get("recovery_id"),
        "client_request_id": recovery.get("client_request_id"),
        "source_revision_state": recovery.get("source_revision_state"),
        "source_preview_id": recovery.get("source_preview_id"),
        "source_preview_hash": recovery.get("source_preview_hash"),
        "preview_refresh_required": True,
        "approval_available": False,
        "created_at": recovery.get("created_at"),
    }


def _analysis_plan_conflict(db: Session, *, session_id: str) -> Layer3WorkbenchError | None:
    plans = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).all()
    if not plans:
        return None
    if any(bool(plan.approved_by_operator) for plan in plans):
        return Layer3WorkbenchError(
            "plan_already_approved",
            f"Layer 3 session '{session_id}' already has an approved analysis plan.",
            status="conflict",
            http_status=409,
        )
    return Layer3WorkbenchError(
        "plan_already_materialized",
        f"Layer 3 session '{session_id}' already has a non-approved analysis plan.",
        status="conflict",
        http_status=409,
    )


def _require_gate_c_committed(db: Session, *, session_id: str) -> None:
    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    if typing_record_count == 0 or analysis_set_count == 0:
        raise Layer3WorkbenchError(
            "gate_c_not_committed",
            f"Layer 3 session '{session_id}' does not have committed Gate C typing authority.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["commit_gate_c_typing"],
        )


def _recovery_response(
    *,
    request_id: str,
    session: L3Session,
    recovery: dict[str, Any],
) -> dict[str, Any]:
    return {
        **base_response(PLAN_REVISION_RECOVERY_RESULT_SCHEMA_ID, request_id=request_id),
        "session_id": session.session_id,
        "source_revision_state": recovery["source_revision_state"],
        "next_state": PLAN_REVISION_RECOVERY_NEXT_STATE,
        "preview_refresh_required": True,
        "approval_available": False,
        "execution_started": False,
        "recovery_lifecycle_only": True,
        "source_preview_id": recovery["source_preview_id"],
        "source_preview_hash": recovery["source_preview_hash"],
        "operator_decision": recovery["operator_decision"],
        "operator_note_recorded": bool(recovery.get("operator_note_recorded")),
        "authority_rail": authority_rail(
            session_id=session.session_id,
            current_gate="plan",
            persistence_mode="plan_revision_recovery",
            counts=_gate_b_summary_from_session(session),
            typing_status="committed",
            downstream_unavailable=PLAN_REVISION_RECOVERY_DOWNSTREAM_UNAVAILABLE,
        ),
        "downstream_unavailable": list(PLAN_REVISION_RECOVERY_DOWNSTREAM_UNAVAILABLE),
        "plan_revision_recovery": json_clone(recovery),
    }


def _raise_if_duplicate_conflicts(existing: dict[str, Any], payload: dict[str, Any]) -> None:
    source_state = str(payload.get("source_revision_state") or "").strip()
    source_preview_id = str(payload.get("source_preview_id") or "").strip()
    source_preview_hash = str(payload.get("source_preview_hash") or "").strip()
    if source_state != str(existing.get("source_revision_state") or ""):
        raise Layer3WorkbenchError(
            "plan_revision_state_mismatch",
            "Plan revision recovery must reference the same source revision state as the recorded recovery.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_revision_state"],
        )
    if (
        source_preview_id != str(existing.get("source_preview_id") or "")
        or source_preview_hash != str(existing.get("source_preview_hash") or "")
    ):
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan revision recovery must reference the same source preview id and hash as the recorded recovery.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_preview_id", "source_preview_hash"],
            next_allowed_actions=["inspect_recorded_plan_revision_recovery"],
        )


def recover_plan_revision_for_preview_refresh(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for plan revision recovery.",
            status="invalid",
            blocked_fields=["client_request_id"],
        )

    operator_decision = str(payload.get("operator_decision") or "").strip()
    if operator_decision != PLAN_REVISION_RECOVERY_DECISION:
        raise Layer3WorkbenchError(
            "unsupported_revision_recovery_decision",
            f"Unsupported plan revision recovery decision: {operator_decision or 'missing'}.",
            status="invalid",
            blocked_fields=["operator_decision"],
            next_allowed_actions=["use_supported_revision_recovery_decision"],
        )

    forbidden = plan_revision_recovery_blocked_fields(payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan revision recovery request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_recovery_preview_refresh_only_request"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan revision recovery.", http_status=404)

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)

    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    plan_conflict = _analysis_plan_conflict(db, session_id=session_id)
    if plan_conflict is not None:
        raise plan_conflict

    existing_recovery = plan_revision_recovery_from_session(session)
    if existing_recovery is not None and str(existing_recovery.get("client_request_id") or "") == request_id:
        _raise_if_duplicate_conflicts(existing_recovery, payload)
        return _recovery_response(request_id=request_id, session=session, recovery=existing_recovery)

    control = raw_plan_revision_control_from_session(session)
    if control is None or control.get("recovery_state") == PLAN_REVISION_RECOVERY_STATE:
        raise Layer3WorkbenchError(
            "plan_revision_recovery_not_available",
            f"Layer 3 session '{session_id}' does not have an active plan revision-control state to recover.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["refresh_session_summary"],
        )

    source_revision_state = str(payload.get("source_revision_state") or "").strip()
    if source_revision_state not in PLAN_REVISION_RECOVERABLE_STATES or source_revision_state != str(control.get("state") or ""):
        raise Layer3WorkbenchError(
            "plan_revision_state_mismatch",
            "Plan revision recovery must reference the recorded source revision-control state.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_revision_state"],
            next_allowed_actions=["refresh_session_summary"],
        )

    source_preview_id = str(payload.get("source_preview_id") or "").strip()
    source_preview_hash = str(payload.get("source_preview_hash") or "").strip()
    if (
        source_preview_id != str(control.get("source_preview_id") or "")
        or source_preview_hash != str(control.get("source_preview_hash") or "")
    ):
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan revision recovery must reference the recorded source preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_preview_id", "source_preview_hash"],
            next_allowed_actions=["refresh_session_summary"],
        )

    _require_gate_c_committed(db, session_id=session_id)

    created_at = utcnow_iso_z()
    recovery_id = stable_id(
        "plan-revision-recovery",
        {
            "session_id": session_id,
            "client_request_id": request_id,
            "source_revision_state": source_revision_state,
            "source_preview_id": source_preview_id,
            "source_preview_hash": source_preview_hash,
        },
    )
    recovery = plan_revision_recovery_record(
        recovery_id=recovery_id,
        client_request_id=request_id,
        source_revision_state=source_revision_state,
        source_preview_id=source_preview_id,
        source_preview_hash=source_preview_hash,
        operator_decision=operator_decision,
        operator_note=str(payload.get("operator_note") or "").strip(),
        created_at=created_at,
    )
    recovered_control = {
        **json_clone(control),
        "approval_available": False,
        "execution_started": False,
        "recovery_state": PLAN_REVISION_RECOVERY_STATE,
        "recovered_at": created_at,
        "recovery_id": recovery_id,
        "recovery_client_request_id": request_id,
    }
    session.summary_json = {
        **json_clone(session.summary_json or {}),
        PLAN_REVISION_CONTROL_CONTEXT_KEY: recovered_control,
        PLAN_REVISION_RECOVERY_CONTEXT_KEY: recovery,
    }
    db.commit()
    return _recovery_response(request_id=request_id, session=session, recovery=recovery)
