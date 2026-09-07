from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models.models import AnalysisArtifact, AnalysisRun, AssumptionCheck, CaveatNote, L3PassRun
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


def test_execution_result_review_response_preserves_workbench_projection() -> None:
    pass_run = _pass_run()
    review_state = {
        "review_state": "execution_result_review_approved",
        "operator_decision": "approved",
        "review_record_ref": "layer3://review/pass-run-review",
        "trace_summary": {"reviewed_item_count": 1, "nested": {"stable": True}},
        "reviewed_output_items": [{"item_ref": "item-1", "trace_status": "resolved"}],
        "unresolved_trace_count": 0,
        "review_notes": "Reviewed and traceable.",
        "pass_type": PASS_TYPE_SINGLE_ITEM,
        "pass_scope": "single_item",
        "selected_method_name": "cross_correlation",
        "source_gate": "source-gate-review",
        "source_dataset_version_ids": ["dataset-version-output"],
        "cohort_shape": "single_item",
    }

    assert layer3_workbench._execution_result_review_response is execution_review.execution_result_review_response

    response = execution_review.execution_result_review_response(
        request_id="request-review-response",
        status="recorded",
        session_id=pass_run.session_id,
        analysis_plan_id=pass_run.analysis_plan_id,
        preview_id="preview-review",
        preview_hash="hash-review",
        pass_run=pass_run,
        analysis_run_id="analysis-run-review",
        review_state=review_state,
    )

    assert response["schema_id"] == execution_review.EXECUTION_RESULT_REVIEW_SCHEMA_ID
    assert response["status"] == "recorded"
    assert response["request_id"] == "request-review-response"
    assert response["session_id"] == pass_run.session_id
    assert response["analysis_plan_id"] == pass_run.analysis_plan_id
    assert response["pass_run_id"] == pass_run.pass_run_id
    assert response["preview_identity"]["schema_id"] == "layer3.plan_preview_identity.v1"
    assert response["preview_identity"]["preview_id"] == "preview-review"
    assert response["preview_identity"]["preview_hash"] == "hash-review"
    assert response["preview_identity"]["authority_source"] == "server_owner_service_preview"
    assert response["preview_identity"]["stale_preview_writes_blocked"] is True
    assert response["analysis_run_id"] == "analysis-run-review"
    assert response["result_status_available"] is True
    assert response["result_review_enabled"] is True
    assert response["review_state"] == "execution_result_review_approved"
    assert response["operator_decision"] == "approved"
    assert response["review_record_ref"] == "layer3://review/pass-run-review"
    assert response["trace_summary"] == review_state["trace_summary"]
    assert response["reviewed_output_items"] == review_state["reviewed_output_items"]
    assert response["unresolved_trace_count"] == 0
    assert response["package_review_enabled"] is False
    assert response["handoff_enabled"] is False
    assert response["downstream_unavailable"] == list(
        execution_review.EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE
    )
    assert response["review_notes_recorded"] is True
    assert response["engine_family"] == pass_run.engine_family
    assert response["pass_type"] == PASS_TYPE_SINGLE_ITEM
    assert response["pass_scope"] == "single_item"
    assert response["selected_method_name"] == "cross_correlation"
    assert response["source_gate"] == "source-gate-review"
    assert response["source_dataset_version_ids"] == ["dataset-version-output"]
    assert response["cohort_shape"] == "single_item"

    review_state["trace_summary"]["nested"]["stable"] = False
    review_state["reviewed_output_items"][0]["trace_status"] = "mutated"
    review_state["source_dataset_version_ids"].append("mutated-dataset")
    assert response["trace_summary"]["nested"]["stable"] is True
    assert response["reviewed_output_items"][0]["trace_status"] == "resolved"
    assert response["source_dataset_version_ids"] == ["dataset-version-output"]


def _analysis_run(
    method_name: str = "structural_break",
    *,
    caveats: list[dict] | None = None,
    assumptions: list[dict] | None = None,
    artifacts: list[dict] | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        analysis_run_id="analysis-run-caveats",
        dataset_version_id="dataset-version-caveats",
        method_name=method_name,
        status="completed",
        parameters_json={},
        window_scope_json={},
    )
    for caveat in caveats or []:
        run.caveats.append(CaveatNote(analysis_run_id=run.analysis_run_id, **caveat))
    for assumption in assumptions or []:
        run.assumptions.append(AssumptionCheck(analysis_run_id=run.analysis_run_id, **assumption))
    for artifact in artifacts or []:
        run.artifacts.append(AnalysisArtifact(analysis_run_id=run.analysis_run_id, **artifact))
    return run


_EMPTY_CAVEAT_PROJECTION = {
    "caveats": [],
    "assumption_checks": [],
    "caveat_count": 0,
    "assumption_check_count": 0,
    "outcome_summary": None,
}


def _leaf_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, None
            yield from _leaf_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _leaf_values(item)
    else:
        yield None, value


def _assert_text_only_projection(projection: dict) -> None:
    forbidden_keys = {"storage_ref", "raw_storage_ref", "artifacts", "payload", "metadata_json", "values", "observed", "residual", "breakpoints"}
    for key, leaf in _leaf_values({k: projection[k] for k in ("caveats", "assumption_checks", "outcome_summary")}):
        if key is not None:
            assert key not in forbidden_keys, key
        else:
            assert leaf is None or isinstance(leaf, (str, bool)), leaf


def test_result_caveat_projection_projects_text_only_caveats_and_checks() -> None:
    run = _analysis_run(
        caveats=[
            {"caveat_type": "penalty_sensitivity", "severity": "medium", "message": "series_a: penalty=2 (source=explicit)."},
            {"caveat_type": "nonstationary_break_interpretation", "severity": "high", "message": "series_a: breaks may reflect trend."},
        ],
        assumptions=[
            {
                "assumption_name": "minimum_segment_length",
                "check_method": "ruptures_segment_lengths",
                "check_result": "pass",
                "severity": "medium",
                "notes": "series_a: segment_lengths=[18, 18]",
            }
        ],
        artifacts=[
            {
                "artifact_type": "structural_break_result",
                "title": "Structural breaks: series_a",
                "storage_ref": "/private/should-not-leak/structural_break_result.json",
                "summary": "series_a: structural break metadata",
                "metadata_json": {"break_count": 1},
            }
        ],
    )

    projection = execution_review.result_caveat_projection(run)

    assert projection == {
        "caveats": [
            {"caveat_type": "penalty_sensitivity", "severity": "medium", "message": "series_a: penalty=2 (source=explicit)."},
            {"caveat_type": "nonstationary_break_interpretation", "severity": "high", "message": "series_a: breaks may reflect trend."},
        ],
        "assumption_checks": [
            {
                "assumption_name": "minimum_segment_length",
                "check_method": "ruptures_segment_lengths",
                "check_result": "pass",
                "severity": "medium",
                "notes": "series_a: segment_lengths=[18, 18]",
            }
        ],
        "caveat_count": 2,
        "assumption_check_count": 1,
        "outcome_summary": None,
    }
    assert list(projection) == list(execution_review.RESULT_CAVEAT_PROJECTION_KEYS) + ["outcome_summary"]
    serialized = json.dumps(projection, sort_keys=True)
    assert "storage_ref" not in serialized
    assert "should-not-leak" not in serialized
    assert "break_count" not in serialized
    _assert_text_only_projection(projection)


def test_result_caveat_projection_returns_empty_shape_for_missing_or_bare_run() -> None:
    assert execution_review.result_caveat_projection(None) == _EMPTY_CAVEAT_PROJECTION
    assert execution_review.result_caveat_projection(_analysis_run()) == _EMPTY_CAVEAT_PROJECTION
    assert execution_review.result_caveat_projection(_analysis_run("decomposition")) == _EMPTY_CAVEAT_PROJECTION


def test_result_caveat_projection_labels_zero_break_outcome_as_expected_artifact_absence() -> None:
    zero_break_run = _analysis_run(
        caveats=[
            {"caveat_type": "penalty_sensitivity", "severity": "medium", "message": "series_a: penalty=8 (source=explicit)."},
            {"caveat_type": "no_breakpoints_detected", "severity": "low", "message": "series_a: no structural breakpoints were detected at penalty=8 using model=l2."},
            {"caveat_type": "no_breakpoints_detected", "severity": "low", "message": "series_b: no structural breakpoints were detected at penalty=8 using model=l2."},
            {"caveat_type": "no_structural_break_artifacts", "severity": "medium", "message": "No variables produced structural break artifacts."},
        ],
        assumptions=[
            {
                "assumption_name": "minimum_segment_length",
                "check_method": "ruptures_segment_lengths",
                "check_result": "pass",
                "severity": "medium",
                "notes": "series_a: segment_lengths=[36]",
            }
        ],
    )

    projection = execution_review.result_caveat_projection(zero_break_run)

    assert projection["caveat_count"] == 4
    assert projection["outcome_summary"] == {
        "outcome": "no_breakpoints_detected",
        "artifact_absence_expected": True,
        "message": execution_review.NO_BREAKPOINTS_OUTCOME_MESSAGE,
    }
    assert "expected" in projection["outcome_summary"]["message"]
    assert "not a failure" in projection["outcome_summary"]["message"]
    _assert_text_only_projection(projection)

    break_found_run = _analysis_run(
        caveats=[
            {"caveat_type": "no_breakpoints_detected", "severity": "low", "message": "series_b: no structural breakpoints were detected at penalty=8 using model=l2."},
        ],
        artifacts=[
            {
                "artifact_type": "structural_break_result",
                "title": "Structural breaks: series_a",
                "storage_ref": "artifacts/structural_break_result.json",
                "summary": "series_a: structural break metadata",
                "metadata_json": {},
            }
        ],
    )
    assert execution_review.result_caveat_projection(break_found_run)["outcome_summary"] is None

    decomposition_without_artifacts = _analysis_run(
        "decomposition",
        caveats=[{"caveat_type": "no_decomposition_artifacts", "severity": "medium", "message": "No variables met STL decomposition prerequisites."}],
    )
    assert execution_review.result_caveat_projection(decomposition_without_artifacts)["outcome_summary"] is None


def test_execution_result_review_response_echoes_caveat_projection_with_get_defaults() -> None:
    pass_run = _pass_run()
    base_review_state = {
        "review_state": "execution_result_review_approved",
        "operator_decision": "approved",
        "review_record_ref": "layer3://review/pass-run-review",
        "trace_summary": {"reviewed_item_count": 0},
        "reviewed_output_items": [],
        "unresolved_trace_count": 0,
        "review_notes": None,
    }
    projection = {
        "caveats": [{"caveat_type": "insufficient_observations", "severity": "high", "message": "value: STL requires at least 24 observations for this workflow."}],
        "assumption_checks": [
            {"assumption_name": "sufficient_observations", "check_method": "row_count_threshold", "check_result": "fail", "severity": "high", "notes": "value: n=3"}
        ],
        "caveat_count": 1,
        "assumption_check_count": 1,
    }

    def _response(review_state: dict) -> dict:
        return execution_review.execution_result_review_response(
            request_id="request-review-caveats",
            status="recorded",
            session_id=pass_run.session_id,
            analysis_plan_id=pass_run.analysis_plan_id,
            preview_id="preview-review",
            preview_hash="hash-review",
            pass_run=pass_run,
            analysis_run_id="analysis-run-review",
            review_state=review_state,
        )

    echoed = _response({**base_review_state, **projection})
    assert echoed["caveats"] == projection["caveats"]
    assert echoed["assumption_checks"] == projection["assumption_checks"]
    assert echoed["caveat_count"] == 1
    assert echoed["assumption_check_count"] == 1
    assert "outcome_summary" not in echoed
    projection["caveats"][0]["message"] = "mutated"
    assert echoed["caveats"][0]["message"].startswith("value: STL requires")

    defaulted = _response(dict(base_review_state))
    assert defaulted["caveats"] == []
    assert defaulted["assumption_checks"] == []
    assert defaulted["caveat_count"] == 0
    assert defaulted["assumption_check_count"] == 0
