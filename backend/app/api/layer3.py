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
    preview_hash_contract: dict[str, Any]
    idempotency_contract: dict[str, Any]
    concurrency_contract: dict[str, Any]
    deferred_decisions: dict[str, Any]


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
    material_candidates: list[dict[str, Any]]
    partial_retrieval: bool
    authority_rail: dict[str, Any]


class Layer3GateBDecisionResponse(Layer3BaseResponse):
    session_id: str
    selection_manifest_id: str
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
    unresolved_trace_count: int
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


@router.post("/preflight", response_model=Layer3PreflightResponse)
def post_preflight(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.preflight(payload))


@router.post("/source-preview", response_model=Layer3SourcePreviewResponse)
def post_source_preview(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.source_preview(payload))


@router.post("/material-preview", response_model=Layer3MaterialPreviewResponse)
def post_material_preview(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.material_preview(payload))


@router.post("/gate-b/decision", response_model=Layer3GateBDecisionResponse)
def post_gate_b_decision(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.gate_b_decision(db, payload))


@router.post("/gate-c/preview", response_model=Layer3GateCPreviewResponse)
def post_gate_c_preview(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.gate_c_preview(db, payload))


@router.post("/gate-c/override")
def post_gate_c_override(payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=layer3_workbench.gate_c_override_unavailable(payload),
    )


@router.post("/plan/preview", response_model=Layer3PlanPreviewResponse)
def post_plan_preview(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_preview(db, payload))


@router.post("/plan/approve", response_model=Layer3PlanApprovalResponse)
def post_plan_approve(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_approval(db, payload))


@router.post("/plan/revise", response_model=Layer3PlanRevisionResponse)
def post_plan_revise(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_revision(db, payload))


@router.post("/execution/select", response_model=Layer3ExecutionSelectionResponse)
def post_execution_select(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_selection(db, payload))


@router.post("/execution/start", response_model=Layer3AnalysisExecutionStartResponse)
def post_execution_start(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.analysis_execution_start(db, payload))


@router.post("/execution/result/status", response_model=Layer3ExecutionResultStatusResponse)
def post_execution_result_status(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_result_status(db, payload))


@router.post("/execution/result/review", response_model=Layer3ExecutionResultReviewResponse)
def post_execution_result_review(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_result_review(db, payload))


@router.post("/package/review/preview", response_model=Layer3PackageReviewPreviewResponse)
def post_package_review_preview(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_review_preview(db, payload))


@router.post("/package/review/commit", response_model=Layer3PackageConstructionCommitResponse)
def post_package_review_commit(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_construction_commit(db, payload))


@router.post("/package/review/submit", response_model=Layer3PackageReviewSubmitResponse)
def post_package_review_submit(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.package_review_submit(db, payload))


@router.post("/handoff/export/prepare", response_model=Layer3HandoffExportPrepareResponse)
def post_handoff_export_prepare(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.handoff_export_prepare(db, payload))


@router.post("/handoff/aps/dispatch", response_model=Layer3ApsHandoffDispatchResponse)
def post_aps_handoff_dispatch(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.aps_handoff_dispatch(db, payload))


@router.post("/handoff/export/download/prepare", response_model=None)
def post_external_export_download_prepare(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.external_export_download_prepare(db, payload))


@router.post("/handoff/export/download/deliver", response_model=None)
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


@router.get("/session/{session_id}", response_model=None)
def get_session_summary(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.session_summary(db, session_id))
