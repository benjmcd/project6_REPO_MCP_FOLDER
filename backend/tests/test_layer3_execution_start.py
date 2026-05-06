from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3PassRun
from app.services import layer3_execution_start as execution_start
from app.services import layer3_workbench
from app.services.layer3_execution_state import EXECUTION_PASS_COMPLETED_STATE
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_TYPE_SINGLE_ITEM,
)


def _pass_run() -> L3PassRun:
    return L3PassRun(
        pass_run_id="pass-run-start-response",
        session_id="session-start-response",
        analysis_plan_id="plan-start-response",
        analysis_set_id="set-start-response",
        pass_type=PASS_TYPE_SINGLE_ITEM,
        engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
        status=PASS_STATUS_COMPLETED,
        input_payload_ref="payload://pass-run-start-response/input",
        output_payload_ref="payload://pass-run-start-response/output",
        summary_json={
            "execution_started": True,
            "analysis_run_id": "analysis-run-start-response",
            "selected_method_name": "descriptive_summary",
            "dataset_version_id": "dataset-version-start-response",
        },
    )


def _without_server_time(response: dict) -> dict:
    return {key: value for key, value in response.items() if key != "server_time"}


def test_analysis_execution_start_response_preserves_workbench_projection() -> None:
    pass_run = _pass_run()

    response = execution_start.analysis_execution_start_response(
        request_id="request-start-response",
        status=PASS_STATUS_COMPLETED,
        session_id="session-start-response",
        analysis_plan_id="plan-start-response",
        preview_id="preview-start-response",
        preview_hash="hash-start-response",
        pass_run=pass_run,
    )
    workbench_response = layer3_workbench._analysis_execution_start_response(
        request_id="request-start-response",
        status=PASS_STATUS_COMPLETED,
        session_id="session-start-response",
        analysis_plan_id="plan-start-response",
        preview_id="preview-start-response",
        preview_hash="hash-start-response",
        pass_run=pass_run,
    )

    assert _without_server_time(response) == _without_server_time(workbench_response)
    assert response["schema_id"] == "layer3.analysis_execution_start.v1"
    assert response["execution_started"] is True
    assert response["analysis_run_id"] == "analysis-run-start-response"
    assert response["pass_run_status"] == PASS_STATUS_COMPLETED
    assert response["output_payload_ref"] == "payload://pass-run-start-response/output"
    assert response["downstream_unavailable"] == ["results", "package", "handoff"]
    assert response["next_state"] == EXECUTION_PASS_COMPLETED_STATE
    assert response["selected_method_name"] == "descriptive_summary"
    assert response["dataset_version_id"] == "dataset-version-start-response"
