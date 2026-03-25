import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base  # noqa: E402
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage  # noqa: E402
from app.services import nrc_aps_content_index  # noqa: E402


def test_chunking_boundary_and_small_text_contract():
    policy = nrc_aps_content_index.normalize_chunking_policy(
        {
            "content_chunk_size_chars": 200,
            "content_chunk_overlap_chars": 20,
            "content_chunk_min_chars": 50,
        }
    )
    assert policy["chunk_size_chars"] == 200
    assert policy["chunk_overlap_chars"] == 20
    assert policy["min_chunk_chars"] == 50

    empty_chunks = nrc_aps_content_index.chunk_document_units(
        ordered_units=[],
        chunk_size_chars=policy["chunk_size_chars"],
        chunk_overlap_chars=policy["chunk_overlap_chars"],
        min_chunk_chars=policy["min_chunk_chars"],
    )
    assert empty_chunks == []

    short_text = "abcd"
    short_chunks = nrc_aps_content_index.chunk_document_units(
        ordered_units=[
            {
                "page_number": 1,
                "unit_kind": "text_block",
                "text": short_text,
                "start_char": 0,
                "end_char": len(short_text),
            }
        ],
        chunk_size_chars=policy["chunk_size_chars"],
        chunk_overlap_chars=policy["chunk_overlap_chars"],
        min_chunk_chars=policy["min_chunk_chars"],
    )
    assert short_chunks == []

    min_text = "x" * policy["min_chunk_chars"]
    min_chunks = nrc_aps_content_index.chunk_document_units(
        ordered_units=[
            {
                "page_number": 3,
                "unit_kind": "pdf_text_block",
                "text": min_text,
                "start_char": 0,
                "end_char": len(min_text),
            }
        ],
        chunk_size_chars=policy["chunk_size_chars"],
        chunk_overlap_chars=policy["chunk_overlap_chars"],
        min_chunk_chars=policy["min_chunk_chars"],
    )
    assert len(min_chunks) == 1
    assert min_chunks[0]["start_char"] == 0
    assert min_chunks[0]["end_char"] == policy["min_chunk_chars"]
    assert min_chunks[0]["page_start"] == 3
    assert min_chunks[0]["page_end"] == 3
    assert min_chunks[0]["unit_kind"] == "pdf_text_block"

    oversized_chunks = nrc_aps_content_index.chunk_document_units(
        ordered_units=[
            {
                "page_number": 1,
                "unit_kind": "pdf_text_block",
                "text": "y" * 240,
                "start_char": 0,
                "end_char": 240,
            }
        ],
        chunk_size_chars=200,
        chunk_overlap_chars=20,
        min_chunk_chars=50,
    )
    assert len(oversized_chunks) == 1


def test_search_semantics_and_ranking_are_deterministic():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        doc = ApsContentDocument(
            content_id="content-a",
            content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="sha-a",
            normalized_char_count=32,
            chunk_count=2,
            content_status="indexed",
            media_type="application/pdf",
            document_class="born_digital_pdf",
            quality_status="limited",
            page_count=1,
            diagnostics_ref="/tmp/diag.json",
        )
        db.add(doc)
        db.add(
            ApsContentChunk(
                content_id="content-a",
                chunk_id="chunk-a0",
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=20,
                chunk_text="alpha beta alpha",
                chunk_text_sha256="sha-chunk-a0",
                page_start=1,
                page_end=1,
                unit_kind="pdf_text_block",
                quality_status="limited",
            )
        )
        db.add(
            ApsContentChunk(
                content_id="content-a",
                chunk_id="chunk-a1",
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=1,
                start_char=20,
                end_char=40,
                chunk_text="alpha beta",
                chunk_text_sha256="sha-chunk-a1",
                page_start=1,
                page_end=1,
                unit_kind="pdf_text_block",
                quality_status="limited",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-a",
                run_id="run-1",
                target_id="target-1",
                accession_number="ML1",
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                content_units_ref="/tmp/content-a.json",
                normalized_text_ref="/tmp/content-a.txt",
                normalized_text_sha256="sha-a",
                blob_ref="/tmp/content-a.bin",
                blob_sha256="blob-a",
                download_exchange_ref="/tmp/download-a.json",
                discovery_ref="/tmp/discovery-a.json",
                selection_ref="/tmp/selection-a.json",
                diagnostics_ref="/tmp/diag.json",
            )
        )
        db.commit()

        result = nrc_aps_content_index.search_content_units(
            db,
            query_text="ALPHA beta",
            run_id="run-1",
            limit=10,
            offset=0,
        )
        assert result["query_tokens"] == ["alpha", "beta"]
        assert result["total"] == 2
        assert result["items"][0]["chunk_id"] == "chunk-a0"
        assert result["items"][0]["summed_term_frequency"] == 3
        assert result["items"][0]["page_start"] == 1
        assert result["items"][0]["unit_kind"] == "pdf_text_block"
        assert result["items"][0]["effective_content_type"] == "application/pdf"
        assert result["items"][1]["chunk_id"] == "chunk-a1"

        try:
            nrc_aps_content_index.search_content_units(db, query_text="   ", run_id="run-1")
            assert False, "empty query should fail"
        except ValueError as exc:
            assert str(exc) == "empty_query"
    finally:
        db.close()


def test_low_quality_processed_document_is_preserved_but_not_chunked(tmp_path: Path):
    normalized_text_ref = tmp_path / "weak.txt"
    diagnostics_ref = tmp_path / "weak_diag.json"
    normalized_text_ref.write_text("short weak text", encoding="utf-8")
    diagnostics_ref.write_text(
        '{"ordered_units":[{"page_number":1,"unit_kind":"text_block","text":"short weak text","start_char":0,"end_char":15}],"page_count":1,"quality_status":"weak","document_class":"text_plain","effective_content_type":"text/plain"}',
        encoding="utf-8",
    )
    payload = nrc_aps_content_index.build_content_units_payload_from_target_artifact(
        run_id="run-low-quality",
        target_id="target-low-quality",
        target_artifact_payload={
            "run_id": "run-low-quality",
            "target_id": "target-low-quality",
            "accession_number": "ML-WEAK-1",
            "pipeline_mode": "hydrate_process",
            "outcome_status": "processed",
            "evidence": {"discovery_ref": "/tmp/discovery.json", "selection_ref": "/tmp/selection.json"},
            "download": {
                "blob_ref": "/tmp/blob.bin",
                "blob_sha256": "blob-sha",
                "download_exchange_ref": "/tmp/download.json",
            },
            "extraction": {
                "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
                "normalized_text_ref": str(normalized_text_ref),
                "normalized_text_sha256": "norm-sha",
                "effective_content_type": "text/plain",
                "document_class": "text_plain",
                "quality_status": "weak",
                "page_count": 1,
                "diagnostics_ref": str(diagnostics_ref),
            },
        },
        source_metadata_ref="/tmp/meta.json",
        artifact_storage_dir=tmp_path,
        chunking_policy=nrc_aps_content_index.normalize_chunking_policy({}),
    )
    assert payload["content_status"] == nrc_aps_content_index.APS_CONTENT_STATUS_LOW_QUALITY_TEXT
    assert payload["chunk_count"] == 0
    assert payload["chunks"] == []
    assert payload["diagnostics_ref"] == str(diagnostics_ref)


def test_download_only_reprocessing_persists_diagnostics_ref(tmp_path: Path):
    blob_path = tmp_path / "born_digital.pdf"
    blob_path.write_bytes((FIXTURE_DIR / "born_digital.pdf").read_bytes())

    payload = nrc_aps_content_index.build_content_units_payload_from_target_artifact(
        run_id="run-download-only",
        target_id="target-download-only",
        target_artifact_payload={
            "run_id": "run-download-only",
            "target_id": "target-download-only",
            "accession_number": "ML-DOWNLOAD-1",
            "pipeline_mode": "download_only",
            "outcome_status": "downloaded",
            "evidence": {"discovery_ref": "/tmp/discovery.json", "selection_ref": "/tmp/selection.json"},
            "download": {
                "blob_ref": str(blob_path),
                "blob_sha256": "blob-sha",
                "download_exchange_ref": "/tmp/download.json",
                "content_type": "application/pdf",
            },
            "extraction": {},
        },
        source_metadata_ref="/tmp/meta.json",
        artifact_storage_dir=tmp_path,
        chunking_policy=nrc_aps_content_index.normalize_chunking_policy({}),
    )

    assert payload["content_status"] == nrc_aps_content_index.APS_CONTENT_STATUS_INDEXED
    assert payload["chunk_count"] == 1
    assert payload["diagnostics_ref"]
    assert Path(payload["diagnostics_ref"]).exists()


def test_visual_page_refs_propagates_through_content_units_payload(tmp_path: Path):
    normalized_text_ref = tmp_path / "norm.txt"
    diagnostics_ref = tmp_path / "diag.json"
    normalized_text_ref.write_text("visual test content " * 20, encoding="utf-8")
    visual_refs = [{"page": 1, "ref": "/tmp/page_1.png"}, {"page": 2, "ref": "/tmp/page_2.png"}]
    diagnostics_ref.write_text(
        '{"ordered_units":[{"page_number":1,"unit_kind":"text_block","text":"'
        + "visual test content " * 20
        + '","start_char":0,"end_char":400}],"page_count":2,"quality_status":"limited","document_class":"born_digital_pdf","effective_content_type":"application/pdf","visual_page_refs":[{"page":1,"ref":"/tmp/page_1.png"},{"page":2,"ref":"/tmp/page_2.png"}]}',
        encoding="utf-8",
    )
    payload = nrc_aps_content_index.build_content_units_payload_from_target_artifact(
        run_id="run-vpr",
        target_id="target-vpr",
        target_artifact_payload={
            "run_id": "run-vpr",
            "target_id": "target-vpr",
            "accession_number": "ML-VPR-1",
            "pipeline_mode": "hydrate_process",
            "outcome_status": "processed",
            "evidence": {"discovery_ref": "/tmp/discovery.json", "selection_ref": "/tmp/selection.json"},
            "download": {"blob_ref": "/tmp/blob.bin", "blob_sha256": "blob-sha"},
            "extraction": {
                "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
                "normalized_text_ref": str(normalized_text_ref),
                "normalized_text_sha256": "norm-sha",
                "effective_content_type": "application/pdf",
                "document_class": "born_digital_pdf",
                "quality_status": "limited",
                "page_count": 2,
                "diagnostics_ref": str(diagnostics_ref),
                "visual_page_refs": visual_refs,
            },
        },
        source_metadata_ref="/tmp/meta.json",
        artifact_storage_dir=tmp_path,
        chunking_policy=nrc_aps_content_index.normalize_chunking_policy({}),
    )
    assert payload["visual_page_refs"] == visual_refs


def test_visual_page_refs_defaults_to_empty_list_when_absent(tmp_path: Path):
    normalized_text_ref = tmp_path / "norm.txt"
    diagnostics_ref = tmp_path / "diag.json"
    normalized_text_ref.write_text("no visual refs " * 20, encoding="utf-8")
    diagnostics_ref.write_text(
        '{"ordered_units":[{"page_number":1,"unit_kind":"text_block","text":"'
        + "no visual refs " * 20
        + '","start_char":0,"end_char":300}],"page_count":1,"quality_status":"limited","document_class":"text_plain","effective_content_type":"text/plain"}',
        encoding="utf-8",
    )
    payload = nrc_aps_content_index.build_content_units_payload_from_target_artifact(
        run_id="run-novpr",
        target_id="target-novpr",
        target_artifact_payload={
            "run_id": "run-novpr",
            "target_id": "target-novpr",
            "accession_number": "ML-NOVPR-1",
            "pipeline_mode": "hydrate_process",
            "outcome_status": "processed",
            "evidence": {"discovery_ref": "/tmp/discovery.json", "selection_ref": "/tmp/selection.json"},
            "download": {"blob_ref": "/tmp/blob.bin", "blob_sha256": "blob-sha"},
            "extraction": {
                "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
                "normalized_text_ref": str(normalized_text_ref),
                "normalized_text_sha256": "norm-sha",
                "effective_content_type": "text/plain",
                "document_class": "text_plain",
                "quality_status": "limited",
                "page_count": 1,
                "diagnostics_ref": str(diagnostics_ref),
            },
        },
        source_metadata_ref="/tmp/meta.json",
        artifact_storage_dir=tmp_path,
        chunking_policy=nrc_aps_content_index.normalize_chunking_policy({}),
    )
    assert payload["visual_page_refs"] == []


# ---------------------------------------------------------------------------
# DB persistence & response-surface roundtrip tests
# ---------------------------------------------------------------------------


def test_upsert_persists_visual_page_refs_to_db():
    """visual_page_refs in payload must survive upsert and appear in the DB column."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        visual_refs = [
            {"page_number": 2, "visual_page_class": "diagram_or_visual", "status": "preserved", "width": 612.0, "height": 792.0},
            {"page_number": 5, "visual_page_class": "diagram_or_visual", "status": "visual_capture_failed"},
        ]
        nrc_aps_content_index.upsert_content_units_payload(
            db,
            payload={
                "content_id": "content-vpr-db",
                "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
                "content_status": "indexed",
                "chunk_count": 0,
                "chunks": [],
                "visual_page_refs": visual_refs,
                "run_id": "run-vpr-db",
                "target_id": "target-vpr-db",
                "accession_number": "ML-VPR-DB",
            },
        )
        db.commit()

        doc = db.query(ApsContentDocument).filter(ApsContentDocument.content_id == "content-vpr-db").first()
        assert doc is not None
        assert doc.visual_page_refs_json is not None
        stored = json.loads(doc.visual_page_refs_json)
        assert stored == visual_refs
    finally:
        db.close()


def test_upsert_stores_null_when_visual_page_refs_absent():
    """When payload has no visual_page_refs key, the DB column should be NULL."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        nrc_aps_content_index.upsert_content_units_payload(
            db,
            payload={
                "content_id": "content-no-vpr",
                "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                "content_status": "indexed",
                "chunk_count": 0,
                "chunks": [],
                "run_id": "run-no-vpr",
                "target_id": "target-no-vpr",
            },
        )
        db.commit()

        doc = db.query(ApsContentDocument).filter(ApsContentDocument.content_id == "content-no-vpr").first()
        assert doc is not None
        assert doc.visual_page_refs_json is None
    finally:
        db.close()


def test_deserialize_visual_page_refs_safe_degradation():
    """NULL, empty, and invalid JSON all degrade safely to []."""
    deser = nrc_aps_content_index._deserialize_visual_page_refs
    assert deser(None) == []
    assert deser("") == []
    assert deser("not-json") == []
    assert deser("42") == []
    assert deser('{"a": 1}') == []
    valid = [{"page_number": 1, "status": "preserved"}]
    assert deser(json.dumps(valid)) == valid


def test_visual_page_refs_roundtrips_through_search_response_surface():
    """Prove visual_page_refs survives: payload → upsert → DB → search_content_units response."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        visual_refs = [
            {"page_number": 3, "visual_page_class": "diagram_or_visual", "status": "preserved", "width": 612.0, "height": 792.0},
        ]
        nrc_aps_content_index.upsert_content_units_payload(
            db,
            payload={
                "content_id": "content-rt",
                "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
                "content_status": "indexed",
                "normalized_text_sha256": "sha-rt",
                "normalized_char_count": 40,
                "chunk_count": 1,
                "effective_content_type": "application/pdf",
                "document_class": "born_digital_pdf",
                "quality_status": "limited",
                "page_count": 5,
                "visual_page_refs": visual_refs,
                "chunks": [
                    {
                        "chunk_id": "chunk-rt-0",
                        "chunk_ordinal": 0,
                        "start_char": 0,
                        "end_char": 40,
                        "chunk_text": "reactor coolant system diagram analysis",
                        "chunk_text_sha256": "sha-chunk-rt-0",
                        "page_start": 1,
                        "page_end": 5,
                        "unit_kind": "pdf_text_block",
                    }
                ],
                "run_id": "run-rt",
                "target_id": "target-rt",
                "accession_number": "ML-RT-1",
                "content_units_ref": "/tmp/content-rt.json",
                "normalized_text_ref": "/tmp/content-rt.txt",
                "blob_ref": "/tmp/content-rt.bin",
                "blob_sha256": "blob-rt",
            },
        )
        db.commit()

        # Prove response-surface: search_content_units includes visual_page_refs
        result = nrc_aps_content_index.search_content_units(
            db,
            query_text="reactor coolant",
            run_id="run-rt",
            limit=10,
            offset=0,
        )
        assert result["total"] >= 1
        item = result["items"][0]
        assert "visual_page_refs" in item
        assert item["visual_page_refs"] == visual_refs

        # Prove response-surface: list_content_units_for_run includes visual_page_refs
        list_result = nrc_aps_content_index.list_content_units_for_run(
            db,
            run_id="run-rt",
            limit=10,
            offset=0,
        )
        assert list_result["total"] >= 1
        list_item = list_result["items"][0]
        assert "visual_page_refs" in list_item
        assert list_item["visual_page_refs"] == visual_refs
    finally:
        db.close()


def test_legacy_rows_without_visual_page_refs_degrade_to_empty_list():
    """Rows created before the column (NULL value) must return [] in API responses."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        # Manually create models without setting visual_page_refs_json (simulates legacy row)
        doc = ApsContentDocument(
            content_id="content-legacy",
            content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            content_status="indexed",
            chunk_count=1,
            page_count=1,
        )
        db.add(doc)
        db.add(
            ApsContentChunk(
                content_id="content-legacy",
                chunk_id="chunk-legacy-0",
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=0,
                start_char=0,
                end_char=10,
                chunk_text="legacy text",
                chunk_text_sha256="sha-legacy",
            )
        )
        db.add(
            ApsContentLinkage(
                content_id="content-legacy",
                run_id="run-legacy",
                target_id="target-legacy",
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            )
        )
        db.commit()

        # visual_page_refs_json is NULL — should degrade to []
        assert doc.visual_page_refs_json is None

        result = nrc_aps_content_index.search_content_units(
            db, query_text="legacy", run_id="run-legacy", limit=10, offset=0
        )
        assert result["total"] >= 1
        assert result["items"][0]["visual_page_refs"] == []
    finally:
        db.close()
