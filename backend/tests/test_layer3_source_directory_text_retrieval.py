from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import ConnectorRun, ConnectorRunTarget, L3MaterialSnapshot, L3OutputPackage
from app.services.layer3_source_directory_text_index import (
    SourceDirectoryTextIndexError,
    source_directory_material_text_index,
)
from app.services.layer3_source_directory_text_retrieval import (
    SourceDirectoryTextRetrievalError,
    source_directory_material_text_retrieval,
)
from main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", "")
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.layer3_session_factory = session_local
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _scan_payload(client_request_id: str = "source-directory-retrieval-scan") -> dict[str, str]:
    return {
        "client_request_id": client_request_id,
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _write_retrieval_source_dir(root: Path) -> None:
    root.mkdir()
    lines = ["alpha beta beta lead\n"]
    lines.extend(f"context filler line {index}\n" for index in range(1, 42))
    lines.append("alpha beta tail\n")
    (root / "retrieval.txt").write_text("".join(lines), encoding="utf-8")


def _material_preview_payload(scan_body: dict, relative_name: str = "retrieval.txt") -> dict[str, str]:
    file_record = next(item for item in scan_body["files"] if item["relative_name"] == relative_name)
    return {
        "client_request_id": f"source-directory-material-preview-{relative_name}",
        "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
        "source_ingestion_file_id": file_record["source_ingestion_file_id"],
        "file_identity_hash": file_record["file_identity_hash"],
        "authority_basis_hash": file_record["authority_basis_hash"],
    }


def _approve_source_directory_file(client: TestClient, scan_body: dict) -> dict[str, str]:
    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    candidate = preview_body["material_candidate"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "source-directory-retrieval-gate-b",
            "preflight_id": "preflight-source-directory-retrieval",
            "source_set_id": scan_body["source_ingestion_batch_id"],
            "material_preview_id": preview_body["material_preview_id"],
            "material_preview_hash": preview_body["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": candidate,
                }
            ],
        },
    )
    assert gate_b.status_code == 200
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == gate_b.json()["session_id"])
            .one()
        )
        return {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "payload_hash": snapshot.payload_hash,
            "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
            "source_ingestion_file_id": candidate["payload"]["source_ingestion_file_id"],
            "content_sha256": candidate["payload"]["content_sha256"],
            "file_identity_hash": candidate["payload"]["file_identity_hash"],
            "authority_basis_hash": candidate["payload"]["authority_basis_hash"],
        }
    finally:
        db.close()


def _text_index_payload(snapshot_info: dict[str, str]) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-text-index-{snapshot_info['source_ingestion_file_id']}",
        **snapshot_info,
    }


def _retrieval_payload(snapshot_info: dict[str, str], index_authority_hash: str, query_text: str) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-text-retrieval-{snapshot_info['source_ingestion_file_id']}",
        **snapshot_info,
        "index_authority_hash": index_authority_hash,
        "query_text": query_text,
    }


def _admitted_material(client: TestClient, tmp_path, monkeypatch) -> tuple[Path, dict[str, str], str]:
    source_dir = tmp_path / "operator-source-dir"
    _write_retrieval_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))
    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json())
    db = client.layer3_session_factory()
    try:
        index_body = source_directory_material_text_index(db, _text_index_payload(snapshot_info))
    finally:
        db.close()
    return source_dir, snapshot_info, index_body["index_authority_hash"]


def test_source_directory_text_retrieval_returns_deterministic_ranked_segments_without_side_effects(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        body = source_directory_material_text_retrieval(
            db,
            {
                **_retrieval_payload(snapshot_info, index_authority_hash, "BETA alpha alpha"),
                "limit": 2,
                "offset": 0,
            },
        )
        replay = source_directory_material_text_retrieval(
            db,
            {
                **_retrieval_payload(snapshot_info, index_authority_hash, "BETA alpha alpha"),
                "limit": 2,
                "offset": 0,
            },
        )

        assert body["schema_id"] == "layer3.source_directory_text_retrieval.v1"
        assert body["mode"] == "source_directory_material_deterministic_lexical_retrieval_authority"
        assert body["status"] == "available"
        assert body["retrieval_contract_id"] == "source_directory_material_deterministic_lexical_retrieval_authority"
        assert body["retrieval_mode"] == "deterministic_lexical_segment_retrieval"
        assert body["query_tokens"] == ["alpha", "beta"]
        assert body["index_authority_hash"] == index_authority_hash
        assert body["source_ingestion_file_id"] == snapshot_info["source_ingestion_file_id"]
        assert body["material_snapshot_id"] == snapshot_info["material_snapshot_id"]
        assert body["total"] == 2
        assert len(body["items"]) == 2
        assert body["items"][0]["summed_term_frequency"] > body["items"][1]["summed_term_frequency"]
        assert body["items"][0]["matched_unique_query_terms"] == 2
        assert [item["segment_id"] for item in body["items"]] == [item["segment_id"] for item in replay["items"]]
        assert body["source_index_rows_written"] is False
        assert body["retrieval_rows_written"] is False
        assert body["negative_invariants"]["retrieval_rows_written"] is False
        assert body["negative_invariants"]["vector_index_enabled"] is False
        assert body["negative_invariants"]["embedding_generation_enabled"] is False
        assert body["negative_invariants"]["qualitative_hybrid_runtime_enabled"] is False
        assert body["negative_invariants"]["connector_dispatch_enabled"] is False
        assert body["negative_invariants"]["provider_public_delivery_enabled"] is False
        assert str(source_dir) not in str(body)
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_source_directory_text_retrieval_rejects_stale_index_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, _ = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextRetrievalError) as exc_info:
            source_directory_material_text_retrieval(
                db,
                _retrieval_payload(snapshot_info, "0" * 64, "alpha beta"),
            )
        assert exc_info.value.code == "source_directory_text_retrieval_stale_index_authority"
        assert exc_info.value.details["blocked_fields"] == ["index_authority_hash"]
    finally:
        db.close()


def test_source_directory_text_retrieval_uses_text_index_fail_closed_authority_path(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    (source_dir / "retrieval.txt").write_text("alpha beta drift\n", encoding="utf-8")

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_text_retrieval(
                db,
                _retrieval_payload(snapshot_info, index_authority_hash, "alpha beta"),
            )
        assert exc_info.value.code == "source_directory_text_index_file_identity_mismatch"
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_source_directory_text_retrieval_validates_query_fields_and_paging(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        no_match = source_directory_material_text_retrieval(
            db,
            _retrieval_payload(snapshot_info, index_authority_hash, "notpresent"),
        )
        assert no_match["total"] == 0
        assert no_match["items"] == []

        page = source_directory_material_text_retrieval(
            db,
            {
                **_retrieval_payload(snapshot_info, index_authority_hash, "alpha beta"),
                "limit": 1,
                "offset": 1,
            },
        )
        assert page["total"] == 2
        assert page["limit"] == 1
        assert page["offset"] == 1
        assert len(page["items"]) == 1

        with pytest.raises(SourceDirectoryTextRetrievalError) as empty_query:
            source_directory_material_text_retrieval(
                db,
                _retrieval_payload(snapshot_info, index_authority_hash, " , "),
            )
        assert empty_query.value.code == "source_directory_text_retrieval_empty_query"

        with pytest.raises(SourceDirectoryTextRetrievalError) as forbidden:
            source_directory_material_text_retrieval(
                db,
                {
                    **_retrieval_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "vector_index": "not-admitted",
                    "provider_model": "not-admitted",
                },
            )
        assert forbidden.value.code == "source_directory_text_retrieval_forbidden_field_not_admitted"
        assert forbidden.value.details["forbidden_fields"] == ["provider_model", "vector_index"]

        with pytest.raises(SourceDirectoryTextRetrievalError) as unknown:
            source_directory_material_text_retrieval(
                db,
                {
                    **_retrieval_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "result_shape": "not-admitted",
                },
            )
        assert unknown.value.code == "source_directory_text_retrieval_unknown_field"
        assert unknown.value.details["unknown_fields"] == ["result_shape"]

        with pytest.raises(SourceDirectoryTextRetrievalError) as bad_limit:
            source_directory_material_text_retrieval(
                db,
                {
                    **_retrieval_payload(snapshot_info, index_authority_hash, "alpha beta"),
                    "limit": 51,
                },
            )
        assert bad_limit.value.code == "source_directory_text_retrieval_limit_out_of_bounds"
    finally:
        db.close()
