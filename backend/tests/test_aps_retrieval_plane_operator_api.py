from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models import ApsContentChunk, ApsContentDocument, ApsContentLinkage, ApsRetrievalChunk, ConnectorRun, ConnectorRunTarget  # noqa: E402
from app.services import aps_retrieval_plane  # noqa: E402
from app.services import aps_retrieval_plane_read  # noqa: E402
from app.services import nrc_aps_content_index  # noqa: E402
from main import app  # noqa: E402


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


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
        "accession_number": "ML-API-001",
        "content_contract_id": nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
        "chunking_contract_id": nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
        "normalization_contract_id": nrc_aps_content_index.APS_NORMALIZATION_CONTRACT_ID,
        "content_id": content_id,
        "content_status": "indexed",
        "normalized_char_count": 29,
        "normalized_text_ref": "normalized.txt",
        "normalized_text_sha256": "norm-api-sha",
        "effective_content_type": "application/pdf",
        "document_class": "inspection_report",
        "quality_status": "strong",
        "page_count": 2,
        "diagnostics_ref": "diagnostics-linkage.json",
        "blob_ref": "blob.pdf",
        "blob_sha256": "blob-api-sha",
        "download_exchange_ref": "download.json",
        "discovery_ref": "discovery.json",
        "selection_ref": "selection.json",
        "visual_page_refs": [{"page_number": 1, "status": "preserved"}],
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _seed_canonical_rows(db, *, artifact_dir: Path, run_id: str = "run-api-001") -> str:
    target_id = "target-api-001"
    content_id = "content-api-001"
    _seed_run_and_target(db, run_id=run_id, target_id=target_id)
    chunks = [
        {
            "chunk_id": "chunk-api-000",
            "chunk_ordinal": 0,
            "start_char": 0,
            "end_char": 16,
            "chunk_text": "alpha beta alpha",
            "chunk_text_sha256": "sha-api-000",
            "page_start": 1,
            "page_end": 1,
            "unit_kind": "pdf_paragraph",
        },
        {
            "chunk_id": "chunk-api-001",
            "chunk_ordinal": 1,
            "start_char": 17,
            "end_char": 27,
            "chunk_text": "alpha beta",
            "chunk_text_sha256": "sha-api-001",
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
            normalized_text_sha256="norm-api-sha",
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
            accession_number="ML-API-001",
            content_contract_id=nrc_aps_content_index.APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=nrc_aps_content_index.APS_CHUNKING_CONTRACT_ID,
            content_units_ref=content_units_ref,
            normalized_text_ref="normalized.txt",
            normalized_text_sha256="norm-api-sha",
            blob_ref="blob.pdf",
            blob_sha256="blob-api-sha",
            download_exchange_ref="download.json",
            discovery_ref="discovery.json",
            selection_ref="selection.json",
            diagnostics_ref="diagnostics-linkage.json",
        )
    )
    db.commit()
    return run_id


class TestApsRetrievalPlaneOperatorApi(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_operator_routes_match_public_routes_after_rebuild(self):
        db = TestingSessionLocal()
        try:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(self.temp_dir.name))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            db.commit()
        finally:
            db.close()

        public_list = client.get(f"/api/v1/connectors/runs/{run_id}/content-units")
        operator_list = client.get(f"/api/v1/connectors/runs/{run_id}/_operator/retrieval-content-units")
        assert public_list.status_code == 200, public_list.text
        assert operator_list.status_code == 200, operator_list.text
        assert operator_list.json() == public_list.json()

        search_payload = {"query": "alpha beta", "run_id": run_id, "limit": 10, "offset": 0}
        public_search = client.post("/api/v1/connectors/nrc-adams-aps/content-search", json=search_payload)
        operator_search = client.post("/api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search", json=search_payload)
        assert public_search.status_code == 200, public_search.text
        assert operator_search.status_code == 200, operator_search.text
        assert operator_search.json() == public_search.json()

    def test_operator_routes_fail_closed_and_public_routes_remain_canonical(self):
        db = TestingSessionLocal()
        try:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(self.temp_dir.name))
        finally:
            db.close()

        public_list = client.get(f"/api/v1/connectors/runs/{run_id}/content-units")
        operator_list = client.get(f"/api/v1/connectors/runs/{run_id}/_operator/retrieval-content-units")
        assert public_list.status_code == 200, public_list.text
        assert operator_list.status_code == 409, operator_list.text
        assert operator_list.json()["detail"] == {
            "code": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_CODE,
            "message": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_MESSAGE,
        }

        search_payload = {"query": "alpha beta", "run_id": run_id, "limit": 10, "offset": 0}
        public_search = client.post("/api/v1/connectors/nrc-adams-aps/content-search", json=search_payload)
        operator_search = client.post("/api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search", json=search_payload)
        assert public_search.status_code == 200, public_search.text
        assert public_search.json()["total"] == 2
        assert operator_search.status_code == 409, operator_search.text
        assert operator_search.json()["detail"] == {
            "code": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_CODE,
            "message": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_MESSAGE,
        }

    def test_operator_routes_return_409_for_partial_materialization(self):
        db = TestingSessionLocal()
        try:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(self.temp_dir.name))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            row = (
                db.query(ApsRetrievalChunk)
                .filter(ApsRetrievalChunk.run_id == run_id, ApsRetrievalChunk.chunk_id == "chunk-api-001")
                .one()
            )
            db.delete(row)
            db.commit()
        finally:
            db.close()

        operator_list = client.get(f"/api/v1/connectors/runs/{run_id}/_operator/retrieval-content-units")
        assert operator_list.status_code == 409, operator_list.text
        assert operator_list.json()["detail"] == {
            "code": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_CODE,
            "message": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_MESSAGE,
        }

        operator_search = client.post(
            "/api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search",
            json={"query": "alpha beta", "run_id": run_id, "limit": 10, "offset": 0},
        )
        assert operator_search.status_code == 409, operator_search.text
        assert operator_search.json()["detail"] == {
            "code": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_CODE,
            "message": aps_retrieval_plane_read.RETRIEVAL_NOT_MATERIALIZED_MESSAGE,
        }

    def test_operator_search_without_run_id_remains_supported(self):
        db = TestingSessionLocal()
        try:
            run_id = _seed_canonical_rows(db, artifact_dir=Path(self.temp_dir.name))
            aps_retrieval_plane.rebuild_retrieval_plane_for_run(
                db,
                run_id=run_id,
                rebuilt_at=datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc),
            )
            db.commit()
        finally:
            db.close()

        response = client.post(
            "/api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search",
            json={"query": "alpha beta", "limit": 10, "offset": 0},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["query_tokens"] == ["alpha", "beta"]
        assert payload["total"] == 2
        assert payload["items"][0]["chunk_id"] == "chunk-api-000"


if __name__ == "__main__":
    unittest.main()
