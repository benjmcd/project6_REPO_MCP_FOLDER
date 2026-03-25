import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
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

    empty_chunks = nrc_aps_content_index.chunk_normalized_text(
        normalized_text="",
        chunk_size_chars=policy["chunk_size_chars"],
        chunk_overlap_chars=policy["chunk_overlap_chars"],
    )
    assert empty_chunks == []

    short_text = "abcd"
    short_chunks = nrc_aps_content_index.chunk_normalized_text(
        normalized_text=short_text,
        chunk_size_chars=policy["chunk_size_chars"],
        chunk_overlap_chars=policy["chunk_overlap_chars"],
    )
    assert len(short_chunks) == 1
    assert short_chunks[0]["start_char"] == 0
    assert short_chunks[0]["end_char"] == len(short_text)

    min_text = "x" * policy["min_chunk_chars"]
    min_chunks = nrc_aps_content_index.chunk_normalized_text(
        normalized_text=min_text,
        chunk_size_chars=policy["chunk_size_chars"],
        chunk_overlap_chars=policy["chunk_overlap_chars"],
    )
    assert len(min_chunks) == 1
    assert min_chunks[0]["start_char"] == 0
    assert min_chunks[0]["end_char"] == policy["min_chunk_chars"]


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
            normalization_contract_id="aps_text_normalization_v1",
            normalized_text_sha256="sha-a",
            normalized_char_count=32,
            chunk_count=2,
            content_status="indexed",
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
        assert result["items"][1]["chunk_id"] == "chunk-a1"

        try:
            nrc_aps_content_index.search_content_units(db, query_text="   ", run_id="run-1")
            assert False, "empty query should fail"
        except ValueError as exc:
            assert str(exc) == "empty_query"
    finally:
        db.close()
