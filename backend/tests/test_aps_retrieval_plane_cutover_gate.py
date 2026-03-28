from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(BACKEND))

from app.db.session import Base  # noqa: E402
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ConnectorRun, ConnectorRunTarget  # noqa: E402
from app.services import aps_retrieval_plane  # noqa: E402
from app.services import nrc_aps_content_index  # noqa: E402


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
        "accession_number": "ML-GATE-001",
        "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
        "content_id": content_id,
        "content_status": "indexed",
        "normalized_char_count": 29,
        "normalized_text_ref": "normalized.txt",
        "normalized_text_sha256": "norm-gate-sha",
        "effective_content_type": "application/pdf",
        "document_class": "inspection_report",
        "quality_status": "strong",
        "page_count": 2,
        "diagnostics_ref": "diagnostics-linkage.json",
        "blob_ref": "blob.pdf",
        "blob_sha256": "blob-gate-sha",
        "download_exchange_ref": "download.json",
        "discovery_ref": "discovery.json",
        "selection_ref": "selection.json",
        "visual_page_refs": [{"page_number": 1, "status": "preserved"}],
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _seed_canonical_rows(db, *, artifact_dir: Path, run_id: str = "run-gate-001") -> str:
    target_id = "target-gate-001"
    content_id = "content-gate-001"
    _seed_run_and_target(db, run_id=run_id, target_id=target_id)
    chunks = [
        {
            "chunk_id": "chunk-gate-000",
            "chunk_ordinal": 0,
            "start_char": 0,
            "end_char": 16,
            "chunk_text": "alpha beta alpha",
            "chunk_text_sha256": "sha-gate-000",
            "page_start": 1,
            "page_end": 1,
            "unit_kind": "pdf_paragraph",
        },
        {
            "chunk_id": "chunk-gate-001",
            "chunk_ordinal": 1,
            "start_char": 17,
            "end_char": 27,
            "chunk_text": "alpha beta",
            "chunk_text_sha256": "sha-gate-001",
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
            normalized_text_sha256="norm-gate-sha",
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
            accession_number="ML-GATE-001",
            content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=content_units_ref,
            normalized_text_ref="normalized.txt",
            normalized_text_sha256="norm-gate-sha",
            blob_ref="blob.pdf",
            blob_sha256="blob-gate-sha",
            download_exchange_ref="download.json",
            discovery_ref="discovery.json",
            selection_ref="selection.json",
            diagnostics_ref="diagnostics-linkage.json",
        )
    )
    db.commit()
    return run_id


class TestApsRetrievalPlaneCutoverGate(unittest.TestCase):
    def _run_gate(self, *, db_path: Path, storage_dir: Path, run_id: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        env["STORAGE_DIR"] = str(storage_dir)
        env["DB_INIT_MODE"] = "none"
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "nrc_aps_retrieval_cutover_gate.py"),
                "--run-id",
                run_id,
            ],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_gate_wrapper_returns_zero_without_writing_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "gate.db"
            storage_dir = temp_root / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
            db = Session()
            try:
                run_id = _seed_canonical_rows(db, artifact_dir=storage_dir)
                aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                    db,
                    run_id=run_id,
                    rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
                )
                db.commit()
            finally:
                db.close()
                engine.dispose()
            result = self._run_gate(db_path=db_path, storage_dir=storage_dir, run_id=run_id)
            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            self.assertEqual(list(temp_root.glob("*.json")), [])

    def test_gate_wrapper_fails_closed_without_writing_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "gate.db"
            storage_dir = temp_root / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
            db = Session()
            try:
                run_id = _seed_canonical_rows(db, artifact_dir=storage_dir)
            finally:
                db.close()
                engine.dispose()
            result = self._run_gate(db_path=db_path, storage_dir=storage_dir, run_id=run_id)
            self.assertEqual(result.returncode, 1, msg=result.stderr or result.stdout)
            self.assertEqual(list(temp_root.glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
