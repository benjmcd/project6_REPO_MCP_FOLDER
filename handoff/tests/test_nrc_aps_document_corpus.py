import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.db.session import Base  # noqa: E402
from app.services import nrc_aps_content_index  # noqa: E402
from app.services import nrc_aps_document_processing  # noqa: E402
from tests.support_nrc_aps_doc_corpus import corpus_ocr_available, expected_behavior, fixture_bytes, fixture_path, manifest_entries  # noqa: E402


def _entry_id(entry: dict[str, object]) -> str:
    return str(entry.get("fixture_id") or "unknown")


def _in_memory_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return Session()


def _download_only_target_artifact(*, blob_path: Path, entry: dict[str, object]) -> dict[str, object]:
    return {
        "run_id": f"run-{_entry_id(entry)}",
        "target_id": f"target-{_entry_id(entry)}",
        "accession_number": f"ML-{_entry_id(entry).upper()}",
        "pipeline_mode": "download_only",
        "outcome_status": "downloaded",
        "evidence": {
            "discovery_ref": "/tmp/discovery.json",
            "selection_ref": "/tmp/selection.json",
        },
        "download": {
            "blob_ref": str(blob_path),
            "blob_sha256": "blob-sha",
            "download_exchange_ref": "/tmp/download.json",
            "content_type": str(entry.get("declared_content_type") or ""),
        },
        "extraction": {},
    }


def test_manifest_entries_are_resolvable_and_well_formed():
    entries = manifest_entries()
    assert entries
    fixture_ids = set()
    for entry in entries:
        fixture_id = _entry_id(entry)
        assert fixture_id not in fixture_ids
        fixture_ids.add(fixture_id)
        assert str(entry.get("fixture_role") or "").strip() in {"regression_only", "representative_lower_bound"}
        assert fixture_path(entry).exists()
        assert str(entry.get("declared_content_type") or "").strip()
        expectation = expected_behavior(entry, ocr_available=True)
        assert "expects_success" in expectation


@pytest.mark.parametrize("entry", manifest_entries(), ids=_entry_id)
def test_manifest_entries_drive_document_processing_contract(entry: dict[str, object]):
    expectation = expected_behavior(entry, ocr_available=corpus_ocr_available())
    content = fixture_bytes(entry)
    if not expectation["expects_success"]:
        with pytest.raises(ValueError, match=str(expectation["expected_failure"])):
            nrc_aps_document_processing.process_document(
                content=content,
                declared_content_type=str(entry.get("declared_content_type") or ""),
            )
        return

    result = nrc_aps_document_processing.process_document(
        content=content,
        declared_content_type=str(entry.get("declared_content_type") or ""),
    )
    assert result["document_class"] == expectation["expected_document_class"]
    assert result["quality_status"] == expectation["expected_quality_status"]
    assert Path(result["normalized_text_ref"]).exists() if "normalized_text_ref" in result else True
    normalized_text = str(result["normalized_text"] or "").lower()
    for query in expectation["gold_queries"]:
        assert query in normalized_text
    for code in expectation["expected_degradation_codes"]:
        assert code in list(result.get("degradation_codes") or [])


@pytest.mark.parametrize("entry", manifest_entries(), ids=_entry_id)
def test_manifest_entries_drive_content_index_searchability(entry: dict[str, object], tmp_path: Path):
    expectation = expected_behavior(entry, ocr_available=corpus_ocr_available())
    blob_path = tmp_path / str(entry.get("path") or "fixture.bin")
    blob_path.write_bytes(fixture_bytes(entry))

    if not expectation["expects_success"]:
        with pytest.raises(ValueError, match=str(expectation["expected_failure"])):
            nrc_aps_document_processing.process_document(
                content=blob_path.read_bytes(),
                declared_content_type=str(entry.get("declared_content_type") or ""),
            )
        return

    payload = nrc_aps_content_index.build_content_units_payload_from_target_artifact(
        run_id=f"run-{_entry_id(entry)}",
        target_id=f"target-{_entry_id(entry)}",
        target_artifact_payload=_download_only_target_artifact(blob_path=blob_path, entry=entry),
        source_metadata_ref="/tmp/meta.json",
        artifact_storage_dir=tmp_path,
        chunking_policy=nrc_aps_content_index.normalize_chunking_policy({}),
    )
    session = _in_memory_session()
    try:
        nrc_aps_content_index.upsert_content_units_payload(session, payload=payload)
        session.commit()
        if expectation["searchable_expected"]:
            assert payload["content_status"] == nrc_aps_content_index.APS_CONTENT_STATUS_INDEXED
            assert int(payload["chunk_count"]) >= 1
            for query in expectation["gold_queries"]:
                search = nrc_aps_content_index.search_content_units(
                    session,
                    query_text=query,
                    run_id=f"run-{_entry_id(entry)}",
                    limit=10,
                    offset=0,
                )
                assert search["total"] >= 1
        else:
            assert payload["content_status"] in {
                nrc_aps_content_index.APS_CONTENT_STATUS_LOW_QUALITY_TEXT,
                nrc_aps_content_index.APS_CONTENT_STATUS_UNUSABLE_TEXT,
                nrc_aps_content_index.APS_CONTENT_STATUS_EMPTY_NORMALIZED_TEXT,
            }
            assert int(payload["chunk_count"]) == 0
    finally:
        session.close()
