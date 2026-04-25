from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import layer3_workbench
from app.services.layer3_workbench import Layer3WorkbenchError

router = APIRouter()


def _json_or_error(handler: Callable[[], dict[str, Any]]) -> dict[str, Any] | JSONResponse:
    try:
        return handler()
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=layer3_workbench.workbench_error_response(exc),
        )


@router.get("/bootstrap")
def get_bootstrap() -> dict[str, Any]:
    return layer3_workbench.bootstrap()


@router.get("/readiness")
def get_readiness() -> dict[str, Any]:
    return layer3_workbench.readiness_contract()


@router.post("/preflight", response_model=None)
def post_preflight(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.preflight(payload))


@router.post("/source-preview", response_model=None)
def post_source_preview(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.source_preview(payload))


@router.post("/material-preview", response_model=None)
def post_material_preview(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.material_preview(payload))


@router.post("/gate-b/decision", response_model=None)
def post_gate_b_decision(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.gate_b_decision(db, payload))


@router.post("/gate-c/preview", response_model=None)
def post_gate_c_preview(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.gate_c_preview(db, payload))


@router.post("/gate-c/override")
def post_gate_c_override(payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=layer3_workbench.gate_c_override_unavailable(payload),
    )


@router.post("/plan/preview", response_model=None)
def post_plan_preview(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_preview(db, payload))


@router.post("/plan/approve", response_model=None)
def post_plan_approve(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_approval(db, payload))


@router.post("/plan/revise", response_model=None)
def post_plan_revise(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.plan_revision(db, payload))


@router.post("/execution/select", response_model=None)
def post_execution_select(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_selection(db, payload))


@router.post("/execution/start", response_model=None)
def post_execution_start(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.analysis_execution_start(db, payload))


@router.post("/execution/result/status", response_model=None)
def post_execution_result_status(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.execution_result_status(db, payload))


@router.get("/session/{session_id}", response_model=None)
def get_session_summary(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    return _json_or_error(lambda: layer3_workbench.session_summary(db, session_id))
