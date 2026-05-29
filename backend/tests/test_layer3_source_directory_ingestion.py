from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, create_engine
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
    L3MaterialSnapshot,
    L3OutputPackage,
    L3SourceDirectoryIngestionBatch,
    L3SourceDirectoryIngestionFile,
)
from app.services import layer3_source_directory_ingestion
from app.services.layer3_source_directory_text_index import (
    SourceDirectoryTextIndexError,
    source_directory_material_text_index,
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


def test_source_directory_ingestion_uses_64_bit_size_and_mtime_columns() -> None:
    assert isinstance(L3SourceDirectoryIngestionBatch.__table__.c.total_size_bytes.type, BigInteger)
    assert isinstance(L3SourceDirectoryIngestionFile.__table__.c.content_size_bytes.type, BigInteger)
    assert isinstance(L3SourceDirectoryIngestionFile.__table__.c.mtime_ns.type, BigInteger)


def _write_source_dir(root: Path) -> None:
    root.mkdir()
    (root / "alpha.csv").write_text("name,value\nalpha,1\n", encoding="utf-8")
    (root / "bravo.json").write_text('{"rows":[{"name":"bravo","value":2}]}', encoding="utf-8")
    (root / "charlie.txt").write_text("plain text source\n", encoding="utf-8")
    (root / "delta.md").write_text("# Markdown source\n", encoding="utf-8")


def _write_recursive_source_dir(root: Path) -> None:
    _write_source_dir(root)
    nested = root / "nested"
    deeper = nested / "reports"
    deeper.mkdir(parents=True)
    (nested / "echo.txt").write_text("nested text source\n", encoding="utf-8")
    (deeper / "foxtrot.md").write_text("# Two-level markdown source\n", encoding="utf-8")


def _material_preview_payload(scan_body: dict, relative_name: str = "alpha.csv") -> dict[str, str]:
    file_record = next(item for item in scan_body["files"] if item["relative_name"] == relative_name)
    return {
        "client_request_id": f"source-directory-material-preview-{relative_name}",
        "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
        "source_ingestion_file_id": file_record["source_ingestion_file_id"],
        "file_identity_hash": file_record["file_identity_hash"],
        "authority_basis_hash": file_record["authority_basis_hash"],
    }


def _approve_source_directory_file(client: TestClient, scan_body: dict, relative_name: str) -> dict[str, str]:
    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body, relative_name),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    candidate = preview_body["material_candidate"]
    request_suffix = relative_name.replace("/", "-").replace(".", "-")
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": f"source-directory-gate-b-{request_suffix}",
            "preflight_id": f"preflight-source-directory-{request_suffix}",
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

    preview_schema = schema["paths"]["/api/v1/layer3/source/ingestion/server-configured-directory/material-preview"][
        "post"
    ]
    preview_request_ref = preview_schema["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    preview_request_schema = schema["components"]["schemas"][preview_request_ref.rsplit("/", 1)[-1]]
    assert preview_request_schema["additionalProperties"] is False
    assert set(preview_request_schema["required"]) == {
        "client_request_id",
        "source_ingestion_batch_id",
        "source_ingestion_file_id",
        "file_identity_hash",
        "authority_basis_hash",
    }
    assert "local_path" not in preview_request_schema["properties"]
    assert "recursive" not in preview_request_schema["properties"]


def test_layer3_source_directory_ingestion_fails_closed_when_config_unset(client: TestClient) -> None:
    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload(),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_ingestion_dir_unset"


def test_layer3_source_directory_ingestion_rejects_file_count_before_hashing(monkeypatch, tmp_path) -> None:
    source_dir = tmp_path / "operator-source-dir"
    source_dir.mkdir()
    (source_dir / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    (source_dir / "bravo.txt").write_text("bravo\n", encoding="utf-8")
    monkeypatch.setattr(layer3_source_directory_ingestion, "MAX_BATCH_FILES", 1)

    def forbidden_observe(*_args, **_kwargs):
        raise AssertionError("_observe_file must not run before file-count admission")

    monkeypatch.setattr(layer3_source_directory_ingestion, "_observe_file", forbidden_observe)

    with pytest.raises(layer3_source_directory_ingestion.SourceDirectoryIngestionError) as exc:
        layer3_source_directory_ingestion._observe_recursive_files(source_dir)  # noqa: SLF001

    assert exc.value.code == "source_directory_ingestion_batch_too_large"


def test_layer3_source_directory_ingestion_reports_unreadable_files(monkeypatch, tmp_path) -> None:
    source_file = tmp_path / "alpha.txt"
    source_file.write_text("alpha\n", encoding="utf-8")
    original_read_bytes = Path.read_bytes

    def blocked_read_bytes(path: Path) -> bytes:
        if path == source_file:
            raise OSError("blocked for test")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", blocked_read_bytes)

    with pytest.raises(layer3_source_directory_ingestion.SourceDirectoryIngestionError) as exc:
        layer3_source_directory_ingestion._observe_file(source_file, "alpha.txt", ".txt")  # noqa: SLF001

    assert exc.value.code == "source_directory_ingestion_file_unreadable"
    assert exc.value.details["relative_name"] == "alpha.txt"


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
    assert body["runtime_policy_id"] == "recursive_server_configured_directory_text_table_policy_v1"
    assert body["direct_child_only"] is False
    assert body["recursive_traversal_admitted"] is True
    assert body["max_recursion_depth"] == 2
    assert body["max_relative_path_segments"] == 3
    assert body["caller_selected_recursive_flag_allowed"] is False
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
    assert body["negative_invariants"]["recursive_traversal_enabled"] is True
    assert body["negative_invariants"]["caller_selected_recursive_flag_enabled"] is False
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


def test_layer3_source_directory_ingestion_allows_unchanged_files_across_new_batches(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    first = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-unchanged-first"),
    )
    assert first.status_code == 201
    (source_dir / "alpha.csv").write_text("name,value\nalpha,2\n", encoding="utf-8")

    second = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-unchanged-second"),
    )
    assert second.status_code == 201
    assert second.json()["source_ingestion_batch_id"] != first.json()["source_ingestion_batch_id"]

    stale_request = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-unchanged-first"),
    )
    assert stale_request.status_code == 409
    assert stale_request.json()["error"]["code"] == "source_directory_ingestion_idempotency_conflict"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3SourceDirectoryIngestionBatch).count() == 2
        assert db.query(L3SourceDirectoryIngestionFile).count() == 8
    finally:
        db.close()


def test_layer3_source_directory_ingestion_records_recursive_relative_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_recursive_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-recursive"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["runtime_policy_id"] == "recursive_server_configured_directory_text_table_policy_v1"
    assert body["direct_child_only"] is False
    assert body["recursive_traversal_admitted"] is True
    assert body["eligible_file_count"] == 6
    assert [item["relative_name"] for item in body["files"]] == [
        "alpha.csv",
        "bravo.json",
        "charlie.txt",
        "delta.md",
        "nested/echo.txt",
        "nested/reports/foxtrot.md",
    ]
    assert all("\\" not in item["relative_name"] for item in body["files"])
    assert all(item["absolute_path_exposed"] is False for item in body["files"])
    assert str(source_dir) not in str(body)
    assert body["authority_snapshot"]["runtime_policy_id"] == (
        "recursive_server_configured_directory_text_table_policy_v1"
    )
    assert body["authority_snapshot"]["max_recursion_depth"] == 2
    assert body["authority_snapshot"]["max_relative_path_segments"] == 3

    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(body, "nested/reports/foxtrot.md"),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert "# Two-level markdown source" in preview_body["material_candidate"]["preview_text"]
    assert preview_body["source_gate"]["direct_child_only"] is False
    assert preview_body["source_gate"]["recursive_traversal_admitted"] is True
    assert str(source_dir) not in str(preview_body)

    snapshot_info = _approve_source_directory_file(client, body, "nested/echo.txt")
    db = client.layer3_session_factory()
    try:
        indexed = source_directory_material_text_index(db, _text_index_payload(snapshot_info))
        assert indexed["status"] == "available"
        assert indexed["source_shape"] == "server_configured_directory_file"
        assert "nested text source" in "".join(segment["text"] for segment in indexed["segments"])
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_source_directory_material_preview_reaches_gate_b_without_broad_outputs(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-material"),
    )
    assert scan.status_code == 201
    scan_body = scan.json()
    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body),
    )

    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["schema_id"] == "layer3.source_directory_material_preview.v1"
    assert preview_body["mode"] == "source_directory_ingestion_gate_b_material_admission"
    assert preview_body["status"] == "available"
    assert preview_body["source_gate"]["canonical_source_of_truth"] == "L3SourceDirectoryIngestionFile"
    assert preview_body["source_gate"]["absolute_path_exposed"] is False
    assert preview_body["source_gate"]["rag_vector_index_enabled"] is False
    assert preview_body["source_gate"]["package_construction_enabled"] is False
    assert preview_body["material_candidate"]["candidate_id"].startswith("mat-server_configured_directory_file-")
    assert preview_body["material_candidate"]["source_class"] == "server_configured_directory_file"
    assert preview_body["material_candidate"]["preview_text"].replace("\r\n", "\n") == "name,value\nalpha,1\n"
    assert str(source_dir) not in str(preview_body)

    candidate = preview_body["material_candidate"]
    rendered_decision_basis = {
        key: candidate[key]
        for key in (
            "source_ref",
            "query_basis",
            "provenance_ref",
            "source_identity",
            "source_provenance",
            "payload",
            "load_summary",
        )
    }
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "source-directory-gate-b-001",
            "preflight_id": "preflight-source-directory",
            "source_set_id": scan_body["source_ingestion_batch_id"],
            "material_preview_id": preview_body["material_preview_id"],
            "material_preview_hash": preview_body["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": rendered_decision_basis,
                }
            ],
        },
    )
    assert gate_b.status_code == 200
    gate_b_body = gate_b.json()
    assert gate_b_body["status"] == "ok"
    assert gate_b_body["approved_candidate_ids"] == [candidate["candidate_id"]]
    assert gate_b_body["next_state"] == "gate_c_preview_ready"
    gate_c = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={"client_request_id": "source-directory-gate-c-001", "session_id": gate_b_body["session_id"]},
    )
    assert gate_c.status_code == 200
    gate_c_body = gate_c.json()
    assert gate_c_body["typing_records"][0]["planning_shape_family"] == "document_chunks"
    assert gate_c_body["typing_records"][0]["chosen_modality"] == "qualitative"

    db = client.layer3_session_factory()
    try:
        snapshots = db.query(L3MaterialSnapshot).all()
        assert len(snapshots) == 1
        assert snapshots[0].source_shape == "server_configured_directory_file"
        assert snapshots[0].source_identity_json["source_ingestion_batch_id"] == scan_body["source_ingestion_batch_id"]
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_source_directory_text_index_segments_admitted_material_without_broad_outputs(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-text-index"),
    )
    assert scan.status_code == 201
    scan_body = scan.json()

    expected_text = {
        "alpha.csv": "name,value",
        "bravo.json": '"rows"',
        "charlie.txt": "plain text source",
        "delta.md": "# Markdown source",
    }
    for relative_name, expected in expected_text.items():
        snapshot_info = _approve_source_directory_file(client, scan_body, relative_name)
        db = client.layer3_session_factory()
        try:
            body = source_directory_material_text_index(db, _text_index_payload(snapshot_info))
            replay = source_directory_material_text_index(db, _text_index_payload(snapshot_info))

            assert body["schema_id"] == "layer3.source_directory_text_index.v1"
            assert body["mode"] == "source_directory_material_deterministic_text_index_authority"
            assert body["status"] == "available"
            assert body["index_contract_id"] == "source_directory_material_deterministic_text_index_authority"
            assert body["index_mode"] == "deterministic_text_segments"
            assert body["segmentation_version"] == "line-window-v1"
            assert body["source_shape"] == "server_configured_directory_file"
            assert body["source_ingestion_batch_id"] == scan_body["source_ingestion_batch_id"]
            assert body["source_ingestion_file_id"] == snapshot_info["source_ingestion_file_id"]
            assert body["material_snapshot_id"] == snapshot_info["material_snapshot_id"]
            assert body["payload_hash"] == snapshot_info["payload_hash"]
            assert body["segment_count"] >= 1
            assert expected in "".join(segment["text"] for segment in body["segments"])
            assert [segment["segment_id"] for segment in body["segments"]] == [
                segment["segment_id"] for segment in replay["segments"]
            ]
            assert body["index_authority_hash"] == replay["index_authority_hash"]
            assert body["source_index_rows_written"] is False
            assert body["negative_invariants"]["source_index_rows_written"] is False
            assert body["negative_invariants"]["route_admitted"] is False
            assert body["negative_invariants"]["vector_index_enabled"] is False
            assert body["negative_invariants"]["embedding_generation_enabled"] is False
            assert body["negative_invariants"]["retrieval_query_enabled"] is False
            assert body["negative_invariants"]["qualitative_hybrid_runtime_enabled"] is False
            assert body["negative_invariants"]["connector_dispatch_enabled"] is False
            assert body["negative_invariants"]["provider_public_delivery_enabled"] is False
            assert str(source_dir) not in str(body)
        finally:
            db.close()

    db = client.layer3_session_factory()
    try:
        assert db.query(L3MaterialSnapshot).count() == 4
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_source_directory_text_index_fails_closed_on_live_file_drift(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-text-index-drift"),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json(), "alpha.csv")
    (source_dir / "alpha.csv").write_text("name,value\nalpha,99\n", encoding="utf-8")

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_text_index(db, _text_index_payload(snapshot_info))
        assert exc_info.value.code == "source_directory_text_index_file_identity_mismatch"
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_source_directory_text_index_rejects_forbidden_retrieval_scope(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-text-index-forbidden"),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json(), "alpha.csv")

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_text_index(
                db,
                {
                    **_text_index_payload(snapshot_info),
                    "vector_index": "not-admitted",
                    "retrieval_query_text": "not-admitted",
                },
            )
        assert exc_info.value.code == "source_directory_text_index_forbidden_field_not_admitted"
        assert exc_info.value.details["forbidden_fields"] == ["retrieval_query_text", "vector_index"]
    finally:
        db.close()


def test_layer3_source_directory_text_index_fails_closed_on_payload_hash_mismatch(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-text-index-payload"),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json(), "alpha.csv")
    snapshot_info["payload_hash"] = "0" * 64

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_text_index(db, _text_index_payload(snapshot_info))
        assert exc_info.value.code == "source_directory_text_index_stale_request_authority"
        assert exc_info.value.details["blocked_fields"] == ["payload_hash"]
    finally:
        db.close()


def test_layer3_source_directory_text_index_requires_material_identity_fields(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-text-index-missing-identity"),
    )
    assert scan.status_code == 201
    snapshot_info = _approve_source_directory_file(client, scan.json(), "alpha.csv")
    payload = _text_index_payload(snapshot_info)
    payload.pop("file_identity_hash")

    db = client.layer3_session_factory()
    try:
        with pytest.raises(SourceDirectoryTextIndexError) as exc_info:
            source_directory_material_text_index(db, payload)
        assert exc_info.value.code == "source_directory_text_index_stale_request_authority"
        assert exc_info.value.details["missing_fields"] == ["file_identity_hash"]
    finally:
        db.close()


def test_layer3_source_directory_material_preview_fails_closed_on_stale_authority(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-stale"),
    )
    assert scan.status_code == 201
    payload = _material_preview_payload(scan.json())
    payload["file_identity_hash"] = "0" * 64

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=payload,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_material_preview_stale_authority"
    assert body["error"]["details"]["blocked_fields"] == ["file_identity_hash"]


def test_layer3_source_directory_material_preview_rejects_live_file_drift(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-drift"),
    )
    assert scan.status_code == 201
    payload = _material_preview_payload(scan.json())
    (source_dir / "alpha.csv").write_text("name,value\nalpha,99\n", encoding="utf-8")

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=payload,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_material_preview_file_identity_mismatch"


def test_layer3_source_directory_material_preview_fails_closed_when_config_drifts(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir"
    _write_source_dir(source_dir)
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-config-drift"),
    )
    assert scan.status_code == 201
    payload = _material_preview_payload(scan.json())
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", "")

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=payload,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_material_config_unavailable"


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


def test_layer3_source_directory_ingestion_fails_closed_on_recursive_policy_violations(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    cases: list[tuple[str, tuple[str, ...], str, bytes]] = [
        (
            "too-deep",
            ("one", "two", "three", "too-deep.txt"),
            "source_directory_ingestion_recursion_depth_exceeded",
            b"too deep\n",
        ),
        (
            "hidden-segment",
            (".hidden", "secret.txt"),
            "source_directory_ingestion_hidden_path_not_admitted",
            b"secret\n",
        ),
        (
            "nested-unsupported",
            ("nested", "blocked.pdf"),
            "source_directory_ingestion_extension_not_admitted",
            b"%PDF-1.4",
        ),
    ]
    for case_name, parts, expected_code, payload in cases:
        source_dir = tmp_path / f"operator-source-dir-{case_name}"
        source_dir.mkdir()
        target = source_dir.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

        response = client.post(
            "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
            json=_scan_payload(f"source-directory-scan-{case_name}"),
        )

        assert response.status_code == 400
        body = response.json()
        assert body["status"] == "blocked"
        assert body["error"]["code"] == expected_code


def test_layer3_source_directory_ingestion_fails_closed_on_nested_symlink(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "operator-source-dir-symlink"
    source_dir.mkdir()
    nested = source_dir / "nested"
    nested.mkdir()
    target = source_dir / "target.txt"
    target.write_text("target\n", encoding="utf-8")
    symlink = nested / "link.txt"
    try:
        symlink.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available in this environment")
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(source_dir))

    response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json=_scan_payload("source-directory-scan-symlink"),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_directory_ingestion_reparse_or_device_not_admitted"


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
