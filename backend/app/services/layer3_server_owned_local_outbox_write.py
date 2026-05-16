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
    layer3_workbench,
)
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow
from app.services.nrc_aps_evidence_bundle import EvidenceBundleError, load_persisted_bundle_artifact


SERVER_OWNED_LOCAL_OUTBOX_WRITE_SCHEMA_ID = "layer3.server_owned_local_outbox_write_receipt.v1"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATE_SCHEMA_ID = "layer3.server_owned_local_outbox_write_state.v1"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_SOURCE_GATE = "608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY = "server_owned_local_delivery_outbox_destination"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_DISPATCH_MODE = "server_owned_local_outbox_write_via_storage_dir"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_OPERATOR_DECISION = "write_server_owned_local_outbox"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECEIPT_ID_PREFIX = "l3solowr"
SERVER_OWNED_LOCAL_OUTBOX_STORAGE_DIRNAME = "layer3-outbox"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_REDACTED_SOURCE_REF = (
    "artifact://server-owned-local-outbox-source-redacted"
)
SERVER_OWNED_LOCAL_OUTBOX_WRITE_NOT_READY_STATE = "server_owned_local_outbox_write_not_ready"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_READY_STATE = "server_owned_local_outbox_write_ready"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE = "server_owned_local_outbox_write_recorded"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_REPLAY_STATE = "server_owned_local_outbox_write_replay"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_CONFLICT_STATE = "server_owned_local_outbox_write_conflict"
SERVER_OWNED_LOCAL_OUTBOX_WRITE_STALE_AUTHORITY_STATE = (
    "server_owned_local_outbox_write_stale_authority"
)
SERVER_OWNED_LOCAL_OUTBOX_WRITE_FAILED_STATE = "server_owned_local_outbox_write_failed"

SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "connector_local_destination_receipt_id",
        "server_owned_local_outbox_target_receipt_id",
        "server_owned_local_outbox_target_state",
        "external_export_download_record_ref",
        "target_identity",
        "dispatch_mode",
        "operator_decision",
    }
)
SERVER_OWNED_LOCAL_OUTBOX_WRITE_OPTIONAL_FIELDS = frozenset({"decision_notes"})
SERVER_OWNED_LOCAL_OUTBOX_WRITE_FORBIDDEN_FIELDS = frozenset(
    {
        "connector_key",
        "connector_run_id",
        "connector_run_target_id",
        "connector_secret",
        "destination_id",
        "destination_path",
        "destination_secret",
        "destination_url",
        "provider_url",
        "provider_public_url",
        "provider_public_delivery",
        "public_url",
        "signed_url",
        "download_url",
        "bucket",
        "object_key",
        "local_path",
        "local_file_path",
        "package_payload",
        "package_variant_content",
        "rebuild_package",
        "rewrite_output",
        "source_upload",
        "source_expansion",
        "local_directory",
        "rag_vector_index",
        "runtime_db_write",
        "retry",
        "rerun",
        "cancel",
        "hybrid_execution",
        "rag_execution",
        "hidden_llm_planning",
        "credential",
        "credentials",
        "network_write",
        "external_connector_invocation",
        "destination_write",
        "real_destination_integration",
        "auth_policy",
        "security_override",
        "frontend_durable_authority",
        "full_mockup_activation",
    }
)
SERVER_OWNED_LOCAL_OUTBOX_WRITE_ALLOWED_FIELDS = (
    SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUIRED_FIELDS | SERVER_OWNED_LOCAL_OUTBOX_WRITE_OPTIONAL_FIELDS
)
SERVER_OWNED_LOCAL_OUTBOX_WRITE_DOWNSTREAM_UNAVAILABLE = (
    "real_connector_invocation",
    "external_destination_write",
    "connector_run_creation",
    "credentials",
    "provider_public_delivery_use",
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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _outbox_root() -> Path:
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    root = Path(settings.layer3_local_outbox_dir).resolve(strict=False)
    try:
        root.relative_to(storage_root)
    except ValueError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_storage_root_invalid",
            "Server-owned local outbox root must be derived under STORAGE_DIR.",
            status="blocked",
            http_status=409,
            blocked_fields=["storage_dir"],
        ) from exc
    root.mkdir(parents=True, exist_ok=True)
    return root


def _outbox_path(relative_ref: str) -> Path:
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    root = _outbox_root()
    resolved = (storage_root / relative_ref).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_path_escape",
            "Server-owned local outbox write path must stay under the derived outbox root.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_ref"],
        ) from exc
    return resolved


def _redacted_storage_ref(relative_ref: str) -> str:
    normalized = relative_ref.replace("\\", "/")
    prefix = f"{SERVER_OWNED_LOCAL_OUTBOX_STORAGE_DIRNAME}/"
    suffix = normalized[len(prefix) :] if normalized.startswith(prefix) else normalized
    return f"storage://server-owned-local-outbox/{suffix}"


def _existing_connector_record(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get("connector_dispatch_record")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_STATE_SCHEMA_ID:
        return None
    return state


def _existing_local_receipt_summary(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get("connector_local_destination_receipt")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != layer3_connector_local_destination_receipt.CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE_SCHEMA_ID:
        return None
    return state


def _existing_external_export_download_prepare(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get("external_export_download_prepare")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID:
        return None
    return state


def _existing_target_summary(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get("server_owned_local_outbox_target")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != layer3_server_owned_local_outbox_target.SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATE_SCHEMA_ID:
        return None
    return state


def _authority_basis(
    *,
    payload: dict[str, Any],
    target_row: L3ServerOwnedLocalOutboxTargetReceipt,
    local_row: L3ConnectorLocalDestinationReceipt,
    readiness_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.server_owned_local_outbox_write_authority.v1",
        "record_source_gate": SERVER_OWNED_LOCAL_OUTBOX_WRITE_SOURCE_GATE,
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": _string(payload.get("analysis_plan_id")),
        "pass_run_id": target_row.pass_run_id,
        "reconciliation_record_id": target_row.reconciliation_record_id,
        "connector_dispatch_record_ref": target_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": target_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": target_row.connector_local_destination_receipt_id,
        "server_owned_local_outbox_target_receipt_id": (
            target_row.server_owned_local_outbox_target_receipt_id
        ),
        "server_owned_local_outbox_target_state": target_row.target_state,
        "server_owned_local_outbox_target_authority_basis_hash": target_row.authority_basis_hash,
        "connector_local_destination_receipt_authority_basis_hash": local_row.authority_basis_hash,
        "target_identity": SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY,
        "dispatch_mode": SERVER_OWNED_LOCAL_OUTBOX_WRITE_DISPATCH_MODE,
        "source_artifact_hash": readiness_state.get("source_artifact_hash"),
        "source_artifact_size_bytes": readiness_state.get("source_artifact_size_bytes"),
        "accepted_artifact_hash": target_row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": target_row.accepted_artifact_size_bytes,
    }


def _response(
    *,
    request_id: str,
    status: str,
    write_operation_state: str,
    row: L3ServerOwnedLocalOutboxWriteReceipt,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            SERVER_OWNED_LOCAL_OUTBOX_WRITE_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "server_owned_local_outbox_write_receipt_id": row.server_owned_local_outbox_write_receipt_id,
        "server_owned_local_outbox_target_receipt_id": row.server_owned_local_outbox_target_receipt_id,
        "server_owned_local_outbox_write_state": row.write_state,
        "write_operation_state": write_operation_state,
        "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
        "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "target_identity": row.target_identity,
        "dispatch_mode": row.dispatch_mode,
        "outbox_artifact_ref": _redacted_storage_ref(row.outbox_artifact_ref),
        "outbox_manifest_ref": _redacted_storage_ref(row.outbox_manifest_ref),
        "outbox_artifact_hash": row.outbox_artifact_hash,
        "outbox_artifact_size_bytes": row.outbox_artifact_size_bytes,
        "accepted_artifact_ref": SERVER_OWNED_LOCAL_OUTBOX_WRITE_REDACTED_SOURCE_REF,
        "accepted_artifact_hash": row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": row.accepted_artifact_size_bytes,
        "authority_basis_hash": row.authority_basis_hash,
        "server_owned_local_outbox_write_enabled": True,
        "server_owned_local_outbox_write_performed": True,
        "fake_target_contract_enabled": True,
        "real_connector_invocation_enabled": False,
        "external_destination_write_enabled": False,
        "operator_destination_path_enabled": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "network_write_enabled": False,
        "real_destination_integration_enabled": False,
        "provider_public_url_enabled": False,
        "provider_public_delivery_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_enabled": False,
        "auth_security_implementation_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "downstream_unavailable": list(SERVER_OWNED_LOCAL_OUTBOX_WRITE_DOWNSTREAM_UNAVAILABLE),
        "next_state": row.write_state,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=row.session_id,
            current_gate="handoff",
            persistence_mode="durable_server_owned_local_outbox_write_receipt",
            downstream_unavailable=SERVER_OWNED_LOCAL_OUTBOX_WRITE_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def _write_bytes_atomic(*, source_path: Path, target_path: Path, expected_hash: str, expected_size: int) -> None:
    if target_path.exists():
        if _file_sha256(target_path) == expected_hash and int(target_path.stat().st_size) == expected_size:
            return
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_existing_artifact_conflict",
            "Existing server-owned local outbox artifact conflicts with the validated source artifact.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_ref"],
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target_path.parent), prefix="._", suffix=".tmp")
    tmp_path = Path(tmp_name)
    with os.fdopen(fd, "wb") as target, source_path.open("rb") as source:
        shutil.copyfileobj(source, target)
    if _file_sha256(tmp_path) != expected_hash or int(tmp_path.stat().st_size) != expected_size:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_artifact_verification_failed",
            "Copied server-owned local outbox artifact did not match the validated source artifact.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_hash", "source_artifact_size_bytes"],
        )
    os.replace(tmp_path, target_path)


def _write_manifest_atomic(path: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == serialized:
            return
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_existing_manifest_conflict",
            "Existing server-owned local outbox manifest conflicts with the write receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_manifest_ref"],
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix="._", suffix=".tmp")
    tmp_path = Path(tmp_name)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
    os.replace(tmp_path, path)


def _verify_existing_row(row: L3ServerOwnedLocalOutboxWriteReceipt) -> None:
    artifact_path = _outbox_path(row.outbox_artifact_ref)
    if not artifact_path.exists() or not artifact_path.is_file():
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_artifact_missing",
            "Recorded server-owned local outbox artifact is missing.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_ref"],
        )
    if _file_sha256(artifact_path) != row.outbox_artifact_hash:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_artifact_hash_mismatch",
            "Recorded server-owned local outbox artifact hash no longer matches the durable receipt.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_ref"],
        )


def write_server_owned_local_outbox(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for server-owned local outbox write.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_server_owned_local_outbox_write_request"],
        )

    unknown = sorted(key for key in payload if key not in SERVER_OWNED_LOCAL_OUTBOX_WRITE_ALLOWED_FIELDS)
    forbidden = sorted(key for key in SERVER_OWNED_LOCAL_OUTBOX_WRITE_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_scope_not_admitted",
            "Server-owned local outbox write request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_server_owned_local_outbox_write_request"],
        )

    missing = sorted(
        field
        for field in SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_server_owned_local_outbox_write_fields",
            "Server-owned local outbox write request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_server_owned_local_outbox_write_request"],
        )

    if _string(payload.get("target_identity")) != SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_target_identity_not_admitted",
            "target_identity must be server_owned_local_delivery_outbox_destination.",
            status="invalid",
            blocked_fields=["target_identity"],
        )
    if _string(payload.get("dispatch_mode")) != SERVER_OWNED_LOCAL_OUTBOX_WRITE_DISPATCH_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_dispatch_mode_not_admitted",
            "dispatch_mode must be server_owned_local_outbox_write_via_storage_dir.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if _string(payload.get("operator_decision")) != SERVER_OWNED_LOCAL_OUTBOX_WRITE_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_server_owned_local_outbox_write_decision",
            "operator_decision must be write_server_owned_local_outbox.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if (
        _string(payload.get("server_owned_local_outbox_target_state"))
        != layer3_server_owned_local_outbox_target.SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECORDED_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_requires_fake_target",
            "Server-owned local outbox write requires server_owned_local_outbox_fake_target_recorded state.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_state"],
            next_allowed_actions=["record_server_owned_local_outbox_fake_target"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().one_or_none()
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).with_for_update().one_or_none()
    if session is None or pass_run is None or reconciliation is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_requires_existing_authority",
            "Server-owned local outbox write requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_server_owned_local_outbox_target_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
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
    if target_row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_requires_fake_target",
            "Server-owned local outbox write requires an existing fake-target receipt row.",
            status="blocked",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
            next_allowed_actions=["record_server_owned_local_outbox_fake_target"],
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
    if local_row is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_requires_local_receipt",
            "Server-owned local outbox write requires an existing connector-local destination receipt row.",
            status="blocked",
            http_status=409,
            blocked_fields=["connector_local_destination_receipt_id"],
            next_allowed_actions=["record_internal_fake_local_destination_receipt"],
        )

    expected = {
        "pass_run_id": target_row.pass_run_id,
        "reconciliation_record_id": target_row.reconciliation_record_id,
        "connector_dispatch_record_ref": target_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": target_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": target_row.connector_local_destination_receipt_id,
    }
    for field, expected_value in expected.items():
        if _string(payload.get(field)) != _string(expected_value):
            raise layer3_workbench.Layer3WorkbenchError(
                f"server_owned_local_outbox_write_{field}_mismatch",
                f"Supplied {field} does not match recorded fake-target authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )
    if target_row.target_identity != SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_target_identity_not_admitted",
            "Fake-target receipt target identity is not admitted for local outbox write.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
        )

    connector_record = _existing_connector_record(reconciliation)
    local_summary = _existing_local_receipt_summary(reconciliation)
    readiness_state = _existing_external_export_download_prepare(reconciliation)
    target_summary = _existing_target_summary(reconciliation)
    if target_summary is None or _string(target_summary.get("server_owned_local_outbox_target_receipt_id")) != target_receipt_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_stale_authority",
            "Recorded fake-target summary no longer matches durable target receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
        )
    if _string(target_summary.get("authority_basis_hash")) != target_row.authority_basis_hash:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_stale_authority",
            "Recorded fake-target authority hash no longer matches durable target receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_target_receipt_id"],
        )
    if (
        connector_record is None
        or connector_record.get("connector_dispatch_record_state")
        != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_stale_authority",
            "Server-owned local outbox write requires current connector dispatch record authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["connector_dispatch_record_ref"],
        )
    if local_summary is None or _string(local_summary.get("authority_basis_hash")) != local_row.authority_basis_hash:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_stale_authority",
            "Recorded connector-local receipt summary no longer matches durable local receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["connector_local_destination_receipt_id"],
        )
    if (
        readiness_state is None
        or readiness_state.get("external_export_download_state") != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_stale_authority",
            "Server-owned local outbox write requires current external export/download readiness authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )

    authority_mismatches = {
        "connector_dispatch_record_ref": connector_record.get("connector_dispatch_record_ref"),
        "external_export_download_record_ref": readiness_state.get("external_export_download_record_ref"),
        "accepted_artifact_hash": readiness_state.get("source_artifact_hash"),
        "accepted_artifact_size_bytes": readiness_state.get("source_artifact_size_bytes"),
    }
    observed = {
        "connector_dispatch_record_ref": target_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": target_row.external_export_download_record_ref,
        "accepted_artifact_hash": target_row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": target_row.accepted_artifact_size_bytes,
    }
    for field, expected_value in authority_mismatches.items():
        if _string(expected_value) != _string(observed[field]):
            raise layer3_workbench.Layer3WorkbenchError(
                "server_owned_local_outbox_write_stale_authority",
                f"Recorded {field} no longer matches fake-target authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )

    basis = _authority_basis(
        payload=payload,
        target_row=target_row,
        local_row=local_row,
        readiness_state=readiness_state,
    )
    authority_basis_hash = stable_hash(basis)
    existing_by_client = (
        db.query(L3ServerOwnedLocalOutboxWriteReceipt)
        .filter(L3ServerOwnedLocalOutboxWriteReceipt.client_request_id == request_id)
        .one_or_none()
    )
    if existing_by_client is not None:
        if existing_by_client.authority_basis_hash == authority_basis_hash:
            _verify_existing_row(existing_by_client)
            return _response(
                request_id=request_id,
                status="already_recorded",
                write_operation_state=SERVER_OWNED_LOCAL_OUTBOX_WRITE_REPLAY_STATE,
                row=existing_by_client,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_client_request_conflict",
            "client_request_id already belongs to a different server-owned local outbox write authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing_by_basis = (
        db.query(L3ServerOwnedLocalOutboxWriteReceipt)
        .filter(L3ServerOwnedLocalOutboxWriteReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_already_recorded",
            "This fake-target authority already has a server-owned local outbox write receipt.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "server_owned_local_outbox_target_receipt_id"],
        )

    descriptor = readiness_state.get("external_export_download_descriptor")
    if not isinstance(descriptor, dict):
        descriptor = {}
    source_artifact_ref = _string(descriptor.get("source_artifact_ref") or readiness_state.get("source_artifact_ref"))
    try:
        _bundle_payload, source_path = load_persisted_bundle_artifact(bundle_ref=source_artifact_ref)
    except EvidenceBundleError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_source_artifact_unavailable",
            f"Server-owned local outbox write could not validate the existing APS bundle artifact: {exc.message}",
            status="blocked",
            http_status=409,
            blocked_fields=["source_artifact_ref"],
            next_allowed_actions=["refresh_external_export_download_authority"],
        ) from exc
    expected_hash = _string(readiness_state.get("source_artifact_hash"))
    try:
        expected_size = int(readiness_state.get("source_artifact_size_bytes") or -1)
    except (TypeError, ValueError):
        expected_size = -1
    actual_hash = _file_sha256(source_path)
    actual_size = int(source_path.stat().st_size)
    if actual_hash != expected_hash:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_source_artifact_hash_mismatch",
            "Validated source artifact hash does not match recorded readiness.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_hash"],
        )
    if actual_size != expected_size:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_source_artifact_size_mismatch",
            "Validated source artifact size does not match recorded readiness.",
            status="conflict",
            http_status=409,
            blocked_fields=["source_artifact_size_bytes"],
        )

    now = utcnow()
    write_receipt_id = stable_id(
        SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECEIPT_ID_PREFIX,
        {"authority_basis_hash": authority_basis_hash, "client_request_id": request_id},
        digest_chars=27,
    )
    artifact_ref = f"{SERVER_OWNED_LOCAL_OUTBOX_STORAGE_DIRNAME}/{write_receipt_id}/artifact.json"
    manifest_ref = f"{SERVER_OWNED_LOCAL_OUTBOX_STORAGE_DIRNAME}/{write_receipt_id}/receipt.json"
    artifact_path = _outbox_path(artifact_ref)
    manifest_path = _outbox_path(manifest_ref)
    _write_bytes_atomic(
        source_path=source_path,
        target_path=artifact_path,
        expected_hash=expected_hash,
        expected_size=expected_size,
    )
    outbox_hash = _file_sha256(artifact_path)
    outbox_size = int(artifact_path.stat().st_size)
    if outbox_hash != expected_hash or outbox_size != expected_size:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_write_artifact_verification_failed",
            "Server-owned local outbox artifact did not verify after write.",
            status="conflict",
            http_status=409,
            blocked_fields=["server_owned_local_outbox_ref"],
        )

    manifest_payload = {
        "schema_id": SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATE_SCHEMA_ID,
        "server_owned_local_outbox_write_receipt_id": write_receipt_id,
        "server_owned_local_outbox_target_receipt_id": target_receipt_id,
        "write_state": SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE,
        "target_identity": SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY,
        "dispatch_mode": SERVER_OWNED_LOCAL_OUTBOX_WRITE_DISPATCH_MODE,
        "outbox_artifact_ref": artifact_ref,
        "outbox_artifact_hash": outbox_hash,
        "outbox_artifact_size_bytes": outbox_size,
        "accepted_artifact_ref": SERVER_OWNED_LOCAL_OUTBOX_WRITE_REDACTED_SOURCE_REF,
        "accepted_artifact_hash": expected_hash,
        "accepted_artifact_size_bytes": expected_size,
        "authority_basis_hash": authority_basis_hash,
        "created_at": now.isoformat(),
        "external_connector_invocation_enabled": False,
        "external_destination_write_enabled": False,
        "connector_run_created": False,
        "connector_run_target_created": False,
        "credentials_enabled": False,
        "provider_public_delivery_enabled": False,
    }
    _write_manifest_atomic(manifest_path, manifest_payload)

    row = L3ServerOwnedLocalOutboxWriteReceipt(
        server_owned_local_outbox_write_receipt_id=write_receipt_id,
        server_owned_local_outbox_target_receipt_id=target_receipt_id,
        session_id=session_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        connector_local_destination_receipt_id=local_receipt_id,
        client_request_id=request_id,
        connector_dispatch_record_ref=target_row.connector_dispatch_record_ref,
        external_export_download_record_ref=target_row.external_export_download_record_ref,
        target_identity=SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY,
        dispatch_mode=SERVER_OWNED_LOCAL_OUTBOX_WRITE_DISPATCH_MODE,
        write_state=SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE,
        outbox_artifact_ref=artifact_ref,
        outbox_manifest_ref=manifest_ref,
        outbox_artifact_hash=outbox_hash,
        outbox_artifact_size_bytes=outbox_size,
        accepted_artifact_hash=expected_hash,
        accepted_artifact_size_bytes=expected_size,
        authority_basis_hash=authority_basis_hash,
        authority_snapshot_json=json_clone(basis),
        created_by_request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "server_owned_local_outbox_write": {
            "schema_id": SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATE_SCHEMA_ID,
            "server_owned_local_outbox_write_receipt_id": write_receipt_id,
            "server_owned_local_outbox_target_receipt_id": target_receipt_id,
            "server_owned_local_outbox_write_state": SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE,
            "connector_local_destination_receipt_id": local_receipt_id,
            "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
            "external_export_download_record_ref": row.external_export_download_record_ref,
            "target_identity": SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY,
            "dispatch_mode": SERVER_OWNED_LOCAL_OUTBOX_WRITE_DISPATCH_MODE,
            "outbox_artifact_ref": _redacted_storage_ref(artifact_ref),
            "outbox_manifest_ref": _redacted_storage_ref(manifest_ref),
            "outbox_artifact_hash": outbox_hash,
            "outbox_artifact_size_bytes": outbox_size,
            "accepted_artifact_ref": SERVER_OWNED_LOCAL_OUTBOX_WRITE_REDACTED_SOURCE_REF,
            "accepted_artifact_hash": expected_hash,
            "accepted_artifact_size_bytes": expected_size,
            "authority_basis_hash": authority_basis_hash,
            "record_source_gate": SERVER_OWNED_LOCAL_OUTBOX_WRITE_SOURCE_GATE,
            "server_owned_local_outbox_write_enabled": True,
            "server_owned_local_outbox_write_performed": True,
            "real_connector_invocation_enabled": False,
            "external_destination_write_enabled": False,
            "connector_run_created": False,
            "connector_run_target_created": False,
            "credentials_enabled": False,
            "provider_public_delivery_enabled": False,
        },
    }
    db.commit()

    return _response(
        request_id=request_id,
        status="recorded",
        write_operation_state=SERVER_OWNED_LOCAL_OUTBOX_WRITE_RECORDED_STATE,
        row=row,
    )
