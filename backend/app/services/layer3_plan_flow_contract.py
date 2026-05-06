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
PLAN_REVISION_RECOVERY_FORBIDDEN_FIELDS = PLAN_REVISION_FORBIDDEN_FIELDS | frozenset(
    {
        "approve_plan",
        "approved_plan_supersession",
        "delete_approved_plan",
        "analysis_run_id",
        "package_mutation",
        "connector_dispatch",
        "provider_public_url",
        "source_expansion",
        "browser_persisted_state",
    }
)
APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS = PLAN_REVISION_RECOVERY_FORBIDDEN_FIELDS | frozenset(
    {
        "replacement_plan",
        "reopen_approved_plan",
        "approved_plan_replacement",
        "create_pass_runs",
        "start_execution",
        "destination_connector",
        "destination",
        "local_upload",
        "local_directory",
        "frontend_state",
        "hidden_llm_plan",
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


def plan_revision_recovery_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in PLAN_REVISION_RECOVERY_FORBIDDEN_FIELDS if key in payload)


def approved_plan_cancel_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS if key in payload)


def execution_selection_blocked_fields(payload: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in EXECUTION_SELECTION_FORBIDDEN_FIELDS if key in payload)


def source_classes_from_plan_preview(plan_preview: Mapping[str, Any]) -> list[str]:
    source_classes = set()
    for collection_name in ("admitted_sets", "excluded_sets"):
        for item in plan_preview.get(collection_name) or []:
            source_summary = item.get("source_summary") if isinstance(item, dict) else {}
            for source_class in (source_summary or {}).get("source_classes") or []:
                source_classes.add(str(source_class))
    return sorted(source_classes)
