from __future__ import annotations

from typing import Any, Mapping


PLAN_APPROVAL_FORBIDDEN_FIELDS = frozenset(
    {
        "execute",
        "execution",
        "run",
        "run_analysis",
        "package",
        "package_review",
        "handoff",
        "plan_edits",
        "natural_language_plan",
        "llm_plan",
    }
)
PLAN_REVISION_FORBIDDEN_FIELDS = PLAN_APPROVAL_FORBIDDEN_FIELDS | frozenset(
    {
        "execution_started",
        "create_pass_runs",
        "pass_run_ids",
        "artifact_manifest",
        "result_review",
        "qualitative_plan",
        "hybrid_plan",
        "rag_plan",
        "vector_plan",
    }
)
EXECUTION_SELECTION_FORBIDDEN_FIELDS = frozenset(
    {
        "execute",
        "execution",
        "run",
        "run_analysis",
        "start_execution",
        "analysis_run_id",
        "analysis_run_ids",
        "result_review",
        "results",
        "package",
        "package_review",
        "handoff",
        "artifact_manifest",
        "local_upload",
        "local_directory",
        "rag_plan",
        "vector_plan",
        "qualitative_plan",
        "hybrid_plan",
    }
)


def plan_approval_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in PLAN_APPROVAL_FORBIDDEN_FIELDS if key in payload)


def plan_revision_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in PLAN_REVISION_FORBIDDEN_FIELDS if key in payload)


def execution_selection_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in EXECUTION_SELECTION_FORBIDDEN_FIELDS if key in payload)
