from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3ConnectorLocalDestinationReceipt,
    L3ExternalLocalExportAuditEvent,
    L3ExternalLocalExportReceipt,
    L3LocalOutboxProviderPrivateHandoffReceipt,
    L3PassRun,
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3ServerOwnedLocalOutboxWriteReceipt,
    L3Session,
)
from app.services import (
    layer3_connector_dispatch_entry,
    layer3_local_outbox_provider_private_handoff,
    layer3_server_owned_local_outbox_target,
    layer3_server_owned_local_outbox_write,
    layer3_workbench,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow


EXTERNAL_LOCAL_EXPORT_WRITE_SCHEMA_ID = "layer3.external_local_export.write.v1"
EXTERNAL_LOCAL_EXPORT_STATUS_SCHEMA_ID = "layer3.external_local_export.status.v1"
EXTERNAL_LOCAL_EXPORT_AUDIT_SCHEMA_ID = "layer3.external_local_export.audit.v1"
EXTERNAL_LOCAL_EXPORT_STATE_SCHEMA_ID = "layer3.external_local_export.state.v1"
EXTERNAL_LOCAL_EXPORT_SOURCE_GATE = "626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE"
EXTERNAL_LOCAL_EXPORT_TARGET_IDENTITY = "server_configured_external_local_export_directory"
EXTERNAL_LOCAL_EXPORT_TARGET_CLASS = "server_configured_external_destination_write"
EXTERNAL_LOCAL_EXPORT_DISPATCH_MODE = "server_configured_external_local_export_directory_write"
EXTERNAL_LOCAL_EXPORT_OPERATOR_DECISION = "write_server_configured_external_local_export_directory"
EXTERNAL_LOCAL_EXPORT_RECEIPT_ID_PREFIX = "l3ele"
EXTERNAL_LOCAL_EXPORT_DESTINATION_LABEL = "server_configured_external_local_export_directory"

EXTERNAL_LOCAL_EXPORT_NOT_READY_STATE = "external_local_export_not_ready"
EXTERNAL_LOCAL_EXPORT_READY_STATE = "external_local_export_ready"
EXTERNAL_LOCAL_EXPORT_WRITTEN_STATE = "external_local_export_written"
EXTERNAL_LOCAL_EXPORT_REPLAY_STATE = "external_local_export_replay"
EXTERNAL_LOCAL_EXPORT_CONFLICT_STATE = "external_local_export_conflict"
EXTERNAL_LOCAL_EXPORT_STALE_AUTHORITY_STATE = "external_local_export_stale_authority"
EXTERNAL_LOCAL_EXPORT_FAILED_STATE = "external_local_export_failed"

EXTERNAL_LOCAL_EXPORT_REQUIRED_FIELDS = frozenset(
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
    }
)
EXTERNAL_LOCAL_EXPORT_OPTIONAL_FIELDS = frozenset(
    {"provider_private_handoff_receipt_id", "decision_notes"}
)
EXTERNAL_LOCAL_EXPORT_ALLOWED_FIELDS = EXTERNAL_LOCAL_EXPORT_REQUIRED_FIELDS | EXTERNAL_LOCAL_EXPORT_OPTIONAL_FIELDS
EXTERNAL_LOCAL_EXPORT_FORBIDDEN_FIELDS = frozenset(
    {
        "destination_path",
        "destination_url",
        "destination_id",
        "destination",
        "destination_selector",
        "local_path",
        "local_file_path",
        "local_directory",
        "bucket",
        "object_key",
        "provider_url",
        "provider_public_url",
        "provider_public_delivery",
        "public_url",
        "signed_url",
        "download_url",
        "raw_token",
        "provider_token",
        "provider_credentials",
        "connector_key",
        "connector_payload",
        "connector_secret",
        "connector_run_id",
        "connector_run_target_id",
        "credentials",
        "credential",
        "network_write",
        "external_connector_invocation",
        "package_mutation",
        "package_payload",
        "package_variant_content",
        "rebuild_package",
        "rewrite_output",
        "source_upload",
        "source_expansion",
        "web_connector",
        "rag_vector_index",
        "rag_vector_state",
        "prompt_model_settings",
        "prompt_or_model_payload",
        "auth_security_override",
        "auth_policy",
        "security_override",
        "browser_durable_authority",
        "frontend_durable_authority",
        "full_mockup_activation",
        "retry",
        "rerun",
        "cancel",
    }
)
EXTERNAL_LOCAL_EXPORT_DOWNSTREAM_UNAVAILABLE = (
    "real_connector_invocation",
    "connector_run_creation",
    "connector_run_target_creation",
    "credentials",
    "network_egress",
    "provider_public_delivery_use",
    "raw_public_url_exposure",
    "raw_token_use",
    "package_mutation_reconstruction",
    "source_expansion",
    "rag_vector",
    "qualitative_hybrid_analysis_runtime",
    "auth_security_implementation",
    "full_mockup_activation",
    "frontend_durable_authority",
    "generic_downstream_dispatch",
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_to(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def _configured_root() -> Path:
    raw = _string(getattr(settings, "layer3_external_local_export_dir", ""))
    if not raw:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_not_configured",
            "Server-configured external local export directory is not configured.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        )
    root = Path(raw)
    if not root.is_absolute():
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_not_absolute",
            "Server-configured external local export directory must be absolute.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        )
    resolved = root.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_unsafe_root",
            "Server-configured external local export directory cannot be a filesystem root.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        )
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    outbox_root = Path(settings.layer3_local_outbox_dir).resolve(strict=False)
    if resolved == storage_root or _relative_to(resolved, storage_root):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_inside_storage",
            "Server-configured external local export directory must be outside app-owned storage.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        )
    if resolved == outbox_root or _relative_to(resolved, outbox_root):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_inside_outbox",
            "Server-configured external local export directory must be outside app-owned local outbox staging.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        )
    try:
        resolved.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_unavailable",
            "Server-configured external local export directory is not writable.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        ) from exc
    return resolved


def _outbox_path(relative_ref: str) -> Path:
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    outbox_root = Path(settings.layer3_local_outbox_dir).resolve(strict=False)
    resolved = (storage_root / relative_ref).resolve(strict=False)
    if not _relative_to(resolved, outbox_root):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_source_path_escape",
            "External local export may read only server-owned local outbox refs.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )
    return resolved


def _target_paths(receipt_id: str) -> tuple[Path, Path]:
    root = _configured_root()
    artifact_path = (root / receipt_id / "artifact.json").resolve(strict=False)
    manifest_path = (root / receipt_id / "manifest.json").resolve(strict=False)
    if not _relative_to(artifact_path, root) or not _relative_to(manifest_path, root):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_path_escape",
            "External local export target path escaped the server-configured directory.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        )
    return artifact_path, manifest_path


def _redacted_ref(receipt_id: str, filename: str) -> str:
    return f"external-local-export://{receipt_id}/{filename}"


def _write_bytes_atomic(*, source_path: Path, target_path: Path, expected_hash: str, expected_size: int) -> None:
    tmp_path: Path | None = None
    try:
        if target_path.exists():
            if _file_sha256(target_path) == expected_hash and int(target_path.stat().st_size) == expected_size:
                return
            raise layer3_workbench.Layer3WorkbenchError(
                "external_local_export_existing_output_conflict",
                "Existing external local export output conflicts with the validated source bytes.",
                status="conflict",
                http_status=409,
                blocked_fields=["server_configured_external_local_export_directory"],
            )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(target_path.parent), prefix="._", suffix=".tmp")
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as target, source_path.open("rb") as source:
            shutil.copyfileobj(source, target)
        if _file_sha256(tmp_path) != expected_hash or int(tmp_path.stat().st_size) != expected_size:
            tmp_path.unlink(missing_ok=True)
            raise layer3_workbench.Layer3WorkbenchError(
                "external_local_export_verification_failed",
                "External local export copied bytes did not match the durable outbox receipt.",
                status="conflict",
                http_status=409,
                blocked_fields=["server_owned_local_outbox_write_receipt_id"],
            )
        os.replace(tmp_path, target_path)
    except layer3_workbench.Layer3WorkbenchError:
        raise
    except OSError as exc:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_directory_unavailable",
            "Server-configured external local export directory is not writable.",
            status="blocked",
            http_status=409,
            blocked_fields=["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"],
        ) from exc


def _verify_existing_row(row: L3ExternalLocalExportReceipt) -> None:
    artifact_path, manifest_path = _target_paths(row.external_local_export_receipt_id)
    checks = (
        (artifact_path, row.external_artifact_hash, row.external_artifact_size_bytes),
        (manifest_path, row.external_manifest_hash, row.external_manifest_size_bytes),
    )
    for path, expected_hash, expected_size in checks:
        if not path.exists() or not path.is_file():
            raise layer3_workbench.Layer3WorkbenchError(
                "external_local_export_output_missing",
                "Recorded external local export output is missing.",
                status="conflict",
                http_status=409,
                blocked_fields=["external_local_export_receipt_id"],
            )
        if _file_sha256(path) != expected_hash or int(path.stat().st_size) != int(expected_size):
            raise layer3_workbench.Layer3WorkbenchError(
                "external_local_export_output_hash_mismatch",
                "Recorded external local export output no longer matches its durable receipt.",
                status="conflict",
                http_status=409,
                blocked_fields=["external_local_export_receipt_id"],
            )


def _blocked_fields(payload: dict[str, Any]) -> list[str]:
    unknown = sorted(key for key in payload if key not in EXTERNAL_LOCAL_EXPORT_ALLOWED_FIELDS)
    forbidden = sorted(key for key in EXTERNAL_LOCAL_EXPORT_FORBIDDEN_FIELDS if key in payload)
    return sorted(set(unknown) | set(forbidden))


def _missing_fields(payload: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field in EXTERNAL_LOCAL_EXPORT_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )


def _latest_audit(
    db: Session,
    receipt_id: str,
) -> L3ExternalLocalExportAuditEvent | None:
    return (
        db.query(L3ExternalLocalExportAuditEvent)
        .filter(L3ExternalLocalExportAuditEvent.external_local_export_receipt_id == receipt_id)
        .order_by(L3ExternalLocalExportAuditEvent.created_at.desc())
        .first()
    )


def _audit_receipt(row: L3ExternalLocalExportReceipt, audit: L3ExternalLocalExportAuditEvent | None) -> dict[str, Any]:
    return {
        "schema_id": EXTERNAL_LOCAL_EXPORT_AUDIT_SCHEMA_ID,
        "external_local_export_receipt_id": row.external_local_export_receipt_id,
        "external_local_export_audit_event_id": audit.external_local_export_audit_event_id if audit else None,
        "authority_basis_hash": row.authority_basis_hash,
        "redacted_destination_label": EXTERNAL_LOCAL_EXPORT_DESTINATION_LABEL,
        "real_connector_invocation_enabled": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "network_egress_enabled": False,
        "provider_public_delivery_enabled": False,
        "raw_public_url_exposed": False,
        "raw_token_exposed": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "auth_security_implementation_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "generic_downstream_dispatch_enabled": False,
    }


def _response(
    *,
    schema_id: str,
    request_id: str,
    status: str,
    operation_state: str,
    row: L3ExternalLocalExportReceipt,
    audit: L3ExternalLocalExportAuditEvent | None,
) -> dict[str, Any]:
    return {
        **base_response(schema_id, request_id=request_id, status=status),
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "external_local_export_receipt_id": row.external_local_export_receipt_id,
        "server_owned_local_outbox_write_receipt_id": row.server_owned_local_outbox_write_receipt_id,
        "server_owned_local_outbox_target_receipt_id": row.server_owned_local_outbox_target_receipt_id,
        "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
        "provider_private_handoff_receipt_id": row.provider_private_handoff_receipt_id,
        "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "target_identity": row.target_identity,
        "target_class": row.target_class,
        "dispatch_mode": row.dispatch_mode,
        "external_local_export_state": row.export_state,
        "export_operation_state": operation_state,
        "redacted_destination_label": row.redacted_destination_label,
        "external_artifact_ref": row.external_artifact_ref,
        "external_manifest_ref": row.external_manifest_ref,
        "external_artifact_hash": row.external_artifact_hash,
        "external_artifact_size_bytes": row.external_artifact_size_bytes,
        "external_manifest_hash": row.external_manifest_hash,
        "external_manifest_size_bytes": row.external_manifest_size_bytes,
        "source_outbox_artifact_ref": _redacted_ref(row.external_local_export_receipt_id, "source-artifact-redacted"),
        "source_outbox_artifact_hash": row.source_outbox_artifact_hash,
        "source_outbox_artifact_size_bytes": row.source_outbox_artifact_size_bytes,
        "authority_basis_hash": row.authority_basis_hash,
        "idempotency_key": row.idempotency_key,
        "audit_receipt": _audit_receipt(row, audit),
        "server_configured_external_local_export_write_enabled": True,
        "server_configured_external_local_export_write_performed": row.export_state == EXTERNAL_LOCAL_EXPORT_WRITTEN_STATE,
        "external_destination_write_enabled": True,
        "operator_destination_path_enabled": False,
        "real_connector_invocation_enabled": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "network_egress_enabled": False,
        "provider_public_delivery_enabled": False,
        "raw_public_url_exposed": False,
        "raw_token_exposed": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "qualitative_hybrid_analysis_runtime_enabled": False,
        "auth_security_implementation_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_LOCAL_EXPORT_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": ["inspect_external_local_export_status"],
        "next_state": row.export_state,
    }


def _authority_basis(
    *,
    payload: dict[str, Any],
    write_row: L3ServerOwnedLocalOutboxWriteReceipt,
    target_row: L3ServerOwnedLocalOutboxTargetReceipt,
    local_row: L3ConnectorLocalDestinationReceipt,
    provider_row: L3LocalOutboxProviderPrivateHandoffReceipt | None,
    manifest_hash: str,
    manifest_size: int,
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.external_local_export.authority.v1",
        "record_source_gate": EXTERNAL_LOCAL_EXPORT_SOURCE_GATE,
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": _string(payload.get("analysis_plan_id")),
        "pass_run_id": write_row.pass_run_id,
        "reconciliation_record_id": write_row.reconciliation_record_id,
        "connector_dispatch_record_ref": write_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": write_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": write_row.connector_local_destination_receipt_id,
        "server_owned_local_outbox_target_receipt_id": write_row.server_owned_local_outbox_target_receipt_id,
        "server_owned_local_outbox_write_receipt_id": write_row.server_owned_local_outbox_write_receipt_id,
        "provider_private_handoff_receipt_id": (
            provider_row.provider_private_handoff_receipt_id if provider_row is not None else None
        ),
        "server_owned_local_outbox_write_authority_basis_hash": write_row.authority_basis_hash,
        "server_owned_local_outbox_target_authority_basis_hash": target_row.authority_basis_hash,
        "connector_local_destination_receipt_authority_basis_hash": local_row.authority_basis_hash,
        "provider_private_handoff_authority_basis_hash": (
            provider_row.authority_basis_hash if provider_row is not None else None
        ),
        "target_identity": EXTERNAL_LOCAL_EXPORT_TARGET_IDENTITY,
        "target_class": EXTERNAL_LOCAL_EXPORT_TARGET_CLASS,
        "dispatch_mode": EXTERNAL_LOCAL_EXPORT_DISPATCH_MODE,
        "redacted_destination_label": EXTERNAL_LOCAL_EXPORT_DESTINATION_LABEL,
        "outbox_artifact_hash": write_row.outbox_artifact_hash,
        "outbox_artifact_size_bytes": write_row.outbox_artifact_size_bytes,
        "outbox_manifest_hash": manifest_hash,
        "outbox_manifest_size_bytes": manifest_size,
    }


def _validate_authority(
    db: Session,
    payload: dict[str, Any],
) -> tuple[
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxWriteReceipt,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3ConnectorLocalDestinationReceipt,
    L3LocalOutboxProviderPrivateHandoffReceipt | None,
]:
    if _string(payload.get("target_identity")) != EXTERNAL_LOCAL_EXPORT_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_target_identity_not_admitted",
            "target_identity must be server_configured_external_local_export_directory.",
            status="invalid",
            blocked_fields=["target_identity"],
        )
    if _string(payload.get("dispatch_mode")) != EXTERNAL_LOCAL_EXPORT_DISPATCH_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_dispatch_mode_not_admitted",
            "dispatch_mode must be server_configured_external_local_export_directory_write.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if _string(payload.get("operator_decision")) != EXTERNAL_LOCAL_EXPORT_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_external_local_export_decision",
            "operator_decision must be write_server_configured_external_local_export_directory.",
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
            "external_local_export_requires_existing_authority",
            "External local export requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_pass_run_mismatch",
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
            "external_local_export_requires_outbox_write",
            "External local export requires an existing server-owned local outbox write receipt.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )
    if write_row.write_state != layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_requires_recorded_outbox_write",
            "External local export requires server_owned_local_outbox_write_recorded state.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
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
    if target_row is None or local_row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_requires_receipt_chain",
            "External local export requires existing local receipt and server-owned local outbox target receipt.",
            status="blocked",
            http_status=409,
            blocked_fields=[
                "connector_local_destination_receipt_id",
                "server_owned_local_outbox_target_receipt_id",
            ],
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
                f"external_local_export_{field}_mismatch",
                f"Supplied {field} does not match recorded local outbox write authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )
    if target_row.target_identity != layer3_server_owned_local_outbox_target.SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_target_authority_not_admitted",
            "Local outbox target receipt identity is not admitted for external local export.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
        )
    if write_row.target_identity != layer3_server_owned_local_outbox_write.SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_write_authority_not_admitted",
            "Outbox write receipt target identity is not admitted for external local export.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )

    provider_row = None
    provider_receipt_id = _string(payload.get("provider_private_handoff_receipt_id"))
    latest_provider_row = (
        db.query(L3LocalOutboxProviderPrivateHandoffReceipt)
        .filter(
            L3LocalOutboxProviderPrivateHandoffReceipt.server_owned_local_outbox_write_receipt_id
            == write_row.server_owned_local_outbox_write_receipt_id,
            L3LocalOutboxProviderPrivateHandoffReceipt.session_id == session_id,
        )
        .order_by(L3LocalOutboxProviderPrivateHandoffReceipt.created_at.desc())
        .first()
    )
    if latest_provider_row is not None and not provider_receipt_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_requires_provider_private_handoff",
            "Provider-private handoff receipt is required when provider-private preparation exists for the outbox write.",
            status="blocked",
            http_status=409,
            blocked_fields=["provider_private_handoff_receipt_id"],
        )
    if provider_receipt_id:
        provider_row = (
            db.query(L3LocalOutboxProviderPrivateHandoffReceipt)
            .filter(
                L3LocalOutboxProviderPrivateHandoffReceipt.provider_private_handoff_receipt_id == provider_receipt_id,
                L3LocalOutboxProviderPrivateHandoffReceipt.server_owned_local_outbox_write_receipt_id
                == write_row.server_owned_local_outbox_write_receipt_id,
                L3LocalOutboxProviderPrivateHandoffReceipt.session_id == session_id,
            )
            .one_or_none()
        )
        if provider_row is None:
            raise layer3_workbench.Layer3WorkbenchError(
                "external_local_export_provider_private_handoff_mismatch",
                "Provider-private handoff receipt does not match the outbox write authority.",
                status="conflict",
                http_status=409,
                blocked_fields=["provider_private_handoff_receipt_id"],
            )
        if provider_row.target_identity != (
            layer3_local_outbox_provider_private_handoff.LOCAL_OUTBOX_PROVIDER_PRIVATE_TARGET_IDENTITY
        ):
            raise layer3_workbench.Layer3WorkbenchError(
                "external_local_export_provider_private_handoff_not_admitted",
                "Provider-private handoff receipt identity is not admitted for external local export.",
                status="conflict",
                http_status=409,
                blocked_fields=["provider_private_handoff_receipt_id"],
            )

    summary = reconciliation.summary_json if isinstance(reconciliation.summary_json, dict) else {}
    summary_write = summary.get("server_owned_local_outbox_write")
    summary_target = summary.get("server_owned_local_outbox_target")
    summary_local = summary.get("connector_local_destination_receipt")
    summary_connector = summary.get("connector_dispatch_record")
    summary_readiness = summary.get("external_export_download_prepare")
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
        or not isinstance(summary_readiness, dict)
        or summary_readiness.get("external_export_download_state")
        != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
    )
    if stale:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_stale_authority",
            "Recorded local outbox authority no longer matches durable receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )
    return reconciliation, write_row, target_row, local_row, provider_row


def write_external_local_export(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for external local export.",
            status="invalid",
            blocked_fields=["client_request_id"],
        )
    blocked = _blocked_fields(payload)
    if blocked:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_scope_not_admitted",
            "External local export request includes non-admitted fields: " + ", ".join(blocked) + ".",
            status="invalid",
            blocked_fields=blocked,
        )
    missing = _missing_fields(payload)
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_external_local_export_fields",
            "External local export request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
        )

    reconciliation, write_row, target_row, local_row, provider_row = _validate_authority(db, payload)
    source_artifact_path = _outbox_path(write_row.outbox_artifact_ref)
    source_manifest_path = _outbox_path(write_row.outbox_manifest_ref)
    if (
        not source_artifact_path.exists()
        or not source_manifest_path.exists()
        or _file_sha256(source_artifact_path) != write_row.outbox_artifact_hash
        or int(source_artifact_path.stat().st_size) != int(write_row.outbox_artifact_size_bytes)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_stale_authority",
            "Recorded server-owned local outbox bytes no longer match durable write receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_write_receipt_id"],
        )

    manifest_hash = _file_sha256(source_manifest_path)
    manifest_size = int(source_manifest_path.stat().st_size)
    basis = _authority_basis(
        payload=payload,
        write_row=write_row,
        target_row=target_row,
        local_row=local_row,
        provider_row=provider_row,
        manifest_hash=manifest_hash,
        manifest_size=manifest_size,
    )
    authority_basis_hash = stable_hash(basis)
    existing_by_client = (
        db.query(L3ExternalLocalExportReceipt)
        .filter(L3ExternalLocalExportReceipt.client_request_id == request_id)
        .one_or_none()
    )
    if existing_by_client is not None:
        if existing_by_client.authority_basis_hash == authority_basis_hash:
            _verify_existing_row(existing_by_client)
            return _response(
                schema_id=EXTERNAL_LOCAL_EXPORT_WRITE_SCHEMA_ID,
                request_id=request_id,
                status="already_recorded",
                operation_state=EXTERNAL_LOCAL_EXPORT_REPLAY_STATE,
                row=existing_by_client,
                audit=_latest_audit(db, existing_by_client.external_local_export_receipt_id),
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_client_request_conflict",
            "client_request_id already belongs to a different external local export authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing_by_basis = (
        db.query(L3ExternalLocalExportReceipt)
        .filter(L3ExternalLocalExportReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        _verify_existing_row(existing_by_basis)
        return _response(
            schema_id=EXTERNAL_LOCAL_EXPORT_WRITE_SCHEMA_ID,
            request_id=request_id,
            status="already_recorded",
            operation_state=EXTERNAL_LOCAL_EXPORT_REPLAY_STATE,
            row=existing_by_basis,
            audit=_latest_audit(db, existing_by_basis.external_local_export_receipt_id),
        )

    receipt_id = stable_id(EXTERNAL_LOCAL_EXPORT_RECEIPT_ID_PREFIX, authority_basis_hash, digest_chars=30)
    artifact_path, manifest_path = _target_paths(receipt_id)
    _write_bytes_atomic(
        source_path=source_artifact_path,
        target_path=artifact_path,
        expected_hash=write_row.outbox_artifact_hash,
        expected_size=int(write_row.outbox_artifact_size_bytes),
    )
    _write_bytes_atomic(
        source_path=source_manifest_path,
        target_path=manifest_path,
        expected_hash=manifest_hash,
        expected_size=manifest_size,
    )
    artifact_hash = _file_sha256(artifact_path)
    artifact_size = int(artifact_path.stat().st_size)
    copied_manifest_hash = _file_sha256(manifest_path)
    copied_manifest_size = int(manifest_path.stat().st_size)
    if artifact_hash != write_row.outbox_artifact_hash or artifact_size != int(write_row.outbox_artifact_size_bytes):
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_verification_failed",
            "External local export artifact did not verify after write.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_local_export_receipt_id"],
        )
    if copied_manifest_hash != manifest_hash or copied_manifest_size != manifest_size:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_manifest_verification_failed",
            "External local export manifest did not verify after write.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_local_export_receipt_id"],
        )

    now = utcnow()
    row = L3ExternalLocalExportReceipt(
        external_local_export_receipt_id=receipt_id,
        server_owned_local_outbox_write_receipt_id=write_row.server_owned_local_outbox_write_receipt_id,
        server_owned_local_outbox_target_receipt_id=write_row.server_owned_local_outbox_target_receipt_id,
        connector_local_destination_receipt_id=write_row.connector_local_destination_receipt_id,
        provider_private_handoff_receipt_id=(
            provider_row.provider_private_handoff_receipt_id if provider_row is not None else None
        ),
        session_id=write_row.session_id,
        pass_run_id=write_row.pass_run_id,
        reconciliation_record_id=write_row.reconciliation_record_id,
        client_request_id=request_id,
        connector_dispatch_record_ref=write_row.connector_dispatch_record_ref,
        external_export_download_record_ref=write_row.external_export_download_record_ref,
        target_identity=EXTERNAL_LOCAL_EXPORT_TARGET_IDENTITY,
        target_class=EXTERNAL_LOCAL_EXPORT_TARGET_CLASS,
        dispatch_mode=EXTERNAL_LOCAL_EXPORT_DISPATCH_MODE,
        export_state=EXTERNAL_LOCAL_EXPORT_WRITTEN_STATE,
        redacted_destination_label=EXTERNAL_LOCAL_EXPORT_DESTINATION_LABEL,
        external_artifact_ref=_redacted_ref(receipt_id, "artifact.json"),
        external_manifest_ref=_redacted_ref(receipt_id, "manifest.json"),
        external_artifact_hash=artifact_hash,
        external_artifact_size_bytes=artifact_size,
        external_manifest_hash=copied_manifest_hash,
        external_manifest_size_bytes=copied_manifest_size,
        source_outbox_artifact_hash=write_row.outbox_artifact_hash,
        source_outbox_artifact_size_bytes=write_row.outbox_artifact_size_bytes,
        authority_basis_hash=authority_basis_hash,
        idempotency_key=request_id,
        redacted_failure_code=None,
        authority_snapshot_json=json_clone(basis),
        created_by_request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    audit = L3ExternalLocalExportAuditEvent(
        external_local_export_receipt_id=receipt_id,
        event_type="write",
        event_status="accepted",
        request_id=request_id,
        authority_basis_hash=authority_basis_hash,
        reason_code="written_after_local_outbox_authority_validation",
        event_payload_json={
            "redacted_destination_label": EXTERNAL_LOCAL_EXPORT_DESTINATION_LABEL,
            "external_artifact_ref": row.external_artifact_ref,
            "external_manifest_ref": row.external_manifest_ref,
            "real_connector_invocation_enabled": False,
            "connector_run_created": False,
            "connector_run_target_created": False,
            "credentials_enabled": False,
            "network_egress_enabled": False,
            "provider_public_delivery_enabled": False,
        },
        created_at=now,
    )
    db.add_all([row, audit])
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "external_local_export": {
            "schema_id": EXTERNAL_LOCAL_EXPORT_STATE_SCHEMA_ID,
            "external_local_export_receipt_id": receipt_id,
            "external_local_export_state": EXTERNAL_LOCAL_EXPORT_WRITTEN_STATE,
            "server_owned_local_outbox_write_receipt_id": row.server_owned_local_outbox_write_receipt_id,
            "server_owned_local_outbox_target_receipt_id": row.server_owned_local_outbox_target_receipt_id,
            "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
            "provider_private_handoff_receipt_id": row.provider_private_handoff_receipt_id,
            "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
            "external_export_download_record_ref": row.external_export_download_record_ref,
            "target_identity": EXTERNAL_LOCAL_EXPORT_TARGET_IDENTITY,
            "target_class": EXTERNAL_LOCAL_EXPORT_TARGET_CLASS,
            "dispatch_mode": EXTERNAL_LOCAL_EXPORT_DISPATCH_MODE,
            "redacted_destination_label": EXTERNAL_LOCAL_EXPORT_DESTINATION_LABEL,
            "external_artifact_ref": row.external_artifact_ref,
            "external_manifest_ref": row.external_manifest_ref,
            "external_artifact_hash": row.external_artifact_hash,
            "external_artifact_size_bytes": row.external_artifact_size_bytes,
            "external_manifest_hash": row.external_manifest_hash,
            "external_manifest_size_bytes": row.external_manifest_size_bytes,
            "authority_basis_hash": authority_basis_hash,
            "record_source_gate": EXTERNAL_LOCAL_EXPORT_SOURCE_GATE,
            "server_configured_external_local_export_write_performed": True,
            "real_connector_invocation_enabled": False,
            "connector_run_created": False,
            "connector_run_target_created": False,
            "credentials_enabled": False,
            "network_egress_enabled": False,
            "provider_public_delivery_enabled": False,
        },
    }
    db.commit()
    db.refresh(row)
    db.refresh(audit)
    return _response(
        schema_id=EXTERNAL_LOCAL_EXPORT_WRITE_SCHEMA_ID,
        request_id=request_id,
        status="written",
        operation_state=EXTERNAL_LOCAL_EXPORT_WRITTEN_STATE,
        row=row,
        audit=audit,
    )


def external_local_export_status(db: Session, external_local_export_receipt_id: str) -> dict[str, Any]:
    receipt_id = _string(external_local_export_receipt_id)
    if not receipt_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_receipt_id_required",
            "external_local_export_receipt_id is required.",
            status="invalid",
            blocked_fields=["external_local_export_receipt_id"],
        )
    row = (
        db.query(L3ExternalLocalExportReceipt)
        .filter(L3ExternalLocalExportReceipt.external_local_export_receipt_id == receipt_id)
        .one_or_none()
    )
    if row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_local_export_not_recorded",
            "External local export receipt has no durable server-side state.",
            status="not_found",
            http_status=404,
            blocked_fields=["external_local_export_receipt_id"],
        )
    _verify_existing_row(row)
    return _response(
        schema_id=EXTERNAL_LOCAL_EXPORT_STATUS_SCHEMA_ID,
        request_id=f"external-local-export-status:{receipt_id}",
        status="ok",
        operation_state=row.export_state,
        row=row,
        audit=_latest_audit(db, receipt_id),
    )
