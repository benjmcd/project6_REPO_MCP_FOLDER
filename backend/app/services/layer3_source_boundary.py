from __future__ import annotations

from typing import Any


SOURCE_BOUNDARY_CONTRACT_SCHEMA_ID = "layer3.source_boundary_contract.v1"
SOURCE_BOUNDARY_MODE = "supported_source_classes_plus_operator_source_intake"

SUPPORTED_SOURCE_CLASSES = ("dataset_version", "aps_content_document")
SOURCE_INTAKE_SUPPORTED_MODES = ("operator_single_upload_source_intake",)
UNSUPPORTED_SOURCE_CLASSES = (
    "rag_vector_index",
    "arbitrary_local_directory",
    "broad_file_upload",
    "web_connector",
    "unbounded_runtime_db",
)
SOURCE_EXPANSION_DEFERRED_CAPABILITIES = (
    "local_upload_or_directory_source_expansion",
    "broad_file_upload_source_expansion",
    "web_connector_source_expansion",
    "rag_vector_retrieval",
    "unbounded_runtime_db_source_expansion",
)
SOURCE_BOUNDARY_FORBIDDEN_RUNTIME_FIELDS = (
    "source_upload",
    "local_upload",
    "local_directory",
    "rag_vector_index",
    "rag_plan",
    "vector_plan",
    "web_connector",
    "runtime_db_write",
    "source_expansion",
    "schema_widening",
)


def requested_source_classes(manual_constraints: dict[str, Any]) -> list[str]:
    source_classes = manual_constraints.get("source_classes") or []
    if not source_classes:
        return list(SUPPORTED_SOURCE_CLASSES)
    return [str(item) for item in source_classes]


def unsupported_requested(classes: list[str]) -> list[str]:
    return [item for item in classes if item not in SUPPORTED_SOURCE_CLASSES]


def source_class_from_source_candidate_id(source_candidate_id: str) -> str | None:
    for source_class in SUPPORTED_SOURCE_CLASSES:
        if source_candidate_id.startswith(f"src-{source_class}-"):
            return source_class
    return None


def source_class_from_material_candidate_id(candidate_id: str) -> str | None:
    for source_class in SUPPORTED_SOURCE_CLASSES:
        if candidate_id.startswith(f"mat-{source_class}-"):
            return source_class
    return None


def source_boundary_contract() -> dict[str, Any]:
    return {
        "schema_id": SOURCE_BOUNDARY_CONTRACT_SCHEMA_ID,
        "mode": SOURCE_BOUNDARY_MODE,
        "supported_source_classes": list(SUPPORTED_SOURCE_CLASSES),
        "supported_source_intake_modes": list(SOURCE_INTAKE_SUPPORTED_MODES),
        "unsupported_source_classes": list(UNSUPPORTED_SOURCE_CLASSES),
        "deferred_capabilities": list(SOURCE_EXPANSION_DEFERRED_CAPABILITIES),
        "forbidden_runtime_fields": list(SOURCE_BOUNDARY_FORBIDDEN_RUNTIME_FIELDS),
        "source_upload_enabled": False,
        "source_intake_upload_enabled": True,
        "source_intake_record_enabled": True,
        "source_intake_upload_route": "/api/v1/layer3/source/intake/upload",
        "generic_source_upload_preflight_field_enabled": False,
        "operator_upload_material_preview_enabled": False,
        "operator_upload_material_preview_requires_later_freeze": True,
        "local_directory_enabled": False,
        "broad_file_upload_enabled": False,
        "web_connector_enabled": False,
        "rag_vector_enabled": False,
        "unbounded_runtime_db_enabled": False,
        "requires_later_freeze": True,
    }
