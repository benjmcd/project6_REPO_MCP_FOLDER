from app.services.layer3_source_boundary import (
    SUPPORTED_SOURCE_CLASSES,
    UNSUPPORTED_SOURCE_CLASSES,
    requested_source_classes,
    source_class_from_material_candidate_id,
    source_class_from_source_candidate_id,
    source_boundary_contract,
    unsupported_requested,
)


def test_source_boundary_defaults_and_rejects_deferred_source_classes() -> None:
    assert requested_source_classes({}) == ["dataset_version", "aps_content_document"]
    assert requested_source_classes({"source_classes": ("dataset_version", 123)}) == [
        "dataset_version",
        "123",
    ]

    assert unsupported_requested(["dataset_version", "rag_vector_index"]) == [
        "rag_vector_index"
    ]
    assert tuple(UNSUPPORTED_SOURCE_CLASSES) == (
        "rag_vector_index",
        "arbitrary_local_directory",
        "broad_file_upload",
        "web_connector",
        "unbounded_runtime_db",
    )


def test_source_boundary_candidate_id_parsing_is_limited_to_admitted_classes() -> None:
    assert tuple(SUPPORTED_SOURCE_CLASSES) == ("dataset_version", "aps_content_document")
    assert (
        source_class_from_source_candidate_id("src-dataset_version-source123")
        == "dataset_version"
    )
    assert (
        source_class_from_source_candidate_id("src-aps_content_document-source123")
        == "aps_content_document"
    )
    assert source_class_from_source_candidate_id("src-rag_vector_index-source123") is None

    assert (
        source_class_from_material_candidate_id("mat-dataset_version-material123")
        == "dataset_version"
    )
    assert (
        source_class_from_material_candidate_id("mat-aps_content_document-material123")
        == "aps_content_document"
    )
    assert source_class_from_material_candidate_id("mat-web_connector-material123") is None


def test_source_boundary_contract_keeps_deferred_source_expansion_fail_closed() -> None:
    contract = source_boundary_contract()

    assert contract["schema_id"] == "layer3.source_boundary_contract.v1"
    assert contract["mode"] == "supported_source_classes_only"
    assert contract["supported_source_classes"] == [
        "dataset_version",
        "aps_content_document",
    ]
    assert contract["unsupported_source_classes"] == [
        "rag_vector_index",
        "arbitrary_local_directory",
        "broad_file_upload",
        "web_connector",
        "unbounded_runtime_db",
    ]
    assert contract["deferred_capabilities"] == [
        "local_upload_or_directory_source_expansion",
        "broad_file_upload_source_expansion",
        "web_connector_source_expansion",
        "rag_vector_retrieval",
        "unbounded_runtime_db_source_expansion",
    ]
    assert set(contract["forbidden_runtime_fields"]) >= {
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
    }
    assert contract["source_upload_enabled"] is False
    assert contract["local_directory_enabled"] is False
    assert contract["broad_file_upload_enabled"] is False
    assert contract["web_connector_enabled"] is False
    assert contract["rag_vector_enabled"] is False
    assert contract["unbounded_runtime_db_enabled"] is False
    assert contract["requires_later_freeze"] is True
