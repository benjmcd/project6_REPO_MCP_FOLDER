from __future__ import annotations

from pathlib import Path

from app.services import layer3_external_export_contract as contract
from app.services import layer3_workbench


def test_external_export_download_contract_is_shared_without_behavior_change() -> None:
    assert (
        layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS
        is contract.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS
        is contract.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS
    )
    assert (
        layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS
        is contract.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS
        is contract.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS
    )

    assert layer3_workbench.ExternalExportDownloadDelivery is contract.ExternalExportDownloadDelivery
    assert (
        layer3_workbench.external_export_download_delivery_request_fields
        is contract.external_export_download_delivery_request_fields
    )
    delivery = contract.ExternalExportDownloadDelivery(
        artifact_path=Path("bundle.json"),
        media_type="application/json",
        filename="bundle.json",
        headers={"X-Layer3-Schema-Id": "layer3.external_export_download_delivery.v1"},
    )
    assert delivery.authority == {}


def test_external_export_download_contract_blocks_same_fields_as_legacy_logic() -> None:
    prepare_payload = {
        "session_id": "session-1",
        "download_url": "https://example.invalid/bundle.json",
        "unexpected_field": True,
    }
    legacy_prepare_blocked = sorted(
        set(
            key
            for key in prepare_payload
            if key not in contract.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS
        )
        | set(
            key
            for key in contract.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS
            if key in prepare_payload
        )
    )
    assert contract.external_export_download_prepare_blocked_fields(prepare_payload) == legacy_prepare_blocked

    delivery_payload = {
        "session_id": "session-1",
        "external_export_download_record_ref": "external-export-download:ready",
        "download_url": "https://example.invalid/bundle.json",
        "destination_id": "external-destination",
        "unexpected_field": True,
    }
    legacy_delivery_blocked = sorted(
        set(
            key
            for key in delivery_payload
            if key not in contract.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS
        )
        | set(
            key
            for key in contract.EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS
            if key in delivery_payload
        )
    )
    assert contract.external_export_download_delivery_blocked_fields(delivery_payload) == legacy_delivery_blocked


def test_external_export_download_delivery_request_fields_match_legacy_missing_order() -> None:
    payload = {
        "client_request_id": " delivery-request ",
        "session_id": " session-1 ",
        "analysis_plan_id": "plan-1",
        "pass_run_id": "pass-run-1",
        "preview_id": "preview-1",
        "preview_hash": "preview-hash",
        "result_review_record_ref": "result-review-ref",
        "package_review_preview_hash": "package-review-preview-hash",
        "reconciliation_record_id": " reconciliation-1 ",
        "package_review_submit_record_ref": "package-review-submit-ref",
        "package_review_state": "package_review_approved",
        "prepare_record_ref": "prepare-ref",
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": "handoff-envelope-ref",
        "handoff_target": "aps_evidence_bundle_handoff",
        "export_mode": "reference_envelope_prepare_only",
        "aps_handoff_record_ref": "aps-handoff-ref",
        "aps_handoff_state": "aps_handoff_dispatched",
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "aps_evidence_bundle_only",
        "aps_output_package_id": "aps-output-package",
        "aps_output_package_kind": "aps_evidence_bundle_handoff",
        "aps_bundle_ref": " aps-bundle-ref ",
        "aps_bundle_id": " aps-bundle-id ",
        "aps_schema_id": " aps.schema.v1 ",
        "external_export_download_record_ref": " readiness-ref ",
        "export_download_descriptor_ref": " descriptor-ref ",
        "external_export_download_state": "external_export_download_prepared",
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "delivery_mode": "same_origin_artifact_stream",
        "operator_decision": "deliver_external_export_download",
        "output_package_ids": ["pkg-user", "pkg-internal", "pkg-review"],
        "package_kinds": ["user_facing", "canonical_internal", "review_facing"],
        "payload_refs": ["payload://user", "payload://internal", "payload://review"],
        "payload_hashes": ["hash-user", "hash-internal", "hash-review"],
    }

    parsed = contract.external_export_download_delivery_request_fields(payload)

    assert isinstance(parsed, contract.ExternalExportDownloadDeliveryRequestFields)
    assert parsed.request_id == "delivery-request"
    assert parsed.session_id == "session-1"
    assert parsed.reconciliation_record_id == "reconciliation-1"
    assert parsed.supplied_readiness_ref == "readiness-ref"
    assert parsed.supplied_descriptor_ref == "descriptor-ref"
    assert parsed.supplied_aps_bundle_ref == "aps-bundle-ref"
    assert parsed.supplied_aps_bundle_id == "aps-bundle-id"
    assert parsed.supplied_aps_schema_id == "aps.schema.v1"
    assert parsed.raw_output_package_ids is payload["output_package_ids"]
    assert parsed.raw_package_kinds is payload["package_kinds"]
    assert parsed.raw_payload_refs is payload["payload_refs"]
    assert parsed.raw_payload_hashes is payload["payload_hashes"]
    assert parsed.missing_fields == []

    partial = {
        "client_request_id": "delivery-request",
        "session_id": "session-1",
        "reconciliation_record_id": "reconciliation-1",
        "external_export_download_record_ref": "readiness-ref",
        "download_mode": "reference_only_prepare",
        "delivery_mode": "same_origin_artifact_stream",
        "operator_decision": "deliver_external_export_download",
        "output_package_ids": [],
        "package_kinds": ["user_facing"],
    }
    legacy_missing = [
        field
        for field, value in (
            ("session_id", "session-1"),
            ("analysis_plan_id", ""),
            ("pass_run_id", ""),
            ("preview_id", ""),
            ("preview_hash", ""),
            ("result_review_record_ref", ""),
            ("package_review_preview_hash", ""),
            ("reconciliation_record_id", "reconciliation-1"),
            ("package_review_submit_record_ref", ""),
            ("package_review_state", ""),
            ("prepare_record_ref", ""),
            ("handoff_export_state", ""),
            ("handoff_export_envelope_ref", ""),
            ("handoff_target", ""),
            ("export_mode", ""),
            ("aps_handoff_record_ref", ""),
            ("aps_handoff_state", ""),
            ("aps_handoff_target", ""),
            ("dispatch_mode", ""),
            ("aps_output_package_id", ""),
            ("aps_output_package_kind", ""),
            ("aps_bundle_ref", ""),
            ("aps_bundle_id", ""),
            ("aps_schema_id", ""),
            ("external_export_download_record_ref", "readiness-ref"),
            ("export_download_descriptor_ref", ""),
            ("external_export_download_state", ""),
            ("export_download_target", ""),
            ("download_mode", "reference_only_prepare"),
            ("delivery_mode", "same_origin_artifact_stream"),
            ("operator_decision", "deliver_external_export_download"),
        )
        if not value
    ]
    legacy_missing.extend(["output_package_ids", "payload_refs", "payload_hashes"])
    assert contract.external_export_download_delivery_request_fields(partial).missing_fields == legacy_missing
