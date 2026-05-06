from __future__ import annotations

from typing import Any

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services.layer3_aps_handoff import PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
from app.services.layer3_authority_rail import authority_rail
from app.services.layer3_package_entry import SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE
from app.services.layer3_pass_entry import (
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    SOURCE_GATE_COHORT_DESC_FREEZE,
)
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone
from app.services.layer3_workbench_package_state import (
    PACKAGE_REVIEW_APPROVED_STATE,
    packages_in_review_order,
)

EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = "layer3.external_export_download_prepare.v1"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID = "layer3.external_export_download_delivery_ui.v1"
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION = "deliver_external_export_download"
EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE = "external_export_download_prepared"
HANDOFF_EXPORT_PREPARED_STATE = "handoff_export_prepared"
APS_HANDOFF_DISPATCHED_STATE = "aps_handoff_dispatched"
ASSOCIATED_COHORT_DELIVERY_UI_UNAVAILABLE_STATE = (
    "associated_cohort_external_export_download_delivery_ui_unavailable"
)
ASSOCIATED_COHORT_DELIVERY_UI_READY_STATE = "associated_cohort_external_export_download_delivery_ui_ready"
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
        **base_response(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID, request_id=request_id, status=status),
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
    descriptor = readiness_state.get("external_export_download_descriptor")
    if isinstance(descriptor, dict):
        body["external_export_download_descriptor"] = descriptor
    return body
