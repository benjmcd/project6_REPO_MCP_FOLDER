from __future__ import annotations

from typing import Any

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services.layer3_authority_rail import authority_rail
from app.services.layer3_package_submit_response import COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone
from app.services.layer3_workbench_package_state import (
    HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
    cohort_package_construction_source,
    packages_in_review_order,
)

HANDOFF_EXPORT_PREPARE_SCHEMA_ID = "layer3.handoff_export_prepare.v1"
COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID = "layer3.cohort_handoff_export_prepare.v1"


def handoff_export_prepare_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    preview_id: str,
    preview_hash: str,
    analysis_run_id: str | None,
    result_review_record_ref: str,
    package_review_preview_hash: str,
    reconciliation_record: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    prepare_state: dict[str, Any],
) -> dict[str, Any]:
    ordered_packages = packages_in_review_order(packages)
    body = {
        **base_response(HANDOFF_EXPORT_PREPARE_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": result_review_record_ref,
        "package_review_preview_hash": package_review_preview_hash,
        "reconciliation_record_id": reconciliation_record.reconciliation_record_id,
        "output_package_ids": [package.output_package_id for package in ordered_packages],
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": [package.payload_ref for package in ordered_packages],
        "payload_hashes": [package.payload_hash for package in ordered_packages],
        "package_review_submit_record_ref": prepare_state["package_review_submit_record_ref"],
        "package_review_state": prepare_state["package_review_state"],
        "operator_decision": prepare_state["operator_decision"],
        "decision_notes": prepare_state.get("decision_notes"),
        "handoff_export_state": prepare_state["handoff_export_state"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "external_handoff_enabled": False,
        "external_export_enabled": False,
        "dispatch_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_state": prepare_state["handoff_export_state"],
        "prepare_record_ref": prepare_state["prepare_record_ref"],
        "authority_rail": authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode="durable_handoff_export_prepare",
            downstream_unavailable=HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }
    envelope = prepare_state.get("handoff_export_envelope")
    if isinstance(envelope, dict):
        body["handoff_export_envelope"] = envelope
    if cohort_package_construction_source(prepare_state.get("package_construction_source_gate")):
        body["schema_id"] = COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID
        body["package_review_submit_schema_id"] = COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    for key in (
        "pass_type",
        "pass_scope",
        "method",
        "source_gate",
        "package_construction_source_gate",
        "source_shape",
        "source_dataset_version_ids",
        "package_review_submit_schema_id",
    ):
        if key in prepare_state:
            body[key] = json_clone(prepare_state[key])
    return body
