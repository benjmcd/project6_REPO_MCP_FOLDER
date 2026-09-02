"""Shared helpers and schema constants for app.api.layer3.

This module MUST NOT import from app.api.layer3 (the package __init__) to
avoid a circular-import cycle.  Everything here depends only on stdlib,
third-party libraries, app.services.*, and app.core.*.
"""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import parse_qsl

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services import (
    layer3_candidate_b_operator_workflow_access_policy,
    layer3_corrected_package_artifact_set,
    layer3_external_local_export,
    layer3_internal_webhook_connector,
    layer3_local_outbox_provider_private_handoff,
    layer3_package_supersession_commit,
    layer3_raw_mixed_bridge,
    layer3_raw_mixed_materialization,
    layer3_replacement_package_artifact_manifest,
    layer3_replacement_package_namespace,
    layer3_replacement_package_set_authority,
    layer3_sec_xbrl_auth_binding,
    layer3_sec_xbrl_controlled_value_reveal_submit,
    layer3_sec_xbrl_e2e_integration,
    layer3_sec_xbrl_e2e_offline_orchestrator,
    layer3_sec_xbrl_full_pipeline_orchestrator,
    layer3_sec_xbrl_in_app_auth_policy,
    layer3_sec_xbrl_offline_evidence_loader,
    layer3_sec_xbrl_operator_review_workflow,
    layer3_sec_xbrl_projection_persistence,
    layer3_sec_xbrl_statement_packet_persistence,
    layer3_sec_xbrl_value_reveal_authority,
)
from app.services.layer3_preflight_request_contract import PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS
from app.services.layer3_sec_xbrl_offline_companyfacts_stage import SecXbrlCompanyfactsStageError
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response

__all__ = [
    # helpers
    "_string_array_or_string_map_schema",
    "_forbidden_request_field_schema",
    "_json_request_body",
    "_json_or_error",
    "_companyfacts_stage_error_response",
    "_json_or_error_with_companyfacts_stage",
    "_sec_xbrl_operator_review_workflow_error_response",
    "_sec_xbrl_staged_evidence_loader_error_response",
    "_sec_xbrl_staged_evidence_orchestrator_error_response",
    "_sec_xbrl_staged_evidence_persistence_error_response",
    "_sec_xbrl_full_pipeline_orchestrator_error_response",
    "_sec_xbrl_value_reveal_authority_error_response",
    "_sec_xbrl_controlled_value_reveal_submit_error_response",
    "_sec_xbrl_auth_policy_error_response",
    "_route_level_operator_identity",
    "_sec_xbrl_policy_request_fields",
    "_sec_xbrl_policy_decision",
    "_sec_xbrl_binding_request_id",
    "_sec_xbrl_require_binding",
    "_sec_xbrl_record_binding",
    "_sec_xbrl_commit_bound_receipts",
    "_sec_xbrl_auth_binding_projection",
    "_candidate_b_policy_request_context",
    "_candidate_b_policy_json_or_error",
    "_payload_from_request",
    "_FULL_PIPELINE_FORBIDDEN_MARKERS",
    "_full_pipeline_contains_forbidden_marker",
    "SecXbrlInAppAuthPolicyError",
    # schema constants
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA",
    "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA",
    "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ROUTE_JSON_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ROUTE_FORM_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_BODY",
    "ASSOCIATED_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA",
    "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_REQUEST_SCHEMA",
    "PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_REQUEST_FIELDS",
    "PROVIDER_PRIVATE_SIGNED_URL_PREPARE_REQUEST_SCHEMA",
    "PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUEST_SCHEMA",
    "PROVIDER_PUBLIC_URL_FORBIDDEN_REQUEST_FIELDS",
    "PROVIDER_PUBLIC_URL_PREPARE_REQUEST_SCHEMA",
    "PROVIDER_PUBLIC_URL_REVOKE_REQUEST_SCHEMA",
    "PROVIDER_PUBLIC_URL_DELIVERY_USE_REQUEST_SCHEMA",
    "SOURCE_CLASS_SCHEMA",
    "PREFLIGHT_REQUEST_SCHEMA",
    "SOURCE_PREVIEW_REQUEST_SCHEMA",
    "MATERIAL_PREVIEW_REQUEST_SCHEMA",
    "RAW_MIXED_CORPUS_SEED_REQUEST_SCHEMA",
    "RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA",
    "GATE_B_DECISION_ITEM_SCHEMA",
    "GATE_B_DECISION_REQUEST_SCHEMA",
    "GATE_C_PREVIEW_REQUEST_SCHEMA",
    "PLAN_PREVIEW_REQUEST_SCHEMA",
    "PLAN_APPROVAL_REQUEST_SCHEMA",
    "APPROVED_PLAN_CANCEL_REQUEST_SCHEMA",
    "PLAN_REVISION_REQUEST_SCHEMA",
    "PLAN_REVISION_RECOVERY_REQUEST_SCHEMA",
    "EXECUTION_SELECTION_REQUEST_SCHEMA",
    "ANALYSIS_EXECUTION_START_REQUEST_SCHEMA",
    "EXECUTION_RESULT_STATUS_REQUEST_SCHEMA",
    "EXECUTION_RESULT_REVIEW_REQUEST_SCHEMA",
    "PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA",
    "PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA",
    "PACKAGE_REVIEW_SUBMIT_REQUEST_SCHEMA",
    "PACKAGE_SUPERSESSION_PREVIEW_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA",
    "PACKAGE_SUPERSESSION_COMMIT_REQUEST_SCHEMA",
    "PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA",
    "CORRECTED_PACKAGE_ARTIFACT_SET_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_NAMESPACE_RECORD_REQUEST_SCHEMA",
    "REPLACEMENT_PACKAGE_NAMESPACE_FROM_CORRECTED_MANIFEST_REQUEST_SCHEMA",
    "PACKAGE_REPLACEMENT_ACTIVATION_COMMIT_REQUEST_SCHEMA",
    "HANDOFF_EXPORT_PREPARE_REQUEST_SCHEMA",
    "APS_HANDOFF_DISPATCH_REQUEST_SCHEMA",
    "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_REQUEST_SCHEMA",
    "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUEST_SCHEMA",
    "CONNECTOR_DATASET_HANDOFF_REQUEST_SCHEMA",
    "CONNECTOR_DISPATCH_RECORD_REQUEST_SCHEMA",
    "CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUEST_SCHEMA",
    "SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_REQUEST_SCHEMA",
    "SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUEST_SCHEMA",
    "LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_FORBIDDEN_REQUEST_FIELDS",
    "LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_PREPARE_REQUEST_SCHEMA",
    "EXTERNAL_LOCAL_EXPORT_FORBIDDEN_REQUEST_FIELDS",
    "EXTERNAL_LOCAL_EXPORT_WRITE_REQUEST_SCHEMA",
    "INTERNAL_WEBHOOK_DISPATCH_FORBIDDEN_REQUEST_FIELDS",
    "INTERNAL_WEBHOOK_DISPATCH_REQUEST_SCHEMA",
]

# ---------------------------------------------------------------------------
# Pure schema-building helpers
# ---------------------------------------------------------------------------

def _string_array_or_string_map_schema(description: str) -> dict[str, Any]:
    return {
        "oneOf": [
            {"type": "array", "items": {"type": "string"}},
            {"type": "object", "additionalProperties": {"type": "string"}},
        ],
        "description": description,
    }


def _forbidden_request_field_schema() -> dict[str, Any]:
    return {
        "not": {},
        "description": "Known but non-admitted; service rejects fail-closed.",
    }


EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "material_preview_id",
        "material_preview_hash",
        "contract_hash",
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
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "export_download_target",
        "download_mode",
        "delivery_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "package_kinds": {"type": "array", "items": {"type": "string"}},
        "payload_refs": _string_array_or_string_map_schema(
            "List of payload refs or a mapping keyed by package kind or package id."
        ),
        "payload_hashes": _string_array_or_string_map_schema(
            "List of payload hashes or a mapping keyed by package kind or package id."
        ),
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string"},
        "prepare_record_ref": {"type": "string"},
        "handoff_export_state": {"type": "string"},
        "handoff_export_envelope_ref": {"type": "string"},
        "handoff_target": {"type": "string"},
        "export_mode": {"type": "string"},
        "aps_handoff_record_ref": {"type": "string"},
        "aps_handoff_state": {"type": "string"},
        "aps_handoff_target": {"type": "string"},
        "dispatch_mode": {"type": "string"},
        "aps_output_package_id": {"type": "string"},
        "aps_output_package_kind": {"type": "string"},
        "aps_bundle_ref": {"type": "string"},
        "aps_bundle_id": {"type": "string"},
        "aps_schema_id": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "export_download_descriptor_ref": {"type": "string"},
        "external_export_download_state": {"type": "string"},
        "export_download_target": {"type": "string", "enum": ["aps_evidence_bundle_download_reference"]},
        "download_mode": {"type": "string", "enum": ["reference_only_prepare"]},
        "delivery_mode": {"type": "string", "enum": ["same_origin_artifact_stream"]},
        "operator_decision": {"type": "string", "enum": ["deliver_external_export_download"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "aps_bundle_hash": {"type": "string"},
        "aps_bundle_size_bytes": {"type": "integer"},
    },
}


EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Browser-managed form delivery uses one form field per JSON request key. "
        "Each form field value is the JSON-stringified value for that key. "
        "output_package_ids and package_kinds must be sent as JSON array strings. "
        "payload_refs and payload_hashes may be sent as JSON array strings or JSON "
        "object strings keyed by package kind or package id, not as repeated form keys."
    ),
    "required": list(EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA["required"]),
    "properties": {
        key: {
            "type": "string",
            "description": "JSON-stringified value for the matching JSON request field.",
        }
        for key in EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA["properties"]
    },
}


MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Mixed-source external export/download delivery accepts only material-authority lifecycle "
        "fields over recorded P19 readiness and streams one existing mixed-source package artifact "
        "through the same-origin response. URLs, signed references, provider/connector dispatch, "
        "destinations, package rewrites, and source-shape expansion remain non-admitted."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "material_preview_id",
        "material_preview_hash",
        "package_review_preview_hash",
        "contract_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_id",
        "package_kind",
        "package_payload_hash",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "external_export_download_readiness_record_ref",
        "external_export_download_readiness_ref",
        "external_export_download_readiness_state",
        "delivery_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "contract_hash": {"type": "string"},
        "construction_basis_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_id": {"type": "string"},
        "package_kind": {
            "type": "string",
            "enum": ["canonical_internal", "user_facing", "review_facing"],
        },
        "package_payload_hash": {"type": "string"},
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string", "enum": ["package_review_approved"]},
        "prepare_record_ref": {"type": "string"},
        "handoff_export_state": {"type": "string", "enum": ["handoff_export_prepared"]},
        "handoff_export_envelope_ref": {"type": "string"},
        "handoff_target": {"type": "string", "enum": ["mixed_source_review_package"]},
        "export_mode": {"type": "string", "enum": ["reference_envelope_only"]},
        "aps_handoff_target": {"type": "string", "enum": ["mixed_source_aps_evidence_bundle"]},
        "dispatch_mode": {"type": "string", "enum": ["server_side_mixed_source_aps_handoff"]},
        "aps_handoff_record_ref": {"type": "string"},
        "aps_handoff_state": {"type": "string", "enum": ["aps_handoff_dispatched"]},
        "external_export_download_readiness_record_ref": {"type": "string"},
        "external_export_download_readiness_ref": {"type": "string"},
        "external_export_download_readiness_state": {
            "type": "string",
            "enum": ["mixed_source_external_export_download_ready"],
        },
        "delivery_mode": {"type": "string", "enum": ["same_origin_artifact_stream"]},
        "operator_decision": {"type": "string", "enum": ["deliver_mixed_source_external_export_download"]},
        "decision_notes": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional mixed-source package kind guard; when provided it must be "
                "canonical_internal, user_facing, and review_facing in order."
            ),
        },
        "analysis_plan_id": _forbidden_request_field_schema(),
        "pass_run_id": _forbidden_request_field_schema(),
        "preview_id": _forbidden_request_field_schema(),
        "preview_hash": _forbidden_request_field_schema(),
        "result_review_record_ref": _forbidden_request_field_schema(),
        "analysis_run_id": _forbidden_request_field_schema(),
        "package_kinds": _forbidden_request_field_schema(),
        "payload_refs": _forbidden_request_field_schema(),
        "payload_hashes": _forbidden_request_field_schema(),
        "external_export_download_record_ref": _forbidden_request_field_schema(),
        "export_download_descriptor_ref": _forbidden_request_field_schema(),
        "external_export_download_state": _forbidden_request_field_schema(),
        "export_download_target": _forbidden_request_field_schema(),
        "download_mode": _forbidden_request_field_schema(),
        "aps_output_package_id": _forbidden_request_field_schema(),
        "aps_output_package_kind": _forbidden_request_field_schema(),
        "aps_bundle_ref": _forbidden_request_field_schema(),
        "aps_bundle_id": _forbidden_request_field_schema(),
        "aps_schema_id": _forbidden_request_field_schema(),
        "download": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "download_token": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_private_signed_url": _forbidden_request_field_schema(),
        "destination": _forbidden_request_field_schema(),
        "destination_selector": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "dispatch": _forbidden_request_field_schema(),
        "send": _forbidden_request_field_schema(),
        "local_outbox": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "package_review_amendment": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
    },
}


MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Mixed-source form delivery uses one form field per JSON request key. "
        "Each form field value is the JSON-stringified value for that key."
    ),
    "required": list(MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA["required"]),
    "properties": {
        key: {
            "type": "string",
            "description": "JSON-stringified value for the matching mixed-source JSON request field.",
        }
        for key in MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA["properties"]
    },
}


EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ROUTE_JSON_REQUEST_SCHEMA: dict[str, Any] = {
    "oneOf": [
        EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA,
        MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA,
    ],
    "description": "Same-origin delivery accepts either legacy APS-bundle delivery or P20 mixed-source package delivery.",
}


EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ROUTE_FORM_REQUEST_SCHEMA: dict[str, Any] = {
    "oneOf": [
        EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA,
        MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA,
    ],
    "description": (
        "Same-origin form delivery accepts either legacy APS-bundle delivery fields or P20 mixed-source "
        "package delivery fields."
    ),
}


EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_BODY: dict[str, Any] = {
    "required": True,
    "content": {
        "application/json": {"schema": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ROUTE_JSON_REQUEST_SCHEMA},
        "application/x-www-form-urlencoded": {"schema": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ROUTE_FORM_REQUEST_SCHEMA},
    },
}


ASSOCIATED_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA: dict[str, Any] = {
    **EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA,
    "description": (
        "Server-owned same-origin signed delivery reference generation for legacy associated-cohort "
        "external export/download uses the existing validated delivery authority payload."
    ),
}


MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA: dict[str, Any] = {
    **MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA,
    "description": (
        "Server-owned same-origin signed delivery reference generation for mixed-source package "
        "artifacts accepts the same P19 delivery authority payload with the explicit signed-reference "
        "operator decision."
    ),
    "properties": {
        **MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA["properties"],
        "operator_decision": {
            "type": "string",
            "enum": ["generate_mixed_source_external_export_download_signed_reference"],
        },
    },
}


EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA: dict[str, Any] = {
    "oneOf": [
        ASSOCIATED_COHORT_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA,
        MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA,
    ],
    "description": (
        "Server-owned same-origin signed delivery reference generation accepts either legacy "
        "associated-cohort delivery authority or P22 mixed-source package delivery authority. "
        "Both variants stay same-origin and forbid URL, provider, connector, destination, and "
        "package mutation fields."
    ),
}


EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["signed_reference_token"],
    "properties": {
        "signed_reference_token": {
            "type": "string",
            "description": "Server-generated short-lived signed delivery reference token.",
        },
    },
}

PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_REQUEST_FIELDS = (
    "provider_credentials",
    "provider_secret",
    "provider_bucket",
    "provider_container",
    "provider_object_key",
    "provider_object_identity",
    "raw_provider_signature",
    "raw_provider_object_key",
    "raw_local_path",
    "local_path",
    "local_file_path",
    "destination_id",
    "destination_url",
    "destination",
    "destination_selector",
    "connector_payload",
    "connector_secret",
    "connector_run_id",
    "connector_dispatch",
    "source_upload",
    "source_expansion",
    "local_upload",
    "local_directory",
    "web_connector",
    "package_mutation",
    "package_payload",
    "package_variant_content",
    "rebuild_package",
    "rewrite_output",
    "rag_vector_settings",
    "rag_vector_state",
    "prompt_model_settings",
    "prompt_or_model_payload",
    "auth_security_override",
    "auth_internal_state",
    "browser_durable_authority",
    "public_url",
    "public_proxy_url",
    "provider_url",
    "download_url",
    "signed_reference_token",
    "signed_url",
    "provider_private_signed_url_token",
    "raw_provider_private_signed_url_token",
)


PROVIDER_PRIVATE_SIGNED_URL_PREPARE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Backend/API-only provider-private signed URL prepare over existing "
        "external_export_download_prepared authority; use/revoke and rendered UI are deferred."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "export_download_target",
        "download_mode",
        "delivery_mode",
        "operator_decision",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "recipient_scope",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "export_download_descriptor_ref": {"type": "string"},
        "external_export_download_state": {"type": "string", "enum": ["external_export_download_prepared"]},
        "export_download_target": {"type": "string", "enum": ["aps_evidence_bundle_download_reference"]},
        "download_mode": {"type": "string", "enum": ["reference_only_prepare"]},
        "delivery_mode": {"type": "string", "enum": ["provider_private_signed_url"]},
        "operator_decision": {"type": "string", "enum": ["prepare_provider_private_signed_url"]},
        "source_artifact_hash": {"type": "string"},
        "source_artifact_size_bytes": {"type": "integer"},
        "recipient_scope": {"type": "string"},
        "requested_ttl_seconds": {"type": "integer", "minimum": 1, "maximum": 900, "default": 300},
        "signed_reference_receipt_id": {"type": "string"},
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_REQUEST_FIELDS
        },
    },
}


PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Backend/API-only provider-private signed URL revoke over existing durable "
        "receipt state; use and rendered UI remain deferred."
    ),
    "required": [
        "client_request_id",
        "provider_signed_url_receipt_id",
        "idempotency_key",
        "revoked_by",
        "revocation_reason",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "provider_signed_url_receipt_id": {"type": "string"},
        "idempotency_key": {"type": "string"},
        "revoked_by": {"type": "string"},
        "revocation_reason": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["revoke_provider_private_signed_url"]},
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_REQUEST_FIELDS
        },
    },
}


PROVIDER_PUBLIC_URL_FORBIDDEN_REQUEST_FIELDS = (
    "provider_public_url",
    "public_url",
    "raw_public_url",
    "public_proxy_url",
    "download_url",
    "signed_url",
    "provider_url",
    "provider_credentials",
    "provider_secret",
    "provider_token",
    "provider_bucket",
    "provider_container",
    "provider_object_key",
    "provider_object_identity",
    "raw_provider_signature",
    "raw_provider_object_key",
    "connector_dispatch",
    "connector_run_id",
    "destination_id",
    "destination_url",
    "package_mutation",
    "source_expansion",
    "local_directory",
    "web_connector",
    "rag_vector_state",
    "auth_security_override",
    "browser_durable_authority",
)


PROVIDER_PUBLIC_URL_PREPARE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Backend/API-only provider-public URL prepare/status entry over current durable "
        "provider-public URL state; delivery/use, revoke, rendered controls, public proxy, "
        "and auth/security behavior remain deferred."
    ),
    "required": [
        "client_request_id",
        "provider_private_signed_url_receipt_id",
        "recipient_scope",
        "delivery_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "provider_private_signed_url_receipt_id": {"type": "string"},
        "recipient_scope": {"type": "string"},
        "requested_ttl_seconds": {"type": "integer", "minimum": 1, "maximum": 900, "default": 300},
        "delivery_mode": {"type": "string", "enum": ["provider_public_url"]},
        "operator_decision": {"type": "string", "enum": ["prepare_provider_public_url"]},
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in PROVIDER_PUBLIC_URL_FORBIDDEN_REQUEST_FIELDS
        },
    },
}


PROVIDER_PUBLIC_URL_REVOKE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Backend/API-only provider-public URL revoke entry over current durable "
        "provider-public URL state; delivery/use, rendered controls, public proxy, "
        "and auth/security behavior remain deferred."
    ),
    "required": [
        "client_request_id",
        "provider_public_url_receipt_id",
        "idempotency_key",
        "revoked_by",
        "revocation_reason",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "provider_public_url_receipt_id": {"type": "string"},
        "idempotency_key": {"type": "string"},
        "revoked_by": {"type": "string"},
        "revocation_reason": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["revoke_provider_public_url"]},
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in PROVIDER_PUBLIC_URL_FORBIDDEN_REQUEST_FIELDS
        },
    },
}


PROVIDER_PUBLIC_URL_DELIVERY_USE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Read-only fake-provider provider-public delivery/use decision over existing "
        "redacted provider-public receipt authority. It never returns raw URLs, streams "
        "bytes, redirects, writes provider objects, invokes connector/network dispatch, "
        "or creates durable use/audit rows."
    ),
    "required": [
        "client_request_id",
        "provider_public_url_receipt_id",
        "delivery_use_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "provider_public_url_receipt_id": {"type": "string"},
        "expected_authority_hash": {"type": "string"},
        "expected_source_artifact_hash": {"type": "string"},
        "expected_source_artifact_size_bytes": {"type": "integer"},
        "delivery_use_mode": {"type": "string", "enum": ["fake_provider_redacted_use_decision"]},
        "operator_decision": {"type": "string", "enum": ["use_provider_public_url_redacted_fake_provider"]},
        **{
            field: _forbidden_request_field_schema()
            for field in (
                *PROVIDER_PUBLIC_URL_FORBIDDEN_REQUEST_FIELDS,
                "source_payload",
                "local_path",
                "prompt_model_settings",
                "prompt_or_model_payload",
            )
        },
    },
}


def _json_request_body(schema: dict[str, Any]) -> dict[str, Any]:
    return {"required": True, "content": {"application/json": {"schema": schema}}}


SOURCE_CLASS_SCHEMA: dict[str, Any] = {
    "type": "string",
    "enum": ["dataset_version", "aps_content_document"],
}


PREFLIGHT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Known preflight fields; source-widening fields are rejected before service execution.",
    "required": ["natural_language_intent"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.preflight_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string"},
        "natural_language_intent": {"type": "string"},
        "manual_constraints": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "topics": {"type": "array", "items": {"type": "string"}},
                "source_classes": {"type": "array", "items": SOURCE_CLASS_SCHEMA},
                "date_bounds": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "null"},
                    ],
                },
                "required_artifacts": {"type": "array", "items": {"type": "string"}},
                "conflict": {"type": "boolean"},
                "conflicts": {"type": "array", "items": {"type": "string"}},
                **{
                    field: _forbidden_request_field_schema()
                    for field in sorted(PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS)
                },
            },
        },
        "actor": {"type": "string"},
    },
}


SOURCE_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict source-preview fields; source expansion fields are rejected before service execution.",
    "required": ["preflight_id"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.source_preview_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string"},
        "preflight_id": {"type": "string"},
        "selected_source_classes": {"type": "array", "items": SOURCE_CLASS_SCHEMA},
        "actor": {"type": "string"},
    },
}


MATERIAL_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict material-preview fields; source expansion fields are rejected before service execution.",
    "required": ["source_candidate_ids"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.material_preview_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string"},
        "preflight_id": {"type": "string"},
        "source_set_id": {"type": "string"},
        "source_candidate_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "dataset_version_ids": {"type": "array", "items": {"type": "string"}},
        "aps_content_document_ids": {"type": "array", "items": {"type": "string"}},
        "query_basis": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "terms": {"type": "array", "items": {"type": "string"}},
                "filters": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "dataset_version_ids": {"type": "array", "items": {"type": "string"}},
                        "aps_content_document_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        "actor": {"type": "string"},
    },
}


RAW_MIXED_CORPUS_SEED_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Strict raw mixed corpus seed-only fields; source upload, local-directory, web, "
        "RAG/vector, package, connector, provider/public URL, mockup, hidden-LLM, and "
        "auth/security fields are rejected before service mutation."
    ),
    "required": [
        "client_request_id",
        "seed_mode",
        "corpus_batch_id",
        "aps_run_id",
        "target_ids",
        "artifact_manifest_ref",
        "artifact_manifest_hash",
        "requested_source_classes",
        "operator_confirmation",
    ],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.raw_mixed_corpus_seed_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string", "minLength": 1},
        "seed_mode": {"type": "string", "enum": ["raw_mixed_corpus_bridge_seed_only"]},
        "corpus_batch_id": {"type": "string", "minLength": 1},
        "aps_run_id": {"type": "string", "minLength": 1},
        "target_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "artifact_manifest_ref": {
            "type": "string",
            "minLength": 1,
            "description": "Server-owned storage-root manifest reference; no local upload or directory traversal.",
        },
        "artifact_manifest_hash": {"type": "string", "minLength": 64, "maxLength": 64},
        "requested_source_classes": {"type": "array", "items": SOURCE_CLASS_SCHEMA, "minItems": 2},
        "operator_confirmation": {"type": "boolean"},
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(layer3_raw_mixed_bridge.RAW_MIXED_CORPUS_FORBIDDEN_FIELDS)
        },
    },
}


RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Strict raw mixed corpus materialization fields; the endpoint writes only admitted "
        "source authority rows from a server-owned manifest and rejects source upload, "
        "local-directory, web, RAG/vector, package, connector, provider/public URL, mockup, "
        "hidden-LLM, and auth/security fields."
    ),
    "required": [
        "client_request_id",
        "materialization_mode",
        "corpus_batch_id",
        "artifact_manifest_ref",
        "artifact_manifest_hash",
        "requested_source_classes",
        "operator_confirmation",
    ],
    "properties": {
        "schema_id": {
            "type": "string",
            "enum": [layer3_raw_mixed_materialization.RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID],
        },
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string", "minLength": 1},
        "materialization_mode": {
            "type": "string",
            "enum": [layer3_raw_mixed_materialization.RAW_MIXED_CORPUS_MATERIALIZE_MODE],
        },
        "corpus_batch_id": {"type": "string", "minLength": 1},
        "artifact_manifest_ref": {
            "type": "string",
            "minLength": 1,
            "description": "Server-owned storage-root materialization manifest reference; no local upload or directory traversal.",
        },
        "artifact_manifest_hash": {"type": "string", "minLength": 64, "maxLength": 64},
        "requested_source_classes": {"type": "array", "items": SOURCE_CLASS_SCHEMA, "minItems": 2},
        "operator_confirmation": {"type": "boolean"},
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(layer3_raw_mixed_bridge.RAW_MIXED_CORPUS_FORBIDDEN_FIELDS)
        },
    },
}


GATE_B_DECISION_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate_id", "decision"],
    "properties": {
        "candidate_id": {"type": "string"},
        "decision": {"type": "string", "enum": ["approved", "denied", "isolated", "flagged"]},
        "operator_reason": {"type": "string"},
        "decision_basis": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "source_ref": {"type": "string"},
                "query_basis": {"type": "string"},
                "provenance_ref": {"type": "string"},
                "source_identity": {"type": "object", "additionalProperties": True},
                "source_provenance": {"type": "object", "additionalProperties": True},
                "payload": {"type": "object", "additionalProperties": True},
                "load_summary": {"type": "object", "additionalProperties": True},
            },
        },
    },
}


GATE_B_DECISION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict Gate B fields; client_request_id is required for durable idempotency and denied, isolated, and flagged decisions require operator_reason at runtime.",
    "required": ["client_request_id", "candidate_decisions"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.gate_b_decision_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string", "minLength": 1},
        "preflight_id": {"type": "string"},
        "source_set_id": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "actor": {"type": "string"},
        "candidate_decisions": {
            "type": "array",
            "items": GATE_B_DECISION_ITEM_SCHEMA,
            "minItems": 1,
        },
        "commit_reason": {"type": "string"},
    },
}


GATE_C_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict Gate C preview fields; commit_typing controls owner-service materialization.",
    "required": ["session_id"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.gate_c_preview_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "commit_typing": {"type": "boolean"},
        "actor": {"type": "string"},
    },
}


PLAN_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict plan-preview fields; execution/package/handoff/source-widening fields are rejected before service mutation.",
    "required": ["session_id"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.plan_preview_request.v1"]},
        "schema_version": {"type": "integer"},
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "preview_scope": {"type": "string", "enum": ["owner_service_default"]},
        "include_exclusions": {"type": "boolean"},
        "requested_method_name": {"type": "string"},
    },
}


PLAN_APPROVAL_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict plan-approval fields; extra execution/package/handoff fields are rejected before service mutation.",
    "required": ["session_id", "preview_id", "preview_hash", "operator_confirmation"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.plan_approval_request.v1"]},
        "schema_version": {"type": "integer"},
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "operator_confirmation": {"type": "boolean", "enum": [True]},
        "approval_scope": {"type": "string", "enum": ["owner_service_default"]},
        "requested_method_name": {"type": "string"},
    },
}


APPROVED_PLAN_CANCEL_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict approved-plan cancellation fields; only cancel-without-replacement before pass-run creation is admitted.",
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
    ],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.approved_plan_cancel_request.v1"]},
        "schema_version": {"type": "integer"},
        "client_request_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "source_preview_id": {"type": "string"},
        "source_preview_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["cancel_approved_plan_without_replacement"]},
        "operator_note": {"type": "string"},
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "replacement_plan": _forbidden_request_field_schema(),
        "reopen_approved_plan": _forbidden_request_field_schema(),
        "delete_approved_plan": _forbidden_request_field_schema(),
        "create_pass_runs": _forbidden_request_field_schema(),
        "execution": _forbidden_request_field_schema(),
        "analysis_run_id": _forbidden_request_field_schema(),
        "package_mutation": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "vector_plan": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_plan": _forbidden_request_field_schema(),
        "frontend_state": _forbidden_request_field_schema(),
        "hidden_llm_plan": _forbidden_request_field_schema(),
    },
}


PLAN_REVISION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict plan-revision fields; explicit execution/package/handoff/source-widening fields remain fail-closed.",
    "required": ["session_id", "preview_id", "preview_hash", "operator_decision"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.plan_revision_request.v1"]},
        "schema_version": {"type": "integer"},
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["reject_current_preview", "request_revision"]},
        "operator_note": {"type": "string"},
        "requested_method_name": {"type": "string"},
        "execute": _forbidden_request_field_schema(),
        "execution": _forbidden_request_field_schema(),
        "run": _forbidden_request_field_schema(),
        "run_analysis": _forbidden_request_field_schema(),
        "package": _forbidden_request_field_schema(),
        "package_review": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "plan_edits": _forbidden_request_field_schema(),
        "natural_language_plan": _forbidden_request_field_schema(),
        "llm_plan": _forbidden_request_field_schema(),
        "execution_started": _forbidden_request_field_schema(),
        "create_pass_runs": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "result_review": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_plan": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "vector_plan": _forbidden_request_field_schema(),
    },
}


PLAN_REVISION_RECOVERY_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict plan-revision recovery fields; only server-authorized preview refresh from recorded revision-control state is admitted.",
    "required": [
        "client_request_id",
        "session_id",
        "source_revision_state",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
    ],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.plan_revision_recovery_request.v1"]},
        "schema_version": {"type": "integer"},
        "client_request_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string"},
        "source_revision_state": {"type": "string", "enum": ["plan_rejected", "plan_revision_requested"]},
        "source_preview_id": {"type": "string"},
        "source_preview_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["recover_for_preview_refresh"]},
        "operator_note": {"type": "string"},
        "approve_plan": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "delete_approved_plan": _forbidden_request_field_schema(),
        "execute": _forbidden_request_field_schema(),
        "execution": _forbidden_request_field_schema(),
        "run": _forbidden_request_field_schema(),
        "run_analysis": _forbidden_request_field_schema(),
        "package": _forbidden_request_field_schema(),
        "package_review": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "plan_edits": _forbidden_request_field_schema(),
        "natural_language_plan": _forbidden_request_field_schema(),
        "llm_plan": _forbidden_request_field_schema(),
        "execution_started": _forbidden_request_field_schema(),
        "create_pass_runs": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "analysis_run_id": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "result_review": _forbidden_request_field_schema(),
        "package_mutation": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_plan": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "vector_plan": _forbidden_request_field_schema(),
        "browser_persisted_state": _forbidden_request_field_schema(),
    },
}


EXECUTION_SELECTION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict execution-selection fields; explicit execution/run/result/package/handoff/source-widening fields remain fail-closed.",
    "required": ["client_request_id", "session_id", "analysis_plan_id", "preview_id", "preview_hash"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "operator_reason": {"type": "string"},
        "execute": _forbidden_request_field_schema(),
        "execution": _forbidden_request_field_schema(),
        "run": _forbidden_request_field_schema(),
        "run_analysis": _forbidden_request_field_schema(),
        "start_execution": _forbidden_request_field_schema(),
        "analysis_run_id": _forbidden_request_field_schema(),
        "analysis_run_ids": _forbidden_request_field_schema(),
        "result_review": _forbidden_request_field_schema(),
        "results": _forbidden_request_field_schema(),
        "package": _forbidden_request_field_schema(),
        "package_review": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "vector_plan": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_plan": _forbidden_request_field_schema(),
    },
}


ANALYSIS_EXECUTION_START_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict analysis execution-start fields; explicit batch/package/handoff/source-widening fields remain fail-closed.",
    "required": ["client_request_id", "session_id", "analysis_plan_id", "pass_run_id", "preview_id", "preview_hash"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "execution_mode": {"type": "string", "enum": ["synchronous_single_pass"]},
        "operator_reason": {"type": "string"},
        "run_all": _forbidden_request_field_schema(),
        "batch": _forbidden_request_field_schema(),
        "package": _forbidden_request_field_schema(),
        "package_review": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "result_review": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "vector_plan": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_plan": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "results": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "schema_widening": _forbidden_request_field_schema(),
    },
}


EXECUTION_RESULT_STATUS_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict status-only result inspection fields; explicit review/package/handoff/source-widening fields remain fail-closed.",
    "required": ["session_id", "analysis_plan_id", "pass_run_id", "preview_id", "preview_hash"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "operator_view_mode": {"type": "string", "enum": ["status_only"]},
        "approve_result": _forbidden_request_field_schema(),
        "reject_result": _forbidden_request_field_schema(),
        "result_review": _forbidden_request_field_schema(),
        "result_decision": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "package": _forbidden_request_field_schema(),
        "package_review": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "run_all": _forbidden_request_field_schema(),
        "batch": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "vector_plan": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_plan": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
    },
}


EXECUTION_RESULT_REVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "review_notes are required by runtime for changes_requested, rejected, and blocked decisions.",
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["approved", "changes_requested", "rejected", "blocked"]},
        "review_notes": {"type": "string"},
        "reviewed_output_items": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        "analysis_run_id": {"type": "string"},
        "package": _forbidden_request_field_schema(),
        "package_review": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "package_variant": _forbidden_request_field_schema(),
        "aps_handoff": _forbidden_request_field_schema(),
        "external_export_download": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "connector_ref": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "onlook": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
    },
}


PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict package-review preview fields; selected-pass and material-preview request shapes are mutually exclusive, and explicit package/handoff/source-widening fields remain fail-closed.",
    "required": ["session_id"],
    "oneOf": [
        {
            "required": ["session_id", "analysis_plan_id", "pass_run_id", "preview_id", "preview_hash"],
            "not": {"anyOf": [{"required": ["material_preview_id"]}, {"required": ["material_preview_hash"]}]},
        },
        {
            "required": ["session_id", "material_preview_id", "material_preview_hash"],
            "not": {
                "anyOf": [
                    {"required": ["analysis_plan_id"]},
                    {"required": ["pass_run_id"]},
                    {"required": ["preview_id"]},
                    {"required": ["preview_hash"]},
                    {"required": ["result_review_record_ref"]},
                    {"required": ["analysis_run_id"]},
                ]
            },
        },
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "package": _forbidden_request_field_schema(),
        "package_review_decision": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "package_variant": _forbidden_request_field_schema(),
        "output_package_id": _forbidden_request_field_schema(),
        "reconciliation_record_id": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "aps_handoff": _forbidden_request_field_schema(),
        "onlook": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
    },
}


PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict package construction commit fields; selected-pass and material-authority request shapes are mutually exclusive, and explicit review/handoff/source-widening/package-payload fields remain fail-closed.",
    "required": ["client_request_id", "session_id", "package_review_preview_hash"],
    "oneOf": [
        {
            "required": [
                "client_request_id",
                "session_id",
                "analysis_plan_id",
                "pass_run_id",
                "preview_id",
                "preview_hash",
                "result_review_record_ref",
                "package_review_preview_hash",
            ],
            "not": {
                "anyOf": [
                    {"required": ["material_preview_id"]},
                    {"required": ["material_preview_hash"]},
                    {"required": ["contract_hash"]},
                ]
            },
        },
        {
            "required": [
                "client_request_id",
                "session_id",
                "material_preview_id",
                "material_preview_hash",
                "package_review_preview_hash",
                "contract_hash",
            ],
            "not": {
                "anyOf": [
                    {"required": ["analysis_plan_id"]},
                    {"required": ["pass_run_id"]},
                    {"required": ["preview_id"]},
                    {"required": ["preview_hash"]},
                    {"required": ["result_review_record_ref"]},
                    {"required": ["analysis_run_id"]},
                ]
            },
        },
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "contract_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "package_review_decision": _forbidden_request_field_schema(),
        "submit_package_review": _forbidden_request_field_schema(),
        "approve_package": _forbidden_request_field_schema(),
        "reject_package": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "aps_handoff": _forbidden_request_field_schema(),
        "external_export_download": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "connector_ref": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "onlook": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
    },
}


PACKAGE_REVIEW_SUBMIT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Package-review submit accepts exactly one authority shape: selected-pass lifecycle authority "
        "or mixed-source material authority. decision_notes are required by runtime for changes_requested, "
        "rejected, and blocked decisions."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "operator_decision",
    ],
    "oneOf": [
        {
            "required": [
                "client_request_id",
                "session_id",
                "analysis_plan_id",
                "pass_run_id",
                "preview_id",
                "preview_hash",
                "result_review_record_ref",
                "package_review_preview_hash",
                "reconciliation_record_id",
                "output_package_ids",
                "payload_hashes",
                "operator_decision",
            ],
            "not": {
                "anyOf": [
                    {"required": ["material_preview_id"]},
                    {"required": ["material_preview_hash"]},
                    {"required": ["contract_hash"]},
                ]
            },
        },
        {
            "required": [
                "client_request_id",
                "session_id",
                "material_preview_id",
                "material_preview_hash",
                "package_review_preview_hash",
                "contract_hash",
                "construction_basis_hash",
                "reconciliation_record_id",
                "output_package_ids",
                "payload_hashes",
                "operator_decision",
            ],
            "not": {
                "anyOf": [
                    {"required": ["analysis_plan_id"]},
                    {"required": ["pass_run_id"]},
                    {"required": ["preview_id"]},
                    {"required": ["preview_hash"]},
                    {"required": ["result_review_record_ref"]},
                    {"required": ["analysis_run_id"]},
                    {"required": ["payload_refs"]},
                ]
            },
        },
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "contract_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "construction_basis_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "payload_refs": _string_array_or_string_map_schema(
            "List of package payload refs or a mapping keyed by package kind or package id."
        ),
        "payload_hashes": _string_array_or_string_map_schema(
            "List of package payload hashes or a mapping keyed by package kind or package id."
        ),
        "operator_decision": {"type": "string", "enum": ["approved", "changes_requested", "rejected", "blocked"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "aps_handoff": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "external_export_download": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "connector_ref": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "onlook": _forbidden_request_field_schema(),
    },
}


PACKAGE_SUPERSESSION_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Read-only package supersession preview. Existing package rows and payload refs remain immutable; "
        "broad package mutation/reconstruction stays fail-closed."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_preview_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "payload_refs": {"type": "array", "items": {"type": "string"}},
        "payload_hashes": {"type": "array", "items": {"type": "string"}},
        "package_review_preview_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["preview_package_supersession"]},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_submit_record_ref": {"type": "string"},
        "handoff_export_record_ref": {"type": "string"},
        "aps_handoff_record_ref": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_payload_ref": _forbidden_request_field_schema(),
        "update_payload_hash": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "package_review_amendment": _forbidden_request_field_schema(),
        "handoff_export_amendment": _forbidden_request_field_schema(),
        "aps_handoff_amendment": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
    },
}


REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-owned replacement package artifact materialization from package supersession preview authority. "
        "It writes only deterministic replacement artifacts under the server-owned replacement-package-artifacts "
        "namespace and returns computed replacement package-set request fields."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "package_supersession_preview_hash": {"type": "string"},
        "source_package_set_hash": {"type": "string"},
        "source_output_package_ids": {"type": "array", "items": {"type": "string"}},
        "source_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "source_payload_refs": {"type": "array", "items": {"type": "string"}},
        "source_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "operator_decision": {
            "type": "string",
            "enum": ["materialize_replacement_package_artifacts_from_supersession_preview"],
        },
        "replacement_package_set_id": _forbidden_request_field_schema(),
        "replacement_package_set_hash": _forbidden_request_field_schema(),
        "replacement_package_kinds": _forbidden_request_field_schema(),
        "replacement_payload_refs": _forbidden_request_field_schema(),
        "replacement_payload_hashes": _forbidden_request_field_schema(),
        "authority_basis_hash": _forbidden_request_field_schema(),
        "materialization_basis_hash": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "replacement_package_payloads": _forbidden_request_field_schema(),
        "replacement_package_payload_bytes": _forbidden_request_field_schema(),
        "edited_package_content": _forbidden_request_field_schema(),
        "artifact_bytes": _forbidden_request_field_schema(),
        "generate_artifact": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_package_row": _forbidden_request_field_schema(),
        "update_payload_ref": _forbidden_request_field_schema(),
        "update_payload_hash": _forbidden_request_field_schema(),
        "replacement_package_set_authority_id": _forbidden_request_field_schema(),
        "package_supersession_commit": _forbidden_request_field_schema(),
        "package_supersession_commit_id": _forbidden_request_field_schema(),
        "replacement_output_package_ids": _forbidden_request_field_schema(),
        "package_row_mutation": _forbidden_request_field_schema(),
        "package_payload_write": _forbidden_request_field_schema(),
        "package_payload_rewrite": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_payload": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
    },
}


REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Durable replacement package-set authority record. It records replacement package-set ids, refs, and hashes "
        "without creating or mutating package rows and without writing package payloads."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "source_package_set_hash": {"type": "string"},
        "source_output_package_ids": {"type": "array", "items": {"type": "string"}},
        "source_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "source_payload_refs": {"type": "array", "items": {"type": "string"}},
        "source_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "replacement_package_set_id": {"type": "string"},
        "replacement_package_set_hash": {"type": "string"},
        "replacement_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "replacement_payload_refs": {"type": "array", "items": {"type": "string"}},
        "replacement_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "authority_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["record_replacement_package_set_authority"]},
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "replacement_package_payloads": _forbidden_request_field_schema(),
        "edited_package_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_payload_ref": _forbidden_request_field_schema(),
        "update_payload_hash": _forbidden_request_field_schema(),
        "package_supersession_commit": _forbidden_request_field_schema(),
        "package_row_mutation": _forbidden_request_field_schema(),
        "package_payload_rewrite": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
    },
}


REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-derived replacement package-set authority from an existing corrected package artifact-set authority. "
        "The caller supplies only identity and basis fields; package refs, hashes, and authority basis are derived "
        "server-side, and raw local paths are not exposed in the response."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "corrected_package_artifact_set_id",
        "corrected_artifact_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "source_package_set_hash": {"type": "string"},
        "corrected_package_artifact_set_id": {"type": "string"},
        "corrected_artifact_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["record_replacement_package_set_authority"]},
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(
                layer3_replacement_package_set_authority.REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
            )
        },
    },
}


PACKAGE_SUPERSESSION_COMMIT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Durable package supersession commit lineage record. It records immutable lineage from the existing "
        "source package set to an existing replacement package-set authority without mutating package rows "
        "or writing package payloads."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_authority_id",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "replacement_authority_basis_hash",
        "downstream_dependency_hash",
        "commit_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "package_supersession_preview_hash": {"type": "string"},
        "source_package_set_hash": {"type": "string"},
        "source_output_package_ids": {"type": "array", "items": {"type": "string"}},
        "source_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "source_payload_refs": {"type": "array", "items": {"type": "string"}},
        "source_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "replacement_package_set_authority_id": {"type": "string"},
        "replacement_package_set_id": {"type": "string"},
        "replacement_package_set_hash": {"type": "string"},
        "replacement_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "replacement_payload_refs": {"type": "array", "items": {"type": "string"}},
        "replacement_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "replacement_authority_basis_hash": {"type": "string"},
        "downstream_dependency_hash": {"type": "string"},
        "commit_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["commit_package_supersession"]},
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "replacement_output_package_ids": _forbidden_request_field_schema(),
        "replacement_package_payloads": _forbidden_request_field_schema(),
        "edited_package_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_package_row": _forbidden_request_field_schema(),
        "package_row_mutation": _forbidden_request_field_schema(),
        "package_payload_rewrite": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff_package": _forbidden_request_field_schema(),
        "export_package": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_payload": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_plan": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_plan": _forbidden_request_field_schema(),
        "ui_control": _forbidden_request_field_schema(),
        "auth_context": _forbidden_request_field_schema(),
        "security_context": _forbidden_request_field_schema(),
    },
}


PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-computed package supersession commit from corrected-artifact replacement authority. "
        "The caller supplies only identity and basis fields; source and replacement refs/hashes, downstream hash, "
        "preview hash, and commit basis hash are derived server-side and raw local paths are redacted in the response."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "corrected_package_artifact_set_id",
        "corrected_artifact_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "corrected_package_artifact_set_id": {"type": "string"},
        "corrected_artifact_basis_hash": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "replacement_authority_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["commit_package_supersession"]},
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(
                layer3_package_supersession_commit.PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
            )
        },
    },
}


REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Durable replacement package artifact manifest record. It server-verifies existing replacement refs and "
        "hashes without generating artifacts, creating output package rows, or writing package payloads."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "hash_algorithm",
        "artifact_namespace",
        "artifact_manifest_hash",
        "authority_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "package_supersession_commit_id": {"type": "string"},
        "package_supersession_commit_basis_hash": {"type": "string"},
        "replacement_package_set_id": {"type": "string"},
        "replacement_package_set_hash": {"type": "string"},
        "replacement_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "replacement_payload_refs": {"type": "array", "items": {"type": "string"}},
        "replacement_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "hash_algorithm": {"type": "string", "enum": ["sha256"]},
        "artifact_namespace": {"type": "string", "enum": ["replacement-package-artifacts"]},
        "artifact_manifest_hash": {"type": "string"},
        "authority_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["record_replacement_package_artifact_manifest"]},
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "replacement_package_payloads": _forbidden_request_field_schema(),
        "replacement_package_payload_bytes": _forbidden_request_field_schema(),
        "edited_package_content": _forbidden_request_field_schema(),
        "artifact_bytes": _forbidden_request_field_schema(),
        "generate_artifact": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_package_row": _forbidden_request_field_schema(),
        "update_payload_ref": _forbidden_request_field_schema(),
        "update_payload_hash": _forbidden_request_field_schema(),
        "replacement_output_package_ids": _forbidden_request_field_schema(),
        "package_row_mutation": _forbidden_request_field_schema(),
        "package_payload_write": _forbidden_request_field_schema(),
        "package_payload_rewrite": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_payload": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "approved_plan_supersession": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
    },
}


REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-computed replacement package artifact manifest record from existing materialization, "
        "replacement package-set authority, and supersession commit rows. It accepts authority ids only, "
        "computes manifest hashes and byte-size basis server-side, and returns redacted artifact refs. "
        "Successful responses use schema_id layer3.replacement_package_artifact_manifest_from_authority.v1."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_artifact_materialization_id",
        "materialization_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "replacement_artifact_materialization_id": {"type": "string"},
        "materialization_basis_hash": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "replacement_authority_basis_hash": {"type": "string"},
        "package_supersession_commit_id": {"type": "string"},
        "package_supersession_commit_basis_hash": {"type": "string"},
        "operator_decision": {
            "type": "string",
            "enum": ["record_replacement_package_artifact_manifest_from_authority"],
        },
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(
                layer3_replacement_package_artifact_manifest.REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_FORBIDDEN_FIELDS
            )
        },
    },
}


REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-computed replacement package artifact manifest record from corrected artifact-set, "
        "corrected-artifact replacement package-set authority, and corrected-artifact supersession commit rows. "
        "It accepts authority ids only, computes manifest hashes and byte-size basis server-side, and returns "
        "redacted artifact refs. Successful responses use schema_id "
        "layer3.replacement_package_artifact_manifest_from_corrected_artifact_set_authority.v1."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "corrected_package_artifact_set_id",
        "corrected_artifact_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "corrected_package_artifact_set_id": {"type": "string"},
        "corrected_artifact_basis_hash": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "replacement_authority_basis_hash": {"type": "string"},
        "package_supersession_commit_id": {"type": "string"},
        "package_supersession_commit_basis_hash": {"type": "string"},
        "operator_decision": {
            "type": "string",
            "enum": ["record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority"],
        },
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(
                layer3_replacement_package_artifact_manifest.REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
            )
        },
    },
}


CORRECTED_PACKAGE_ARTIFACT_SET_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-owned corrected package artifact-set authority record from existing structured review, "
        "source package, package-review preview, and server-owned artifact materialization authority. "
        "It accepts no corrected artifact refs, browser bytes, diffs, paths, URLs, package mutation, "
        "connector dispatch, credentials, source expansion, or RAG/vector instructions. Successful "
        "responses use schema_id layer3.corrected_package_artifact_set.v1 and redact raw artifact refs."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "result_review_record_ref",
        "reviewed_output_items_hash",
        "package_review_preview_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "source_package_set_hash": {"type": "string"},
        "source_output_package_ids": {"type": "array", "items": {"type": "string"}},
        "source_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "source_payload_refs": {"type": "array", "items": {"type": "string"}},
        "source_payload_hashes": {"type": "array", "items": {"type": "string"}},
        "result_review_record_ref": {"type": "string"},
        "reviewed_output_items_hash": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "operator_decision": {
            "type": "string",
            "enum": ["record_corrected_package_artifact_set_from_review_corrections"],
        },
        "package_supersession_preview_hash": {"type": "string"},
        "replacement_artifact_materialization_id": {"type": "string"},
        "materialization_basis_hash": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(
                layer3_corrected_package_artifact_set.CORRECTED_PACKAGE_ARTIFACT_SET_FORBIDDEN_FIELDS
            )
        },
    },
}


REPLACEMENT_PACKAGE_NAMESPACE_RECORD_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Durable replacement output package namespace row. It records response-safe metadata for one "
        "server-verified replacement artifact in a separate replacement table without mutating source "
        "L3OutputPackage rows or writing package payloads."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "replacement_artifact_manifest_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "source_output_package_id",
        "package_kind",
        "package_schema_id",
        "artifact_ref",
        "artifact_hash",
        "authority_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "replacement_artifact_manifest_id": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "package_supersession_commit_id": {"type": "string"},
        "source_output_package_id": {"type": "string"},
        "package_kind": {
            "type": "string",
            "enum": ["canonical_internal", "user_facing", "review_facing"],
        },
        "package_schema_id": {
            "type": "string",
            "enum": [
                "layer3.canonical_internal_package.v1",
                "layer3.user_facing_package.v1",
                "layer3.review_facing_package.v1",
            ],
        },
        "artifact_ref": {"type": "string"},
        "artifact_hash": {"type": "string"},
        "authority_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["record_replacement_package_namespace"]},
        "package_payload": _forbidden_request_field_schema(),
        "package_payload_bytes": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "replacement_package_payloads": _forbidden_request_field_schema(),
        "replacement_package_payload_bytes": _forbidden_request_field_schema(),
        "replacement_content": _forbidden_request_field_schema(),
        "generated_file_bytes": _forbidden_request_field_schema(),
        "edited_package_content": _forbidden_request_field_schema(),
        "artifact_bytes": _forbidden_request_field_schema(),
        "generate_artifact": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_package_row": _forbidden_request_field_schema(),
        "update_payload_ref": _forbidden_request_field_schema(),
        "update_payload_hash": _forbidden_request_field_schema(),
        "source_l3_output_package_write": _forbidden_request_field_schema(),
        "source_output_package_update": _forbidden_request_field_schema(),
        "package_row_mutation": _forbidden_request_field_schema(),
        "package_payload_write": _forbidden_request_field_schema(),
        "package_payload_rewrite": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "connector_destination": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_payload": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "source_directory": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_input": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "qualitative_execution_instruction": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_prompt": _forbidden_request_field_schema(),
        "hidden_llm_plan": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "rendered_control_state": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "auth_security_directive": _forbidden_request_field_schema(),
        "auth_context": _forbidden_request_field_schema(),
        "security_context": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
    },
}


REPLACEMENT_PACKAGE_NAMESPACE_FROM_CORRECTED_MANIFEST_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-computed complete replacement namespace set from corrected-artifact manifest authority. "
        "It accepts authority ids and basis hashes only, derives source package ids, package kinds, "
        "schema ids, artifact refs, artifact hashes, and per-row authority basis hashes server-side, "
        "and records L3ReplacementOutputPackage rows without mutating source packages."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "corrected_package_artifact_set_id",
        "corrected_artifact_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "replacement_artifact_manifest_id",
        "replacement_artifact_manifest_authority_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "corrected_package_artifact_set_id": {"type": "string"},
        "corrected_artifact_basis_hash": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "replacement_authority_basis_hash": {"type": "string"},
        "package_supersession_commit_id": {"type": "string"},
        "package_supersession_commit_basis_hash": {"type": "string"},
        "replacement_artifact_manifest_id": {"type": "string"},
        "replacement_artifact_manifest_authority_basis_hash": {"type": "string"},
        "operator_decision": {
            "type": "string",
            "enum": ["record_replacement_package_namespace_from_corrected_artifact_manifest_authority"],
        },
        **{
            field: _forbidden_request_field_schema()
            for field in sorted(
                layer3_replacement_package_namespace.REPLACEMENT_PACKAGE_NAMESPACE_FROM_CORRECTED_MANIFEST_FORBIDDEN_FIELDS
            )
        },
    },
}


PACKAGE_REPLACEMENT_ACTIVATION_COMMIT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Durable package replacement activation commit. It selects one complete response-safe replacement "
        "namespace set as active package authority without mutating source L3OutputPackage rows, rewriting "
        "package payloads, dispatching connectors, or accepting browser-supplied paths."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "replacement_artifact_manifest_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "replacement_output_package_ids",
        "source_output_package_ids",
        "package_kinds",
        "replacement_activation_basis_hash",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "replacement_artifact_manifest_id": {"type": "string"},
        "replacement_package_set_authority_id": {"type": "string"},
        "package_supersession_commit_id": {"type": "string"},
        "replacement_output_package_ids": {"type": "array", "items": {"type": "string"}},
        "source_output_package_ids": {"type": "array", "items": {"type": "string"}},
        "package_kinds": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["canonical_internal", "user_facing", "review_facing"],
            },
        },
        "replacement_activation_basis_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["activate_replacement_output_package_namespace"]},
        "package_payload": _forbidden_request_field_schema(),
        "package_payload_bytes": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "replacement_package_payloads": _forbidden_request_field_schema(),
        "replacement_package_payload_bytes": _forbidden_request_field_schema(),
        "edited_package_content": _forbidden_request_field_schema(),
        "artifact_bytes": _forbidden_request_field_schema(),
        "generate_artifact": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "mutate_package": _forbidden_request_field_schema(),
        "replace_package": _forbidden_request_field_schema(),
        "delete_package": _forbidden_request_field_schema(),
        "update_package_row": _forbidden_request_field_schema(),
        "update_payload_ref": _forbidden_request_field_schema(),
        "update_payload_hash": _forbidden_request_field_schema(),
        "source_l3_output_package_write": _forbidden_request_field_schema(),
        "source_output_package_update": _forbidden_request_field_schema(),
        "package_row_mutation": _forbidden_request_field_schema(),
        "package_payload_write": _forbidden_request_field_schema(),
        "package_payload_rewrite": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "handoff": _forbidden_request_field_schema(),
        "export": _forbidden_request_field_schema(),
        "connector_destination": _forbidden_request_field_schema(),
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_payload": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "source_directory": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_input": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "qualitative_execution_instruction": _forbidden_request_field_schema(),
        "qualitative_plan": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_prompt": _forbidden_request_field_schema(),
        "hidden_llm_plan": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "rendered_control_state": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
        "auth_security_directive": _forbidden_request_field_schema(),
        "auth_context": _forbidden_request_field_schema(),
        "security_context": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
    },
}


HANDOFF_EXPORT_PREPARE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Handoff/export prepare accepts exactly one authority shape: selected-pass lifecycle authority "
        "or mixed-source material authority. decision_notes are required by runtime for hold, decline, "
        "and blocked decisions."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "handoff_target",
        "export_mode",
        "operator_decision",
    ],
    "oneOf": [
        {
            "required": [
                "client_request_id",
                "session_id",
                "analysis_plan_id",
                "pass_run_id",
                "preview_id",
                "preview_hash",
                "result_review_record_ref",
                "package_review_preview_hash",
                "reconciliation_record_id",
                "output_package_ids",
                "payload_hashes",
                "package_review_submit_record_ref",
                "package_review_state",
                "package_review_submit_schema_id",
                "handoff_target",
                "export_mode",
                "operator_decision",
            ],
            "not": {
                "anyOf": [
                    {"required": ["material_preview_id"]},
                    {"required": ["material_preview_hash"]},
                    {"required": ["contract_hash"]},
                ]
            },
        },
        {
            "required": [
                "client_request_id",
                "session_id",
                "material_preview_id",
                "material_preview_hash",
                "package_review_preview_hash",
                "contract_hash",
                "construction_basis_hash",
                "reconciliation_record_id",
                "output_package_ids",
                "payload_hashes",
                "package_review_submit_record_ref",
                "package_review_state",
                "handoff_target",
                "export_mode",
                "operator_decision",
            ],
            "not": {
                "anyOf": [
                    {"required": ["analysis_plan_id"]},
                    {"required": ["pass_run_id"]},
                    {"required": ["preview_id"]},
                    {"required": ["preview_hash"]},
                    {"required": ["result_review_record_ref"]},
                    {"required": ["analysis_run_id"]},
                    {"required": ["payload_refs"]},
                    {"required": ["package_review_submit_schema_id"]},
                ]
            },
        },
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "contract_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "construction_basis_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "payload_refs": _string_array_or_string_map_schema(
            "List of payload refs or a mapping keyed by package kind or package id."
        ),
        "payload_hashes": _string_array_or_string_map_schema(
            "List of payload hashes or a mapping keyed by package kind or package id."
        ),
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string", "enum": ["package_review_approved"]},
        "package_review_submit_schema_id": {"type": "string"},
        "handoff_target": {"type": "string", "enum": ["internal_export_envelope", "mixed_source_review_package"]},
        "export_mode": {"type": "string", "enum": ["prepare_only", "reference_envelope_only"]},
        "operator_decision": {"type": "string", "enum": ["authorize_prepare", "hold", "decline", "blocked"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
        "aps_handoff": _forbidden_request_field_schema(),
        "dispatch": _forbidden_request_field_schema(),
        "send": _forbidden_request_field_schema(),
        "external_export": _forbidden_request_field_schema(),
        "external_target": _forbidden_request_field_schema(),
        "download": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "destination": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "connector_ref": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "active_package_authority_applied": _forbidden_request_field_schema(),
        "package_replacement_activation_id": _forbidden_request_field_schema(),
        "replacement_activation_basis_hash": _forbidden_request_field_schema(),
        "active_replacement_output_package_ids": _forbidden_request_field_schema(),
        "active_payload_refs": _forbidden_request_field_schema(),
        "active_payload_hashes": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "package_review_amendment": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
    },
}


APS_HANDOFF_DISPATCH_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "APS handoff dispatch accepts exactly one authority shape: selected-pass lifecycle authority "
        "or mixed-source material authority."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "operator_decision",
    ],
    "oneOf": [
        {
            "required": [
                "client_request_id",
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
                "aps_handoff_target",
                "dispatch_mode",
                "operator_decision",
            ],
            "not": {
                "anyOf": [
                    {"required": ["material_preview_id"]},
                    {"required": ["material_preview_hash"]},
                    {"required": ["contract_hash"]},
                    {"required": ["construction_basis_hash"]},
                ]
            },
        },
        {
            "required": [
                "client_request_id",
                "session_id",
                "material_preview_id",
                "material_preview_hash",
                "package_review_preview_hash",
                "contract_hash",
                "construction_basis_hash",
                "reconciliation_record_id",
                "output_package_ids",
                "payload_hashes",
                "package_review_submit_record_ref",
                "package_review_state",
                "prepare_record_ref",
                "handoff_export_state",
                "handoff_export_envelope_ref",
                "handoff_target",
                "export_mode",
                "aps_handoff_target",
                "dispatch_mode",
                "operator_decision",
            ],
            "not": {
                "anyOf": [
                    {"required": ["analysis_plan_id"]},
                    {"required": ["pass_run_id"]},
                    {"required": ["preview_id"]},
                    {"required": ["preview_hash"]},
                    {"required": ["result_review_record_ref"]},
                    {"required": ["analysis_run_id"]},
                    {"required": ["package_kinds"]},
                    {"required": ["payload_refs"]},
                ]
            },
        },
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "contract_hash": {"type": "string"},
        "construction_basis_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "package_kinds": {"type": "array", "items": {"type": "string"}},
        "payload_refs": _string_array_or_string_map_schema(
            "List of payload refs or a mapping keyed by package kind or package id."
        ),
        "payload_hashes": _string_array_or_string_map_schema(
            "List of payload hashes or a mapping keyed by package kind or package id."
        ),
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string", "enum": ["package_review_approved"]},
        "prepare_record_ref": {"type": "string"},
        "handoff_export_state": {"type": "string", "enum": ["handoff_export_prepared"]},
        "handoff_export_envelope_ref": {"type": "string"},
        "handoff_target": {"type": "string", "enum": ["internal_export_envelope", "mixed_source_review_package"]},
        "export_mode": {"type": "string", "enum": ["prepare_only", "reference_envelope_only"]},
        "aps_handoff_target": {"type": "string", "enum": ["aps_evidence_bundle", "mixed_source_aps_evidence_bundle"]},
        "dispatch_mode": {"type": "string", "enum": ["server_side_aps_handoff", "server_side_mixed_source_aps_handoff"]},
        "operator_decision": {"type": "string", "enum": ["dispatch_aps_handoff", "dispatch_mixed_source_aps_handoff"]},
        "decision_notes": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional mixed-source material-authority package kind guard; when provided it must be "
                "canonical_internal, user_facing, and review_facing in order."
            ),
        },
        "analysis_run_id": {"type": "string"},
        "external_export": _forbidden_request_field_schema(),
        "external_target": _forbidden_request_field_schema(),
        "download": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "destination": _forbidden_request_field_schema(),
        "destination_selector": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "dispatch": _forbidden_request_field_schema(),
        "send": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "package_review_amendment": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
    },
}


MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Mixed-source external export/download readiness accepts only material-authority lifecycle "
        "fields over an already recorded P18 mixed-source APS handoff dispatch. It records readiness "
        "only; delivery, download URLs, signed/public references, connector dispatch, and provider "
        "behavior are known but non-admitted."
    ),
    "required": [
        "client_request_id",
        "session_id",
        "material_preview_id",
        "material_preview_hash",
        "package_review_preview_hash",
        "contract_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "material_preview_id": {"type": "string"},
        "material_preview_hash": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "contract_hash": {"type": "string"},
        "construction_basis_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "payload_hashes": _string_array_or_string_map_schema(
            "List of payload hashes or a mapping keyed by package kind or package id."
        ),
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string", "enum": ["package_review_approved"]},
        "prepare_record_ref": {"type": "string"},
        "handoff_export_state": {"type": "string", "enum": ["handoff_export_prepared"]},
        "handoff_export_envelope_ref": {"type": "string"},
        "handoff_target": {"type": "string", "enum": ["mixed_source_review_package"]},
        "export_mode": {"type": "string", "enum": ["reference_envelope_only"]},
        "aps_handoff_target": {"type": "string", "enum": ["mixed_source_aps_evidence_bundle"]},
        "dispatch_mode": {"type": "string", "enum": ["server_side_mixed_source_aps_handoff"]},
        "aps_handoff_record_ref": {"type": "string"},
        "aps_handoff_state": {"type": "string", "enum": ["aps_handoff_dispatched"]},
        "operator_decision": {
            "type": "string",
            "enum": ["record_mixed_source_external_export_download_readiness"],
        },
        "decision_notes": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional mixed-source material-authority package kind guard; when provided it must be "
                "canonical_internal, user_facing, and review_facing in order."
            ),
        },
        "analysis_plan_id": _forbidden_request_field_schema(),
        "pass_run_id": _forbidden_request_field_schema(),
        "preview_id": _forbidden_request_field_schema(),
        "preview_hash": _forbidden_request_field_schema(),
        "result_review_record_ref": _forbidden_request_field_schema(),
        "analysis_run_id": _forbidden_request_field_schema(),
        "package_kinds": _forbidden_request_field_schema(),
        "payload_refs": _forbidden_request_field_schema(),
        "external_export": _forbidden_request_field_schema(),
        "external_target": _forbidden_request_field_schema(),
        "download": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_private_signed_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "destination": _forbidden_request_field_schema(),
        "destination_selector": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "dispatch": _forbidden_request_field_schema(),
        "send": _forbidden_request_field_schema(),
        "local_outbox": _forbidden_request_field_schema(),
        "outbox": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "package_review_amendment": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
    },
}


EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
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
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "package_kinds": {"type": "array", "items": {"type": "string"}},
        "payload_refs": _string_array_or_string_map_schema(
            "List of payload refs or a mapping keyed by package kind or package id."
        ),
        "payload_hashes": _string_array_or_string_map_schema(
            "List of payload hashes or a mapping keyed by package kind or package id."
        ),
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string", "enum": ["package_review_approved"]},
        "prepare_record_ref": {"type": "string"},
        "handoff_export_state": {"type": "string", "enum": ["handoff_export_prepared"]},
        "handoff_export_envelope_ref": {"type": "string"},
        "handoff_target": {"type": "string", "enum": ["internal_export_envelope"]},
        "export_mode": {"type": "string", "enum": ["prepare_only"]},
        "aps_handoff_record_ref": {"type": "string"},
        "aps_handoff_state": {"type": "string", "enum": ["aps_handoff_dispatched"]},
        "aps_handoff_target": {"type": "string", "enum": ["aps_evidence_bundle"]},
        "dispatch_mode": {"type": "string", "enum": ["server_side_aps_handoff"]},
        "aps_output_package_id": {"type": "string"},
        "aps_output_package_kind": {"type": "string", "enum": ["aps_evidence_bundle_handoff"]},
        "aps_bundle_ref": {"type": "string"},
        "aps_bundle_id": {"type": "string"},
        "aps_schema_id": {"type": "string"},
        "export_download_target": {"type": "string", "enum": ["aps_evidence_bundle_download_reference"]},
        "download_mode": {"type": "string", "enum": ["reference_only_prepare"]},
        "operator_decision": {"type": "string", "enum": ["prepare_external_export_download"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "aps_bundle_hash": {"type": "string"},
        "aps_bundle_size_bytes": {"type": "integer"},
        "download": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "download_token": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "local_file_path": _forbidden_request_field_schema(),
        "external_target": _forbidden_request_field_schema(),
        "destination": _forbidden_request_field_schema(),
        "destination_selector": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_dispatch": _forbidden_request_field_schema(),
        "generic_dispatch": _forbidden_request_field_schema(),
        "dispatch": _forbidden_request_field_schema(),
        "send": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "analysis_artifact": _forbidden_request_field_schema(),
        "artifact_manifest": _forbidden_request_field_schema(),
        "create_package": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "edited_findings": _forbidden_request_field_schema(),
        "result_review_amendment": _forbidden_request_field_schema(),
        "package_review_amendment": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "recover": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "selected_pass_ids": _forbidden_request_field_schema(),
        "pass_run_ids": _forbidden_request_field_schema(),
        "new_analysis_plan": _forbidden_request_field_schema(),
        "plan_revision": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "schema_migration": _forbidden_request_field_schema(),
    },
}


CONNECTOR_DATASET_HANDOFF_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["client_request_id", "session_id"],
    "properties": {
        "client_request_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
    },
}


CONNECTOR_DISPATCH_RECORD_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_state",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "external_export_download_record_ref",
        "external_export_download_state",
        "delivery_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "package_review_preview_hash": {"type": "string"},
        "output_package_ids": {"type": "array", "items": {"type": "string"}},
        "package_kinds": {"type": "array", "items": {"type": "string"}},
        "payload_refs": {"type": "array", "items": {"type": "string"}},
        "payload_hashes": {"type": "array", "items": {"type": "string"}},
        "package_review_submit_record_ref": {"type": "string"},
        "prepare_record_ref": {"type": "string"},
        "handoff_export_state": {"type": "string", "enum": ["handoff_export_prepared"]},
        "aps_handoff_record_ref": {"type": "string"},
        "aps_handoff_state": {"type": "string", "enum": ["aps_handoff_dispatched"]},
        "aps_handoff_target": {"type": "string", "enum": ["aps_evidence_bundle"]},
        "aps_output_package_id": {"type": "string"},
        "aps_output_package_kind": {"type": "string", "enum": ["aps_evidence_bundle_handoff"]},
        "aps_bundle_ref": {"type": "string"},
        "source_artifact_hash": {"type": "string"},
        "source_artifact_size_bytes": {"type": "integer"},
        "external_export_download_record_ref": {"type": "string"},
        "external_export_download_state": {"type": "string", "enum": ["external_export_download_prepared"]},
        "delivery_mode": {"type": "string", "enum": ["same_origin_artifact_stream"]},
        "operator_decision": {"type": "string", "enum": ["record_internal_connector_dispatch"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "external_export_download_descriptor_ref": {"type": "string"},
        "source_artifact_ref": {"type": "string"},
        "source_artifact_schema_id": {"type": "string"},
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_secret": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_secret": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "bucket": _forbidden_request_field_schema(),
        "object_key": _forbidden_request_field_schema(),
        "local_path": _forbidden_request_field_schema(),
        "local_file_path": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
    },
}


CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "external_export_download_record_ref",
        "external_export_download_state",
        "destination_target",
        "dispatch_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "external_export_download_state": {"type": "string", "enum": ["external_export_download_prepared"]},
        "destination_target": {"type": "string", "enum": ["layer3_internal_fake_local_destination_receipt"]},
        "dispatch_mode": {"type": "string", "enum": ["internal_fake_local_destination_receipt_only"]},
        "operator_decision": {"type": "string", "enum": ["record_internal_fake_local_destination_receipt"]},
        "decision_notes": {"type": "string"},
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_secret": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_secret": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "bucket": _forbidden_request_field_schema(),
        "object_key": _forbidden_request_field_schema(),
        "local_path": _forbidden_request_field_schema(),
        "local_file_path": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "credential": _forbidden_request_field_schema(),
        "credentials": _forbidden_request_field_schema(),
        "network_write": _forbidden_request_field_schema(),
        "external_connector_invocation": _forbidden_request_field_schema(),
        "destination_write": _forbidden_request_field_schema(),
        "real_destination_integration": _forbidden_request_field_schema(),
    },
}


SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "connector_local_destination_receipt_id",
        "connector_local_destination_receipt_state",
        "external_export_download_record_ref",
        "target_identity",
        "dispatch_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "connector_local_destination_receipt_id": {"type": "string"},
        "connector_local_destination_receipt_state": {
            "type": "string",
            "enum": ["connector_local_destination_receipt_recorded"],
        },
        "external_export_download_record_ref": {"type": "string"},
        "target_identity": {"type": "string", "enum": ["server_owned_local_delivery_outbox_destination"]},
        "dispatch_mode": {"type": "string", "enum": ["single_named_destination_dispatch_fake_target_first"]},
        "operator_decision": {"type": "string", "enum": ["record_server_owned_local_outbox_fake_target"]},
        "decision_notes": {"type": "string"},
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_run_target_id": _forbidden_request_field_schema(),
        "connector_secret": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_path": _forbidden_request_field_schema(),
        "destination_secret": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_public_delivery": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "bucket": _forbidden_request_field_schema(),
        "object_key": _forbidden_request_field_schema(),
        "local_path": _forbidden_request_field_schema(),
        "local_file_path": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "credential": _forbidden_request_field_schema(),
        "credentials": _forbidden_request_field_schema(),
        "network_write": _forbidden_request_field_schema(),
        "external_connector_invocation": _forbidden_request_field_schema(),
        "destination_write": _forbidden_request_field_schema(),
        "real_destination_integration": _forbidden_request_field_schema(),
        "auth_policy": _forbidden_request_field_schema(),
        "security_override": _forbidden_request_field_schema(),
        "frontend_durable_authority": _forbidden_request_field_schema(),
        "full_mockup_activation": _forbidden_request_field_schema(),
    },
}


SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "connector_local_destination_receipt_id",
        "server_owned_local_outbox_target_receipt_id",
        "server_owned_local_outbox_target_state",
        "external_export_download_record_ref",
        "target_identity",
        "dispatch_mode",
        "operator_decision",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "connector_local_destination_receipt_id": {"type": "string"},
        "server_owned_local_outbox_target_receipt_id": {"type": "string"},
        "server_owned_local_outbox_target_state": {
            "type": "string",
            "enum": ["server_owned_local_outbox_fake_target_recorded"],
        },
        "external_export_download_record_ref": {"type": "string"},
        "target_identity": {"type": "string", "enum": ["server_owned_local_delivery_outbox_destination"]},
        "dispatch_mode": {"type": "string", "enum": ["server_owned_local_outbox_write_via_storage_dir"]},
        "operator_decision": {"type": "string", "enum": ["write_server_owned_local_outbox"]},
        "decision_notes": {"type": "string"},
        "connector_key": _forbidden_request_field_schema(),
        "connector_run_id": _forbidden_request_field_schema(),
        "connector_run_target_id": _forbidden_request_field_schema(),
        "connector_secret": _forbidden_request_field_schema(),
        "destination_id": _forbidden_request_field_schema(),
        "destination_path": _forbidden_request_field_schema(),
        "destination_secret": _forbidden_request_field_schema(),
        "destination_url": _forbidden_request_field_schema(),
        "provider_url": _forbidden_request_field_schema(),
        "provider_public_url": _forbidden_request_field_schema(),
        "provider_public_delivery": _forbidden_request_field_schema(),
        "public_url": _forbidden_request_field_schema(),
        "signed_url": _forbidden_request_field_schema(),
        "download_url": _forbidden_request_field_schema(),
        "bucket": _forbidden_request_field_schema(),
        "object_key": _forbidden_request_field_schema(),
        "local_path": _forbidden_request_field_schema(),
        "local_file_path": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
        "rebuild_package": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "source_upload": _forbidden_request_field_schema(),
        "source_expansion": _forbidden_request_field_schema(),
        "local_directory": _forbidden_request_field_schema(),
        "rag_vector_index": _forbidden_request_field_schema(),
        "runtime_db_write": _forbidden_request_field_schema(),
        "retry": _forbidden_request_field_schema(),
        "rerun": _forbidden_request_field_schema(),
        "cancel": _forbidden_request_field_schema(),
        "hybrid_execution": _forbidden_request_field_schema(),
        "rag_execution": _forbidden_request_field_schema(),
        "hidden_llm_planning": _forbidden_request_field_schema(),
        "credential": _forbidden_request_field_schema(),
        "credentials": _forbidden_request_field_schema(),
        "network_write": _forbidden_request_field_schema(),
        "external_connector_invocation": _forbidden_request_field_schema(),
        "destination_write": _forbidden_request_field_schema(),
        "real_destination_integration": _forbidden_request_field_schema(),
        "auth_policy": _forbidden_request_field_schema(),
        "security_override": _forbidden_request_field_schema(),
        "frontend_durable_authority": _forbidden_request_field_schema(),
        "full_mockup_activation": _forbidden_request_field_schema(),
    },
}




LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_FORBIDDEN_REQUEST_FIELDS = tuple(
    sorted(layer3_local_outbox_provider_private_handoff.LOCAL_OUTBOX_PROVIDER_PRIVATE_FORBIDDEN_FIELDS)
)

LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_PREPARE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "connector_dispatch_record_ref",
        "connector_local_destination_receipt_id",
        "server_owned_local_outbox_target_receipt_id",
        "server_owned_local_outbox_write_receipt_id",
        "external_export_download_record_ref",
        "target_identity",
        "dispatch_mode",
        "operator_decision",
        "recipient_scope",
    ],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "connector_local_destination_receipt_id": {"type": "string"},
        "server_owned_local_outbox_target_receipt_id": {"type": "string"},
        "server_owned_local_outbox_write_receipt_id": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "target_identity": {
            "type": "string",
            "enum": [
                layer3_local_outbox_provider_private_handoff.LOCAL_OUTBOX_PROVIDER_PRIVATE_TARGET_IDENTITY
            ],
        },
        "dispatch_mode": {
            "type": "string",
            "enum": [
                layer3_local_outbox_provider_private_handoff.LOCAL_OUTBOX_PROVIDER_PRIVATE_DISPATCH_MODE
            ],
        },
        "operator_decision": {
            "type": "string",
            "enum": [
                layer3_local_outbox_provider_private_handoff.LOCAL_OUTBOX_PROVIDER_PRIVATE_OPERATOR_DECISION
            ],
        },
        "recipient_scope": {"type": "string"},
        "requested_ttl_seconds": {"type": "integer", "minimum": 1},
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_FORBIDDEN_REQUEST_FIELDS
        },
    },
}


EXTERNAL_LOCAL_EXPORT_FORBIDDEN_REQUEST_FIELDS = tuple(
    sorted(layer3_external_local_export.EXTERNAL_LOCAL_EXPORT_FORBIDDEN_FIELDS)
)

EXTERNAL_LOCAL_EXPORT_WRITE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-configured external local export directory write from durable local outbox authority. "
        "The caller supplies only receipt and authority refs; destination paths, URLs, credentials, "
        "connector runs, package mutation, source expansion, and RAG/vector fields are not admitted."
    ),
    "required": sorted(layer3_external_local_export.EXTERNAL_LOCAL_EXPORT_REQUIRED_FIELDS),
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "connector_local_destination_receipt_id": {"type": "string"},
        "server_owned_local_outbox_target_receipt_id": {"type": "string"},
        "server_owned_local_outbox_write_receipt_id": {"type": "string"},
        "provider_private_handoff_receipt_id": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "target_identity": {
            "type": "string",
            "enum": [layer3_external_local_export.EXTERNAL_LOCAL_EXPORT_TARGET_IDENTITY],
        },
        "dispatch_mode": {
            "type": "string",
            "enum": [layer3_external_local_export.EXTERNAL_LOCAL_EXPORT_DISPATCH_MODE],
        },
        "operator_decision": {
            "type": "string",
            "enum": [layer3_external_local_export.EXTERNAL_LOCAL_EXPORT_OPERATOR_DECISION],
        },
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in EXTERNAL_LOCAL_EXPORT_FORBIDDEN_REQUEST_FIELDS
        },
    },
}


INTERNAL_WEBHOOK_DISPATCH_FORBIDDEN_REQUEST_FIELDS = tuple(
    sorted(layer3_internal_webhook_connector.INTERNAL_WEBHOOK_FORBIDDEN_FIELDS)
)

INTERNAL_WEBHOOK_DISPATCH_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": (
        "Server-configured internal webhook dispatch from durable local outbox authority. "
        "The caller supplies only receipt and authority refs; destination URLs, provider URLs, "
        "raw local paths, package payloads, package bytes, credentials, tokens, arbitrary headers, "
        "connector targets, retries, source expansion, RAG/vector input, optional-tool input, and "
        "auth/security overrides are not admitted."
    ),
    "required": sorted(layer3_internal_webhook_connector.INTERNAL_WEBHOOK_REQUIRED_FIELDS),
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "reconciliation_record_id": {"type": "string"},
        "connector_dispatch_record_ref": {"type": "string"},
        "connector_local_destination_receipt_id": {"type": "string"},
        "server_owned_local_outbox_target_receipt_id": {"type": "string"},
        "server_owned_local_outbox_write_receipt_id": {"type": "string"},
        "external_export_download_record_ref": {"type": "string"},
        "target_identity": {
            "type": "string",
            "enum": [layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TARGET_IDENTITY],
        },
        "target_class": {
            "type": "string",
            "enum": [layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TARGET_CLASS],
        },
        "dispatch_mode": {
            "type": "string",
            "enum": [layer3_internal_webhook_connector.INTERNAL_WEBHOOK_DISPATCH_MODE],
        },
        "operator_decision": {
            "type": "string",
            "enum": [layer3_internal_webhook_connector.INTERNAL_WEBHOOK_OPERATOR_DECISION],
        },
        "decision_notes": {"type": "string"},
        **{
            field: _forbidden_request_field_schema()
            for field in INTERNAL_WEBHOOK_DISPATCH_FORBIDDEN_REQUEST_FIELDS
        },
    },
}




# ---------------------------------------------------------------------------
# Response-wrapping helpers
# ---------------------------------------------------------------------------

def _json_or_error(handler: Callable[[], dict[str, Any]]) -> dict[str, Any] | JSONResponse:
    try:
        return handler()
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )


def _companyfacts_stage_error_response(exc: SecXbrlCompanyfactsStageError) -> JSONResponse:
    """Map SecXbrlCompanyfactsStageError to a governed 409 envelope (never a raw 500)."""
    return JSONResponse(
        status_code=409,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=409,
                blocked_fields=[],
                next_allowed_actions=["inspect_sec_xbrl_offline_evidence_storage"],
            )
        ),
    )


def _json_or_error_with_companyfacts_stage(
    handler: Callable[[], dict[str, Any]],
) -> dict[str, Any] | JSONResponse:
    """Like _json_or_error but also maps SecXbrlCompanyfactsStageError to a governed 4xx."""
    try:
        return handler()
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )
    except SecXbrlCompanyfactsStageError as exc:
        return _companyfacts_stage_error_response(exc)


def _sec_xbrl_operator_review_workflow_error_response(
    exc: layer3_sec_xbrl_operator_review_workflow.SecXbrlOperatorReviewWorkflowError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[str(field) for field in exc.details.get("required_any_of", [])],
                next_allowed_actions=["inspect_existing_sec_xbrl_operator_review_workflow_authority"],
            )
        ),
    )


def _sec_xbrl_staged_evidence_loader_error_response(
    exc: layer3_sec_xbrl_offline_evidence_loader.SecXbrlOfflineEvidenceLoaderError,
) -> JSONResponse:
    http_status = 404 if exc.code.endswith("_missing") else 409
    return JSONResponse(
        status_code=http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=http_status,
                blocked_fields=[],
                next_allowed_actions=["inspect_sec_xbrl_offline_evidence_storage"],
            )
        ),
    )


def _sec_xbrl_staged_evidence_orchestrator_error_response(
    exc: layer3_sec_xbrl_e2e_offline_orchestrator.SecXbrlE2EOfflineOrchestratorError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=409,
                blocked_fields=[],
                next_allowed_actions=["inspect_sec_xbrl_offline_evidence_storage"],
            )
        ),
    )


def _sec_xbrl_staged_evidence_persistence_error_response(
    exc: (
        layer3_sec_xbrl_projection_persistence.SecXbrlProjectionPersistenceError
        | layer3_sec_xbrl_statement_packet_persistence.SecXbrlStatementPacketPersistenceError
        | layer3_sec_xbrl_e2e_integration.SecXbrlE2EIntegrationError
    ),
) -> JSONResponse:
    http_status = getattr(exc, "http_status", 409)
    return JSONResponse(
        status_code=http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=http_status,
                blocked_fields=[],
                next_allowed_actions=["inspect_sec_xbrl_offline_evidence_storage"],
            )
        ),
    )


def _sec_xbrl_full_pipeline_orchestrator_error_response(
    exc: layer3_sec_xbrl_full_pipeline_orchestrator.SecXbrlFullPipelineOrchestratorError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.error_code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[],
                next_allowed_actions=["inspect_sec_xbrl_full_pipeline_orchestrator_error"],
            )
        ),
    )


def _sec_xbrl_value_reveal_authority_error_response(
    exc: layer3_sec_xbrl_value_reveal_authority.SecXbrlValueRevealAuthorityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(field)
                    for field in exc.details.get("required_any_of", exc.details.get("blocked_keys", []))
                ],
                next_allowed_actions=["inspect_existing_sec_xbrl_operator_review_decision_authority"],
            )
        ),
    )


def _sec_xbrl_controlled_value_reveal_submit_error_response(
    exc: layer3_sec_xbrl_controlled_value_reveal_submit.SecXbrlControlledValueRevealSubmitError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(field)
                    for field in exc.details.get("required_any_of", exc.details.get("blocked_keys", []))
                ],
                next_allowed_actions=["prepare_sec_xbrl_value_reveal_authority"],
            )
        ),
    )


SecXbrlInAppAuthPolicyError = layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError


def _route_level_operator_identity(request: Request, *, access: str = "write") -> dict[str, Any]:
    return layer3_sec_xbrl_in_app_auth_policy.route_level_operator_authorization_required(
        {str(key): str(value) for key, value in request.headers.items()},
        access=access,
    )


def _sec_xbrl_auth_policy_error_response(
    exc: (
        layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError
        | layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError
    ),
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(field)
                    for field in exc.details.get(
                        "blocked_fields",
                        exc.details.get("mismatched_fields", []),
                    )
                ],
                next_allowed_actions=["inspect_existing_sec_xbrl_auth_binding_authority"],
            )
        ),
    )


def _sec_xbrl_policy_request_fields(payload: BaseModel) -> dict[str, Any]:
    return {
        **payload.model_dump(exclude_none=True),
        **dict(payload.model_extra or {}),
    }


def _sec_xbrl_policy_decision(
    request: Request,
    payload: BaseModel,
    *,
    route_family: str,
    requested_role: str = layer3_sec_xbrl_in_app_auth_policy.OWNER_ROLE,
) -> dict[str, Any]:
    return layer3_sec_xbrl_in_app_auth_policy.authorize_sec_xbrl_route(
        headers={str(key): str(value) for key, value in request.headers.items()},
        route_family=route_family,
        requested_role=requested_role,
        request_fields=_sec_xbrl_policy_request_fields(payload),
    )


def _sec_xbrl_binding_request_id(client_request_id: str, route_family: str) -> str:
    return layer3_sec_xbrl_in_app_auth_policy.binding_client_request_id(
        client_request_id=client_request_id,
        route_family=route_family,
    )


def _sec_xbrl_require_binding(
    db: Session,
    *,
    source_receipt_kind: str,
    route_family: str,
    policy_decision: dict[str, Any],
    source_receipt_id: str | None = None,
    source_receipt_basis_hash: str | None = None,
) -> dict[str, Any]:
    return layer3_sec_xbrl_auth_binding.require_sec_xbrl_owner_binding(
        db,
        source_receipt_kind=source_receipt_kind,
        source_receipt_id=source_receipt_id,
        source_receipt_basis_hash=source_receipt_basis_hash,
        route_family=route_family,
        policy_decision=policy_decision,
    )


def _sec_xbrl_record_binding(
    db: Session,
    *,
    client_request_id: str,
    source_receipt_kind: str,
    source_receipt_id: str,
    source_receipt_basis_hash: str,
    route_family: str,
    policy_decision: dict[str, Any],
    commit: bool = True,
) -> dict[str, Any]:
    return layer3_sec_xbrl_auth_binding.record_sec_xbrl_auth_binding(
        db,
        client_request_id=_sec_xbrl_binding_request_id(client_request_id, route_family),
        source_receipt_kind=source_receipt_kind,
        source_receipt_id=source_receipt_id,
        source_receipt_basis_hash=source_receipt_basis_hash,
        route_family=route_family,
        policy_decision=policy_decision,
        commit=commit,
    )


def _sec_xbrl_commit_bound_receipts(db: Session) -> None:
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_atomic_commit_failed",
            "SEC XBRL source receipt and auth binding receipt commit failed as one transaction.",
            http_status=409,
        ) from exc


def _sec_xbrl_auth_binding_projection(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "auth_binding_ref": binding["auth_binding_ref"],
        "auth_binding_basis_hash": binding["binding_basis_hash"],
        "auth_binding_route_family": binding["route_family"],
        "auth_binding_policy_hash": binding["policy_hash"],
        "auth_binding_role": binding["role"],
        "auth_binding_required": True,
    }


def _candidate_b_policy_request_context(request: Request) -> dict[str, str]:
    return {str(key): str(value) for key, value in request.headers.items()}


def _candidate_b_policy_json_or_error(
    request: Request,
    handler: Callable[[], dict[str, Any]],
) -> dict[str, Any] | JSONResponse:
    try:
        with layer3_candidate_b_operator_workflow_access_policy.request_context(
            _candidate_b_policy_request_context(request),
        ):
            return handler()
    except (
        layer3_candidate_b_operator_workflow_access_policy.CandidateBOperatorWorkflowAccessPolicyError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


async def _payload_from_request(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").lower()
    if "application/x-www-form-urlencoded" in content_type:
        raw = (await request.body()).decode("utf-8")
        payload: dict[str, Any] = {}
        for key, value in parse_qsl(raw, keep_blank_values=True):
            try:
                payload[key] = json.loads(value)
            except json.JSONDecodeError:
                payload[key] = value
        return payload
    try:
        parsed = await request.json()
    except json.JSONDecodeError as exc:
        raise Layer3WorkbenchError(
            "invalid_layer3_request_json",
            "Request body must be valid JSON.",
        ) from exc
    if not isinstance(parsed, dict):
        raise Layer3WorkbenchError(
            "invalid_layer3_request_json",
            "Request body must be a JSON object.",
        )
    return parsed




# ---------------------------------------------------------------------------
# Pipeline input-sanitization helpers
# ---------------------------------------------------------------------------

_FULL_PIPELINE_FORBIDDEN_MARKERS = ("/archives/", "sec.gov", "https://", "http://")


def _full_pipeline_contains_forbidden_marker(obj: Any) -> bool:
    """True if the JSON-serialized object contains any forbidden raw-reference marker
    (SEC URL host, scheme, or filing-archive path). Case-insensitive substring scan."""
    serialized = json.dumps(obj, default=str).lower()
    return any(marker in serialized for marker in _FULL_PIPELINE_FORBIDDEN_MARKERS)
