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
    assert contract["supported_source_intake_modes"] == [
        "operator_single_upload_source_intake",
        "operator_source_intake_inventory_read_only",
        "operator_source_intake_material_preview_read_only",
    ]
    assert contract["source_upload_enabled"] is False
    assert contract["source_intake_upload_enabled"] is True
    assert contract["source_intake_record_enabled"] is True
    assert contract["generic_source_upload_preflight_field_enabled"] is False
    assert contract["operator_upload_material_preview_enabled"] is True
    assert contract["operator_upload_material_preview_requires_later_freeze"] is False
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
    inventory_path = schema["paths"]["/api/v1/layer3/source/intake/inventory"]["get"]
    assert (
        inventory_path["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/Layer3SourceIntakeInventoryResponse"
    )
    inventory_schema = schema["components"]["schemas"]["Layer3SourceIntakeInventoryResponse"]
    inventory_required = set(inventory_schema["required"])
    assert {
        "source_gate",
        "source_intake_inventory_mode",
        "inventory_count",
        "records",
        "downstream_eligibility",
        "negative_invariants",
    }.issubset(inventory_required)
    preview_path = schema["paths"]["/api/v1/layer3/source/intake/{source_intake_record_id}/preview"]["get"]
    assert (
        preview_path["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/Layer3SourceIntakeMaterialPreviewResponse"
    )
    preview_schema = schema["components"]["schemas"]["Layer3SourceIntakeMaterialPreviewResponse"]
    preview_required = set(preview_schema["required"])
    assert {
        "source_gate",
        "source_intake_preview_mode",
        "source_intake_record_id",
        "material_preview_id",
        "material_candidate",
        "partial_retrieval",
        "downstream_eligibility",
        "negative_invariants",
    }.issubset(preview_required)


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
    assert body["downstream_eligibility"]["eligible_for_material_preview"] is True
    assert body["downstream_eligibility"]["material_preview_requires_later_freeze"] is False
    assert body["negative_invariants"]["broad_file_upload_enabled"] is False
    assert body["negative_invariants"]["local_directory_enabled"] is False
    assert body["negative_invariants"]["web_connector_enabled"] is False
    assert body["negative_invariants"]["rag_vector_index_enabled"] is False
    assert body["negative_invariants"]["runtime_db_write_enabled"] is False
    assert body["negative_invariants"]["unbounded_material_preview_enabled_for_operator_upload"] is False

    replay = _upload_source_intake(client)
    replay_body = replay.json()
    assert replay.status_code == 201
    assert replay_body["status"] == "already_recorded"
    assert replay_body["source_intake_record_id"] == body["source_intake_record_id"]
    assert replay_body["authority_basis_hash"] == body["authority_basis_hash"]


def test_layer3_source_intake_inventory_lists_safe_metadata_only(client):
    upload = _upload_source_intake(client)
    upload_body = upload.json()

    response = client.get("/api/v1/layer3/source/intake/inventory")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == "layer3.source_intake_inventory.v1"
    assert body["mode"] == "operator_source_intake_inventory_read_only"
    assert body["status"] == "available"
    assert body["source_gate"]["canonical_source_of_truth"] == "L3SourceIntakeRecord"
    assert body["source_gate"]["no_file_bytes_returned"] is True
    assert body["source_gate"]["absolute_path_exposed"] is False
    assert body["source_gate"]["material_preview_enabled"] is False
    assert body["downstream_eligibility"]["eligible_for_source_inventory"] is True
    assert body["downstream_eligibility"]["eligible_for_material_preview"] is True
    assert body["negative_invariants"]["web_connector_enabled"] is False
    assert body["inventory_count"] == 1

    record = body["records"][0]
    assert record["source_intake_record_id"] == upload_body["source_intake_record_id"]
    assert record["client_request_id"] == "source-intake-api-001"
    assert record["storage_pointer"]["absolute_path_exposed"] is False
    assert record["storage_pointer"]["storage_ref"] == upload_body["storage_pointer"]["storage_ref"]
    assert ":" not in record["storage_pointer"]["storage_ref"]
    assert "file_bytes" not in record
    assert "absolute_path" not in record["storage_pointer"]
    assert record["downstream_eligibility"]["eligible_for_rag_vector_index"] is False


def test_layer3_source_intake_material_preview_returns_bounded_text_only(client):
    upload = _upload_source_intake(client)
    record_id = upload.json()["source_intake_record_id"]

    response = client.get(
        f"/api/v1/layer3/source/intake/{record_id}/preview",
        params={"max_chars": "12"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == "layer3.source_intake_material_preview.v1"
    assert body["mode"] == "operator_source_intake_material_preview_read_only"
    assert body["source_gate"]["canonical_source_of_truth"] == "L3SourceIntakeRecord"
    assert body["source_gate"]["absolute_path_exposed"] is False
    assert body["source_gate"]["bounded_text_preview"] is True
    assert body["source_gate"]["rag_vector_index_enabled"] is False
    assert body["source_gate"]["web_connector_enabled"] is False
    assert body["source_gate"]["package_construction_enabled"] is False
    assert body["downstream_eligibility"]["eligible_for_material_preview"] is True
    assert body["negative_invariants"]["rag_vector_index_enabled"] is False
    assert body["negative_invariants"]["unbounded_material_preview_enabled_for_operator_upload"] is False
    assert body["partial_retrieval"] is True

    candidate = body["material_candidate"]
    assert candidate["candidate_id"] == f"mat-source_intake_record-{record_id}"
    assert candidate["source_class"] == "operator_uploaded_single_source"
    assert candidate["preview_text"] == "Layer 3 oper"
    assert candidate["preview_char_count"] == 12
    assert candidate["preview_truncated"] is True
    assert candidate["storage_pointer"]["absolute_path_exposed"] is False
    assert "file_bytes" not in candidate
    assert "absolute_path" not in candidate["storage_pointer"]


def test_layer3_source_intake_material_preview_accepts_media_type_parameters(client):
    upload = _upload_source_intake(
        client,
        data={
            "client_request_id": "source-intake-api-charset-001",
            "declared_media_type": "text/plain; charset=utf-8",
        },
    )
    record_id = upload.json()["source_intake_record_id"]

    response = client.get(f"/api/v1/layer3/source/intake/{record_id}/preview")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == "layer3.source_intake_material_preview.v1"
    assert body["material_candidate"]["media_type"] == "text/plain; charset=utf-8"
    assert body["material_candidate"]["preview_text"] == "Layer 3 operator source body"


def test_layer3_source_intake_material_preview_rejects_invalid_limit(client):
    upload = _upload_source_intake(client)
    record_id = upload.json()["source_intake_record_id"]

    response = client.get(
        f"/api/v1/layer3/source/intake/{record_id}/preview",
        params={"max_chars": "4001"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_preview_max_chars_invalid"


def test_layer3_source_intake_inventory_rejects_deferred_filters(client):
    response = client.get(
        "/api/v1/layer3/source/intake/inventory",
        params={"source_family": "web_connector"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_inventory_source_family_not_admitted"


def test_layer3_source_intake_inventory_rejects_invalid_limit(client):
    response = client.get("/api/v1/layer3/source/intake/inventory", params={"limit": "101"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_inventory_limit_invalid"


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
