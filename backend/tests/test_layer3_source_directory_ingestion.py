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
    ConnectorRun,
    ConnectorRunTarget,
    L3OutputPackage,
    L3SourceDirectoryIngestionBatch,
    L3SourceDirectoryIngestionFile,
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


def _scan_payload(client_request_id: str = "source-directory-scan-001") -> dict[str, str]:
    return {
        "client_request_id": client_request_id,
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _write_source_dir(root: Path) -> None:
    root.mkdir()
    (root / "alpha.csv").write_text("name,value\nalpha,1\n", encoding="utf-8")
    (root / "bravo.json").write_text('{"rows":[{"name":"bravo","value":2}]}', encoding="utf-8")
    (root / "charlie.txt").write_text("plain text source\n", encoding="utf-8")
    (root / "delta.md").write_text("# Markdown source\n", encoding="utf-8")


def test_layer3_source_directory_ingestion_openapi_contract(client: TestClient) -> None:
    schema = client.app.openapi()

    scan_schema = schema["paths"]["/api/v1/layer3/source/ingestion/server-configured-directory/scan"]["post"]
    request_ref = scan_schema["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {"client_request_id", "operator_decision"}
    assert "local_path" not in request_schema["properties"]
    assert "recursive" not in request_schema["properties"]

    response_ref = scan_schema["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    response_schema = schema["components"]["schemas"][response_ref.rsplit("/", 1)[-1]]
    assert {
        "source_ingestion_batch_id",
        "config_authority",
        "source_root_ref",
        "source_root_absolute_path_exposed",
        "files",
        "negative_invariants",
    }.issubset(set(response_schema["required"]))


def test_layer3_source_directory_ingestion_fails_closed_when_config_unset(client: TestClient) -> None:
    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_ingestion_dir_unset"


def test_layer3_source_directory_ingestion_records_redacted_durable_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["schema_id"] == "layer3.source_directory_ingestion_batch.v1"
    assert body["mode"] == "server_configured_operator_directory_text_table_ingestion"
    assert body["status"] == "recorded"
    assert body["source_family"] == "server_configured_operator_directory_text_table_source_family"
    assert body["config_authority"] == "LAYER3_SOURCE_INGESTION_DIR"
    assert body["source_root_ref"] == "server-configured://LAYER3_SOURCE_INGESTION_DIR"
    assert body["source_root_absolute_path_exposed"] is False
    assert body["direct_child_only"] is True
    assert body["allowed_extensions"] == [".csv", ".json", ".txt", ".md"]
    assert body["eligible_file_count"] == 4
    assert [item["relative_name"] for item in body["files"]] == [
        "alpha.csv",
        "bravo.json",
        "charlie.txt",
        "delta.md",
    ]
    assert all(item["absolute_path_exposed"] is False for item in body["files"])
    assert str(source_dir) not in str(body)
    assert body["negative_invariants"]["recursive_traversal_enabled"] is False
    assert body["negative_invariants"]["rag_vector_index_enabled"] is False
    assert body["negative_invariants"]["package_construction_enabled"] is False
    assert body["negative_invariants"]["connector_dispatch_enabled"] is False

    status = client.get(
        f"/api/v1/layer3/source/ingestion/server-configured-directory/status/{body['source_ingestion_batch_id']}"
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["schema_id"] == "layer3.source_directory_ingestion_status.v1"
    assert status_body["source_ingestion_batch_id"] == body["source_ingestion_batch_id"]
    assert str(source_dir) not in str(status_body)

    replay = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )
    assert replay.status_code == 201
    assert replay.json()["status"] == "already_recorded"
    assert replay.json()["source_ingestion_batch_id"] == body["source_ingestion_batch_id"]

    same_basis_new_request = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-002"),
    )
    assert same_basis_new_request.status_code == 201
    assert same_basis_new_request.json()["status"] == "already_recorded"
    assert same_basis_new_request.json()["source_ingestion_batch_id"] == body["source_ingestion_batch_id"]
    assert same_basis_new_request.json()["request_id"] == "source-directory-scan-002"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3SourceDirectoryIngestionBatch).count() == 1
        assert db.query(L3SourceDirectoryIngestionFile).count() == 4
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_source_directory_ingestion_rejects_forbidden_or_unsupported_scope(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    forbidden = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json={**_scan_payload(), "local_path": str(source_dir), "recursive": True},
    )
    assert forbidden.status_code == 422

    (source_dir / "blocked.pdf").write_bytes(b"%PDF-1.4")
    unsupported = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-unsupported"),
    )
    assert unsupported.status_code == 400
    body = unsupported.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_ingestion_extension_not_admitted"


def test_layer3_source_directory_ingestion_rejects_app_owned_storage_root(
    client: TestClient,
    monkeypatch,
) -> None:
    storage_source_dir = Path(settings.storage_dir) / "operator-source-dir"
    storage_source_dir.mkdir(parents=True)
    (storage_source_dir / "alpha.txt").write_text("inside storage should fail\n", encoding="utf-8")
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(storage_source_dir))

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-storage-root"),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_ingestion_dir_not_admitted"
