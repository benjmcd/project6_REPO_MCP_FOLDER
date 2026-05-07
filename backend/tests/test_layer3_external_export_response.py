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
from app.services.layer3_package_submit_response import COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
from app.services.layer3_pass_entry import (
    COHORT_SHAPE_ALIGNED_WIDE_TABLE,
    PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
    PASS_TYPE_ASSOCIATED_COHORT,
    SOURCE_GATE_COHORT_DESC_FREEZE,
)
from app.services.layer3_workbench_package_state import APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID


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


def test_external_export_delivery_helpers_are_shared_with_workbench() -> None:
    assert layer3_workbench._safe_download_token is export_response.safe_download_token
    assert (
        layer3_workbench._external_export_download_prepare_payload_for_delivery
        is export_response.external_export_download_prepare_payload_for_delivery
    )

    assert export_response.safe_download_token(" session:bad/name.. ", fallback="fallback") == "session-bad-name"
    assert export_response.safe_download_token("...", fallback="fallback") == "fallback"
    assert len(export_response.safe_download_token("x" * 120, fallback="fallback")) == 96

    payload = {
        "client_request_id": "delivery-request",
        "session_id": "session-export-response",
        "operator_decision": "deliver_external_export_download",
        "decision_notes": "operator delivery note must not override readiness",
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "delivery_mode": "same_origin_artifact_stream",
        "public_url": "not-admitted",
    }
    readiness_state = {
        "client_request_id": "readiness-request",
        "decision_notes": "readiness note",
    }

    prepare_payload = export_response.external_export_download_prepare_payload_for_delivery(
        payload,
        readiness_state=readiness_state,
    )

    assert prepare_payload["client_request_id"] == "readiness-request"
    assert prepare_payload["operator_decision"] == "prepare_external_export_download"
    assert prepare_payload["decision_notes"] == "readiness note"
    assert prepare_payload["session_id"] == "session-export-response"
    assert prepare_payload["export_download_target"] == "aps_evidence_bundle_download_reference"
    assert prepare_payload["download_mode"] == "reference_only_prepare"
    assert "delivery_mode" not in prepare_payload
    assert "public_url" not in prepare_payload


class _PackageQuery:
    def __init__(self, package: L3OutputPackage | None) -> None:
        self.package = package

    def filter(self, *args, **kwargs):
        return self

    def one_or_none(self) -> L3OutputPackage | None:
        return self.package


class _PackageDb:
    def __init__(
        self,
        package: L3OutputPackage | None = None,
        *,
        reconciliation: L3ReconciliationRecord | None = None,
    ) -> None:
        self.package = package
        self.reconciliation = reconciliation

    def query(self, model):
        if model is L3ReconciliationRecord:
            return _PackageQuery(self.reconciliation)
        assert model is L3OutputPackage
        return _PackageQuery(self.package)


def test_external_export_bundle_identity_helper_is_shared_with_workbench() -> None:
    assert (
        layer3_workbench._aps_bundle_identity_for_external_export_download
        is export_response.aps_bundle_identity_for_external_export_download
    )

    package = L3OutputPackage(
        session_id="session-export-response",
        reconciliation_record_id="reconciliation-export-response",
        output_package_id="aps-output-package",
        package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        payload_ref="layer3://aps-bundle/ref",
        payload_hash="source-artifact-hash",
        summary_json={
            "bundle_id": "aps-bundle-id",
            "aps_schema_id": "layer3.aps_evidence_bundle.v1",
        },
    )
    dispatch_state = {
        "aps_handoff_state": export_response.APS_HANDOFF_DISPATCHED_STATE,
        "aps_output_package_id": "aps-output-package",
        "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        "aps_bundle_ref": "layer3://aps-bundle/ref",
        "aps_bundle_id": "aps-bundle-id",
        "aps_schema_id": "layer3.aps_evidence_bundle.v1",
    }

    identity = export_response.aps_bundle_identity_for_external_export_download(
        _PackageDb(package),
        session_id="session-export-response",
        reconciliation_record_id="reconciliation-export-response",
        dispatch_state=dispatch_state,
        error_prefix="external_export_download_test",
        existing_readiness={
            "source_artifact_hash": "source-artifact-hash",
            "source_artifact_size_bytes": 42,
        },
        validate_source_artifact=False,
    )

    assert identity == {
        "aps_output_package_id": "aps-output-package",
        "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        "aps_bundle_ref": "layer3://aps-bundle/ref",
        "aps_bundle_id": "aps-bundle-id",
        "aps_schema_id": "layer3.aps_evidence_bundle.v1",
        "source_artifact_ref": "layer3://aps-bundle/ref",
        "source_artifact_schema_id": "layer3.aps_evidence_bundle.v1",
        "source_artifact_hash": "source-artifact-hash",
        "source_artifact_size_bytes": 42,
    }


def test_external_export_summary_helper_is_shared_with_workbench(monkeypatch) -> None:
    assert (
        layer3_workbench._external_export_download_prepare_summary
        is export_response.external_export_download_prepare_summary
    )

    dispatch_state = {
        "schema_id": APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
        "state": export_response.APS_HANDOFF_DISPATCHED_STATE,
        "analysis_run_id": "analysis-run-export-response",
        "result_review_record_ref": "layer3://result-review/record",
        "package_review_preview_hash": "package-preview-hash-export",
        "reconciliation_record_id": "reconciliation-export-response",
        "output_package_ids": ["pkg-user", "pkg-internal", "pkg-review"],
        "package_kinds": ["user_facing", "canonical_internal", "review_facing"],
        "payload_refs": ["payload://user", "payload://internal", "payload://review"],
        "payload_hashes": ["hash-user", "hash-internal", "hash-review"],
        "package_review_submit_record_ref": "layer3://package-review-submit/record",
        "package_review_state": "package_review_approved",
        "prepare_record_ref": "layer3://handoff-export/prepare/record",
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": "layer3://handoff-export/envelope",
        "handoff_target": "aps_evidence_bundle_handoff",
        "export_mode": "reference_envelope_prepare_only",
        "aps_handoff_record_ref": "layer3://aps-handoff/record",
        "aps_handoff_state": export_response.APS_HANDOFF_DISPATCHED_STATE,
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "pass_type": PASS_TYPE_ASSOCIATED_COHORT,
        "pass_scope": PASS_SCOPE_QUANT_ASSOCIATED_COHORT,
        "method": "descriptive_summary",
        "source_gate": SOURCE_GATE_COHORT_DESC_FREEZE,
        "package_construction_source_gate": SOURCE_WORKBENCH_COHORT_PACKAGE_CONSTRUCTION_FREEZE,
        "source_shape": COHORT_SHAPE_ALIGNED_WIDE_TABLE,
        "source_dataset_version_ids": ["dataset-version-1"],
        "package_review_submit_schema_id": COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
    }
    reconciliation = L3ReconciliationRecord(
        session_id="session-export-response",
        reconciliation_record_id="reconciliation-export-response",
        summary_json={"aps_handoff_dispatch": dispatch_state},
    )

    def fake_bundle_identity(*args, **kwargs):
        return {
            "aps_output_package_id": "aps-output-package",
            "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            "aps_bundle_ref": "layer3://aps-bundle/ref",
            "aps_bundle_id": "aps-bundle-id",
            "aps_schema_id": "layer3.aps_evidence_bundle.v1",
            "source_artifact_ref": "layer3://aps-bundle/ref",
            "source_artifact_schema_id": "layer3.aps_evidence_bundle.v1",
            "source_artifact_hash": "source-artifact-hash",
            "source_artifact_size_bytes": 42,
        }

    monkeypatch.setattr(export_response, "aps_bundle_identity_for_external_export_download", fake_bundle_identity)

    summary = export_response.external_export_download_prepare_summary(
        _PackageDb(reconciliation=reconciliation),
        session_id="session-export-response",
        aps_handoff_dispatch_state=dispatch_state,
    )

    assert summary["schema_id"] == export_response.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID
    assert summary["available"] is True
    assert summary["state"] == "external_export_download_ready"
    assert summary["operator_decision"] == "prepare_external_export_download"
    assert summary["aps_output_package_id"] == "aps-output-package"
    assert summary["source_artifact_hash"] == "source-artifact-hash"
    assert summary["external_export_download_prepare_enabled"] is True
    assert summary["browser_download_enabled"] is False
    assert summary["download_url_enabled"] is False
    assert summary["connector_dispatch_enabled"] is False
    assert summary["destination_selection_enabled"] is False
    assert summary["generic_downstream_dispatch_enabled"] is False
    assert summary["pass_type"] == PASS_TYPE_ASSOCIATED_COHORT
    assert summary["source_dataset_version_ids"] == ["dataset-version-1"]
