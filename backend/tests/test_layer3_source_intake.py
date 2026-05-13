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
from app.services.layer3_source_boundary import source_boundary_contract
from main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
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
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _upload_source_intake(client, *, data: dict[str, str] | None = None):
    payload = {
        "client_request_id": "source-intake-api-001",
        "operator_decision": "record_operator_uploaded_source",
        "source_label": "Operator uploaded source",
        "source_description": "Single source corpus uploaded by the operator.",
        "freshness_timestamp": "2026-05-13T00:00:00Z",
    }
    if data:
        payload.update(data)
    return client.post(
        "/api/v1/layer3/source/intake/upload",
        data=payload,
        files={"file": ("operator-source.txt", b"Layer 3 operator source body", "text/plain")},
    )


def test_layer3_source_boundary_admits_operator_upload_intake_without_broad_source_widening():
    contract = source_boundary_contract()

    assert contract["supported_source_classes"] == ["dataset_version", "aps_content_document"]
    assert contract["supported_source_intake_modes"] == ["operator_single_upload_source_intake"]
    assert contract["source_upload_enabled"] is False
    assert contract["source_intake_upload_enabled"] is True
    assert contract["source_intake_record_enabled"] is True
    assert contract["generic_source_upload_preflight_field_enabled"] is False
    assert contract["operator_upload_material_preview_enabled"] is False
    assert contract["operator_upload_material_preview_requires_later_freeze"] is True
    assert contract["broad_file_upload_enabled"] is False
    assert contract["local_directory_enabled"] is False
    assert contract["web_connector_enabled"] is False
    assert contract["rag_vector_enabled"] is False
    assert contract["unbounded_runtime_db_enabled"] is False


def test_layer3_source_intake_openapi_contract(client):
    schema = client.app.openapi()

    path_item = schema["paths"]["/api/v1/layer3/source/intake/upload"]["post"]
    assert "multipart/form-data" in path_item["requestBody"]["content"]
    response_schema = schema["components"]["schemas"]["Layer3SourceIntakeRecordResponse"]
    required = set(response_schema["required"])
    assert {
        "source_intake_record_id",
        "source_intake_mode",
        "source_family",
        "source_identity",
        "source_provenance",
        "storage_pointer",
        "content_sha256",
        "metadata_hash",
        "authority_basis_hash",
        "downstream_eligibility",
        "negative_invariants",
    }.issubset(required)


def test_layer3_source_intake_upload_records_server_owned_authority(client):
    response = _upload_source_intake(client)

    assert response.status_code == 201
    body = response.json()
    assert body["schema_id"] == "layer3.source_intake_record.v1"
    assert body["mode"] == "operator_single_upload_source_intake"
    assert body["status"] == "recorded"
    assert body["source_family"] == "operator_uploaded_single_source"
    assert body["source_identity"]["content_size_bytes"] == len(b"Layer 3 operator source body")
    assert body["source_provenance"]["server_authority"].startswith("Layer 3 source intake record owns")
    assert body["storage_pointer"]["storage_ref"].startswith("raw/layer3-source-intake/")
    assert body["storage_pointer"]["absolute_path_exposed"] is False
    assert "\\" not in body["storage_pointer"]["storage_ref"]
    assert body["downstream_eligibility"]["source_intake_recorded"] is True
    assert body["downstream_eligibility"]["eligible_for_source_inventory"] is True
    assert body["downstream_eligibility"]["eligible_for_material_preview"] is False
    assert body["downstream_eligibility"]["material_preview_requires_later_freeze"] is True
    assert body["negative_invariants"]["broad_file_upload_enabled"] is False
    assert body["negative_invariants"]["local_directory_enabled"] is False
    assert body["negative_invariants"]["web_connector_enabled"] is False
    assert body["negative_invariants"]["rag_vector_index_enabled"] is False
    assert body["negative_invariants"]["runtime_db_write_enabled"] is False

    replay = _upload_source_intake(client)
    replay_body = replay.json()
    assert replay.status_code == 201
    assert replay_body["status"] == "already_recorded"
    assert replay_body["source_intake_record_id"] == body["source_intake_record_id"]
    assert replay_body["authority_basis_hash"] == body["authority_basis_hash"]


def test_layer3_source_intake_rejects_deferred_source_modes(client):
    response = _upload_source_intake(client, data={"local_directory": r"C:\not-admitted"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_forbidden_field"
    assert body["error"]["details"]["forbidden_fields"] == ["local_directory"]


def test_layer3_source_intake_rejects_wrong_operator_decision(client):
    response = _upload_source_intake(client, data={"operator_decision": "materialize_uploaded_source"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_operator_decision_not_admitted"
