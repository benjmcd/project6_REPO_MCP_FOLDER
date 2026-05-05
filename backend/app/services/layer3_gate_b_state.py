from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3Session

GATE_B_IDEMPOTENCY_SCHEMA_ID = "layer3.gate_b_idempotency.v1"
GATE_B_IDEMPOTENCY_CONTEXT_KEY = "layer3_gate_b_idempotency_v1"


def gate_b_idempotency_record(
    *,
    client_request_id: str,
    preflight_id: str,
    source_set_id: str,
    material_preview_id: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> dict[str, Any]:
    return {
        "schema_id": GATE_B_IDEMPOTENCY_SCHEMA_ID,
        "client_request_id": client_request_id,
        "preflight_id": preflight_id,
        "source_set_id": source_set_id,
        "material_preview_id": material_preview_id,
        "material_preview_hash": material_preview_hash,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
    }


def gate_b_idempotency_from_session(session: L3Session) -> dict[str, Any] | None:
    context = session.operator_context_json or {}
    record = context.get(GATE_B_IDEMPOTENCY_CONTEXT_KEY)
    if not isinstance(record, dict):
        return None
    if record.get("schema_id") != GATE_B_IDEMPOTENCY_SCHEMA_ID:
        return None
    return record


def find_gate_b_idempotency_session(
    db: Session,
    *,
    client_request_id: str,
) -> tuple[L3Session, dict[str, Any]] | None:
    if not client_request_id:
        return None
    query = db.query(L3Session).order_by(L3Session.created_at.desc(), L3Session.session_id.desc())
    for session in query.yield_per(100):
        record = gate_b_idempotency_from_session(session)
        if record is not None and str(record.get("client_request_id") or "") == client_request_id:
            return session, record
    return None
