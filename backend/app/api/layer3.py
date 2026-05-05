from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import layer3_workbench
from app.services.layer3_workbench import Layer3WorkbenchError

router = APIRouter()


class Layer3BaseResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str
    schema_version: int
    request_id: str
    server_time: str
    status: str


class Layer3WorkbenchBootstrapResponse(Layer3BaseResponse):
    route: str
    api_root: str
    supported_source_classes: list[str]
    preview_only_source_classes: list[str]
    unsupported_source_classes: list[str]
    gate_labels: list[str]
    active_gate_labels: list[str]
    unavailable_gate_labels: list[str]
    state_action_contract: dict[str, Any]
    features: dict[str, bool]
    execution_readiness: dict[str, Any]
    authority_rail: dict[str, Any]


class Layer3ExecutionReadinessResponse(Layer3BaseResponse):
    execution_admitted: bool
    execution_enabled: bool
    execution_selection_admitted: bool
    execution_selection_endpoint: str
    analysis_execution_admitted: bool
    analysis_execution_start_admitted: bool
    analysis_execution_start_endpoint: str
    execution_result_status_admitted: bool
    execution_result_status_endpoint: str
    execution_result_review_admitted: bool
    execution_result_review_endpoint: str
    package_review_preview_admitted: bool
    package_review_preview_endpoint: str
    package_construction_commit_admitted: bool
    package_construction_commit_endpoint: str
    package_review_submit_admitted: bool
    package_review_submit_endpoint: str
    handoff_export_prepare_admitted: bool
    handoff_export_prepare_endpoint: str
    aps_handoff_dispatch_admitted: bool
    aps_handoff_dispatch_endpoint: str
    external_export_download_prepare_admitted: bool
    external_export_download_prepare_endpoint: str
    external_export_download_deliver_admitted: bool
    external_export_download_deliver_endpoint: str
    package_review_admitted: bool
    external_handoff_admitted: bool
    external_export_admitted: bool
    dispatch_admitted: bool
    readiness_state: str
    required_gates: list[str]
    implemented_gates: list[str]
    deferred_gates: list[str]
    state_model: dict[str, Any]
    state_action_contract: dict[str, Any]
    preview_hash_contract: dict[str, Any]
    material_preview_hash_contract: dict[str, Any]
    idempotency_contract: dict[str, Any]
    concurrency_contract: dict[str, Any]
    deferred_decisions: dict[str, Any]


class Layer3PlanApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str
    preview_id: str
    preview_hash: str
    operator_confirmation: bool
    approval_scope: str | None = None


class Layer3GateBDecisionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    decision: str
    operator_reason: str | None = None
    decision_basis: dict[str, Any] | None = None


class Layer3GateBDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    preflight_id: str | None = None
    source_set_id: str | None = None
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    actor: str | None = None
    candidate_decisions: list[Layer3GateBDecisionItem]
    commit_reason: str | None = None


class Layer3GateCPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    session_id: str
    commit_typing: bool | None = None
    actor: str | None = None


class Layer3ExecutionSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    operator_reason: str | None = None
    execute: Any | None = None
    execution: Any | None = None
    run: Any | None = None
    run_analysis: Any | None = None
    start_execution: Any | None = None
    analysis_run_id: Any | None = None
    analysis_run_ids: Any | None = None
    result_review: Any | None = None
    results: Any | None = None
    package: Any | None = None
    package_review: Any | None = None
    handoff: Any | None = None
    artifact_manifest: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_plan: Any | None = None


class Layer3PlanRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    operator_decision: str | None = None
    operator_note: str | None = None
    execute: Any | None = None
    execution: Any | None = None
    run: Any | None = None
    run_analysis: Any | None = None
    package: Any | None = None
    package_review: Any | None = None
    handoff: Any | None = None
    plan_edits: Any | None = None
    natural_language_plan: Any | None = None
    llm_plan: Any | None = None
    execution_started: Any | None = None
    create_pass_runs: Any | None = None
    pass_run_ids: Any | None = None
    artifact_manifest: Any | None = None
    result_review: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_plan: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None


class Layer3AnalysisExecutionStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    execution_mode: str | None = None
    operator_reason: str | None = None
    run_all: Any | None = None
    batch: Any | None = None
    package: Any | None = None
    package_review: Any | None = None
    handoff: Any | None = None
    result_review: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_plan: Any | None = None
    approved_plan_supersession: Any | None = None
    schema_migration: Any | None = None
    artifact_manifest: Any | None = None
    results: Any | None = None
    source_expansion: Any | None = None
    schema_widening: Any | None = None


class Layer3ExecutionResultStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    analysis_run_id: str | None = None
    operator_view_mode: str | None = None
    approve_result: Any | None = None
    reject_result: Any | None = None
    result_review: Any | None = None
    result_decision: Any | None = None
    edited_findings: Any | None = None
    package: Any | None = None
    package_review: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    cancel: Any | None = None
    run_all: Any | None = None
    batch: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_plan: Any | None = None
    approved_plan_supersession: Any | None = None
    schema_migration: Any | None = None
    runtime_db_write: Any | None = None


class Layer3PreflightResponse(Layer3BaseResponse):
    preflight_id: str
    normalized_intent: dict[str, Any]
    blockers: list[Any]
    warnings: list[Any]
    eligible_for_source_selection: bool
    authority_rail: dict[str, Any]


class Layer3SourcePreviewResponse(Layer3BaseResponse):
    source_set_id: str
    source_candidates: list[dict[str, Any]]
    unsupported_sources: list[Any]
    authority_rail: dict[str, Any]


class Layer3MaterialPreviewResponse(Layer3BaseResponse):
    material_preview_id: str
    material_preview_hash: str
    material_candidates: list[dict[str, Any]]
    partial_retrieval: bool
    authority_rail: dict[str, Any]


class Layer3DatasetVersionCandidatesResponse(Layer3BaseResponse):
    dataset_version_candidates: list[dict[str, Any]]
    candidate_count: int
    source_system: str
    source_family_summary: dict[str, Any]
    authority_rail: dict[str, Any]


class Layer3ApsContentDocumentCandidatesResponse(Layer3BaseResponse):
    aps_content_document_candidates: list[dict[str, Any]]
    candidate_count: int
    source_system: str
    authority_rail: dict[str, Any]


class Layer3GateBDecisionResponse(Layer3BaseResponse):
    session_id: str
    selection_manifest_id: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    approved_candidate_ids: list[str]
    denied_candidate_ids: list[str]
    isolated_candidate_ids: list[str]
    flagged_candidate_ids: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3GateCPreviewResponse(Layer3BaseResponse):
    session_id: str
    typing_records: list[dict[str, Any]]
    analysis_units: list[dict[str, Any]]
    analysis_groups: list[dict[str, Any]]
    analysis_sets: list[dict[str, Any]]
    unsupported_material: list[dict[str, Any]]
    override_allowed: bool
    next_state: str
    authority_rail: dict[str, Any]


class Layer3TypingOverrideUnavailableResponse(Layer3BaseResponse):
    error_code: str
    message: str
    recoverable: bool
    next_allowed_actions: list[str]


class Layer3PlanPreviewResponse(Layer3BaseResponse):
    session_id: str
    next_state: str
    preview_id: str
    preview_hash: str
    preview_identity: dict[str, Any]
    preview_only: bool
    authority_rail: dict[str, Any]
    plan_preview: dict[str, Any]


class Layer3PlanApprovalResponse(Layer3BaseResponse):
    session_id: str
    next_state: str
    approval_only: bool
    execution_started: bool
    analysis_plan_id: str
    plan_status: str
    approved_by_operator: bool
    approved_at: str | None
    authority_rail: dict[str, Any]
    approved_plan: dict[str, Any]


class Layer3PlanRevisionResponse(Layer3BaseResponse):
    session_id: str
    next_state: str
    revision_control_only: bool
    execution_started: bool
    source_preview_id: str
    source_preview_hash: str
    operator_decision: str
    operator_note_recorded: bool
    authority_rail: dict[str, Any]
    downstream_unavailable: list[str]
    plan_revision_control: dict[str, Any]


class Layer3ExecutionSelectionResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    preview_identity: dict[str, Any]
    pass_run_ids: list[str]
    pass_run_count: int
    execution_started: bool
    analysis_run_ids: list[str]
    pass_run_statuses: dict[str, str]
    downstream_unavailable: list[str]
    next_state: str


class Layer3AnalysisExecutionStartResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    execution_started: bool
    analysis_run_id: str | None
    pass_run_status: str
    output_payload_ref: str | None
    downstream_unavailable: list[str]
    next_state: str
    engine_family: str | None
    selected_method_name: str | None
    dataset_version_id: str | None


class Layer3ExecutionResultStatusResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    execution_started: bool
    analysis_run_id: str | None
    analysis_run_status: str | None
    pass_run_status: str
    output_payload_ref: str | None
    output_metadata_summary: dict[str, Any] | None
    output_metadata_error: str | None
    warnings_present: bool
    error_present: bool
    error_message: str | None
    result_status_available: bool
    result_review_enabled: bool
    package_review_enabled: bool
    handoff_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    operator_view_mode: str
    engine_family: str | None
    selected_method_name: str | None
    dataset_version_id: str | None


class Layer3ExecutionResultReviewResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_status_available: bool
    result_review_enabled: bool
    review_state: str
    operator_decision: str
    review_record_ref: str
    trace_summary: dict[str, Any]
    reviewed_output_items: list[dict[str, Any]]
    unresolved_trace_count: int
    package_review_enabled: bool
    handoff_enabled: bool
    downstream_unavailable: list[str]
    review_notes_recorded: bool
    engine_family: str | None
    pass_type: str | None = None
    pass_scope: str | None = None
    selected_method_name: str | None = None
    source_gate: str | None = None
    source_dataset_version_ids: list[str] | None = None
    cohort_shape: str | None = None


class Layer3PackageReviewPreviewResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    package_review_preview_hash: str
    analysis_run_id: str | None
    result_status_available: bool
    result_review_state: str | None
    result_review_record_ref: str | None
    package_review_preview_enabled: bool
    package_commit_enabled: bool
    package_review_enabled: bool
    candidate_package_kinds: list[dict[str, Any]]
    package_owner_compatibility: dict[str, Any]
    blocked_reasons: list[str]
    downstream_unavailable: list[str]
    next_state: str
    output_metadata_summary: dict[str, Any]
    trace_summary: dict[str, Any] | None
    reviewed_output_item_summary: dict[str, Any] | None = None
    unresolved_trace_count: int
    pass_type: str | None = None
    pass_scope: str | None = None
    selected_method_name: str | None = None
    source_gate: str | None = None
    source_dataset_version_ids: list[str] | None = None
    cohort_shape: str | None = None
    authority_rail: dict[str, Any]


class Layer3PackageConstructionCommitResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    pass_scope: str | None = None
    method: str | None = None
    source_gate: str | None = None
    package_construction_source_gate: str | None = None
    source_shape: str | None = None
    source_dataset_version_ids: list[str] | None = None
    reviewed_output_item_summary: dict[str, Any] | None = None
    package_review_submit_enabled: bool
    handoff_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3PackageReviewSubmitResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    reconciliation_record_id: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    operator_decision: str
    decision_notes: str | None
    package_review_state: str
    submit_record_ref: str
    package_review_submit_enabled: bool
    handoff_enabled: bool
    export_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3HandoffExportPrepareResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    reconciliation_record_id: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    pass_type: str | None = None
    pass_scope: str | None = None
    method: str | None = None
    source_gate: str | None = None
    package_construction_source_gate: str | None = None
    source_shape: str | None = None
    source_dataset_version_ids: list[str] | None = None
    package_review_submit_schema_id: str | None = None
    package_review_submit_record_ref: str
    package_review_state: str
    operator_decision: str
    decision_notes: str | None
    handoff_export_state: str
    handoff_target: str
    export_mode: str
    external_handoff_enabled: bool
    external_export_enabled: bool
    dispatch_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    prepare_record_ref: str
    handoff_export_envelope: dict[str, Any] | None = None
    authority_rail: dict[str, Any]


class Layer3ApsHandoffDispatchResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    reconciliation_record_id: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    pass_type: str | None = None
    pass_scope: str | None = None
    method: str | None = None
    source_gate: str | None = None
    package_construction_source_gate: str | None = None
    source_shape: str | None = None
    source_dataset_version_ids: list[str] | None = None
    package_review_submit_schema_id: str | None = None
    package_review_submit_record_ref: str
    package_review_state: str
    prepare_record_ref: str
    handoff_export_state: str
    handoff_export_envelope_ref: str
    handoff_target: str
    export_mode: str
    aps_handoff_target: str
    dispatch_mode: str
    operator_decision: str
    decision_notes: str | None
    aps_handoff_state: str
    aps_handoff_record_ref: str
    aps_output_package_id: str
    aps_output_package_kind: str
    aps_bundle_ref: str
    aps_bundle_id: str
    aps_schema_id: str
    source_package_refs: dict[str, str]
    source_package_hashes: dict[str, str]
    external_export_enabled: bool
    download_enabled: bool
    connector_dispatch_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ExternalExportDownloadPrepareResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    reconciliation_record_id: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    package_review_submit_record_ref: str
    package_review_state: str
    prepare_record_ref: str
    handoff_export_state: str
    handoff_export_envelope_ref: str
    handoff_target: str
    export_mode: str
    aps_handoff_record_ref: str
    aps_handoff_state: str
    aps_handoff_target: str
    dispatch_mode: str
    aps_output_package_id: str
    aps_output_package_kind: str
    aps_bundle_ref: str
    aps_bundle_id: str
    aps_schema_id: str
    export_download_target: str
    download_mode: str
    operator_decision: str
    decision_notes: str | None
    external_export_download_state: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    source_artifact_ref: str
    source_artifact_schema_id: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    browser_download_enabled: bool
    download_url_enabled: bool
    connector_dispatch_enabled: bool
    destination_selection_enabled: bool
    generic_downstream_dispatch_enabled: bool
    downstream_unavailable: list[str]
    delivery_ui: dict[str, Any] | None = None
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ExternalExportDownloadSignedReferenceResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    reconciliation_record_id: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    signed_reference_state: str
    signed_reference_token: str
    signed_reference_token_id: str
    signed_reference_token_prefix: str
    signed_reference_receipt_id: str
    signed_reference_replay_policy: str
    signed_reference_use_count: int
    signed_reference_max_use_count: int
    signed_reference_revoked: bool
    signed_reference_audit_event_id: str
    signed_reference_expires_at: str
    signed_reference_expires_in_seconds: int
    signed_reference_use_endpoint: str
    delivery_mode: str
    server_authority: str
    source_artifact_ref: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    pass_type: str
    pass_scope: str
    method: str
    source_gate: str
    source_shape: str
    source_dataset_version_ids: list[str]
    public_url_enabled: bool
    external_object_store_url_enabled: bool
    connector_dispatch_enabled: bool
    destination_selection_enabled: bool
    generic_downstream_dispatch_enabled: bool
    package_mutation_enabled: bool
    schema_runtime_source_widening_enabled: bool
    authority_rail: dict[str, Any]
    next_state: str


class Layer3WorkbenchErrorResponse(Layer3BaseResponse):
    error_code: str
    message: str
    recoverable: bool
    blocked_fields: list[str]
    next_allowed_actions: list[str]


def _workbench_error_responses(*statuses: int) -> dict[int, dict[str, type[Layer3WorkbenchErrorResponse]]]:
    return {status: {"model": Layer3WorkbenchErrorResponse} for status in statuses}


def _string_array_or_string_map_schema(description: str) -> dict[str, Any]:
    return {
        "oneOf": [
            {"type": "array", "items": {"type": "string"}},
            {"type": "object", "additionalProperties": {"type": "string"}},
        ],
        "description": description,
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


EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_BODY: dict[str, Any] = {
    "required": True,
    "content": {
        "application/json": {"schema": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA},
        "application/x-www-form-urlencoded": {"schema": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORM_REQUEST_SCHEMA},
    },
}


EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA: dict[str, Any] = {
    **EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_SCHEMA,
    "description": (
        "Server-owned same-origin signed delivery reference generation uses the existing validated "
        "external export/download delivery authority payload."
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


def _json_request_body(schema: dict[str, Any]) -> dict[str, Any]:
    return {"required": True, "content": {"application/json": {"schema": schema}}}


SOURCE_CLASS_SCHEMA: dict[str, Any] = {
    "type": "string",
    "enum": ["dataset_version", "aps_content_document"],
}


PREFLIGHT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "description": "Known preflight fields; current runtime tolerates extra metadata fields.",
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
            },
        },
        "actor": {"type": "string"},
    },
}


SOURCE_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "description": "Known source-preview fields; selected_source_classes defaults to supported source classes.",
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
    "additionalProperties": True,
    "description": "Known material-preview fields; preflight/source-set ids are carried as authority context.",
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
            },
        },
    },
}


GATE_B_DECISION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict Gate B fields; denied, isolated, and flagged decisions require operator_reason at runtime.",
    "required": ["candidate_decisions"],
    "properties": {
        "schema_id": {"type": "string", "enum": ["layer3.gate_b_decision_request.v1"]},
        "schema_version": {"type": "integer", "enum": [1]},
        "client_request_id": {"type": "string"},
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
    "additionalProperties": True,
    "required": ["session_id"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "preview_scope": {"type": "string", "enum": ["owner_service_default"]},
        "include_exclusions": {"type": "boolean"},
    },
}


PLAN_APPROVAL_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict plan-approval fields; extra execution/package/handoff fields are rejected before service mutation.",
    "required": ["session_id", "preview_id", "preview_hash", "operator_confirmation"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "operator_confirmation": {"type": "boolean", "enum": [True]},
        "approval_scope": {"type": "string", "enum": ["owner_service_default"]},
    },
}


PLAN_REVISION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict plan-revision fields; explicit execution/package/handoff/source-widening fields remain fail-closed.",
    "required": ["session_id", "preview_id", "preview_hash", "operator_decision"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "operator_decision": {"type": "string", "enum": ["reject_current_preview", "request_revision"]},
        "operator_note": {"type": "string"},
        "execute": {"description": "Known but non-admitted; service rejects fail-closed."},
        "execution": {"description": "Known but non-admitted; service rejects fail-closed."},
        "run": {"description": "Known but non-admitted; service rejects fail-closed."},
        "run_analysis": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "handoff": {"description": "Known but non-admitted; service rejects fail-closed."},
        "plan_edits": {"description": "Known but non-admitted; service rejects fail-closed."},
        "natural_language_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "llm_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "execution_started": {"description": "Known but non-admitted; service rejects fail-closed."},
        "create_pass_runs": {"description": "Known but non-admitted; service rejects fail-closed."},
        "pass_run_ids": {"description": "Known but non-admitted; service rejects fail-closed."},
        "artifact_manifest": {"description": "Known but non-admitted; service rejects fail-closed."},
        "result_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "qualitative_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "hybrid_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "rag_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "vector_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
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
        "execute": {"description": "Known but non-admitted; service rejects fail-closed."},
        "execution": {"description": "Known but non-admitted; service rejects fail-closed."},
        "run": {"description": "Known but non-admitted; service rejects fail-closed."},
        "run_analysis": {"description": "Known but non-admitted; service rejects fail-closed."},
        "start_execution": {"description": "Known but non-admitted; service rejects fail-closed."},
        "analysis_run_id": {"description": "Known but non-admitted; service rejects fail-closed."},
        "analysis_run_ids": {"description": "Known but non-admitted; service rejects fail-closed."},
        "result_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "results": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "handoff": {"description": "Known but non-admitted; service rejects fail-closed."},
        "artifact_manifest": {"description": "Known but non-admitted; service rejects fail-closed."},
        "local_upload": {"description": "Known but non-admitted; service rejects fail-closed."},
        "local_directory": {"description": "Known but non-admitted; service rejects fail-closed."},
        "rag_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "vector_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "qualitative_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "hybrid_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
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
        "run_all": {"description": "Known but non-admitted; service rejects fail-closed."},
        "batch": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "handoff": {"description": "Known but non-admitted; service rejects fail-closed."},
        "result_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "local_upload": {"description": "Known but non-admitted; service rejects fail-closed."},
        "local_directory": {"description": "Known but non-admitted; service rejects fail-closed."},
        "rag_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "vector_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "qualitative_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "hybrid_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "approved_plan_supersession": {"description": "Known but non-admitted; service rejects fail-closed."},
        "schema_migration": {"description": "Known but non-admitted; service rejects fail-closed."},
        "artifact_manifest": {"description": "Known but non-admitted; service rejects fail-closed."},
        "results": {"description": "Known but non-admitted; service rejects fail-closed."},
        "source_expansion": {"description": "Known but non-admitted; service rejects fail-closed."},
        "schema_widening": {"description": "Known but non-admitted; service rejects fail-closed."},
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
        "approve_result": {"description": "Known but non-admitted; service rejects fail-closed."},
        "reject_result": {"description": "Known but non-admitted; service rejects fail-closed."},
        "result_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "result_decision": {"description": "Known but non-admitted; service rejects fail-closed."},
        "edited_findings": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package": {"description": "Known but non-admitted; service rejects fail-closed."},
        "package_review": {"description": "Known but non-admitted; service rejects fail-closed."},
        "handoff": {"description": "Known but non-admitted; service rejects fail-closed."},
        "export": {"description": "Known but non-admitted; service rejects fail-closed."},
        "rerun": {"description": "Known but non-admitted; service rejects fail-closed."},
        "retry": {"description": "Known but non-admitted; service rejects fail-closed."},
        "cancel": {"description": "Known but non-admitted; service rejects fail-closed."},
        "run_all": {"description": "Known but non-admitted; service rejects fail-closed."},
        "batch": {"description": "Known but non-admitted; service rejects fail-closed."},
        "local_upload": {"description": "Known but non-admitted; service rejects fail-closed."},
        "local_directory": {"description": "Known but non-admitted; service rejects fail-closed."},
        "rag_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "vector_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "qualitative_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "hybrid_plan": {"description": "Known but non-admitted; service rejects fail-closed."},
        "approved_plan_supersession": {"description": "Known but non-admitted; service rejects fail-closed."},
        "schema_migration": {"description": "Known but non-admitted; service rejects fail-closed."},
        "runtime_db_write": {"description": "Known but non-admitted; service rejects fail-closed."},
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
    },
}


PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["session_id", "analysis_plan_id", "pass_run_id", "preview_id", "preview_hash"],
    "properties": {
        "client_request_id": {"type": "string"},
        "session_id": {"type": "string"},
        "analysis_plan_id": {"type": "string"},
        "pass_run_id": {"type": "string"},
        "preview_id": {"type": "string"},
        "preview_hash": {"type": "string"},
        "result_review_record_ref": {"type": "string"},
        "analysis_run_id": {"type": "string"},
    },
}


PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA: dict[str, Any] = {
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
        "analysis_run_id": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
    },
}


PACKAGE_REVIEW_SUBMIT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "decision_notes are required by runtime for changes_requested, rejected, and blocked decisions.",
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
    },
}


HANDOFF_EXPORT_PREPARE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "decision_notes are required by runtime for hold, decline, and blocked decisions.",
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
        "handoff_target",
        "export_mode",
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
        "payload_refs": _string_array_or_string_map_schema(
            "List of payload refs or a mapping keyed by package kind or package id."
        ),
        "payload_hashes": _string_array_or_string_map_schema(
            "List of payload hashes or a mapping keyed by package kind or package id."
        ),
        "package_review_submit_record_ref": {"type": "string"},
        "package_review_state": {"type": "string", "enum": ["package_review_approved"]},
        "handoff_target": {"type": "string", "enum": ["internal_export_envelope"]},
        "export_mode": {"type": "string", "enum": ["prepare_only"]},
        "operator_decision": {"type": "string", "enum": ["authorize_prepare", "hold", "decline", "blocked"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
        "expected_package_kinds": {
            "type": "array",
            "items": {"type": "string", "enum": ["canonical_internal", "user_facing", "review_facing"]},
        },
    },
}


APS_HANDOFF_DISPATCH_REQUEST_SCHEMA: dict[str, Any] = {
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
        "aps_handoff_target",
        "dispatch_mode",
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
        "aps_handoff_target": {"type": "string", "enum": ["aps_evidence_bundle"]},
        "dispatch_mode": {"type": "string", "enum": ["server_side_aps_handoff"]},
        "operator_decision": {"type": "string", "enum": ["dispatch_aps_handoff"]},
        "decision_notes": {"type": "string"},
        "analysis_run_id": {"type": "string"},
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
    },
}


class Layer3SessionSummaryResponse(Layer3BaseResponse):
    session_id: str
    selection_manifest_id: str
    current_gate: str
    gate_b_summary: dict[str, int]
    gate_c_summary: dict[str, Any]
    plan_preview: dict[str, Any]
    plan_approval: dict[str, Any]
    plan_revision: dict[str, Any]
    execution_selection: dict[str, Any]
    analysis_execution_start: dict[str, Any]
    execution_result_review: dict[str, Any]
    package_review_preview: dict[str, Any]
    package_construction: dict[str, Any]
    package_review_submit: dict[str, Any]
    handoff_export_prepare: dict[str, Any]
    aps_handoff_dispatch: dict[str, Any]
    external_export_download: dict[str, Any]
    sublayer_visualization: dict[str, Any]
    state_action_contract: dict[str, Any]
    downstream_unavailable: list[str]
    authority_rail: dict[str, Any]


def _json_or_error(handler: Callable[[], dict[str, Any]]) -> dict[str, Any] | JSONResponse:
    try:
        return handler()
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=layer3_workbench.workbench_error_response(exc),
        )


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


@router.get("/bootstrap", response_model=Layer3WorkbenchBootstrapResponse)
def get_bootstrap() -> dict[str, Any]:
    return layer3_workbench.bootstrap()


@router.get("/readiness", response_model=Layer3ExecutionReadinessResponse)
def get_readiness() -> dict[str, Any]:
    return layer3_workbench.readiness_contract()


@router.post(
    "/preflight",
    response_model=Layer3PreflightResponse,
    openapi_extra={"requestBody": _json_request_body(PREFLIGHT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_preflight(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.preflight(payload))


@router.post(
    "/source-preview",
    response_model=Layer3SourcePreviewResponse,
    openapi_extra={"requestBody": _json_request_body(SOURCE_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_source_preview(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.source_preview(payload))


@router.post(
    "/material-preview",
    response_model=Layer3MaterialPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(MATERIAL_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_material_preview(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.material_preview(payload, db))


@router.get(
    "/dataset-version-candidates",
    response_model=Layer3DatasetVersionCandidatesResponse,
    responses=_workbench_error_responses(400),
)
def get_dataset_version_candidates(limit: int = 50, db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.aps_dataset_version_candidates(db, limit=limit))


@router.get(
    "/aps-content-document-candidates",
    response_model=Layer3ApsContentDocumentCandidatesResponse,
    responses=_workbench_error_responses(400),
)
def get_aps_content_document_candidates(limit: int = 50, db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.aps_content_document_candidates(db, limit=limit))


@router.post(
    "/gate-b/decision",
    response_model=Layer3GateBDecisionResponse,
    openapi_extra={"requestBody": _json_request_body(GATE_B_DECISION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 409),
)
def post_gate_b_decision(
    payload: Layer3GateBDecisionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.gate_b_decision(db, payload.model_dump(exclude_none=True)))


@router.post(
    "/gate-c/preview",
    response_model=Layer3GateCPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(GATE_C_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_gate_c_preview(
    payload: Layer3GateCPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.gate_c_preview(db, payload.model_dump(exclude_none=True)))


@router.post(
    "/gate-c/override",
    status_code=409,
    response_model=Layer3TypingOverrideUnavailableResponse,
)
def post_gate_c_override(payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=layer3_workbench.gate_c_override_unavailable(payload),
    )


@router.post(
    "/plan/preview",
    response_model=Layer3PlanPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_preview(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_preview(db, payload))


@router.post(
    "/plan/approve",
    response_model=Layer3PlanApprovalResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_APPROVAL_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_approve(
    payload: Layer3PlanApprovalRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_workbench.plan_approval(
            db,
            payload.model_dump(exclude_none=True),
        )
    )


@router.post(
    "/plan/revise",
    response_model=Layer3PlanRevisionResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_REVISION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_revise(
    payload: Layer3PlanRevisionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_revision(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/select",
    response_model=Layer3ExecutionSelectionResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_SELECTION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_select(
    payload: Layer3ExecutionSelectionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_selection(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/start",
    response_model=Layer3AnalysisExecutionStartResponse,
    openapi_extra={"requestBody": _json_request_body(ANALYSIS_EXECUTION_START_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_start(
    payload: Layer3AnalysisExecutionStartRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.analysis_execution_start(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/result/status",
    response_model=Layer3ExecutionResultStatusResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_RESULT_STATUS_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_result_status(
    payload: Layer3ExecutionResultStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_result_status(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/result/review",
    response_model=Layer3ExecutionResultReviewResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_RESULT_REVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_result_review(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_result_review(db, payload))


@router.post(
    "/package/review/preview",
    response_model=Layer3PackageReviewPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_preview(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_review_preview(db, payload))


@router.post(
    "/package/review/commit",
    response_model=Layer3PackageConstructionCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_commit(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_construction_commit(db, payload))


@router.post(
    "/package/review/submit",
    response_model=Layer3PackageReviewSubmitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REVIEW_SUBMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_submit(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_review_submit(db, payload))


@router.post(
    "/handoff/export/prepare",
    response_model=Layer3HandoffExportPrepareResponse,
    response_model_exclude_unset=True,
    openapi_extra={"requestBody": _json_request_body(HANDOFF_EXPORT_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_handoff_export_prepare(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.handoff_export_prepare(db, payload))


@router.post(
    "/handoff/aps/dispatch",
    response_model=Layer3ApsHandoffDispatchResponse,
    openapi_extra={"requestBody": _json_request_body(APS_HANDOFF_DISPATCH_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_aps_handoff_dispatch(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.aps_handoff_dispatch(db, payload))


@router.post(
    "/handoff/export/download/prepare",
    response_model=Layer3ExternalExportDownloadPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_export_download_prepare(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.external_export_download_prepare(db, payload))


@router.post(
    "/handoff/export/download/signed-reference/generate",
    response_model=Layer3ExternalExportDownloadSignedReferenceResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_export_download_signed_reference_generate(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.external_export_download_generate_signed_reference(db, payload))


@router.post(
    "/handoff/export/download/deliver",
    response_model=None,
    openapi_extra={"requestBody": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_BODY},
    responses={
        200: {
            "description": "APS evidence bundle artifact attachment.",
            "content": {
                "application/json": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
            "headers": {
                "Content-Disposition": {"schema": {"type": "string"}},
                "X-Layer3-Schema-Id": {"schema": {"type": "string"}},
                "X-Layer3-Delivery-State": {"schema": {"type": "string"}},
                "X-Layer3-Source-Artifact-Hash": {"schema": {"type": "string"}},
            },
        },
        400: {"model": Layer3WorkbenchErrorResponse},
        404: {"model": Layer3WorkbenchErrorResponse},
        409: {"model": Layer3WorkbenchErrorResponse},
    },
)
async def post_external_export_download_deliver(
    request: Request,
    db: Session = Depends(get_db),
) -> FileResponse | JSONResponse:
    try:
        payload = await _payload_from_request(request)
        delivery = layer3_workbench.external_export_download_deliver(db, payload)
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=layer3_workbench.workbench_error_response(exc),
        )
    return FileResponse(
        path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        content_disposition_type="attachment",
        headers=delivery.headers,
    )


@router.post(
    "/handoff/export/download/signed-reference/use",
    response_model=None,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_REQUEST_SCHEMA)},
    responses={
        200: {
            "description": "APS evidence bundle artifact attachment from a server-owned signed delivery reference.",
            "content": {
                "application/json": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
            "headers": {
                "Content-Disposition": {"schema": {"type": "string"}},
                "X-Layer3-Schema-Id": {"schema": {"type": "string"}},
                "X-Layer3-Delivery-State": {"schema": {"type": "string"}},
                "X-Layer3-Source-Artifact-Hash": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-State": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Expires-At": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Token-Id": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Receipt-Id": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Replay-Policy": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Use-Count": {"schema": {"type": "string"}},
            },
        },
        400: {"model": Layer3WorkbenchErrorResponse},
        404: {"model": Layer3WorkbenchErrorResponse},
        409: {"model": Layer3WorkbenchErrorResponse},
    },
)
def post_external_export_download_signed_reference_use(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> FileResponse | JSONResponse:
    try:
        delivery = layer3_workbench.external_export_download_use_signed_reference(db, payload)
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=layer3_workbench.workbench_error_response(exc),
        )
    return FileResponse(
        path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        content_disposition_type="attachment",
        headers=delivery.headers,
    )


@router.get(
    "/session/{session_id}",
    response_model=Layer3SessionSummaryResponse,
    responses={404: {"model": Layer3WorkbenchErrorResponse}},
)
def get_session_summary(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.session_summary(db, session_id))
