from __future__ import annotations

from typing import Any

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services.layer3_authority_rail import authority_rail
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_response_contract import base_response
from app.services.layer3_utils import json_clone
from app.services.layer3_workbench_package_state import (
    cohort_package_construction_source,
    package_review_submit_downstream_unavailable,
    packages_in_review_order,
)

PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = "layer3.package_review_submit.v1"
COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = "layer3.cohort_package_review_submit.v1"
QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = "layer3.qual_aps_package_review_submit.v1"
SOURCE_INTAKE_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = "layer3.source_intake_package_review_submit.v1"


def package_review_submit_response(
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
    review_state: dict[str, Any],
) -> dict[str, Any]:
    ordered_packages = packages_in_review_order(packages)
    associated_cohort_submit = cohort_package_construction_source(
        review_state.get("package_construction_source_gate")
    )
    qualitative_aps_submit = (
        str(review_state.get("package_construction_source_gate") or "")
        == "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE"
    )
    source_intake_submit = (
        str(review_state.get("package_construction_source_gate") or "")
        == "314_SOURCE_INTAKE_PACKAGE_CONSTRUCTION_COMMIT_BOUNDARY_FREEZE"
    )
    downstream_unavailable = package_review_submit_downstream_unavailable(
        str(review_state.get("package_review_state") or ""),
        associated_cohort_submit=associated_cohort_submit,
        qualitative_aps_submit=qualitative_aps_submit,
        source_intake_submit=source_intake_submit,
    )
    body = {
        **base_response(PACKAGE_REVIEW_SUBMIT_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "analysis_run_id": analysis_run_id,
        "result_review_record_ref": result_review_record_ref,
        "package_review_preview_hash": package_review_preview_hash,
        "construction_basis_hash": review_state.get("construction_basis_hash"),
        "reconciliation_record_id": reconciliation_record.reconciliation_record_id,
        "output_package_ids": [package.output_package_id for package in ordered_packages],
        "package_kinds": [package.package_kind for package in ordered_packages],
        "payload_refs": [package.payload_ref for package in ordered_packages],
        "payload_hashes": [package.payload_hash for package in ordered_packages],
        "operator_decision": review_state["operator_decision"],
        "decision_notes": review_state.get("decision_notes"),
        "package_review_state": review_state["package_review_state"],
        "submit_record_ref": review_state["submit_record_ref"],
        "pass_type": review_state.get("pass_type"),
        "pass_scope": review_state.get("pass_scope"),
        "method": review_state.get("method"),
        "source_gate": review_state.get("source_gate"),
        "package_construction_source_gate": review_state.get("package_construction_source_gate"),
        "source_shape": review_state.get("source_shape"),
        "source_dataset_version_ids": json_clone(review_state.get("source_dataset_version_ids") or []),
        "source_intake_record_id": review_state.get("source_intake_record_id"),
        "candidate_id": review_state.get("candidate_id"),
        "output_payload_ref": review_state.get("output_payload_ref"),
        "output_payload_hash": review_state.get("output_payload_hash"),
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "export_enabled": False,
        "aps_handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "downstream_unavailable": list(downstream_unavailable),
        "next_state": review_state["package_review_state"],
        "authority_rail": authority_rail(
            session_id=session_id,
            current_gate="package",
            persistence_mode=(
                "durable_source_intake_package_review_submit"
                if source_intake_submit
                else "durable_package_review_submit"
            ),
            downstream_unavailable=downstream_unavailable,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }
    if associated_cohort_submit:
        body["schema_id"] = COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    if qualitative_aps_submit:
        body["schema_id"] = QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    if source_intake_submit:
        body["schema_id"] = SOURCE_INTAKE_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    return body
