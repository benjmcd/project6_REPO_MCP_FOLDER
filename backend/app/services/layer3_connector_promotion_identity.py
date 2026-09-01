"""Durable, server-derived identity arbitration for connector Gate-B promotion."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ConnectorRun,
    ConnectorRunTarget,
    L3ConnectorPromotionReceipt,
    L3ConnectorSourceIntakeRecord,
    L3MaterialSnapshot,
    L3SelectionManifest,
    L3Session,
    uuid_str,
)
from app.services.layer3_connector_source_intake import (
    ADOPTED_EXTERNAL_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX,
    ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
    ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY,
    CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX,
    CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION,
    CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY,
    ConnectorSourceIntakeError,
    _storage_path_from_ref,
    validate_adopted_external_carrier,
    validate_connector_intake_gate_b_decision_basis,
)
from app.services.layer3_gate_b_state import gate_b_decision_manifest_id


IDENTITY_METADATA_HASH_VERSION = "layer3.connector_source_intake.identity_metadata.v1"
IDENTITY_KEY_SCHEMA_ID = "layer3.connector_promotion_identity_key.v1"
RECEIPT_SCHEMA_VERSION = "layer3.connector_promotion_receipt.v1"
RECEIPT_BASIS_SCHEMA_ID = "layer3.connector_promotion_receipt_basis.v1"
_LOCK_MARKER = "layer3_connector_promotion_identity_lock"
_GLOBAL_ADVISORY_LOCK_KEY = 7_264_951_187_230_001_319


class ConnectorPromotionIdentityError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CandidateIdentity:
    connector_source_intake_record_id: str
    identity_metadata_hash_version: str
    source_family: str
    content_sha256: str
    identity_metadata_hash: str
    canonical_identity_key_hash: str


@dataclass(frozen=True)
class PromotionArbitration:
    identity: CandidateIdentity
    record: L3ConnectorSourceIntakeRecord
    decision: Mapping[str, Any]


def acquire_identity_lock(db: Session) -> None:
    """Acquire one conservative A0 transaction lock before writer-session reads."""
    if db.info.get(_LOCK_MARKER) is True:
        return
    if db.in_transaction():
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_lock_unavailable",
            "Connector promotion identity lock is unavailable.",
        )
    dialect = db.get_bind().dialect.name
    try:
        if dialect == "sqlite":
            db.execute(text("PRAGMA busy_timeout=250"))
            db.execute(text("BEGIN IMMEDIATE"))
        elif dialect == "postgresql":
            db.execute(text("SET LOCAL lock_timeout='250ms'"))
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _GLOBAL_ADVISORY_LOCK_KEY},
            )
        else:
            raise ConnectorPromotionIdentityError(
                "connector_promotion_identity_lock_unavailable",
                "Connector promotion identity lock is unavailable.",
            )
    except DBAPIError as exc:
        db.rollback()
        db.info.pop(_LOCK_MARKER, None)
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_lock_unavailable",
            "Connector promotion identity lock is unavailable.",
        ) from exc
    db.info[_LOCK_MARKER] = True


def release_identity_lock_marker(db: Session) -> None:
    db.info.pop(_LOCK_MARKER, None)


def identity_lock_active(db: Session) -> bool:
    return db.info.get(_LOCK_MARKER) is True


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_prefixes() -> tuple[str, ...]:
    # Parse-then-gate design (deliberate): this promotion-side recognizer is flag-gated,
    # while the intake and source-boundary candidate-id parsers recognize the adopt prefix
    # unconditionally. Admission is enforced flag-gated deeper (_server_rows / _assert_record_admitted
    # / record_adopted_external_source_intake), so no adopt material is admitted when the flag is off.
    # The only flags-off observable difference vs. pre-adopt is that a *nonexistent* adopt-prefixed
    # candidate id surfaces as 404 record-not-found rather than 400 not-admitted — harmless, no leak.
    prefixes = [CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX]
    if settings.layer3_adopted_external_source_intake_enabled:
        prefixes.append(ADOPTED_EXTERNAL_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX)
    return tuple(prefixes)


def _candidate_prefix(record: L3ConnectorSourceIntakeRecord) -> str:
    if record.source_family == ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY:
        return ADOPTED_EXTERNAL_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX
    return CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX


def _record_id(candidate: Mapping[str, Any]) -> str:
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    for prefix in _candidate_prefixes():
        if candidate_id.startswith(prefix):
            record_id = candidate_id[len(prefix) :].strip()
            if record_id:
                return record_id
    raise ConnectorPromotionIdentityError(
        "connector_promotion_not_eligible",
        "Connector promotion candidate is not eligible.",
    )


def possible_exact_candidate(raw_decisions: object) -> Mapping[str, Any] | None:
    if not isinstance(raw_decisions, list):
        return None
    connector_decisions = [
        decision
        for decision in raw_decisions
        if isinstance(decision, Mapping)
        and any(
            str(decision.get("candidate_id") or "").strip().startswith(prefix)
            for prefix in _candidate_prefixes()
        )
    ]
    if not connector_decisions:
        return None
    if len(raw_decisions) != 1 or len(connector_decisions) != 1:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_invalid_shape",
            "Connector promotion requires exactly one connector-intake candidate decision.",
        )
    return connector_decisions[0]


def _server_rows(
    db: Session,
    record_id: str,
) -> tuple[L3ConnectorSourceIntakeRecord, ConnectorRun, ConnectorRunTarget]:
    record = db.get(L3ConnectorSourceIntakeRecord, record_id)
    run = db.get(ConnectorRun, record.connector_run_id) if record is not None else None
    target = db.get(ConnectorRunTarget, record.connector_run_target_id) if record is not None else None
    connector_family_eligible = bool(
        record is not None
        and record.operator_decision == CONNECTOR_SOURCE_INTAKE_OPERATOR_DECISION
        and record.source_family == CONNECTOR_SOURCE_INTAKE_SOURCE_FAMILY
    )
    adopted_family_eligible = bool(
        settings.layer3_adopted_external_source_intake_enabled
        and record is not None
        and record.operator_decision
        == ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION
        and record.source_family == ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY
    )
    eligible = bool(
        record is not None
        and run is not None
        and target is not None
        and record.status == "recorded"
        and (connector_family_eligible or adopted_family_eligible)
        and record.connector_run_id == run.connector_run_id
        and record.connector_run_target_id == target.connector_run_target_id
        and record.connector_key == run.connector_key
        and target.connector_run_id == run.connector_run_id
        and target.status == "downloaded"
        and target.public_read_confirmed is True
        and target.downloaded_sha256 == record.content_sha256
        and target.raw_storage_ref == record.storage_ref
        and bool(str(target.sciencebase_item_id or "").strip())
        and str(record.media_type or "").split(";", 1)[0].strip().lower() == "text/csv"
    )
    if not eligible:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_not_eligible",
            "Connector promotion candidate is not eligible.",
        )
    assert record is not None and run is not None and target is not None
    if adopted_family_eligible:
        adoption_provenance = (record.provenance_json or {}).get(
            "adoption_provenance"
        )
        if not isinstance(adoption_provenance, Mapping):
            raise ConnectorPromotionIdentityError(
                "connector_promotion_not_eligible",
                "Connector promotion candidate is not eligible.",
            )
        try:
            validate_adopted_external_carrier(
                run,
                target,
                adoption_provenance=adoption_provenance,
            )
        except ConnectorSourceIntakeError as exc:
            raise ConnectorPromotionIdentityError(
                "connector_promotion_not_eligible",
                "Connector promotion candidate is not eligible.",
            ) from exc
    try:
        storage_path = _storage_path_from_ref(record.storage_ref)
        if not storage_path.is_file():
            raise OSError("missing source object")
        raw_bytes = Path(storage_path).read_bytes()
    except (OSError, ValueError) as exc:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_not_eligible",
            "Connector promotion candidate is not eligible.",
        ) from exc
    if len(raw_bytes) != record.content_size_bytes or hashlib.sha256(raw_bytes).hexdigest() != record.content_sha256:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_not_eligible",
            "Connector promotion candidate is not eligible.",
        )
    return record, run, target


def derive_candidate_identity(db: Session, candidate: Mapping[str, Any]) -> CandidateIdentity:
    record_id = _record_id(candidate)
    record, run, target = _server_rows(db, record_id)
    expected_candidate_id = f"{_candidate_prefix(record)}{record_id}"
    if str(candidate.get("candidate_id") or "").strip() != expected_candidate_id:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_not_eligible",
            "Connector promotion candidate is not eligible.",
        )
    metadata_hash = _stable_hash(
        {
            "fields": {
                "connector_key": run.connector_key,
                "media_type": str(record.media_type or "").strip().lower(),
                "sciencebase_item_id": str(target.sciencebase_item_id).strip(),
            },
            "schema_id": IDENTITY_METADATA_HASH_VERSION,
        }
    )
    canonical_hash = _stable_hash(
        {
            "fields": {
                "content_sha256": record.content_sha256,
                "identity_metadata_hash": metadata_hash,
                "identity_metadata_hash_version": IDENTITY_METADATA_HASH_VERSION,
                "source_family": record.source_family,
            },
            "schema_id": IDENTITY_KEY_SCHEMA_ID,
        }
    )
    return CandidateIdentity(
        connector_source_intake_record_id=record_id,
        identity_metadata_hash_version=IDENTITY_METADATA_HASH_VERSION,
        source_family=record.source_family,
        content_sha256=record.content_sha256,
        identity_metadata_hash=metadata_hash,
        canonical_identity_key_hash=canonical_hash,
    )


def begin_arbitration(db: Session, decision: Mapping[str, Any]) -> PromotionArbitration:
    if db.info.get(_LOCK_MARKER) is not True:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_lock_unavailable",
            "Connector promotion identity lock is unavailable.",
        )
    identity = derive_candidate_identity(db, decision)
    record = db.get(L3ConnectorSourceIntakeRecord, identity.connector_source_intake_record_id)
    assert record is not None
    existing = (
        db.query(L3ConnectorPromotionReceipt)
        .filter(
            L3ConnectorPromotionReceipt.canonical_identity_key_hash
            == identity.canonical_identity_key_hash
        )
        .one_or_none()
    )
    if existing is not None:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_conflict",
            "Connector promotion identity already has a distinct durable request.",
        )
    basis = decision.get("decision_basis")
    if decision.get("decision") != "approved" or not isinstance(basis, Mapping):
        raise ConnectorPromotionIdentityError(
            "connector_promotion_not_eligible",
            "Connector promotion candidate is not eligible.",
        )
    try:
        validate_connector_intake_gate_b_decision_basis(
            db,
            candidate_id=str(decision.get("candidate_id") or ""),
            decision_basis=basis,
        )
    except ConnectorSourceIntakeError as exc:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_not_eligible",
            "Connector promotion candidate is not eligible.",
        ) from exc
    expected_pair = (identity.identity_metadata_hash_version, identity.identity_metadata_hash)
    current_pair = (record.identity_metadata_hash_version, record.identity_metadata_hash)
    if current_pair not in {(None, None), expected_pair}:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_conflict",
            "Connector promotion identity conflicts with durable state.",
        )
    return PromotionArbitration(identity=identity, record=record, decision=decision)


def _receipt_result(receipt: L3ConnectorPromotionReceipt, disposition: str) -> dict[str, str]:
    return {
        "receipt_disposition": disposition,
        "connector_promotion_receipt_id": receipt.connector_promotion_receipt_id,
        "canonical_identity_key_hash": receipt.canonical_identity_key_hash,
    }


def _approval_hash(identity: CandidateIdentity) -> str:
    return _stable_hash(
        {
            "decision": "approved",
            "identity": identity.__dict__,
            "schema_id": "layer3.connector_promotion_decision_semantics.v1",
        }
    )


def _promotion_basis_hash(
    identity: CandidateIdentity,
    *,
    approval_hash: str,
    session_id: str,
    manifest_id: str,
    snapshot_id: str,
    decision_manifest_id: str,
    decision_manifest_hash: str,
    material_preview_hash: str,
) -> str:
    return _stable_hash(
        {
            "approval_hash": approval_hash,
            "gate_b": {
                "decision_manifest_hash": decision_manifest_hash,
                "decision_manifest_id": decision_manifest_id,
                "material_preview_hash": material_preview_hash,
                "material_snapshot_id": snapshot_id,
                "selection_manifest_id": manifest_id,
                "session_id": session_id,
            },
            "identity": identity.__dict__,
            "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
            "schema_id": RECEIPT_BASIS_SCHEMA_ID,
        }
    )


def replay_result(db: Session, *, session_id: str) -> dict[str, str]:
    receipts = (
        db.query(L3ConnectorPromotionReceipt)
        .filter(L3ConnectorPromotionReceipt.gate_b_session_id == session_id)
        .all()
    )
    if len(receipts) != 1:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_conflict",
            "Connector promotion replay does not match one durable receipt.",
        )
    receipt = receipts[0]
    session = db.get(L3Session, receipt.gate_b_session_id)
    manifest = db.get(L3SelectionManifest, receipt.gate_b_selection_manifest_id)
    snapshot = db.get(L3MaterialSnapshot, receipt.gate_b_material_snapshot_id)
    record = db.get(L3ConnectorSourceIntakeRecord, receipt.connector_source_intake_record_id)
    if session is None or manifest is None or snapshot is None or record is None:
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_conflict",
            "Connector promotion replay conflicts with durable receipt state.",
        )
    candidate = {
        "candidate_id": (
            f"{_candidate_prefix(record)}"
            f"{receipt.connector_source_intake_record_id}"
        )
    }
    identity = derive_candidate_identity(db, candidate)
    context = session.operator_context_json if isinstance(session.operator_context_json, Mapping) else {}
    decision_manifest = context.get("layer3_gate_b_decision_manifest_v1")
    if not isinstance(decision_manifest, Mapping):
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_conflict",
            "Connector promotion replay conflicts with durable receipt state.",
        )
    decision_hash = _stable_hash(decision_manifest)
    decision_id = gate_b_decision_manifest_id(dict(decision_manifest))
    approval_hash = _approval_hash(identity)
    basis_hash = _promotion_basis_hash(
        identity,
        approval_hash=approval_hash,
        session_id=session.session_id,
        manifest_id=manifest.selection_manifest_id,
        snapshot_id=snapshot.material_snapshot_id,
        decision_manifest_id=receipt.gate_b_decision_manifest_id,
        decision_manifest_hash=decision_hash,
        material_preview_hash=receipt.material_preview_hash,
    )
    if (
        receipt.receipt_schema_version != RECEIPT_SCHEMA_VERSION
        or receipt.identity_metadata_hash_version != identity.identity_metadata_hash_version
        or receipt.source_family != identity.source_family
        or receipt.content_sha256 != identity.content_sha256
        or receipt.identity_metadata_hash != identity.identity_metadata_hash
        or receipt.canonical_identity_key_hash != identity.canonical_identity_key_hash
        or session.session_id != session_id
        or session.selection_manifest_id != manifest.selection_manifest_id
        or manifest.session_id != session.session_id
        or snapshot.session_id != session.session_id
        or receipt.gate_b_decision_manifest_id != decision_id
        or receipt.gate_b_decision_manifest_hash != decision_hash
        or receipt.approval_hash != approval_hash
        or receipt.promotion_basis_hash != basis_hash
        or (record.identity_metadata_hash_version, record.identity_metadata_hash)
        != (identity.identity_metadata_hash_version, identity.identity_metadata_hash)
    ):
        raise ConnectorPromotionIdentityError(
            "connector_promotion_identity_conflict",
            "Connector promotion replay conflicts with durable receipt state.",
        )
    return _receipt_result(receipt, "reused")


def stage_promotion_receipt(
    db: Session,
    arbitration: PromotionArbitration,
    *,
    session: L3Session,
    manifest: L3SelectionManifest,
    snapshot: L3MaterialSnapshot,
    decision_manifest: Mapping[str, Any],
    decision_manifest_id: str,
    material_preview_hash: str,
) -> dict[str, str]:
    identity = arbitration.identity
    decision_manifest_hash = _stable_hash(decision_manifest)
    approval_hash = _approval_hash(identity)
    basis_hash = _promotion_basis_hash(
        identity,
        approval_hash=approval_hash,
        session_id=session.session_id,
        manifest_id=manifest.selection_manifest_id,
        snapshot_id=snapshot.material_snapshot_id,
        decision_manifest_id=decision_manifest_id,
        decision_manifest_hash=decision_manifest_hash,
        material_preview_hash=material_preview_hash,
    )
    receipt = L3ConnectorPromotionReceipt(
        connector_promotion_receipt_id=uuid_str(),
        receipt_schema_version=RECEIPT_SCHEMA_VERSION,
        identity_metadata_hash_version=identity.identity_metadata_hash_version,
        source_family=identity.source_family,
        content_sha256=identity.content_sha256,
        identity_metadata_hash=identity.identity_metadata_hash,
        canonical_identity_key_hash=identity.canonical_identity_key_hash,
        connector_source_intake_record_id=identity.connector_source_intake_record_id,
        gate_b_session_id=session.session_id,
        gate_b_selection_manifest_id=manifest.selection_manifest_id,
        gate_b_material_snapshot_id=snapshot.material_snapshot_id,
        gate_b_decision_manifest_id=decision_manifest_id,
        gate_b_decision_manifest_hash=decision_manifest_hash,
        material_preview_hash=material_preview_hash,
        approval_hash=approval_hash,
        promotion_basis_hash=basis_hash,
    )
    arbitration.record.identity_metadata_hash_version = identity.identity_metadata_hash_version
    arbitration.record.identity_metadata_hash = identity.identity_metadata_hash
    db.add(receipt)
    db.flush()
    return _receipt_result(receipt, "created")
