"""DB-backed proof tests for diagnostics_ref persistence and cross-run semantics.

Proves:
1. upsert_content_units_payload() persists diagnostics_ref to both document and linkage
2. Cross-run / deduplicated-content scenario: same content_id across multiple runs
   does NOT expose stale document-level diagnostics_ref through the serializer
3. Linkage-only authority: serializer returns None when linkage has no diagnostics_ref,
   even when document row has a value from another run
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
)
from app.services.nrc_aps_content_index import (
    APS_CHUNKING_CONTRACT_ID,
    APS_CONTENT_CONTRACT_ID,
    _serialize_index_row,
    upsert_content_units_payload,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def _seed_run_and_target(db, *, run_id: str, target_id: str):
    """Create the required ConnectorRun and ConnectorRunTarget rows."""
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc-adams-aps",
        source_system="nrc_adams",
        source_mode="aps",
        status="completed",
    )
    db.add(run)
    db.flush()
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=0,
    )
    db.add(target)
    db.flush()


def _make_payload(*, run_id: str, target_id: str, diagnostics_ref: str | None, content_id: str = "cid-shared") -> dict:
    # chunk_id is content-scoped (not run-scoped) because chunks are deduplicated
    # along with the document row. All runs sharing a content_id share chunks.
    return {
        "schema_id": "aps.content_units.v2",
        "schema_version": 1,
        "run_id": run_id,
        "target_id": target_id,
        "accession_number": "ML000000001",
        "content_contract_id": APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": "aps_text_normalization_v2",
        "content_id": content_id,
        "content_status": "indexed",
        "quality_status": "strong",
        "effective_content_type": "application/pdf",
        "document_class": "inspection_report",
        "page_count": 5,
        "diagnostics_ref": diagnostics_ref,
        "normalized_text_ref": "/tmp/test_norm.txt",
        "normalized_text_sha256": "a" * 64,
        "normalized_char_count": 100,
        "blob_ref": "/tmp/test.pdf",
        "blob_sha256": "b" * 64,
        "chunk_count": 1,
        "chunks": [
            {
                "chunk_id": "chunk-shared-0",
                "chunk_ordinal": 0,
                "start_char": 0,
                "end_char": 50,
                "chunk_text": "Test content for persistence proof.",
                "chunk_text_sha256": "c" * 64,
                "page_start": 1,
                "page_end": 1,
                "unit_kind": "pdf_paragraph",
            }
        ],
    }


class TestDiagnosticsRefDirectPersistence(unittest.TestCase):
    """Phase 4 proof #1: upsert_content_units_payload persists diagnostics_ref
    to both ApsContentDocument and ApsContentLinkage."""

    def test_document_and_linkage_both_persist_diagnostics_ref(self):
        db = _make_session()
        _seed_run_and_target(db, run_id="run-A", target_id="tgt-A")

        payload = _make_payload(
            run_id="run-A",
            target_id="tgt-A",
            diagnostics_ref="/artifacts/run-A_tgt-A_diag.json",
        )
        upsert_content_units_payload(db, payload=payload)
        db.commit()

        doc = db.query(ApsContentDocument).filter_by(content_id="cid-shared").first()
        linkage = db.query(ApsContentLinkage).filter_by(content_id="cid-shared", run_id="run-A").first()

        self.assertIsNotNone(doc)
        self.assertEqual(doc.diagnostics_ref, "/artifacts/run-A_tgt-A_diag.json")
        self.assertIsNotNone(linkage)
        self.assertEqual(linkage.diagnostics_ref, "/artifacts/run-A_tgt-A_diag.json")


class TestCrossRunDiagnosticsRefSafety(unittest.TestCase):
    """Phase 4 proof #4: cross-run / deduplicated-content scenario.

    Scenario:
    - Run A upserts content_id X with diagnostics_ref = "diag-A"
    - Run B upserts same content_id X with diagnostics_ref = "diag-B"
    - Document row is overwritten to "diag-B" (deduplication)
    - When serializing run A's linkage, result must use linkage-A's value,
      not the document's now-stale value for run A.
    """

    def test_cross_run_document_overwrite_does_not_leak_into_serializer(self):
        db = _make_session()
        _seed_run_and_target(db, run_id="run-A", target_id="tgt-A")
        _seed_run_and_target(db, run_id="run-B", target_id="tgt-B")

        # Run A upserts content_id "cid-shared"
        payload_a = _make_payload(
            run_id="run-A",
            target_id="tgt-A",
            diagnostics_ref="/artifacts/run-A_tgt-A_diag.json",
        )
        upsert_content_units_payload(db, payload=payload_a)
        db.commit()

        # Run B upserts the same content_id and overwrites the document row.
        payload_b = _make_payload(
            run_id="run-B",
            target_id="tgt-B",
            diagnostics_ref="/artifacts/run-B_tgt-B_diag.json",
        )
        upsert_content_units_payload(db, payload=payload_b)
        db.commit()

        # Verify document row was overwritten to run B's value
        doc = db.query(ApsContentDocument).filter_by(content_id="cid-shared").first()
        self.assertEqual(doc.diagnostics_ref, "/artifacts/run-B_tgt-B_diag.json")

        # Verify linkage A still has its own value
        linkage_a = db.query(ApsContentLinkage).filter_by(
            content_id="cid-shared", run_id="run-A"
        ).first()
        self.assertEqual(linkage_a.diagnostics_ref, "/artifacts/run-A_tgt-A_diag.json")

        # Verify linkage B has its own value
        linkage_b = db.query(ApsContentLinkage).filter_by(
            content_id="cid-shared", run_id="run-B"
        ).first()
        self.assertEqual(linkage_b.diagnostics_ref, "/artifacts/run-B_tgt-B_diag.json")

        # Chunks are content-scoped; both runs share the same chunk
        chunk = db.query(ApsContentChunk).filter_by(
            content_id="cid-shared",
            chunk_id="chunk-shared-0",
        ).first()
        self.assertIsNotNone(chunk)

        # Serializer for run A must return run A's diagnostics_ref,
        # not the document's now-run-B value.
        row_a = _serialize_index_row(linkage=linkage_a, document=doc, chunk=chunk)
        self.assertEqual(row_a["diagnostics_ref"], "/artifacts/run-A_tgt-A_diag.json")

        # Serializer for run B returns run B's diagnostics_ref
        row_b = _serialize_index_row(linkage=linkage_b, document=doc, chunk=chunk)
        self.assertEqual(row_b["diagnostics_ref"], "/artifacts/run-B_tgt-B_diag.json")

    def test_absent_linkage_diagnostics_ref_returns_none_not_document_value(self):
        """If linkage has no diagnostics_ref, serializer must return None.

        It must not return the document-level value, which may belong to
        a different run.
        """
        db = _make_session()
        _seed_run_and_target(db, run_id="run-A", target_id="tgt-A")
        _seed_run_and_target(db, run_id="run-B", target_id="tgt-B")

        # Run A upserts with diagnostics_ref
        payload_a = _make_payload(
            run_id="run-A",
            target_id="tgt-A",
            diagnostics_ref="/artifacts/run-A_diag.json",
        )
        upsert_content_units_payload(db, payload=payload_a)
        db.commit()

        # Run B upserts same content_id WITHOUT diagnostics_ref
        payload_b = _make_payload(
            run_id="run-B",
            target_id="tgt-B",
            diagnostics_ref=None,
        )
        upsert_content_units_payload(db, payload=payload_b)
        db.commit()

        doc = db.query(ApsContentDocument).filter_by(content_id="cid-shared").first()
        linkage_b = db.query(ApsContentLinkage).filter_by(
            content_id="cid-shared", run_id="run-B"
        ).first()
        chunk = db.query(ApsContentChunk).filter_by(
            content_id="cid-shared",
            chunk_id="chunk-shared-0",
        ).first()

        # Document may have run-B's None or run-A's value depending on overwrite.
        # The point: serializer must return None for run-B, not whatever document has.
        self.assertIsNone(linkage_b.diagnostics_ref)

        row_b = _serialize_index_row(linkage=linkage_b, document=doc, chunk=chunk)
        self.assertIsNone(row_b["diagnostics_ref"])


if __name__ == "__main__":
    unittest.main()
