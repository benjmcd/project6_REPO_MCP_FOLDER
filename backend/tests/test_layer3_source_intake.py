from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
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
    AnalysisArtifact,
    AnalysisRun,
    L3Descriptor,
    L3GateBIdempotencyKey,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3Session,
)
from app.services import layer3_source_intake
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
    test_client.layer3_session_factory = session_local
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
        "source_intake_gate_b_material_admission",
    ]
    assert contract["source_upload_enabled"] is False
    assert contract["source_intake_upload_enabled"] is True
    assert contract["source_intake_record_enabled"] is True
    assert contract["generic_source_upload_preflight_field_enabled"] is False
    assert contract["operator_upload_material_preview_enabled"] is True
    assert contract["operator_upload_material_preview_requires_later_freeze"] is False
    assert contract["source_intake_gate_b_material_admission_enabled"] is True
    assert contract["operator_upload_gate_b_admission_requires_later_freeze"] is False
    assert contract["source_intake_gate_b_material_admission_route"] == "/api/v1/layer3/gate-b/decision"
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
        "material_preview_hash",
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
    assert body["downstream_eligibility"]["eligible_for_gate_b_material_admission"] is True
    assert body["downstream_eligibility"]["gate_b_material_admission_requires_later_freeze"] is False
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
    assert record["source_description_truncated"] is False
    assert len(record["source_description"]) <= 512
    assert record["downstream_eligibility"]["eligible_for_rag_vector_index"] is False

    assert "define_later_freeze_before_material_preview_or_rag_use" not in body["next_allowed_actions"]
    assert "use_bounded_preview_for_operator_review_only" in body["next_allowed_actions"]


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
    assert body["source_gate"]["gate_b_material_admission_route"] == "POST /api/v1/layer3/gate-b/decision"
    assert body["downstream_eligibility"]["eligible_for_material_preview"] is True
    assert body["downstream_eligibility"]["eligible_for_gate_b_material_admission"] is True
    assert body["material_preview_hash"]
    assert body["negative_invariants"]["rag_vector_index_enabled"] is False
    assert body["negative_invariants"]["unbounded_material_preview_enabled_for_operator_upload"] is False
    assert body["partial_retrieval"] is True

    candidate = body["material_candidate"]
    assert candidate["candidate_id"] == f"mat-source_intake_record-{record_id}"
    assert candidate["source_class"] == "operator_uploaded_single_source"
    assert candidate["query_basis"] == "operator_uploaded_source_intake"
    assert candidate["source_ref"] == f"source_intake_record:{record_id}"
    assert candidate["source_identity"]["source_intake_record_id"] == record_id
    assert candidate["payload"]["source_intake_record_id"] == record_id
    assert candidate["load_summary"]["source_intake_gate_b_material_admission"] is True
    assert candidate["preview_text"] == "Layer 3 oper"
    assert candidate["preview_char_count"] == 12
    assert candidate["preview_truncated"] is True
    assert candidate["storage_pointer"]["absolute_path_exposed"] is False
    assert "file_bytes" not in candidate
    assert "absolute_path" not in candidate["storage_pointer"]


def _source_intake_gate_b_payload(
    preview_body: dict[str, object],
    *,
    client_request_id: str = "source-intake-gate-b-001",
) -> dict[str, object]:
    candidate = preview_body["material_candidate"]
    assert isinstance(candidate, dict)
    decision_basis = {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": candidate["source_identity"],
        "source_provenance": candidate["source_provenance"],
        "payload": candidate["payload"],
        "load_summary": candidate["load_summary"],
    }
    return {
        "client_request_id": client_request_id,
        "preflight_id": "source-intake-preflight-001",
        "source_set_id": "source-intake-source-set-001",
        "material_preview_id": preview_body["material_preview_id"],
        "material_preview_hash": preview_body["material_preview_hash"],
        "actor": "operator",
        "candidate_decisions": [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": "approved",
                "operator_reason": "Admit the persisted source-intake record for Gate B material selection.",
                "decision_basis": decision_basis,
            }
        ],
        "commit_reason": "Gate B admission for existing source-intake record.",
    }


def test_layer3_source_intake_gate_b_decision_admits_existing_record_without_downstream_side_effects(client):
    upload = _upload_source_intake(client)
    record_id = upload.json()["source_intake_record_id"]
    preview = client.get(f"/api/v1/layer3/source/intake/{record_id}/preview")
    preview_body = preview.json()
    payload = _source_intake_gate_b_payload(preview_body)

    response = client.post("/api/v1/layer3/gate-b/decision", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["material_preview_hash"] == preview_body["material_preview_hash"]
    assert body["approved_candidate_ids"] == [preview_body["material_candidate"]["candidate_id"]]
    assert body["next_state"] == "gate_c_preview_ready"

    replay = client.post("/api/v1/layer3/gate-b/decision", json=payload)
    replay_body = replay.json()
    assert replay.status_code == 200
    assert replay_body["status"] == "already_committed"
    assert replay_body["session_id"] == body["session_id"]

    db = client.layer3_session_factory()
    try:
        assert db.query(L3Session).count() == 1
        assert db.query(L3Descriptor).count() == 1
        assert db.query(L3MaterialSnapshot).count() == 1
        assert db.query(L3GateBIdempotencyKey).count() == 1
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
        snapshot = db.query(L3MaterialSnapshot).one()
        assert snapshot.source_shape == "operator_uploaded_single_source"
        assert snapshot.source_identity_json["source_intake_record_id"] == record_id
        assert snapshot.source_identity_json["content_sha256"] == upload.json()["content_sha256"]
        assert "absolute_path" not in snapshot.source_identity_json
    finally:
        db.close()


def test_layer3_source_intake_gate_b_decision_rejects_forbidden_or_stale_authority(client):
    upload = _upload_source_intake(client)
    record_id = upload.json()["source_intake_record_id"]
    preview = client.get(f"/api/v1/layer3/source/intake/{record_id}/preview")
    preview_body = preview.json()
    forbidden_payload = _source_intake_gate_b_payload(
        preview_body,
        client_request_id="source-intake-gate-b-forbidden-001",
    )
    forbidden_payload["candidate_decisions"][0]["decision_basis"]["local_path"] = "C:/tmp/not-admitted.txt"

    forbidden_response = client.post("/api/v1/layer3/gate-b/decision", json=forbidden_payload)

    assert forbidden_response.status_code == 400
    forbidden_body = forbidden_response.json()
    assert forbidden_body["status"] == "blocked"
    assert forbidden_body["error_code"] == "source_intake_gate_b_forbidden_field_not_admitted"
    assert (
        "candidate_decisions.decision_basis.local_path"
        in forbidden_body["blocked_fields"]
    )

    db = client.layer3_session_factory()
    try:
        record = db.get(layer3_source_intake.L3SourceIntakeRecord, record_id)
        record.status = "already_recorded"
        db.commit()
    finally:
        db.close()

    stale_payload = _source_intake_gate_b_payload(
        preview_body,
        client_request_id="source-intake-gate-b-stale-001",
    )
    stale_response = client.post("/api/v1/layer3/gate-b/decision", json=stale_payload)

    assert stale_response.status_code == 409
    stale_body = stale_response.json()
    assert stale_body["status"] == "conflict"
    assert stale_body["error_code"] == "source_intake_gate_b_record_not_admitted"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3Session).count() == 0
        assert db.query(L3MaterialSnapshot).count() == 0
        assert db.query(L3GateBIdempotencyKey).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_source_intake_gate_b_decision_rejects_fabricated_binary_admission(client):
    upload = _upload_source_intake(
        client,
        data={
            "client_request_id": "source-intake-binary-001",
            "declared_media_type": "application/pdf",
        },
    )
    upload_body = upload.json()
    record_id = upload_body["source_intake_record_id"]
    source_identity = {
        **upload_body["source_identity"],
        "source_intake_record_id": record_id,
    }
    decision_basis = {
        "source_ref": f"source_intake_record:{record_id}",
        "query_basis": "operator_uploaded_source_intake",
        "provenance_ref": f"source_intake_record:{record_id}:metadata:{upload_body['metadata_hash']}",
        "source_identity": source_identity,
        "source_provenance": upload_body["source_provenance"],
        "payload": {
            "source_intake_record_id": record_id,
            "source_class": "operator_uploaded_single_source",
            "content_sha256": upload_body["content_sha256"],
            "metadata_hash": upload_body["metadata_hash"],
            "authority_basis_hash": upload_body["authority_basis_hash"],
        },
        "load_summary": {"source_intake_gate_b_material_admission": True},
    }

    response = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "source-intake-gate-b-binary-001",
            "preflight_id": "source-intake-preflight-binary-001",
            "source_set_id": "source-intake-source-set-binary-001",
            "material_preview_id": "fabricated-binary-preview",
            "candidate_decisions": [
                {
                    "candidate_id": f"mat-source_intake_record-{record_id}",
                    "decision": "approved",
                    "operator_reason": "Fabricated binary admission should fail closed.",
                    "decision_basis": decision_basis,
                }
            ],
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error_code"] == "source_intake_gate_b_media_type_not_admitted"
    db = client.layer3_session_factory()
    try:
        assert db.query(L3Session).count() == 0
        assert db.query(L3MaterialSnapshot).count() == 0
    finally:
        db.close()


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


def test_layer3_source_intake_inventory_rejects_malformed_limit_with_contract_error(client):
    response = client.get("/api/v1/layer3/source/intake/inventory", params={"limit": "abc"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_inventory_limit_invalid"


def test_layer3_source_intake_rejects_unbounded_source_description(client):
    response = _upload_source_intake(
        client,
        data={
            "client_request_id": "source-intake-long-description-001",
            "source_description": "x" * 2001,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_description_too_long"
    assert body["error"]["details"]["max_chars"] == 2000


def test_layer3_source_intake_inventory_bounds_legacy_description_and_preview_eligibility():
    record = SimpleNamespace(
        source_intake_record_id="source-intake-record-legacy",
        client_request_id="source-intake-legacy-001",
        status="recorded",
        source_family="operator_uploaded_single_source",
        source_label="Legacy source",
        source_description="d" * 600,
        original_filename="legacy.txt",
        media_type="text/plain",
        content_sha256="a" * 64,
        content_size_bytes=12,
        metadata_hash="b" * 64,
        authority_basis_hash="c" * 64,
        provenance_json={},
        storage_ref="raw/layer3-source-intake/legacy.txt",
        downstream_eligibility_json={
            "source_intake_recorded": True,
            "eligible_for_source_inventory": True,
            "eligible_for_material_preview": False,
            "material_preview_requires_later_freeze": True,
            "eligible_for_gate_b_material_admission": False,
            "gate_b_material_admission_requires_later_freeze": True,
            "eligible_for_rag_vector_index": False,
            "eligible_for_web_connector": False,
            "eligible_for_unbounded_runtime_db": False,
        },
        freshness_timestamp=None,
        created_at=None,
        updated_at=None,
    )

    body = layer3_source_intake._inventory_record_response(record)

    assert len(body["source_description"]) == 512
    assert body["source_description_truncated"] is True
    assert body["downstream_eligibility"]["eligible_for_material_preview"] is True
    assert body["downstream_eligibility"]["material_preview_requires_later_freeze"] is False
    assert body["downstream_eligibility"]["eligible_for_gate_b_material_admission"] is True
    assert body["downstream_eligibility"]["gate_b_material_admission_requires_later_freeze"] is False


def test_layer3_source_intake_rejects_deferred_source_modes(client):
    response = _upload_source_intake(client, data={"local_directory": r"C:\not-admitted"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_forbidden_field"
    assert body["error"]["details"]["forbidden_fields"] == ["local_directory"]


def test_layer3_source_intake_rejects_duplicate_form_fields(client):
    response = client.post(
        "/api/v1/layer3/source/intake/upload",
        files=[
            ("client_request_id", (None, "source-intake-duplicate-001")),
            ("client_request_id", (None, "source-intake-duplicate-002")),
            ("operator_decision", (None, "record_operator_uploaded_source")),
            ("source_label", (None, "Operator uploaded source")),
            ("freshness_timestamp", (None, "2026-05-13T00:00:00Z")),
            ("file", ("operator-source.txt", b"Layer 3 operator source body", "text/plain")),
        ],
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_duplicate_field"
    assert body["error"]["details"]["duplicate_fields"] == ["client_request_id"]


def test_layer3_source_intake_rejects_duplicate_file_fields(client):
    response = client.post(
        "/api/v1/layer3/source/intake/upload",
        files=[
            ("client_request_id", (None, "source-intake-duplicate-file-001")),
            ("operator_decision", (None, "record_operator_uploaded_source")),
            ("source_label", (None, "Operator uploaded source")),
            ("freshness_timestamp", (None, "2026-05-13T00:00:00Z")),
            ("file", ("operator-source-a.txt", b"Layer 3 source body A", "text/plain")),
            ("file", ("operator-source-b.txt", b"Layer 3 source body B", "text/plain")),
        ],
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_duplicate_file_field"
    assert body["error"]["details"]["duplicate_file_fields"] == ["file"]
    assert body["error"]["details"]["file_part_count"] == 2


def test_layer3_source_intake_rejects_wrong_operator_decision(client):
    response = _upload_source_intake(client, data={"operator_decision": "materialize_uploaded_source"})

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "source_intake_operator_decision_not_admitted"
