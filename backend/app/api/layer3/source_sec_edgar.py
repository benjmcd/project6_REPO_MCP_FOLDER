from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import (
    layer3_sec_edgar_arelle_value_reveal,
    layer3_sec_edgar_authority_envelope,
    layer3_sec_edgar_delivery_status_provenance,
    layer3_sec_edgar_downstream_proof,
    layer3_sec_edgar_downstream_status,
    layer3_sec_edgar_durable_delivery_archive,
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
    layer3_sec_edgar_live_downstream_proof,
    layer3_sec_edgar_live_downstream_status,
    layer3_sec_edgar_live_material_bridge,
    layer3_sec_edgar_live_repeatability_trial,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_material_bridge,
    layer3_sec_edgar_operator_inspection,
    layer3_sec_edgar_operator_product_surface,
    layer3_sec_edgar_real_company_corpus_validation,
    layer3_sec_edgar_real_filing_acquisition_connector,
    layer3_sec_edgar_real_filing_downstream_validation,
    layer3_sec_edgar_repeatability_trial,
    layer3_sec_edgar_source_acquisition,
)
from app.services import layer3_sec_xbrl_companyfacts_acquire_stage
from app.services import layer3_sec_xbrl_in_app_auth_policy
from app.api.layer3 import router
from app.api.layer3._shared import *  # noqa: F401,F403
from app.api.layer3 import (
    Layer3SecEdgarArelleValueRevealRequest,
    Layer3SecEdgarArelleValueRevealResponse,
    Layer3SecEdgarCompanyfactsAcquireStageRequest,
    Layer3SecEdgarCompanyfactsAcquireStageResponse,
    Layer3SecEdgarDeliveryStatusProvenanceRequest,
    Layer3SecEdgarDeliveryStatusProvenanceResponse,
    Layer3SecEdgarDurableDeliveryArchiveRequest,
    Layer3SecEdgarDurableDeliveryArchiveResponse,
    Layer3SecEdgarHtmlInlineXbrlDownstreamOperatorStatusRequest,
    Layer3SecEdgarHtmlInlineXbrlDownstreamOperatorStatusResponse,
    Layer3SecEdgarHtmlInlineXbrlDownstreamProofRequest,
    Layer3SecEdgarHtmlInlineXbrlDownstreamProofResponse,
    Layer3SecEdgarHtmlInlineXbrlFactAuthorityRequest,
    Layer3SecEdgarHtmlInlineXbrlFactAuthorityResponse,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeRequest,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeResponse,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialRequest,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialResponse,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusRequest,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusResponse,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamProofRequest,
    Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamProofResponse,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareRequest,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareResponse,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitRequest,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitResponse,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewRequest,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewResponse,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitRequest,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitResponse,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductRequest,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductResponse,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationRequest,
    Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationResponse,
    Layer3SecEdgarHtmlInlineXbrlMaterialBridgeRequest,
    Layer3SecEdgarHtmlInlineXbrlMaterialBridgeResponse,
    Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserRequest,
    Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserResponse,
    Layer3SecEdgarOperatorInspectionRequest,
    Layer3SecEdgarOperatorInspectionResponse,
    Layer3SecEdgarOperatorProductSurfaceRequest,
    Layer3SecEdgarOperatorProductSurfaceResponse,
    Layer3SecEdgarRealCompanyCorpusValidationRequest,
    Layer3SecEdgarRealCompanyCorpusValidationResponse,
    Layer3SecEdgarRealFilingAcquisitionConnectorRequest,
    Layer3SecEdgarRealFilingAcquisitionConnectorResponse,
    Layer3SecEdgarRealFilingDownstreamValidationRequest,
    Layer3SecEdgarRealFilingDownstreamValidationResponse,
    Layer3SecEdgarTextTableAuthorityEnvelopeRequest,
    Layer3SecEdgarTextTableAuthorityEnvelopeResponse,
    Layer3SecEdgarTextTableDownstreamOperatorRepeatabilityTrialRequest,
    Layer3SecEdgarTextTableDownstreamOperatorRepeatabilityTrialResponse,
    Layer3SecEdgarTextTableDownstreamOperatorStatusRequest,
    Layer3SecEdgarTextTableDownstreamOperatorStatusResponse,
    Layer3SecEdgarTextTableDownstreamProofRequest,
    Layer3SecEdgarTextTableDownstreamProofResponse,
    Layer3SecEdgarTextTableLiveSourceArtifactAcquireRequest,
    Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorRepeatabilityTrialRequest,
    Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorRepeatabilityTrialResponse,
    Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorStatusRequest,
    Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorStatusResponse,
    Layer3SecEdgarTextTableLiveSourceArtifactDownstreamProofRequest,
    Layer3SecEdgarTextTableLiveSourceArtifactDownstreamProofResponse,
    Layer3SecEdgarTextTableLiveSourceArtifactMaterialAuthorityBridgeRequest,
    Layer3SecEdgarTextTableLiveSourceArtifactMaterialAuthorityBridgeResponse,
    Layer3SecEdgarTextTableLiveSourceArtifactResponse,
    Layer3SecEdgarTextTableMaterialAuthorityBridgeRequest,
    Layer3SecEdgarTextTableMaterialAuthorityBridgeResponse,
    Layer3SecEdgarTextTableSourceAcquisitionAuthorityRequest,
    Layer3SecEdgarTextTableSourceAcquisitionAuthorityResponse,
    _workbench_error_responses,
)


@router.post(
    "/source/sec-edgar/text-table/authority-envelope/validate",
    response_model=Layer3SecEdgarTextTableAuthorityEnvelopeResponse,
    responses=_workbench_error_responses(400),
)
def post_sec_edgar_text_table_authority_envelope_validate(
    payload: Layer3SecEdgarTextTableAuthorityEnvelopeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/material-authority/bridge",
    response_model=Layer3SecEdgarTextTableMaterialAuthorityBridgeResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_sec_edgar_text_table_material_authority_bridge(
    payload: Layer3SecEdgarTextTableMaterialAuthorityBridgeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_material_bridge.prepare_sec_edgar_text_table_material_authority_bridge(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/live-source-artifact/material-authority/bridge",
    response_model=Layer3SecEdgarTextTableLiveSourceArtifactMaterialAuthorityBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_text_table_live_source_artifact_material_authority_bridge(
    payload: Layer3SecEdgarTextTableLiveSourceArtifactMaterialAuthorityBridgeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_live_material_bridge.prepare_sec_edgar_text_table_live_source_artifact_material_authority_bridge(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/source-acquisition/authority",
    response_model=Layer3SecEdgarTextTableSourceAcquisitionAuthorityResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_sec_edgar_text_table_source_acquisition_authority(
    payload: Layer3SecEdgarTextTableSourceAcquisitionAuthorityRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_source_acquisition.record_sec_edgar_text_table_source_acquisition_authority(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/live-source-artifact/acquire",
    response_model=Layer3SecEdgarTextTableLiveSourceArtifactResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_sec_edgar_text_table_live_source_artifact_acquire(
    payload: Layer3SecEdgarTextTableLiveSourceArtifactAcquireRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_live_source_artifact.acquire_sec_edgar_text_table_live_source_artifact(
            payload.model_dump(exclude_none=True),
        )
    )


@router.post(
    "/source/sec-edgar/companyfacts/acquire-and-stage",
    response_model=Layer3SecEdgarCompanyfactsAcquireStageResponse,
    responses=_workbench_error_responses(400, 409),
)
def post_sec_edgar_companyfacts_acquire_and_stage(
    payload: Layer3SecEdgarCompanyfactsAcquireStageRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error_with_companyfacts_stage(
        lambda: layer3_sec_xbrl_companyfacts_acquire_stage.acquire_and_stage_companyfacts(
            client_request_id=payload.client_request_id,
            cik=payload.cik,
            connector_receipt_hash=payload.connector_receipt_hash,
            operator_confirmation=payload.operator_confirmation,
        )
    )


@router.get(
    "/source/sec-edgar/text-table/live-source-artifact/status/{live_source_artifact_receipt_id}",
    response_model=Layer3SecEdgarTextTableLiveSourceArtifactResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_text_table_live_source_artifact_status(
    live_source_artifact_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_live_source_artifact.inspect_sec_edgar_text_table_live_source_artifact_status(
            live_source_artifact_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-filing/acquisition/connector",
    response_model=Layer3SecEdgarRealFilingAcquisitionConnectorResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_real_filing_acquisition_connector(
    payload: Layer3SecEdgarRealFilingAcquisitionConnectorRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_real_filing_acquisition_connector.acquire_sec_edgar_real_filing_validation_corpus(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/real-filing/acquisition/connector/status/{sec_edgar_real_filing_acquisition_connector_receipt_id}",
    response_model=Layer3SecEdgarRealFilingAcquisitionConnectorResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_real_filing_acquisition_connector_status(
    sec_edgar_real_filing_acquisition_connector_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_real_filing_acquisition_connector.inspect_sec_edgar_real_filing_acquisition_connector_status(
            sec_edgar_real_filing_acquisition_connector_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-filing/acquisition/connector/downstream-validation",
    response_model=Layer3SecEdgarRealFilingDownstreamValidationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_real_filing_downstream_validation(
    payload: Layer3SecEdgarRealFilingDownstreamValidationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_real_filing_downstream_validation.record_sec_edgar_real_filing_connector_downstream_validation(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/real-filing/acquisition/connector/downstream-validation/status/{sec_edgar_real_filing_downstream_validation_receipt_id}",
    response_model=Layer3SecEdgarRealFilingDownstreamValidationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_real_filing_downstream_validation_status(
    sec_edgar_real_filing_downstream_validation_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_real_filing_downstream_validation.inspect_sec_edgar_real_filing_downstream_validation_status(
            sec_edgar_real_filing_downstream_validation_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-company-corpus/validation",
    response_model=Layer3SecEdgarRealCompanyCorpusValidationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_real_company_corpus_validation(
    payload: Layer3SecEdgarRealCompanyCorpusValidationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
        owner_stamp = layer3_sec_xbrl_in_app_auth_policy.derive_sec_xbrl_evidence_owner(
            dict(request.headers)
        )
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_real_company_corpus_validation.validate_sec_edgar_real_company_corpus_product_path(
            payload.model_dump(exclude_none=True),
            db,
            evidence_owner=owner_stamp,
        )
    )


@router.get(
    "/source/sec-edgar/real-company-corpus/validation/status/{sec_edgar_real_company_corpus_validation_receipt_id}",
    response_model=Layer3SecEdgarRealCompanyCorpusValidationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_real_company_corpus_validation_status(
    sec_edgar_real_company_corpus_validation_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_real_company_corpus_validation.inspect_sec_edgar_real_company_corpus_validation_status(
            sec_edgar_real_company_corpus_validation_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-company-corpus/delivery-status/provenance",
    response_model=Layer3SecEdgarDeliveryStatusProvenanceResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_delivery_status_provenance(
    payload: Layer3SecEdgarDeliveryStatusProvenanceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_delivery_status_provenance.inspect_sec_edgar_real_company_delivery_status_provenance(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/real-company-corpus/delivery-status/provenance/status/{sec_edgar_delivery_status_provenance_receipt_id}",
    response_model=Layer3SecEdgarDeliveryStatusProvenanceResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_delivery_status_provenance_status(
    sec_edgar_delivery_status_provenance_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_delivery_status_provenance.inspect_sec_edgar_delivery_status_provenance_status(
            sec_edgar_delivery_status_provenance_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-company-corpus/operator-inspection",
    response_model=Layer3SecEdgarOperatorInspectionResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_operator_inspection(
    payload: Layer3SecEdgarOperatorInspectionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_operator_inspection.inspect_sec_edgar_real_company_operator_surface(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/real-company-corpus/operator-inspection/status/{sec_edgar_operator_inspection_receipt_id}",
    response_model=Layer3SecEdgarOperatorInspectionResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_operator_inspection_status(
    sec_edgar_operator_inspection_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_operator_inspection.inspect_sec_edgar_operator_inspection_status(
            sec_edgar_operator_inspection_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-company-corpus/operator-product-surface",
    response_model=Layer3SecEdgarOperatorProductSurfaceResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_operator_product_surface(
    payload: Layer3SecEdgarOperatorProductSurfaceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_operator_product_surface.render_sec_edgar_operator_product_surface(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/real-company-corpus/operator-product-surface/status/{sec_edgar_operator_product_surface_receipt_id}",
    response_model=Layer3SecEdgarOperatorProductSurfaceResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_operator_product_surface_status(
    sec_edgar_operator_product_surface_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_operator_product_surface.inspect_sec_edgar_operator_product_surface_status(
            sec_edgar_operator_product_surface_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-company-corpus/operator-value-reveal",
    response_model=Layer3SecEdgarArelleValueRevealResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_arelle_value_reveal(
    payload: Layer3SecEdgarArelleValueRevealRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_arelle_value_reveal.reveal_sec_edgar_arelle_values(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/real-company-corpus/operator-value-reveal/status/{reveal_receipt_id}",
    response_model=Layer3SecEdgarArelleValueRevealResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_arelle_value_reveal_status(
    reveal_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_arelle_value_reveal.inspect_sec_edgar_arelle_value_reveal_status(
            reveal_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/real-company-corpus/durable-delivery/archive",
    response_model=Layer3SecEdgarDurableDeliveryArchiveResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_durable_delivery_archive(
    payload: Layer3SecEdgarDurableDeliveryArchiveRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_durable_delivery_archive.archive_sec_edgar_durable_delivery(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/real-company-corpus/durable-delivery/archive/status/{sec_edgar_durable_delivery_archive_receipt_id}",
    response_model=Layer3SecEdgarDurableDeliveryArchiveResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_durable_delivery_archive_status(
    sec_edgar_durable_delivery_archive_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_durable_delivery_archive.inspect_sec_edgar_durable_delivery_archive_status(
            sec_edgar_durable_delivery_archive_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/source-family/parser",
    response_model=Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_source_family_parser(
    payload: Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/source-family/parser/status/{sec_edgar_html_inline_xbrl_parser_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlSourceFamilyParserResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_source_family_parser_status(
    sec_edgar_html_inline_xbrl_parser_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_parser.inspect_sec_edgar_html_inline_xbrl_source_family_parser_status(
            sec_edgar_html_inline_xbrl_parser_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactAuthorityResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_authority(
    payload: Layer3SecEdgarHtmlInlineXbrlFactAuthorityRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_authority.derive_sec_edgar_html_inline_xbrl_fact_authority(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/status/{sec_edgar_html_inline_xbrl_fact_authority_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactAuthorityResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_authority_status(
    sec_edgar_html_inline_xbrl_fact_authority_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_authority.inspect_sec_edgar_html_inline_xbrl_fact_authority_status(
            sec_edgar_html_inline_xbrl_fact_authority_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_material_bridge(
    payload: Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/status/{sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_material_bridge_status(
    sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.inspect_sec_edgar_html_inline_xbrl_fact_material_bridge_status(
            sec_edgar_html_inline_xbrl_fact_material_bridge_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_statement_classification(
    payload: Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/status/{statement_classification_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_statement_classification_status(
    statement_classification_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.inspect_sec_edgar_html_inline_xbrl_fact_statement_classification_status(
            statement_classification_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product(
    payload: Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.build_sec_edgar_html_inline_xbrl_statement_candidate_product_evidence(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/status/{downstream_product_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_status(
    downstream_product_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_status(
            downstream_product_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package-review/preview",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_preview(
    payload: Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review.preview_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package-review/preview/status/{package_review_preview_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewPreviewResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_preview_status(
    package_review_preview_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review.inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_status(
            package_review_preview_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package/commit",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction_commit(
    payload: Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction.commit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package/commit/status/{package_construction_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageConstructionCommitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction_status(
    package_construction_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction.inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_status(
            package_construction_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package-review/submit",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit(
    payload: Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit.submit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/package-review/submit/status/{package_review_submit_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductPackageReviewSubmitResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit_status(
    package_review_submit_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit.inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_status(
            package_review_submit_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/handoff-export/prepare",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare(
    payload: Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareRequest,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare.prepare_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export(
            payload.model_dump(exclude_none=True),
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/statement-classification/downstream-product/handoff-export/prepare/status/{handoff_export_prepare_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactStatementClassificationDownstreamProductHandoffExportPrepareResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare_status(
    handoff_export_prepare_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare.inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepare_status(
            handoff_export_prepare_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_material_downstream_proof(
    payload: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamProofRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_proof.record_sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_proof(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/status",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusResponse,
    responses=_workbench_error_responses(400),
)
def post_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status(
    payload: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status.inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/fact-authority/material-bridge/downstream-proof/operator-repeatability/trial",
    response_model=Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial(
    payload: Layer3SecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorRepeatabilityTrialRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_repeatability_trial.record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/material-authority/bridge",
    response_model=Layer3SecEdgarHtmlInlineXbrlMaterialBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_material_bridge(
    payload: Layer3SecEdgarHtmlInlineXbrlMaterialBridgeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_material_bridge.prepare_sec_edgar_html_inline_xbrl_material_bridge(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.get(
    "/source/sec-edgar/html-inline-xbrl/material-authority/bridge/status/{sec_edgar_html_inline_xbrl_material_bridge_receipt_id}",
    response_model=Layer3SecEdgarHtmlInlineXbrlMaterialBridgeResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_sec_edgar_html_inline_xbrl_material_bridge_status(
    sec_edgar_html_inline_xbrl_material_bridge_receipt_id: str,
    request: Request,
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_material_bridge.inspect_sec_edgar_html_inline_xbrl_material_bridge_status(
            sec_edgar_html_inline_xbrl_material_bridge_receipt_id,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/downstream-proof",
    response_model=Layer3SecEdgarHtmlInlineXbrlDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_html_inline_xbrl_downstream_proof(
    payload: Layer3SecEdgarHtmlInlineXbrlDownstreamProofRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_downstream_proof.record_sec_edgar_html_inline_xbrl_downstream_layer3_proof(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/downstream-proof",
    response_model=Layer3SecEdgarTextTableDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_text_table_downstream_proof(
    payload: Layer3SecEdgarTextTableDownstreamProofRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_downstream_proof.record_sec_edgar_text_table_downstream_layer3_proof(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/live-source-artifact/downstream-proof",
    response_model=Layer3SecEdgarTextTableLiveSourceArtifactDownstreamProofResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_text_table_live_source_artifact_downstream_proof(
    payload: Layer3SecEdgarTextTableLiveSourceArtifactDownstreamProofRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_live_downstream_proof.record_sec_edgar_text_table_live_source_artifact_downstream_layer3_proof(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/html-inline-xbrl/downstream-proof/status",
    response_model=Layer3SecEdgarHtmlInlineXbrlDownstreamOperatorStatusResponse,
    responses=_workbench_error_responses(400),
)
def post_sec_edgar_html_inline_xbrl_downstream_operator_status(
    payload: Layer3SecEdgarHtmlInlineXbrlDownstreamOperatorStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_html_inline_xbrl_downstream_status.inspect_sec_edgar_html_inline_xbrl_downstream_operator_status(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/live-source-artifact/downstream-proof/status",
    response_model=Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorStatusResponse,
    responses=_workbench_error_responses(400),
)
def post_sec_edgar_text_table_live_source_artifact_downstream_operator_status(
    payload: Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_live_downstream_status.inspect_sec_edgar_text_table_live_source_artifact_downstream_operator_status(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/live-source-artifact/downstream/operator-repeatability/trial",
    response_model=Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorRepeatabilityTrialResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial(
    payload: Layer3SecEdgarTextTableLiveSourceArtifactDownstreamOperatorRepeatabilityTrialRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_live_repeatability_trial.record_sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/downstream-proof/status",
    response_model=Layer3SecEdgarTextTableDownstreamOperatorStatusResponse,
    responses=_workbench_error_responses(400),
)
def post_sec_edgar_text_table_downstream_operator_status(
    payload: Layer3SecEdgarTextTableDownstreamOperatorStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_downstream_status.inspect_sec_edgar_text_table_downstream_layer3_operator_status(
            payload.model_dump(exclude_none=True),
            db,
        )
    )


@router.post(
    "/source/sec-edgar/text-table/downstream/operator-repeatability/trial",
    response_model=Layer3SecEdgarTextTableDownstreamOperatorRepeatabilityTrialResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def post_sec_edgar_text_table_downstream_operator_repeatability_trial(
    payload: Layer3SecEdgarTextTableDownstreamOperatorRepeatabilityTrialRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except layer3_sec_xbrl_in_app_auth_policy.SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_sec_edgar_repeatability_trial.record_sec_edgar_text_table_downstream_operator_repeatability_trial(
            payload.model_dump(exclude_none=True),
            db,
        )
    )
