from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services.layer3_aps_handoff import APS_HANDOFF_SCHEMA_ID, PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
from app.services.layer3_authority_rail import authority_rail
from app.services.layer3_external_export_contract import (
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS,
    ExternalExportDownloadDelivery,
)
from app.services.layer3_package_entry import (
    SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
    SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
)
from app.services.layer3_pass_entry import (
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    PASS_TYPE_SINGLE_ITEM,
    SOURCE_GATE_COHORT_DESC_FREEZE,
)
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_qual_aps_execution import (
    PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
    QUAL_APS_METHOD_NAME,
    QUAL_APS_SOURCE_GATE,
    SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone
from app.services.layer3_workbench_error import Layer3WorkbenchError
from app.services.layer3_workbench_package_state import (
    EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
    PACKAGE_REVIEW_APPROVED_STATE,
    aps_handoff_dispatch_from_reconciliation,
    external_export_download_prepare_from_reconciliation,
    packages_in_review_order,
)

EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = "layer3.external_export_download_prepare.v1"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = "layer3.external_export_download_delivery.v1"
QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = "layer3.qual_aps_external_export_download_prepare.v1"
QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = "layer3.qual_aps_external_export_download_delivery.v1"
SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = "layer3.source_intake_external_export_download_prepare.v1"
SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = "layer3.source_intake_external_export_download_delivery.v1"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID = "layer3.external_export_download_delivery_ui.v1"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION = "deliver_external_export_download"
EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION = "prepare_external_export_download"
EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE = "external_export_download_unavailable"
EXTERNAL_EXPORT_DOWNLOAD_READY_STATE = "external_export_download_ready"
EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE = "external_export_download_prepared"
EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE = "external_export_download_blocked"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE = "external_export_download_delivered"
HANDOFF_EXPORT_PREPARED_STATE = "handoff_export_prepared"
APS_HANDOFF_DISPATCHED_STATE = "aps_handoff_dispatched"
ASSOCIATED_COHORT_DELIVERY_UI_UNAVAILABLE_STATE = (
    "associated_cohort_external_export_download_delivery_ui_unavailable"
)
ASSOCIATED_COHORT_DELIVERY_UI_READY_STATE = "associated_cohort_external_export_download_delivery_ui_ready"
QUAL_APS_DELIVERY_UI_UNAVAILABLE_STATE = "external_export_download_delivery_ui_unavailable"
QUAL_APS_DELIVERY_UI_READY_STATE = "external_export_download_delivery_ui_ready"
SOURCE_INTAKE_DELIVERY_UI_UNAVAILABLE_STATE = "source_intake_external_export_download_delivery_ui_blocked"
SOURCE_INTAKE_DELIVERY_UI_READY_STATE = "source_intake_external_export_download_delivery_ui_ready"
EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE = (
    "browser_download",
    "download_url",
    "connector_dispatch",
    "destination_selection",
    "generic_downstream_dispatch",
)

ASSOCIATED_COHORT_READINESS_IDENTITY_FIELDS = (
    "pass_type",
    "pass_scope",
    "method",
    "source_gate",
    "package_construction_source_gate",
    "source_shape",
    "source_dataset_version_ids",
    "package_review_submit_schema_id",
    "content_id",
    "content_contract_id",
    "chunking_contract_id",
    "material_snapshot_id",
    "analysis_unit_id",
    "analysis_set_id",
    "output_payload_ref",
    "output_payload_hash",
    "source_intake_record_id",
    "candidate_id",
)


def cohort_readiness_identity(source: dict[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    for key in ASSOCIATED_COHORT_READINESS_IDENTITY_FIELDS:
        value = source.get(key)
        if value is not None:
            identity[key] = json_clone(value)
    return identity


def associated_cohort_external_export_download(readiness_state: dict[str, Any]) -> bool:
    return readiness_state.get("pass_type") == PASS_TYPE_ASSOCIATED_COHORT or (
        readiness_state.get("pass_scope") == PASS_SCOPE_QUANT_ASSOCIATED_COHORT
        and readiness_state.get("method") == "descriptive_summary"
        and readiness_state.get("source_gate") == SOURCE_GATE_COHORT_DESC_FREEZE
        and readiness_state.get("source_shape") == COHORT_SHAPE_ALIGNED_WIDE_TABLE
    )


def qualitative_aps_external_export_download_deferred(readiness_state: dict[str, Any]) -> bool:
    return bool(
        readiness_state.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        or readiness_state.get("source_gate") == QUAL_APS_SOURCE_GATE
        or readiness_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE
        or readiness_state.get("source_shape") == SOURCE_SHAPE_APS_CONTENT_DOCUMENT
    )


def qualitative_aps_external_export_download_admitted(readiness_state: dict[str, Any]) -> bool:
    return bool(
        readiness_state.get("pass_type") == PASS_TYPE_SINGLE_ITEM
        and readiness_state.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        and readiness_state.get("method") == QUAL_APS_METHOD_NAME
        and readiness_state.get("source_gate") == QUAL_APS_SOURCE_GATE
        and readiness_state.get("package_construction_source_gate")
        == SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE
        and readiness_state.get("source_shape") == SOURCE_SHAPE_APS_CONTENT_DOCUMENT
        and list(readiness_state.get("source_dataset_version_ids") or []) == []
        and bool(str(readiness_state.get("content_id") or "").strip())
        and bool(str(readiness_state.get("content_contract_id") or "").strip())
        and bool(str(readiness_state.get("chunking_contract_id") or "").strip())
        and bool(str(readiness_state.get("material_snapshot_id") or "").strip())
        and bool(str(readiness_state.get("analysis_unit_id") or "").strip())
        and bool(str(readiness_state.get("analysis_set_id") or "").strip())
        and bool(str(readiness_state.get("output_payload_ref") or "").strip())
        and bool(str(readiness_state.get("output_payload_hash") or "").strip())
    )


def source_intake_external_export_download_admitted(readiness_state: dict[str, Any]) -> bool:
    return bool(
        readiness_state.get("pass_type") == PASS_TYPE_SINGLE_ITEM
        and readiness_state.get("pass_scope") == "qualitative_single_item_operator_uploaded_source"
        and readiness_state.get("method") == "operator_uploaded_source_review_preview"
        and readiness_state.get("source_gate") == "306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE"
        and readiness_state.get("package_construction_source_gate")
        == "314_SOURCE_INTAKE_PACKAGE_CONSTRUCTION_COMMIT_BOUNDARY_FREEZE"
        and readiness_state.get("source_shape") == "operator_uploaded_single_source"
        and list(readiness_state.get("source_dataset_version_ids") or []) == []
        and readiness_state.get("package_review_submit_schema_id")
        == "layer3.source_intake_package_review_submit.v1"
        and bool(str(readiness_state.get("source_intake_record_id") or "").strip())
        and bool(str(readiness_state.get("candidate_id") or "").strip())
        and bool(str(readiness_state.get("output_payload_ref") or "").strip())
        and bool(str(readiness_state.get("output_payload_hash") or "").strip())
    )


def associated_cohort_delivery_ui_state(
    readiness_state: dict[str, Any],
    *,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    source_dataset_version_ids = readiness_state.get("source_dataset_version_ids")
    required_refs = (
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_envelope_ref",
        "aps_handoff_record_ref",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "source_artifact_hash",
        "source_artifact_size_bytes",
    )
    mismatches = [
        field
        for field, expected in {
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
            "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
            "method": "descriptive_summary",
            "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
            "package_construction_source_gate": SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
            "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
            "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
        }.items()
        if readiness_state.get(field) != expected
    ]
    missing_refs = [field for field in required_refs if readiness_state.get(field) in (None, "", [])]
    if not isinstance(source_dataset_version_ids, list) or not source_dataset_version_ids:
        missing_refs.append("source_dataset_version_ids")

    available = not blocked_reason and not mismatches and not missing_refs
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID,
        "available": available,
        "state": (
            ASSOCIATED_COHORT_DELIVERY_UI_READY_STATE
            if available
            else ASSOCIATED_COHORT_DELIVERY_UI_UNAVAILABLE_STATE
        ),
        "blocked_reason": blocked_reason
        or ("missing_or_mismatched_associated_cohort_delivery_authority" if not available else None),
        "blocked_fields": sorted(set(mismatches + missing_refs)),
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
        "delivery_mode": "same_origin_artifact_stream",
        "server_authority": "associated_cohort_external_export_download_delivery_ui_gate",
        "browser_managed_same_origin_attachment_enabled": available,
        "public_url_enabled": False,
        "signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "schema_runtime_source_widening_enabled": False,
    }


def qualitative_aps_delivery_ui_state(
    readiness_state: dict[str, Any],
    *,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    required_refs = (
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_envelope_ref",
        "aps_handoff_record_ref",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "content_id",
        "content_contract_id",
        "chunking_contract_id",
        "material_snapshot_id",
        "analysis_unit_id",
        "analysis_set_id",
        "output_payload_ref",
        "output_payload_hash",
    )
    mismatches = [
        field
        for field, expected in {
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
            "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
        }.items()
        if readiness_state.get(field) != expected
    ]
    missing_refs = [field for field in required_refs if readiness_state.get(field) in (None, "", [])]
    if not qualitative_aps_external_export_download_admitted(readiness_state):
        mismatches.append("qualitative_aps_external_export_download_authority")
    available = not blocked_reason and not mismatches and not missing_refs
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID,
        "available": available,
        "state": QUAL_APS_DELIVERY_UI_READY_STATE if available else QUAL_APS_DELIVERY_UI_UNAVAILABLE_STATE,
        "blocked_reason": blocked_reason
        or ("missing_or_mismatched_qualitative_aps_delivery_authority" if not available else None),
        "blocked_fields": sorted(set(mismatches + missing_refs)),
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
        "delivery_mode": "same_origin_artifact_stream",
        "server_authority": "qualitative_aps_external_export_download_delivery_ui_gate",
        "browser_managed_same_origin_attachment_enabled": available,
        "public_url_enabled": False,
        "signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "schema_runtime_source_widening_enabled": False,
    }


def aps_bundle_delivery_ui_state(
    readiness_state: dict[str, Any],
    *,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    required_refs = (
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_envelope_ref",
        "aps_handoff_record_ref",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "source_artifact_hash",
        "source_artifact_size_bytes",
    )
    mismatches = [
        field
        for field, expected in {
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
            "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
        }.items()
        if readiness_state.get(field) != expected
    ]
    missing_refs = [field for field in required_refs if readiness_state.get(field) in (None, "", [])]
    if (
        associated_cohort_external_export_download(readiness_state)
        or source_intake_external_export_download_admitted(readiness_state)
        or qualitative_aps_external_export_download_admitted(readiness_state)
    ):
        mismatches.append("generic_aps_bundle_delivery_authority")
    available = not blocked_reason and not mismatches and not missing_refs
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID,
        "available": available,
        "state": QUAL_APS_DELIVERY_UI_READY_STATE if available else QUAL_APS_DELIVERY_UI_UNAVAILABLE_STATE,
        "blocked_reason": blocked_reason
        or ("missing_or_mismatched_aps_bundle_delivery_authority" if not available else None),
        "blocked_fields": sorted(set(mismatches + missing_refs)),
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
        "delivery_mode": "same_origin_artifact_stream",
        "server_authority": "aps_bundle_external_export_download_delivery_ui_gate",
        "browser_managed_same_origin_attachment_enabled": available,
        "public_url_enabled": False,
        "signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "schema_runtime_source_widening_enabled": False,
    }


def source_intake_delivery_ui_state(
    readiness_state: dict[str, Any],
    *,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    required_refs = (
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_envelope_ref",
        "aps_handoff_record_ref",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "source_intake_record_id",
        "candidate_id",
        "output_payload_ref",
        "output_payload_hash",
    )
    mismatches = [
        field
        for field, expected in {
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "aps_handoff_state": APS_HANDOFF_DISPATCHED_STATE,
            "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
        }.items()
        if readiness_state.get(field) != expected
    ]
    missing_refs = [field for field in required_refs if readiness_state.get(field) in (None, "", [])]
    if not source_intake_external_export_download_admitted(readiness_state):
        mismatches.append("source_intake_external_export_download_authority")
    available = not blocked_reason and not mismatches and not missing_refs
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID,
        "available": available,
        "state": SOURCE_INTAKE_DELIVERY_UI_READY_STATE if available else SOURCE_INTAKE_DELIVERY_UI_UNAVAILABLE_STATE,
        "blocked_reason": blocked_reason
        or ("missing_or_mismatched_source_intake_delivery_authority" if not available else None),
        "blocked_fields": sorted(set(mismatches + missing_refs)),
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION,
        "delivery_mode": "same_origin_artifact_stream",
        "server_authority": "source_intake_external_export_download_delivery_ui_gate",
        "browser_managed_same_origin_attachment_enabled": available,
        "public_url_enabled": False,
        "signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "schema_runtime_source_widening_enabled": False,
    }


def _aps_handoff_package_for_dispatch(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
    dispatch_state: dict[str, Any],
) -> L3OutputPackage | None:
    output_package_id = str(dispatch_state.get("aps_output_package_id") or "").strip()
    if not output_package_id:
        return None
    return (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
            L3OutputPackage.output_package_id == output_package_id,
            L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        )
        .one_or_none()
    )


def aps_bundle_identity_for_external_export_download(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
    dispatch_state: dict[str, Any],
    error_prefix: str,
    existing_readiness: dict[str, Any] | None = None,
    validate_source_artifact: bool = True,
) -> dict[str, Any]:
    if dispatch_state.get("aps_handoff_state") != APS_HANDOFF_DISPATCHED_STATE:
        raise Layer3WorkbenchError(
            f"{error_prefix}_requires_aps_handoff_dispatch",
            "External export/download readiness requires recorded aps_handoff_dispatched state.",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_handoff_state"],
            next_allowed_actions=["record_aps_handoff_dispatch"],
        )
    if dispatch_state.get("aps_output_package_kind") != PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF:
        raise Layer3WorkbenchError(
            f"{error_prefix}_aps_package_kind_mismatch",
            "Recorded APS handoff dispatch must reference an aps_evidence_bundle_handoff package.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_output_package_kind"],
        )
    package = _aps_handoff_package_for_dispatch(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
        dispatch_state=dispatch_state,
    )
    if package is None:
        raise Layer3WorkbenchError(
            f"{error_prefix}_aps_package_missing",
            "Recorded APS handoff dispatch does not match an existing APS evidence-bundle handoff package.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_output_package_id"],
        )
    aps_bundle_ref = str(package.payload_ref or "").strip()
    if not aps_bundle_ref or aps_bundle_ref != str(dispatch_state.get("aps_bundle_ref") or "").strip():
        raise Layer3WorkbenchError(
            f"{error_prefix}_aps_bundle_ref_mismatch",
            "Recorded APS bundle ref does not match the APS handoff package payload ref.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
        )
    aps_summary = package.summary_json or {}
    aps_bundle_id = str(aps_summary.get("bundle_id") or "").strip()
    aps_schema_id = str(aps_summary.get("aps_schema_id") or APS_HANDOFF_SCHEMA_ID).strip()
    if not aps_bundle_id or aps_bundle_id != str(dispatch_state.get("aps_bundle_id") or "").strip():
        raise Layer3WorkbenchError(
            f"{error_prefix}_aps_bundle_id_mismatch",
            "Recorded APS bundle id does not match the APS handoff package summary.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_id"],
        )
    if not aps_schema_id or aps_schema_id != str(dispatch_state.get("aps_schema_id") or "").strip():
        raise Layer3WorkbenchError(
            f"{error_prefix}_aps_schema_mismatch",
            "Recorded APS schema id does not match the APS handoff package summary.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_schema_id"],
        )
    if not validate_source_artifact:
        source_artifact_hash = str(
            (existing_readiness or {}).get("source_artifact_hash") or package.payload_hash or ""
        ).strip()
        if not source_artifact_hash or str(package.payload_hash or "").strip() != source_artifact_hash:
            raise Layer3WorkbenchError(
                f"{error_prefix}_source_artifact_hash_mismatch",
                "Recorded external export/download readiness hash does not match the APS handoff package payload hash.",
                status="conflict",
                http_status=409,
                blocked_fields=["aps_bundle_hash"],
            )
        try:
            source_artifact_size = int((existing_readiness or {}).get("source_artifact_size_bytes") or -1)
        except (TypeError, ValueError):
            source_artifact_size = -1
        if source_artifact_size < 0:
            try:
                source_artifact_size = int(Path(aps_bundle_ref).stat().st_size)
            except (OSError, ValueError):
                source_artifact_size = -1
        if source_artifact_size < 0:
            raise Layer3WorkbenchError(
                f"{error_prefix}_source_artifact_size_mismatch",
                "Recorded external export/download readiness is missing the APS bundle artifact size.",
                status="conflict",
                http_status=409,
                blocked_fields=["aps_bundle_size_bytes"],
            )
        return {
            "aps_output_package_id": package.output_package_id,
            "aps_output_package_kind": package.package_kind,
            "aps_bundle_ref": aps_bundle_ref,
            "aps_bundle_id": aps_bundle_id,
            "aps_schema_id": aps_schema_id,
            "source_artifact_ref": aps_bundle_ref,
            "source_artifact_schema_id": aps_schema_id,
            "source_artifact_hash": source_artifact_hash,
            "source_artifact_size_bytes": source_artifact_size,
        }
    try:
        from app.services.nrc_aps_evidence_bundle import EvidenceBundleError, load_persisted_bundle_artifact
    except ModuleNotFoundError as exc:
        raise Layer3WorkbenchError(
            f"{error_prefix}_source_artifact_validator_unavailable",
            f"External export/download readiness could not load the APS bundle artifact validator: {exc}",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
            next_allowed_actions=["inspect_aps_handoff_dispatch_state"],
        ) from exc
    try:
        bundle_payload, bundle_path = load_persisted_bundle_artifact(bundle_ref=aps_bundle_ref)
    except EvidenceBundleError as exc:
        raise Layer3WorkbenchError(
            f"{error_prefix}_source_artifact_unavailable",
            f"External export/download readiness could not validate the existing APS bundle artifact: {exc.message}",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
            next_allowed_actions=["inspect_aps_handoff_dispatch_state"],
        ) from exc
    if str(bundle_payload.get("bundle_id") or "").strip() != aps_bundle_id:
        raise Layer3WorkbenchError(
            f"{error_prefix}_source_artifact_mismatch",
            "Validated APS bundle artifact does not match the recorded APS bundle id.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_id"],
        )
    source_artifact_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if str(package.payload_hash or "").strip() != source_artifact_hash:
        raise Layer3WorkbenchError(
            f"{error_prefix}_source_artifact_hash_mismatch",
            "Validated APS bundle artifact hash does not match the APS handoff package payload hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_hash"],
        )
    return {
        "aps_output_package_id": package.output_package_id,
        "aps_output_package_kind": package.package_kind,
        "aps_bundle_ref": aps_bundle_ref,
        "aps_bundle_id": aps_bundle_id,
        "aps_schema_id": aps_schema_id,
        "source_artifact_ref": aps_bundle_ref,
        "source_artifact_schema_id": aps_schema_id,
        "source_artifact_hash": source_artifact_hash,
        "source_artifact_size_bytes": int(bundle_path.stat().st_size),
    }


def external_export_download_prepare_summary(
    db: Session,
    *,
    session_id: str,
    aps_handoff_dispatch_state: dict[str, Any],
) -> dict[str, Any]:
    reconciliation_record_id = str(aps_handoff_dispatch_state.get("reconciliation_record_id") or "").strip()
    aps_handoff_record_ref = str(aps_handoff_dispatch_state.get("aps_handoff_record_ref") or "").strip()
    if (
        aps_handoff_dispatch_state.get("state") != APS_HANDOFF_DISPATCHED_STATE
        or not reconciliation_record_id
        or not aps_handoff_record_ref
    ):
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE,
            "blocked_reason": "aps_handoff_dispatched_required",
            "reconciliation_record_id": reconciliation_record_id or None,
            "aps_handoff_record_ref": aps_handoff_record_ref or None,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
            "external_export_download_prepare_enabled": False,
            "browser_download_enabled": False,
            "download_url_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_selection_enabled": False,
            "generic_downstream_dispatch_enabled": False,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
        }

    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.session_id == session_id,
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
        )
        .one_or_none()
    )
    recorded_dispatch = aps_handoff_dispatch_from_reconciliation(reconciliation)
    if recorded_dispatch is None:
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE,
            "blocked_reason": "aps_handoff_dispatch_state_missing",
            "reconciliation_record_id": reconciliation_record_id,
            "aps_handoff_record_ref": aps_handoff_record_ref,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
            "external_export_download_prepare_enabled": False,
            "browser_download_enabled": False,
            "download_url_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_selection_enabled": False,
            "generic_downstream_dispatch_enabled": False,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
        }
    recorded_readiness = external_export_download_prepare_from_reconciliation(reconciliation)
    if recorded_readiness is not None:
        summary_schema_id = (
            QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
            if qualitative_aps_external_export_download_admitted(recorded_readiness)
            else SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
            if source_intake_external_export_download_admitted(recorded_readiness)
            else EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID
        )
        summary = {
            "schema_id": summary_schema_id,
            "available": False,
            "state": recorded_readiness.get("external_export_download_state"),
            "blocked_reason": None,
            "external_export_download_record_ref": recorded_readiness.get("external_export_download_record_ref"),
            "export_download_descriptor_ref": recorded_readiness.get("export_download_descriptor_ref"),
            "operator_decision": recorded_readiness.get("operator_decision"),
            "decision_notes": recorded_readiness.get("decision_notes"),
            "analysis_run_id": recorded_readiness.get("analysis_run_id"),
            "result_review_record_ref": recorded_readiness.get("result_review_record_ref"),
            "package_review_preview_hash": recorded_readiness.get("package_review_preview_hash"),
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": list(recorded_readiness.get("output_package_ids") or []),
            "package_kinds": list(recorded_readiness.get("package_kinds") or []),
            "payload_refs": list(recorded_readiness.get("payload_refs") or []),
            "payload_hashes": list(recorded_readiness.get("payload_hashes") or []),
            "package_review_submit_record_ref": recorded_readiness.get("package_review_submit_record_ref"),
            "package_review_state": recorded_readiness.get("package_review_state"),
            "prepare_record_ref": recorded_readiness.get("prepare_record_ref"),
            "handoff_export_state": recorded_readiness.get("handoff_export_state"),
            "handoff_export_envelope_ref": recorded_readiness.get("handoff_export_envelope_ref"),
            "handoff_target": recorded_readiness.get("handoff_target"),
            "export_mode": recorded_readiness.get("export_mode"),
            "aps_handoff_record_ref": recorded_readiness.get("aps_handoff_record_ref"),
            "aps_handoff_state": recorded_readiness.get("aps_handoff_state"),
            "aps_handoff_target": recorded_readiness.get("aps_handoff_target"),
            "dispatch_mode": recorded_readiness.get("dispatch_mode"),
            "aps_output_package_id": recorded_readiness.get("aps_output_package_id"),
            "aps_output_package_kind": recorded_readiness.get("aps_output_package_kind"),
            "aps_bundle_ref": recorded_readiness.get("aps_bundle_ref"),
            "aps_bundle_id": recorded_readiness.get("aps_bundle_id"),
            "aps_schema_id": recorded_readiness.get("aps_schema_id"),
            "source_artifact_ref": recorded_readiness.get("source_artifact_ref"),
            "source_artifact_schema_id": recorded_readiness.get("source_artifact_schema_id"),
            "source_artifact_hash": recorded_readiness.get("source_artifact_hash"),
            "source_artifact_size_bytes": recorded_readiness.get("source_artifact_size_bytes"),
            **cohort_readiness_identity(recorded_readiness),
            "export_download_target": recorded_readiness.get("export_download_target"),
            "download_mode": recorded_readiness.get("download_mode"),
            "external_export_download_prepare_enabled": False,
            "browser_download_enabled": False,
            "download_url_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_selection_enabled": False,
            "generic_downstream_dispatch_enabled": False,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
        }
        if associated_cohort_external_export_download(recorded_readiness):
            summary["delivery_ui"] = recorded_readiness.get("delivery_ui") or associated_cohort_delivery_ui_state(
                recorded_readiness
            )
        elif source_intake_external_export_download_admitted(recorded_readiness):
            summary["delivery_ui"] = recorded_readiness.get("delivery_ui") or source_intake_delivery_ui_state(
                recorded_readiness
            )
        else:
            delivery_ui = recorded_readiness.get("delivery_ui") or aps_bundle_delivery_ui_state(recorded_readiness)
            if delivery_ui["available"]:
                summary["delivery_ui"] = delivery_ui
        return summary

    if (
        qualitative_aps_external_export_download_deferred(recorded_dispatch)
        and not qualitative_aps_external_export_download_admitted(recorded_dispatch)
    ):
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": EXTERNAL_EXPORT_DOWNLOAD_UNAVAILABLE_STATE,
            "blocked_reason": "qualitative_aps_external_export_download_not_admitted",
            "reconciliation_record_id": reconciliation_record_id,
            "aps_handoff_record_ref": aps_handoff_record_ref,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
            "external_export_download_prepare_enabled": False,
            "browser_download_enabled": False,
            "download_url_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_selection_enabled": False,
            "generic_downstream_dispatch_enabled": False,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
        }

    try:
        bundle_identity = aps_bundle_identity_for_external_export_download(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
            dispatch_state=recorded_dispatch,
            error_prefix="external_export_download_summary",
        )
    except Layer3WorkbenchError as exc:
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "available": False,
            "state": EXTERNAL_EXPORT_DOWNLOAD_BLOCKED_STATE,
            "blocked_reason": exc.message,
            "reconciliation_record_id": reconciliation_record_id,
            "aps_handoff_record_ref": aps_handoff_record_ref,
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
            "external_export_download_prepare_enabled": False,
            "browser_download_enabled": False,
            "download_url_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_selection_enabled": False,
            "generic_downstream_dispatch_enabled": False,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
        }

    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "available": True,
        "state": EXTERNAL_EXPORT_DOWNLOAD_READY_STATE,
        "blocked_reason": None,
        "analysis_run_id": recorded_dispatch.get("analysis_run_id"),
        "result_review_record_ref": recorded_dispatch.get("result_review_record_ref"),
        "package_review_preview_hash": recorded_dispatch.get("package_review_preview_hash"),
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": list(recorded_dispatch.get("output_package_ids") or []),
        "package_kinds": list(recorded_dispatch.get("package_kinds") or []),
        "payload_refs": list(recorded_dispatch.get("payload_refs") or []),
        "payload_hashes": list(recorded_dispatch.get("payload_hashes") or []),
        "package_review_submit_record_ref": recorded_dispatch.get("package_review_submit_record_ref"),
        "package_review_state": recorded_dispatch.get("package_review_state"),
        "prepare_record_ref": recorded_dispatch.get("prepare_record_ref"),
        "handoff_export_state": recorded_dispatch.get("handoff_export_state"),
        "handoff_export_envelope_ref": recorded_dispatch.get("handoff_export_envelope_ref"),
        "handoff_target": recorded_dispatch.get("handoff_target"),
        "export_mode": recorded_dispatch.get("export_mode"),
        "aps_handoff_record_ref": aps_handoff_record_ref,
        "aps_handoff_state": recorded_dispatch.get("aps_handoff_state"),
        "aps_handoff_target": recorded_dispatch.get("aps_handoff_target"),
        "dispatch_mode": recorded_dispatch.get("dispatch_mode"),
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "aps_output_package_id": bundle_identity["aps_output_package_id"],
        "aps_output_package_kind": bundle_identity["aps_output_package_kind"],
        "aps_bundle_ref": bundle_identity["aps_bundle_ref"],
        "aps_bundle_id": bundle_identity["aps_bundle_id"],
        "aps_schema_id": bundle_identity["aps_schema_id"],
        "source_artifact_ref": bundle_identity["source_artifact_ref"],
        "source_artifact_schema_id": bundle_identity["source_artifact_schema_id"],
        "source_artifact_hash": bundle_identity["source_artifact_hash"],
        "source_artifact_size_bytes": bundle_identity["source_artifact_size_bytes"],
        **cohort_readiness_identity(recorded_dispatch),
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "external_export_download_prepare_enabled": True,
        "browser_download_enabled": False,
        "download_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
    }


def external_export_download_prepare_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    preview_id: str,
    preview_hash: str,
    result_review_record_ref: str,
    package_review_preview_hash: str,
    reconciliation_record: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    readiness_state: dict[str, Any],
) -> dict[str, Any]:
    ordered_packages = packages_in_review_order(packages)
    body = {
        **base_response(
            QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
            if qualitative_aps_external_export_download_admitted(readiness_state)
            else SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
            if source_intake_external_export_download_admitted(readiness_state)
            else EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": readiness_state.get("analysis_run_id"),
        "result_review_record_ref": result_review_record_ref,
        "package_review_preview_hash": package_review_preview_hash,
        "reconciliation_record_id": reconciliation_record.reconciliation_record_id,
        "output_package_ids": [package.output_package_id for package in ordered_packages],
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": [package.payload_ref for package in ordered_packages],
        "payload_hashes": [package.payload_hash for package in ordered_packages],
        "package_review_submit_record_ref": readiness_state["package_review_submit_record_ref"],
        "package_review_state": readiness_state["package_review_state"],
        "prepare_record_ref": readiness_state["prepare_record_ref"],
        "handoff_export_state": readiness_state["handoff_export_state"],
        "handoff_export_envelope_ref": readiness_state["handoff_export_envelope_ref"],
        "handoff_target": readiness_state["handoff_target"],
        "export_mode": readiness_state["export_mode"],
        "aps_handoff_record_ref": readiness_state["aps_handoff_record_ref"],
        "aps_handoff_state": readiness_state["aps_handoff_state"],
        "aps_handoff_target": readiness_state["aps_handoff_target"],
        "dispatch_mode": readiness_state["dispatch_mode"],
        "aps_output_package_id": readiness_state["aps_output_package_id"],
        "aps_output_package_kind": readiness_state["aps_output_package_kind"],
        "aps_bundle_ref": readiness_state["aps_bundle_ref"],
        "aps_bundle_id": readiness_state["aps_bundle_id"],
        "aps_schema_id": readiness_state["aps_schema_id"],
        "export_download_target": readiness_state["export_download_target"],
        "download_mode": readiness_state["download_mode"],
        "operator_decision": readiness_state["operator_decision"],
        "decision_notes": readiness_state.get("decision_notes"),
        "external_export_download_state": readiness_state["external_export_download_state"],
        "external_export_download_record_ref": readiness_state["external_export_download_record_ref"],
        "export_download_descriptor_ref": readiness_state["export_download_descriptor_ref"],
        "source_artifact_ref": readiness_state["source_artifact_ref"],
        "source_artifact_schema_id": readiness_state["source_artifact_schema_id"],
        "source_artifact_hash": readiness_state["source_artifact_hash"],
        "source_artifact_size_bytes": readiness_state["source_artifact_size_bytes"],
        "browser_download_enabled": False,
        "download_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE),
        "next_state": readiness_state["external_export_download_state"],
        "authority_rail": authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode="durable_external_export_download_prepare",
            downstream_unavailable=EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }
    body.update(cohort_readiness_identity(readiness_state))
    if associated_cohort_external_export_download(readiness_state):
        body["delivery_ui"] = associated_cohort_delivery_ui_state(readiness_state)
    elif source_intake_external_export_download_admitted(readiness_state):
        body["delivery_ui"] = source_intake_delivery_ui_state(readiness_state)
    else:
        delivery_ui = aps_bundle_delivery_ui_state(readiness_state)
        if delivery_ui["available"]:
            body["delivery_ui"] = delivery_ui
    descriptor = readiness_state.get("external_export_download_descriptor")
    if isinstance(descriptor, dict):
        body["external_export_download_descriptor"] = descriptor
    return body


def safe_download_token(value: str, *, fallback: str) -> str:
    token = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in str(value or "").strip())
    token = token.strip(".-")
    return (token or fallback)[:96]


def external_export_download_prepare_payload_for_delivery(
    payload: dict[str, Any],
    *,
    readiness_state: dict[str, Any],
) -> dict[str, Any]:
    prepare_payload = {
        key: payload[key]
        for key in EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS
        if key in payload and key not in {"client_request_id", "operator_decision", "decision_notes"}
    }
    prepare_payload["client_request_id"] = str(readiness_state.get("client_request_id") or "").strip()
    prepare_payload["operator_decision"] = EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION
    if readiness_state.get("decision_notes") is not None:
        prepare_payload["decision_notes"] = readiness_state.get("decision_notes")
    return prepare_payload


def external_export_download_delivery_response(
    *,
    session_id: str,
    supplied_aps_bundle_id: str,
    supplied_readiness_ref: str,
    source_artifact_ref: str,
    expected_artifact_hash: str,
    expected_artifact_size: int,
    validation_body: dict[str, Any],
) -> ExternalExportDownloadDelivery:
    filename = (
        f"layer3-{safe_download_token(session_id, fallback='session')}-"
        f"{safe_download_token(supplied_aps_bundle_id, fallback='aps-bundle')}.json"
    )

    try:
        from app.services.nrc_aps_evidence_bundle import EvidenceBundleError, load_persisted_bundle_artifact
    except ModuleNotFoundError as exc:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_artifact_validator_unavailable",
            f"External export/download delivery could not load the APS bundle artifact validator: {exc}",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
            next_allowed_actions=["inspect_external_export_download_readiness"],
        ) from exc
    try:
        bundle_payload, bundle_path = load_persisted_bundle_artifact(bundle_ref=source_artifact_ref)
    except EvidenceBundleError as exc:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_source_artifact_unavailable",
            f"External export/download delivery could not validate the existing APS bundle artifact: {exc.message}",
            status="blocked",
            http_status=409,
            blocked_fields=["aps_bundle_ref"],
            next_allowed_actions=["inspect_external_export_download_readiness"],
        ) from exc

    artifact_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    artifact_size = int(bundle_path.stat().st_size)
    if artifact_hash != expected_artifact_hash:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_source_artifact_hash_mismatch",
            "Validated APS bundle artifact hash does not match recorded readiness.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_hash"],
        )
    if artifact_size != expected_artifact_size:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_source_artifact_size_mismatch",
            "Validated APS bundle artifact size does not match recorded readiness.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_size_bytes"],
        )
    if str(bundle_payload.get("bundle_id") or "") != supplied_aps_bundle_id:
        raise Layer3WorkbenchError(
            "external_export_download_delivery_aps_bundle_id_mismatch",
            "Validated APS bundle payload does not match the supplied APS bundle id.",
            status="conflict",
            http_status=409,
            blocked_fields=["aps_bundle_id"],
        )

    return ExternalExportDownloadDelivery(
        artifact_path=bundle_path,
        media_type="application/json",
        filename=filename,
        headers={
            "X-Layer3-Schema-Id": (
                QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID
                if qualitative_aps_external_export_download_admitted(validation_body)
                else SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID
                if source_intake_external_export_download_admitted(validation_body)
                else EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID
            ),
            "X-Layer3-Delivery-State": EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE,
            "X-Layer3-Source-Artifact-Hash": artifact_hash,
            "X-Layer3-External-Export-Download-Record-Ref": supplied_readiness_ref,
        },
        authority=json_clone(validation_body),
    )
