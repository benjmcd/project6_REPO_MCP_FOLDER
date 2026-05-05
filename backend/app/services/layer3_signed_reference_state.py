from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.models import (
    L3SignedReferenceAuditEvent,
    L3SignedReferenceReceipt,
    L3SignedReferenceRevocation,
    L3SignedReferenceToken,
    uuid_str,
)


SIGNED_REFERENCE_REPLAY_POLICY_SINGLE_USE = "single_use"
SIGNED_REFERENCE_TOKEN_STATE_READY = "ready"
SIGNED_REFERENCE_TOKEN_STATE_USED = "used"
SIGNED_REFERENCE_TOKEN_STATE_REVOKED = "revoked"
SIGNED_REFERENCE_TOKEN_STATE_EXPIRED = "expired"
INTERNAL_ARTIFACT_REF_PLACEHOLDER = "internal_artifact_ref_bound_by_hash"


@dataclass(frozen=True)
class SignedReferenceStateError(ValueError):
    error_code: str
    message: str
    status: str = "conflict"
    http_status: int = 409
    blocked_fields: list[str] = field(default_factory=list)
    next_allowed_actions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SignedReferenceDurableState:
    signed_reference_token_id: str
    signed_reference_token_prefix: str
    signed_reference_receipt_id: str
    signed_reference_replay_policy: str
    signed_reference_use_count: int
    signed_reference_max_use_count: int
    signed_reference_revoked: bool
    signed_reference_audit_event_id: str

    def response_fields(self) -> dict[str, Any]:
        return {
            "signed_reference_token_id": self.signed_reference_token_id,
            "signed_reference_token_prefix": self.signed_reference_token_prefix,
            "signed_reference_receipt_id": self.signed_reference_receipt_id,
            "signed_reference_replay_policy": self.signed_reference_replay_policy,
            "signed_reference_use_count": self.signed_reference_use_count,
            "signed_reference_max_use_count": self.signed_reference_max_use_count,
            "signed_reference_revoked": self.signed_reference_revoked,
            "signed_reference_audit_event_id": self.signed_reference_audit_event_id,
        }


def hash_signed_reference_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _epoch_to_utc(epoch_seconds: int) -> datetime:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _artifact_receipt_payload(*, authority_basis: dict[str, Any], token_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": token_body.get("schema_id"),
        "schema_version": token_body.get("schema_version"),
        "delivery_authority": _response_safe_authority_basis(authority_basis),
        "expires_at_epoch": token_body.get("expires_at_epoch"),
        "process_restart_invalidates_existing_tokens": False,
    }


def _response_safe_authority_basis(authority_basis: dict[str, Any]) -> dict[str, Any]:
    internal_artifact_ref = authority_basis.get("source_artifact_ref")

    def make_response_safe(value: Any) -> Any:
        if internal_artifact_ref and value == internal_artifact_ref:
            return INTERNAL_ARTIFACT_REF_PLACEHOLDER
        if isinstance(value, dict):
            return {key: make_response_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [make_response_safe(item) for item in value]
        return value

    return make_response_safe(authority_basis)


def _token_revoked(db: Session, token_id: str) -> bool:
    return (
        db.query(L3SignedReferenceRevocation)
        .filter(L3SignedReferenceRevocation.signed_reference_token_id == token_id)
        .first()
        is not None
    )


def _state_from_token(token_row: L3SignedReferenceToken, receipt: L3SignedReferenceReceipt, audit: L3SignedReferenceAuditEvent) -> SignedReferenceDurableState:
    return SignedReferenceDurableState(
        signed_reference_token_id=token_row.signed_reference_token_id,
        signed_reference_token_prefix=token_row.token_prefix,
        signed_reference_receipt_id=receipt.signed_reference_receipt_id,
        signed_reference_replay_policy=token_row.replay_policy,
        signed_reference_use_count=token_row.use_count,
        signed_reference_max_use_count=token_row.max_use_count,
        signed_reference_revoked=token_row.state == SIGNED_REFERENCE_TOKEN_STATE_REVOKED,
        signed_reference_audit_event_id=audit.signed_reference_audit_event_id,
    )


def record_generated_signed_reference(
    db: Session,
    *,
    raw_token: str,
    token_body: dict[str, Any],
    request_id: str,
    payload: dict[str, Any],
    authority_basis: dict[str, Any],
) -> SignedReferenceDurableState:
    token_hash = hash_signed_reference_token(raw_token)
    authority_hash = _canonical_hash(authority_basis)
    expires_at_epoch = int(token_body["expires_at_epoch"])
    request_basis_hash = _canonical_hash(
        {
            "authority_hash": authority_hash,
            "expires_at_epoch": expires_at_epoch,
            "request_id": request_id,
            "schema_id": token_body.get("schema_id"),
            "token_hash": token_hash,
        }
    )
    now = _utcnow()
    artifact_ref = str(authority_basis.get("source_artifact_ref") or "")
    artifact_hash = str(authority_basis.get("source_artifact_hash") or "")
    artifact_size = int(authority_basis.get("source_artifact_size_bytes") or 0)
    try:
        existing = (
            db.query(L3SignedReferenceToken)
            .filter(L3SignedReferenceToken.token_hash == token_hash)
            .with_for_update()
            .one_or_none()
        )
        if existing is None:
            existing = L3SignedReferenceToken(
                signed_reference_token_id=uuid_str(),
                session_id=str(payload["session_id"]),
                reconciliation_record_id=str(payload["reconciliation_record_id"]),
                token_hash=token_hash,
                token_prefix=token_hash[:16],
                state=SIGNED_REFERENCE_TOKEN_STATE_READY,
                replay_policy=SIGNED_REFERENCE_REPLAY_POLICY_SINGLE_USE,
                max_use_count=1,
                use_count=0,
                expires_at=_epoch_to_utc(expires_at_epoch),
                authority_hash=authority_hash,
                authority_snapshot_json=_response_safe_authority_basis(authority_basis),
                request_basis_hash=request_basis_hash,
                created_by_request_id=request_id,
                created_at=now,
                updated_at=now,
            )
            db.add(existing)
            db.flush()
        elif existing.authority_hash != authority_hash or existing.request_basis_hash != request_basis_hash:
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_state_mismatch",
                "Existing durable signed-reference state does not match the generated reference authority.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )
        elif existing.state != SIGNED_REFERENCE_TOKEN_STATE_READY or existing.use_count >= existing.max_use_count:
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_replay_denied",
                "Existing durable signed-reference token state is already terminal for this generation basis.",
                blocked_fields=["client_request_id"],
                next_allowed_actions=["submit_new_external_export_download_signed_reference_request"],
            )

        receipt = L3SignedReferenceReceipt(
            signed_reference_receipt_id=uuid_str(),
            signed_reference_token_id=existing.signed_reference_token_id,
            receipt_type="generated",
            receipt_status="generated",
            request_id=request_id,
            authority_hash=authority_hash,
            artifact_ref=artifact_ref,
            artifact_hash=artifact_hash,
            artifact_size_bytes=artifact_size,
            receipt_payload_json=_artifact_receipt_payload(authority_basis=authority_basis, token_body=token_body),
            created_at=now,
        )
        audit = L3SignedReferenceAuditEvent(
            signed_reference_audit_event_id=uuid_str(),
            signed_reference_token_id=existing.signed_reference_token_id,
            event_type="generate",
            event_status="accepted",
            request_id=request_id,
            authority_hash=authority_hash,
            reason_code="generated_after_delivery_authority_validation",
            event_payload_json=receipt.receipt_payload_json,
            created_at=now,
        )
        db.add_all([receipt, audit])
        db.commit()
        db.refresh(existing)
        return _state_from_token(existing, receipt, audit)
    except SignedReferenceStateError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise SignedReferenceStateError(
            "external_export_download_signed_reference_state_persist_failed",
            "Durable signed-reference state could not be recorded.",
            blocked_fields=["signed_reference_token"],
            next_allowed_actions=["retry_external_export_download_signed_reference_generation"],
        ) from exc


def record_used_signed_reference(
    db: Session,
    *,
    raw_token: str,
    token_body: dict[str, Any],
    request_id: str | None,
    authority_basis: dict[str, Any],
    now_epoch: int,
) -> SignedReferenceDurableState:
    token_hash = hash_signed_reference_token(raw_token)
    authority_hash = _canonical_hash(authority_basis)
    now = _epoch_to_utc(now_epoch)
    artifact_ref = str(authority_basis.get("source_artifact_ref") or "")
    artifact_hash = str(authority_basis.get("source_artifact_hash") or "")
    artifact_size = int(authority_basis.get("source_artifact_size_bytes") or 0)
    try:
        token_row = (
            db.query(L3SignedReferenceToken)
            .filter(L3SignedReferenceToken.token_hash == token_hash)
            .with_for_update()
            .one_or_none()
        )
        if token_row is None:
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_state_not_recorded",
                "Signed delivery reference token has no durable server-side state.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )
        if _token_revoked(db, token_row.signed_reference_token_id):
            token_row.state = SIGNED_REFERENCE_TOKEN_STATE_REVOKED
        if token_row.state == SIGNED_REFERENCE_TOKEN_STATE_REVOKED:
            audit = L3SignedReferenceAuditEvent(
                signed_reference_audit_event_id=uuid_str(),
                signed_reference_token_id=token_row.signed_reference_token_id,
                event_type="use",
                event_status="rejected",
                request_id=request_id,
                authority_hash=authority_hash,
                reason_code="token_revoked",
                event_payload_json={},
                created_at=now,
            )
            db.add(audit)
            db.commit()
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_revoked",
                "Signed delivery reference token has been revoked.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )
        if token_row.authority_hash != authority_hash:
            audit = L3SignedReferenceAuditEvent(
                signed_reference_audit_event_id=uuid_str(),
                signed_reference_token_id=token_row.signed_reference_token_id,
                event_type="use",
                event_status="rejected",
                request_id=request_id,
                authority_hash=authority_hash,
                reason_code="authority_hash_mismatch",
                event_payload_json={"recorded_authority_hash": token_row.authority_hash},
                created_at=now,
            )
            db.add(audit)
            db.commit()
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_authority_mismatch",
                "Durable signed-reference authority no longer matches the current delivery authority.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )
        if now >= _as_utc(token_row.expires_at):
            token_row.state = SIGNED_REFERENCE_TOKEN_STATE_EXPIRED
            token_row.updated_at = now
            audit = L3SignedReferenceAuditEvent(
                signed_reference_audit_event_id=uuid_str(),
                signed_reference_token_id=token_row.signed_reference_token_id,
                event_type="use",
                event_status="rejected",
                request_id=request_id,
                authority_hash=authority_hash,
                reason_code="token_expired",
                event_payload_json={"expires_at": _as_utc(token_row.expires_at).isoformat()},
                created_at=now,
            )
            db.add(audit)
            db.commit()
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_expired",
                "Signed delivery reference token has expired in durable server-side state.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )
        if token_row.use_count >= token_row.max_use_count or token_row.state == SIGNED_REFERENCE_TOKEN_STATE_USED:
            audit = L3SignedReferenceAuditEvent(
                signed_reference_audit_event_id=uuid_str(),
                signed_reference_token_id=token_row.signed_reference_token_id,
                event_type="use",
                event_status="rejected",
                request_id=request_id,
                authority_hash=authority_hash,
                reason_code="single_use_replay_denied",
                event_payload_json={"use_count": token_row.use_count, "max_use_count": token_row.max_use_count},
                created_at=now,
            )
            db.add(audit)
            db.commit()
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_replay_denied",
                "Signed delivery reference token has already been used.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )

        consumed = (
            db.query(L3SignedReferenceToken)
            .filter(
                L3SignedReferenceToken.signed_reference_token_id == token_row.signed_reference_token_id,
                L3SignedReferenceToken.state == SIGNED_REFERENCE_TOKEN_STATE_READY,
                L3SignedReferenceToken.use_count < L3SignedReferenceToken.max_use_count,
            )
            .update(
                {
                    L3SignedReferenceToken.use_count: L3SignedReferenceToken.use_count + 1,
                    L3SignedReferenceToken.state: SIGNED_REFERENCE_TOKEN_STATE_USED,
                    L3SignedReferenceToken.last_used_at: now,
                    L3SignedReferenceToken.updated_at: now,
                },
                synchronize_session=False,
            )
        )
        if consumed != 1:
            db.rollback()
            audit = L3SignedReferenceAuditEvent(
                signed_reference_audit_event_id=uuid_str(),
                signed_reference_token_id=token_row.signed_reference_token_id,
                event_type="use",
                event_status="rejected",
                request_id=request_id,
                authority_hash=authority_hash,
                reason_code="single_use_replay_denied",
                event_payload_json={
                    "use_count": token_row.use_count,
                    "max_use_count": token_row.max_use_count,
                },
                created_at=now,
            )
            db.add(audit)
            db.commit()
            raise SignedReferenceStateError(
                "external_export_download_signed_reference_replay_denied",
                "Signed delivery reference token has already been used.",
                blocked_fields=["signed_reference_token"],
                next_allowed_actions=["regenerate_external_export_download_signed_reference"],
            )

        db.flush()
        db.refresh(token_row)
        receipt = L3SignedReferenceReceipt(
            signed_reference_receipt_id=uuid_str(),
            signed_reference_token_id=token_row.signed_reference_token_id,
            receipt_type="used",
            receipt_status="delivered",
            request_id=request_id,
            authority_hash=authority_hash,
            artifact_ref=artifact_ref,
            artifact_hash=artifact_hash,
            artifact_size_bytes=artifact_size,
            receipt_payload_json=_artifact_receipt_payload(authority_basis=authority_basis, token_body=token_body),
            created_at=now,
        )
        audit = L3SignedReferenceAuditEvent(
            signed_reference_audit_event_id=uuid_str(),
            signed_reference_token_id=token_row.signed_reference_token_id,
            event_type="use",
            event_status="accepted",
            request_id=request_id,
            authority_hash=authority_hash,
            reason_code="single_use_delivery_accepted",
            event_payload_json=receipt.receipt_payload_json,
            created_at=now,
        )
        db.add_all([receipt, audit])
        db.commit()
        db.refresh(token_row)
        return _state_from_token(token_row, receipt, audit)
    except SignedReferenceStateError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise SignedReferenceStateError(
            "external_export_download_signed_reference_state_persist_failed",
            "Durable signed-reference use state could not be recorded.",
            blocked_fields=["signed_reference_token"],
            next_allowed_actions=["retry_external_export_download_signed_reference_use"],
        ) from exc
