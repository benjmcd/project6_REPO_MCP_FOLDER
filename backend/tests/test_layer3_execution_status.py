from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3PassRun
from app.services import layer3_execution_status as execution_status
from app.services import layer3_workbench
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_SCOPE_QUANT_SINGLE_ITEM,
    PASS_STATUS_COMPLETED,
    PASS_STATUS_FAILED,
    PASS_TYPE_SINGLE_ITEM,
)


def _pass_run(
    *,
    status: str = PASS_STATUS_COMPLETED,
    summary_json: dict | None = None,
) -> L3PassRun:
    return L3PassRun(
        pass_run_id="pass-run-status-response",
        session_id="session-status-response",
        analysis_plan_id="plan-status-response",
        analysis_set_id="set-status-response",
        pass_type=PASS_TYPE_SINGLE_ITEM,
        engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
        status=status,
        input_payload_ref="payload://pass-run-status-response/input",
        output_payload_ref="payload://pass-run-status-response/output",
        summary_json=summary_json
        or {
            "execution_started": True,
            "analysis_run_id": "analysis-run-status-response",
            "pass_scope": PASS_SCOPE_QUANT_SINGLE_ITEM,
            "selected_method_name": "descriptive_summary",
            "dataset_version_id": "dataset-version-status-response",
            "planned_pass": {"pass_scope": "unused-fallback"},
        },
    )


def _without_server_time(response: dict) -> dict:
    return {key: value for key, value in response.items() if key != "server_time"}


def test_execution_result_status_response_preserves_workbench_available_projection() -> None:
    pass_run = _pass_run()
    output_metadata_summary = {
        "schema_id": "layer3.output_metadata_summary.v1",
        "output_payload_ref": "payload://pass-run-status-response/output",
    }

    response = execution_status.execution_result_status_response(
        request_id="request-status-response",
        status="available",
        session_id="session-status-response",
        analysis_plan_id="plan-status-response",
        preview_id="preview-status-response",
        preview_hash="hash-status-response",
        pass_run=pass_run,
        analysis_run=None,
        output_metadata_summary=output_metadata_summary,
        output_metadata_error=None,
    )
    workbench_response = layer3_workbench._execution_result_status_response(
        request_id="request-status-response",
        status="available",
        session_id="session-status-response",
        analysis_plan_id="plan-status-response",
        preview_id="preview-status-response",
        preview_hash="hash-status-response",
        pass_run=pass_run,
        analysis_run=None,
        output_metadata_summary=output_metadata_summary,
        output_metadata_error=None,
    )

    assert _without_server_time(response) == _without_server_time(workbench_response)
    assert response["schema_id"] == "layer3.execution_result_status.v1"
    assert response["result_status_available"] is True
    assert response["next_state"] == "execution_result_status_available"
    assert response["output_metadata_summary"] == output_metadata_summary
    assert response["downstream_unavailable"] == ["result_review", "package", "handoff"]
    assert response["pass_scope"] == PASS_SCOPE_QUANT_SINGLE_ITEM
    assert response["selected_method_name"] == "descriptive_summary"
    assert response["dataset_version_id"] == "dataset-version-status-response"


def test_execution_result_status_response_preserves_failed_projection() -> None:
    pass_run = _pass_run(
        status=PASS_STATUS_FAILED,
        summary_json={
            "execution_started": True,
            "analysis_run_id": "analysis-run-status-response",
            "error": "execution failed",
            "planned_pass": {"pass_scope": PASS_SCOPE_QUANT_SINGLE_ITEM},
        },
    )

    response = execution_status.execution_result_status_response(
        request_id="request-status-failed",
        status="blocked",
        session_id="session-status-response",
        analysis_plan_id="plan-status-response",
        preview_id="preview-status-response",
        preview_hash="hash-status-response",
        pass_run=pass_run,
        analysis_run=None,
        output_metadata_summary=None,
        output_metadata_error="output missing",
    )

    assert response["error_present"] is True
    assert response["error_message"] == "execution failed"
    assert response["output_metadata_error"] == "output missing"
    assert response["next_state"] == "execution_result_status_blocked"
    assert response["result_review_enabled"] is False
