from __future__ import annotations

from typing import Any


SOURCE_BOUNDARY_CONTRACT_SCHEMA_ID = "layer3.source_boundary_contract.v1"
SOURCE_BOUNDARY_MODE = "supported_source_classes_plus_operator_source_intake"

SUPPORTED_SOURCE_CLASSES = ("dataset_version", "aps_content_document")
SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_MODE = "source_intake_gate_b_material_admission"
SOURCE_INTAKE_GATE_B_SOURCE_CLASS = "operator_uploaded_single_source"
SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX = "mat-source_intake_record-"
SOURCE_DIRECTORY_GATE_B_MATERIAL_ADMISSION_MODE = "source_directory_ingestion_gate_b_material_admission"
SOURCE_DIRECTORY_GATE_B_SOURCE_CLASS = "server_configured_directory_file"
SOURCE_DIRECTORY_GATE_B_CANDIDATE_PREFIX = "mat-server_configured_directory_file-"
CONNECTOR_SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_MODE = "connector_source_intake_gate_b_material_admission"
CONNECTOR_SOURCE_INTAKE_GATE_B_SOURCE_CLASS = "connector_produced_single_source"
CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX = "mat-connector_source_intake_record-"
ADOPTED_EXTERNAL_GATE_B_SOURCE_CLASS = "adopted_external_single_source"
ADOPTED_EXTERNAL_GATE_B_CANDIDATE_PREFIX = "mat-adopted_source_intake_record-"
SOURCE_INTAKE_SUPPORTED_MODES = (
    "operator_single_upload_source_intake",
    "operator_source_intake_inventory_read_only",
    "operator_source_intake_material_preview_read_only",
    SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_MODE,
    "server_configured_operator_directory_text_table_ingestion",
    SOURCE_DIRECTORY_GATE_B_MATERIAL_ADMISSION_MODE,
    CONNECTOR_SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_MODE,
)
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
    if candidate_id.startswith(SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX):
        return SOURCE_INTAKE_GATE_B_SOURCE_CLASS
    if candidate_id.startswith(SOURCE_DIRECTORY_GATE_B_CANDIDATE_PREFIX):
        return SOURCE_DIRECTORY_GATE_B_SOURCE_CLASS
    if candidate_id.startswith(CONNECTOR_SOURCE_INTAKE_GATE_B_CANDIDATE_PREFIX):
        return CONNECTOR_SOURCE_INTAKE_GATE_B_SOURCE_CLASS
    if candidate_id.startswith(ADOPTED_EXTERNAL_GATE_B_CANDIDATE_PREFIX):
        return ADOPTED_EXTERNAL_GATE_B_SOURCE_CLASS
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
        "source_intake_inventory_route": "/api/v1/layer3/source/intake/inventory",
        "source_intake_material_preview_route": "/api/v1/layer3/source/intake/{source_intake_record_id}/preview",
        "source_intake_gate_b_material_admission_route": "/api/v1/layer3/gate-b/decision",
        "source_intake_gate_b_material_admission_enabled": True,
        "operator_upload_gate_b_admission_requires_later_freeze": False,
        "server_configured_directory_ingestion_enabled": True,
        "server_configured_directory_ingestion_route": (
            "/api/v1/layer3/source/ingestion/server-configured-directory/scan"
        ),
        "server_configured_directory_ingestion_status_route": (
            "/api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}"
        ),
        "server_configured_directory_material_preview_enabled": True,
        "server_configured_directory_material_preview_route": (
            "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview"
        ),
        "server_configured_directory_gate_b_material_admission_route": "/api/v1/layer3/gate-b/decision",
        "server_configured_directory_material_preview_requires_later_freeze": False,
        "server_configured_directory_ingestion_source_family": (
            "server_configured_operator_directory_text_table_source_family"
        ),
        "server_configured_directory_ingestion_config_authority": "LAYER3_SOURCE_INGESTION_DIR",
        "server_configured_directory_ingestion_allowed_extensions": [".csv", ".json", ".txt", ".md"],
        "server_configured_directory_ingestion_direct_child_only": True,
        "generic_source_upload_preflight_field_enabled": False,
        "operator_upload_material_preview_enabled": True,
        "operator_upload_material_preview_requires_later_freeze": False,
        "local_directory_enabled": False,
        "broad_file_upload_enabled": False,
        "web_connector_enabled": False,
        "rag_vector_enabled": False,
        "unbounded_runtime_db_enabled": False,
        "requires_later_freeze": True,
    }
