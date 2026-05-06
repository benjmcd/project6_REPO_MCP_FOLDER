from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


PREFLIGHT_MANUAL_CONSTRAINT_ALLOWED_FIELDS = frozenset(
    {
        "topics",
        "source_classes",
        "date_bounds",
        "required_artifacts",
        "conflict",
        "conflicts",
    }
)
PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS = frozenset(
    {
        "analysis_run_id",
        "artifact_manifest",
        "broad_file_upload",
        "broad_qualitative_execution",
        "connector_dispatch",
        "create_pass_runs",
        "destination",
        "destination_id",
        "destination_url",
        "download_url",
        "execute",
        "execution",
        "export",
        "frontend_only_durable_state",
        "frontend_state",
        "handoff",
        "hidden_llm_plan",
        "hidden_llm_planning",
        "hybrid_execution",
        "hybrid_plan",
        "local_directory",
        "local_upload",
        "package",
        "package_mutation",
        "package_payload",
        "package_reconstruction",
        "pass_run_ids",
        "provider_public_url",
        "provider_url",
        "public_url",
        "rag_execution",
        "rag_plan",
        "rag_vector_index",
        "rag_vector_retrieval",
        "replacement_package_payloads",
        "runtime_db_write",
        "schema_widening",
        "signed_url",
        "source_expansion",
        "source_upload",
        "vector_plan",
        "web_connector",
    }
)


def manual_constraints_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = payload.get("manual_constraints") or {}
    return dict(value) if isinstance(value, Mapping) else {}


def preflight_manual_constraint_blocked_fields(manual_constraints: Mapping[str, Any]) -> list[str]:
    blocked: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for raw_key, nested_value in value.items():
                key = str(raw_key)
                key_path = f"{path}.{key}" if path else key
                if key in PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS:
                    blocked.append(f"manual_constraints.{key_path}")
                visit(nested_value, key_path)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(manual_constraints, "")
    return sorted(set(blocked))
