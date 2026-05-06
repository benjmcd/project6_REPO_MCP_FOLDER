from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services import layer3_external_export_response as export_response
from app.services import layer3_workbench
from app.services.layer3_aps_handoff import PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
)
from app.services.layer3_pass_entry import (
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    SOURCE_GATE_COHORT_DESC_FREEZE,
)


def _package(package_kind: str, output_package_id: str, *, payload_hash: str) -> L3OutputPackage:
    return L3OutputPackage(
        package_kind=package_kind,
        output_package_id=output_package_id,
        payload_hash=payload_hash,
        payload_ref=f"payload://{output_package_id}",
    )


def _packages() -> list[L3OutputPackage]:
    return [
        _package(PACKAGE_KIND_USER_FACING, "pkg-user", payload_hash="hash-user"),
        _package(PACKAGE_KIND_CANONICAL_INTERNAL, "pkg-internal", payload_hash="hash-internal"),
        _package(PACKAGE_KIND_REVIEW_FACING, "pkg-review", payload_hash="hash-review"),
    ]


def _reconciliation() -> L3ReconciliationRecord:
    return L3ReconciliationRecord(reconciliation_record_id="reconciliation-export-response")


def _readiness_state(**overrides) -> dict:
    state = {
        "analysis_run_id": "analysis-run-export-response",
        "result_review_record_ref": "layer3://result-review/record",
        "package_review_preview_hash": "package-preview-hash-export",
        "reconciliation_record_id": "reconciliation-export-response",
        "package_review_submit_record_ref": "layer3://package-review-submit/record",
        "package_review_state": "package_review_approved",
        "prepare_record_ref": "layer3://handoff-export/prepare/record",
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": "layer3://handoff-export/envelope",
        "handoff_target": "aps_evidence_bundle_handoff",
        "export_mode": "reference_envelope_prepare_only",
        "aps_handoff_record_ref": "layer3://aps-handoff/record",
        "aps_handoff_state": "aps_handoff_dispatched",
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "aps_evidence_bundle_only",
        "aps_output_package_id": "pkg-aps",
        "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        "aps_bundle_ref": "layer3://aps-bundle/ref",
        "aps_bundle_id": "aps-bundle-id",
        "aps_schema_id": "aps.schema.v1",
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "operator_decision": "prepare_external_export_download",
        "decision_notes": "Prepare reference-only download.",
        "external_export_download_state": "external_export_download_prepared",
        "external_export_download_record_ref": "layer3://external-export-download/record",
        "export_download_descriptor_ref": "layer3://external-export-download/descriptor",
        "source_artifact_ref": "layer3://artifacts/aps-bundle",
        "source_artifact_schema_id": "layer3.aps_bundle_artifact.v1",
        "source_artifact_hash": "hash-artifact",
        "source_artifact_size_bytes": 4096,
    }
    state.update(overrides)
    return state


def _response_kwargs(**readiness_overrides) -> dict:
    return {
        "request_id": "request-export-response",
        "status": "prepared",
        "session_id": "session-export-response",
        "analysis_plan_id": "plan-export-response",
        "pass_run_id": "pass-run-export-response",
        "preview_id": "preview-export-response",
        "preview_hash": "hash-preview-export-response",
        "result_review_record_ref": "layer3://result-review/record",
        "package_review_preview_hash": "package-preview-hash-export",
        "reconciliation_record": _reconciliation(),
        "packages": _packages(),
        "readiness_state": _readiness_state(**readiness_overrides),
    }


def _without_server_time(response: dict) -> dict:
    return {key: value for key, value in response.items() if key != "server_time"}


def test_external_export_download_prepare_response_preserves_workbench_projection() -> None:
    kwargs = _response_kwargs()

    assert (
        layer3_workbench._external_export_download_prepare_response
        is export_response.external_export_download_prepare_response
    )

    response = export_response.external_export_download_prepare_response(**kwargs)
    workbench_response = layer3_workbench._external_export_download_prepare_response(**kwargs)

    assert _without_server_time(response) == _without_server_time(workbench_response)
    assert response["schema_id"] == export_response.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
    assert response["preview_identity"]["preview_id"] == "preview-export-response"
    assert response["output_package_ids"] == ["pkg-internal", "pkg-user", "pkg-review"]
    assert response["package_kinds"] == [
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    ]
    assert response["payload_refs"] == ["payload://pkg-internal", "payload://pkg-user", "payload://pkg-review"]
    assert response["payload_hashes"] == ["hash-internal", "hash-user", "hash-review"]
    assert response["browser_download_enabled"] is False
    assert response["download_url_enabled"] is False
    assert response["connector_dispatch_enabled"] is False
    assert response["destination_selection_enabled"] is False
    assert response["generic_downstream_dispatch_enabled"] is False
    assert response["downstream_unavailable"] == list(export_response.EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE)
    assert response["authority_rail"]["persistence_mode"] == "durable_external_export_download_prepare"


def test_external_export_download_prepare_response_preserves_cohort_delivery_ui_projection() -> None:
    source_ids = ["dataset-cohort-a", "dataset-cohort-b"]
    response = export_response.external_export_download_prepare_response(
        **_response_kwargs(
            pass_type=PASS_TYPE_ASSOCIATED_COHORT,
            pass_scope=PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
            method="descriptive_summary",
            source_gate=SOURCE_GATE_COHORT_DESC_FREEZE,
            package_construction_source_gate=SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
            source_shape=COHORT_SHAPE_ALIGNED_WIDE_TABLE,
            source_dataset_version_ids=source_ids,
            package_review_submit_schema_id="layer3.cohort_package_review_submit.v1",
            external_export_download_descriptor={"ref": "descriptor"},
        )
    )

    assert response["pass_type"] == PASS_TYPE_ASSOCIATED_COHORT
    assert response["source_dataset_version_ids"] == source_ids
    assert response["source_dataset_version_ids"] is not source_ids
    assert response["external_export_download_descriptor"] == {"ref": "descriptor"}
    assert response["delivery_ui"]["schema_id"] == export_response.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID
    assert response["delivery_ui"]["available"] is True
    assert response["delivery_ui"]["operator_decision"] == export_response.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION
    assert response["delivery_ui"]["public_url_enabled"] is False
    assert response["delivery_ui"]["signed_url_enabled"] is False
    assert response["delivery_ui"]["connector_dispatch_enabled"] is False
    assert response["delivery_ui"]["destination_selection_enabled"] is False
    assert response["delivery_ui"]["generic_downstream_dispatch_enabled"] is False
    assert response["delivery_ui"]["package_mutation_enabled"] is False
