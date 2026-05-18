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
from app.models.models import (
    AnalysisRun,
    ConnectorRun,
    ConnectorRunTarget,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
)
from app.services.layer3_source_directory_text_index import (
    SourceDirectoryTextIndexError,
    source_directory_material_text_index,
)
from app.services.layer3_source_directory_vector_index import (
    SourceDirectoryVectorIndexError,
    source_directory_material_embedding_vector_index,
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


def _scan_payload(client_request_id: str = "source-directory-vector-scan") -> dict[str, str]:
    return {
        "client_request_id": client_request_id,
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _write_vector_source_dir(root: Path) -> None:
    root.mkdir()
    lines = ["alpha beta beta lead\n"]
    lines.extend(f"context filler line {index}\n" for index in range(1, 42))
    lines.append("alpha gamma tail\n")
    (root / "vector.txt").write_text("".join(lines), encoding="utf-8")


def _material_preview_payload(scan_body: dict, relative_name: str = "vector.txt") -> dict[str, str]:
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
            "client_request_id": "source-directory-vector-gate-b",
            "preflight_id": "preflight-source-directory-vector",
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


def _vector_payload(snapshot_info: dict[str, str], index_authority_hash: str) -> dict[str, str]:
    return {
        "client_request_id": f"source-directory-vector-index-{snapshot_info['source_ingestion_file_id']}",
        **snapshot_info,
        "index_authority_hash": index_authority_hash,
    }


def _admitted_material(client: TestClient, tmp_path, monkeypatch) -> tuple[Path, dict[str, str], str]:
    source_dir = tmp_path / "operator-source-dir"
    _write_vector_source_dir(source_dir)
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


def _assert_no_downstream_side_effects(db) -> None:
    assert db.query(L3PassRun).count() == 0
    assert db.query(AnalysisRun).count() == 0
    assert db.query(L3OutputPackage).count() == 0
    assert db.query(ConnectorRun).count() == 0
    assert db.query(ConnectorRunTarget).count() == 0


def test_source_directory_vector_index_returns_deterministic_descriptors_without_side_effects(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        body = source_directory_material_embedding_vector_index(
            db,
            _vector_payload(snapshot_info, index_authority_hash),
        )
        replay = source_directory_material_embedding_vector_index(
            db,
            _vector_payload(snapshot_info, index_authority_hash),
        )

        assert body["schema_id"] == "layer3.source_directory_embedding_vector_index.v1"
        assert body["mode"] == "source_directory_material_deterministic_embedding_vector_index_authority"
        assert body["status"] == "available"
        assert body["embedding_contract_id"] == "source_directory_material_deterministic_embedding_vector_index_authority"
        assert body["embedding_mode"] == "deterministic_local_hashing_vector_embedding"
        assert body["vector_index_mode"] == "deterministic_source_directory_segment_vector_index"
        assert body["feature_hash_version"] == "source-directory-hash-vector-v1"
        assert body["vector_dimensions"] == 4096
        assert body["index_authority_hash"] == index_authority_hash
        assert body["embedding_index_authority_hash"] == replay["embedding_index_authority_hash"]
        assert body["vector_descriptors"] == replay["vector_descriptors"]
        assert body["segment_count"] == len(body["vector_descriptors"])
        assert body["source_ingestion_file_id"] == snapshot_info["source_ingestion_file_id"]
        assert body["material_snapshot_id"] == snapshot_info["material_snapshot_id"]

        descriptor = body["vector_descriptors"][0]
        assert descriptor["embedding_vector_hash"] == replay["vector_descriptors"][0]["embedding_vector_hash"]
        assert len(descriptor["embedding_vector_hash"]) == 64
        assert descriptor["nonzero_feature_count"] > 0
        assert descriptor["token_count"] > 0
        assert descriptor["vector_l2_norm"] > 0
        assert "text" not in descriptor
        assert "vector" not in descriptor
        assert "features" not in descriptor

        assert body["source_index_rows_written"] is False
        assert body["embedding_vector_rows_written"] is False
        assert body["vector_index_rows_written"] is False
        assert body["retrieval_rows_written"] is False
        assert body["context_packet_rows_written"] is False
        assert body["qualitative_analysis_rows_written"] is False
        assert body["analysis_run_rows_written"] is False
        assert body["package_rows_written"] is False
        assert body["connector_rows_written"] is False
        assert body["negative_invariants"]["persistent_vector_store_enabled"] is False
        assert body["negative_invariants"]["durable_embedding_rows_enabled"] is False
        assert body["negative_invariants"]["vector_query_enabled"] is False
        assert body["negative_invariants"]["rag_execution_enabled"] is False
        assert body["negative_invariants"]["embedding_model_provider_enabled"] is False
        assert body["negative_invariants"]["network_egress_enabled"] is False
        assert str(source_dir) not in str(body)
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_vector_index_rejects_stale_index_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, _ = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryVectorIndexError) as exc_info:
            source_directory_material_embedding_vector_index(
                db,
                _vector_payload(snapshot_info, "0" * 64),
            )
        assert exc_info.value.code == "source_directory_vector_index_stale_index_authority"
        assert exc_info.value.details["blocked_fields"] == ["index_authority_hash"]
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_vector_index_uses_text_index_fail_closed_authority_path(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)
    (source_dir / "vector.txt").write_text("alpha beta drift\n", encoding="utf-8")

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_embedding_vector_index(
                db,
                _vector_payload(snapshot_info, index_authority_hash),
            )
        assert exc_info.value.code == "source_directory_text_index_file_identity_mismatch"
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()


def test_source_directory_vector_index_validates_forbidden_unknown_and_required_fields(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _, snapshot_info, index_authority_hash = _admitted_material(client, tmp_path, monkeypatch)

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryVectorIndexError) as forbidden:
            source_directory_material_embedding_vector_index(
                db,
                {
                    **_vector_payload(snapshot_info, index_authority_hash),
                    "query_text": "not-admitted",
                    "provider_model": "not-admitted",
                    "vector": [1.0],
                },
            )
        assert forbidden.value.code == "source_directory_vector_index_forbidden_field_not_admitted"
        assert forbidden.value.details["forbidden_fields"] == ["provider_model", "query_text", "vector"]

        with pytest.raises(SourceDirectoryVectorIndexError) as unknown:
            source_directory_material_embedding_vector_index(
                db,
                {
                    **_vector_payload(snapshot_info, index_authority_hash),
                    "result_shape": "not-admitted",
                },
            )
        assert unknown.value.code == "source_directory_vector_index_unknown_field"
        assert unknown.value.details["unknown_fields"] == ["result_shape"]

        missing = _vector_payload(snapshot_info, index_authority_hash)
        missing.pop("index_authority_hash")
        with pytest.raises(SourceDirectoryVectorIndexError) as required:
            source_directory_material_embedding_vector_index(db, missing)
        assert required.value.code == "source_directory_vector_index_required_field_missing"
        assert required.value.details["field"] == "index_authority_hash"
        _assert_no_downstream_side_effects(db)
    finally:
        db.close()
