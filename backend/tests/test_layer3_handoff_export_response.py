from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services import layer3_handoff_export_response as handoff_response
from app.services import layer3_workbench
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
    SOURCE_WORKBENCH_PACKAGE_CONSTRUCTION_FREEZE,
    SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
)
from app.services.layer3_package_submit_response import (
    COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
    QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
)
from app.services.layer3_workbench_package_state import HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE


def _package(package_kind: str, output_package_id: str, *, payload_hash: str) -> L3OutputPackage:
    return L3OutputPackage(
        package_kind=package_kind,
        output_package_id=output_package_id,
        payload_hash=payload_hash,
        payload_ref=f"payload://{output_package_id}",
    )


def _reconciliation() -> L3ReconciliationRecord:
    return L3ReconciliationRecord(reconciliation_record_id="reconciliation-handoff-response")


def _prepare_state(**overrides) -> dict:
    state = {
        "package_review_submit_record_ref": "layer3://package-review-submit/session/record",
        "package_review_state": "package_review_approved",
        "operator_decision": "authorize_prepare",
        "decision_notes": "Prepare the internal export envelope.",
        "handoff_export_state": "handoff_export_prepared",
        "prepare_record_ref": "layer3://handoff-export-prepare/session/record",
        "handoff_export_envelope": {
            "schema_id": "layer3.handoff_export_envelope.v1",
            "envelope_ref": "layer3://handoff-export-envelope/session/envelope",
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
        },
        "pass_type": "single_item",
        "pass_scope": "quant_single_item",
        "method": "descriptive_summary",
        "source_gate": "source-gate-handoff-response",
        "package_construction_source_gate": SOURCE_WORKBENCH_PACKAGE_CONSTRUCTION_FREEZE,
        "source_shape": "single_item",
        "source_dataset_version_ids": ["dataset-handoff-response"],
    }
    state.update(overrides)
    return state


def _packages() -> list[L3OutputPackage]:
    return [
        _package(PACKAGE_KIND_USER_FACING, "pkg-user", payload_hash="hash-user"),
        _package(PACKAGE_KIND_CANONICAL_INTERNAL, "pkg-internal", payload_hash="hash-internal"),
        _package(PACKAGE_KIND_REVIEW_FACING, "pkg-review", payload_hash="hash-review"),
    ]


def _kwargs(**state_overrides) -> dict:
    return {
        "request_id": "request-handoff-response",
        "status": "prepared",
        "session_id": "session-handoff-response",
        "analysis_plan_id": "plan-handoff-response",
        "pass_run_id": "pass-run-handoff-response",
        "preview_id": "preview-handoff-response",
        "preview_hash": "hash-handoff-response",
        "analysis_run_id": "analysis-run-handoff-response",
        "result_review_record_ref": "layer3://result-review/session/record",
        "package_review_preview_hash": "package-preview-hash-handoff",
        "reconciliation_record": _reconciliation(),
        "packages": _packages(),
        "prepare_state": _prepare_state(**state_overrides),
    }


def _without_server_time(response: dict) -> dict:
    return {key: value for key, value in response.items() if key != "server_time"}


def test_handoff_export_prepare_response_preserves_workbench_projection() -> None:
    kwargs = _kwargs()

    assert layer3_workbench._handoff_export_prepare_response is handoff_response.handoff_export_prepare_response

    response = handoff_response.handoff_export_prepare_response(**kwargs)
    workbench_response = layer3_workbench._handoff_export_prepare_response(**kwargs)

    assert _without_server_time(response) == _without_server_time(workbench_response)
    assert response["schema_id"] == handoff_response.HANDOFF_EXPORT_PREPARE_SCHEMA_ID
    assert response["status"] == "prepared"
    assert response["request_id"] == "request-handoff-response"
    assert response["preview_identity"]["preview_hash"] == "hash-handoff-response"
    assert response["output_package_ids"] == ["pkg-internal", "pkg-user", "pkg-review"]
    assert response["package_kinds"] == [
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    ]
    assert response["payload_refs"] == ["payload://pkg-internal", "payload://pkg-user", "payload://pkg-review"]
    assert response["payload_hashes"] == ["hash-internal", "hash-user", "hash-review"]
    assert response["handoff_target"] == "internal_export_envelope"
    assert response["export_mode"] == "prepare_only"
    assert response["external_handoff_enabled"] is False
    assert response["external_export_enabled"] is False
    assert response["dispatch_enabled"] is False
    assert response["downstream_unavailable"] == list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE)
    assert response["authority_rail"]["persistence_mode"] == "durable_handoff_export_prepare"
    assert response["authority_rail"]["downstream_unavailable"] == list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE)
    assert response["handoff_export_envelope"]["dispatch_enabled"] is False


def test_handoff_export_prepare_response_preserves_cohort_schema_and_provenance() -> None:
    response = handoff_response.handoff_export_prepare_response(
        **_kwargs(
            package_construction_source_gate=SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
            pass_type="associated_cohort",
            pass_scope="quant_associated_cohort",
            source_shape="aligned_wide_table",
            source_dataset_version_ids=["dataset-cohort-a", "dataset-cohort-b"],
            package_review_submit_schema_id=COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
        )
    )

    assert response["schema_id"] == handoff_response.COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID
    assert response["package_review_submit_schema_id"] == COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    assert response["pass_type"] == "associated_cohort"
    assert response["pass_scope"] == "quant_associated_cohort"
    assert response["source_shape"] == "aligned_wide_table"
    assert response["source_dataset_version_ids"] == ["dataset-cohort-a", "dataset-cohort-b"]
    assert response["external_handoff_enabled"] is False
    assert response["external_export_enabled"] is False
    assert response["dispatch_enabled"] is False


def test_handoff_export_prepare_response_preserves_qualitative_aps_schema_and_disabled_downstream() -> None:
    response = handoff_response.handoff_export_prepare_response(
        **_kwargs(
            package_construction_source_gate=SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
            construction_basis_hash="construction-basis-qual-aps",
            pass_type="single_item",
            pass_scope="single_aps_doc_qualitative_pass",
            method="single_aps_doc_qualitative_pass",
            source_gate="qual_aps_doc_output_freeze",
            source_shape="aps_content_document",
            source_dataset_version_ids=[],
            package_review_submit_schema_id=QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
        )
    )

    assert response["schema_id"] == handoff_response.QUAL_APS_HANDOFF_EXPORT_PREPARE_SCHEMA_ID
    assert response["package_review_submit_schema_id"] == QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    assert response["construction_basis_hash"] == "construction-basis-qual-aps"
    assert response["pass_type"] == "single_item"
    assert response["source_shape"] == "aps_content_document"
    assert response["source_dataset_version_ids"] == []
    assert response["aps_handoff_enabled"] is False
    assert response["external_export_download_enabled"] is False
    assert response["connector_dispatch_enabled"] is False
    assert response["provider_public_url_enabled"] is False
