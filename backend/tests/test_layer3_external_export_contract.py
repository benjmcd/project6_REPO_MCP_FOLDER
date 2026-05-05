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
