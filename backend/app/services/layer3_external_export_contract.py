from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS = frozenset(
    {
        "download",
        "download_url",
        "download_token",
        "public_url",
        "signed_url",
        "local_file_path",
        "external_target",
        "destination",
        "destination_selector",
        "connector_run_id",
        "connector_dispatch",
        "generic_dispatch",
        "dispatch",
        "send",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
    }
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS = frozenset(
    {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "dispatch_mode",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "export_download_target",
        "download_mode",
        "operator_decision",
        "client_request_id",
        "decision_notes",
        "analysis_run_id",
        "aps_bundle_hash",
        "aps_bundle_size_bytes",
    }
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS = frozenset(
    {
        "download_url",
        "download_token",
        "public_url",
        "signed_url",
        "local_file_path",
        "external_target",
        "destination",
        "destination_selector",
        "destination_id",
        "connector_run_id",
        "connector_dispatch",
        "generic_dispatch",
        "dispatch",
        "send",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
        "handoff_export_amendment",
        "aps_handoff_amendment",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
    }
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS = EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS | frozenset(
    {
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "delivery_mode",
    }
)


@dataclass(frozen=True)
class ExternalExportDownloadDelivery:
    artifact_path: Path
    media_type: str
    filename: str
    headers: dict[str, str]
    authority: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalExportDownloadDeliveryRequestFields:
    request_id: str
    session_id: str
    reconciliation_record_id: str
    supplied_readiness_ref: str
    supplied_descriptor_ref: str
    supplied_readiness_state: str
    delivery_mode: str
    operator_decision: str
    export_download_target: str
    download_mode: str
    supplied_aps_bundle_ref: str
    supplied_aps_bundle_id: str
    supplied_aps_schema_id: str
    raw_output_package_ids: Any
    raw_package_kinds: Any
    raw_payload_refs: Any
    raw_payload_hashes: Any
    missing_fields: list[str]


def _payload_text(payload: Mapping[str, Any], field: str) -> str:
    return str(payload.get(field) or "").strip()


def external_export_download_delivery_request_fields(
    payload: Mapping[str, Any],
) -> ExternalExportDownloadDeliveryRequestFields:
    session_id = _payload_text(payload, "session_id")
    reconciliation_record_id = _payload_text(payload, "reconciliation_record_id")
    supplied_readiness_ref = _payload_text(payload, "external_export_download_record_ref")
    supplied_descriptor_ref = _payload_text(payload, "export_download_descriptor_ref")
    supplied_readiness_state = _payload_text(payload, "external_export_download_state")
    delivery_mode = _payload_text(payload, "delivery_mode")
    operator_decision = _payload_text(payload, "operator_decision")
    export_download_target = _payload_text(payload, "export_download_target")
    download_mode = _payload_text(payload, "download_mode")
    supplied_aps_bundle_ref = _payload_text(payload, "aps_bundle_ref")
    supplied_aps_bundle_id = _payload_text(payload, "aps_bundle_id")
    supplied_aps_schema_id = _payload_text(payload, "aps_schema_id")
    raw_output_package_ids = payload.get("output_package_ids")
    raw_package_kinds = payload.get("package_kinds")
    raw_payload_refs = payload.get("payload_refs")
    raw_payload_hashes = payload.get("payload_hashes")
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", _payload_text(payload, "analysis_plan_id")),
            ("pass_run_id", _payload_text(payload, "pass_run_id")),
            ("preview_id", _payload_text(payload, "preview_id")),
            ("preview_hash", _payload_text(payload, "preview_hash")),
            ("result_review_record_ref", _payload_text(payload, "result_review_record_ref")),
            ("package_review_preview_hash", _payload_text(payload, "package_review_preview_hash")),
            ("reconciliation_record_id", reconciliation_record_id),
            ("package_review_submit_record_ref", _payload_text(payload, "package_review_submit_record_ref")),
            ("package_review_state", _payload_text(payload, "package_review_state")),
            ("prepare_record_ref", _payload_text(payload, "prepare_record_ref")),
            ("handoff_export_state", _payload_text(payload, "handoff_export_state")),
            ("handoff_export_envelope_ref", _payload_text(payload, "handoff_export_envelope_ref")),
            ("handoff_target", _payload_text(payload, "handoff_target")),
            ("export_mode", _payload_text(payload, "export_mode")),
            ("aps_handoff_record_ref", _payload_text(payload, "aps_handoff_record_ref")),
            ("aps_handoff_state", _payload_text(payload, "aps_handoff_state")),
            ("aps_handoff_target", _payload_text(payload, "aps_handoff_target")),
            ("dispatch_mode", _payload_text(payload, "dispatch_mode")),
            ("aps_output_package_id", _payload_text(payload, "aps_output_package_id")),
            ("aps_output_package_kind", _payload_text(payload, "aps_output_package_kind")),
            ("aps_bundle_ref", supplied_aps_bundle_ref),
            ("aps_bundle_id", supplied_aps_bundle_id),
            ("aps_schema_id", supplied_aps_schema_id),
            ("external_export_download_record_ref", supplied_readiness_ref),
            ("export_download_descriptor_ref", supplied_descriptor_ref),
            ("external_export_download_state", supplied_readiness_state),
            ("export_download_target", export_download_target),
            ("download_mode", download_mode),
            ("delivery_mode", delivery_mode),
            ("operator_decision", operator_decision),
        )
        if not value
    ]
    if not raw_output_package_ids:
        missing.append("output_package_ids")
    if not raw_package_kinds:
        missing.append("package_kinds")
    if not raw_payload_refs:
        missing.append("payload_refs")
    if not raw_payload_hashes:
        missing.append("payload_hashes")
    return ExternalExportDownloadDeliveryRequestFields(
        request_id=_payload_text(payload, "client_request_id"),
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
        supplied_readiness_ref=supplied_readiness_ref,
        supplied_descriptor_ref=supplied_descriptor_ref,
        supplied_readiness_state=supplied_readiness_state,
        delivery_mode=delivery_mode,
        operator_decision=operator_decision,
        export_download_target=export_download_target,
        download_mode=download_mode,
        supplied_aps_bundle_ref=supplied_aps_bundle_ref,
        supplied_aps_bundle_id=supplied_aps_bundle_id,
        supplied_aps_schema_id=supplied_aps_schema_id,
        raw_output_package_ids=raw_output_package_ids,
        raw_package_kinds=raw_package_kinds,
        raw_payload_refs=raw_payload_refs,
        raw_payload_hashes=raw_payload_hashes,
        missing_fields=missing,
    )


def external_export_download_delivery_readiness_mismatches(
    request_fields: ExternalExportDownloadDeliveryRequestFields,
    readiness_state: Mapping[str, Any],
) -> list[tuple[str, str, Any]]:
    comparisons = (
        (
            "external_export_download_record_ref",
            request_fields.supplied_readiness_ref,
            readiness_state.get("external_export_download_record_ref"),
        ),
        (
            "export_download_descriptor_ref",
            request_fields.supplied_descriptor_ref,
            readiness_state.get("export_download_descriptor_ref"),
        ),
        ("aps_bundle_ref", request_fields.supplied_aps_bundle_ref, readiness_state.get("aps_bundle_ref")),
        ("aps_bundle_id", request_fields.supplied_aps_bundle_id, readiness_state.get("aps_bundle_id")),
        ("aps_schema_id", request_fields.supplied_aps_schema_id, readiness_state.get("aps_schema_id")),
    )
    return [
        (field, supplied, expected)
        for field, supplied, expected in comparisons
        if str(supplied or "") != str(expected or "")
    ]


def external_export_download_prepare_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(
        key for key in payload if key not in EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS if key in payload
    )
    return sorted(set(unknown) | set(forbidden))


def external_export_download_delivery_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    unknown = sorted(
        key for key in payload if key not in EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS if key in payload
    )
    return sorted(set(unknown) | set(forbidden))
