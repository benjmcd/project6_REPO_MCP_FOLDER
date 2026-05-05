from __future__ import annotations

from typing import Any


SUPPORTED_SOURCE_CLASSES = ("dataset_version", "aps_content_document")
UNSUPPORTED_SOURCE_CLASSES = (
    "rag_vector_index",
    "arbitrary_local_directory",
    "broad_file_upload",
    "web_connector",
    "unbounded_runtime_db",
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
