from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3ConnectorLocalDestinationReceipt,
    L3LocalOutboxProviderPrivateHandoffAuditEvent,
    L3LocalOutboxProviderPrivateHandoffReceipt,
    L3PassRun,
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3ServerOwnedLocalOutboxWriteReceipt,
    L3Session,
    uuid_str,
)
from app.services import (
    layer3_connector_dispatch_entry,
    layer3_server_owned_local_outbox_target,
    layer3_server_owned_local_outbox_write,
    layer3_workbench,
)
from app.services.layer3_provider_private_signed_url_fake_provider import (
    PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
    PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS,
    ProviderArtifactAuthority,
    ProviderPrivateSignedUrlError,
    ProviderPrivateSignedUrlFakeProvider,
    ProviderPrivateSignedUrlPrepareRequest,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow


LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARE_SCHEMA_ID = "layer3.local_outbox_provider_private_handoff.prepare.v1"
LOCAL_OUTBOX_PROVIDER_PRIVATE_STATUS_SCHEMA_ID = "layer3.local_outbox_provider_private_handoff.status.v1"
LOCAL_OUTBOX_PROVIDER_PRIVATE_AUDIT_SCHEMA_ID = "layer3.local_outbox_provider_private_handoff.audit.v1"
LOCAL_OUTBOX_PROVIDER_PRIVATE_SOURCE_GATE = "610_REAL_TARGET_FREEZE"
LOCAL_OUTBOX_PROVIDER_PRIVATE_TARGET_IDENTITY = "server_owned_local_outbox_provider_private_handoff_destination"
LOCAL_OUTBOX_PROVIDER_PRIVATE_DISPATCH_MODE = "provider_private_fake_provider_prepare_status_from_local_outbox_receipt"
LOCAL_OUTBOX_PROVIDER_PRIVATE_OPERATOR_DECISION = "prepare_provider_private_handoff_from_local_outbox"
LOCAL_OUTBOX_PROVIDER_PRIVATE_MARKER = "provider-private-local-outbox-handoff:redacted"
LOCAL_OUTBOX_PROVIDER_PRIVATE_REPLAY_POLICY = "single_prepare_status_only"
LOCAL_OUTBOX_PROVIDER_PRIVATE_RECEIPT_ID_PREFIX = "l3lopp"

LOCAL_OUTBOX_PROVIDER_PRIVATE_NOT_READY_STATE = "local_outbox_provider_private_handoff_not_ready"
LOCAL_OUTBOX_PROVIDER_PRIVATE_READY_STATE = "local_outbox_provider_private_handoff_ready"
LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARED_STATE = "local_outbox_provider_private_handoff_prepared"
LOCAL_OUTBOX_PROVIDER_PRIVATE_REPLAY_STATE = "local_outbox_provider_private_handoff_replay"
LOCAL_OUTBOX_PROVIDER_PRIVATE_CONFLICT_STATE = "local_outbox_provider_private_handoff_conflict"
LOCAL_OUTBOX_PROVIDER_PRIVATE_STALE_AUTHORITY_STATE = "local_outbox_provider_private_handoff_stale_authority"
LOCAL_OUTBOX_PROVIDER_PRIVATE_EXPIRED_STATE = "local_outbox_provider_private_handoff_expired"
LOCAL_OUTBOX_PROVIDER_PRIVATE_FAILED_STATE = "local_outbox_provider_private_handoff_failed"

LOCAL_OUTBOX_PROVIDER_PRIVATE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "connector_local_destination_receipt_id",
        "server_owned_local_outbox_target_receipt_id",
        "server_owned_local_outbox_write_receipt_id",
        "external_export_download_record_ref",
        "target_identity",
        "dispatch_mode",
        "operator_decision",
        "recipient_scope",
    }
)
LOCAL_OUTBOX_PROVIDER_PRIVATE_OPTIONAL_FIELDS = frozenset({"requested_ttl_seconds", "decision_notes"})
LOCAL_OUTBOX_PROVIDER_PRIVATE_ALLOWED_FIELDS = (
    LOCAL_OUTBOX_PROVIDER_PRIVATE_REQUIRED_FIELDS | LOCAL_OUTBOX_PROVIDER_PRIVATE_OPTIONAL_FIELDS
)
LOCAL_OUTBOX_PROVIDER_PRIVATE_FORBIDDEN_FIELDS = frozenset(
    {
        "provider_credentials",
        "provider_secret",
        "provider_token",
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
        "destination_path",
        "destination_secret",
        "destination_url",
        "destination",
        "destination_selector",
        "connector_key",
        "connector_payload",
        "connector_secret",
        "connector_run_id",
        "connector_run_target_id",
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
        "rag_vector_index",
        "prompt_model_settings",
        "prompt_or_model_payload",
        "auth_security_override",
        "auth_internal_state",
        "auth_policy",
        "security_override",
        "browser_durable_authority",
        "frontend_durable_authority",
        "full_mockup_activation",
        "public_url",
        "public_proxy_url",
        "provider_url",
        "provider_public_url",
        "provider_public_delivery",
        "download_url",
        "signed_reference_token",
        "signed_url",
        "provider_private_signed_url_token",
        "raw_provider_private_signed_url_token",
        "credential",
        "credentials",
        "network_write",
        "external_connector_invocation",
        "destination_write",
        "real_destination_integration",
        "retry",
        "rerun",
        "cancel",
        "use",
        "revoke",
    }
)
LOCAL_OUTBOX_PROVIDER_PRIVATE_DOWNSTREAM_UNAVAILABLE = (
    "real_connector_invocation",
    "external_destination_write",
    "connector_run_creation",
    "connector_run_target_creation",
    "credentials",
    "provider_public_delivery_use",
    "raw_token_use",
    "package_mutation_reconstruction",
    "source_expansion",
    "rag_vector",
    "auth_security_implementation",
    "full_mockup_activation",
    "frontend_durable_authority",
    "generic_downstream_dispatch",
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _datetime_epoch(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.astimezone(timezone.utc).timestamp())


def _epoch_iso(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redacted_storage_ref(relative_ref: str) -> str:
    normalized = relative_ref.replace("\\", "/")
    prefix = "layer3-outbox/"
    suffix = normalized[len(prefix) :] if normalized.startswith(prefix) else normalized
    return f"storage://server-owned-local-outbox/{suffix}"


def _blocked_fields(payload: dict[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in LOCAL_OUTBOX_PROVIDER_PRIVATE_ALLOWED_FIELDS)
    forbidden = sorted(key for key in LOCAL_OUTBOX_PROVIDER_PRIVATE_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def _missing_fields(payload: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field in LOCAL_OUTBOX_PROVIDER_PRIVATE_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )


def _ttl_seconds(payload: dict[str, Any]) -> int:
    raw_value = payload.get("requested_ttl_seconds", 300)
    try:
        ttl = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_ttl_invalid",
            "requested_ttl_seconds must be an integer.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
        ) from exc
    if ttl <= 0 or ttl > PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the admitted provider-private TTL bound.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
            next_allowed_actions=["submit_bounded_local_outbox_provider_private_ttl"],
        )
    return ttl


def _existing_summary(reconciliation: L3ReconciliationRecord, key: str) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get(key)
    return state if isinstance(state, dict) else None


def _authority_basis(
    *,
    payload: dict[str, Any],
    write_row: L3ServerOwnedLocalOutboxWriteReceipt,
    target_row: L3ServerOwnedLocalOutboxTargetReceipt,
    local_row: L3ConnectorLocalDestinationReceipt,
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.local_outbox_provider_private_handoff_authority.v1",
        "record_source_gate": LOCAL_OUTBOX_PROVIDER_PRIVATE_SOURCE_GATE,
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": _string(payload.get("analysis_plan_id")),
        "pass_run_id": write_row.pass_run_id,
        "reconciliation_record_id": write_row.reconciliation_record_id,
        "connector_dispatch_record_ref": write_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": write_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": write_row.connector_local_destination_receipt_id,
        "server_owned_local_outbox_target_receipt_id": write_row.server_owned_local_outbox_target_receipt_id,
        "server_owned_local_outbox_write_receipt_id": write_row.server_owned_local_outbox_write_receipt_id,
        "server_owned_local_outbox_write_authority_basis_hash": write_row.authority_basis_hash,
        "server_owned_local_outbox_target_authority_basis_hash": target_row.authority_basis_hash,
        "connector_local_destination_receipt_authority_basis_hash": local_row.authority_basis_hash,
        "target_identity": LOCAL_OUTBOX_PROVIDER_PRIVATE_TARGET_IDENTITY,
        "dispatch_mode": LOCAL_OUTBOX_PROVIDER_PRIVATE_DISPATCH_MODE,
        "source_artifact_hash": write_row.accepted_artifact_hash,
        "source_artifact_size_bytes": write_row.accepted_artifact_size_bytes,
        "outbox_artifact_hash": write_row.outbox_artifact_hash,
        "outbox_artifact_size_bytes": write_row.outbox_artifact_size_bytes,
        "outbox_artifact_ref": _redacted_storage_ref(write_row.outbox_artifact_ref),
        "outbox_manifest_ref": _redacted_storage_ref(write_row.outbox_manifest_ref),
    }


def _request_basis_hash(*, authority_basis_hash: str, client_request_id: str, recipient_scope: str, ttl: int) -> str:
    return stable_hash(
        {
            "authority_basis_hash": authority_basis_hash,
            "client_request_id": client_request_id,
            "recipient_scope": recipient_scope,
            "requested_ttl_seconds": ttl,
        }
    )


def _latest_audit_event(
    db: Session,
    receipt_id: str,
) -> L3LocalOutboxProviderPrivateHandoffAuditEvent | None:
    return (
        db.query(L3LocalOutboxProviderPrivateHandoffAuditEvent)
        .filter(L3LocalOutboxProviderPrivateHandoffAuditEvent.provider_private_handoff_receipt_id == receipt_id)
        .order_by(L3LocalOutboxProviderPrivateHandoffAuditEvent.created_at.desc())
        .first()
    )


def _status_from_receipt(row: L3LocalOutboxProviderPrivateHandoffReceipt, *, now_epoch: int) -> str:
    if row.handoff_state == LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARED_STATE:
        if now_epoch >= _datetime_epoch(row.provider_private_expires_at):
            return LOCAL_OUTBOX_PROVIDER_PRIVATE_EXPIRED_STATE
    return row.handoff_state


def _audit_receipt(
    row: L3LocalOutboxProviderPrivateHandoffReceipt,
    audit: L3LocalOutboxProviderPrivateHandoffAuditEvent | None,
) -> dict[str, Any]:
    return {
        "schema_id": LOCAL_OUTBOX_PROVIDER_PRIVATE_AUDIT_SCHEMA_ID,
        "provider_private_handoff_receipt_id": row.provider_private_handoff_receipt_id,
        "provider_private_handoff_audit_event_id": (
            audit.provider_private_handoff_audit_event_id if audit is not None else None
        ),
        "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
        "authority_basis_hash": row.authority_basis_hash,
        "fake_provider_object_identity_hash": row.fake_provider_object_identity_hash,
        "provider_private_marker": LOCAL_OUTBOX_PROVIDER_PRIVATE_MARKER,
        "provider_secret_redacted": True,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
        "real_connector_invocation_enabled": False,
        "external_destination_write_enabled": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "provider_public_delivery_enabled": False,
        "raw_token_use_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "auth_security_implementation_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def _response(
    *,
    schema_id: str,
    request_id: str,
    status: str,
    operation_state: str,
    row: L3LocalOutboxProviderPrivateHandoffReceipt,
    audit: L3LocalOutboxProviderPrivateHandoffAuditEvent | None,
    now_epoch: int,
) -> dict[str, Any]:
    state = _status_from_receipt(row, now_epoch=now_epoch)
    expires_at_epoch = _datetime_epoch(row.provider_private_expires_at)
    return {
        **base_response(schema_id, request_id=request_id, status=status),
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "provider_private_handoff_receipt_id": row.provider_private_handoff_receipt_id,
        "server_owned_local_outbox_write_receipt_id": row.server_owned_local_outbox_write_receipt_id,
        "server_owned_local_outbox_target_receipt_id": row.server_owned_local_outbox_target_receipt_id,
        "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
        "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "target_identity": row.target_identity,
        "dispatch_mode": row.dispatch_mode,
        "recipient_scope": row.recipient_scope,
        "provider_private_handoff_state": state,
        "handoff_operation_state": operation_state,
        "provider_private_marker": LOCAL_OUTBOX_PROVIDER_PRIVATE_MARKER,
        "provider_private_expires_at": _epoch_iso(expires_at_epoch),
        "provider_private_expires_in_seconds": max(0, expires_at_epoch - now_epoch),
        "provider_private_replay_policy": row.provider_private_replay_policy,
        "provider_private_revocation_supported": False,
        "provider_private_use_route_enabled": False,
        "raw_token_exposed": False,
        "source_artifact_hash": row.source_artifact_hash,
        "source_artifact_size_bytes": row.source_artifact_size_bytes,
        "outbox_artifact_ref": _redacted_storage_ref(row.outbox_artifact_ref),
        "outbox_manifest_ref": _redacted_storage_ref(row.outbox_manifest_ref),
        "outbox_artifact_hash": row.outbox_artifact_hash,
        "outbox_artifact_size_bytes": row.outbox_artifact_size_bytes,
        "authority_basis_hash": row.authority_basis_hash,
        "request_basis_hash": row.request_basis_hash,
        "audit_receipt": _audit_receipt(row, audit),
        "authority_rail": {
            "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
            "artifact_authority": "server_owned_local_outbox_write_receipt_authority",
            "durable_state_authority": True,
            "provider_secret_redacted": True,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
            "same_origin_delivery_changed": False,
        },
        "real_connector_invocation_enabled": False,
        "external_provider_network_write_enabled": False,
        "external_object_store_write_enabled": False,
        "external_destination_write_enabled": False,
        "operator_destination_path_enabled": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "provider_public_url_enabled": False,
        "provider_public_delivery_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "auth_security_implementation_enabled": False,
        "rendered_write_controls_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "downstream_unavailable": list(LOCAL_OUTBOX_PROVIDER_PRIVATE_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": ["inspect_local_outbox_provider_private_handoff_status"],
        "next_state": state,
    }


def _validate_authority(
    db: Session,
    payload: dict[str, Any],
) -> tuple[
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxWriteReceipt,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3ConnectorLocalDestinationReceipt,
]:
    if _string(payload.get("target_identity")) != LOCAL_OUTBOX_PROVIDER_PRIVATE_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_target_identity_not_admitted",
            "target_identity must be server_owned_local_outbox_provider_private_handoff_destination.",
            status="invalid",
            blocked_fields=["target_identity"],
        )
    if _string(payload.get("dispatch_mode")) != LOCAL_OUTBOX_PROVIDER_PRIVATE_DISPATCH_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_dispatch_mode_not_admitted",
            "dispatch_mode must be provider_private_fake_provider_prepare_status_from_local_outbox_receipt.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if _string(payload.get("operator_decision")) != LOCAL_OUTBOX_PROVIDER_PRIVATE_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_local_outbox_provider_private_handoff_decision",
            "operator_decision must be prepare_provider_private_handoff_from_local_outbox.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if not _string(payload.get("recipient_scope")):
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_recipient_scope_required",
            "recipient_scope is required for local-outbox provider-private handoff prepare.",
            status="invalid",
            blocked_fields=["recipient_scope"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().one_or_none()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().one_or_none()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if session is None or pass_run is None or reconciliation is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_requires_existing_authority",
            "Local-outbox provider-private handoff requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_server_owned_local_outbox_write_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    write_receipt_id = _string(payload.get("server_owned_local_outbox_write_receipt_id"))
    write_row = (
        db.query(L3ServerOwnedLocalOutboxWriteReceipt)
        .filter(
            L3ServerOwnedLocalOutboxWriteReceipt.server_owned_local_outbox_write_receipt_id == write_receipt_id,
            L3ServerOwnedLocalOutboxWriteReceipt.session_id == session_id,
            L3ServerOwnedLocalOutboxWriteReceipt.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    if write_row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_requires_outbox_write",
            "Local-outbox provider-private handoff requires an existing server-owned local outbox write receipt.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
            next_allowed_actions=["write_server_owned_local_outbox"],
        )
    if write_row.write_state != layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_requires_recorded_outbox_write",
            "Local-outbox provider-private handoff requires server_owned_local_outbox_write_recorded state.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )

    target_receipt_id = _string(payload.get("server_owned_local_outbox_target_receipt_id"))
    target_row = (
        db.query(L3ServerOwnedLocalOutboxTargetReceipt)
        .filter(
            L3ServerOwnedLocalOutboxTargetReceipt.server_owned_local_outbox_target_receipt_id == target_receipt_id,
            L3ServerOwnedLocalOutboxTargetReceipt.session_id == session_id,
            L3ServerOwnedLocalOutboxTargetReceipt.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    local_receipt_id = _string(payload.get("connector_local_destination_receipt_id"))
    local_row = (
        db.query(L3ConnectorLocalDestinationReceipt)
        .filter(
            L3ConnectorLocalDestinationReceipt.connector_local_destination_receipt_id == local_receipt_id,
            L3ConnectorLocalDestinationReceipt.session_id == session_id,
            L3ConnectorLocalDestinationReceipt.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    if target_row is None or local_row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_requires_receipt_chain",
            "Local-outbox provider-private handoff requires existing local receipt and fake-target receipt authority.",
            status="blocked",
            http_status=409,
            blocked_fields=[
                "connector_local_destination_receipt_id",
                "server_owned_local_outbox_target_receipt_id",
            ],
            next_allowed_actions=["record_server_owned_local_outbox_fake_target"],
        )

    expected = {
        "pass_run_id": write_row.pass_run_id,
        "reconciliation_record_id": write_row.reconciliation_record_id,
        "connector_dispatch_record_ref": write_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": write_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": write_row.connector_local_destination_receipt_id,
        "server_owned_local_outbox_target_receipt_id": write_row.server_owned_local_outbox_target_receipt_id,
    }
    for field, expected_value in expected.items():
        if _string(payload.get(field)) != _string(expected_value):
            raise layer3_workbench.Layer3WorkbenchError(
                f"local_outbox_provider_private_handoff_{field}_mismatch",
                f"Supplied {field} does not match recorded local outbox write authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )

    summary_write = _existing_summary(reconciliation, "server_owned_local_outbox_write")
    summary_target = _existing_summary(reconciliation, "server_owned_local_outbox_target")
    summary_local = _existing_summary(reconciliation, "connector_local_destination_receipt")
    summary_connector = _existing_summary(reconciliation, "connector_dispatch_record")
    summary_readiness = _existing_summary(reconciliation, "external_export_download_prepare")
    stale = (
        summary_write is None
        or _string(summary_write.get("server_owned_local_outbox_write_receipt_id")) != write_receipt_id
        or _string(summary_write.get("authority_basis_hash")) != write_row.authority_basis_hash
        or summary_target is None
        or _string(summary_target.get("authority_basis_hash")) != target_row.authority_basis_hash
        or summary_local is None
        or _string(summary_local.get("authority_basis_hash")) != local_row.authority_basis_hash
        or summary_connector is None
        or summary_connector.get("connector_dispatch_record_state")
        != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_STATE
        or summary_readiness is None
        or summary_readiness.get("external_export_download_state")
        != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
    )
    if stale:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_stale_authority",
            "Recorded local outbox authority no longer matches durable receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
            next_allowed_actions=["refresh_local_outbox_handoff_authority"],
        )

    if target_row.target_identity != layer3_server_owned_local_outbox_target.SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_target_authority_not_admitted",
            "Fake-target receipt target identity is not admitted for local-outbox provider-private handoff.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
        )
    if write_row.target_identity != layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_write_authority_not_admitted",
            "Outbox write target identity is not admitted for provider-private handoff.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )

    storage_root = Path(settings.storage_dir).resolve(strict=False)
    outbox_root = Path(settings.layer3_local_outbox_dir).resolve(strict=False)
    artifact_path = (storage_root / write_row.outbox_artifact_ref).resolve(strict=False)
    manifest_path = (storage_root / write_row.outbox_manifest_ref).resolve(strict=False)
    try:
        artifact_path.relative_to(outbox_root)
        manifest_path.relative_to(outbox_root)
    except ValueError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_outbox_path_escape",
            "Local-outbox provider-private handoff may read only derived server-owned local outbox refs.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        ) from exc
    if (
        not artifact_path.is_file()
        or not manifest_path.is_file()
        or _file_sha256(artifact_path) != write_row.outbox_artifact_hash
        or int(artifact_path.stat().st_size) != int(write_row.outbox_artifact_size_bytes)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_stale_authority",
            "Recorded local outbox artifact no longer matches durable write receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
            next_allowed_actions=["refresh_server_owned_local_outbox_write"],
        )
    return reconciliation, write_row, target_row, local_row


def prepare_local_outbox_provider_private_handoff(
    db: Session,
    payload: dict[str, Any],
    *,
    fake_provider: ProviderPrivateSignedUrlFakeProvider | None = None,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for local-outbox provider-private handoff prepare.",
            status="invalid",
            blocked_fields=["client_request_id"],
        )
    blocked = _blocked_fields(payload)
    if blocked:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_scope_not_admitted",
            "Local-outbox provider-private handoff prepare includes non-admitted fields: "
            + ", ".join(blocked)
            + ".",
            status="invalid",
            blocked_fields=blocked,
            next_allowed_actions=["submit_local_outbox_provider_private_handoff_prepare_request"],
        )
    missing = _missing_fields(payload)
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_local_outbox_provider_private_handoff_fields",
            "Local-outbox provider-private handoff prepare request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
        )
    ttl = _ttl_seconds(payload)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    _reconciliation, write_row, target_row, local_row = _validate_authority(db, payload)
    basis = _authority_basis(payload=payload, write_row=write_row, target_row=target_row, local_row=local_row)
    authority_basis_hash = stable_hash(basis)
    request_basis_hash = _request_basis_hash(
        authority_basis_hash=authority_basis_hash,
        client_request_id=request_id,
        recipient_scope=_string(payload.get("recipient_scope")),
        ttl=ttl,
    )

    existing_by_client = (
        db.query(L3LocalOutboxProviderPrivateHandoffReceipt)
        .filter(L3LocalOutboxProviderPrivateHandoffReceipt.client_request_id == request_id)
        .one_or_none()
    )
    if existing_by_client is not None:
        if existing_by_client.request_basis_hash == request_basis_hash:
            audit = L3LocalOutboxProviderPrivateHandoffAuditEvent(
                provider_private_handoff_audit_event_id=uuid_str(),
                provider_private_handoff_receipt_id=existing_by_client.provider_private_handoff_receipt_id,
                event_type="prepare",
                event_status="accepted",
                request_id=request_id,
                authority_basis_hash=existing_by_client.authority_basis_hash,
                reason_code="idempotent_prepare_reused",
                event_payload_json={"provider_private_marker": LOCAL_OUTBOX_PROVIDER_PRIVATE_MARKER},
                created_at=utcnow(),
            )
            db.add(audit)
            db.commit()
            db.refresh(existing_by_client)
            db.refresh(audit)
            return _response(
                schema_id=LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARE_SCHEMA_ID,
                request_id=request_id,
                status="already_recorded",
                operation_state=LOCAL_OUTBOX_PROVIDER_PRIVATE_REPLAY_STATE,
                row=existing_by_client,
                audit=audit,
                now_epoch=effective_now,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_client_request_conflict",
            "client_request_id already belongs to a different local-outbox provider-private handoff basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )

    existing_by_basis = (
        db.query(L3LocalOutboxProviderPrivateHandoffReceipt)
        .filter(L3LocalOutboxProviderPrivateHandoffReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        audit = L3LocalOutboxProviderPrivateHandoffAuditEvent(
            provider_private_handoff_audit_event_id=uuid_str(),
            provider_private_handoff_receipt_id=existing_by_basis.provider_private_handoff_receipt_id,
            event_type="prepare",
            event_status="accepted",
            request_id=request_id,
            authority_basis_hash=existing_by_basis.authority_basis_hash,
            reason_code="same_local_outbox_authority_prepare_reused",
            event_payload_json={"new_client_request_id": request_id},
            created_at=utcnow(),
        )
        db.add(audit)
        db.commit()
        db.refresh(existing_by_basis)
        db.refresh(audit)
        return _response(
            schema_id=LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARE_SCHEMA_ID,
            request_id=request_id,
            status="already_recorded",
            operation_state=LOCAL_OUTBOX_PROVIDER_PRIVATE_REPLAY_STATE,
            row=existing_by_basis,
            audit=audit,
            now_epoch=effective_now,
        )

    provider = fake_provider or ProviderPrivateSignedUrlFakeProvider()
    try:
        fake_receipt = provider.prepare(
            ProviderPrivateSignedUrlPrepareRequest(
                client_request_id=request_id,
                authority=ProviderArtifactAuthority(
                    source_artifact_ref=basis["outbox_artifact_ref"],
                    source_artifact_hash=write_row.outbox_artifact_hash,
                    source_artifact_size_bytes=write_row.outbox_artifact_size_bytes,
                    external_export_download_record_ref=write_row.external_export_download_record_ref,
                    export_download_descriptor_ref=f"local-outbox-write:{write_row.server_owned_local_outbox_write_receipt_id}",
                ),
                recipient_scope=_string(payload.get("recipient_scope")),
                requested_ttl_seconds=ttl,
                now_epoch=0,
            )
        )
    except ProviderPrivateSignedUrlError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            exc.error_code,
            exc.message,
            status=exc.status,
            http_status=409 if exc.status not in {"invalid", "not_found"} else 400,
            blocked_fields=list(exc.blocked_fields),
            next_allowed_actions=list(exc.next_allowed_actions),
        ) from exc

    receipt_id = stable_id(LOCAL_OUTBOX_PROVIDER_PRIVATE_RECEIPT_ID_PREFIX, request_basis_hash, digest_chars=29)
    now = utcnow()
    expires_at = datetime.fromtimestamp(effective_now + ttl, timezone.utc)
    row = L3LocalOutboxProviderPrivateHandoffReceipt(
        provider_private_handoff_receipt_id=receipt_id,
        server_owned_local_outbox_write_receipt_id=write_row.server_owned_local_outbox_write_receipt_id,
        server_owned_local_outbox_target_receipt_id=write_row.server_owned_local_outbox_target_receipt_id,
        connector_local_destination_receipt_id=write_row.connector_local_destination_receipt_id,
        session_id=write_row.session_id,
        pass_run_id=write_row.pass_run_id,
        reconciliation_record_id=write_row.reconciliation_record_id,
        client_request_id=request_id,
        connector_dispatch_record_ref=write_row.connector_dispatch_record_ref,
        external_export_download_record_ref=write_row.external_export_download_record_ref,
        target_identity=LOCAL_OUTBOX_PROVIDER_PRIVATE_TARGET_IDENTITY,
        dispatch_mode=LOCAL_OUTBOX_PROVIDER_PRIVATE_DISPATCH_MODE,
        recipient_scope=_string(payload.get("recipient_scope")),
        requested_ttl_seconds=ttl,
        handoff_state=LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARED_STATE,
        provider_private_marker=LOCAL_OUTBOX_PROVIDER_PRIVATE_MARKER,
        provider_private_expires_at=expires_at,
        provider_private_replay_policy=LOCAL_OUTBOX_PROVIDER_PRIVATE_REPLAY_POLICY,
        fake_provider_object_identity_hash=fake_receipt.audit_receipt["provider_object_identity_hash"],
        fake_provider_token_hash=fake_receipt.audit_receipt["provider_url_token_hash"],
        source_artifact_hash=write_row.accepted_artifact_hash,
        source_artifact_size_bytes=write_row.accepted_artifact_size_bytes,
        outbox_artifact_ref=write_row.outbox_artifact_ref,
        outbox_manifest_ref=write_row.outbox_manifest_ref,
        outbox_artifact_hash=write_row.outbox_artifact_hash,
        outbox_artifact_size_bytes=write_row.outbox_artifact_size_bytes,
        authority_basis_hash=authority_basis_hash,
        request_basis_hash=request_basis_hash,
        authority_snapshot_json=json_clone(basis),
        created_by_request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    audit = L3LocalOutboxProviderPrivateHandoffAuditEvent(
        provider_private_handoff_audit_event_id=uuid_str(),
        provider_private_handoff_receipt_id=receipt_id,
        event_type="prepare",
        event_status="accepted",
        request_id=request_id,
        authority_basis_hash=authority_basis_hash,
        reason_code="prepared_after_local_outbox_authority_validation",
        event_payload_json={
            "provider_private_marker": LOCAL_OUTBOX_PROVIDER_PRIVATE_MARKER,
            "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
            "raw_token_exposed": False,
            "fake_provider_object_identity_hash": row.fake_provider_object_identity_hash,
        },
        created_at=now,
    )
    db.add_all([row, audit])
    db.commit()
    db.refresh(row)
    db.refresh(audit)
    return _response(
        schema_id=LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARE_SCHEMA_ID,
        request_id=request_id,
        status="prepared",
        operation_state=LOCAL_OUTBOX_PROVIDER_PRIVATE_PREPARED_STATE,
        row=row,
        audit=audit,
        now_epoch=effective_now,
    )


def local_outbox_provider_private_handoff_status(
    db: Session,
    provider_private_handoff_receipt_id: str,
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    receipt_id = _string(provider_private_handoff_receipt_id)
    if not receipt_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_receipt_id_required",
            "provider_private_handoff_receipt_id is required.",
            status="invalid",
            blocked_fields=["provider_private_handoff_receipt_id"],
        )
    row = (
        db.query(L3LocalOutboxProviderPrivateHandoffReceipt)
        .filter(L3LocalOutboxProviderPrivateHandoffReceipt.provider_private_handoff_receipt_id == receipt_id)
        .one_or_none()
    )
    if row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "local_outbox_provider_private_handoff_not_recorded",
            "Local-outbox provider-private handoff receipt has no durable server-side state.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_private_handoff_receipt_id"],
            next_allowed_actions=["prepare_local_outbox_provider_private_handoff"],
        )
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    audit = _latest_audit_event(db, receipt_id)
    return _response(
        schema_id=LOCAL_OUTBOX_PROVIDER_PRIVATE_STATUS_SCHEMA_ID,
        request_id=f"local-outbox-provider-private-status:{receipt_id}",
        status="ok",
        operation_state=_status_from_receipt(row, now_epoch=effective_now),
        row=row,
        audit=audit,
        now_epoch=effective_now,
    )
