from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request
from typing import Any, Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3ConnectorLocalDestinationReceipt,
    L3InternalWebhookDispatchAuditEvent,
    L3InternalWebhookDispatchReceipt,
    L3PassRun,
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3ServerOwnedLocalOutboxWriteReceipt,
    L3Session,
)
from app.services import (
    layer3_connector_dispatch_entry,
    layer3_connector_local_destination_receipt,
    layer3_server_owned_local_outbox_target,
    layer3_server_owned_local_outbox_write,
    layer3_workbench,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow


INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID = "layer3.internal_webhook.dispatch.v1"
INTERNAL_WEBHOOK_STATUS_SCHEMA_ID = "layer3.internal_webhook.status.v1"
INTERNAL_WEBHOOK_AUDIT_SCHEMA_ID = "layer3.internal_webhook.audit.v1"
INTERNAL_WEBHOOK_STATE_SCHEMA_ID = "layer3.internal_webhook.state.v1"
INTERNAL_WEBHOOK_DELIVERY_ENVELOPE_SCHEMA_ID = "layer3.internal_webhook.delivery_envelope.v1"
INTERNAL_WEBHOOK_SOURCE_GATE = "852_INTERNAL_WEBHOOK_CONNECTOR_FREEZE"
INTERNAL_WEBHOOK_TARGET_IDENTITY = "server_configured_internal_webhook_destination"
INTERNAL_WEBHOOK_TARGET_CLASS = "real_connector_invocation"
INTERNAL_WEBHOOK_DISPATCH_MODE = "server_configured_allowlisted_internal_webhook_post"
INTERNAL_WEBHOOK_OPERATOR_DECISION = "dispatch_server_configured_internal_webhook"
INTERNAL_WEBHOOK_RECEIPT_ID_PREFIX = "l3iwh"
INTERNAL_WEBHOOK_PACKAGE_KIND = "handoff_export_delivery_envelope"
INTERNAL_WEBHOOK_DISPATCHED_STATE = "internal_webhook_dispatched"
INTERNAL_WEBHOOK_FAILED_STATE = "internal_webhook_failed"
INTERNAL_WEBHOOK_REPLAY_STATE = "internal_webhook_replay"
INTERNAL_WEBHOOK_CONFLICT_STATE = "internal_webhook_conflict"

INTERNAL_WEBHOOK_REQUIRED_FIELDS = frozenset(
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
        "target_class",
        "dispatch_mode",
        "operator_decision",
    }
)
INTERNAL_WEBHOOK_OPTIONAL_FIELDS = frozenset({"decision_notes"})
INTERNAL_WEBHOOK_ALLOWED_FIELDS = INTERNAL_WEBHOOK_REQUIRED_FIELDS | INTERNAL_WEBHOOK_OPTIONAL_FIELDS
INTERNAL_WEBHOOK_FORBIDDEN_FIELDS = frozenset(
    {
        "destination_url",
        "raw_destination_url",
        "destination",
        "destination_id",
        "destination_selector",
        "target_url",
        "provider_url",
        "provider_public_url",
        "provider_private_signed_url",
        "public_url",
        "public_proxy_url",
        "download_url",
        "signed_url",
        "cloud_object_key",
        "object_key",
        "bucket",
        "provider_credentials",
        "provider_token",
        "provider_secret",
        "credentials",
        "credential",
        "token",
        "raw_token",
        "headers",
        "header",
        "raw_header",
        "request_headers",
        "body_override",
        "connector_target",
        "connector_run_id",
        "connector_run_target_id",
        "connector_key",
        "connector_secret",
        "connector_payload",
        "package_payload",
        "package_bytes",
        "raw_package_bytes",
        "package_variant_content",
        "rebuild_package",
        "rewrite_output",
        "source_upload",
        "source_material",
        "source_expansion",
        "local_path",
        "local_file_path",
        "local_directory",
        "rag_vector_input",
        "rag_vector_index",
        "rag_vector_state",
        "optional_tool_input",
        "tabpfn_runtime",
        "nrc_rag_runtime",
        "auth_security_override",
        "auth_policy",
        "security_override",
        "browser_durable_authority",
        "frontend_durable_authority",
        "retry",
        "rerun",
        "cancel",
    }
)
INTERNAL_WEBHOOK_DOWNSTREAM_UNAVAILABLE = (
    "arbitrary_connector_dispatch",
    "arbitrary_destination_url",
    "operator_supplied_url",
    "provider_public_url",
    "provider_private_signed_url",
    "cloud_object_store_write",
    "oauth_or_provider_credentials",
    "connector_run_creation",
    "connector_run_target_creation",
    "package_mutation",
    "source_expansion",
    "rag_vector",
    "optional_tool_runtime",
    "gate_c_optional_tool_admission",
    "broad_auth_security",
    "rendered_write_submit_control",
)

WebhookTransport = Callable[[str, dict[str, Any], dict[str, str], float], tuple[int, Any]]


def _string(value: Any) -> str:
    return str(value or "").strip()


def _redacted_outbox_ref(relative_ref: str) -> str:
    normalized = relative_ref.replace("\\", "/")
    prefix = f"{layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_STORAGE_DIRNAME}/"
    suffix = normalized[len(prefix) :] if normalized.startswith(prefix) else normalized
    return f"storage://server-owned-local-outbox/{suffix}"


def _blocked_fields(payload: dict[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in INTERNAL_WEBHOOK_ALLOWED_FIELDS)
    forbidden = sorted(key for key in INTERNAL_WEBHOOK_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def _missing_fields(payload: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field in INTERNAL_WEBHOOK_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )


def _destination_display_name() -> str:
    return _string(settings.layer3_internal_webhook_display_name) or "server-configured-internal-webhook"


def _configured_destination_url() -> str:
    raw = _string(settings.layer3_internal_webhook_url)
    if not raw:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_destination_not_configured",
            "Server-configured internal webhook URL is not configured.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_INTERNAL_WEBHOOK_URL"],
        )
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_destination_invalid",
            "Server-configured internal webhook URL must be an HTTP(S) URL with a host.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_INTERNAL_WEBHOOK_URL"],
        )
    host = parsed.hostname.lower()
    admitted = host in {"localhost", "127.0.0.1", "::1"}
    if not admitted:
        try:
            address = ipaddress.ip_address(host)
            admitted = address.is_loopback or address.is_private or address.is_link_local
        except ValueError:
            admitted = "." not in host or host.endswith((".local", ".internal", ".lan"))
    if not admitted:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_destination_not_allowlisted_internal",
            "Server-configured internal webhook URL must resolve to an internal allowlisted destination.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_INTERNAL_WEBHOOK_URL"],
        )
    return raw


def _urllib_transport(
    url: str,
    envelope: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(envelope, sort_keys=True).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            try:
                parsed_body: Any = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed_body = body[:256]
            return int(response.status), parsed_body
    except urllib.error.HTTPError as exc:
        return int(exc.code), "http_error_response"
    except TimeoutError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_dispatch_timeout",
            "Internal webhook dispatch timed out.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_configured_internal_webhook_destination"],
        ) from exc
    except OSError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_dispatch_failed",
            "Internal webhook dispatch failed before a complete accepted response.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_configured_internal_webhook_destination"],
        ) from exc


INTERNAL_WEBHOOK_TRANSPORT: WebhookTransport = _urllib_transport


def _latest_audit(
    db: Session,
    receipt_id: str,
) -> L3InternalWebhookDispatchAuditEvent | None:
    return (
        db.query(L3InternalWebhookDispatchAuditEvent)
        .filter(L3InternalWebhookDispatchAuditEvent.internal_webhook_dispatch_receipt_id == receipt_id)
        .order_by(L3InternalWebhookDispatchAuditEvent.created_at.desc())
        .first()
    )


def _audit_receipt(
    row: L3InternalWebhookDispatchReceipt,
    audit: L3InternalWebhookDispatchAuditEvent | None,
) -> dict[str, Any]:
    return {
        "schema_id": INTERNAL_WEBHOOK_AUDIT_SCHEMA_ID,
        "internal_webhook_dispatch_receipt_id": row.internal_webhook_dispatch_receipt_id,
        "internal_webhook_dispatch_audit_event_id": (
            audit.internal_webhook_dispatch_audit_event_id if audit else None
        ),
        "authority_basis_hash": row.authority_basis_hash,
        "redacted_destination_display_name": row.redacted_destination_display_name,
        "raw_target_url_exposed": False,
        "raw_token_exposed": False,
        "raw_headers_exposed": False,
        "raw_local_path_exposed": False,
        "raw_package_payload_exposed": False,
        "raw_package_bytes_exposed": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "provider_public_url_enabled": False,
        "provider_private_signed_url_enabled": False,
    }


def _response(
    *,
    schema_id: str,
    request_id: str,
    status: str,
    operation_state: str,
    row: L3InternalWebhookDispatchReceipt,
    audit: L3InternalWebhookDispatchAuditEvent | None,
) -> dict[str, Any]:
    return {
        **base_response(schema_id, request_id=request_id, status=status),
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "internal_webhook_dispatch_receipt_id": row.internal_webhook_dispatch_receipt_id,
        "server_owned_local_outbox_write_receipt_id": row.server_owned_local_outbox_write_receipt_id,
        "server_owned_local_outbox_target_receipt_id": row.server_owned_local_outbox_target_receipt_id,
        "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
        "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "package_kind": row.package_kind,
        "package_artifact_ref": row.package_artifact_ref,
        "package_artifact_hash": row.package_artifact_hash,
        "package_artifact_size_bytes": row.package_artifact_size_bytes,
        "handoff_export_prepare_ref": row.handoff_export_prepare_ref,
        "target_identity": row.target_identity,
        "target_class": row.target_class,
        "dispatch_mode": row.dispatch_mode,
        "internal_webhook_dispatch_state": row.dispatch_status,
        "dispatch_operation_state": operation_state,
        "redacted_destination_display_name": row.redacted_destination_display_name,
        "idempotency_key": row.idempotency_key,
        "request_basis_hash": row.request_basis_hash,
        "authority_basis_hash": row.authority_basis_hash,
        "response_status_code": row.response_status_code,
        "redacted_response_summary": json_clone(row.redacted_response_summary_json or {}),
        "failure_code": row.failure_code,
        "audit_receipt": _audit_receipt(row, audit),
        "server_configured_internal_webhook_enabled": True,
        "internal_webhook_post_performed": row.dispatch_status == INTERNAL_WEBHOOK_DISPATCHED_STATE,
        "real_connector_invocation_enabled": True,
        "server_configured_allowlisted_url_enabled": True,
        "operator_destination_url_enabled": False,
        "raw_target_url_exposed": False,
        "raw_token_exposed": False,
        "raw_headers_exposed": False,
        "raw_local_path_exposed": False,
        "raw_package_payload_exposed": False,
        "raw_package_bytes_exposed": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "provider_public_url_enabled": False,
        "provider_private_signed_url_enabled": False,
        "cloud_object_store_write_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "optional_tool_runtime_enabled": False,
        "auth_security_implementation_enabled": False,
        "rendered_write_submit_control_enabled": False,
        "downstream_unavailable": list(INTERNAL_WEBHOOK_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": ["inspect_internal_webhook_dispatch_status"],
        "next_state": row.dispatch_status,
    }


def _request_basis_hash(*, authority_basis_hash: str, client_request_id: str) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.internal_webhook.request_basis.v1",
            "authority_basis_hash": authority_basis_hash,
            "client_request_id": client_request_id,
            "target_identity": INTERNAL_WEBHOOK_TARGET_IDENTITY,
            "target_class": INTERNAL_WEBHOOK_TARGET_CLASS,
            "dispatch_mode": INTERNAL_WEBHOOK_DISPATCH_MODE,
        }
    )


def _authority_basis(
    *,
    payload: dict[str, Any],
    write_row: L3ServerOwnedLocalOutboxWriteReceipt,
    target_row: L3ServerOwnedLocalOutboxTargetReceipt,
    local_row: L3ConnectorLocalDestinationReceipt,
    package_review_submit_state: dict[str, Any],
    handoff_export_prepare_state: dict[str, Any],
    external_export_download_state: dict[str, Any],
    destination_url: str,
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.internal_webhook.authority.v1",
        "record_source_gate": INTERNAL_WEBHOOK_SOURCE_GATE,
        "session_id": write_row.session_id,
        "analysis_plan_id": _string(payload.get("analysis_plan_id")),
        "pass_run_id": write_row.pass_run_id,
        "reconciliation_record_id": write_row.reconciliation_record_id,
        "connector_dispatch_record_ref": write_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": write_row.external_export_download_record_ref,
        "server_owned_local_outbox_write_receipt_id": write_row.server_owned_local_outbox_write_receipt_id,
        "server_owned_local_outbox_target_receipt_id": write_row.server_owned_local_outbox_target_receipt_id,
        "connector_local_destination_receipt_id": write_row.connector_local_destination_receipt_id,
        "server_owned_local_outbox_write_authority_basis_hash": write_row.authority_basis_hash,
        "server_owned_local_outbox_target_authority_basis_hash": target_row.authority_basis_hash,
        "connector_local_destination_receipt_authority_basis_hash": local_row.authority_basis_hash,
        "package_review_submit_record_ref": package_review_submit_state.get("submit_record_ref"),
        "handoff_export_prepare_ref": handoff_export_prepare_state.get("prepare_record_ref"),
        "handoff_export_envelope_ref": handoff_export_prepare_state.get("handoff_export_envelope_ref"),
        "external_export_download_record_ref_from_readiness": external_export_download_state.get(
            "external_export_download_record_ref"
        ),
        "target_identity": INTERNAL_WEBHOOK_TARGET_IDENTITY,
        "target_class": INTERNAL_WEBHOOK_TARGET_CLASS,
        "dispatch_mode": INTERNAL_WEBHOOK_DISPATCH_MODE,
        "redacted_destination_display_name": _destination_display_name(),
        "destination_url_hash": stable_hash({"schema_id": "layer3.internal_webhook.url_hash.v1", "url": destination_url}),
        "package_kind": INTERNAL_WEBHOOK_PACKAGE_KIND,
        "package_artifact_hash": write_row.outbox_artifact_hash,
        "package_artifact_size_bytes": write_row.outbox_artifact_size_bytes,
    }


def _validate_authority(
    db: Session,
    payload: dict[str, Any],
) -> tuple[
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxWriteReceipt,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3ConnectorLocalDestinationReceipt,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if _string(payload.get("target_identity")) != INTERNAL_WEBHOOK_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_target_identity_not_admitted",
            "target_identity must be server_configured_internal_webhook_destination.",
            status="invalid",
            blocked_fields=["target_identity"],
        )
    if _string(payload.get("target_class")) != INTERNAL_WEBHOOK_TARGET_CLASS:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_target_class_not_admitted",
            "target_class must be real_connector_invocation.",
            status="invalid",
            blocked_fields=["target_class"],
        )
    if _string(payload.get("dispatch_mode")) != INTERNAL_WEBHOOK_DISPATCH_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_dispatch_mode_not_admitted",
            "dispatch_mode must be server_configured_allowlisted_internal_webhook_post.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if _string(payload.get("operator_decision")) != INTERNAL_WEBHOOK_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_internal_webhook_decision",
            "operator_decision must be dispatch_server_configured_internal_webhook.",
            status="invalid",
            blocked_fields=["operator_decision"],
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
            "internal_webhook_requires_existing_authority",
            "Internal webhook dispatch requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_pass_run_mismatch",
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
    target_row = (
        db.query(L3ServerOwnedLocalOutboxTargetReceipt)
        .filter(
            L3ServerOwnedLocalOutboxTargetReceipt.server_owned_local_outbox_target_receipt_id
            == _string(payload.get("server_owned_local_outbox_target_receipt_id")),
            L3ServerOwnedLocalOutboxTargetReceipt.session_id == session_id,
            L3ServerOwnedLocalOutboxTargetReceipt.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    local_row = (
        db.query(L3ConnectorLocalDestinationReceipt)
        .filter(
            L3ConnectorLocalDestinationReceipt.connector_local_destination_receipt_id
            == _string(payload.get("connector_local_destination_receipt_id")),
            L3ConnectorLocalDestinationReceipt.session_id == session_id,
            L3ConnectorLocalDestinationReceipt.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    if write_row is None or target_row is None or local_row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_requires_receipt_chain",
            "Internal webhook dispatch requires existing local receipt, target receipt, and outbox write receipt.",
            status="blocked",
            http_status=409,
            blocked_fields=[
                "connector_local_destination_receipt_id",
                "server_owned_local_outbox_target_receipt_id",
                "server_owned_local_outbox_write_receipt_id",
            ],
        )
    if write_row.write_state != layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_requires_recorded_outbox_write",
            "Internal webhook dispatch requires server_owned_local_outbox_write_recorded state.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
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
                f"internal_webhook_{field}_mismatch",
                f"Supplied {field} does not match recorded local outbox write authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )
    if target_row.target_identity != layer3_server_owned_local_outbox_target.SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_target_authority_not_admitted",
            "Local outbox target receipt identity is not admitted for internal webhook dispatch.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
        )
    if write_row.target_identity != layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_write_authority_not_admitted",
            "Outbox write receipt target identity is not admitted for internal webhook dispatch.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )

    summary = reconciliation.summary_json if isinstance(reconciliation.summary_json, dict) else {}
    summary_write = summary.get("server_owned_local_outbox_write")
    summary_target = summary.get("server_owned_local_outbox_target")
    summary_local = summary.get("connector_local_destination_receipt")
    summary_connector = summary.get("connector_dispatch_record")
    package_review_submit_state = summary.get("package_review_submit")
    handoff_export_prepare_state = summary.get("handoff_export_prepare")
    external_export_download_state = summary.get("external_export_download_prepare")
    stale = (
        not isinstance(summary_write, dict)
        or _string(summary_write.get("server_owned_local_outbox_write_receipt_id")) != write_receipt_id
        or _string(summary_write.get("authority_basis_hash")) != write_row.authority_basis_hash
        or not isinstance(summary_target, dict)
        or _string(summary_target.get("authority_basis_hash")) != target_row.authority_basis_hash
        or not isinstance(summary_local, dict)
        or _string(summary_local.get("authority_basis_hash")) != local_row.authority_basis_hash
        or not isinstance(summary_connector, dict)
        or summary_connector.get("connector_dispatch_record_state")
        != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_STATE
        or not isinstance(package_review_submit_state, dict)
        or (
            package_review_submit_state.get("state") or package_review_submit_state.get("package_review_state")
        )
        != layer3_workbench.PACKAGE_REVIEW_APPROVED_STATE
        or not package_review_submit_state.get("submit_record_ref")
        or not isinstance(handoff_export_prepare_state, dict)
        or handoff_export_prepare_state.get("handoff_export_state")
        != layer3_workbench.HANDOFF_EXPORT_PREPARED_STATE
        or not handoff_export_prepare_state.get("prepare_record_ref")
        or not isinstance(external_export_download_state, dict)
        or external_export_download_state.get("external_export_download_state")
        != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
        or _string(external_export_download_state.get("external_export_download_record_ref"))
        != write_row.external_export_download_record_ref
    )
    if stale:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_stale_authority",
            "Recorded package review, handoff/export, export/download, or outbox authority is stale.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )
    return (
        reconciliation,
        write_row,
        target_row,
        local_row,
        package_review_submit_state,
        handoff_export_prepare_state,
        external_export_download_state,
    )


def _delivery_envelope(
    *,
    row: L3InternalWebhookDispatchReceipt,
) -> dict[str, Any]:
    return {
        "schema_id": INTERNAL_WEBHOOK_DELIVERY_ENVELOPE_SCHEMA_ID,
        "schema_version": 1,
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "package_kind": row.package_kind,
        "package_artifact_ref": row.package_artifact_ref,
        "package_artifact_hash": row.package_artifact_hash,
        "package_artifact_size_bytes": row.package_artifact_size_bytes,
        "handoff_export_prepare_ref": row.handoff_export_prepare_ref,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "target_identity": row.target_identity,
        "target_class": row.target_class,
        "dispatch_mode": row.dispatch_mode,
        "redacted_destination_display_name": row.redacted_destination_display_name,
        "idempotency_key": row.idempotency_key,
        "request_basis_hash": row.request_basis_hash,
        "authority_basis_hash": row.authority_basis_hash,
        "raw_package_bytes_included": False,
        "raw_package_payload_included": False,
        "raw_target_url_included": False,
    }


def _redacted_response_summary(status_code: int, body: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {"response_kind": type(body).__name__}
    if isinstance(body, dict):
        safe_keys = sorted(str(key) for key in body.keys())[:20]
        summary["response_keys"] = safe_keys
    elif isinstance(body, str):
        summary["response_text_size"] = len(body)
    return {"status_code": status_code, **summary}


def _record_audit(
    *,
    db: Session,
    row: L3InternalWebhookDispatchReceipt,
    event_type: str,
    event_status: str,
    reason_code: str,
    request_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> L3InternalWebhookDispatchAuditEvent:
    audit = L3InternalWebhookDispatchAuditEvent(
        internal_webhook_dispatch_receipt_id=row.internal_webhook_dispatch_receipt_id,
        event_type=event_type,
        event_status=event_status,
        request_id=request_id or row.client_request_id,
        authority_basis_hash=row.authority_basis_hash,
        reason_code=reason_code,
        event_payload_json=json_clone(payload or {}),
        created_at=utcnow(),
    )
    db.add(audit)
    return audit


def dispatch_internal_webhook(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for internal webhook dispatch.",
            status="invalid",
            blocked_fields=["client_request_id"],
        )
    blocked = _blocked_fields(payload)
    if blocked:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_scope_not_admitted",
            "Internal webhook request includes non-admitted fields: " + ", ".join(blocked) + ".",
            status="invalid",
            blocked_fields=blocked,
        )
    missing = _missing_fields(payload)
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_internal_webhook_fields",
            "Internal webhook request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
        )

    destination_url = _configured_destination_url()
    (
        reconciliation,
        write_row,
        target_row,
        local_row,
        package_review_submit_state,
        handoff_export_prepare_state,
        external_export_download_state,
    ) = _validate_authority(db, payload)
    basis = _authority_basis(
        payload=payload,
        write_row=write_row,
        target_row=target_row,
        local_row=local_row,
        package_review_submit_state=package_review_submit_state,
        handoff_export_prepare_state=handoff_export_prepare_state,
        external_export_download_state=external_export_download_state,
        destination_url=destination_url,
    )
    authority_basis_hash = stable_hash(basis)
    request_basis_hash = _request_basis_hash(
        authority_basis_hash=authority_basis_hash,
        client_request_id=request_id,
    )
    existing_by_client = (
        db.query(L3InternalWebhookDispatchReceipt)
        .filter(L3InternalWebhookDispatchReceipt.client_request_id == request_id)
        .one_or_none()
    )
    if existing_by_client is not None:
        if existing_by_client.request_basis_hash == request_basis_hash:
            audit = _record_audit(
                db=db,
                row=existing_by_client,
                event_type="dispatch",
                event_status="accepted",
                reason_code="idempotent_dispatch_reused",
                request_id=request_id,
            )
            db.commit()
            db.refresh(existing_by_client)
            db.refresh(audit)
            return _response(
                schema_id=INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID,
                request_id=request_id,
                status="already_recorded",
                operation_state=INTERNAL_WEBHOOK_REPLAY_STATE,
                row=existing_by_client,
                audit=audit,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_client_request_conflict",
            "client_request_id already belongs to a different internal webhook authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing_by_basis = (
        db.query(L3InternalWebhookDispatchReceipt)
        .filter(L3InternalWebhookDispatchReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        audit = _record_audit(
            db=db,
            row=existing_by_basis,
            event_type="dispatch",
            event_status="accepted",
            reason_code="same_package_basis_dispatch_reused",
            request_id=request_id,
            payload={"new_client_request_id": request_id},
        )
        db.commit()
        db.refresh(existing_by_basis)
        db.refresh(audit)
        return _response(
            schema_id=INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID,
            request_id=request_id,
            status="already_recorded",
            operation_state=INTERNAL_WEBHOOK_REPLAY_STATE,
            row=existing_by_basis,
            audit=audit,
        )

    now = utcnow()
    receipt_id = stable_id(INTERNAL_WEBHOOK_RECEIPT_ID_PREFIX, request_basis_hash, digest_chars=30)
    row = L3InternalWebhookDispatchReceipt(
        internal_webhook_dispatch_receipt_id=receipt_id,
        server_owned_local_outbox_write_receipt_id=write_row.server_owned_local_outbox_write_receipt_id,
        server_owned_local_outbox_target_receipt_id=write_row.server_owned_local_outbox_target_receipt_id,
        connector_local_destination_receipt_id=write_row.connector_local_destination_receipt_id,
        session_id=write_row.session_id,
        pass_run_id=write_row.pass_run_id,
        reconciliation_record_id=write_row.reconciliation_record_id,
        client_request_id=request_id,
        connector_dispatch_record_ref=write_row.connector_dispatch_record_ref,
        external_export_download_record_ref=write_row.external_export_download_record_ref,
        package_kind=INTERNAL_WEBHOOK_PACKAGE_KIND,
        package_artifact_ref=_redacted_outbox_ref(write_row.outbox_artifact_ref),
        package_artifact_hash=write_row.outbox_artifact_hash,
        package_artifact_size_bytes=write_row.outbox_artifact_size_bytes,
        handoff_export_prepare_ref=_string(handoff_export_prepare_state.get("prepare_record_ref")),
        target_identity=INTERNAL_WEBHOOK_TARGET_IDENTITY,
        target_class=INTERNAL_WEBHOOK_TARGET_CLASS,
        dispatch_mode=INTERNAL_WEBHOOK_DISPATCH_MODE,
        redacted_destination_display_name=_destination_display_name(),
        idempotency_key=request_id,
        request_basis_hash=request_basis_hash,
        authority_basis_hash=authority_basis_hash,
        dispatch_status=INTERNAL_WEBHOOK_FAILED_STATE,
        response_status_code=None,
        redacted_response_summary_json={},
        failure_code=None,
        authority_snapshot_json=json_clone(basis),
        created_by_request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    _record_audit(
        db=db,
        row=row,
        event_type="dispatch",
        event_status="attempted",
        reason_code="authority_validated_internal_webhook_post_attempted",
        payload={"redacted_destination_display_name": row.redacted_destination_display_name},
    )
    envelope = _delivery_envelope(row=row)
    headers = {
        "Content-Type": "application/json",
        "X-Layer3-Envelope-Schema": INTERNAL_WEBHOOK_DELIVERY_ENVELOPE_SCHEMA_ID,
    }
    try:
        status_code, response_body = INTERNAL_WEBHOOK_TRANSPORT(destination_url, envelope, headers, 5.0)
    except layer3_workbench.Layer3WorkbenchError as exc:
        row.dispatch_status = INTERNAL_WEBHOOK_FAILED_STATE
        row.failure_code = exc.error_code
        row.updated_at = utcnow()
        audit = _record_audit(
            db=db,
            row=row,
            event_type="dispatch",
            event_status="failed",
            reason_code=exc.error_code,
            payload={"redacted_destination_display_name": row.redacted_destination_display_name},
        )
        db.commit()
        db.refresh(row)
        db.refresh(audit)
        raise
    if status_code < 200 or status_code >= 300:
        row.dispatch_status = INTERNAL_WEBHOOK_FAILED_STATE
        row.response_status_code = status_code
        row.failure_code = "internal_webhook_non_success_response"
        row.redacted_response_summary_json = _redacted_response_summary(status_code, response_body)
        row.updated_at = utcnow()
        audit = _record_audit(
            db=db,
            row=row,
            event_type="dispatch",
            event_status="failed",
            reason_code=row.failure_code,
            payload=row.redacted_response_summary_json,
        )
        db.commit()
        db.refresh(row)
        db.refresh(audit)
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_non_success_response",
            "Internal webhook dispatch did not return an accepted 2xx response.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_configured_internal_webhook_destination"],
        )

    row.dispatch_status = INTERNAL_WEBHOOK_DISPATCHED_STATE
    row.response_status_code = status_code
    row.redacted_response_summary_json = _redacted_response_summary(status_code, response_body)
    row.failure_code = None
    row.updated_at = utcnow()
    audit = _record_audit(
        db=db,
        row=row,
        event_type="dispatch",
        event_status="accepted",
        reason_code="internal_webhook_post_completed",
        payload=row.redacted_response_summary_json,
    )
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "internal_webhook_dispatch": {
            "schema_id": INTERNAL_WEBHOOK_STATE_SCHEMA_ID,
            "internal_webhook_dispatch_receipt_id": receipt_id,
            "state": INTERNAL_WEBHOOK_DISPATCHED_STATE,
            "session_id": row.session_id,
            "pass_run_id": row.pass_run_id,
            "reconciliation_record_id": row.reconciliation_record_id,
            "server_owned_local_outbox_write_receipt_id": row.server_owned_local_outbox_write_receipt_id,
            "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
            "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
            "external_export_download_record_ref": row.external_export_download_record_ref,
            "package_kind": row.package_kind,
            "package_artifact_hash": row.package_artifact_hash,
            "package_artifact_size_bytes": row.package_artifact_size_bytes,
            "handoff_export_prepare_ref": row.handoff_export_prepare_ref,
            "target_identity": row.target_identity,
            "target_class": row.target_class,
            "dispatch_mode": row.dispatch_mode,
            "redacted_destination_display_name": row.redacted_destination_display_name,
            "authority_basis_hash": row.authority_basis_hash,
            "request_basis_hash": row.request_basis_hash,
            "response_status_code": row.response_status_code,
            "record_source_gate": INTERNAL_WEBHOOK_SOURCE_GATE,
            "server_configured_internal_webhook_enabled": True,
            "internal_webhook_post_performed": True,
            "connector_run_created": False,
            "connector_run_target_created": False,
            "credentials_enabled": False,
            "provider_public_url_enabled": False,
            "provider_private_signed_url_enabled": False,
            "package_mutation_enabled": False,
            "source_expansion_enabled": False,
            "rag_vector_enabled": False,
            "optional_tool_runtime_enabled": False,
        },
    }
    db.commit()
    db.refresh(row)
    db.refresh(audit)
    return _response(
        schema_id=INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID,
        request_id=request_id,
        status="dispatched",
        operation_state=INTERNAL_WEBHOOK_DISPATCHED_STATE,
        row=row,
        audit=audit,
    )


def internal_webhook_status(db: Session, internal_webhook_dispatch_receipt_id: str) -> dict[str, Any]:
    receipt_id = _string(internal_webhook_dispatch_receipt_id)
    if not receipt_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_dispatch_receipt_id_required",
            "internal_webhook_dispatch_receipt_id is required.",
            status="invalid",
            blocked_fields=["internal_webhook_dispatch_receipt_id"],
        )
    row = (
        db.query(L3InternalWebhookDispatchReceipt)
        .filter(L3InternalWebhookDispatchReceipt.internal_webhook_dispatch_receipt_id == receipt_id)
        .one_or_none()
    )
    if row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "internal_webhook_dispatch_not_recorded",
            "Internal webhook dispatch receipt has no durable server-side state.",
            status="not_found",
            http_status=404,
            blocked_fields=["internal_webhook_dispatch_receipt_id"],
        )
    return _response(
        schema_id=INTERNAL_WEBHOOK_STATUS_SCHEMA_ID,
        request_id=f"status-{receipt_id}",
        status="ok",
        operation_state=row.dispatch_status,
        row=row,
        audit=_latest_audit(db, receipt_id),
    )
