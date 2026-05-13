from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.models import (
    L3ProviderPublicUrlAuditEvent,
    L3ProviderPublicUrlObjectAuthority,
    L3ProviderPublicUrlReceipt,
    L3ProviderPublicUrlRevocation,
    uuid_str,
)


PROVIDER_PUBLIC_URL_STATE_PREPARED = "provider_public_url_prepared"
PROVIDER_PUBLIC_URL_STATE_REVOKED = "provider_public_url_revoked"
PROVIDER_PUBLIC_URL_STATE_EXPIRED = "provider_public_url_expired"
PROVIDER_PUBLIC_URL_REPLAY_POLICY_STATUS_ONLY = "status_only"
PROVIDER_PUBLIC_URL_MAX_TTL_SECONDS = 900
PROVIDER_PUBLIC_URL_REDACTED_MARKER = "provider-public-url:redacted"
PROVIDER_PUBLIC_URL_RECEIPT_ID_PREFIX = "ppub_"


@dataclass(frozen=True)
class ProviderPublicUrlStateError(ValueError):
    error_code: str
    message: str
    status: str = "conflict"
    blocked_fields: tuple[str, ...] = ()
    next_allowed_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderPublicUrlDurableState:
    provider_public_url_receipt_id: str
    provider_public_url_object_authority_id: str
    provider_public_url_prefix: str
    provider_public_url_state: str
    provider_public_url_replay_policy: str
    provider_public_url_revoked: bool
    provider_public_url_audit_event_id: str

    def response_fields(self) -> dict[str, Any]:
        return {
            "provider_public_url_receipt_id": self.provider_public_url_receipt_id,
            "provider_public_url_object_authority_id": self.provider_public_url_object_authority_id,
            "provider_public_url": PROVIDER_PUBLIC_URL_REDACTED_MARKER,
            "provider_public_url_prefix": self.provider_public_url_prefix,
            "provider_public_url_state": self.provider_public_url_state,
            "provider_public_url_replay_policy": self.provider_public_url_replay_policy,
            "provider_public_url_revoked": self.provider_public_url_revoked,
            "provider_public_url_audit_event_id": self.provider_public_url_audit_event_id,
            "raw_public_url_exposed": False,
            "public_url_enabled": False,
        }


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _secret_hash(raw_value: str) -> str:
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def _epoch_to_utc(epoch_seconds: int) -> datetime:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc)


def _normalize_authority_basis(authority_basis: dict[str, Any]) -> dict[str, Any]:
    size_raw = authority_basis.get("source_artifact_size_bytes")
    try:
        size_value = int(size_raw)
    except (TypeError, ValueError):
        size_value = 0
    return {
        "session_id": str(authority_basis.get("session_id") or "").strip(),
        "provider_private_signed_url_receipt_id": str(
            authority_basis.get("provider_private_signed_url_receipt_id") or ""
        ).strip(),
        "external_export_download_record_ref": str(
            authority_basis.get("external_export_download_record_ref") or ""
        ).strip(),
        "export_download_descriptor_ref": str(authority_basis.get("export_download_descriptor_ref") or "").strip(),
        "source_artifact_hash": str(authority_basis.get("source_artifact_hash") or "").strip().lower(),
        "source_artifact_size_bytes": size_value,
    }


def _response_safe_authority_basis(authority_basis: dict[str, Any]) -> dict[str, Any]:
    safe = dict(authority_basis)
    safe["provider_public_url"] = PROVIDER_PUBLIC_URL_REDACTED_MARKER
    safe["raw_public_url_exposed"] = False
    return safe


def _validate_authority_basis(*, authority_basis: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_authority_basis(authority_basis)
    missing = []
    for field_name in (
        "session_id",
        "provider_private_signed_url_receipt_id",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "source_artifact_hash",
    ):
        if not normalized[field_name]:
            missing.append(field_name)
    if normalized["source_artifact_size_bytes"] <= 0:
        missing.append("source_artifact_size_bytes")
    if missing:
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_authority_fields_missing",
            "Provider-public URL durable-state authority is missing required fields.",
            status="invalid",
            blocked_fields=tuple(missing),
            next_allowed_actions=("submit_complete_provider_public_url_authority",),
        )
    if len(normalized["source_artifact_hash"]) != 64 or any(
        character not in "0123456789abcdef" for character in normalized["source_artifact_hash"]
    ):
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_artifact_hash_invalid",
            "source_artifact_hash must be a lowercase SHA-256 hex digest.",
            status="invalid",
            blocked_fields=("source_artifact_hash",),
            next_allowed_actions=("refresh_provider_public_url_authority",),
        )
    return normalized


def _authority_hash(authority_basis: dict[str, Any]) -> str:
    return _canonical_hash(authority_basis)


def _provider_public_object_identity_hash(authority_basis: dict[str, Any]) -> str:
    return _canonical_hash(
        {
            "session_id": authority_basis["session_id"],
            "provider_private_signed_url_receipt_id": authority_basis["provider_private_signed_url_receipt_id"],
            "external_export_download_record_ref": authority_basis["external_export_download_record_ref"],
            "export_download_descriptor_ref": authority_basis["export_download_descriptor_ref"],
            "source_artifact_hash": authority_basis["source_artifact_hash"],
            "source_artifact_size_bytes": authority_basis["source_artifact_size_bytes"],
        }
    )


def _request_basis_hash(
    *,
    authority_hash: str,
    client_request_id: str,
    recipient_scope: str,
    requested_ttl_seconds: int,
) -> str:
    return _canonical_hash(
        {
            "authority_hash": authority_hash,
            "client_request_id": client_request_id,
            "recipient_scope": recipient_scope,
            "requested_ttl_seconds": requested_ttl_seconds,
        }
    )


def _receipt_id_from_request_basis(*, request_basis_hash: str) -> str:
    return f"{PROVIDER_PUBLIC_URL_RECEIPT_ID_PREFIX}{request_basis_hash[:31]}"


def _state_from_rows(receipt: L3ProviderPublicUrlReceipt, audit: L3ProviderPublicUrlAuditEvent) -> ProviderPublicUrlDurableState:
    return ProviderPublicUrlDurableState(
        provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
        provider_public_url_object_authority_id=receipt.provider_public_url_object_authority_id,
        provider_public_url_prefix=receipt.provider_public_url_prefix,
        provider_public_url_state=receipt.provider_public_url_state,
        provider_public_url_replay_policy=receipt.provider_public_url_replay_policy,
        provider_public_url_revoked=receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_REVOKED,
        provider_public_url_audit_event_id=audit.provider_public_url_audit_event_id,
    )


def _authority_by_hash(db: Session, *, authority_hash: str) -> L3ProviderPublicUrlObjectAuthority | None:
    return (
        db.query(L3ProviderPublicUrlObjectAuthority)
        .filter(L3ProviderPublicUrlObjectAuthority.authority_hash == authority_hash)
        .with_for_update()
        .one_or_none()
    )


def _get_or_create_authority(
    db: Session,
    *,
    normalized_authority: dict[str, Any],
    authority_hash: str,
    provider_public_object_identity_hash: str,
    now: datetime,
) -> L3ProviderPublicUrlObjectAuthority:
    authority = _authority_by_hash(db, authority_hash=authority_hash)
    if authority is not None:
        return authority
    authority = L3ProviderPublicUrlObjectAuthority(
        provider_public_url_object_authority_id=uuid_str(),
        session_id=normalized_authority["session_id"],
        provider_private_signed_url_receipt_id=normalized_authority["provider_private_signed_url_receipt_id"],
        external_export_download_record_ref=normalized_authority["external_export_download_record_ref"],
        export_download_descriptor_ref=normalized_authority["export_download_descriptor_ref"],
        source_artifact_hash=normalized_authority["source_artifact_hash"],
        source_artifact_size_bytes=normalized_authority["source_artifact_size_bytes"],
        authority_hash=authority_hash,
        authority_snapshot_json=_response_safe_authority_basis(normalized_authority),
        provider_public_object_identity_hash=provider_public_object_identity_hash,
        created_at=now,
    )
    db.add(authority)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        authority = _authority_by_hash(db, authority_hash=authority_hash)
        if authority is None:
            raise
    return authority


def record_prepared_provider_public_url_receipt(
    db: Session,
    *,
    request_id: str,
    client_request_id: str,
    authority_basis: dict[str, Any],
    recipient_scope: str,
    requested_ttl_seconds: int,
    now_epoch: int,
    provider_public_url: str,
) -> ProviderPublicUrlDurableState:
    if not client_request_id.strip():
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_client_request_id_required",
            "client_request_id is required.",
            status="invalid",
            blocked_fields=("client_request_id",),
            next_allowed_actions=("submit_provider_public_url_client_request_id",),
        )
    if not recipient_scope.strip():
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_recipient_scope_required",
            "recipient_scope is required.",
            status="invalid",
            blocked_fields=("recipient_scope",),
            next_allowed_actions=("submit_provider_public_url_recipient_scope",),
        )
    if not provider_public_url.strip():
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_url_required",
            "provider_public_url is required for hashing and redacted durable state.",
            status="invalid",
            blocked_fields=("provider_public_url",),
            next_allowed_actions=("submit_provider_public_url_for_hashing",),
        )
    if requested_ttl_seconds <= 0 or requested_ttl_seconds > PROVIDER_PUBLIC_URL_MAX_TTL_SECONDS:
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the admitted durable-state TTL bound.",
            status="invalid",
            blocked_fields=("requested_ttl_seconds",),
            next_allowed_actions=("submit_bounded_provider_public_url_ttl",),
        )

    now = _epoch_to_utc(now_epoch)
    normalized_client_request_id = client_request_id.strip()
    normalized_recipient_scope = recipient_scope.strip()
    normalized_authority = _validate_authority_basis(authority_basis=authority_basis)
    authority_hash = _authority_hash(normalized_authority)
    object_identity_hash = _provider_public_object_identity_hash(normalized_authority)
    request_basis_hash = _request_basis_hash(
        authority_hash=authority_hash,
        client_request_id=normalized_client_request_id,
        recipient_scope=normalized_recipient_scope,
        requested_ttl_seconds=requested_ttl_seconds,
    )
    receipt_id = _receipt_id_from_request_basis(request_basis_hash=request_basis_hash)
    public_url_hash = _secret_hash(provider_public_url.strip())
    try:
        existing = (
            db.query(L3ProviderPublicUrlReceipt)
            .filter(L3ProviderPublicUrlReceipt.client_request_id == normalized_client_request_id)
            .with_for_update()
            .one_or_none()
        )
        if existing is not None:
            if (
                existing.authority_hash != authority_hash
                or existing.request_basis_hash != request_basis_hash
                or existing.provider_public_url_hash != public_url_hash
            ):
                raise ProviderPublicUrlStateError(
                    "provider_public_url_state_idempotency_conflict",
                    "client_request_id was already used for different provider-public URL authority.",
                    blocked_fields=("client_request_id", "recipient_scope", "requested_ttl_seconds", "source_artifact_hash"),
                    next_allowed_actions=("submit_new_client_request_id",),
                )
            audit = L3ProviderPublicUrlAuditEvent(
                provider_public_url_audit_event_id=uuid_str(),
                provider_public_url_receipt_id=existing.provider_public_url_receipt_id,
                event_type="prepare",
                event_status="accepted",
                request_id=request_id,
                authority_hash=authority_hash,
                reason_code="idempotent_prepare_reused",
                event_payload_json={
                    "provider_public_url_hash": existing.provider_public_url_hash,
                    "provider_public_url_state": existing.provider_public_url_state,
                    "raw_public_url_exposed": False,
                },
                created_at=now,
            )
            db.add(audit)
            db.commit()
            db.refresh(existing)
            db.refresh(audit)
            return _state_from_rows(existing, audit)

        authority = _get_or_create_authority(
            db,
            normalized_authority=normalized_authority,
            authority_hash=authority_hash,
            provider_public_object_identity_hash=object_identity_hash,
            now=now,
        )
        receipt = L3ProviderPublicUrlReceipt(
            provider_public_url_receipt_id=receipt_id,
            provider_public_url_object_authority_id=authority.provider_public_url_object_authority_id,
            client_request_id=normalized_client_request_id,
            recipient_scope=normalized_recipient_scope,
            provider_public_url_state=PROVIDER_PUBLIC_URL_STATE_PREPARED,
            provider_public_url_replay_policy=PROVIDER_PUBLIC_URL_REPLAY_POLICY_STATUS_ONLY,
            provider_public_url_hash=public_url_hash,
            provider_public_url_prefix=public_url_hash[:16],
            provider_public_url_expires_at=_epoch_to_utc(now_epoch + requested_ttl_seconds),
            authority_hash=authority_hash,
            request_basis_hash=request_basis_hash,
            created_by_request_id=request_id,
            created_at=now,
            updated_at=now,
        )
        audit = L3ProviderPublicUrlAuditEvent(
            provider_public_url_audit_event_id=uuid_str(),
            provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
            event_type="prepare",
            event_status="accepted",
            request_id=request_id,
            authority_hash=authority_hash,
            reason_code="generated_after_authority_validation",
            event_payload_json={
                "authority_snapshot": authority.authority_snapshot_json,
                "provider_public_object_identity_hash": object_identity_hash,
                "recipient_scope_hash": _canonical_hash(normalized_recipient_scope),
                "provider_public_url_hash": public_url_hash,
                "provider_public_url": PROVIDER_PUBLIC_URL_REDACTED_MARKER,
                "raw_public_url_exposed": False,
            },
            created_at=now,
        )
        db.add_all([receipt, audit])
        db.commit()
        db.refresh(receipt)
        db.refresh(audit)
        return _state_from_rows(receipt, audit)
    except ProviderPublicUrlStateError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_prepare_persist_failed",
            "Provider-public URL durable-state prepare could not be recorded.",
            blocked_fields=("provider_public_url_receipt_id",),
            next_allowed_actions=("retry_provider_public_url_prepare",),
        ) from exc


def revoke_provider_public_url_receipt(
    db: Session,
    *,
    provider_public_url_receipt_id: str,
    idempotency_key: str,
    revoked_by: str,
    revocation_reason: str,
    now_epoch: int,
    authority_basis: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> ProviderPublicUrlDurableState:
    if not idempotency_key.strip():
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_revocation_idempotency_key_required",
            "idempotency_key is required.",
            status="invalid",
            blocked_fields=("idempotency_key",),
            next_allowed_actions=("submit_revocation_idempotency_key",),
        )
    if not revoked_by.strip():
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_revoked_by_required",
            "revoked_by is required.",
            status="invalid",
            blocked_fields=("revoked_by",),
            next_allowed_actions=("submit_revoked_by",),
        )
    if not revocation_reason.strip():
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_revocation_reason_required",
            "revocation_reason is required.",
            status="invalid",
            blocked_fields=("revocation_reason",),
            next_allowed_actions=("submit_revocation_reason",),
        )

    now = _epoch_to_utc(now_epoch)
    normalized_idempotency_key = idempotency_key.strip()
    normalized_revoked_by = revoked_by.strip()
    revocation_reason_hash = _canonical_hash(revocation_reason.strip())
    try:
        receipt = (
            db.query(L3ProviderPublicUrlReceipt)
            .filter(L3ProviderPublicUrlReceipt.provider_public_url_receipt_id == provider_public_url_receipt_id)
            .with_for_update()
            .one_or_none()
        )
        if receipt is None:
            raise ProviderPublicUrlStateError(
                "provider_public_url_state_not_recorded",
                "Provider-public URL receipt has no durable server-side state.",
                status="not_found",
                blocked_fields=("provider_public_url_receipt_id",),
                next_allowed_actions=("prepare_provider_public_url",),
            )
        if authority_basis is not None:
            normalized_authority = _validate_authority_basis(authority_basis=authority_basis)
            authority_hash = _authority_hash(normalized_authority)
            if receipt.authority_hash != authority_hash:
                audit = L3ProviderPublicUrlAuditEvent(
                    provider_public_url_audit_event_id=uuid_str(),
                    provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
                    event_type="revoke",
                    event_status="rejected",
                    request_id=request_id,
                    authority_hash=authority_hash,
                    reason_code="authority_hash_mismatch",
                    event_payload_json={"recorded_authority_hash": receipt.authority_hash},
                    created_at=now,
                )
                db.add(audit)
                db.commit()
                raise ProviderPublicUrlStateError(
                    "provider_public_url_state_authority_mismatch",
                    "Current artifact authority no longer matches the provider-public URL durable receipt.",
                    blocked_fields=("session_id", "source_artifact_hash", "source_artifact_size_bytes"),
                    next_allowed_actions=("prepare_new_provider_public_url",),
                )
        existing_revocation = (
            db.query(L3ProviderPublicUrlRevocation)
            .filter(
                L3ProviderPublicUrlRevocation.provider_public_url_receipt_id == receipt.provider_public_url_receipt_id,
                L3ProviderPublicUrlRevocation.idempotency_key == normalized_idempotency_key,
            )
            .with_for_update()
            .one_or_none()
        )
        if existing_revocation is not None:
            if (
                existing_revocation.revocation_reason_hash != revocation_reason_hash
                or existing_revocation.revoked_by != normalized_revoked_by
            ):
                audit = L3ProviderPublicUrlAuditEvent(
                    provider_public_url_audit_event_id=uuid_str(),
                    provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
                    event_type="revoke",
                    event_status="rejected",
                    request_id=request_id,
                    authority_hash=receipt.authority_hash,
                    reason_code="revocation_idempotency_conflict",
                    event_payload_json={"incoming_revocation_reason_hash": revocation_reason_hash},
                    created_at=now,
                )
                db.add(audit)
                db.commit()
                raise ProviderPublicUrlStateError(
                    "provider_public_url_state_revocation_idempotency_conflict",
                    "idempotency_key was already used for a different provider-public URL revocation.",
                    blocked_fields=("idempotency_key", "revoked_by", "revocation_reason"),
                    next_allowed_actions=("submit_new_revocation_idempotency_key",),
                )
            audit = L3ProviderPublicUrlAuditEvent(
                provider_public_url_audit_event_id=uuid_str(),
                provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
                event_type="revoke",
                event_status="accepted",
                request_id=request_id,
                authority_hash=receipt.authority_hash,
                reason_code="revocation_idempotent_reused",
                event_payload_json={"revocation_reason_hash": existing_revocation.revocation_reason_hash},
                created_at=now,
            )
            db.add(audit)
            db.commit()
            db.refresh(receipt)
            db.refresh(audit)
            return _state_from_rows(receipt, audit)
        if receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_REVOKED:
            audit = L3ProviderPublicUrlAuditEvent(
                provider_public_url_audit_event_id=uuid_str(),
                provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
                event_type="revoke",
                event_status="rejected",
                request_id=request_id,
                authority_hash=receipt.authority_hash,
                reason_code="already_revoked",
                event_payload_json={},
                created_at=now,
            )
            db.add(audit)
            db.commit()
            raise ProviderPublicUrlStateError(
                "provider_public_url_state_already_revoked",
                "Provider-public URL receipt has already been revoked.",
                blocked_fields=("provider_public_url_receipt_id",),
                next_allowed_actions=("inspect_provider_public_url_status",),
            )

        receipt.provider_public_url_state = PROVIDER_PUBLIC_URL_STATE_REVOKED
        receipt.updated_at = now
        revocation = L3ProviderPublicUrlRevocation(
            provider_public_url_revocation_id=uuid_str(),
            provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
            idempotency_key=normalized_idempotency_key,
            revoked_by=normalized_revoked_by,
            revocation_reason_hash=revocation_reason_hash,
            revocation_payload_json={"revocation_reason_hash": revocation_reason_hash},
            created_at=now,
        )
        audit = L3ProviderPublicUrlAuditEvent(
            provider_public_url_audit_event_id=uuid_str(),
            provider_public_url_receipt_id=receipt.provider_public_url_receipt_id,
            event_type="revoke",
            event_status="accepted",
            request_id=request_id,
            authority_hash=receipt.authority_hash,
            reason_code="revoked_by_operator",
            event_payload_json={"revocation_reason_hash": revocation_reason_hash, "raw_public_url_exposed": False},
            created_at=now,
        )
        db.add_all([revocation, audit])
        db.commit()
        db.refresh(receipt)
        db.refresh(audit)
        return _state_from_rows(receipt, audit)
    except ProviderPublicUrlStateError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise ProviderPublicUrlStateError(
            "provider_public_url_state_revoke_persist_failed",
            "Provider-public URL durable-state revocation could not be recorded.",
            blocked_fields=("provider_public_url_receipt_id",),
            next_allowed_actions=("retry_provider_public_url_revoke",),
        ) from exc
