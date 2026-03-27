import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ApsRetrievalChunk, ConnectorRun, ConnectorRunTarget
from app.services import aps_retrieval_plane
from app.services import aps_retrieval_plane_validation
from app.services.nrc_aps_content_index import APS_CHUNKING_CONTRACT_ID, APS_CONTENT_CONTRACT_ID


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


def _seed_canonical_triplet(db, *, run_id: str = "run-001", target_id: str = "target-001"):
    updated_at = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
    _seed_run_and_target(db, run_id=run_id, target_id=target_id)
    chunk_text = "Sample APS retrieval content."
    db.add(
        ApsContentDocument(
            content_id="content-001",
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
            diagnostics_ref="diagnostics-document.json",
            visual_page_refs_json=json.dumps([{"page_number": 1, "status": "preserved"}]),
            updated_at=updated_at,
            created_at=updated_at - timedelta(minutes=5),
        )
    )
    db.add(
        ApsContentChunk(
            content_id="content-001",
            chunk_id="chunk-001",
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
            quality_status="strong",
            updated_at=updated_at,
            created_at=updated_at - timedelta(minutes=4),
        )
    )
    db.add(
        ApsContentLinkage(
            content_id="content-001",
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
            diagnostics_ref="diagnostics-linkage.json",
            created_at=updated_at - timedelta(minutes=3),
        )
    )
    db.flush()


class TestApsRetrievalPlaneValidation(unittest.TestCase):
    def test_validation_passes_when_retrieval_rows_match(self):
        db = _make_session()
        _seed_canonical_triplet(db)
        aps_retrieval_plane.rebuild_retrieval_plane_for_run(
            db,
            run_id="run-001",
            rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
        )
        report = aps_retrieval_plane_validation.validate_retrieval_plane_for_run(db, run_id="run-001")
        self.assertTrue(report["passed"])
        self.assertEqual(report["failure_codes"], [])
        self.assertEqual(report["canonical_row_count"], 1)
        self.assertEqual(report["retrieval_row_count"], 1)

    def test_validation_reports_field_mismatch(self):
        db = _make_session()
        _seed_canonical_triplet(db)
        aps_retrieval_plane.rebuild_retrieval_plane_for_run(
            db,
            run_id="run-001",
            rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
        )
        row = db.query(ApsRetrievalChunk).one()
        row.search_text = "corrupted retrieval search text"
        db.flush()

        report = aps_retrieval_plane_validation.validate_retrieval_plane_for_run(db, run_id="run-001")
        self.assertFalse(report["passed"])
        self.assertIn(aps_retrieval_plane_validation.APS_RETRIEVAL_VALIDATION_FIELD_MISMATCH, report["failure_codes"])
        self.assertEqual(report["field_mismatches"][0]["field"], "search_text")

    def test_validation_fails_closed_on_empty_canonical_scope(self):
        db = _make_session()
        _seed_run_and_target(db, run_id="run-001", target_id="target-001")
        report = aps_retrieval_plane_validation.validate_retrieval_plane_for_run(db, run_id="run-001")
        self.assertFalse(report["passed"])
        self.assertIn(aps_retrieval_plane_validation.APS_RETRIEVAL_VALIDATION_EMPTY_CANONICAL_SCOPE, report["failure_codes"])

    def test_validation_fails_closed_when_retrieval_scope_is_missing(self):
        db = _make_session()
        _seed_canonical_triplet(db)
        report = aps_retrieval_plane_validation.validate_retrieval_plane_for_run(db, run_id="run-001")
        self.assertFalse(report["passed"])
        self.assertIn(aps_retrieval_plane_validation.APS_RETRIEVAL_VALIDATION_EMPTY_RETRIEVAL_SCOPE, report["failure_codes"])


if __name__ == "__main__":
    unittest.main()
