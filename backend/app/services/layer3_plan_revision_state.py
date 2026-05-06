from __future__ import annotations

from typing import Any

from app.models.models import L3Session

PLAN_REVISION_CONTROL_SCHEMA_ID = "layer3.plan_revision_control.v1"
PLAN_REVISION_CONTROL_CONTEXT_KEY = "plan_revision_control"
PLAN_REVISION_RECOVERY_SCHEMA_ID = "layer3.plan_revision_recovery_control.v1"
PLAN_REVISION_RECOVERY_CONTEXT_KEY = "plan_revision_recovery"
PLAN_REVISION_DECISIONS = frozenset({"reject_current_preview", "request_revision"})
PLAN_REVISION_RECOVERY_DECISION = "recover_for_preview_refresh"
PLAN_REVISION_RECOVERY_STATE = "plan_preview_refresh_required"
PLAN_REVISION_STATE_BY_DECISION = {
    "reject_current_preview": "plan_rejected",
    "request_revision": "plan_revision_requested",
}
PLAN_REVISION_RECOVERABLE_STATES = frozenset(PLAN_REVISION_STATE_BY_DECISION.values())


def raw_plan_revision_control_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    control = (session.summary_json or {}).get(PLAN_REVISION_CONTROL_CONTEXT_KEY)
    if not isinstance(control, dict):
        return None
    if control.get("schema_id") != PLAN_REVISION_CONTROL_SCHEMA_ID:
        return None
    return control


def plan_revision_control_from_session(session: L3Session | None) -> dict[str, Any] | None:
    control = raw_plan_revision_control_from_session(session)
    if control is None:
        return None
    if control.get("recovery_state") == PLAN_REVISION_RECOVERY_STATE:
        return None
    return control


def plan_revision_recovery_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    recovery = (session.summary_json or {}).get(PLAN_REVISION_RECOVERY_CONTEXT_KEY)
    if not isinstance(recovery, dict):
        return None
    if recovery.get("schema_id") != PLAN_REVISION_RECOVERY_SCHEMA_ID:
        return None
    return recovery


def plan_revision_control_record(
    *,
    source_preview_id: str,
    source_preview_hash: str,
    operator_decision: str,
    operator_note: str,
    created_at: str,
) -> dict[str, Any]:
    if operator_decision not in PLAN_REVISION_DECISIONS:
        raise ValueError(f"Unsupported plan revision decision: {operator_decision or 'missing'}.")
    return {
        "schema_id": PLAN_REVISION_CONTROL_SCHEMA_ID,
        "state": PLAN_REVISION_STATE_BY_DECISION[operator_decision],
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "approval_available": False,
        "execution_started": False,
        "created_at": created_at,
    }


def plan_revision_recovery_record(
    *,
    recovery_id: str,
    client_request_id: str,
    source_revision_state: str,
    source_preview_id: str,
    source_preview_hash: str,
    operator_decision: str,
    operator_note: str,
    created_at: str,
) -> dict[str, Any]:
    if source_revision_state not in PLAN_REVISION_RECOVERABLE_STATES:
        raise ValueError(f"Unsupported plan revision recovery state: {source_revision_state or 'missing'}.")
    if operator_decision != PLAN_REVISION_RECOVERY_DECISION:
        raise ValueError(f"Unsupported plan revision recovery decision: {operator_decision or 'missing'}.")
    return {
        "schema_id": PLAN_REVISION_RECOVERY_SCHEMA_ID,
        "recovery_id": recovery_id,
        "client_request_id": client_request_id,
        "state": PLAN_REVISION_RECOVERY_STATE,
        "source_revision_state": source_revision_state,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "preview_refresh_required": True,
        "approval_available": False,
        "execution_started": False,
        "created_at": created_at,
    }
