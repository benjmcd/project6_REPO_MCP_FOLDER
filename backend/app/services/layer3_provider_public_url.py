from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ProviderPublicUrlAuditEvent,
    L3ProviderPublicUrlObjectAuthority,
    L3ProviderPublicUrlReceipt,
)
from app.services.layer3_provider_public_url_state import (
    PROVIDER_PUBLIC_URL_MAX_TTL_SECONDS,
    PROVIDER_PUBLIC_URL_REDACTED_MARKER,
    PROVIDER_PUBLIC_URL_REPLAY_POLICY_STATUS_ONLY,
    PROVIDER_PUBLIC_URL_STATE_EXPIRED,
    PROVIDER_PUBLIC_URL_STATE_PREPARED,
    PROVIDER_PUBLIC_URL_STATE_REVOKED,
    ProviderPublicUrlStateError,
    record_prepared_provider_public_url_receipt,
    revoke_provider_public_url_receipt,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_workbench_error import Layer3WorkbenchError


PROVIDER_PUBLIC_URL_PREPARE_SCHEMA_ID = "layer3.provider_public_url.prepare.v1"
PROVIDER_PUBLIC_URL_STATUS_SCHEMA_ID = "layer3.provider_public_url.status.v1"
PROVIDER_PUBLIC_URL_REVOKE_SCHEMA_ID = "layer3.provider_public_url.revoke.v1"
PROVIDER_PUBLIC_URL_DELIVERY_MODE = "provider_public_url"
PROVIDER_PUBLIC_URL_OPERATOR_DECISION = "prepare_provider_public_url"
PROVIDER_PUBLIC_URL_REVOKE_OPERATOR_DECISION = "revoke_provider_public_url"
PROVIDER_PUBLIC_URL_DEFAULT_TTL_SECONDS = 300
PROVIDER_PUBLIC_URL_FAKE_PROVIDER_AUTHORITY = "layer3_provider_public_url_fake_provider"

PROVIDER_PUBLIC_URL_PREPARE_ALLOWED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_private_signed_url_receipt_id",
        "recipient_scope",
        "requested_ttl_seconds",
        "delivery_mode",
        "operator_decision",
        "decision_notes",
    }
)
PROVIDER_PUBLIC_URL_PREPARE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_private_signed_url_receipt_id",
        "recipient_scope",
        "delivery_mode",
        "operator_decision",
    }
)
PROVIDER_PUBLIC_URL_REVOKE_ALLOWED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_public_url_receipt_id",
        "idempotency_key",
        "revoked_by",
        "revocation_reason",
        "operator_decision",
        "decision_notes",
    }
)
PROVIDER_PUBLIC_URL_REVOKE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_public_url_receipt_id",
        "idempotency_key",
        "revoked_by",
        "revocation_reason",
        "operator_decision",
    }
)
PROVIDER_PUBLIC_URL_FORBIDDEN_FIELDS = frozenset(
    {
        "provider_public_url",
        "public_url",
        "raw_public_url",
        "public_proxy_url",
        "download_url",
        "signed_url",
        "provider_url",
        "provider_credentials",
        "provider_secret",
        "provider_token",
        "connector_dispatch",
        "connector_run_id",
        "destination_id",
        "destination_url",
        "package_mutation",
        "source_expansion",
        "local_directory",
        "web_connector",
        "rag_vector_state",
        "auth_security_override",
        "browser_durable_authority",
    }
)


def _text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return "" if value is None else str(value).strip()


def _blocked_fields(payload: dict[str, Any], *, allowed_fields: frozenset[str]) -> list[str]:
    return sorted(field for field, value in payload.items() if field not in allowed_fields and value is not None)


def _missing_fields(payload: dict[str, Any], *, required_fields: frozenset[str]) -> list[str]:
    return sorted(field for field in required_fields if not _text(payload, field))


def _ttl_seconds(payload: dict[str, Any]) -> int:
    value = payload.get("requested_ttl_seconds", PROVIDER_PUBLIC_URL_DEFAULT_TTL_SECONDS)
    try:
        ttl = int(value)
    except (TypeError, ValueError) as exc:
        raise Layer3WorkbenchError(
            "provider_public_url_ttl_invalid",
            "requested_ttl_seconds must be an integer.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
            next_allowed_actions=["submit_bounded_provider_public_url_ttl"],
        ) from exc
    if ttl <= 0 or ttl > PROVIDER_PUBLIC_URL_MAX_TTL_SECONDS:
        raise Layer3WorkbenchError(
            "provider_public_url_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the admitted durable-state TTL bound.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
            next_allowed_actions=["submit_bounded_provider_public_url_ttl"],
        )
    return ttl


def _require_prepare_fixed_values(payload: dict[str, Any]) -> None:
    expected = {
        "delivery_mode": PROVIDER_PUBLIC_URL_DELIVERY_MODE,
        "operator_decision": PROVIDER_PUBLIC_URL_OPERATOR_DECISION,
    }
    mismatches = sorted(field for field, expected_value in expected.items() if _text(payload, field) != expected_value)
    if mismatches:
        raise Layer3WorkbenchError(
            "provider_public_url_prepare_fixed_value_mismatch",
            "Provider-public URL prepare request contains non-admitted fixed-value fields.",
            status="invalid",
            blocked_fields=mismatches,
            next_allowed_actions=["submit_provider_public_url_prepare_fixed_values"],
        )


def _require_revoke_fixed_values(payload: dict[str, Any]) -> None:
    if _text(payload, "operator_decision") != PROVIDER_PUBLIC_URL_REVOKE_OPERATOR_DECISION:
        raise Layer3WorkbenchError(
            "provider_public_url_revoke_fixed_value_mismatch",
            "Provider-public URL revoke request contains non-admitted fixed-value fields.",
            status="invalid",
            blocked_fields=["operator_decision"],
            next_allowed_actions=["submit_provider_public_url_revoke_fixed_values"],
        )


def _datetime_epoch(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def _epoch_iso(value: int) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _status_from_receipt(receipt: L3ProviderPublicUrlReceipt, *, now_epoch: int) -> str:
    if (
        receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_PREPARED
        and now_epoch >= _datetime_epoch(receipt.provider_public_url_expires_at)
    ):
        return PROVIDER_PUBLIC_URL_STATE_EXPIRED
    return receipt.provider_public_url_state


def _private_authority_basis(db: Session, *, provider_private_signed_url_receipt_id: str) -> dict[str, Any]:
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, provider_private_signed_url_receipt_id)
    if receipt is None:
        raise Layer3WorkbenchError(
            "provider_public_url_private_receipt_not_found",
            "Provider-private signed URL receipt is required before provider-public URL prepare.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_private_signed_url_receipt_id"],
            next_allowed_actions=["prepare_provider_private_signed_url"],
        )
    if receipt.provider_private_signed_url_state == "provider_private_signed_url_revoked":
        raise Layer3WorkbenchError(
            "provider_public_url_private_receipt_revoked",
            "Provider-private signed URL receipt has been revoked and cannot authorize provider-public URL state.",
            status="conflict",
            blocked_fields=["provider_private_signed_url_receipt_id"],
            next_allowed_actions=["prepare_new_provider_private_signed_url"],
        )
    authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    if authority is None:
        raise Layer3WorkbenchError(
            "provider_public_url_private_authority_missing",
            "Provider-private signed URL authority row is missing.",
            status="conflict",
            blocked_fields=["provider_private_signed_url_receipt_id"],
            next_allowed_actions=["prepare_provider_private_signed_url"],
        )
    return {
        "session_id": authority.session_id,
        "provider_private_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "external_export_download_record_ref": authority.external_export_download_record_ref,
        "export_download_descriptor_ref": authority.export_download_descriptor_ref,
        "source_artifact_hash": authority.source_artifact_hash,
        "source_artifact_size_bytes": authority.source_artifact_size_bytes,
    }


def _fake_public_url(*, authority_basis: dict[str, Any], client_request_id: str) -> str:
    return (
        "https://provider-public.invalid/layer3/"
        f"{authority_basis['provider_private_signed_url_receipt_id']}/"
        f"{authority_basis['source_artifact_hash']}?client_request_id={client_request_id}"
    )


def _state_error_to_workbench(exc: ProviderPublicUrlStateError) -> Layer3WorkbenchError:
    return Layer3WorkbenchError(
        exc.error_code,
        exc.message,
        status=exc.status,
        http_status=404 if exc.status == "not_found" else (400 if exc.status == "invalid" else 409),
        blocked_fields=list(exc.blocked_fields),
        next_allowed_actions=list(exc.next_allowed_actions),
    )


def _audit_receipt(
    *,
    receipt: L3ProviderPublicUrlReceipt,
    authority: L3ProviderPublicUrlObjectAuthority,
    audit: L3ProviderPublicUrlAuditEvent | None,
) -> dict[str, Any]:
    return {
        "provider_public_url_receipt_id": receipt.provider_public_url_receipt_id,
        "provider_public_url_object_authority_id": receipt.provider_public_url_object_authority_id,
        "provider_public_url_prefix": receipt.provider_public_url_prefix,
        "provider_public_url_audit_event_id": audit.provider_public_url_audit_event_id if audit is not None else None,
        "provider_authority": PROVIDER_PUBLIC_URL_FAKE_PROVIDER_AUTHORITY,
        "authority_hash": authority.authority_hash,
        "provider_public_object_identity_hash": authority.provider_public_object_identity_hash,
        "provider_public_url_secret_redacted": True,
        "raw_public_url_exposed": False,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
    }


def _receipt_response(
    *,
    schema_id: str,
    request_id: str,
    status: str,
    receipt: L3ProviderPublicUrlReceipt,
    authority: L3ProviderPublicUrlObjectAuthority,
    audit: L3ProviderPublicUrlAuditEvent | None,
    now_epoch: int,
) -> dict[str, Any]:
    expires_at_epoch = _datetime_epoch(receipt.provider_public_url_expires_at)
    state = _status_from_receipt(receipt, now_epoch=now_epoch)
    body = {
        **base_response(schema_id, request_id=request_id, status=status),
        "provider_public_url_receipt_id": receipt.provider_public_url_receipt_id,
        "provider_public_url_state": state,
        "delivery_mode": PROVIDER_PUBLIC_URL_DELIVERY_MODE,
        "provider_public_url_redacted": PROVIDER_PUBLIC_URL_REDACTED_MARKER,
        "provider_public_url_expires_at": _epoch_iso(expires_at_epoch),
        "provider_public_url_replay_policy": receipt.provider_public_url_replay_policy,
        "provider_public_url_revocation_supported": False,
        "provider_public_url_revoked": receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_REVOKED,
        "source_artifact_hash": authority.source_artifact_hash,
        "source_artifact_size_bytes": authority.source_artifact_size_bytes,
        "audit_receipt": _audit_receipt(receipt=receipt, authority=authority, audit=audit),
        "raw_public_url_exposed": False,
        "public_url_enabled": False,
        "next_allowed_actions": ["inspect_provider_public_url_status"],
    }
    if schema_id == PROVIDER_PUBLIC_URL_PREPARE_SCHEMA_ID:
        body.update(
            {
                "status": "prepared",
                "session_id": authority.session_id,
                "provider_private_signed_url_receipt_id": authority.provider_private_signed_url_receipt_id,
                "external_export_download_record_ref": authority.external_export_download_record_ref,
                "export_download_descriptor_ref": authority.export_download_descriptor_ref,
                "provider_public_url_expires_in_seconds": max(0, expires_at_epoch - now_epoch),
                "authority_rail": {
                    "provider_authority": PROVIDER_PUBLIC_URL_FAKE_PROVIDER_AUTHORITY,
                    "artifact_authority": "provider_private_signed_url_receipt_authority",
                    "durable_state_authority": True,
                    "provider_public_url_secret_redacted": True,
                    "raw_public_url_exposed": False,
                    "provider_network_enabled": False,
                    "provider_object_write_enabled": False,
                    "connector_dispatch_enabled": False,
                    "destination_write_enabled": False,
                    "public_url_enabled": False,
                    "same_origin_delivery_changed": False,
                },
                "next_state": state,
            }
        )
    return body


def provider_public_url_prepare(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    blocked = _blocked_fields(payload, allowed_fields=PROVIDER_PUBLIC_URL_PREPARE_ALLOWED_FIELDS)
    if blocked:
        raise Layer3WorkbenchError(
            "provider_public_url_prepare_scope_not_admitted",
            "Provider-public URL prepare includes non-admitted fields.",
            status="invalid",
            blocked_fields=blocked,
            next_allowed_actions=["submit_bounded_provider_public_url_prepare_request"],
        )
    missing = _missing_fields(payload, required_fields=PROVIDER_PUBLIC_URL_PREPARE_REQUIRED_FIELDS)
    if missing:
        raise Layer3WorkbenchError(
            "missing_provider_public_url_prepare_fields",
            f"Provider-public URL prepare request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_provider_public_url_prepare_request"],
        )
    _require_prepare_fixed_values(payload)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    ttl_seconds = _ttl_seconds(payload)
    authority_basis = _private_authority_basis(
        db,
        provider_private_signed_url_receipt_id=_text(payload, "provider_private_signed_url_receipt_id"),
    )
    try:
        state = record_prepared_provider_public_url_receipt(
            db,
            request_id=_text(payload, "client_request_id"),
            client_request_id=_text(payload, "client_request_id"),
            authority_basis=authority_basis,
            recipient_scope=_text(payload, "recipient_scope"),
            requested_ttl_seconds=ttl_seconds,
            now_epoch=effective_now,
            provider_public_url=_fake_public_url(
                authority_basis=authority_basis,
                client_request_id=_text(payload, "client_request_id"),
            ),
        )
    except ProviderPublicUrlStateError as exc:
        raise _state_error_to_workbench(exc) from exc

    receipt = db.get(L3ProviderPublicUrlReceipt, state.provider_public_url_receipt_id)
    authority = db.get(L3ProviderPublicUrlObjectAuthority, state.provider_public_url_object_authority_id)
    audit = db.get(L3ProviderPublicUrlAuditEvent, state.provider_public_url_audit_event_id)
    if receipt is None or authority is None:
        raise Layer3WorkbenchError(
            "provider_public_url_state_missing_after_prepare",
            "Provider-public URL durable state was not readable after prepare.",
            status="conflict",
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["retry_provider_public_url_prepare"],
        )
    return _receipt_response(
        schema_id=PROVIDER_PUBLIC_URL_PREPARE_SCHEMA_ID,
        request_id=_text(payload, "client_request_id"),
        status="prepared",
        receipt=receipt,
        authority=authority,
        audit=audit,
        now_epoch=effective_now,
    )


def provider_public_url_status(
    db: Session,
    provider_public_url_receipt_id: str,
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    receipt = db.get(L3ProviderPublicUrlReceipt, provider_public_url_receipt_id)
    if receipt is None:
        raise Layer3WorkbenchError(
            "provider_public_url_receipt_not_found",
            "Provider-public URL receipt was not found.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["prepare_provider_public_url"],
        )
    authority = db.get(L3ProviderPublicUrlObjectAuthority, receipt.provider_public_url_object_authority_id)
    if authority is None:
        raise Layer3WorkbenchError(
            "provider_public_url_authority_not_found",
            "Provider-public URL authority row was not found.",
            status="conflict",
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["prepare_provider_public_url"],
        )
    audit = (
        db.query(L3ProviderPublicUrlAuditEvent)
        .filter(L3ProviderPublicUrlAuditEvent.provider_public_url_receipt_id == receipt.provider_public_url_receipt_id)
        .order_by(L3ProviderPublicUrlAuditEvent.created_at.desc())
        .first()
    )
    return _receipt_response(
        schema_id=PROVIDER_PUBLIC_URL_STATUS_SCHEMA_ID,
        request_id=f"provider-public-url-status:{provider_public_url_receipt_id}",
        status="ok",
        receipt=receipt,
        authority=authority,
        audit=audit,
        now_epoch=effective_now,
    )


def provider_public_url_revoke(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    blocked = _blocked_fields(payload, allowed_fields=PROVIDER_PUBLIC_URL_REVOKE_ALLOWED_FIELDS)
    if blocked:
        raise Layer3WorkbenchError(
            "provider_public_url_revoke_scope_not_admitted",
            "Provider-public URL revoke includes non-admitted fields.",
            status="invalid",
            blocked_fields=blocked,
            next_allowed_actions=["submit_bounded_provider_public_url_revoke_request"],
        )
    missing = _missing_fields(payload, required_fields=PROVIDER_PUBLIC_URL_REVOKE_REQUIRED_FIELDS)
    if missing:
        raise Layer3WorkbenchError(
            "missing_provider_public_url_revoke_fields",
            f"Provider-public URL revoke request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_provider_public_url_revoke_request"],
        )
    _require_revoke_fixed_values(payload)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    try:
        state = revoke_provider_public_url_receipt(
            db,
            provider_public_url_receipt_id=_text(payload, "provider_public_url_receipt_id"),
            idempotency_key=_text(payload, "idempotency_key"),
            revoked_by=_text(payload, "revoked_by"),
            revocation_reason=_text(payload, "revocation_reason"),
            now_epoch=effective_now,
            request_id=_text(payload, "client_request_id"),
        )
    except ProviderPublicUrlStateError as exc:
        raise _state_error_to_workbench(exc) from exc

    receipt = db.get(L3ProviderPublicUrlReceipt, state.provider_public_url_receipt_id)
    authority = db.get(L3ProviderPublicUrlObjectAuthority, state.provider_public_url_object_authority_id)
    audit = db.get(L3ProviderPublicUrlAuditEvent, state.provider_public_url_audit_event_id)
    if receipt is None or authority is None:
        raise Layer3WorkbenchError(
            "provider_public_url_state_missing_after_revoke",
            "Provider-public URL durable state was not readable after revoke.",
            status="conflict",
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["inspect_provider_public_url_status"],
        )
    return _receipt_response(
        schema_id=PROVIDER_PUBLIC_URL_REVOKE_SCHEMA_ID,
        request_id=_text(payload, "client_request_id"),
        status="revoked",
        receipt=receipt,
        authority=authority,
        audit=audit,
        now_epoch=effective_now,
    )
