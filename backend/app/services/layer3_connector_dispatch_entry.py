from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3OutputPackage, L3PassRun, L3ReconciliationRecord, L3Session
from app.services import layer3_workbench
from app.services.layer3_aps_handoff import PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
from app.services.layer3_pass_entry import PASS_SCOPE_QUANT_ASSOCIATED_COHORT, PASS_TYPE_ASSOCIATED_COHORT
from app.services.layer3_utils import json_clone, stable_id, utcnow_iso_z


CONNECTOR_DISPATCH_RECORD_SCHEMA_ID = "layer3.connector_dispatch_record.v1"
CONNECTOR_DISPATCH_RECORD_STATE_SCHEMA_ID = "layer3.connector_dispatch_record_state.v1"
CONNECTOR_DISPATCH_RECORD_SOURCE_GATE = "121_CONNECTOR_DISPATCH_ENTRY_FREEZE"
CONNECTOR_DISPATCH_RECORD_MODE = "internal_dispatch_record_only"
CONNECTOR_DISPATCH_RECORD_STATE = "connector_dispatch_recorded"
CONNECTOR_DISPATCH_RECORD_OPERATOR_DECISION = "record_internal_connector_dispatch"
CONNECTOR_DISPATCH_RECORD_DELIVERY_MODE = "same_origin_artifact_stream"

CONNECTOR_DISPATCH_RECORD_REQUIRED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_state",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "external_export_download_record_ref",
        "external_export_download_state",
        "delivery_mode",
        "operator_decision",
        "client_request_id",
    }
)
CONNECTOR_DISPATCH_RECORD_OPTIONAL_FIELDS = frozenset(
    {
        "decision_notes",
        "analysis_run_id",
        "external_export_download_descriptor_ref",
        "source_artifact_ref",
        "source_artifact_schema_id",
    }
)
CONNECTOR_DISPATCH_RECORD_FORBIDDEN_FIELDS = frozenset(
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
    }
)
CONNECTOR_DISPATCH_RECORD_ALLOWED_FIELDS = (
    CONNECTOR_DISPATCH_RECORD_REQUIRED_FIELDS | CONNECTOR_DISPATCH_RECORD_OPTIONAL_FIELDS
)
CONNECTOR_DISPATCH_RECORD_DOWNSTREAM_UNAVAILABLE = (
    "external_connector_invocation",
    "destination_write",
    "connector_run_creation",
    "provider_public_url",
    "package_mutation_reconstruction",
    "source_upload_expansion",
    "broad_qualitative_hybrid_rag_execution",
    "full_mockup_activation",
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_string(item) for item in value]


def _state_from_reconciliation(
    reconciliation: L3ReconciliationRecord,
    key: str,
    expected_schema: str,
) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get(key)
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != expected_schema:
        return None
    return state


def _record_from_reconciliation(reconciliation: L3ReconciliationRecord) -> dict[str, Any] | None:
    return _state_from_reconciliation(
        reconciliation,
        "connector_dispatch_record",
        CONNECTOR_DISPATCH_RECORD_STATE_SCHEMA_ID,
    )


def _raise_mismatch(error_code: str, field: str, message: str) -> None:
    raise layer3_workbench.Layer3WorkbenchError(
        error_code,
        message,
        status="conflict",
        http_status=409,
        blocked_fields=[field],
    )


def _compare_required_payload(
    *,
    payload: dict[str, Any],
    readiness_state: dict[str, Any],
    aps_state: dict[str, Any],
) -> None:
    expected_values = {
        "analysis_plan_id": readiness_state.get("analysis_plan_id"),
        "pass_run_id": readiness_state.get("pass_run_id"),
        "result_review_record_ref": readiness_state.get("result_review_record_ref"),
        "package_review_preview_hash": readiness_state.get("package_review_preview_hash"),
        "reconciliation_record_id": readiness_state.get("reconciliation_record_id"),
        "package_review_submit_record_ref": readiness_state.get("package_review_submit_record_ref"),
        "prepare_record_ref": readiness_state.get("prepare_record_ref"),
        "handoff_export_state": layer3_workbench.HANDOFF_EXPORT_PREPARED_STATE,
        "aps_handoff_record_ref": readiness_state.get("aps_handoff_record_ref"),
        "aps_handoff_state": layer3_workbench.APS_HANDOFF_DISPATCHED_STATE,
        "aps_handoff_target": "aps_evidence_bundle",
        "aps_output_package_id": readiness_state.get("aps_output_package_id"),
        "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        "aps_bundle_ref": readiness_state.get("aps_bundle_ref"),
        "source_artifact_hash": readiness_state.get("source_artifact_hash"),
        "external_export_download_record_ref": readiness_state.get("external_export_download_record_ref"),
        "external_export_download_state": layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
        "delivery_mode": CONNECTOR_DISPATCH_RECORD_DELIVERY_MODE,
        "operator_decision": CONNECTOR_DISPATCH_RECORD_OPERATOR_DECISION,
    }
    for field, expected in expected_values.items():
        if _string(payload.get(field)) != _string(expected):
            _raise_mismatch(
                f"connector_dispatch_record_{field}_mismatch",
                field,
                f"Supplied {field} does not match the existing connector dispatch authority chain.",
            )
    optional_expected_values = {
        "analysis_run_id": readiness_state.get("analysis_run_id"),
        "external_export_download_descriptor_ref": readiness_state.get("export_download_descriptor_ref"),
        "source_artifact_ref": readiness_state.get("source_artifact_ref"),
        "source_artifact_schema_id": readiness_state.get("source_artifact_schema_id"),
    }
    for field, expected in optional_expected_values.items():
        if field in payload and _string(payload.get(field)) != _string(expected):
            _raise_mismatch(
                f"connector_dispatch_record_{field}_mismatch",
                field,
                f"Supplied {field} does not match the existing connector dispatch authority chain.",
            )

    if _string_list(payload.get("output_package_ids")) != _string_list(readiness_state.get("output_package_ids")):
        _raise_mismatch(
            "connector_dispatch_record_output_package_ids_mismatch",
            "output_package_ids",
            "Supplied output_package_ids do not match the recorded external export/download readiness.",
        )
    if _string_list(payload.get("package_kinds")) != _string_list(readiness_state.get("package_kinds")):
        _raise_mismatch(
            "connector_dispatch_record_package_kinds_mismatch",
            "package_kinds",
            "Supplied package_kinds do not match the recorded external export/download readiness.",
        )
    if _string_list(payload.get("payload_refs")) != _string_list(readiness_state.get("payload_refs")):
        _raise_mismatch(
            "connector_dispatch_record_payload_refs_mismatch",
            "payload_refs",
            "Supplied payload_refs do not match the recorded external export/download readiness.",
        )
    if _string_list(payload.get("payload_hashes")) != _string_list(readiness_state.get("payload_hashes")):
        _raise_mismatch(
            "connector_dispatch_record_payload_hashes_mismatch",
            "payload_hashes",
            "Supplied payload_hashes do not match the recorded external export/download readiness.",
        )

    try:
        supplied_size = int(payload.get("source_artifact_size_bytes"))
    except (TypeError, ValueError):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_source_artifact_size_invalid",
            "source_artifact_size_bytes must be an integer.",
            status="invalid",
            blocked_fields=["source_artifact_size_bytes"],
        ) from None
    if supplied_size != int(readiness_state.get("source_artifact_size_bytes") or -1):
        _raise_mismatch(
            "connector_dispatch_record_source_artifact_size_mismatch",
            "source_artifact_size_bytes",
            "Supplied source_artifact_size_bytes does not match the recorded external export/download readiness.",
        )

    for field in (
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
    ):
        if _string(readiness_state.get(field)) != _string(aps_state.get(field)):
            _raise_mismatch(
                f"connector_dispatch_record_aps_{field}_stale",
                field,
                "Recorded external export/download readiness no longer matches APS handoff dispatch authority.",
            )


def _record_basis(
    *,
    payload: dict[str, Any],
    readiness_state: dict[str, Any],
    aps_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.connector_dispatch_record_authority.v1",
        "record_source_gate": CONNECTOR_DISPATCH_RECORD_SOURCE_GATE,
        "client_request_id": _string(payload.get("client_request_id")),
        "dispatch_mode": CONNECTOR_DISPATCH_RECORD_MODE,
        "operator_decision": CONNECTOR_DISPATCH_RECORD_OPERATOR_DECISION,
        "decision_notes": _string(payload.get("decision_notes")) or None,
        "delivery_mode": CONNECTOR_DISPATCH_RECORD_DELIVERY_MODE,
        "session_id": _string(payload.get("session_id")),
        "analysis_plan_id": readiness_state.get("analysis_plan_id"),
        "pass_run_id": readiness_state.get("pass_run_id"),
        "analysis_run_id": readiness_state.get("analysis_run_id"),
        "result_review_record_ref": readiness_state.get("result_review_record_ref"),
        "package_review_preview_hash": readiness_state.get("package_review_preview_hash"),
        "reconciliation_record_id": readiness_state.get("reconciliation_record_id"),
        "output_package_ids": _string_list(readiness_state.get("output_package_ids")),
        "package_kinds": _string_list(readiness_state.get("package_kinds")),
        "payload_refs": _string_list(readiness_state.get("payload_refs")),
        "payload_hashes": _string_list(readiness_state.get("payload_hashes")),
        "package_review_submit_record_ref": readiness_state.get("package_review_submit_record_ref"),
        "package_review_state": readiness_state.get("package_review_state"),
        "prepare_record_ref": readiness_state.get("prepare_record_ref"),
        "handoff_export_state": readiness_state.get("handoff_export_state"),
        "aps_handoff_record_ref": readiness_state.get("aps_handoff_record_ref"),
        "aps_handoff_state": readiness_state.get("aps_handoff_state"),
        "aps_handoff_target": readiness_state.get("aps_handoff_target"),
        "aps_output_package_id": readiness_state.get("aps_output_package_id"),
        "aps_output_package_kind": readiness_state.get("aps_output_package_kind"),
        "aps_bundle_ref": readiness_state.get("aps_bundle_ref"),
        "source_artifact_ref": readiness_state.get("source_artifact_ref"),
        "source_artifact_schema_id": readiness_state.get("source_artifact_schema_id"),
        "source_artifact_hash": readiness_state.get("source_artifact_hash"),
        "source_artifact_size_bytes": readiness_state.get("source_artifact_size_bytes"),
        "external_export_download_record_ref": readiness_state.get("external_export_download_record_ref"),
        "external_export_download_state": readiness_state.get("external_export_download_state"),
        "external_export_download_descriptor_ref": readiness_state.get("export_download_descriptor_ref"),
        "aps_authority_ref": aps_state.get("aps_handoff_record_ref"),
    }


def _response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    record_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            CONNECTOR_DISPATCH_RECORD_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "session_id": session_id,
        "analysis_plan_id": record_state["analysis_plan_id"],
        "pass_run_id": record_state["pass_run_id"],
        "preview_identity": {
            "preview_id": record_state.get("source_preview_id"),
            "preview_hash": record_state.get("source_preview_hash"),
        },
        "analysis_run_id": record_state.get("analysis_run_id"),
        "result_review_record_ref": record_state["result_review_record_ref"],
        "package_review_preview_hash": record_state["package_review_preview_hash"],
        "reconciliation_record_id": record_state["reconciliation_record_id"],
        "output_package_ids": _string_list(record_state.get("output_package_ids")),
        "package_kinds": _string_list(record_state.get("package_kinds")),
        "payload_refs": _string_list(record_state.get("payload_refs")),
        "payload_hashes": _string_list(record_state.get("payload_hashes")),
        "package_review_submit_record_ref": record_state["package_review_submit_record_ref"],
        "package_review_state": record_state["package_review_state"],
        "prepare_record_ref": record_state["prepare_record_ref"],
        "handoff_export_state": record_state["handoff_export_state"],
        "aps_handoff_record_ref": record_state["aps_handoff_record_ref"],
        "aps_handoff_state": record_state["aps_handoff_state"],
        "aps_handoff_target": record_state["aps_handoff_target"],
        "aps_output_package_id": record_state["aps_output_package_id"],
        "aps_output_package_kind": record_state["aps_output_package_kind"],
        "aps_bundle_ref": record_state["aps_bundle_ref"],
        "source_artifact_ref": record_state["source_artifact_ref"],
        "source_artifact_schema_id": record_state["source_artifact_schema_id"],
        "source_artifact_hash": record_state["source_artifact_hash"],
        "source_artifact_size_bytes": record_state["source_artifact_size_bytes"],
        "external_export_download_record_ref": record_state["external_export_download_record_ref"],
        "external_export_download_state": record_state["external_export_download_state"],
        "external_export_download_descriptor_ref": record_state["external_export_download_descriptor_ref"],
        "delivery_mode": record_state["delivery_mode"],
        "operator_decision": record_state["operator_decision"],
        "decision_notes": record_state.get("decision_notes"),
        "dispatch_mode": record_state["dispatch_mode"],
        "connector_dispatch_record_state": record_state["connector_dispatch_record_state"],
        "connector_dispatch_record_ref": record_state["connector_dispatch_record_ref"],
        "internal_dispatch_record_only_enabled": True,
        "external_connector_invocation_enabled": False,
        "destination_write_enabled": False,
        "connector_run_created": False,
        "provider_public_url_enabled": False,
        "package_mutation_enabled": False,
        "source_widening_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "downstream_unavailable": list(CONNECTOR_DISPATCH_RECORD_DOWNSTREAM_UNAVAILABLE),
        "next_state": CONNECTOR_DISPATCH_RECORD_STATE,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=session_id,
            current_gate="package",
            persistence_mode="durable_connector_dispatch_record",
            downstream_unavailable=CONNECTOR_DISPATCH_RECORD_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def record_internal_connector_dispatch(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for internal connector dispatch record.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_connector_dispatch_record_request"],
        )

    unknown = sorted(key for key in payload if key not in CONNECTOR_DISPATCH_RECORD_ALLOWED_FIELDS)
    forbidden = sorted(key for key in CONNECTOR_DISPATCH_RECORD_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_scope_not_admitted",
            "Internal connector dispatch record request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_internal_dispatch_record_only_request"],
        )

    missing = sorted(
        field
        for field in CONNECTOR_DISPATCH_RECORD_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_connector_dispatch_record_fields",
            "Internal connector dispatch record request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_connector_dispatch_record_request"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    delivery_mode = _string(payload.get("delivery_mode"))
    operator_decision = _string(payload.get("operator_decision"))
    decision_notes = _string(payload.get("decision_notes")) or None

    if delivery_mode != CONNECTOR_DISPATCH_RECORD_DELIVERY_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_delivery_mode_not_admitted",
            "delivery_mode must be same_origin_artifact_stream for the first internal connector record lane.",
            status="invalid",
            blocked_fields=["delivery_mode"],
        )
    if operator_decision != CONNECTOR_DISPATCH_RECORD_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_connector_dispatch_record_decision",
            "operator_decision must be record_internal_connector_dispatch.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

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
            "connector_dispatch_record_requires_existing_authority",
            "Internal connector dispatch record requires existing session, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_external_export_download_prepare_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and approved plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    aps_state = _state_from_reconciliation(
        reconciliation,
        "aps_handoff_dispatch",
        layer3_workbench.APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
    )
    if aps_state is None or aps_state.get("aps_handoff_state") != layer3_workbench.APS_HANDOFF_DISPATCHED_STATE:
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_requires_aps_handoff_dispatch",
            "Internal connector dispatch record requires recorded APS handoff dispatch.",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_handoff_state"],
            next_allowed_actions=["record_aps_handoff_dispatch"],
        )
    readiness_state = _state_from_reconciliation(
        reconciliation,
        "external_export_download_prepare",
        layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
    )
    if (
        readiness_state is None
        or readiness_state.get("external_export_download_state")
        != layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_requires_external_export_download_prepare",
            "Internal connector dispatch record requires recorded external_export_download_prepared state.",
            status="blocked",
            http_status=409,
            blocked_fields=["external_export_download_state"],
            next_allowed_actions=["record_external_export_download_prepare"],
        )
    if (
        readiness_state.get("pass_type") != PASS_TYPE_ASSOCIATED_COHORT
        or readiness_state.get("pass_scope") != PASS_SCOPE_QUANT_ASSOCIATED_COHORT
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_source_not_admitted",
            "Internal connector dispatch record is admitted only for associated-cohort APS evidence-bundle authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["pass_type", "pass_scope"],
            next_allowed_actions=["inspect_associated_cohort_external_export_download_prepare_state"],
        )

    _compare_required_payload(payload=payload, readiness_state=readiness_state, aps_state=aps_state)

    source_package_ids = _string_list(readiness_state.get("output_package_ids"))
    source_packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
            L3OutputPackage.output_package_id.in_(source_package_ids),
        )
        .order_by(L3OutputPackage.package_kind.asc())
        .all()
    )
    if {package.output_package_id for package in source_packages} != set(source_package_ids):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_package_rows_mismatch",
            "Internal connector dispatch record requires the recorded source package rows to remain present.",
            status="conflict",
            http_status=409,
            blocked_fields=["output_package_ids"],
        )
    aps_package = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
            L3OutputPackage.output_package_id == readiness_state.get("aps_output_package_id"),
            L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        )
        .one_or_none()
    )
    if aps_package is None or aps_package.payload_ref != readiness_state.get("aps_bundle_ref"):
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_aps_package_row_mismatch",
            "Internal connector dispatch record requires the recorded APS evidence-bundle package row.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_output_package_id", "aps_bundle_ref"],
        )

    basis = _record_basis(payload=payload, readiness_state=readiness_state, aps_state=aps_state)
    record_ref = stable_id("l3-connector-dispatch-record", basis)
    existing_record = _record_from_reconciliation(reconciliation)
    if existing_record is not None:
        if existing_record.get("connector_dispatch_record_ref") == record_ref and existing_record.get(
            "client_request_id"
        ) == request_id:
            return _response(
                request_id=request_id,
                status="already_recorded",
                session_id=session_id,
                record_state=existing_record,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "connector_dispatch_record_already_recorded",
            "This external export/download readiness already has an internal connector dispatch record.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "operator_decision"],
        )

    record_state = {
        "schema_id": CONNECTOR_DISPATCH_RECORD_STATE_SCHEMA_ID,
        "client_request_id": request_id,
        "connector_dispatch_record_ref": record_ref,
        "connector_dispatch_record_state": CONNECTOR_DISPATCH_RECORD_STATE,
        "dispatch_mode": CONNECTOR_DISPATCH_RECORD_MODE,
        "delivery_mode": CONNECTOR_DISPATCH_RECORD_DELIVERY_MODE,
        "operator_decision": CONNECTOR_DISPATCH_RECORD_OPERATOR_DECISION,
        "decision_notes": decision_notes,
        "record_source_gate": CONNECTOR_DISPATCH_RECORD_SOURCE_GATE,
        "authority_basis": basis,
        "analysis_plan_id": readiness_state["analysis_plan_id"],
        "pass_run_id": readiness_state["pass_run_id"],
        "source_preview_id": readiness_state.get("source_preview_id"),
        "source_preview_hash": readiness_state.get("source_preview_hash"),
        "analysis_run_id": readiness_state.get("analysis_run_id"),
        "result_review_record_ref": readiness_state["result_review_record_ref"],
        "package_review_preview_hash": readiness_state["package_review_preview_hash"],
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": _string_list(readiness_state.get("output_package_ids")),
        "package_kinds": _string_list(readiness_state.get("package_kinds")),
        "payload_refs": _string_list(readiness_state.get("payload_refs")),
        "payload_hashes": _string_list(readiness_state.get("payload_hashes")),
        "package_review_submit_record_ref": readiness_state["package_review_submit_record_ref"],
        "package_review_state": readiness_state["package_review_state"],
        "prepare_record_ref": readiness_state["prepare_record_ref"],
        "handoff_export_state": readiness_state["handoff_export_state"],
        "aps_handoff_record_ref": readiness_state["aps_handoff_record_ref"],
        "aps_handoff_state": readiness_state["aps_handoff_state"],
        "aps_handoff_target": readiness_state["aps_handoff_target"],
        "aps_output_package_id": readiness_state["aps_output_package_id"],
        "aps_output_package_kind": readiness_state["aps_output_package_kind"],
        "aps_bundle_ref": readiness_state["aps_bundle_ref"],
        "source_artifact_ref": readiness_state["source_artifact_ref"],
        "source_artifact_schema_id": readiness_state["source_artifact_schema_id"],
        "source_artifact_hash": readiness_state["source_artifact_hash"],
        "source_artifact_size_bytes": readiness_state["source_artifact_size_bytes"],
        "external_export_download_record_ref": readiness_state["external_export_download_record_ref"],
        "external_export_download_state": readiness_state["external_export_download_state"],
        "external_export_download_descriptor_ref": readiness_state["export_download_descriptor_ref"],
        "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
        "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
        "method": readiness_state.get("method"),
        "source_gate": readiness_state.get("source_gate"),
        "package_construction_source_gate": readiness_state.get("package_construction_source_gate"),
        "source_shape": readiness_state.get("source_shape"),
        "source_dataset_version_ids": json_clone(readiness_state.get("source_dataset_version_ids") or []),
        "recorded_at": utcnow_iso_z(),
        "internal_dispatch_record_only_enabled": True,
        "external_connector_invocation_enabled": False,
        "destination_write_enabled": False,
        "connector_run_created": False,
        "provider_public_url_enabled": False,
        "package_mutation_enabled": False,
        "source_widening_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "downstream_unavailable": list(CONNECTOR_DISPATCH_RECORD_DOWNSTREAM_UNAVAILABLE),
    }
    reconciliation.summary_json = {
        **json_clone(reconciliation.summary_json or {}),
        "connector_dispatch_record": record_state,
    }
    db.commit()

    return _response(
        request_id=request_id,
        status="recorded",
        session_id=session_id,
        record_state=record_state,
    )
