from app.services.layer3_source_boundary import (
    SUPPORTED_SOURCE_CLASSES,
    UNSUPPORTED_SOURCE_CLASSES,
    requested_source_classes,
    source_class_from_material_candidate_id,
    source_class_from_source_candidate_id,
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
