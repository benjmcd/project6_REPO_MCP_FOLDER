from __future__ import annotations

from app.services import analyst_insight_document_bridge


def test_infer_default_link_keys_prefers_accession_and_page():
    rows = [
        {"accession_number": "ML1", "page_start": 1},
        {"accession_number": "ML1", "page_start": 2},
    ]
    assert analyst_insight_document_bridge.infer_default_link_keys(rows) == ["accession_number", "page_start"]


def test_infer_default_link_keys_fallback():
    rows = [{"content_id": "c1", "chunk_ordinal": 0}]
    assert analyst_insight_document_bridge.infer_default_link_keys(rows) == ["content_id", "chunk_ordinal"]


def test_group_by_target():
    slim = [
        {"target_id": "t-a", "content_id": "1"},
        {"target_id": "t-b", "content_id": "2"},
    ]
    g = analyst_insight_document_bridge.group_by_target(slim)
    assert set(g.keys()) == {"target_t-a", "target_t-b"}
    assert len(g["target_t-a"]) == 1


def test_slim_preserves_lineage_fields():
    raw = {
        "chunk_text": "x" * 600,
        "content_id": "cid",
        "chunk_id": "kid",
        "target_id": "tid",
        "run_id": "rid",
        "accession_number": "ACC",
        "chunk_ordinal": 3,
        "page_start": 2,
        "chunk_text_sha256": "abc",
        "quality_status": "indexed",
    }
    s = analyst_insight_document_bridge.slim_content_unit(raw)
    assert s["layer"] == "document_processing_storage"
    assert s["chunk_text_len"] == 600
    assert len(s["chunk_text_preview"]) <= analyst_insight_document_bridge._TEXT_PREVIEW_CHARS


def test_admissibility_rejected_empty():
    v = {"row_count": 0, "missing_field_issues": [], "outliers": []}
    a = analyst_insight_document_bridge.admissibility_from_validation(v)
    assert a["state"] == "rejected"


def test_admissibility_validated():
    v = {"row_count": 2, "missing_field_issues": [], "outliers": []}
    a = analyst_insight_document_bridge.admissibility_from_validation(v)
    assert a["state"] == "validated"


def test_pipeline_reads_rows_seeded_like_ingestion_layer():
    """End-to-end against in-memory SQLite with ORM rows matching NRC APS index persistence."""
    import tempfile
    from pathlib import Path

    from test_aps_retrieval_plane_read import _make_session, _seed_canonical_rows

    db = _make_session()
    with tempfile.TemporaryDirectory() as temp_dir:
        run_id = _seed_canonical_rows(db, artifact_dir=Path(temp_dir), run_id="run-bridge-db-001")
    out = analyst_insight_document_bridge.run_pipeline_from_document_storage(
        db,
        connector_run_id=run_id,
        material_source="content_index",
        limit=50,
        offset=0,
    )
    assert out["document_storage"]["units_in_window"] >= 1
    assert out["tier1_data_plane"]["database_kind"] == "sqlite"
    assert out["tier1_data_plane"]["database_kind_source"] == "session_engine"
    assert out["tier1_data_plane"]["persistence"] == "tier1_sqlalchemy_session"
    assert "aps_content_chunk" in out["tier1_data_plane"]["tables"]


def test_tier1_metadata_lists_retrieval_tables():
    from app.services import analyst_insight_db_source

    meta = analyst_insight_db_source.tier1_data_plane_metadata(material_source="retrieval_plane")
    assert "aps_retrieval_chunk_v1" in meta["tables"]
