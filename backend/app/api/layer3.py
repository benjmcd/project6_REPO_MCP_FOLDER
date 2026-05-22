from __future__ import annotations

import json
from typing import Any, Callable, Literal
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import (
    layer3_connector_dispatch_entry,
    layer3_connector_local_destination_receipt,
    layer3_corrected_package_artifact_set,
    layer3_external_local_export,
    layer3_internal_webhook_connector,
    layer3_package_mutation_entry,
    layer3_package_supersession_commit,
    layer3_raw_mixed_bridge,
    layer3_raw_mixed_materialization,
    layer3_local_outbox_provider_private_handoff,
    layer3_package_replacement_activation,
    layer3_replacement_package_materialization,
    layer3_replacement_package_namespace,
    layer3_replacement_package_artifact_manifest,
    layer3_replacement_package_set_authority,
    layer3_provider_private_signed_url,
    layer3_provider_public_url,
    layer3_provider_public_url_delivery_use,
    layer3_server_owned_local_outbox_target,
    layer3_server_owned_local_outbox_write,
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_artifact_status,
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_default_readiness,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_final_proof,
    layer3_candidate_b_operator_status,
    layer3_candidate_b_promotion_closure,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_visual_lane_status,
    layer3_source_directory_ingestion,
    layer3_source_directory_material_admission,
    layer3_source_directory_context_packet,
    layer3_source_directory_hybrid_analysis,
    layer3_source_directory_hybrid_authority,
    layer3_source_directory_hybrid_context,
    layer3_source_directory_internal_webhook,
    layer3_source_directory_qualitative_analysis,
    layer3_source_directory_text_index,
    layer3_source_directory_text_retrieval,
    layer3_source_directory_vector_index,
    layer3_source_directory_vector_retrieval,
    layer3_source_intake,
    layer3_workbench,
)
from app.services.layer3_preflight_request_contract import PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response

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
    authority_matrix_contract: dict[str, Any]
    mockup_activation_readiness: dict[str, Any]
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
    internal_connector_dispatch_record_admitted: bool
    internal_connector_dispatch_record_endpoint: str
    internal_fake_local_destination_receipt_admitted: bool
    internal_fake_local_destination_receipt_endpoint: str
    package_supersession_preview_admitted: bool
    package_supersession_preview_endpoint: str
    replacement_package_artifact_materialization_admitted: bool
    replacement_package_artifact_materialization_endpoint: str
    replacement_package_set_authority_admitted: bool
    replacement_package_set_authority_endpoint: str
    package_supersession_commit_admitted: bool
    package_supersession_commit_endpoint: str
    replacement_package_artifact_manifest_admitted: bool
    replacement_package_artifact_manifest_endpoint: str
    replacement_package_namespace_admitted: bool
    replacement_package_namespace_endpoint: str
    plan_revision_recovery_admitted: bool
    plan_revision_recovery_endpoint: str
    approved_plan_cancel_admitted: bool
    approved_plan_cancel_endpoint: str
    candidate_b_bundle_material_bridge_admitted: bool
    candidate_b_bundle_material_bridge_endpoint: str
    candidate_b_artifact_family_status_admitted: bool
    candidate_b_artifact_family_status_endpoint: str
    candidate_b_bundle_downstream_proof_admitted: bool
    candidate_b_bundle_downstream_proof_endpoint: str
    candidate_b_runtime_downstream_proof_admitted: bool
    candidate_b_runtime_downstream_proof_endpoint: str
    candidate_b_default_promotion_operator_status_admitted: bool
    candidate_b_default_promotion_operator_status_endpoint: str
    candidate_b_default_promotion_closure_evidence_admitted: bool
    candidate_b_default_promotion_closure_evidence_endpoint: str
    candidate_b_default_promotion_final_proof_admitted: bool
    candidate_b_default_promotion_final_proof_endpoint: str
    candidate_b_default_promotion_final_proof_status_admitted: bool
    candidate_b_default_promotion_final_proof_status_endpoint: str
    source_directory_ingestion_scan_admitted: bool
    source_directory_ingestion_scan_endpoint: str
    source_directory_ingestion_status_admitted: bool
    source_directory_ingestion_status_endpoint: str
    source_directory_material_preview_admitted: bool
    source_directory_material_preview_endpoint: str
    source_directory_vector_retrieval_admitted: bool
    source_directory_vector_retrieval_endpoint: str
    source_directory_hybrid_context_packet_admitted: bool
    source_directory_hybrid_context_packet_endpoint: str
    source_directory_hybrid_context_packet_qualitative_analysis_admitted: bool
    source_directory_hybrid_context_packet_qualitative_analysis_endpoint: str
    source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_admitted: bool
    source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview_endpoint: str
    source_directory_hybrid_context_packet_qualitative_analysis_package_commit_admitted: bool
    source_directory_hybrid_context_packet_qualitative_analysis_package_commit_endpoint: str
    source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_admitted: bool
    source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_endpoint: str
    source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_admitted: bool
    source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_endpoint: str
    source_directory_qualitative_hybrid_analysis_admitted: bool
    source_directory_qualitative_hybrid_analysis_endpoint: str
    source_directory_operator_status_surface: str
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
    authority_matrix_contract: dict[str, Any]
    preview_hash_contract: dict[str, Any]
    material_preview_hash_contract: dict[str, Any]
    idempotency_contract: dict[str, Any]
    concurrency_contract: dict[str, Any]
    deferred_decisions: dict[str, Any]


class Layer3AuthorityMatrixResponse(Layer3BaseResponse):
    route: str
    api_root: str
    authority_matrix_contract: dict[str, Any]


class Layer3PreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    natural_language_intent: str
    manual_constraints: dict[str, Any] | None = None
    actor: str | None = None


class Layer3PlanApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    session_id: str
    preview_id: str
    preview_hash: str
    operator_confirmation: bool
    approval_scope: str | None = None


class Layer3ApprovedPlanCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    session_id: str
    analysis_plan_id: str
    source_preview_id: str
    source_preview_hash: str
    operator_decision: str
    operator_note: str | None = None
    approved_plan_supersession: Any | None = None
    replacement_plan: Any | None = None
    reopen_approved_plan: Any | None = None
    delete_approved_plan: Any | None = None
    create_pass_runs: Any | None = None
    execution: Any | None = None
    analysis_run_id: Any | None = None
    package_mutation: Any | None = None
    connector_dispatch: Any | None = None
    provider_public_url: Any | None = None
    source_expansion: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_plan: Any | None = None
    frontend_state: Any | None = None
    hidden_llm_plan: Any | None = None


class Layer3PlanPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    session_id: str | None = None
    preview_scope: str | None = None
    include_exclusions: bool | None = None


class Layer3SourcePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    preflight_id: str
    selected_source_classes: list[str] | None = None
    actor: str | None = None


class Layer3MaterialPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    preflight_id: str | None = None
    source_set_id: str | None = None
    source_candidate_ids: list[str] = Field(min_length=1)
    dataset_version_ids: list[str] | None = None
    aps_content_document_ids: list[str] | None = None
    query_basis: dict[str, Any] | None = None
    actor: str | None = None


class Layer3RawMixedCorpusSeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    seed_mode: Literal["raw_mixed_corpus_bridge_seed_only"]
    corpus_batch_id: str = Field(min_length=1)
    aps_run_id: str = Field(min_length=1)
    target_ids: list[str] = Field(min_length=1)
    artifact_manifest_ref: str = Field(min_length=1)
    artifact_manifest_hash: str = Field(min_length=64, max_length=64)
    requested_source_classes: list[str] = Field(min_length=2)
    operator_confirmation: bool
    source_upload: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    local_path: Any | None = None
    directory_path: Any | None = None
    broad_file_upload: Any | None = None
    file_bytes: Any | None = None
    file_glob: Any | None = None
    web_connector: Any | None = None
    connector_key: Any | None = None
    connector_secret: Any | None = None
    source_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    rag_vector_index: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    embedding_model: Any | None = None
    runtime_db_write: Any | None = None
    unbounded_runtime_db: Any | None = None
    package_payload: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    hidden_llm_planning: Any | None = None
    mockup_activation: Any | None = None
    auth_policy_override: Any | None = None


class Layer3RawMixedCorpusMaterializeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    materialization_mode: Literal["raw_mixed_existing_source_materialization_entry"]
    corpus_batch_id: str = Field(min_length=1)
    artifact_manifest_ref: str = Field(min_length=1)
    artifact_manifest_hash: str = Field(min_length=64, max_length=64)
    requested_source_classes: list[str] = Field(min_length=2)
    operator_confirmation: bool
    source_upload: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    local_path: Any | None = None
    directory_path: Any | None = None
    broad_file_upload: Any | None = None
    file_bytes: Any | None = None
    file_glob: Any | None = None
    web_connector: Any | None = None
    connector_key: Any | None = None
    connector_secret: Any | None = None
    source_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    rag_vector_index: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    embedding_model: Any | None = None
    runtime_db_write: Any | None = None
    unbounded_runtime_db: Any | None = None
    package_payload: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    hidden_llm_planning: Any | None = None
    mockup_activation: Any | None = None
    auth_policy_override: Any | None = None


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
    client_request_id: str = Field(min_length=1)
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


class Layer3GateCOverrideUnavailableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    session_id: str | None = None
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

    schema_id: str | None = None
    schema_version: int | None = None
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


class Layer3PlanRevisionRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    session_id: str
    source_revision_state: str
    source_preview_id: str
    source_preview_hash: str
    operator_decision: str
    operator_note: str | None = None
    approve_plan: Any | None = None
    approved_plan_supersession: Any | None = None
    delete_approved_plan: Any | None = None
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
    analysis_run_id: Any | None = None
    artifact_manifest: Any | None = None
    result_review: Any | None = None
    package_mutation: Any | None = None
    connector_dispatch: Any | None = None
    provider_public_url: Any | None = None
    source_expansion: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_plan: Any | None = None
    rag_plan: Any | None = None
    vector_plan: Any | None = None
    browser_persisted_state: Any | None = None


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


class Layer3ExecutionResultReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    operator_decision: str | None = None
    review_notes: str | None = None
    reviewed_output_items: list[dict[str, Any]] | None = None
    analysis_run_id: str | None = None
    package: Any | None = None
    package_review: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None
    runtime_db_write: Any | None = None
    artifact_manifest: Any | None = None
    package_variant: Any | None = None
    aps_handoff: Any | None = None
    edited_findings: Any | None = None
    rewrite_output: Any | None = None


class Layer3PackageReviewPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    result_review_record_ref: str | None = None
    analysis_run_id: str | None = None
    package: Any | None = None
    package_review_decision: Any | None = None
    create_package: Any | None = None
    package_variant: Any | None = None
    output_package_id: Any | None = None
    reconciliation_record_id: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None
    runtime_db_write: Any | None = None
    artifact_manifest: Any | None = None
    aps_handoff: Any | None = None
    edited_findings: Any | None = None
    rewrite_output: Any | None = None


class Layer3PackageConstructionCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    result_review_record_ref: str | None = None
    package_review_preview_hash: str | None = None
    analysis_run_id: str | None = None
    expected_package_kinds: list[str] | None = None
    package_review_decision: Any | None = None
    submit_package_review: Any | None = None
    approve_package: Any | None = None
    reject_package: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None
    runtime_db_write: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    aps_handoff: Any | None = None
    edited_findings: Any | None = None
    rewrite_output: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None


class Layer3PackageReviewSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    result_review_record_ref: str | None = None
    package_review_preview_hash: str | None = None
    construction_basis_hash: str | None = None
    reconciliation_record_id: str | None = None
    output_package_ids: Any | None = None
    payload_refs: Any | None = None
    payload_hashes: Any | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    analysis_run_id: str | None = None
    expected_package_kinds: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    aps_handoff: Any | None = None
    create_package: Any | None = None
    rebuild_package: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rewrite_output: Any | None = None
    edited_findings: Any | None = None
    result_review_amendment: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None
    runtime_db_write: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None


class Layer3PackageSupersessionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    output_package_ids: list[str] | None = None
    package_kinds: list[str] | None = None
    payload_refs: list[str] | None = None
    payload_hashes: list[str] | None = None
    package_review_preview_hash: str | None = None
    operator_decision: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    analysis_run_id: str | None = None
    result_review_record_ref: str | None = None
    package_review_submit_record_ref: str | None = None
    handoff_export_record_ref: str | None = None
    aps_handoff_record_ref: str | None = None
    external_export_download_record_ref: str | None = None
    connector_dispatch_record_ref: str | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    result_review_amendment: Any | None = None
    package_review_amendment: Any | None = None
    handoff_export_amendment: Any | None = None
    aps_handoff_amendment: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3ReplacementPackageArtifactMaterializationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    package_supersession_preview_hash: str | None = None
    source_package_set_hash: str | None = None
    source_output_package_ids: list[str] | None = None
    source_package_kinds: list[str] | None = None
    source_payload_refs: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    operator_decision: str | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    authority_basis_hash: Any | None = None
    materialization_basis_hash: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    edited_package_content: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    replacement_package_set_authority_id: Any | None = None
    package_supersession_commit: Any | None = None
    package_supersession_commit_id: Any | None = None
    replacement_output_package_ids: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3ReplacementPackageSetAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    source_package_set_hash: str | None = None
    source_output_package_ids: list[str] | None = None
    source_package_kinds: list[str] | None = None
    source_payload_refs: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    replacement_package_set_id: str | None = None
    replacement_package_set_hash: str | None = None
    replacement_package_kinds: list[str] | None = None
    replacement_payload_refs: list[str] | None = None
    replacement_payload_hashes: list[str] | None = None
    authority_basis_hash: str | None = None
    operator_decision: str | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    edited_package_content: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    package_supersession_commit: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3ReplacementPackageSetAuthorityFromCorrectedArtifactSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    source_package_set_hash: str | None = None
    corrected_package_artifact_set_id: str | None = None
    corrected_artifact_basis_hash: str | None = None
    operator_decision: str | None = None
    source_output_package_ids: Any | None = None
    source_package_kinds: Any | None = None
    source_payload_refs: Any | None = None
    source_payload_hashes: Any | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    authority_basis_hash: Any | None = None
    corrected_artifact_refs: Any | None = None
    corrected_artifact_hashes: Any | None = None
    corrected_artifact_bytes: Any | None = None
    corrected_package_payloads: Any | None = None
    replacement_output_package_ids: Any | None = None
    source_l3_output_package_write: Any | None = None
    source_output_package_update: Any | None = None
    browser_generated_diff: Any | None = None
    rendered_control_state: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    edited_package_content: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    package_supersession_commit: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3SourceDirectoryReplacementPackageSetAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    package_supersession_preview_hash: str | None = None
    source_package_set_hash: str | None = None
    operator_decision: str | None = None
    source_output_package_ids: Any | None = None
    source_package_kinds: Any | None = None
    source_payload_refs: Any | None = None
    source_payload_hashes: Any | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    authority_basis_hash: Any | None = None
    materialization_basis_hash: Any | None = None
    replacement_package_set_authority_id: Any | None = None
    commit_basis_hash: Any | None = None
    downstream_dependency_hash: Any | None = None
    frontend_state: Any | None = None
    browser_state: Any | None = None
    rendered_control_state: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    edited_package_content: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    package_supersession_commit: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3CorrectedPackageArtifactSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    source_package_set_hash: str | None = None
    source_output_package_ids: list[str] | None = None
    source_package_kinds: list[str] | None = None
    source_payload_refs: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    result_review_record_ref: str | None = None
    reviewed_output_items_hash: str | None = None
    package_review_preview_hash: str | None = None
    operator_decision: str | None = None
    package_supersession_preview_hash: str | None = None
    replacement_artifact_materialization_id: str | None = None
    materialization_basis_hash: str | None = None
    corrected_artifact_refs: Any | None = None
    corrected_artifact_hashes: Any | None = None
    corrected_artifact_bytes: Any | None = None
    corrected_package_payloads: Any | None = None
    package_payload: Any | None = None
    package_payload_bytes: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    edited_package_content: Any | None = None
    browser_generated_diff: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    replacement_output_package_ids: Any | None = None
    source_l3_output_package_write: Any | None = None
    source_output_package_update: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    source_directory: Any | None = None
    local_directory: Any | None = None
    rag_vector_input: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_execution_instruction: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_prompt: Any | None = None
    hidden_llm_plan: Any | None = None
    hidden_llm_planning: Any | None = None
    rendered_control_state: Any | None = None
    schema_migration: Any | None = None
    auth_security_directive: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3PackageSupersessionCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    package_supersession_preview_hash: str | None = None
    source_package_set_hash: str | None = None
    source_output_package_ids: list[str] | None = None
    source_package_kinds: list[str] | None = None
    source_payload_refs: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    replacement_package_set_authority_id: str | None = None
    replacement_package_set_id: str | None = None
    replacement_package_set_hash: str | None = None
    replacement_package_kinds: list[str] | None = None
    replacement_payload_refs: list[str] | None = None
    replacement_payload_hashes: list[str] | None = None
    replacement_authority_basis_hash: str | None = None
    downstream_dependency_hash: str | None = None
    commit_basis_hash: str | None = None
    operator_decision: str | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_output_package_ids: Any | None = None
    replacement_package_payloads: Any | None = None
    edited_package_content: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff_package: Any | None = None
    export_package: Any | None = None
    connector_key: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_plan: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_plan: Any | None = None
    ui_control: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None


class Layer3PackageSupersessionCommitFromCorrectedArtifactSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    corrected_package_artifact_set_id: str | None = None
    corrected_artifact_basis_hash: str | None = None
    replacement_package_set_authority_id: str | None = None
    replacement_authority_basis_hash: str | None = None
    operator_decision: str | None = None
    package_supersession_preview_hash: Any | None = None
    source_package_set_hash: Any | None = None
    source_output_package_ids: Any | None = None
    source_package_kinds: Any | None = None
    source_payload_refs: Any | None = None
    source_payload_hashes: Any | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    downstream_dependency_hash: Any | None = None
    commit_basis_hash: Any | None = None
    corrected_artifact_refs: Any | None = None
    corrected_artifact_hashes: Any | None = None
    corrected_artifact_bytes: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    analysis_artifact: Any | None = None
    delete_package: Any | None = None
    edited_package_content: Any | None = None
    export_package: Any | None = None
    handoff_package: Any | None = None
    mutate_package: Any | None = None
    rebuild_package: Any | None = None
    replace_package: Any | None = None
    rewrite_output: Any | None = None
    update_package_row: Any | None = None
    replacement_output_package_ids: Any | None = None
    replacement_package_payloads: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    destination_id: Any | None = None
    destination_path: Any | None = None
    destination_url: Any | None = None
    connector_run_id: Any | None = None
    connector_run_target_id: Any | None = None
    connector_key: Any | None = None
    connector_payload: Any | None = None
    credential_id: Any | None = None
    credential_payload: Any | None = None
    auth_token: Any | None = None
    public_url: Any | None = None
    provider_public_url: Any | None = None
    signed_url: Any | None = None
    local_path: Any | None = None
    local_directory: Any | None = None
    source_directory: Any | None = None
    source_upload: Any | None = None
    rag_query: Any | None = None
    rag_plan: Any | None = None
    rag_execution: Any | None = None
    vector_index: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    hidden_llm_plan: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None
    ui_control: Any | None = None
    frontend_state: Any | None = None
    browser_state: Any | None = None


class Layer3SourceDirectoryPackageSupersessionCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    package_supersession_preview_hash: str | None = None
    source_package_set_hash: str | None = None
    replacement_package_set_authority_id: str | None = None
    replacement_authority_basis_hash: str | None = None
    operator_decision: str | None = None
    source_output_package_ids: Any | None = None
    source_package_kinds: Any | None = None
    source_payload_refs: Any | None = None
    source_payload_hashes: Any | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    downstream_dependency_hash: Any | None = None
    commit_basis_hash: Any | None = None
    authority_basis_hash: Any | None = None
    materialization_basis_hash: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_output_package_ids: Any | None = None
    replacement_package_payloads: Any | None = None
    edited_package_content: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_rewrite: Any | None = None
    artifact_manifest: Any | None = None
    analysis_artifact: Any | None = None
    handoff_package: Any | None = None
    export_package: Any | None = None
    connector_key: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_plan: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_plan: Any | None = None
    ui_control: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None
    frontend_state: Any | None = None
    browser_state: Any | None = None
    rendered_control_state: Any | None = None


class Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    reconciliation_record_id: str | None = None
    package_supersession_commit_id: str | None = None
    package_supersession_commit_basis_hash: str | None = None
    replacement_package_set_authority_id: str | None = None
    replacement_authority_basis_hash: str | None = None
    delivery_mode: str | None = None
    operator_decision: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    decision_notes: str | None = None
    provider_private_signed_url_token: Any | None = None
    raw_provider_private_signed_url_token: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_public_url: Any | None = None
    raw_public_url: Any | None = None
    raw_provider_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    provider_object_key: Any | None = None
    provider_bucket: Any | None = None
    provider_container: Any | None = None
    package_payload: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    source_payload_refs: Any | None = None
    replacement_payload_refs: Any | None = None
    local_path: Any | None = None
    raw_local_path: Any | None = None
    connector_run_id: Any | None = None
    destination_url: Any | None = None
    destination_id: Any | None = None
    source_expansion: Any | None = None
    rag_vector_index: Any | None = None
    model_runtime: Any | None = None
    frontend_state: Any | None = None
    browser_state: Any | None = None
    frontend_durable_authority: Any | None = None


class Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlPrepareRequest(
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlBaseRequest
):
    recipient_scope: str | None = None
    requested_ttl_seconds: int | None = None


class Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlStatusRequest(
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlBaseRequest
):
    provider_signed_url_receipt_id: str | None = None


class Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlUseRequest(
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlStatusRequest
):
    pass


class Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlRevokeRequest(
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlStatusRequest
):
    idempotency_key: str | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None


class Layer3ReplacementPackageArtifactManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    replacement_package_set_authority_id: str | None = None
    package_supersession_commit_id: str | None = None
    package_supersession_commit_basis_hash: str | None = None
    replacement_package_set_id: str | None = None
    replacement_package_set_hash: str | None = None
    replacement_package_kinds: list[str] | None = None
    replacement_payload_refs: list[str] | None = None
    replacement_payload_hashes: list[str] | None = None
    hash_algorithm: str | None = None
    artifact_namespace: str | None = None
    artifact_manifest_hash: str | None = None
    authority_basis_hash: str | None = None
    operator_decision: str | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    edited_package_content: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    replacement_output_package_ids: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3ReplacementPackageArtifactManifestFromAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    replacement_artifact_materialization_id: str | None = None
    materialization_basis_hash: str | None = None
    replacement_package_set_authority_id: str | None = None
    replacement_authority_basis_hash: str | None = None
    package_supersession_commit_id: str | None = None
    package_supersession_commit_basis_hash: str | None = None
    operator_decision: str | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    verified_artifact_refs: Any | None = None
    verified_artifact_hashes: Any | None = None
    verified_artifact_byte_sizes: Any | None = None
    hash_algorithm: Any | None = None
    artifact_namespace: Any | None = None
    artifact_manifest_hash: Any | None = None
    authority_basis_hash: Any | None = None
    manifest_snapshot: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    edited_package_content: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    replacement_output_package_ids: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3ReplacementPackageArtifactManifestFromCorrectedArtifactSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    corrected_package_artifact_set_id: str | None = None
    corrected_artifact_basis_hash: str | None = None
    replacement_package_set_authority_id: str | None = None
    replacement_authority_basis_hash: str | None = None
    package_supersession_commit_id: str | None = None
    package_supersession_commit_basis_hash: str | None = None
    operator_decision: str | None = None
    replacement_artifact_materialization_id: Any | None = None
    materialization_basis_hash: Any | None = None
    replacement_package_set_id: Any | None = None
    replacement_package_set_hash: Any | None = None
    replacement_package_kinds: Any | None = None
    replacement_payload_refs: Any | None = None
    replacement_payload_hashes: Any | None = None
    verified_artifact_refs: Any | None = None
    verified_artifact_hashes: Any | None = None
    verified_artifact_byte_sizes: Any | None = None
    corrected_artifact_refs: Any | None = None
    corrected_artifact_hashes: Any | None = None
    corrected_artifact_byte_sizes: Any | None = None
    corrected_artifact_bytes: Any | None = None
    corrected_package_payloads: Any | None = None
    hash_algorithm: Any | None = None
    artifact_namespace: Any | None = None
    artifact_manifest_hash: Any | None = None
    authority_basis_hash: Any | None = None
    manifest_snapshot: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    edited_package_content: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    replacement_output_package_ids: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_run_target_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_path: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    source_directory: Any | None = None
    local_path: Any | None = None
    local_directory: Any | None = None
    rag_query: Any | None = None
    vector_index: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    schema_migration: Any | None = None
    approved_plan_supersession: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None
    credential_id: Any | None = None
    credential_payload: Any | None = None
    auth_token: Any | None = None
    frontend_state: Any | None = None
    browser_state: Any | None = None


class Layer3ReplacementPackageNamespaceRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    replacement_artifact_manifest_id: str | None = None
    replacement_package_set_authority_id: str | None = None
    package_supersession_commit_id: str | None = None
    source_output_package_id: str | None = None
    package_kind: str | None = None
    package_schema_id: str | None = None
    artifact_ref: str | None = None
    artifact_hash: str | None = None
    authority_basis_hash: str | None = None
    operator_decision: str | None = None
    package_payload: Any | None = None
    package_payload_bytes: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    replacement_content: Any | None = None
    generated_file_bytes: Any | None = None
    edited_package_content: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    source_l3_output_package_write: Any | None = None
    source_output_package_update: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_destination: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_expansion: Any | None = None
    source_upload: Any | None = None
    source_directory: Any | None = None
    local_directory: Any | None = None
    rag_vector_input: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_execution_instruction: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_prompt: Any | None = None
    hidden_llm_plan: Any | None = None
    hidden_llm_planning: Any | None = None
    rendered_control_state: Any | None = None
    schema_migration: Any | None = None
    auth_security_directive: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3ReplacementPackageNamespaceFromCorrectedManifestRequest(
    Layer3ReplacementPackageNamespaceRecordRequest
):
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    corrected_package_artifact_set_id: str | None = None
    corrected_artifact_basis_hash: str | None = None
    replacement_authority_basis_hash: str | None = None
    package_supersession_commit_basis_hash: str | None = None
    replacement_artifact_manifest_authority_basis_hash: str | None = None
    source_output_package_ids: Any | None = None
    package_kinds: Any | None = None
    package_schema_ids: Any | None = None
    artifact_refs: Any | None = None
    artifact_hashes: Any | None = None
    authority_basis_hashes: Any | None = None
    replacement_output_package_id: Any | None = None
    replacement_output_package_ids: Any | None = None
    replacement_activation_basis_hash: Any | None = None
    replacement_namespace_rows: Any | None = None
    namespace_row_ids: Any | None = None
    browser_state: Any | None = None
    frontend_state: Any | None = None


class Layer3PackageReplacementActivationCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    replacement_artifact_manifest_id: str | None = None
    replacement_package_set_authority_id: str | None = None
    package_supersession_commit_id: str | None = None
    replacement_output_package_ids: list[str] | None = None
    source_output_package_ids: list[str] | None = None
    package_kinds: list[str] | None = None
    replacement_activation_basis_hash: str | None = None
    operator_decision: str | None = None
    package_payload: Any | None = None
    package_payload_bytes: Any | None = None
    package_variant_content: Any | None = None
    replacement_package_payloads: Any | None = None
    replacement_package_payload_bytes: Any | None = None
    edited_package_content: Any | None = None
    artifact_bytes: Any | None = None
    generate_artifact: Any | None = None
    rewrite_output: Any | None = None
    rebuild_package: Any | None = None
    mutate_package: Any | None = None
    replace_package: Any | None = None
    delete_package: Any | None = None
    update_package_row: Any | None = None
    update_payload_ref: Any | None = None
    update_payload_hash: Any | None = None
    source_l3_output_package_write: Any | None = None
    source_output_package_update: Any | None = None
    package_row_mutation: Any | None = None
    package_payload_write: Any | None = None
    package_payload_rewrite: Any | None = None
    analysis_artifact: Any | None = None
    handoff: Any | None = None
    export: Any | None = None
    connector_destination: Any | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_payload: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    provider_public_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    source_upload: Any | None = None
    source_directory: Any | None = None
    local_directory: Any | None = None
    rag_vector_input: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    qualitative_execution_instruction: Any | None = None
    qualitative_plan: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_prompt: Any | None = None
    hidden_llm_plan: Any | None = None
    hidden_llm_planning: Any | None = None
    rendered_control_state: Any | None = None
    schema_migration: Any | None = None
    auth_security_directive: Any | None = None
    auth_context: Any | None = None
    security_context: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None


class Layer3HandoffExportPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    result_review_record_ref: str | None = None
    package_review_preview_hash: str | None = None
    construction_basis_hash: str | None = None
    reconciliation_record_id: str | None = None
    output_package_ids: Any | None = None
    payload_refs: Any | None = None
    payload_hashes: Any | None = None
    package_review_submit_record_ref: str | None = None
    package_review_state: str | None = None
    package_review_submit_schema_id: str | None = None
    handoff_target: str | None = None
    export_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    analysis_run_id: str | None = None
    expected_package_kinds: Any | None = None
    aps_handoff: Any | None = None
    dispatch: Any | None = None
    send: Any | None = None
    external_export: Any | None = None
    external_target: Any | None = None
    download: Any | None = None
    connector_run_id: Any | None = None
    runtime_db_write: Any | None = None
    analysis_artifact: Any | None = None
    active_package_authority_applied: Any | None = None
    package_replacement_activation_id: Any | None = None
    replacement_activation_basis_hash: Any | None = None
    active_replacement_output_package_ids: Any | None = None
    active_payload_refs: Any | None = None
    active_payload_hashes: Any | None = None
    artifact_manifest: Any | None = None
    create_package: Any | None = None
    rebuild_package: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rewrite_output: Any | None = None
    edited_findings: Any | None = None
    result_review_amendment: Any | None = None
    package_review_amendment: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None


class Layer3ApsHandoffDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    result_review_record_ref: str | None = None
    package_review_preview_hash: str | None = None
    reconciliation_record_id: str | None = None
    output_package_ids: Any | None = None
    package_kinds: Any | None = None
    payload_refs: Any | None = None
    payload_hashes: Any | None = None
    package_review_submit_record_ref: str | None = None
    package_review_state: str | None = None
    prepare_record_ref: str | None = None
    handoff_export_state: str | None = None
    handoff_export_envelope_ref: str | None = None
    handoff_target: str | None = None
    export_mode: str | None = None
    aps_handoff_target: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    analysis_run_id: str | None = None
    external_export: Any | None = None
    external_target: Any | None = None
    download: Any | None = None
    download_url: Any | None = None
    destination: Any | None = None
    destination_selector: Any | None = None
    connector_run_id: Any | None = None
    connector_dispatch: Any | None = None
    dispatch: Any | None = None
    send: Any | None = None
    runtime_db_write: Any | None = None
    analysis_artifact: Any | None = None
    artifact_manifest: Any | None = None
    create_package: Any | None = None
    rebuild_package: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rewrite_output: Any | None = None
    edited_findings: Any | None = None
    result_review_amendment: Any | None = None
    package_review_amendment: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None


class Layer3ExternalExportDownloadPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    result_review_record_ref: str | None = None
    package_review_preview_hash: str | None = None
    reconciliation_record_id: str | None = None
    output_package_ids: Any | None = None
    package_kinds: Any | None = None
    payload_refs: Any | None = None
    payload_hashes: Any | None = None
    package_review_submit_record_ref: str | None = None
    package_review_state: str | None = None
    prepare_record_ref: str | None = None
    handoff_export_state: str | None = None
    handoff_export_envelope_ref: str | None = None
    handoff_target: str | None = None
    export_mode: str | None = None
    aps_handoff_record_ref: str | None = None
    aps_handoff_state: str | None = None
    aps_handoff_target: str | None = None
    dispatch_mode: str | None = None
    aps_output_package_id: str | None = None
    aps_output_package_kind: str | None = None
    aps_bundle_ref: str | None = None
    aps_bundle_id: str | None = None
    aps_schema_id: str | None = None
    export_download_target: str | None = None
    download_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    analysis_run_id: str | None = None
    aps_bundle_hash: str | None = None
    aps_bundle_size_bytes: int | None = None
    download: Any | None = None
    download_url: Any | None = None
    download_token: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    local_file_path: Any | None = None
    external_target: Any | None = None
    destination: Any | None = None
    destination_selector: Any | None = None
    connector_run_id: Any | None = None
    connector_dispatch: Any | None = None
    generic_dispatch: Any | None = None
    dispatch: Any | None = None
    send: Any | None = None
    runtime_db_write: Any | None = None
    analysis_artifact: Any | None = None
    artifact_manifest: Any | None = None
    create_package: Any | None = None
    rebuild_package: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rewrite_output: Any | None = None
    edited_findings: Any | None = None
    result_review_amendment: Any | None = None
    package_review_amendment: Any | None = None
    rerun: Any | None = None
    retry: Any | None = None
    recover: Any | None = None
    cancel: Any | None = None
    selected_pass_ids: Any | None = None
    pass_run_ids: Any | None = None
    new_analysis_plan: Any | None = None
    plan_revision: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    schema_migration: Any | None = None


class Layer3ProviderPrivateSignedUrlPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    external_export_download_record_ref: str | None = None
    export_download_descriptor_ref: str | None = None
    external_export_download_state: str | None = None
    export_download_target: str | None = None
    download_mode: str | None = None
    delivery_mode: str | None = None
    operator_decision: str | None = None
    source_artifact_hash: str | None = None
    source_artifact_size_bytes: int | None = None
    recipient_scope: str | None = None
    requested_ttl_seconds: int | None = None
    decision_notes: str | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_bucket: Any | None = None
    provider_container: Any | None = None
    provider_object_key: Any | None = None
    provider_object_identity: Any | None = None
    raw_provider_signature: Any | None = None
    raw_provider_object_key: Any | None = None
    raw_local_path: Any | None = None
    local_path: Any | None = None
    local_file_path: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    destination: Any | None = None
    destination_selector: Any | None = None
    connector_payload: Any | None = None
    connector_secret: Any | None = None
    connector_run_id: Any | None = None
    connector_dispatch: Any | None = None
    source_upload: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    web_connector: Any | None = None
    package_mutation: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    rag_vector_settings: Any | None = None
    rag_vector_state: Any | None = None
    prompt_model_settings: Any | None = None
    prompt_or_model_payload: Any | None = None
    auth_security_override: Any | None = None
    auth_internal_state: Any | None = None
    browser_durable_authority: Any | None = None
    public_url: Any | None = None
    public_proxy_url: Any | None = None
    provider_url: Any | None = None
    download_url: Any | None = None
    signed_reference_token: Any | None = None
    signed_url: Any | None = None
    provider_private_signed_url_token: Any | None = None
    raw_provider_private_signed_url_token: Any | None = None


class Layer3ProviderPrivateSignedUrlRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    provider_signed_url_receipt_id: str | None = None
    idempotency_key: str | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_bucket: Any | None = None
    provider_container: Any | None = None
    provider_object_key: Any | None = None
    provider_object_identity: Any | None = None
    raw_provider_signature: Any | None = None
    raw_provider_object_key: Any | None = None
    raw_local_path: Any | None = None
    local_path: Any | None = None
    local_file_path: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    destination: Any | None = None
    destination_selector: Any | None = None
    connector_payload: Any | None = None
    connector_secret: Any | None = None
    connector_run_id: Any | None = None
    connector_dispatch: Any | None = None
    source_upload: Any | None = None
    source_expansion: Any | None = None
    local_upload: Any | None = None
    local_directory: Any | None = None
    web_connector: Any | None = None
    package_mutation: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    rag_vector_settings: Any | None = None
    rag_vector_state: Any | None = None
    prompt_model_settings: Any | None = None
    prompt_or_model_payload: Any | None = None
    auth_security_override: Any | None = None
    auth_internal_state: Any | None = None
    browser_durable_authority: Any | None = None
    public_url: Any | None = None
    public_proxy_url: Any | None = None
    provider_url: Any | None = None
    download_url: Any | None = None
    signed_reference_token: Any | None = None
    signed_url: Any | None = None
    provider_private_signed_url_token: Any | None = None
    raw_provider_private_signed_url_token: Any | None = None


class Layer3ProviderPublicUrlPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    provider_private_signed_url_receipt_id: str | None = None
    recipient_scope: str | None = None
    requested_ttl_seconds: int | None = None
    delivery_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    raw_public_url: Any | None = None
    public_proxy_url: Any | None = None
    download_url: Any | None = None
    signed_url: Any | None = None
    provider_url: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_token: Any | None = None
    provider_bucket: Any | None = None
    provider_container: Any | None = None
    provider_object_key: Any | None = None
    provider_object_identity: Any | None = None
    raw_provider_signature: Any | None = None
    raw_provider_object_key: Any | None = None
    connector_dispatch: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    package_mutation: Any | None = None
    source_expansion: Any | None = None
    local_directory: Any | None = None
    web_connector: Any | None = None
    rag_vector_state: Any | None = None
    auth_security_override: Any | None = None
    browser_durable_authority: Any | None = None


class Layer3ProviderPublicUrlRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    provider_public_url_receipt_id: str | None = None
    idempotency_key: str | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    raw_public_url: Any | None = None
    public_proxy_url: Any | None = None
    download_url: Any | None = None
    signed_url: Any | None = None
    provider_url: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_token: Any | None = None
    provider_bucket: Any | None = None
    provider_container: Any | None = None
    provider_object_key: Any | None = None
    provider_object_identity: Any | None = None
    raw_provider_signature: Any | None = None
    raw_provider_object_key: Any | None = None
    connector_dispatch: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    package_mutation: Any | None = None
    source_expansion: Any | None = None
    local_directory: Any | None = None
    web_connector: Any | None = None
    rag_vector_state: Any | None = None
    auth_security_override: Any | None = None
    browser_durable_authority: Any | None = None


class Layer3ProviderPublicUrlDeliveryUseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    provider_public_url_receipt_id: str | None = None
    expected_authority_hash: str | None = None
    expected_source_artifact_hash: str | None = None
    expected_source_artifact_size_bytes: int | None = None
    delivery_use_mode: str | None = None
    operator_decision: str | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    raw_public_url: Any | None = None
    public_proxy_url: Any | None = None
    download_url: Any | None = None
    signed_url: Any | None = None
    provider_url: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_token: Any | None = None
    provider_bucket: Any | None = None
    provider_container: Any | None = None
    provider_object_key: Any | None = None
    provider_object_identity: Any | None = None
    raw_provider_signature: Any | None = None
    raw_provider_object_key: Any | None = None
    connector_dispatch: Any | None = None
    connector_run_id: Any | None = None
    destination_id: Any | None = None
    destination_url: Any | None = None
    package_mutation: Any | None = None
    source_expansion: Any | None = None
    source_payload: Any | None = None
    local_directory: Any | None = None
    local_path: Any | None = None
    web_connector: Any | None = None
    rag_vector_state: Any | None = None
    prompt_model_settings: Any | None = None
    prompt_or_model_payload: Any | None = None
    auth_security_override: Any | None = None
    browser_durable_authority: Any | None = None


class Layer3ConnectorDispatchRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    result_review_record_ref: str | None = None
    package_review_preview_hash: str | None = None
    output_package_ids: list[str] | None = None
    package_kinds: list[str] | None = None
    payload_refs: list[str] | None = None
    payload_hashes: list[str] | None = None
    package_review_submit_record_ref: str | None = None
    prepare_record_ref: str | None = None
    handoff_export_state: str | None = None
    aps_handoff_record_ref: str | None = None
    aps_handoff_state: str | None = None
    aps_handoff_target: str | None = None
    aps_output_package_id: str | None = None
    aps_output_package_kind: str | None = None
    aps_bundle_ref: str | None = None
    source_artifact_hash: str | None = None
    source_artifact_size_bytes: int | None = None
    external_export_download_record_ref: str | None = None
    external_export_download_state: str | None = None
    delivery_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    analysis_run_id: str | None = None
    external_export_download_descriptor_ref: str | None = None
    source_artifact_ref: str | None = None
    source_artifact_schema_id: str | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_secret: Any | None = None
    destination_id: Any | None = None
    destination_secret: Any | None = None
    destination_url: Any | None = None
    provider_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    bucket: Any | None = None
    object_key: Any | None = None
    local_path: Any | None = None
    local_file_path: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None


class Layer3ConnectorLocalDestinationReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    connector_dispatch_record_ref: str | None = None
    external_export_download_record_ref: str | None = None
    external_export_download_state: str | None = None
    destination_target: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_secret: Any | None = None
    destination_id: Any | None = None
    destination_secret: Any | None = None
    destination_url: Any | None = None
    provider_url: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    bucket: Any | None = None
    object_key: Any | None = None
    local_path: Any | None = None
    local_file_path: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    source_upload: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    credential: Any | None = None
    credentials: Any | None = None
    network_write: Any | None = None
    external_connector_invocation: Any | None = None
    destination_write: Any | None = None
    real_destination_integration: Any | None = None


class Layer3ServerOwnedLocalOutboxFakeTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    connector_dispatch_record_ref: str | None = None
    connector_local_destination_receipt_id: str | None = None
    connector_local_destination_receipt_state: str | None = None
    external_export_download_record_ref: str | None = None
    target_identity: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_run_target_id: Any | None = None
    connector_secret: Any | None = None
    destination_id: Any | None = None
    destination_path: Any | None = None
    destination_secret: Any | None = None
    destination_url: Any | None = None
    provider_url: Any | None = None
    provider_public_url: Any | None = None
    provider_public_delivery: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    bucket: Any | None = None
    object_key: Any | None = None
    local_path: Any | None = None
    local_file_path: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    source_upload: Any | None = None
    source_expansion: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    credential: Any | None = None
    credentials: Any | None = None
    network_write: Any | None = None
    external_connector_invocation: Any | None = None
    destination_write: Any | None = None
    real_destination_integration: Any | None = None
    auth_policy: Any | None = None
    security_override: Any | None = None
    frontend_durable_authority: Any | None = None
    full_mockup_activation: Any | None = None


class Layer3ServerOwnedLocalOutboxWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    connector_dispatch_record_ref: str | None = None
    connector_local_destination_receipt_id: str | None = None
    server_owned_local_outbox_target_receipt_id: str | None = None
    server_owned_local_outbox_target_state: str | None = None
    external_export_download_record_ref: str | None = None
    target_identity: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    connector_key: Any | None = None
    connector_run_id: Any | None = None
    connector_run_target_id: Any | None = None
    connector_secret: Any | None = None
    destination_id: Any | None = None
    destination_path: Any | None = None
    destination_secret: Any | None = None
    destination_url: Any | None = None
    provider_url: Any | None = None
    provider_public_url: Any | None = None
    provider_public_delivery: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    download_url: Any | None = None
    bucket: Any | None = None
    object_key: Any | None = None
    local_path: Any | None = None
    local_file_path: Any | None = None
    package_payload: Any | None = None
    package_variant_content: Any | None = None
    rebuild_package: Any | None = None
    rewrite_output: Any | None = None
    source_upload: Any | None = None
    source_expansion: Any | None = None
    local_directory: Any | None = None
    rag_vector_index: Any | None = None
    runtime_db_write: Any | None = None
    retry: Any | None = None
    rerun: Any | None = None
    cancel: Any | None = None
    hybrid_execution: Any | None = None
    rag_execution: Any | None = None
    hidden_llm_planning: Any | None = None
    credential: Any | None = None
    credentials: Any | None = None
    network_write: Any | None = None
    external_connector_invocation: Any | None = None
    destination_write: Any | None = None
    real_destination_integration: Any | None = None
    auth_policy: Any | None = None
    security_override: Any | None = None
    frontend_durable_authority: Any | None = None
    full_mockup_activation: Any | None = None


class Layer3LocalOutboxProviderPrivateHandoffPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    connector_dispatch_record_ref: str | None = None
    connector_local_destination_receipt_id: str | None = None
    server_owned_local_outbox_target_receipt_id: str | None = None
    server_owned_local_outbox_write_receipt_id: str | None = None
    external_export_download_record_ref: str | None = None
    target_identity: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    recipient_scope: str | None = None
    requested_ttl_seconds: int | None = None
    decision_notes: str | None = None


class Layer3ExternalLocalExportWriteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    connector_dispatch_record_ref: str | None = None
    connector_local_destination_receipt_id: str | None = None
    server_owned_local_outbox_target_receipt_id: str | None = None
    server_owned_local_outbox_write_receipt_id: str | None = None
    provider_private_handoff_receipt_id: str | None = None
    external_export_download_record_ref: str | None = None
    target_identity: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None


class Layer3InternalWebhookDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str | None = None
    session_id: str | None = None
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    reconciliation_record_id: str | None = None
    connector_dispatch_record_ref: str | None = None
    connector_local_destination_receipt_id: str | None = None
    server_owned_local_outbox_target_receipt_id: str | None = None
    server_owned_local_outbox_write_receipt_id: str | None = None
    external_export_download_record_ref: str | None = None
    target_identity: str | None = None
    target_class: str | None = None
    dispatch_mode: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None


class Layer3SourceDirectoryIngestionScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    operator_decision: Literal["scan_server_configured_operator_directory"]
    source_family: Literal["server_configured_operator_directory_text_table_source_family"] | None = None
    ingestion_mode: Literal["server_configured_operator_directory_text_table_ingestion"] | None = None


class Layer3CandidateBBundleMaterialBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    bridge_mode: Literal["candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1"]
    candidate_b_bundle_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    operator_confirmation: bool


class Layer3CandidateBRuntimeMaterialBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    bridge_mode: Literal["candidate_b_runtime_source_to_layer3_material_authority_v1"]
    candidate_b_run_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    operator_confirmation: bool


class Layer3CandidateBArtifactFamilyStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_retained_artifact_family_status_v1"]
    operator_decision: Literal["inspect_candidate_b_governed_retained_artifact_family_status"]
    candidate_b_source_kind: Literal["bundle", "runtime"]
    bridge_receipt_id: str = Field(min_length=1)


class Layer3CandidateBVisualLaneStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_visual_lane_status_v1"]
    operator_decision: Literal["inspect_candidate_b_visual_lane_evidence_status"]
    candidate_b_run_id: str = Field(min_length=1)
    bridge_receipt_id: str = Field(min_length=1)


class Layer3CandidateBBundleDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["candidate_b_bundle_downstream_e2e_proof_v1"]
    operator_decision: Literal["record_candidate_b_bundle_downstream_e2e_proof"]
    candidate_b_bundle_id: str = Field(min_length=1)
    bridge_receipt_id: str = Field(min_length=1)
    coverage_evidence: dict[str, Any]
    operator_confirmation: bool


class Layer3CandidateBRuntimeDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["candidate_b_visual_lane_runtime_downstream_e2e_proof_v1"]
    operator_decision: Literal["record_candidate_b_visual_lane_runtime_downstream_e2e_proof"]
    candidate_b_run_id: str = Field(min_length=1)
    bridge_receipt_id: str = Field(min_length=1)
    candidate_b_visual_lane_status_evidence: dict[str, Any]
    coverage_evidence: dict[str, Any]
    operator_confirmation: bool


class Layer3CandidateBDefaultPromotionOperatorStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_default_promotion_operator_status_v1"]
    operator_decision: Literal["inspect_candidate_b_default_promotion_operator_status"]
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    candidate_b_bundle_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    candidate_b_bundle_bridge_receipt_id: str = Field(min_length=1)
    candidate_b_runtime_bridge_receipt_id: str = Field(min_length=1)
    candidate_b_visual_lane_status_evidence: dict[str, Any]
    runtime_downstream_proof: dict[str, Any]


class Layer3CandidateBDefaultPromotionClosureEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    closure_mode: Literal["candidate_b_default_promotion_closure_evidence_v1"]
    operator_decision: Literal["record_candidate_b_default_promotion_closure_evidence"]
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    candidate_b_bundle_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    candidate_b_bundle_bridge_receipt_id: str = Field(min_length=1)
    candidate_b_runtime_bridge_receipt_id: str = Field(min_length=1)
    eligible_corpus_scope: str = Field(min_length=1)
    regression_disposition: str = Field(min_length=1)
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool
    bundle_downstream_proof: dict[str, Any]
    runtime_downstream_proof: dict[str, Any]
    operator_status_evidence: dict[str, Any]


class Layer3CandidateBDefaultPromotionReadinessAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    readiness_mode: Literal["candidate_b_default_promotion_readiness_audit_v1"]
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    candidate_b_bundle_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    candidate_b_bundle_bridge_receipt_id: str = Field(min_length=1)
    candidate_b_runtime_bridge_receipt_id: str = Field(min_length=1)
    eligible_corpus_scope: str = Field(min_length=1)
    regression_disposition: str = Field(min_length=1)
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool
    bundle_downstream_proof: dict[str, Any]
    runtime_downstream_proof: dict[str, Any]
    candidate_b_visual_lane_status_evidence: dict[str, Any]
    operator_status_evidence: dict[str, Any]
    closure_evidence: dict[str, Any]


class Layer3CandidateBDefaultPromotionFinalProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["candidate_b_default_promotion_final_proof_v1"]
    operator_decision: Literal["record_candidate_b_default_promotion_final_proof"]
    readiness_audit: dict[str, Any]
    operator_confirmation: bool


class Layer3CandidateBDefaultPromotionFinalProofStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_default_promotion_final_proof_status_v1"]
    operator_decision: Literal["inspect_candidate_b_default_promotion_final_proof_status"]
    candidate_b_runtime_bridge_receipt_id: str = Field(min_length=1)
    proof_receipt_id: str = Field(min_length=1)


class Layer3SourceDirectoryMaterialPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    source_ingestion_batch_id: str = Field(min_length=1)
    source_ingestion_file_id: str = Field(min_length=1)
    file_identity_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    max_chars: int | None = None
    actor: str | None = None


class Layer3SourceDirectoryHybridAuthorityPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    material_snapshot_id: str | None = Field(default=None, min_length=1)
    analysis_question: str | None = Field(default=None, min_length=1)
    analysis_focus: str | None = Field(default=None, min_length=1)
    query_text: str | None = Field(default=None, min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    limit: int | None = Field(default=None, ge=1, le=50)
    offset: int | None = Field(default=None, ge=0)


class Layer3SourceDirectoryVectorRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    material_snapshot_id: str = Field(min_length=1)
    source_ingestion_batch_id: str = Field(min_length=1)
    source_ingestion_file_id: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)
    file_identity_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    payload_hash: str = Field(min_length=64, max_length=64)
    index_authority_hash: str = Field(min_length=64, max_length=64)
    embedding_index_authority_hash: str = Field(min_length=64, max_length=64)
    query_text: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Layer3SourceDirectoryHybridContextPacketRequest(Layer3SourceDirectoryVectorRetrievalRequest):
    limit: int | None = Field(default=None, ge=1, le=50)
    offset: int | None = Field(default=None, ge=0)


class Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest(
    Layer3SourceDirectoryHybridContextPacketRequest
):
    analysis_question: str = Field(min_length=1)
    analysis_focus: str = Field(min_length=1)


class Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest
):
    client_request_id: str | None = Field(default=None, min_length=1)


class Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest
):
    qualitative_analysis_hash: str = Field(min_length=64, max_length=64)
    source_directory_hybrid_package_review_preview_hash: str = Field(min_length=64, max_length=64)
    operator_decision: Literal["commit_source_directory_hybrid_context_packet_qualitative_analysis_package"]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest
):
    qualitative_analysis_hash: str = Field(min_length=64, max_length=64)
    source_directory_hybrid_package_review_preview_hash: str = Field(min_length=64, max_length=64)
    construction_basis_hash: str = Field(min_length=64, max_length=64)
    reconciliation_record_id: str = Field(min_length=1)
    output_package_ids: list[str] = Field(min_length=1)
    package_kinds: list[str] = Field(min_length=1)
    payload_hashes: list[str] = Field(min_length=1)
    operator_decision: Literal["approved", "changes_requested", "rejected", "blocked"]
    decision_notes: str | None = None


class Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitRequest
):
    package_review_submit_record_ref: str = Field(min_length=1)
    package_review_state: Literal["package_review_approved"]
    handoff_target: Literal["internal_export_envelope"]
    export_mode: Literal["prepare_only"]
    operator_decision: Literal["authorize_prepare", "hold", "decline", "blocked"]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareRequest
):
    prepare_record_ref: str = Field(min_length=1)
    handoff_export_state: Literal["handoff_export_prepared"]
    handoff_export_envelope_ref: str = Field(min_length=1)
    external_export_download_target: Literal[
        "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
    ]
    download_mode: Literal["reference_only_prepare"]
    operator_decision: Literal["prepare_source_directory_hybrid_external_export_download"]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareRequest
):
    external_export_download_record_ref: str = Field(min_length=1)
    export_download_descriptor_ref: str = Field(min_length=1)
    external_export_download_state: Literal["external_export_download_prepared"]
    target_identity: Literal["server_configured_internal_webhook_destination"]
    target_class: Literal["real_connector_invocation"]
    dispatch_mode: Literal["server_configured_allowlisted_internal_webhook_post"]
    operator_decision: Literal["dispatch_source_directory_hybrid_internal_webhook"]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareRequest
):
    external_export_download_record_ref: str = Field(min_length=1)
    export_download_descriptor_ref: str = Field(min_length=1)
    external_export_download_state: Literal["external_export_download_prepared"]
    delivery_mode: Literal["same_origin_artifact_stream"]
    output_package_id: str = Field(min_length=1)
    package_kind: Literal["canonical_internal", "user_facing", "review_facing"]
    package_payload_hash: str = Field(min_length=64, max_length=64)
    operator_decision: Literal["deliver_source_directory_hybrid_external_export_download"]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest
):
    delivery_mode: Literal["provider_private_signed_url"]
    recipient_scope: str = Field(min_length=1)
    requested_ttl_seconds: int | None = Field(default=None, ge=1, le=900)
    operator_decision: Literal["prepare_source_directory_hybrid_provider_private_signed_url"]
    provider_private_signed_url_token: Any | None = None
    raw_provider_private_signed_url_token: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_public_url: Any | None = None
    raw_public_url: Any | None = None
    raw_provider_url: Any | None = None


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest
):
    delivery_mode: Literal["provider_private_signed_url"]
    provider_signed_url_receipt_id: str = Field(min_length=1)
    operator_decision: Literal["use_source_directory_hybrid_provider_private_signed_url"]
    provider_private_signed_url_token: Any | None = None
    raw_provider_private_signed_url_token: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_public_url: Any | None = None
    raw_public_url: Any | None = None
    raw_provider_url: Any | None = None


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest
):
    delivery_mode: Literal["provider_private_signed_url"]
    provider_signed_url_receipt_id: str = Field(min_length=1)
    operator_decision: Literal["inspect_source_directory_hybrid_provider_private_signed_url_status"]
    provider_private_signed_url_token: Any | None = None
    raw_provider_private_signed_url_token: Any | None = None
    provider_credentials: Any | None = None
    provider_secret: Any | None = None
    provider_public_url: Any | None = None
    raw_public_url: Any | None = None
    raw_provider_url: Any | None = None


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeRequest(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusRequest
):
    operator_decision: Literal["revoke_source_directory_hybrid_provider_private_signed_url"]
    idempotency_key: str = Field(min_length=1)
    revoked_by: str = Field(min_length=1)
    revocation_reason: str = Field(min_length=1)


class Layer3SourceDirectoryQualitativeAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    analysis_question: str = Field(min_length=1)
    analysis_focus: str = Field(min_length=1)
    material_snapshot_id: str = Field(min_length=1)
    source_ingestion_batch_id: str = Field(min_length=1)
    source_ingestion_file_id: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)
    file_identity_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    payload_hash: str = Field(min_length=64, max_length=64)
    index_authority_hash: str = Field(min_length=64, max_length=64)
    query_text: str = Field(min_length=1)
    limit: int | None = Field(default=None, ge=1, le=50)
    offset: int | None = Field(default=None, ge=0)


class Layer3SourceDirectoryQualitativeAnalysisPackageCommitRequest(
    Layer3SourceDirectoryQualitativeAnalysisRequest
):
    qualitative_analysis_hash: str = Field(min_length=64, max_length=64)
    source_directory_package_review_preview_hash: str = Field(min_length=64, max_length=64)
    operator_decision: Literal["commit_source_directory_qualitative_analysis_package"]


class Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitRequest(
    Layer3SourceDirectoryQualitativeAnalysisRequest
):
    qualitative_analysis_hash: str = Field(min_length=64, max_length=64)
    source_directory_package_review_preview_hash: str = Field(min_length=64, max_length=64)
    construction_basis_hash: str = Field(min_length=64, max_length=64)
    reconciliation_record_id: str = Field(min_length=1)
    output_package_ids: list[str] = Field(min_length=3, max_length=3)
    package_kinds: list[str] = Field(min_length=3, max_length=3)
    payload_hashes: list[str] = Field(min_length=3, max_length=3)
    operator_decision: Literal["approved", "changes_requested", "rejected", "blocked"]
    decision_notes: str | None = None


class Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewRequest(
    Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitRequest
):
    package_review_submit_record_ref: str = Field(min_length=1)
    package_review_state: Literal["package_review_approved"]
    operator_decision: Literal["preview_source_directory_package_supersession"]


class Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareRequest(
    Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitRequest
):
    package_review_submit_record_ref: str = Field(min_length=1)
    package_review_state: Literal["package_review_approved"]
    handoff_target: Literal["internal_export_envelope"]
    export_mode: Literal["prepare_only"]
    operator_decision: Literal["authorize_prepare", "hold", "decline", "blocked"]


class Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareRequest(
    Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareRequest
):
    prepare_record_ref: str = Field(min_length=1)
    handoff_export_state: Literal["handoff_export_prepared"]
    handoff_export_envelope_ref: str = Field(min_length=1)
    external_export_download_target: Literal["source_directory_qualitative_analysis_package_download_reference"]
    download_mode: Literal["reference_only_prepare"]
    operator_decision: Literal["prepare_source_directory_external_export_download"]


class Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliverRequest(
    Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareRequest
):
    external_export_download_record_ref: str = Field(min_length=1)
    export_download_descriptor_ref: str = Field(min_length=1)
    external_export_download_state: Literal["external_export_download_prepared"]
    delivery_mode: Literal["same_origin_artifact_stream"]
    output_package_id: str = Field(min_length=1)
    package_kind: Literal["canonical_internal", "user_facing", "review_facing"]
    package_payload_hash: str = Field(min_length=64, max_length=64)
    operator_decision: Literal["deliver_source_directory_external_export_download"]


class Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliveryStatusResponse(Layer3BaseResponse):
    mode: str
    delivery_status: str
    delivery_available: bool
    delivery_streaming_performed: bool
    delivery_state: str
    source_gate: str
    validated_delivery_source_gate: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    output_package_id: str
    package_kind: str
    package_payload_hash: str
    payload_ref_redacted: bool
    raw_local_path_exposed: bool
    same_origin_delivery_enabled: bool
    browser_managed_same_origin_attachment_enabled: bool
    provider_public_delivery_enabled: bool
    provider_private_signed_url_enabled: bool
    connector_dispatch_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    package_payload_rewrite_enabled: bool
    source_package_row_mutation_enabled: bool
    delivery_headers: dict[str, str]
    delivery_authority: dict[str, Any]
    next_allowed_actions: list[str]


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


class Layer3SourceIntakeRecordResponse(Layer3BaseResponse):
    source_intake_record_id: str
    source_intake_mode: str
    source_family: str
    source_label: str
    source_identity: dict[str, Any]
    source_provenance: dict[str, Any]
    storage_pointer: dict[str, Any]
    content_sha256: str
    metadata_hash: str
    authority_basis_hash: str
    downstream_eligibility: dict[str, Any]
    source_gate: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryIngestionResponse(Layer3BaseResponse):
    source_ingestion_batch_id: str
    runtime_policy_id: str | None = None
    source_family: str
    ingestion_mode: str
    config_authority: str
    source_root_ref: str
    source_root_absolute_path_exposed: bool
    direct_child_only: bool
    recursive_traversal_admitted: bool | None = None
    max_recursion_depth: int | None = None
    max_relative_path_segments: int | None = None
    caller_selected_recursive_flag_allowed: bool | None = None
    allowed_extensions: list[str]
    eligible_file_count: int
    total_size_bytes: int
    directory_fingerprint_hash: str
    authority_basis_hash: str
    authority_snapshot: dict[str, Any]
    files: list[dict[str, Any]]
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3CandidateBBundleMaterialBridgeResponse(Layer3BaseResponse):
    mode: str
    bridge_receipt_id: str
    bridge_receipt_ref: str
    curated_material_root_ref: str
    curated_root_absolute_path_exposed: bool
    bridge_config_authority: str
    source_ingestion_config_authority: str
    source_ingestion_required_root_ref: str
    source_ingestion_mode: str
    candidate_b_bundle_id: str
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_source_kind: str
    candidate_b_bundle_validation: dict[str, Any]
    compare_target_set: dict[str, Any]
    admitted_artifact_subset: dict[str, Any]
    excluded_artifact_subset: dict[str, Any]
    governed_retained_artifact_family: dict[str, Any]
    authority_hashes: dict[str, str]
    provenance: dict[str, Any]
    layer3_material_preview_compatible: bool
    gate_b_material_authority_compatible: bool
    layer3_compatibility: dict[str, Any]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBRuntimeMaterialBridgeResponse(Layer3BaseResponse):
    mode: str
    bridge_receipt_id: str
    bridge_receipt_ref: str
    curated_material_root_ref: str
    curated_root_absolute_path_exposed: bool
    bridge_config_authority: str
    source_ingestion_config_authority: str
    source_ingestion_required_root_ref: str
    source_ingestion_mode: str
    candidate_b_run_id: str
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_source_kind: str
    document_processing_engine: str
    candidate_b_runtime_validation: dict[str, Any]
    compare_target_set: dict[str, Any]
    admitted_artifact_subset: dict[str, Any]
    excluded_artifact_subset: dict[str, Any]
    governed_retained_artifact_family: dict[str, Any]
    authority_hashes: dict[str, str]
    provenance: dict[str, Any]
    layer3_material_preview_compatible: bool
    gate_b_material_authority_compatible: bool
    layer3_compatibility: dict[str, Any]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBArtifactFamilyStatusResponse(Layer3BaseResponse):
    mode: str
    candidate_b_source_kind: str
    bridge_receipt_id: str
    bridge_receipt_ref: str
    bridge_receipt_hash: str
    governed_retained_artifact_family_hash: str
    artifact_family_status: str
    governed_retained_artifact_family: dict[str, Any]
    operator_projection: dict[str, Any]
    material_text_payload_policy: str | None
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBVisualLaneStatusResponse(Layer3BaseResponse):
    mode: str
    candidate_b_source_kind: str
    candidate_b_run_id: str
    bridge_receipt_id: str
    bridge_receipt_ref: str
    bridge_receipt_hash: str
    document_processing_engine: str
    visual_lane_mode: str
    visual_lane_status: str
    candidate_b_visual_lane_evidence: dict[str, Any]
    operator_projection: dict[str, Any]
    material_policy: dict[str, bool]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBRuntimeDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    candidate_b_source_kind: str
    candidate_b_run_id: str
    bridge_receipt_id: str
    bridge_receipt_hash: str
    document_processing_engine: str
    visual_lane_mode: str
    candidate_b_visual_lane_status_hash: str
    proof_state: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    coverage: list[str]
    coverage_evidence: dict[str, Any]
    coverage_evidence_hash: str
    raw_local_path_exposed: bool
    provider_private_token_exposed: bool
    provider_public_url_enabled: bool
    provider_object_writes_enabled: bool
    connector_dispatch_enabled: bool
    candidate_b_default_promotion_enabled: bool
    visual_lane_mode_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBundleDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    candidate_b_source_kind: str
    candidate_b_bundle_id: str
    bridge_receipt_id: str
    bridge_receipt_hash: str
    coverage_evidence_hash: str
    negative_invariants_hash: str
    operator_confirmation: bool
    proof_state: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    coverage: list[str]
    coverage_evidence: dict[str, Any]
    raw_local_path_exposed: bool
    provider_private_token_exposed: bool
    provider_public_url_enabled: bool
    provider_object_writes_enabled: bool
    connector_dispatch_enabled: bool
    candidate_b_default_promotion_enabled: bool
    visual_lane_mode_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBDefaultPromotionOperatorStatusResponse(Layer3BaseResponse):
    mode: str
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_bundle_id: str
    candidate_b_run_id: str
    bundle_bridge_receipt_id: str
    bundle_bridge_receipt_hash: str
    runtime_bridge_receipt_id: str
    runtime_bridge_receipt_hash: str
    candidate_b_visual_lane_status_hash: str
    runtime_downstream_proof_hash: str
    operator_visible_provenance_status: bool
    bundle_status_projection_visible: bool
    runtime_status_projection_visible: bool
    default_selector_change_visible_as_enabled: bool
    operator_status_hash: str
    operator_status_receipt_id: str
    operator_status_receipt_ref: str
    candidate_b_source_kind: str
    raw_local_path_exposed: bool
    provider_private_token_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBDefaultPromotionClosureEvidenceResponse(Layer3BaseResponse):
    mode: str
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_bundle_id: str
    candidate_b_run_id: str
    bundle_bridge_receipt_id: str
    bundle_bridge_receipt_hash: str
    runtime_bridge_receipt_id: str
    runtime_bridge_receipt_hash: str
    bundle_downstream_proof_hash: str
    runtime_downstream_proof_hash: str
    operator_status_hash: str
    eligible_corpus_scope: str
    regression_disposition: str
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool
    closure_evidence_hash: str
    closure_receipt_id: str
    closure_receipt_ref: str
    rollback_selector: str
    selector_mutation_performed: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    provider_private_token_exposed: bool
    artifact_bytes_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBDefaultPromotionReadinessAuditResponse(Layer3BaseResponse):
    mode: str
    readiness_state: str
    readiness_audit_id: str
    readiness_audit_hash: str
    blocked_reasons: list[dict[str, Any]]
    baseline_current_default_evidence: dict[str, Any]
    candidate_a_admitted_variant_evidence: dict[str, Any]
    candidate_b_selector_evidence: dict[str, Any]
    selected_evidence: dict[str, Any]
    bridge_receipts: dict[str, Any]
    compare_target_sets: dict[str, Any]
    authority_hashes: dict[str, Any]
    downstream_proofs: dict[str, Any]
    candidate_b_visual_lane_status_evidence: dict[str, Any]
    operator_status_evidence: dict[str, Any]
    closure_evidence: dict[str, Any]
    candidate_b_final_operator_inspection_evidence: dict[str, Any]
    rollback_to_baseline: dict[str, Any]
    regression_disposition: str
    fail_closed_behavior: dict[str, bool]
    default_selector_change_enabled: bool
    candidate_b_default_promotion_enabled: bool
    selector_mutation_performed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBDefaultPromotionFinalProofResponse(Layer3BaseResponse):
    mode: str
    readiness_audit_id: str
    readiness_audit_hash: str
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_bundle_id: str
    candidate_b_run_id: str
    bundle_bridge_receipt_hash: str
    runtime_bridge_receipt_hash: str
    bundle_downstream_proof_hash: str
    runtime_downstream_proof_hash: str
    candidate_b_visual_lane_status_hash: str
    operator_status_hash: str
    closure_evidence_hash: str
    final_operator_inspection_hash: str
    default_selector_change_enabled: bool
    candidate_b_default_promotion_enabled: bool
    rollback_selector: str
    final_operator_inspection_complete: bool
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    proof_state: str
    selector_mutation_performed: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    provider_private_token_exposed: bool
    artifact_bytes_exposed: bool
    candidate_b_final_operator_inspection_evidence: dict[str, Any]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBDefaultPromotionFinalProofStatusResponse(Layer3BaseResponse):
    mode: str
    proof_state: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    readiness_audit_id: str
    readiness_audit_hash: str
    candidate_b_run_id: str
    candidate_b_bundle_id: str
    candidate_b_default_promotion_enabled: bool
    default_selector_change_enabled: bool
    rollback_selector: str
    final_operator_inspection_complete: bool
    candidate_b_final_operator_inspection_evidence: dict[str, Any]
    selector_mutation_performed: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    provider_private_token_exposed: bool
    artifact_bytes_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryMaterialPreviewResponse(Layer3BaseResponse):
    source_gate: dict[str, Any]
    source_directory_preview_mode: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_preview_id: str
    material_preview_hash: str
    material_candidate: dict[str, Any]
    partial_retrieval: bool
    downstream_eligibility: dict[str, bool]
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryHybridAuthorityPrepareResponse(Layer3BaseResponse):
    mode: str
    session_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    index_authority_hash: str
    embedding_index_authority_hash: str
    authority_prepare_hash: str
    authority_payload: dict[str, Any]
    redaction_guards: dict[str, bool]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryVectorRetrievalResponse(Layer3BaseResponse):
    mode: str
    retrieval_contract_id: str
    retrieval_mode: str
    query_tokens: list[str]
    top_k: int
    total: int
    items: list[dict[str, Any]]
    embedding_contract_id: str
    embedding_mode: str
    vector_index_mode: str
    feature_hash_version: str
    vector_dimensions: int
    embedding_index_authority_hash: str
    index_contract_id: str
    index_mode: str
    segmentation_version: str
    index_authority_hash: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_snapshot_id: str
    source_shape: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryHybridContextPacketResponse(Layer3BaseResponse):
    mode: str
    hybrid_context_contract_id: str
    hybrid_context_mode: str
    source_gate: str
    hybrid_context_packet_hash: str
    lexical_context_packet_hash: str
    lexical_context_packet_contract_id: str
    lexical_context_packet_mode: str
    vector_retrieval_contract_id: str
    vector_retrieval_mode: str
    embedding_contract_id: str
    embedding_mode: str
    vector_index_mode: str
    feature_hash_version: str
    vector_dimensions: int
    query_tokens: list[str]
    lexical_total: int
    lexical_limit: int
    lexical_offset: int
    vector_total: int
    vector_top_k: int
    hybrid_total: int
    items: list[dict[str, Any]]
    index_authority_hash: str
    embedding_index_authority_hash: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_snapshot_id: str
    source_shape: str | None
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    source_index_rows_written: bool
    embedding_vector_rows_written: bool
    vector_index_rows_written: bool
    retrieval_rows_written: bool
    context_packet_rows_written: bool
    qualitative_analysis_rows_written: bool
    analysis_run_rows_written: bool
    package_rows_written: bool
    connector_rows_written: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisResponse(Layer3BaseResponse):
    mode: str
    analysis_contract_id: str
    analysis_mode: str
    source_gate: str
    qualitative_analysis_hash: str
    analysis_question: str
    analysis_focus: str
    hybrid_context_packet_hash: str
    hybrid_context_contract_id: str
    hybrid_context_mode: str
    validated_hybrid_context_schema_id: str
    validated_hybrid_context_mode: str
    lexical_context_packet_hash: str
    lexical_context_packet_contract_id: str
    lexical_context_packet_mode: str
    vector_retrieval_contract_id: str
    vector_retrieval_mode: str
    embedding_contract_id: str
    embedding_mode: str
    vector_index_mode: str
    feature_hash_version: str
    vector_dimensions: int
    query_tokens: list[str]
    evidence_summary: dict[str, Any]
    salient_terms: list[dict[str, Any]]
    supporting_segments: list[dict[str, Any]]
    coverage_notes: list[dict[str, Any]]
    analysis_limits: list[dict[str, Any]]
    lexical_total: int
    lexical_limit: int
    lexical_offset: int
    vector_total: int
    vector_top_k: int
    hybrid_total: int
    index_authority_hash: str
    embedding_index_authority_hash: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_snapshot_id: str
    source_shape: str | None
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    source_directory_package_review_preview_enabled: bool
    source_directory_hybrid_package_review_preview_hash: str
    source_directory_hybrid_package_review_preview: dict[str, Any]
    candidate_package_kinds: list[str]
    package_commit_enabled: bool
    package_review_submit_enabled: bool
    handoff_enabled: bool
    external_export_download_enabled: bool
    source_index_rows_written: bool
    embedding_vector_rows_written: bool
    vector_index_rows_written: bool
    retrieval_rows_written: bool
    context_packet_rows_written: bool
    qualitative_analysis_rows_written: bool
    qualitative_generation_rows_written: bool
    analysis_run_rows_written: bool
    package_rows_written: bool
    connector_rows_written: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusResponse(Layer3BaseResponse):
    mode: str
    analysis_status: str
    source_gate: str
    validated_analysis_schema_id: str
    validated_analysis_mode: str
    analysis_contract_id: str
    analysis_mode: str
    qualitative_analysis_hash: str
    hybrid_context_packet_hash: str
    hybrid_context_contract_id: str
    hybrid_context_mode: str
    validated_hybrid_context_schema_id: str
    validated_hybrid_context_mode: str
    lexical_context_packet_hash: str
    lexical_context_packet_contract_id: str
    lexical_context_packet_mode: str
    vector_retrieval_contract_id: str
    vector_retrieval_mode: str
    embedding_contract_id: str
    embedding_mode: str
    vector_index_mode: str
    feature_hash_version: str
    vector_dimensions: int
    query_tokens: list[str]
    coverage_label: str
    supporting_segment_count: int
    salient_term_count: int
    coverage_note_count: int
    analysis_limit_count: int
    lexical_total: int
    lexical_limit: int
    lexical_offset: int
    vector_total: int
    vector_top_k: int
    hybrid_total: int
    index_authority_hash: str
    embedding_index_authority_hash: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_snapshot_id: str
    source_shape: str | None
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    source_directory_package_review_preview_available: bool
    source_directory_hybrid_package_review_preview_hash: str
    source_directory_hybrid_package_review_preview_payload_redacted: bool
    supporting_segments_redacted: bool
    analysis_result_redacted: bool
    source_directory_hybrid_package_commit_available: bool
    source_directory_hybrid_package_review_submit_available: bool
    source_directory_hybrid_handoff_export_prepare_available: bool
    source_directory_hybrid_external_export_download_prepare_available: bool
    reconciliation_record_id: str | None
    construction_basis_hash: str | None
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str | None
    package_review_submit_record_ref: str | None
    handoff_export_state: str | None
    handoff_export_prepare_record_ref: str | None
    handoff_target: str | None
    export_mode: str | None
    external_export_download_record_ref: str | None
    external_export_download_state: str | None
    external_export_download_target: str | None
    export_download_descriptor_ref: str | None
    download_mode: str | None
    package_review_submit_enabled: bool
    handoff_enabled: bool
    export_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    provider_private_signed_url_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    downstream_unavailable: list[str]
    status_defects: list[str]
    source_index_rows_written: bool
    embedding_vector_rows_written: bool
    vector_index_rows_written: bool
    retrieval_rows_written: bool
    context_packet_rows_written: bool
    qualitative_analysis_rows_written: bool
    qualitative_generation_rows_written: bool
    analysis_run_rows_written: bool
    package_rows_written: bool
    connector_rows_written: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    embedding_index_authority_hash: str
    lexical_context_packet_hash: str
    hybrid_context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_hybrid_package_review_preview_hash: str
    construction_basis_hash: str | None
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_rows_written: bool
    package_payloads_written: bool
    source_package_row_mutation_enabled: bool
    package_payload_rewrite_enabled: bool
    package_review_submit_enabled: bool
    handoff_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_construction_source_gate: str
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    decision_notes: str | None
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    embedding_index_authority_hash: str
    lexical_context_packet_hash: str
    hybrid_context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_hybrid_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str
    submit_record_ref: str
    package_review_submit_enabled: bool
    handoff_enabled: bool
    export_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_construction_source_gate: str
    source_gate: str
    downstream_unavailable: list[str]
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    decision_notes: str | None
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    embedding_index_authority_hash: str
    lexical_context_packet_hash: str
    hybrid_context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_hybrid_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str
    package_review_submit_record_ref: str
    handoff_export_state: str
    prepare_record_ref: str
    handoff_target: str
    export_mode: str
    handoff_export_envelope: dict[str, Any]
    handoff_enabled: bool
    export_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    provider_private_signed_url_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_review_submit_source_gate: str
    package_construction_source_gate: str
    source_gate: str
    downstream_unavailable: list[str]
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareResponse(
    Layer3BaseResponse
):
    mode: str
    operator_decision: str
    decision_notes: str | None
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    embedding_index_authority_hash: str
    lexical_context_packet_hash: str
    hybrid_context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_hybrid_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str
    package_review_submit_record_ref: str
    handoff_export_state: str
    prepare_record_ref: str
    handoff_export_envelope_ref: str
    handoff_target: str
    export_mode: str
    external_export_download_state: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    external_export_download_target: str
    download_mode: str
    external_export_download_descriptor: dict[str, Any]
    same_origin_delivery_enabled: bool
    browser_download_enabled: bool
    provider_public_delivery_enabled: bool
    provider_private_signed_url_enabled: bool
    connector_dispatch_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_review_submit_source_gate: str
    package_construction_source_gate: str
    source_gate: str
    downstream_unavailable: list[str]
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchResponse(
    Layer3BaseResponse
):
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    reconciliation_record_id: str
    source_directory_internal_webhook_dispatch_receipt_id: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    package_review_submit_record_ref: str
    handoff_export_prepare_ref: str
    handoff_export_envelope_ref: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    package_set_hash: str
    target_identity: str
    target_class: str
    dispatch_mode: str
    source_directory_internal_webhook_dispatch_state: str
    dispatch_operation_state: str
    redacted_destination_display_name: str
    idempotency_key: str
    request_basis_hash: str
    authority_basis_hash: str
    response_status_code: int | None
    redacted_response_summary: dict[str, Any]
    failure_code: str | None
    audit_receipt: dict[str, Any]
    server_configured_internal_webhook_enabled: bool
    source_directory_internal_webhook_post_performed: bool
    real_connector_invocation_enabled: bool
    server_configured_allowlisted_url_enabled: bool
    operator_destination_url_enabled: bool
    raw_target_url_exposed: bool
    raw_token_exposed: bool
    raw_headers_exposed: bool
    raw_local_path_exposed: bool
    raw_package_payload_exposed: bool
    raw_package_bytes_exposed: bool
    connector_dispatch_enabled: bool
    connector_run_created: bool
    connector_run_target_created: bool
    credentials_enabled: bool
    provider_public_url_enabled: bool
    provider_private_signed_url_enabled: bool
    cloud_object_store_write_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_enabled: bool
    optional_tool_runtime_enabled: bool
    internal_webhook_network_egress_enabled: bool
    external_provider_network_enabled: bool
    auth_security_implementation_enabled: bool
    frontend_durable_authority_enabled: bool
    full_mockup_activation_enabled: bool
    rendered_write_submit_control_enabled: bool
    downstream_unavailable: list[str]
    next_allowed_actions: list[str]
    next_state: str


class Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliveryStatusResponse(
    Layer3BaseResponse
):
    mode: str
    delivery_status: str
    delivery_available: bool
    delivery_streaming_performed: bool
    delivery_state: str
    source_gate: str
    validated_delivery_source_gate: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    output_package_id: str
    package_kind: str
    package_payload_hash: str
    payload_ref_redacted: bool
    raw_local_path_exposed: bool
    same_origin_delivery_enabled: bool
    browser_managed_same_origin_attachment_enabled: bool
    provider_public_delivery_enabled: bool
    provider_private_signed_url_enabled: bool
    connector_dispatch_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    package_payload_rewrite_enabled: bool
    source_package_row_mutation_enabled: bool
    delivery_headers: dict[str, str]
    delivery_authority: dict[str, Any]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareResponse(
    Layer3BaseResponse
):
    mode: str
    session_id: str
    reconciliation_record_id: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    output_package_id: str
    package_kind: str
    package_payload_hash: str
    provider_signed_url_receipt_id: str
    provider_private_signed_url_object_authority_id: str
    provider_signed_url_state: str
    delivery_mode: str
    provider_url_redacted: str
    provider_url_expires_at: str
    provider_url_expires_in_seconds: int
    provider_url_replay_policy: str
    provider_url_revocation_supported: bool
    provider_url_use_count: int
    provider_url_max_use_count: int
    provider_url_revoked: bool
    source_artifact_ref: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    source_directory_delivery_authority: dict[str, Any]
    audit_receipt: dict[str, Any]
    authority_rail: dict[str, Any]
    source_directory_provider_private_signed_url_enabled: bool
    provider_private_signed_url_enabled: bool
    provider_public_url_prepare_enabled: bool
    same_origin_delivery_changed: bool
    raw_local_path_exposed: bool
    raw_provider_url_exposed: bool
    raw_provider_private_signed_url_token_exposed: bool
    provider_network_enabled: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    destination_write_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    frontend_durable_authority_enabled: bool
    next_allowed_actions: list[str]
    next_state: str


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseResponse(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareResponse
):
    delivery_use_decision: Literal["allowed"]
    delivery_use_mode: Literal["server_owned_redacted_provider_private_use"]


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusResponse(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareResponse
):
    pass


class Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeResponse(
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareResponse
):
    revocation_recorded: bool
    revocation_idempotency_key: str


class Layer3SourceDirectoryQualitativeAnalysisResponse(Layer3BaseResponse):
    mode: str
    analysis_contract_id: str
    analysis_mode: str
    qualitative_analysis_hash: str
    source_directory_package_review_preview_enabled: bool
    source_directory_package_review_preview_hash: str
    source_directory_package_review_preview: dict[str, Any]
    candidate_package_kinds: list[str]
    package_commit_enabled: bool
    package_review_submit_enabled: bool
    handoff_enabled: bool
    external_export_download_enabled: bool
    context_packet_contract_id: str
    context_packet_mode: str
    context_packet_hash: str
    analysis_question: str
    analysis_focus: str
    query_tokens: list[str]
    evidence_summary: dict[str, Any]
    salient_terms: list[dict[str, Any]]
    supporting_segments: list[dict[str, Any]]
    coverage_notes: list[dict[str, Any]]
    analysis_limits: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    index_contract_id: str | None
    index_mode: str | None
    segmentation_version: str | None
    index_authority_hash: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_snapshot_id: str
    source_shape: str | None
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    source_index_rows_written: bool
    retrieval_rows_written: bool
    context_packet_rows_written: bool
    qualitative_analysis_rows_written: bool
    qualitative_generation_rows_written: bool
    analysis_run_rows_written: bool
    package_rows_written: bool
    connector_rows_written: bool
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryQualitativeAnalysisStatusResponse(Layer3BaseResponse):
    mode: str
    analysis_status: str
    source_gate: str
    validated_analysis_schema_id: str
    validated_analysis_mode: str
    analysis_contract_id: str
    analysis_mode: str
    qualitative_analysis_hash: str
    context_packet_contract_id: str
    context_packet_mode: str
    context_packet_hash: str
    source_directory_package_review_preview_available: bool
    source_directory_package_review_preview_hash: str
    source_directory_package_review_preview_payload_redacted: bool
    supporting_segments_redacted: bool
    analysis_result_redacted: bool
    query_tokens: list[str]
    coverage_label: str
    supporting_segment_count: int
    salient_term_count: int
    coverage_note_count: int
    analysis_limit_count: int
    total: int
    limit: int
    offset: int
    index_contract_id: str | None
    index_mode: str | None
    segmentation_version: str | None
    index_authority_hash: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    material_snapshot_id: str
    source_shape: str | None
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    source_index_rows_written: bool
    retrieval_rows_written: bool
    context_packet_rows_written: bool
    qualitative_analysis_rows_written: bool
    qualitative_generation_rows_written: bool
    analysis_run_rows_written: bool
    package_rows_written: bool
    connector_rows_written: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SourceDirectoryQualitativeAnalysisPackageCommitResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_package_review_preview_hash: str
    construction_basis_hash: str | None
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_rows_written: bool
    package_payloads_written: bool
    source_package_row_mutation_enabled: bool
    package_payload_rewrite_enabled: bool
    package_review_submit_enabled: bool
    handoff_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_construction_source_gate: str
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    decision_notes: str | None
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str
    submit_record_ref: str
    package_review_submit_enabled: bool
    handoff_enabled: bool
    export_enabled: bool
    aps_handoff_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_construction_source_gate: str
    source_gate: str
    downstream_unavailable: list[str]
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    package_review_submit_record_ref: str
    package_review_state: str
    source_package_set_hash: str
    package_supersession_preview_hash: str
    downstream_dependency_hash: str
    downstream_dependencies: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    replacement_package_set_authority_enabled: bool
    package_supersession_commit_enabled: bool
    package_row_mutation_enabled: bool
    package_payload_rewrite_enabled: bool
    source_package_row_mutation_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    source_gate: str
    package_review_submit_source_gate: str
    package_construction_source_gate: str
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    decision_notes: str | None
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str
    package_review_submit_record_ref: str
    handoff_export_state: str
    prepare_record_ref: str
    handoff_target: str
    export_mode: str
    handoff_export_envelope: dict[str, Any]
    handoff_enabled: bool
    export_enabled: bool
    aps_handoff_enabled: bool
    external_export_download_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_delivery_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_review_submit_source_gate: str
    package_construction_source_gate: str
    source_gate: str
    downstream_unavailable: list[str]
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    decision_notes: str | None
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    source_ingestion_batch_id: str
    source_ingestion_file_id: str
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str
    payload_hash: str
    index_authority_hash: str
    context_packet_hash: str
    qualitative_analysis_hash: str
    source_directory_package_review_preview_hash: str
    construction_basis_hash: str
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_hashes: list[str]
    payload_refs_redacted: bool
    package_review_state: str
    package_review_submit_record_ref: str
    handoff_export_state: str
    prepare_record_ref: str
    handoff_export_envelope_ref: str
    handoff_target: str
    export_mode: str
    external_export_download_state: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    external_export_download_target: str
    download_mode: str
    external_export_download_descriptor: dict[str, Any]
    same_origin_delivery_enabled: bool
    browser_download_enabled: bool
    provider_public_delivery_enabled: bool
    provider_private_signed_url_enabled: bool
    connector_dispatch_enabled: bool
    network_egress_enabled: bool
    frontend_durable_authority_enabled: bool
    prompt_model_provider_runtime_enabled: bool
    package_review_submit_source_gate: str
    package_construction_source_gate: str
    source_gate: str
    downstream_unavailable: list[str]
    next_state: str
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceIntakeInventoryResponse(Layer3BaseResponse):
    source_gate: dict[str, Any]
    source_intake_inventory_mode: str
    source_family: str
    inventory_count: int
    limit: int
    filters: dict[str, Any]
    records: list[dict[str, Any]]
    downstream_eligibility: dict[str, bool]
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3SourceIntakeMaterialPreviewResponse(Layer3BaseResponse):
    source_gate: dict[str, Any]
    source_intake_preview_mode: str
    source_intake_record_id: str
    material_preview_id: str
    material_preview_hash: str
    material_candidate: dict[str, Any]
    partial_retrieval: bool
    downstream_eligibility: dict[str, bool]
    next_allowed_actions: list[str]
    negative_invariants: dict[str, bool]


class Layer3MaterialPreviewResponse(Layer3BaseResponse):
    material_preview_id: str
    material_preview_hash: str
    material_candidates: list[dict[str, Any]]
    partial_retrieval: bool
    authority_rail: dict[str, Any]


class Layer3RawMixedCorpusSeedResponse(Layer3BaseResponse):
    source_seed_id: str
    seed_mode: str
    source_seed_state: str
    dataset_version_ids: list[str]
    aps_content_document_ids: list[str]
    source_classes: list[str]
    artifact_manifest_ref: str
    artifact_manifest_hash: str
    layer3_flow_started: bool
    next_allowed_actions: list[str]


class Layer3RawMixedCorpusMaterializeResponse(Layer3BaseResponse):
    source_materialization_id: str
    materialization_mode: str
    source_materialization_state: str
    dataset_version_ids: list[str]
    aps_content_document_ids: list[str]
    source_classes: list[str]
    artifact_manifest_ref: str
    artifact_manifest_hash: str
    database_rows_written: dict[str, int]
    files_written: list[str]
    layer3_flow_started: bool
    next_allowed_actions: list[str]


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


class Layer3ApprovedPlanCancelResponse(Layer3BaseResponse):
    session_id: str
    next_state: str
    approved_plan_cancelled: bool
    approval_available: bool
    execution_started: bool
    replacement_plan_created: bool
    analysis_plan_id: str
    plan_status: str
    previous_plan_status: str
    approved_by_operator: bool
    approved_at: str | None
    source_preview_id: str
    source_preview_hash: str
    operator_decision: str
    operator_note_recorded: bool
    authority_rail: dict[str, Any]
    downstream_unavailable: list[str]
    approved_plan_cancel: dict[str, Any]


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


class Layer3PlanRevisionRecoveryResponse(Layer3BaseResponse):
    session_id: str
    source_revision_state: str
    next_state: str
    preview_refresh_required: bool
    approval_available: bool
    execution_started: bool
    recovery_lifecycle_only: bool
    source_preview_id: str
    source_preview_hash: str
    operator_decision: str
    operator_note_recorded: bool
    authority_rail: dict[str, Any]
    downstream_unavailable: list[str]
    plan_revision_recovery: dict[str, Any]


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
    package_review_submit_enabled: bool | None = None
    handoff_enabled: bool | None = None
    aps_handoff_enabled: bool | None = None
    external_export_download_enabled: bool | None = None
    connector_dispatch_enabled: bool | None = None
    provider_public_url_enabled: bool | None = None
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
    engine_family: str | None = None
    pass_scope: str | None = None
    method: str | None = None
    selected_method_name: str | None = None
    source_gate: str | None = None
    source_dataset_version_ids: list[str] | None = None
    cohort_shape: str | None = None
    source_shape: str | None = None
    content_id: str | None = None
    content_contract_id: str | None = None
    chunking_contract_id: str | None = None
    material_snapshot_id: str | None = None
    analysis_unit_id: str | None = None
    analysis_set_id: str | None = None
    output_payload_ref: str | None = None
    output_payload_hash: str | None = None
    chunk_count: int | None = None
    authority_rail: dict[str, Any]


class Layer3PackageConstructionCommitResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    construction_basis_hash: str | None = None
    reconciliation_record_id: str
    output_packages: list[dict[str, Any]]
    output_package_ids: list[str] | None = None
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    pass_scope: str | None = None
    method: str | None = None
    source_gate: str | None = None
    package_construction_source_gate: str | None = None
    source_shape: str | None = None
    source_dataset_version_ids: list[str] | None = None
    content_id: str | None = None
    content_contract_id: str | None = None
    chunking_contract_id: str | None = None
    material_snapshot_id: str | None = None
    analysis_unit_id: str | None = None
    analysis_set_id: str | None = None
    output_payload_ref: str | None = None
    output_payload_hash: str | None = None
    reviewed_output_item_summary: dict[str, Any] | None = None
    package_commit_enabled: bool | None = None
    package_review_submit_enabled: bool
    handoff_enabled: bool
    aps_handoff_enabled: bool | None = None
    external_export_download_enabled: bool | None = None
    connector_dispatch_enabled: bool | None = None
    provider_public_url_enabled: bool | None = None
    downstream_unavailable: list[str]
    next_allowed_actions: list[str] | None = None
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
    construction_basis_hash: str | None
    reconciliation_record_id: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    operator_decision: str
    decision_notes: str | None
    package_review_state: str
    submit_record_ref: str
    package_review_submit_enabled: bool
    handoff_enabled: bool
    export_enabled: bool
    aps_handoff_enabled: bool | None = None
    external_export_download_enabled: bool | None = None
    connector_dispatch_enabled: bool | None = None
    provider_public_url_enabled: bool | None = None
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3PackageSupersessionPreviewResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str | None
    package_review_preview_hash: str
    reconciliation_record_id: str
    output_package_ids: list[str]
    package_kinds: list[str]
    payload_refs: list[str]
    payload_hashes: list[str]
    operator_decision: str
    package_supersession_preview_mode: str
    package_supersession_preview_hash: str
    package_set_hash: str
    package_rows: list[dict[str, Any]]
    downstream_dependencies: list[dict[str, Any]]
    downstream_dependency_detected: bool
    immutable_package_rule_enforced: bool
    package_row_mutation_enabled: bool
    package_payload_rewrite_enabled: bool
    package_supersession_commit_enabled: bool
    database_write_enabled: bool
    filesystem_write_enabled: bool
    broad_package_mutation_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ReplacementPackageSetAuthorityResponse(Layer3BaseResponse):
    replacement_package_set_authority_id: str
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    reconciliation_record_id: str
    source_package_set_hash: str
    source_output_package_ids: list[str]
    source_package_kinds: list[str]
    source_payload_refs: list[str]
    source_payload_hashes: list[str]
    replacement_package_set_id: str
    replacement_package_set_hash: str
    replacement_package_kinds: list[str]
    replacement_payload_refs: list[str]
    replacement_payload_hashes: list[str]
    authority_basis_hash: str
    authority_snapshot: dict[str, Any]
    operator_decision: str
    replacement_package_set_authority_mode: str
    source_gate: str
    authority_record_persisted: bool
    package_row_mutation_enabled: bool
    package_payload_write_enabled: bool
    package_supersession_commit_enabled: bool
    broad_package_mutation_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ReplacementPackageArtifactMaterializationResponse(Layer3BaseResponse):
    replacement_artifact_materialization_id: str
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    reconciliation_record_id: str
    package_supersession_preview_hash: str
    source_package_set_hash: str
    source_output_package_ids: list[str]
    source_package_kinds: list[str]
    source_payload_refs: list[str]
    source_payload_hashes: list[str]
    replacement_package_set_id: str
    replacement_package_set_hash: str
    replacement_package_kinds: list[str]
    replacement_payload_refs: list[str]
    replacement_payload_hashes: list[str]
    authority_basis_hash: str
    materialization_basis_hash: str
    materialization_snapshot: dict[str, Any]
    operator_decision: str
    replacement_package_artifact_materialization_mode: str
    source_gate: str
    artifact_namespace: str
    hash_algorithm: str
    materialization_record_persisted: bool
    artifact_write_enabled: bool
    package_row_mutation_enabled: bool
    source_l3_output_package_mutation_enabled: bool
    source_package_payload_rewrite_enabled: bool
    replacement_package_set_authority_record_enabled: bool
    package_supersession_commit_enabled: bool
    replacement_artifact_manifest_record_enabled: bool
    replacement_namespace_record_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    created_at: str | None
    updated_at: str | None
    authority_rail: dict[str, Any]


class Layer3PackageSupersessionCommitResponse(Layer3BaseResponse):
    package_supersession_commit_id: str
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    reconciliation_record_id: str
    replacement_package_set_authority_id: str
    package_supersession_preview_hash: str
    source_package_set_hash: str
    source_output_package_ids: list[str]
    source_package_kinds: list[str]
    source_payload_refs: list[str]
    source_payload_hashes: list[str]
    replacement_package_set_id: str
    replacement_package_set_hash: str
    replacement_package_kinds: list[str]
    replacement_payload_refs: list[str]
    replacement_payload_hashes: list[str]
    replacement_authority_basis_hash: str
    downstream_dependency_hash: str
    commit_basis_hash: str
    commit_snapshot: dict[str, Any]
    operator_decision: str
    package_supersession_commit_mode: str
    source_gate: str
    package_supersession_commit_record_persisted: bool
    package_row_mutation_enabled: bool
    package_payload_write_enabled: bool
    l3_output_package_write_enabled: bool
    broad_package_mutation_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ReplacementPackageArtifactManifestResponse(Layer3BaseResponse):
    replacement_package_artifact_manifest_id: str
    replacement_artifact_materialization_id: str | None = None
    materialization_basis_hash: str | None = None
    replacement_authority_basis_hash: str | None = None
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    reconciliation_record_id: str
    replacement_package_set_authority_id: str
    package_supersession_commit_id: str
    package_supersession_commit_basis_hash: str
    replacement_package_set_id: str
    replacement_package_set_hash: str
    replacement_package_kinds: list[str]
    replacement_payload_refs: list[str]
    replacement_payload_hashes: list[str]
    verified_artifact_refs: list[str]
    verified_artifact_hashes: list[str]
    verified_artifact_byte_sizes: list[int]
    hash_algorithm: str
    artifact_namespace: str
    artifact_manifest_hash: str
    authority_basis_hash: str
    manifest_snapshot: dict[str, Any]
    operator_decision: str
    record_from_authority_operator_decision: str | None = None
    replacement_package_artifact_manifest_mode: str
    source_gate: str
    manifest_record_persisted: bool
    artifact_generation_enabled: bool
    package_row_mutation_enabled: bool
    package_payload_write_enabled: bool
    l3_output_package_write_enabled: bool
    broad_package_mutation_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ReplacementPackageNamespaceRecordResponse(Layer3BaseResponse):
    replacement_output_package_id: str
    session_id: str
    source_output_package_id: str
    replacement_artifact_manifest_id: str
    replacement_package_set_authority_id: str
    package_supersession_commit_id: str
    package_kind: str
    package_schema_id: str
    artifact_ref: str
    artifact_hash: str
    authority_basis_hash: str
    summary: dict[str, Any]
    operator_decision: str
    replacement_package_namespace_mode: str
    source_gate: str
    namespace_row_persisted: bool
    package_row_mutation_enabled: bool
    package_payload_write_enabled: bool
    l3_output_package_write_enabled: bool
    broad_package_mutation_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ReplacementPackageNamespaceSetResponse(Layer3BaseResponse):
    replacement_package_namespace_mode: str
    source_gate: str
    record_from_authority_operator_decision: str
    replacement_artifact_manifest_id: str
    replacement_package_set_authority_id: str
    package_supersession_commit_id: str
    corrected_package_artifact_set_id: str
    replacement_output_package_ids: list[str]
    source_output_package_ids: list[str]
    package_kinds: list[str]
    artifact_refs: list[str]
    artifact_hashes: list[str]
    namespace_records: list[Layer3ReplacementPackageNamespaceRecordResponse]
    namespace_rows_persisted: bool
    complete_namespace_set: bool
    server_derived_namespace_rows: bool
    per_kind_row_idempotency_keys: bool
    package_row_mutation_enabled: bool
    package_payload_write_enabled: bool
    l3_output_package_write_enabled: bool
    replacement_activation_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    source_widening_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    authority_rail: dict[str, Any]


class Layer3CorrectedPackageArtifactSetResponse(Layer3BaseResponse):
    corrected_package_artifact_set_id: str
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    reconciliation_record_id: str
    replacement_artifact_materialization_id: str
    materialization_basis_hash: str
    source_package_set_hash: str
    source_output_package_ids: list[str]
    source_package_kinds: list[str]
    source_payload_hashes: list[str]
    result_review_record_ref: str
    reviewed_output_items_hash: str
    package_review_preview_hash: str
    corrected_package_set_id: str
    corrected_package_set_hash: str
    corrected_package_kinds: list[str]
    corrected_artifact_refs: list[str]
    corrected_artifact_hashes: list[str]
    corrected_artifact_byte_sizes: list[int]
    artifact_namespace: str
    hash_algorithm: str
    artifact_manifest_hash: str
    corrected_artifact_basis_hash: str
    audit_history: list[dict[str, Any]]
    authority_snapshot: dict[str, Any]
    operator_decision: str
    corrected_package_artifact_set_mode: str
    source_gate: str
    corrected_package_artifact_set_record_persisted: bool
    artifact_refs_redacted: bool
    package_rebuild_enabled: bool
    package_row_mutation_enabled: bool
    source_l3_output_package_mutation_enabled: bool
    package_payload_rewrite_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    source_widening_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    created_at: str | None
    updated_at: str | None
    authority_rail: dict[str, Any]


class Layer3PackageReplacementActivationCommitResponse(Layer3BaseResponse):
    package_replacement_activation_id: str
    session_id: str
    replacement_artifact_manifest_id: str
    replacement_package_set_authority_id: str
    package_supersession_commit_id: str
    replacement_output_package_ids: list[str]
    source_output_package_ids: list[str]
    package_kinds: list[str]
    active_artifact_refs: list[str]
    active_artifact_hashes: list[str]
    replacement_activation_basis_hash: str
    activation_snapshot: dict[str, Any]
    operator_decision: str
    package_replacement_activation_mode: str
    source_gate: str
    activation_receipt_persisted: bool
    package_activation_state_persisted: bool
    source_l3_output_package_mutated: bool
    package_row_mutation_enabled: bool
    package_payload_write_enabled: bool
    package_payload_rewrite_enabled: bool
    downstream_handoff_rebinding_enabled: bool
    source_widening_enabled: bool
    connector_dispatch_enabled: bool
    provider_public_url_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    frontend_only_durable_state_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    created_at: str | None
    updated_at: str | None
    authority_rail: dict[str, Any]


class Layer3HandoffExportPrepareResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    construction_basis_hash: str | None = None
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
    active_package_authority_applied: bool | None = None
    package_replacement_activation_id: str | None = None
    source_output_package_ids: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    active_replacement_output_package_ids: list[str] | None = None
    active_payload_refs: list[str] | None = None
    active_payload_hashes: list[str] | None = None
    replacement_activation_basis_hash: str | None = None
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
    aps_handoff_enabled: bool | None = None
    external_export_download_enabled: bool | None = None
    connector_dispatch_enabled: bool | None = None
    provider_public_url_enabled: bool | None = None
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
    active_package_authority_applied: bool | None = None
    package_replacement_activation_id: str | None = None
    source_output_package_ids: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    active_replacement_output_package_ids: list[str] | None = None
    active_payload_refs: list[str] | None = None
    active_payload_hashes: list[str] | None = None
    replacement_activation_basis_hash: str | None = None
    content_id: str | None = None
    content_contract_id: str | None = None
    chunking_contract_id: str | None = None
    material_snapshot_id: str | None = None
    analysis_unit_id: str | None = None
    analysis_set_id: str | None = None
    output_payload_ref: str | None = None
    output_payload_hash: str | None = None
    chunk_count: int | None = None
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
    provider_public_url_enabled: bool | None = None
    downstream_unavailable: list[str]
    next_allowed_actions: list[str] | None = None
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
    active_package_authority_applied: bool | None = None
    package_replacement_activation_id: str | None = None
    source_output_package_ids: list[str] | None = None
    source_payload_hashes: list[str] | None = None
    active_replacement_output_package_ids: list[str] | None = None
    active_payload_refs: list[str] | None = None
    active_payload_hashes: list[str] | None = None
    replacement_activation_basis_hash: str | None = None
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


class Layer3ConnectorDispatchRecordResponse(Layer3BaseResponse):
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
    aps_handoff_record_ref: str
    aps_handoff_state: str
    aps_handoff_target: str
    aps_output_package_id: str
    aps_output_package_kind: str
    aps_bundle_ref: str
    source_artifact_ref: str
    source_artifact_schema_id: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    external_export_download_record_ref: str
    external_export_download_state: str
    external_export_download_descriptor_ref: str
    delivery_mode: str
    operator_decision: str
    decision_notes: str | None
    dispatch_mode: str
    connector_dispatch_record_state: str
    connector_dispatch_record_ref: str
    internal_dispatch_record_only_enabled: bool
    external_connector_invocation_enabled: bool
    destination_write_enabled: bool
    connector_run_created: bool
    provider_public_url_enabled: bool
    package_mutation_enabled: bool
    source_widening_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ConnectorLocalDestinationReceiptResponse(Layer3BaseResponse):
    session_id: str
    pass_run_id: str
    reconciliation_record_id: str
    connector_local_destination_receipt_id: str
    connector_local_destination_receipt_state: str
    connector_dispatch_record_ref: str
    external_export_download_record_ref: str
    destination_target: str
    dispatch_mode: str
    accepted_artifact_ref: str
    accepted_artifact_hash: str
    accepted_artifact_size_bytes: int
    authority_basis_hash: str
    internal_fake_local_destination_enabled: bool
    external_connector_invocation_enabled: bool
    destination_write_enabled: bool
    connector_run_created: bool
    network_write_enabled: bool
    real_destination_integration_enabled: bool
    provider_public_url_enabled: bool
    package_mutation_enabled: bool
    source_widening_enabled: bool
    qualitative_hybrid_rag_execution_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ServerOwnedLocalOutboxFakeTargetResponse(Layer3BaseResponse):
    session_id: str
    pass_run_id: str
    reconciliation_record_id: str
    server_owned_local_outbox_target_receipt_id: str
    server_owned_local_outbox_target_state: str
    target_operation_state: str
    connector_dispatch_record_ref: str
    connector_local_destination_receipt_id: str
    external_export_download_record_ref: str
    target_identity: str
    dispatch_mode: str
    accepted_artifact_ref: str
    accepted_artifact_hash: str
    accepted_artifact_size_bytes: int
    authority_basis_hash: str
    fake_target_contract_enabled: bool
    real_connector_invocation_enabled: bool
    destination_write_enabled: bool
    destination_write_performed: bool
    connector_run_created: bool
    connector_run_target_created: bool
    credentials_enabled: bool
    network_write_enabled: bool
    real_destination_integration_enabled: bool
    provider_public_url_enabled: bool
    provider_public_delivery_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_enabled: bool
    auth_security_implementation_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3ServerOwnedLocalOutboxWriteResponse(Layer3BaseResponse):
    session_id: str
    pass_run_id: str
    reconciliation_record_id: str
    server_owned_local_outbox_write_receipt_id: str
    server_owned_local_outbox_target_receipt_id: str
    server_owned_local_outbox_write_state: str
    write_operation_state: str
    connector_dispatch_record_ref: str
    connector_local_destination_receipt_id: str
    external_export_download_record_ref: str
    target_identity: str
    dispatch_mode: str
    outbox_artifact_ref: str
    outbox_manifest_ref: str
    outbox_artifact_hash: str
    outbox_artifact_size_bytes: int
    accepted_artifact_ref: str
    accepted_artifact_hash: str
    accepted_artifact_size_bytes: int
    authority_basis_hash: str
    server_owned_local_outbox_write_enabled: bool
    server_owned_local_outbox_write_performed: bool
    fake_target_contract_enabled: bool
    real_connector_invocation_enabled: bool
    external_destination_write_enabled: bool
    operator_destination_path_enabled: bool
    connector_run_created: bool
    connector_run_target_created: bool
    credentials_enabled: bool
    network_write_enabled: bool
    real_destination_integration_enabled: bool
    provider_public_url_enabled: bool
    provider_public_delivery_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_enabled: bool
    auth_security_implementation_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    downstream_unavailable: list[str]
    next_state: str
    authority_rail: dict[str, Any]


class Layer3LocalOutboxProviderPrivateHandoffResponse(Layer3BaseResponse):
    session_id: str
    pass_run_id: str
    reconciliation_record_id: str
    provider_private_handoff_receipt_id: str
    server_owned_local_outbox_write_receipt_id: str
    server_owned_local_outbox_target_receipt_id: str
    connector_local_destination_receipt_id: str
    connector_dispatch_record_ref: str
    external_export_download_record_ref: str
    target_identity: str
    dispatch_mode: str
    recipient_scope: str
    provider_private_handoff_state: str
    handoff_operation_state: str
    provider_private_marker: str
    provider_private_expires_at: str
    provider_private_expires_in_seconds: int
    provider_private_replay_policy: str
    provider_private_revocation_supported: bool
    provider_private_use_route_enabled: bool
    raw_token_exposed: bool
    source_artifact_hash: str
    source_artifact_size_bytes: int
    outbox_artifact_ref: str
    outbox_manifest_ref: str
    outbox_artifact_hash: str
    outbox_artifact_size_bytes: int
    authority_basis_hash: str
    request_basis_hash: str
    audit_receipt: dict[str, Any]
    authority_rail: dict[str, Any]
    real_connector_invocation_enabled: bool
    external_provider_network_write_enabled: bool
    external_object_store_write_enabled: bool
    external_destination_write_enabled: bool
    connector_run_created: bool
    connector_run_target_created: bool
    credentials_enabled: bool
    provider_public_delivery_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_enabled: bool
    auth_security_implementation_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    downstream_unavailable: list[str]
    next_allowed_actions: list[str]
    next_state: str


class Layer3ExternalLocalExportResponse(Layer3BaseResponse):
    session_id: str
    pass_run_id: str
    reconciliation_record_id: str
    external_local_export_receipt_id: str
    server_owned_local_outbox_write_receipt_id: str
    server_owned_local_outbox_target_receipt_id: str
    connector_local_destination_receipt_id: str
    provider_private_handoff_receipt_id: str | None
    connector_dispatch_record_ref: str
    external_export_download_record_ref: str
    target_identity: str
    target_class: str
    dispatch_mode: str
    external_local_export_state: str
    export_operation_state: str
    redacted_destination_label: str
    external_artifact_ref: str
    external_manifest_ref: str
    external_artifact_hash: str
    external_artifact_size_bytes: int
    external_manifest_hash: str
    external_manifest_size_bytes: int
    source_outbox_artifact_ref: str
    source_outbox_artifact_hash: str
    source_outbox_artifact_size_bytes: int
    authority_basis_hash: str
    idempotency_key: str
    audit_receipt: dict[str, Any]
    server_configured_external_local_export_write_enabled: bool
    server_configured_external_local_export_write_performed: bool
    external_destination_write_enabled: bool
    operator_destination_path_enabled: bool
    real_connector_invocation_enabled: bool
    connector_run_created: bool
    connector_run_target_created: bool
    credentials_enabled: bool
    network_egress_enabled: bool
    provider_public_delivery_enabled: bool
    raw_public_url_exposed: bool
    raw_token_exposed: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_enabled: bool
    qualitative_hybrid_analysis_runtime_enabled: bool
    auth_security_implementation_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    generic_downstream_dispatch_enabled: bool
    downstream_unavailable: list[str]
    next_allowed_actions: list[str]
    next_state: str


class Layer3InternalWebhookDispatchResponse(Layer3BaseResponse):
    session_id: str
    pass_run_id: str
    reconciliation_record_id: str
    internal_webhook_dispatch_receipt_id: str
    server_owned_local_outbox_write_receipt_id: str
    server_owned_local_outbox_target_receipt_id: str
    connector_local_destination_receipt_id: str
    connector_dispatch_record_ref: str
    external_export_download_record_ref: str
    package_kind: str
    package_artifact_ref: str
    package_artifact_hash: str
    package_artifact_size_bytes: int
    handoff_export_prepare_ref: str
    target_identity: str
    target_class: str
    dispatch_mode: str
    internal_webhook_dispatch_state: str
    dispatch_operation_state: str
    redacted_destination_display_name: str
    idempotency_key: str
    request_basis_hash: str
    authority_basis_hash: str
    response_status_code: int | None
    redacted_response_summary: dict[str, Any]
    failure_code: str | None
    audit_receipt: dict[str, Any]
    server_configured_internal_webhook_enabled: bool
    internal_webhook_post_performed: bool
    real_connector_invocation_enabled: bool
    server_configured_allowlisted_url_enabled: bool
    operator_destination_url_enabled: bool
    raw_target_url_exposed: bool
    raw_token_exposed: bool
    raw_headers_exposed: bool
    raw_local_path_exposed: bool
    raw_package_payload_exposed: bool
    raw_package_bytes_exposed: bool
    connector_run_created: bool
    connector_run_target_created: bool
    credentials_enabled: bool
    provider_public_url_enabled: bool
    provider_private_signed_url_enabled: bool
    cloud_object_store_write_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_enabled: bool
    optional_tool_runtime_enabled: bool
    auth_security_implementation_enabled: bool
    rendered_write_submit_control_enabled: bool
    downstream_unavailable: list[str]
    next_allowed_actions: list[str]
    next_state: str


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


class Layer3ProviderPrivateSignedUrlPrepareResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    reconciliation_record_id: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    provider_signed_url_receipt_id: str
    provider_signed_url_state: str
    delivery_mode: str
    provider_url_redacted: str
    provider_url_expires_at: str
    provider_url_expires_in_seconds: int
    provider_url_replay_policy: str
    provider_url_revocation_supported: bool
    provider_url_use_count: int
    provider_url_max_use_count: int
    provider_url_revoked: bool
    source_artifact_hash: str
    source_artifact_size_bytes: int
    authority_rail: dict[str, Any]
    audit_receipt: dict[str, Any]
    next_allowed_actions: list[str]
    next_state: str


class Layer3ProviderPrivateSignedUrlStatusResponse(Layer3BaseResponse):
    provider_signed_url_receipt_id: str
    provider_signed_url_state: str
    delivery_mode: str
    provider_url_redacted: str
    provider_url_expires_at: str
    provider_url_replay_policy: str
    provider_url_revocation_supported: bool
    provider_url_use_count: int
    provider_url_max_use_count: int
    provider_url_revoked: bool
    source_artifact_hash: str
    source_artifact_size_bytes: int
    audit_receipt: dict[str, Any]
    next_allowed_actions: list[str]


class Layer3ProviderPrivateSignedUrlRevokeResponse(Layer3BaseResponse):
    provider_signed_url_receipt_id: str
    provider_signed_url_state: str
    delivery_mode: str
    provider_url_redacted: str
    provider_url_expires_at: str
    provider_url_replay_policy: str
    provider_url_revocation_supported: bool
    provider_url_use_count: int
    provider_url_max_use_count: int
    provider_url_revoked: bool
    source_artifact_hash: str
    source_artifact_size_bytes: int
    revocation_recorded: bool
    revocation_idempotency_key: str
    authority_rail: dict[str, Any]
    audit_receipt: dict[str, Any]
    next_allowed_actions: list[str]
    next_state: str


class Layer3ProviderPublicUrlPrepareResponse(Layer3BaseResponse):
    session_id: str
    provider_private_signed_url_receipt_id: str
    external_export_download_record_ref: str
    export_download_descriptor_ref: str
    provider_public_url_receipt_id: str
    provider_public_url_state: str
    delivery_mode: str
    provider_public_url_redacted: str
    provider_public_url_expires_at: str
    provider_public_url_expires_in_seconds: int
    provider_public_url_replay_policy: str
    provider_public_url_revocation_supported: bool
    provider_public_url_revoked: bool
    source_artifact_hash: str
    source_artifact_size_bytes: int
    raw_public_url_exposed: bool
    public_url_enabled: bool
    authority_rail: dict[str, Any]
    audit_receipt: dict[str, Any]
    next_allowed_actions: list[str]
    next_state: str


class Layer3ProviderPublicUrlStatusResponse(Layer3BaseResponse):
    provider_public_url_receipt_id: str
    provider_public_url_state: str
    delivery_mode: str
    provider_public_url_redacted: str
    provider_public_url_expires_at: str
    provider_public_url_replay_policy: str
    provider_public_url_revocation_supported: bool
    provider_public_url_revoked: bool
    source_artifact_hash: str
    source_artifact_size_bytes: int
    raw_public_url_exposed: bool
    public_url_enabled: bool
    audit_receipt: dict[str, Any]
    next_allowed_actions: list[str]


class Layer3ProviderPublicUrlRevokeResponse(Layer3ProviderPublicUrlStatusResponse):
    pass


class Layer3ProviderPublicUrlDeliveryUseResponse(Layer3BaseResponse):
    provider_public_url_receipt_id: str
    provider_public_url_object_authority_id: str
    provider_public_url_state: str
    delivery_use_mode: str
    delivery_use_decision: str
    delivery_use_denied_reason: str | None = None
    provider_public_url_redacted: str
    provider_public_url_replay_policy: str
    authority_hash: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    raw_public_url_exposed: bool
    public_url_enabled: bool
    provider_network_enabled: bool
    provider_object_write_enabled: bool
    public_redirect_enabled: bool
    byte_streaming_enabled: bool
    durable_use_row_created: bool
    audit_row_created: bool
    provider_credentials_enabled: bool
    connector_dispatch_enabled: bool
    package_mutation_enabled: bool
    source_expansion_enabled: bool
    rag_vector_indexing_enabled: bool
    frontend_durable_authority_enabled: bool
    next_allowed_actions: list[str]


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
        "edited_findings": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
    },
}


PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict package-review preview fields; explicit package/handoff/source-widening fields remain fail-closed.",
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
        "edited_findings": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
    },
}


PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "description": "Strict package construction commit fields; explicit review/handoff/source-widening/package-payload fields remain fail-closed.",
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
        "edited_findings": _forbidden_request_field_schema(),
        "rewrite_output": _forbidden_request_field_schema(),
        "package_payload": _forbidden_request_field_schema(),
        "package_variant_content": _forbidden_request_field_schema(),
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
        "package_review_submit_schema_id",
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
        "handoff_target": {"type": "string", "enum": ["internal_export_envelope"]},
        "export_mode": {"type": "string", "enum": ["prepare_only"]},
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


class Layer3SessionSummaryResponse(Layer3BaseResponse):
    session_id: str
    selection_manifest_id: str
    current_gate: str
    gate_b_summary: dict[str, int]
    gate_c_summary: dict[str, Any]
    plan_preview: dict[str, Any]
    plan_approval: dict[str, Any]
    plan_revision: dict[str, Any]
    plan_revision_recovery: dict[str, Any]
    approved_plan_cancel: dict[str, Any]
    execution_selection: dict[str, Any]
    analysis_execution_start: dict[str, Any]
    execution_result_review: dict[str, Any]
    package_review_preview: dict[str, Any]
    package_construction: dict[str, Any]
    package_review_submit: dict[str, Any]
    handoff_export_prepare: dict[str, Any]
    aps_handoff_dispatch: dict[str, Any]
    external_export_download: dict[str, Any]
    connector_local_destination_receipt: dict[str, Any]
    server_owned_local_outbox_target: dict[str, Any]
    server_owned_local_outbox_write: dict[str, Any]
    local_outbox_provider_private_handoff: dict[str, Any]
    external_local_export: dict[str, Any]
    internal_webhook_dispatch: dict[str, Any]
    pdf_location_projection: dict[str, Any]
    sublayer_visualization: dict[str, Any]
    analysis_environment_projection: dict[str, Any]
    state_action_contract: dict[str, Any]
    downstream_unavailable: list[str]
    authority_rail: dict[str, Any]


def _json_or_error(handler: Callable[[], dict[str, Any]]) -> dict[str, Any] | JSONResponse:
    try:
        return handler()
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
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


@router.get("/authority-matrix", response_model=Layer3AuthorityMatrixResponse)
def get_authority_matrix() -> dict[str, Any]:
    return layer3_workbench.authority_matrix_contract()


@router.post(
    "/preflight",
    response_model=Layer3PreflightResponse,
    openapi_extra={"requestBody": _json_request_body(PREFLIGHT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_preflight(payload: Layer3PreflightRequest) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.preflight(payload.model_dump(exclude_none=True)))


@router.post(
    "/source-preview",
    response_model=Layer3SourcePreviewResponse,
    openapi_extra={"requestBody": _json_request_body(SOURCE_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_source_preview(payload: Layer3SourcePreviewRequest) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.source_preview(payload.model_dump(exclude_none=True)))


@router.post(
    "/source/intake/upload",
    response_model=Layer3SourceIntakeRecordResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 409),
)
async def post_source_intake_upload(
    request: Request,
    file: UploadFile = File(...),
    client_request_id: str = Form(...),
    operator_decision: str = Form(...),
    source_label: str = Form(...),
    source_description: str | None = Form(None),
    source_family: str | None = Form(None),
    freshness_timestamp: str | None = Form(None),
    declared_media_type: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    _ = (
        client_request_id,
        operator_decision,
        source_label,
        source_description,
        source_family,
        freshness_timestamp,
        declared_media_type,
    )
    try:
        form = await request.form()
        fields = layer3_source_intake.normalise_source_intake_form_items(form.multi_items())
        file_bytes = await file.read()
        return layer3_source_intake.record_operator_upload_source_intake(
            db,
            file_bytes=file_bytes,
            original_filename=file.filename,
            media_type=file.content_type,
            form_fields=fields,
        )
    except layer3_source_intake.SourceIntakeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.get(
    "/source/intake/inventory",
    response_model=Layer3SourceIntakeInventoryResponse,
    responses=_workbench_error_responses(400),
)
def get_source_intake_inventory(
    limit: str = "50",
    source_family: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        return layer3_source_intake.source_intake_inventory(
            db,
            limit=limit,
            source_family=source_family,
            status=status,
        )
    except layer3_source_intake.SourceIntakeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.get(
    "/source/intake/{source_intake_record_id}/preview",
    response_model=Layer3SourceIntakeMaterialPreviewResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_source_intake_material_preview(
    source_intake_record_id: str,
    max_chars: int = 4000,
    db: Session = Depends(get_db),
):
    try:
        return layer3_source_intake.source_intake_material_preview(
            db,
            source_intake_record_id=source_intake_record_id,
            max_chars=max_chars,
        )
    except layer3_source_intake.SourceIntakeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/bundle/material-bridge",
    response_model=Layer3CandidateBBundleMaterialBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_bundle_material_bridge(
    payload: Layer3CandidateBBundleMaterialBridgeRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_bundle_bridge.CandidateBBundleBridgeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/runtime/material-bridge",
    response_model=Layer3CandidateBRuntimeMaterialBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_runtime_material_bridge(
    payload: Layer3CandidateBRuntimeMaterialBridgeRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_runtime_bridge.CandidateBRuntimeBridgeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/artifact-family/status",
    response_model=Layer3CandidateBArtifactFamilyStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_artifact_family_status(
    payload: Layer3CandidateBArtifactFamilyStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_artifact_status.candidate_b_retained_artifact_family_status(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_artifact_status.CandidateBArtifactStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/visual-lane/status",
    response_model=Layer3CandidateBVisualLaneStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_visual_lane_status(
    payload: Layer3CandidateBVisualLaneStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_visual_lane_status.candidate_b_visual_lane_status(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_visual_lane_status.CandidateBVisualLaneStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/runtime/downstream-proof",
    response_model=Layer3CandidateBRuntimeDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_runtime_downstream_proof(
    payload: Layer3CandidateBRuntimeDownstreamProofRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_downstream_proof.candidate_b_runtime_downstream_proof(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_downstream_proof.CandidateBDownstreamProofError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/bundle/downstream-proof",
    response_model=Layer3CandidateBBundleDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_bundle_downstream_proof(
    payload: Layer3CandidateBBundleDownstreamProofRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_bundle_downstream_proof.candidate_b_bundle_downstream_proof(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_bundle_downstream_proof.CandidateBBundleDownstreamProofError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/operator-status",
    response_model=Layer3CandidateBDefaultPromotionOperatorStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_default_promotion_operator_status(
    payload: Layer3CandidateBDefaultPromotionOperatorStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_operator_status.candidate_b_default_promotion_operator_status(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_operator_status.CandidateBOperatorStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/closure-evidence",
    response_model=Layer3CandidateBDefaultPromotionClosureEvidenceResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_default_promotion_closure_evidence(
    payload: Layer3CandidateBDefaultPromotionClosureEvidenceRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_promotion_closure.candidate_b_default_promotion_closure_evidence(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_promotion_closure.CandidateBPromotionClosureError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/readiness-audit",
    response_model=Layer3CandidateBDefaultPromotionReadinessAuditResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_default_promotion_readiness_audit(
    payload: Layer3CandidateBDefaultPromotionReadinessAuditRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_default_readiness.evaluate_candidate_b_default_promotion_readiness(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_default_readiness.CandidateBDefaultReadinessError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/final-proof",
    response_model=Layer3CandidateBDefaultPromotionFinalProofResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_default_promotion_final_proof(
    payload: Layer3CandidateBDefaultPromotionFinalProofRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_final_proof.candidate_b_default_promotion_final_proof(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_final_proof.CandidateBFinalProofError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/final-proof/status",
    response_model=Layer3CandidateBDefaultPromotionFinalProofStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_default_promotion_final_proof_status(
    payload: Layer3CandidateBDefaultPromotionFinalProofStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_candidate_b_final_proof.candidate_b_default_promotion_final_proof_status(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_final_proof.CandidateBFinalProofError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/scan",
    response_model=Layer3SourceDirectoryIngestionResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_ingestion_scan(
    payload: Layer3SourceDirectoryIngestionScanRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_source_directory_ingestion.scan_server_configured_directory(
            db,
            payload.model_dump(exclude_unset=True),
        )
    except layer3_source_directory_ingestion.SourceDirectoryIngestionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.get(
    "/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}",
    response_model=Layer3SourceDirectoryIngestionResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_source_directory_ingestion_status(
    source_ingestion_batch_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_source_directory_ingestion.source_directory_ingestion_status(
            db,
            source_ingestion_batch_id,
        )
    except layer3_source_directory_ingestion.SourceDirectoryIngestionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/material-preview",
    response_model=Layer3SourceDirectoryMaterialPreviewResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_material_preview(
    payload: Layer3SourceDirectoryMaterialPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_source_directory_material_admission.source_directory_material_preview(
            db,
            payload.model_dump(exclude_unset=True),
        )
    except layer3_source_directory_material_admission.SourceDirectoryMaterialAdmissionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-authority/prepare",
    response_model=Layer3SourceDirectoryHybridAuthorityPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_authority_prepare(
    payload: Layer3SourceDirectoryHybridAuthorityPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_source_directory_hybrid_authority.source_directory_hybrid_authority_prepare(
            db,
            payload.model_dump(exclude_unset=True),
        )
    except (
        layer3_source_directory_hybrid_authority.SourceDirectoryHybridAuthorityError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/vector-retrieval",
    response_model=Layer3SourceDirectoryVectorRetrievalResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_vector_retrieval(
    payload: Layer3SourceDirectoryVectorRetrievalRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_source_directory_vector_retrieval.source_directory_material_vector_retrieval(
            db,
            payload.model_dump(exclude_unset=True),
        )
    except (
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet",
    response_model=Layer3SourceDirectoryHybridContextPacketResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet(
    payload: Layer3SourceDirectoryHybridContextPacketRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return layer3_source_directory_hybrid_context.source_directory_material_hybrid_retrieval_context_packet(
            db,
            payload.model_dump(exclude_unset=True),
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis",
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/status",
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_status(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_status(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/commit",
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_package_commit(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_package_commit(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridPackageCommitError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit",
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridPackageReviewSubmitError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare",
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridHandoffExportPrepareError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare",
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadPrepareError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/internal-webhook/dispatch"
    ),
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_dispatch(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_source_directory_internal_webhook.dispatch_source_directory_internal_webhook(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/internal-webhook/status/"
        "{source_directory_internal_webhook_dispatch_receipt_id}"
    ),
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_source_directory_hybrid_context_packet_qualitative_analysis_internal_webhook_status(
    source_directory_internal_webhook_dispatch_receipt_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_source_directory_internal_webhook.source_directory_internal_webhook_status(
            db,
            source_directory_internal_webhook_dispatch_receipt_id,
        )
    )


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/download/deliver/status"
    ),
    response_model=Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliveryStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadDeliveryError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare"
    ),
    response_model=(
        Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareResponse
    ),
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadDeliveryError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridProviderPrivateSignedUrlPrepareError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/download/provider-private-signed-url/status"
    ),
    response_model=(
        Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusResponse
    ),
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_status(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_status(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadDeliveryError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridProviderPrivateSignedUrlStatusError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/download/provider-private-signed-url/use"
    ),
    response_model=(
        Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseResponse
    ),
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_use(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_use(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadDeliveryError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridProviderPrivateSignedUrlUseError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/download/provider-private-signed-url/revoke"
    ),
    response_model=(
        Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeResponse
    ),
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_revoke(
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_revoke(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadDeliveryError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridProviderPrivateSignedUrlRevokeError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/hybrid-context-packet/"
        "qualitative-analysis/handoff/export/download/deliver"
    ),
    response_model=None,
    responses=_workbench_error_responses(400, 404, 409),
)
async def post_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
    request: Request,
    db: Session = Depends(get_db),
) -> FileResponse | JSONResponse:
    try:
        payload = await _payload_from_request(request)
        delivery = (
            layer3_source_directory_hybrid_analysis
            .source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
                db,
                payload,
            )
        )
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridAnalysisError,
        layer3_source_directory_hybrid_analysis.SourceDirectoryHybridExternalExportDownloadDeliveryError,
        layer3_source_directory_hybrid_context.SourceDirectoryHybridContextError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
        layer3_source_directory_vector_index.SourceDirectoryVectorIndexError,
        layer3_source_directory_vector_retrieval.SourceDirectoryVectorRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    return FileResponse(
        path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        content_disposition_type="attachment",
        headers=delivery.headers,
    )


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis",
    response_model=Layer3SourceDirectoryQualitativeAnalysisResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_hybrid_analysis(
    payload: Layer3SourceDirectoryQualitativeAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_material_context_packet_qualitative_hybrid_analysis(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/status",
    response_model=Layer3SourceDirectoryQualitativeAnalysisStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_hybrid_analysis_status(
    payload: Layer3SourceDirectoryQualitativeAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_hybrid_analysis_status(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/commit",
    response_model=Layer3SourceDirectoryQualitativeAnalysisPackageCommitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_package_commit(
    payload: Layer3SourceDirectoryQualitativeAnalysisPackageCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_package_commit(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryPackageCommitError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/review/submit",
    response_model=Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_package_review_submit(
    payload: Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_package_review_submit(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryPackageReviewSubmitError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/supersession/preview"
    ),
    response_model=Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_package_supersession_preview(
    payload: Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_package_supersession_preview(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryPackageSupersessionPreviewError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/replacement-set/record-from-supersession-preview"
    ),
    response_model=Layer3ReplacementPackageSetAuthorityResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_package_replacement_set_record(
    payload: Layer3SourceDirectoryReplacementPackageSetAuthorityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: (
            layer3_replacement_package_set_authority
            .record_replacement_package_set_authority_from_source_directory_supersession_preview(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    )


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/supersession/commit"
    ),
    response_model=Layer3PackageSupersessionCommitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_package_supersession_commit(
    payload: Layer3SourceDirectoryPackageSupersessionCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_package_supersession_commit.commit_package_supersession_from_source_directory_lifecycle(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/supersession/provider-private-signed-url/prepare"
    ),
    response_model=Layer3BaseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_package_supersession_provider_private_signed_url_prepare(
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: (
            layer3_package_supersession_commit
            .source_directory_package_supersession_provider_private_signed_url_prepare(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    )


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/supersession/provider-private-signed-url/status"
    ),
    response_model=Layer3BaseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_package_supersession_provider_private_signed_url_status(
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: (
            layer3_package_supersession_commit
            .source_directory_package_supersession_provider_private_signed_url_status(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    )


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/supersession/provider-private-signed-url/use"
    ),
    response_model=Layer3BaseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_package_supersession_provider_private_signed_url_use(
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlUseRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: (
            layer3_package_supersession_commit
            .source_directory_package_supersession_provider_private_signed_url_use(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    )


@router.post(
    (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/"
        "package/supersession/provider-private-signed-url/revoke"
    ),
    response_model=Layer3BaseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_package_supersession_provider_private_signed_url_revoke(
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: (
            layer3_package_supersession_commit
            .source_directory_package_supersession_provider_private_signed_url_revoke(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    )


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/prepare",
    response_model=Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_handoff_export_prepare(
    payload: Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_handoff_export_prepare(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryHandoffExportPrepareError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/prepare",
    response_model=Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_external_export_download_prepare(
    payload: Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_external_export_download_prepare(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryExternalExportDownloadPrepareError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver/status",
    response_model=Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliveryStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_source_directory_qualitative_analysis_external_export_download_delivery_status(
    payload: Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliverRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        return (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_external_export_download_delivery_status(
                db,
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryExternalExportDownloadDeliveryError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver",
    response_model=None,
    responses=_workbench_error_responses(400, 404, 409),
)
async def post_source_directory_qualitative_analysis_external_export_download_deliver(
    request: Request,
    db: Session = Depends(get_db),
) -> FileResponse | JSONResponse:
    try:
        payload = await _payload_from_request(request)
        delivery = (
            layer3_source_directory_qualitative_analysis
            .source_directory_qualitative_analysis_external_export_download_deliver(
                db,
                payload,
            )
        )
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )
    except (
        layer3_source_directory_context_packet.SourceDirectoryContextPacketError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryExternalExportDownloadDeliveryError,
        layer3_source_directory_qualitative_analysis.SourceDirectoryQualitativeAnalysisError,
        layer3_source_directory_text_index.SourceDirectoryTextIndexError,
        layer3_source_directory_text_retrieval.SourceDirectoryTextRetrievalError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    return FileResponse(
        path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        content_disposition_type="attachment",
        headers=delivery.headers,
    )


@router.post(
    "/source/mixed-corpus/seed",
    response_model=Layer3RawMixedCorpusSeedResponse,
    openapi_extra={"requestBody": _json_request_body(RAW_MIXED_CORPUS_SEED_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_raw_mixed_corpus_seed(
    payload: Layer3RawMixedCorpusSeedRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_raw_mixed_bridge.seed_raw_mixed_corpus(payload.model_dump(exclude_unset=True), db)
    )


@router.post(
    "/source/mixed-corpus/materialize",
    response_model=Layer3RawMixedCorpusMaterializeResponse,
    openapi_extra={"requestBody": _json_request_body(RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_raw_mixed_corpus_materialize(
    payload: Layer3RawMixedCorpusMaterializeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_raw_mixed_materialization.materialize_raw_mixed_corpus(
            payload.model_dump(exclude_unset=True),
            db,
        )
    )


@router.post(
    "/material-preview",
    response_model=Layer3MaterialPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(MATERIAL_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_material_preview(
    payload: Layer3MaterialPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.material_preview(payload.model_dump(exclude_none=True), db))


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
def post_gate_c_override(payload: Layer3GateCOverrideUnavailableRequest) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=layer3_workbench.gate_c_override_unavailable(payload.model_dump(exclude_none=True)),
    )


@router.post(
    "/plan/preview",
    response_model=Layer3PlanPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_preview(
    payload: Layer3PlanPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_preview(db, payload.model_dump(exclude_none=True)))


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
    "/plan/approved/cancel",
    response_model=Layer3ApprovedPlanCancelResponse,
    openapi_extra={"requestBody": _json_request_body(APPROVED_PLAN_CANCEL_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_approved_cancel(
    payload: Layer3ApprovedPlanCancelRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.approved_plan_cancel(db, payload.model_dump(exclude_unset=True)))


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
    "/plan/revision/recover",
    response_model=Layer3PlanRevisionRecoveryResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_REVISION_RECOVERY_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_revision_recover(
    payload: Layer3PlanRevisionRecoveryRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_revision_recovery(db, payload.model_dump(exclude_unset=True)))


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
    payload: Layer3ExecutionResultReviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_result_review(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/review/preview",
    response_model=Layer3PackageReviewPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_preview(
    payload: Layer3PackageReviewPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_review_preview(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/review/commit",
    response_model=Layer3PackageConstructionCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_commit(
    payload: Layer3PackageConstructionCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_construction_commit(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/review/submit",
    response_model=Layer3PackageReviewSubmitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REVIEW_SUBMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_submit(
    payload: Layer3PackageReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_review_submit(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/mutation/preview",
    response_model=Layer3PackageSupersessionPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_SUPERSESSION_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_mutation_preview(
    payload: Layer3PackageSupersessionPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_package_mutation_entry.preview_package_supersession(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/materialize",
    response_model=Layer3ReplacementPackageArtifactMaterializationResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_materialize(
    payload: Layer3ReplacementPackageArtifactMaterializationRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_materialization.materialize_replacement_package_artifacts(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-set/record",
    response_model=Layer3ReplacementPackageSetAuthorityResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_set_record(
    payload: Layer3ReplacementPackageSetAuthorityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_set_authority.record_replacement_package_set_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-set/record-from-corrected-artifact-set",
    response_model=Layer3ReplacementPackageSetAuthorityResponse,
    openapi_extra={
        "requestBody": _json_request_body(
            REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA
        )
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_set_record_from_corrected_artifact_set(
    payload: Layer3ReplacementPackageSetAuthorityFromCorrectedArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_set_authority.record_replacement_package_set_authority_from_corrected_artifact_set(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/supersession/commit",
    response_model=Layer3PackageSupersessionCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_SUPERSESSION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_supersession_commit(
    payload: Layer3PackageSupersessionCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_package_supersession_commit.commit_package_supersession(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/supersession/commit-from-corrected-artifact-set-authority",
    response_model=Layer3PackageSupersessionCommitResponse,
    openapi_extra={
        "requestBody": _json_request_body(PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA)
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_supersession_commit_from_corrected_artifact_set_authority(
    payload: Layer3PackageSupersessionCommitFromCorrectedArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_package_supersession_commit.commit_package_supersession_from_corrected_artifact_set_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/manifest/record",
    response_model=Layer3ReplacementPackageArtifactManifestResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_manifest_record(
    payload: Layer3ReplacementPackageArtifactManifestRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_artifact_manifest.record_replacement_package_artifact_manifest(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/manifest/record-from-authority",
    response_model=Layer3ReplacementPackageArtifactManifestResponse,
    openapi_extra={
        "requestBody": _json_request_body(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUEST_SCHEMA)
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_manifest_record_from_authority(
    payload: Layer3ReplacementPackageArtifactManifestFromAuthorityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_artifact_manifest.record_replacement_package_artifact_manifest_from_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority",
    response_model=Layer3ReplacementPackageArtifactManifestResponse,
    openapi_extra={
        "requestBody": _json_request_body(
            REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA
        )
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_manifest_record_from_corrected_artifact_set_authority(
    payload: Layer3ReplacementPackageArtifactManifestFromCorrectedArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_artifact_manifest.record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/corrected-artifact-set/record",
    response_model=Layer3CorrectedPackageArtifactSetResponse,
    openapi_extra={"requestBody": _json_request_body(CORRECTED_PACKAGE_ARTIFACT_SET_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_corrected_artifact_set_record(
    payload: Layer3CorrectedPackageArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_corrected_package_artifact_set.record_corrected_package_artifact_set(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-namespace/record",
    response_model=Layer3ReplacementPackageNamespaceRecordResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_NAMESPACE_RECORD_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_namespace_record(
    payload: Layer3ReplacementPackageNamespaceRecordRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_namespace.record_replacement_package_namespace(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-namespace/record-from-corrected-artifact-manifest-authority",
    response_model=Layer3ReplacementPackageNamespaceSetResponse,
    openapi_extra={
        "requestBody": _json_request_body(
            REPLACEMENT_PACKAGE_NAMESPACE_FROM_CORRECTED_MANIFEST_REQUEST_SCHEMA
        )
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_namespace_record_from_corrected_artifact_manifest_authority(
    payload: Layer3ReplacementPackageNamespaceFromCorrectedManifestRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_replacement_package_namespace.record_replacement_package_namespace_from_corrected_artifact_manifest_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-activation/commit",
    response_model=Layer3PackageReplacementActivationCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REPLACEMENT_ACTIVATION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_activation_commit(
    payload: Layer3PackageReplacementActivationCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_package_replacement_activation.commit_package_replacement_activation(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/prepare",
    response_model=Layer3HandoffExportPrepareResponse,
    response_model_exclude_unset=True,
    openapi_extra={"requestBody": _json_request_body(HANDOFF_EXPORT_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_handoff_export_prepare(
    payload: Layer3HandoffExportPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.handoff_export_prepare(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/handoff/aps/dispatch",
    response_model=Layer3ApsHandoffDispatchResponse,
    openapi_extra={"requestBody": _json_request_body(APS_HANDOFF_DISPATCH_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_aps_handoff_dispatch(
    payload: Layer3ApsHandoffDispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.aps_handoff_dispatch(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/handoff/export/download/prepare",
    response_model=Layer3ExternalExportDownloadPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_export_download_prepare(
    payload: Layer3ExternalExportDownloadPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_workbench.external_export_download_prepare(db, payload.model_dump(exclude_unset=True))
    )


@router.post(
    "/handoff/connector/record",
    response_model=Layer3ConnectorDispatchRecordResponse,
    openapi_extra={"requestBody": _json_request_body(CONNECTOR_DISPATCH_RECORD_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_connector_dispatch_record(
    payload: Layer3ConnectorDispatchRecordRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_connector_dispatch_entry.record_internal_connector_dispatch(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-destination/receipt",
    response_model=Layer3ConnectorLocalDestinationReceiptResponse,
    openapi_extra={"requestBody": _json_request_body(CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_connector_local_destination_receipt(
    payload: Layer3ConnectorLocalDestinationReceiptRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_connector_local_destination_receipt.record_internal_fake_local_destination_receipt(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-outbox/fake-target",
    response_model=Layer3ServerOwnedLocalOutboxFakeTargetResponse,
    openapi_extra={"requestBody": _json_request_body(SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_server_owned_local_outbox_fake_target(
    payload: Layer3ServerOwnedLocalOutboxFakeTargetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_server_owned_local_outbox_target.record_server_owned_local_outbox_fake_target(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-outbox/write",
    response_model=Layer3ServerOwnedLocalOutboxWriteResponse,
    openapi_extra={"requestBody": _json_request_body(SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_server_owned_local_outbox_write(
    payload: Layer3ServerOwnedLocalOutboxWriteRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_server_owned_local_outbox_write.write_server_owned_local_outbox(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-outbox/provider-private/prepare",
    response_model=Layer3LocalOutboxProviderPrivateHandoffResponse,
    openapi_extra={"requestBody": _json_request_body(LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_local_outbox_provider_private_handoff_prepare(
    payload: Layer3LocalOutboxProviderPrivateHandoffPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_local_outbox_provider_private_handoff.prepare_local_outbox_provider_private_handoff(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/connector/local-outbox/provider-private/status/{provider_private_handoff_receipt_id}",
    response_model=Layer3LocalOutboxProviderPrivateHandoffResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_local_outbox_provider_private_handoff_status(
    provider_private_handoff_receipt_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_local_outbox_provider_private_handoff.local_outbox_provider_private_handoff_status(
            db,
            provider_private_handoff_receipt_id,
        )
    )


@router.post(
    "/handoff/connector/local-outbox/external-local-export/write",
    response_model=Layer3ExternalLocalExportResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_LOCAL_EXPORT_WRITE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_local_export_write(
    payload: Layer3ExternalLocalExportWriteRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_external_local_export.write_external_local_export(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/connector/local-outbox/external-local-export/status/{external_local_export_receipt_id}",
    response_model=Layer3ExternalLocalExportResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_external_local_export_status(
    external_local_export_receipt_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_external_local_export.external_local_export_status(
            db,
            external_local_export_receipt_id,
        )
    )


@router.post(
    "/handoff/export/internal-webhook/dispatch",
    response_model=Layer3InternalWebhookDispatchResponse,
    openapi_extra={"requestBody": _json_request_body(INTERNAL_WEBHOOK_DISPATCH_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_internal_webhook_dispatch(
    payload: Layer3InternalWebhookDispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_internal_webhook_connector.dispatch_internal_webhook(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/export/internal-webhook/status/{internal_webhook_dispatch_receipt_id}",
    response_model=Layer3InternalWebhookDispatchResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_internal_webhook_dispatch_status(
    internal_webhook_dispatch_receipt_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_internal_webhook_connector.internal_webhook_status(
            db,
            internal_webhook_dispatch_receipt_id,
        )
    )


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
    "/handoff/export/download/provider-private-signed-url/prepare",
    response_model=Layer3ProviderPrivateSignedUrlPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PRIVATE_SIGNED_URL_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_private_signed_url_prepare(
    payload: Layer3ProviderPrivateSignedUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_private_signed_url.provider_private_signed_url_prepare(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}",
    response_model=Layer3ProviderPrivateSignedUrlStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_provider_private_signed_url_status(
    provider_signed_url_receipt_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_private_signed_url.provider_private_signed_url_status(
            db,
            provider_signed_url_receipt_id,
        )
    )


@router.post(
    "/handoff/export/download/provider-private-signed-url/revoke",
    response_model=Layer3ProviderPrivateSignedUrlRevokeResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_private_signed_url_revoke(
    payload: Layer3ProviderPrivateSignedUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_private_signed_url.provider_private_signed_url_revoke(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/download/provider-public-url/prepare",
    response_model=Layer3ProviderPublicUrlPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PUBLIC_URL_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_public_url_prepare(
    payload: Layer3ProviderPublicUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_public_url.provider_public_url_prepare(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}",
    response_model=Layer3ProviderPublicUrlStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_provider_public_url_status(
    provider_public_url_receipt_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_public_url.provider_public_url_status(
            db,
            provider_public_url_receipt_id,
        )
    )


@router.post(
    "/handoff/export/download/provider-public-url/revoke",
    response_model=Layer3ProviderPublicUrlRevokeResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PUBLIC_URL_REVOKE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_public_url_revoke(
    payload: Layer3ProviderPublicUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_public_url.provider_public_url_revoke(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/download/provider-public-url/use",
    response_model=Layer3ProviderPublicUrlDeliveryUseResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PUBLIC_URL_DELIVERY_USE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_public_url_delivery_use(
    payload: Layer3ProviderPublicUrlDeliveryUseRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(
        lambda: layer3_provider_public_url_delivery_use.provider_public_url_delivery_use(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


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
            content=workbench_error_response(exc),
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
            content=workbench_error_response(exc),
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
    responses={
        404: {"model": Layer3WorkbenchErrorResponse},
        409: {"model": Layer3WorkbenchErrorResponse},
    },
)
def get_session_summary(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.session_summary(db, session_id))
