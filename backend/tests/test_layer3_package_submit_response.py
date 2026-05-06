from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3OutputPackage, L3ReconciliationRecord
from app.services import layer3_package_submit_response as submit_response
from app.services import layer3_workbench
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
)
from app.services.layer3_workbench_package_state import (
    COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE,
    HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE,
)


def _package(package_kind: str, output_package_id: str, *, payload_hash: str) -> L3OutputPackage:
    return L3OutputPackage(
        package_kind=package_kind,
        output_package_id=output_package_id,
        payload_hash=payload_hash,
        payload_ref=f"payload://{output_package_id}",
    )


def _reconciliation() -> L3ReconciliationRecord:
    return L3ReconciliationRecord(reconciliation_record_id="reconciliation-submit-response")


def _review_state(**overrides) -> dict:
    state = {
        "operator_decision": "approved",
        "decision_notes": "Ready for handoff.",
        "package_review_state": "package_review_approved",
        "submit_record_ref": "layer3://package-review-submit/session/record",
        "pass_type": "single_item",
        "pass_scope": "quant_single_item",
        "method": "descriptive_summary",
        "source_gate": "source-gate-submit-response",
        "package_construction_source_gate": "workbench_package_construction_freeze",
        "source_shape": "single_item",
        "source_dataset_version_ids": ["dataset-submit-response"],
    }
    state.update(overrides)
    return state


def _without_server_time(response: dict) -> dict:
    return {key: value for key, value in response.items() if key != "server_time"}


def test_package_review_submit_response_preserves_workbench_projection() -> None:
    packages = [
        _package(PACKAGE_KIND_USER_FACING, "pkg-user", payload_hash="hash-user"),
        _package(PACKAGE_KIND_CANONICAL_INTERNAL, "pkg-internal", payload_hash="hash-internal"),
        _package(PACKAGE_KIND_REVIEW_FACING, "pkg-review", payload_hash="hash-review"),
    ]
    kwargs = {
        "request_id": "request-submit-response",
        "status": "recorded",
        "session_id": "session-submit-response",
        "analysis_plan_id": "plan-submit-response",
        "pass_run_id": "pass-run-submit-response",
        "preview_id": "preview-submit-response",
        "preview_hash": "hash-submit-response",
        "analysis_run_id": "analysis-run-submit-response",
        "result_review_record_ref": "layer3://result-review/record",
        "package_review_preview_hash": "package-preview-hash-submit",
        "reconciliation_record": _reconciliation(),
        "packages": packages,
        "review_state": _review_state(),
    }

    assert layer3_workbench._package_review_submit_response is submit_response.package_review_submit_response

    response = submit_response.package_review_submit_response(**kwargs)
    workbench_response = layer3_workbench._package_review_submit_response(**kwargs)

    assert _without_server_time(response) == _without_server_time(workbench_response)
    assert response["schema_id"] == submit_response.PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    assert response["status"] == "recorded"
    assert response["request_id"] == "request-submit-response"
    assert response["preview_identity"]["preview_id"] == "preview-submit-response"
    assert response["output_package_ids"] == ["pkg-internal", "pkg-user", "pkg-review"]
    assert response["package_kinds"] == [
        PACKAGE_KIND_CANONICAL_INTERNAL,
        PACKAGE_KIND_USER_FACING,
        PACKAGE_KIND_REVIEW_FACING,
    ]
    assert response["payload_hashes"] == ["hash-internal", "hash-user", "hash-review"]
    assert response["package_review_submit_enabled"] is False
    assert response["handoff_enabled"] is False
    assert response["export_enabled"] is False
    assert response["downstream_unavailable"] == list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE)
    assert response["next_state"] == "package_review_approved"
    assert response["authority_rail"]["persistence_mode"] == "durable_package_review_submit"
    assert response["authority_rail"]["downstream_unavailable"] == list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE)


def test_package_review_submit_response_preserves_cohort_schema_and_blocks_export() -> None:
    response = submit_response.package_review_submit_response(
        request_id="request-submit-cohort",
        status="recorded",
        session_id="session-submit-response",
        analysis_plan_id="plan-submit-response",
        pass_run_id="pass-run-submit-response",
        preview_id="preview-submit-response",
        preview_hash="hash-submit-response",
        analysis_run_id=None,
        result_review_record_ref="layer3://result-review/record",
        package_review_preview_hash="package-preview-hash-submit",
        reconciliation_record=_reconciliation(),
        packages=[
            _package(PACKAGE_KIND_CANONICAL_INTERNAL, "pkg-internal", payload_hash="hash-internal"),
            _package(PACKAGE_KIND_USER_FACING, "pkg-user", payload_hash="hash-user"),
            _package(PACKAGE_KIND_REVIEW_FACING, "pkg-review", payload_hash="hash-review"),
        ],
        review_state=_review_state(
            package_construction_source_gate=SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
            pass_type="associated_cohort",
            pass_scope="quant_associated_cohort",
            source_shape="aligned_wide_table",
            source_dataset_version_ids=["dataset-cohort-a", "dataset-cohort-b"],
        ),
    )

    assert response["schema_id"] == submit_response.COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    assert response["downstream_unavailable"] == list(COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE)
    assert response["authority_rail"]["downstream_unavailable"] == list(
        COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
    )
    assert response["source_dataset_version_ids"] == ["dataset-cohort-a", "dataset-cohort-b"]
    assert response["analysis_run_id"] is None
