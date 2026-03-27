import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ApsRetrievalChunk,
    ConnectorRun,
    ConnectorRunTarget,
)
from app.services import aps_retrieval_plane
from app.services import aps_retrieval_plane_contract as contract
from app.services.nrc_aps_content_index import APS_CHUNKING_CONTRACT_ID, APS_CONTENT_CONTRACT_ID


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def _seed_run_and_target(db, *, run_id: str, target_id: str) -> None:
    db.add(
        ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc-adams-aps",
            source_system="nrc_adams",
            source_mode="aps",
            status="completed",
        )
    )
    db.flush()
    db.add(
        ConnectorRunTarget(
            connector_run_target_id=target_id,
            connector_run_id=run_id,
            ordinal=0,
            status="completed",
        )
    )
    db.flush()


def _seed_canonical_triplet(
    db,
    *,
    run_id: str = "run-001",
    target_id: str = "target-001",
    content_id: str = "content-001",
    chunk_id: str = "chunk-001",
    chunk_text: str = "Sample APS retrieval content.",
    chunk_quality_status: str | None = None,
    linkage_diagnostics_ref: str | None = "diagnostics-linkage.json",
    document_diagnostics_ref: str | None = "diagnostics-document.json",
    visual_page_refs_json: str | None = None,
    updated_at: datetime | None = None,
):
    if updated_at is None:
        updated_at = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
    visual_refs = visual_page_refs_json or json.dumps([{"page_number": 1, "status": "preserved"}])
    _seed_run_and_target(db, run_id=run_id, target_id=target_id)
    document = ApsContentDocument(
        content_id=content_id,
        content_contract_id=APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
        normalization_contract_id="aps_text_normalization_v2",
        normalized_text_sha256="d" * 64,
        normalized_char_count=len(chunk_text),
        chunk_count=1,
        content_status="indexed",
        media_type="application/pdf",
        document_class="inspection_report",
        quality_status="strong",
        page_count=2,
        diagnostics_ref=document_diagnostics_ref,
        visual_page_refs_json=visual_refs,
        updated_at=updated_at,
        created_at=updated_at - timedelta(minutes=5),
    )
    chunk = ApsContentChunk(
        content_id=content_id,
        chunk_id=chunk_id,
        content_contract_id=APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
        chunk_ordinal=0,
        start_char=0,
        end_char=len(chunk_text),
        chunk_text=chunk_text,
        chunk_text_sha256=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
        page_start=1,
        page_end=1,
        unit_kind="pdf_paragraph",
        quality_status=chunk_quality_status,
        updated_at=updated_at,
        created_at=updated_at - timedelta(minutes=4),
    )
    linkage = ApsContentLinkage(
        content_id=content_id,
        run_id=run_id,
        target_id=target_id,
        accession_number="ML25001A001",
        content_contract_id=APS_CONTENT_CONTRACT_ID,
        chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
        content_units_ref="content_units.json",
        normalized_text_ref="normalized.txt",
        normalized_text_sha256="d" * 64,
        blob_ref="blob.pdf",
        blob_sha256="b" * 64,
        download_exchange_ref="download.json",
        discovery_ref="discovery.json",
        selection_ref="selection.json",
        diagnostics_ref=linkage_diagnostics_ref,
        created_at=updated_at - timedelta(minutes=3),
    )
    db.add_all([document, chunk, linkage])
    db.flush()
    return linkage, document, chunk


class TestApsRetrievalPlane(unittest.TestCase):
    def test_build_expected_row_uses_linkage_diagnostics_only(self):
        db = _make_session()
        linkage, document, chunk = _seed_canonical_triplet(db)
        row = aps_retrieval_plane.build_expected_retrieval_row(
            linkage=linkage,
            document=document,
            chunk=chunk,
        )
        self.assertEqual(row["retrieval_contract_id"], contract.APS_RETRIEVAL_CONTRACT_ID)
        self.assertEqual(row["diagnostics_ref"], "diagnostics-linkage.json")
        self.assertEqual(row["search_text"], chunk.chunk_text)
        self.assertEqual(row["quality_status"], "strong")
        self.assertEqual(row["visual_page_refs_json"], '[{"page_number":1,"status":"preserved"}]')

    def test_rebuild_is_stable_when_source_signature_is_unchanged(self):
        db = _make_session()
        _seed_canonical_triplet(db)
        first_rebuilt_at = datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc)
        first = aps_retrieval_plane.rebuild_retrieval_plane_for_run(
            db,
            run_id="run-001",
            rebuilt_at=first_rebuilt_at,
        )
        row = db.query(ApsRetrievalChunk).one()
        first_signature = row.source_signature_sha256
        self.assertEqual(first["inserted"], 1)
        self.assertEqual(_as_utc(row.rebuilt_at), first_rebuilt_at)

        second = aps_retrieval_plane.rebuild_retrieval_plane_for_run(
            db,
            run_id="run-001",
            rebuilt_at=first_rebuilt_at + timedelta(minutes=5),
        )
        row = db.query(ApsRetrievalChunk).one()
        self.assertEqual(second["unchanged"], 1)
        self.assertEqual(_as_utc(row.rebuilt_at), first_rebuilt_at)
        self.assertEqual(row.source_signature_sha256, first_signature)

    def test_rebuild_updates_row_when_source_signature_changes(self):
        db = _make_session()
        _seed_canonical_triplet(db)
        aps_retrieval_plane.rebuild_retrieval_plane_for_run(
            db,
            run_id="run-001",
            rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
        )
        row = db.query(ApsRetrievalChunk).one()
        original_signature = row.source_signature_sha256

        changed_text = "Changed APS retrieval content."
        chunk = db.query(ApsContentChunk).one()
        chunk.chunk_text = changed_text
        chunk.chunk_text_sha256 = hashlib.sha256(changed_text.encode("utf-8")).hexdigest()
        chunk.end_char = len(changed_text)
        chunk.updated_at = datetime(2026, 3, 27, 13, 0, tzinfo=timezone.utc)
        db.flush()

        rebuilt_at = datetime(2026, 3, 27, 13, 5, tzinfo=timezone.utc)
        result = aps_retrieval_plane.rebuild_retrieval_plane_for_run(
            db,
            run_id="run-001",
            rebuilt_at=rebuilt_at,
        )
        row = db.query(ApsRetrievalChunk).one()
        self.assertEqual(result["updated"], 1)
        self.assertEqual(row.chunk_text, changed_text)
        self.assertEqual(_as_utc(row.rebuilt_at), rebuilt_at)
        self.assertNotEqual(row.source_signature_sha256, original_signature)


if __name__ == "__main__":
    unittest.main()
