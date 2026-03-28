from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import Base  # noqa: E402
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ApsRetrievalChunk, ConnectorRun, ConnectorRunTarget  # noqa: E402
from app.services import aps_retrieval_plane  # noqa: E402
from app.services import aps_retrieval_plane_cutover_validation  # noqa: E402
from app.services import aps_retrieval_plane_read  # noqa: E402
from app.services import nrc_aps_content_index  # noqa: E402


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
            artifact_surface="documents",
            ordinal=0,
            status="completed",
        )
    )
    db.flush()


def _write_content_units_artifact(
    *,
    base_dir: Path,
    run_id: str,
    target_id: str,
    content_id: str,
    chunks: list[dict[str, object]],
) -> str:
    path = base_dir / f"{run_id}_{target_id}_content_units.json"
    payload = {
        "schema_id": nrc_aps_content_index.APS_CONTENT_UNITS_SCHEMA_ID,
        "schema_version": nrc_aps_content_index.APS_CONTENT_INDEX_SCHEMA_VERSION,
        "run_id": run_id,
        "target_id": target_id,
        "accession_number": "ML-CUTOVER-001",
        "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
        "content_id": content_id,
        "content_status": "indexed",
        "normalized_char_count": 29,
        "normalized_text_ref": "normalized.txt",
        "normalized_text_sha256": "norm-cutover-sha",
        "effective_content_type": "application/pdf",
        "document_class": "inspection_report",
        "quality_status": "strong",
        "page_count": 2,
        "diagnostics_ref": "diagnostics-linkage.json",
        "blob_ref": "blob.pdf",
        "blob_sha256": "blob-cutover-sha",
        "download_exchange_ref": "download.json",
        "discovery_ref": "discovery.json",
        "selection_ref": "selection.json",
        "visual_page_refs": [{"page_number": 1, "status": "preserved"}],
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _seed_canonical_rows(db, *, artifact_dir: Path, run_id: str = "run-cutover-001") -> str:
    target_id = "target-cutover-001"
    content_id = "content-cutover-001"
    _seed_run_and_target(db, run_id=run_id, target_id=target_id)
    chunks = [
        {
            "chunk_id": "chunk-cutover-000",
            "chunk_ordinal": 0,
            "start_char": 0,
            "end_char": 16,
            "chunk_text": "alpha beta alpha",
            "chunk_text_sha256": "sha-cutover-000",
            "page_start": 1,
            "page_end": 1,
            "unit_kind": "pdf_paragraph",
        },
        {
            "chunk_id": "chunk-cutover-001",
            "chunk_ordinal": 1,
            "start_char": 17,
            "end_char": 27,
            "chunk_text": "alpha beta",
            "chunk_text_sha256": "sha-cutover-001",
            "page_start": 1,
            "page_end": 1,
            "unit_kind": "pdf_paragraph",
        },
    ]
    content_units_ref = _write_content_units_artifact(
        base_dir=artifact_dir,
        run_id=run_id,
        target_id=target_id,
        content_id=content_id,
        chunks=chunks,
    )
    db.add(
        ApsContentDocument(
            content_id=content_id,
            content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256="norm-cutover-sha",
            normalized_char_count=29,
            chunk_count=2,
            content_status="indexed",
            media_type="application/pdf",
            document_class="inspection_report",
            quality_status="strong",
            page_count=2,
            diagnostics_ref="diagnostics-document.json",
            visual_page_refs_json=json.dumps([{"page_number": 1, "status": "preserved"}]),
            updated_at=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
        )
    )
    for chunk in chunks:
        db.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=str(chunk["chunk_id"]),
                content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=int(chunk["chunk_ordinal"]),
                start_char=int(chunk["start_char"]),
                end_char=int(chunk["end_char"]),
                chunk_text=str(chunk["chunk_text"]),
                chunk_text_sha256=str(chunk["chunk_text_sha256"]),
                page_start=int(chunk["page_start"]),
                page_end=int(chunk["page_end"]),
                unit_kind=str(chunk["unit_kind"]),
                quality_status="strong",
                updated_at=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
            )
        )
    db.add(
        ApsContentLinkage(
            content_id=content_id,
            run_id=run_id,
            target_id=target_id,
            accession_number="ML-CUTOVER-001",
            content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=content_units_ref,
            normalized_text_ref="normalized.txt",
            normalized_text_sha256="norm-cutover-sha",
            blob_ref="blob.pdf",
            blob_sha256="blob-cutover-sha",
            download_exchange_ref="download.json",
            discovery_ref="discovery.json",
            selection_ref="selection.json",
            diagnostics_ref="diagnostics-linkage.json",
        )
    )
    db.commit()
    return run_id


class TestApsRetrievalPlaneCutoverValidation(unittest.TestCase):
    def test_cutover_validation_returns_match_for_list_and_search(self):
        db = _make_session()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(temp_dir))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            report = aps_retrieval_plane_cutover_validation.validate_retrieval_cutover_for_run(db, run_id=run_id)
        self.assertTrue(report["passed"])
        self.assertEqual(report["overall_verdict"], aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_MATCH)
        self.assertEqual([check["verdict"] for check in report["checks"]], ["match", "match"])

    def test_cutover_validation_returns_payload_mismatch(self):
        db = _make_session()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(temp_dir))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            row = db.query(ApsRetrievalChunk).filter(ApsRetrievalChunk.run_id == run_id, ApsRetrievalChunk.chunk_id == "chunk-cutover-001").one()
            row.blob_ref = "blob-mutated.pdf"
            db.commit()
            report = aps_retrieval_plane_cutover_validation.validate_retrieval_cutover_for_run(db, run_id=run_id, query_text="alpha beta")
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["overall_verdict"],
            aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_PAYLOAD_MISMATCH,
        )
        self.assertIn("payload_mismatch", [check["verdict"] for check in report["checks"]])

    def test_cutover_validation_returns_order_mismatch(self):
        db = _make_session()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(temp_dir))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            original_list = aps_retrieval_plane_read.list_content_units_for_run
            original_search = aps_retrieval_plane_read.search_content_units

            def _reversed_items(payload: dict[str, object]) -> dict[str, object]:
                clone = dict(payload)
                clone["items"] = list(reversed([dict(item or {}) for item in (payload.get("items") or [])]))
                return clone

            def _list_override(inner_db, *, run_id: str, limit: int = 50, offset: int = 0):
                return _reversed_items(original_list(inner_db, run_id=run_id, limit=limit, offset=offset))

            def _search_override(inner_db, *, query_text: str, run_id: str | None = None, limit: int = 20, offset: int = 0):
                return _reversed_items(original_search(inner_db, query_text=query_text, run_id=run_id, limit=limit, offset=offset))

            aps_retrieval_plane_read.list_content_units_for_run = _list_override
            aps_retrieval_plane_read.search_content_units = _search_override
            try:
                report = aps_retrieval_plane_cutover_validation.validate_retrieval_cutover_for_run(db, run_id=run_id, query_text="alpha beta")
            finally:
                aps_retrieval_plane_read.list_content_units_for_run = original_list
                aps_retrieval_plane_read.search_content_units = original_search
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["overall_verdict"],
            aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_ORDER_MISMATCH,
        )
        self.assertEqual([check["verdict"] for check in report["checks"]], ["order_mismatch", "order_mismatch"])

    def test_cutover_validation_fails_closed_on_empty_runtime(self):
        db = _make_session()
        report = aps_retrieval_plane_cutover_validation.validate_retrieval_cutover_for_run(db, run_id="run-empty-001")
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["overall_verdict"],
            aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_EMPTY_RUNTIME,
        )
        self.assertEqual([check["verdict"] for check in report["checks"]], ["empty_runtime", "empty_runtime"])

    def test_cutover_validation_fails_closed_when_retrieval_not_materialized(self):
        db = _make_session()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(temp_dir))
            report = aps_retrieval_plane_cutover_validation.validate_retrieval_cutover_for_run(db, run_id=run_id, query_text="alpha beta")
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["overall_verdict"],
            aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED,
        )
        self.assertEqual([check["verdict"] for check in report["checks"]], ["retrieval_not_materialized", "retrieval_not_materialized"])

    def test_cutover_validation_fails_closed_when_retrieval_is_partially_materialized(self):
        db = _make_session()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(temp_dir))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            row = db.query(ApsRetrievalChunk).filter(ApsRetrievalChunk.run_id == run_id, ApsRetrievalChunk.chunk_id == "chunk-cutover-001").one()
            db.delete(row)
            db.commit()
            report = aps_retrieval_plane_cutover_validation.validate_retrieval_cutover_for_run(db, run_id=run_id, query_text="alpha beta")
        self.assertFalse(report["passed"])
        self.assertEqual(
            report["overall_verdict"],
            aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_RETRIEVAL_NOT_MATERIALIZED,
        )
        self.assertEqual([check["verdict"] for check in report["checks"]], ["retrieval_not_materialized", "retrieval_not_materialized"])

    def test_report_writer_is_separate_from_validate_path(self):
        payload = {
            "schema_id": aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_ID,
            "schema_version": aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_PROOF_SCHEMA_VERSION,
            "passed": True,
            "overall_verdict": aps_retrieval_plane_cutover_validation.APS_RETRIEVAL_CUTOVER_VERDICT_MATCH,
            "checks": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "cutover_report.json"
            written_path = aps_retrieval_plane_cutover_validation.write_retrieval_cutover_report(payload, report_path=report_path)
            self.assertEqual(written_path, str(report_path))
            written_payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(written_payload, payload)


if __name__ == "__main__":
    unittest.main()
