from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.models import (
    L3MaterialSnapshot,
    L3OutputPackage,
    L3ReconciliationRecord,
    L3Session,
    L3SourceDirectoryInternalWebhookDispatchAuditEvent,
    L3SourceDirectoryInternalWebhookDispatchReceipt,
)
from app.services import layer3_internal_webhook_connector, layer3_source_directory_hybrid_analysis
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow
from app.services.layer3_workbench_error import Layer3WorkbenchError


SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID = (
    "layer3.source_directory_internal_webhook.dispatch.v1"
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_STATUS_SCHEMA_ID = (
    "layer3.source_directory_internal_webhook.status.v1"
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_AUDIT_SCHEMA_ID = (
    "layer3.source_directory_internal_webhook.audit.v1"
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_STATE_SCHEMA_ID = (
    "layer3.source_directory_internal_webhook.state.v1"
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DELIVERY_ENVELOPE_SCHEMA_ID = (
    "layer3.source_directory_internal_webhook.delivery_envelope.v1"
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_SOURCE_GATE = "934_SOURCE_DIRECTORY_INTERNAL_WEBHOOK_RUNTIME_ENTRY"
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_OPERATOR_DECISION = (
    "dispatch_source_directory_hybrid_internal_webhook"
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_RECEIPT_ID_PREFIX = "l3sih"
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCHED_STATE = "source_directory_internal_webhook_dispatched"
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_FAILED_STATE = "source_directory_internal_webhook_failed"
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_REPLAY_STATE = "source_directory_internal_webhook_replay"

_TARGET_IDENTITY = layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TARGET_IDENTITY
_TARGET_CLASS = layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TARGET_CLASS
_DISPATCH_MODE = layer3_internal_webhook_connector.INTERNAL_WEBHOOK_DISPATCH_MODE

SOURCE_DIRECTORY_INTERNAL_WEBHOOK_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "material_snapshot_id",
        "source_ingestion_batch_id",
        "source_ingestion_file_id",
        "content_sha256",
        "file_identity_hash",
        "authority_basis_hash",
        "payload_hash",
        "index_authority_hash",
        "embedding_index_authority_hash",
        "query_text",
        "analysis_question",
        "analysis_focus",
        "qualitative_analysis_hash",
        "source_directory_hybrid_package_review_preview_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "handoff_target",
        "export_mode",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "external_export_download_target",
        "download_mode",
        "target_identity",
        "target_class",
        "dispatch_mode",
        "operator_decision",
    }
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_OPTIONAL_FIELDS = frozenset({"limit", "offset", "top_k", "decision_notes"})
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_ALLOWED_FIELDS = (
    SOURCE_DIRECTORY_INTERNAL_WEBHOOK_REQUIRED_FIELDS | SOURCE_DIRECTORY_INTERNAL_WEBHOOK_OPTIONAL_FIELDS
)
SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DOWNSTREAM_UNAVAILABLE = (
    "operator_supplied_url",
    "raw_target_url",
    "raw_token",
    "raw_headers",
    "raw_package_payload",
    "raw_package_bytes",
    "connector_run_creation",
    "provider_public_delivery",
    "provider_private_signed_url",
    "package_mutation",
    "source_expansion",
    "rag_vector_indexing",
    "optional_tool_runtime",
    "frontend_durable_authority",
    "full_mockup_activation",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in payload if key not in SOURCE_DIRECTORY_INTERNAL_WEBHOOK_ALLOWED_FIELDS)


def _missing_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(
        field
        for field in SOURCE_DIRECTORY_INTERNAL_WEBHOOK_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )


def _string_list(payload: Mapping[str, Any], field: str) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_list_field_invalid",
            "Source-directory internal webhook list fields must be supplied as non-empty string lists.",
            status="invalid",
            blocked_fields=[field],
        )
    normalized = [_text(item) for item in value]
    if not normalized or any(not item for item in normalized):
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_list_field_invalid",
            "Source-directory internal webhook list fields must be supplied as non-empty string lists.",
            status="invalid",
            blocked_fields=[field],
        )
    return normalized


def _require_fixed_values(payload: Mapping[str, Any]) -> None:
    expected = {
        "target_identity": _TARGET_IDENTITY,
        "target_class": _TARGET_CLASS,
        "dispatch_mode": _DISPATCH_MODE,
        "operator_decision": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_OPERATOR_DECISION,
        "external_export_download_state": (
            layer3_source_directory_hybrid_analysis.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
        ),
        "external_export_download_target": layer3_source_directory_hybrid_analysis.EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": layer3_source_directory_hybrid_analysis.EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "handoff_export_state": layer3_source_directory_hybrid_analysis.HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "package_review_state": layer3_source_directory_hybrid_analysis.PACKAGE_REVIEW_APPROVED_STATE,
    }
    mismatches = [field for field, expected_value in expected.items() if _text(payload.get(field)) != expected_value]
    if mismatches:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_fixed_value_mismatch",
            "Source-directory internal webhook request contains non-admitted fixed-value fields.",
            status="invalid",
            http_status=409,
            blocked_fields=mismatches,
        )


def _qualitative_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    keys = {
        "client_request_id",
        "material_snapshot_id",
        "source_ingestion_batch_id",
        "source_ingestion_file_id",
        "content_sha256",
        "file_identity_hash",
        "authority_basis_hash",
        "payload_hash",
        "index_authority_hash",
        "embedding_index_authority_hash",
        "query_text",
        "analysis_question",
        "analysis_focus",
        "limit",
        "offset",
        "top_k",
    }
    return {key: payload[key] for key in keys if key in payload}


def _load_authority(
    db: Session,
    payload: Mapping[str, Any],
) -> tuple[L3Session, L3ReconciliationRecord, L3MaterialSnapshot, list[L3OutputPackage], dict[str, Any]]:
    try:
        qualitative = layer3_source_directory_hybrid_analysis.source_directory_hybrid_context_packet_qualitative_analysis(
            db,
            _qualitative_payload(payload),
        )
    except Exception as exc:
        if all(hasattr(exc, name) for name in ("code", "message", "http_status")):
            raise Layer3WorkbenchError(
                f"source_directory_internal_webhook_{exc.code}",
                exc.message,
                status="conflict" if exc.http_status == 409 else "invalid",
                http_status=exc.http_status,
                blocked_fields=list(getattr(exc, "details", {}).get("blocked_fields") or []),
            ) from exc
        raise
    hash_mismatches = [
        field
        for field in (
            "qualitative_analysis_hash",
            "source_directory_hybrid_package_review_preview_hash",
        )
        if _text(payload.get(field)) != _text(qualitative.get(field))
    ]
    if hash_mismatches:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_qualitative_authority_mismatch",
            "Source-directory internal webhook must reference current server-recomputed qualitative authority.",
            status="conflict",
            http_status=409,
            blocked_fields=hash_mismatches,
        )
    material_snapshot_id = _text(payload.get("material_snapshot_id"))
    material_snapshot = db.get(L3MaterialSnapshot, material_snapshot_id)
    if material_snapshot is None:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_material_snapshot_not_found",
            "No material snapshot exists for the supplied source-directory authority.",
            status="not_found",
            http_status=404,
            blocked_fields=["material_snapshot_id"],
        )
    session = db.get(L3Session, material_snapshot.session_id)
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == _text(payload.get("reconciliation_record_id")),
            L3ReconciliationRecord.session_id == material_snapshot.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if session is None or reconciliation is None:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_requires_existing_authority",
            "Source-directory internal webhook dispatch requires existing session and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["material_snapshot_id", "reconciliation_record_id"],
        )
    packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session.session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation.reconciliation_record_id,
        )
        .with_for_update()
        .all()
    )
    expected_kinds = list(layer3_source_directory_hybrid_analysis.PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    if len(packages) != len(expected_kinds) or {package.package_kind for package in packages} != set(expected_kinds):
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_requires_complete_package_set",
            "Source-directory internal webhook dispatch requires the complete recorded package set.",
            status="blocked",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    review_order = {kind: index for index, kind in enumerate(expected_kinds)}
    packages = sorted(packages, key=lambda package: review_order[package.package_kind])
    return session, reconciliation, material_snapshot, packages, qualitative


def _validate_readiness(
    payload: Mapping[str, Any],
    *,
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    qualitative: Mapping[str, Any],
) -> dict[str, Any]:
    summary = reconciliation.summary_json if isinstance(reconciliation.summary_json, dict) else {}
    readiness = summary.get("external_export_download_prepare")
    if not isinstance(readiness, dict):
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_requires_external_export_download_prepare",
            "Source-directory internal webhook dispatch requires recorded external export/download readiness.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    supplied_package_ids = _string_list(payload, "output_package_ids")
    supplied_package_kinds = _string_list(payload, "package_kinds")
    supplied_payload_hashes = _string_list(payload, "payload_hashes")
    mismatches = [
        field
        for field, expected in {
            "external_export_download_record_ref": _text(payload.get("external_export_download_record_ref")),
            "export_download_descriptor_ref": _text(payload.get("export_download_descriptor_ref")),
            "external_export_download_state": _text(payload.get("external_export_download_state")),
            "external_export_download_target": _text(payload.get("external_export_download_target")),
            "download_mode": _text(payload.get("download_mode")),
            "package_review_submit_record_ref": _text(payload.get("package_review_submit_record_ref")),
            "package_review_state": _text(payload.get("package_review_state")),
            "prepare_record_ref": _text(payload.get("prepare_record_ref")),
            "handoff_export_state": _text(payload.get("handoff_export_state")),
            "handoff_export_envelope_ref": _text(payload.get("handoff_export_envelope_ref")),
            "construction_basis_hash": _text(payload.get("construction_basis_hash")),
            "package_review_preview_hash": _text(
                payload.get("source_directory_hybrid_package_review_preview_hash")
            ),
            "qualitative_analysis_hash": _text(payload.get("qualitative_analysis_hash")),
            "hybrid_context_packet_hash": _text(qualitative.get("hybrid_context_packet_hash")),
            "embedding_index_authority_hash": _text(qualitative.get("embedding_index_authority_hash")),
        }.items()
        if _text(readiness.get(field) or (readiness.get("authority_basis") or {}).get(field)) != expected
    ]
    if supplied_package_ids != expected_package_ids:
        mismatches.append("output_package_ids")
    if supplied_package_kinds != expected_package_kinds:
        mismatches.append("package_kinds")
    if supplied_payload_hashes != expected_payload_hashes:
        mismatches.append("payload_hashes")
    if mismatches:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_readiness_mismatch",
            "Recorded external export/download readiness does not match the supplied internal webhook basis.",
            status="conflict",
            http_status=409,
            blocked_fields=sorted(set(mismatches)),
        )
    return readiness


def _authority_basis(
    payload: Mapping[str, Any],
    *,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    readiness: Mapping[str, Any],
    qualitative: Mapping[str, Any],
    destination_url: str,
) -> dict[str, Any]:
    package_ids = [package.output_package_id for package in packages]
    package_kinds = [package.package_kind for package in packages]
    payload_hashes = [package.payload_hash for package in packages]
    package_set_hash = stable_hash(
        {
            "schema_id": "layer3.source_directory_internal_webhook.package_set.v1",
            "output_package_ids": package_ids,
            "package_kinds": package_kinds,
            "payload_hashes": payload_hashes,
        }
    )
    return {
        "schema_id": "layer3.source_directory_internal_webhook.authority.v1",
        "source_gate": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_SOURCE_GATE,
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": _text(payload.get("source_ingestion_batch_id")),
        "source_ingestion_file_id": _text(payload.get("source_ingestion_file_id")),
        "content_sha256": _text(payload.get("content_sha256")),
        "file_identity_hash": _text(payload.get("file_identity_hash")),
        "authority_basis_hash": _text(payload.get("authority_basis_hash")),
        "payload_hash": _text(payload.get("payload_hash")),
        "index_authority_hash": _text(payload.get("index_authority_hash")),
        "embedding_index_authority_hash": _text(payload.get("embedding_index_authority_hash")),
        "hybrid_context_packet_hash": _text(qualitative.get("hybrid_context_packet_hash")),
        "qualitative_analysis_hash": _text(payload.get("qualitative_analysis_hash")),
        "package_review_preview_hash": _text(
            payload.get("source_directory_hybrid_package_review_preview_hash")
        ),
        "construction_basis_hash": _text(payload.get("construction_basis_hash")),
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "package_review_submit_record_ref": _text(payload.get("package_review_submit_record_ref")),
        "prepare_record_ref": _text(payload.get("prepare_record_ref")),
        "handoff_export_envelope_ref": _text(payload.get("handoff_export_envelope_ref")),
        "external_export_download_record_ref": _text(payload.get("external_export_download_record_ref")),
        "export_download_descriptor_ref": _text(payload.get("export_download_descriptor_ref")),
        "output_package_ids": package_ids,
        "package_kinds": package_kinds,
        "payload_hashes": payload_hashes,
        "package_set_hash": package_set_hash,
        "external_export_download_authority_basis": json_clone(readiness.get("authority_basis") or {}),
        "target_identity": _TARGET_IDENTITY,
        "target_class": _TARGET_CLASS,
        "dispatch_mode": _DISPATCH_MODE,
        "redacted_destination_display_name": layer3_internal_webhook_connector._destination_display_name(),
        "destination_url_hash": stable_hash(
            {"schema_id": "layer3.source_directory_internal_webhook.url_hash.v1", "url": destination_url}
        ),
    }


def _request_basis_hash(*, authority_basis_hash: str, client_request_id: str) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.source_directory_internal_webhook.request_basis.v1",
            "authority_basis_hash": authority_basis_hash,
            "client_request_id": client_request_id,
            "target_identity": _TARGET_IDENTITY,
            "target_class": _TARGET_CLASS,
            "dispatch_mode": _DISPATCH_MODE,
        }
    )


def _latest_audit(
    db: Session,
    receipt_id: str,
) -> L3SourceDirectoryInternalWebhookDispatchAuditEvent | None:
    return (
        db.query(L3SourceDirectoryInternalWebhookDispatchAuditEvent)
        .filter(
            L3SourceDirectoryInternalWebhookDispatchAuditEvent.source_directory_internal_webhook_dispatch_receipt_id
            == receipt_id
        )
        .order_by(L3SourceDirectoryInternalWebhookDispatchAuditEvent.created_at.desc())
        .first()
    )


def _record_audit(
    *,
    db: Session,
    row: L3SourceDirectoryInternalWebhookDispatchReceipt,
    event_type: str,
    event_status: str,
    reason_code: str,
    request_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> L3SourceDirectoryInternalWebhookDispatchAuditEvent:
    audit = L3SourceDirectoryInternalWebhookDispatchAuditEvent(
        source_directory_internal_webhook_dispatch_receipt_id=(
            row.source_directory_internal_webhook_dispatch_receipt_id
        ),
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


def _audit_receipt(
    row: L3SourceDirectoryInternalWebhookDispatchReceipt,
    audit: L3SourceDirectoryInternalWebhookDispatchAuditEvent | None,
) -> dict[str, Any]:
    return {
        "schema_id": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_AUDIT_SCHEMA_ID,
        "source_directory_internal_webhook_dispatch_receipt_id": (
            row.source_directory_internal_webhook_dispatch_receipt_id
        ),
        "source_directory_internal_webhook_dispatch_audit_event_id": (
            audit.source_directory_internal_webhook_dispatch_audit_event_id if audit else None
        ),
        "authority_basis_hash": row.authority_basis_hash,
        "redacted_destination_display_name": row.redacted_destination_display_name,
        "raw_target_url_exposed": False,
        "raw_token_exposed": False,
        "raw_headers_exposed": False,
        "raw_package_payload_exposed": False,
        "raw_package_bytes_exposed": False,
        "connector_run_created": False,
        "provider_public_url_enabled": False,
        "provider_private_signed_url_enabled": False,
    }


def _delivery_envelope(row: L3SourceDirectoryInternalWebhookDispatchReceipt) -> dict[str, Any]:
    authority = json_clone(row.authority_snapshot_json or {})
    return {
        "schema_id": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DELIVERY_ENVELOPE_SCHEMA_ID,
        "schema_version": 1,
        "source_gate": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_SOURCE_GATE,
        "session_id": row.session_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "material_snapshot_id": row.material_snapshot_id,
        "source_ingestion_batch_id": row.source_ingestion_batch_id,
        "source_ingestion_file_id": row.source_ingestion_file_id,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "export_download_descriptor_ref": row.export_download_descriptor_ref,
        "handoff_export_prepare_ref": row.handoff_export_prepare_ref,
        "handoff_export_envelope_ref": row.handoff_export_envelope_ref,
        "output_package_ids": json_clone(row.output_package_ids_json),
        "package_kinds": json_clone(row.package_kinds_json),
        "payload_hashes": json_clone(row.payload_hashes_json),
        "package_set_hash": authority.get("package_set_hash"),
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


def _response(
    *,
    schema_id: str,
    request_id: str,
    status: str,
    operation_state: str,
    row: L3SourceDirectoryInternalWebhookDispatchReceipt,
    audit: L3SourceDirectoryInternalWebhookDispatchAuditEvent | None,
) -> dict[str, Any]:
    authority = json_clone(row.authority_snapshot_json or {})
    return {
        **base_response(schema_id, request_id=request_id, status=status),
        "session_id": row.session_id,
        "selection_manifest_id": authority.get("selection_manifest_id"),
        "material_snapshot_id": row.material_snapshot_id,
        "source_ingestion_batch_id": row.source_ingestion_batch_id,
        "source_ingestion_file_id": row.source_ingestion_file_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "source_directory_internal_webhook_dispatch_receipt_id": (
            row.source_directory_internal_webhook_dispatch_receipt_id
        ),
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "export_download_descriptor_ref": row.export_download_descriptor_ref,
        "package_review_submit_record_ref": row.package_review_submit_record_ref,
        "handoff_export_prepare_ref": row.handoff_export_prepare_ref,
        "handoff_export_envelope_ref": row.handoff_export_envelope_ref,
        "output_package_ids": json_clone(row.output_package_ids_json),
        "package_kinds": json_clone(row.package_kinds_json),
        "payload_hashes": json_clone(row.payload_hashes_json),
        "package_set_hash": authority.get("package_set_hash"),
        "target_identity": row.target_identity,
        "target_class": row.target_class,
        "dispatch_mode": row.dispatch_mode,
        "source_directory_internal_webhook_dispatch_state": row.dispatch_status,
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
        "source_directory_internal_webhook_post_performed": (
            row.dispatch_status == SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCHED_STATE
        ),
        "real_connector_invocation_enabled": True,
        "server_configured_allowlisted_url_enabled": True,
        "operator_destination_url_enabled": False,
        "raw_target_url_exposed": False,
        "raw_token_exposed": False,
        "raw_headers_exposed": False,
        "raw_local_path_exposed": False,
        "raw_package_payload_exposed": False,
        "raw_package_bytes_exposed": False,
        "connector_dispatch_enabled": False,
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
        "internal_webhook_network_egress_enabled": True,
        "external_provider_network_enabled": False,
        "auth_security_implementation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
        "rendered_write_submit_control_enabled": False,
        "downstream_unavailable": list(SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": ["inspect_source_directory_internal_webhook_dispatch_status"],
        "next_state": row.dispatch_status,
    }


def _redacted_response_summary(status_code: int, body: Any) -> dict[str, Any]:
    return layer3_internal_webhook_connector._redacted_response_summary(status_code, body)


def dispatch_source_directory_internal_webhook(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _text(payload.get("client_request_id"))
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for source-directory internal webhook dispatch.",
            status="invalid",
            blocked_fields=["client_request_id"],
        )
    blocked = _blocked_fields(payload)
    if blocked:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_scope_not_admitted",
            "Source-directory internal webhook request includes non-admitted fields.",
            status="invalid",
            blocked_fields=blocked,
        )
    missing = _missing_fields(payload)
    if missing:
        raise Layer3WorkbenchError(
            "missing_source_directory_internal_webhook_fields",
            "Source-directory internal webhook request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
        )
    _require_fixed_values(payload)
    destination_url = layer3_internal_webhook_connector._configured_destination_url()
    session, reconciliation, material_snapshot, packages, qualitative = _load_authority(db, payload)
    readiness = _validate_readiness(
        payload,
        reconciliation=reconciliation,
        packages=packages,
        qualitative=qualitative,
    )
    basis = _authority_basis(
        payload,
        session=session,
        material_snapshot=material_snapshot,
        reconciliation=reconciliation,
        packages=packages,
        readiness=readiness,
        qualitative=qualitative,
        destination_url=destination_url,
    )
    authority_basis_hash = stable_hash(basis)
    request_basis_hash = _request_basis_hash(
        authority_basis_hash=authority_basis_hash,
        client_request_id=request_id,
    )
    existing_by_client = (
        db.query(L3SourceDirectoryInternalWebhookDispatchReceipt)
        .filter(L3SourceDirectoryInternalWebhookDispatchReceipt.client_request_id == request_id)
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
                schema_id=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID,
                request_id=request_id,
                status="already_recorded",
                operation_state=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_REPLAY_STATE,
                row=existing_by_client,
                audit=audit,
            )
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_client_request_conflict",
            "client_request_id already belongs to a different source-directory internal webhook basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing_by_basis = (
        db.query(L3SourceDirectoryInternalWebhookDispatchReceipt)
        .filter(L3SourceDirectoryInternalWebhookDispatchReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        audit = _record_audit(
            db=db,
            row=existing_by_basis,
            event_type="dispatch",
            event_status="accepted",
            reason_code="same_source_directory_basis_dispatch_reused",
            request_id=request_id,
            payload={"new_client_request_id": request_id},
        )
        db.commit()
        db.refresh(existing_by_basis)
        db.refresh(audit)
        return _response(
            schema_id=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID,
            request_id=request_id,
            status="already_recorded",
            operation_state=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_REPLAY_STATE,
            row=existing_by_basis,
            audit=audit,
        )

    now = utcnow()
    receipt_id = stable_id(SOURCE_DIRECTORY_INTERNAL_WEBHOOK_RECEIPT_ID_PREFIX, request_basis_hash, digest_chars=30)
    row = L3SourceDirectoryInternalWebhookDispatchReceipt(
        source_directory_internal_webhook_dispatch_receipt_id=receipt_id,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
        material_snapshot_id=material_snapshot.material_snapshot_id,
        source_ingestion_batch_id=_text(payload.get("source_ingestion_batch_id")),
        source_ingestion_file_id=_text(payload.get("source_ingestion_file_id")),
        client_request_id=request_id,
        external_export_download_record_ref=_text(payload.get("external_export_download_record_ref")),
        export_download_descriptor_ref=_text(payload.get("export_download_descriptor_ref")),
        package_review_submit_record_ref=_text(payload.get("package_review_submit_record_ref")),
        handoff_export_prepare_ref=_text(payload.get("prepare_record_ref")),
        handoff_export_envelope_ref=_text(payload.get("handoff_export_envelope_ref")),
        target_identity=_TARGET_IDENTITY,
        target_class=_TARGET_CLASS,
        dispatch_mode=_DISPATCH_MODE,
        redacted_destination_display_name=layer3_internal_webhook_connector._destination_display_name(),
        idempotency_key=request_id,
        request_basis_hash=request_basis_hash,
        authority_basis_hash=authority_basis_hash,
        dispatch_status=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_FAILED_STATE,
        response_status_code=None,
        redacted_response_summary_json={},
        failure_code=None,
        output_package_ids_json=[package.output_package_id for package in packages],
        package_kinds_json=[package.package_kind for package in packages],
        payload_hashes_json=[package.payload_hash for package in packages],
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
        reason_code="source_directory_authority_validated_internal_webhook_post_attempted",
        payload={"redacted_destination_display_name": row.redacted_destination_display_name},
    )
    envelope = _delivery_envelope(row)
    headers = {
        "Content-Type": "application/json",
        "X-Layer3-Envelope-Schema": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DELIVERY_ENVELOPE_SCHEMA_ID,
    }
    try:
        status_code, response_body = layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT(
            destination_url,
            envelope,
            headers,
            5.0,
        )
    except Layer3WorkbenchError as exc:
        row.dispatch_status = SOURCE_DIRECTORY_INTERNAL_WEBHOOK_FAILED_STATE
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
        row.dispatch_status = SOURCE_DIRECTORY_INTERNAL_WEBHOOK_FAILED_STATE
        row.response_status_code = status_code
        row.failure_code = "source_directory_internal_webhook_non_success_response"
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
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_non_success_response",
            "Source-directory internal webhook dispatch did not return an accepted 2xx response.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_configured_internal_webhook_destination"],
        )

    row.dispatch_status = SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCHED_STATE
    row.response_status_code = status_code
    row.redacted_response_summary_json = _redacted_response_summary(status_code, response_body)
    row.failure_code = None
    row.updated_at = utcnow()
    audit = _record_audit(
        db=db,
        row=row,
        event_type="dispatch",
        event_status="accepted",
        reason_code="source_directory_internal_webhook_post_completed",
        payload=row.redacted_response_summary_json,
    )
    summary_state = {
        "schema_id": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_STATE_SCHEMA_ID,
        "source_directory_internal_webhook_dispatch_receipt_id": receipt_id,
        "state": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCHED_STATE,
        "session_id": row.session_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "material_snapshot_id": row.material_snapshot_id,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "export_download_descriptor_ref": row.export_download_descriptor_ref,
        "package_set_hash": basis["package_set_hash"],
        "target_identity": row.target_identity,
        "target_class": row.target_class,
        "dispatch_mode": row.dispatch_mode,
        "redacted_destination_display_name": row.redacted_destination_display_name,
        "authority_basis_hash": row.authority_basis_hash,
        "request_basis_hash": row.request_basis_hash,
        "response_status_code": row.response_status_code,
        "record_source_gate": SOURCE_DIRECTORY_INTERNAL_WEBHOOK_SOURCE_GATE,
        "server_configured_internal_webhook_enabled": True,
        "source_directory_internal_webhook_post_performed": True,
        "connector_dispatch_enabled": False,
        "connector_run_created": False,
        "credentials_enabled": False,
        "provider_public_url_enabled": False,
        "provider_private_signed_url_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "frontend_durable_authority_enabled": False,
    }
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "source_directory_internal_webhook_dispatch": summary_state,
    }
    session.summary_json = {
        **json_clone(session.summary_json or {}),
        "source_directory_internal_webhook_dispatch": summary_state,
    }
    db.commit()
    db.refresh(row)
    db.refresh(audit)
    return _response(
        schema_id=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCH_SCHEMA_ID,
        request_id=request_id,
        status="dispatched",
        operation_state=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_DISPATCHED_STATE,
        row=row,
        audit=audit,
    )


def source_directory_internal_webhook_status(
    db: Session,
    source_directory_internal_webhook_dispatch_receipt_id: str,
) -> dict[str, Any]:
    receipt_id = _text(source_directory_internal_webhook_dispatch_receipt_id)
    if not receipt_id:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_dispatch_receipt_id_required",
            "source_directory_internal_webhook_dispatch_receipt_id is required.",
            status="invalid",
            blocked_fields=["source_directory_internal_webhook_dispatch_receipt_id"],
        )
    row = (
        db.query(L3SourceDirectoryInternalWebhookDispatchReceipt)
        .filter(
            L3SourceDirectoryInternalWebhookDispatchReceipt.source_directory_internal_webhook_dispatch_receipt_id
            == receipt_id
        )
        .one_or_none()
    )
    if row is None:
        raise Layer3WorkbenchError(
            "source_directory_internal_webhook_dispatch_not_recorded",
            "Source-directory internal webhook dispatch receipt has no durable server-side state.",
            status="not_found",
            http_status=404,
            blocked_fields=["source_directory_internal_webhook_dispatch_receipt_id"],
        )
    return _response(
        schema_id=SOURCE_DIRECTORY_INTERNAL_WEBHOOK_STATUS_SCHEMA_ID,
        request_id=f"status-{receipt_id}",
        status="ok",
        operation_state=row.dispatch_status,
        row=row,
        audit=_latest_audit(db, receipt_id),
    )
