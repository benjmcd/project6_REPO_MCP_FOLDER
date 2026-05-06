from __future__ import annotations

from typing import Any

from app.models.models import L3PassRun
from app.services.layer3_execution_state import (
    execution_state_for_pass_runs,
    pass_run_analysis_run_id,
    pass_run_execution_started,
)
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_response_contract import base_response

ANALYSIS_EXECUTION_START_SCHEMA_ID = "layer3.analysis_execution_start.v1"
ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE = ("results", "package", "handoff")


def analysis_execution_start_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_run: L3PassRun,
) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    return {
        **base_response(ANALYSIS_EXECUTION_START_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_identity": preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "execution_started": pass_run_execution_started(pass_run),
        "analysis_run_id": pass_run_analysis_run_id(pass_run),
        "pass_run_status": pass_run.status,
        "output_payload_ref": pass_run.output_payload_ref,
        "downstream_unavailable": list(ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE),
        "next_state": execution_state_for_pass_runs([pass_run]),
        "engine_family": pass_run.engine_family,
        "selected_method_name": summary.get("selected_method_name"),
        "dataset_version_id": summary.get("dataset_version_id"),
    }
