from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED,
    L3_GATE_B_IDEMPOTENCY_STATUS_COMMITTED,
    L3GateBIdempotencyKey,
    L3SelectionManifest,
    L3Session,
)
from app.services.layer3_utils import stable_hash, utcnow

GATE_B_IDEMPOTENCY_SCHEMA_ID = "layer3.gate_b_idempotency.v1"
GATE_B_IDEMPOTENCY_CONTEXT_KEY = "layer3_gate_b_idempotency_v1"
GATE_B_IDEMPOTENCY_STATUS_CLAIMED = L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED
GATE_B_IDEMPOTENCY_STATUS_COMMITTED = L3_GATE_B_IDEMPOTENCY_STATUS_COMMITTED


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


def gate_b_idempotency_request_hash(
    *,
    client_request_id: str,
    preflight_id: str,
    source_set_id: str,
    material_preview_id: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> str:
    return stable_hash(
        {
            "schema_id": GATE_B_IDEMPOTENCY_SCHEMA_ID,
            "client_request_id": client_request_id,
            "preflight_id": preflight_id,
            "source_set_id": source_set_id,
            "material_preview_id": material_preview_id,
            "material_preview_hash": material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        }
    )


def gate_b_idempotency_from_session(session: L3Session) -> dict[str, Any] | None:
    context = session.operator_context_json or {}
    record = context.get(GATE_B_IDEMPOTENCY_CONTEXT_KEY)
    if not isinstance(record, dict):
        return None
    if record.get("schema_id") != GATE_B_IDEMPOTENCY_SCHEMA_ID:
        return None
    return record


def find_gate_b_idempotency_claim(
    db: Session,
    *,
    client_request_id: str,
) -> L3GateBIdempotencyKey | None:
    if not client_request_id:
        return None
    return (
        db.query(L3GateBIdempotencyKey)
        .filter(L3GateBIdempotencyKey.client_request_id == client_request_id)
        .one_or_none()
    )


def gate_b_idempotency_claim_matches(
    claim: L3GateBIdempotencyKey,
    *,
    client_request_id: str,
    preflight_id: str,
    source_set_id: str,
    material_preview_id: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> bool:
    return (
        claim.client_request_id == client_request_id
        and claim.preflight_id == preflight_id
        and claim.source_set_id == source_set_id
        and claim.material_preview_id == material_preview_id
        and claim.material_preview_hash == material_preview_hash
        and claim.gate_b_decision_manifest_id == gate_b_decision_manifest_id
        and claim.request_basis_hash
        == gate_b_idempotency_request_hash(
            client_request_id=client_request_id,
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            material_preview_id=material_preview_id,
            material_preview_hash=material_preview_hash,
            gate_b_decision_manifest_id=gate_b_decision_manifest_id,
        )
    )


def claim_gate_b_idempotency(
    db: Session,
    *,
    client_request_id: str,
    preflight_id: str,
    source_set_id: str,
    material_preview_id: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> tuple[L3GateBIdempotencyKey | None, L3GateBIdempotencyKey | None]:
    now = utcnow()
    claim = L3GateBIdempotencyKey(
        client_request_id=client_request_id,
        request_basis_hash=gate_b_idempotency_request_hash(
            client_request_id=client_request_id,
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            material_preview_id=material_preview_id,
            material_preview_hash=material_preview_hash,
            gate_b_decision_manifest_id=gate_b_decision_manifest_id,
        ),
        preflight_id=preflight_id,
        source_set_id=source_set_id,
        material_preview_id=material_preview_id,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
        status=GATE_B_IDEMPOTENCY_STATUS_CLAIMED,
        created_at=now,
        updated_at=now,
    )
    db.add(claim)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return None, find_gate_b_idempotency_claim(db, client_request_id=client_request_id)
    return claim, None


def complete_gate_b_idempotency_claim(
    claim: L3GateBIdempotencyKey,
    *,
    session: L3Session,
    manifest: L3SelectionManifest,
) -> None:
    claim.status = GATE_B_IDEMPOTENCY_STATUS_COMMITTED
    claim.session_id = session.session_id
    claim.selection_manifest_id = manifest.selection_manifest_id
    claim.updated_at = utcnow()


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
