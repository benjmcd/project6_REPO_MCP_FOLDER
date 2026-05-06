from __future__ import annotations

from typing import Any

from app.models.models import AnalysisRun, L3PassRun
from app.services.layer3_execution_state import (
    analysis_execution_start_from_pass_run,
    pass_run_analysis_run_id,
)
from app.services.layer3_pass_entry import (
    PASS_STATUS_COMPLETED_WITH_WARNINGS,
    PASS_STATUS_FAILED,
)
from app.services.layer3_preview_contract import preview_identity
from app.services.layer3_response_contract import base_response

EXECUTION_RESULT_STATUS_SCHEMA_ID = "layer3.execution_result_status.v1"
EXECUTION_RESULT_STATUS_AVAILABLE_STATE = "execution_result_status_available"
EXECUTION_RESULT_STATUS_BLOCKED_STATE = "execution_result_status_blocked"
EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE = "execution_result_status_missing_output"
EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE = ("result_review", "package", "handoff")


def execution_result_status_response(
    *,
    request_id: str | None,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_run: L3PassRun,
    analysis_run: AnalysisRun | None,
    output_metadata_summary: dict[str, Any] | None,
    output_metadata_error: str | None,
) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    planned_pass = summary.get("planned_pass")
    if not isinstance(planned_pass, dict):
        planned_pass = {}
    start_state = analysis_execution_start_from_pass_run(pass_run)
    pass_error = summary.get("error") or ((start_state or {}).get("error"))
    return {
        **base_response(EXECUTION_RESULT_STATUS_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_identity": preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "execution_started": bool(start_state) or bool(summary.get("execution_started")),
        "analysis_run_id": pass_run_analysis_run_id(pass_run),
        "analysis_run_status": analysis_run.status if analysis_run is not None else None,
        "pass_run_status": pass_run.status,
        "output_payload_ref": pass_run.output_payload_ref,
        "output_metadata_summary": output_metadata_summary,
        "output_metadata_error": output_metadata_error,
        "warnings_present": pass_run.status == PASS_STATUS_COMPLETED_WITH_WARNINGS,
        "error_present": pass_run.status == PASS_STATUS_FAILED or bool(pass_error),
        "error_message": str(pass_error) if pass_error else None,
        "result_status_available": status == "available",
        "result_review_enabled": False,
        "package_review_enabled": False,
        "handoff_enabled": False,
        "downstream_unavailable": list(EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE),
        "next_state": (
            EXECUTION_RESULT_STATUS_AVAILABLE_STATE
            if status == "available"
            else (
                EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE
                if status == "missing_output_metadata"
                else EXECUTION_RESULT_STATUS_BLOCKED_STATE
            )
        ),
        "operator_view_mode": "status_only",
        "engine_family": pass_run.engine_family,
        "pass_type": pass_run.pass_type,
        "pass_scope": summary.get("pass_scope") or planned_pass.get("pass_scope"),
        "selected_method_name": summary.get("selected_method_name"),
        "dataset_version_id": summary.get("dataset_version_id"),
    }
