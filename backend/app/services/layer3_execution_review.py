from __future__ import annotations

from typing import Any

from app.models.models import L3PassRun
from app.services.layer3_workbench_error import Layer3WorkbenchError

EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID = "layer3.execution_result_review_state.v1"
EXECUTION_RESULT_REVIEW_ITEM_TYPES = frozenset(
    {
        "datum",
        "fact",
        "finding",
        "insight",
        "caveat",
        "contradiction",
        "unsupported_claim",
        "generated_narrative",
    }
)


def execution_result_review_from_pass_run(pass_run: L3PassRun) -> dict[str, Any] | None:
    state = (pass_run.summary_json or {}).get("execution_result_review")
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID:
        return None
    return state


def normalize_result_review_items(
    *,
    items: Any,
    session_id: str,
    analysis_plan_id: str,
    pass_run: L3PassRun,
    analysis_run_id: str | None,
    output_metadata_summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    if items is None:
        return [], 0
    if not isinstance(items, list):
        raise Layer3WorkbenchError(
            "reviewed_output_items_malformed",
            "reviewed_output_items must be a list when supplied.",
            status="invalid",
            blocked_fields=["reviewed_output_items"],
        )
    if len(items) > 50:
        raise Layer3WorkbenchError(
            "reviewed_output_items_too_large",
            "This result-review tranche admits at most 50 reviewed output items.",
            status="invalid",
            blocked_fields=["reviewed_output_items"],
        )

    normalized: list[dict[str, Any]] = []
    unresolved = 0
    required_trace = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "output_payload_ref": output_metadata_summary["output_payload_ref"],
    }
    if analysis_run_id:
        required_trace["analysis_run_id"] = analysis_run_id

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            unresolved += 1
            normalized.append(
                {
                    "index": index,
                    "item_type": None,
                    "trace_status": "unresolved",
                    "missing_trace_fields": ["item"],
                }
            )
            continue
        item_type = str(item.get("item_type") or "").strip()
        trace = item.get("trace") if isinstance(item.get("trace"), dict) else {}
        missing = [
            field
            for field, expected in required_trace.items()
            if str(trace.get(field) or "").strip() != str(expected)
        ]
        if item_type not in EXECUTION_RESULT_REVIEW_ITEM_TYPES:
            missing.append("item_type")
        if missing:
            unresolved += 1
        normalized.append(
            {
                "index": index,
                "item_ref": str(item.get("item_ref") or item.get("output_item_ref") or f"item-{index}"),
                "item_type": item_type or None,
                "trace_status": "resolved" if not missing else "unresolved",
                "missing_trace_fields": sorted(set(missing)),
            }
        )
    return normalized, unresolved


def result_review_trace_summary(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run: L3PassRun,
    analysis_run_id: str | None,
    output_metadata_summary: dict[str, Any],
    reviewed_items: list[dict[str, Any]],
    unresolved_trace_count: int,
) -> dict[str, Any]:
    summary = pass_run.summary_json or {}
    return {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "analysis_run_id": analysis_run_id,
        "output_payload_ref": output_metadata_summary["output_payload_ref"],
        "analysis_set_id": output_metadata_summary.get("analysis_set_id"),
        "dataset_version_id": output_metadata_summary.get("dataset_version_id") or summary.get("dataset_version_id"),
        "selected_method_name": output_metadata_summary.get("selected_method_name") or summary.get("selected_method_name"),
        "pass_scope": output_metadata_summary.get("pass_scope") or summary.get("pass_scope"),
        "source_dataset_version_ids": (
            list(output_metadata_summary.get("source_dataset_version_ids"))
            if isinstance(output_metadata_summary.get("source_dataset_version_ids"), list)
            else (
                list(summary.get("source_dataset_version_ids_json"))
                if isinstance(summary.get("source_dataset_version_ids_json"), list)
                else []
            )
        ),
        "cohort_shape": output_metadata_summary.get("cohort_shape") or summary.get("cohort_shape"),
        "requested_method_name": output_metadata_summary.get("requested_method_name") or summary.get("requested_method_name"),
        "requested_method_source": output_metadata_summary.get("requested_method_source") or summary.get("requested_method_source"),
        "artifact_count": output_metadata_summary.get("artifact_count", 0),
        "artifact_types": list(output_metadata_summary.get("artifact_types") or []),
        "source_gate": output_metadata_summary.get("source_gate"),
        "reviewed_item_count": len(reviewed_items),
        "unresolved_trace_count": unresolved_trace_count,
    }
