from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import L3PassRun
from app.services import layer3_execution_review as execution_review
from app.services import layer3_workbench
from app.services.layer3_pass_entry import (
    ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
    PASS_STATUS_COMPLETED,
    PASS_TYPE_SINGLE_ITEM,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError


def _pass_run(summary_json: dict | None = None) -> L3PassRun:
    return L3PassRun(
        pass_run_id="pass-run-review",
        session_id="session-review",
        analysis_plan_id="plan-review",
        analysis_set_id="set-review",
        pass_type=PASS_TYPE_SINGLE_ITEM,
        engine_family=ENGINE_FAMILY_WRAPPED_QUANTITATIVE_ANALYSIS,
        status=PASS_STATUS_COMPLETED,
        input_payload_ref="payload://input",
        output_payload_ref="payload://output",
        summary_json=summary_json or {},
    )


def _output_metadata_summary() -> dict:
    return {
        "output_payload_ref": "payload://output",
        "analysis_set_id": "set-review",
        "dataset_version_id": "dataset-version-output",
        "selected_method_name": "cross_correlation",
        "pass_scope": "single_item",
        "source_dataset_version_ids": ["dataset-version-output"],
        "cohort_shape": "single_item",
        "requested_method_name": "cross_correlation",
        "requested_method_source": "default",
        "artifact_count": 1,
        "artifact_types": ["table"],
        "source_gate": "source-gate-review",
    }


def test_execution_result_review_from_pass_run_preserves_workbench_projection() -> None:
    review_state = {
        "schema_id": execution_review.EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID,
        "review_record_ref": "layer3://review/pass-run-review",
        "review_state": "execution_result_review_approved",
    }
    pass_run = _pass_run({"execution_result_review": review_state})

    assert execution_review.execution_result_review_from_pass_run(pass_run) == review_state
    assert layer3_workbench._execution_result_review_from_pass_run(pass_run) == review_state

    pass_run.summary_json["execution_result_review"] = {
        **review_state,
        "schema_id": "wrong-schema",
    }
    assert execution_review.execution_result_review_from_pass_run(pass_run) is None
    assert layer3_workbench._execution_result_review_from_pass_run(pass_run) is None


def test_normalize_result_review_items_preserves_trace_semantics() -> None:
    pass_run = _pass_run()
    output_summary = _output_metadata_summary()
    items = [
        {
            "item_ref": "traceable-output",
            "item_type": "datum",
            "trace": {
                "session_id": pass_run.session_id,
                "analysis_plan_id": pass_run.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "analysis_run_id": "analysis-run-review",
                "output_payload_ref": output_summary["output_payload_ref"],
            },
        },
        {
            "output_item_ref": "untraceable-output",
            "item_type": "unsupported-type",
            "trace": {"session_id": "wrong-session"},
        },
        "not-an-item",
    ]

    normalized, unresolved = execution_review.normalize_result_review_items(
        items=items,
        session_id=pass_run.session_id,
        analysis_plan_id=pass_run.analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id="analysis-run-review",
        output_metadata_summary=output_summary,
    )

    assert unresolved == 2
    assert normalized == layer3_workbench._normalize_result_review_items(
        items=items,
        session_id=pass_run.session_id,
        analysis_plan_id=pass_run.analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id="analysis-run-review",
        output_metadata_summary=output_summary,
    )[0]
    assert normalized[0]["trace_status"] == "resolved"
    assert normalized[1]["item_ref"] == "untraceable-output"
    assert "item_type" in normalized[1]["missing_trace_fields"]
    assert normalized[2]["missing_trace_fields"] == ["item"]


def test_normalize_result_review_items_preserves_fail_closed_errors() -> None:
    pass_run = _pass_run()
    output_summary = _output_metadata_summary()

    with pytest.raises(Layer3WorkbenchError) as malformed:
        execution_review.normalize_result_review_items(
            items={"not": "a-list"},
            session_id=pass_run.session_id,
            analysis_plan_id=pass_run.analysis_plan_id,
            pass_run=pass_run,
            analysis_run_id=None,
            output_metadata_summary=output_summary,
        )
    assert malformed.value.error_code == "reviewed_output_items_malformed"
    assert malformed.value.blocked_fields == ["reviewed_output_items"]

    with pytest.raises(Layer3WorkbenchError) as too_large:
        execution_review.normalize_result_review_items(
            items=[{}] * 51,
            session_id=pass_run.session_id,
            analysis_plan_id=pass_run.analysis_plan_id,
            pass_run=pass_run,
            analysis_run_id=None,
            output_metadata_summary=output_summary,
        )
    assert too_large.value.error_code == "reviewed_output_items_too_large"
    assert too_large.value.blocked_fields == ["reviewed_output_items"]


def test_result_review_trace_summary_preserves_workbench_projection() -> None:
    pass_run = _pass_run(
        {
            "dataset_version_id": "dataset-version-summary",
            "selected_method_name": "fallback-method",
            "pass_scope": "fallback-scope",
            "source_dataset_version_ids_json": ["dataset-version-summary"],
        }
    )
    output_summary = {
        **_output_metadata_summary(),
        "dataset_version_id": None,
        "selected_method_name": None,
        "pass_scope": None,
        "source_dataset_version_ids": None,
        "artifact_types": ["table", "chart"],
    }
    reviewed_items = [{"index": 0, "trace_status": "resolved"}]

    trace_summary = execution_review.result_review_trace_summary(
        session_id=pass_run.session_id,
        analysis_plan_id=pass_run.analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id="analysis-run-review",
        output_metadata_summary=output_summary,
        reviewed_items=reviewed_items,
        unresolved_trace_count=0,
    )

    assert trace_summary == layer3_workbench._result_review_trace_summary(
        session_id=pass_run.session_id,
        analysis_plan_id=pass_run.analysis_plan_id,
        pass_run=pass_run,
        analysis_run_id="analysis-run-review",
        output_metadata_summary=output_summary,
        reviewed_items=reviewed_items,
        unresolved_trace_count=0,
    )
    assert trace_summary["dataset_version_id"] == "dataset-version-summary"
    assert trace_summary["selected_method_name"] == "fallback-method"
    assert trace_summary["source_dataset_version_ids"] == ["dataset-version-summary"]
    assert trace_summary["reviewed_item_count"] == 1
