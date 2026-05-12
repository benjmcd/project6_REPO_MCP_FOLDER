from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
    L3PassRun,
    L3ProviderPrivateSignedUrlAuditEvent,
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ReconciliationRecord,
    L3Session,
)
from app.services.layer3_provider_private_signed_url_fake_provider import (
    PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
    PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS,
    ProviderArtifactAuthority,
    ProviderPrivateSignedUrlError,
    ProviderPrivateSignedUrlFakeProvider,
    ProviderPrivateSignedUrlPrepareRequest,
)
from app.services.layer3_provider_private_signed_url_state import (
    INTERNAL_ARTIFACT_REF_PLACEHOLDER,
    PROVIDER_PRIVATE_SIGNED_URL_REPLAY_POLICY_SINGLE_USE,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_PREPARED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED,
    ProviderPrivateSignedUrlStateError,
    record_prepared_provider_private_signed_url_receipt,
    revoke_provider_private_signed_url_receipt,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_workbench_error import Layer3WorkbenchError
from app.services.layer3_workbench_package_state import external_export_download_prepare_from_reconciliation


PROVIDER_PRIVATE_SIGNED_URL_PREPARE_SCHEMA_ID = "layer3.provider_private_signed_url.prepare.v1"
PROVIDER_PRIVATE_SIGNED_URL_REVOKE_SCHEMA_ID = "layer3.provider_private_signed_url.revoke.v1"
PROVIDER_PRIVATE_SIGNED_URL_STATUS_SCHEMA_ID = "layer3.provider_private_signed_url.status.v1"
PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE = "provider_private_signed_url"
PROVIDER_PRIVATE_SIGNED_URL_OPERATOR_DECISION = "prepare_provider_private_signed_url"
PROVIDER_PRIVATE_SIGNED_URL_REVOKE_OPERATOR_DECISION = "revoke_provider_private_signed_url"
PROVIDER_PRIVATE_SIGNED_URL_DEFAULT_TTL_SECONDS = 300
PROVIDER_PRIVATE_SIGNED_URL_FIXED_FAKE_PROVIDER_EPOCH = 0
PROVIDER_PRIVATE_SIGNED_URL_REDACTED_MARKER = "provider-private-signed-url:redacted"

PROVIDER_PRIVATE_SIGNED_URL_ALLOWED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "export_download_target",
        "download_mode",
        "delivery_mode",
        "operator_decision",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "recipient_scope",
        "requested_ttl_seconds",
        "decision_notes",
    }
)
PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS = frozenset(
    {
        "provider_credentials",
        "provider_secret",
        "provider_bucket",
        "provider_container",
        "provider_object_key",
        "provider_object_identity",
        "raw_provider_signature",
        "raw_provider_object_key",
        "raw_local_path",
        "local_path",
        "local_file_path",
        "destination_id",
        "destination_url",
        "destination",
        "destination_selector",
        "connector_payload",
        "connector_secret",
        "connector_run_id",
        "connector_dispatch",
        "source_upload",
        "source_expansion",
        "local_upload",
        "local_directory",
        "web_connector",
        "package_mutation",
        "package_payload",
        "package_variant_content",
        "rebuild_package",
        "rewrite_output",
        "rag_vector_settings",
        "rag_vector_state",
        "prompt_model_settings",
        "prompt_or_model_payload",
        "auth_security_override",
        "auth_internal_state",
        "browser_durable_authority",
        "public_url",
        "public_proxy_url",
        "provider_url",
        "download_url",
        "signed_reference_token",
        "signed_url",
        "provider_private_signed_url_token",
        "raw_provider_private_signed_url_token",
    }
)
PROVIDER_PRIVATE_SIGNED_URL_REVOKE_ALLOWED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_signed_url_receipt_id",
        "idempotency_key",
        "revoked_by",
        "revocation_reason",
        "operator_decision",
        "decision_notes",
    }
)


def _text(payload: Mapping[str, Any], field: str) -> str:
    return str(payload.get(field) or "").strip()


def _epoch_iso(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def _datetime_epoch(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.astimezone(timezone.utc).timestamp())


def _missing_fields(payload: Mapping[str, Any]) -> list[str]:
    return [
        field
        for field in (
            "client_request_id",
            "session_id",
            "analysis_plan_id",
            "pass_run_id",
            "reconciliation_record_id",
            "external_export_download_record_ref",
            "export_download_descriptor_ref",
            "external_export_download_state",
            "export_download_target",
            "download_mode",
            "delivery_mode",
            "operator_decision",
            "source_artifact_hash",
            "source_artifact_size_bytes",
            "recipient_scope",
        )
        if payload.get(field) in (None, "")
    ]


def _blocked_fields(
    payload: Mapping[str, Any],
    *,
    allowed_fields: frozenset[str] = PROVIDER_PRIVATE_SIGNED_URL_ALLOWED_FIELDS,
) -> list[str]:
    unknown = sorted(key for key in payload if key not in allowed_fields)
    forbidden = sorted(key for key in PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def _missing_revoke_fields(payload: Mapping[str, Any]) -> list[str]:
    return [
        field
        for field in (
            "client_request_id",
            "provider_signed_url_receipt_id",
            "idempotency_key",
            "revoked_by",
            "revocation_reason",
            "operator_decision",
        )
        if payload.get(field) in (None, "")
    ]


def _ttl_seconds(payload: Mapping[str, Any]) -> int:
    raw_value = payload.get("requested_ttl_seconds", PROVIDER_PRIVATE_SIGNED_URL_DEFAULT_TTL_SECONDS)
    try:
        ttl = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_ttl_invalid",
            "requested_ttl_seconds must be an integer.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
        ) from exc
    if ttl <= 0 or ttl > PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the admitted provider-private TTL bound.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
            next_allowed_actions=["submit_bounded_provider_private_signed_url_ttl"],
        )
    return ttl


def _state_error(exc: ProviderPrivateSignedUrlStateError) -> Layer3WorkbenchError:
    http_status = 404 if exc.status == "not_found" else 409 if exc.status in {"blocked", "conflict"} else 400
    return Layer3WorkbenchError(
        exc.error_code,
        exc.message,
        status=exc.status,
        http_status=http_status,
        blocked_fields=list(exc.blocked_fields),
        next_allowed_actions=list(exc.next_allowed_actions),
    )


def _fake_provider_error(exc: ProviderPrivateSignedUrlError) -> Layer3WorkbenchError:
    http_status = 409 if exc.status in {"provider_private_signed_url_blocked", "provider_private_signed_url_conflict"} else 400
    return Layer3WorkbenchError(
        exc.error_code,
        "Provider-private signed URL fake-provider prepare failed without exposing provider secrets.",
        status="blocked" if http_status == 409 else "invalid",
        http_status=http_status,
        blocked_fields=list(exc.blocked_fields),
        next_allowed_actions=list(exc.next_allowed_actions),
    )


def _require_fixed_values(payload: Mapping[str, Any]) -> None:
    expected = {
        "external_export_download_state": "external_export_download_prepared",
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "delivery_mode": PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE,
        "operator_decision": PROVIDER_PRIVATE_SIGNED_URL_OPERATOR_DECISION,
    }
    for field, expected_value in expected.items():
        if _text(payload, field) != expected_value:
            raise Layer3WorkbenchError(
                f"provider_private_signed_url_{field}_not_admitted",
                f"{field} must be {expected_value}.",
                status="invalid",
                blocked_fields=[field],
            )


def _require_revoke_fixed_values(payload: Mapping[str, Any]) -> None:
    if _text(payload, "operator_decision") != PROVIDER_PRIVATE_SIGNED_URL_REVOKE_OPERATOR_DECISION:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_revoke_operator_decision_not_admitted",
            f"operator_decision must be {PROVIDER_PRIVATE_SIGNED_URL_REVOKE_OPERATOR_DECISION}.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )


def _load_readiness_authority(db: Session, payload: Mapping[str, Any]) -> dict[str, Any]:
    session_id = _text(payload, "session_id")
    analysis_plan_id = _text(payload, "analysis_plan_id")
    pass_run_id = _text(payload, "pass_run_id")
    reconciliation_record_id = _text(payload, "reconciliation_record_id")
    session = db.query(L3Session).filter(L3Session.session_id == session_id).one_or_none()
    plan = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.analysis_plan_id == analysis_plan_id).one_or_none()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one_or_none()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .one_or_none()
    )
    missing = []
    if session is None:
        missing.append("session_id")
    if plan is None:
        missing.append("analysis_plan_id")
    if pass_run is None:
        missing.append("pass_run_id")
    if reconciliation is None:
        missing.append("reconciliation_record_id")
    if missing:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_authority_not_found",
            "Provider-private signed URL prepare requires existing Layer 3 session, plan, pass, and reconciliation authority.",
            status="not_found",
            http_status=404,
            blocked_fields=missing,
            next_allowed_actions=["inspect_existing_layer3_authority"],
        )
    if plan.session_id != session_id or pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_plan_pass_mismatch",
            "Supplied plan/pass authority does not belong to the supplied Layer 3 session.",
            status="conflict",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id"],
        )

    readiness_state = external_export_download_prepare_from_reconciliation(reconciliation)
    if readiness_state is None or readiness_state.get("external_export_download_state") != "external_export_download_prepared":
        raise Layer3WorkbenchError(
            "provider_private_signed_url_requires_external_export_download_prepared",
            "Provider-private signed URL prepare requires recorded external_export_download_prepared authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_state"],
            next_allowed_actions=["record_external_export_download_prepare"],
        )
    for field in (
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "export_download_target",
        "download_mode",
        "source_artifact_hash",
    ):
        if _text(payload, field) != str(readiness_state.get(field) or "").strip():
            raise Layer3WorkbenchError(
                f"provider_private_signed_url_{field}_mismatch",
                f"Supplied {field} does not match recorded external export/download authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
                next_allowed_actions=["refresh_external_export_download_authority"],
            )
    try:
        supplied_size = int(payload.get("source_artifact_size_bytes"))
        recorded_size = int(readiness_state.get("source_artifact_size_bytes"))
    except (TypeError, ValueError) as exc:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_source_artifact_size_invalid",
            "source_artifact_size_bytes must be an integer matching recorded authority.",
            status="invalid",
            blocked_fields=["source_artifact_size_bytes"],
        ) from exc
    if supplied_size != recorded_size:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_source_artifact_size_bytes_mismatch",
            "Supplied source_artifact_size_bytes does not match recorded external export/download authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_size_bytes"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        )
    return readiness_state


def _validate_server_owned_artifact(readiness_state: Mapping[str, Any]) -> None:
    artifact_ref = str(readiness_state.get("source_artifact_ref") or "").strip()
    if not artifact_ref:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_source_artifact_ref_missing",
            "Recorded external export/download authority is missing its server-owned artifact reference.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_ref"],
        )
    artifact_path = Path(artifact_ref)
    if not artifact_path.exists() or not artifact_path.is_file():
        raise Layer3WorkbenchError(
            "provider_private_signed_url_source_artifact_unavailable",
            "Recorded external export/download artifact is unavailable.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_artifact_ref"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        )
    artifact_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    artifact_size = artifact_path.stat().st_size
    if artifact_hash != str(readiness_state.get("source_artifact_hash") or ""):
        raise Layer3WorkbenchError(
            "provider_private_signed_url_source_artifact_hash_mismatch",
            "Current source artifact hash does not match recorded external export/download authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_hash"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        )
    if artifact_size != int(readiness_state.get("source_artifact_size_bytes") or -1):
        raise Layer3WorkbenchError(
            "provider_private_signed_url_source_artifact_size_bytes_mismatch",
            "Current source artifact size does not match recorded external export/download authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_size_bytes"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        )


def _authority_basis(payload: Mapping[str, Any], readiness_state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": _text(payload, "session_id"),
        "reconciliation_record_id": _text(payload, "reconciliation_record_id"),
        "source_artifact_ref": str(readiness_state.get("source_artifact_ref") or "").strip(),
        "source_artifact_hash": _text(payload, "source_artifact_hash").lower(),
        "source_artifact_size_bytes": int(payload.get("source_artifact_size_bytes")),
        "external_export_download_record_ref": _text(payload, "external_export_download_record_ref"),
        "export_download_descriptor_ref": _text(payload, "export_download_descriptor_ref"),
    }


def _latest_audit_event(db: Session, receipt_id: str) -> L3ProviderPrivateSignedUrlAuditEvent | None:
    return (
        db.query(L3ProviderPrivateSignedUrlAuditEvent)
        .filter(L3ProviderPrivateSignedUrlAuditEvent.provider_private_signed_url_receipt_id == receipt_id)
        .order_by(
            L3ProviderPrivateSignedUrlAuditEvent.created_at.desc(),
            L3ProviderPrivateSignedUrlAuditEvent.provider_private_signed_url_audit_event_id.desc(),
        )
        .first()
    )


def _audit_event_by_id(db: Session, audit_event_id: str) -> L3ProviderPrivateSignedUrlAuditEvent | None:
    return (
        db.query(L3ProviderPrivateSignedUrlAuditEvent)
        .filter(L3ProviderPrivateSignedUrlAuditEvent.provider_private_signed_url_audit_event_id == audit_event_id)
        .one_or_none()
    )


def _revoke_authority_basis(db: Session, *, receipt_id: str) -> dict[str, Any] | None:
    receipt = (
        db.query(L3ProviderPrivateSignedUrlReceipt)
        .filter(L3ProviderPrivateSignedUrlReceipt.provider_private_signed_url_receipt_id == receipt_id)
        .one_or_none()
    )
    if receipt is None:
        return None
    authority = (
        db.query(L3ProviderPrivateSignedUrlObjectAuthority)
        .filter(
            L3ProviderPrivateSignedUrlObjectAuthority.provider_private_signed_url_object_authority_id
            == receipt.provider_private_signed_url_object_authority_id
        )
        .one_or_none()
    )
    if authority is None:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_revoke_authority_missing",
            "Provider-private signed URL revoke requires durable object authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
            next_allowed_actions=["prepare_provider_private_signed_url"],
        )
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == authority.reconciliation_record_id,
            L3ReconciliationRecord.session_id == authority.session_id,
        )
        .one_or_none()
    )
    if reconciliation is None:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_revoke_authority_not_found",
            "Provider-private signed URL revoke could not reload recorded external export/download authority.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_signed_url_receipt_id"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        )
    readiness_state = external_export_download_prepare_from_reconciliation(reconciliation)
    if readiness_state is None:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_revoke_authority_missing",
            "Provider-private signed URL revoke requires recorded external_export_download_prepared authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        )
    mismatches = []
    expected = {
        "external_export_download_record_ref": authority.external_export_download_record_ref,
        "export_download_descriptor_ref": authority.export_download_descriptor_ref,
        "source_artifact_hash": authority.source_artifact_hash,
        "source_artifact_size_bytes": str(authority.source_artifact_size_bytes),
    }
    for field, expected_value in expected.items():
        if str(readiness_state.get(field) or "").strip() != str(expected_value):
            mismatches.append(field)
    if mismatches:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_revoke_authority_mismatch",
            "Provider-private signed URL revoke authority no longer matches recorded prepare authority.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatches,
            next_allowed_actions=["prepare_new_provider_private_signed_url"],
        )
    _validate_server_owned_artifact(readiness_state)
    return {
        "session_id": authority.session_id,
        "reconciliation_record_id": authority.reconciliation_record_id,
        "source_artifact_ref": str(readiness_state.get("source_artifact_ref") or "").strip(),
        "source_artifact_hash": authority.source_artifact_hash,
        "source_artifact_size_bytes": authority.source_artifact_size_bytes,
        "external_export_download_record_ref": authority.external_export_download_record_ref,
        "export_download_descriptor_ref": authority.export_download_descriptor_ref,
    }


def _status_from_receipt(receipt: L3ProviderPrivateSignedUrlReceipt, *, now_epoch: int) -> str:
    if (
        receipt.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_PREPARED
        and now_epoch >= _datetime_epoch(receipt.provider_private_signed_url_expires_at)
    ):
        return PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED
    return receipt.provider_private_signed_url_state


def _audit_receipt(
    *,
    receipt: L3ProviderPrivateSignedUrlReceipt,
    authority: L3ProviderPrivateSignedUrlObjectAuthority,
    audit: L3ProviderPrivateSignedUrlAuditEvent | None,
) -> dict[str, Any]:
    return {
        "provider_private_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": receipt.provider_private_signed_url_object_authority_id,
        "provider_private_signed_url_token_prefix": receipt.provider_private_signed_url_token_prefix,
        "provider_private_signed_url_audit_event_id": (
            audit.provider_private_signed_url_audit_event_id if audit is not None else None
        ),
        "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
        "authority_hash": authority.authority_hash,
        "provider_object_identity_hash": authority.provider_object_identity_hash,
        "source_artifact_ref": INTERNAL_ARTIFACT_REF_PLACEHOLDER,
        "provider_url_secret_redacted": True,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
    }


def _receipt_response(
    *,
    schema_id: str,
    request_id: str,
    status: str,
    receipt: L3ProviderPrivateSignedUrlReceipt,
    authority: L3ProviderPrivateSignedUrlObjectAuthority,
    audit: L3ProviderPrivateSignedUrlAuditEvent | None,
    now_epoch: int,
    session_id: str | None = None,
    analysis_plan_id: str | None = None,
    pass_run_id: str | None = None,
    reconciliation_record_id: str | None = None,
    revocation_idempotency_key: str | None = None,
) -> dict[str, Any]:
    expires_at_epoch = _datetime_epoch(receipt.provider_private_signed_url_expires_at)
    state = _status_from_receipt(receipt, now_epoch=now_epoch)
    body = {
        **base_response(schema_id, request_id=request_id, status=status),
        "provider_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_signed_url_state": state,
        "delivery_mode": PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE,
        "provider_url_redacted": PROVIDER_PRIVATE_SIGNED_URL_REDACTED_MARKER,
        "provider_url_expires_at": _epoch_iso(expires_at_epoch),
        "provider_url_replay_policy": receipt.provider_private_signed_url_replay_policy,
        "provider_url_revocation_supported": True,
        "provider_url_use_count": receipt.provider_private_signed_url_use_count,
        "provider_url_max_use_count": receipt.provider_private_signed_url_max_use_count,
        "provider_url_revoked": receipt.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED,
        "source_artifact_hash": authority.source_artifact_hash,
        "source_artifact_size_bytes": authority.source_artifact_size_bytes,
        "audit_receipt": _audit_receipt(receipt=receipt, authority=authority, audit=audit),
        "next_allowed_actions": ["inspect_provider_private_signed_url_status"],
    }
    if schema_id == PROVIDER_PRIVATE_SIGNED_URL_PREPARE_SCHEMA_ID:
        body.update(
            {
                "session_id": session_id or authority.session_id,
                "analysis_plan_id": analysis_plan_id,
                "pass_run_id": pass_run_id,
                "reconciliation_record_id": reconciliation_record_id or authority.reconciliation_record_id,
                "external_export_download_record_ref": authority.external_export_download_record_ref,
                "export_download_descriptor_ref": authority.export_download_descriptor_ref,
                "status": "prepared",
                "provider_url_expires_in_seconds": max(0, expires_at_epoch - now_epoch),
                "authority_rail": {
                    "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
                    "artifact_authority": "existing_external_export_download_prepare_authority",
                    "durable_state_authority": True,
                    "provider_url_secret_redacted": True,
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
    if schema_id == PROVIDER_PRIVATE_SIGNED_URL_REVOKE_SCHEMA_ID:
        body.update(
            {
                "status": "revoked",
                "revocation_recorded": True,
                "revocation_idempotency_key": revocation_idempotency_key,
                "authority_rail": {
                    "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
                    "artifact_authority": "existing_external_export_download_prepare_authority",
                    "durable_state_authority": True,
                    "provider_url_secret_redacted": True,
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


def provider_private_signed_url_prepare(
    db: Session,
    payload: dict[str, Any],
    *,
    fake_provider: ProviderPrivateSignedUrlFakeProvider | None = None,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    blocked = _blocked_fields(payload)
    if blocked:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_scope_not_admitted",
            "Provider-private signed URL prepare includes non-admitted fields.",
            status="invalid",
            blocked_fields=blocked,
            next_allowed_actions=["submit_bounded_provider_private_signed_url_prepare_request"],
        )
    missing = _missing_fields(payload)
    if missing:
        raise Layer3WorkbenchError(
            "missing_provider_private_signed_url_prepare_fields",
            f"Provider-private signed URL prepare request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_provider_private_signed_url_prepare_request"],
        )
    _require_fixed_values(payload)
    ttl_seconds = _ttl_seconds(payload)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    readiness_state = _load_readiness_authority(db, payload)
    _validate_server_owned_artifact(readiness_state)
    authority_basis = _authority_basis(payload, readiness_state)

    provider = fake_provider or ProviderPrivateSignedUrlFakeProvider()
    try:
        fake_receipt = provider.prepare(
            ProviderPrivateSignedUrlPrepareRequest(
                client_request_id=_text(payload, "client_request_id"),
                authority=ProviderArtifactAuthority(
                    source_artifact_ref=authority_basis["source_artifact_ref"],
                    source_artifact_hash=authority_basis["source_artifact_hash"],
                    source_artifact_size_bytes=authority_basis["source_artifact_size_bytes"],
                    external_export_download_record_ref=authority_basis["external_export_download_record_ref"],
                    export_download_descriptor_ref=authority_basis["export_download_descriptor_ref"],
                ),
                recipient_scope=_text(payload, "recipient_scope"),
                requested_ttl_seconds=ttl_seconds,
                now_epoch=PROVIDER_PRIVATE_SIGNED_URL_FIXED_FAKE_PROVIDER_EPOCH,
            )
        )
    except ProviderPrivateSignedUrlError as exc:
        raise _fake_provider_error(exc) from exc

    request_id = _text(payload, "client_request_id")
    try:
        durable_state = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id=request_id,
            client_request_id=request_id,
            authority_basis=authority_basis,
            recipient_scope=_text(payload, "recipient_scope"),
            requested_ttl_seconds=ttl_seconds,
            now_epoch=effective_now,
            provider_private_signed_url_token=fake_receipt.token_for_test,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _state_error(exc) from exc

    receipt = (
        db.query(L3ProviderPrivateSignedUrlReceipt)
        .filter(
            L3ProviderPrivateSignedUrlReceipt.provider_private_signed_url_receipt_id
            == durable_state.provider_private_signed_url_receipt_id
        )
        .one()
    )
    authority = (
        db.query(L3ProviderPrivateSignedUrlObjectAuthority)
        .filter(
            L3ProviderPrivateSignedUrlObjectAuthority.provider_private_signed_url_object_authority_id
            == receipt.provider_private_signed_url_object_authority_id
        )
        .one()
    )
    audit = _audit_event_by_id(db, durable_state.provider_private_signed_url_audit_event_id)
    return _receipt_response(
        schema_id=PROVIDER_PRIVATE_SIGNED_URL_PREPARE_SCHEMA_ID,
        request_id=request_id,
        status="prepared",
        receipt=receipt,
        authority=authority,
        audit=audit,
        now_epoch=effective_now,
        session_id=_text(payload, "session_id"),
        analysis_plan_id=_text(payload, "analysis_plan_id"),
        pass_run_id=_text(payload, "pass_run_id"),
        reconciliation_record_id=_text(payload, "reconciliation_record_id"),
    )


def provider_private_signed_url_revoke(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    blocked = _blocked_fields(payload, allowed_fields=PROVIDER_PRIVATE_SIGNED_URL_REVOKE_ALLOWED_FIELDS)
    if blocked:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_revoke_scope_not_admitted",
            "Provider-private signed URL revoke includes non-admitted fields.",
            status="invalid",
            blocked_fields=blocked,
            next_allowed_actions=["submit_bounded_provider_private_signed_url_revoke_request"],
        )
    missing = _missing_revoke_fields(payload)
    if missing:
        raise Layer3WorkbenchError(
            "missing_provider_private_signed_url_revoke_fields",
            f"Provider-private signed URL revoke request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_provider_private_signed_url_revoke_request"],
        )
    _require_revoke_fixed_values(payload)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    request_id = _text(payload, "client_request_id")
    receipt_id = _text(payload, "provider_signed_url_receipt_id")
    idempotency_key = _text(payload, "idempotency_key")
    authority_basis = _revoke_authority_basis(db, receipt_id=receipt_id)
    try:
        durable_state = revoke_provider_private_signed_url_receipt(
            db,
            provider_private_signed_url_receipt_id=receipt_id,
            idempotency_key=idempotency_key,
            revoked_by=_text(payload, "revoked_by"),
            revocation_reason=_text(payload, "revocation_reason"),
            authority_basis=authority_basis,
            now_epoch=effective_now,
            request_id=request_id,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _state_error(exc) from exc

    receipt = (
        db.query(L3ProviderPrivateSignedUrlReceipt)
        .filter(
            L3ProviderPrivateSignedUrlReceipt.provider_private_signed_url_receipt_id
            == durable_state.provider_private_signed_url_receipt_id
        )
        .one()
    )
    authority = (
        db.query(L3ProviderPrivateSignedUrlObjectAuthority)
        .filter(
            L3ProviderPrivateSignedUrlObjectAuthority.provider_private_signed_url_object_authority_id
            == receipt.provider_private_signed_url_object_authority_id
        )
        .one()
    )
    audit = _audit_event_by_id(db, durable_state.provider_private_signed_url_audit_event_id)
    return _receipt_response(
        schema_id=PROVIDER_PRIVATE_SIGNED_URL_REVOKE_SCHEMA_ID,
        request_id=request_id,
        status="revoked",
        receipt=receipt,
        authority=authority,
        audit=audit,
        now_epoch=effective_now,
        revocation_idempotency_key=idempotency_key,
    )


def provider_private_signed_url_status(
    db: Session,
    provider_signed_url_receipt_id: str,
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    receipt_id = str(provider_signed_url_receipt_id or "").strip()
    if not receipt_id:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_receipt_id_required",
            "provider_signed_url_receipt_id is required.",
            status="invalid",
            blocked_fields=["provider_signed_url_receipt_id"],
        )
    receipt = (
        db.query(L3ProviderPrivateSignedUrlReceipt)
        .filter(L3ProviderPrivateSignedUrlReceipt.provider_private_signed_url_receipt_id == receipt_id)
        .one_or_none()
    )
    if receipt is None:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_receipt_not_found",
            "Provider-private signed URL receipt was not found.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_signed_url_receipt_id"],
            next_allowed_actions=["prepare_provider_private_signed_url"],
        )
    authority = (
        db.query(L3ProviderPrivateSignedUrlObjectAuthority)
        .filter(
            L3ProviderPrivateSignedUrlObjectAuthority.provider_private_signed_url_object_authority_id
            == receipt.provider_private_signed_url_object_authority_id
        )
        .one_or_none()
    )
    if authority is None:
        raise Layer3WorkbenchError(
            "provider_private_signed_url_authority_missing",
            "Provider-private signed URL receipt is missing durable object authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
        )
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    audit = _latest_audit_event(db, receipt.provider_private_signed_url_receipt_id)
    return _receipt_response(
        schema_id=PROVIDER_PRIVATE_SIGNED_URL_STATUS_SCHEMA_ID,
        request_id=f"provider-private-signed-url-status:{receipt_id}",
        status="ok",
        receipt=receipt,
        authority=authority,
        audit=audit,
        now_epoch=effective_now,
    )
