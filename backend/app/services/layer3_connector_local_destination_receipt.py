from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3ConnectorLocalDestinationReceipt,
    L3PassRun,
    L3ReconciliationRecord,
    L3Session,
)
from app.services import layer3_connector_dispatch_entry, layer3_workbench
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow


CONNECTOR_LOCAL_DESTINATION_RECEIPT_SCHEMA_ID = "layer3.connector_local_destination_receipt.v1"
CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE_SCHEMA_ID = "layer3.connector_local_destination_receipt_state.v1"
CONNECTOR_LOCAL_DESTINATION_RECEIPT_SOURCE_GATE = (
    "580_LAYER3_CONNECTOR_INTERNAL_FAKE_LOCAL_DESTINATION_RECEIPT_IMPLEMENTATION_ENTRY_FREEZE"
)
CONNECTOR_LOCAL_DESTINATION_RECEIPT_TARGET = "layer3_internal_fake_local_destination_receipt"
CONNECTOR_LOCAL_DESTINATION_RECEIPT_MODE = "internal_fake_local_destination_receipt_only"
CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE = "connector_local_destination_receipt_recorded"
CONNECTOR_LOCAL_DESTINATION_RECEIPT_OPERATOR_DECISION = "record_internal_fake_local_destination_receipt"
CONNECTOR_LOCAL_DESTINATION_REDACTED_ARTIFACT_REF = "artifact://layer3-internal-fake-local-destination-redacted"
CONNECTOR_LOCAL_DESTINATION_RECEIPT_ID_PREFIX = "l3cldr"

CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "external_export_download_record_ref",
        "external_export_download_state",
        "destination_target",
        "dispatch_mode",
        "operator_decision",
    }
)
CONNECTOR_LOCAL_DESTINATION_RECEIPT_OPTIONAL_FIELDS = frozenset({"decision_notes"})
CONNECTOR_LOCAL_DESTINATION_RECEIPT_FORBIDDEN_FIELDS = frozenset(
    {
        "connector_key",
        "connector_run_id",
        "connector_secret",
        "destination_id",
        "destination_secret",
        "destination_url",
        "provider_url",
        "provider_public_url",
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
    }
)
CONNECTOR_LOCAL_DESTINATION_RECEIPT_ALLOWED_FIELDS = (
    CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUIRED_FIELDS | CONNECTOR_LOCAL_DESTINATION_RECEIPT_OPTIONAL_FIELDS
)
CONNECTOR_LOCAL_DESTINATION_DOWNSTREAM_UNAVAILABLE = (
    "external_connector_invocation",
    "destination_write",
    "connector_run_creation",
    "real_destination_integration",
    "network_write",
    "provider_public_url",
    "package_mutation_reconstruction",
    "source_upload_expansion",
    "broad_qualitative_hybrid_rag_execution",
    "full_mockup_activation",
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


def _existing_external_export_download_prepare(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get("external_export_download_prepare")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID:
        return None
    return state


def _delivery_authority_payload(
    *,
    payload: dict[str, Any],
    connector_record: dict[str, Any],
    readiness_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "client_request_id": _string(payload.get("client_request_id")),
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": connector_record.get("analysis_plan_id"),
        "pass_run_id": connector_record.get("pass_run_id"),
        "preview_id": connector_record.get("source_preview_id") or readiness_state.get("source_preview_id"),
        "preview_hash": connector_record.get("source_preview_hash") or readiness_state.get("source_preview_hash"),
        "result_review_record_ref": connector_record.get("result_review_record_ref"),
        "package_review_preview_hash": connector_record.get("package_review_preview_hash"),
        "reconciliation_record_id": connector_record.get("reconciliation_record_id"),
        "output_package_ids": connector_record.get("output_package_ids"),
        "package_kinds": connector_record.get("package_kinds"),
        "payload_refs": connector_record.get("payload_refs"),
        "payload_hashes": connector_record.get("payload_hashes"),
        "package_review_submit_record_ref": connector_record.get("package_review_submit_record_ref"),
        "package_review_state": connector_record.get("package_review_state"),
        "prepare_record_ref": connector_record.get("prepare_record_ref"),
        "handoff_export_state": connector_record.get("handoff_export_state"),
        "handoff_export_envelope_ref": readiness_state.get("handoff_export_envelope_ref"),
        "handoff_target": readiness_state.get("handoff_target"),
        "export_mode": readiness_state.get("export_mode"),
        "aps_handoff_record_ref": connector_record.get("aps_handoff_record_ref"),
        "aps_handoff_state": connector_record.get("aps_handoff_state"),
        "aps_handoff_target": connector_record.get("aps_handoff_target"),
        "dispatch_mode": readiness_state.get("dispatch_mode"),
        "aps_output_package_id": connector_record.get("aps_output_package_id"),
        "aps_output_package_kind": connector_record.get("aps_output_package_kind"),
        "aps_bundle_ref": connector_record.get("aps_bundle_ref"),
        "aps_bundle_id": readiness_state.get("aps_bundle_id"),
        "aps_schema_id": readiness_state.get("aps_schema_id"),
        "external_export_download_record_ref": connector_record.get("external_export_download_record_ref"),
        "export_download_descriptor_ref": connector_record.get("external_export_download_descriptor_ref")
        or readiness_state.get("export_download_descriptor_ref"),
        "external_export_download_state": connector_record.get("external_export_download_state"),
        "export_download_target": readiness_state.get("export_download_target"),
        "download_mode": readiness_state.get("download_mode"),
        "delivery_mode": "same_origin_artifact_stream",
        "operator_decision": layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
    }


def _validate_existing_delivery_authority(
    *,
    db: Session,
    payload: dict[str, Any],
    connector_record: dict[str, Any],
    readiness_state: dict[str, Any],
) -> None:
    delivery_payload = _delivery_authority_payload(
        payload=payload,
        connector_record=connector_record,
        readiness_state=readiness_state,
    )
    delivery_request = layer3_workbench.external_export_download_delivery_request_fields(delivery_payload)
    missing = delivery_request.missing_fields
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_external_export_download_delivery_fields",
            f"External export/download delivery request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_external_export_download_delivery_request"],
        )
    blocked_payload_fields = layer3_workbench.external_export_download_delivery_blocked_fields(delivery_payload)
    if blocked_payload_fields:
        blocked_text = ", ".join(blocked_payload_fields)
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_scope_not_admitted",
            f"External export/download delivery request includes non-admitted fields: {blocked_text}.",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_bounded_external_export_download_delivery_request"],
        )
    if delivery_request.export_download_target != "aps_evidence_bundle_download_reference":
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_target_not_admitted",
            "export_download_target must be aps_evidence_bundle_download_reference.",
            status="invalid",
            blocked_fields=["export_download_target"],
        )
    if delivery_request.download_mode != "reference_only_prepare":
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_download_mode_not_admitted",
            "download_mode must be reference_only_prepare.",
            status="invalid",
            blocked_fields=["download_mode"],
        )
    if delivery_request.delivery_mode != "same_origin_artifact_stream":
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_mode_not_admitted",
            "delivery_mode must be same_origin_artifact_stream.",
            status="invalid",
            blocked_fields=["delivery_mode"],
        )
    if delivery_request.operator_decision != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_external_export_download_delivery_decision",
            "operator_decision must be deliver_external_export_download.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if delivery_request.supplied_readiness_state != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_requires_delivery_authority",
            "Internal fake/local destination receipt requires validated same-origin delivery authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
            next_allowed_actions=["validate_same_origin_external_export_download_delivery"],
        )
    if not str(readiness_state.get("client_request_id") or "").strip():
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_readiness_request_id_missing",
            "Recorded external export/download readiness is missing its idempotency basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )
    for field, _supplied, _expected in layer3_workbench.external_export_download_delivery_readiness_mismatches(
        delivery_request,
        readiness_state,
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            f"external_export_download_delivery_{field}_mismatch",
            f"Supplied {field} does not match recorded external export/download readiness.",
            status="conflict",
            http_status=409,
            blocked_fields=[field],
        )
    validation_body = layer3_workbench.external_export_download_prepare(
        db,
        layer3_workbench._external_export_download_prepare_payload_for_delivery(  # noqa: SLF001
            delivery_payload,
            readiness_state=readiness_state,
        ),
        validate_source_artifact=False,
    )
    if validation_body.get("external_export_download_record_ref") != delivery_request.supplied_readiness_ref:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_readiness_mismatch",
            "Validated readiness authority does not match the requested delivery record.",
            status="conflict",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
        )
    descriptor = readiness_state.get("external_export_download_descriptor")
    if not isinstance(descriptor, dict) or descriptor.get("descriptor_ref") != delivery_request.supplied_descriptor_ref:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_descriptor_mismatch",
            "Recorded external export/download descriptor is missing or stale.",
            status="conflict",
            http_status=409,
            blocked_fields=["export_download_descriptor_ref"],
        )
    source_artifact_ref = str(descriptor.get("source_artifact_ref") or "").strip()
    if not source_artifact_ref or source_artifact_ref != delivery_request.supplied_aps_bundle_ref:
        raise layer3_workbench.Layer3WorkbenchError(
            "external_export_download_delivery_source_artifact_mismatch",
            "Recorded source artifact does not match the supplied APS bundle ref.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
        )
    try:
        expected_artifact_size = int(readiness_state.get("source_artifact_size_bytes") or -1)
    except (TypeError, ValueError):
        expected_artifact_size = -1
    delivery = layer3_workbench._external_export_download_delivery_response(  # noqa: SLF001
        session_id=delivery_request.session_id,
        supplied_aps_bundle_id=delivery_request.supplied_aps_bundle_id,
        supplied_readiness_ref=delivery_request.supplied_readiness_ref,
        source_artifact_ref=source_artifact_ref,
        expected_artifact_hash=str(readiness_state.get("source_artifact_hash") or ""),
        expected_artifact_size=expected_artifact_size,
        validation_body=validation_body,
    )
    if (
        delivery.headers.get("X-Layer3-Delivery-State")
        != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_requires_delivery_authority",
            "Internal fake/local destination receipt requires validated same-origin delivery authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_record_ref"],
            next_allowed_actions=["validate_same_origin_external_export_download_delivery"],
        )


def _authority_basis(
    *,
    payload: dict[str, Any],
    connector_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.connector_local_destination_receipt_authority.v1",
        "record_source_gate": CONNECTOR_LOCAL_DESTINATION_RECEIPT_SOURCE_GATE,
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": connector_record.get("analysis_plan_id"),
        "pass_run_id": connector_record.get("pass_run_id"),
        "reconciliation_record_id": connector_record.get("reconciliation_record_id"),
        "connector_dispatch_record_ref": connector_record.get("connector_dispatch_record_ref"),
        "connector_dispatch_record_state": connector_record.get("connector_dispatch_record_state"),
        "source_connector_dispatch_mode": connector_record.get("dispatch_mode"),
        "external_export_download_record_ref": connector_record.get("external_export_download_record_ref"),
        "external_export_download_state": connector_record.get("external_export_download_state"),
        "destination_target": CONNECTOR_LOCAL_DESTINATION_RECEIPT_TARGET,
        "dispatch_mode": CONNECTOR_LOCAL_DESTINATION_RECEIPT_MODE,
        "accepted_artifact_hash": connector_record.get("source_artifact_hash"),
        "accepted_artifact_size_bytes": connector_record.get("source_artifact_size_bytes"),
    }


def _response(
    *,
    request_id: str,
    status: str,
    row: L3ConnectorLocalDestinationReceipt,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            CONNECTOR_LOCAL_DESTINATION_RECEIPT_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "session_id": row.session_id,
        "pass_run_id": row.pass_run_id,
        "reconciliation_record_id": row.reconciliation_record_id,
        "connector_local_destination_receipt_id": row.connector_local_destination_receipt_id,
        "connector_local_destination_receipt_state": row.receipt_state,
        "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
        "external_export_download_record_ref": row.external_export_download_record_ref,
        "destination_target": row.destination_target,
        "dispatch_mode": row.dispatch_mode,
        "accepted_artifact_ref": CONNECTOR_LOCAL_DESTINATION_REDACTED_ARTIFACT_REF,
        "accepted_artifact_hash": row.accepted_artifact_hash,
        "accepted_artifact_size_bytes": row.accepted_artifact_size_bytes,
        "authority_basis_hash": row.authority_basis_hash,
        "internal_fake_local_destination_enabled": True,
        "external_connector_invocation_enabled": False,
        "destination_write_enabled": False,
        "connector_run_created": False,
        "network_write_enabled": False,
        "real_destination_integration_enabled": False,
        "provider_public_url_enabled": False,
        "package_mutation_enabled": False,
        "source_widening_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "downstream_unavailable": list(CONNECTOR_LOCAL_DESTINATION_DOWNSTREAM_UNAVAILABLE),
        "next_state": CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=row.session_id,
            current_gate="handoff",
            persistence_mode="durable_connector_local_destination_receipt",
            downstream_unavailable=CONNECTOR_LOCAL_DESTINATION_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def record_internal_fake_local_destination_receipt(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for internal fake/local destination receipt.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_connector_local_destination_receipt_request"],
        )

    unknown = sorted(key for key in payload if key not in CONNECTOR_LOCAL_DESTINATION_RECEIPT_ALLOWED_FIELDS)
    forbidden = sorted(key for key in CONNECTOR_LOCAL_DESTINATION_RECEIPT_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_scope_not_admitted",
            "Internal fake/local destination receipt request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_internal_fake_local_destination_receipt_request"],
        )

    missing = sorted(
        field
        for field in CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_connector_local_destination_receipt_fields",
            "Internal fake/local destination receipt request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_connector_local_destination_receipt_request"],
        )

    if _string(payload.get("destination_target")) != CONNECTOR_LOCAL_DESTINATION_RECEIPT_TARGET:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_target_not_admitted",
            "destination_target must be layer3_internal_fake_local_destination_receipt.",
            status="invalid",
            blocked_fields=["destination_target"],
        )
    if _string(payload.get("dispatch_mode")) != CONNECTOR_LOCAL_DESTINATION_RECEIPT_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_dispatch_mode_not_admitted",
            "dispatch_mode must be internal_fake_local_destination_receipt_only.",
            status="invalid",
            blocked_fields=["dispatch_mode"],
        )
    if _string(payload.get("operator_decision")) != CONNECTOR_LOCAL_DESTINATION_RECEIPT_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_connector_local_destination_receipt_decision",
            "operator_decision must be record_internal_fake_local_destination_receipt.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if _string(payload.get("external_export_download_state")) != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_requires_external_export_download_prepare",
            "Internal fake/local destination receipt requires external_export_download_prepared state.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_state"],
            next_allowed_actions=["record_external_export_download_prepare"],
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
            "connector_local_destination_receipt_requires_existing_authority",
            "Internal fake/local destination receipt requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_connector_dispatch_record_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    connector_record = _existing_connector_record(reconciliation)
    if (
        connector_record is None
        or connector_record.get("connector_dispatch_record_state")
        != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_requires_connector_dispatch_record",
            "Internal fake/local destination receipt requires an existing connector_dispatch_recorded state.",
            status="blocked",
            http_status=409,
            blocked_fields=["connector_dispatch_record_ref"],
            next_allowed_actions=["record_internal_connector_dispatch"],
        )

    expected = {
        "analysis_plan_id": connector_record.get("analysis_plan_id"),
        "pass_run_id": connector_record.get("pass_run_id"),
        "reconciliation_record_id": connector_record.get("reconciliation_record_id"),
        "connector_dispatch_record_ref": connector_record.get("connector_dispatch_record_ref"),
        "external_export_download_record_ref": connector_record.get("external_export_download_record_ref"),
        "external_export_download_state": connector_record.get("external_export_download_state"),
    }
    for field, expected_value in expected.items():
        if _string(payload.get(field)) != _string(expected_value):
            raise layer3_workbench.Layer3WorkbenchError(
                f"connector_local_destination_receipt_{field}_mismatch",
                f"Supplied {field} does not match the recorded connector dispatch authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
            )
    if connector_record.get("dispatch_mode") != layer3_connector_dispatch_entry.CONNECTOR_DISPATCH_RECORD_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_source_dispatch_mode_not_admitted",
            "Internal fake/local destination receipt requires internal_dispatch_record_only source authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["connector_dispatch_record_ref"],
        )
    readiness_state = _existing_external_export_download_prepare(reconciliation)
    if (
        readiness_state is None
        or readiness_state.get("external_export_download_state")
        != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_requires_external_export_download_prepare",
            "Internal fake/local destination receipt requires recorded external_export_download_prepared state.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_state"],
            next_allowed_actions=["record_external_export_download_prepare"],
        )
    basis = _authority_basis(payload=payload, connector_record=connector_record)
    authority_basis_hash = stable_hash(basis)
    existing_by_client = (
        db.query(L3ConnectorLocalDestinationReceipt)
        .filter(L3ConnectorLocalDestinationReceipt.client_request_id == request_id)
        .one_or_none()
    )
    if existing_by_client is not None:
        if existing_by_client.authority_basis_hash == authority_basis_hash:
            return _response(request_id=request_id, status="already_recorded", row=existing_by_client)
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_client_request_conflict",
            "client_request_id already belongs to a different local destination receipt authority basis.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing_by_basis = (
        db.query(L3ConnectorLocalDestinationReceipt)
        .filter(L3ConnectorLocalDestinationReceipt.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )
    if existing_by_basis is not None:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_local_destination_receipt_already_recorded",
            "This connector dispatch authority already has an internal fake/local destination receipt.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "connector_dispatch_record_ref"],
        )
    _validate_existing_delivery_authority(
        db=db,
        payload=payload,
        connector_record=connector_record,
        readiness_state=readiness_state,
    )

    now = utcnow()
    receipt_id = stable_id(
        CONNECTOR_LOCAL_DESTINATION_RECEIPT_ID_PREFIX,
        {"authority_basis_hash": authority_basis_hash, "client_request_id": request_id},
        digest_chars=29,
    )
    row = L3ConnectorLocalDestinationReceipt(
        connector_local_destination_receipt_id=receipt_id,
        session_id=session_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        client_request_id=request_id,
        connector_dispatch_record_ref=_string(payload.get("connector_dispatch_record_ref")),
        external_export_download_record_ref=_string(payload.get("external_export_download_record_ref")),
        destination_target=CONNECTOR_LOCAL_DESTINATION_RECEIPT_TARGET,
        dispatch_mode=CONNECTOR_LOCAL_DESTINATION_RECEIPT_MODE,
        receipt_state=CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE,
        accepted_artifact_hash=_string(connector_record.get("source_artifact_hash")),
        accepted_artifact_size_bytes=int(connector_record.get("source_artifact_size_bytes") or 0),
        authority_basis_hash=authority_basis_hash,
        authority_snapshot_json=json_clone(basis),
        created_by_request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "connector_local_destination_receipt": {
            "schema_id": CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE_SCHEMA_ID,
            "connector_local_destination_receipt_id": receipt_id,
            "connector_local_destination_receipt_state": CONNECTOR_LOCAL_DESTINATION_RECEIPT_STATE,
            "destination_target": CONNECTOR_LOCAL_DESTINATION_RECEIPT_TARGET,
            "dispatch_mode": CONNECTOR_LOCAL_DESTINATION_RECEIPT_MODE,
            "connector_dispatch_record_ref": row.connector_dispatch_record_ref,
            "external_export_download_record_ref": row.external_export_download_record_ref,
            "accepted_artifact_ref": CONNECTOR_LOCAL_DESTINATION_REDACTED_ARTIFACT_REF,
            "accepted_artifact_hash": row.accepted_artifact_hash,
            "accepted_artifact_size_bytes": row.accepted_artifact_size_bytes,
            "authority_basis_hash": authority_basis_hash,
            "record_source_gate": CONNECTOR_LOCAL_DESTINATION_RECEIPT_SOURCE_GATE,
            "external_connector_invocation_enabled": False,
            "destination_write_enabled": False,
            "connector_run_created": False,
            "network_write_enabled": False,
            "real_destination_integration_enabled": False,
        },
    }
    db.commit()

    return _response(request_id=request_id, status="recorded", row=row)
