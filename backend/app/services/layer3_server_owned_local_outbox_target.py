from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3ConnectorLocalDestinationReceipt,
    L3PassRun,
    L3ReconciliationRecord,
    L3ServerOwnedLocalOutboxTargetReceipt,
    L3Session,
)
from app.services import layer3_connector_dispatch_entry, layer3_connector_local_destination_receipt, layer3_workbench
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow


SERVER_OWNED_LOCAL_OUTBOX_TARGET_SCHEMA_ID = "layer3.server_owned_local_outbox_fake_target_receipt.v1"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATE_SCHEMA_ID = "layer3.server_owned_local_outbox_fake_target_state.v1"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_SOURCE_GATE = "606_REAL_TARGET_IMPLEMENTATION_ENTRY_FREEZE"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY = "server_owned_local_delivery_outbox_destination"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_DISPATCH_MODE = "single_named_destination_dispatch_fake_target_first"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_OPERATOR_DECISION = "record_server_owned_local_outbox_fake_target"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_REDACTED_ARTIFACT_REF = (
    "artifact://server-owned-local-outbox-fake-target-redacted"
)
SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECEIPT_ID_PREFIX = "l3solotr"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_NOT_READY_STATE = "server_owned_local_outbox_target_not_ready"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_READY_STATE = "server_owned_local_outbox_fake_target_ready"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECORDED_STATE = "server_owned_local_outbox_fake_target_recorded"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_REPLAY_STATE = "server_owned_local_outbox_fake_target_replay"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_CONFLICT_STATE = "server_owned_local_outbox_fake_target_conflict"
SERVER_OWNED_LOCAL_OUTBOX_TARGET_STALE_AUTHORITY_STATE = (
    "server_owned_local_outbox_fake_target_stale_authority"
)
SERVER_OWNED_LOCAL_OUTBOX_TARGET_FAILED_STATE = "server_owned_local_outbox_fake_target_failed"

SERVER_OWNED_LOCAL_OUTBOX_TARGET_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "connector_local_destination_receipt_id",
        "connector_local_destination_receipt_state",
        "external_export_download_record_ref",
        "target_identity",
        "dispatch_mode",
        "operator_decision",
    }
)
SERVER_OWNED_LOCAL_OUTBOX_TARGET_OPTIONAL_FIELDS = frozenset({"decision_notes"})
SERVER_OWNED_LOCAL_OUTBOX_TARGET_FORBIDDEN_FIELDS = frozenset(
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
SERVER_OWNED_LOCAL_OUTBOX_TARGET_ALLOWED_FIELDS = (
    SERVER_OWNED_LOCAL_OUTBOX_TARGET_REQUIRED_FIELDS | SERVER_OWNED_LOCAL_OUTBOX_TARGET_OPTIONAL_FIELDS
)
SERVER_OWNED_LOCAL_OUTBOX_TARGET_DOWNSTREAM_UNAVAILABLE = (
    "real_connector_invocation",
    "production_destination_write",
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
    if (
        state.get("schema_id")
        != layer3_connector_local_destination_receipt.CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE_SCHEMA_ID
    ):
        return None
    return state


def _existing_external_export_download_prepare(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get("external_export_download_prepare")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID:
        return None
    return state


def _target_authority_basis(
    *,
    payload: dict[str, Any],
    local_row: L3ConnectorLocalDestinationReceipt,
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.server_owned_local_outbox_fake_target_authority.v1",
        "record_source_gate": SERVER_OWNED_LOCAL_OUTBOX_TARGET_SOURCE_GATE,
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": _string(payload.get("analysis_plan_id")),
        "pass_run_id": local_row.pass_run_id,
        "reconciliation_record_id": local_row.reconciliation_record_id,
        "connector_dispatch_record_ref": local_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": local_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": local_row.connector_local_destination_receipt_id,
        "connector_local_destination_receipt_state": local_row.receipt_state,
        "connector_local_destination_receipt_authority_basis_hash": local_row.authority_basis_hash,
        "target_identity": SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY,
        "dispatch_mode": SERVER_OWNED_LOCAL_OUTBOX_TARGET_DISPATCH_MODE,
        "accepted_artifact_hash": local_row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": local_row.accepted_artifact_size_bytes,
    }


def _response(
    *,
    request_id: str,
    status: str,
    target_operation_state: str,
    row: L3ServerOwnedLocalOutboxTargetReceipt,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            SERVER_OWNED_LOCAL_OUTBOX_TARGET_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "server_owned_local_outbox_target_receipt_id": row.server_owned_local_outbox_target_receipt_id,
        "server_owned_local_outbox_target_state": row.target_state,
        "target_operation_state": target_operation_state,
        "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
        "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "target_identity": row.target_identity,
        "dispatch_mode": row.dispatch_mode,
        "accepted_artifact_ref": SERVER_OWNED_LOCAL_OUTBOX_TARGET_REDACTED_ARTIFACT_REF,
        "accepted_artifact_hash": row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": row.accepted_artifact_size_bytes,
        "authority_basis_hash": row.authority_basis_hash,
        "fake_target_contract_enabled": True,
        "real_connector_invocation_enabled": False,
        "destination_write_enabled": False,
        "destination_write_performed": False,
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
        "downstream_unavailable": list(SERVER_OWNED_LOCAL_OUTBOX_TARGET_DOWNSTREAM_UNAVAILABLE),
        "next_state": row.target_state,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=row.session_id,
            current_gate="handoff",
            persistence_mode="durable_server_owned_local_outbox_fake_target_receipt",
            downstream_unavailable=SERVER_OWNED_LOCAL_OUTBOX_TARGET_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def record_server_owned_local_outbox_fake_target(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for server-owned local outbox fake-target receipt.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_server_owned_local_outbox_fake_target_request"],
        )

    unknown = sorted(key for key in payload if key not in SERVER_OWNED_LOCAL_OUTBOX_TARGET_ALLOWED_FIELDS)
    forbidden = sorted(key for key in SERVER_OWNED_LOCAL_OUTBOX_TARGET_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_scope_not_admitted",
            "Server-owned local outbox fake-target request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_server_owned_local_outbox_fake_target_request"],
        )

    missing = sorted(
        field
        for field in SERVER_OWNED_LOCAL_OUTBOX_TARGET_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_server_owned_local_outbox_target_fields",
            "Server-owned local outbox fake-target request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_server_owned_local_outbox_fake_target_request"],
        )

    if _string(payload.get("target_identity")) != SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_identity_not_admitted",
            "target_identity must be server_owned_local_delivery_outbox_destination.",
            status="invalid",
            blocked_fields=["target_identity"],
        )
    if _string(payload.get("dispatch_mode")) != SERVER_OWNED_LOCAL_OUTBOX_TARGET_DISPATCH_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_dispatch_mode_not_admitted",
            "dispatch_mode must be single_named_destination_dispatch_fake_target_first.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if _string(payload.get("operator_decision")) != SERVER_OWNED_LOCAL_OUTBOX_TARGET_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_server_owned_local_outbox_target_decision",
            "operator_decision must be record_server_owned_local_outbox_fake_target.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if (
        _string(payload.get("connector_local_destination_receipt_state"))
        != layer3_connector_local_destination_receipt.CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_requires_local_receipt",
            "Server-owned local outbox fake target requires connector_local_destination_receipt_recorded state.",
            status="blocked",
            http_status=409,
            blocked_fields=["connector_local_destination_receipt_state"],
            next_allowed_actions=["record_internal_fake_local_destination_receipt"],
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
            "server_owned_local_outbox_target_requires_existing_authority",
            "Server-owned local outbox fake target requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_connector_local_destination_receipt_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
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
            "server_owned_local_outbox_target_requires_local_receipt",
            "Server-owned local outbox fake target requires an existing connector-local destination receipt row.",
            status="blocked",
            http_status=409,
            blocked_fields=["connector_local_destination_receipt_id"],
            next_allowed_actions=["record_internal_fake_local_destination_receipt"],
        )

    basis = _target_authority_basis(payload=payload, local_row=local_row)
    authority_basis_hash = stable_hash(basis)
    existing_by_client = (
        db.query(L3ServerOwnedLocalOutboxTargetReceipt)
        .filter(L3ServerOwnedLocalOutboxTargetReceipt.client_request_id == request_id)
        .one_or_none()
    )
    if existing_by_client is not None:
        if existing_by_client.authority_basis_hash == authority_basis_hash:
            return _response(
                request_id=request_id,
                status="already_recorded",
                target_operation_state=SERVER_OWNED_LOCAL_OUTBOX_TARGET_REPLAY_STATE,
                row=existing_by_client,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_client_request_conflict",
            "client_request_id already belongs to a different server-owned local outbox target authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing_by_basis = (
        db.query(L3ServerOwnedLocalOutboxTargetReceipt)
        .filter(L3ServerOwnedLocalOutboxTargetReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_already_recorded",
            "This connector-local receipt authority already has a server-owned local outbox fake-target receipt.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "connector_local_destination_receipt_id"],
        )

    connector_record = _existing_connector_record(reconciliation)
    local_summary = _existing_local_receipt_summary(reconciliation)
    readiness_state = _existing_external_export_download_prepare(reconciliation)
    expected = {
        "pass_run_id": local_row.pass_run_id,
        "reconciliation_record_id": local_row.reconciliation_record_id,
        "connector_dispatch_record_ref": local_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": local_row.external_export_download_record_ref,
        "connector_local_destination_receipt_id": local_row.connector_local_destination_receipt_id,
        "connector_local_destination_receipt_state": local_row.receipt_state,
    }
    for field, expected_value in expected.items():
        if _string(payload.get(field)) != _string(expected_value):
            raise layer3_workbench.Layer3WorkbenchError(
                f"server_owned_local_outbox_target_{field}_mismatch",
                f"Supplied {field} does not match recorded connector-local receipt authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )
    if (
        connector_record is None
        or connector_record.get("connector_dispatch_record_state")
        != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_stale_authority",
            "Server-owned local outbox fake target requires current connector dispatch record authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["connector_dispatch_record_ref"],
        )
    if (
        local_summary is None
        or _string(local_summary.get("connector_local_destination_receipt_id")) != local_row.connector_local_destination_receipt_id
        or _string(local_summary.get("authority_basis_hash")) != local_row.authority_basis_hash
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_stale_authority",
            "Recorded connector-local receipt summary no longer matches durable local receipt authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["connector_local_destination_receipt_id"],
        )
    if readiness_state is None or readiness_state.get("external_export_download_state") != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "server_owned_local_outbox_target_stale_authority",
            "Server-owned local outbox fake target requires current external export/download readiness authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )
    authority_mismatches = {
        "connector_dispatch_record_ref": connector_record.get("connector_dispatch_record_ref"),
        "external_export_download_record_ref": readiness_state.get("external_export_download_record_ref"),
        "accepted_artifact_hash": connector_record.get("source_artifact_hash")
        or readiness_state.get("source_artifact_hash"),
        "accepted_artifact_size_bytes": connector_record.get("source_artifact_size_bytes")
        or readiness_state.get("source_artifact_size_bytes"),
    }
    observed = {
        "connector_dispatch_record_ref": local_row.connector_dispatch_record_ref,
        "external_export_download_record_ref": local_row.external_export_download_record_ref,
        "accepted_artifact_hash": local_row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": local_row.accepted_artifact_size_bytes,
    }
    for field, expected_value in authority_mismatches.items():
        if _string(expected_value) != _string(observed[field]):
            raise layer3_workbench.Layer3WorkbenchError(
                "server_owned_local_outbox_target_stale_authority",
                f"Recorded {field} no longer matches connector-local receipt authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )

    now = utcnow()
    receipt_id = stable_id(
        SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECEIPT_ID_PREFIX,
        {"authority_basis_hash": authority_basis_hash, "client_request_id": request_id},
        digest_chars=27,
    )
    row = L3ServerOwnedLocalOutboxTargetReceipt(
        server_owned_local_outbox_target_receipt_id=receipt_id,
        session_id=session_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        connector_local_destination_receipt_id=local_receipt_id,
        client_request_id=request_id,
        connector_dispatch_record_ref=local_row.connector_dispatch_record_ref,
        external_export_download_record_ref=local_row.external_export_download_record_ref,
        target_identity=SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY,
        dispatch_mode=SERVER_OWNED_LOCAL_OUTBOX_TARGET_DISPATCH_MODE,
        target_state=SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECORDED_STATE,
        accepted_artifact_hash=local_row.accepted_artifact_hash,
        accepted_artifact_size_bytes=local_row.accepted_artifact_size_bytes,
        authority_basis_hash=authority_basis_hash,
        authority_snapshot_json=json_clone(basis),
        created_by_request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "server_owned_local_outbox_target": {
            "schema_id": SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATE_SCHEMA_ID,
            "server_owned_local_outbox_target_receipt_id": receipt_id,
            "server_owned_local_outbox_target_state": SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECORDED_STATE,
            "connector_local_destination_receipt_id": local_receipt_id,
            "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
            "external_export_download_record_ref": row.external_export_download_record_ref,
            "target_identity": SERVER_OWNED_LOCAL_OUTBOX_TARGET_IDENTITY,
            "dispatch_mode": SERVER_OWNED_LOCAL_OUTBOX_TARGET_DISPATCH_MODE,
            "accepted_artifact_ref": SERVER_OWNED_LOCAL_OUTBOX_TARGET_REDACTED_ARTIFACT_REF,
            "accepted_artifact_hash": row.accepted_artifact_hash,
            "accepted_artifact_size_bytes": row.accepted_artifact_size_bytes,
            "authority_basis_hash": authority_basis_hash,
            "record_source_gate": SERVER_OWNED_LOCAL_OUTBOX_TARGET_SOURCE_GATE,
            "fake_target_contract_enabled": True,
            "real_connector_invocation_enabled": False,
            "destination_write_enabled": False,
            "destination_write_performed": False,
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
        target_operation_state=SERVER_OWNED_LOCAL_OUTBOX_TARGET_RECORDED_STATE,
        row=row,
    )
