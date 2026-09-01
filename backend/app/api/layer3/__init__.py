from __future__ import annotations

import json
from typing import Any, Callable, Literal
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
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
    layer3_sec_edgar_authority_envelope,
    layer3_sec_edgar_downstream_proof,
    layer3_sec_edgar_downstream_status,
    layer3_sec_edgar_html_inline_xbrl_downstream_proof,
    layer3_sec_edgar_html_inline_xbrl_downstream_status,
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof,
    layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_repeatability_trial,
    layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit,
    layer3_sec_edgar_html_inline_xbrl_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_durable_delivery_archive,
    layer3_sec_edgar_live_downstream_proof,
    layer3_sec_edgar_live_downstream_status,
    layer3_sec_edgar_live_repeatability_trial,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_live_material_bridge,
    layer3_sec_edgar_material_bridge,
    layer3_sec_edgar_delivery_status_provenance,
    layer3_sec_edgar_operator_inspection,
    layer3_sec_edgar_operator_product_surface,
    layer3_sec_edgar_arelle_value_reveal,
    layer3_sec_edgar_real_company_corpus_validation,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_edgar_real_filing_downstream_validation,
    layer3_sec_edgar_repeatability_trial,
    layer3_sec_edgar_source_acquisition,
    layer3_sec_xbrl_admission_status,
    layer3_sec_xbrl_auth_binding,
    layer3_sec_xbrl_controlled_value_reveal_submit,
    layer3_sec_xbrl_in_app_auth_policy,
    layer3_sec_xbrl_operator_review_workflow,
    layer3_sec_xbrl_posture,
    layer3_sec_xbrl_value_reveal_authority,
    layer3_provider_private_signed_url,
    layer3_provider_public_url,
    layer3_provider_public_url_delivery_use,
    layer3_server_owned_local_outbox_target,
    layer3_server_owned_local_outbox_write,
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_artifact_status,
    layer3_candidate_b_broader_scope_default_promotion,
    layer3_candidate_b_broader_scope_promotion_readiness,
    layer3_candidate_b_broader_scope_readiness,
    layer3_candidate_b_broader_scope_repeatability_trial,
    layer3_candidate_b_broader_scope_runtime,
    layer3_candidate_b_broader_scope_selector_use,
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_default_readiness,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_final_proof,
    layer3_candidate_b_full_corpus_operator_workflow_completion_failure,
    layer3_candidate_b_full_corpus_operator_workflow_completion_monitor,
    layer3_candidate_b_full_corpus_operator_workflow_execution_boundary,
    layer3_candidate_b_full_corpus_operator_workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_lifecycle,
    layer3_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof,
    layer3_candidate_b_full_corpus_operator_workflow_process_completion_result,
    layer3_candidate_b_full_corpus_operator_workflow_process_execution,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_queue_state,
    layer3_candidate_b_full_corpus_operator_repeatability_checkpoint,
    layer3_candidate_b_full_corpus_repeatability_acceptance_closeout,
    layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint,
    layer3_candidate_b_full_corpus_repeatability_rerun_trial,
    layer3_candidate_b_full_corpus_operator_workflow_retry_policy,
    layer3_candidate_b_full_corpus_operator_workflow_retry_completion_failure,
    layer3_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_retry_queue_state,
    layer3_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_retry_worker_attempt,
    layer3_candidate_b_full_corpus_operator_workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_status,
    layer3_candidate_b_full_corpus_operator_workflow_worker_attempt,
    layer3_candidate_b_operator_workflow_access_policy,
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
    layer3_sec_xbrl_offline_evidence_loader,
    layer3_sec_xbrl_e2e_offline_orchestrator,
    layer3_sec_xbrl_projection_persistence,
    layer3_sec_xbrl_statement_packet_persistence,
    layer3_sec_xbrl_e2e_integration,
)
from app.services import layer3_sec_xbrl_companyfacts_acquire_stage
from app.services import layer3_sec_xbrl_full_pipeline_orchestrator
from app.services.layer3_sec_xbrl_offline_companyfacts_stage import SecXbrlCompanyfactsStageError
from app.core.config import settings
from app.services.layer3_preflight_request_contract import PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS
from app.services.layer3_response_contract import base_response
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    Layer3AnalysisProductError,
    create_analysis_product_draft,
)
from app.services.layer3_analysis_product_promotion import (
    AnalysisProductTransitionRequest,
    transition_analysis_product,
)
from app.services.layer3_sublayer_state import serialize_analysis_product as _serialize_analysis_product
from app.services.layer3_working_set import (
    Layer3WorkingSetError,
    WorkingSetDraft,
    WorkingSetMemberDraft,
    create_working_set,
)

router = APIRouter()

from app.api.layer3._shared import *  # noqa: F401,F403


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
    analysis_product_package_inventory_enabled: bool = False
    layer3_public_dataset_analysis_enabled: bool = False
    layer3_public_connector_value_reveal_enabled: bool = False
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
    candidate_b_runtime_material_bridge_admitted: bool
    candidate_b_runtime_material_bridge_endpoint: str
    candidate_b_runtime_bridge_source_scan_admitted: bool
    candidate_b_runtime_bridge_source_scan_endpoint: str
    candidate_b_artifact_family_status_admitted: bool
    candidate_b_artifact_family_status_endpoint: str
    candidate_b_visual_lane_status_admitted: bool
    candidate_b_visual_lane_status_endpoint: str
    candidate_b_bundle_downstream_proof_admitted: bool
    candidate_b_bundle_downstream_proof_endpoint: str
    candidate_b_runtime_downstream_proof_admitted: bool
    candidate_b_runtime_downstream_proof_endpoint: str
    candidate_b_default_promotion_operator_status_admitted: bool
    candidate_b_default_promotion_operator_status_endpoint: str
    candidate_b_default_promotion_closure_evidence_admitted: bool
    candidate_b_default_promotion_closure_evidence_endpoint: str
    candidate_b_default_promotion_readiness_audit_admitted: bool
    candidate_b_default_promotion_readiness_audit_endpoint: str
    candidate_b_broader_eligible_corpus_scope_readiness_audit_admitted: bool
    candidate_b_broader_eligible_corpus_scope_readiness_audit_endpoint: str
    candidate_b_default_promotion_final_proof_admitted: bool
    candidate_b_default_promotion_final_proof_endpoint: str
    candidate_b_default_promotion_final_proof_status_admitted: bool
    candidate_b_default_promotion_final_proof_status_endpoint: str
    candidate_b_broader_eligible_corpus_default_scope_selector_use_status_admitted: bool
    candidate_b_broader_eligible_corpus_default_scope_selector_use_status_endpoint: str
    candidate_b_broader_eligible_corpus_default_scope_selector_activation_admitted: bool
    candidate_b_broader_eligible_corpus_default_scope_selector_activation_endpoint: str
    candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_admitted: bool
    candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_endpoint: str
    candidate_b_full_corpus_operator_workflow_status_admitted: bool
    candidate_b_full_corpus_operator_workflow_status_endpoint: str
    candidate_b_full_corpus_operator_workflow_run_admitted: bool
    candidate_b_full_corpus_operator_workflow_run_endpoint: str
    candidate_b_full_corpus_operator_workflow_history_admitted: bool
    candidate_b_full_corpus_operator_workflow_history_endpoint: str
    candidate_b_full_corpus_operator_workflow_lifecycle_expire_admitted: bool
    candidate_b_full_corpus_operator_workflow_lifecycle_expire_endpoint: str
    candidate_b_full_corpus_operator_workflow_queue_state_admitted: bool
    candidate_b_full_corpus_operator_workflow_queue_state_endpoint: str
    candidate_b_full_corpus_operator_workflow_scheduler_lease_admitted: bool
    candidate_b_full_corpus_operator_workflow_scheduler_lease_endpoint: str
    candidate_b_full_corpus_operator_workflow_worker_attempt_admitted: bool
    candidate_b_full_corpus_operator_workflow_worker_attempt_endpoint: str
    candidate_b_full_corpus_operator_workflow_progress_checkpoint_admitted: bool
    candidate_b_full_corpus_operator_workflow_progress_checkpoint_endpoint: str
    candidate_b_full_corpus_operator_workflow_completion_failure_admitted: bool
    candidate_b_full_corpus_operator_workflow_completion_failure_endpoint: str
    candidate_b_full_corpus_operator_workflow_execution_boundary_admitted: bool
    candidate_b_full_corpus_operator_workflow_execution_boundary_endpoint: str
    candidate_b_full_corpus_operator_workflow_process_execution_admitted: bool
    candidate_b_full_corpus_operator_workflow_process_execution_endpoint: str
    candidate_b_full_corpus_operator_workflow_process_completion_result_admitted: bool
    candidate_b_full_corpus_operator_workflow_process_completion_result_endpoint: str
    candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_admitted: bool
    candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_endpoint: str
    candidate_b_full_corpus_operator_workflow_completion_monitor_admitted: bool
    candidate_b_full_corpus_operator_workflow_completion_monitor_endpoint: str
    candidate_b_full_corpus_operator_repeatability_checkpoint_admitted: bool
    candidate_b_full_corpus_operator_repeatability_checkpoint_endpoint: str
    candidate_b_full_corpus_repeatability_rerun_trial_admitted: bool
    candidate_b_full_corpus_repeatability_rerun_trial_endpoint: str
    candidate_b_full_corpus_repeatability_acceptance_checkpoint_admitted: bool
    candidate_b_full_corpus_repeatability_acceptance_checkpoint_endpoint: str
    candidate_b_full_corpus_operator_workflow_retry_policy_admitted: bool
    candidate_b_full_corpus_operator_workflow_retry_policy_endpoint: str
    candidate_b_full_corpus_operator_workflow_retry_queue_state_admitted: bool
    candidate_b_full_corpus_operator_workflow_retry_queue_state_endpoint: str
    candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_admitted: bool
    candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_endpoint: str
    candidate_b_full_corpus_operator_workflow_retry_worker_attempt_admitted: bool
    candidate_b_full_corpus_operator_workflow_retry_worker_attempt_endpoint: str
    candidate_b_default_promotion_selector_switch_admitted: bool
    candidate_b_default_promotion_selector_scope: str
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


class Layer3SecEdgarTextTableAuthorityEnvelopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    authority_envelope_mode: str | None = None
    dataset_version_id: str = Field(min_length=1)
    expected_authority_envelope_hash: str | None = None
    expected_parser_family: str | None = None
    expected_source_family: str | None = None
    expected_typed_content_contract_id: str | None = None
    rollback_confirmed: bool = False
    operator_confirmed: bool = False
    actor: str | None = None


class Layer3SecEdgarTextTableMaterialAuthorityBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    bridge_mode: Literal["sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1"]
    dataset_version_id: str = Field(min_length=1)
    authority_envelope_hash: str = Field(min_length=64, max_length=64)
    authority_envelope_ref: str | None = None
    expected_materialization_receipt_hash: str | None = None
    expected_material_preview_hash: str | None = None
    rollback_confirmed: bool = False
    operator_confirmed: bool = False
    actor: str | None = None


class Layer3SecEdgarTextTableSourceAcquisitionAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    acquisition_mode: Literal["sec_edgar_text_table_source_acquisition_authority_v1"]
    operator_decision: Literal["record_sec_edgar_text_table_source_acquisition_authority"]
    dataset_version_id: str = Field(min_length=1)
    source_artifact_receipt_id: str = Field(min_length=1)
    source_artifact_receipt_hash: str = Field(min_length=64, max_length=64)
    source_artifact_ref_hash: str = Field(min_length=64, max_length=64)
    accession_or_submission_id_hash: str = Field(min_length=64, max_length=64)
    cik_or_filer_ref_hash: str = Field(min_length=64, max_length=64)
    form_type: str = Field(min_length=1)
    filing_date: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)
    content_length: int = Field(gt=0)
    parser_family: Literal["sec_edgar_filing"]
    parser_contract_id: Literal["aps_sec_edgar_filing_parser_v1"]
    typed_content_contract_id: Literal["aps_sec_edgar_filing_units_v1"]
    materialization_receipt_hash: str = Field(min_length=64, max_length=64)
    dataset_version_hash: str = Field(min_length=64, max_length=64)
    authority_envelope_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarTextTableLiveSourceArtifactAcquireRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    acquisition_mode: Literal["sec_edgar_text_table_live_source_artifact_acquisition_v1"]
    operator_decision: Literal["acquire_sec_edgar_text_table_live_source_artifact"]
    cik_or_filer_ref: str = Field(min_length=1)
    accession_or_submission_id: str = Field(min_length=1)
    form_type: str = Field(min_length=1)
    filing_date: str = Field(min_length=1)
    expected_content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarCompanyfactsAcquireStageRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    cik: str = Field(min_length=1)
    connector_receipt_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarCompanyfactsAcquireStageResponse(Layer3BaseResponse):
    status: str
    acquire: dict[str, Any]
    stage: dict[str, Any]


class Layer3SecEdgarRealFilingAcquisitionConnectorRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    connector_mode: Literal["sec_edgar_real_filing_acquisition_connector_v1"]
    operator_decision: Literal["acquire_sec_edgar_real_filing_validation_corpus"]
    example_set_mode: Literal["bounded_real_sec_validation_corpus_v1"] | None = None
    cik_refs: list[str] | None = None
    form_types: list[str] | None = None
    company_matrix: list[str] | None = None
    filing_selection_policy: Literal[
        "explicit_form_types_v1",
        "real_company_recent_annual_and_interim_or_current_v1",
    ] | None = None
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarRealFilingDownstreamValidationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    validation_mode: Literal["sec_edgar_real_filing_acquisition_connector_downstream_validation_v1"]
    operator_decision: Literal["record_sec_edgar_real_filing_connector_downstream_validation"]
    connector_receipt_id: str = Field(min_length=1)
    connector_receipt_hash: str = Field(min_length=64, max_length=64)
    connector_example_id: str = Field(min_length=1)
    live_source_artifact_receipt_id: str = Field(min_length=1)
    live_source_artifact_receipt_hash: str = Field(min_length=64, max_length=64)
    source_acquisition_receipt_id: str = Field(min_length=1)
    source_acquisition_receipt_hash: str = Field(min_length=64, max_length=64)
    live_source_artifact_material_bridge_receipt_id: str = Field(min_length=1)
    live_source_artifact_material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    gate_b_decision_manifest_id: str = Field(min_length=1)
    live_downstream_proof_hash: str = Field(min_length=64, max_length=64)
    downstream_proof_hash: str = Field(min_length=64, max_length=64)
    operator_status_request: dict[str, Any]
    operator_status_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarRealCompanyCorpusValidationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    validation_mode: Literal["sec_edgar_real_company_corpus_validation_v1"]
    operator_decision: Literal["validate_sec_edgar_real_company_corpus_product_path"]
    company_matrix: list[str] | None = None
    form_types: list[str] | None = None
    filing_selection_policy: Literal[
        "explicit_form_types_v1",
        "real_company_recent_annual_and_interim_or_current_v1",
    ] | None = None
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarDeliveryStatusProvenanceRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_edgar_delivery_status_provenance_v1"]
    operator_decision: Literal["inspect_sec_edgar_real_company_delivery_status_provenance"]
    sec_edgar_real_company_corpus_validation_receipt_id: str = Field(min_length=1)
    sec_edgar_real_company_corpus_validation_receipt_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarOperatorInspectionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    inspection_mode: Literal["sec_edgar_operator_inspection_v1"]
    operator_decision: Literal["inspect_sec_edgar_real_company_operator_surface"]
    sec_edgar_delivery_status_provenance_receipt_id: str = Field(min_length=1)
    sec_edgar_delivery_status_provenance_receipt_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarOperatorProductSurfaceRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    surface_mode: Literal["sec_edgar_operator_product_surface_runtime_v1"]
    operator_decision: Literal["render_sec_edgar_operator_product_surface"]
    sec_edgar_operator_inspection_receipt_id: str = Field(min_length=1)
    sec_edgar_operator_inspection_receipt_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    value_reveal_policy: Literal["sec_edgar_operator_surface_gated_value_reveal_v1"] | None = None
    value_reveal_confirmation: bool | None = None
    value_reveal_max_records: int | None = None
    actor: str | None = None


class Layer3SecEdgarArelleValueRevealRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str | None = None
    actor: str | None = None
    operator_reveal_confirmation: bool | None = None
    sidecar_receipt_id: str | None = None
    sidecar_receipt_hash: str | None = None
    dataset_version_id: str | None = None
    dataset_version_hash: str | None = None


class Layer3SecEdgarDurableDeliveryArchiveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    archive_mode: Literal["sec_edgar_durable_delivery_archive_v1"]
    operator_decision: Literal["archive_sec_edgar_operator_product_surface_delivery_package"]
    sec_edgar_operator_product_surface_receipt_id: str = Field(min_length=1)
    sec_edgar_operator_product_surface_receipt_hash: str = Field(min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    parser_mode: Literal["sec_edgar_html_inline_xbrl_source_family_parser_v1"]
    operator_decision: Literal["parse_sec_edgar_html_inline_xbrl_source_family"]
    connector_receipt_id: str = Field(min_length=1)
    connector_receipt_hash: str = Field(min_length=64, max_length=64)
    connector_example_id: str = Field(min_length=1)
    live_source_artifact_receipt_id: str = Field(min_length=1)
    live_source_artifact_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlMaterialBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    bridge_mode: Literal["sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority_v1"]
    operator_decision: Literal["bridge_sec_edgar_html_inline_xbrl_parser_to_layer3_material_authority"]
    parser_receipt_id: str = Field(min_length=1)
    parser_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_connector_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_live_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_materialization_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_material_preview_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_gate_b_decision_manifest_id: str | None = None
    rollback_confirmed: bool = False
    operator_confirmed: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    fact_authority_mode: Literal["sec_edgar_html_inline_xbrl_parser_to_fact_authority_v1"]
    operator_decision: Literal["derive_sec_edgar_html_inline_xbrl_fact_authority"]
    parser_receipt_id: str = Field(min_length=1)
    parser_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_connector_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_live_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    expected_primary_document_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_document_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_table_candidate_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inline_xbrl_marker_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    bridge_mode: Literal["sec_edgar_html_inline_xbrl_fact_authority_to_layer3_fact_material_authority_v1"]
    operator_decision: Literal["bridge_sec_edgar_html_inline_xbrl_fact_authority_to_layer3_fact_material_authority"]
    fact_authority_receipt_id: str = Field(min_length=1)
    fact_authority_receipt_hash: str = Field(min_length=64, max_length=64)
    arelle_sidecar_receipt_id: str | None = Field(default=None, min_length=1)
    arelle_sidecar_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    parser_receipt_id: str = Field(min_length=1)
    parser_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_connector_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_live_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    expected_primary_document_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_document_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_table_candidate_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inline_xbrl_marker_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_diagnostics_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_materialization_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_material_preview_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_gate_b_decision_manifest_id: str | None = None
    rollback_confirmed: bool = False
    operator_confirmed: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    classification_mode: Literal["sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1"]
    operator_decision: Literal["classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates"]
    fact_authority_receipt_id: str = Field(min_length=1)
    fact_authority_receipt_hash: str = Field(min_length=64, max_length=64)
    fact_material_bridge_receipt_id: str = Field(min_length=1)
    fact_material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_parser_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_connector_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_live_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    expected_primary_document_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_document_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_table_candidate_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inline_xbrl_marker_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_diagnostics_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_materialization_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_dataset_version_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_gate_b_decision_manifest_id: str | None = None
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    product_mode: Literal["sec_edgar_html_inline_xbrl_statement_candidate_product_v1"]
    operator_decision: Literal["build_sec_edgar_html_inline_xbrl_statement_candidate_product_evidence"]
    statement_classification_receipt_id: str = Field(min_length=1)
    statement_classification_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_fact_authority_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_material_bridge_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_parser_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_connector_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_live_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_source_artifact_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    expected_primary_document_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_document_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_content_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_table_candidate_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inline_xbrl_marker_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_classification_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_classification_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_group_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_unclassified_fact_inventory_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_classification_diagnostics_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_materialization_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_dataset_version_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_gate_b_decision_manifest_id: str | None = None
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    package_review_mode: Literal["sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_v1"]
    operator_decision: Literal["preview_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review"]
    downstream_product_receipt_id: str = Field(min_length=1)
    downstream_product_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_statement_classification_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_authority_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_material_bridge_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_parser_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_candidate_product_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inspection_summary_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_redaction_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitRequest(
    BaseModel
):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    package_construction_mode: Literal[
        "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_commit_v1"
    ]
    operator_decision: Literal["commit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction"]
    package_review_preview_receipt_id: str = Field(min_length=1)
    package_review_preview_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_candidate_package_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_review_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_redaction_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_product_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_classification_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_authority_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_material_bridge_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_parser_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_candidate_product_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inspection_summary_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitRequest(
    BaseModel
):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    package_review_submit_mode: Literal[
        "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_v1"
    ]
    operator_decision: Literal["submit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review"]
    review_decision: Literal["approved", "changes_requested", "rejected", "blocked"]
    decision_notes: str | None = None
    package_construction_receipt_id: str = Field(min_length=1)
    package_construction_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_package_payload_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_payload_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_review_preview_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_candidate_package_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_review_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_redaction_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_product_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_classification_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_authority_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_material_bridge_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_parser_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_candidate_product_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inspection_summary_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareRequest(
    BaseModel
):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    handoff_export_prepare_mode: Literal[
        "sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepare_v1"
    ]
    operator_decision: Literal["prepare_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export"]
    package_review_submit_receipt_id: str = Field(min_length=1)
    package_review_submit_receipt_hash: str = Field(min_length=64, max_length=64)
    expected_package_review_submit_record_ref: str | None = None
    expected_package_construction_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_payload_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_payload_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_review_preview_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_candidate_package_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_review_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_package_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_redaction_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_product_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_classification_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_authority_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_fact_material_bridge_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_parser_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_candidate_product_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_product_order_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_inspection_summary_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_downstream_readiness_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_confirmation: bool = False
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["sec_edgar_html_inline_xbrl_downstream_layer3_e2e_proof_v1"]
    operator_decision: Literal["record_sec_edgar_html_inline_xbrl_downstream_layer3_e2e_proof"]
    parser_receipt_id: str = Field(min_length=1)
    parser_receipt_hash: str = Field(min_length=64, max_length=64)
    material_bridge_receipt_id: str = Field(min_length=1)
    material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    dataset_version_id: str = Field(min_length=1)
    material_preview_hash: str = Field(min_length=64, max_length=64)
    gate_b_decision_manifest_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    selection_manifest_id: str = Field(min_length=1)
    material_snapshot_payload_hash: str = Field(min_length=64, max_length=64)
    coverage_evidence: dict[str, Any]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_e2e_proof_v1"]
    operator_decision: Literal["record_sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_e2e_proof"]
    parser_receipt_id: str = Field(min_length=1)
    parser_receipt_hash: str = Field(min_length=64, max_length=64)
    fact_authority_receipt_id: str = Field(min_length=1)
    fact_authority_receipt_hash: str = Field(min_length=64, max_length=64)
    fact_material_bridge_receipt_id: str = Field(min_length=1)
    fact_material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    dataset_version_id: str = Field(min_length=1)
    material_preview_hash: str = Field(min_length=64, max_length=64)
    gate_b_decision_manifest_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    selection_manifest_id: str = Field(min_length=1)
    material_snapshot_payload_hash: str = Field(min_length=64, max_length=64)
    coverage_evidence: dict[str, Any]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_v1"]
    operator_decision: Literal["inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status"]
    fact_material_downstream_proof_request: dict[str, Any] | None = None
    expected_proof_hash: str | None = Field(default=None, min_length=64, max_length=64)
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    trial_mode: Literal[
        "append_only_trial_receipt_over_original_and_repeat_fact_material_downstream_status_authority_without_sec_fetch_or_processing_execution"
    ]
    operator_decision: Literal[
        "record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial"
    ]
    original_operator_status_request: dict[str, Any]
    original_operator_status_hash: str = Field(min_length=64, max_length=64)
    repeat_operator_status_request: dict[str, Any]
    repeat_operator_status_hash: str = Field(min_length=64, max_length=64)
    operator_repeatability_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarHtmlInlineXbrlDownstreamOperatorStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_edgar_html_inline_xbrl_downstream_operator_status_v1"]
    operator_decision: Literal["inspect_sec_edgar_html_inline_xbrl_downstream_operator_status"]
    html_inline_xbrl_downstream_proof_request: dict[str, Any] | None = None
    expected_proof_hash: str | None = Field(default=None, min_length=64, max_length=64)
    actor: str | None = None


class Layer3SecEdgarTextTableLiveSourceArtifactMaterialAuthorityBridgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    bridge_mode: Literal["sec_edgar_text_table_live_source_artifact_to_layer3_material_authority_v1"]
    live_source_artifact_receipt_id: str = Field(min_length=1)
    live_source_artifact_receipt_hash: str = Field(min_length=64, max_length=64)
    source_acquisition_receipt_id: str = Field(min_length=1)
    source_acquisition_receipt_hash: str = Field(min_length=64, max_length=64)
    dataset_version_id: str = Field(min_length=1)
    authority_envelope_hash: str = Field(min_length=64, max_length=64)
    expected_materialization_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_material_preview_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_gate_b_decision_manifest_id: str | None = None
    rollback_confirmed: bool = False
    operator_confirmed: bool = False
    actor: str | None = None


class Layer3SecEdgarTextTableDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["sec_edgar_text_table_downstream_layer3_e2e_proof_v1"]
    operator_decision: Literal["record_sec_edgar_text_table_downstream_layer3_e2e_proof"]
    dataset_version_id: str = Field(min_length=1)
    authority_envelope_hash: str = Field(min_length=64, max_length=64)
    bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    material_preview_hash: str = Field(min_length=64, max_length=64)
    gate_b_decision_manifest_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    selection_manifest_id: str = Field(min_length=1)
    material_snapshot_payload_hash: str = Field(min_length=64, max_length=64)
    coverage_evidence: dict[str, Any]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarTextTableLiveSourceArtifactDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    proof_mode: Literal["sec_edgar_text_table_live_source_artifact_downstream_layer3_e2e_proof_v1"]
    operator_decision: Literal["record_sec_edgar_text_table_live_source_artifact_downstream_layer3_e2e_proof"]
    live_source_artifact_receipt_id: str = Field(min_length=1)
    live_source_artifact_receipt_hash: str = Field(min_length=64, max_length=64)
    source_acquisition_receipt_id: str = Field(min_length=1)
    source_acquisition_receipt_hash: str = Field(min_length=64, max_length=64)
    dataset_version_id: str = Field(min_length=1)
    authority_envelope_hash: str = Field(min_length=64, max_length=64)
    live_source_artifact_material_bridge_receipt_id: str = Field(min_length=1)
    live_source_artifact_material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    material_bridge_receipt_hash: str = Field(min_length=64, max_length=64)
    material_preview_hash: str = Field(min_length=64, max_length=64)
    gate_b_decision_manifest_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    selection_manifest_id: str = Field(min_length=1)
    material_snapshot_payload_hash: str = Field(min_length=64, max_length=64)
    coverage_evidence: dict[str, Any]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_edgar_text_table_live_source_artifact_downstream_operator_status_v1"]
    operator_decision: Literal["inspect_sec_edgar_text_table_live_source_artifact_downstream_operator_status"]
    live_downstream_proof_request: dict[str, Any] | None = None
    expected_proof_hash: str | None = Field(default=None, min_length=64, max_length=64)
    actor: str | None = None


class Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorRepeatabilityTrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    trial_mode: Literal[
        "append_only_trial_receipt_over_original_and_repeat_live_downstream_status_authority_without_sec_fetch_or_processing_execution"
    ]
    operator_decision: Literal[
        "record_sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial"
    ]
    original_operator_status_request: dict[str, Any]
    original_operator_status_hash: str = Field(min_length=64, max_length=64)
    repeat_operator_status_request: dict[str, Any]
    repeat_operator_status_hash: str = Field(min_length=64, max_length=64)
    operator_repeatability_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecEdgarTextTableDownstreamOperatorStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_edgar_text_table_downstream_layer3_operator_status_v1"]
    operator_decision: Literal["inspect_sec_edgar_text_table_downstream_layer3_operator_status"]
    downstream_proof_request: dict[str, Any] | None = None
    expected_proof_hash: str | None = Field(default=None, min_length=64, max_length=64)
    actor: str | None = None


class Layer3SecEdgarTextTableDownstreamOperatorRepeatabilityTrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str | None = None
    schema_version: int | None = None
    client_request_id: str = Field(min_length=1)
    trial_mode: Literal[
        "append_only_trial_receipt_over_original_and_repeat_downstream_status_authority_without_sec_fetch_or_processing_execution"
    ]
    operator_decision: Literal["record_sec_edgar_text_table_downstream_operator_repeatability_trial"]
    original_operator_status_request: dict[str, Any]
    original_operator_status_hash: str = Field(min_length=64, max_length=64)
    repeat_operator_status_request: dict[str, Any]
    repeat_operator_status_hash: str = Field(min_length=64, max_length=64)
    operator_repeatability_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    operator_confirmation: bool
    actor: str | None = None


class Layer3SecXbrlOperatorReviewWorkflowOpenRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str = Field(min_length=1)
    sec_xbrl_statement_packet_set_id: str = Field(min_length=1)


class Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str = Field(min_length=1)
    expected_sidecar_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    expected_statement_classification_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    period_limit: int = Field(default=3, ge=1, le=10)
    connector_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    cik_hash: str | None = Field(default=None, min_length=64, max_length=64)
    require_companyfacts_oracle: bool = False


class Layer3SecXbrlOperatorReviewWorkflowOpenFullPipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    company_matrix: list[str]
    cik: str = Field(min_length=1)
    period_limit: int = Field(default=3, ge=1, le=10)
    require_companyfacts_oracle: bool = False
    operator_confirmation: bool = False


class Layer3SecXbrlOperatorReviewWorkflowStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_xbrl_operator_review_workflow_status_v1"]
    operator_decision: Literal["inspect_sec_xbrl_operator_review_workflow_status"]
    sec_xbrl_operator_review_workflow_id: str | None = Field(default=None, min_length=1)
    workflow_basis_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_role: Literal["owner", "auditor"] | None = Field(default=None)


class Layer3SecXbrlProductionAdmissionStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    admission_status_mode: Literal["sec_xbrl_production_admission_status_v1"]
    operator_decision: Literal["inspect_sec_xbrl_production_admission_status"]
    sec_xbrl_operator_review_workflow_id: str | None = Field(default=None, min_length=1)
    workflow_basis_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_role: Literal["owner", "auditor"] | None = Field(default=None)


class Layer3SecXbrlOperatorReviewWorkflowAuditorAttachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_request_id: str = Field(min_length=1)
    auditor_attach_mode: Literal["sec_xbrl_operator_review_workflow_auditor_attach_v1"]
    operator_decision: Literal["attach_sec_xbrl_operator_review_auditor_read"]
    sec_xbrl_operator_review_workflow_id: str | None = Field(default=None, min_length=1)
    workflow_basis_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_role: Literal["auditor"]  # attach is auditor-only; selector, gated server-side


class Layer3SecXbrlOperatorReviewDecisionSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str = Field(min_length=1)
    submit_mode: Literal["sec_xbrl_operator_review_decision_submit_v1"]
    operator_decision: Literal["submit_sec_xbrl_operator_review_decision"]
    review_decision: Literal["approved", "changes_requested", "rejected", "blocked"]
    decision_reason_code: Literal[
        "ready_for_next_freeze",
        "needs_packet_revision",
        "authority_gap",
        "redaction_gap",
        "operator_blocked",
    ]
    sec_xbrl_operator_review_workflow_id: str | None = Field(default=None, min_length=1)
    workflow_basis_hash: str | None = Field(default=None, min_length=64, max_length=64)
    decision_notes: str | None = None


class Layer3SecXbrlOperatorReviewDecisionStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["sec_xbrl_operator_review_decision_status_v1"]
    operator_decision: Literal["inspect_sec_xbrl_operator_review_decision_status"]
    sec_xbrl_operator_review_decision_id: str | None = Field(default=None, min_length=1)
    decision_basis_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_role: Literal["owner", "auditor"] | None = Field(default=None)


class Layer3SecXbrlValueRevealAuthorityPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str = Field(min_length=1)
    authority_mode: Literal["sec_xbrl_value_reveal_authority_receipt_v1"]
    operator_decision: Literal["prepare_sec_xbrl_value_reveal_authority"]
    sec_xbrl_operator_review_decision_id: str = Field(min_length=1)
    decision_basis_hash: str = Field(min_length=64, max_length=64)
    operator_attestation: str | None = None


class Layer3SecXbrlControlledValueRevealSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_request_id: str = Field(min_length=1)
    submit_mode: Literal["sec_xbrl_controlled_value_reveal_submit_v1"]
    operator_decision: Literal["submit_explicit_sec_xbrl_value_reveal_from_authority_receipt"]
    sec_xbrl_value_reveal_authority_receipt_id: str = Field(min_length=1)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    operator_reveal_confirmation: Literal[True]
    max_records: int | None = Field(default=None, ge=1)
    page_cursor: str | None = None


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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
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
    onlook: Any | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
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
    external_export_download: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    connector_ref: Any | None = None
    connector_dispatch: Any | None = None
    onlook: Any | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
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
    external_export_download: Any | None = None
    provider_public_url: Any | None = None
    public_url: Any | None = None
    connector_ref: Any | None = None
    connector_dispatch: Any | None = None
    onlook: Any | None = None


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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
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
    download_url: Any | None = None
    provider_public_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    signed_url: Any | None = None
    destination: Any | None = None
    connector_dispatch: Any | None = None
    connector_ref: Any | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
    construction_basis_hash: str | None = None
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
    expected_package_kinds: Any | None = None
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


class Layer3MixedSourceExternalExportDownloadReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = None
    session_id: str | None = None
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    package_review_preview_hash: str | None = None
    contract_hash: str | None = None
    construction_basis_hash: str | None = None
    reconciliation_record_id: str | None = None
    output_package_ids: Any | None = None
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
    aps_handoff_record_ref: str | None = None
    aps_handoff_state: str | None = None
    operator_decision: str | None = None
    decision_notes: str | None = None
    expected_package_kinds: Any | None = None
    analysis_plan_id: Any | None = None
    pass_run_id: Any | None = None
    preview_id: Any | None = None
    preview_hash: Any | None = None
    result_review_record_ref: Any | None = None
    analysis_run_id: Any | None = None
    package_kinds: Any | None = None
    payload_refs: Any | None = None
    external_export: Any | None = None
    external_target: Any | None = None
    download: Any | None = None
    download_url: Any | None = None
    signed_url: Any | None = None
    provider_public_url: Any | None = None
    provider_private_signed_url: Any | None = None
    provider_url: Any | None = None
    public_url: Any | None = None
    destination: Any | None = None
    destination_selector: Any | None = None
    connector_run_id: Any | None = None
    connector_dispatch: Any | None = None
    dispatch: Any | None = None
    send: Any | None = None
    local_outbox: Any | None = None
    outbox: Any | None = None
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


class Layer3ConnectorDatasetHandoffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str
    session_id: str


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
    bridge_mode: Literal[
        "candidate_b_runtime_source_to_layer3_material_authority_v1",
        "candidate_b_full_corpus_runtime_to_layer3_material_authority_v1",
    ]
    candidate_b_run_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    operator_confirmation: bool


class Layer3CandidateBRuntimeBridgeSourceScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    source_scan_mode: Literal["candidate_b_runtime_bridge_curated_source_scan_v1"]
    operator_decision: Literal["scan_candidate_b_runtime_bridge_curated_material_root"]
    bridge_receipt_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    operator_confirmation: bool
    source_family: Literal["server_configured_operator_directory_text_table_source_family"] | None = None
    ingestion_mode: Literal["server_configured_operator_directory_text_table_ingestion"] | None = None


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


class Layer3CandidateBFullCorpusOperatorWorkflowStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_full_corpus_operator_workflow_status_v1"]
    operator_decision: Literal["inspect_candidate_b_full_corpus_operator_workflow_status"]
    operator_role: Literal["owner", "auditor"] | None = None
    policy_hash: str | None = Field(default=None, min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    bridge_receipt_id: str = Field(min_length=1)
    downstream_proof_id: str = Field(min_length=1)


class Layer3CandidateBFullCorpusOperatorWorkflowRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    run_mode: Literal["candidate_b_full_corpus_operator_workflow_run_v1"]
    operator_decision: Literal["start_candidate_b_full_corpus_operator_workflow"]
    operator_role: Literal["owner"] | None = None
    policy_hash: str | None = Field(default=None, min_length=64, max_length=64)
    runtime_root_lifecycle_receipt_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    compare_target_set_hash: str = Field(min_length=64, max_length=64)
    material_relative_name: str | None = None


class Layer3CandidateBFullCorpusOperatorWorkflowLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    lifecycle_mode: Literal["candidate_b_operator_workflow_run_expiry_closeout_receipt_v1"]
    operator_decision: Literal["expire_or_close_server_owned_workflow_run_receipt"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowQueueStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    queue_state_mode: Literal["append_only_queue_state_receipt_without_background_scheduler"]
    operator_decision: Literal["record_candidate_b_async_workflow_queue_state"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowSchedulerLeaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    scheduler_lease_mode: Literal["append_only_scheduler_lease_receipt_without_background_worker"]
    operator_decision: Literal["record_candidate_b_async_scheduler_lease"]
    queue_state_receipt_id: str = Field(min_length=1)
    queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowWorkerAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    worker_attempt_mode: Literal["append_only_worker_attempt_receipt_without_job_execution"]
    operator_decision: Literal["record_candidate_b_async_worker_attempt"]
    worker_attempt_number: Literal[1]
    scheduler_lease_receipt_id: str = Field(min_length=1)
    scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    queue_state_receipt_id: str = Field(min_length=1)
    queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowProgressCheckpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    progress_checkpoint_mode: Literal[
        "append_only_progress_checkpoint_receipt_without_completion_or_cancel_retry_resume"
    ]
    operator_decision: Literal["record_candidate_b_async_progress_checkpoint"]
    progress_checkpoint_sequence: int = Field(ge=1)
    worker_attempt_receipt_id: str = Field(min_length=1)
    worker_attempt_receipt_hash: str = Field(min_length=64, max_length=64)
    worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_receipt_id: str = Field(min_length=1)
    scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    queue_state_receipt_id: str = Field(min_length=1)
    queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowCompletionFailureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    completion_failure_mode: Literal[
        "append_only_completion_failure_receipt_without_cancel_retry_resume_or_source_receipt_mutation"
    ]
    operator_decision: Literal["record_candidate_b_async_completion_failure"]
    terminal_outcome: Literal["completed", "failed"]
    terminal_failure_code: str | None = None
    terminal_failure_phase: str | None = None
    latest_progress_checkpoint_receipt_id: str = Field(min_length=1)
    latest_progress_checkpoint_receipt_hash: str = Field(min_length=64, max_length=64)
    latest_progress_checkpoint_authority_hash: str = Field(min_length=64, max_length=64)
    progress_checkpoint_sequence: int = Field(ge=1)
    worker_attempt_receipt_id: str = Field(min_length=1)
    worker_attempt_receipt_hash: str = Field(min_length=64, max_length=64)
    worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_receipt_id: str = Field(min_length=1)
    scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    queue_state_receipt_id: str = Field(min_length=1)
    queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowRetryPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    retry_policy_mode: Literal[
        "append_only_retry_policy_receipt_without_creating_retry_attempt_or_mutating_terminal_receipts"
    ]
    operator_decision: Literal["record_candidate_b_async_retry_policy"]
    retry_policy_result: Literal["eligible", "ineligible"]
    retry_policy_reason: str = Field(min_length=1)
    completion_failure_receipt_id: str = Field(min_length=1)
    completion_failure_receipt_hash: str = Field(min_length=64, max_length=64)
    completion_failure_authority_hash: str = Field(min_length=64, max_length=64)
    terminal_outcome: str = Field(min_length=1)
    terminal_outcome_hash: str = Field(min_length=64, max_length=64)
    latest_progress_checkpoint_receipt_id: str = Field(min_length=1)
    latest_progress_checkpoint_receipt_hash: str = Field(min_length=64, max_length=64)
    latest_progress_checkpoint_authority_hash: str = Field(min_length=64, max_length=64)
    progress_checkpoint_sequence: int = Field(ge=1)
    worker_attempt_receipt_id: str = Field(min_length=1)
    worker_attempt_receipt_hash: str = Field(min_length=64, max_length=64)
    worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_receipt_id: str = Field(min_length=1)
    scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    queue_state_receipt_id: str = Field(min_length=1)
    queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowRetryQueueStateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    retry_queue_state_mode: Literal[
        "append_only_retry_queue_state_receipt_without_creating_scheduler_lease_worker_attempt_or_mutating_original_lineage"
    ]
    operator_decision: Literal["record_candidate_b_async_retry_queue_state"]
    retry_policy_receipt_id: str = Field(min_length=1)
    retry_policy_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_policy_authority_hash: str = Field(min_length=64, max_length=64)
    retry_policy_result: Literal["eligible", "ineligible"]
    completion_failure_receipt_id: str = Field(min_length=1)
    completion_failure_receipt_hash: str = Field(min_length=64, max_length=64)
    completion_failure_authority_hash: str = Field(min_length=64, max_length=64)
    failed_worker_attempt_receipt_id: str = Field(min_length=1)
    failed_worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    retry_scheduler_lease_mode: Literal[
        "append_only_retry_scheduler_lease_receipt_without_creating_worker_attempt_or_mutating_retry_queue_state_original_lineage"
    ]
    operator_decision: Literal["record_candidate_b_async_retry_scheduler_lease"]
    retry_queue_state_receipt_id: str = Field(min_length=1)
    retry_queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    retry_attempt_number: int = Field(ge=2)
    retry_policy_receipt_id: str = Field(min_length=1)
    retry_policy_authority_hash: str = Field(min_length=64, max_length=64)
    completion_failure_receipt_id: str = Field(min_length=1)
    failed_worker_attempt_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    retry_worker_attempt_mode: Literal["append_only_retry_worker_attempt_receipt_without_job_execution"]
    operator_decision: Literal["record_candidate_b_async_retry_worker_attempt"]
    retry_attempt_number: Literal[2]
    retry_scheduler_lease_receipt_id: str = Field(min_length=1)
    retry_scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_receipt_id: str = Field(min_length=1)
    retry_queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    retry_policy_receipt_id: str = Field(min_length=1)
    retry_policy_authority_hash: str = Field(min_length=64, max_length=64)
    completion_failure_receipt_id: str = Field(min_length=1)
    failed_worker_attempt_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    retry_progress_checkpoint_mode: Literal[
        "append_only_retry_progress_checkpoint_receipt_without_retry_completion_cancel_resume_or_job_execution"
    ]
    operator_decision: Literal["record_candidate_b_async_retry_progress_checkpoint"]
    retry_progress_checkpoint_sequence: int = Field(ge=1)
    retry_attempt_number: Literal[2]
    retry_worker_attempt_receipt_id: str = Field(min_length=1)
    retry_worker_attempt_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    retry_scheduler_lease_receipt_id: str = Field(min_length=1)
    retry_scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_receipt_id: str = Field(min_length=1)
    retry_queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    retry_policy_receipt_id: str = Field(min_length=1)
    retry_policy_authority_hash: str = Field(min_length=64, max_length=64)
    completion_failure_receipt_id: str = Field(min_length=1)
    failed_worker_attempt_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    retry_completion_failure_mode: Literal[
        "append_only_retry_completion_failure_receipt_without_cancel_resume_job_execution_or_source_receipt_mutation"
    ]
    operator_decision: Literal["record_candidate_b_async_retry_completion_failure"]
    retry_terminal_outcome: Literal["completed", "failed"]
    terminal_failure_code: str | None = None
    terminal_failure_phase: str | None = None
    retry_attempt_number: Literal[2]
    latest_retry_progress_checkpoint_receipt_id: str = Field(min_length=1)
    latest_retry_progress_checkpoint_receipt_hash: str = Field(min_length=64, max_length=64)
    latest_retry_progress_checkpoint_authority_hash: str = Field(min_length=64, max_length=64)
    retry_progress_checkpoint_sequence: int = Field(ge=1)
    retry_worker_attempt_receipt_id: str = Field(min_length=1)
    retry_worker_attempt_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    retry_scheduler_lease_receipt_id: str = Field(min_length=1)
    retry_scheduler_lease_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_scheduler_lease_authority_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_receipt_id: str = Field(min_length=1)
    retry_queue_state_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_queue_state_authority_hash: str = Field(min_length=64, max_length=64)
    retry_policy_receipt_id: str = Field(min_length=1)
    retry_policy_receipt_hash: str = Field(min_length=64, max_length=64)
    retry_policy_authority_hash: str = Field(min_length=64, max_length=64)
    completion_failure_receipt_id: str = Field(min_length=1)
    completion_failure_receipt_hash: str = Field(min_length=64, max_length=64)
    completion_failure_authority_hash: str = Field(min_length=64, max_length=64)
    failed_worker_attempt_receipt_id: str = Field(min_length=1)
    failed_worker_attempt_receipt_hash: str = Field(min_length=64, max_length=64)
    failed_worker_attempt_authority_hash: str = Field(min_length=64, max_length=64)
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowExecutionBoundaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    execution_boundary_mode: Literal[
        "append_only_execution_boundary_receipt_without_process_start_or_job_execution"
    ]
    operator_decision: Literal["record_candidate_b_async_background_job_execution_boundary"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowProcessExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    process_execution_mode: Literal[
        "server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority"
    ]
    operator_decision: Literal["record_candidate_b_async_background_process_execution"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)
    execution_boundary_receipt_id: str = Field(min_length=1)
    execution_boundary_receipt_hash: str = Field(min_length=64, max_length=64)
    execution_boundary_authority_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowProcessCompletionResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    process_completion_result_mode: Literal[
        "append_only_process_completion_result_adoption_receipt_without_source_run_mutation_or_raw_output_exposure"
    ]
    operator_decision: Literal["record_candidate_b_async_process_completion_result_adoption"]
    terminal_state: Literal["completed", "failed", "blocked", "expired"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)
    process_execution_receipt_id: str = Field(min_length=1)
    process_execution_receipt_hash: str = Field(min_length=64, max_length=64)
    process_execution_authority_hash: str = Field(min_length=64, max_length=64)
    result_workflow_receipt_id: str | None = None
    result_workflow_receipt_hash: str | None = Field(default=None, min_length=64, max_length=64)
    terminal_failure_code: str | None = None
    terminal_failure_phase: str | None = None
    redacted_failure_summary_hash: str | None = Field(default=None, min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    adopted_result_downstream_proof_mode: Literal[
        "read_only_adopted_process_result_downstream_operator_proof_without_result_mutation_or_reexecution"
    ]
    operator_decision: Literal["record_candidate_b_async_adopted_process_result_downstream_operator_proof"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)
    process_completion_result_receipt_id: str = Field(min_length=1)
    process_completion_result_receipt_hash: str = Field(min_length=64, max_length=64)
    process_completion_result_authority_hash: str = Field(min_length=64, max_length=64)
    process_execution_receipt_id: str = Field(min_length=1)
    process_execution_receipt_hash: str = Field(min_length=64, max_length=64)
    process_execution_authority_hash: str = Field(min_length=64, max_length=64)
    result_workflow_receipt_id: str = Field(min_length=1)
    result_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    result_status_request_hash: str = Field(min_length=64, max_length=64)
    result_downstream_proof_hash: str = Field(min_length=64, max_length=64)


class Layer3CandidateBFullCorpusOperatorWorkflowCompletionMonitorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    completion_monitor_mode: Literal[
        "read_only_operator_workflow_completion_monitor_without_process_control_result_mutation_or_reexecution"
    ]
    operator_decision: Literal["inspect_candidate_b_async_operator_workflow_completion_monitor"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)
    process_execution_receipt_id: str | None = None
    process_execution_receipt_hash: str | None = None
    process_completion_result_receipt_id: str | None = None
    process_completion_result_receipt_hash: str | None = None
    adopted_result_downstream_proof_receipt_id: str | None = None
    adopted_result_downstream_proof_receipt_hash: str | None = None


class Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    repeatability_checkpoint_mode: Literal[
        "append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation"
    ]
    operator_decision: Literal["record_candidate_b_full_corpus_operator_repeatability_checkpoint"]
    operator_workflow_receipt_id: str = Field(min_length=1)
    operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
    authority_basis_hash: str = Field(min_length=64, max_length=64)
    history_hash: str = Field(min_length=64, max_length=64)
    workflow_status_hash: str = Field(min_length=64, max_length=64)
    completion_monitor_hash: str = Field(min_length=64, max_length=64)
    runtime_root_lifecycle_receipt_id: str = Field(min_length=1)
    bridge_receipt_id: str = Field(min_length=1)
    downstream_proof_id: str = Field(min_length=1)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    candidate_b_run_id: str = Field(min_length=1)
    compare_target_set_hash: str = Field(min_length=64, max_length=64)
    material_relative_name: str = Field(min_length=1)
    operator_runbook_repeatability_steps: list[str] = Field(min_length=4, max_length=4)


class Layer3CandidateBFullCorpusRepeatabilityRerunTrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    rerun_trial_mode: Literal[
        "append_only_repeatability_rerun_trial_receipt_without_process_execution_or_authority_mutation"
    ]
    operator_decision: Literal["record_candidate_b_full_corpus_repeatability_rerun_trial"]
    original_repeatability_checkpoint_receipt_id: str = Field(min_length=1)
    original_repeatability_checkpoint_receipt_hash: str = Field(min_length=64, max_length=64)
    original_repeatability_checkpoint_hash: str = Field(min_length=64, max_length=64)
    original_repeatability_checkpoint_authority_hash: str = Field(min_length=64, max_length=64)
    original_operator_workflow_receipt_id: str = Field(min_length=1)
    original_operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    original_row_hash: str = Field(min_length=64, max_length=64)
    original_authority_basis_hash: str = Field(min_length=64, max_length=64)
    original_history_hash: str = Field(min_length=64, max_length=64)
    original_workflow_status_hash: str = Field(min_length=64, max_length=64)
    original_completion_monitor_hash: str = Field(min_length=64, max_length=64)
    rerun_operator_workflow_receipt_id: str = Field(min_length=1)
    rerun_operator_workflow_receipt_hash: str = Field(min_length=64, max_length=64)
    rerun_row_hash: str = Field(min_length=64, max_length=64)
    rerun_authority_basis_hash: str = Field(min_length=64, max_length=64)
    rerun_history_hash: str = Field(min_length=64, max_length=64)
    rerun_workflow_status_hash: str = Field(min_length=64, max_length=64)
    rerun_completion_monitor_hash: str = Field(min_length=64, max_length=64)
    baseline_run_id: str = Field(min_length=1)
    candidate_a_run_id: str = Field(min_length=1)
    original_candidate_b_run_id: str = Field(min_length=1)
    rerun_candidate_b_run_id: str = Field(min_length=1)
    compare_target_set_hash: str = Field(min_length=64, max_length=64)
    material_relative_name: str = Field(min_length=1)
    regression_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    operator_runbook_repeatability_steps: list[str] = Field(min_length=7, max_length=7)


class Layer3CandidateBFullCorpusRepeatabilityAcceptanceCheckpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    acceptance_checkpoint_mode: Literal[
        "append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation"
    ]
    operator_decision: Literal["record_candidate_b_full_corpus_repeatability_acceptance_checkpoint"]
    operator_acceptance_decision: str = Field(min_length=1)
    original_repeatability_checkpoint_receipt_id: str = Field(min_length=1)
    original_repeatability_checkpoint_receipt_hash: str = Field(min_length=64, max_length=64)
    original_repeatability_checkpoint_hash: str = Field(min_length=64, max_length=64)
    original_repeatability_checkpoint_authority_hash: str = Field(min_length=64, max_length=64)
    repeatability_rerun_trial_receipt_id: str = Field(min_length=1)
    repeatability_rerun_trial_receipt_hash: str = Field(min_length=64, max_length=64)
    repeatability_rerun_trial_hash: str = Field(min_length=64, max_length=64)
    repeatability_rerun_trial_authority_hash: str = Field(min_length=64, max_length=64)
    original_workflow_status_hash: str = Field(min_length=64, max_length=64)
    original_completion_monitor_hash: str = Field(min_length=64, max_length=64)
    rerun_workflow_status_hash: str = Field(min_length=64, max_length=64)
    rerun_completion_monitor_hash: str = Field(min_length=64, max_length=64)
    acceptance_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    operator_runbook_repeatability_steps: list[str] = Field(min_length=4, max_length=4)


class Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    acceptance_closeout_mode: Literal[
        "append_only_acceptance_operator_closeout_receipt_without_process_execution_or_authority_mutation"
    ]
    operator_decision: Literal["record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout"]
    repeatability_acceptance_checkpoint_receipt_id: str = Field(min_length=1)
    repeatability_acceptance_checkpoint_receipt_hash: str = Field(min_length=64, max_length=64)
    repeatability_acceptance_checkpoint_hash: str = Field(min_length=64, max_length=64)
    repeatability_acceptance_checkpoint_authority_hash: str = Field(min_length=64, max_length=64)
    acceptance_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    rendered_acceptance_control_mode: Literal[
        "rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control"
    ]
    rendered_acceptance_control_proof_state: Literal["headed_and_headless_passed"]
    headless_rendered_proof_label: Literal[
        "candidate_b_repeatability_acceptance_rendered_control_headless_chromium_pass"
    ]
    headed_rendered_proof_label: Literal[
        "candidate_b_repeatability_acceptance_rendered_control_headed_chromium_pass"
    ]
    operator_runbook_closeout_steps: list[str] = Field(min_length=4, max_length=4)
    negative_invariant_attestations: dict[str, bool]


class Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    closeout_status_mode: Literal[
        "read_only_acceptance_closeout_status_without_receipt_creation_lineage_mutation_or_frontend_authority"
    ]
    operator_decision: Literal["inspect_candidate_b_full_corpus_repeatability_acceptance_closeout_status"]
    operator_role: Literal["auditor"] | None = None
    repeatability_acceptance_operator_closeout_receipt_id: str | None = Field(default=None, min_length=1)
    repeatability_acceptance_operator_closeout_receipt_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    repeatability_acceptance_checkpoint_receipt_id: str | None = Field(default=None, min_length=1)
    repeatability_acceptance_checkpoint_receipt_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    repeatability_acceptance_checkpoint_authority_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )


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


class Layer3CandidateBBroaderEligibleCorpusScopeReadinessAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    audit_mode: Literal["candidate_b_broader_eligible_corpus_scope_readiness_audit_v1"]
    exact_corpus_class_list: list[str]
    explicit_exclusion_list: list[str]
    proposed_default_scope_classes: list[str]
    scope_evidence: dict[str, Any]
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeRuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    runtime_mode: Literal["candidate_b_broader_eligible_corpus_default_scope_runtime_v1"]
    readiness_audit_id: str = Field(min_length=1)
    readiness_audit_hash: str = Field(min_length=1)
    readiness_audit: dict[str, Any] | None = None
    selected_scope_classes: list[str]
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    selector_use_mode: Literal["candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1"]
    runtime_selection_receipt_id: str = Field(min_length=1)
    runtime_selection_receipt_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_broader_eligible_corpus_default_scope_selector_use_status_v1"]
    operator_decision: Literal["inspect_candidate_b_broader_eligible_corpus_default_scope_selector_use_status"]
    selector_use_receipt_id: str = Field(min_length=1)
    selector_use_receipt_hash: str = Field(min_length=1)
    runtime_selection_receipt_id: str = Field(min_length=1)
    runtime_selection_receipt_hash: str = Field(min_length=1)


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    activation_mode: Literal["candidate_b_broader_eligible_corpus_default_scope_selector_activation_runtime_v1"]
    selector_use_status_hash: str = Field(min_length=1)
    selector_use_receipt_id: str = Field(min_length=1)
    selector_use_receipt_hash: str = Field(min_length=1)
    runtime_selection_receipt_id: str = Field(min_length=1)
    runtime_selection_receipt_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeActivationReceiptConsumptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    consumption_mode: Literal[
        "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_runtime_v1"
    ]
    activation_receipt_id: str = Field(min_length=1)
    activation_receipt_hash: str = Field(min_length=1)
    selector_use_status_hash: str = Field(min_length=1)
    selector_use_receipt_id: str = Field(min_length=1)
    selector_use_receipt_hash: str = Field(min_length=1)
    runtime_selection_receipt_id: str = Field(min_length=1)
    runtime_selection_receipt_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    use_mode: Literal["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_runtime_v1"]
    consumption_receipt_id: str = Field(min_length=1)
    consumption_receipt_hash: str = Field(min_length=1)
    activation_receipt_id: str = Field(min_length=1)
    activation_receipt_hash: str = Field(min_length=1)
    selector_use_status_hash: str = Field(min_length=1)
    selector_use_receipt_id: str = Field(min_length=1)
    selector_use_receipt_hash: str = Field(min_length=1)
    runtime_selection_receipt_id: str = Field(min_length=1)
    runtime_selection_receipt_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    status_mode: Literal["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_v1"]
    operator_decision: Literal[
        "inspect_candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status"
    ]
    use_receipt_id: str = Field(min_length=1)
    use_receipt_hash: str = Field(min_length=1)
    consumption_receipt_id: str = Field(min_length=1)
    consumption_receipt_hash: str = Field(min_length=1)
    activation_receipt_id: str = Field(min_length=1)
    activation_receipt_hash: str = Field(min_length=1)
    selector_use_status_hash: str = Field(min_length=1)
    selector_use_receipt_id: str = Field(min_length=1)
    selector_use_receipt_hash: str = Field(min_length=1)
    runtime_selection_receipt_id: str = Field(min_length=1)
    runtime_selection_receipt_hash: str = Field(min_length=1)
    readiness_audit_id: str = Field(min_length=1)
    readiness_audit_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeOperatorRepeatabilityTrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    trial_mode: Literal[
        "append_only_trial_receipt_over_original_and_repeat_use_status_authority_without_processing_execution"
    ]
    operator_decision: Literal["record_candidate_b_broader_scope_operator_repeatability_trial"]
    operator_repeatability_disposition: Literal[
        "no_regression_observed",
        "delta_reviewed_no_regression",
        "regression_detected_blocked",
    ]
    selected_scope_classes: list[str]
    original_use_receipt_status_hash: str = Field(min_length=1)
    original_use_receipt_id: str = Field(min_length=1)
    original_use_receipt_hash: str = Field(min_length=1)
    original_consumption_receipt_id: str = Field(min_length=1)
    original_consumption_receipt_hash: str = Field(min_length=1)
    original_activation_receipt_id: str = Field(min_length=1)
    original_activation_receipt_hash: str = Field(min_length=1)
    original_selector_use_status_hash: str = Field(min_length=1)
    original_selector_use_receipt_id: str = Field(min_length=1)
    original_selector_use_receipt_hash: str = Field(min_length=1)
    original_runtime_selection_receipt_id: str = Field(min_length=1)
    original_runtime_selection_receipt_hash: str = Field(min_length=1)
    original_readiness_audit_id: str = Field(min_length=1)
    original_readiness_audit_hash: str = Field(min_length=1)
    repeat_use_receipt_status_hash: str = Field(min_length=1)
    repeat_use_receipt_id: str = Field(min_length=1)
    repeat_use_receipt_hash: str = Field(min_length=1)
    repeat_consumption_receipt_id: str = Field(min_length=1)
    repeat_consumption_receipt_hash: str = Field(min_length=1)
    repeat_activation_receipt_id: str = Field(min_length=1)
    repeat_activation_receipt_hash: str = Field(min_length=1)
    repeat_selector_use_status_hash: str = Field(min_length=1)
    repeat_selector_use_receipt_id: str = Field(min_length=1)
    repeat_selector_use_receipt_hash: str = Field(min_length=1)
    repeat_runtime_selection_receipt_id: str = Field(min_length=1)
    repeat_runtime_selection_receipt_hash: str = Field(min_length=1)
    repeat_readiness_audit_id: str = Field(min_length=1)
    repeat_readiness_audit_hash: str = Field(min_length=1)
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopePromotionReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    readiness_mode: Literal[
        "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_audit_v1"
    ]
    operator_decision: Literal["evaluate_candidate_b_broader_scope_default_promotion_readiness"]
    trial_receipt_id: str = Field(min_length=1)
    trial_receipt_hash: str = Field(min_length=1)
    trial_authority_hash: str = Field(min_length=1)
    authority_pair_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]
    production_ownership_storage_policy: dict[str, Any] | None = None
    operator_visible_status_confirmed: bool
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeDefaultPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str = Field(min_length=1)
    promotion_mode: Literal[
        "candidate_b_broader_eligible_corpus_default_scope_default_promotion_runtime_v1"
    ]
    operator_decision: Literal["record_candidate_b_broader_scope_default_promotion"]
    promotion_readiness_audit_id: str = Field(min_length=1)
    promotion_readiness_audit_hash: str = Field(min_length=1)
    promotion_readiness_audit: dict[str, Any]
    trial_receipt_id: str = Field(min_length=1)
    trial_receipt_hash: str = Field(min_length=1)
    selected_scope_classes: list[str]
    production_policy_hash: str = Field(min_length=1)
    operator_visible_status_confirmed: bool
    promotion_readiness_rendered_status_confirmed: bool
    promotion_readiness_closeout_confirmed: bool
    rollback_to_baseline_confirmation: bool
    operator_confirmation: bool


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
    runtime_delivery_artifact_authority_hash: str
    runtime_delivery_artifact_coverage_steps: list[str]
    runtime_delivery_artifact_projection_visible: bool
    runtime_delivery_artifact_roles_bound: bool
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


class Layer3CandidateBFullCorpusOperatorWorkflowStatusResponse(Layer3BaseResponse):
    mode: str
    workflow_receipt_id: str
    workflow_receipt_hash: str
    workflow_status: str
    workflow_status_hash: str
    workflow_status_ref: str
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_run_id: str
    compare_target_set_hash: str
    bridge_receipt_id: str
    bridge_receipt_hash: str
    downstream_proof_id: str
    downstream_proof_hash: str
    coverage_count: int
    corpus: dict[str, Any]
    eligibility_summary: dict[str, Any]
    baseline_rollback: dict[str, Any]
    layer3: dict[str, Any]
    artifact_family: dict[str, Any]
    runtime_root_lifecycle: dict[str, Any]
    retry_terminal_status_projection: dict[str, Any]
    execution_boundary_projection: dict[str, Any]
    process_execution_projection: dict[str, Any]
    process_completion_result_projection: dict[str, Any]
    adopted_result_downstream_proof_projection: dict[str, Any]
    operator_projection: dict[str, Any]
    validate_only_triplet: bool
    artifacts_seeded_or_generated_by_triplet_validator: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowHistoryResponse(Layer3BaseResponse):
    mode: str
    history_scope: str
    history_state: str
    status_endpoint: str
    rendered_history_mode: str
    receipt_count: int
    history_rows: list[dict[str, Any]]
    history_hash: str
    history_ref: str
    configured_receipt_authority_used: bool
    read_only_history_projection: bool
    single_run_status_endpoint_reused_for_detail: bool
    browser_supplied_receipt_root_admitted: bool
    browser_supplied_runtime_roots_admitted: bool
    browser_supplied_source_directory_admitted: bool
    browser_supplied_bridge_dir_admitted: bool
    operator_supplied_local_path_admitted: bool
    operator_supplied_raw_url_admitted: bool
    cancel_runtime_admitted: bool
    retry_runtime_admitted: bool
    retry_progress_checkpoint_runtime_admitted: bool
    retry_terminal_status_projection_runtime_admitted: bool
    execution_boundary_runtime_admitted: bool
    process_execution_runtime_admitted: bool
    process_completion_result_runtime_admitted: bool
    adopted_result_downstream_proof_runtime_admitted: bool
    resume_runtime_admitted: bool
    queue_state_authority_runtime_admitted: bool
    queue_scheduler_runtime_admitted: bool
    expiry_mutation_runtime_admitted: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRunResponse(Layer3BaseResponse):
    mode: str
    status: str
    run_state: str
    state_machine: list[str]
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    run_receipt_id: str
    run_receipt_hash: str
    run_receipt_ref: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    runtime_root_lifecycle: dict[str, Any]
    baseline_run_id: str
    candidate_a_run_id: str
    candidate_b_run_id: str
    compare_target_set_hash: str
    bridge_receipt_id: str
    bridge_receipt_hash: str
    downstream_proof_id: str
    downstream_proof_hash: str
    coverage_count: int
    corpus: dict[str, Any]
    layer3: dict[str, Any]
    artifact_family: dict[str, Any]
    baseline_rollback: dict[str, Any]
    status_endpoint: str
    status_request: dict[str, Any]
    receipt_persisted: bool
    queue_scheduler_admitted: str
    cancel_endpoint_admitted: str
    rendered_run_start_control_admitted: bool
    rendered_progress_control_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowLifecycleResponse(Layer3BaseResponse):
    mode: str
    status: str
    lifecycle_state: str
    lifecycle_receipt_id: str
    lifecycle_receipt_hash: str
    lifecycle_receipt_ref: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    lifecycle_authority: dict[str, Any]
    lifecycle_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_lifecycle_receipt: bool
    source_run_receipt_mutated: bool
    run_state_before_lifecycle: str
    run_state_after_lifecycle: str
    selected_lifecycle_action: str
    rendered_lifecycle_mode: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    queue_scheduler_runtime_selected_now: bool
    expiry_closeout_runtime_selected: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowQueueStateResponse(Layer3BaseResponse):
    mode: str
    status: str
    queue_state: str
    queue_state_receipt_id: str
    queue_state_receipt_hash: str
    queue_state_receipt_ref: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    queue_state_record: dict[str, Any]
    queue_state_hash: str
    queue_state_authority: dict[str, Any]
    queue_state_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_queue_state_receipt: bool
    source_run_receipt_mutated: bool
    run_state_before_queue_state: str
    run_state_after_queue_state: str
    selected_queue_state_mode: str
    selected_queue_state_endpoint: str
    rendered_queue_state_mode: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    queue_state_authority_runtime_selected: bool
    queue_scheduler_runtime_selected_now: bool
    background_worker_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowSchedulerLeaseResponse(Layer3BaseResponse):
    mode: str
    status: str
    scheduler_lease_state: str
    scheduler_lease_receipt_id: str
    scheduler_lease_receipt_hash: str
    scheduler_lease_receipt_ref: str
    queue_state_receipt_id: str
    queue_state_receipt_hash: str
    queue_state_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    scheduler_lease: dict[str, Any]
    scheduler_lease_hash: str
    scheduler_lease_authority: dict[str, Any]
    scheduler_lease_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_scheduler_lease_receipt: bool
    exclusive_queue_state_lease: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    run_state_before_scheduler_lease: str
    run_state_after_scheduler_lease: str
    queue_state_before_scheduler_lease: str
    selected_scheduler_mode: str
    selected_scheduler_endpoint: str
    selected_scheduler_receipt_binding: str
    selected_scheduler_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    queue_state_endpoint: str
    scheduler_lease_runtime_selected: bool
    background_worker_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowWorkerAttemptResponse(Layer3BaseResponse):
    mode: str
    status: str
    worker_attempt_state: str
    worker_attempt_number: int
    worker_attempt_receipt_id: str
    worker_attempt_receipt_hash: str
    worker_attempt_receipt_ref: str
    scheduler_lease_receipt_id: str
    scheduler_lease_receipt_hash: str
    scheduler_lease_authority_hash: str
    queue_state_receipt_id: str
    queue_state_receipt_hash: str
    queue_state_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    worker_attempt: dict[str, Any]
    worker_attempt_hash: str
    worker_attempt_authority: dict[str, Any]
    worker_attempt_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_worker_attempt_receipt: bool
    exclusive_initial_attempt_per_scheduler_lease: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    run_state_before_worker_attempt: str
    run_state_after_worker_attempt: str
    scheduler_lease_state_before_worker_attempt: str
    selected_worker_attempt_mode: str
    selected_worker_attempt_endpoint: str
    selected_worker_attempt_receipt_binding: str
    selected_worker_attempt_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    queue_state_endpoint: str
    scheduler_lease_endpoint: str
    worker_attempt_endpoint: str
    worker_attempt_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    progress_checkpoint_runtime_selected_now: bool
    completion_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowProgressCheckpointResponse(Layer3BaseResponse):
    mode: str
    status: str
    progress_checkpoint_state: str
    progress_checkpoint_sequence: int
    progress_checkpoint_receipt_id: str
    progress_checkpoint_receipt_hash: str
    progress_checkpoint_receipt_ref: str
    worker_attempt_receipt_id: str
    worker_attempt_receipt_hash: str
    worker_attempt_authority_hash: str
    scheduler_lease_receipt_id: str
    scheduler_lease_receipt_hash: str
    scheduler_lease_authority_hash: str
    queue_state_receipt_id: str
    queue_state_receipt_hash: str
    queue_state_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    previous_progress_checkpoint_sequence: int | None
    previous_progress_checkpoint_receipt_id: str | None
    progress_checkpoint: dict[str, Any]
    progress_checkpoint_hash: str
    progress_checkpoint_authority: dict[str, Any]
    progress_checkpoint_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_progress_checkpoint_receipt: bool
    monotonic_progress_checkpoint_sequence: bool
    worker_attempt_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    run_state_before_progress_checkpoint: str
    run_state_after_progress_checkpoint: str
    worker_attempt_state_before_progress_checkpoint: str
    selected_progress_checkpoint_mode: str
    selected_progress_checkpoint_endpoint: str
    selected_progress_checkpoint_receipt_binding: str
    selected_progress_checkpoint_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    queue_state_endpoint: str
    scheduler_lease_endpoint: str
    worker_attempt_endpoint: str
    progress_checkpoint_endpoint: str
    progress_checkpoint_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    completion_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowCompletionFailureResponse(Layer3BaseResponse):
    mode: str
    completion_failure_state: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_receipt_ref: str
    terminal_outcome: str
    terminal_failure_code: str | None
    terminal_failure_phase: str | None
    terminal_outcome_hash: str
    worker_attempt_receipt_id: str
    worker_attempt_receipt_hash: str
    worker_attempt_authority_hash: str
    latest_progress_checkpoint_receipt_id: str
    latest_progress_checkpoint_receipt_hash: str
    latest_progress_checkpoint_authority_hash: str
    progress_checkpoint_sequence: int
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    completion_failure_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_completion_failure_receipt: bool
    exclusive_terminal_receipt_per_worker_attempt: bool
    progress_checkpoint_receipt_mutated: bool
    worker_attempt_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    selected_completion_failure_mode: str
    selected_completion_failure_endpoint: str
    selected_completion_failure_receipt_binding: str
    selected_completion_failure_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    progress_checkpoint_endpoint: str
    completion_failure_endpoint: str
    completion_failure_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    terminal_failure_payload_operator_safe: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRetryPolicyResponse(Layer3BaseResponse):
    mode: str
    retry_policy_state: str
    retry_policy_receipt_id: str
    retry_policy_receipt_hash: str
    retry_policy_receipt_ref: str
    retry_policy_result: str
    retry_policy_reason: str
    retry_policy_hash: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_authority_hash: str
    terminal_outcome: str
    terminal_outcome_hash: str
    terminal_failure_code: str
    terminal_failure_phase: str
    worker_attempt_receipt_id: str
    worker_attempt_receipt_hash: str
    worker_attempt_authority_hash: str
    latest_progress_checkpoint_receipt_id: str
    latest_progress_checkpoint_receipt_hash: str
    latest_progress_checkpoint_authority_hash: str
    progress_checkpoint_sequence: int
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    retry_policy_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_retry_policy_receipt: bool
    exclusive_retry_policy_per_failed_terminal_receipt: bool
    retry_attempt_created: bool
    completion_failure_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    worker_attempt_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    selected_retry_policy_mode: str
    selected_retry_policy_endpoint: str
    selected_retry_policy_receipt_binding: str
    selected_retry_policy_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    progress_checkpoint_endpoint: str
    completion_failure_endpoint: str
    retry_policy_endpoint: str
    retry_policy_runtime_selected: bool
    retry_attempt_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRetryQueueStateResponse(Layer3BaseResponse):
    mode: str
    retry_queue_state: str
    retry_queue_state_receipt_id: str
    retry_queue_state_receipt_hash: str
    retry_queue_state_receipt_ref: str
    retry_attempt_number: int
    retry_policy_receipt_id: str
    retry_policy_receipt_hash: str
    retry_policy_authority_hash: str
    retry_policy_result: str
    retry_policy_reason: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_authority_hash: str
    terminal_outcome: str
    terminal_failure_code: str
    terminal_failure_phase: str
    failed_worker_attempt_receipt_id: str
    failed_worker_attempt_receipt_hash: str
    failed_worker_attempt_authority_hash: str
    latest_progress_checkpoint_receipt_id: str
    latest_progress_checkpoint_receipt_hash: str
    latest_progress_checkpoint_authority_hash: str
    progress_checkpoint_sequence: int
    original_scheduler_lease_receipt_id: str
    original_scheduler_lease_receipt_hash: str
    original_scheduler_lease_authority_hash: str
    original_queue_state_receipt_id: str
    original_queue_state_receipt_hash: str
    original_queue_state_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    retry_queue_state_hash: str
    retry_queue_state_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_retry_queue_state_receipt: bool
    exclusive_retry_queue_state_per_eligible_retry_policy_receipt: bool
    retry_policy_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    worker_attempt_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    selected_retry_queue_state_mode: str
    selected_retry_queue_state_endpoint: str
    selected_retry_queue_state_receipt_binding: str
    selected_retry_queue_state_idempotency_basis: str
    retry_policy_result_required: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    retry_policy_endpoint: str
    retry_queue_state_endpoint: str
    retry_queue_state_runtime_selected: bool
    retry_scheduler_lease_creation_admitted_now: bool
    retry_worker_attempt_creation_admitted_now: bool
    retry_progress_checkpoint_creation_admitted_now: bool
    retry_completion_failure_creation_admitted_now: bool
    retry_attempt_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseResponse(Layer3BaseResponse):
    mode: str
    retry_scheduler_lease_state: str
    retry_scheduler_lease_receipt_id: str
    retry_scheduler_lease_receipt_hash: str
    retry_scheduler_lease_receipt_ref: str
    retry_attempt_number: int
    retry_queue_state_receipt_id: str
    retry_queue_state_receipt_hash: str
    retry_queue_state_authority_hash: str
    retry_policy_receipt_id: str
    retry_policy_receipt_hash: str
    retry_policy_authority_hash: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_authority_hash: str
    failed_worker_attempt_receipt_id: str
    failed_worker_attempt_receipt_hash: str
    failed_worker_attempt_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    retry_scheduler_lease_hash: str
    retry_scheduler_lease_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_retry_scheduler_lease_receipt: bool
    exclusive_retry_queue_state_lease: bool
    retry_queue_state_receipt_mutated: bool
    retry_policy_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    worker_attempt_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    selected_retry_scheduler_lease_mode: str
    selected_retry_scheduler_lease_endpoint: str
    selected_retry_scheduler_lease_receipt_binding: str
    selected_retry_scheduler_lease_idempotency_basis: str
    retry_queue_state_receipt_required: bool
    retry_queue_state_runtime_required: bool
    retry_attempt_number_required: int
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    retry_queue_state_endpoint: str
    retry_scheduler_lease_endpoint: str
    retry_scheduler_lease_runtime_selected: bool
    retry_worker_attempt_creation_admitted_now: bool
    retry_progress_checkpoint_creation_admitted_now: bool
    retry_completion_failure_creation_admitted_now: bool
    retry_worker_attempt_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptResponse(Layer3BaseResponse):
    mode: str
    retry_worker_attempt_state: str
    retry_worker_attempt_receipt_id: str
    retry_worker_attempt_receipt_hash: str
    retry_worker_attempt_receipt_ref: str
    retry_attempt_number: int
    retry_scheduler_lease_receipt_id: str
    retry_scheduler_lease_receipt_hash: str
    retry_scheduler_lease_authority_hash: str
    retry_queue_state_receipt_id: str
    retry_queue_state_receipt_hash: str
    retry_queue_state_authority_hash: str
    retry_policy_receipt_id: str
    retry_policy_receipt_hash: str
    retry_policy_authority_hash: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_authority_hash: str
    failed_worker_attempt_receipt_id: str
    failed_worker_attempt_receipt_hash: str
    failed_worker_attempt_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    retry_worker_attempt: dict[str, Any]
    retry_worker_attempt_hash: str
    retry_worker_attempt_authority: dict[str, Any]
    retry_worker_attempt_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_retry_worker_attempt_receipt: bool
    exclusive_retry_worker_attempt_per_retry_scheduler_lease: bool
    retry_scheduler_lease_receipt_mutated: bool
    retry_queue_state_receipt_mutated: bool
    retry_policy_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    failed_worker_attempt_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    run_state_before_retry_worker_attempt: str
    run_state_after_retry_worker_attempt: str
    retry_scheduler_lease_state_before_retry_worker_attempt: str
    selected_retry_worker_attempt_mode: str
    selected_retry_worker_attempt_endpoint: str
    selected_retry_worker_attempt_receipt_binding: str
    selected_retry_worker_attempt_idempotency_basis: str
    selected_retry_worker_attempt_number: int
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    retry_queue_state_endpoint: str
    retry_scheduler_lease_endpoint: str
    retry_worker_attempt_endpoint: str
    retry_worker_attempt_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    retry_progress_checkpoint_runtime_selected_now: bool
    retry_completion_failure_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointResponse(Layer3BaseResponse):
    mode: str
    retry_progress_checkpoint_state: str
    retry_progress_checkpoint_sequence: int
    retry_progress_checkpoint_receipt_id: str
    retry_progress_checkpoint_receipt_hash: str
    retry_progress_checkpoint_receipt_ref: str
    retry_attempt_number: int
    retry_worker_attempt_receipt_id: str
    retry_worker_attempt_receipt_hash: str
    retry_worker_attempt_authority_hash: str
    retry_scheduler_lease_receipt_id: str
    retry_scheduler_lease_receipt_hash: str
    retry_scheduler_lease_authority_hash: str
    retry_queue_state_receipt_id: str
    retry_queue_state_receipt_hash: str
    retry_queue_state_authority_hash: str
    retry_policy_receipt_id: str
    retry_policy_receipt_hash: str
    retry_policy_authority_hash: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_authority_hash: str
    failed_worker_attempt_receipt_id: str
    failed_worker_attempt_receipt_hash: str
    failed_worker_attempt_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    source_operator_workflow_receipt_id: str
    source_operator_workflow_receipt_hash: str
    authority_basis_hash: str
    row_hash: str
    history_hash: str
    previous_retry_progress_checkpoint_sequence: int | None
    previous_retry_progress_checkpoint_receipt_id: str | None
    retry_progress_checkpoint: dict[str, Any]
    retry_progress_checkpoint_hash: str
    retry_progress_checkpoint_authority: dict[str, Any]
    retry_progress_checkpoint_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_retry_progress_checkpoint_receipt: bool
    monotonic_retry_progress_checkpoint_sequence: bool
    retry_worker_attempt_receipt_mutated: bool
    retry_scheduler_lease_receipt_mutated: bool
    retry_queue_state_receipt_mutated: bool
    retry_policy_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    failed_worker_attempt_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    run_state_before_retry_progress_checkpoint: str
    run_state_after_retry_progress_checkpoint: str
    retry_worker_attempt_state_before_retry_progress_checkpoint: str
    selected_retry_progress_checkpoint_mode: str
    selected_retry_progress_checkpoint_endpoint: str
    selected_retry_progress_checkpoint_receipt_binding: str
    selected_retry_progress_checkpoint_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    retry_queue_state_endpoint: str
    retry_scheduler_lease_endpoint: str
    retry_worker_attempt_endpoint: str
    retry_progress_checkpoint_endpoint: str
    retry_progress_checkpoint_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    retry_completion_failure_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    default_scope_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureResponse(Layer3BaseResponse):
    mode: str
    retry_completion_failure_state: str
    retry_completion_failure_receipt_id: str
    retry_completion_failure_receipt_hash: str
    retry_completion_failure_receipt_ref: str
    retry_terminal_outcome: str
    terminal_failure_code: str | None
    terminal_failure_phase: str | None
    retry_terminal_outcome_hash: str
    retry_attempt_number: int
    latest_retry_progress_checkpoint_receipt_id: str
    latest_retry_progress_checkpoint_receipt_hash: str
    latest_retry_progress_checkpoint_authority_hash: str
    retry_progress_checkpoint_sequence: int
    retry_worker_attempt_receipt_id: str
    retry_worker_attempt_receipt_hash: str
    retry_worker_attempt_authority_hash: str
    retry_scheduler_lease_receipt_id: str
    retry_scheduler_lease_receipt_hash: str
    retry_scheduler_lease_authority_hash: str
    retry_queue_state_receipt_id: str
    retry_queue_state_receipt_hash: str
    retry_queue_state_authority_hash: str
    retry_policy_receipt_id: str
    retry_policy_receipt_hash: str
    retry_policy_authority_hash: str
    completion_failure_receipt_id: str
    completion_failure_receipt_hash: str
    completion_failure_authority_hash: str
    failed_worker_attempt_receipt_id: str
    failed_worker_attempt_receipt_hash: str
    failed_worker_attempt_authority_hash: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    retry_completion_failure_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_retry_completion_failure_receipt: bool
    exclusive_retry_terminal_receipt_per_retry_worker_attempt: bool
    retry_progress_checkpoint_receipt_mutated: bool
    retry_worker_attempt_receipt_mutated: bool
    retry_scheduler_lease_receipt_mutated: bool
    retry_queue_state_receipt_mutated: bool
    retry_policy_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    failed_worker_attempt_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    source_run_receipt_mutated: bool
    selected_retry_completion_failure_mode: str
    selected_retry_completion_failure_endpoint: str
    selected_retry_completion_failure_receipt_binding: str
    selected_retry_completion_failure_idempotency_basis: str
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    retry_queue_state_endpoint: str
    retry_scheduler_lease_endpoint: str
    retry_worker_attempt_endpoint: str
    retry_progress_checkpoint_endpoint: str
    retry_completion_failure_endpoint: str
    retry_completion_failure_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    cancel_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    expiry_enforcement_runtime_selected_now: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    retry_terminal_failure_payload_operator_safe: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowExecutionBoundaryResponse(Layer3BaseResponse):
    mode: str
    execution_boundary_state: str
    execution_boundary_receipt_id: str
    execution_boundary_receipt_hash: str
    execution_boundary_receipt_ref: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    row_hash: str
    authority_basis_hash: str
    history_hash: str
    execution_boundary: dict[str, Any]
    execution_boundary_hash: str
    execution_boundary_authority: dict[str, Any]
    execution_boundary_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_execution_boundary_receipt: bool
    source_run_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    worker_attempt_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    retry_policy_receipt_mutated: bool
    retry_queue_state_receipt_mutated: bool
    retry_scheduler_lease_receipt_mutated: bool
    retry_worker_attempt_receipt_mutated: bool
    retry_progress_checkpoint_receipt_mutated: bool
    retry_completion_failure_receipt_mutated: bool
    execution_boundary_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    actual_subprocess_spawn_admitted_now: bool
    actual_corpus_processing_execution_admitted_now: bool
    browser_triggered_process_start_admitted: bool
    operator_supplied_command_admitted: bool
    operator_supplied_local_path_admitted: bool
    operator_supplied_raw_url_admitted: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    execution_boundary_endpoint: str
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowProcessExecutionResponse(Layer3BaseResponse):
    mode: str
    process_execution_state: str
    process_execution_receipt_id: str
    process_execution_receipt_hash: str
    process_execution_receipt_ref: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    row_hash: str
    authority_basis_hash: str
    history_hash: str
    execution_boundary_receipt_id: str
    execution_boundary_receipt_hash: str
    execution_boundary_authority_hash: str
    process_invocation: dict[str, Any]
    process_invocation_hash: str
    process_execution_authority: dict[str, Any]
    process_execution_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    allowlisted_command_family: str
    redacted_process_status_projection: dict[str, Any]
    redacted_process_ref: str
    server_process_handle_hash: str
    process_failure_recorded: bool = False
    process_timeout_recorded: bool = False
    process_failure_code: str = ""
    process_failure_phase: str = ""
    redacted_failure_summary_hash: str = ""
    append_only_process_execution_receipt: bool
    process_started: bool
    source_run_receipt_mutated: bool
    queue_state_receipt_mutated: bool
    scheduler_lease_receipt_mutated: bool
    worker_attempt_receipt_mutated: bool
    progress_checkpoint_receipt_mutated: bool
    completion_failure_receipt_mutated: bool
    retry_completion_failure_receipt_mutated: bool
    execution_boundary_receipt_mutated: bool
    background_process_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    actual_subprocess_spawn_admitted_now: bool
    actual_corpus_processing_execution_admitted_now: bool
    browser_triggered_process_start_admitted: bool
    operator_supplied_command_admitted: bool
    operator_supplied_local_path_admitted: bool
    operator_supplied_raw_url_admitted: bool
    cancel_runtime_selected_now: bool
    retry_runtime_selected_now: bool
    resume_runtime_selected_now: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    process_execution_endpoint: str
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowProcessCompletionResultResponse(Layer3BaseResponse):
    mode: str
    process_completion_result_state: str
    process_completion_result_receipt_id: str
    process_completion_result_receipt_hash: str
    process_completion_result_receipt_ref: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    row_hash: str
    authority_basis_hash: str
    history_hash: str
    process_execution_receipt_id: str
    process_execution_receipt_hash: str
    process_execution_authority_hash: str
    terminal_state: str
    result_workflow_receipt_id: str
    result_workflow_receipt_hash: str
    result_authority_hash: str
    result_status_request: dict[str, Any]
    result_status_request_hash: str
    result_downstream_proof_hash: str
    terminal_failure_code: str
    terminal_failure_phase: str
    redacted_failure_summary_hash: str
    process_completion_result_authority: dict[str, Any]
    process_completion_result_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_process_completion_result_receipt: bool
    process_execution_receipt_mutated: bool
    source_run_receipt_mutated: bool
    execution_boundary_receipt_mutated: bool
    process_completion_result_runtime_selected: bool
    result_adoption_runtime_selected: bool
    background_process_runtime_selected_now: bool
    job_execution_runtime_selected_now: bool
    actual_subprocess_spawn_admitted_now: bool
    actual_corpus_processing_execution_admitted_now: bool
    browser_triggered_process_start_admitted: bool
    operator_supplied_command_admitted: bool
    operator_supplied_local_path_admitted: bool
    operator_supplied_raw_url_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    default_scope_expansion_admitted: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    process_completion_result_endpoint: str
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    adopted_result_downstream_proof_state: str
    adopted_result_downstream_proof_receipt_id: str
    adopted_result_downstream_proof_receipt_hash: str
    adopted_result_downstream_proof_receipt_ref: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    row_hash: str
    authority_basis_hash: str
    history_hash: str
    process_completion_result_receipt_id: str
    process_completion_result_receipt_hash: str
    process_completion_result_authority_hash: str
    process_execution_receipt_id: str
    process_execution_receipt_hash: str
    process_execution_authority_hash: str
    result_workflow_receipt_id: str
    result_workflow_receipt_hash: str
    result_authority_hash: str
    result_status_request_hash: str
    result_downstream_proof_hash: str
    adopted_result_status_hash: str
    adopted_result_downstream_proof_status: str
    adopted_result_layer3_projection: dict[str, Any]
    adopted_result_downstream_proof_authority: dict[str, Any]
    adopted_result_downstream_proof_authority_hash: str
    idempotency_key_hash: str
    idempotent_replay: bool
    append_only_adopted_result_downstream_proof_receipt: bool
    process_completion_result_receipt_mutated: bool
    process_execution_receipt_mutated: bool
    source_run_receipt_mutated: bool
    adopted_result_workflow_receipt_mutated: bool
    downstream_proof_receipt_mutated: bool
    adopted_result_downstream_proof_runtime_selected: bool
    actual_subprocess_spawn_admitted_now: bool
    actual_corpus_processing_execution_admitted_now: bool
    browser_triggered_process_start_admitted: bool
    operator_supplied_command_admitted: bool
    operator_supplied_local_path_admitted: bool
    operator_supplied_raw_url_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    default_scope_expansion_admitted: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_exception_trace_admitted: bool
    raw_log_excerpt_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    status_endpoint: str
    status_request: dict[str, Any]
    history_endpoint: str
    history_request: dict[str, Any]
    adopted_result_downstream_proof_endpoint: str
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorWorkflowCompletionMonitorResponse(Layer3BaseResponse):
    mode: str
    operator_workflow_receipt_id: str
    operator_workflow_receipt_hash: str
    row_hash: str
    authority_basis_hash: str
    history_hash: str
    completion_monitor_state: str
    completion_monitor_hash: str
    completion_monitor_ref: str
    completion_monitor_endpoint: str
    history_endpoint: str
    status_endpoint: str
    process_execution_projection: dict[str, Any]
    process_completion_result_projection: dict[str, Any]
    adopted_result_downstream_proof_projection: dict[str, Any]
    operator_projection: dict[str, Any]
    read_only_completion_monitor_projection: bool
    process_control_admitted: bool
    process_kill_cancel_retry_resume_admitted: bool
    process_completion_result_mutation_admitted: bool
    process_execution_receipt_mutation_admitted: bool
    source_run_receipt_mutation_admitted: bool
    raw_pid_admitted: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    default_scope_expansion_admitted: bool
    selector_mutation_performed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    repeatability_checkpoint_state: str
    repeatability_checkpoint_receipt_id: str
    repeatability_checkpoint_hash: str
    repeatability_checkpoint_authority_hash: str
    repeatability_checkpoint_receipt_hash: str
    repeatability_checkpoint_receipt_ref: str
    repeatability_checkpoint: dict[str, Any]
    repeatability_checkpoint_authority: dict[str, Any]
    append_only_repeatability_checkpoint_receipt: bool
    exclusive_repeatability_checkpoint_per_authority: bool
    idempotent_replay: bool
    workflow_receipt_mutated: bool
    process_execution_receipt_mutated: bool
    process_completion_result_receipt_mutated: bool
    adopted_result_downstream_proof_receipt_mutated: bool
    actual_corpus_processing_execution_admitted_now: bool
    actual_subprocess_spawn_admitted_now: bool
    process_control_admitted: bool
    process_kill_cancel_retry_resume_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    default_scope_expansion_admitted: bool
    raw_pid_admitted: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    history_endpoint: str
    status_endpoint: str
    completion_monitor_endpoint: str
    repeatability_checkpoint_endpoint: str
    status_request: dict[str, Any]
    history_request: dict[str, Any]
    completion_monitor_request: dict[str, Any]
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusRepeatabilityRerunTrialResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    repeatability_rerun_trial_state: str
    repeatability_rerun_trial_receipt_id: str
    repeatability_rerun_trial_hash: str
    repeatability_rerun_trial_authority_hash: str
    repeatability_rerun_trial_receipt_hash: str
    repeatability_rerun_trial_receipt_ref: str
    repeatability_rerun_trial: dict[str, Any]
    repeatability_rerun_trial_authority: dict[str, Any]
    append_only_repeatability_rerun_trial_receipt: bool
    exclusive_repeatability_rerun_trial_per_authority: bool
    idempotent_replay: bool
    original_repeatability_checkpoint_receipt_mutated: bool
    original_workflow_receipt_mutated: bool
    rerun_workflow_receipt_mutated: bool
    process_execution_receipt_mutated: bool
    process_completion_result_receipt_mutated: bool
    adopted_result_downstream_proof_receipt_mutated: bool
    actual_corpus_processing_execution_admitted_now: bool
    actual_subprocess_spawn_admitted_now: bool
    process_control_admitted: bool
    process_kill_cancel_retry_resume_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    default_scope_expansion_admitted: bool
    raw_pid_admitted: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    history_endpoint: str
    status_endpoint: str
    completion_monitor_endpoint: str
    repeatability_checkpoint_endpoint: str
    repeatability_rerun_trial_endpoint: str
    original_status_request: dict[str, Any]
    rerun_status_request: dict[str, Any]
    history_request: dict[str, Any]
    original_completion_monitor_request: dict[str, Any]
    rerun_completion_monitor_request: dict[str, Any]
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusRepeatabilityAcceptanceCheckpointResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    repeatability_acceptance_checkpoint_state: str
    repeatability_acceptance_checkpoint_receipt_id: str
    repeatability_acceptance_checkpoint_hash: str
    repeatability_acceptance_checkpoint_authority_hash: str
    repeatability_acceptance_checkpoint_receipt_hash: str
    repeatability_acceptance_checkpoint_receipt_ref: str
    repeatability_acceptance_checkpoint: dict[str, Any]
    repeatability_acceptance_checkpoint_authority: dict[str, Any]
    append_only_repeatability_acceptance_checkpoint_receipt: bool
    exclusive_repeatability_acceptance_checkpoint_per_authority: bool
    idempotent_replay: bool
    original_repeatability_checkpoint_receipt_mutated: bool
    repeatability_rerun_trial_receipt_mutated: bool
    original_workflow_receipt_mutated: bool
    rerun_workflow_receipt_mutated: bool
    process_execution_receipt_mutated: bool
    process_completion_result_receipt_mutated: bool
    adopted_result_downstream_proof_receipt_mutated: bool
    actual_corpus_processing_execution_admitted_now: bool
    actual_subprocess_spawn_admitted_now: bool
    process_control_admitted: bool
    process_kill_cancel_retry_resume_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    default_scope_expansion_admitted: bool
    raw_pid_admitted: bool
    raw_stdout_admitted: bool
    raw_stderr_admitted: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    selector_mutation_performed: bool
    repeatability_checkpoint_endpoint: str
    repeatability_rerun_trial_endpoint: str
    repeatability_acceptance_checkpoint_endpoint: str
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    repeatability_acceptance_operator_closeout_state: str
    repeatability_acceptance_operator_closeout_receipt_id: str
    repeatability_acceptance_operator_closeout_hash: str
    repeatability_acceptance_operator_closeout_authority_hash: str
    repeatability_acceptance_operator_closeout_receipt_hash: str
    repeatability_acceptance_operator_closeout_receipt_ref: str
    repeatability_acceptance_operator_closeout: dict[str, Any]
    repeatability_acceptance_operator_closeout_authority: dict[str, Any]
    append_only_repeatability_acceptance_operator_closeout_receipt: bool
    exclusive_repeatability_acceptance_operator_closeout_per_authority: bool
    idempotent_replay: bool
    repeatability_acceptance_operator_closeout_receipt_mutation_admitted: bool
    repeatability_acceptance_checkpoint_receipt_mutated: bool
    original_repeatability_checkpoint_receipt_mutated: bool
    repeatability_rerun_trial_receipt_mutated: bool
    original_workflow_receipt_mutated: bool
    rerun_workflow_receipt_mutated: bool
    process_execution_receipt_mutated: bool
    process_completion_result_receipt_mutated: bool
    adopted_result_downstream_proof_receipt_mutated: bool
    baseline_rollback_preserved: bool
    candidate_a_semantics_preserved: bool
    candidate_b_default_scope_preserved: str
    negative_invariants: dict[str, bool]
    selector_mutation_performed: bool
    repeatability_acceptance_checkpoint_endpoint: str
    repeatability_acceptance_operator_closeout_endpoint: str
    next_allowed_actions: list[str]


class Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatusResponse(Layer3BaseResponse):
    mode: str
    closeout_status_projection_state: str
    closeout_status_hash: str
    repeatability_acceptance_operator_closeout_receipt_available: bool
    repeatability_acceptance_operator_closeout_receipt_id: str
    repeatability_acceptance_operator_closeout_receipt_hash: str
    repeatability_acceptance_operator_closeout_hash: str
    repeatability_acceptance_operator_closeout_authority_hash: str
    repeatability_acceptance_operator_closeout_receipt_ref: str
    repeatability_acceptance_checkpoint_receipt_id: str
    repeatability_acceptance_checkpoint_receipt_hash: str
    repeatability_acceptance_checkpoint_authority_hash: str
    original_repeatability_checkpoint_receipt_id: str
    repeatability_rerun_trial_receipt_id: str
    original_operator_workflow_receipt_id: str
    rerun_operator_workflow_receipt_id: str
    baseline_run_id: str
    candidate_a_run_id: str
    original_candidate_b_run_id: str
    rerun_candidate_b_run_id: str
    compare_target_set_hash: str
    material_relative_name: str
    acceptance_disposition: str
    comparison_hash: str
    negative_invariants_hash: str
    rendered_acceptance_control_proof_state: str
    comparison_summary: dict[str, Any]
    negative_invariants: dict[str, bool]
    rendered_acceptance_control_proof: dict[str, Any]
    operator_projection: dict[str, Any]
    ownership_access_policy: dict[str, Any]
    source_closeout_endpoint: str
    repeatability_acceptance_operator_closeout_status_endpoint: str


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
    candidate_b_operator_status_evidence: dict[str, Any]
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


class Layer3CandidateBBroaderEligibleCorpusScopeReadinessAuditResponse(Layer3BaseResponse):
    mode: str
    audit_state: str
    audit_id: str
    audit_hash: str
    blocked_reasons: list[dict[str, Any]]
    current_default_scope: str
    selected_decision_scope: str
    exact_corpus_class_list: list[str]
    explicit_exclusion_list: list[str]
    proposed_default_scope_classes: list[str]
    scope_class_results: list[dict[str, Any]]
    required_scope_evidence: list[str]
    required_exclusions: list[str]
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_expansion_admitted: bool
    selector_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeRuntimeResponse(Layer3BaseResponse):
    mode: str
    runtime_state: str
    selection_receipt_id: str | None
    selection_receipt_hash: str | None
    selection_receipt_ref: str | None
    selection_receipt_status: str
    blocked_reasons: list[dict[str, Any]]
    readiness_audit_binding: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_source: str
    current_default_scope_preserved: str
    non_pdf_default_preserved: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_scope_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_expansion_enabled: bool
    selector_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseResponse(Layer3BaseResponse):
    mode: str
    selector_use_state: str
    selector_use_receipt_id: str | None
    selector_use_receipt_hash: str | None
    selector_use_receipt_ref: str | None
    selector_use_receipt_status: str
    blocked_reasons: list[dict[str, Any]]
    runtime_selection_receipt_binding: dict[str, Any]
    selector_authority: dict[str, Any]
    selected_scope_classes: list[str]
    current_default_scope_before_use: str
    default_scope_enabled_for_selected_classes: bool
    non_selected_class_default_preserved: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_selector_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_expansion_enabled: bool
    selector_use_authority_recorded: bool
    selector_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseStatusResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    selector_use_status_hash: str
    selector_use_receipt_id: str
    selector_use_receipt_hash: str
    selector_use_receipt_status: str
    selector_use_state: str
    runtime_selection_receipt_binding: dict[str, Any]
    selector_authority: dict[str, Any]
    operator_visible_selector_status: dict[str, Any]
    selected_scope_classes: list[str]
    current_default_scope_before_use: str
    default_scope_enabled_for_selected_classes: bool
    non_selected_class_default_preserved: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics_preserved: bool
    selector_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorActivationResponse(Layer3BaseResponse):
    mode: str
    selector_activation_state: str
    activation_receipt_id: str | None
    activation_receipt_hash: str | None
    activation_receipt_ref: str | None
    activation_receipt_status: str
    blocked_reasons: list[dict[str, Any]]
    activation_authority: dict[str, Any]
    selector_use_receipt_binding: dict[str, Any]
    runtime_selection_receipt_binding: dict[str, Any]
    readiness_audit_binding: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_source: str
    current_default_before_activation_runtime: str
    default_scope_activation_enabled: bool
    default_scope_expansion_enabled: bool
    non_selected_class_default: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_activation_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    selector_activation_authority_recorded: bool
    selector_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeActivationReceiptConsumptionResponse(Layer3BaseResponse):
    mode: str
    activation_receipt_consumption_state: str
    consumption_receipt_id: str | None
    consumption_receipt_hash: str | None
    consumption_receipt_ref: str | None
    consumption_receipt_status: str
    blocked_reasons: list[dict[str, Any]]
    consumption_authority: dict[str, Any]
    activation_receipt_binding: dict[str, Any]
    selector_use_status_binding: dict[str, Any]
    selector_use_receipt_binding: dict[str, Any]
    runtime_selection_receipt_binding: dict[str, Any]
    readiness_audit_binding: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_source: str
    current_default_before_consumption_runtime: str
    default_scope_consumption_enabled: bool
    default_scope_expansion_enabled: bool
    non_selected_class_default: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_consumption_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    activation_receipt_consumption_authority_recorded: bool
    selector_mutation_performed: bool
    default_scope_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseResponse(Layer3BaseResponse):
    mode: str
    consumption_receipt_use_state: str
    use_receipt_id: str | None
    use_receipt_hash: str | None
    use_receipt_ref: str | None
    use_receipt_status: str
    blocked_reasons: list[dict[str, Any]]
    use_authority: dict[str, Any]
    consumption_receipt_binding: dict[str, Any]
    activation_receipt_binding: dict[str, Any]
    selector_use_status_binding: dict[str, Any]
    selector_use_receipt_binding: dict[str, Any]
    runtime_selection_receipt_binding: dict[str, Any]
    readiness_audit_binding: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_source: str
    current_default_before_use_runtime: str
    default_scope_use_enabled: bool
    default_scope_expansion_enabled: bool
    default_scope_application_scope: str
    non_selected_class_default: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_use_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_use_authority_recorded: bool
    selector_mutation_performed: bool
    default_scope_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseStatusResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    use_receipt_status_hash: str | None
    use_receipt_id: str
    use_receipt_hash: str
    use_receipt_status: str
    consumption_receipt_use_state: str
    use_authority: dict[str, Any]
    consumption_receipt_binding: dict[str, Any]
    activation_receipt_binding: dict[str, Any]
    selector_use_status_binding: dict[str, Any]
    selector_use_receipt_binding: dict[str, Any]
    runtime_selection_receipt_binding: dict[str, Any]
    readiness_audit_binding: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_source: str
    current_default_before_use_runtime: str
    default_scope_use_enabled: bool
    default_scope_expansion_enabled: bool
    default_scope_application_scope: str
    non_selected_class_default: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    operator_visible_use_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_use_authority_recorded: bool
    selector_mutation_performed: bool
    default_scope_mutation_performed: bool
    use_receipt_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeOperatorRepeatabilityTrialResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    operator_repeatability_trial_state: str
    operator_repeatability_disposition: str
    trial_receipt_id: str
    trial_receipt_hash: str
    trial_receipt_ref: str
    trial_receipt_status: str
    trial_authority_hash: str
    authority_pair_hash: str
    idempotent_replay: bool
    append_only_repeatability_trial_receipt: bool
    exclusive_trial_per_original_repeat_authority_pair: bool
    original_use_status: dict[str, Any]
    repeat_use_status: dict[str, Any]
    readiness_audit_binding: dict[str, Any]
    runtime_selection_receipt_binding: dict[str, Any]
    selector_use_status_binding: dict[str, Any]
    selector_use_receipt_binding: dict[str, Any]
    activation_receipt_binding: dict[str, Any]
    consumption_receipt_binding: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_hash: str
    original_receipt_chain_hash: str
    repeat_receipt_chain_hash: str
    original_negative_invariants_hash: str
    repeat_negative_invariants_hash: str
    use_status_hash_comparison: str
    receipt_chain_hash_comparison: str
    selected_scope_classes_hash_comparison: str
    negative_invariants_hash_comparison: str
    trial_authority: dict[str, Any]
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_repeatability_trial_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_expansion_admitted: bool
    actual_corpus_processing_execution_admitted: bool
    actual_subprocess_spawn_admitted: bool
    process_control_admitted: bool
    selector_mutation_performed: bool
    default_scope_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopePromotionReadinessResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    promotion_readiness_state: str
    promotion_readiness_audit_id: str
    promotion_readiness_audit_hash: str
    blocked_reasons: list[dict[str, Any]]
    required_promotion_authority_chain: list[str]
    trial_receipt_binding: dict[str, Any]
    production_ownership_storage_policy: dict[str, Any]
    operator_visible_status_evidence: dict[str, Any]
    selected_scope_classes: list[str]
    current_default_scope_before_promotion_readiness_audit: str
    scope_class_policy: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    default_scope_promotion_ready_for_separate_selection: bool
    selector_mutation_admitted_now: bool
    selector_mutation_performed: bool
    default_scope_expansion_admitted: bool
    default_scope_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3CandidateBBroaderEligibleCorpusDefaultScopeDefaultPromotionResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    default_promotion_state: str
    default_promotion_receipt_id: str | None
    default_promotion_receipt_hash: str | None
    default_promotion_receipt_ref: str | None
    default_promotion_receipt_status: str
    idempotent_replay: bool
    blocked_reasons: list[dict[str, Any]]
    required_promotion_authority_chain: list[str]
    promotion_readiness_audit_binding: dict[str, Any]
    trial_receipt_binding: dict[str, Any]
    production_ownership_storage_policy: dict[str, Any]
    selected_scope_classes: list[str]
    selected_scope_classes_hash: str
    scope_class_policy: str
    default_scope_promotion_enabled_for_selected_classes: bool
    default_scope_policy_mutation_performed: bool
    default_scope_expansion_mutation_performed: bool
    current_default_scope_before_promotion: str
    non_selected_class_default: str
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_scope_authority: dict[str, Any]
    operator_visible_status_evidence: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    selector_mutation_performed: bool
    source_expansion_admitted: bool
    runtime_db_or_storage_expansion_admitted: bool
    pdf_or_image_text_material_ingestion_admitted: bool
    provider_object_write_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    auth_security_expansion_enabled: bool
    full_mockup_activation_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
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
    candidate_b_operator_status_evidence: dict[str, Any]
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
    operator_status_hash: str
    candidate_b_operator_status_evidence: dict[str, Any]
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
    mixed_source_package_semantics: dict[str, Any]
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


class Layer3SecEdgarTextTableAuthorityEnvelopeResponse(Layer3BaseResponse):
    authority_envelope_mode: str
    authority_envelope_state: str
    dataset_version_id: str
    dataset_version_hash: str | None
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    authority_envelope_id: str | None
    authority_envelope_hash: str | None
    authority_envelope_ref: str | None
    materialization_receipt_model: str
    materialization_receipt_id: str | None
    materialization_receipt_hash: str | None
    material_analysis_payload: dict[str, Any]
    provenance_summary: dict[str, Any]
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]


class Layer3SecEdgarTextTableMaterialAuthorityBridgeResponse(Layer3BaseResponse):
    mode: str
    bridge_state: str
    dataset_version_id: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    authority_envelope_hash: str
    material_preview_request_basis: dict[str, Any] | None = None
    material_preview_hash: str | None = None
    gate_b_decision_manifest_id: str | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]


class Layer3SecEdgarTextTableSourceAcquisitionAuthorityResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    source_acquisition_authority_state: str
    source_acquisition_receipt_id: str
    source_acquisition_receipt_hash: str
    source_acquisition_receipt_ref: str
    source_acquisition_receipt_status: str
    idempotent_replay: bool
    append_only_source_acquisition_authority_receipt: bool
    exclusive_receipt_per_source_artifact_authority: bool
    dataset_version_id: str
    source_family: str
    parser_family: str
    parser_contract_id: str
    typed_content_contract_id: str
    source_mode: str
    dataset_version_hash: str
    materialization_receipt_hash: str
    authority_envelope_hash: str
    source_artifact_authority: dict[str, Any]
    authority_bindings: dict[str, Any]
    compatibility: dict[str, Any]
    operator_visible_source_acquisition_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_default_scope: dict[str, Any]
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableLiveSourceArtifactResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    source_family: str
    parser_family: str
    parser_contract_id: str
    typed_content_contract_id: str
    source_artifact_family: str
    live_source_artifact_receipt_id: str
    live_source_artifact_receipt_hash: str
    live_source_artifact_receipt_status: str
    source_artifact_receipt: dict[str, Any]
    retained_source_artifact_manifest: dict[str, Any]
    source_identity: dict[str, Any]
    sec_request_policy: dict[str, Any]
    cache: dict[str, Any]
    idempotency: dict[str, Any]
    compatibility: dict[str, Any]
    operator_visible_live_source_artifact_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    baseline_rollback: dict[str, Any]
    candidate_a_semantics: dict[str, Any]
    candidate_b_default_scope: dict[str, Any]
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarRealFilingAcquisitionConnectorResponse(Layer3BaseResponse):
    connector_mode: str
    operator_decision: str
    connector_state: str
    connector_receipt_id: str
    connector_receipt_hash: str
    example_set: dict[str, Any]
    corpus_manifest: dict[str, Any]
    acquisition_receipts: list[dict[str, Any]]
    diagnostics: dict[str, Any]
    sec_request_policy: dict[str, Any]
    cache: dict[str, Any]
    idempotency: dict[str, Any]
    downstream_validation: dict[str, Any]
    operator_visible_status: dict[str, Any]
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarRealFilingDownstreamValidationResponse(Layer3BaseResponse):
    validation_mode: str
    operator_decision: str
    validation_state: str
    validation_receipt_id: str
    validation_receipt_hash: str
    validation_receipt_ref: str
    idempotent_replay: bool
    connector_receipt_id: str
    connector_receipt_hash: str
    connector_example_id: str
    authority_bindings: dict[str, Any]
    identity_binding: dict[str, Any]
    identity_binding_hash: str
    diagnostics: dict[str, Any]
    diagnostics_hash: str
    operator_status_summary: dict[str, Any]
    status_projection: dict[str, Any]
    cache: dict[str, Any]
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarRealCompanyCorpusValidationResponse(Layer3BaseResponse):
    validation_mode: str
    operator_decision: str
    validation_state: str
    validation_receipt_id: str | None = None
    validation_receipt_hash: str | None = None
    validation_receipt_ref: str | None = None
    connector_receipt_id: str | None = None
    connector_receipt_hash: str | None = None
    company_matrix: list[str] | None = None
    filing_selection_policy: str | None = None
    filing_validation_records: list[dict[str, Any]] | None = None
    product_utility_matrix: list[dict[str, Any]] | None = None
    diagnostics: dict[str, Any] | None = None
    cache: dict[str, Any] | None = None
    blocked_reasons: list[dict[str, Any]] | None = None
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str] | None = None


class Layer3SecEdgarDeliveryStatusProvenanceResponse(Layer3BaseResponse):
    status_mode: str
    operator_decision: str
    delivery_status_provenance_state: str
    delivery_status_provenance_receipt_id: str | None = None
    delivery_status_provenance_receipt_hash: str | None = None
    delivery_status_provenance_receipt_ref: str | None = None
    validation_receipt_id: str | None = None
    validation_receipt_hash: str | None = None
    connector_receipt_hash: str | None = None
    company_matrix: list[str] | None = None
    filing_count: int | None = None
    validation_receipt_status: str | None = None
    handoff_export_prepare_status: str | None = None
    delivery_readiness_status: str | None = None
    delivery_status_records: list[dict[str, Any]] | None = None
    provenance_hash_matrix: list[dict[str, Any]] | None = None
    blocked_or_degraded_delivery_gaps: list[dict[str, Any]] | None = None
    diagnostics: dict[str, Any] | None = None
    cache: dict[str, Any] | None = None
    blocked_reasons: list[dict[str, Any]] | None = None
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str] | None = None


class Layer3SecEdgarOperatorInspectionResponse(Layer3BaseResponse):
    inspection_mode: str
    operator_decision: str
    operator_inspection_state: str
    operator_inspection_receipt_id: str | None = None
    operator_inspection_receipt_hash: str | None = None
    operator_inspection_receipt_ref: str | None = None
    delivery_status_provenance_receipt_id: str | None = None
    delivery_status_provenance_receipt_hash: str | None = None
    validation_receipt_hash: str | None = None
    connector_receipt_hash: str | None = None
    filing_count: int | None = None
    inspection_status: str | None = None
    company_filing_inspection_matrix: list[dict[str, Any]] | None = None
    readiness_rollup: dict[str, Any] | None = None
    provenance_status: dict[str, Any] | None = None
    blocked_or_degraded_delivery_gaps: list[dict[str, Any]] | None = None
    operator_inspection_summary: dict[str, Any] | None = None
    cache: dict[str, Any] | None = None
    blocked_reasons: list[dict[str, Any]] | None = None
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str] | None = None


class Layer3SecEdgarOperatorProductSurfaceResponse(Layer3BaseResponse):
    surface_mode: str
    rendered_mode: str
    operator_decision: str
    operator_product_surface_state: str
    operator_product_surface_receipt_id: str | None = None
    operator_product_surface_receipt_hash: str | None = None
    operator_product_surface_receipt_ref: str | None = None
    operator_inspection_receipt_id: str | None = None
    operator_inspection_receipt_hash: str | None = None
    delivery_status_provenance_receipt_id: str | None = None
    delivery_status_provenance_receipt_hash: str | None = None
    validation_receipt_hash: str | None = None
    connector_receipt_hash: str | None = None
    product_views: dict[str, Any] | None = None
    value_reveal: dict[str, Any] | None = None
    surface_rollup: dict[str, Any] | None = None
    authority_chain: dict[str, Any] | None = None
    cache: dict[str, Any] | None = None
    blocked_reasons: list[dict[str, Any]] | None = None
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str] | None = None


class Layer3SecEdgarArelleValueRevealResponse(Layer3BaseResponse):
    reveal_mode: str
    reveal_state: str
    reveal_receipt_id: str | None = None
    reveal_receipt_hash: str | None = None
    reveal_receipt_ref: str | None = None
    actor_hash: str | None = None
    audit_server_time: str | None = None
    sidecar_receipt_id: str | None = None
    sidecar_receipt_hash: str | None = None
    dataset_version_id: str | None = None
    dataset_version_hash: str | None = None
    lineage_hashes: dict[str, Any] | None = None
    fact_count: int | None = None
    fact_inventory_hash: str | None = None
    value_inventory_hash: str | None = None
    value_semantics: str | None = None
    audit_receipt: dict[str, Any] | None = None
    idempotent_replay: bool | None = None
    revealed_fact_count: int
    revealed_facts: list[dict[str, Any]]
    status_projection: dict[str, Any] | None = None
    blocked_reasons: list[dict[str, Any]] | None = None
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str] | None = None


class Layer3SecEdgarDurableDeliveryArchiveResponse(Layer3BaseResponse):
    archive_mode: str
    runtime_version: str
    operator_decision: str
    durable_delivery_archive_state: str
    sec_edgar_durable_delivery_archive_receipt_id: str | None = None
    sec_edgar_durable_delivery_archive_receipt_hash: str | None = None
    sec_edgar_durable_delivery_archive_receipt_ref: str | None = None
    archive_manifest_hash: str | None = None
    archive_order_hash: str | None = None
    source_authority_chain_hash: str | None = None
    redaction_manifest_hash: str | None = None
    archive_manifest: dict[str, Any] | None = None
    operator_product_surface_receipt_id: str | None = None
    operator_product_surface_receipt_hash: str | None = None
    delivery_status_provenance_receipt_hash: str | None = None
    operator_inspection_receipt_hash: str | None = None
    validation_receipt_hash: str | None = None
    connector_receipt_hash: str | None = None
    cache: dict[str, Any] | None = None
    blocked_reasons: list[dict[str, Any]] | None = None
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    status_surface_mode: str | None = None
    response_authority: str | None = None
    read_only_status_surface: bool | None = None
    archive_status_surface_hash: str | None = None
    archive_status_surface: dict[str, Any] | None = None
    downstream_unavailable: list[str] | None = None
    next_allowed_actions: list[str] | None = None


class Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserResponse(Layer3BaseResponse):
    parser_mode: str
    operator_decision: str
    parser_state: str
    parser_receipt_id: str
    parser_receipt_hash: str
    parser_receipt_ref: str
    idempotent_replay: bool
    connector_receipt_id: str
    connector_receipt_hash: str
    connector_example_id: str
    live_source_artifact_receipt_id: str
    live_source_artifact_receipt_hash: str
    source_artifact_receipt_hash: str
    identity_binding: dict[str, Any]
    document_inventory: list[dict[str, Any]]
    document_inventory_hash: str
    content_order: list[dict[str, Any]]
    content_order_hash: str
    table_candidate_inventory: list[dict[str, Any]]
    table_candidate_inventory_hash: str
    inline_xbrl_marker_inventory: list[dict[str, Any]]
    inline_xbrl_marker_inventory_hash: str
    diagnostics: dict[str, Any]
    diagnostics_hash: str
    status_projection: dict[str, Any]
    cache: dict[str, Any]
    negative_invariants: dict[str, bool]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlMaterialBridgeResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    bridge_state: str
    parser_receipt_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    material_preview_request_basis: dict[str, Any] | None = None
    material_preview_hash: str | None = None
    gate_b_decision_manifest_id: str | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]


class Layer3SecEdgarHtmlInlineXbrlFactAuthorityResponse(Layer3BaseResponse):
    mode: str
    fact_authority_mode: str
    operator_decision: str
    fact_authority_state: str
    fact_authority_receipt_id: str | None = None
    fact_authority_receipt_ref: str | None = None
    fact_authority_receipt_hash: str | None = None
    idempotent_replay: bool
    source_family: str
    parser_family: str
    parser_receipt_hash: str
    fact_count: int
    fact_inventory_hash: str | None = None
    diagnostics_hash: str | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]


class Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    bridge_state: str
    fact_material_bridge_receipt_id: str | None = None
    fact_material_bridge_receipt_hash: str | None = None
    bridge_receipt_id: str | None = None
    bridge_receipt_hash: str | None = None
    fact_authority_receipt_hash: str
    parser_receipt_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    material_preview_request_basis: dict[str, Any] | None = None
    material_preview_hash: str | None = None
    gate_b_decision_manifest_id: str | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationResponse(Layer3BaseResponse):
    mode: str
    classification_mode: str
    operator_decision: str
    classification_state: str
    statement_classification_receipt_id: str | None = None
    statement_classification_receipt_ref: str | None = None
    statement_classification_receipt_hash: str | None = None
    fact_authority_receipt_hash: str
    fact_material_bridge_receipt_hash: str
    parser_receipt_hash: str | None = None
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    classification_inventory: list[dict[str, Any]] = Field(default_factory=list)
    classification_inventory_hash: str | None = None
    classification_order_hash: str | None = None
    statement_group_inventory: list[dict[str, Any]] = Field(default_factory=list)
    statement_group_inventory_hash: str | None = None
    unclassified_fact_inventory_hash: str | None = None
    classification_diagnostics: dict[str, Any] | None = None
    classification_diagnostics_hash: str | None = None
    authority_hashes: dict[str, Any] | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductResponse(Layer3BaseResponse):
    mode: str
    product_mode: str
    classification_mode: str
    operator_decision: str
    product_state: str
    downstream_product_receipt_id: str | None = None
    downstream_product_receipt_ref: str | None = None
    downstream_product_receipt_hash: str | None = None
    statement_classification_receipt_id: str | None = None
    statement_classification_receipt_hash: str | None = None
    fact_authority_receipt_hash: str | None = None
    fact_material_bridge_receipt_hash: str | None = None
    parser_receipt_hash: str | None = None
    source_family: str | None = None
    parser_family: str | None = None
    typed_content_contract_id: str | None = None
    product_manifest: dict[str, Any] | None = None
    product_manifest_hash: str | None = None
    statement_candidate_product_hash: str | None = None
    product_order_hash: str | None = None
    inspection_summary_hash: str | None = None
    redaction_manifest_hash: str | None = None
    downstream_readiness_hash: str | None = None
    authority_hashes: dict[str, Any] | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewResponse(
    Layer3BaseResponse
):
    mode: str
    package_review_mode: str
    product_mode: str
    classification_mode: str
    operator_decision: str
    package_review_preview_state: str
    package_review_preview_receipt_id: str | None = None
    package_review_preview_receipt_ref: str | None = None
    package_review_preview_receipt_hash: str | None = None
    downstream_product_receipt_id: str | None = None
    downstream_product_receipt_hash: str | None = None
    statement_classification_receipt_id: str | None = None
    statement_classification_receipt_hash: str | None = None
    fact_authority_receipt_hash: str | None = None
    fact_material_bridge_receipt_hash: str | None = None
    parser_receipt_hash: str | None = None
    source_family: str | None = None
    typed_content_contract_id: str | None = None
    candidate_package_manifest: dict[str, Any] | None = None
    candidate_package_manifest_hash: str | None = None
    review_readiness_manifest: dict[str, Any] | None = None
    review_readiness_hash: str | None = None
    package_order_hash: str | None = None
    redaction_manifest_hash: str | None = None
    product_manifest_hash: str | None = None
    statement_candidate_product_hash: str | None = None
    product_order_hash: str | None = None
    inspection_summary_hash: str | None = None
    downstream_readiness_hash: str | None = None
    authority_hashes: dict[str, Any] | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitResponse(
    Layer3BaseResponse
):
    mode: str
    package_construction_mode: str
    package_review_mode: str
    product_mode: str
    classification_mode: str
    operator_decision: str
    package_construction_state: str
    package_construction_receipt_id: str | None = None
    package_construction_receipt_ref: str | None = None
    package_construction_receipt_hash: str | None = None
    package_review_preview_receipt_id: str | None = None
    package_review_preview_receipt_hash: str | None = None
    downstream_product_receipt_hash: str | None = None
    statement_classification_receipt_hash: str | None = None
    fact_authority_receipt_hash: str | None = None
    fact_material_bridge_receipt_hash: str | None = None
    parser_receipt_hash: str | None = None
    source_family: str | None = None
    typed_content_contract_id: str | None = None
    candidate_package_manifest_hash: str | None = None
    review_readiness_hash: str | None = None
    package_order_hash: str | None = None
    redaction_manifest_hash: str | None = None
    product_manifest_hash: str | None = None
    statement_candidate_product_hash: str | None = None
    product_order_hash: str | None = None
    inspection_summary_hash: str | None = None
    downstream_readiness_hash: str | None = None
    package_payload_manifest: dict[str, Any] | None = None
    package_payload_manifest_hash: str | None = None
    package_payload_order_hash: str | None = None
    package_kinds: list[str] | None = None
    payload_refs: list[str] | None = None
    payload_hashes: list[str] | None = None
    authority_hashes: dict[str, Any] | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitResponse(
    Layer3BaseResponse
):
    mode: str
    package_review_submit_mode: str
    package_construction_mode: str
    package_review_mode: str
    product_mode: str
    classification_mode: str
    operator_decision: str
    review_decision: str | None = None
    decision_notes_present: bool
    decision_notes_hash: str | None = None
    package_review_state: str
    package_review_submit_receipt_id: str | None = None
    package_review_submit_receipt_ref: str | None = None
    package_review_submit_record_ref: str | None = None
    package_review_submit_receipt_hash: str | None = None
    package_construction_receipt_id: str | None = None
    package_construction_receipt_hash: str | None = None
    package_review_preview_receipt_id: str | None = None
    package_review_preview_receipt_hash: str | None = None
    downstream_product_receipt_hash: str | None = None
    statement_classification_receipt_hash: str | None = None
    fact_authority_receipt_hash: str | None = None
    fact_material_bridge_receipt_hash: str | None = None
    parser_receipt_hash: str | None = None
    source_family: str | None = None
    typed_content_contract_id: str | None = None
    candidate_package_manifest_hash: str | None = None
    review_readiness_hash: str | None = None
    package_order_hash: str | None = None
    redaction_manifest_hash: str | None = None
    product_manifest_hash: str | None = None
    statement_candidate_product_hash: str | None = None
    product_order_hash: str | None = None
    inspection_summary_hash: str | None = None
    downstream_readiness_hash: str | None = None
    package_payload_manifest: dict[str, Any] | None = None
    package_payload_manifest_hash: str | None = None
    package_payload_order_hash: str | None = None
    package_kinds: list[str] | None = None
    payload_refs: list[str] | None = None
    payload_hashes: list[str] | None = None
    authority_hashes: dict[str, Any] | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareResponse(
    Layer3BaseResponse
):
    mode: str
    handoff_export_prepare_mode: str
    package_review_submit_mode: str | None = None
    package_construction_mode: str | None = None
    package_review_mode: str | None = None
    product_mode: str | None = None
    classification_mode: str | None = None
    operator_decision: str
    handoff_export_state: str
    handoff_export_prepare_receipt_id: str | None = None
    handoff_export_prepare_receipt_ref: str | None = None
    handoff_export_prepare_record_ref: str | None = None
    handoff_export_prepare_receipt_hash: str | None = None
    handoff_export_manifest: dict[str, Any] | None = None
    handoff_export_manifest_hash: str | None = None
    handoff_export_order_hash: str | None = None
    package_review_submit_receipt_id: str | None = None
    package_review_submit_receipt_hash: str | None = None
    package_review_submit_record_ref: str | None = None
    review_decision: str | None = None
    package_review_state: str | None = None
    decision_notes_present: bool | None = None
    decision_notes_hash: str | None = None
    package_construction_receipt_id: str | None = None
    package_construction_receipt_hash: str | None = None
    package_review_preview_receipt_id: str | None = None
    package_review_preview_receipt_hash: str | None = None
    downstream_product_receipt_hash: str | None = None
    statement_classification_receipt_hash: str | None = None
    fact_authority_receipt_hash: str | None = None
    fact_material_bridge_receipt_hash: str | None = None
    parser_receipt_hash: str | None = None
    source_family: str | None = None
    typed_content_contract_id: str | None = None
    candidate_package_manifest_hash: str | None = None
    review_readiness_hash: str | None = None
    package_order_hash: str | None = None
    redaction_manifest_hash: str | None = None
    product_manifest_hash: str | None = None
    statement_candidate_product_hash: str | None = None
    product_order_hash: str | None = None
    inspection_summary_hash: str | None = None
    downstream_readiness_hash: str | None = None
    package_payload_manifest_hash: str | None = None
    package_payload_order_hash: str | None = None
    package_kinds: list[str] | None = None
    payload_refs: list[str] | None = None
    payload_hashes: list[str] | None = None
    authority_hashes: dict[str, Any] | None = None
    status_projection: dict[str, Any]
    negative_invariants: dict[str, Any]
    redaction_policy_id: str
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    proof_state: str
    dataset_version_id: str
    dataset_version_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    parser_receipt_id: str
    parser_receipt_hash: str
    material_bridge_receipt_id: str
    material_bridge_receipt_hash: str
    bridge_receipt_hash: str
    materialization_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    material_snapshot_payload_hash: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    coverage: list[str]
    coverage_evidence: dict[str, Any]
    coverage_evidence_hash: str
    negative_invariants_hash: str
    status_projection: dict[str, Any]
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    provider_private_token_exposed: bool
    provider_public_url_enabled: bool
    provider_object_writes_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    proof_state: str
    dataset_version_id: str
    dataset_version_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    parser_receipt_id: str
    parser_receipt_hash: str
    fact_authority_receipt_id: str
    fact_authority_receipt_hash: str
    fact_inventory_hash: str
    diagnostics_hash: str
    fact_material_bridge_receipt_id: str
    fact_material_bridge_receipt_hash: str
    bridge_receipt_hash: str
    materialization_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    material_snapshot_payload_hash: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    coverage: list[str]
    coverage_evidence: dict[str, Any]
    coverage_evidence_hash: str
    negative_invariants_hash: str
    status_projection: dict[str, Any]
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    provider_private_token_exposed: bool
    provider_public_url_enabled: bool
    provider_object_writes_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusResponse(Layer3BaseResponse):
    mode: str
    operator_status_state: str
    expected_proof_hash: str
    proof_hash: str
    proof_state: str
    dataset_version_id: str
    dataset_version_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    parser_receipt_hash: str
    connector_receipt_hash: str
    live_source_artifact_receipt_hash: str
    source_artifact_receipt_hash: str
    content_sha256: str
    primary_document_hash: str
    content_order_hash: str
    inline_xbrl_marker_inventory_hash: str
    fact_authority_receipt_hash: str
    fact_inventory_hash: str
    diagnostics_hash: str
    materialization_receipt_hash: str
    fact_material_bridge_receipt_hash: str
    material_bridge_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_payload_hash: str
    coverage_evidence_hash: str
    negative_invariants_hash: str
    blocked_reason_codes: list[str]
    operator_status_hash: str
    operator_status_projection_ref: str
    selected_status_states: list[str]
    proof_available: bool
    proof_summary: dict[str, Any]
    status_projection: dict[str, Any]
    blocked_reasons: list[dict[str, Any]]
    raw_proof_request_rendered: bool
    raw_proof_receipt_path_rendered: bool
    raw_local_path_rendered: bool
    raw_url_rendered: bool
    artifact_bytes_rendered: bool
    raw_fact_values_rendered: bool
    fact_value_reconstruction_enabled: bool
    provider_private_token_rendered: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    operator_repeatability_trial_state: str
    operator_repeatability_disposition: str
    trial_receipt_id: str
    trial_receipt_hash: str
    trial_receipt_ref: str
    trial_receipt_status: str
    trial_authority_hash: str
    authority_pair_hash: str
    idempotent_replay: bool
    append_only_repeatability_trial_receipt: bool
    exclusive_trial_per_original_repeat_authority_pair: bool
    original_operator_status: dict[str, Any]
    repeat_operator_status: dict[str, Any]
    authority_bindings: dict[str, Any]
    operator_status_hash_comparison: str
    proof_hash_comparison: str
    coverage_step_set_comparison: str
    fact_inventory_hash_comparison: str
    fact_material_authority_hash_comparison: str
    trial_authority: dict[str, Any]
    operator_visible_repeatability_trial_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarHtmlInlineXbrlDownstreamOperatorStatusResponse(Layer3BaseResponse):
    mode: str
    operator_status_state: str
    expected_proof_hash: str
    proof_hash: str
    proof_state: str
    dataset_version_id: str
    dataset_version_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    parser_receipt_hash: str
    connector_receipt_hash: str
    live_source_artifact_receipt_hash: str
    source_artifact_receipt_hash: str
    content_sha256: str
    primary_document_hash: str
    content_order_hash: str
    materialization_receipt_hash: str
    material_bridge_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_payload_hash: str
    coverage_evidence_hash: str
    negative_invariants_hash: str
    blocked_reason_codes: list[str]
    operator_status_hash: str
    operator_status_projection_ref: str
    selected_status_states: list[str]
    proof_available: bool
    proof_summary: dict[str, Any]
    status_projection: dict[str, Any]
    blocked_reasons: list[dict[str, Any]]
    raw_proof_request_rendered: bool
    raw_proof_receipt_path_rendered: bool
    raw_local_path_rendered: bool
    raw_url_rendered: bool
    artifact_bytes_rendered: bool
    provider_private_token_rendered: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableLiveSourceArtifactMaterialAuthorityBridgeResponse(Layer3BaseResponse):
    mode: str
    bridge_state: str
    dataset_version_id: str
    source_family: str
    parser_family: str
    parser_contract_id: str
    typed_content_contract_id: str
    live_source_artifact_receipt_hash: str | None = None
    source_acquisition_receipt_hash: str | None = None
    material_preview_request_basis: dict[str, Any] | None = None
    material_preview_hash: str | None = None
    gate_b_decision_manifest_id: str | None = None
    status_projection: dict[str, Any] | None = None
    negative_invariants: dict[str, Any]


class Layer3SecEdgarTextTableDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    proof_state: str
    dataset_version_id: str
    dataset_version_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    authority_envelope_hash: str
    materialization_receipt_hash: str
    bridge_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_id: str
    material_snapshot_payload_hash: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    coverage: list[str]
    coverage_evidence: dict[str, Any]
    coverage_evidence_hash: str
    negative_invariants_hash: str
    status_projection: dict[str, Any]
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    provider_private_token_exposed: bool
    provider_public_url_enabled: bool
    provider_object_writes_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableLiveSourceArtifactDownstreamProofResponse(Layer3BaseResponse):
    mode: str
    proof_state: str
    dataset_version_id: str
    authority_envelope_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    live_source_artifact_receipt_id: str
    live_source_artifact_receipt_hash: str
    source_acquisition_receipt_id: str
    source_acquisition_receipt_hash: str
    live_source_artifact_material_bridge_receipt_id: str
    live_source_artifact_material_bridge_receipt_hash: str
    material_bridge_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_payload_hash: str
    downstream_proof_hash: str
    proof_hash: str
    proof_receipt_id: str
    proof_receipt_ref: str
    coverage: list[str]
    coverage_evidence_hash: str
    negative_invariants_hash: str
    status_projection: dict[str, Any]
    raw_local_path_exposed: bool
    raw_url_exposed: bool
    artifact_bytes_exposed: bool
    provider_object_writes_enabled: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorStatusResponse(Layer3BaseResponse):
    mode: str
    operator_status_state: str
    expected_proof_hash: str
    proof_hash: str
    proof_state: str
    dataset_version_id: str
    authority_envelope_hash: str
    source_family: str
    parser_family: str
    typed_content_contract_id: str
    live_source_artifact_receipt_hash: str
    source_acquisition_receipt_hash: str
    live_source_artifact_material_bridge_receipt_hash: str
    material_bridge_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_payload_hash: str
    downstream_proof_hash: str
    coverage_evidence_hash: str
    negative_invariants_hash: str
    operator_status_hash: str
    operator_status_projection_ref: str
    selected_status_states: list[str]
    proof_available: bool
    proof_summary: dict[str, Any]
    status_projection: dict[str, Any]
    blocked_reasons: list[dict[str, Any]]
    raw_proof_receipt_path_rendered: bool
    raw_local_path_rendered: bool
    raw_url_rendered: bool
    artifact_bytes_rendered: bool
    provider_private_token_rendered: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorRepeatabilityTrialResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    operator_repeatability_trial_state: str
    operator_repeatability_disposition: str
    trial_receipt_id: str
    trial_receipt_hash: str
    trial_receipt_ref: str
    trial_receipt_status: str
    trial_authority_hash: str
    authority_pair_hash: str
    idempotent_replay: bool
    append_only_repeatability_trial_receipt: bool
    exclusive_trial_per_original_repeat_authority_pair: bool
    original_operator_status: dict[str, Any]
    repeat_operator_status: dict[str, Any]
    authority_bindings: dict[str, Any]
    operator_status_hash_comparison: str
    proof_hash_comparison: str
    coverage_step_set_comparison: str
    trial_authority: dict[str, Any]
    operator_visible_repeatability_trial_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableDownstreamOperatorStatusResponse(Layer3BaseResponse):
    mode: str
    operator_status_state: str
    expected_proof_hash: str
    proof_hash: str
    proof_state: str
    dataset_version_id: str
    dataset_version_hash: str
    materialization_receipt_hash: str
    authority_envelope_hash: str
    bridge_receipt_hash: str
    material_preview_hash: str
    gate_b_decision_manifest_id: str
    session_id: str
    selection_manifest_id: str
    material_snapshot_payload_hash: str
    coverage_evidence_hash: str
    negative_invariants_hash: str
    blocked_reason_codes: list[str]
    operator_status_hash: str
    operator_status_projection_ref: str
    selected_status_states: list[str]
    proof_available: bool
    proof_summary: dict[str, Any]
    status_projection: dict[str, Any]
    blocked_reasons: list[dict[str, Any]]
    raw_proof_receipt_path_rendered: bool
    raw_local_path_rendered: bool
    raw_url_rendered: bool
    artifact_bytes_rendered: bool
    provider_private_token_rendered: bool
    connector_dispatch_enabled: bool
    rag_vector_model_runtime_enabled: bool
    runtime_db_or_storage_expansion_admitted: bool
    frontend_durable_authority_enabled: bool
    browser_storage_authority_enabled: bool
    full_mockup_activation_enabled: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecEdgarTextTableDownstreamOperatorRepeatabilityTrialResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    operator_repeatability_trial_state: str
    operator_repeatability_disposition: str
    trial_receipt_id: str
    trial_receipt_hash: str
    trial_receipt_ref: str
    trial_receipt_status: str
    trial_authority_hash: str
    authority_pair_hash: str
    idempotent_replay: bool
    append_only_repeatability_trial_receipt: bool
    exclusive_trial_per_original_repeat_authority_pair: bool
    original_operator_status: dict[str, Any]
    repeat_operator_status: dict[str, Any]
    authority_bindings: dict[str, Any]
    operator_status_hash_comparison: str
    proof_hash_comparison: str
    coverage_step_set_comparison: str
    trial_authority: dict[str, Any]
    operator_visible_repeatability_trial_status: dict[str, Any]
    fail_closed_behavior: dict[str, bool]
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecXbrlOperatorReviewWorkflowOpenResponse(Layer3BaseResponse):
    sec_xbrl_operator_review_workflow_id: str
    sec_xbrl_statement_packet_set_id: str
    client_request_id: str
    workflow_basis_hash: str
    statement_packet_basis_hash: str
    source_projection_basis_hash: str
    control_mode: str
    redaction_policy: str
    statement_count: int
    row_count: int
    review_exception_count: int
    review_ready: bool
    permitted_controls: list[str]
    blocked_controls: list[dict[str, Any]]
    authority_refs: dict[str, Any]
    review_summary: dict[str, Any]
    idempotent_replay: bool
    auth_binding_ref: str
    auth_binding_basis_hash: str
    auth_binding_route_family: str
    auth_binding_policy_hash: str
    auth_binding_role: str
    auth_binding_required: bool
    workflow_open_api_route_enabled: bool
    status_api_route_enabled: bool
    decision_submit_api_route_enabled: bool
    runtime_default_enabled: bool
    value_reveal_performed: bool
    source_acquisition_performed: bool
    arelle_invoked: bool
    delivery_export_enabled: bool
    rendered_ui_enabled: bool
    production_readiness_claimed: bool


class Layer3SecXbrlOperatorReviewWorkflowOpenFromStagedEvidenceResponse(Layer3BaseResponse):
    client_request_id: str
    sec_xbrl_projection_set_id: str
    sec_xbrl_statement_packet_set_id: str
    sec_xbrl_operator_review_workflow_id: str
    workflow_basis_hash: str | None
    statement_packet_basis_hash: str | None
    source_projection_basis_hash: str | None
    source_report_schema_id: str
    source_report_hash: str | None
    authority_refs: dict[str, Any]
    summary: dict[str, Any]
    containment: dict[str, Any]
    controls: dict[str, Any]
    evidence_bundle_status: str
    auth_binding_ref: str
    auth_binding_basis_hash: str
    auth_binding_route_family: str
    auth_binding_policy_hash: str
    auth_binding_role: str
    auth_binding_required: bool
    workflow_open_api_route_enabled: bool
    status_api_route_enabled: bool
    decision_submit_api_route_enabled: bool
    production_readiness_claimed: bool


class Layer3SecXbrlOperatorReviewWorkflowStatusResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    workflow_schema_id: str
    sec_xbrl_operator_review_workflow_id: str
    sec_xbrl_statement_packet_set_id: str
    workflow_basis_hash: str
    statement_packet_basis_hash: str
    source_projection_basis_hash: str
    control_mode: str
    workflow_status: str
    redaction_policy: str
    statement_count: int
    row_count: int
    review_exception_count: int
    review_ready: bool
    permitted_controls: list[str]
    blocked_controls: list[dict[str, Any]]
    authority_refs: dict[str, Any]
    review_summary: dict[str, Any]
    status_surface_mode: str
    read_only_status_surface: bool
    durable_workflow_authority_used: bool
    status_api_route_enabled: bool
    open_workflow_api_route_enabled: bool
    runtime_default_enabled: bool
    value_reveal_performed: bool
    source_acquisition_performed: bool
    arelle_invoked: bool
    delivery_export_enabled: bool
    rendered_ui_enabled: bool
    operator_review_decision_recorded: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecXbrlOperatorReviewDecisionSubmitResponse(Layer3BaseResponse):
    sec_xbrl_operator_review_decision_id: str
    sec_xbrl_operator_review_workflow_id: str
    client_request_id: str
    decision_basis_hash: str
    workflow_basis_hash: str
    statement_packet_basis_hash: str
    source_projection_basis_hash: str
    decision_mode: str
    review_decision: str
    decision_status: str
    redaction_policy: str
    decision_reason_code: str
    decision_notes_present: bool
    decision_notes_hash: str | None
    decision_summary: dict[str, Any]
    authority_refs: dict[str, Any]
    permitted_controls_after_decision: list[str]
    blocked_controls_after_decision: list[dict[str, Any]]
    idempotent_replay: bool
    operator_review_decision_recorded: bool
    runtime_default_enabled: bool
    value_reveal_performed: bool
    source_acquisition_performed: bool
    arelle_invoked: bool
    delivery_export_enabled: bool
    api_route_enabled: bool
    decision_submit_api_route_enabled: bool
    workflow_open_api_route_enabled: bool
    rendered_ui_enabled: bool
    production_readiness_claimed: bool
    workflow_mutated: bool
    statement_packet_mutated: bool
    projection_mutated: bool


class Layer3SecXbrlOperatorReviewDecisionStatusResponse(Layer3BaseResponse):
    mode: str
    operator_decision: str
    decision_schema_id: str
    sec_xbrl_operator_review_decision_id: str
    sec_xbrl_operator_review_workflow_id: str
    decision_basis_hash: str
    workflow_basis_hash: str
    statement_packet_basis_hash: str
    source_projection_basis_hash: str
    decision_mode: str
    review_decision: str
    decision_status: str
    redaction_policy: str
    decision_reason_code: str
    decision_notes_present: bool
    decision_notes_hash: str | None
    decision_summary: dict[str, Any]
    authority_refs: dict[str, Any]
    permitted_controls_after_decision: list[str]
    blocked_controls_after_decision: list[dict[str, Any]]
    status_surface_mode: str
    read_only_status_surface: bool
    durable_decision_authority_used: bool
    decision_status_api_route_enabled: bool
    decision_submit_api_route_enabled: bool
    workflow_open_api_route_enabled: bool
    runtime_default_enabled: bool
    value_reveal_performed: bool
    source_acquisition_performed: bool
    arelle_invoked: bool
    delivery_export_enabled: bool
    rendered_ui_enabled: bool
    operator_review_decision_recorded: bool
    workflow_mutated: bool
    statement_packet_mutated: bool
    projection_mutated: bool
    negative_invariants: dict[str, bool]
    next_allowed_actions: list[str]


class Layer3SecXbrlValueRevealAuthorityPrepareResponse(Layer3BaseResponse):
    sec_xbrl_value_reveal_authority_receipt_id: str
    value_reveal_authority_receipt_ref: str
    client_request_id: str
    authority_basis_hash: str
    authority_mode: str
    authority_policy_id: str
    redaction_policy: str
    sec_xbrl_operator_review_decision_id: str
    decision_basis_hash: str
    sec_xbrl_operator_review_workflow_id: str
    workflow_basis_hash: str
    sec_xbrl_statement_packet_set_id: str
    statement_packet_basis_hash: str
    sec_xbrl_projection_set_id: str
    projection_basis_hash: str
    dataset_version_id: str
    dataset_version_hash: str
    sidecar_receipt_id_hash: str
    sidecar_receipt_hash: str
    value_store_hash: str
    operator_actor_hash: str | None
    authority_summary: dict[str, Any]
    negative_invariants: dict[str, bool]
    eligible_for_explicit_value_reveal: bool
    idempotent_replay: bool
    next_allowed_actions: list[str]
    runtime_default_enabled: bool
    value_reveal_performed: bool
    source_acquisition_performed: bool
    arelle_invoked: bool
    delivery_export_enabled: bool
    rendered_ui_enabled: bool
    production_readiness_claimed: bool


class Layer3SecXbrlControlledValueRevealSubmitResponse(Layer3BaseResponse):
    submit_mode: str
    submit_state: str
    sec_xbrl_controlled_value_reveal_submit_receipt_id: str
    value_reveal_submit_receipt_ref: str
    client_request_id_hash: str
    submit_basis_hash: str
    sec_xbrl_value_reveal_authority_receipt_id: str
    authority_basis_hash: str
    submit_policy_id: str
    redaction_policy: str
    sec_xbrl_operator_review_decision_id: str | None = None
    decision_basis_hash: str | None = None
    sec_xbrl_operator_review_workflow_id: str | None = None
    workflow_basis_hash: str | None = None
    sec_xbrl_statement_packet_set_id: str | None = None
    statement_packet_basis_hash: str | None = None
    sec_xbrl_projection_set_id: str | None = None
    projection_basis_hash: str | None = None
    dataset_version_id: str | None = None
    dataset_version_hash: str | None = None
    sidecar_receipt_id_hash: str | None = None
    sidecar_receipt_hash: str | None = None
    value_store_hash: str | None = None
    revealed_fact_count: int
    next_page_cursor: str | None = None
    total_record_count: int
    page_record_count: int
    page_index: int
    revealed_facts: list[dict[str, Any]]
    value_redacted_fact_count: int
    fact_inventory_hash: str
    value_inventory_hash: str
    response_inventory_hash: str
    submit_summary: dict[str, Any]
    negative_invariants: dict[str, bool]
    transient_values_returned: bool
    idempotent_replay: bool
    status_surface_hash_count_only: bool
    audit_receipt_raw_values_persisted: bool
    raw_sidecar_receipt_id_persisted: bool
    runtime_default_enabled: bool
    source_acquisition_performed: bool
    arelle_invoked: bool
    delivery_export_enabled: bool
    rendered_ui_enabled: bool
    production_readiness_claimed: bool
    next_allowed_actions: list[str]


class Layer3ApsContentDocumentCandidatesResponse(Layer3BaseResponse):
    aps_content_document_candidates: list[dict[str, Any]]
    candidate_count: int
    source_system: str
    authority_rail: dict[str, Any]


class Layer3ApsRefusedArtifactTracesResponse(Layer3BaseResponse):
    refused_artifact_traces: list[dict[str, Any]]
    trace_count: int
    inspected_run_count: int
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


class Layer3PublicConnectorExecutionResultValuesResponse(Layer3BaseResponse):
    session_id: str
    analysis_plan_id: str
    pass_run_id: str
    preview_identity: dict[str, Any]
    analysis_run_id: str
    dataset_version_id: str
    selected_method_name: str
    provenance: dict[str, Any]
    values: dict[str, Any]


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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    preview_identity: dict[str, Any]
    package_review_preview_hash: str
    package_family: str | None = None
    contract_schema_id: str | None = None
    contract_hash: str | None = None
    selected_source_ids: dict[str, list[str]] | None = None
    narrative_table_link_count: int | None = None
    missing_authority_inputs: list[str] | None = None
    negative_authority_flags: dict[str, bool] | None = None
    mixed_source_package_review_preview: dict[str, Any] | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    preview_identity: dict[str, Any]
    analysis_run_id: str | None
    result_review_record_ref: str
    package_review_preview_hash: str
    contract_hash: str | None = None
    selected_source_ids: dict[str, list[str]] | None = None
    narrative_table_link_count: int | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
    package_family: str | None = None
    negative_authority_flags: dict[str, bool] | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
    package_family: str | None = None
    negative_authority_flags: dict[str, Any] | None = None
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
    handoff_export_envelope_ref: str | None = None
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
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    contract_hash: str | None = None
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
    aps_handoff_dispatch_schema_id: str | None = None
    package_family: str | None = None
    expected_package_kinds: list[str] | None = None
    negative_authority_flags: dict[str, Any] | None = None
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


class Layer3MixedSourceExternalExportDownloadReadinessResponse(Layer3BaseResponse):
    session_id: str
    material_preview_id: str
    material_preview_hash: str
    contract_hash: str
    package_review_preview_hash: str
    construction_basis_hash: str
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
    aps_handoff_target: str
    dispatch_mode: str
    aps_handoff_record_ref: str
    aps_handoff_state: str
    operator_decision: str
    decision_notes: str | None
    package_family: str
    readiness_schema_id: str | None = None
    external_export_download_readiness_schema_id: str
    external_export_download_readiness_state: str
    external_export_download_readiness_record_ref: str
    external_export_download_readiness_ref: str
    negative_authority_flags: dict[str, Any]
    external_export_enabled: bool
    download_enabled: bool
    download_url_enabled: bool
    signed_reference_enabled: bool
    provider_public_url_enabled: bool
    provider_private_signed_url_enabled: bool
    connector_dispatch_enabled: bool
    delivery_enabled: bool
    external_export_download_enabled: bool
    downstream_unavailable: list[str]
    next_allowed_actions: list[str]
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


class Layer3ConnectorDatasetHandoffResponse(Layer3BaseResponse):
    session_id: str
    error_code: str | None = None
    message: str | None = None
    recoverable: bool | None = None
    next_allowed_actions: list[str] | None = None
    connector_promotion_receipt_id: str | None = None
    canonical_identity_key_hash: str | None = None
    reconciliation_record_id: str | None = None
    construction_basis_hash: str | None = None
    output_packages: list[dict[str, Any]] | None = None
    output_package_ids: list[str] | None = None
    package_kinds: list[str] | None = None
    payload_refs: list[str] | None = None
    payload_hashes: list[str] | None = None
    source_gate: str | None = None
    handoff_enabled: bool | None = None
    downstream_unavailable: dict[str, bool] | None = None
    negative_invariants: dict[str, bool] | None = None
    replayed: bool | None = None
    next_state: str
    authority_rail: dict[str, Any] | None = None


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
    analysis_plan_id: str | None = None
    pass_run_id: str | None = None
    preview_identity: dict[str, Any] | None = None
    reconciliation_record_id: str
    external_export_download_record_ref: str | None = None
    export_download_descriptor_ref: str | None = None
    material_preview_id: str | None = None
    material_preview_hash: str | None = None
    package_review_preview_hash: str | None = None
    contract_hash: str | None = None
    construction_basis_hash: str | None = None
    package_family: str | None = None
    output_package_id: str | None = None
    package_kind: str | None = None
    package_payload_hash: str | None = None
    package_review_submit_record_ref: str | None = None
    package_review_state: str | None = None
    prepare_record_ref: str | None = None
    handoff_export_state: str | None = None
    handoff_export_envelope_ref: str | None = None
    handoff_target: str | None = None
    export_mode: str | None = None
    aps_handoff_target: str | None = None
    dispatch_mode: str | None = None
    aps_handoff_record_ref: str | None = None
    aps_handoff_state: str | None = None
    external_export_download_readiness_record_ref: str | None = None
    external_export_download_readiness_ref: str | None = None
    external_export_download_readiness_state: str | None = None
    external_export_download_delivery_record_ref: str | None = None
    external_export_download_delivery_ref: str | None = None
    external_export_download_delivery_state: str | None = None
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
    signed_reference_delivery_mode: str | None = None
    operator_decision: str | None = None
    use_operator_decision: str | None = None
    server_authority: str
    source_artifact_ref: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    schema_id_authority: str | None = None
    pass_type: str | None = None
    pass_scope: str | None = None
    method: str | None = None
    source_gate: str | None = None
    source_shape: str | None = None
    source_dataset_version_ids: list[str] = Field(default_factory=list)
    download_url_enabled: bool | None = None
    public_url_enabled: bool
    external_object_store_url_enabled: bool | None = None
    provider_public_url_enabled: bool | None = None
    provider_private_signed_url_enabled: bool | None = None
    connector_dispatch_enabled: bool
    destination_selection_enabled: bool
    generic_downstream_dispatch_enabled: bool
    package_payload_rewrite_enabled: bool | None = None
    package_mutation_enabled: bool
    schema_runtime_source_widening_enabled: bool
    production_readiness_enabled: bool | None = None
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
    analysis_product_inventory_projection: dict[str, Any]
    state_action_contract: dict[str, Any]
    downstream_unavailable: list[str]
    authority_rail: dict[str, Any]


class Layer3SublayerVisualizationCollectionResponse(Layer3BaseResponse):
    session_id: str
    collection: str
    authority_source: str
    read_model: str
    total: int
    included_count: int
    limit: int
    offset: int
    has_more: bool
    items: list[dict[str, Any]]
    no_side_effects: bool



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
def post_preflight(
    request: Request,
    payload: Layer3PreflightRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.preflight(payload.model_dump(exclude_none=True)))


@router.post(
    "/source-preview",
    response_model=Layer3SourcePreviewResponse,
    openapi_extra={"requestBody": _json_request_body(SOURCE_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_source_preview(
    request: Request,
    payload: Layer3SourcePreviewRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.source_preview(payload.model_dump(exclude_none=True)))



@router.post(
    "/material-preview",
    response_model=Layer3MaterialPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(MATERIAL_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400),
)
def post_material_preview(
    payload: Layer3MaterialPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.material_preview(payload.model_dump(exclude_none=True), db))


@router.get(
    "/dataset-version-candidates",
    response_model=Layer3DatasetVersionCandidatesResponse,
    responses=_workbench_error_responses(400),
)
def get_dataset_version_candidates(
    request: Request,
    limit: int = 50, db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.aps_dataset_version_candidates(db, limit=limit))


@router.get(
    "/public-dataset-version-candidates",
    response_model=Layer3DatasetVersionCandidatesResponse,
    responses=_workbench_error_responses(400),
)
def get_public_dataset_version_candidates(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_workbench.public_connector_dataset_version_candidates(db, limit=limit)
    )


@router.get(
    "/aps-content-document-candidates",
    response_model=Layer3ApsContentDocumentCandidatesResponse,
    responses=_workbench_error_responses(400),
)
def get_aps_content_document_candidates(
    request: Request,
    limit: int = 50, db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.aps_content_document_candidates(db, limit=limit))


@router.get(
    "/aps-refused-artifact-traces",
    response_model=Layer3ApsRefusedArtifactTracesResponse,
    responses=_workbench_error_responses(400),
)
def get_aps_refused_artifact_traces(
    request: Request,
    limit: int = 50, db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.aps_refused_artifact_traces(db, limit=limit))


@router.post(
    "/gate-b/decision",
    response_model=Layer3GateBDecisionResponse,
    openapi_extra={"requestBody": _json_request_body(GATE_B_DECISION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 409),
)
def post_gate_b_decision(
    payload: Layer3GateBDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.gate_b_decision(db, payload.model_dump(exclude_none=True)))


@router.post(
    "/gate-c/preview",
    response_model=Layer3GateCPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(GATE_C_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_gate_c_preview(
    payload: Layer3GateCPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.gate_c_preview(db, payload.model_dump(exclude_none=True)))


@router.post(
    "/gate-c/override",
    status_code=409,
    response_model=Layer3TypingOverrideUnavailableResponse,
)
def post_gate_c_override(
    request: Request,
    payload: Layer3GateCOverrideUnavailableRequest,
) -> JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.plan_preview(db, payload.model_dump(exclude_none=True)))


@router.post(
    "/plan/approve",
    response_model=Layer3PlanApprovalResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_APPROVAL_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_approve(
    payload: Layer3PlanApprovalRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.approved_plan_cancel(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/plan/revise",
    response_model=Layer3PlanRevisionResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_REVISION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_revise(
    payload: Layer3PlanRevisionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.plan_revision(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/plan/revision/recover",
    response_model=Layer3PlanRevisionRecoveryResponse,
    openapi_extra={"requestBody": _json_request_body(PLAN_REVISION_RECOVERY_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409, 500),
)
def post_plan_revision_recover(
    payload: Layer3PlanRevisionRecoveryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.plan_revision_recovery(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/select",
    response_model=Layer3ExecutionSelectionResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_SELECTION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_select(
    payload: Layer3ExecutionSelectionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.execution_selection(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/start",
    response_model=Layer3AnalysisExecutionStartResponse,
    openapi_extra={"requestBody": _json_request_body(ANALYSIS_EXECUTION_START_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_start(
    payload: Layer3AnalysisExecutionStartRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.analysis_execution_start(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/result/status",
    response_model=Layer3ExecutionResultStatusResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_RESULT_STATUS_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_result_status(
    payload: Layer3ExecutionResultStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.execution_result_status(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/execution/result/public-values",
    response_model=Layer3PublicConnectorExecutionResultValuesResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_RESULT_STATUS_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_public_connector_execution_result_values(
    payload: Layer3ExecutionResultStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_workbench.public_connector_execution_result_values(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/execution/result/review",
    response_model=Layer3ExecutionResultReviewResponse,
    openapi_extra={"requestBody": _json_request_body(EXECUTION_RESULT_REVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_execution_result_review(
    payload: Layer3ExecutionResultReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.execution_result_review(db, payload.model_dump(exclude_unset=True)))


@router.get(
    "/session/{session_id}",
    response_model=Layer3SessionSummaryResponse,
    responses={
        404: {"model": Layer3WorkbenchErrorResponse},
        409: {"model": Layer3WorkbenchErrorResponse},
    },
)
def get_session_summary(
    request: Request,
    session_id: str, db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.session_summary(db, session_id))


@router.get(
    "/session/{session_id}/sublayer-visualization/{collection}",
    response_model=Layer3SublayerVisualizationCollectionResponse,
    responses=_workbench_error_responses(400, 404),
)
def get_session_sublayer_visualization_collection(
    session_id: str,
    collection: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_workbench.session_sublayer_visualization_collection(
            db,
            session_id=session_id,
            collection=collection,
            limit=limit,
            offset=offset,
        )
    )


# ---------------------------------------------------------------------------
# Analysis-product authoring — Manual Draft 3C
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_DRAFT_SCHEMA_ID = "layer3.analysis_product.v1"
WORKING_SET_SCHEMA_ID = "layer3.working_set.v1"


class Layer3AnalysisProductEvidenceLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_kind: str = Field(min_length=1)
    ref_id: str = Field(min_length=1)
    evidence_role: str = Field(min_length=1)
    locator: dict[str, Any] | None = None


class Layer3AnalysisProductDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    client_request_id: str = Field(min_length=1)
    product_kind: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    evidence: list[Layer3AnalysisProductEvidenceLinkRequest] = Field(default_factory=list)
    is_non_evidentiary: bool = False
    authoring_provenance: dict[str, Any] | None = None


class Layer3AnalysisProductDraftResponse(Layer3BaseResponse):
    analysis_product_id: str
    session_id: str
    product_kind: str
    executor_type: str
    lifecycle_status: str
    title: str
    evidence_count: int
    grounded: bool
    basis_hash: str
    spec_hash: str
    created_at: str
    replayed: bool


@router.post(
    "/analysis-product/draft",
    response_model=Layer3AnalysisProductDraftResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_analysis_product_draft(
    payload: Layer3AnalysisProductDraftRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    draft = AnalysisProductDraft(
        product_kind=payload.product_kind,
        title=payload.title,
        body=payload.body,
        evidence=tuple(
            AnalysisProductEvidenceDraft(
                ref_kind=ev.ref_kind,
                ref_id=ev.ref_id,
                evidence_role=ev.evidence_role,
                locator=ev.locator,
            )
            for ev in payload.evidence
        ),
        is_non_evidentiary=payload.is_non_evidentiary,
        authoring_provenance=payload.authoring_provenance,
        executor_type="human",
    )
    try:
        result = create_analysis_product_draft(
            db,
            session_id=payload.session_id,
            client_request_id=payload.client_request_id,
            draft=draft,
        )
        db.commit()
        product = result.product
        serialized = _serialize_analysis_product(product, list(result.evidence_links))
        return {
            **base_response(ANALYSIS_PRODUCT_DRAFT_SCHEMA_ID),
            "analysis_product_id": product.analysis_product_id,
            "session_id": product.session_id,
            "product_kind": product.product_kind,
            "executor_type": product.executor_type,
            "lifecycle_status": product.lifecycle_status,
            "title": product.title,
            "evidence_count": serialized["evidence_count"],
            "grounded": serialized["grounded"],
            "basis_hash": product.basis_hash,
            "spec_hash": product.spec_hash,
            "created_at": serialized["created_at"] or "",
            "replayed": result.replayed,
        }
    except Layer3AnalysisProductError as exc:
        db.rollback()
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


# ---------------------------------------------------------------------------
# Working-set authoring — 3C Working Set Formalization v0
# ---------------------------------------------------------------------------


class Layer3WorkingSetMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_kind: str = Field(min_length=1)
    ref_id: str = Field(min_length=1)


class Layer3WorkingSetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    client_request_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    members: list[Layer3WorkingSetMemberRequest] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None


class Layer3WorkingSetCreateResponse(Layer3BaseResponse):
    working_set_id: str
    session_id: str
    name: str
    member_count: int
    basis_hash: str
    created_at: str
    replayed: bool


@router.post(
    "/working-set",
    response_model=Layer3WorkingSetCreateResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_working_set(
    payload: Layer3WorkingSetCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    draft = WorkingSetDraft(
        name=payload.name,
        members=tuple(
            WorkingSetMemberDraft(ref_kind=m.ref_kind, ref_id=m.ref_id)
            for m in payload.members
        ),
        provenance=payload.provenance,
    )
    try:
        result = create_working_set(
            db,
            session_id=payload.session_id,
            client_request_id=payload.client_request_id,
            draft=draft,
        )
        db.commit()
        ws = result.working_set
        return {
            **base_response(WORKING_SET_SCHEMA_ID),
            "working_set_id": ws.working_set_id,
            "session_id": ws.session_id,
            "name": ws.name,
            "member_count": ws.member_count,
            "basis_hash": ws.basis_hash,
            "created_at": ws.created_at.isoformat() if ws.created_at is not None else "",
            "replayed": result.replayed,
        }
    except Layer3WorkingSetError as exc:
        db.rollback()
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


# ---------------------------------------------------------------------------
# Analysis-product generation — Deterministic 3C Product Generation v0
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_GENERATE_SCHEMA_ID = "layer3.analysis_product_generation.v1"


class Layer3AnalysisProductGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    client_request_id: str = Field(min_length=1)
    working_set_id: str = Field(min_length=1)
    method_id: str = Field(min_length=1)


class Layer3AnalysisProductGenerateResponse(Layer3BaseResponse):
    analysis_product_id: str
    session_id: str
    working_set_id: str
    method_id: str
    method_version: int
    executor_type: str
    lifecycle_status: str
    title: str
    evidence_count: int
    created_at: str
    replayed: bool


@router.post(
    "/analysis-product/generate",
    response_model=Layer3AnalysisProductGenerateResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_analysis_product_generate(
    payload: Layer3AnalysisProductGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    from app.services.layer3_analysis_product_generation import (
        Layer3GenerationResult,
        generate_analysis_product,
    )
    from app.services.layer3_lifecycle_events import bounded_operator_ref, emit_lifecycle_event

    # Re-derive the (idempotent, side-effect-free) principal for the bounded
    # audit ref. The gate above stays a bare call so the identity-seam drift
    # guard sees it as the first statement in the try.
    _principal = _route_level_operator_identity(request, access="write")

    try:
        gen_result = generate_analysis_product(
            db,
            session_id=payload.session_id,
            client_request_id=payload.client_request_id,
            working_set_id=payload.working_set_id,
            method_id=payload.method_id,
        )
        db.commit()
        product = gen_result.product
        # Emit immediately after commit (before serialization) so a committed
        # product always fires its lifecycle event even if serialization fails.
        # Skip on idempotent replay: no new product was created, so it is not a
        # real lifecycle change and must not inflate the audit stream.
        if not gen_result.replayed:
            emit_lifecycle_event(
                "product_generated",
                request_id=getattr(getattr(request, "state", None), "request_id", None),
                operator_ref=bounded_operator_ref(_principal),
                product_id=product.analysis_product_id,
                method_id=gen_result.method_id,
                method_version=gen_result.method_version,
                lifecycle_status=product.lifecycle_status,
            )
        serialized = _serialize_analysis_product(product, list(gen_result.evidence_links))
        return {
            **base_response(ANALYSIS_PRODUCT_GENERATE_SCHEMA_ID),
            "analysis_product_id": product.analysis_product_id,
            "session_id": product.session_id,
            "working_set_id": payload.working_set_id,
            "method_id": gen_result.method_id,
            "method_version": gen_result.method_version,
            "executor_type": product.executor_type,
            "lifecycle_status": product.lifecycle_status,
            "title": product.title,
            "evidence_count": serialized["evidence_count"],
            "created_at": serialized["created_at"] or "",
            "replayed": gen_result.replayed,
        }
    except Layer3AnalysisProductError as exc:
        db.rollback()
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


# ---------------------------------------------------------------------------
# Analysis-product method catalog — Deterministic 3C Method Catalog (R9)
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_METHODS_SCHEMA_ID = "layer3.deterministic_method_catalog.v1"


class Layer3AnalysisProductMethodEntryResponse(BaseModel):
    method_id: str
    method_version: int
    label: str
    product_kind: str
    consumes_member_state: bool
    description: str


class Layer3AnalysisProductMethodsResponse(Layer3BaseResponse):
    methods: list[Layer3AnalysisProductMethodEntryResponse]


@router.get(
    "/analysis-product/methods",
    response_model=Layer3AnalysisProductMethodsResponse,
    responses=_workbench_error_responses(400),
)
def get_analysis_product_methods(
    request: Request,
) -> dict[str, Any] | JSONResponse:
    """Return the server-owned deterministic method catalog.

    Derived solely from the DETERMINISTIC_METHODS registry; no DB access,
    no query parameters.  Sorted by method_id for stable UI ordering.
    Requires operator-identity seam (read access) exactly like sibling GETs.
    """
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    from app.services.layer3_deterministic_methods import DETERMINISTIC_METHODS

    methods = sorted(
        [
            {
                "method_id": spec.method_id,
                "method_version": spec.version,
                "label": spec.label,
                "product_kind": spec.product_kind,
                "consumes_member_state": spec.consumes_member_state,
                "description": spec.description,
            }
            for spec in DETERMINISTIC_METHODS.values()
        ],
        key=lambda m: m["method_id"],
    )
    return {
        **base_response(ANALYSIS_PRODUCT_METHODS_SCHEMA_ID),
        "methods": methods,
    }


# ---------------------------------------------------------------------------
# Analysis-product replay verify — Deterministic 3C Reproducibility Verify
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_REPLAY_VERIFY_SCHEMA_ID = "layer3.analysis_product_replay_verify.v1"


class Layer3AnalysisProductReplayVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    analysis_product_id: str = Field(min_length=1)


class Layer3AnalysisProductReplayVerifyResponse(Layer3BaseResponse):
    analysis_product_id: str
    executor_type: str
    method_id: str
    reproduced: bool
    classification: str
    method_present: bool
    method_version_match: bool | None
    input_basis_match: bool | None
    input_state_match: bool | None
    result_match: bool | None
    method_version_recorded: int | None
    method_version_current: int | None
    input_basis_hash_recorded: str | None
    input_basis_hash_current: str | None
    input_state_hash_recorded: str | None
    input_state_hash_current: str | None
    param_hash_recorded: str | None
    validation_recorded: str | None
    result_summary_hash_recorded: str | None
    result_summary_hash_current: str | None


@router.post(
    "/analysis-product/replay-verify",
    response_model=Layer3AnalysisProductReplayVerifyResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_analysis_product_replay_verify(
    payload: Layer3AnalysisProductReplayVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    from app.services.layer3_analysis_product_replay import verify_analysis_product_replay
    from app.services.layer3_lifecycle_events import bounded_operator_ref, emit_lifecycle_event

    # Re-derive the (idempotent, side-effect-free) principal for the bounded
    # audit ref; the gate above stays a bare call for the identity-seam guard.
    _principal = _route_level_operator_identity(request, access="read")

    try:
        result = verify_analysis_product_replay(
            db,
            session_id=payload.session_id,
            analysis_product_id=payload.analysis_product_id,
        )
        emit_lifecycle_event(
            "product_replay_verified",
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            operator_ref=bounded_operator_ref(_principal),
            product_id=result.analysis_product_id,
            reproduced=result.reproduced,
            classification=result.classification,
        )
        return {
            **base_response(ANALYSIS_PRODUCT_REPLAY_VERIFY_SCHEMA_ID),
            "analysis_product_id": result.analysis_product_id,
            "executor_type": result.executor_type,
            "method_id": result.method_id,
            "reproduced": result.reproduced,
            "classification": result.classification,
            "method_present": result.method_present,
            "method_version_match": result.method_version_match,
            "input_basis_match": result.input_basis_match,
            "input_state_match": result.input_state_match,
            "result_match": result.result_match,
            "method_version_recorded": result.method_version_recorded,
            "method_version_current": result.method_version_current,
            "input_basis_hash_recorded": result.input_basis_hash_recorded,
            "input_basis_hash_current": result.input_basis_hash_current,
            "input_state_hash_recorded": result.input_state_hash_recorded,
            "input_state_hash_current": result.input_state_hash_current,
            "param_hash_recorded": result.param_hash_recorded,
            "validation_recorded": result.validation_recorded,
            "result_summary_hash_recorded": result.result_summary_hash_recorded,
            "result_summary_hash_current": result.result_summary_hash_current,
        }
    except Layer3AnalysisProductError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


# ---------------------------------------------------------------------------
# Analysis-product lineage — 3C read-only inspector
# ---------------------------------------------------------------------------

LINEAGE_SCHEMA_ID = "layer3.analysis_product_lineage.v1"


class Layer3AnalysisProductLineageResponse(Layer3BaseResponse):
    analysis_product_id: str
    product: dict[str, Any]
    working_set: dict[str, Any] | None
    working_set_linked: bool
    method_provenance: dict[str, Any] | None
    evidence_refs: list[dict[str, Any]]
    evidence_refs_truncated: bool
    review_trail: list[dict[str, Any]]
    review_trail_truncated: bool
    review_trail_total: int
    package: dict[str, Any]


@router.get(
    "/analysis-product/{analysis_product_id}/lineage",
    response_model=Layer3AnalysisProductLineageResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_analysis_product_lineage(
    analysis_product_id: str,
    request: Request,
    session_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    from app.services.layer3_analysis_product_lineage import build_analysis_product_lineage

    try:
        lineage = build_analysis_product_lineage(
            db,
            session_id=session_id,
            analysis_product_id=analysis_product_id,
        )
        return {
            **base_response(LINEAGE_SCHEMA_ID),
            **{k: v for k, v in lineage.items() if k != "schema_id"},
        }
    except Layer3AnalysisProductError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


# ---------------------------------------------------------------------------
# Analysis-product promotion — 3C Review/Promotion
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_TRANSITION_SCHEMA_ID = "layer3.analysis_product_promotion.v1"


class Layer3AnalysisProductTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    client_request_id: str = Field(min_length=1)
    decision_intent: str = Field(min_length=1)
    decision_reason_code: str = Field(min_length=1)
    operator_identity: str | None = None
    decision_notes: str | None = None
    decision_provenance: dict[str, Any] | None = None


class Layer3AnalysisProductTransitionResponse(Layer3BaseResponse):
    analysis_product_id: str
    session_id: str
    from_status: str
    lifecycle_status: str
    review_decision: str
    decision_reason_code: str
    grounding_asserted: bool
    decision_basis_hash: str
    analysis_product_review_decision_id: str
    created_at: str
    replayed: bool


@router.post(
    "/analysis-product/{analysis_product_id}/transition",
    response_model=Layer3AnalysisProductTransitionResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_analysis_product_transition(
    analysis_product_id: str,
    payload: Layer3AnalysisProductTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    from app.services.layer3_lifecycle_events import bounded_operator_ref, emit_lifecycle_event
    # Capture request_id + bounded operator ref BEFORE `request` is rebound below.
    # The gate above stays a bare call for the identity-seam guard; re-deriving
    # the principal here is idempotent and side-effect-free.
    _lifecycle_request_id = getattr(getattr(request, "state", None), "request_id", None)
    _lifecycle_operator_ref = bounded_operator_ref(
        _route_level_operator_identity(request, access="write")
    )
    request = AnalysisProductTransitionRequest(
        decision_intent=payload.decision_intent,
        decision_reason_code=payload.decision_reason_code,
        operator_identity=payload.operator_identity,
        decision_notes=payload.decision_notes,
        decision_provenance=payload.decision_provenance,
    )
    try:
        result = transition_analysis_product(
            db,
            session_id=payload.session_id,
            analysis_product_id=analysis_product_id,
            client_request_id=payload.client_request_id,
            request=request,
        )
        db.commit()
        decision = result.decision
        product = result.product
        # Skip on idempotent replay: a re-submitted decision did not change
        # lifecycle state, so it must not be recorded as a real transition.
        if not result.replayed:
            emit_lifecycle_event(
                "product_transitioned",
                request_id=_lifecycle_request_id,
                operator_ref=_lifecycle_operator_ref,
                product_id=product.analysis_product_id,
                from_status=decision.from_status,
                to_status=product.lifecycle_status,
                review_decision=decision.review_decision,
                decision_reason_code=decision.decision_reason_code,
            )
        return {
            **base_response(ANALYSIS_PRODUCT_TRANSITION_SCHEMA_ID),
            "analysis_product_id": product.analysis_product_id,
            "session_id": product.session_id,
            "from_status": decision.from_status,
            "lifecycle_status": product.lifecycle_status,
            "review_decision": decision.review_decision,
            "decision_reason_code": decision.decision_reason_code,
            "grounding_asserted": bool(decision.grounding_asserted),
            "decision_basis_hash": decision.decision_basis_hash,
            "analysis_product_review_decision_id": decision.analysis_product_review_decision_id,
            "created_at": decision.created_at.isoformat() if decision.created_at is not None else "",
            "replayed": result.replayed,
        }
    except Layer3AnalysisProductError as exc:
        db.rollback()
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


from app.api.layer3 import handoff  # noqa: F401  -- registers handoff routes on the shared router
from app.api.layer3 import package  # noqa: F401  -- registers package routes on the shared router
from app.api.layer3 import source_ingestion  # noqa: F401  -- registers source-ingestion routes on the shared router
from app.api.layer3 import source_sec_edgar  # noqa: F401  -- registers source-sec-edgar routes on the shared router
from app.api.layer3 import sec_xbrl  # noqa: F401
from app.api.layer3 import operator_identity  # noqa: F401  -- registers operator identity projection route on the shared router
from app.api.layer3.sec_xbrl import (  # re-export for test coupling
    post_sec_xbrl_operator_review_workflow_open_from_staged_evidence,
    _full_pipeline_leaf_equals_raw_cik,
)
