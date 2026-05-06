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
from app.services.layer3_response_contract import LAYER3_SCHEMA_VERSION as SCHEMA_VERSION
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow

GATE_B_IDEMPOTENCY_SCHEMA_ID = "layer3.gate_b_idempotency.v1"
GATE_B_DECISION_MANIFEST_SCHEMA_ID = "layer3.gate_b_decision_manifest.v1"
MATERIAL_PREVIEW_BASIS_SCHEMA_ID = "layer3.material_preview_basis.v1"
GATE_B_IDEMPOTENCY_CONTEXT_KEY = "layer3_gate_b_idempotency_v1"
GATE_B_IDEMPOTENCY_STATUS_CLAIMED = L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED
GATE_B_IDEMPOTENCY_STATUS_COMMITTED = L3_GATE_B_IDEMPOTENCY_STATUS_COMMITTED
GATE_B_DECISIONS = ("approved", "denied", "isolated", "flagged")


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


def gate_b_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {decision: sum(1 for item in decisions if item["decision"] == decision) for decision in GATE_B_DECISIONS}


def gate_b_summary_from_session(session: L3Session) -> dict[str, int]:
    summary = session.summary_json or {}
    counts = summary.get("gate_b_summary_v1")
    if isinstance(counts, dict):
        return {decision: int(counts.get(decision, 0)) for decision in GATE_B_DECISIONS}
    decisions = ((session.operator_context_json or {}).get("layer3_gate_b_decision_manifest_v1") or {}).get("items") or []
    return gate_b_counts([item for item in decisions if isinstance(item, dict)])


def material_candidate_basis_from_preview(candidate: dict[str, Any]) -> dict[str, str]:
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    source_class = str(candidate.get("source_class") or "").strip()
    return {
        "candidate_id": candidate_id,
        "source_class": source_class,
        "source_ref": str(candidate.get("source_ref") or "").strip(),
        "query_basis": str(candidate.get("query_basis") or "").strip(),
        "provenance_ref": str(candidate.get("provenance_ref") or "").strip(),
    }


def material_candidate_basis_from_decision(
    *, candidate_id: str, source_class: str, decision_basis: dict[str, Any]
) -> dict[str, str]:
    return {
        "candidate_id": candidate_id,
        "source_class": source_class,
        "source_ref": str(decision_basis.get("source_ref") or "").strip(),
        "query_basis": str(decision_basis.get("query_basis") or "").strip(),
        "provenance_ref": str(decision_basis.get("provenance_ref") or "").strip(),
    }


def material_preview_basis(candidate_bases: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_id": MATERIAL_PREVIEW_BASIS_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "items": sorted(json_clone(candidate_bases), key=lambda item: item["candidate_id"]),
    }


def material_preview_hash(candidate_bases: list[dict[str, str]]) -> str:
    return stable_hash(material_preview_basis(candidate_bases))


def candidate_decision_manifest(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(json_clone(decisions), key=lambda item: str(item.get("candidate_id") or ""))
    return {"schema_id": GATE_B_DECISION_MANIFEST_SCHEMA_ID, "schema_version": SCHEMA_VERSION, "items": ordered}


def gate_b_decision_manifest_id(decision_manifest: dict[str, Any]) -> str:
    return stable_id("gate-b", decision_manifest)


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
