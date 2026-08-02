from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app._version import BUILD_INFO
from app.api.deps import get_db
from app.core.config import settings
from app.models import AnalysisRun, AnnotationWindow, ConnectorRun, ConnectorRunTarget, Dataset, DatasetVersion, VariableProfile
from app.schemas.api import (
    AnalysisRecommendationOut,
    AnalysisRecommendationRequest,
    AnalysisRunIn,
    AnalysisRunOut,
    AnnotationWindowIn,
    AnnotationWindowOut,
    BlsConnectorRunIn,
    CftcCotConnectorRunIn,
    ConnectorEgressArmingIn,
    ConnectorEgressExecuteIn,
    ConnectorRunOut,
    ConnectorRunEventsPageOut,
    ConnectorRunContentUnitsPageOut,
    ConnectorRunReportsOut,
    ConnectorRunSubmitOut,
    ConnectorRunTargetsPageOut,
    DatasetDetailOut,
    DatasetOut,
    NrcApsContentSearchIn,
    NrcApsContentSearchOut,
    NrcApsEvidenceCitationPackCreateIn,
    NrcApsEvidenceCitationPackOut,
    NrcApsEvidenceReportCreateIn,
    NrcApsEvidenceReportExportCreateIn,
    NrcApsContextPacketCreateIn,
    NrcApsContextPacketOut,
    NrcApsContextDossierCreateIn,
    NrcApsContextDossierOut,
    NrcApsDeterministicChallengeArtifactCreateIn,
    NrcApsDeterministicChallengeArtifactOut,
    NrcApsDeterministicChallengeReviewPacketCreateIn,
    NrcApsDeterministicChallengeReviewPacketOut,
    NrcApsDeterministicInsightArtifactCreateIn,
    NrcApsDeterministicInsightArtifactOut,
    NrcApsEvidenceReportExportPackageCreateIn,
    NrcApsEvidenceReportExportPackageOut,
    NrcApsEvidenceReportExportOut,
    NrcApsEvidenceReportOut,
    NrcApsEvidenceBundleAssembleIn,
    NrcApsEvidenceBundleOut,
    NrcAdamsApsConnectorRunIn,
    OecdSdmxConnectorRunIn,
    ProfileRequest,
    SenateLdaConnectorRunIn,
    ScienceBaseConnectorRunIn,
    ScienceBaseMcsConnectorRunIn,
    TransformRecommendationOut,
    TransformationApplyOut,
    TransformationApplyRequest,
    UploadResponse,
    VariableProfileOut,
    WorldBankConnectorRunIn,
)
from app.services.analysis import recommend_analysis, run_analysis
from app.services.connectors_sciencebase import (
    RunNotFoundError,
    SubmissionConflictError,
    execute_connector_run,
    request_cancel_run,
    request_resume_run,
    list_connector_run_events,
    serialize_connector_run_reports,
    serialize_connector_run,
    serialize_connector_target,
    submit_connector_run,
)
from app.services.connectors_nrc_adams import execute_nrc_adams_run, submit_nrc_adams_run
from app.services.connectors_senate_lda import execute_senate_lda_run, submit_senate_lda_run
from app.services.connectors_worldbank import execute_worldbank_run, submit_worldbank_run
from app.services.connectors_cftc_cot import execute_cftc_cot_run, submit_cftc_cot_run
from app.services.connectors_bls import execute_bls_run, submit_bls_run
from app.services.connectors_oecd import OecdSdmxSchemaValidationError, execute_oecd_sdmx_run, submit_oecd_sdmx_run
from app.services import aps_retrieval_plane_read
from app.services import connector_egress_arming
from app.services import connector_egress_authorization
from app.services import nrc_aps_content_index
from app.services import nrc_aps_context_dossier
from app.services import nrc_aps_context_packet
from app.services import nrc_aps_deterministic_challenge_artifact
from app.services import nrc_aps_deterministic_challenge_review_packet
from app.services import nrc_aps_deterministic_insight_artifact
from app.services import nrc_aps_evidence_citation_pack
from app.services import nrc_aps_evidence_report_export_package
from app.services import nrc_aps_evidence_report_export
from app.services import nrc_aps_evidence_report
from app.services import nrc_aps_evidence_bundle
from app.services.ingest import upload_csv_to_dataset
from app.services.profiling import profile_dataset_version
from app.services.transforms import apply_transformations, recommend_transformations
from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    SecXbrlInAppAuthPolicyError,
    route_level_operator_authorization_required,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response
from app.api import market_data_integration
from app.api import market_data_validation
from app.api import market_insight_ai
from app.api import layer3
from app.api import review_nrc_aps

api_router = APIRouter()
api_router.include_router(review_nrc_aps.router, prefix="/review/nrc-aps", tags=["review_nrc_aps"])
api_router.include_router(layer3.router, prefix="/layer3", tags=["layer3_workbench"])
api_router.include_router(market_data_integration.router)
api_router.include_router(market_data_validation.router)
api_router.include_router(market_insight_ai.router)
api_router.include_router(market_data_integration.alias_router)
api_router.include_router(market_data_validation.alias_router)
api_router.include_router(market_insight_ai.alias_router)


# ---------------------------------------------------------------------------
# Module-local auth helpers
# Intentionally NOT imported from app.api.layer3._shared to keep this module
# independent of the layer3 package internal structure.
# ---------------------------------------------------------------------------


def _route_level_operator_identity(request: Request, *, access: str = "write") -> None:
    """Gate: raises SecXbrlInAppAuthPolicyError if operator identity is not admitted."""
    route_level_operator_authorization_required(
        {str(k): str(v) for k, v in request.headers.items()},
        access=access,
    )


def _legacy_api_auth_policy_error_response(exc: SecXbrlInAppAuthPolicyError) -> JSONResponse:
    """Return a governed error envelope matching the layer3 workbench error shape."""
    return JSONResponse(
        status_code=exc.http_status,
        content=workbench_error_response(
            Layer3WorkbenchError(
                error_code=exc.code,
                message=exc.message,
                status="blocked",
                http_status=exc.http_status,
                blocked_fields=[
                    str(f)
                    for f in exc.details.get(
                        "blocked_fields",
                        exc.details.get("mismatched_fields", []),
                    )
                ],
                next_allowed_actions=["inspect_operator_identity_projection"],
            )
        ),
    )


# ---------------------------------------------------------------------------
# Connector run helpers
# ---------------------------------------------------------------------------


def _connector_executor(connector_key: str):
    executors = {
        "sciencebase_public": execute_connector_run,
        "sciencebase_mcs": execute_connector_run,
        "nrc_adams_aps": execute_nrc_adams_run,
        "senate_lda": execute_senate_lda_run,
        "worldbank_indicators": execute_worldbank_run,
        "cftc_cot": execute_cftc_cot_run,
        "bls_v1": execute_bls_run,
        "oecd_sdmx": execute_oecd_sdmx_run,
    }
    return executors.get(connector_key)


def _enqueue_connector_run(background_tasks: BackgroundTasks, connector_key: str, connector_run_id: str) -> None:
    executor = _connector_executor(connector_key)
    if executor is None:
        raise HTTPException(status_code=409, detail=f"connector executor not configured for {connector_key}")
    background_tasks.add_task(executor, connector_run_id)


def _egress_service_http_error(exc: Exception) -> HTTPException:
    code = str(getattr(exc, "code", "connector_egress_request_rejected"))
    message = str(getattr(exc, "message", str(exc)))
    status_code = int(
        getattr(exc, "http_status", getattr(exc, "status_code", 409))
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _safe_egress_arming_projection(
    run: ConnectorRun,
    *,
    created: bool,
) -> ConnectorRunSubmitOut:
    return ConnectorRunSubmitOut.model_validate(
        {
            "connector_run_id": run.connector_run_id,
            "status": run.status,
            "created": created,
            "submitted_at": run.submitted_at,
            "poll_url": (
                f"/api/v1/connectors/egress-armings/{run.connector_run_id}"
            ),
            "submission_idempotency_key": None,
            "request_fingerprint": run.request_fingerprint,
        }
    )


def _configured_code_revision() -> str:
    return str(BUILD_INFO.get("source_sha") or "").strip().lower()


def _resolve_egress_authority(
    *,
    connector_key: str,
    campaign_id: str,
    campaign_fingerprint: str,
    grant_sha256: str,
    now: datetime,
):
    code_revision = _configured_code_revision()
    verified_campaign = (
        connector_egress_authorization
        .resolve_current_dual_live_campaign_definition(
            expected_campaign_id=campaign_id,
            expected_campaign_fingerprint=campaign_fingerprint,
            code_revision=code_revision,
            now=now,
        )
    )
    verified_grant = (
        connector_egress_authorization.resolve_current_connector_egress_grant(
            verified_campaign=verified_campaign,
            connector_key=connector_key,
            expected_grant_sha256=grant_sha256,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
            code_revision=code_revision,
            now=now,
        )
    )
    return verified_grant


def _strict_arming_envelope_for_route(run: ConnectorRun) -> dict:
    config = run.request_config_json
    raw_envelope = (
        config.get("connector_egress_arming")
        if isinstance(config, dict)
        else None
    )
    envelope = dict(raw_envelope) if isinstance(raw_envelope, dict) else {}
    if not connector_egress_arming.is_strict_egress_run(run):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connector_reserved_egress_provenance_malformed",
                "message": (
                    "reserved egress provenance is not one valid strict arming"
                ),
            },
        )
    return envelope


def _reject_strict_generic_read(run: ConnectorRun) -> None:
    if connector_egress_arming.has_reserved_egress_provenance(run):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connector_strict_generic_get_forbidden",
                "message": (
                    "strict egress runs are available only through the "
                    "protected egress-arming projection"
                ),
            },
        )


def _strict_egress_executor(run: ConnectorRun):
    if not connector_egress_arming.is_strict_egress_run(run):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connector_reserved_egress_provenance_malformed",
                "message": (
                    "reserved egress provenance cannot select an executor"
                ),
            },
        )
    executors = {
        "sciencebase_mcs": execute_connector_run,
        "nrc_adams_aps": execute_nrc_adams_run,
    }
    executor = executors.get(run.connector_key)
    if executor is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connector_strict_executor_not_configured",
                "message": "strict egress connector has no admitted executor",
            },
        )
    return executor


def _exclusive_dual_live_proof_mode() -> bool:
    return bool(
        settings.connector_live_egress_enabled
        and settings.connector_live_egress_exclusive_proof_mode
    )


def _reject_generic_connector_during_exclusive_proof(
    *,
    connector_key: str,
) -> None:
    if (
        _exclusive_dual_live_proof_mode()
        and connector_key
        in {"sciencebase_public", "sciencebase_mcs", "nrc_adams_aps"}
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connector_generic_route_blocked_by_exclusive_proof",
                "message": (
                    "generic ScienceBase/NRC connector routes are disabled "
                    "during the exclusive dual-live proof"
                ),
            },
        )


# ---------------------------------------------------------------------------
# Routes — all gated with _route_level_operator_identity
# ---------------------------------------------------------------------------


@api_router.post('/sources/upload', response_model=UploadResponse)
def upload_source(request: Request, file: UploadFile = File(...), name: str = Form(...), description: str | None = Form(None), domain_pack: str | None = Form(None), primary_time_column: str | None = Form(None), db: Session = Depends(get_db)) -> UploadResponse:
    try:
        _route_level_operator_identity(request, access="write")
        return UploadResponse.model_validate(upload_csv_to_dataset(db, file, name, description, domain_pack, primary_time_column))
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get('/datasets', response_model=list[DatasetOut])
def list_datasets(request: Request, db: Session = Depends(get_db)) -> list[DatasetOut]:
    try:
        _route_level_operator_identity(request, access="read")
        datasets = db.query(Dataset).all()
        return [DatasetOut.model_validate({'dataset_id': item.dataset_id, 'name': item.name, 'description': item.description, 'time_column': item.time_column, 'frequency_hint': item.frequency_hint}) for item in datasets]
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get('/datasets/{dataset_id}', response_model=DatasetDetailOut)
def get_dataset(dataset_id: str, request: Request, db: Session = Depends(get_db)) -> DatasetDetailOut:
    try:
        _route_level_operator_identity(request, access="read")
        dataset = db.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail='dataset not found')
        versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).all()
        return DatasetDetailOut.model_validate(
            {
                'dataset_id': dataset.dataset_id,
                'name': dataset.name,
                'description': dataset.description,
                'time_column': dataset.time_column,
                'frequency_hint': dataset.frequency_hint,
                'versions': [
                    {
                        'dataset_version_id': v.dataset_version_id,
                        'version_label': v.version_label,
                        'version_type': v.version_type,
                        'row_count': v.row_count,
                        'source_row_count': v.source_row_count,
                        'dropped_row_count': v.dropped_row_count,
                        'content_hash': v.content_hash,
                    }
                    for v in versions
                ],
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post('/datasets/{dataset_id}/versions/{dataset_version_id}/profile', response_model=list[VariableProfileOut])
def profile_version(dataset_id: str, dataset_version_id: str, payload: ProfileRequest, request: Request, db: Session = Depends(get_db)) -> list[VariableProfileOut]:
    try:
        _route_level_operator_identity(request, access="write")
        dataset = db.get(Dataset, dataset_id)
        version = db.get(DatasetVersion, dataset_version_id)
        if not dataset or not version or version.dataset_id != dataset.dataset_id:
            raise HTTPException(status_code=404, detail='dataset or version not found')
        profiles = profile_dataset_version(db, dataset_version_id, detect_seasonality=payload.detect_seasonality, detect_stationarity=payload.detect_stationarity)
        return [VariableProfileOut.model_validate({'variable_profile_id': p.variable_profile_id, 'variable_id': p.variable_id, 'missingness_rate': p.missingness_rate, 'mean_value': p.mean_value, 'median_value': p.median_value, 'min_value': p.min_value, 'max_value': p.max_value, 'std_dev': p.std_dev, 'skewness': p.skewness, 'outlier_fraction': p.outlier_fraction, 'negative_values_flag': p.negative_values_flag, 'zero_values_flag': p.zero_values_flag, 'bounded_flag': p.bounded_flag, 'seasonality_flag': p.seasonality_flag, 'stationarity_hint': p.stationarity_hint, 'summary_json': p.summary_json}) for p in profiles]
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post('/datasets/{dataset_id}/versions/{dataset_version_id}/transformations/recommend', response_model=list[TransformRecommendationOut])
def recommend_transforms_route(dataset_id: str, dataset_version_id: str, request: Request, db: Session = Depends(get_db)) -> list[TransformRecommendationOut]:
    try:
        _route_level_operator_identity(request, access="write")
        dataset = db.get(Dataset, dataset_id)
        version = db.get(DatasetVersion, dataset_version_id)
        if not dataset or not version or version.dataset_id != dataset.dataset_id:
            raise HTTPException(status_code=404, detail='dataset or version not found')
        profile_count = db.query(VariableProfile).filter(VariableProfile.dataset_version_id == dataset_version_id).count()
        if profile_count == 0:
            profile_dataset_version(db, dataset_version_id)
        return [TransformRecommendationOut.model_validate(item) for item in recommend_transformations(db, dataset_version_id)]
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post('/datasets/{dataset_id}/versions/{dataset_version_id}/transformations/apply', response_model=TransformationApplyOut)
def apply_transforms_route(dataset_id: str, dataset_version_id: str, payload: TransformationApplyRequest, request: Request, db: Session = Depends(get_db)) -> TransformationApplyOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            return TransformationApplyOut.model_validate(apply_transformations(db, dataset_id, dataset_version_id, payload.version_label, payload.rationale, [item.model_dump() for item in payload.steps]))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post('/datasets/{dataset_id}/versions/{dataset_version_id}/annotations', response_model=AnnotationWindowOut)
def create_annotation(dataset_id: str, dataset_version_id: str, payload: AnnotationWindowIn, request: Request, db: Session = Depends(get_db)) -> AnnotationWindowOut:
    try:
        _route_level_operator_identity(request, access="write")
        dataset = db.get(Dataset, dataset_id)
        version = db.get(DatasetVersion, dataset_version_id)
        if not dataset or not version or version.dataset_id != dataset.dataset_id:
            raise HTTPException(status_code=404, detail='dataset or version not found')
        annotation = AnnotationWindow(dataset_version_id=dataset_version_id, label=payload.label, annotation_type=payload.annotation_type, start_time=datetime.fromisoformat(payload.start_time), end_time=datetime.fromisoformat(payload.end_time), notes=payload.notes)
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
        return AnnotationWindowOut.model_validate({'annotation_window_id': annotation.annotation_window_id, 'label': annotation.label, 'annotation_type': annotation.annotation_type, 'start_time': annotation.start_time, 'end_time': annotation.end_time, 'notes': annotation.notes})
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get('/datasets/{dataset_id}/versions/{dataset_version_id}/annotations', response_model=list[AnnotationWindowOut])
def list_annotations(dataset_id: str, dataset_version_id: str, request: Request, db: Session = Depends(get_db)) -> list[AnnotationWindowOut]:
    try:
        _route_level_operator_identity(request, access="read")
        dataset = db.get(Dataset, dataset_id)
        version = db.get(DatasetVersion, dataset_version_id)
        if not dataset or not version or version.dataset_id != dataset.dataset_id:
            raise HTTPException(status_code=404, detail='dataset or version not found')
        annotations = db.query(AnnotationWindow).filter(AnnotationWindow.dataset_version_id == dataset_version_id).order_by(AnnotationWindow.start_time.asc()).all()
        return [AnnotationWindowOut.model_validate({'annotation_window_id': a.annotation_window_id, 'label': a.label, 'annotation_type': a.annotation_type, 'start_time': a.start_time, 'end_time': a.end_time, 'notes': a.notes}) for a in annotations]
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post('/datasets/{dataset_id}/versions/{dataset_version_id}/analysis/recommend', response_model=AnalysisRecommendationOut)
def recommend_analysis_route(dataset_id: str, dataset_version_id: str, payload: AnalysisRecommendationRequest, request: Request, db: Session = Depends(get_db)) -> AnalysisRecommendationOut:
    try:
        _route_level_operator_identity(request, access="write")
        dataset = db.get(Dataset, dataset_id)
        version = db.get(DatasetVersion, dataset_version_id)
        if not dataset or not version or version.dataset_id != dataset.dataset_id:
            raise HTTPException(status_code=404, detail='dataset or version not found')
        try:
            return AnalysisRecommendationOut.model_validate(recommend_analysis(db, dataset_version_id, payload.goal_type))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post('/analysis-runs', response_model=AnalysisRunOut)
def create_analysis_run(payload: AnalysisRunIn, request: Request, db: Session = Depends(get_db)) -> AnalysisRunOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            run = run_analysis(db, payload.dataset_version_id, payload.method_name, payload.goal_type, payload.parameters, payload.annotation_window_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _serialize_analysis_run(db, run.analysis_run_id)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get('/analysis-runs/{analysis_run_id}', response_model=AnalysisRunOut)
def get_analysis_run(analysis_run_id: str, request: Request, db: Session = Depends(get_db)) -> AnalysisRunOut:
    try:
        _route_level_operator_identity(request, access="read")
        return _serialize_analysis_run(db, analysis_run_id)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/egress-armings",
    status_code=status.HTTP_201_CREATED,
    response_model=ConnectorRunSubmitOut,
)
def create_connector_egress_arming_route(
    payload: ConnectorEgressArmingIn,
    request: Request,
    db: Session = Depends(get_db),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        now = datetime.now(UTC)
        verified_grant = _resolve_egress_authority(
            connector_key=payload.connector_key,
            campaign_id=payload.campaign_id,
            campaign_fingerprint=payload.campaign_fingerprint,
            grant_sha256=payload.grant_sha256,
            now=now,
        )
        operator_receipt = (
            connector_egress_authorization.authorize_connector_egress_owner(
                request,
                verified_grant=verified_grant,
                access="write",
            )
        )
        run, created = connector_egress_arming.create_connector_egress_arming(
            db,
            payload=payload,
            verified_grant=verified_grant,
            operator_receipt=operator_receipt.model_dump(mode="json"),
            code_revision=_configured_code_revision(),
        )
        return _safe_egress_arming_projection(run, created=created)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)
    except (
        connector_egress_authorization.ConnectorEgressAuthorizationError,
        connector_egress_arming.ConnectorEgressArmingError,
    ) as exc:
        raise _egress_service_http_error(exc) from exc


@api_router.get(
    "/connectors/egress-armings/{connector_run_id}",
    response_model=ConnectorRunSubmitOut,
)
def get_connector_egress_arming_route(
    connector_run_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="egress arming not found")
        _strict_arming_envelope_for_route(run)
        return _safe_egress_arming_projection(run, created=False)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/egress-armings/{connector_run_id}/execute",
    status_code=status.HTTP_409_CONFLICT,
    response_model=None,
    deprecated=True,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Strict egress execution is disabled over HTTP; use the "
                "owned CLI acquisition child."
            ),
        },
    },
)
def execute_connector_egress_arming_route(
    connector_run_id: str,
    payload: ConnectorEgressExecuteIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "connector_strict_egress_http_execute_disabled",
                "message": (
                    "Strict egress execution is available only through the "
                    "owned CLI acquisition child."
                ),
            },
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/sciencebase-public/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_sciencebase_public_run(
    payload: ScienceBaseConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        _reject_generic_connector_during_exclusive_proof(
            connector_key="sciencebase_public"
        )
        try:
            run, created = submit_connector_run(
                db,
                connector_key="sciencebase_public",
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/sciencebase-mcs/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_sciencebase_mcs_run(
    payload: ScienceBaseMcsConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        _reject_generic_connector_during_exclusive_proof(
            connector_key="sciencebase_mcs"
        )
        try:
            run, created = submit_connector_run(
                db,
                connector_key="sciencebase_mcs",
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/nrc-adams-aps/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_nrc_adams_aps_run(
    payload: NrcAdamsApsConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        _reject_generic_connector_during_exclusive_proof(
            connector_key="nrc_adams_aps"
        )
        try:
            run, created = submit_nrc_adams_run(
                db,
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/senate-lda/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_senate_lda_run(
    payload: SenateLdaConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            run, created = submit_senate_lda_run(
                db,
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/worldbank/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_worldbank_run(
    payload: WorldBankConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            run, created = submit_worldbank_run(
                db,
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/cftc-cot/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_cftc_cot_run(
    payload: CftcCotConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            run, created = submit_cftc_cot_run(
                db,
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/bls/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_bls_run(
    payload: BlsConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            run, created = submit_bls_run(
                db,
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/oecd-sdmx/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunSubmitOut)
def create_oecd_sdmx_run(
    payload: OecdSdmxConnectorRunIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConnectorRunSubmitOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            run, created = submit_oecd_sdmx_run(
                db,
                payload=payload.model_dump(),
                idempotency_key=idempotency_key,
            )
        except SubmissionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OecdSdmxSchemaValidationError as exc:
            raise HTTPException(status_code=422, detail={"error_code": str(exc), "message": str(exc)}) from exc
        if created and run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunSubmitOut.model_validate(
            {
                "connector_run_id": run.connector_run_id,
                "status": run.status,
                "created": created,
                "submitted_at": run.submitted_at,
                "poll_url": f"/api/v1/connectors/runs/{run.connector_run_id}",
                "submission_idempotency_key": run.submission_idempotency_key,
                "request_fingerprint": run.request_fingerprint,
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/runs/{connector_run_id}", response_model=ConnectorRunOut)
def get_connector_run(connector_run_id: str, request: Request, db: Session = Depends(get_db)) -> ConnectorRunOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="connector run not found")
        _reject_strict_generic_read(run)
        return ConnectorRunOut.model_validate(serialize_connector_run(db, run))
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/runs/{connector_run_id}/targets", response_model=ConnectorRunTargetsPageOut)
def get_connector_run_targets(
    connector_run_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> ConnectorRunTargetsPageOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="connector run not found")
        _reject_strict_generic_read(run)
        query = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == connector_run_id)
        if status_filter:
            query = query.filter(ConnectorRunTarget.status == status_filter)
        total = query.count()
        targets = query.order_by(ConnectorRunTarget.ordinal.asc()).offset(offset).limit(limit).all()
        return ConnectorRunTargetsPageOut.model_validate(
            {
                "connector_run_id": connector_run_id,
                "total": total,
                "limit": limit,
                "offset": offset,
                "targets": [serialize_connector_target(item) for item in targets],
            }
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/runs/{connector_run_id}/events", response_model=ConnectorRunEventsPageOut)
def get_connector_run_events(
    connector_run_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConnectorRunEventsPageOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="connector run not found")
        _reject_strict_generic_read(run)
        return ConnectorRunEventsPageOut.model_validate(
            list_connector_run_events(
                db,
                connector_run_id=connector_run_id,
                limit=limit,
                offset=offset,
            )
        )
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/runs/{connector_run_id}/reports", response_model=ConnectorRunReportsOut)
def get_connector_run_reports(connector_run_id: str, request: Request, db: Session = Depends(get_db)) -> ConnectorRunReportsOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="connector run not found")
        _reject_strict_generic_read(run)
        return ConnectorRunReportsOut.model_validate(serialize_connector_run_reports(run))
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/runs/{connector_run_id}/content-units", response_model=ConnectorRunContentUnitsPageOut)
def get_connector_run_content_units(
    connector_run_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConnectorRunContentUnitsPageOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="connector run not found")
        _reject_strict_generic_read(run)
        payload = nrc_aps_content_index.list_content_units_for_run(
            db,
            run_id=connector_run_id,
            limit=limit,
            offset=offset,
        )
        return ConnectorRunContentUnitsPageOut.model_validate(payload)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/nrc-adams-aps/content-search", response_model=NrcApsContentSearchOut)
def search_nrc_adams_content(
    payload: NrcApsContentSearchIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsContentSearchOut:
    try:
        _route_level_operator_identity(request, access="read")
        run_id = str(payload.run_id or "").strip() or None
        if run_id:
            run = db.get(ConnectorRun, run_id)
            if not run:
                raise HTTPException(status_code=404, detail="connector run not found")
        limit = max(1, min(int(payload.limit), 100))
        offset = max(0, int(payload.offset))
        try:
            result = nrc_aps_content_index.search_content_units(
                db,
                query_text=payload.query,
                run_id=run_id,
                limit=limit,
                offset=offset,
            )
        except ValueError as exc:
            if str(exc) == "empty_query":
                raise HTTPException(status_code=422, detail="query must contain at least one alphanumeric token") from exc
            raise
        return NrcApsContentSearchOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/runs/{connector_run_id}/_operator/retrieval-content-units",
    response_model=ConnectorRunContentUnitsPageOut,
)
def get_connector_run_retrieval_content_units(
    connector_run_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConnectorRunContentUnitsPageOut:
    try:
        _route_level_operator_identity(request, access="read")
        run = db.get(ConnectorRun, connector_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="connector run not found")
        _reject_strict_generic_read(run)
        try:
            payload = aps_retrieval_plane_read.list_content_units_for_run(
                db,
                run_id=connector_run_id,
                limit=limit,
                offset=offset,
            )
        except aps_retrieval_plane_read.RetrievalPlaneReadError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
        return ConnectorRunContentUnitsPageOut.model_validate(payload)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/_operator/retrieval-content-search",
    response_model=NrcApsContentSearchOut,
)
def search_nrc_adams_retrieval_content(
    payload: NrcApsContentSearchIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsContentSearchOut:
    try:
        _route_level_operator_identity(request, access="read")
        run_id = str(payload.run_id or "").strip() or None
        if run_id:
            run = db.get(ConnectorRun, run_id)
            if not run:
                raise HTTPException(status_code=404, detail="connector run not found")
        limit = max(1, min(int(payload.limit), 100))
        offset = max(0, int(payload.offset))
        try:
            result = aps_retrieval_plane_read.search_content_units(
                db,
                query_text=payload.query,
                run_id=run_id,
                limit=limit,
                offset=offset,
            )
        except aps_retrieval_plane_read.RetrievalPlaneReadError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc
        except ValueError as exc:
            if str(exc) == "empty_query":
                raise HTTPException(status_code=422, detail="query must contain at least one alphanumeric token") from exc
            raise
        return NrcApsContentSearchOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/nrc-adams-aps/evidence-bundles", response_model=NrcApsEvidenceBundleOut)
def assemble_nrc_adams_evidence_bundle(
    payload: NrcApsEvidenceBundleAssembleIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsEvidenceBundleOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_evidence_bundle.assemble_evidence_bundle(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_evidence_bundle.EvidenceBundleError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceBundleOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/nrc-adams-aps/evidence-bundles/{bundle_id}", response_model=NrcApsEvidenceBundleOut)
def get_nrc_adams_evidence_bundle(
    bundle_id: str,
    request: Request,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=0),
) -> NrcApsEvidenceBundleOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_evidence_bundle.get_persisted_bundle_page(
                bundle_id=str(bundle_id or "").strip(),
                limit=limit,
                offset=offset,
            )
        except nrc_aps_evidence_bundle.EvidenceBundleError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceBundleOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/nrc-adams-aps/citation-packs", response_model=NrcApsEvidenceCitationPackOut)
def assemble_nrc_adams_evidence_citation_pack(
    payload: NrcApsEvidenceCitationPackCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsEvidenceCitationPackOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_evidence_citation_pack.assemble_evidence_citation_pack(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_evidence_citation_pack.EvidenceCitationPackError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceCitationPackOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/nrc-adams-aps/citation-packs/{citation_pack_id}", response_model=NrcApsEvidenceCitationPackOut)
def get_nrc_adams_evidence_citation_pack(
    citation_pack_id: str,
    request: Request,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=0),
) -> NrcApsEvidenceCitationPackOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_evidence_citation_pack.get_persisted_citation_pack_page(
                citation_pack_id=str(citation_pack_id or "").strip(),
                limit=limit,
                offset=offset,
            )
        except nrc_aps_evidence_citation_pack.EvidenceCitationPackError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceCitationPackOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/nrc-adams-aps/evidence-reports", response_model=NrcApsEvidenceReportOut)
def assemble_nrc_adams_evidence_report(
    payload: NrcApsEvidenceReportCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsEvidenceReportOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_evidence_report.assemble_evidence_report(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_evidence_report.EvidenceReportError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceReportOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get("/connectors/nrc-adams-aps/evidence-reports/{evidence_report_id}", response_model=NrcApsEvidenceReportOut)
def get_nrc_adams_evidence_report(
    evidence_report_id: str,
    request: Request,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=0),
) -> NrcApsEvidenceReportOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_evidence_report.get_persisted_evidence_report_page(
                evidence_report_id=str(evidence_report_id or "").strip(),
                limit=limit,
                offset=offset,
            )
        except nrc_aps_evidence_report.EvidenceReportError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceReportOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/nrc-adams-aps/evidence-report-exports", response_model=NrcApsEvidenceReportExportOut)
def assemble_nrc_adams_evidence_report_export(
    payload: NrcApsEvidenceReportExportCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsEvidenceReportExportOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_evidence_report_export.assemble_evidence_report_export(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_evidence_report_export.EvidenceReportExportError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceReportExportOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/evidence-report-exports/{evidence_report_export_id}",
    response_model=NrcApsEvidenceReportExportOut,
)
def get_nrc_adams_evidence_report_export(
    evidence_report_export_id: str,
    request: Request,
) -> NrcApsEvidenceReportExportOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_evidence_report_export.get_persisted_evidence_report_export(
                evidence_report_export_id=str(evidence_report_export_id or "").strip(),
            )
        except nrc_aps_evidence_report_export.EvidenceReportExportError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceReportExportOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/evidence-report-export-packages",
    response_model=NrcApsEvidenceReportExportPackageOut,
)
def assemble_nrc_adams_evidence_report_export_package(
    payload: NrcApsEvidenceReportExportPackageCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsEvidenceReportExportPackageOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_evidence_report_export_package.assemble_evidence_report_export_package(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceReportExportPackageOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/evidence-report-export-packages/{evidence_report_export_package_id}",
    response_model=NrcApsEvidenceReportExportPackageOut,
)
def get_nrc_adams_evidence_report_export_package(
    evidence_report_export_package_id: str,
    request: Request,
) -> NrcApsEvidenceReportExportPackageOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_evidence_report_export_package.get_persisted_evidence_report_export_package(
                evidence_report_export_package_id=str(evidence_report_export_package_id or "").strip(),
            )
        except nrc_aps_evidence_report_export_package.EvidenceReportExportPackageError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsEvidenceReportExportPackageOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/context-packets",
    response_model=NrcApsContextPacketOut,
)
def assemble_nrc_adams_context_packet(
    payload: NrcApsContextPacketCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsContextPacketOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_context_packet.assemble_context_packet(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_context_packet.ContextPacketError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsContextPacketOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/context-packets/{context_packet_id}",
    response_model=NrcApsContextPacketOut,
)
def get_nrc_adams_context_packet(
    context_packet_id: str,
    request: Request,
) -> NrcApsContextPacketOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_context_packet.get_persisted_context_packet(
                context_packet_id=str(context_packet_id or "").strip(),
            )
        except nrc_aps_context_packet.ContextPacketError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsContextPacketOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/context-dossiers",
    response_model=NrcApsContextDossierOut,
)
def assemble_nrc_adams_context_dossier(
    payload: NrcApsContextDossierCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsContextDossierOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_context_dossier.assemble_context_dossier(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_context_dossier.ContextDossierError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsContextDossierOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/context-dossiers/{context_dossier_id}",
    response_model=NrcApsContextDossierOut,
)
def get_nrc_adams_context_dossier(
    context_dossier_id: str,
    request: Request,
) -> NrcApsContextDossierOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_context_dossier.get_persisted_context_dossier(
                context_dossier_id=str(context_dossier_id or "").strip(),
            )
        except nrc_aps_context_dossier.ContextDossierError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsContextDossierOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/deterministic-insight-artifacts",
    response_model=NrcApsDeterministicInsightArtifactOut,
)
def assemble_nrc_adams_deterministic_insight_artifact(
    payload: NrcApsDeterministicInsightArtifactCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsDeterministicInsightArtifactOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_deterministic_insight_artifact.assemble_deterministic_insight_artifact(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_deterministic_insight_artifact.DeterministicInsightArtifactError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsDeterministicInsightArtifactOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/deterministic-insight-artifacts/{deterministic_insight_artifact_id}",
    response_model=NrcApsDeterministicInsightArtifactOut,
)
def get_nrc_adams_deterministic_insight_artifact(
    deterministic_insight_artifact_id: str,
    request: Request,
) -> NrcApsDeterministicInsightArtifactOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_deterministic_insight_artifact.get_persisted_deterministic_insight_artifact(
                deterministic_insight_artifact_id=str(deterministic_insight_artifact_id or "").strip(),
            )
        except nrc_aps_deterministic_insight_artifact.DeterministicInsightArtifactError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsDeterministicInsightArtifactOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/deterministic-challenge-artifacts",
    response_model=NrcApsDeterministicChallengeArtifactOut,
)
def assemble_nrc_adams_deterministic_challenge_artifact(
    payload: NrcApsDeterministicChallengeArtifactCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsDeterministicChallengeArtifactOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_deterministic_challenge_artifact.assemble_deterministic_challenge_artifact(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_deterministic_challenge_artifact.DeterministicChallengeArtifactError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsDeterministicChallengeArtifactOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/deterministic-challenge-artifacts/{deterministic_challenge_artifact_id}",
    response_model=NrcApsDeterministicChallengeArtifactOut,
)
def get_nrc_adams_deterministic_challenge_artifact(
    deterministic_challenge_artifact_id: str,
    request: Request,
) -> NrcApsDeterministicChallengeArtifactOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_deterministic_challenge_artifact.get_persisted_deterministic_challenge_artifact(
                deterministic_challenge_artifact_id=str(deterministic_challenge_artifact_id or "").strip(),
            )
        except nrc_aps_deterministic_challenge_artifact.DeterministicChallengeArtifactError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsDeterministicChallengeArtifactOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post(
    "/connectors/nrc-adams-aps/deterministic-challenge-review-packets",
    response_model=NrcApsDeterministicChallengeReviewPacketOut,
)
def assemble_nrc_adams_deterministic_challenge_review_packet(
    payload: NrcApsDeterministicChallengeReviewPacketCreateIn,
    request: Request,
    db: Session = Depends(get_db),
) -> NrcApsDeterministicChallengeReviewPacketOut:
    try:
        _route_level_operator_identity(request, access="write")
        try:
            result = nrc_aps_deterministic_challenge_review_packet.assemble_deterministic_challenge_review_packet(
                db,
                request_payload=payload.model_dump(),
            )
        except nrc_aps_deterministic_challenge_review_packet.DeterministicChallengeReviewPacketError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsDeterministicChallengeReviewPacketOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.get(
    "/connectors/nrc-adams-aps/deterministic-challenge-review-packets/{deterministic_challenge_review_packet_id}",
    response_model=NrcApsDeterministicChallengeReviewPacketOut,
)
def get_nrc_adams_deterministic_challenge_review_packet(
    deterministic_challenge_review_packet_id: str,
    request: Request,
) -> NrcApsDeterministicChallengeReviewPacketOut:
    try:
        _route_level_operator_identity(request, access="read")
        try:
            result = nrc_aps_deterministic_challenge_review_packet.get_persisted_deterministic_challenge_review_packet(
                deterministic_challenge_review_packet_id=str(deterministic_challenge_review_packet_id or "").strip(),
            )
        except nrc_aps_deterministic_challenge_review_packet.DeterministicChallengeReviewPacketError as exc:
            raise HTTPException(
                status_code=int(exc.status_code),
                detail={"code": str(exc.code), "message": str(exc.message)},
            ) from exc
        return NrcApsDeterministicChallengeReviewPacketOut.model_validate(result)
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/runs/{connector_run_id}/resume", status_code=status.HTTP_202_ACCEPTED, response_model=ConnectorRunOut)
def resume_connector_run(
    connector_run_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> ConnectorRunOut:
    try:
        _route_level_operator_identity(request, access="write")
        current = db.get(ConnectorRun, connector_run_id)
        if current is None:
            raise HTTPException(status_code=404, detail="connector run not found")
        if connector_egress_arming.has_reserved_egress_provenance(current):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "connector_strict_resume_forbidden",
                    "message": "strict egress armings cannot use generic resume",
                },
            )
        _reject_generic_connector_during_exclusive_proof(
            connector_key=current.connector_key
        )
        try:
            run = request_resume_run(db, connector_run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if run.status == "pending":
            _enqueue_connector_run(background_tasks, run.connector_key, run.connector_run_id)
        return ConnectorRunOut.model_validate(serialize_connector_run(db, run))
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


@api_router.post("/connectors/runs/{connector_run_id}/cancel", response_model=ConnectorRunOut)
def cancel_connector_run(connector_run_id: str, request: Request, db: Session = Depends(get_db)) -> ConnectorRunOut:
    try:
        _route_level_operator_identity(request, access="write")
        current = db.get(ConnectorRun, connector_run_id)
        if current is None:
            raise HTTPException(status_code=404, detail="connector run not found")
        if connector_egress_arming.has_reserved_egress_provenance(current):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "connector_strict_cancel_forbidden",
                    "message": "strict egress armings cannot use generic cancel",
                },
            )
        try:
            run = request_cancel_run(db, connector_run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return ConnectorRunOut.model_validate(serialize_connector_run(db, run))
    except SecXbrlInAppAuthPolicyError as exc:
        return _legacy_api_auth_policy_error_response(exc)


def _serialize_analysis_run(db: Session, analysis_run_id: str) -> AnalysisRunOut:
    run = db.get(AnalysisRun, analysis_run_id)
    if not run:
        raise HTTPException(status_code=404, detail='analysis run not found')
    payload = {'analysis_run_id': run.analysis_run_id, 'dataset_version_id': run.dataset_version_id, 'method_name': run.method_name, 'goal_type': run.goal_type, 'status': run.status, 'route_reason': run.route_reason, 'parameters_json': run.parameters_json, 'artifacts': [{'artifact_id': a.artifact_id, 'artifact_type': a.artifact_type, 'title': a.title, 'storage_ref': a.storage_ref, 'summary': a.summary, 'metadata_json': a.metadata_json} for a in run.artifacts], 'assumptions': [{'assumption_check_id': a.assumption_check_id, 'assumption_name': a.assumption_name, 'check_result': a.check_result, 'severity': a.severity, 'notes': a.notes} for a in run.assumptions], 'caveats': [{'caveat_note_id': c.caveat_note_id, 'caveat_type': c.caveat_type, 'severity': c.severity, 'message': c.message} for c in run.caveats]}
    return AnalysisRunOut.model_validate(payload)
