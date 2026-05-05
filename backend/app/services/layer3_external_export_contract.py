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
