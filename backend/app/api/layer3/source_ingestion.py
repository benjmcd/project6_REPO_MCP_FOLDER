from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import (
    layer3_candidate_b_artifact_status,
    layer3_candidate_b_broader_scope_default_promotion,
    layer3_candidate_b_broader_scope_promotion_readiness,
    layer3_candidate_b_broader_scope_readiness,
    layer3_candidate_b_broader_scope_repeatability_trial,
    layer3_candidate_b_broader_scope_runtime,
    layer3_candidate_b_broader_scope_selector_use,
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_default_readiness,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_final_proof,
    layer3_candidate_b_full_corpus_operator_repeatability_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof,
    layer3_candidate_b_full_corpus_operator_workflow_completion_failure,
    layer3_candidate_b_full_corpus_operator_workflow_completion_monitor,
    layer3_candidate_b_full_corpus_operator_workflow_execution_boundary,
    layer3_candidate_b_full_corpus_operator_workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_lifecycle,
    layer3_candidate_b_full_corpus_operator_workflow_process_completion_result,
    layer3_candidate_b_full_corpus_operator_workflow_process_execution,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_queue_state,
    layer3_candidate_b_full_corpus_operator_workflow_retry_completion_failure,
    layer3_candidate_b_full_corpus_operator_workflow_retry_policy,
    layer3_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_retry_queue_state,
    layer3_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_retry_worker_attempt,
    layer3_candidate_b_full_corpus_operator_workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_status,
    layer3_candidate_b_full_corpus_operator_workflow_worker_attempt,
    layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint,
    layer3_candidate_b_full_corpus_repeatability_acceptance_closeout,
    layer3_candidate_b_full_corpus_repeatability_rerun_trial,
    layer3_candidate_b_operator_status,
    layer3_candidate_b_operator_workflow_access_policy,
    layer3_candidate_b_promotion_closure,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_visual_lane_status,
    layer3_connector_promotion,
    layer3_package_supersession_commit,
    layer3_raw_mixed_bridge,
    layer3_raw_mixed_materialization,
    layer3_replacement_package_set_authority,
    layer3_source_directory_context_packet,
    layer3_source_directory_hybrid_analysis,
    layer3_source_directory_hybrid_authority,
    layer3_source_directory_hybrid_context,
    layer3_source_directory_ingestion,
    layer3_source_directory_internal_webhook,
    layer3_source_directory_material_admission,
    layer3_source_directory_qualitative_analysis,
    layer3_source_directory_text_index,
    layer3_source_directory_text_retrieval,
    layer3_source_directory_vector_index,
    layer3_source_directory_vector_retrieval,
    layer3_source_intake,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response
from app.api.layer3 import router  # the shared APIRouter instance
from app.api.layer3._shared import *  # noqa: F401,F403
from app.api.layer3 import (  # Pydantic models still defined in __init__
    Layer3BaseResponse,
    Layer3CandidateBArtifactFamilyStatusRequest,
    Layer3CandidateBArtifactFamilyStatusResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeActivationReceiptConsumptionRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeActivationReceiptConsumptionResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseStatusRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseStatusResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeDefaultPromotionRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeDefaultPromotionResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeOperatorRepeatabilityTrialRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeOperatorRepeatabilityTrialResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopePromotionReadinessRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopePromotionReadinessResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeRuntimeRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeRuntimeResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorActivationRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorActivationResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseResponse,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseStatusRequest,
    Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseStatusResponse,
    Layer3CandidateBBroaderEligibleCorpusScopeReadinessAuditRequest,
    Layer3CandidateBBroaderEligibleCorpusScopeReadinessAuditResponse,
    Layer3CandidateBBundleDownstreamProofRequest,
    Layer3CandidateBBundleDownstreamProofResponse,
    Layer3CandidateBBundleMaterialBridgeRequest,
    Layer3CandidateBBundleMaterialBridgeResponse,
    Layer3CandidateBDefaultPromotionClosureEvidenceRequest,
    Layer3CandidateBDefaultPromotionClosureEvidenceResponse,
    Layer3CandidateBDefaultPromotionFinalProofRequest,
    Layer3CandidateBDefaultPromotionFinalProofResponse,
    Layer3CandidateBDefaultPromotionFinalProofStatusRequest,
    Layer3CandidateBDefaultPromotionFinalProofStatusResponse,
    Layer3CandidateBDefaultPromotionOperatorStatusRequest,
    Layer3CandidateBDefaultPromotionOperatorStatusResponse,
    Layer3CandidateBDefaultPromotionReadinessAuditRequest,
    Layer3CandidateBDefaultPromotionReadinessAuditResponse,
    Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointRequest,
    Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowCompletionFailureRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowCompletionFailureResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowCompletionMonitorRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowCompletionMonitorResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowExecutionBoundaryRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowExecutionBoundaryResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowHistoryResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowLifecycleRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowLifecycleResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowProcessCompletionResultRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowProcessCompletionResultResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowProcessExecutionRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowProcessExecutionResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowProgressCheckpointRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowProgressCheckpointResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowQueueStateRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowQueueStateResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryPolicyRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryPolicyResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryQueueStateRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryQueueStateResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowRunRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowRunResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowSchedulerLeaseRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowSchedulerLeaseResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowStatusRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowStatusResponse,
    Layer3CandidateBFullCorpusOperatorWorkflowWorkerAttemptRequest,
    Layer3CandidateBFullCorpusOperatorWorkflowWorkerAttemptResponse,
    Layer3CandidateBFullCorpusRepeatabilityAcceptanceCheckpointRequest,
    Layer3CandidateBFullCorpusRepeatabilityAcceptanceCheckpointResponse,
    Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutRequest,
    Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutResponse,
    Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatusRequest,
    Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatusResponse,
    Layer3CandidateBFullCorpusRepeatabilityRerunTrialRequest,
    Layer3CandidateBFullCorpusRepeatabilityRerunTrialResponse,
    Layer3CandidateBRuntimeBridgeSourceScanRequest,
    Layer3CandidateBRuntimeDownstreamProofRequest,
    Layer3CandidateBRuntimeDownstreamProofResponse,
    Layer3CandidateBRuntimeMaterialBridgeRequest,
    Layer3CandidateBRuntimeMaterialBridgeResponse,
    Layer3CandidateBVisualLaneStatusRequest,
    Layer3CandidateBVisualLaneStatusResponse,
    Layer3PackageSupersessionCommitResponse,
    Layer3RawMixedCorpusMaterializeRequest,
    Layer3RawMixedCorpusMaterializeResponse,
    Layer3RawMixedCorpusSeedRequest,
    Layer3RawMixedCorpusSeedResponse,
    Layer3ReplacementPackageSetAuthorityResponse,
    Layer3SourceDirectoryHybridAuthorityPrepareRequest,
    Layer3SourceDirectoryHybridAuthorityPrepareResponse,
    Layer3SourceDirectoryHybridContextPacketRequest,
    Layer3SourceDirectoryHybridContextPacketResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliveryStatusResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisResponse,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusRequest,
    Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusResponse,
    Layer3SourceDirectoryIngestionResponse,
    Layer3SourceDirectoryIngestionScanRequest,
    Layer3SourceDirectoryMaterialPreviewRequest,
    Layer3SourceDirectoryMaterialPreviewResponse,
    Layer3SourceDirectoryPackageSupersessionCommitRequest,
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlPrepareRequest,
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlRevokeRequest,
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlStatusRequest,
    Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlUseRequest,
    Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliverRequest,
    Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliveryStatusResponse,
    Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareRequest,
    Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareResponse,
    Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareRequest,
    Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareResponse,
    Layer3SourceDirectoryQualitativeAnalysisPackageCommitRequest,
    Layer3SourceDirectoryQualitativeAnalysisPackageCommitResponse,
    Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitRequest,
    Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitResponse,
    Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewRequest,
    Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewResponse,
    Layer3SourceDirectoryQualitativeAnalysisRequest,
    Layer3SourceDirectoryQualitativeAnalysisResponse,
    Layer3SourceDirectoryQualitativeAnalysisStatusResponse,
    Layer3SourceDirectoryReplacementPackageSetAuthorityRequest,
    Layer3SourceDirectoryVectorRetrievalRequest,
    Layer3SourceDirectoryVectorRetrievalResponse,
    Layer3SourceIntakeInventoryResponse,
    Layer3SourceIntakeMaterialPreviewResponse,
    Layer3SourceIntakeRecordResponse,
    _workbench_error_responses,
)


class ConnectorPromotionResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_b_session_id: UUID


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
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    limit: str = "50",
    source_family: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    max_chars: int = 4000,
    db: Session = Depends(get_db),
):
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBBundleMaterialBridgeRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBRuntimeMaterialBridgeRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_runtime_bridge.CandidateBRuntimeBridgeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/runtime/material-bridge/source-scan",
    response_model=Layer3SourceDirectoryIngestionResponse,
    status_code=201,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_runtime_material_bridge_source_scan(
    request: Request,
    payload: Layer3CandidateBRuntimeBridgeSourceScanRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_runtime_bridge.scan_candidate_b_runtime_bridge_curated_source_directory(
            db,
            payload.model_dump(exclude_unset=True),
        )
    except (
        layer3_candidate_b_runtime_bridge.CandidateBRuntimeBridgeError,
        layer3_source_directory_ingestion.SourceDirectoryIngestionError,
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/artifact-family/status",
    response_model=Layer3CandidateBArtifactFamilyStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_artifact_family_status(
    request: Request,
    payload: Layer3CandidateBArtifactFamilyStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBVisualLaneStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBRuntimeDownstreamProofRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBBundleDownstreamProofRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBDefaultPromotionOperatorStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_operator_status.candidate_b_default_promotion_operator_status(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_operator_status.CandidateBOperatorStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/run",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRunResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_run(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRunRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_run_service = layer3_candidate_b_full_corpus_operator_workflow_run
    try:
        with layer3_candidate_b_operator_workflow_access_policy.request_context(
            _candidate_b_policy_request_context(request),
        ):
            return workflow_run_service.candidate_b_full_corpus_operator_workflow_run(
                payload.model_dump(exclude_unset=True),
            )
    except workflow_run_service.CandidateBFullCorpusOperatorWorkflowRunError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except (
        layer3_candidate_b_operator_workflow_access_policy.CandidateBOperatorWorkflowAccessPolicyError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/status",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_status(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowStatusRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_status_service = layer3_candidate_b_full_corpus_operator_workflow_status
    try:
        with layer3_candidate_b_operator_workflow_access_policy.request_context(
            _candidate_b_policy_request_context(request),
        ):
            return workflow_status_service.candidate_b_full_corpus_operator_workflow_status(
                payload.model_dump(exclude_unset=True),
            )
    except workflow_status_service.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except (
        layer3_candidate_b_operator_workflow_access_policy.CandidateBOperatorWorkflowAccessPolicyError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowLifecycleResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_lifecycle_expire(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowLifecycleRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_lifecycle_service = layer3_candidate_b_full_corpus_operator_workflow_lifecycle
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_lifecycle_service.expire_candidate_b_full_corpus_operator_workflow_run(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_lifecycle_service.CandidateBFullCorpusOperatorWorkflowLifecycleError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowQueueStateResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_queue_state(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowQueueStateRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_queue_state_service = layer3_candidate_b_full_corpus_operator_workflow_queue_state
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_queue_state_service.record_candidate_b_full_corpus_operator_workflow_queue_state(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_queue_state_service.CandidateBFullCorpusOperatorWorkflowQueueStateError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowSchedulerLeaseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_scheduler_lease(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowSchedulerLeaseRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_scheduler_lease_service = layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_scheduler_lease_service.record_candidate_b_full_corpus_operator_workflow_scheduler_lease(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_scheduler_lease_service.CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowWorkerAttemptResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_worker_attempt(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowWorkerAttemptRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_worker_attempt_service = layer3_candidate_b_full_corpus_operator_workflow_worker_attempt
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_worker_attempt_service.record_candidate_b_full_corpus_operator_workflow_worker_attempt(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_worker_attempt_service.CandidateBFullCorpusOperatorWorkflowWorkerAttemptError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowProgressCheckpointResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_progress_checkpoint(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowProgressCheckpointRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_progress_checkpoint_service = layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_progress_checkpoint_service.record_candidate_b_full_corpus_operator_workflow_progress_checkpoint(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_progress_checkpoint_service.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowCompletionFailureResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_completion_failure(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowCompletionFailureRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_completion_failure_service = layer3_candidate_b_full_corpus_operator_workflow_completion_failure
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_completion_failure_service.record_candidate_b_full_corpus_operator_workflow_completion_failure(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_completion_failure_service.CandidateBFullCorpusOperatorWorkflowCompletionFailureError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRetryPolicyResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_retry_policy(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRetryPolicyRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_retry_policy_service = layer3_candidate_b_full_corpus_operator_workflow_retry_policy
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_retry_policy_service.record_candidate_b_full_corpus_operator_workflow_retry_policy(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_retry_policy_service.CandidateBFullCorpusOperatorWorkflowRetryPolicyError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRetryQueueStateResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_retry_queue_state(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRetryQueueStateRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_retry_queue_state_service = layer3_candidate_b_full_corpus_operator_workflow_retry_queue_state
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_retry_queue_state_service.record_candidate_b_full_corpus_operator_workflow_retry_queue_state(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_retry_queue_state_service.CandidateBFullCorpusOperatorWorkflowRetryQueueStateError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_retry_scheduler_lease_service = layer3_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_retry_scheduler_lease_service.record_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_retry_scheduler_lease_service.CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_retry_worker_attempt(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_retry_worker_attempt_service = layer3_candidate_b_full_corpus_operator_workflow_retry_worker_attempt
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_retry_worker_attempt_service.record_candidate_b_full_corpus_operator_workflow_retry_worker_attempt(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        workflow_retry_worker_attempt_service.CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_retry_progress_checkpoint_service = (
        layer3_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_retry_progress_checkpoint_service.record_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        workflow_retry_progress_checkpoint_service.CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_retry_completion_failure(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_retry_completion_failure_service = (
        layer3_candidate_b_full_corpus_operator_workflow_retry_completion_failure
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_retry_completion_failure_service.record_candidate_b_full_corpus_operator_workflow_retry_completion_failure(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        workflow_retry_completion_failure_service.CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowExecutionBoundaryResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_execution_boundary(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowExecutionBoundaryRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_execution_boundary_service = (
        layer3_candidate_b_full_corpus_operator_workflow_execution_boundary
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_execution_boundary_service.record_candidate_b_full_corpus_operator_workflow_execution_boundary(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_execution_boundary_service.CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowProcessExecutionResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_process_execution(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowProcessExecutionRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_process_execution_service = (
        layer3_candidate_b_full_corpus_operator_workflow_process_execution
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_process_execution_service.record_candidate_b_full_corpus_operator_workflow_process_execution(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except workflow_process_execution_service.CandidateBFullCorpusOperatorWorkflowProcessExecutionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowProcessCompletionResultResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_process_completion_result(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowProcessCompletionResultRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_process_completion_result_service = (
        layer3_candidate_b_full_corpus_operator_workflow_process_completion_result
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_process_completion_result_service.record_candidate_b_full_corpus_operator_workflow_process_completion_result(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        workflow_process_completion_result_service.CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_adopted_result_downstream_proof_service = (
        layer3_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_adopted_result_downstream_proof_service.record_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        workflow_adopted_result_downstream_proof_service.CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowCompletionMonitorResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_workflow_completion_monitor(
    payload: Layer3CandidateBFullCorpusOperatorWorkflowCompletionMonitorRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_completion_monitor_service = (
        layer3_candidate_b_full_corpus_operator_workflow_completion_monitor
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: workflow_completion_monitor_service.inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        workflow_completion_monitor_service.CandidateBFullCorpusOperatorWorkflowCompletionMonitorError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint",
    response_model=Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_operator_repeatability_checkpoint(
    payload: Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    repeatability_checkpoint_service = (
        layer3_candidate_b_full_corpus_operator_repeatability_checkpoint
    )
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: repeatability_checkpoint_service.record_candidate_b_full_corpus_operator_repeatability_checkpoint(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        repeatability_checkpoint_service.CandidateBFullCorpusOperatorRepeatabilityCheckpointError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial",
    response_model=Layer3CandidateBFullCorpusRepeatabilityRerunTrialResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_repeatability_rerun_trial(
    payload: Layer3CandidateBFullCorpusRepeatabilityRerunTrialRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    rerun_trial_service = layer3_candidate_b_full_corpus_repeatability_rerun_trial
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: rerun_trial_service.record_candidate_b_full_corpus_repeatability_rerun_trial(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except rerun_trial_service.CandidateBFullCorpusRepeatabilityRerunTrialError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint",
    response_model=Layer3CandidateBFullCorpusRepeatabilityAcceptanceCheckpointResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
    payload: Layer3CandidateBFullCorpusRepeatabilityAcceptanceCheckpointRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    acceptance_checkpoint_service = layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: acceptance_checkpoint_service.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except (
        acceptance_checkpoint_service.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout",
    response_model=Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_repeatability_acceptance_closeout(
    payload: Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    closeout_service = layer3_candidate_b_full_corpus_repeatability_acceptance_closeout
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: closeout_service.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except closeout_service.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout/status",
    response_model=Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_full_corpus_repeatability_acceptance_closeout_status(
    payload: Layer3CandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatusRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    closeout_service = layer3_candidate_b_full_corpus_repeatability_acceptance_closeout
    try:
        return _candidate_b_policy_json_or_error(
            request,
            lambda: closeout_service.candidate_b_full_corpus_repeatability_acceptance_closeout_status(
                payload.model_dump(exclude_unset=True),
            ),
        )
    except closeout_service.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/closure-evidence",
    response_model=Layer3CandidateBDefaultPromotionClosureEvidenceResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_default_promotion_closure_evidence(
    request: Request,
    payload: Layer3CandidateBDefaultPromotionClosureEvidenceRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_promotion_closure.candidate_b_default_promotion_closure_evidence(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_promotion_closure.CandidateBPromotionClosureError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.get(
    "/source/ingestion/candidate-b/full-corpus/operator-workflow/history",
    response_model=Layer3CandidateBFullCorpusOperatorWorkflowHistoryResponse,
    responses=_workbench_error_responses(404, 409),
)
def get_candidate_b_full_corpus_operator_workflow_history(
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    workflow_history_service = layer3_candidate_b_full_corpus_operator_workflow_history
    try:
        with layer3_candidate_b_operator_workflow_access_policy.request_context(
            _candidate_b_policy_request_context(request),
        ):
            return workflow_history_service.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history_service.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except (
        layer3_candidate_b_operator_workflow_access_policy.CandidateBOperatorWorkflowAccessPolicyError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/readiness-audit",
    response_model=Layer3CandidateBDefaultPromotionReadinessAuditResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_default_promotion_readiness_audit(
    request: Request,
    payload: Layer3CandidateBDefaultPromotionReadinessAuditRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_default_readiness.evaluate_candidate_b_default_promotion_readiness(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_default_readiness.CandidateBDefaultReadinessError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit",
    response_model=Layer3CandidateBBroaderEligibleCorpusScopeReadinessAuditResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_broader_eligible_corpus_scope_readiness_audit(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusScopeReadinessAuditRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_broader_scope_readiness.evaluate_candidate_b_broader_scope_readiness(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_broader_scope_readiness.CandidateBBroaderScopeReadinessError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeRuntimeResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_runtime(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeRuntimeRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_broader_scope_runtime.select_candidate_b_broader_scope_runtime(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_broader_scope_runtime.CandidateBBroaderScopeRuntimeError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_selector_use(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_broader_scope_selector_use.record_candidate_b_broader_scope_selector_use(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use/status",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_selector_use_status(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorUseStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_broader_scope_selector_use.inspect_candidate_b_broader_scope_selector_use_status(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-activation",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorActivationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_selector_activation(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeSelectorActivationRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_broader_scope_selector_use.record_candidate_b_broader_scope_selector_activation(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorActivationError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/activation-receipt/consume",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeActivationReceiptConsumptionResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeActivationReceiptConsumptionRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return (
            layer3_candidate_b_broader_scope_selector_use
            .record_candidate_b_broader_scope_activation_receipt_consumption(
                payload.model_dump(exclude_unset=True),
            )
        )
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeActivationConsumptionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorActivationError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return layer3_candidate_b_broader_scope_selector_use.record_candidate_b_broader_scope_consumption_receipt_use(
            payload.model_dump(exclude_unset=True),
        )
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeConsumptionReceiptUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeActivationConsumptionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorActivationError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use/status",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeConsumptionReceiptUseStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return (
            layer3_candidate_b_broader_scope_selector_use
            .inspect_candidate_b_broader_scope_consumption_receipt_use_status(
                payload.model_dump(exclude_unset=True),
            )
        )
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeConsumptionReceiptUseStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeConsumptionReceiptUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeActivationConsumptionError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorActivationError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseStatusError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())
    except layer3_candidate_b_broader_scope_selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/operator-repeatability/trial",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeOperatorRepeatabilityTrialResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeOperatorRepeatabilityTrialRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return (
            layer3_candidate_b_broader_scope_repeatability_trial
            .record_candidate_b_broader_scope_operator_repeatability_trial(
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_candidate_b_broader_scope_repeatability_trial
        .CandidateBBroaderScopeOperatorRepeatabilityTrialError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/promotion-readiness",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopePromotionReadinessResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_promotion_readiness(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopePromotionReadinessRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return (
            layer3_candidate_b_broader_scope_promotion_readiness
            .evaluate_candidate_b_broader_scope_default_promotion_readiness(
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_candidate_b_broader_scope_promotion_readiness
        .CandidateBBroaderScopePromotionReadinessError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/default-promotion",
    response_model=Layer3CandidateBBroaderEligibleCorpusDefaultScopeDefaultPromotionResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_candidate_b_broader_eligible_corpus_default_scope_default_promotion(
    request: Request,
    payload: Layer3CandidateBBroaderEligibleCorpusDefaultScopeDefaultPromotionRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        return (
            layer3_candidate_b_broader_scope_default_promotion
            .record_candidate_b_broader_scope_default_promotion(
                payload.model_dump(exclude_unset=True),
            )
        )
    except (
        layer3_candidate_b_broader_scope_default_promotion
        .CandidateBBroaderScopeDefaultPromotionError
    ) as exc:
        return JSONResponse(status_code=exc.http_status, content=exc.response_body())


@router.post(
    "/source/ingestion/candidate-b/default-promotion/final-proof",
    response_model=Layer3CandidateBDefaultPromotionFinalProofResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_candidate_b_default_promotion_final_proof(
    request: Request,
    payload: Layer3CandidateBDefaultPromotionFinalProofRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3CandidateBDefaultPromotionFinalProofStatusRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryIngestionScanRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryMaterialPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridAuthorityPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryVectorRetrievalRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextPacketRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisPackageReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisHandoffExportPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisInternalWebhookDispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisExternalExportDownloadDeliverRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlUseRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryHybridContextQualitativeAnalysisProviderPrivateSignedUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisPackageCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisPackageReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisPackageSupersessionPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryReplacementPackageSetAuthorityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryPackageSupersessionCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlUseRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryPackageSupersessionProviderPrivateSignedUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisHandoffExportPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3SourceDirectoryQualitativeAnalysisExternalExportDownloadDeliverRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3RawMixedCorpusSeedRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
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
    request: Request,
    payload: Layer3RawMixedCorpusMaterializeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_raw_mixed_materialization.materialize_raw_mixed_corpus(
            payload.model_dump(exclude_unset=True),
            db,
        )
    )


@router.post(
    "/source/connector/promotion/resolve",
    response_model=None,
)
def post_connector_promotion_resolve(
    request: Request,
    payload: ConnectorPromotionResolveRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    if not getattr(request.state, "b1b_prevalidation_authorized", False):
        if not layer3_connector_promotion.bridge_precondition_available():
            error_code = "connector_promotion_bridge_unavailable"
            return JSONResponse(
                status_code=layer3_connector_promotion.b1b_error_spec(error_code)[0],
                content=layer3_connector_promotion.b1b_error_body(error_code),
            )
    try:
        return layer3_connector_promotion.resolve_connector_promotion(
            db,
            gate_b_session_id=str(payload.gate_b_session_id),
        )
    except layer3_connector_promotion.ConnectorPromotionError as exc:
        return JSONResponse(
            status_code=layer3_connector_promotion.b1b_error_spec(exc.code)[0],
            content=layer3_connector_promotion.b1b_error_body(exc.code),
        )
