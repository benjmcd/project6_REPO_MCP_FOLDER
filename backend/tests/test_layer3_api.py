from __future__ import annotations

import os
import sys
from pathlib import Path

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
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _prepare_material(client: TestClient) -> tuple[dict, dict, dict]:
    preflight = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-preflight",
            "natural_language_intent": "Review deterministic Layer 3 source material.",
            "manual_constraints": {"source_classes": ["dataset_version", "aps_content_document"]},
        },
    ).json()
    source = client.post(
        "/api/v1/layer3/source-preview",
        json={
            "client_request_id": "api-source",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version", "aps_content_document"],
        },
    ).json()
    material = client.post(
        "/api/v1/layer3/material-preview",
        json={
            "client_request_id": "api-material",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [item["source_candidate_id"] for item in source["source_candidates"]],
            "query_basis": {"terms": ["deterministic", "source"]},
        },
    ).json()
    return preflight, source, material


def _assert_common_response_envelope(body: dict) -> None:
    assert body["schema_id"].startswith("layer3.")
    assert body["schema_version"] == 1
    assert body["request_id"]
    assert body["server_time"].endswith("Z")
    assert body["status"]


def test_layer3_api_full_first_slice_flow(client: TestClient) -> None:
    bootstrap = client.get("/api/v1/layer3/bootstrap")
    assert bootstrap.status_code == 200
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["features"]["handoff"] is False

    preflight, source, material = _prepare_material(client)
    for response_body in (bootstrap_body, preflight, source, material):
        _assert_common_response_envelope(response_body)
    assert preflight["status"] == "ok"
    assert source["authority_rail"]["current_gate"] == "gate_b"
    assert len(material["material_candidates"]) == 2

    first, second = material["material_candidates"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": first["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": {
                        "source_ref": first["source_ref"],
                        "query_basis": first["query_basis"],
                        "provenance_ref": first["provenance_ref"],
                    },
                },
                {
                    "candidate_id": second["candidate_id"],
                    "decision": "denied",
                    "operator_reason": "Not in first-slice scope.",
                    "decision_basis": {
                        "source_ref": second["source_ref"],
                        "query_basis": second["query_basis"],
                        "provenance_ref": second["provenance_ref"],
                    },
                },
            ],
            "actor": "pytest",
        },
    )
    assert gate_b.status_code == 200
    gate_b_body = gate_b.json()
    _assert_common_response_envelope(gate_b_body)
    assert gate_b_body["authority_rail"]["approved_material_count"] == 1
    assert gate_b_body["authority_rail"]["denied_material_count"] == 1

    gate_c = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={
            "client_request_id": "api-gate-c",
            "session_id": gate_b_body["session_id"],
            "commit_typing": False,
        },
    )
    assert gate_c.status_code == 200
    gate_c_body = gate_c.json()
    _assert_common_response_envelope(gate_c_body)
    assert gate_c_body["override_allowed"] is False
    assert gate_c_body["typing_records"][0]["authoritative"] is False
    assert gate_c_body["authority_rail"]["approved_material_count"] == 1
    assert gate_c_body["authority_rail"]["denied_material_count"] == 1
    assert gate_c_body["authority_rail"]["source_authority"]["source_classes"] == ["dataset_version"]

    summary = client.get(f"/api/v1/layer3/session/{gate_b_body['session_id']}")
    assert summary.status_code == 200
    summary_body = summary.json()
    _assert_common_response_envelope(summary_body)
    assert summary_body["gate_c_summary"]["typing_committed"] is False


def test_layer3_api_gate_b_no_approved_material_is_blocked_error(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]

    blocked = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-no-approved",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": first["candidate_id"],
                    "decision": "denied",
                    "operator_reason": "Not approved for this first-slice session.",
                    "decision_basis": {
                        "source_ref": first["source_ref"],
                        "query_basis": first["query_basis"],
                        "provenance_ref": first["provenance_ref"],
                    },
                },
            ],
            "actor": "pytest",
        },
    )

    assert blocked.status_code == 400
    body = blocked.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["status"] == "blocked"
    assert body["error_code"] == "no_approved_material"
    assert "session_id" not in body


def test_layer3_api_gate_c_commit_typing_materializes_once_when_explicit(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-commit",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": first["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": {
                        "source_ref": first["source_ref"],
                        "query_basis": first["query_basis"],
                        "provenance_ref": first["provenance_ref"],
                    },
                },
            ],
            "actor": "pytest",
        },
    ).json()

    committed = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={
            "client_request_id": "api-gate-c-commit",
            "session_id": gate_b["session_id"],
            "commit_typing": True,
        },
    )
    assert committed.status_code == 200
    committed_body = committed.json()
    _assert_common_response_envelope(committed_body)
    assert committed_body["typing_records"][0]["authoritative"] is True
    assert committed_body["analysis_units"][0]["authoritative"] is True
    assert committed_body["authority_rail"]["approved_material_count"] == 1
    assert committed_body["authority_rail"]["source_authority"]["source_classes"] == ["dataset_version"]
    assert committed_body["authority_rail"]["typing_status"] == "committed"

    summary = client.get(f"/api/v1/layer3/session/{gate_b['session_id']}")
    assert summary.status_code == 200
    assert summary.json()["gate_c_summary"]["typing_committed"] is True

    duplicate = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={
            "client_request_id": "api-gate-c-commit-duplicate",
            "session_id": gate_b["session_id"],
            "commit_typing": True,
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "typing_already_materialized"


def test_layer3_api_error_shape_and_override_unavailable(client: TestClient) -> None:
    blocked = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-blocked",
            "natural_language_intent": "",
            "manual_constraints": {},
        },
    )
    assert blocked.status_code == 400
    assert blocked.json()["schema_id"] == "layer3.workbench_error.v1"
    assert blocked.json()["error_code"] == "empty_intent"
    assert "detail" not in blocked.json()

    override = client.post(
        "/api/v1/layer3/gate-c/override",
        json={"client_request_id": "api-override", "session_id": "missing"},
    )
    assert override.status_code == 409
    assert override.json()["schema_id"] == "layer3.typing_override_unavailable.v1"
    assert override.json()["error_code"] == "override_unavailable"
