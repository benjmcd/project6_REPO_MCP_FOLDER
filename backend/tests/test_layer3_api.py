from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

from app.api.deps import get_db
from app.core.config import Settings, bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ConnectorRun,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3GateBIdempotencyKey,
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementOutputPackage,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
    L3SignedReferenceAuditEvent,
    L3SignedReferenceReceipt,
    L3SignedReferenceToken,
    L3TypingRecord,
)
from app.services import (
    dataframe_io,
    layer3_connector_dispatch_entry,
    layer3_package_mutation_entry,
    layer3_package_supersession_commit,
    layer3_pass_entry as layer3_pass_entry_module,
    layer3_raw_mixed_bridge,
    layer3_replacement_package_artifact_manifest,
    layer3_replacement_package_namespace,
    layer3_replacement_package_set_authority,
    layer3_workbench,
)
from app.services.layer3_aps_handoff import (
    PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
    Layer3ApsHandoffError,
)
from app.services.layer3_package_entry import Layer3PackageEntryError
from app.services.layer3_pass_entry import Layer3PassEntryError
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import Layer3TypingEntryError, materialize_typing_entry
from main import app
from test_layer3_aps_handoff import _seed_aps_content_fixture, _seed_timeseries_dataset_version
from test_layer3_pass_entry import (
    _build_quant_cohort_ready_session,
    _build_quant_ready_session,
    _seed_timeseries_dataset_version as _seed_cohort_timeseries_dataset_version,
)
from test_layer3_workbench import _seed_aps_derived_dataset_version


def _settings_for_test(**values):
    base_values = {
        "DB_INIT_MODE": "none",
        "DEPLOYMENT_MODE": "local",
        "ALLOWED_ORIGINS": "*",
        "CORS_ALLOW_CREDENTIALS": None,
        "AUTH_OWNER": "none",
        "TRUSTED_PROXY_MODE": "false",
        "STORAGE_EXPOSURE": "auto",
    }
    base_values.update(values)
    return Settings(_env_file=None, **base_values)


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
    test_client = TestClient(app)
    test_client.layer3_session_factory = SessionLocal
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_layer3_deployment_profile_local_defaults_preserve_proof_posture() -> None:
    profile = _settings_for_test()

    assert profile.deployment_mode == "local"
    assert profile.allowed_origin_list == ["*"]
    assert profile.cors_allow_credentials_enabled is True
    assert profile.storage_mount_enabled is True

    cors_middleware = next(middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware")
    assert cors_middleware.kwargs["allow_origins"] == ["*"]
    assert cors_middleware.kwargs["allow_credentials"] is True
    assert any(getattr(route, "path", None) == "/storage" for route in app.routes)


def test_layer3_deployment_profile_nonlocal_accepts_proxy_owned_guardrail() -> None:
    profile = _settings_for_test(
        DEPLOYMENT_MODE="nonlocal",
        ALLOWED_ORIGINS="https://review.example.com, https://ops.example.com",
        AUTH_OWNER="proxy",
        TRUSTED_PROXY_MODE="true",
    )

    assert profile.allowed_origin_list == ["https://review.example.com", "https://ops.example.com"]
    assert profile.cors_allow_credentials_enabled is False
    assert profile.auth_owner == "proxy"
    assert profile.proxy_identity_header == "X-Forwarded-User"
    assert profile.storage_mount_enabled is False


def test_layer3_deployment_profile_nonlocal_main_disables_direct_storage(tmp_path) -> None:
    code = """
import json
from main import app

cors = next(middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware")
print(json.dumps({
    "allow_origins": cors.kwargs["allow_origins"],
    "allow_credentials": cors.kwargs["allow_credentials"],
    "storage_mounted": any(getattr(route, "path", None) == "/storage" for route in app.routes),
}))
"""
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(BACKEND) + os.pathsep + env.get("PYTHONPATH", ""),
            "DB_INIT_MODE": "none",
            "STORAGE_DIR": str(tmp_path / "storage"),
            "DEPLOYMENT_MODE": "nonlocal",
            "ALLOWED_ORIGINS": "https://review.example.com",
            "AUTH_OWNER": "proxy",
            "TRUSTED_PROXY_MODE": "true",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND.parent),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    body = json.loads(result.stdout)

    assert body == {
        "allow_origins": ["https://review.example.com"],
        "allow_credentials": False,
        "storage_mounted": False,
    }


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {
                "DEPLOYMENT_MODE": "nonlocal",
                "ALLOWED_ORIGINS": "*",
                "AUTH_OWNER": "proxy",
                "TRUSTED_PROXY_MODE": "true",
            },
            "ALLOWED_ORIGINS must use explicit origins",
        ),
        (
            {
                "DEPLOYMENT_MODE": "nonlocal",
                "ALLOWED_ORIGINS": "http://review.example.com",
                "AUTH_OWNER": "proxy",
                "TRUSTED_PROXY_MODE": "true",
            },
            "ALLOWED_ORIGINS must use HTTPS origins",
        ),
        (
            {
                "DEPLOYMENT_MODE": "nonlocal",
                "ALLOWED_ORIGINS": "https://review.example.com",
                "TRUSTED_PROXY_MODE": "true",
            },
            "AUTH_OWNER=proxy is required",
        ),
        (
            {
                "DEPLOYMENT_MODE": "nonlocal",
                "ALLOWED_ORIGINS": "https://review.example.com",
                "AUTH_OWNER": "proxy",
            },
            "TRUSTED_PROXY_MODE=true is required",
        ),
        (
            {
                "DEPLOYMENT_MODE": "nonlocal",
                "ALLOWED_ORIGINS": "https://review.example.com",
                "AUTH_OWNER": "proxy",
                "TRUSTED_PROXY_MODE": "true",
                "STORAGE_EXPOSURE": "enabled",
            },
            "STORAGE_EXPOSURE must be auto or disabled",
        ),
        (
            {
                "DEPLOYMENT_MODE": "nonlocal",
                "ALLOWED_ORIGINS": "https://review.example.com",
                "AUTH_OWNER": "proxy",
                "TRUSTED_PROXY_MODE": "true",
                "STORAGE_EXPOSURE": "proxy_protected",
            },
            "STORAGE_EXPOSURE must be auto or disabled",
        ),
    ],
)
def test_layer3_deployment_profile_nonlocal_fails_closed(values: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _settings_for_test(**values)


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


def _gate_b_decision_basis(candidate: dict) -> dict:
    return {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": candidate["source_identity"],
        "source_provenance": candidate["source_provenance"],
        "payload": candidate["payload"],
        "load_summary": candidate["load_summary"],
    }


def _assert_common_response_envelope(body: dict) -> None:
    assert body["schema_id"].startswith("layer3.")
    assert body["schema_version"] == 1
    assert body["request_id"]
    assert body["server_time"].endswith("Z")
    assert body["status"]


def _assert_workbench_error_response(response, *, status_code: int, error_code: str) -> dict:
    assert response.status_code == status_code
    body = response.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == error_code
    assert "detail" not in body
    return body


def _openapi_response_schema(spec: dict, path: str, method: str) -> dict:
    schema = spec["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
    ref = schema.get("$ref")
    assert ref, f"{path} {method} must use a component response schema"
    return spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def _openapi_response_schema_for_status(spec: dict, path: str, method: str, status: str) -> dict:
    schema = spec["paths"][path][method]["responses"][status]["content"]["application/json"]["schema"]
    ref = schema.get("$ref")
    assert ref, f"{path} {method} {status} must use a component response schema"
    return spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]


def _resolve_openapi_schema(spec: dict, schema: dict) -> dict:
    ref = schema.get("$ref")
    if ref:
        return spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    return schema


def _assert_workbench_error_responses(spec: dict, path: str, method: str, statuses: tuple[str, ...]) -> None:
    responses = spec["paths"][path][method]["responses"]
    for status in statuses:
        assert status in responses, f"{path} {method} must document {status} workbench errors"
        error_schema = _openapi_response_schema_for_status(spec, path, method, status)
        assert error_schema["title"] == "Layer3WorkbenchErrorResponse"
        assert {
            "schema_id",
            "schema_version",
            "request_id",
            "server_time",
            "status",
            "error_code",
            "message",
            "recoverable",
            "blocked_fields",
            "next_allowed_actions",
        } <= set(error_schema["required"])


def _assert_string_array_or_string_map_schema(schema: dict) -> None:
    assert schema["oneOf"] == [
        {"type": "array", "items": {"type": "string"}},
        {"type": "object", "additionalProperties": {"type": "string"}},
    ]


def _assert_forbidden_request_field_schema(schema: dict, field: str) -> None:
    property_schema = schema["properties"][field]
    assert property_schema["description"].startswith("Known but non-admitted")
    assert property_schema["not"] == {}


def test_layer3_forbidden_sentinel_openapi_fields_are_impossible(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    seen: set[tuple[str, str]] = set()
    for path, path_item in spec["paths"].items():
        post = path_item.get("post")
        if not post:
            continue
        request_body = post.get("requestBody", {})
        content = request_body.get("content", {})
        schema = content.get("application/json", {}).get("schema")
        if not isinstance(schema, dict):
            continue
        for field, property_schema in schema.get("properties", {}).items():
            if not isinstance(property_schema, dict):
                continue
            description = property_schema.get("description")
            if isinstance(description, str) and description.startswith("Known but non-admitted"):
                _assert_forbidden_request_field_schema(schema, field)
                seen.add((path, field))
    assert {
        ("/api/v1/layer3/source/mixed-corpus/seed", "local_directory"),
        ("/api/v1/layer3/plan/approved/cancel", "provider_public_url"),
        ("/api/v1/layer3/execution/select", "rag_plan"),
        ("/api/v1/layer3/package/review/commit", "package_payload"),
        ("/api/v1/layer3/handoff/connector/record", "connector_key"),
    } <= seen


def test_layer3_bootstrap_readiness_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    bootstrap_schema = _openapi_response_schema(spec, "/api/v1/layer3/bootstrap", "get")
    assert bootstrap_schema["title"] == "Layer3WorkbenchBootstrapResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "route",
        "api_root",
        "features",
        "execution_readiness",
        "state_action_contract",
        "authority_rail",
    } <= set(bootstrap_schema["required"])
    assert bootstrap_schema["properties"]["features"]["additionalProperties"]["type"] == "boolean"

    readiness_schema = _openapi_response_schema(spec, "/api/v1/layer3/readiness", "get")
    assert readiness_schema["title"] == "Layer3ExecutionReadinessResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "execution_admitted",
        "execution_enabled",
        "state_model",
        "state_action_contract",
        "preview_hash_contract",
        "material_preview_hash_contract",
        "idempotency_contract",
        "concurrency_contract",
        "deferred_decisions",
    } <= set(readiness_schema["required"])


def test_layer3_first_slice_preview_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    preflight_request_schema = spec["paths"]["/api/v1/layer3/preflight"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert preflight_request_schema["additionalProperties"] is False
    assert set(preflight_request_schema["required"]) == {"natural_language_intent"}
    assert preflight_request_schema["properties"]["natural_language_intent"]["type"] == "string"
    assert preflight_request_schema["properties"]["manual_constraints"]["additionalProperties"] is True
    assert "source-widening fields are rejected before service execution" in preflight_request_schema["description"]
    assert preflight_request_schema["properties"]["manual_constraints"]["properties"]["source_classes"]["items"][
        "enum"
    ] == ["dataset_version", "aps_content_document"]
    manual_constraint_properties = preflight_request_schema["properties"]["manual_constraints"]["properties"]
    for field in ("local_upload", "provider_public_url", "rag_plan"):
        assert manual_constraint_properties[field]["description"].startswith("Known but non-admitted")
        assert manual_constraint_properties[field]["not"] == {}

    preflight_schema = _openapi_response_schema(spec, "/api/v1/layer3/preflight", "post")
    assert preflight_schema["title"] == "Layer3PreflightResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "preflight_id",
        "normalized_intent",
        "eligible_for_source_selection",
        "authority_rail",
    } <= set(preflight_schema["required"])

    source_request_schema = spec["paths"]["/api/v1/layer3/source-preview"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert source_request_schema["additionalProperties"] is False
    assert set(source_request_schema["required"]) == {"preflight_id"}
    assert "source expansion fields are rejected before service execution" in source_request_schema["description"]
    assert source_request_schema["properties"]["selected_source_classes"]["items"]["enum"] == [
        "dataset_version",
        "aps_content_document",
    ]

    source_schema = _openapi_response_schema(spec, "/api/v1/layer3/source-preview", "post")
    assert source_schema["title"] == "Layer3SourcePreviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "source_set_id",
        "source_candidates",
        "unsupported_sources",
        "authority_rail",
    } <= set(source_schema["required"])

    material_request_schema = spec["paths"]["/api/v1/layer3/material-preview"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert material_request_schema["additionalProperties"] is False
    assert set(material_request_schema["required"]) == {"source_candidate_ids"}
    assert "source expansion fields are rejected before service execution" in material_request_schema["description"]
    assert material_request_schema["properties"]["source_candidate_ids"]["items"]["type"] == "string"
    assert material_request_schema["properties"]["source_candidate_ids"]["minItems"] == 1
    assert material_request_schema["properties"]["query_basis"]["properties"]["terms"]["items"]["type"] == "string"

    material_schema = _openapi_response_schema(spec, "/api/v1/layer3/material-preview", "post")
    assert material_schema["title"] == "Layer3MaterialPreviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "material_preview_id",
        "material_preview_hash",
        "material_candidates",
        "partial_retrieval",
        "authority_rail",
    } <= set(material_schema["required"])

    raw_mixed_request_schema = spec["paths"]["/api/v1/layer3/source/mixed-corpus/seed"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert raw_mixed_request_schema["additionalProperties"] is False
    assert set(raw_mixed_request_schema["required"]) == {
        "client_request_id",
        "seed_mode",
        "corpus_batch_id",
        "aps_run_id",
        "target_ids",
        "artifact_manifest_ref",
        "artifact_manifest_hash",
        "requested_source_classes",
        "operator_confirmation",
    }
    assert raw_mixed_request_schema["properties"]["seed_mode"]["enum"] == ["raw_mixed_corpus_bridge_seed_only"]
    assert raw_mixed_request_schema["properties"]["requested_source_classes"]["items"]["enum"] == [
        "dataset_version",
        "aps_content_document",
    ]
    for field in ("local_directory", "web_connector", "rag_vector_index", "package_payload", "provider_url"):
        assert raw_mixed_request_schema["properties"][field]["description"].startswith("Known but non-admitted")
        assert raw_mixed_request_schema["properties"][field]["not"] == {}

    raw_mixed_schema = _openapi_response_schema(spec, "/api/v1/layer3/source/mixed-corpus/seed", "post")
    assert raw_mixed_schema["title"] == "Layer3RawMixedCorpusSeedResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "source_seed_id",
        "seed_mode",
        "source_seed_state",
        "dataset_version_ids",
        "aps_content_document_ids",
        "source_classes",
        "artifact_manifest_ref",
        "artifact_manifest_hash",
        "layer3_flow_started",
        "next_allowed_actions",
    } <= set(raw_mixed_schema["required"])
    _assert_workbench_error_responses(spec, "/api/v1/layer3/source/mixed-corpus/seed", "post", ("400", "404", "409"))

    dataset_candidate_schema = _openapi_response_schema(spec, "/api/v1/layer3/dataset-version-candidates", "get")
    assert dataset_candidate_schema["title"] == "Layer3DatasetVersionCandidatesResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "dataset_version_candidates",
        "candidate_count",
        "source_system",
        "source_family_summary",
        "authority_rail",
    } <= set(dataset_candidate_schema["required"])

    aps_content_candidate_schema = _openapi_response_schema(
        spec,
        "/api/v1/layer3/aps-content-document-candidates",
        "get",
    )
    assert aps_content_candidate_schema["title"] == "Layer3ApsContentDocumentCandidatesResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "aps_content_document_candidates",
        "candidate_count",
        "source_system",
        "authority_rail",
    } <= set(aps_content_candidate_schema["required"])


def test_layer3_api_lists_aps_derived_dataset_version_candidates(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        dataset_version_id = _seed_aps_derived_dataset_version(db, tmp_path)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/layer3/dataset-version-candidates")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == "layer3.aps_dataset_version_candidates.v1"
    assert body["candidate_count"] == 1
    candidate = body["dataset_version_candidates"][0]
    assert candidate["dataset_version_id"] == dataset_version_id
    assert candidate["source_system"] == "nrc_adams_aps"
    assert candidate["parser_family"] == "csv_table"
    assert candidate["source_family_label"] == "CSV table"
    assert body["source_family_summary"]["observed_candidate_counts"] == {"csv_table": 1}


def test_layer3_api_lists_aps_content_document_candidates(client: TestClient, tmp_path) -> None:
    run_id = "api-aps-doc-run-001"
    target_id = "api-aps-doc-target-001"
    content_id = "api-aps-doc-content-001"
    db = client.layer3_session_factory()
    try:
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_id,
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/layer3/aps-content-document-candidates")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == "layer3.aps_content_document_candidates.v1"
    assert body["candidate_count"] == 1
    candidate = body["aps_content_document_candidates"][0]
    assert candidate["content_id"] == content_id
    assert candidate["source_family_label"] == "APS content document"
    assert candidate["source_admission_state"] == "admitted_content_document"
    assert candidate["run_id"] == run_id
    assert candidate["target_id"] == target_id
    assert candidate["accession_number"] == "ML26001A001"


def test_layer3_gate_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    gate_b_request_schema = spec["paths"]["/api/v1/layer3/gate-b/decision"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert gate_b_request_schema["additionalProperties"] is False
    assert set(gate_b_request_schema["required"]) == {"client_request_id", "candidate_decisions"}
    assert gate_b_request_schema["properties"]["client_request_id"]["minLength"] == 1
    assert gate_b_request_schema["properties"]["candidate_decisions"]["minItems"] == 1
    assert gate_b_request_schema["properties"]["material_preview_hash"]["type"] == "string"
    gate_b_decision_item_schema = gate_b_request_schema["properties"]["candidate_decisions"]["items"]
    assert gate_b_decision_item_schema["additionalProperties"] is False
    assert set(gate_b_decision_item_schema["required"]) == {"candidate_id", "decision"}
    assert gate_b_decision_item_schema["properties"]["decision"]["enum"] == [
        "approved",
        "denied",
        "isolated",
        "flagged",
    ]
    assert "operator_reason" in gate_b_decision_item_schema["properties"]

    gate_b_schema = _openapi_response_schema(spec, "/api/v1/layer3/gate-b/decision", "post")
    assert gate_b_schema["title"] == "Layer3GateBDecisionResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "selection_manifest_id",
        "material_preview_hash",
        "gate_b_decision_manifest_id",
        "approved_candidate_ids",
        "denied_candidate_ids",
        "isolated_candidate_ids",
        "flagged_candidate_ids",
        "next_state",
        "authority_rail",
    } <= set(gate_b_schema["required"])

    gate_c_request_schema = spec["paths"]["/api/v1/layer3/gate-c/preview"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert gate_c_request_schema["additionalProperties"] is False
    assert set(gate_c_request_schema["required"]) == {"session_id"}
    assert gate_c_request_schema["properties"]["commit_typing"]["type"] == "boolean"

    gate_c_schema = _openapi_response_schema(spec, "/api/v1/layer3/gate-c/preview", "post")
    assert gate_c_schema["title"] == "Layer3GateCPreviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "typing_records",
        "analysis_units",
        "analysis_groups",
        "analysis_sets",
        "unsupported_material",
        "override_allowed",
        "next_state",
        "authority_rail",
    } <= set(gate_c_schema["required"])


def test_layer3_plan_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    preview_request_schema = spec["paths"]["/api/v1/layer3/plan/preview"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert preview_request_schema["additionalProperties"] is False
    assert set(preview_request_schema["required"]) == {"session_id"}
    assert preview_request_schema["properties"]["schema_id"]["enum"] == ["layer3.plan_preview_request.v1"]
    assert preview_request_schema["properties"]["preview_scope"]["enum"] == ["owner_service_default"]
    assert preview_request_schema["properties"]["include_exclusions"]["type"] == "boolean"
    assert "source-widening fields are rejected before service mutation" in preview_request_schema["description"]

    preview_schema = _openapi_response_schema(spec, "/api/v1/layer3/plan/preview", "post")
    assert preview_schema["title"] == "Layer3PlanPreviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "next_state",
        "preview_id",
        "preview_hash",
        "preview_identity",
        "preview_only",
        "authority_rail",
        "plan_preview",
    } <= set(preview_schema["required"])

    approval_request_schema = spec["paths"]["/api/v1/layer3/plan/approve"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert approval_request_schema["additionalProperties"] is False
    assert set(approval_request_schema["required"]) == {
        "session_id",
        "preview_id",
        "preview_hash",
        "operator_confirmation",
    }
    assert approval_request_schema["properties"]["schema_id"]["enum"] == ["layer3.plan_approval_request.v1"]
    assert approval_request_schema["properties"]["operator_confirmation"] == {"type": "boolean", "enum": [True]}
    assert approval_request_schema["properties"]["approval_scope"]["enum"] == ["owner_service_default"]

    cancel_request_schema = spec["paths"]["/api/v1/layer3/plan/approved/cancel"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert cancel_request_schema["additionalProperties"] is False
    assert set(cancel_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
    }
    assert cancel_request_schema["properties"]["schema_id"]["enum"] == ["layer3.approved_plan_cancel_request.v1"]
    assert cancel_request_schema["properties"]["operator_decision"]["enum"] == [
        "cancel_approved_plan_without_replacement"
    ]
    assert cancel_request_schema["properties"]["replacement_plan"]["description"].startswith("Known but non-admitted")
    assert cancel_request_schema["properties"]["provider_public_url"]["description"].startswith(
        "Known but non-admitted"
    )

    revision_request_schema = spec["paths"]["/api/v1/layer3/plan/revise"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert revision_request_schema["additionalProperties"] is False
    assert revision_request_schema["properties"]["schema_id"]["enum"] == ["layer3.plan_revision_request.v1"]

    approval_schema = _openapi_response_schema(spec, "/api/v1/layer3/plan/approve", "post")
    assert approval_schema["title"] == "Layer3PlanApprovalResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "next_state",
        "approval_only",
        "execution_started",
        "analysis_plan_id",
        "plan_status",
        "approved_by_operator",
        "approved_at",
        "authority_rail",
        "approved_plan",
    } <= set(approval_schema["required"])

    cancel_schema = _openapi_response_schema(spec, "/api/v1/layer3/plan/approved/cancel", "post")
    assert cancel_schema["title"] == "Layer3ApprovedPlanCancelResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "next_state",
        "approved_plan_cancelled",
        "approval_available",
        "execution_started",
        "replacement_plan_created",
        "analysis_plan_id",
        "plan_status",
        "previous_plan_status",
        "approved_by_operator",
        "approved_at",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
        "operator_note_recorded",
        "authority_rail",
        "downstream_unavailable",
        "approved_plan_cancel",
    } <= set(cancel_schema["required"])

    revision_request_schema = spec["paths"]["/api/v1/layer3/plan/revise"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert revision_request_schema["additionalProperties"] is False
    assert set(revision_request_schema["required"]) == {
        "session_id",
        "preview_id",
        "preview_hash",
        "operator_decision",
    }
    assert revision_request_schema["properties"]["operator_decision"]["enum"] == [
        "reject_current_preview",
        "request_revision",
    ]
    assert revision_request_schema["properties"]["execute"]["description"].startswith("Known but non-admitted")
    assert revision_request_schema["properties"]["rag_plan"]["description"].startswith("Known but non-admitted")

    revision_schema = _openapi_response_schema(spec, "/api/v1/layer3/plan/revise", "post")
    assert revision_schema["title"] == "Layer3PlanRevisionResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "next_state",
        "revision_control_only",
        "execution_started",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
        "operator_note_recorded",
        "authority_rail",
        "downstream_unavailable",
        "plan_revision_control",
    } <= set(revision_schema["required"])

    recovery_request_schema = spec["paths"]["/api/v1/layer3/plan/revision/recover"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert recovery_request_schema["additionalProperties"] is False
    assert set(recovery_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "source_revision_state",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
    }
    assert recovery_request_schema["properties"]["schema_id"]["enum"] == [
        "layer3.plan_revision_recovery_request.v1"
    ]
    assert recovery_request_schema["properties"]["operator_decision"]["enum"] == ["recover_for_preview_refresh"]
    assert recovery_request_schema["properties"]["source_revision_state"]["enum"] == [
        "plan_rejected",
        "plan_revision_requested",
    ]
    assert recovery_request_schema["properties"]["execute"]["description"].startswith("Known but non-admitted")
    assert recovery_request_schema["properties"]["provider_public_url"]["description"].startswith(
        "Known but non-admitted"
    )

    recovery_schema = _openapi_response_schema(spec, "/api/v1/layer3/plan/revision/recover", "post")
    assert recovery_schema["title"] == "Layer3PlanRevisionRecoveryResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "source_revision_state",
        "next_state",
        "preview_refresh_required",
        "approval_available",
        "execution_started",
        "recovery_lifecycle_only",
        "source_preview_id",
        "source_preview_hash",
        "operator_decision",
        "operator_note_recorded",
        "authority_rail",
        "downstream_unavailable",
        "plan_revision_recovery",
    } <= set(recovery_schema["required"])


def test_layer3_execution_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    selection_request_schema = spec["paths"]["/api/v1/layer3/execution/select"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert selection_request_schema["additionalProperties"] is False
    assert set(selection_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "preview_id",
        "preview_hash",
    }
    assert selection_request_schema["properties"]["operator_reason"]["type"] == "string"
    assert selection_request_schema["properties"]["execution"]["description"].startswith("Known but non-admitted")
    assert selection_request_schema["properties"]["rag_plan"]["description"].startswith("Known but non-admitted")

    selection_schema = _openapi_response_schema(spec, "/api/v1/layer3/execution/select", "post")
    assert selection_schema["title"] == "Layer3ExecutionSelectionResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "preview_identity",
        "pass_run_ids",
        "pass_run_count",
        "execution_started",
        "analysis_run_ids",
        "pass_run_statuses",
        "downstream_unavailable",
        "next_state",
    } <= set(selection_schema["required"])

    start_request_schema = spec["paths"]["/api/v1/layer3/execution/start"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert start_request_schema["additionalProperties"] is False
    assert set(start_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
    }
    assert start_request_schema["properties"]["execution_mode"]["enum"] == ["synchronous_single_pass"]
    assert start_request_schema["properties"]["run_all"]["description"].startswith("Known but non-admitted")
    assert start_request_schema["properties"]["source_expansion"]["description"].startswith("Known but non-admitted")

    start_schema = _openapi_response_schema(spec, "/api/v1/layer3/execution/start", "post")
    assert start_schema["title"] == "Layer3AnalysisExecutionStartResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "execution_started",
        "analysis_run_id",
        "pass_run_status",
        "output_payload_ref",
        "downstream_unavailable",
        "next_state",
        "engine_family",
        "selected_method_name",
        "dataset_version_id",
    } <= set(start_schema["required"])


def test_layer3_execution_result_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    status_request_schema = spec["paths"]["/api/v1/layer3/execution/result/status"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert status_request_schema["additionalProperties"] is False
    assert set(status_request_schema["required"]) == {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
    }
    assert status_request_schema["properties"]["operator_view_mode"]["enum"] == ["status_only"]
    assert status_request_schema["properties"]["result_review"]["description"].startswith("Known but non-admitted")
    assert status_request_schema["properties"]["runtime_db_write"]["description"].startswith("Known but non-admitted")

    status_schema = _openapi_response_schema(spec, "/api/v1/layer3/execution/result/status", "post")
    assert status_schema["title"] == "Layer3ExecutionResultStatusResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "execution_started",
        "analysis_run_id",
        "analysis_run_status",
        "pass_run_status",
        "output_payload_ref",
        "output_metadata_summary",
        "output_metadata_error",
        "warnings_present",
        "error_present",
        "error_message",
        "result_status_available",
        "result_review_enabled",
        "package_review_enabled",
        "handoff_enabled",
        "downstream_unavailable",
        "next_state",
        "operator_view_mode",
        "engine_family",
        "selected_method_name",
        "dataset_version_id",
    } <= set(status_schema["required"])

    review_request_schema = spec["paths"]["/api/v1/layer3/execution/result/review"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert review_request_schema["additionalProperties"] is False
    assert set(review_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "operator_decision",
    }
    assert review_request_schema["properties"]["operator_decision"]["enum"] == [
        "approved",
        "changes_requested",
        "rejected",
        "blocked",
    ]
    assert review_request_schema["properties"]["reviewed_output_items"]["type"] == "array"
    assert review_request_schema["properties"]["package_review"]["description"].startswith("Known but non-admitted")
    assert review_request_schema["properties"]["source_expansion"]["description"].startswith("Known but non-admitted")

    review_schema = _openapi_response_schema(spec, "/api/v1/layer3/execution/result/review", "post")
    assert review_schema["title"] == "Layer3ExecutionResultReviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_status_available",
        "result_review_enabled",
        "review_state",
        "operator_decision",
        "review_record_ref",
        "trace_summary",
        "reviewed_output_items",
        "unresolved_trace_count",
        "package_review_enabled",
        "handoff_enabled",
        "downstream_unavailable",
        "review_notes_recorded",
        "engine_family",
    } <= set(review_schema["required"])


def test_layer3_package_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    preview_request_schema = spec["paths"]["/api/v1/layer3/package/review/preview"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert preview_request_schema["additionalProperties"] is False
    assert set(preview_request_schema["required"]) == {
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
    }
    assert preview_request_schema["properties"]["package"]["description"].startswith("Known but non-admitted")
    assert preview_request_schema["properties"]["source_expansion"]["description"].startswith("Known but non-admitted")

    preview_schema = _openapi_response_schema(spec, "/api/v1/layer3/package/review/preview", "post")
    assert preview_schema["title"] == "Layer3PackageReviewPreviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "package_review_preview_hash",
        "analysis_run_id",
        "result_status_available",
        "result_review_state",
        "result_review_record_ref",
        "package_review_preview_enabled",
        "package_commit_enabled",
        "package_review_enabled",
        "candidate_package_kinds",
        "package_owner_compatibility",
        "blocked_reasons",
        "downstream_unavailable",
        "next_state",
        "output_metadata_summary",
        "trace_summary",
        "unresolved_trace_count",
        "authority_rail",
    } <= set(preview_schema["required"])

    commit_request_schema = spec["paths"]["/api/v1/layer3/package/review/commit"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert commit_request_schema["additionalProperties"] is False
    assert set(commit_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
    }
    assert commit_request_schema["properties"]["expected_package_kinds"]["items"]["enum"] == [
        "canonical_internal",
        "user_facing",
        "review_facing",
    ]
    assert commit_request_schema["properties"]["handoff"]["description"].startswith("Known but non-admitted")
    assert commit_request_schema["properties"]["package_payload"]["description"].startswith("Known but non-admitted")

    commit_schema = _openapi_response_schema(spec, "/api/v1/layer3/package/review/commit", "post")
    assert commit_schema["title"] == "Layer3PackageConstructionCommitResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_packages",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_enabled",
        "handoff_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(commit_schema["required"])

    submit_request_schema = spec["paths"]["/api/v1/layer3/package/review/submit"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert submit_request_schema["additionalProperties"] is False
    assert set(submit_request_schema["required"]) == {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "operator_decision",
    }
    assert submit_request_schema["properties"]["operator_decision"]["enum"] == [
        "approved",
        "changes_requested",
        "rejected",
        "blocked",
    ]
    assert submit_request_schema["properties"]["output_package_ids"]["type"] == "array"
    assert submit_request_schema["properties"]["construction_basis_hash"]["type"] == "string"
    _assert_string_array_or_string_map_schema(submit_request_schema["properties"]["payload_refs"])
    _assert_string_array_or_string_map_schema(submit_request_schema["properties"]["payload_hashes"])
    assert submit_request_schema["properties"]["handoff"]["description"].startswith("Known but non-admitted")
    assert submit_request_schema["properties"]["package_payload"]["description"].startswith("Known but non-admitted")

    submit_schema = _openapi_response_schema(spec, "/api/v1/layer3/package/review/submit", "post")
    assert submit_schema["title"] == "Layer3PackageReviewSubmitResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "construction_basis_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "operator_decision",
        "decision_notes",
        "package_review_state",
        "submit_record_ref",
        "package_review_submit_enabled",
        "handoff_enabled",
        "export_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(submit_schema["required"])


def test_layer3_handoff_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    prepare_request_schema = spec["paths"]["/api/v1/layer3/handoff/export/prepare"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert prepare_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "package_review_submit_schema_id",
        "handoff_target",
        "export_mode",
        "operator_decision",
    } == set(prepare_request_schema["required"])
    assert prepare_request_schema["properties"]["handoff_target"]["enum"] == ["internal_export_envelope"]
    assert prepare_request_schema["properties"]["export_mode"]["enum"] == ["prepare_only"]
    assert prepare_request_schema["properties"]["operator_decision"]["enum"] == [
        "authorize_prepare",
        "hold",
        "decline",
        "blocked",
    ]
    _assert_string_array_or_string_map_schema(prepare_request_schema["properties"]["payload_refs"])
    _assert_string_array_or_string_map_schema(prepare_request_schema["properties"]["payload_hashes"])
    assert prepare_request_schema["properties"]["dispatch"]["description"].startswith("Known but non-admitted")
    assert prepare_request_schema["properties"]["package_payload"]["description"].startswith("Known but non-admitted")

    prepare_schema = _openapi_response_schema(spec, "/api/v1/layer3/handoff/export/prepare", "post")
    assert prepare_schema["title"] == "Layer3HandoffExportPrepareResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "operator_decision",
        "decision_notes",
        "handoff_export_state",
        "handoff_target",
        "export_mode",
        "external_handoff_enabled",
        "external_export_enabled",
        "dispatch_enabled",
        "downstream_unavailable",
        "next_state",
        "prepare_record_ref",
        "authority_rail",
    } <= set(prepare_schema["required"])
    assert "handoff_export_envelope" in prepare_schema["properties"]
    assert "handoff_export_envelope" not in prepare_schema["required"]

    dispatch_request_schema = spec["paths"]["/api/v1/layer3/handoff/aps/dispatch"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert dispatch_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "operator_decision",
    } == set(dispatch_request_schema["required"])
    assert dispatch_request_schema["properties"]["aps_handoff_target"]["enum"] == ["aps_evidence_bundle"]
    assert dispatch_request_schema["properties"]["dispatch_mode"]["enum"] == ["server_side_aps_handoff"]
    assert dispatch_request_schema["properties"]["operator_decision"]["enum"] == ["dispatch_aps_handoff"]
    _assert_string_array_or_string_map_schema(dispatch_request_schema["properties"]["payload_refs"])
    _assert_string_array_or_string_map_schema(dispatch_request_schema["properties"]["payload_hashes"])
    assert dispatch_request_schema["properties"]["connector_dispatch"]["description"].startswith(
        "Known but non-admitted"
    )
    assert dispatch_request_schema["properties"]["download_url"]["description"].startswith("Known but non-admitted")

    dispatch_schema = _openapi_response_schema(spec, "/api/v1/layer3/handoff/aps/dispatch", "post")
    assert dispatch_schema["title"] == "Layer3ApsHandoffDispatchResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "operator_decision",
        "decision_notes",
        "aps_handoff_state",
        "aps_handoff_record_ref",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "source_package_refs",
        "source_package_hashes",
        "external_export_enabled",
        "download_enabled",
        "connector_dispatch_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(dispatch_schema["required"])


def test_layer3_external_export_download_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    prepare_request_schema = spec["paths"]["/api/v1/layer3/handoff/export/download/prepare"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    assert prepare_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "dispatch_mode",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "export_download_target",
        "download_mode",
        "operator_decision",
    } == set(prepare_request_schema["required"])
    assert prepare_request_schema["properties"]["export_download_target"]["enum"] == [
        "aps_evidence_bundle_download_reference"
    ]
    assert prepare_request_schema["properties"]["download_mode"]["enum"] == ["reference_only_prepare"]
    assert prepare_request_schema["properties"]["operator_decision"]["enum"] == ["prepare_external_export_download"]
    _assert_string_array_or_string_map_schema(prepare_request_schema["properties"]["payload_refs"])
    _assert_string_array_or_string_map_schema(prepare_request_schema["properties"]["payload_hashes"])
    assert prepare_request_schema["properties"]["public_url"]["description"].startswith("Known but non-admitted")
    assert prepare_request_schema["properties"]["connector_dispatch"]["description"].startswith(
        "Known but non-admitted"
    )

    prepare_schema = _openapi_response_schema(spec, "/api/v1/layer3/handoff/export/download/prepare", "post")
    assert prepare_schema["title"] == "Layer3ExternalExportDownloadPrepareResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "dispatch_mode",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "export_download_target",
        "download_mode",
        "operator_decision",
        "decision_notes",
        "external_export_download_state",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "source_artifact_ref",
        "source_artifact_schema_id",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "browser_download_enabled",
        "download_url_enabled",
        "connector_dispatch_enabled",
        "destination_selection_enabled",
        "generic_downstream_dispatch_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(prepare_schema["required"])
    assert "delivery_ui" in prepare_schema["properties"]

    supersession_request_schema = spec["paths"]["/api/v1/layer3/package/mutation/preview"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert supersession_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_preview_hash",
        "operator_decision",
    } == set(supersession_request_schema["required"])
    assert supersession_request_schema["properties"]["operator_decision"]["enum"] == [
        "preview_package_supersession"
    ]
    assert supersession_request_schema["properties"]["package_payload"]["description"].startswith(
        "Known but non-admitted"
    )
    assert supersession_request_schema["properties"]["provider_public_url"]["description"].startswith(
        "Known but non-admitted"
    )

    supersession_schema = _openapi_response_schema(spec, "/api/v1/layer3/package/mutation/preview", "post")
    assert supersession_schema["title"] == "Layer3PackageSupersessionPreviewResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "operator_decision",
        "package_supersession_preview_mode",
        "package_supersession_preview_hash",
        "package_set_hash",
        "package_rows",
        "downstream_dependencies",
        "downstream_dependency_detected",
        "immutable_package_rule_enforced",
        "package_row_mutation_enabled",
        "package_payload_rewrite_enabled",
        "package_supersession_commit_enabled",
        "database_write_enabled",
        "filesystem_write_enabled",
        "broad_package_mutation_enabled",
        "source_widening_enabled",
        "connector_dispatch_enabled",
        "provider_public_url_enabled",
        "qualitative_hybrid_rag_execution_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(supersession_schema["required"])

    replacement_request_schema = spec["paths"]["/api/v1/layer3/package/replacement-set/record"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    assert replacement_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "operator_decision",
    } == set(replacement_request_schema["required"])
    assert replacement_request_schema["properties"]["operator_decision"]["enum"] == [
        "record_replacement_package_set_authority"
    ]
    assert replacement_request_schema["properties"]["package_payload"]["description"].startswith(
        "Known but non-admitted"
    )
    assert replacement_request_schema["properties"]["package_supersession_commit"]["description"].startswith(
        "Known but non-admitted"
    )

    replacement_schema = _openapi_response_schema(spec, "/api/v1/layer3/package/replacement-set/record", "post")
    assert replacement_schema["title"] == "Layer3ReplacementPackageSetAuthorityResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "replacement_package_set_authority_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "authority_snapshot",
        "operator_decision",
        "replacement_package_set_authority_mode",
        "source_gate",
        "authority_record_persisted",
        "package_row_mutation_enabled",
        "package_payload_write_enabled",
        "package_supersession_commit_enabled",
        "broad_package_mutation_enabled",
        "source_widening_enabled",
        "connector_dispatch_enabled",
        "provider_public_url_enabled",
        "qualitative_hybrid_rag_execution_enabled",
        "frontend_only_durable_state_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(replacement_schema["required"])

    commit_request_schema = spec["paths"]["/api/v1/layer3/package/supersession/commit"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert commit_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_authority_id",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "replacement_authority_basis_hash",
        "downstream_dependency_hash",
        "commit_basis_hash",
        "operator_decision",
    } == set(commit_request_schema["required"])
    assert commit_request_schema["properties"]["operator_decision"]["enum"] == ["commit_package_supersession"]
    assert commit_request_schema["properties"]["package_payload"]["description"].startswith("Known but non-admitted")
    assert commit_request_schema["properties"]["replacement_output_package_ids"]["description"].startswith(
        "Known but non-admitted"
    )

    commit_schema = _openapi_response_schema(spec, "/api/v1/layer3/package/supersession/commit", "post")
    assert commit_schema["title"] == "Layer3PackageSupersessionCommitResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "package_supersession_commit_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_package_set_authority_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "replacement_authority_basis_hash",
        "downstream_dependency_hash",
        "commit_basis_hash",
        "commit_snapshot",
        "operator_decision",
        "package_supersession_commit_mode",
        "source_gate",
        "package_supersession_commit_record_persisted",
        "package_row_mutation_enabled",
        "package_payload_write_enabled",
        "l3_output_package_write_enabled",
        "broad_package_mutation_enabled",
        "source_widening_enabled",
        "connector_dispatch_enabled",
        "provider_public_url_enabled",
        "qualitative_hybrid_rag_execution_enabled",
        "frontend_only_durable_state_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(commit_schema["required"])

    artifact_manifest_request_schema = spec["paths"][
        "/api/v1/layer3/package/replacement-artifact/manifest/record"
    ]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert artifact_manifest_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "hash_algorithm",
        "artifact_namespace",
        "artifact_manifest_hash",
        "authority_basis_hash",
        "operator_decision",
    } == set(artifact_manifest_request_schema["required"])
    assert artifact_manifest_request_schema["properties"]["operator_decision"]["enum"] == [
        "record_replacement_package_artifact_manifest"
    ]
    assert artifact_manifest_request_schema["properties"]["hash_algorithm"]["enum"] == ["sha256"]
    assert artifact_manifest_request_schema["properties"]["artifact_namespace"]["enum"] == [
        "replacement-package-artifacts"
    ]
    assert artifact_manifest_request_schema["properties"]["generate_artifact"]["description"].startswith(
        "Known but non-admitted"
    )
    assert artifact_manifest_request_schema["properties"]["replacement_output_package_ids"]["description"].startswith(
        "Known but non-admitted"
    )

    artifact_manifest_schema = _openapi_response_schema(
        spec,
        "/api/v1/layer3/package/replacement-artifact/manifest/record",
        "post",
    )
    assert artifact_manifest_schema["title"] == "Layer3ReplacementPackageArtifactManifestResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "replacement_package_artifact_manifest_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "verified_artifact_refs",
        "verified_artifact_hashes",
        "verified_artifact_byte_sizes",
        "hash_algorithm",
        "artifact_namespace",
        "artifact_manifest_hash",
        "authority_basis_hash",
        "manifest_snapshot",
        "operator_decision",
        "replacement_package_artifact_manifest_mode",
        "source_gate",
        "manifest_record_persisted",
        "artifact_generation_enabled",
        "package_row_mutation_enabled",
        "package_payload_write_enabled",
        "l3_output_package_write_enabled",
        "broad_package_mutation_enabled",
        "source_widening_enabled",
        "connector_dispatch_enabled",
        "provider_public_url_enabled",
        "qualitative_hybrid_rag_execution_enabled",
        "frontend_only_durable_state_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(artifact_manifest_schema["required"])

    namespace_request_schema = spec["paths"]["/api/v1/layer3/package/replacement-namespace/record"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    assert namespace_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "replacement_artifact_manifest_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "source_output_package_id",
        "package_kind",
        "package_schema_id",
        "artifact_ref",
        "artifact_hash",
        "authority_basis_hash",
        "operator_decision",
    } == set(namespace_request_schema["required"])
    assert namespace_request_schema["properties"]["operator_decision"]["enum"] == [
        "record_replacement_package_namespace"
    ]
    assert namespace_request_schema["properties"]["package_payload"]["description"].startswith(
        "Known but non-admitted"
    )
    assert namespace_request_schema["properties"]["connector_destination"]["description"].startswith(
        "Known but non-admitted"
    )
    assert namespace_request_schema["properties"]["auth_security_directive"]["description"].startswith(
        "Known but non-admitted"
    )

    namespace_schema = _openapi_response_schema(
        spec,
        "/api/v1/layer3/package/replacement-namespace/record",
        "post",
    )
    assert namespace_schema["title"] == "Layer3ReplacementPackageNamespaceRecordResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "replacement_output_package_id",
        "session_id",
        "source_output_package_id",
        "replacement_artifact_manifest_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "package_kind",
        "package_schema_id",
        "artifact_ref",
        "artifact_hash",
        "authority_basis_hash",
        "summary",
        "operator_decision",
        "replacement_package_namespace_mode",
        "source_gate",
        "namespace_row_persisted",
        "package_row_mutation_enabled",
        "package_payload_write_enabled",
        "l3_output_package_write_enabled",
        "broad_package_mutation_enabled",
        "source_widening_enabled",
        "connector_dispatch_enabled",
        "provider_public_url_enabled",
        "qualitative_hybrid_rag_execution_enabled",
        "frontend_only_durable_state_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(namespace_schema["required"])

    record_request_schema = spec["paths"]["/api/v1/layer3/handoff/connector/record"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    assert record_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_state",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "external_export_download_record_ref",
        "external_export_download_state",
        "delivery_mode",
        "operator_decision",
    } == set(record_request_schema["required"])
    assert record_request_schema["properties"]["delivery_mode"]["enum"] == ["same_origin_artifact_stream"]
    assert record_request_schema["properties"]["operator_decision"]["enum"] == [
        "record_internal_connector_dispatch"
    ]
    assert record_request_schema["properties"]["connector_key"]["description"].startswith("Known but non-admitted")
    assert record_request_schema["properties"]["provider_public_url"]["description"].startswith(
        "Known but non-admitted"
    )

    record_schema = _openapi_response_schema(spec, "/api/v1/layer3/handoff/connector/record", "post")
    assert record_schema["title"] == "Layer3ConnectorDispatchRecordResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_identity",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "source_artifact_ref",
        "source_artifact_schema_id",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "external_export_download_record_ref",
        "external_export_download_state",
        "external_export_download_descriptor_ref",
        "delivery_mode",
        "operator_decision",
        "decision_notes",
        "dispatch_mode",
        "connector_dispatch_record_state",
        "connector_dispatch_record_ref",
        "internal_dispatch_record_only_enabled",
        "external_connector_invocation_enabled",
        "destination_write_enabled",
        "connector_run_created",
        "provider_public_url_enabled",
        "package_mutation_enabled",
        "source_widening_enabled",
        "qualitative_hybrid_rag_execution_enabled",
        "downstream_unavailable",
        "next_state",
        "authority_rail",
    } <= set(record_schema["required"])


def test_layer3_json_workbench_error_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    route_statuses = {
        ("/api/v1/layer3/preflight", "post"): ("400",),
        ("/api/v1/layer3/source-preview", "post"): ("400",),
        ("/api/v1/layer3/source/mixed-corpus/seed", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/material-preview", "post"): ("400",),
        ("/api/v1/layer3/gate-b/decision", "post"): ("400", "409"),
        ("/api/v1/layer3/gate-c/preview", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/plan/preview", "post"): ("400", "404", "409", "500"),
        ("/api/v1/layer3/plan/approve", "post"): ("400", "404", "409", "500"),
        ("/api/v1/layer3/plan/approved/cancel", "post"): ("400", "404", "409", "500"),
        ("/api/v1/layer3/plan/revise", "post"): ("400", "404", "409", "500"),
        ("/api/v1/layer3/plan/revision/recover", "post"): ("400", "404", "409", "500"),
        ("/api/v1/layer3/execution/select", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/execution/start", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/execution/result/status", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/execution/result/review", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/package/review/preview", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/package/review/commit", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/package/review/submit", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/package/mutation/preview", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/package/replacement-artifact/manifest/record", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/package/replacement-namespace/record", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/handoff/export/prepare", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/handoff/aps/dispatch", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/handoff/export/download/prepare", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/handoff/connector/record", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/handoff/export/download/signed-reference/generate", "post"): ("400", "404", "409"),
        ("/api/v1/layer3/handoff/export/download/signed-reference/use", "post"): ("400", "404", "409"),
    }
    for (path, method), statuses in route_statuses.items():
        _assert_workbench_error_responses(spec, path, method, statuses)


@pytest.mark.parametrize(
    ("service_name", "method", "path", "payload"),
    [
        (
            "preflight",
            "post",
            "/api/v1/layer3/preflight",
            {"natural_language_intent": "Forced API boundary proof."},
        ),
        ("source_preview", "post", "/api/v1/layer3/source-preview", {"preflight_id": "preflight-forced"}),
        (
            "material_preview",
            "post",
            "/api/v1/layer3/material-preview",
            {"source_candidate_ids": ["src-dataset_version-forced"]},
        ),
        ("aps_dataset_version_candidates", "get", "/api/v1/layer3/dataset-version-candidates?limit=1", None),
        ("aps_content_document_candidates", "get", "/api/v1/layer3/aps-content-document-candidates?limit=1", None),
        (
            "gate_b_decision",
            "post",
            "/api/v1/layer3/gate-b/decision",
            {
                "client_request_id": "forced-boundary",
                "candidate_decisions": [{"candidate_id": "c1", "decision": "approved"}],
            },
        ),
        ("gate_c_preview", "post", "/api/v1/layer3/gate-c/preview", {"session_id": "session-forced"}),
        ("plan_preview", "post", "/api/v1/layer3/plan/preview", {}),
        (
            "plan_approval",
            "post",
            "/api/v1/layer3/plan/approve",
            {
                "session_id": "session-forced",
                "preview_id": "preview-forced",
                "preview_hash": "hash-forced",
                "operator_confirmation": True,
            },
        ),
        ("plan_revision", "post", "/api/v1/layer3/plan/revise", {}),
        (
            "plan_revision_recovery",
            "post",
            "/api/v1/layer3/plan/revision/recover",
            {
                "client_request_id": "forced-recovery-boundary",
                "session_id": "session-forced",
                "source_revision_state": "plan_rejected",
                "source_preview_id": "preview-forced",
                "source_preview_hash": "hash-forced",
                "operator_decision": "recover_for_preview_refresh",
            },
        ),
        (
            "approved_plan_cancel",
            "post",
            "/api/v1/layer3/plan/approved/cancel",
            {
                "client_request_id": "forced-approved-plan-cancel",
                "session_id": "session-forced",
                "analysis_plan_id": "plan-forced",
                "source_preview_id": "preview-forced",
                "source_preview_hash": "hash-forced",
                "operator_decision": "cancel_approved_plan_without_replacement",
            },
        ),
        ("execution_selection", "post", "/api/v1/layer3/execution/select", {}),
        ("analysis_execution_start", "post", "/api/v1/layer3/execution/start", {}),
        ("execution_result_status", "post", "/api/v1/layer3/execution/result/status", {}),
        ("execution_result_review", "post", "/api/v1/layer3/execution/result/review", {}),
        ("package_review_preview", "post", "/api/v1/layer3/package/review/preview", {}),
        ("package_construction_commit", "post", "/api/v1/layer3/package/review/commit", {}),
        ("package_review_submit", "post", "/api/v1/layer3/package/review/submit", {}),
        ("handoff_export_prepare", "post", "/api/v1/layer3/handoff/export/prepare", {}),
        ("aps_handoff_dispatch", "post", "/api/v1/layer3/handoff/aps/dispatch", {}),
        ("external_export_download_prepare", "post", "/api/v1/layer3/handoff/export/download/prepare", {}),
        (
            "external_export_download_generate_signed_reference",
            "post",
            "/api/v1/layer3/handoff/export/download/signed-reference/generate",
            {},
        ),
        ("session_summary", "get", "/api/v1/layer3/session/session-forced", None),
    ],
)
def test_layer3_api_json_or_error_call_sites_return_workbench_error_envelope(
    client: TestClient,
    monkeypatch,
    service_name: str,
    method: str,
    path: str,
    payload: dict | None,
) -> None:
    def _raise_forced_boundary_error(*_args, **_kwargs):
        raise layer3_workbench.Layer3WorkbenchError(
            "forced_api_boundary_error",
            "Forced API boundary proof.",
            status="conflict",
            http_status=409,
            recoverable=False,
            blocked_fields=["forced_field"],
            next_allowed_actions=["inspect_api_boundary"],
        )

    monkeypatch.setattr(layer3_workbench, service_name, _raise_forced_boundary_error)

    response = client.get(path) if method == "get" else client.post(path, json=payload)

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="forced_api_boundary_error",
    )
    assert body["message"] == "Forced API boundary proof."
    assert body["recoverable"] is False
    assert body["blocked_fields"] == ["forced_field"]
    assert body["next_allowed_actions"] == ["inspect_api_boundary"]


def test_layer3_raw_mixed_seed_api_boundary_returns_workbench_error_envelope(
    client: TestClient,
    monkeypatch,
) -> None:
    def _raise_forced_boundary_error(*_args, **_kwargs):
        raise layer3_workbench.Layer3WorkbenchError(
            "forced_raw_mixed_seed_boundary_error",
            "Forced raw mixed seed boundary proof.",
            status="conflict",
            http_status=409,
            recoverable=False,
            blocked_fields=["forced_field"],
            next_allowed_actions=["inspect_raw_mixed_seed_boundary"],
        )

    monkeypatch.setattr(layer3_raw_mixed_bridge, "seed_raw_mixed_corpus", _raise_forced_boundary_error)

    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/seed",
        json={
            "client_request_id": "forced-raw-mixed-seed-boundary",
            "seed_mode": "raw_mixed_corpus_bridge_seed_only",
            "corpus_batch_id": "forced-batch",
            "aps_run_id": "forced-run",
            "target_ids": ["forced-target"],
            "artifact_manifest_ref": "raw-mixed/forced.json",
            "artifact_manifest_hash": "0" * 64,
            "requested_source_classes": ["dataset_version", "aps_content_document"],
            "operator_confirmation": True,
        },
    )

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="forced_raw_mixed_seed_boundary_error",
    )
    assert body["message"] == "Forced raw mixed seed boundary proof."
    assert body["recoverable"] is False
    assert body["blocked_fields"] == ["forced_field"]
    assert body["next_allowed_actions"] == ["inspect_raw_mixed_seed_boundary"]


def test_layer3_connector_dispatch_record_api_boundary_returns_workbench_error_envelope(
    client: TestClient,
    monkeypatch,
) -> None:
    def _raise_forced_boundary_error(*_args, **_kwargs):
        raise layer3_workbench.Layer3WorkbenchError(
            "forced_connector_record_boundary_error",
            "Forced connector record boundary proof.",
            status="conflict",
            http_status=409,
            recoverable=False,
            blocked_fields=["forced_field"],
            next_allowed_actions=["inspect_connector_record_boundary"],
        )

    monkeypatch.setattr(
        layer3_connector_dispatch_entry,
        "record_internal_connector_dispatch",
        _raise_forced_boundary_error,
    )

    response = client.post("/api/v1/layer3/handoff/connector/record", json={})

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="forced_connector_record_boundary_error",
    )
    assert body["message"] == "Forced connector record boundary proof."
    assert body["recoverable"] is False
    assert body["blocked_fields"] == ["forced_field"]
    assert body["next_allowed_actions"] == ["inspect_connector_record_boundary"]


def test_layer3_replacement_package_artifact_manifest_api_boundary_returns_workbench_error_envelope(
    client: TestClient,
    monkeypatch,
) -> None:
    def _raise_forced_boundary_error(*_args, **_kwargs):
        raise layer3_workbench.Layer3WorkbenchError(
            "forced_replacement_artifact_manifest_boundary_error",
            "Forced replacement artifact manifest boundary proof.",
            status="conflict",
            http_status=409,
            recoverable=False,
            blocked_fields=["forced_field"],
            next_allowed_actions=["inspect_replacement_artifact_manifest_boundary"],
        )

    monkeypatch.setattr(
        layer3_replacement_package_artifact_manifest,
        "record_replacement_package_artifact_manifest",
        _raise_forced_boundary_error,
    )

    response = client.post("/api/v1/layer3/package/replacement-artifact/manifest/record", json={})

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="forced_replacement_artifact_manifest_boundary_error",
    )
    assert body["message"] == "Forced replacement artifact manifest boundary proof."
    assert body["recoverable"] is False
    assert body["blocked_fields"] == ["forced_field"]
    assert body["next_allowed_actions"] == ["inspect_replacement_artifact_manifest_boundary"]


def test_layer3_replacement_package_namespace_api_boundary_returns_workbench_error_envelope(
    client: TestClient,
    monkeypatch,
) -> None:
    def _raise_forced_boundary_error(*_args, **_kwargs):
        raise layer3_workbench.Layer3WorkbenchError(
            "forced_replacement_package_namespace_boundary_error",
            "Forced replacement package namespace boundary proof.",
            status="conflict",
            http_status=409,
            recoverable=False,
            blocked_fields=["forced_field"],
            next_allowed_actions=["inspect_replacement_package_namespace_boundary"],
        )

    monkeypatch.setattr(
        layer3_replacement_package_namespace,
        "record_replacement_package_namespace",
        _raise_forced_boundary_error,
    )

    response = client.post("/api/v1/layer3/package/replacement-namespace/record", json={})

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="forced_replacement_package_namespace_boundary_error",
    )
    assert body["message"] == "Forced replacement package namespace boundary proof."
    assert body["recoverable"] is False
    assert body["blocked_fields"] == ["forced_field"]
    assert body["next_allowed_actions"] == ["inspect_replacement_package_namespace_boundary"]


def test_layer3_package_supersession_preview_api_boundary_returns_workbench_error_envelope(
    client: TestClient,
    monkeypatch,
) -> None:
    def _raise_forced_boundary_error(*_args, **_kwargs):
        raise layer3_workbench.Layer3WorkbenchError(
            "forced_package_supersession_preview_boundary_error",
            "Forced package supersession preview boundary proof.",
            status="conflict",
            http_status=409,
            recoverable=False,
            blocked_fields=["forced_field"],
            next_allowed_actions=["inspect_package_supersession_preview_boundary"],
        )

    monkeypatch.setattr(
        layer3_package_mutation_entry,
        "preview_package_supersession",
        _raise_forced_boundary_error,
    )

    response = client.post("/api/v1/layer3/package/mutation/preview", json={})

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="forced_package_supersession_preview_boundary_error",
    )
    assert body["message"] == "Forced package supersession preview boundary proof."
    assert body["recoverable"] is False
    assert body["blocked_fields"] == ["forced_field"]
    assert body["next_allowed_actions"] == ["inspect_package_supersession_preview_boundary"]


def test_layer3_special_route_openapi_contracts(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    override_responses = spec["paths"]["/api/v1/layer3/gate-c/override"]["post"]["responses"]
    assert "200" not in override_responses
    override_request_schema = spec["paths"]["/api/v1/layer3/gate-c/override"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    override_request_schema = _resolve_openapi_schema(spec, override_request_schema)
    assert override_request_schema["additionalProperties"] is False
    assert {
        "schema_id",
        "schema_version",
        "client_request_id",
        "session_id",
        "actor",
    } == set(override_request_schema["properties"])
    override_schema = _openapi_response_schema_for_status(spec, "/api/v1/layer3/gate-c/override", "post", "409")
    assert override_schema["title"] == "Layer3TypingOverrideUnavailableResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "error_code",
        "message",
        "recoverable",
        "next_allowed_actions",
    } <= set(override_schema["required"])

    deliver_responses = spec["paths"]["/api/v1/layer3/handoff/export/download/deliver"]["post"]["responses"]
    deliver_request_body = spec["paths"]["/api/v1/layer3/handoff/export/download/deliver"]["post"]["requestBody"]
    assert deliver_request_body["required"] is True
    assert {"application/json", "application/x-www-form-urlencoded"} <= set(deliver_request_body["content"])
    deliver_request_schema = deliver_request_body["content"]["application/json"]["schema"]
    deliver_form_schema = deliver_request_body["content"]["application/x-www-form-urlencoded"]["schema"]
    assert deliver_request_schema["additionalProperties"] is False
    assert {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "dispatch_mode",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "aps_bundle_id",
        "aps_schema_id",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "export_download_target",
        "download_mode",
        "delivery_mode",
        "operator_decision",
    } <= set(deliver_request_schema["required"])
    assert deliver_request_schema["properties"]["delivery_mode"]["enum"] == ["same_origin_artifact_stream"]
    assert deliver_request_schema["properties"]["operator_decision"]["enum"] == ["deliver_external_export_download"]
    _assert_string_array_or_string_map_schema(deliver_request_schema["properties"]["payload_refs"])
    _assert_string_array_or_string_map_schema(deliver_request_schema["properties"]["payload_hashes"])
    assert "download_url" not in deliver_request_schema["properties"]
    assert "connector_run_id" not in deliver_request_schema["properties"]
    assert deliver_form_schema["additionalProperties"] is False
    assert "JSON-stringified" in deliver_form_schema["description"]
    assert "JSON array strings or JSON object strings" in deliver_form_schema["description"]
    assert "not as repeated form keys" in deliver_form_schema["description"]
    assert set(deliver_request_schema["required"]) == set(deliver_form_schema["required"])
    assert set(deliver_request_schema["properties"]) == set(deliver_form_schema["properties"])
    assert deliver_request_schema["properties"]["output_package_ids"]["type"] == "array"
    assert deliver_form_schema["properties"]["output_package_ids"]["type"] == "string"
    assert deliver_form_schema["properties"]["payload_refs"]["type"] == "string"
    assert deliver_form_schema["properties"]["payload_hashes"]["type"] == "string"
    assert "download_url" not in deliver_form_schema["properties"]
    assert "connector_run_id" not in deliver_form_schema["properties"]

    deliver_success_schema = deliver_responses["200"]["content"]["application/json"]["schema"]
    assert deliver_success_schema == {"type": "string", "format": "binary"}
    assert {
        "Content-Disposition",
        "X-Layer3-Schema-Id",
        "X-Layer3-Delivery-State",
        "X-Layer3-Source-Artifact-Hash",
    } <= set(deliver_responses["200"]["headers"])
    for status in ("400", "404", "409"):
        error_schema = _openapi_response_schema_for_status(
            spec,
            "/api/v1/layer3/handoff/export/download/deliver",
            "post",
            status,
        )
        assert error_schema["title"] == "Layer3WorkbenchErrorResponse"
        assert {
            "schema_id",
            "schema_version",
            "request_id",
            "server_time",
            "status",
            "error_code",
            "message",
            "recoverable",
            "blocked_fields",
            "next_allowed_actions",
        } <= set(error_schema["required"])

    signed_generate = spec["paths"]["/api/v1/layer3/handoff/export/download/signed-reference/generate"]["post"]
    signed_generate_schema = signed_generate["requestBody"]["content"]["application/json"]["schema"]
    assert signed_generate_schema["additionalProperties"] is False
    assert set(signed_generate_schema["required"]) == set(deliver_request_schema["required"])
    assert signed_generate_schema["properties"]["delivery_mode"]["enum"] == ["same_origin_artifact_stream"]
    assert "download_url" not in signed_generate_schema["properties"]
    assert "download_token" not in signed_generate_schema["properties"]
    assert "public_url" not in signed_generate_schema["properties"]
    assert "signed_url" not in signed_generate_schema["properties"]
    signed_generate_success = signed_generate["responses"]["200"]["content"]["application/json"]["schema"]
    assert signed_generate_success["$ref"].endswith("/Layer3ExternalExportDownloadSignedReferenceResponse")
    for status in ("400", "404", "409"):
        error_schema = _openapi_response_schema_for_status(
            spec,
            "/api/v1/layer3/handoff/export/download/signed-reference/generate",
            "post",
            status,
        )
        assert error_schema["title"] == "Layer3WorkbenchErrorResponse"

    signed_use = spec["paths"]["/api/v1/layer3/handoff/export/download/signed-reference/use"]["post"]
    signed_use_schema = signed_use["requestBody"]["content"]["application/json"]["schema"]
    assert signed_use_schema["type"] == "object"
    assert signed_use_schema["additionalProperties"] is False
    assert signed_use_schema["required"] == ["signed_reference_token"]
    assert signed_use_schema["properties"] == {
        "signed_reference_token": {
            "type": "string",
            "description": "Server-generated short-lived signed delivery reference token.",
        },
    }
    signed_use_success = signed_use["responses"]["200"]["content"]["application/json"]["schema"]
    assert signed_use_success == {"type": "string", "format": "binary"}
    assert {
        "Content-Disposition",
        "X-Layer3-Schema-Id",
        "X-Layer3-Delivery-State",
        "X-Layer3-Source-Artifact-Hash",
        "X-Layer3-Signed-Reference-State",
        "X-Layer3-Signed-Reference-Expires-At",
        "X-Layer3-Signed-Reference-Token-Id",
        "X-Layer3-Signed-Reference-Receipt-Id",
        "X-Layer3-Signed-Reference-Replay-Policy",
        "X-Layer3-Signed-Reference-Use-Count",
    } <= set(signed_use["responses"]["200"]["headers"])
    for status in ("400", "404", "409"):
        error_schema = _openapi_response_schema_for_status(
            spec,
            "/api/v1/layer3/handoff/export/download/signed-reference/use",
            "post",
            status,
        )
        assert error_schema["title"] == "Layer3WorkbenchErrorResponse"

    session_schema = _openapi_response_schema(spec, "/api/v1/layer3/session/{session_id}", "get")
    assert session_schema["title"] == "Layer3SessionSummaryResponse"
    assert {
        "schema_id",
        "schema_version",
        "request_id",
        "server_time",
        "status",
        "session_id",
        "selection_manifest_id",
        "current_gate",
        "gate_b_summary",
        "gate_c_summary",
        "plan_preview",
        "plan_approval",
        "plan_revision",
        "approved_plan_cancel",
        "execution_selection",
        "analysis_execution_start",
        "execution_result_review",
        "package_review_preview",
        "package_construction",
        "package_review_submit",
        "handoff_export_prepare",
        "aps_handoff_dispatch",
        "external_export_download",
        "sublayer_visualization",
        "state_action_contract",
        "downstream_unavailable",
        "authority_rail",
    } <= set(session_schema["required"])
    session_error_schema = _openapi_response_schema_for_status(
        spec,
        "/api/v1/layer3/session/{session_id}",
        "get",
        "404",
    )
    assert session_error_schema["title"] == "Layer3WorkbenchErrorResponse"
    session_conflict_schema = _openapi_response_schema_for_status(
        spec,
        "/api/v1/layer3/session/{session_id}",
        "get",
        "409",
    )
    assert session_conflict_schema["title"] == "Layer3WorkbenchErrorResponse"


def _approve_quant_plan(client: TestClient, tmp_path) -> tuple[str, dict, dict]:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-execution-selection-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-execution-selection-approval",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200
    return session_id, preview_body, approval.json()


def _build_aps_handoff_ready_session(db, tmp_path: Path) -> tuple[str, str, str, str]:
    dataset_version_id = "dv-api-aps-handoff-001"
    run_id = "run-api-aps-handoff-001"
    target_id = "target-api-aps-handoff-001"
    content_id = "content-api-aps-handoff-001"
    _seed_timeseries_dataset_version(db, tmp_path, dataset_version_id=dataset_version_id)
    _seed_aps_content_fixture(db, tmp_path, run_id=run_id, target_id=target_id, content_id=content_id)

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": "sel-api-aps-handoff-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": "sel-api-aps-handoff-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="api-aps-handoff-dispatch-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "api_aps_handoff_dispatch"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={
                    "dataset_id": f"ds-{dataset_version_id}",
                    "storage_ref": str(tmp_path / "datasets" / f"{dataset_version_id}.csv"),
                },
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": content_id, "run_id": run_id, "target_id": target_id},
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "aps qualitative companion"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id, run_id, target_id, content_id


def _build_cohort_aps_handoff_ready_session(db, tmp_path: Path) -> tuple[str, str, str, str]:
    first_dataset_version_id = "dv-api-cohort-aps-001"
    second_dataset_version_id = "dv-api-cohort-aps-002"
    run_id = "run-api-cohort-aps-001"
    target_id = "target-api-cohort-aps-001"
    content_id = "content-api-cohort-aps-001"
    _seed_cohort_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-api-cohort-aps-001",
        dataset_version_id=first_dataset_version_id,
        values=[50 + index for index in range(24)],
    )
    _seed_cohort_timeseries_dataset_version(
        db,
        tmp_path,
        dataset_id="ds-api-cohort-aps-002",
        dataset_version_id=second_dataset_version_id,
        values=[150 + (index * 2) for index in range(24)],
    )
    _seed_aps_content_fixture(db, tmp_path, run_id=run_id, target_id=target_id, content_id=content_id)

    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"selection_group": "sel-api-cohort-aps-quant"},
                "selection_basis": {"selection_id": "sel-api-cohort-aps-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": "sel-api-cohort-aps-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="api-cohort-aps-handoff-dispatch-proof",
        entry_route_context={"entrypoint": "pytest"},
        operator_context={"operator": "pytest"},
        summary={"phase": "api_cohort_aps_handoff_dispatch"},
    )

    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    descriptors_by_type = {descriptor.descriptor_type: descriptor for descriptor in descriptors}
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors_by_type["dataset_version"],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": first_dataset_version_id},
                source_provenance={
                    "dataset_id": "ds-api-cohort-aps-001",
                    "storage_ref": str(tmp_path / "datasets" / f"{first_dataset_version_id}.csv"),
                },
                payload={"dataset_version_id": first_dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": second_dataset_version_id},
                source_provenance={
                    "dataset_id": "ds-api-cohort-aps-002",
                    "storage_ref": str(tmp_path / "datasets" / f"{second_dataset_version_id}.csv"),
                },
                payload={"dataset_version_id": second_dataset_version_id},
                load_summary={"loaded_records": 1, "failed_records": 0},
            ),
        ],
        storage_root=tmp_path,
    )
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors_by_type["aps_content_document"],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": content_id, "run_id": run_id, "target_id": target_id},
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "aps qualitative companion for cohort handoff"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=tmp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    associated_set = (
        db.query(L3AnalysisSet)
        .filter(
            L3AnalysisSet.session_id == session.session_id,
            L3AnalysisSet.set_type == "associated_cohort",
        )
        .one()
    )
    associated_set.formation_basis_json = {
        **associated_set.formation_basis_json,
        "requested_method_name": "descriptive_summary",
    }
    db.commit()
    return session.session_id, run_id, target_id, content_id


def _approve_aps_handoff_plan(client: TestClient, tmp_path) -> tuple[str, dict, dict]:
    db = client.layer3_session_factory()
    try:
        session_id, _, _, _ = _build_aps_handoff_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-aps-dispatch-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-aps-dispatch-approval",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200
    return session_id, preview_body, approval.json()


def _approve_cohort_aps_handoff_plan(client: TestClient, tmp_path) -> tuple[str, dict, dict]:
    db = client.layer3_session_factory()
    try:
        session_id, _, _, _ = _build_cohort_aps_handoff_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-cohort-aps-dispatch-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-cohort-aps-dispatch-approval",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200
    return session_id, preview_body, approval.json()


def _approve_quant_cohort_plan(client: TestClient, tmp_path) -> tuple[str, dict, dict]:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_cohort_ready_session(
            db,
            tmp_path,
            requested_method_name="descriptive_summary",
        )
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-cohort-execution-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-cohort-execution-approval",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200
    return session_id, preview_body, approval.json()


def _patch_cohort_dataframe_persistence(monkeypatch, tmp_path) -> None:
    def _persist_dataframe_as_csv(db, version, df, time_column) -> None:
        frame = df.copy()
        storage_path = tmp_path / "cohort-derived" / f"{version.dataset_version_id}.csv"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(storage_path, index=False)
        version.storage_ref = str(storage_path)
        version.row_count = int(len(frame))
        db.flush()

    monkeypatch.setattr(dataframe_io, "persist_dataframe_as_version_rows", _persist_dataframe_as_csv)


def _select_quant_pass(
    client: TestClient,
    tmp_path,
    *,
    request_id: str = "api-analysis-execution-selection",
) -> tuple[str, dict, dict, dict]:
    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": request_id,
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200
    return session_id, preview_body, approval_body, selection.json()


def _select_quant_cohort_pass(
    client: TestClient,
    tmp_path,
    *,
    request_id: str = "api-analysis-execution-cohort-selection",
) -> tuple[str, dict, dict, dict]:
    session_id, preview_body, approval_body = _approve_quant_cohort_plan(client, tmp_path)
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": request_id,
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200
    return session_id, preview_body, approval_body, selection.json()


def _start_and_approve_quant_result_review(
    client: TestClient,
    *,
    session_id: str,
    preview_body: dict,
    approval_body: dict,
    selection_body: dict,
    request_id: str,
) -> tuple[dict, dict, dict]:
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": f"{request_id}-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200
    start_body = start.json()

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["status"] == "available"

    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": f"{request_id}-review",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Output is traceable enough for package preview readiness.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200
    review_body = review.json()
    assert review_body["review_state"] == "execution_result_review_approved"
    return start_body, status_body, review_body


def _execute_and_approve_quant_result_review(
    client: TestClient,
    tmp_path,
    *,
    request_id: str = "api-package-preview",
) -> tuple[str, dict, dict, dict, dict, dict, dict]:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id=f"{request_id}-selection",
    )
    start_body, status_body, review_body = _start_and_approve_quant_result_review(
        client,
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        request_id=request_id,
    )
    return session_id, preview_body, approval_body, selection_body, start_body, status_body, review_body


def _construct_quant_package_set(
    client: TestClient,
    tmp_path,
    *,
    request_id: str,
) -> tuple[str, dict, dict, dict, dict, dict, dict, dict, dict]:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        _status_body,
        review_body,
    ) = _execute_and_approve_quant_result_review(client, tmp_path, request_id=request_id)
    pass_run_id = selection_body["pass_run_ids"][0]
    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_id}-package-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200
    package_preview_body = package_preview.json()
    commit_payload = {
        "client_request_id": f"{request_id}-package-commit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    package_commit = client.post("/api/v1/layer3/package/review/commit", json=commit_payload)
    assert package_commit.status_code == 200
    return (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        package_preview_body,
        package_commit.json(),
        commit_payload,
    )


def _submit_quant_package_review(
    client: TestClient,
    tmp_path,
    *,
    request_id: str,
    operator_decision: str = "approved",
    decision_notes: str | None = None,
) -> tuple[str, dict, dict, dict, dict, dict, dict, dict, dict, dict]:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id=request_id)
    pass_run_id = selection_body["pass_run_ids"][0]
    submit_payload = {
        "client_request_id": f"{request_id}-package-submit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": operator_decision,
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    if decision_notes is not None:
        submit_payload["decision_notes"] = decision_notes
    submit = client.post("/api/v1/layer3/package/review/submit", json=submit_payload)
    assert submit.status_code == 200
    return (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        package_preview_body,
        commit_body,
        submit_payload,
        submit.json(),
    )


def _package_supersession_preview_payload(
    *,
    request_id: str,
    session_id: str,
    approval_body: dict,
    selection_body: dict,
    review_body: dict,
    commit_body: dict,
    start_body: dict | None = None,
    submit_body: dict | None = None,
    prepare_body: dict | None = None,
    dispatch_body: dict | None = None,
    readiness_body: dict | None = None,
    connector_body: dict | None = None,
) -> dict:
    payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "analysis_run_id": (start_body or {}).get("analysis_run_id"),
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "package_kinds": commit_body["package_kinds"],
        "payload_refs": commit_body["payload_refs"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "preview_package_supersession",
    }
    if submit_body is not None:
        payload["package_review_submit_record_ref"] = submit_body["submit_record_ref"]
    if prepare_body is not None:
        payload["handoff_export_record_ref"] = prepare_body["prepare_record_ref"]
    if dispatch_body is not None:
        payload["aps_handoff_record_ref"] = dispatch_body["aps_handoff_record_ref"]
    if readiness_body is not None:
        payload["external_export_download_record_ref"] = readiness_body["external_export_download_record_ref"]
    if connector_body is not None:
        payload["connector_dispatch_record_ref"] = connector_body["connector_dispatch_record_ref"]
    return {key: value for key, value in payload.items() if value is not None}


def _replacement_package_set_authority_payload(
    *,
    request_id: str,
    session_id: str,
    approval_body: dict,
    selection_body: dict,
    commit_body: dict,
    source_package_set_hash: str,
) -> dict:
    replacement_package_set_id = f"replacement-set-{request_id}"
    replacement_package_kinds = list(commit_body["package_kinds"])
    replacement_payload_refs = [f"{payload_ref}.replacement" for payload_ref in commit_body["payload_refs"]]
    replacement_payload_hashes = [
        hashlib.sha256(f"{request_id}:{package_kind}:{payload_ref}".encode("utf-8")).hexdigest()
        for package_kind, payload_ref in zip(replacement_package_kinds, replacement_payload_refs)
    ]
    replacement_package_set_hash = layer3_replacement_package_set_authority.replacement_package_set_hash(
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    authority_basis_hash = layer3_replacement_package_set_authority.replacement_package_set_authority_basis_hash(
        session_id=session_id,
        analysis_plan_id=approval_body["analysis_plan_id"],
        pass_run_id=selection_body["pass_run_ids"][0],
        reconciliation_record_id=commit_body["reconciliation_record_id"],
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=[package["output_package_id"] for package in commit_body["output_packages"]],
        source_package_kinds=commit_body["package_kinds"],
        source_payload_refs=commit_body["payload_refs"],
        source_payload_hashes=commit_body["payload_hashes"],
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    return {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "source_package_set_hash": source_package_set_hash,
        "source_output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "source_package_kinds": commit_body["package_kinds"],
        "source_payload_refs": commit_body["payload_refs"],
        "source_payload_hashes": commit_body["payload_hashes"],
        "replacement_package_set_id": replacement_package_set_id,
        "replacement_package_set_hash": replacement_package_set_hash,
        "replacement_package_kinds": replacement_package_kinds,
        "replacement_payload_refs": replacement_payload_refs,
        "replacement_payload_hashes": replacement_payload_hashes,
        "authority_basis_hash": authority_basis_hash,
        "operator_decision": "record_replacement_package_set_authority",
    }


def _package_supersession_commit_payload(
    *,
    request_id: str,
    session_id: str,
    approval_body: dict,
    selection_body: dict,
    commit_body: dict,
    supersession_preview_body: dict,
    replacement_authority_body: dict,
) -> dict:
    downstream_dependency_hash = layer3_package_supersession_commit.package_supersession_downstream_dependency_hash(
        supersession_preview_body["downstream_dependencies"]
    )
    commit_basis_hash = layer3_package_supersession_commit.package_supersession_commit_basis_hash(
        session_id=session_id,
        analysis_plan_id=approval_body["analysis_plan_id"],
        pass_run_id=selection_body["pass_run_ids"][0],
        reconciliation_record_id=commit_body["reconciliation_record_id"],
        package_supersession_preview_hash=supersession_preview_body["package_supersession_preview_hash"],
        source_package_set_hash=supersession_preview_body["package_set_hash"],
        source_output_package_ids=[package["output_package_id"] for package in commit_body["output_packages"]],
        source_package_kinds=commit_body["package_kinds"],
        source_payload_refs=commit_body["payload_refs"],
        source_payload_hashes=commit_body["payload_hashes"],
        replacement_package_set_authority_id=replacement_authority_body["replacement_package_set_authority_id"],
        replacement_authority_basis_hash=replacement_authority_body["authority_basis_hash"],
        replacement_package_set_id=replacement_authority_body["replacement_package_set_id"],
        replacement_package_set_hash=replacement_authority_body["replacement_package_set_hash"],
        replacement_package_kinds=replacement_authority_body["replacement_package_kinds"],
        replacement_payload_refs=replacement_authority_body["replacement_payload_refs"],
        replacement_payload_hashes=replacement_authority_body["replacement_payload_hashes"],
        downstream_dependency_hash=downstream_dependency_hash,
    )
    return {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "package_supersession_preview_hash": supersession_preview_body["package_supersession_preview_hash"],
        "source_package_set_hash": supersession_preview_body["package_set_hash"],
        "source_output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "source_package_kinds": commit_body["package_kinds"],
        "source_payload_refs": commit_body["payload_refs"],
        "source_payload_hashes": commit_body["payload_hashes"],
        "replacement_package_set_authority_id": replacement_authority_body["replacement_package_set_authority_id"],
        "replacement_package_set_id": replacement_authority_body["replacement_package_set_id"],
        "replacement_package_set_hash": replacement_authority_body["replacement_package_set_hash"],
        "replacement_package_kinds": replacement_authority_body["replacement_package_kinds"],
        "replacement_payload_refs": replacement_authority_body["replacement_payload_refs"],
        "replacement_payload_hashes": replacement_authority_body["replacement_payload_hashes"],
        "replacement_authority_basis_hash": replacement_authority_body["authority_basis_hash"],
        "downstream_dependency_hash": downstream_dependency_hash,
        "commit_basis_hash": commit_basis_hash,
        "operator_decision": "commit_package_supersession",
    }


def _handoff_export_prepare_payload(
    *,
    request_id: str,
    session_id: str,
    preview_body: dict,
    approval_body: dict,
    selection_body: dict,
    start_body: dict,
    review_body: dict,
    commit_body: dict,
    submit_body: dict,
    operator_decision: str = "authorize_prepare",
    decision_notes: str | None = None,
) -> dict:
    payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "payload_refs": commit_body["payload_refs"],
        "payload_hashes": commit_body["payload_hashes"],
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": submit_body["package_review_state"],
        "package_review_submit_schema_id": submit_body.get("schema_id", "layer3.package_review_submit.v1"),
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": operator_decision,
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    if commit_body.get("construction_basis_hash") is not None:
        payload["construction_basis_hash"] = commit_body["construction_basis_hash"]
    if decision_notes is not None:
        payload["decision_notes"] = decision_notes
    return payload


def _aps_handoff_dispatch_payload(
    *,
    request_id: str,
    session_id: str,
    preview_body: dict,
    approval_body: dict,
    selection_body: dict,
    start_body: dict,
    review_body: dict,
    commit_body: dict,
    submit_body: dict,
    prepare_body: dict,
    decision_notes: str | None = None,
) -> dict:
    envelope = prepare_body.get("handoff_export_envelope") or {}
    payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "package_kinds": commit_body["package_kinds"],
        "payload_refs": commit_body["payload_refs"],
        "payload_hashes": commit_body["payload_hashes"],
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": submit_body["package_review_state"],
        "prepare_record_ref": prepare_body["prepare_record_ref"],
        "handoff_export_state": prepare_body["handoff_export_state"],
        "handoff_export_envelope_ref": envelope.get("envelope_ref"),
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "operator_decision": "dispatch_aps_handoff",
    }
    if decision_notes is not None:
        payload["decision_notes"] = decision_notes
    return payload


def _external_export_download_prepare_payload(
    *,
    request_id: str,
    session_id: str,
    preview_body: dict,
    approval_body: dict,
    selection_body: dict,
    start_body: dict,
    review_body: dict,
    commit_body: dict,
    submit_body: dict,
    prepare_body: dict,
    dispatch_body: dict,
    decision_notes: str | None = None,
) -> dict:
    aps_bundle_path = Path(dispatch_body["aps_bundle_ref"])
    payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "package_kinds": commit_body["package_kinds"],
        "payload_refs": commit_body["payload_refs"],
        "payload_hashes": commit_body["payload_hashes"],
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": submit_body["package_review_state"],
        "prepare_record_ref": prepare_body["prepare_record_ref"],
        "handoff_export_state": prepare_body["handoff_export_state"],
        "handoff_export_envelope_ref": prepare_body["handoff_export_envelope"]["envelope_ref"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_record_ref": dispatch_body["aps_handoff_record_ref"],
        "aps_handoff_state": dispatch_body["aps_handoff_state"],
        "aps_handoff_target": dispatch_body["aps_handoff_target"],
        "dispatch_mode": dispatch_body["dispatch_mode"],
        "aps_output_package_id": dispatch_body["aps_output_package_id"],
        "aps_output_package_kind": dispatch_body["aps_output_package_kind"],
        "aps_bundle_ref": dispatch_body["aps_bundle_ref"],
        "aps_bundle_id": dispatch_body["aps_bundle_id"],
        "aps_schema_id": dispatch_body["aps_schema_id"],
        "aps_bundle_hash": hashlib.sha256(aps_bundle_path.read_bytes()).hexdigest(),
        "aps_bundle_size_bytes": aps_bundle_path.stat().st_size,
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "operator_decision": "prepare_external_export_download",
    }
    if decision_notes is not None:
        payload["decision_notes"] = decision_notes
    return payload


def _external_export_download_deliver_payload(
    *,
    request_id: str,
    prepare_payload: dict,
    readiness_body: dict,
    decision_notes: str | None = None,
) -> dict:
    payload = {
        **prepare_payload,
        "client_request_id": request_id,
        "operator_decision": "deliver_external_export_download",
        "external_export_download_record_ref": readiness_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": readiness_body["export_download_descriptor_ref"],
        "external_export_download_state": readiness_body["external_export_download_state"],
        "delivery_mode": "same_origin_artifact_stream",
    }
    if decision_notes is not None:
        payload["decision_notes"] = decision_notes
    else:
        payload.pop("decision_notes", None)
    return payload


def _connector_dispatch_record_payload(
    *,
    request_id: str,
    session_id: str,
    approval_body: dict,
    selection_body: dict,
    review_body: dict,
    commit_body: dict,
    submit_body: dict,
    prepare_body: dict,
    dispatch_body: dict,
    readiness_body: dict,
    decision_notes: str | None = None,
) -> dict:
    payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": selection_body["pass_run_ids"][0],
        "analysis_run_id": readiness_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "package_kinds": commit_body["package_kinds"],
        "payload_refs": commit_body["payload_refs"],
        "payload_hashes": commit_body["payload_hashes"],
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "prepare_record_ref": prepare_body["prepare_record_ref"],
        "handoff_export_state": prepare_body["handoff_export_state"],
        "aps_handoff_record_ref": dispatch_body["aps_handoff_record_ref"],
        "aps_handoff_state": dispatch_body["aps_handoff_state"],
        "aps_handoff_target": dispatch_body["aps_handoff_target"],
        "aps_output_package_id": dispatch_body["aps_output_package_id"],
        "aps_output_package_kind": dispatch_body["aps_output_package_kind"],
        "aps_bundle_ref": dispatch_body["aps_bundle_ref"],
        "source_artifact_hash": readiness_body["source_artifact_hash"],
        "source_artifact_size_bytes": readiness_body["source_artifact_size_bytes"],
        "source_artifact_ref": readiness_body["source_artifact_ref"],
        "source_artifact_schema_id": readiness_body["source_artifact_schema_id"],
        "external_export_download_record_ref": readiness_body["external_export_download_record_ref"],
        "external_export_download_state": readiness_body["external_export_download_state"],
        "external_export_download_descriptor_ref": readiness_body["export_download_descriptor_ref"],
        "delivery_mode": "same_origin_artifact_stream",
        "operator_decision": "record_internal_connector_dispatch",
    }
    if decision_notes is not None:
        payload["decision_notes"] = decision_notes
    return payload


def _prepare_cohort_connector_dispatch_record(
    client: TestClient,
    tmp_path,
    monkeypatch,
    *,
    request_id: str,
) -> tuple[str, dict, dict, dict, dict, dict, dict, dict, dict, dict]:
    _patch_cohort_dataframe_persistence(monkeypatch, tmp_path)
    session_id, preview_body, approval_body = _approve_cohort_aps_handoff_plan(client, tmp_path)
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_id}-selection",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200
    selection_body = selection.json()
    start_body, status_body, review_body = _start_and_approve_quant_result_review(
        client,
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        request_id=request_id,
    )
    assert status_body["pass_type"] == "associated_cohort"
    pass_run_id = selection_body["pass_run_ids"][0]
    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_id}-package-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200
    package_preview_body = package_preview.json()
    assert package_preview_body["pass_type"] == "associated_cohort"
    package_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_id}-package-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_commit.status_code == 200
    commit_body = package_commit.json()
    package_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": f"{request_id}-package-submit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": commit_body["package_review_preview_hash"],
            "reconciliation_record_id": commit_body["reconciliation_record_id"],
            "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
            "payload_hashes": commit_body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_submit.status_code == 200
    submit_body = package_submit.json()
    prepare = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id=f"{request_id}-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
        ),
    )
    assert prepare.status_code == 200
    prepare_body = prepare.json()
    dispatch = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json=_aps_handoff_dispatch_payload(
            request_id=f"{request_id}-aps-dispatch",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
            prepare_body=prepare_body,
        ),
    )
    assert dispatch.status_code == 200, dispatch.json()
    dispatch_body = dispatch.json()
    readiness = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json=_external_export_download_prepare_payload(
            request_id=f"{request_id}-download-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
            prepare_body=prepare_body,
            dispatch_body=dispatch_body,
        ),
    )
    assert readiness.status_code == 200, readiness.json()
    readiness_body = readiness.json()
    assert readiness_body["pass_type"] == "associated_cohort"
    return (
        session_id,
        approval_body,
        selection_body,
        start_body,
        review_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_body,
        readiness_body,
    )


def _insert_orphan_aps_handoff_package(
    client: TestClient,
    tmp_path,
    *,
    session_id: str,
    reconciliation_record_id: str,
    suffix: str,
) -> None:
    payload_path = tmp_path / f"orphan-aps-handoff-{suffix}.json"
    payload_path.write_text(json.dumps({"test_scope": "orphan_aps_handoff_package"}), encoding="utf-8")
    db = client.layer3_session_factory()
    try:
        db.add(
            L3OutputPackage(
                session_id=session_id,
                reconciliation_record_id=reconciliation_record_id,
                package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
                status="package_complete",
                payload_ref=str(payload_path),
                payload_hash=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
                summary_json={"test_scope": "orphan_aps_handoff_package"},
            )
        )
        db.commit()
    finally:
        db.close()


def _prepare_aps_handoff_dispatch(
    client: TestClient,
    tmp_path,
    *,
    request_id: str,
) -> tuple[str, dict, dict, dict, dict, dict, dict, dict, dict, dict, dict]:
    session_id, preview_body, approval_body = _approve_aps_handoff_plan(client, tmp_path)
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"{request_id}-selection",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200
    selection_body = selection.json()
    start_body, _status_body, review_body = _start_and_approve_quant_result_review(
        client,
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        request_id=request_id,
    )
    pass_run_id = selection_body["pass_run_ids"][0]
    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": f"{request_id}-package-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200
    package_preview_body = package_preview.json()
    package_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": f"{request_id}-package-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_commit.status_code == 200
    commit_body = package_commit.json()
    package_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": f"{request_id}-package-submit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": commit_body["package_review_preview_hash"],
            "reconciliation_record_id": commit_body["reconciliation_record_id"],
            "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
            "payload_hashes": commit_body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_submit.status_code == 200
    submit_body = package_submit.json()
    prepare = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id=f"{request_id}-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
        ),
    )
    assert prepare.status_code == 200
    prepare_body = prepare.json()
    assert prepare_body["handoff_export_state"] == "handoff_export_prepared"
    return (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        package_preview_body,
        commit_body,
        submit_body,
        prepare_body,
        _aps_handoff_dispatch_payload(
            request_id=f"{request_id}-aps-dispatch",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
            prepare_body=prepare_body,
        ),
    )


def test_layer3_api_gate_c_preview_maps_typing_entry_error(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    def _raise_typing_entry_error(*_args, **_kwargs):
        raise Layer3TypingEntryError(
            f"Layer 3 session '{session_id}' already has typing records"
        )

    monkeypatch.setattr(
        layer3_workbench,
        "materialize_typing_entry",
        _raise_typing_entry_error,
    )

    response = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={
            "client_request_id": "api-gate-c-typing-error-map",
            "session_id": session_id,
            "commit_typing": True,
        },
    )

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="typing_already_materialized",
    )
    assert body["status"] == "blocked"


def test_layer3_api_plan_preview_maps_pass_entry_error(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    def _raise_pass_entry_error(*_args, **_kwargs):
        raise Layer3PassEntryError(
            f"Layer 3 session '{session_id}' has no admissible analysis sets for Gate C pass entry"
        )

    monkeypatch.setattr(layer3_workbench, "preview_pass_entry", _raise_pass_entry_error)

    response = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-preview-pass-error-map",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="no_admissible_plan",
    )
    assert body["status"] == "blocked"


def test_layer3_api_session_summary_fails_closed_on_manifest_mismatch(
    client: TestClient,
    tmp_path,
) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
        session = db.get(L3Session, session_id)
        assert session is not None
        session.selection_manifest_id = "mismatched-manifest-id"
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/v1/layer3/session/{session_id}")

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="selection_manifest_mismatch",
    )
    assert body["status"] == "conflict"
    assert body["blocked_fields"] == ["selection_manifest_id"]
    assert body["next_allowed_actions"] == ["inspect_session_manifest_state"]


def test_layer3_api_package_review_commit_maps_package_entry_error(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        _status_body,
        review_body,
    ) = _execute_and_approve_quant_result_review(
        client,
        tmp_path,
        request_id="api-package-entry-error-map",
    )
    pass_run_id = selection_body["pass_run_ids"][0]
    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-package-entry-error-map-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200

    def _raise_package_entry_error(*_args, **_kwargs):
        raise Layer3PackageEntryError("forced package-entry proof failure")

    monkeypatch.setattr(
        layer3_workbench,
        "materialize_workbench_package_commit",
        _raise_package_entry_error,
    )

    response = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": "api-package-entry-error-map-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview.json()[
                "package_review_preview_hash"
            ],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="package_construction_commit_blocked",
    )
    assert body["status"] == "conflict"
    assert body["next_allowed_actions"] == ["inspect_existing_package_state"]


def test_layer3_api_aps_handoff_dispatch_maps_owner_service_error(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    *_, dispatch_payload = _prepare_aps_handoff_dispatch(
        client,
        tmp_path,
        request_id="api-aps-owner-service-error-map",
    )

    def _raise_aps_handoff_error(*_args, **_kwargs):
        raise Layer3ApsHandoffError("forced APS handoff proof failure")

    monkeypatch.setattr(
        layer3_workbench,
        "materialize_aps_handoff",
        _raise_aps_handoff_error,
    )

    response = client.post("/api/v1/layer3/handoff/aps/dispatch", json=dispatch_payload)

    body = _assert_workbench_error_response(
        response,
        status_code=409,
        error_code="aps_handoff_dispatch_blocked",
    )
    assert body["status"] == "blocked"
    assert body["blocked_fields"] == ["aps_handoff_target"]


def test_layer3_api_full_first_slice_flow(client: TestClient) -> None:
    bootstrap = client.get("/api/v1/layer3/bootstrap")
    assert bootstrap.status_code == 200
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["features"]["handoff"] is False
    assert bootstrap_body["features"]["analysis_execution_start"] is True
    assert bootstrap_body["features"]["execution_result_status"] is True
    assert bootstrap_body["features"]["execution_result_review"] is True
    assert bootstrap_body["features"]["package_review_preview"] is True
    assert bootstrap_body["features"]["package_construction_commit"] is True
    assert bootstrap_body["features"]["package_review_submit"] is True
    assert bootstrap_body["features"]["handoff_export_prepare"] is True
    assert bootstrap_body["features"]["aps_handoff_dispatch"] is True
    assert bootstrap_body["features"]["external_export_download_prepare"] is True
    assert bootstrap_body["features"]["external_export_download_deliver"] is True
    assert bootstrap_body["features"]["internal_connector_dispatch_record"] is True
    assert bootstrap_body["features"]["package_supersession_preview"] is True
    assert bootstrap_body["features"]["replacement_package_set_authority"] is True
    assert bootstrap_body["features"]["package_supersession_commit"] is True
    assert bootstrap_body["features"]["replacement_package_artifact_manifest"] is True
    assert bootstrap_body["features"]["replacement_package_namespace"] is True
    assert bootstrap_body["features"]["plan_revision_recovery"] is True
    assert bootstrap_body["features"]["approved_plan_cancel"] is True
    assert bootstrap_body["features"]["package_review"] is False
    assert bootstrap_body["features"]["external_export"] is False
    assert bootstrap_body["features"]["dispatch"] is False
    assert bootstrap_body["features"]["analysis_execution"] is False
    assert bootstrap_body["execution_readiness"]["execution_admitted"] is False
    assert bootstrap_body["execution_readiness"]["analysis_execution_start_admitted"] is True
    assert bootstrap_body["execution_readiness"]["analysis_execution_start_endpoint"] == "/api/v1/layer3/execution/start"
    assert bootstrap_body["execution_readiness"]["execution_result_status_admitted"] is True
    assert bootstrap_body["execution_readiness"]["execution_result_status_endpoint"] == "/api/v1/layer3/execution/result/status"
    assert bootstrap_body["execution_readiness"]["execution_result_review_admitted"] is True
    assert bootstrap_body["execution_readiness"]["execution_result_review_endpoint"] == "/api/v1/layer3/execution/result/review"
    assert bootstrap_body["execution_readiness"]["package_review_preview_admitted"] is True
    assert bootstrap_body["execution_readiness"]["package_review_preview_endpoint"] == "/api/v1/layer3/package/review/preview"
    assert bootstrap_body["execution_readiness"]["package_construction_commit_admitted"] is True
    assert bootstrap_body["execution_readiness"]["package_construction_commit_endpoint"] == "/api/v1/layer3/package/review/commit"
    assert bootstrap_body["execution_readiness"]["package_review_submit_admitted"] is True
    assert bootstrap_body["execution_readiness"]["package_review_submit_endpoint"] == "/api/v1/layer3/package/review/submit"
    assert bootstrap_body["execution_readiness"]["handoff_export_prepare_admitted"] is True
    assert bootstrap_body["execution_readiness"]["handoff_export_prepare_endpoint"] == "/api/v1/layer3/handoff/export/prepare"
    assert bootstrap_body["execution_readiness"]["aps_handoff_dispatch_admitted"] is True
    assert bootstrap_body["execution_readiness"]["aps_handoff_dispatch_endpoint"] == "/api/v1/layer3/handoff/aps/dispatch"
    assert bootstrap_body["execution_readiness"]["external_export_download_prepare_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["external_export_download_prepare_endpoint"]
        == "/api/v1/layer3/handoff/export/download/prepare"
    )
    assert bootstrap_body["execution_readiness"]["external_export_download_deliver_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["external_export_download_deliver_endpoint"]
        == "/api/v1/layer3/handoff/export/download/deliver"
    )
    assert bootstrap_body["execution_readiness"]["internal_connector_dispatch_record_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["internal_connector_dispatch_record_endpoint"]
        == "/api/v1/layer3/handoff/connector/record"
    )
    assert bootstrap_body["execution_readiness"]["package_supersession_preview_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["package_supersession_preview_endpoint"]
        == "/api/v1/layer3/package/mutation/preview"
    )
    assert bootstrap_body["execution_readiness"]["replacement_package_set_authority_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["replacement_package_set_authority_endpoint"]
        == "/api/v1/layer3/package/replacement-set/record"
    )
    assert bootstrap_body["execution_readiness"]["package_supersession_commit_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["package_supersession_commit_endpoint"]
        == "/api/v1/layer3/package/supersession/commit"
    )
    assert bootstrap_body["execution_readiness"]["replacement_package_artifact_manifest_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["replacement_package_artifact_manifest_endpoint"]
        == "/api/v1/layer3/package/replacement-artifact/manifest/record"
    )
    assert bootstrap_body["execution_readiness"]["replacement_package_namespace_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["replacement_package_namespace_endpoint"]
        == "/api/v1/layer3/package/replacement-namespace/record"
    )
    assert bootstrap_body["execution_readiness"]["plan_revision_recovery_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["plan_revision_recovery_endpoint"]
        == "/api/v1/layer3/plan/revision/recover"
    )
    assert bootstrap_body["execution_readiness"]["approved_plan_cancel_admitted"] is True
    assert (
        bootstrap_body["execution_readiness"]["approved_plan_cancel_endpoint"]
        == "/api/v1/layer3/plan/approved/cancel"
    )
    assert bootstrap_body["execution_readiness"]["package_review_admitted"] is False
    assert bootstrap_body["execution_readiness"]["external_handoff_admitted"] is False
    assert bootstrap_body["execution_readiness"]["external_export_admitted"] is False
    assert bootstrap_body["execution_readiness"]["dispatch_admitted"] is False
    assert bootstrap_body["execution_readiness"]["readiness_endpoint"] == "/api/v1/layer3/readiness"

    readiness = client.get("/api/v1/layer3/readiness")
    assert readiness.status_code == 200
    readiness_body = readiness.json()
    _assert_common_response_envelope(readiness_body)
    assert readiness_body["schema_id"] == "layer3.execution_readiness_contract.v1"
    assert readiness_body["execution_admitted"] is False
    assert readiness_body["execution_enabled"] is False
    assert readiness_body["analysis_execution_start_admitted"] is True
    assert readiness_body["analysis_execution_start_endpoint"] == "/api/v1/layer3/execution/start"
    assert readiness_body["execution_result_status_admitted"] is True
    assert readiness_body["execution_result_status_endpoint"] == "/api/v1/layer3/execution/result/status"
    assert readiness_body["execution_result_review_admitted"] is True
    assert readiness_body["execution_result_review_endpoint"] == "/api/v1/layer3/execution/result/review"
    assert readiness_body["package_review_preview_admitted"] is True
    assert readiness_body["package_review_preview_endpoint"] == "/api/v1/layer3/package/review/preview"
    assert readiness_body["package_construction_commit_admitted"] is True
    assert readiness_body["package_construction_commit_endpoint"] == "/api/v1/layer3/package/review/commit"
    assert readiness_body["package_review_submit_admitted"] is True
    assert readiness_body["package_review_submit_endpoint"] == "/api/v1/layer3/package/review/submit"
    assert readiness_body["handoff_export_prepare_admitted"] is True
    assert readiness_body["handoff_export_prepare_endpoint"] == "/api/v1/layer3/handoff/export/prepare"
    assert readiness_body["aps_handoff_dispatch_admitted"] is True
    assert readiness_body["aps_handoff_dispatch_endpoint"] == "/api/v1/layer3/handoff/aps/dispatch"
    assert readiness_body["external_export_download_prepare_admitted"] is True
    assert readiness_body["external_export_download_prepare_endpoint"] == "/api/v1/layer3/handoff/export/download/prepare"
    assert readiness_body["external_export_download_deliver_admitted"] is True
    assert readiness_body["external_export_download_deliver_endpoint"] == "/api/v1/layer3/handoff/export/download/deliver"
    assert readiness_body["internal_connector_dispatch_record_admitted"] is True
    assert readiness_body["internal_connector_dispatch_record_endpoint"] == "/api/v1/layer3/handoff/connector/record"
    assert readiness_body["package_supersession_preview_admitted"] is True
    assert readiness_body["package_supersession_preview_endpoint"] == "/api/v1/layer3/package/mutation/preview"
    assert readiness_body["replacement_package_set_authority_admitted"] is True
    assert (
        readiness_body["replacement_package_set_authority_endpoint"]
        == "/api/v1/layer3/package/replacement-set/record"
    )
    assert readiness_body["package_supersession_commit_admitted"] is True
    assert (
        readiness_body["package_supersession_commit_endpoint"]
        == "/api/v1/layer3/package/supersession/commit"
    )
    assert readiness_body["replacement_package_artifact_manifest_admitted"] is True
    assert (
        readiness_body["replacement_package_artifact_manifest_endpoint"]
        == "/api/v1/layer3/package/replacement-artifact/manifest/record"
    )
    assert readiness_body["replacement_package_namespace_admitted"] is True
    assert (
        readiness_body["replacement_package_namespace_endpoint"]
        == "/api/v1/layer3/package/replacement-namespace/record"
    )
    assert readiness_body["plan_revision_recovery_admitted"] is True
    assert readiness_body["plan_revision_recovery_endpoint"] == "/api/v1/layer3/plan/revision/recover"
    assert readiness_body["approved_plan_cancel_admitted"] is True
    assert readiness_body["approved_plan_cancel_endpoint"] == "/api/v1/layer3/plan/approved/cancel"
    assert readiness_body["package_review_admitted"] is False
    assert readiness_body["external_handoff_admitted"] is False
    assert readiness_body["external_export_admitted"] is False
    assert readiness_body["dispatch_admitted"] is False
    assert readiness_body["readiness_state"] == "execution_readiness_blocked"
    assert bootstrap_body["state_action_contract"] == readiness_body["state_action_contract"]
    assert readiness_body["state_action_contract"]["schema_id"] == "layer3.state_action_contract.v1"
    assert "analysis_execution_start" in readiness_body["state_action_contract"]["action_ids"]
    assert "external_export_download_deliver" in readiness_body["state_action_contract"]["action_ids"]
    assert "internal_connector_dispatch_record" in readiness_body["state_action_contract"]["action_ids"]
    assert "package_supersession_preview" in readiness_body["state_action_contract"]["action_ids"]
    assert "record_replacement_package_set_authority" in readiness_body["state_action_contract"]["action_ids"]
    assert "package_supersession_commit" in readiness_body["state_action_contract"]["action_ids"]
    assert "replacement_package_namespace" in readiness_body["state_action_contract"]["action_ids"]
    assert "plan_revision_recover" in readiness_body["state_action_contract"]["action_ids"]
    assert "approved_plan_cancel" in readiness_body["state_action_contract"]["action_ids"]
    assert "inspect_approved_plan_cancel" in readiness_body["state_action_contract"]["action_ids"]
    admitted_capabilities = {
        item["capability"]: item for item in readiness_body["state_action_contract"]["admitted_capabilities"]
    }
    assert admitted_capabilities["single_aps_doc_qualitative_execution"]["admitted"] is True
    assert (
        admitted_capabilities["single_aps_doc_qualitative_execution"]["source_gate"]
        == "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE"
    )
    assert admitted_capabilities["internal_dispatch_record_only"]["admitted"] is True
    assert admitted_capabilities["internal_dispatch_record_only"]["source_gate"] == "121_CONNECTOR_DISPATCH_ENTRY_FREEZE"
    assert (
        admitted_capabilities["internal_dispatch_record_only"]["owner_service"]
        == "backend/app/services/layer3_connector_dispatch_entry.py"
    )
    assert admitted_capabilities["package_supersession_preview_only"]["admitted"] is True
    assert admitted_capabilities["package_supersession_preview_only"]["source_gate"] == "122_PACKAGE_MUTATION_FREEZE"
    assert (
        admitted_capabilities["package_supersession_preview_only"]["owner_service"]
        == "backend/app/services/layer3_package_mutation_entry.py"
    )
    assert admitted_capabilities["replacement_package_set_authority"]["admitted"] is True
    assert admitted_capabilities["replacement_package_set_authority"]["source_gate"] == "127_PACKAGE_REPLACEMENT_SET_FREEZE"
    assert (
        admitted_capabilities["replacement_package_set_authority"]["owner_service"]
        == "backend/app/services/layer3_replacement_package_set_authority.py"
    )
    assert admitted_capabilities["package_supersession_commit_entry"]["admitted"] is True
    assert admitted_capabilities["package_supersession_commit_entry"]["source_gate"] == "126_PACKAGE_COMMIT_FREEZE"
    assert (
        admitted_capabilities["package_supersession_commit_entry"]["owner_service"]
        == "backend/app/services/layer3_package_supersession_commit.py"
    )
    assert admitted_capabilities["replacement_package_namespace_rows"]["admitted"] is True
    assert (
        admitted_capabilities["replacement_package_namespace_rows"]["source_gate"]
        == "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE"
    )
    assert (
        admitted_capabilities["replacement_package_namespace_rows"]["owner_service"]
        == "backend/app/services/layer3_replacement_package_namespace.py"
    )
    assert admitted_capabilities["plan_revision_recovery_preview_refresh_entry"]["admitted"] is True
    assert (
        admitted_capabilities["plan_revision_recovery_preview_refresh_entry"]["owner_service"]
        == "backend/app/services/layer3_plan_revision_recovery.py"
    )
    assert admitted_capabilities["approved_plan_cancel_without_replacement"]["admitted"] is True
    assert (
        admitted_capabilities["approved_plan_cancel_without_replacement"]["owner_service"]
        == "backend/app/services/layer3_approved_plan_correction.py"
    )
    deferred_capabilities = {
        item["capability"]: item for item in readiness_body["state_action_contract"]["deferred_capabilities"]
    }
    assert "qualitative_execution" not in deferred_capabilities
    assert deferred_capabilities["broad_qualitative_execution"]["admitted"] is False
    assert deferred_capabilities["provider_public_url"]["admitted"] is False
    assert deferred_capabilities["connector_destination_dispatch"]["admitted"] is False
    assert deferred_capabilities["package_mutation_reconstruction"]["admitted"] is False
    assert deferred_capabilities["auth_security_hardening"]["reason"] == "deferred_by_operator_instruction"
    assert readiness_body["preview_hash_contract"]["schema_id"] == "layer3.plan_preview_hash.v1"
    assert readiness_body["material_preview_hash_contract"]["schema_id"] == "layer3.material_preview_hash.v1"
    assert readiness_body["material_preview_hash_contract"]["supplied_hash_required_current_slice"] is False
    assert readiness_body["idempotency_contract"]["client_request_id_supported"] is True
    assert readiness_body["idempotency_contract"]["client_request_id_required_current_slice"] is False
    assert readiness_body["idempotency_contract"]["client_request_id_required_for_gate_b_decision"] is True
    assert readiness_body["idempotency_contract"]["client_request_id_required_for_package_supersession_preview"] is True
    assert (
        readiness_body["idempotency_contract"]["client_request_id_required_for_replacement_package_set_authority"]
        is True
    )
    assert readiness_body["idempotency_contract"]["client_request_id_required_for_package_supersession_commit"] is True
    assert (
        readiness_body["idempotency_contract"]["client_request_id_required_for_replacement_package_namespace"]
        is True
    )
    assert readiness_body["idempotency_contract"]["client_request_id_required_for_plan_revision_recovery"] is True
    assert readiness_body["idempotency_contract"]["client_request_id_required_for_approved_plan_cancel"] is True
    assert "duplicate_package_supersession_preview" in readiness_body["idempotency_contract"]
    assert "duplicate_replacement_package_set_authority" in readiness_body["idempotency_contract"]
    assert "duplicate_package_supersession_commit" in readiness_body["idempotency_contract"]
    assert "duplicate_replacement_package_namespace" in readiness_body["idempotency_contract"]
    assert "duplicate_plan_revision_recovery" in readiness_body["idempotency_contract"]
    assert "duplicate_approved_plan_cancel" in readiness_body["idempotency_contract"]
    assert (
        readiness_body["concurrency_contract"]["replacement_package_namespace_uses_unique_request_basis_and_manifest_kind"]
        is True
    )
    assert readiness_body["concurrency_contract"]["plan_revision_recovery_uses_session_lock"] is True
    assert readiness_body["concurrency_contract"]["plan_revision_recovery_is_preview_refresh_only"] is True
    assert readiness_body["concurrency_contract"]["approved_plan_cancel_uses_session_and_plan_locks"] is True
    assert readiness_body["concurrency_contract"]["approved_plan_cancel_without_replacement_only"] is True
    assert "duplicate_gate_b_decision" in readiness_body["idempotency_contract"]
    assert readiness_body["idempotency_contract"]["gate_b_decision_idempotency_scope"] == "durable_claim_and_post_commit_retry"
    assert readiness_body["idempotency_contract"]["gate_b_decision_concurrent_duplicate_lock"] is True
    assert "preview-hash" in readiness_body["implemented_gates"]
    assert "analysis-execution-start" in readiness_body["implemented_gates"]
    assert "result-status" in readiness_body["implemented_gates"]
    assert "package-review-submit" in readiness_body["implemented_gates"]
    assert "handoff-export-prepare" in readiness_body["implemented_gates"]
    assert "aps-handoff-dispatch" in readiness_body["implemented_gates"]
    assert "external-export-download-prepare" in readiness_body["implemented_gates"]
    assert "external-export-download-deliver" in readiness_body["implemented_gates"]
    assert "revision-recovery" in readiness_body["implemented_gates"]
    assert "approved-plan-cancel" in readiness_body["implemented_gates"]
    assert "revision-recovery" not in readiness_body["deferred_gates"]
    assert readiness_body["plan_revision_recovery_admitted"] is True
    assert readiness_body["plan_revision_recovery_endpoint"] == "/api/v1/layer3/plan/revision/recover"
    assert readiness_body["approved_plan_cancel_admitted"] is True
    assert readiness_body["approved_plan_cancel_endpoint"] == "/api/v1/layer3/plan/approved/cancel"
    states = {item["state"] for item in readiness_body["state_model"]["states"]}
    assert {
        "plan_preview_ready",
        "plan_approved",
        "approved_plan_cancelled",
        "plan_revision_requested",
        "execution_pass_completed",
        "execution_result_status_available",
        "execution_result_status_missing_output",
        "execution_result_review_approved",
        "execution_result_review_changes_requested",
        "execution_result_review_rejected",
        "execution_result_review_blocked",
        "package_review_preview_unavailable",
        "package_review_preview_blocked",
        "package_review_preview_ready",
        "package_review_preview_inspected",
        "package_commit_unavailable",
        "package_commit_blocked",
        "package_commit_ready",
        "package_constructed",
        "package_review_submit_unavailable",
        "package_review_submit_blocked",
        "package_review_submit_ready",
        "package_review_approved",
        "package_review_changes_requested",
        "package_review_rejected",
        "package_review_blocked",
        "handoff_export_unavailable",
        "handoff_export_ready",
        "handoff_export_prepared",
        "handoff_export_held",
        "handoff_export_declined",
        "handoff_export_blocked",
        "aps_handoff_unavailable",
        "aps_handoff_ready",
        "aps_handoff_dispatched",
        "aps_handoff_blocked",
        "aps_handoff_conflict",
        "external_export_download_unavailable",
        "external_export_download_ready",
        "external_export_download_prepared",
        "external_export_download_blocked",
        "external_export_download_conflict",
        "external_export_download_delivery_unavailable",
        "external_export_download_delivery_ready",
        "external_export_download_delivered",
        "external_export_download_delivery_blocked",
        "external_export_download_delivery_conflict",
        "connector_dispatch_recorded",
        "execution_readiness_blocked",
    } <= states

    preflight, source, material = _prepare_material(client)
    for response_body in (bootstrap_body, preflight, source, material):
        _assert_common_response_envelope(response_body)
    assert preflight["status"] == "ok"
    assert source["authority_rail"]["current_gate"] == "gate_b"
    assert len(material["material_candidates"]) == 2
    assert len(material["material_preview_hash"]) == 64

    first, second = material["material_candidates"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "material_preview_hash": material["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": first["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": _gate_b_decision_basis(first),
                },
                {
                    "candidate_id": second["candidate_id"],
                    "decision": "denied",
                    "operator_reason": "Not in first-slice scope.",
                    "decision_basis": _gate_b_decision_basis(second),
                },
            ],
            "actor": "pytest",
        },
    )
    assert gate_b.status_code == 200
    gate_b_body = gate_b.json()
    _assert_common_response_envelope(gate_b_body)
    assert gate_b_body["material_preview_hash"] == material["material_preview_hash"]
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


def test_layer3_api_aps_derived_dataset_version_reaches_package_commit(client: TestClient, tmp_path) -> None:
    with client.layer3_session_factory() as db:
        dataset_version_id = _seed_aps_derived_dataset_version(db, tmp_path)
        db.commit()

    preflight = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-preflight-aps-dataset",
            "natural_language_intent": "Review APS-derived CSV table as quantitative source material.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        },
    )
    assert preflight.status_code == 200
    source = client.post(
        "/api/v1/layer3/source-preview",
        json={
            "client_request_id": "api-source-aps-dataset",
            "preflight_id": preflight.json()["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        },
    )
    assert source.status_code == 200
    material = client.post(
        "/api/v1/layer3/material-preview",
        json={
            "client_request_id": "api-material-aps-dataset",
            "preflight_id": preflight.json()["preflight_id"],
            "source_set_id": source.json()["source_set_id"],
            "source_candidate_ids": [source.json()["source_candidates"][0]["source_candidate_id"]],
            "dataset_version_ids": [dataset_version_id],
            "query_basis": {"terms": ["aps", "csv"]},
        },
    )
    assert material.status_code == 200
    candidate = material.json()["material_candidates"][0]
    assert candidate["source_identity"]["dataset_version_id"] == dataset_version_id
    assert candidate["source_provenance"]["aps_derived"] is True
    assert candidate["source_trace"]["trace_readiness"] == "traceable_aps_dataset_version"
    assert candidate["source_trace"]["source_family_label"] == "CSV table"
    assert candidate["source_trace"]["aps_trace_refs"]["diagnostics_ref"].endswith("/diagnostics.json")

    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-aps-dataset",
            "preflight_id": preflight.json()["preflight_id"],
            "source_set_id": source.json()["source_set_id"],
            "material_preview_id": material.json()["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": {
                        "source_ref": candidate["source_ref"],
                        "query_basis": candidate["query_basis"],
                        "provenance_ref": candidate["provenance_ref"],
                        "source_identity": candidate["source_identity"],
                        "source_provenance": candidate["source_provenance"],
                        "payload": candidate["payload"],
                        "load_summary": candidate["load_summary"],
                    },
                }
            ],
        },
    )
    assert gate_b.status_code == 200
    gate_c = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={
            "client_request_id": "api-gate-c-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "commit_typing": True,
        },
    )
    assert gate_c.status_code == 200
    assert gate_c.json()["typing_records"][0]["planning_shape_family"] == "tabular_numeric"

    plan = client.post(
        "/api/v1/layer3/plan/preview",
        json={"client_request_id": "api-plan-aps-dataset", "session_id": gate_b.json()["session_id"]},
    )
    assert plan.status_code == 200
    assert plan.json()["plan_preview"]["planned_passes"][0]["dataset_version_id"] == dataset_version_id

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "analysis_plan_id": approval.json()["analysis_plan_id"],
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
        },
    )
    assert selection.status_code == 200
    pass_run_id = selection.json()["pass_run_ids"][0]
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-execution-start-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "analysis_plan_id": approval.json()["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
        },
    )
    assert start.status_code == 200
    assert start.json()["dataset_version_id"] == dataset_version_id

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "client_request_id": "api-result-status-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "analysis_plan_id": approval.json()["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
            "analysis_run_id": start.json()["analysis_run_id"],
            "operator_view_mode": "status_only",
        },
    )
    assert status.status_code == 200
    assert status.json()["dataset_version_id"] == dataset_version_id
    assert status.json()["output_metadata_summary"]["dataset_version_id"] == dataset_version_id

    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "analysis_plan_id": approval.json()["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
            "analysis_run_id": start.json()["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "APS-derived dataset output preserves dataset identity for package proof.",
            "reviewed_output_items": [
                {
                    "item_ref": "aps-derived-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": gate_b.json()["session_id"],
                        "analysis_plan_id": approval.json()["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start.json()["analysis_run_id"],
                        "output_payload_ref": status.json()["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200
    assert review.json()["trace_summary"]["dataset_version_id"] == dataset_version_id

    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-package-preview-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "analysis_plan_id": approval.json()["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
            "analysis_run_id": start.json()["analysis_run_id"],
            "result_review_record_ref": review.json()["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200
    assert package_preview.json()["trace_summary"]["dataset_version_id"] == dataset_version_id

    package_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": "api-package-commit-aps-dataset",
            "session_id": gate_b.json()["session_id"],
            "analysis_plan_id": approval.json()["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": plan.json()["preview_id"],
            "preview_hash": plan.json()["preview_hash"],
            "analysis_run_id": start.json()["analysis_run_id"],
            "result_review_record_ref": review.json()["review_record_ref"],
            "package_review_preview_hash": package_preview.json()["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_commit.status_code == 200
    assert package_commit.json()["source_shape"] == "dataset_version"
    assert all(Path(payload_ref).exists() for payload_ref in package_commit.json()["payload_refs"])


def test_layer3_api_aps_content_document_material_preview_carries_trace(client: TestClient, tmp_path) -> None:
    run_id = "api-aps-doc-material-run-001"
    target_id = "api-aps-doc-material-target-001"
    content_id = "api-aps-doc-material-content-001"
    with client.layer3_session_factory() as db:
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=run_id,
            target_id=target_id,
            content_id=content_id,
        )
        db.commit()

    preflight = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-preflight-aps-doc-material",
            "natural_language_intent": "Review indexed APS document chunks as qualitative source material.",
            "manual_constraints": {"source_classes": ["aps_content_document"]},
        },
    )
    assert preflight.status_code == 200
    source = client.post(
        "/api/v1/layer3/source-preview",
        json={
            "client_request_id": "api-source-aps-doc-material",
            "preflight_id": preflight.json()["preflight_id"],
            "selected_source_classes": ["aps_content_document"],
        },
    )
    assert source.status_code == 200
    material = client.post(
        "/api/v1/layer3/material-preview",
        json={
            "client_request_id": "api-material-aps-doc-material",
            "preflight_id": preflight.json()["preflight_id"],
            "source_set_id": source.json()["source_set_id"],
            "source_candidate_ids": [source.json()["source_candidates"][0]["source_candidate_id"]],
            "aps_content_document_ids": [content_id],
            "query_basis": {"terms": ["aps", "document"]},
        },
    )

    assert material.status_code == 200
    candidate = material.json()["material_candidates"][0]
    assert candidate["source_identity"]["content_id"] == content_id
    assert candidate["source_provenance"]["aps_derived"] is True
    assert candidate["source_trace"]["trace_readiness"] == "traceable_aps_content_document"
    assert candidate["source_trace"]["source_family_label"] == "APS content document"
    assert candidate["source_trace"]["chunk_summary"]["loaded_chunk_count"] == 2
    assert candidate["source_trace"]["aps_trace_refs"]["run_id"] == run_id
    assert candidate["source_trace"]["aps_trace_refs"]["target_id"] == target_id


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


def test_layer3_api_gate_b_material_preview_hash_mismatch_fails_closed(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]

    mismatch = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-stale-material-preview",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "material_preview_hash": "stale-material-preview-hash",
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
    )

    assert mismatch.status_code == 409
    body = mismatch.json()
    _assert_common_response_envelope(body)
    assert body["error_code"] == "material_preview_mismatch"
    assert body["blocked_fields"] == ["material_preview_hash", "candidate_decisions"]
    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_layer3_api_gate_b_material_preview_hash_binds_source_authority(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]
    decision_basis = _gate_b_decision_basis(first)
    decision_basis["source_identity"] = {**decision_basis["source_identity"], "dataset_version_id": "tampered-dv"}

    mismatch = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-authority-tamper",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "material_preview_hash": material["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": first["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": decision_basis,
                },
            ],
            "actor": "pytest",
        },
    )

    assert mismatch.status_code == 409
    body = mismatch.json()
    _assert_common_response_envelope(body)
    assert body["error_code"] == "material_preview_mismatch"
    assert body["blocked_fields"] == ["material_preview_hash", "candidate_decisions"]
    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_layer3_api_gate_b_duplicate_candidate_decisions_fail_closed(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]
    decision = {
        "candidate_id": first["candidate_id"],
        "decision": "approved",
        "operator_reason": "",
        "decision_basis": _gate_b_decision_basis(first),
    }

    duplicate = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-duplicate-candidate",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "material_preview_hash": material["material_preview_hash"],
            "candidate_decisions": [decision, decision],
            "actor": "pytest",
        },
    )

    assert duplicate.status_code == 400
    body = duplicate.json()
    _assert_common_response_envelope(body)
    assert body["error_code"] == "duplicate_material_candidate_decision"
    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_layer3_api_gate_b_rejects_extra_fields_before_session_mutation(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]

    rejected = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-strict-extra",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "material_preview_hash": material["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": first["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": _gate_b_decision_basis(first),
                    "analysis_run_id": "run-should-not-be-accepted",
                }
            ],
            "actor": "pytest",
            "execute": True,
        },
    )

    assert rejected.status_code == 422
    detail = rejected.json()["detail"]
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "execute"]
        for item in detail
    )
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "candidate_decisions", 0, "analysis_run_id"]
        for item in detail
    )
    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_layer3_api_gate_b_requires_client_request_id_before_session_mutation(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]
    payload = {
        "preflight_id": preflight["preflight_id"],
        "source_set_id": source["source_set_id"],
        "material_preview_id": material["material_preview_id"],
        "material_preview_hash": material["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": first["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": _gate_b_decision_basis(first),
            }
        ],
        "actor": "pytest",
    }

    missing = client.post("/api/v1/layer3/gate-b/decision", json=payload)
    assert missing.status_code == 422
    assert any(item.get("loc") == ["body", "client_request_id"] for item in missing.json()["detail"])

    blank = client.post("/api/v1/layer3/gate-b/decision", json={**payload, "client_request_id": "   "})
    assert blank.status_code == 400
    blank_body = blank.json()
    _assert_common_response_envelope(blank_body)
    assert blank_body["error_code"] == "client_request_id_required"

    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_layer3_api_gate_b_duplicate_client_request_id_is_idempotent(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first, second = material["material_candidates"]
    payload = {
        "client_request_id": "api-gate-b-idempotent",
        "preflight_id": preflight["preflight_id"],
        "source_set_id": source["source_set_id"],
        "material_preview_id": material["material_preview_id"],
        "material_preview_hash": material["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": first["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": _gate_b_decision_basis(first),
            },
            {
                "candidate_id": second["candidate_id"],
                "decision": "denied",
                "operator_reason": "Not in first-slice scope.",
                "decision_basis": _gate_b_decision_basis(second),
            },
        ],
        "actor": "pytest",
    }

    committed = client.post("/api/v1/layer3/gate-b/decision", json=payload)
    assert committed.status_code == 200
    committed_body = committed.json()
    _assert_common_response_envelope(committed_body)
    assert committed_body["status"] == "ok"

    duplicate = client.post("/api/v1/layer3/gate-b/decision", json=payload)
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    _assert_common_response_envelope(duplicate_body)
    assert duplicate_body["status"] == "already_committed"
    assert duplicate_body["session_id"] == committed_body["session_id"]
    assert duplicate_body["selection_manifest_id"] == committed_body["selection_manifest_id"]
    assert duplicate_body["material_preview_hash"] == material["material_preview_hash"]
    assert duplicate_body["gate_b_decision_manifest_id"] == committed_body["gate_b_decision_manifest_id"]

    reordered_payload = json.loads(json.dumps(payload))
    reordered_payload["candidate_decisions"] = list(reversed(reordered_payload["candidate_decisions"]))
    reordered = client.post("/api/v1/layer3/gate-b/decision", json=reordered_payload)
    assert reordered.status_code == 200
    reordered_body = reordered.json()
    assert reordered_body["status"] == "already_committed"
    assert reordered_body["session_id"] == committed_body["session_id"]
    assert reordered_body["gate_b_decision_manifest_id"] == committed_body["gate_b_decision_manifest_id"]

    conflicting_context_payload = json.loads(json.dumps(payload))
    conflicting_context_payload["source_set_id"] = "different-source-set"
    context_conflict = client.post("/api/v1/layer3/gate-b/decision", json=conflicting_context_payload)
    assert context_conflict.status_code == 409
    assert context_conflict.json()["error_code"] == "idempotency_conflict"

    conflicting_payload = json.loads(json.dumps(payload))
    conflicting_payload["candidate_decisions"][1]["decision"] = "flagged"
    conflicting_payload["candidate_decisions"][1]["operator_reason"] = "Changed after retry."
    conflict = client.post("/api/v1/layer3/gate-b/decision", json=conflicting_payload)
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "idempotency_conflict"

    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 1
        claim = db.query(L3GateBIdempotencyKey).one()
        assert claim.client_request_id == "api-gate-b-idempotent"
        assert claim.status == "committed"
        assert claim.session_id == committed_body["session_id"]
        assert claim.selection_manifest_id == committed_body["selection_manifest_id"]
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


def test_layer3_api_gate_c_rejects_extra_fields_before_typing_mutation(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-before-strict-gate-c",
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
                }
            ],
            "actor": "pytest",
        },
    ).json()

    rejected = client.post(
        "/api/v1/layer3/gate-c/preview",
        json={
            "client_request_id": "api-gate-c-strict-extra",
            "session_id": gate_b["session_id"],
            "commit_typing": True,
            "analysis_run_id": "run-should-not-be-accepted",
            "execute": True,
        },
    )

    assert rejected.status_code == 422
    detail = rejected.json()["detail"]
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "analysis_run_id"]
        for item in detail
    )
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "execute"]
        for item in detail
    )
    with client.layer3_session_factory() as db:
        assert db.query(L3Session).count() == 1
        assert db.query(L3TypingRecord).count() == 0
        assert db.query(L3AnalysisUnit).count() == 0
        assert db.query(L3AnalysisGroup).count() == 0
        assert db.query(L3AnalysisSet).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0


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


def test_layer3_api_plan_preview_is_blocked_before_gate_c_commit(client: TestClient) -> None:
    preflight, source, material = _prepare_material(client)
    first = material["material_candidates"][0]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "api-gate-b-plan-blocked",
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

    blocked = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-before-gate-c",
            "session_id": gate_b["session_id"],
        },
    )

    assert blocked.status_code == 409
    body = blocked.json()
    _assert_common_response_envelope(body)
    assert body["error_code"] == "gate_c_not_committed"
    assert body["status"] == "blocked"

    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-before-gate-c",
            "session_id": gate_b["session_id"],
            "preview_id": "missing-preview",
            "preview_hash": "missing-hash",
            "operator_decision": "request_revision",
        },
    )
    assert revision.status_code == 409
    assert revision.json()["error_code"] == "gate_c_not_committed"


def test_layer3_api_plan_preview_success_is_read_only_for_seeded_admissible_session(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-preview-success",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )

    assert preview.status_code == 200
    body = preview.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.plan_preview_result.v1"
    assert body["preview_only"] is True
    assert body["preview_hash"]
    assert body["preview_identity"] == {
        "schema_id": "layer3.plan_preview_identity.v1",
        "preview_id": body["preview_id"],
        "preview_hash": body["preview_hash"],
        "preview_hash_schema_id": "layer3.plan_preview_hash.v1",
        "authority_source": "server_owner_service_preview",
        "stale_preview_writes_blocked": True,
        "mismatch_error_code": "preview_mismatch",
    }
    assert body["next_state"] == "plan_preview_ready"
    assert body["authority_rail"]["current_gate"] == "plan"
    assert body["authority_rail"]["execution_enabled"] is False
    assert body["authority_rail"]["package_review_enabled"] is False
    assert body["authority_rail"]["downstream_unavailable"] == ["execution", "results", "package"]
    assert body["plan_preview"]["would_create_analysis_plan"] is False
    assert body["plan_preview"]["would_create_pass_runs"] is False
    assert body["plan_preview"]["would_execute_passes"] is False
    assert body["plan_preview"]["preview_hash_contract"]["schema_id"] == "layer3.plan_preview_hash.v1"
    assert body["plan_preview"]["preview_hash_contract"]["mismatch_error_code"] == "preview_mismatch"
    assert body["plan_preview"]["owner_service_basis"]["preview_hash_schema_id"] == "layer3.plan_preview_hash.v1"
    assert len(body["plan_preview"]["admitted_sets"]) == 1
    assert len(body["plan_preview"]["planned_passes"]) == 1

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-success",
            "session_id": session_id,
            "preview_id": body["preview_id"],
            "preview_hash": body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 200
    approval_body = approval.json()
    _assert_common_response_envelope(approval_body)
    assert approval_body["schema_id"] == "layer3.plan_approval_result.v1"
    assert approval_body["next_state"] == "plan_approved"
    assert approval_body["approval_only"] is True
    assert approval_body["execution_started"] is False
    assert approval_body["plan_status"] == "approved"
    assert approval_body["approved_by_operator"] is True
    assert approval_body["authority_rail"]["persistence_mode"] == "approved_plan"
    assert approval_body["authority_rail"]["execution_enabled"] is False
    assert approval_body["authority_rail"]["package_review_enabled"] is False
    assert approval_body["approved_plan"]["would_create_pass_runs"] is False
    assert approval_body["approved_plan"]["would_execute_passes"] is False
    assert approval_body["approved_plan"]["approved_sets"][0]["readiness"] == "approved"
    assert approval_body["approved_plan"]["planned_passes"][0]["approval_only"] is True

    duplicate = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-duplicate",
            "session_id": session_id,
            "preview_id": body["preview_id"],
            "preview_hash": body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "plan_already_approved"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["plan_approval"]["approved"] is True
    assert summary_body["plan_approval"]["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert summary_body["plan_approval"]["pass_run_count"] == 0
    sublayer = summary_body["sublayer_visualization"]
    assert sublayer["schema_id"] == "layer3.sublayer_visualization_state.v1"
    assert sublayer["authority_source"] == "read_only_persisted_layer3_rows"
    assert sublayer["no_side_effects"] is True
    assert len(sublayer["material_objects"]) == 1
    assert sublayer["material_objects"][0]["source_shape"] == "dataset_version"
    assert sublayer["material_objects"][0]["source_identity"]["dataset_version_id"] == "dv-pass-001"
    assert len(sublayer["typing_records"]) == 1
    assert sublayer["typing_records"][0]["chosen_modality"] == "quantitative"
    assert sublayer["typing_records"][0]["owner_service_source_shape"] == "dataset_version"
    assert len(sublayer["analysis_units"]) == 1
    assert len(sublayer["analysis_sets"]) == 1
    assert sublayer["analysis_sets"][0]["analysis_modality"] == "quantitative"
    assert sublayer["analysis_sets"][0]["unit_count"] == 1
    assert sublayer["latest_plan"]["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert sublayer["latest_plan"]["approved"] is True
    assert sublayer["latest_plan"]["approval_only"] is True
    assert len(sublayer["latest_plan"]["approved_sets"]) == 1
    assert len(sublayer["latest_plan"]["planned_passes"]) == 1
    assert sublayer["pass_runs"] == []

    db = client.layer3_session_factory()
    try:
        stored_plan = db.query(L3AnalysisPlan).one()
        assert stored_plan.status == "approved"
        assert stored_plan.approved_by_operator is True
        assert stored_plan.plan_json["approval_only"] is True
        assert stored_plan.plan_json["execution_started"] is False
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    rejected = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-preview-strict-extra",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
            "execute": True,
        },
    )

    assert rejected.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "execute"]
        for item in rejected.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_preflight_rejects_extra_fields_before_service_execution(
    client: TestClient,
    monkeypatch,
) -> None:
    def _unexpected_preflight(_payload):
        raise AssertionError("preflight service should not run when request validation rejects extra fields")

    monkeypatch.setattr(layer3_workbench, "preflight", _unexpected_preflight)

    rejected = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-preflight-strict-extra",
            "natural_language_intent": "Select admitted source classes only.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
            "local_directory": "C:/not-admitted",
        },
    )

    assert rejected.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "local_directory"]
        for item in rejected.json()["detail"]
    )


def test_layer3_api_source_preview_rejects_extra_fields_before_service_execution(client: TestClient) -> None:
    preflight = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-source-preview-strict-preflight",
            "natural_language_intent": "Select admitted source classes only.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        },
    ).json()

    rejected = client.post(
        "/api/v1/layer3/source-preview",
        json={
            "client_request_id": "api-source-preview-strict-extra",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
            "local_directory": "C:/not-admitted",
        },
    )

    assert rejected.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "local_directory"]
        for item in rejected.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_material_preview_rejects_extra_fields_before_service_execution(client: TestClient) -> None:
    preflight = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-material-preview-strict-preflight",
            "natural_language_intent": "Select admitted material only.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        },
    ).json()
    source = client.post(
        "/api/v1/layer3/source-preview",
        json={
            "client_request_id": "api-material-preview-strict-source",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        },
    ).json()

    rejected = client.post(
        "/api/v1/layer3/material-preview",
        json={
            "client_request_id": "api-material-preview-strict-extra",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
            "query_basis": {"terms": ["admitted"], "filters": {"dataset_version_ids": []}},
            "local_directory": "C:/not-admitted",
        },
    )

    assert rejected.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "local_directory"]
        for item in rejected.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3Session).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_plan_revision_rejects_current_preview_without_execution(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-revision-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()

    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-reject",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "reject_current_preview",
            "operator_note": "Reject this preview before approval.",
        },
    )
    assert revision.status_code == 200
    revision_body = revision.json()
    _assert_common_response_envelope(revision_body)
    assert revision_body["schema_id"] == "layer3.plan_revision_result.v1"
    assert revision_body["next_state"] == "plan_rejected"
    assert revision_body["revision_control_only"] is True
    assert revision_body["execution_started"] is False
    assert revision_body["operator_decision"] == "reject_current_preview"
    assert revision_body["operator_note_recorded"] is True
    assert revision_body["authority_rail"]["persistence_mode"] == "plan_revision_control"
    assert revision_body["authority_rail"]["execution_enabled"] is False
    assert revision_body["authority_rail"]["package_review_enabled"] is False
    assert revision_body["downstream_unavailable"] == ["execution", "results", "package"]

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["plan_revision"]["available"] is False
    assert summary_body["plan_revision"]["state"] == "plan_rejected"
    assert summary_body["plan_revision"]["operator_decision"] == "reject_current_preview"
    assert summary_body["plan_revision"]["operator_note_recorded"] is True
    assert summary_body["plan_revision"]["approval_available"] is False
    assert summary_body["plan_revision"]["execution_started"] is False
    assert summary_body["plan_preview"]["available"] is False
    assert summary_body["plan_preview"]["blocked_reason"] == "plan_rejected"
    assert summary_body["plan_approval"]["available"] is False
    assert summary_body["plan_approval"]["blocked_reason"] == "plan_rejected"

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-revision-approval-blocked",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 409
    assert approval.json()["error_code"] == "plan_rejected"

    duplicate_revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-duplicate",
            "session_id": session_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "request_revision",
        },
    )
    assert duplicate_revision.status_code == 409
    assert duplicate_revision.json()["error_code"] == "plan_rejected"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_plan_revision_request_revision_prechecks(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-revision-prechecks-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    ).json()

    unsupported = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-unsupported",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": "approve_anyway",
        },
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["error_code"] == "unsupported_revision_decision"

    forbidden = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-forbidden",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": "request_revision",
            "execute": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "execution_not_admitted"
    assert forbidden.json()["blocked_fields"] == ["execute"]

    unknown_extra = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-unknown-extra",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": "request_revision",
            "destination_connector": "not-admitted",
        },
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        session = db.get(L3Session, session_id)
        assert session is not None
        assert "plan_revision_control" not in (session.summary_json or {})
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()

    mismatch = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-mismatch",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": "stale-preview-hash",
            "operator_decision": "request_revision",
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error_code"] == "preview_mismatch"

    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-request",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": "request_revision",
        },
    )
    assert revision.status_code == 200
    revision_body = revision.json()
    assert revision_body["next_state"] == "plan_revision_requested"
    assert revision_body["revision_control_only"] is True
    assert revision_body["execution_started"] is False
    assert revision_body["operator_note_recorded"] is False

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_approved_plan_cancel_without_replacement_updates_existing_plan_only(
    client: TestClient,
    tmp_path,
) -> None:
    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)
    payload = {
        "schema_id": "layer3.approved_plan_cancel_request.v1",
        "client_request_id": "api-approved-plan-cancel-success",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "source_preview_id": preview_body["preview_id"],
        "source_preview_hash": preview_body["preview_hash"],
        "operator_decision": "cancel_approved_plan_without_replacement",
        "operator_note": "Cancel before execution selection.",
    }

    cancel = client.post("/api/v1/layer3/plan/approved/cancel", json=payload)
    assert cancel.status_code == 200
    cancel_body = cancel.json()
    _assert_common_response_envelope(cancel_body)
    assert cancel_body["schema_id"] == "layer3.approved_plan_cancel_result.v1"
    assert cancel_body["next_state"] == "approved_plan_cancelled"
    assert cancel_body["approved_plan_cancelled"] is True
    assert cancel_body["approval_available"] is False
    assert cancel_body["execution_started"] is False
    assert cancel_body["replacement_plan_created"] is False
    assert cancel_body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert cancel_body["previous_plan_status"] == "approved"
    assert cancel_body["plan_status"] == "cancelled"
    assert cancel_body["source_preview_id"] == preview_body["preview_id"]
    assert cancel_body["source_preview_hash"] == preview_body["preview_hash"]
    assert cancel_body["downstream_unavailable"] == ["execution", "results", "package", "handoff"]
    assert cancel_body["authority_rail"]["persistence_mode"] == "approved_plan_cancel"
    assert cancel_body["authority_rail"]["execution_enabled"] is False
    assert cancel_body["authority_rail"]["package_review_enabled"] is False
    assert cancel_body["approved_plan_cancel"]["operator_note_recorded"] is True

    duplicate = client.post("/api/v1/layer3/plan/approved/cancel", json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["approved_plan_cancel"]["cancellation_id"] == cancel_body["approved_plan_cancel"]["cancellation_id"]

    execution_selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-approved-plan-cancel-selection",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert execution_selection.status_code == 409
    assert execution_selection.json()["error_code"] == "no_approved_plan"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["plan_preview"]["available"] is False
    assert summary_body["plan_preview"]["blocked_reason"] == "approved_plan_cancelled"
    assert summary_body["plan_approval"]["approved"] is False
    assert summary_body["plan_approval"]["blocked_reason"] == "approved_plan_cancelled"
    assert summary_body["approved_plan_cancel"]["state"] == "approved_plan_cancelled"
    assert summary_body["approved_plan_cancel"]["cancelled"] is True
    assert summary_body["execution_selection"]["available"] is False
    assert summary_body["execution_selection"]["blocked_reason"] == "no_approved_plan"

    db = client.layer3_session_factory()
    try:
        session = db.get(L3Session, session_id)
        assert session is not None
        assert session.summary_json["approved_plan_cancel"]["cancellation_id"] == cancel_body["approved_plan_cancel"]["cancellation_id"]
        plans = db.query(L3AnalysisPlan).all()
        assert len(plans) == 1
        stored_plan = plans[0]
        assert stored_plan.analysis_plan_id == approval_body["analysis_plan_id"]
        assert stored_plan.status == "cancelled"
        assert stored_plan.approved_by_operator is True
        assert stored_plan.plan_json["approved_plan_cancel"]["cancellation_id"] == cancel_body["approved_plan_cancel"]["cancellation_id"]
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(ConnectorRun).count() == 0
    finally:
        db.close()


def test_layer3_api_approved_plan_cancel_prechecks_fail_closed(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        no_plan_session_id = "api-approved-plan-cancel-no-plan-session"
        db.add(
            L3Session(
                session_id=no_plan_session_id,
                selection_manifest_id="api-approved-plan-cancel-no-plan-manifest",
                summary_json={},
            )
        )
        db.commit()
    finally:
        db.close()

    no_plan = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-no-plan",
            "session_id": no_plan_session_id,
            "analysis_plan_id": "missing-plan",
            "source_preview_id": "missing-preview",
            "source_preview_hash": "missing-hash",
            "operator_decision": "cancel_approved_plan_without_replacement",
        },
    )
    assert no_plan.status_code == 409
    assert no_plan.json()["error_code"] == "no_approved_plan"

    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)
    forbidden = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-forbidden",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "source_preview_id": preview_body["preview_id"],
            "source_preview_hash": preview_body["preview_hash"],
            "operator_decision": "cancel_approved_plan_without_replacement",
            "replacement_plan": {"mode": "not-admitted"},
            "approved_plan_supersession": True,
            "provider_public_url": "https://example.invalid/object",
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "approved_plan_correction_not_admitted"
    assert forbidden.json()["blocked_fields"] == [
        "approved_plan_supersession",
        "provider_public_url",
        "replacement_plan",
    ]

    unsupported = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-unsupported",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "source_preview_id": preview_body["preview_id"],
            "source_preview_hash": preview_body["preview_hash"],
            "operator_decision": "supersede_approved_plan",
        },
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["error_code"] == "unsupported_approved_plan_cancel_decision"

    stale_plan = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-stale-plan",
            "session_id": session_id,
            "analysis_plan_id": "stale-plan",
            "source_preview_id": preview_body["preview_id"],
            "source_preview_hash": preview_body["preview_hash"],
            "operator_decision": "cancel_approved_plan_without_replacement",
        },
    )
    assert stale_plan.status_code == 409
    assert stale_plan.json()["error_code"] == "approved_plan_mismatch"

    stale_preview = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-stale-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "source_preview_id": preview_body["preview_id"],
            "source_preview_hash": "stale-preview-hash",
            "operator_decision": "cancel_approved_plan_without_replacement",
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    db = client.layer3_session_factory()
    try:
        stored_plan = db.query(L3AnalysisPlan).one()
        assert stored_plan.status == "approved"
        db.add(
            L3AnalysisPlan(
                analysis_plan_id="manual-second-approved-plan",
                session_id=session_id,
                analysis_set_ids_json=list(stored_plan.analysis_set_ids_json),
                status="approved",
                approved_by_operator=True,
                approved_at=stored_plan.approved_at,
                plan_json=dict(stored_plan.plan_json),
            )
        )
        db.commit()
    finally:
        db.close()

    multiple = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-multiple",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "source_preview_id": preview_body["preview_id"],
            "source_preview_hash": preview_body["preview_hash"],
            "operator_decision": "cancel_approved_plan_without_replacement",
        },
    )
    assert multiple.status_code == 409
    assert multiple.json()["error_code"] == "multiple_approved_plans"

    db = client.layer3_session_factory()
    try:
        db.query(L3AnalysisPlan).filter(L3AnalysisPlan.analysis_plan_id == "manual-second-approved-plan").delete()
        analysis_set = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).first()
        assert analysis_set is not None
        db.add(
            L3PassRun(
                pass_run_id="manual-cancel-pass-run",
                session_id=session_id,
                analysis_plan_id=approval_body["analysis_plan_id"],
                analysis_set_id=analysis_set.analysis_set_id,
                pass_type="single_item",
                engine_family="wrapped_quantitative_analysis",
                status="selected_not_started",
                input_payload_ref="memory://manual-cancel-pass-run/input",
                summary_json={"execution_started": False},
            )
        )
        db.commit()
    finally:
        db.close()

    pass_runs = client.post(
        "/api/v1/layer3/plan/approved/cancel",
        json={
            "client_request_id": "api-approved-plan-cancel-pass-runs",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "source_preview_id": preview_body["preview_id"],
            "source_preview_hash": preview_body["preview_hash"],
            "operator_decision": "cancel_approved_plan_without_replacement",
        },
    )
    assert pass_runs.status_code == 409
    assert pass_runs.json()["error_code"] == "pass_runs_already_exist"

    db = client.layer3_session_factory()
    try:
        session = db.get(L3Session, session_id)
        assert session is not None
        assert "approved_plan_cancel" not in (session.summary_json or {})
        plans = db.query(L3AnalysisPlan).order_by(L3AnalysisPlan.analysis_plan_id.asc()).all()
        assert {plan.status for plan in plans} == {"approved"}
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(ConnectorRun).count() == 0
    finally:
        db.close()


@pytest.mark.parametrize(
    ("operator_decision", "expected_state"),
    [
        ("reject_current_preview", "plan_rejected"),
        ("request_revision", "plan_revision_requested"),
    ],
)
def test_layer3_api_plan_revision_recovery_restores_preview_refresh_only(
    client: TestClient,
    tmp_path,
    operator_decision: str,
    expected_state: str,
) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"api-plan-recovery-{operator_decision}-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    ).json()
    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": f"api-plan-recovery-{operator_decision}-revision",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": operator_decision,
        },
    )
    assert revision.status_code == 200

    recovery_payload = {
        "schema_id": "layer3.plan_revision_recovery_request.v1",
        "client_request_id": f"api-plan-recovery-{operator_decision}",
        "session_id": session_id,
        "source_revision_state": expected_state,
        "source_preview_id": preview["preview_id"],
        "source_preview_hash": preview["preview_hash"],
        "operator_decision": "recover_for_preview_refresh",
        "operator_note": "Return to server preview refresh only.",
    }
    recovery = client.post("/api/v1/layer3/plan/revision/recover", json=recovery_payload)
    assert recovery.status_code == 200
    recovery_body = recovery.json()
    _assert_common_response_envelope(recovery_body)
    assert recovery_body["schema_id"] == "layer3.plan_revision_recovery_result.v1"
    assert recovery_body["source_revision_state"] == expected_state
    assert recovery_body["next_state"] == "gate_c_typing_committed"
    assert recovery_body["preview_refresh_required"] is True
    assert recovery_body["approval_available"] is False
    assert recovery_body["execution_started"] is False
    assert recovery_body["recovery_lifecycle_only"] is True
    assert recovery_body["operator_decision"] == "recover_for_preview_refresh"
    assert recovery_body["operator_note_recorded"] is True
    assert recovery_body["downstream_unavailable"] == ["execution", "results", "package", "handoff"]
    assert recovery_body["authority_rail"]["persistence_mode"] == "plan_revision_recovery"
    assert recovery_body["authority_rail"]["execution_enabled"] is False
    assert recovery_body["authority_rail"]["package_review_enabled"] is False
    assert recovery_body["plan_revision_recovery"]["source_preview_id"] == preview["preview_id"]

    duplicate = client.post("/api/v1/layer3/plan/revision/recover", json=recovery_payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["plan_revision_recovery"]["recovery_id"] == recovery_body["plan_revision_recovery"]["recovery_id"]

    stale_approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": f"api-plan-recovery-{operator_decision}-stale-approval",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert stale_approval.status_code == 409
    assert stale_approval.json()["error_code"] == "preview_mismatch"

    refreshed_preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"api-plan-recovery-{operator_decision}-refreshed-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    )
    assert refreshed_preview.status_code == 200
    refreshed_preview_body = refreshed_preview.json()
    assert refreshed_preview_body["preview_id"] != preview["preview_id"]
    assert refreshed_preview_body["preview_hash"] == preview["preview_hash"]
    assert (
        refreshed_preview_body["plan_preview"]["revision_recovery"]["recovery_id"]
        == recovery_body["plan_revision_recovery"]["recovery_id"]
    )

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["plan_revision"]["recovered"] is True
    assert summary_body["plan_revision_recovery"]["state"] == "plan_preview_refresh_required"
    assert summary_body["plan_revision_recovery"]["available"] is False
    assert summary_body["plan_approval"]["available"] is False
    assert summary_body["plan_approval"]["blocked_reason"] == "plan_preview_refresh_required"

    db = client.layer3_session_factory()
    try:
        session = db.get(L3Session, session_id)
        assert session is not None
        assert session.summary_json["plan_revision_control"]["state"] == expected_state
        assert session.summary_json["plan_revision_control"]["recovery_state"] == "plan_preview_refresh_required"
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
        assert db.query(L3OutputPackage).count() == 0
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(ConnectorRun).count() == 0
    finally:
        db.close()


def test_layer3_api_plan_revision_recovery_prechecks_fail_closed(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    no_revision = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-no-revision",
            "session_id": session_id,
            "source_revision_state": "plan_rejected",
            "source_preview_id": "missing-preview",
            "source_preview_hash": "missing-hash",
            "operator_decision": "recover_for_preview_refresh",
        },
    )
    assert no_revision.status_code == 409
    assert no_revision.json()["error_code"] == "plan_revision_recovery_not_available"

    forbidden = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-forbidden",
            "session_id": session_id,
            "source_revision_state": "plan_rejected",
            "source_preview_id": "missing-preview",
            "source_preview_hash": "missing-hash",
            "operator_decision": "recover_for_preview_refresh",
            "execute": True,
            "provider_public_url": "https://example.invalid/object",
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "execution_not_admitted"
    assert forbidden.json()["blocked_fields"] == ["execute", "provider_public_url"]

    unsupported = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-unsupported",
            "session_id": session_id,
            "source_revision_state": "plan_rejected",
            "source_preview_id": "missing-preview",
            "source_preview_hash": "missing-hash",
            "operator_decision": "recover_and_approve",
        },
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["error_code"] == "unsupported_revision_recovery_decision"

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-recovery-prechecks-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    ).json()
    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-recovery-prechecks-revision",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": "request_revision",
        },
    )
    assert revision.status_code == 200

    state_mismatch = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-state-mismatch",
            "session_id": session_id,
            "source_revision_state": "plan_rejected",
            "source_preview_id": preview["preview_id"],
            "source_preview_hash": preview["preview_hash"],
            "operator_decision": "recover_for_preview_refresh",
        },
    )
    assert state_mismatch.status_code == 409
    assert state_mismatch.json()["error_code"] == "plan_revision_state_mismatch"

    preview_mismatch = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-preview-mismatch",
            "session_id": session_id,
            "source_revision_state": "plan_revision_requested",
            "source_preview_id": preview["preview_id"],
            "source_preview_hash": "stale-preview-hash",
            "operator_decision": "recover_for_preview_refresh",
        },
    )
    assert preview_mismatch.status_code == 409
    assert preview_mismatch.json()["error_code"] == "preview_mismatch"

    db = client.layer3_session_factory()
    try:
        analysis_set = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).first()
        assert analysis_set is not None
        db.add(
            L3AnalysisPlan(
                analysis_plan_id="manual-recovery-approved-plan",
                session_id=session_id,
                analysis_set_ids_json=[analysis_set.analysis_set_id],
                status="approved",
                approved_by_operator=True,
                plan_json={"approval_only": True, "execution_started": False},
            )
        )
        db.commit()
    finally:
        db.close()

    approved_blocked = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-approved-plan",
            "session_id": session_id,
            "source_revision_state": "plan_rejected",
            "source_preview_id": preview["preview_id"],
            "source_preview_hash": preview["preview_hash"],
            "operator_decision": "recover_for_preview_refresh",
        },
    )
    assert approved_blocked.status_code == 409
    assert approved_blocked.json()["error_code"] == "plan_already_approved"

    db = client.layer3_session_factory()
    try:
        analysis_set = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).first()
        assert analysis_set is not None
        db.add(
            L3PassRun(
                pass_run_id="manual-recovery-pass-run",
                session_id=session_id,
                analysis_plan_id="manual-recovery-approved-plan",
                analysis_set_id=analysis_set.analysis_set_id,
                pass_type="single_item",
                engine_family="wrapped_quantitative_analysis",
                status="selected_not_started",
                input_payload_ref="memory://manual-recovery-pass-run/input",
                summary_json={"execution_started": False},
            )
        )
        db.commit()
    finally:
        db.close()

    pass_runs_blocked = client.post(
        "/api/v1/layer3/plan/revision/recover",
        json={
            "client_request_id": "api-plan-recovery-pass-runs",
            "session_id": session_id,
            "source_revision_state": "plan_rejected",
            "source_preview_id": preview["preview_id"],
            "source_preview_hash": preview["preview_hash"],
            "operator_decision": "recover_for_preview_refresh",
        },
    )
    assert pass_runs_blocked.status_code == 409
    assert pass_runs_blocked.json()["error_code"] == "pass_runs_already_exist"

    db = client.layer3_session_factory()
    try:
        session = db.get(L3Session, session_id)
        assert session is not None
        assert "plan_revision_recovery" not in (session.summary_json or {})
    finally:
        db.close()


def test_layer3_api_plan_approval_reports_existing_unapproved_plan(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
        db.add(
            L3AnalysisPlan(
                analysis_plan_id="manual-unapproved-plan",
                session_id=session_id,
                analysis_set_ids_json=["manual-analysis-set"],
                status="formed",
                approved_by_operator=False,
                approved_at=None,
                plan_json={
                    "planned_passes_json": [{"analysis_set_id": "manual-analysis-set"}],
                    "excluded_sets_json": [],
                    "execution_started": False,
                },
            )
        )
        db.commit()
    finally:
        db.close()

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    plan_approval = summary.json()["plan_approval"]
    assert plan_approval["available"] is False
    assert plan_approval["approved"] is False
    assert plan_approval["blocked_reason"] == "plan_already_materialized"
    assert plan_approval["approved_by_operator"] is False
    assert plan_approval["approved_at"] is None

    approval = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-existing-unapproved",
            "session_id": session_id,
            "preview_id": "stale-preview-id",
            "preview_hash": "stale-preview-hash",
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert approval.status_code == 409
    assert approval.json()["error_code"] == "plan_already_materialized"

    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": "api-plan-revision-existing-unapproved",
            "session_id": session_id,
            "preview_id": "stale-preview-id",
            "preview_hash": "stale-preview-hash",
            "operator_decision": "request_revision",
        },
    )
    assert revision.status_code == 409
    assert revision.json()["error_code"] == "plan_already_materialized"


def test_layer3_api_plan_approval_rejects_confirmation_and_preview_mismatch(client: TestClient, tmp_path) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-approval-precheck",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    ).json()

    unconfirmed = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-unconfirmed",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_confirmation": False,
            "approval_scope": "owner_service_default",
        },
    )
    assert unconfirmed.status_code == 400
    assert unconfirmed.json()["error_code"] == "operator_confirmation_required"

    mismatch = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-mismatch",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": "stale-preview-hash",
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error_code"] == "preview_mismatch"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_plan_approval_rejects_extra_fields_before_service_mutation(
    client: TestClient,
    tmp_path,
) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": "api-plan-approval-strict-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    ).json()

    rejected = client.post(
        "/api/v1/layer3/plan/approve",
        json={
            "client_request_id": "api-plan-approval-strict-extra",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_confirmation": True,
            "approval_scope": "owner_service_default",
            "execute": True,
        },
    )

    assert rejected.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "execute"]
        for item in rejected.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_execution_selection_creates_only_pass_run_shells(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)

    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_reason": "Select the approved plan without starting analysis.",
        },
    )
    assert selection.status_code == 200
    selection_body = selection.json()
    _assert_common_response_envelope(selection_body)
    assert selection_body["schema_id"] == "layer3.execution_selection.v1"
    assert selection_body["status"] == "selected_not_started"
    assert selection_body["next_state"] == "execution_selected_not_started"
    assert selection_body["execution_started"] is False
    assert selection_body["analysis_run_ids"] == []
    assert selection_body["downstream_unavailable"] == ["results", "package", "handoff"]
    assert len(selection_body["pass_run_ids"]) == 1

    duplicate = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["status"] == "already_selected"
    assert duplicate_body["pass_run_ids"] == selection_body["pass_run_ids"]

    conflicting_duplicate = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": "different-preview-hash",
        },
    )
    assert conflicting_duplicate.status_code == 409
    assert conflicting_duplicate.json()["error_code"] == "idempotency_conflict"

    different_request = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-second-request",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert different_request.status_code == 409
    assert different_request.json()["error_code"] == "execution_selection_already_exists"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["current_gate"] == "execution"
    assert summary_body["execution_selection"]["selected"] is True
    assert summary_body["execution_selection"]["state"] == "execution_selected_not_started"
    assert summary_body["execution_selection"]["pass_run_ids"] == selection_body["pass_run_ids"]
    assert summary_body["execution_selection"]["execution_started"] is False

    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 1
        assert db.query(AnalysisRun).count() == 0
        stored_pass = db.query(L3PassRun).one()
        assert stored_pass.status == "selected_not_started"
        assert stored_pass.started_at is None
        assert stored_pass.completed_at is None
        assert stored_pass.output_payload_ref is None
        assert stored_pass.summary_json["execution_started"] is False
        assert stored_pass.summary_json["analysis_run_id"] is None
        assert stored_pass.summary_json["client_request_id"] == "api-execution-selection-success"
        assert db.query(L3AnalysisPlan).count() == 1
    finally:
        db.close()


def test_layer3_api_execution_selection_prechecks_fail_closed(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)

    missing_request_id = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert missing_request_id.status_code == 400
    assert missing_request_id.json()["error_code"] == "client_request_id_required"

    forbidden = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-forbidden",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "execution": {"start": True},
            "run_analysis": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "analysis_execution_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"execution", "run_analysis"}

    unknown_extra = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-unknown-extra",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "destination_connector": "not-admitted",
        },
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    stale_preview = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-stale-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": "stale-preview-hash",
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_analysis_execution_start_runs_selected_pass_once(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-analysis-execution-selection-success",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "execution_mode": "synchronous_single_pass",
            "operator_reason": "Start the selected quantitative pass only.",
        },
    )
    assert start.status_code == 200
    start_body = start.json()
    _assert_common_response_envelope(start_body)
    assert start_body["schema_id"] == "layer3.analysis_execution_start.v1"
    assert start_body["status"] in {"completed", "completed_with_warnings"}
    assert start_body["pass_run_id"] == pass_run_id
    assert start_body["execution_started"] is True
    assert start_body["analysis_run_id"]
    assert start_body["pass_run_status"] == start_body["status"]
    assert start_body["output_payload_ref"]
    assert start_body["downstream_unavailable"] == ["results", "package", "handoff"]

    duplicate = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["status"] == "already_completed"
    assert duplicate_body["analysis_run_id"] == start_body["analysis_run_id"]

    conflicting_retry = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-conflict",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert conflicting_retry.status_code == 409
    assert conflicting_retry.json()["error_code"] == "analysis_execution_already_started"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["current_gate"] == "execution"
    assert summary_body["execution_selection"]["execution_started"] is True
    assert summary_body["execution_selection"]["analysis_run_ids"] == [start_body["analysis_run_id"]]
    assert summary_body["execution_selection"]["pass_run_statuses"][pass_run_id] == start_body["status"]
    assert summary_body["downstream_unavailable"] == ["results", "package", "handoff"]
    sublayer = summary_body["sublayer_visualization"]
    assert len(sublayer["material_objects"]) == 1
    assert len(sublayer["typing_records"]) == 1
    assert len(sublayer["analysis_sets"]) == 1
    assert sublayer["latest_plan"]["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert len(sublayer["pass_runs"]) == 1
    sublayer_pass_run = sublayer["pass_runs"][0]
    assert sublayer_pass_run["pass_run_id"] == pass_run_id
    assert (
        sublayer_pass_run["analysis_set_id"]
        == sublayer["latest_plan"]["approved_sets"][0]["analysis_set_id"]
    )
    assert sublayer_pass_run["engine_family"] == "wrapped_quantitative_analysis"
    assert sublayer_pass_run["status"] == start_body["status"]
    assert sublayer_pass_run["input_payload_available"] is True
    assert sublayer_pass_run["output_payload_available"] is True
    assert sublayer_pass_run["analysis_run_id"] == start_body["analysis_run_id"]
    assert sublayer_pass_run["selected_method_name"] == "decomposition"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 1
        assert db.query(L3PassRun).count() == 1
        assert db.query(AnalysisRun).count() == 1
        assert db.query(AnalysisArtifact).count() >= 1
        stored_pass = db.query(L3PassRun).one()
        assert stored_pass.status in {"completed", "completed_with_warnings"}
        assert stored_pass.started_at is not None
        assert stored_pass.completed_at is not None
        assert stored_pass.summary_json["execution_started"] is True
        assert stored_pass.summary_json["analysis_run_id"] == start_body["analysis_run_id"]
        assert stored_pass.summary_json["analysis_execution_start"]["client_request_id"] == "api-analysis-execution-start-success"
        assert Path(stored_pass.output_payload_ref).exists()
    finally:
        db.close()


def test_layer3_api_execution_result_status_reads_terminal_pass_without_writes(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-result-status-selection-success",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-result-status-start-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200
    start_body = start.json()

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).one()
        pass_summary_before = dict(stored_pass.summary_json)
        output_payload_ref_before = stored_pass.output_payload_ref
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
        }
    finally:
        db.close()

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "client_request_id": "api-result-status-read",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_view_mode": "status_only",
        },
    )
    assert status.status_code == 200
    status_body = status.json()
    _assert_common_response_envelope(status_body)
    assert status_body["schema_id"] == "layer3.execution_result_status.v1"
    assert status_body["status"] == "available"
    assert status_body["session_id"] == session_id
    assert status_body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert status_body["pass_run_id"] == pass_run_id
    assert status_body["preview_identity"]["preview_id"] == preview_body["preview_id"]
    assert status_body["preview_identity"]["preview_hash"] == preview_body["preview_hash"]
    assert status_body["execution_started"] is True
    assert status_body["analysis_run_id"] == start_body["analysis_run_id"]
    assert status_body["analysis_run_status"] in {"completed", "completed_with_warnings"}
    assert status_body["pass_run_status"] == start_body["pass_run_status"]
    assert status_body["output_payload_ref"] == output_payload_ref_before
    assert status_body["output_metadata_summary"]["present"] is True
    assert status_body["output_metadata_summary"]["readable"] is True
    assert status_body["output_metadata_summary"]["analysis_run_id"] == start_body["analysis_run_id"]
    assert status_body["output_metadata_summary"]["artifact_count"] >= 1
    assert status_body["output_metadata_error"] is None
    assert status_body["result_status_available"] is True
    assert status_body["result_review_enabled"] is False
    assert status_body["package_review_enabled"] is False
    assert status_body["handoff_enabled"] is False
    assert status_body["downstream_unavailable"] == ["result_review", "package", "handoff"]
    assert status_body["next_state"] == "execution_result_status_available"
    assert status_body["operator_view_mode"] == "status_only"

    duplicate = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["analysis_run_id"] == start_body["analysis_run_id"]

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).one()
        assert stored_pass.summary_json == pass_summary_before
        assert stored_pass.output_payload_ref == output_payload_ref_before
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
        } == counts_before
    finally:
        db.close()


def test_layer3_api_selected_cohort_execution_start_and_status_are_bounded(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _patch_cohort_dataframe_persistence(monkeypatch, tmp_path)
    session_id, preview_body, approval_body, selection_body = _select_quant_cohort_pass(
        client,
        tmp_path,
        request_id="api-cohort-result-status-selection",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-cohort-result-status-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200
    start_body = start.json()
    assert start_body["status"] in {"completed", "completed_with_warnings"}
    assert start_body["analysis_run_id"]
    assert start_body["selected_method_name"] == "descriptive_summary"

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "client_request_id": "api-cohort-result-status-read",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_view_mode": "status_only",
        },
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["status"] == "available"
    assert status_body["result_status_available"] is True
    assert status_body["result_review_enabled"] is False
    assert status_body["package_review_enabled"] is False
    assert status_body["handoff_enabled"] is False
    assert status_body["selected_method_name"] == "descriptive_summary"
    assert status_body["output_metadata_summary"]["source_gate"] == "78_COHORT_FREEZE"
    assert status_body["output_metadata_summary"]["source_dataset_version_ids"] == [
        "dv-cohort-001",
        "dv-cohort-002",
    ]

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()

    review_payload = {
        "client_request_id": "api-cohort-result-review-approve",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "operator_decision": "approved",
        "review_notes": "Cohort descriptive summary output is traceable for this bounded review tranche.",
        "reviewed_output_items": [
            {
                "item_ref": "cohort-output",
                "item_type": "finding",
                "trace": {
                    "session_id": session_id,
                    "analysis_plan_id": approval_body["analysis_plan_id"],
                    "pass_run_id": pass_run_id,
                    "analysis_run_id": start_body["analysis_run_id"],
                    "output_payload_ref": status_body["output_payload_ref"],
                },
            }
        ],
    }
    review = client.post("/api/v1/layer3/execution/result/review", json=review_payload)
    assert review.status_code == 200
    review_body = review.json()
    _assert_common_response_envelope(review_body)
    assert review_body["schema_id"] == "layer3.execution_result_review.v1"
    assert review_body["status"] == "recorded"
    assert review_body["result_status_available"] is True
    assert review_body["result_review_enabled"] is True
    assert review_body["review_state"] == "execution_result_review_approved"
    assert review_body["operator_decision"] == "approved"
    assert review_body["unresolved_trace_count"] == 0
    assert review_body["trace_summary"]["output_payload_ref"] == status_body["output_payload_ref"]
    assert review_body["trace_summary"]["selected_method_name"] == "descriptive_summary"
    assert review_body["trace_summary"]["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert review_body["trace_summary"]["source_gate"] == "78_COHORT_FREEZE"
    assert review_body["trace_summary"]["source_dataset_version_ids"] == ["dv-cohort-001", "dv-cohort-002"]
    assert review_body["trace_summary"]["cohort_shape"] == "aligned_wide_table"
    assert review_body["trace_summary"]["requested_method_name"] == "descriptive_summary"
    assert review_body["trace_summary"]["requested_method_source"] == "analysis_set.formation_basis_json.requested_method_name"
    assert review_body["trace_summary"]["reviewed_item_count"] == 1
    assert review_body["pass_type"] == "associated_cohort"
    assert review_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert review_body["selected_method_name"] == "descriptive_summary"
    assert review_body["source_gate"] == "78_COHORT_FREEZE"
    assert review_body["source_dataset_version_ids"] == ["dv-cohort-001", "dv-cohort-002"]
    assert review_body["cohort_shape"] == "aligned_wide_table"
    assert review_body["package_review_enabled"] is False
    assert review_body["handoff_enabled"] is False
    assert review_body["downstream_unavailable"] == ["package", "handoff", "package_review"]

    duplicate = client.post("/api/v1/layer3/execution/result/review", json=review_payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "already_recorded"
    assert duplicate.json()["review_record_ref"] == review_body["review_record_ref"]

    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-cohort-package-preview-read-only",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200
    package_preview_body = package_preview.json()
    _assert_common_response_envelope(package_preview_body)
    assert package_preview_body["schema_id"] == "layer3.package_review_preview.v1"
    assert package_preview_body["status"] == "available"
    assert package_preview_body["package_review_preview_enabled"] is True
    assert package_preview_body["package_commit_enabled"] is True
    assert package_preview_body["package_review_enabled"] is False
    assert package_preview_body["pass_type"] == "associated_cohort"
    assert package_preview_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert package_preview_body["selected_method_name"] == "descriptive_summary"
    assert package_preview_body["source_gate"] == "78_COHORT_FREEZE"
    assert package_preview_body["source_dataset_version_ids"] == ["dv-cohort-001", "dv-cohort-002"]
    assert package_preview_body["cohort_shape"] == "aligned_wide_table"
    assert package_preview_body["reviewed_output_item_summary"] == {
        "reviewed_item_count": 1,
        "unresolved_trace_count": 0,
    }
    assert [item["package_kind"] for item in package_preview_body["candidate_package_kinds"]] == [
        "canonical_internal",
        "user_facing",
        "review_facing",
    ]
    assert all(item["preview_only"] is True for item in package_preview_body["candidate_package_kinds"])
    assert all(item["package_commit_enabled"] is True for item in package_preview_body["candidate_package_kinds"])
    assert package_preview_body["package_owner_compatibility"]["status"] == (
        "associated_cohort_construction_preconditions_satisfied"
    )
    assert package_preview_body["package_owner_compatibility"]["construction_compatible_with_current_workbench_state"] is True
    assert package_preview_body["downstream_unavailable"] == [
        "package_review_submit",
        "handoff",
        "export",
        "aps_handoff",
        "external_export_download",
        "connector",
    ]

    package_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": "api-cohort-package-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_commit.status_code == 200
    package_commit_body = package_commit.json()
    _assert_common_response_envelope(package_commit_body)
    assert package_commit_body["schema_id"] == "layer3.package_construction_commit.v1"
    assert package_commit_body["status"] == "committed"
    assert package_commit_body["reconciliation_record_id"]
    assert package_commit_body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert len(package_commit_body["output_packages"]) == 3
    assert len(package_commit_body["payload_refs"]) == 3
    assert len(package_commit_body["payload_hashes"]) == 3
    assert package_commit_body["package_review_submit_enabled"] is True
    assert package_commit_body["handoff_enabled"] is False
    assert package_commit_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert package_commit_body["method"] == "descriptive_summary"
    assert package_commit_body["source_gate"] == "78_COHORT_FREEZE"
    assert package_commit_body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert package_commit_body["source_shape"] == "aligned_wide_table"
    assert package_commit_body["source_dataset_version_ids"] == ["dv-cohort-001", "dv-cohort-002"]
    assert package_commit_body["reviewed_output_item_summary"] == {
        "reviewed_item_count": 1,
        "unresolved_trace_count": 0,
    }
    assert package_commit_body["downstream_unavailable"] == [
        "handoff",
        "export",
        "aps_handoff",
        "external_export_download",
        "connector",
    ]
    assert all(Path(payload_ref).exists() for payload_ref in package_commit_body["payload_refs"])

    duplicate_package_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": "api-cohort-package-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert duplicate_package_commit.status_code == 200
    assert duplicate_package_commit.json()["status"] == "already_committed"
    assert duplicate_package_commit.json()["reconciliation_record_id"] == package_commit_body["reconciliation_record_id"]
    assert duplicate_package_commit.json()["payload_hashes"] == package_commit_body["payload_hashes"]

    package_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": "api-cohort-package-submit-approved",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "reconciliation_record_id": package_commit_body["reconciliation_record_id"],
            "output_package_ids": [
                package["output_package_id"] for package in package_commit_body["output_packages"]
            ],
            "payload_hashes": package_commit_body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_submit.status_code == 200
    package_submit_body = package_submit.json()
    _assert_common_response_envelope(package_submit_body)
    assert package_submit_body["schema_id"] == "layer3.cohort_package_review_submit.v1"
    assert package_submit_body["status"] == "submitted"
    assert package_submit_body["package_review_state"] == "package_review_approved"
    assert package_submit_body["operator_decision"] == "approved"
    assert package_submit_body["pass_type"] == "associated_cohort"
    assert package_submit_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert package_submit_body["method"] == "descriptive_summary"
    assert package_submit_body["source_gate"] == "78_COHORT_FREEZE"
    assert package_submit_body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert package_submit_body["source_shape"] == "aligned_wide_table"
    assert package_submit_body["source_dataset_version_ids"] == ["dv-cohort-001", "dv-cohort-002"]
    assert package_submit_body["package_review_submit_enabled"] is False
    assert package_submit_body["handoff_enabled"] is False
    assert package_submit_body["export_enabled"] is False
    assert package_submit_body["downstream_unavailable"] == [
        "handoff",
        "export",
        "aps_handoff",
        "external_export_download",
        "connector",
    ]

    duplicate_package_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": "api-cohort-package-submit-approved",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "reconciliation_record_id": package_commit_body["reconciliation_record_id"],
            "output_package_ids": [
                package["output_package_id"] for package in package_commit_body["output_packages"]
            ],
            "payload_hashes": package_commit_body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert duplicate_package_submit.status_code == 200
    assert duplicate_package_submit.json()["status"] == "already_submitted"
    assert duplicate_package_submit.json()["submit_record_ref"] == package_submit_body["submit_record_ref"]

    handoff_after_cohort_submit = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id="api-cohort-package-submit-handoff-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=package_commit_body,
            submit_body=package_submit_body,
        ),
    )
    assert handoff_after_cohort_submit.status_code == 200, handoff_after_cohort_submit.json()
    handoff_body = handoff_after_cohort_submit.json()
    _assert_common_response_envelope(handoff_body)
    assert handoff_body["schema_id"] == "layer3.cohort_handoff_export_prepare.v1"
    assert handoff_body["status"] == "prepared"
    assert handoff_body["handoff_export_state"] == "handoff_export_prepared"
    assert handoff_body["pass_type"] == "associated_cohort"
    assert handoff_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert handoff_body["method"] == "descriptive_summary"
    assert handoff_body["source_gate"] == "78_COHORT_FREEZE"
    assert handoff_body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert handoff_body["source_shape"] == "aligned_wide_table"
    assert handoff_body["source_dataset_version_ids"] == ["dv-cohort-001", "dv-cohort-002"]
    assert handoff_body["package_review_submit_schema_id"] == "layer3.cohort_package_review_submit.v1"
    assert handoff_body["external_handoff_enabled"] is False
    assert handoff_body["external_export_enabled"] is False
    assert handoff_body["dispatch_enabled"] is False
    assert handoff_body["downstream_unavailable"] == ["aps_handoff", "external_export", "downstream_dispatch"]
    assert handoff_body["handoff_export_envelope"]["package_review_submit_schema_id"] == (
        "layer3.cohort_package_review_submit.v1"
    )

    cohort_aps_dispatch = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json=_aps_handoff_dispatch_payload(
            request_id="api-cohort-package-submit-aps-dispatch-blocked",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=package_commit_body,
            submit_body=package_submit_body,
            prepare_body=handoff_body,
        ),
    )
    assert cohort_aps_dispatch.status_code == 409
    assert cohort_aps_dispatch.json()["error_code"] == "aps_handoff_dispatch_blocked"
    assert "contains no aps_content_document provenance admitted for APS handoff" in cohort_aps_dispatch.json()[
        "message"
    ]

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["current_gate"] == "package"
    assert summary_body["package_review_preview"]["package_commit_enabled"] is True
    assert summary_body["package_construction"]["state"] == "package_constructed"
    assert summary_body["package_construction"]["package_commit_enabled"] is False
    assert summary_body["package_construction"]["package_review_submit_enabled"] is False
    assert summary_body["package_review_submit"]["state"] == "package_review_approved"
    assert summary_body["package_review_submit"]["operator_decision"] == "approved"
    assert summary_body["package_review_submit"]["submit_record_ref"] == package_submit_body["submit_record_ref"]
    assert summary_body["package_review_submit"]["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert summary_body["package_review_submit"]["package_review_submit_enabled"] is False
    assert summary_body["handoff_export_prepare"]["state"] == "handoff_export_prepared"
    assert summary_body["handoff_export_prepare"]["blocked_reason"] is None
    assert summary_body["handoff_export_prepare"]["pass_type"] == "associated_cohort"
    assert summary_body["handoff_export_prepare"]["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert summary_body["handoff_export_prepare"]["method"] == "descriptive_summary"
    assert summary_body["handoff_export_prepare"]["source_gate"] == "78_COHORT_FREEZE"
    assert summary_body["handoff_export_prepare"]["package_construction_source_gate"] == (
        "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    )
    assert summary_body["handoff_export_prepare"]["source_shape"] == "aligned_wide_table"
    assert summary_body["handoff_export_prepare"]["source_dataset_version_ids"] == [
        "dv-cohort-001",
        "dv-cohort-002",
    ]
    assert summary_body["handoff_export_prepare"]["package_review_submit_schema_id"] == (
        "layer3.cohort_package_review_submit.v1"
    )
    assert summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_blocked"
    assert "contains no aps_content_document provenance admitted for APS handoff" in summary_body[
        "aps_handoff_dispatch"
    ]["blocked_reason"]
    assert summary_body["downstream_unavailable"] == [
        "aps_handoff",
        "external_export",
        "download",
        "connector_dispatch",
        "non_aps_dispatch",
    ]

    conflict = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-cohort-result-review-conflict",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "rejected",
            "review_notes": "Conflicting cohort review should fail closed.",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "execution_result_review_already_recorded"

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).one()
        assert stored_pass.pass_type == "associated_cohort"
        assert stored_pass.summary_json["requested_method_name"] == "descriptive_summary"
        assert stored_pass.summary_json["source_dataset_version_ids_json"] == ["dv-cohort-001", "dv-cohort-002"]
        assert stored_pass.summary_json["execution_result_review"]["review_record_ref"] == review_body["review_record_ref"]
        assert stored_pass.summary_json["execution_result_review"]["operator_decision"] == "approved"
        assert stored_pass.summary_json["execution_result_review"]["pass_type"] == "associated_cohort"
        assert stored_pass.summary_json["execution_result_review"]["source_gate"] == "78_COHORT_FREEZE"
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert reconciliation.reconciliation_record_id == package_commit_body["reconciliation_record_id"]
        assert reconciliation.summary_json["source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
        assert reconciliation.summary_json["workbench_package_commit"]["package_review_submit_enabled"] is False
        assert reconciliation.summary_json["package_review_submit"]["submit_record_ref"] == package_submit_body["submit_record_ref"]
        assert reconciliation.summary_json["package_review_submit"]["operator_decision"] == "approved"
        assert reconciliation.summary_json["package_review_submit"]["package_review_state"] == "package_review_approved"
        assert reconciliation.summary_json["package_review_submit"]["package_construction_source_gate"] == (
            "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
        )
        assert reconciliation.summary_json["package_review_submit"]["downstream_unavailable"] == [
            "handoff",
            "export",
            "aps_handoff",
            "external_export_download",
            "connector",
        ]
        handoff_state = reconciliation.summary_json["handoff_export_prepare"]
        assert handoff_state["handoff_export_state"] == "handoff_export_prepared"
        assert handoff_state["pass_type"] == "associated_cohort"
        assert handoff_state["pass_scope"] == "quantitative_associated_cohort_dataset_version"
        assert handoff_state["method"] == "descriptive_summary"
        assert handoff_state["source_gate"] == "78_COHORT_FREEZE"
        assert handoff_state["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
        assert handoff_state["package_review_submit_schema_id"] == "layer3.cohort_package_review_submit.v1"
        assert "aps_handoff_dispatch" not in reconciliation.summary_json
        assert reconciliation.summary_json["workbench_package_commit"]["downstream_unavailable"] == [
            "handoff",
            "export",
            "aps_handoff",
            "external_export_download",
            "connector",
        ]
        packages = db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        assert len(packages) == 3
        assert {package.package_kind for package in packages} == {
            "canonical_internal",
            "user_facing",
            "review_facing",
        }
        assert {package.summary_json["source_gate"] for package in packages} == {
            "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
        }
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == {
            **counts_before,
            "packages": counts_before["packages"] + 3,
            "reconciliations": counts_before["reconciliations"] + 1,
        }
    finally:
        db.close()


def test_layer3_api_selected_cohort_result_review_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _patch_cohort_dataframe_persistence(monkeypatch, tmp_path)
    session_id, preview_body, approval_body, selection_body = _select_quant_cohort_pass(
        client,
        tmp_path,
        request_id="api-cohort-result-review-precheck-selection",
    )
    pass_run_id = selection_body["pass_run_ids"][0]
    base_payload = {
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "operator_decision": "approved",
    }

    not_started = client.post(
        "/api/v1/layer3/execution/result/review",
        json={**base_payload, "client_request_id": "api-cohort-result-review-before-start"},
    )
    assert not_started.status_code == 409
    assert not_started.json()["error_code"] == "analysis_execution_start_required"

    forbidden = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            **base_payload,
            "client_request_id": "api-cohort-result-review-forbidden",
            "package_review": True,
            "handoff": True,
            "rewrite_output": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "execution_result_review_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"handoff", "package_review", "rewrite_output"}

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-cohort-result-review-precheck-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200
    start_body = start.json()

    stale_preview = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            **base_payload,
            "client_request_id": "api-cohort-result-review-stale-preview",
            "analysis_run_id": start_body["analysis_run_id"],
            "preview_hash": "stale-preview-hash",
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    unresolved_trace = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            **base_payload,
            "client_request_id": "api-cohort-result-review-unresolved-trace",
            "analysis_run_id": start_body["analysis_run_id"],
            "reviewed_output_items": [
                {
                    "item_ref": "untraceable-cohort-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                    },
                }
            ],
        },
    )
    assert unresolved_trace.status_code == 409
    assert unresolved_trace.json()["error_code"] == "execution_result_review_trace_unresolved"

    db = client.layer3_session_factory()
    try:
        malformed_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        original_summary = dict(malformed_pass.summary_json)
        original_output_payload_ref = malformed_pass.output_payload_ref
        malformed_pass.summary_json = {
            **malformed_pass.summary_json,
            "source_dataset_version_ids_json": "dv-cohort-001",
        }
        db.commit()
    finally:
        db.close()

    malformed_review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-cohort-result-review-malformed-provenance",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
        },
    )
    assert malformed_review.status_code == 409
    assert malformed_review.json()["error_code"] == "associated_cohort_execution_state_not_admitted"

    db = client.layer3_session_factory()
    try:
        missing_output_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        missing_output_pass.summary_json = original_summary
        missing_output_pass.output_payload_ref = original_output_payload_ref
        db.commit()
    finally:
        db.close()

    output_path = Path(original_output_payload_ref)
    original_output_payload = json.loads(output_path.read_text(encoding="utf-8"))
    mismatched_output_payload = {
        **original_output_payload,
        "source_dataset_version_ids_json": ["dv-cohort-999"],
    }
    output_path.write_text(
        json.dumps(mismatched_output_payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    output_mismatch_review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-cohort-result-review-output-mismatch",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
        },
    )
    assert output_mismatch_review.status_code == 409
    assert output_mismatch_review.json()["error_code"] == "associated_cohort_result_review_not_admitted"
    output_path.write_text(
        json.dumps(original_output_payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )

    db = client.layer3_session_factory()
    try:
        missing_output_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        missing_output_pass.output_payload_ref = None
        db.commit()
    finally:
        db.close()

    missing_output_review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-cohort-result-review-missing-output",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
        },
    )
    assert missing_output_review.status_code == 409
    assert missing_output_review.json()["error_code"] == "execution_result_review_not_available"

    db = client.layer3_session_factory()
    try:
        pass_rows = db.query(L3PassRun).all()
        assert all("execution_result_review" not in (row.summary_json or {}) for row in pass_rows)
        assert db.query(L3ReconciliationRecord).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_api_execution_result_review_records_approval_without_downstream_writes(
    client: TestClient,
    tmp_path,
) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-result-review-selection-success",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-result-review-start-success",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200
    start_body = start.json()

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["status"] == "available"

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()

    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-approve",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Output is traceable enough for this bounded tranche.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert review.status_code == 200
    review_body = review.json()
    _assert_common_response_envelope(review_body)
    assert review_body["schema_id"] == "layer3.execution_result_review.v1"
    assert review_body["status"] == "recorded"
    assert review_body["result_status_available"] is True
    assert review_body["result_review_enabled"] is True
    assert review_body["review_state"] == "execution_result_review_approved"
    assert review_body["operator_decision"] == "approved"
    assert review_body["unresolved_trace_count"] == 0
    assert review_body["trace_summary"]["output_payload_ref"] == status_body["output_payload_ref"]
    assert review_body["trace_summary"]["reviewed_item_count"] == 1
    assert review_body["package_review_enabled"] is False
    assert review_body["handoff_enabled"] is False
    assert review_body["downstream_unavailable"] == ["package", "handoff", "package_review"]

    duplicate = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-approve",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "operator_decision": "approved",
            "review_notes": "Output is traceable enough for this bounded tranche.",
            "reviewed_output_items": [
                {
                    "item_ref": "primary-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                        "pass_run_id": pass_run_id,
                        "analysis_run_id": start_body["analysis_run_id"],
                        "output_payload_ref": status_body["output_payload_ref"],
                    },
                }
            ],
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "already_recorded"
    assert duplicate.json()["review_record_ref"] == review_body["review_record_ref"]

    conflict = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-conflict",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "rejected",
            "review_notes": "Conflicting duplicate review.",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "execution_result_review_already_recorded"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["execution_result_review"]["review_record_ref"] == review_body["review_record_ref"]
    assert summary_body["execution_result_review"]["review_state"] == "execution_result_review_approved"
    assert summary_body["execution_result_review"]["package_review_enabled"] is False
    assert summary_body["execution_result_review"]["handoff_enabled"] is False

    db = client.layer3_session_factory()
    try:
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        stored_pass = db.query(L3PassRun).one()
        review_state = stored_pass.summary_json["execution_result_review"]
        assert review_state["review_record_ref"] == review_body["review_record_ref"]
        assert review_state["operator_decision"] == "approved"
    finally:
        db.close()


def test_layer3_api_package_review_preview_requires_approved_result_review_and_is_read_only(
    client: TestClient,
    tmp_path,
) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-package-preview-selection-precheck",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    before_review = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert before_review.status_code == 409
    assert before_review.json()["error_code"] in {
        "analysis_execution_start_required",
        "pass_run_not_terminal",
        "package_review_preview_requires_approved_result_review",
    }

    start_body, status_body, review_body = _start_and_approve_quant_result_review(
        client,
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        request_id="api-package-preview-success",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-package-preview-read-only",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )

    assert preview.status_code == 200
    body = preview.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.package_review_preview.v1"
    assert body["status"] == "available"
    assert body["session_id"] == session_id
    assert body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert body["pass_run_id"] == pass_run_id
    assert body["preview_identity"]["preview_id"] == preview_body["preview_id"]
    assert body["preview_identity"]["preview_hash"] == preview_body["preview_hash"]
    assert body["analysis_run_id"] == start_body["analysis_run_id"]
    assert body["result_status_available"] is True
    assert body["result_review_state"] == "execution_result_review_approved"
    assert body["result_review_record_ref"] == review_body["review_record_ref"]
    assert body["package_review_preview_hash"].startswith("l3-package-preview-")
    assert body["package_review_preview_enabled"] is True
    assert body["package_commit_enabled"] is True
    assert body["package_review_enabled"] is False
    assert [item["package_kind"] for item in body["candidate_package_kinds"]] == [
        "canonical_internal",
        "user_facing",
        "review_facing",
    ]
    assert all(item["preview_only"] is True for item in body["candidate_package_kinds"])
    assert all(item["package_commit_enabled"] is True for item in body["candidate_package_kinds"])
    assert body["package_owner_compatibility"]["materialize_package_entry_callable"] is False
    assert body["package_owner_compatibility"]["preview_candidate_projection_compatible"] is True
    assert "pass_entry" in body["package_owner_compatibility"]["missing_owner_service_inputs"]
    assert body["blocked_reasons"] == []
    assert body["downstream_unavailable"] == [
        "package_review_submit",
        "handoff",
        "export",
    ]
    assert body["next_state"] == "package_review_preview_ready"
    assert body["output_metadata_summary"]["output_payload_ref"] == status_body["output_payload_ref"]
    assert body["unresolved_trace_count"] == 0

    db = client.layer3_session_factory()
    try:
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
    finally:
        db.close()


def test_layer3_api_package_construction_commit_materializes_three_packages_idempotently(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        _status_body,
        review_body,
    ) = _execute_and_approve_quant_result_review(
        client,
        tmp_path,
        request_id="api-package-commit-success",
    )
    pass_run_id = selection_body["pass_run_ids"][0]
    preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-package-commit-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert preview.status_code == 200
    preview_state = preview.json()

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()

    commit_payload = {
        "client_request_id": "api-package-commit-success-commit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": preview_state["package_review_preview_hash"],
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    commit = client.post("/api/v1/layer3/package/review/commit", json=commit_payload)
    assert commit.status_code == 200
    body = commit.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.package_construction_commit.v1"
    assert body["status"] == "committed"
    assert body["next_state"] == "package_constructed"
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert len(body["output_packages"]) == 3
    assert len(body["payload_refs"]) == 3
    assert len(body["payload_hashes"]) == 3
    assert body["package_review_submit_enabled"] is True
    assert body["handoff_enabled"] is False
    assert body["downstream_unavailable"] == ["handoff", "export"]
    for payload_ref, payload_hash in zip(body["payload_refs"], body["payload_hashes"], strict=True):
        payload_path = Path(payload_ref)
        assert payload_path.exists()
        assert hashlib.sha256(payload_path.read_bytes()).hexdigest() == payload_hash
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        assert payload["package_header"]["source_gate"] == "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE"

    db = client.layer3_session_factory()
    try:
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == {
            **counts_before,
            "packages": counts_before["packages"] + 3,
            "reconciliations": counts_before["reconciliations"] + 1,
        }
        packages = db.query(L3OutputPackage).all()
        assert {package.package_kind for package in packages} == {
            "canonical_internal",
            "user_facing",
            "review_facing",
        }
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert reconciliation.summary_json["source_gate"] == "50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE"
        assert reconciliation.summary_json["workbench_package_commit"]["package_review_submit_enabled"] is True
    finally:
        db.close()

    duplicate = client.post("/api/v1/layer3/package/review/commit", json=commit_payload)
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["status"] == "already_committed"
    assert duplicate_body["reconciliation_record_id"] == body["reconciliation_record_id"]
    assert duplicate_body["payload_refs"] == body["payload_refs"]

    conflict_payload = {**commit_payload, "client_request_id": "api-package-commit-conflict"}
    conflict = client.post("/api/v1/layer3/package/review/commit", json=conflict_payload)
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "package_construction_commit_blocked"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["current_gate"] == "package"
    assert summary_body["package_construction"]["state"] == "package_constructed"
    assert summary_body["package_construction"]["package_commit_enabled"] is False
    assert summary_body["package_construction"]["package_review_submit_enabled"] is True
    assert summary_body["package_review_submit"]["state"] == "package_review_submit_ready"
    assert summary_body["package_review_submit"]["package_review_submit_enabled"] is True
    assert summary_body["package_review_submit"]["downstream_unavailable"] == ["handoff", "export"]
    assert summary_body["downstream_unavailable"] == ["handoff", "export"]

    db = client.layer3_session_factory()
    try:
        db.add(
            L3OutputPackage(
                session_id=session_id,
                reconciliation_record_id=body["reconciliation_record_id"],
                package_kind="unexpected_debug_package",
                status="package_complete",
                payload_ref=str(tmp_path / "unexpected-package.json"),
                payload_hash="0" * 64,
                summary_json={"test_scope": "unexpected_package_kind"},
            )
        )
        db.commit()
    finally:
        db.close()

    blocked_summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert blocked_summary.status_code == 200
    blocked_summary_body = blocked_summary.json()
    assert blocked_summary_body["package_construction"]["state"] == "package_commit_blocked"
    assert blocked_summary_body["package_construction"]["blocked_reason"] == "unexpected_package_state"
    assert blocked_summary_body["package_construction"]["unexpected_package_kinds"] == ["unexpected_debug_package"]
    assert blocked_summary_body["package_review_submit"]["state"] == "package_review_submit_unavailable"
    assert blocked_summary_body["downstream_unavailable"] == ["package_review_submit", "handoff", "export"]

    blocked_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": "api-package-commit-unexpected-submit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": body["package_review_preview_hash"],
            "reconciliation_record_id": body["reconciliation_record_id"],
            "output_package_ids": [package["output_package_id"] for package in body["output_packages"]],
            "payload_hashes": body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert blocked_submit.status_code == 409
    assert blocked_submit.json()["error_code"] == "package_review_submit_unexpected_package_state"


def test_layer3_api_package_review_submit_records_decision_without_mutating_packages(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-package-submit-success")
    pass_run_id = selection_body["pass_run_ids"][0]

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
    finally:
        db.close()

    submit_payload = {
        "client_request_id": "api-package-submit-success-submit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    submit = client.post("/api/v1/layer3/package/review/submit", json=submit_payload)
    assert submit.status_code == 200
    body = submit.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.package_review_submit.v1"
    assert body["status"] == "submitted"
    assert body["package_review_state"] == "package_review_approved"
    assert body["operator_decision"] == "approved"
    assert body["decision_notes"] is None
    assert body["package_review_submit_enabled"] is False
    assert body["handoff_enabled"] is False
    assert body["export_enabled"] is False
    assert body["downstream_unavailable"] == ["aps_handoff", "external_export", "downstream_dispatch"]
    assert set(body["output_package_ids"]) == set(submit_payload["output_package_ids"])
    assert body["payload_hashes"] == commit_body["payload_hashes"]

    db = client.layer3_session_factory()
    try:
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation = db.query(L3ReconciliationRecord).one()
        submit_state = reconciliation.summary_json["package_review_submit"]
        assert submit_state["submit_record_ref"] == body["submit_record_ref"]
        assert submit_state["operator_decision"] == "approved"
        assert submit_state["package_review_state"] == "package_review_approved"
        assert submit_state["downstream_unavailable"] == ["aps_handoff", "external_export", "downstream_dispatch"]
        assert reconciliation.summary_json["workbench_package_commit"]["package_review_submit_enabled"] is False
    finally:
        db.close()

    duplicate = client.post("/api/v1/layer3/package/review/submit", json=submit_payload)
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["status"] == "already_submitted"
    assert duplicate_body["submit_record_ref"] == body["submit_record_ref"]

    conflict = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            **submit_payload,
            "client_request_id": "api-package-submit-conflict",
            "operator_decision": "rejected",
            "decision_notes": "Different decision conflicts with recorded submit state.",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "package_review_submit_already_recorded"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["package_review_submit"]["state"] == "package_review_approved"
    assert summary_body["package_review_submit"]["operator_decision"] == "approved"
    assert summary_body["package_review_submit"]["analysis_run_id"] == start_body["analysis_run_id"]
    assert summary_body["package_review_submit"]["result_review_record_ref"] == review_body["review_record_ref"]
    assert summary_body["package_review_submit"]["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert summary_body["package_review_submit"]["package_review_submit_enabled"] is False
    assert summary_body["package_review_submit"]["payload_hashes"] == commit_body["payload_hashes"]
    assert summary_body["package_review_submit"]["downstream_unavailable"] == [
        "aps_handoff",
        "external_export",
        "downstream_dispatch",
    ]
    assert summary_body["handoff_export_prepare"]["available"] is True
    assert summary_body["handoff_export_prepare"]["state"] == "handoff_export_ready"
    assert summary_body["handoff_export_prepare"]["analysis_run_id"] == start_body["analysis_run_id"]
    assert summary_body["handoff_export_prepare"]["result_review_record_ref"] == review_body["review_record_ref"]
    assert summary_body["handoff_export_prepare"]["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert summary_body["handoff_export_prepare"]["package_review_state"] == "package_review_approved"
    assert summary_body["handoff_export_prepare"]["payload_refs"] == commit_body["payload_refs"]
    assert summary_body["handoff_export_prepare"]["payload_hashes"] == commit_body["payload_hashes"]
    assert summary_body["downstream_unavailable"] == ["aps_handoff", "external_export", "downstream_dispatch"]


def test_layer3_api_package_review_submit_preserves_legacy_submit_ref_idempotency(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-package-submit-legacy-ref")
    pass_run_id = selection_body["pass_run_ids"][0]
    submit_payload = {
        "client_request_id": "api-package-submit-legacy-ref-submit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    submit = client.post("/api/v1/layer3/package/review/submit", json=submit_payload)
    assert submit.status_code == 200

    legacy_basis_fields = (
        "schema_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_hashes",
        "operator_decision",
        "decision_notes",
    )
    added_basis_fields = (
        "pass_type",
        "pass_scope",
        "method",
        "source_gate",
        "package_construction_source_gate",
        "source_shape",
        "source_dataset_version_ids",
    )
    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).one()
        reconciliation_summary = dict(reconciliation.summary_json)
        submit_state = dict(reconciliation_summary["package_review_submit"])
        authority_basis = dict(submit_state["authority_basis"])
        legacy_basis = {field: authority_basis[field] for field in legacy_basis_fields}
        legacy_encoded = json.dumps(
            legacy_basis,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        legacy_ref = f"l3-package-review-submit-{hashlib.sha256(legacy_encoded).hexdigest()[:16]}"
        for field in added_basis_fields:
            submit_state.pop(field, None)
        submit_state["authority_basis"] = legacy_basis
        submit_state["submit_record_ref"] = legacy_ref
        reconciliation_summary["package_review_submit"] = submit_state
        reconciliation.summary_json = reconciliation_summary
        db.commit()
    finally:
        db.close()

    duplicate = client.post(
        "/api/v1/layer3/package/review/submit",
        json={**submit_payload, "client_request_id": "api-package-submit-legacy-ref-retry"},
    )
    assert duplicate.status_code == 200, duplicate.text
    duplicate_body = duplicate.json()
    assert duplicate_body["status"] == "already_submitted"
    assert duplicate_body["submit_record_ref"] == legacy_ref


def test_layer3_api_handoff_export_prepare_records_reference_envelope_without_side_effects(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(client, tmp_path, request_id="api-handoff-prepare-success")
    payload = _handoff_export_prepare_payload(
        request_id="api-handoff-prepare-success-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
    )

    def files_under_tmp() -> list[str]:
        return sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file())

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        reconciliation = db.query(L3ReconciliationRecord).one()
        submit_state_before = reconciliation.summary_json["package_review_submit"]
    finally:
        db.close()
    files_before = files_under_tmp()

    prepare = client.post("/api/v1/layer3/handoff/export/prepare", json=payload)
    assert prepare.status_code == 200
    body = prepare.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.handoff_export_prepare.v1"
    assert body["status"] == "prepared"
    assert body["session_id"] == session_id
    assert body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert body["pass_run_id"] == selection_body["pass_run_ids"][0]
    assert body["preview_identity"]["preview_id"] == preview_body["preview_id"]
    assert body["preview_identity"]["preview_hash"] == preview_body["preview_hash"]
    assert body["result_review_record_ref"] == review_body["review_record_ref"]
    assert body["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["output_package_ids"] == payload["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_refs"] == commit_body["payload_refs"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
    assert body["package_review_state"] == "package_review_approved"
    assert body["operator_decision"] == "authorize_prepare"
    assert body["handoff_export_state"] == "handoff_export_prepared"
    assert body["handoff_target"] == "internal_export_envelope"
    assert body["export_mode"] == "prepare_only"
    assert body["external_handoff_enabled"] is False
    assert body["external_export_enabled"] is False
    assert body["dispatch_enabled"] is False
    assert body["downstream_unavailable"] == ["aps_handoff", "external_export", "downstream_dispatch"]
    assert body["next_state"] == "handoff_export_prepared"
    envelope = body["handoff_export_envelope"]
    assert envelope["schema_id"] == "layer3.handoff_export_envelope.v1"
    assert envelope["output_package_ids"] == payload["output_package_ids"]
    assert envelope["payload_refs"] == commit_body["payload_refs"]
    assert envelope["payload_hashes"] == commit_body["payload_hashes"]
    assert envelope["external_handoff_enabled"] is False
    assert envelope["external_export_enabled"] is False
    assert envelope["dispatch_enabled"] is False
    for forbidden_key in (
        "package_payload",
        "generated_external_artifact",
        "download_url",
        "downstream_aps_id",
        "connector_run_id",
        "editable_package_payload",
        "rewritten_content",
    ):
        assert forbidden_key not in envelope

    db = client.layer3_session_factory()
    try:
        assert {
            "plans": db.query(L3AnalysisPlan).count(),
            "passes": db.query(L3PassRun).count(),
            "runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert reconciliation.summary_json["package_review_submit"] == submit_state_before
        prepare_state = reconciliation.summary_json["handoff_export_prepare"]
        assert prepare_state["prepare_record_ref"] == body["prepare_record_ref"]
        assert prepare_state["handoff_export_state"] == "handoff_export_prepared"
        assert prepare_state["handoff_export_envelope"] == envelope
    finally:
        db.close()
    assert files_under_tmp() == files_before

    duplicate = client.post("/api/v1/layer3/handoff/export/prepare", json=payload)
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["status"] == "already_prepared"
    assert duplicate_body["prepare_record_ref"] == body["prepare_record_ref"]

    same_basis_new_request = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**payload, "client_request_id": "api-handoff-prepare-success-prepare-replay"},
    )
    assert same_basis_new_request.status_code == 200
    assert same_basis_new_request.json()["prepare_record_ref"] == body["prepare_record_ref"]

    conflict = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={
            **payload,
            "operator_decision": "hold",
            "decision_notes": "Changing the recorded decision must fail closed.",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "handoff_export_prepare_already_recorded"

    conflicting_notes = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**payload, "decision_notes": "Changing notes must also fail closed."},
    )
    assert conflicting_notes.status_code == 409
    assert conflicting_notes.json()["error_code"] == "handoff_export_prepare_already_recorded"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["handoff_export_prepare"]["state"] == "handoff_export_prepared"
    assert summary_body["handoff_export_prepare"]["external_handoff_enabled"] is False
    assert summary_body["handoff_export_prepare"]["external_export_enabled"] is False
    assert summary_body["handoff_export_prepare"]["dispatch_enabled"] is False
    assert summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_blocked"
    assert summary_body["aps_handoff_dispatch"]["available"] is False
    assert summary_body["downstream_unavailable"] == [
        "aps_handoff",
        "external_export",
        "download",
        "connector_dispatch",
        "non_aps_dispatch",
    ]


def test_layer3_api_handoff_export_prepare_requires_package_review_submit(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-handoff-prepare-unsubmitted")
    payload = _handoff_export_prepare_payload(
        request_id="api-handoff-prepare-unsubmitted-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body={
            "submit_record_ref": "missing-submit-ref",
            "package_review_state": "package_review_approved",
        },
    )
    unsubmitted = client.post("/api/v1/layer3/handoff/export/prepare", json=payload)
    assert unsubmitted.status_code == 409
    assert unsubmitted.json()["error_code"] == "handoff_export_prepare_requires_approved_package_review"


def test_layer3_api_handoff_export_prepare_rejects_nonapproved_package_review_submit(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(
        client,
        tmp_path,
        request_id="api-handoff-prepare-nonapproved",
        operator_decision="blocked",
        decision_notes="Package-review approval is not granted.",
    )
    assert submit_body["package_review_state"] == "package_review_blocked"
    assert submit_body["downstream_unavailable"] == ["handoff", "export"]
    payload = _handoff_export_prepare_payload(
        request_id="api-handoff-prepare-nonapproved-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
    )
    payload["package_review_state"] = "package_review_approved"
    nonapproved = client.post("/api/v1/layer3/handoff/export/prepare", json=payload)
    assert nonapproved.status_code == 409
    assert nonapproved.json()["error_code"] == "handoff_export_prepare_requires_approved_package_review"


def test_layer3_api_handoff_export_prepare_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={"client_request_id": "api-handoff-prepare-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) == {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "package_review_submit_schema_id",
        "handoff_target",
        "export_mode",
        "operator_decision",
    }

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(client, tmp_path, request_id="api-handoff-prepare-prechecks")
    base_payload = _handoff_export_prepare_payload(
        request_id="api-handoff-prepare-prechecks-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
    )

    wrong_target = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "handoff_target": "aps_handoff"},
    )
    assert wrong_target.status_code == 400
    assert wrong_target.json()["error_code"] == "handoff_export_prepare_target_not_admitted"

    wrong_mode = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "export_mode": "dispatch"},
    )
    assert wrong_mode.status_code == 400
    assert wrong_mode.json()["error_code"] == "handoff_export_prepare_mode_not_admitted"

    unsupported_decision = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "operator_decision": "approve_export"},
    )
    assert unsupported_decision.status_code == 400
    assert unsupported_decision.json()["error_code"] == "unsupported_handoff_export_prepare_decision"

    forbidden = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "dispatch": True, "package_payload": {"unexpected": True}, "connector_run_id": "run-1"},
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "handoff_export_prepare_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"connector_run_id", "dispatch", "package_payload"}

    unknown = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "unexpected_control": True},
    )
    assert unknown.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "unexpected_control"]
        for item in unknown.json()["detail"]
    )

    for decision in ("hold", "decline", "blocked"):
        notes_required = client.post(
            "/api/v1/layer3/handoff/export/prepare",
            json={**base_payload, "operator_decision": decision},
        )
        assert notes_required.status_code == 400
        assert notes_required.json()["error_code"] == "handoff_export_prepare_notes_required"

    stale_review_ref = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "result_review_record_ref": "stale-review-ref"},
    )
    assert stale_review_ref.status_code == 409
    assert stale_review_ref.json()["error_code"] == "handoff_export_prepare_result_review_mismatch"

    stale_package_preview = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "package_review_preview_hash": "stale-package-preview"},
    )
    assert stale_package_preview.status_code == 409
    assert stale_package_preview.json()["error_code"] == "handoff_export_prepare_preview_mismatch"

    stale_submit_ref = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "package_review_submit_record_ref": "stale-submit-ref"},
    )
    assert stale_submit_ref.status_code == 409
    assert stale_submit_ref.json()["error_code"] == "handoff_export_prepare_submit_ref_mismatch"

    stale_reconciliation = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "reconciliation_record_id": "stale-reconciliation"},
    )
    assert stale_reconciliation.status_code == 409
    assert stale_reconciliation.json()["error_code"] == "handoff_export_prepare_requires_package_construction"

    stale_package_ids = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "output_package_ids": ["pkg-a", *base_payload["output_package_ids"][1:]]},
    )
    assert stale_package_ids.status_code == 409
    assert stale_package_ids.json()["error_code"] == "handoff_export_prepare_package_ids_mismatch"

    wrong_kinds = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "expected_package_kinds": ["canonical_internal"]},
    )
    assert wrong_kinds.status_code == 409
    assert wrong_kinds.json()["error_code"] == "handoff_export_prepare_kinds_mismatch"

    stale_payload_refs = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "payload_refs": ["stale-ref", *base_payload["payload_refs"][1:]]},
    )
    assert stale_payload_refs.status_code == 409
    assert stale_payload_refs.json()["error_code"] == "handoff_export_prepare_payload_refs_mismatch"

    stale_payload_hashes = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "payload_hashes": ["stale-hash", *base_payload["payload_hashes"][1:]]},
    )
    assert stale_payload_hashes.status_code == 409
    assert stale_payload_hashes.json()["error_code"] == "handoff_export_prepare_payload_hashes_mismatch"

    wrong_request_state = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json={**base_payload, "package_review_state": "package_review_blocked"},
    )
    assert wrong_request_state.status_code == 409
    assert wrong_request_state.json()["error_code"] == "handoff_export_prepare_requires_approved_package_review"

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "handoff_export_prepare" not in reconciliation.summary_json
    finally:
        db.close()


@pytest.mark.parametrize(
    ("operator_decision", "expected_status", "expected_state"),
    [
        ("hold", "held", "handoff_export_held"),
        ("decline", "declined", "handoff_export_declined"),
        ("blocked", "blocked", "handoff_export_blocked"),
    ],
)
def test_layer3_api_handoff_export_prepare_records_non_dispatch_decisions(
    client: TestClient,
    tmp_path,
    operator_decision: str,
    expected_status: str,
    expected_state: str,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(
        client,
        tmp_path,
        request_id=f"api-handoff-prepare-{operator_decision}",
    )
    payload = _handoff_export_prepare_payload(
        request_id=f"api-handoff-prepare-{operator_decision}-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        operator_decision=operator_decision,
        decision_notes=f"{operator_decision} handoff/export preparation for this authority basis.",
    )

    def files_under_tmp() -> list[str]:
        return sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file())

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
    finally:
        db.close()
    files_before = files_under_tmp()

    prepare = client.post("/api/v1/layer3/handoff/export/prepare", json=payload)
    assert prepare.status_code == 200
    body = prepare.json()
    assert body["status"] == expected_status
    assert body["operator_decision"] == operator_decision
    assert body["decision_notes"] == payload["decision_notes"]
    assert body["handoff_export_state"] == expected_state
    assert "handoff_export_envelope" not in body
    assert body["external_handoff_enabled"] is False
    assert body["external_export_enabled"] is False
    assert body["dispatch_enabled"] is False
    assert body["downstream_unavailable"] == ["aps_handoff", "external_export", "downstream_dispatch"]

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        prepare_state = reconciliation.summary_json["handoff_export_prepare"]
        assert prepare_state["operator_decision"] == operator_decision
        assert prepare_state["handoff_export_state"] == expected_state
        assert "handoff_export_envelope" not in prepare_state
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        assert {
            "artifacts": db.query(AnalysisArtifact).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
    finally:
        db.close()
    assert files_under_tmp() == files_before

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    assert summary.json()["handoff_export_prepare"]["state"] == expected_state


def test_layer3_api_aps_handoff_dispatch_materializes_owner_service_bundle_without_mutating_sources(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        _start_body,
        _review_body,
        _package_preview_body,
        commit_body,
        _submit_body,
        prepare_body,
        payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-aps-handoff-dispatch-success")

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        source_packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id.in_(payload["output_package_ids"]))
            .order_by(L3OutputPackage.package_kind.asc())
            .all()
        ]
        counts_before = {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()
    files_before = files_under_tmp()

    ready_summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert ready_summary.status_code == 200
    ready_summary_body = ready_summary.json()
    assert ready_summary_body["handoff_export_prepare"]["state"] == "handoff_export_prepared"
    assert ready_summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_ready"
    assert ready_summary_body["aps_handoff_dispatch"]["available"] is True
    assert ready_summary_body["downstream_unavailable"] == [
        "external_export",
        "download",
        "connector_dispatch",
        "non_aps_dispatch",
    ]

    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert dispatch.status_code == 200, dispatch.json()
    body = dispatch.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.aps_handoff_dispatch.v1"
    assert body["status"] == "dispatched"
    assert body["session_id"] == session_id
    assert body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert body["pass_run_id"] == selection_body["pass_run_ids"][0]
    assert body["result_review_record_ref"] == payload["result_review_record_ref"]
    assert body["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["output_package_ids"] == payload["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_refs"] == commit_body["payload_refs"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["source_package_refs"] == dict(zip(body["package_kinds"], commit_body["payload_refs"]))
    assert body["source_package_hashes"] == dict(zip(body["package_kinds"], commit_body["payload_hashes"]))
    assert body["package_review_submit_record_ref"] == payload["package_review_submit_record_ref"]
    assert body["package_review_state"] == "package_review_approved"
    assert body["prepare_record_ref"] == prepare_body["prepare_record_ref"]
    assert body["handoff_export_state"] == "handoff_export_prepared"
    assert body["handoff_export_envelope_ref"] == payload["handoff_export_envelope_ref"]
    assert body["handoff_target"] == "internal_export_envelope"
    assert body["export_mode"] == "prepare_only"
    assert body["aps_handoff_target"] == "aps_evidence_bundle"
    assert body["dispatch_mode"] == "server_side_aps_handoff"
    assert body["operator_decision"] == "dispatch_aps_handoff"
    assert body["aps_handoff_state"] == "aps_handoff_dispatched"
    assert body["aps_output_package_kind"] == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
    assert body["aps_bundle_ref"]
    assert body["aps_bundle_id"]
    assert body["aps_schema_id"]
    assert body["external_export_enabled"] is False
    assert body["download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["downstream_unavailable"] == [
        "external_export",
        "download",
        "connector_dispatch",
        "non_aps_dispatch",
    ]
    assert body["next_state"] == "aps_handoff_dispatched"
    for forbidden_key in (
        "download_url",
        "connector_run_id",
        "external_target",
        "package_payload",
        "package_variant_content",
        "rewritten_content",
    ):
        assert forbidden_key not in body

    db = client.layer3_session_factory()
    try:
        source_packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id.in_(payload["output_package_ids"]))
            .order_by(L3OutputPackage.package_kind.asc())
            .all()
        ]
        assert source_packages_after == source_packages_before
        assert db.query(AnalysisArtifact).count() == counts_before["artifacts"]
        assert db.query(ConnectorRun).count() == counts_before["connector_runs"]
        assert db.query(L3ReconciliationRecord).count() == counts_before["reconciliations"]
        assert db.query(L3OutputPackage).count() == counts_before["packages"] + 1
        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count()
            == counts_before["aps_packages"] + 1
        )
        aps_package = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .one()
        )
        assert aps_package.output_package_id == body["aps_output_package_id"]
        assert aps_package.payload_ref == body["aps_bundle_ref"]
        assert aps_package.payload_hash
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        dispatch_state = reconciliation.summary_json["aps_handoff_dispatch"]
        assert dispatch_state["aps_handoff_record_ref"] == body["aps_handoff_record_ref"]
        assert dispatch_state["aps_handoff_state"] == "aps_handoff_dispatched"
        assert dispatch_state["aps_output_package_id"] == body["aps_output_package_id"]
    finally:
        db.close()

    files_after = files_under_tmp()
    added_files = files_after - files_before
    assert Path(body["aps_bundle_ref"]).exists()
    assert str(Path(body["aps_bundle_ref"]).relative_to(tmp_path)) in added_files
    assert len(added_files) == 1

    replay = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["status"] == "already_dispatched"
    assert replay_body["aps_handoff_record_ref"] == body["aps_handoff_record_ref"]
    assert replay_body["aps_output_package_id"] == body["aps_output_package_id"]

    same_basis_new_request = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json={**payload, "client_request_id": "api-aps-handoff-dispatch-success-new-request"},
    )
    assert same_basis_new_request.status_code == 409
    assert same_basis_new_request.json()["error_code"] == "aps_handoff_dispatch_already_recorded"

    conflicting_notes = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json={**payload, "decision_notes": "Changing notes after dispatch must fail closed."},
    )
    assert conflicting_notes.status_code == 409
    assert conflicting_notes.json()["error_code"] == "aps_handoff_dispatch_already_recorded"

    db = client.layer3_session_factory()
    try:
        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count()
            == 1
        )
    finally:
        db.close()

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["package_construction"]["state"] == "package_constructed"
    assert summary_body["package_construction"]["unexpected_package_kinds"] == []
    assert summary_body["handoff_export_prepare"]["state"] == "handoff_export_prepared"
    assert summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_dispatched"
    assert summary_body["aps_handoff_dispatch"]["available"] is False
    assert summary_body["aps_handoff_dispatch"]["aps_output_package_id"] == body["aps_output_package_id"]
    assert summary_body["external_export_download"]["state"] == "external_export_download_ready"
    assert summary_body["external_export_download"]["available"] is True
    assert summary_body["external_export_download"]["aps_handoff_record_ref"] == body["aps_handoff_record_ref"]
    assert summary_body["downstream_unavailable"] == [
        "browser_download",
        "download_url",
        "connector_dispatch",
        "destination_selection",
        "generic_downstream_dispatch",
    ]


def test_layer3_api_cohort_aps_handoff_dispatch_materializes_bundle_with_companion_provenance(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    _patch_cohort_dataframe_persistence(monkeypatch, tmp_path)
    session_id, preview_body, approval_body = _approve_cohort_aps_handoff_plan(client, tmp_path)
    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-cohort-aps-dispatch-selection",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200
    selection_body = selection.json()
    assert len(selection_body["pass_run_ids"]) == 1
    pass_run_id = selection_body["pass_run_ids"][0]

    start_body, status_body, review_body = _start_and_approve_quant_result_review(
        client,
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        request_id="api-cohort-aps-dispatch",
    )
    assert status_body["pass_type"] == "associated_cohort"

    package_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-cohort-aps-dispatch-package-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert package_preview.status_code == 200
    package_preview_body = package_preview.json()
    assert package_preview_body["pass_type"] == "associated_cohort"
    assert package_preview_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert package_preview_body["selected_method_name"] == "descriptive_summary"
    assert package_preview_body["source_gate"] == "78_COHORT_FREEZE"
    assert package_preview_body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]
    assert package_preview_body["cohort_shape"] == "aligned_wide_table"
    assert package_preview_body["package_owner_compatibility"]["status"] == (
        "associated_cohort_construction_preconditions_satisfied"
    )
    assert package_preview_body["package_owner_compatibility"][
        "construction_compatible_with_current_workbench_state"
    ] is True

    package_commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": "api-cohort-aps-dispatch-package-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": package_preview_body["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_commit.status_code == 200
    commit_body = package_commit.json()
    assert commit_body["schema_id"] == "layer3.package_construction_commit.v1"
    assert commit_body["status"] == "committed"
    assert commit_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert commit_body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert commit_body["source_shape"] == "aligned_wide_table"
    assert commit_body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]

    package_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": "api-cohort-aps-dispatch-package-submit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": commit_body["package_review_preview_hash"],
            "reconciliation_record_id": commit_body["reconciliation_record_id"],
            "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
            "payload_hashes": commit_body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert package_submit.status_code == 200
    submit_body = package_submit.json()
    assert submit_body["schema_id"] == "layer3.cohort_package_review_submit.v1"
    assert submit_body["package_review_state"] == "package_review_approved"
    assert submit_body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert submit_body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]

    prepare = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id="api-cohort-aps-dispatch-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
        ),
    )
    assert prepare.status_code == 200
    prepare_body = prepare.json()
    assert prepare_body["schema_id"] == "layer3.cohort_handoff_export_prepare.v1"
    assert prepare_body["handoff_export_state"] == "handoff_export_prepared"
    assert prepare_body["package_review_submit_schema_id"] == "layer3.cohort_package_review_submit.v1"
    assert prepare_body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]

    payload = _aps_handoff_dispatch_payload(
        request_id="api-cohort-aps-dispatch-success",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
    )

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        source_packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id.in_(payload["output_package_ids"]))
            .order_by(L3OutputPackage.package_kind.asc())
            .all()
        ]
        counts_before = {
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()
    files_before = files_under_tmp()

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        original_summary_json = dict(reconciliation.summary_json)
        reconciliation.summary_json = {
            **original_summary_json,
            "handoff_export_prepare": {
                **original_summary_json["handoff_export_prepare"],
                "source_dataset_version_ids": ["dv-api-cohort-aps-stale"],
            },
        }
        db.commit()
    finally:
        db.close()

    stale_prepare_dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert stale_prepare_dispatch.status_code == 409
    assert stale_prepare_dispatch.json()["error_code"] == "associated_cohort_aps_handoff_dispatch_not_admitted"
    assert "source_dataset_version_ids" in stale_prepare_dispatch.json()["blocked_fields"]
    assert files_under_tmp() == files_before

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        reconciliation.summary_json = original_summary_json
        db.commit()
    finally:
        db.close()

    ready_summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert ready_summary.status_code == 200
    ready_summary_body = ready_summary.json()
    assert ready_summary_body["handoff_export_prepare"]["state"] == "handoff_export_prepared"
    assert ready_summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_ready"
    assert ready_summary_body["aps_handoff_dispatch"]["available"] is True

    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert dispatch.status_code == 200, dispatch.json()
    body = dispatch.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.aps_handoff_dispatch.v1"
    assert body["status"] == "dispatched"
    assert body["pass_type"] == "associated_cohort"
    assert body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert body["method"] == "descriptive_summary"
    assert body["source_gate"] == "78_COHORT_FREEZE"
    assert body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert body["source_shape"] == "aligned_wide_table"
    assert body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]
    assert body["package_review_submit_schema_id"] == "layer3.cohort_package_review_submit.v1"
    assert body["aps_handoff_state"] == "aps_handoff_dispatched"
    assert body["aps_output_package_kind"] == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
    assert body["external_export_enabled"] is False
    assert body["download_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["downstream_unavailable"] == [
        "external_export",
        "download",
        "connector_dispatch",
        "non_aps_dispatch",
    ]
    for forbidden_key in (
        "download_url",
        "connector_run_id",
        "external_target",
        "package_payload",
        "package_variant_content",
        "rewritten_content",
    ):
        assert forbidden_key not in body

    db = client.layer3_session_factory()
    try:
        source_packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage)
            .filter(L3OutputPackage.output_package_id.in_(payload["output_package_ids"]))
            .order_by(L3OutputPackage.package_kind.asc())
            .all()
        ]
        assert source_packages_after == source_packages_before
        assert db.query(L3AnalysisPlan).count() == counts_before["analysis_plans"]
        assert db.query(AnalysisRun).count() == counts_before["analysis_runs"]
        assert db.query(L3AnalysisSet).count() == counts_before["analysis_sets"]
        assert db.query(AnalysisArtifact).count() == counts_before["artifacts"]
        assert db.query(ConnectorRun).count() == counts_before["connector_runs"]
        assert db.query(L3PassRun).count() == counts_before["pass_runs"]
        assert db.query(L3ReconciliationRecord).count() == counts_before["reconciliations"]
        assert db.query(L3OutputPackage).count() == counts_before["packages"] + 1
        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count()
            == counts_before["aps_packages"] + 1
        )
        aps_package = (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .one()
        )
        assert aps_package.output_package_id == body["aps_output_package_id"]
        assert aps_package.payload_ref == body["aps_bundle_ref"]
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        dispatch_state = reconciliation.summary_json["aps_handoff_dispatch"]
        assert dispatch_state["pass_type"] == "associated_cohort"
        assert dispatch_state["source_dataset_version_ids"] == [
            "dv-api-cohort-aps-001",
            "dv-api-cohort-aps-002",
        ]
        assert dispatch_state["package_review_submit_schema_id"] == "layer3.cohort_package_review_submit.v1"
        assert dispatch_state["aps_output_package_id"] == body["aps_output_package_id"]
    finally:
        db.close()

    files_after = files_under_tmp()
    added_files = files_after - files_before
    assert Path(body["aps_bundle_ref"]).exists()
    assert str(Path(body["aps_bundle_ref"]).relative_to(tmp_path)) in added_files
    assert len(added_files) == 1

    replay = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["status"] == "already_dispatched"
    assert replay_body["aps_handoff_record_ref"] == body["aps_handoff_record_ref"]
    assert replay_body["aps_output_package_id"] == body["aps_output_package_id"]

    conflicting_notes = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json={**payload, "decision_notes": "Changing notes after dispatch must fail closed."},
    )
    assert conflicting_notes.status_code == 409
    assert conflicting_notes.json()["error_code"] == "aps_handoff_dispatch_already_recorded"

    summary_after_dispatch = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary_after_dispatch.status_code == 200
    summary_after_dispatch_body = summary_after_dispatch.json()
    assert summary_after_dispatch_body["handoff_export_prepare"]["state"] == "handoff_export_prepared"
    assert summary_after_dispatch_body["aps_handoff_dispatch"]["state"] == "aps_handoff_dispatched"
    assert summary_after_dispatch_body["aps_handoff_dispatch"]["available"] is False
    assert summary_after_dispatch_body["aps_handoff_dispatch"]["aps_output_package_id"] == body["aps_output_package_id"]
    assert summary_after_dispatch_body["external_export_download"]["state"] == "external_export_download_ready"
    assert summary_after_dispatch_body["external_export_download"]["available"] is True
    assert summary_after_dispatch_body["external_export_download"]["pass_type"] == "associated_cohort"
    assert summary_after_dispatch_body["external_export_download"]["pass_scope"] == (
        "quantitative_associated_cohort_dataset_version"
    )
    assert summary_after_dispatch_body["external_export_download"]["method"] == "descriptive_summary"
    assert summary_after_dispatch_body["external_export_download"]["source_gate"] == "78_COHORT_FREEZE"
    assert summary_after_dispatch_body["external_export_download"]["package_construction_source_gate"] == (
        "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    )
    assert summary_after_dispatch_body["external_export_download"]["source_shape"] == "aligned_wide_table"
    assert summary_after_dispatch_body["external_export_download"]["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]
    assert summary_after_dispatch_body["external_export_download"]["package_review_submit_schema_id"] == (
        "layer3.cohort_package_review_submit.v1"
    )
    assert summary_after_dispatch_body["downstream_unavailable"] == [
        "browser_download",
        "download_url",
        "connector_dispatch",
        "destination_selection",
        "generic_downstream_dispatch",
    ]

    download_payload = _external_export_download_prepare_payload(
        request_id="api-cohort-aps-dispatch-download-prepare-success",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=body,
    )

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        summary_json_after_dispatch = dict(reconciliation.summary_json)
        reconciliation.summary_json = {
            **summary_json_after_dispatch,
            "aps_handoff_dispatch": {
                **summary_json_after_dispatch["aps_handoff_dispatch"],
                "source_dataset_version_ids": ["dv-api-cohort-aps-stale"],
            },
        }
        db.commit()
    finally:
        db.close()

    stale_dispatch_download_prepare = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json=download_payload,
    )
    assert stale_dispatch_download_prepare.status_code == 409
    assert stale_dispatch_download_prepare.json()["error_code"] == (
        "associated_cohort_external_export_download_prepare_not_admitted"
    )
    assert "source_dataset_version_ids" in stale_dispatch_download_prepare.json()["blocked_fields"]
    assert files_under_tmp() == files_after

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        reconciliation.summary_json = summary_json_after_dispatch
        db.commit()
        counts_after_dispatch = {
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_after_dispatch = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert "external_export_download_prepare" not in reconciliation.summary_json
    finally:
        db.close()

    cohort_download_prepare = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json=download_payload,
    )
    assert cohort_download_prepare.status_code == 200, cohort_download_prepare.json()
    download_body = cohort_download_prepare.json()
    _assert_common_response_envelope(download_body)
    assert download_body["schema_id"] == "layer3.external_export_download_prepare.v1"
    assert download_body["status"] == "prepared"
    assert download_body["pass_type"] == "associated_cohort"
    assert download_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert download_body["method"] == "descriptive_summary"
    assert download_body["source_gate"] == "78_COHORT_FREEZE"
    assert download_body["package_construction_source_gate"] == "88_COHORT_PACKAGE_CONSTRUCTION_FREEZE"
    assert download_body["source_shape"] == "aligned_wide_table"
    assert download_body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]
    assert download_body["package_review_submit_schema_id"] == "layer3.cohort_package_review_submit.v1"
    assert download_body["external_export_download_state"] == "external_export_download_prepared"
    assert download_body["source_artifact_ref"] == body["aps_bundle_ref"]
    assert download_body["source_artifact_hash"] == download_payload["aps_bundle_hash"]
    assert download_body["source_artifact_size_bytes"] == download_payload["aps_bundle_size_bytes"]
    assert download_body["browser_download_enabled"] is False
    assert download_body["download_url_enabled"] is False
    assert download_body["connector_dispatch_enabled"] is False
    assert download_body["destination_selection_enabled"] is False
    assert download_body["generic_downstream_dispatch_enabled"] is False
    assert download_body["delivery_ui"] == {
        "schema_id": "layer3.external_export_download_delivery_ui.v1",
        "available": True,
        "state": "associated_cohort_external_export_download_delivery_ui_ready",
        "blocked_reason": None,
        "blocked_fields": [],
        "operator_decision": "deliver_external_export_download",
        "delivery_mode": "same_origin_artifact_stream",
        "server_authority": "associated_cohort_external_export_download_delivery_ui_gate",
        "browser_managed_same_origin_attachment_enabled": True,
        "public_url_enabled": False,
        "signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_selection_enabled": False,
        "generic_downstream_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "schema_runtime_source_widening_enabled": False,
    }
    assert download_body["downstream_unavailable"] == [
        "browser_download",
        "download_url",
        "connector_dispatch",
        "destination_selection",
        "generic_downstream_dispatch",
    ]
    descriptor = download_body["external_export_download_descriptor"]
    assert descriptor["descriptor_ref"] == download_body["export_download_descriptor_ref"]
    assert descriptor["source_artifact_ref"] == body["aps_bundle_ref"]
    for forbidden_key in (
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "external_target",
        "destination",
        "package_payload",
        "raw_aps_bundle",
        "rewritten_content",
    ):
        assert forbidden_key not in download_body
        assert forbidden_key not in descriptor

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_after_dispatch
        packages_after_download_prepare = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after_download_prepare == packages_after_dispatch
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        readiness_state = reconciliation.summary_json["external_export_download_prepare"]
        assert readiness_state["external_export_download_record_ref"] == (
            download_body["external_export_download_record_ref"]
        )
        assert readiness_state["external_export_download_state"] == "external_export_download_prepared"
        assert readiness_state["pass_type"] == "associated_cohort"
        assert readiness_state["source_dataset_version_ids"] == [
            "dv-api-cohort-aps-001",
            "dv-api-cohort-aps-002",
        ]
    finally:
        db.close()
    assert files_under_tmp() == files_after

    download_replay = client.post("/api/v1/layer3/handoff/export/download/prepare", json=download_payload)
    assert download_replay.status_code == 200
    assert download_replay.json()["status"] == "already_prepared"
    assert download_replay.json()["external_export_download_record_ref"] == (
        download_body["external_export_download_record_ref"]
    )

    download_same_basis_new_request = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json={**download_payload, "client_request_id": "api-cohort-aps-dispatch-download-prepare-new-request"},
    )
    assert download_same_basis_new_request.status_code == 409
    assert download_same_basis_new_request.json()["error_code"] == "external_export_download_prepare_already_recorded"

    summary_after_prepare = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary_after_prepare.status_code == 200
    summary_after_prepare_body = summary_after_prepare.json()
    assert summary_after_prepare_body["external_export_download"]["state"] == "external_export_download_prepared"
    assert summary_after_prepare_body["external_export_download"]["available"] is False
    assert summary_after_prepare_body["external_export_download"]["blocked_reason"] is None
    assert summary_after_prepare_body["external_export_download"]["export_download_descriptor_ref"] == (
        download_body["export_download_descriptor_ref"]
    )
    assert summary_after_prepare_body["external_export_download"]["pass_type"] == "associated_cohort"
    assert summary_after_prepare_body["external_export_download"]["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]
    assert summary_after_prepare_body["external_export_download"]["delivery_ui"]["available"] is True
    assert summary_after_prepare_body["external_export_download"]["delivery_ui"]["state"] == (
        "associated_cohort_external_export_download_delivery_ui_ready"
    )
    assert (
        summary_after_prepare_body["external_export_download"]["delivery_ui"][
            "browser_managed_same_origin_attachment_enabled"
        ]
        is True
    )
    assert summary_after_prepare_body["external_export_download"]["delivery_ui"]["public_url_enabled"] is False
    assert summary_after_prepare_body["downstream_unavailable"] == [
        "browser_download",
        "download_url",
        "connector_dispatch",
        "destination_selection",
        "generic_downstream_dispatch",
    ]

    cohort_deliver_payload = _external_export_download_deliver_payload(
        request_id="api-cohort-aps-dispatch-download-deliver-success",
        prepare_payload=download_payload,
        readiness_body=download_body,
        decision_notes="Deliver the associated-cohort APS bundle artifact through the same-origin stream.",
    )
    expected_delivery_bytes = Path(download_body["source_artifact_ref"]).read_bytes()

    db = client.layer3_session_factory()
    try:
        counts_before_delivery = {
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before_delivery = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        readiness_state_before_delivery = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json["external_export_download_prepare"]
        )
    finally:
        db.close()
    files_before_delivery = files_under_tmp()

    cohort_delivery = client.post(
        "/api/v1/layer3/handoff/export/download/deliver",
        json=cohort_deliver_payload,
    )
    assert cohort_delivery.status_code == 200, cohort_delivery.text
    assert cohort_delivery.content == expected_delivery_bytes
    assert cohort_delivery.headers["content-type"].startswith("application/json")
    assert "attachment" in cohort_delivery.headers["content-disposition"]
    assert "filename=" in cohort_delivery.headers["content-disposition"]
    assert cohort_delivery.headers["x-layer3-schema-id"] == "layer3.external_export_download_delivery.v1"
    assert cohort_delivery.headers["x-layer3-delivery-state"] == "external_export_download_delivered"
    assert cohort_delivery.headers["x-layer3-source-artifact-hash"] == download_body["source_artifact_hash"]
    assert cohort_delivery.headers["x-layer3-external-export-download-record-ref"] == (
        download_body["external_export_download_record_ref"]
    )
    assert "download_url" not in cohort_delivery.headers
    assert "public_url" not in cohort_delivery.headers
    assert "signed_url" not in cohort_delivery.headers
    assert "connector_run_id" not in cohort_delivery.headers

    cohort_delivery_replay = client.post(
        "/api/v1/layer3/handoff/export/download/deliver",
        json=cohort_deliver_payload,
    )
    assert cohort_delivery_replay.status_code == 200
    assert cohort_delivery_replay.content == expected_delivery_bytes

    monkeypatch.delenv("LAYER3_SIGNED_REFERENCE_SECRET", raising=False)
    missing_secret_reference = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/generate",
        json=cohort_deliver_payload,
    )
    assert missing_secret_reference.status_code == 409
    assert missing_secret_reference.json()["error_code"] == (
        "external_export_download_signed_reference_secret_required"
    )
    assert missing_secret_reference.json()["blocked_fields"] == ["LAYER3_SIGNED_REFERENCE_SECRET"]

    missing_secret_use = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/use",
        json={"signed_reference_token": "not-a-valid-reference"},
    )
    assert missing_secret_use.status_code == 409
    assert missing_secret_use.json()["error_code"] == "external_export_download_signed_reference_secret_required"

    monkeypatch.setenv("LAYER3_SIGNED_REFERENCE_SECRET", "test-layer3-signed-reference-secret")
    signed_reference = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/generate",
        json=cohort_deliver_payload,
    )
    assert signed_reference.status_code == 200, signed_reference.text
    signed_reference_body = signed_reference.json()
    assert signed_reference_body["schema_id"] == "layer3.external_export_download_signed_reference.v1"
    assert signed_reference_body["status"] == "prepared"
    assert signed_reference_body["signed_reference_state"] == "external_export_download_signed_reference_ready"
    assert signed_reference_body["signed_reference_token_id"]
    assert len(signed_reference_body["signed_reference_token_prefix"]) == 16
    assert signed_reference_body["signed_reference_receipt_id"]
    assert signed_reference_body["signed_reference_replay_policy"] == "single_use"
    assert signed_reference_body["signed_reference_use_count"] == 0
    assert signed_reference_body["signed_reference_max_use_count"] == 1
    assert signed_reference_body["signed_reference_revoked"] is False
    assert signed_reference_body["signed_reference_audit_event_id"]
    assert signed_reference_body["signed_reference_use_endpoint"] == (
        "/api/v1/layer3/handoff/export/download/signed-reference/use"
    )
    assert signed_reference_body["delivery_mode"] == "same_origin_signed_delivery_reference"
    assert signed_reference_body["server_authority"] == (
        "associated_cohort_external_export_download_signed_reference_gate"
    )
    assert signed_reference_body["source_artifact_hash"] == download_body["source_artifact_hash"]
    assert signed_reference_body["source_artifact_size_bytes"] == download_body["source_artifact_size_bytes"]
    assert signed_reference_body["pass_type"] == "associated_cohort"
    assert signed_reference_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"
    assert signed_reference_body["method"] == "descriptive_summary"
    assert signed_reference_body["source_gate"] == "78_COHORT_FREEZE"
    assert signed_reference_body["source_shape"] == "aligned_wide_table"
    assert signed_reference_body["source_dataset_version_ids"] == [
        "dv-api-cohort-aps-001",
        "dv-api-cohort-aps-002",
    ]
    assert signed_reference_body["public_url_enabled"] is False
    assert signed_reference_body["external_object_store_url_enabled"] is False
    assert signed_reference_body["connector_dispatch_enabled"] is False
    assert signed_reference_body["destination_selection_enabled"] is False
    assert signed_reference_body["generic_downstream_dispatch_enabled"] is False
    assert signed_reference_body["package_mutation_enabled"] is False
    assert signed_reference_body["schema_runtime_source_widening_enabled"] is False
    assert signed_reference_body["authority_rail"]["token_authority"] == "server_hmac_with_durable_state"
    assert signed_reference_body["authority_rail"]["durable_state_required"] is True
    assert signed_reference_body["authority_rail"]["replay_policy"] == "single_use"
    assert signed_reference_body["authority_rail"]["configured_secret_present"] is True
    assert signed_reference_body["authority_rail"]["process_restart_invalidates_existing_tokens"] is False
    for forbidden_field in ("download_url", "download_token", "public_url", "signed_url", "connector_run_id"):
        assert forbidden_field not in signed_reference_body

    signed_reference_use = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/use",
        json={"signed_reference_token": signed_reference_body["signed_reference_token"]},
    )
    assert signed_reference_use.status_code == 200, signed_reference_use.text
    assert signed_reference_use.content == expected_delivery_bytes
    assert signed_reference_use.headers["x-layer3-schema-id"] == (
        "layer3.external_export_download_signed_reference_use.v1"
    )
    assert signed_reference_use.headers["x-layer3-delivery-state"] == "external_export_download_delivered"
    assert signed_reference_use.headers["x-layer3-signed-reference-state"] == (
        "external_export_download_signed_reference_delivered"
    )
    assert signed_reference_use.headers["x-layer3-signed-reference-token-id"] == (
        signed_reference_body["signed_reference_token_id"]
    )
    assert signed_reference_use.headers["x-layer3-signed-reference-receipt-id"]
    assert signed_reference_use.headers["x-layer3-signed-reference-replay-policy"] == "single_use"
    assert signed_reference_use.headers["x-layer3-signed-reference-use-count"] == "1"
    assert signed_reference_use.headers["x-layer3-source-artifact-hash"] == download_body["source_artifact_hash"]
    assert "download_url" not in signed_reference_use.headers
    assert "public_url" not in signed_reference_use.headers
    assert "signed_url" not in signed_reference_use.headers

    signed_reference_replay = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/use",
        json={"signed_reference_token": signed_reference_body["signed_reference_token"]},
    )
    assert signed_reference_replay.status_code == 409
    assert signed_reference_replay.json()["error_code"] == "external_export_download_signed_reference_replay_denied"

    signed_reference_regenerate_after_use = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/generate",
        json=cohort_deliver_payload,
    )
    assert signed_reference_regenerate_after_use.status_code == 409
    assert signed_reference_regenerate_after_use.json()["error_code"] == (
        "external_export_download_signed_reference_replay_denied"
    )

    db = client.layer3_session_factory()
    try:
        durable_token = (
            db.query(L3SignedReferenceToken)
            .filter(L3SignedReferenceToken.signed_reference_token_id == signed_reference_body["signed_reference_token_id"])
            .one()
        )
        assert durable_token.token_hash != signed_reference_body["signed_reference_token"]
        assert durable_token.token_prefix == signed_reference_body["signed_reference_token_prefix"]
        assert durable_token.state == "used"
        assert durable_token.replay_policy == "single_use"
        assert durable_token.use_count == 1
        assert durable_token.max_use_count == 1
        durable_snapshot = json.dumps(durable_token.authority_snapshot_json, sort_keys=True)
        assert signed_reference_body["signed_reference_token"] not in durable_snapshot
        assert download_body["source_artifact_ref"] not in durable_snapshot
        receipts = db.query(L3SignedReferenceReceipt).filter(
            L3SignedReferenceReceipt.signed_reference_token_id == durable_token.signed_reference_token_id
        ).all()
        assert len(receipts) == 2
        for receipt in receipts:
            receipt_payload = json.dumps(receipt.receipt_payload_json, sort_keys=True)
            assert signed_reference_body["signed_reference_token"] not in receipt_payload
            assert download_body["source_artifact_ref"] not in receipt_payload
            assert "internal_artifact_ref_bound_by_hash" in receipt_payload
        assert db.query(L3SignedReferenceAuditEvent).filter(
            L3SignedReferenceAuditEvent.signed_reference_token_id == durable_token.signed_reference_token_id
        ).count() == 3
    finally:
        db.close()

    malformed_reference_use = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/use",
        json={"signed_reference_token": "not-a-valid-reference"},
    )
    assert malformed_reference_use.status_code == 400
    assert malformed_reference_use.json()["error_code"] == "external_export_download_signed_reference_malformed"
    extra_field_reference_use = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/use",
        json={
            "signed_reference_token": signed_reference_body["signed_reference_token"],
            "download_url": "https://example.invalid/bundle.json",
        },
    )
    assert extra_field_reference_use.status_code == 400
    assert extra_field_reference_use.json()["error_code"] == (
        "external_export_download_signed_reference_use_scope_not_admitted"
    )

    from app.services import layer3_workbench

    direct_db = client.layer3_session_factory()
    try:
        direct_signed = layer3_workbench.external_export_download_generate_signed_reference(
            direct_db,
            cohort_deliver_payload,
            now_epoch=1000,
        )
        direct_signed_replay = layer3_workbench.external_export_download_generate_signed_reference(
            direct_db,
            cohort_deliver_payload,
            now_epoch=1001,
        )
        assert direct_signed_replay["signed_reference_token"] == direct_signed["signed_reference_token"]
        with pytest.raises(layer3_workbench.Layer3WorkbenchError) as expired:
            layer3_workbench.external_export_download_use_signed_reference(
                direct_db,
                {"signed_reference_token": direct_signed["signed_reference_token"]},
                now_epoch=1200,
            )
        assert expired.value.error_code == "external_export_download_signed_reference_expired"
    finally:
        direct_db.close()

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before_delivery
        packages_after_delivery = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after_delivery == packages_before_delivery
        readiness_state_after_delivery = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json["external_export_download_prepare"]
        )
        assert readiness_state_after_delivery == readiness_state_before_delivery
    finally:
        db.close()
    assert files_under_tmp() == files_before_delivery

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        summary_json_after_delivery = dict(reconciliation.summary_json)
        reconciliation.summary_json = {
            **summary_json_after_delivery,
            "aps_handoff_dispatch": {
                **summary_json_after_delivery["aps_handoff_dispatch"],
                "source_dataset_version_ids": ["dv-api-cohort-aps-stale"],
            },
        }
        db.commit()
    finally:
        db.close()

    stale_dispatch_delivery = client.post(
        "/api/v1/layer3/handoff/export/download/deliver",
        json=cohort_deliver_payload,
    )
    assert stale_dispatch_delivery.status_code == 409
    assert stale_dispatch_delivery.json()["error_code"] == (
        "associated_cohort_external_export_download_prepare_not_admitted"
    )
    assert "source_dataset_version_ids" in stale_dispatch_delivery.json()["blocked_fields"]
    stale_signed_reference_use = client.post(
        "/api/v1/layer3/handoff/export/download/signed-reference/use",
        json={"signed_reference_token": signed_reference_body["signed_reference_token"]},
    )
    assert stale_signed_reference_use.status_code == 409
    assert stale_signed_reference_use.json()["error_code"] == (
        "associated_cohort_external_export_download_prepare_not_admitted"
    )
    assert "source_dataset_version_ids" in stale_signed_reference_use.json()["blocked_fields"]
    assert files_under_tmp() == files_before_delivery

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        reconciliation.summary_json = summary_json_after_delivery
        db.commit()
        assert {
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "aps_packages": db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before_delivery
    finally:
        db.close()


def test_layer3_api_external_export_download_prepare_records_reference_only_descriptor(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-external-export-download-success")
    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=dispatch_payload)
    assert dispatch.status_code == 200, dispatch.json()
    dispatch_body = dispatch.json()
    payload = _external_export_download_prepare_payload(
        request_id="api-external-export-download-success-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
        decision_notes="Prepare a reference-only download descriptor.",
    )

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
    finally:
        db.close()
    files_before = files_under_tmp()

    prepare = client.post("/api/v1/layer3/handoff/export/download/prepare", json=payload)
    assert prepare.status_code == 200, prepare.json()
    body = prepare.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.external_export_download_prepare.v1"
    assert body["status"] == "prepared"
    assert body["session_id"] == session_id
    assert body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert body["pass_run_id"] == selection_body["pass_run_ids"][0]
    assert body["result_review_record_ref"] == review_body["review_record_ref"]
    assert body["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["output_package_ids"] == payload["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_refs"] == commit_body["payload_refs"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
    assert body["package_review_state"] == "package_review_approved"
    assert body["prepare_record_ref"] == prepare_body["prepare_record_ref"]
    assert body["handoff_export_state"] == "handoff_export_prepared"
    assert body["handoff_export_envelope_ref"] == payload["handoff_export_envelope_ref"]
    assert body["handoff_target"] == "internal_export_envelope"
    assert body["export_mode"] == "prepare_only"
    assert body["aps_handoff_record_ref"] == dispatch_body["aps_handoff_record_ref"]
    assert body["aps_handoff_state"] == "aps_handoff_dispatched"
    assert body["aps_handoff_target"] == "aps_evidence_bundle"
    assert body["dispatch_mode"] == "server_side_aps_handoff"
    assert body["aps_output_package_id"] == dispatch_body["aps_output_package_id"]
    assert body["aps_output_package_kind"] == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
    assert body["aps_bundle_ref"] == dispatch_body["aps_bundle_ref"]
    assert body["aps_bundle_id"] == dispatch_body["aps_bundle_id"]
    assert body["aps_schema_id"] == dispatch_body["aps_schema_id"]
    assert body["export_download_target"] == "aps_evidence_bundle_download_reference"
    assert body["download_mode"] == "reference_only_prepare"
    assert body["operator_decision"] == "prepare_external_export_download"
    assert body["external_export_download_state"] == "external_export_download_prepared"
    assert body["source_artifact_ref"] == dispatch_body["aps_bundle_ref"]
    assert body["source_artifact_hash"] == payload["aps_bundle_hash"]
    assert body["source_artifact_size_bytes"] == payload["aps_bundle_size_bytes"]
    assert body["browser_download_enabled"] is False
    assert body["download_url_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["destination_selection_enabled"] is False
    assert body["generic_downstream_dispatch_enabled"] is False
    assert body["downstream_unavailable"] == [
        "browser_download",
        "download_url",
        "connector_dispatch",
        "destination_selection",
        "generic_downstream_dispatch",
    ]
    descriptor = body["external_export_download_descriptor"]
    assert descriptor["descriptor_ref"] == body["export_download_descriptor_ref"]
    assert descriptor["source_artifact_ref"] == dispatch_body["aps_bundle_ref"]
    assert descriptor["browser_download_enabled"] is False
    assert descriptor["download_url_enabled"] is False
    for forbidden_key in (
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "external_target",
        "destination",
        "package_payload",
        "raw_aps_bundle",
        "rewritten_content",
    ):
        assert forbidden_key not in body
        assert forbidden_key not in descriptor

    db = client.layer3_session_factory()
    try:
        assert {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        readiness_state = reconciliation.summary_json["external_export_download_prepare"]
        assert readiness_state["external_export_download_record_ref"] == body["external_export_download_record_ref"]
        assert readiness_state["external_export_download_state"] == "external_export_download_prepared"
        assert readiness_state["external_export_download_descriptor"] == descriptor
    finally:
        db.close()
    assert files_under_tmp() == files_before

    replay = client.post("/api/v1/layer3/handoff/export/download/prepare", json=payload)
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["status"] == "already_prepared"
    assert replay_body["external_export_download_record_ref"] == body["external_export_download_record_ref"]

    same_basis_new_request = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json={**payload, "client_request_id": "api-external-export-download-success-new-request"},
    )
    assert same_basis_new_request.status_code == 409
    assert same_basis_new_request.json()["error_code"] == "external_export_download_prepare_already_recorded"

    conflicting_notes = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json={**payload, "decision_notes": "Changing notes after readiness must fail closed."},
    )
    assert conflicting_notes.status_code == 409
    assert conflicting_notes.json()["error_code"] == "external_export_download_prepare_already_recorded"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["external_export_download"]["state"] == "external_export_download_prepared"
    assert summary_body["external_export_download"]["available"] is False
    assert summary_body["external_export_download"]["export_download_descriptor_ref"] == body["export_download_descriptor_ref"]
    assert summary_body["downstream_unavailable"] == [
        "browser_download",
        "download_url",
        "connector_dispatch",
        "destination_selection",
        "generic_downstream_dispatch",
    ]


def test_layer3_api_package_supersession_preview_inspects_immutable_package_set_without_side_effects(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-package-supersession-preview-success")
    payload = _package_supersession_preview_payload(
        request_id="api-package-supersession-preview-success-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
    )

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        reconciliation_before = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json
        )
    finally:
        db.close()
    files_before = files_under_tmp()

    preview = client.post("/api/v1/layer3/package/mutation/preview", json=payload)
    assert preview.status_code == 200, preview.json()
    body = preview.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.package_supersession_preview.v1"
    assert body["status"] == "previewed"
    assert body["session_id"] == session_id
    assert body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert body["pass_run_id"] == selection_body["pass_run_ids"][0]
    assert body["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["output_package_ids"] == payload["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_refs"] == commit_body["payload_refs"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["operator_decision"] == "preview_package_supersession"
    assert body["package_supersession_preview_mode"] == "package_supersession_preview_only"
    assert body["package_rows"] == [
        {
            "output_package_id": package["output_package_id"],
            "package_kind": package["package_kind"],
            "status": package["status"],
            "payload_ref": package["payload_ref"],
            "payload_hash": package["payload_hash"],
        }
        for package in commit_body["output_packages"]
    ]
    assert body["downstream_dependencies"] == []
    assert body["downstream_dependency_detected"] is False
    assert body["immutable_package_rule_enforced"] is True
    assert body["package_row_mutation_enabled"] is False
    assert body["package_payload_rewrite_enabled"] is False
    assert body["package_supersession_commit_enabled"] is False
    assert body["database_write_enabled"] is False
    assert body["filesystem_write_enabled"] is False
    assert body["broad_package_mutation_enabled"] is False
    assert body["source_widening_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_url_enabled"] is False
    assert body["qualitative_hybrid_rag_execution_enabled"] is False
    assert body["downstream_unavailable"] == [
        "package_row_mutation",
        "package_payload_rewrite",
        "package_supersession_commit",
        "provider_public_url",
        "connector_destination_dispatch",
        "source_upload_expansion",
        "broad_qualitative_hybrid_rag_execution",
        "full_mockup_activation",
    ]
    for forbidden_key in (
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "rebuild_package",
        "provider_public_url",
        "public_url",
        "signed_url",
        "download_url",
        "connector_key",
        "connector_run_id",
    ):
        assert forbidden_key not in body

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation_after = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json
        )
        assert reconciliation_after == reconciliation_before
        assert "package_supersession_preview" not in reconciliation_after
    finally:
        db.close()
    assert files_under_tmp() == files_before

    replay = client.post("/api/v1/layer3/package/mutation/preview", json=payload)
    assert replay.status_code == 200, replay.json()
    assert replay.json()["package_supersession_preview_hash"] == body["package_supersession_preview_hash"]
    assert replay.json()["package_set_hash"] == body["package_set_hash"]

    reordered = client.post(
        "/api/v1/layer3/package/mutation/preview",
        json={
            **payload,
            "client_request_id": "api-package-supersession-preview-reordered",
            "output_package_ids": list(reversed(payload["output_package_ids"])),
            "package_kinds": list(reversed(payload["package_kinds"])),
            "payload_refs": list(reversed(payload["payload_refs"])),
            "payload_hashes": list(reversed(payload["payload_hashes"])),
        },
    )
    assert reordered.status_code == 200, reordered.json()
    assert reordered.json()["output_package_ids"] == payload["output_package_ids"]
    assert reordered.json()["package_supersession_preview_hash"] == body["package_supersession_preview_hash"]


def test_layer3_api_package_supersession_preview_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/package/mutation/preview",
        json={"client_request_id": "api-package-supersession-preview-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) >= {
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_preview_hash",
        "operator_decision",
    }

    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(client, tmp_path, request_id="api-package-supersession-preview-prechecks")
    base_payload = _package_supersession_preview_payload(
        request_id="api-package-supersession-preview-prechecks-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
    )
    missing_downstream_ref = dict(base_payload)
    missing_downstream_ref.pop("package_review_submit_record_ref")
    cases = [
        (
            {**base_payload, "package_payload": {"unsafe": True}},
            400,
            "package_supersession_preview_scope_not_admitted",
        ),
        (
            {**base_payload, "provider_public_url": "https://example.invalid/package.json"},
            400,
            "package_supersession_preview_scope_not_admitted",
        ),
        (
            {**base_payload, "operator_decision": "commit_package_supersession"},
            400,
            "unsupported_package_supersession_preview_decision",
        ),
        (
            {**base_payload, "package_review_preview_hash": "stale-preview-hash"},
            409,
            "package_supersession_preview_package_review_preview_hash_mismatch",
        ),
        (
            {**base_payload, "payload_hashes": ["stale-hash", *base_payload["payload_hashes"][1:]]},
            409,
            "package_supersession_preview_payload_hashes_mismatch",
        ),
        (
            missing_downstream_ref,
            409,
            "package_supersession_preview_package_review_submit_record_ref_required",
        ),
        (
            {**base_payload, "package_review_submit_record_ref": "stale-submit-ref"},
            409,
            "package_supersession_preview_package_review_submit_record_ref_mismatch",
        ),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/package/mutation/preview", json=payload)
        assert response.status_code == expected_status, response.json()
        assert response.json()["error_code"] == expected_error

    unknown_extra = client.post(
        "/api/v1/layer3/package/mutation/preview",
        json={**base_payload, "package_supersession_commit": True},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "package_supersession_commit"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "package_supersession_preview" not in reconciliation.summary_json
    finally:
        db.close()


def test_layer3_api_replacement_package_set_authority_records_without_package_row_or_payload_mutation(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-replacement-package-authority-success")
    preview_payload = _package_supersession_preview_payload(
        request_id="api-replacement-package-authority-success-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
    )
    preview = client.post("/api/v1/layer3/package/mutation/preview", json=preview_payload)
    assert preview.status_code == 200, preview.json()
    payload = _replacement_package_set_authority_payload(
        request_id="api-replacement-package-authority-success-record",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        commit_body=commit_body,
        source_package_set_hash=preview.json()["package_set_hash"],
    )

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
            "replacement_authorities": db.query(L3ReplacementPackageSetAuthority).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        reconciliation_before = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json
        )
    finally:
        db.close()
    files_before = files_under_tmp()

    record = client.post("/api/v1/layer3/package/replacement-set/record", json=payload)
    assert record.status_code == 200, record.json()
    body = record.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.replacement_package_set_authority.v1"
    assert body["status"] == "recorded"
    assert body["session_id"] == session_id
    assert body["source_package_set_hash"] == payload["source_package_set_hash"]
    assert body["source_output_package_ids"] == payload["source_output_package_ids"]
    assert body["source_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["source_payload_refs"] == payload["source_payload_refs"]
    assert body["source_payload_hashes"] == payload["source_payload_hashes"]
    assert body["replacement_package_set_id"] == payload["replacement_package_set_id"]
    assert body["replacement_package_set_hash"] == payload["replacement_package_set_hash"]
    assert body["replacement_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["replacement_payload_refs"] == payload["replacement_payload_refs"]
    assert body["replacement_payload_hashes"] == payload["replacement_payload_hashes"]
    assert body["authority_basis_hash"] == payload["authority_basis_hash"]
    assert body["operator_decision"] == "record_replacement_package_set_authority"
    assert body["replacement_package_set_authority_mode"] == "replacement_package_set_authority"
    assert body["source_gate"] == "127_PACKAGE_REPLACEMENT_SET_FREEZE"
    assert body["authority_record_persisted"] is True
    assert body["package_row_mutation_enabled"] is False
    assert body["package_payload_write_enabled"] is False
    assert body["package_supersession_commit_enabled"] is False
    assert body["broad_package_mutation_enabled"] is False
    assert body["source_widening_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_url_enabled"] is False
    assert body["qualitative_hybrid_rag_execution_enabled"] is False
    assert body["frontend_only_durable_state_enabled"] is False
    assert body["downstream_unavailable"] == [
        "package_row_mutation",
        "package_payload_rewrite",
        "package_supersession_commit",
        "provider_public_url",
        "connector_destination_dispatch",
        "source_upload_expansion",
        "broad_qualitative_hybrid_rag_execution",
        "full_mockup_activation",
    ]
    assert body["authority_snapshot"]["negative_invariants"]["creates_l3_output_package"] is False
    assert body["authority_snapshot"]["negative_invariants"]["writes_package_payload"] is False

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
            "replacement_authorities": db.query(L3ReplacementPackageSetAuthority).count(),
        } == {**counts_before, "replacement_authorities": counts_before["replacement_authorities"] + 1}
        authority = db.query(L3ReplacementPackageSetAuthority).one()
        assert authority.replacement_package_set_authority_id == body["replacement_package_set_authority_id"]
        assert authority.authority_basis_hash == payload["authority_basis_hash"]
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation_after = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json
        )
        assert reconciliation_after == reconciliation_before
    finally:
        db.close()
    assert files_under_tmp() == files_before

    replay = client.post("/api/v1/layer3/package/replacement-set/record", json=payload)
    assert replay.status_code == 200, replay.json()
    assert replay.json()["status"] == "already_recorded"
    assert replay.json()["replacement_package_set_authority_id"] == body["replacement_package_set_authority_id"]

    same_basis = client.post(
        "/api/v1/layer3/package/replacement-set/record",
        json={**payload, "client_request_id": "api-replacement-package-authority-same-basis"},
    )
    assert same_basis.status_code == 200, same_basis.json()
    assert same_basis.json()["status"] == "already_recorded"
    db = client.layer3_session_factory()
    try:
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
    finally:
        db.close()


def test_layer3_api_replacement_package_set_authority_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/package/replacement-set/record",
        json={"client_request_id": "api-replacement-package-authority-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) >= {
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "operator_decision",
    }

    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-replacement-package-authority-prechecks")
    preview_payload = _package_supersession_preview_payload(
        request_id="api-replacement-package-authority-prechecks-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
    )
    preview = client.post("/api/v1/layer3/package/mutation/preview", json=preview_payload)
    assert preview.status_code == 200, preview.json()
    base_payload = _replacement_package_set_authority_payload(
        request_id="api-replacement-package-authority-prechecks-record",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        commit_body=commit_body,
        source_package_set_hash=preview.json()["package_set_hash"],
    )
    cases = [
        (
            {**base_payload, "package_payload": {"unsafe": True}},
            400,
            "replacement_package_set_authority_scope_not_admitted",
        ),
        (
            {**base_payload, "operator_decision": "commit_package_supersession"},
            400,
            "unsupported_replacement_package_set_authority_decision",
        ),
        (
            {**base_payload, "source_package_set_hash": "stale-source-package-set-hash"},
            409,
            "replacement_package_set_authority_source_package_set_hash_mismatch",
        ),
        (
            {
                **base_payload,
                "source_payload_hashes": ["stale-hash", *base_payload["source_payload_hashes"][1:]],
            },
            409,
            "replacement_package_set_authority_source_payload_hashes_mismatch",
        ),
        (
            {**base_payload, "replacement_payload_refs": base_payload["source_payload_refs"]},
            409,
            "replacement_package_set_authority_reuses_source_payload_ref",
        ),
        (
            {**base_payload, "replacement_package_set_hash": "stale-replacement-package-set-hash"},
            409,
            "replacement_package_set_authority_replacement_package_set_hash_mismatch",
        ),
        (
            {**base_payload, "authority_basis_hash": "stale-authority-basis-hash"},
            409,
            "replacement_package_set_authority_basis_hash_mismatch",
        ),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/package/replacement-set/record", json=payload)
        assert response.status_code == expected_status, response.json()
        assert response.json()["error_code"] == expected_error

    unknown_extra = client.post(
        "/api/v1/layer3/package/replacement-set/record",
        json={**base_payload, "replacement_output_package_ids": ["not-admitted"]},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "replacement_output_package_ids"]
        for item in unknown_extra.json()["detail"]
    )
    db = client.layer3_session_factory()
    try:
        assert db.query(L3ReplacementPackageSetAuthority).count() == 0
        assert db.query(L3OutputPackage).count() == 3
    finally:
        db.close()


def test_layer3_api_package_supersession_commit_records_lineage_without_package_mutation(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-package-supersession-commit-success")
    preview_payload = _package_supersession_preview_payload(
        request_id="api-package-supersession-commit-success-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
    )
    preview = client.post("/api/v1/layer3/package/mutation/preview", json=preview_payload)
    assert preview.status_code == 200, preview.json()
    authority_payload = _replacement_package_set_authority_payload(
        request_id="api-package-supersession-commit-success-authority",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        commit_body=commit_body,
        source_package_set_hash=preview.json()["package_set_hash"],
    )
    authority = client.post("/api/v1/layer3/package/replacement-set/record", json=authority_payload)
    assert authority.status_code == 200, authority.json()
    payload = _package_supersession_commit_payload(
        request_id="api-package-supersession-commit-success-commit",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        commit_body=commit_body,
        supersession_preview_body=preview.json(),
        replacement_authority_body=authority.json(),
    )

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
            "replacement_authorities": db.query(L3ReplacementPackageSetAuthority).count(),
            "supersession_commits": db.query(L3PackageSupersessionCommit).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        reconciliation_before = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json
        )
    finally:
        db.close()
    files_before = files_under_tmp()

    record = client.post("/api/v1/layer3/package/supersession/commit", json=payload)
    assert record.status_code == 200, record.json()
    body = record.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.package_supersession_commit.v1"
    assert body["status"] == "committed"
    assert body["session_id"] == session_id
    assert body["replacement_package_set_authority_id"] == authority.json()["replacement_package_set_authority_id"]
    assert body["package_supersession_preview_hash"] == preview.json()["package_supersession_preview_hash"]
    assert body["source_package_set_hash"] == preview.json()["package_set_hash"]
    assert body["source_output_package_ids"] == payload["source_output_package_ids"]
    assert body["source_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["source_payload_refs"] == payload["source_payload_refs"]
    assert body["source_payload_hashes"] == payload["source_payload_hashes"]
    assert body["replacement_package_set_id"] == authority.json()["replacement_package_set_id"]
    assert body["replacement_package_set_hash"] == authority.json()["replacement_package_set_hash"]
    assert body["replacement_package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["replacement_payload_refs"] == authority.json()["replacement_payload_refs"]
    assert body["replacement_payload_hashes"] == authority.json()["replacement_payload_hashes"]
    assert body["replacement_authority_basis_hash"] == authority.json()["authority_basis_hash"]
    assert body["downstream_dependency_hash"] == payload["downstream_dependency_hash"]
    assert body["commit_basis_hash"] == payload["commit_basis_hash"]
    assert body["operator_decision"] == "commit_package_supersession"
    assert body["package_supersession_commit_mode"] == "package_supersession_commit_entry"
    assert body["source_gate"] == "126_PACKAGE_COMMIT_FREEZE"
    assert body["package_supersession_commit_record_persisted"] is True
    assert body["package_row_mutation_enabled"] is False
    assert body["package_payload_write_enabled"] is False
    assert body["l3_output_package_write_enabled"] is False
    assert body["broad_package_mutation_enabled"] is False
    assert body["source_widening_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["provider_public_url_enabled"] is False
    assert body["qualitative_hybrid_rag_execution_enabled"] is False
    assert body["frontend_only_durable_state_enabled"] is False
    assert body["downstream_unavailable"] == [
        "package_row_mutation",
        "package_payload_rewrite",
        "broad_package_mutation_reconstruction",
        "provider_public_url",
        "connector_destination_dispatch",
        "source_upload_expansion",
        "broad_qualitative_hybrid_rag_execution",
        "full_mockup_activation",
    ]
    assert body["commit_snapshot"]["negative_invariants"]["updates_l3_output_package"] is False
    assert body["commit_snapshot"]["negative_invariants"]["writes_package_payload"] is False

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
            "replacement_authorities": db.query(L3ReplacementPackageSetAuthority).count(),
            "supersession_commits": db.query(L3PackageSupersessionCommit).count(),
        } == {**counts_before, "supersession_commits": counts_before["supersession_commits"] + 1}
        commit = db.query(L3PackageSupersessionCommit).one()
        assert commit.package_supersession_commit_id == body["package_supersession_commit_id"]
        assert commit.commit_basis_hash == payload["commit_basis_hash"]
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation_after = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json
        )
        assert reconciliation_after == reconciliation_before
    finally:
        db.close()
    assert files_under_tmp() == files_before

    replay = client.post("/api/v1/layer3/package/supersession/commit", json=payload)
    assert replay.status_code == 200, replay.json()
    assert replay.json()["status"] == "already_committed"
    assert replay.json()["package_supersession_commit_id"] == body["package_supersession_commit_id"]

    same_basis = client.post(
        "/api/v1/layer3/package/supersession/commit",
        json={**payload, "client_request_id": "api-package-supersession-commit-same-basis"},
    )
    assert same_basis.status_code == 200, same_basis.json()
    assert same_basis.json()["status"] == "already_committed"
    db = client.layer3_session_factory()
    try:
        assert db.query(L3PackageSupersessionCommit).count() == 1
    finally:
        db.close()


def test_layer3_api_package_supersession_commit_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/package/supersession/commit",
        json={"client_request_id": "api-package-supersession-commit-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) >= {
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_authority_id",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "replacement_authority_basis_hash",
        "downstream_dependency_hash",
        "commit_basis_hash",
        "operator_decision",
    }

    (
        session_id,
        _preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-package-supersession-commit-prechecks")
    preview_payload = _package_supersession_preview_payload(
        request_id="api-package-supersession-commit-prechecks-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
    )
    preview = client.post("/api/v1/layer3/package/mutation/preview", json=preview_payload)
    assert preview.status_code == 200, preview.json()
    authority_payload = _replacement_package_set_authority_payload(
        request_id="api-package-supersession-commit-prechecks-authority",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        commit_body=commit_body,
        source_package_set_hash=preview.json()["package_set_hash"],
    )
    authority = client.post("/api/v1/layer3/package/replacement-set/record", json=authority_payload)
    assert authority.status_code == 200, authority.json()
    base_payload = _package_supersession_commit_payload(
        request_id="api-package-supersession-commit-prechecks-commit",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        commit_body=commit_body,
        supersession_preview_body=preview.json(),
        replacement_authority_body=authority.json(),
    )
    cases = [
        (
            {**base_payload, "package_payload": {"unsafe": True}},
            400,
            "package_supersession_commit_scope_not_admitted",
        ),
        (
            {**base_payload, "replacement_output_package_ids": ["not-admitted"]},
            400,
            "package_supersession_commit_scope_not_admitted",
        ),
        (
            {**base_payload, "operator_decision": "preview_package_supersession"},
            400,
            "unsupported_package_supersession_commit_decision",
        ),
        (
            {**base_payload, "package_supersession_preview_hash": "stale-preview-hash"},
            409,
            "package_supersession_commit_preview_hash_mismatch",
        ),
        (
            {**base_payload, "source_package_set_hash": "stale-source-package-set-hash"},
            409,
            "package_supersession_commit_source_package_set_hash_mismatch",
        ),
        (
            {**base_payload, "replacement_package_set_hash": "stale-replacement-package-set-hash"},
            409,
            "package_supersession_commit_replacement_package_set_hash_mismatch",
        ),
        (
            {**base_payload, "downstream_dependency_hash": "stale-downstream-dependency-hash"},
            409,
            "package_supersession_commit_downstream_dependency_hash_mismatch",
        ),
        (
            {**base_payload, "commit_basis_hash": "stale-commit-basis-hash"},
            409,
            "package_supersession_commit_basis_hash_mismatch",
        ),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/package/supersession/commit", json=payload)
        assert response.status_code == expected_status, response.json()
        assert response.json()["error_code"] == expected_error

    unknown_extra = client.post(
        "/api/v1/layer3/package/supersession/commit",
        json={**base_payload, "unexpected_runtime_widening": True},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden" and item.get("loc") == ["body", "unexpected_runtime_widening"]
        for item in unknown_extra.json()["detail"]
    )
    db = client.layer3_session_factory()
    try:
        assert db.query(L3PackageSupersessionCommit).count() == 0
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(L3ReplacementPackageSetAuthority).count() == 1
    finally:
        db.close()


def test_layer3_api_package_supersession_preview_detects_downstream_dependencies(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    (
        session_id,
        approval_body,
        selection_body,
        start_body,
        review_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_body,
        readiness_body,
    ) = _prepare_cohort_connector_dispatch_record(
        client,
        tmp_path,
        monkeypatch,
        request_id="api-package-supersession-preview-downstream",
    )
    connector_payload = _connector_dispatch_record_payload(
        request_id="api-package-supersession-preview-downstream-connector",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
        readiness_body=readiness_body,
    )
    connector = client.post("/api/v1/layer3/handoff/connector/record", json=connector_payload)
    assert connector.status_code == 200, connector.json()
    connector_body = connector.json()
    payload = _package_supersession_preview_payload(
        request_id="api-package-supersession-preview-downstream-preview",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
        readiness_body=readiness_body,
        connector_body=connector_body,
    )

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()

    preview = client.post("/api/v1/layer3/package/mutation/preview", json=payload)
    assert preview.status_code == 200, preview.json()
    body = preview.json()
    assert body["downstream_dependency_detected"] is True
    assert [dependency["state_key"] for dependency in body["downstream_dependencies"]] == [
        "package_review_submit",
        "handoff_export_prepare",
        "aps_handoff_dispatch",
        "external_export_download_prepare",
        "connector_dispatch_record",
    ]
    assert body["package_supersession_commit_enabled"] is False

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
    finally:
        db.close()

    missing_handoff_ref = dict(payload)
    missing_handoff_ref.pop("handoff_export_record_ref")
    missing_handoff = client.post("/api/v1/layer3/package/mutation/preview", json=missing_handoff_ref)
    assert missing_handoff.status_code == 409
    assert missing_handoff.json()["error_code"] == "package_supersession_preview_handoff_export_record_ref_required"

    stale_connector_ref = client.post(
        "/api/v1/layer3/package/mutation/preview",
        json={**payload, "connector_dispatch_record_ref": "stale-connector-record"},
    )
    assert stale_connector_ref.status_code == 409
    assert (
        stale_connector_ref.json()["error_code"]
        == "package_supersession_preview_connector_dispatch_record_ref_mismatch"
    )


def test_layer3_api_connector_dispatch_record_records_internal_receipt_without_side_effects(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    (
        session_id,
        approval_body,
        selection_body,
        _start_body,
        review_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_body,
        readiness_body,
    ) = _prepare_cohort_connector_dispatch_record(
        client,
        tmp_path,
        monkeypatch,
        request_id="api-connector-dispatch-record-success",
    )
    payload = _connector_dispatch_record_payload(
        request_id="api-connector-dispatch-record-success-record",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
        readiness_body=readiness_body,
        decision_notes="Record internal connector dispatch intent only.",
    )

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
    finally:
        db.close()
    files_before = files_under_tmp()

    record = client.post("/api/v1/layer3/handoff/connector/record", json=payload)
    assert record.status_code == 200, record.json()
    body = record.json()
    _assert_common_response_envelope(body)
    assert body["schema_id"] == "layer3.connector_dispatch_record.v1"
    assert body["status"] == "recorded"
    assert body["session_id"] == session_id
    assert body["analysis_plan_id"] == approval_body["analysis_plan_id"]
    assert body["pass_run_id"] == selection_body["pass_run_ids"][0]
    assert body["result_review_record_ref"] == review_body["review_record_ref"]
    assert body["package_review_preview_hash"] == commit_body["package_review_preview_hash"]
    assert body["reconciliation_record_id"] == commit_body["reconciliation_record_id"]
    assert body["output_package_ids"] == payload["output_package_ids"]
    assert body["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert body["payload_refs"] == commit_body["payload_refs"]
    assert body["payload_hashes"] == commit_body["payload_hashes"]
    assert body["package_review_submit_record_ref"] == submit_body["submit_record_ref"]
    assert body["package_review_state"] == "package_review_approved"
    assert body["prepare_record_ref"] == prepare_body["prepare_record_ref"]
    assert body["handoff_export_state"] == "handoff_export_prepared"
    assert body["aps_handoff_record_ref"] == dispatch_body["aps_handoff_record_ref"]
    assert body["aps_handoff_state"] == "aps_handoff_dispatched"
    assert body["aps_handoff_target"] == "aps_evidence_bundle"
    assert body["aps_output_package_id"] == dispatch_body["aps_output_package_id"]
    assert body["aps_output_package_kind"] == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
    assert body["aps_bundle_ref"] == dispatch_body["aps_bundle_ref"]
    assert body["source_artifact_hash"] == readiness_body["source_artifact_hash"]
    assert body["source_artifact_size_bytes"] == readiness_body["source_artifact_size_bytes"]
    assert body["external_export_download_record_ref"] == readiness_body["external_export_download_record_ref"]
    assert body["external_export_download_state"] == "external_export_download_prepared"
    assert body["external_export_download_descriptor_ref"] == readiness_body["export_download_descriptor_ref"]
    assert body["delivery_mode"] == "same_origin_artifact_stream"
    assert body["operator_decision"] == "record_internal_connector_dispatch"
    assert body["dispatch_mode"] == "internal_dispatch_record_only"
    assert body["connector_dispatch_record_state"] == "connector_dispatch_recorded"
    assert body["internal_dispatch_record_only_enabled"] is True
    assert body["external_connector_invocation_enabled"] is False
    assert body["destination_write_enabled"] is False
    assert body["connector_run_created"] is False
    assert body["provider_public_url_enabled"] is False
    assert body["package_mutation_enabled"] is False
    assert body["source_widening_enabled"] is False
    assert body["qualitative_hybrid_rag_execution_enabled"] is False
    assert body["downstream_unavailable"] == [
        "external_connector_invocation",
        "destination_write",
        "connector_run_creation",
        "provider_public_url",
        "package_mutation_reconstruction",
        "source_upload_expansion",
        "broad_qualitative_hybrid_rag_execution",
        "full_mockup_activation",
    ]
    for forbidden_key in (
        "connector_key",
        "connector_run_id",
        "destination_id",
        "destination_url",
        "provider_url",
        "public_url",
        "signed_url",
        "download_url",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
    ):
        assert forbidden_key not in body

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_runs": db.query(AnalysisRun).count(),
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        connector_state = reconciliation.summary_json["connector_dispatch_record"]
        assert connector_state["schema_id"] == "layer3.connector_dispatch_record_state.v1"
        assert connector_state["connector_dispatch_record_ref"] == body["connector_dispatch_record_ref"]
        assert connector_state["connector_dispatch_record_state"] == "connector_dispatch_recorded"
        assert connector_state["dispatch_mode"] == "internal_dispatch_record_only"
        assert connector_state["record_source_gate"] == "121_CONNECTOR_DISPATCH_ENTRY_FREEZE"
        assert connector_state["external_connector_invocation_enabled"] is False
        assert connector_state["destination_write_enabled"] is False
        assert connector_state["connector_run_created"] is False
    finally:
        db.close()
    assert files_under_tmp() == files_before

    replay = client.post("/api/v1/layer3/handoff/connector/record", json=payload)
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["status"] == "already_recorded"
    assert replay_body["connector_dispatch_record_ref"] == body["connector_dispatch_record_ref"]

    same_basis_new_request = client.post(
        "/api/v1/layer3/handoff/connector/record",
        json={**payload, "client_request_id": "api-connector-dispatch-record-new-request"},
    )
    assert same_basis_new_request.status_code == 409
    assert same_basis_new_request.json()["error_code"] == "connector_dispatch_record_already_recorded"

    conflicting_notes = client.post(
        "/api/v1/layer3/handoff/connector/record",
        json={**payload, "decision_notes": "Changing notes after connector record must fail closed."},
    )
    assert conflicting_notes.status_code == 409
    assert conflicting_notes.json()["error_code"] == "connector_dispatch_record_already_recorded"


def test_layer3_api_connector_dispatch_record_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    missing = client.post(
        "/api/v1/layer3/handoff/connector/record",
        json={"client_request_id": "api-connector-dispatch-record-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) >= {
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "result_review_record_ref",
        "package_review_preview_hash",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "prepare_record_ref",
        "handoff_export_state",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_handoff_target",
        "aps_output_package_id",
        "aps_output_package_kind",
        "aps_bundle_ref",
        "source_artifact_hash",
        "source_artifact_size_bytes",
        "external_export_download_record_ref",
        "external_export_download_state",
        "delivery_mode",
        "operator_decision",
    }

    (
        session_id,
        approval_body,
        selection_body,
        _start_body,
        review_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_body,
        readiness_body,
    ) = _prepare_cohort_connector_dispatch_record(
        client,
        tmp_path,
        monkeypatch,
        request_id="api-connector-dispatch-record-prechecks",
    )
    base_payload = _connector_dispatch_record_payload(
        request_id="api-connector-dispatch-record-prechecks-record",
        session_id=session_id,
        approval_body=approval_body,
        selection_body=selection_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
        readiness_body=readiness_body,
    )

    cases = [
        (
            {**base_payload, "connector_key": "external-connector"},
            400,
            "connector_dispatch_record_scope_not_admitted",
        ),
        (
            {**base_payload, "delivery_mode": "provider_public_url"},
            400,
            "connector_dispatch_record_delivery_mode_not_admitted",
        ),
        (
            {**base_payload, "operator_decision": "dispatch_connector"},
            400,
            "unsupported_connector_dispatch_record_decision",
        ),
        (
            {**base_payload, "source_artifact_hash": "stale-hash"},
            409,
            "connector_dispatch_record_source_artifact_hash_mismatch",
        ),
        (
            {**base_payload, "external_export_download_record_ref": "stale-download-ref"},
            409,
            "connector_dispatch_record_external_export_download_record_ref_mismatch",
        ),
        (
            {**base_payload, "payload_hashes": ["stale-hash", *base_payload["payload_hashes"][1:]]},
            409,
            "connector_dispatch_record_payload_hashes_mismatch",
        ),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/handoff/connector/record", json=payload)
        assert response.status_code == expected_status, response.json()
        assert response.json()["error_code"] == expected_error

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "connector_dispatch_record" not in reconciliation.summary_json
        summary_before = dict(reconciliation.summary_json)
        reconciliation.summary_json = {
            key: value
            for key, value in summary_before.items()
            if key != "external_export_download_prepare"
        }
        db.commit()
    finally:
        db.close()

    not_prepared = client.post("/api/v1/layer3/handoff/connector/record", json=base_payload)
    assert not_prepared.status_code == 409
    assert not_prepared.json()["error_code"] == "connector_dispatch_record_requires_external_export_download_prepare"

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        reconciliation.summary_json = summary_before
        db.commit()
    finally:
        db.close()

    unknown_extra = client.post(
        "/api/v1/layer3/handoff/connector/record",
        json={**base_payload, "provider_destination_url": "https://example.invalid/bundle.json"},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "provider_destination_url"]
        for item in unknown_extra.json()["detail"]
    )

    (
        non_cohort_session_id,
        non_cohort_preview_body,
        non_cohort_approval_body,
        non_cohort_selection_body,
        non_cohort_start_body,
        non_cohort_review_body,
        _non_cohort_package_preview_body,
        non_cohort_commit_body,
        non_cohort_submit_body,
        non_cohort_prepare_body,
        non_cohort_dispatch_payload,
    ) = _prepare_aps_handoff_dispatch(
        client,
        tmp_path,
        request_id="api-connector-dispatch-record-non-cohort",
    )
    non_cohort_dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=non_cohort_dispatch_payload)
    assert non_cohort_dispatch.status_code == 200, non_cohort_dispatch.json()
    non_cohort_dispatch_body = non_cohort_dispatch.json()
    non_cohort_readiness = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json=_external_export_download_prepare_payload(
            request_id="api-connector-dispatch-record-non-cohort-download",
            session_id=non_cohort_session_id,
            preview_body=non_cohort_preview_body,
            approval_body=non_cohort_approval_body,
            selection_body=non_cohort_selection_body,
            start_body=non_cohort_start_body,
            review_body=non_cohort_review_body,
            commit_body=non_cohort_commit_body,
            submit_body=non_cohort_submit_body,
            prepare_body=non_cohort_prepare_body,
            dispatch_body=non_cohort_dispatch_body,
        ),
    )
    assert non_cohort_readiness.status_code == 200, non_cohort_readiness.json()
    non_cohort_payload = _connector_dispatch_record_payload(
        request_id="api-connector-dispatch-record-non-cohort-record",
        session_id=non_cohort_session_id,
        approval_body=non_cohort_approval_body,
        selection_body=non_cohort_selection_body,
        review_body=non_cohort_review_body,
        commit_body=non_cohort_commit_body,
        submit_body=non_cohort_submit_body,
        prepare_body=non_cohort_prepare_body,
        dispatch_body=non_cohort_dispatch_body,
        readiness_body=non_cohort_readiness.json(),
    )
    non_cohort_record = client.post("/api/v1/layer3/handoff/connector/record", json=non_cohort_payload)
    assert non_cohort_record.status_code == 409
    assert non_cohort_record.json()["error_code"] == "connector_dispatch_record_source_not_admitted"


def test_layer3_api_external_export_download_prepare_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json={"client_request_id": "api-external-export-download-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) >= {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_output_package_id",
        "aps_bundle_ref",
        "export_download_target",
        "download_mode",
        "operator_decision",
    }

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-external-export-download-prechecks")
    not_dispatched_payload = {
        **dispatch_payload,
        "aps_handoff_record_ref": "missing-aps-dispatch-ref",
        "aps_handoff_state": "aps_handoff_dispatched",
        "aps_output_package_id": "missing-aps-output-package",
        "aps_output_package_kind": PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
        "aps_bundle_ref": str(tmp_path / "missing-aps-bundle.json"),
        "aps_bundle_id": "missing-aps-bundle",
        "aps_schema_id": "layer3.aps_evidence_bundle_handoff.v1",
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "operator_decision": "prepare_external_export_download",
    }
    not_dispatched = client.post("/api/v1/layer3/handoff/export/download/prepare", json=not_dispatched_payload)
    assert not_dispatched.status_code == 409
    assert not_dispatched.json()["error_code"] == "external_export_download_prepare_requires_aps_handoff_dispatch"

    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=dispatch_payload)
    assert dispatch.status_code == 200, dispatch.json()
    dispatch_body = dispatch.json()
    base_payload = _external_export_download_prepare_payload(
        request_id="api-external-export-download-prechecks-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
    )

    cases = [
        ({**base_payload, "handoff_target": "external_export"}, 400, "external_export_download_prepare_handoff_target_not_admitted"),
        ({**base_payload, "export_mode": "download"}, 400, "external_export_download_prepare_export_mode_not_admitted"),
        ({**base_payload, "aps_handoff_target": "connector_run"}, 400, "external_export_download_prepare_aps_target_not_admitted"),
        ({**base_payload, "dispatch_mode": "connector_dispatch"}, 400, "external_export_download_prepare_dispatch_mode_not_admitted"),
        ({**base_payload, "export_download_target": "public_download_url"}, 400, "external_export_download_prepare_target_not_admitted"),
        ({**base_payload, "download_mode": "browser_download"}, 400, "external_export_download_prepare_download_mode_not_admitted"),
        ({**base_payload, "operator_decision": "download"}, 400, "unsupported_external_export_download_prepare_decision"),
        ({**base_payload, "download_url": "https://example.invalid/bundle.json"}, 400, "external_export_download_prepare_scope_not_admitted"),
        ({**base_payload, "result_review_record_ref": "stale-review-ref"}, 409, "external_export_download_prepare_result_review_mismatch"),
        ({**base_payload, "package_review_preview_hash": "stale-package-preview"}, 409, "external_export_download_prepare_preview_mismatch"),
        ({**base_payload, "package_review_submit_record_ref": "stale-submit-ref"}, 409, "external_export_download_prepare_submit_ref_mismatch"),
        ({**base_payload, "prepare_record_ref": "stale-prepare-ref"}, 409, "external_export_download_prepare_prepare_ref_mismatch"),
        ({**base_payload, "handoff_export_envelope_ref": "stale-envelope-ref"}, 409, "external_export_download_prepare_envelope_ref_mismatch"),
        ({**base_payload, "aps_handoff_record_ref": "stale-aps-ref"}, 409, "external_export_download_prepare_aps_dispatch_mismatch"),
        ({**base_payload, "output_package_ids": ["pkg-stale", *base_payload["output_package_ids"][1:]]}, 409, "external_export_download_prepare_package_ids_mismatch"),
        ({**base_payload, "package_kinds": ["canonical_internal"]}, 409, "external_export_download_prepare_package_kinds_mismatch"),
        ({**base_payload, "payload_refs": ["stale-ref", *base_payload["payload_refs"][1:]]}, 409, "external_export_download_prepare_payload_refs_mismatch"),
        ({**base_payload, "payload_hashes": ["stale-hash", *base_payload["payload_hashes"][1:]]}, 409, "external_export_download_prepare_payload_hashes_mismatch"),
        ({**base_payload, "package_review_state": "package_review_blocked"}, 409, "external_export_download_prepare_requires_approved_package_review"),
        ({**base_payload, "handoff_export_state": "handoff_export_held"}, 409, "external_export_download_prepare_requires_prepared_handoff_export"),
        ({**base_payload, "aps_handoff_state": "aps_handoff_blocked"}, 409, "external_export_download_prepare_requires_aps_handoff_dispatch"),
        ({**base_payload, "aps_output_package_id": "stale-aps-output"}, 409, "external_export_download_prepare_aps_output_package_id_mismatch"),
        ({**base_payload, "aps_output_package_kind": "canonical_internal"}, 409, "external_export_download_prepare_aps_package_kind_mismatch"),
        ({**base_payload, "aps_bundle_ref": "stale-aps-bundle-ref"}, 409, "external_export_download_prepare_aps_bundle_ref_mismatch"),
        ({**base_payload, "aps_bundle_id": "stale-aps-bundle-id"}, 409, "external_export_download_prepare_aps_bundle_id_mismatch"),
        ({**base_payload, "aps_schema_id": "stale-schema"}, 409, "external_export_download_prepare_aps_schema_id_mismatch"),
        ({**base_payload, "aps_bundle_hash": "stale-hash"}, 409, "external_export_download_prepare_aps_bundle_hash_mismatch"),
        (
            {**base_payload, "aps_bundle_size_bytes": base_payload["aps_bundle_size_bytes"] + 1},
            409,
            "external_export_download_prepare_aps_bundle_size_mismatch",
        ),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/handoff/export/download/prepare", json=payload)
        assert response.status_code == expected_status, response.json()
        assert response.json()["error_code"] == expected_error

    unknown_extra = client.post(
        "/api/v1/layer3/handoff/export/download/prepare",
        json={**base_payload, "provider_public_url": "https://example.invalid/bundle.json"},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "provider_public_url"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "external_export_download_prepare" not in reconciliation.summary_json
    finally:
        db.close()


def test_layer3_api_external_export_download_deliver_streams_validated_bundle_without_side_effects(
    client: TestClient,
    monkeypatch,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-external-export-download-deliver-success")
    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=dispatch_payload)
    assert dispatch.status_code == 200, dispatch.json()
    dispatch_body = dispatch.json()
    prepare_payload = _external_export_download_prepare_payload(
        request_id="api-external-export-download-deliver-success-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
    )
    readiness = client.post("/api/v1/layer3/handoff/export/download/prepare", json=prepare_payload)
    assert readiness.status_code == 200, readiness.json()
    readiness_body = readiness.json()
    deliver_payload = _external_export_download_deliver_payload(
        request_id="api-external-export-download-deliver-success-deliver",
        prepare_payload=prepare_payload,
        readiness_body=readiness_body,
        decision_notes="Deliver the validated APS bundle artifact.",
    )
    bundle_path = Path(readiness_body["source_artifact_ref"])
    expected_bytes = bundle_path.read_bytes()

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    db = client.layer3_session_factory()
    try:
        counts_before = {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        packages_before = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        readiness_state_before = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json["external_export_download_prepare"]
        )
    finally:
        db.close()
    files_before = files_under_tmp()

    from app.services import layer3_workbench, nrc_aps_evidence_bundle

    observed_artifact_validation_transactions: list[bool] = []
    original_load_bundle = nrc_aps_evidence_bundle.load_persisted_bundle_artifact

    direct_db = client.layer3_session_factory()
    try:
        def assert_artifact_validation_after_transaction_release(*, bundle_id=None, bundle_ref=None):
            observed_artifact_validation_transactions.append(direct_db.in_transaction())
            return original_load_bundle(bundle_id=bundle_id, bundle_ref=bundle_ref)

        with monkeypatch.context() as patch:
            patch.setattr(
                nrc_aps_evidence_bundle,
                "load_persisted_bundle_artifact",
                assert_artifact_validation_after_transaction_release,
            )
            direct_delivery = layer3_workbench.external_export_download_deliver(direct_db, deliver_payload)
    finally:
        direct_db.close()

    assert observed_artifact_validation_transactions == [False]
    assert direct_delivery.artifact_path.read_bytes() == expected_bytes
    assert direct_delivery.headers["X-Layer3-Delivery-State"] == "external_export_download_delivered"

    delivery = client.post("/api/v1/layer3/handoff/export/download/deliver", json=deliver_payload)
    assert delivery.status_code == 200, delivery.text
    assert delivery.content == expected_bytes
    assert delivery.headers["content-type"].startswith("application/json")
    assert "attachment" in delivery.headers["content-disposition"]
    assert "filename=" in delivery.headers["content-disposition"]
    assert delivery.headers["x-layer3-schema-id"] == "layer3.external_export_download_delivery.v1"
    assert delivery.headers["x-layer3-delivery-state"] == "external_export_download_delivered"
    assert delivery.headers["x-layer3-source-artifact-hash"] == readiness_body["source_artifact_hash"]
    assert "download_url" not in delivery.headers
    assert "public_url" not in delivery.headers
    assert "signed_url" not in delivery.headers
    assert "connector_run_id" not in delivery.headers

    form_delivery = client.post(
        "/api/v1/layer3/handoff/export/download/deliver",
        data={key: json.dumps(value) for key, value in deliver_payload.items()},
    )
    assert form_delivery.status_code == 200, form_delivery.text
    assert form_delivery.content == expected_bytes
    assert "attachment" in form_delivery.headers["content-disposition"]
    assert form_delivery.headers["x-layer3-delivery-state"] == "external_export_download_delivered"
    assert form_delivery.headers["x-layer3-source-artifact-hash"] == readiness_body["source_artifact_hash"]

    replay = client.post("/api/v1/layer3/handoff/export/download/deliver", json=deliver_payload)
    assert replay.status_code == 200
    assert replay.content == expected_bytes

    db = client.layer3_session_factory()
    try:
        assert {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        packages_after = [
            (
                package.output_package_id,
                package.package_kind,
                package.status,
                package.payload_ref,
                package.payload_hash,
                package.summary_json,
            )
            for package in db.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        ]
        assert packages_after == packages_before
        readiness_state_after = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json["external_export_download_prepare"]
        )
        assert readiness_state_after == readiness_state_before
    finally:
        db.close()
    assert files_under_tmp() == files_before


def test_layer3_api_external_export_download_deliver_fails_closed_when_bundle_artifact_missing(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_payload,
    ) = _prepare_aps_handoff_dispatch(
        client,
        tmp_path,
        request_id="api-external-export-download-deliver-missing-artifact",
    )
    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=dispatch_payload)
    assert dispatch.status_code == 200, dispatch.json()
    dispatch_body = dispatch.json()
    prepare_payload = _external_export_download_prepare_payload(
        request_id="api-external-export-download-deliver-missing-artifact-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
    )
    readiness = client.post("/api/v1/layer3/handoff/export/download/prepare", json=prepare_payload)
    assert readiness.status_code == 200, readiness.json()
    readiness_body = readiness.json()
    deliver_payload = _external_export_download_deliver_payload(
        request_id="api-external-export-download-deliver-missing-artifact-deliver",
        prepare_payload=prepare_payload,
        readiness_body=readiness_body,
    )
    bundle_path = Path(readiness_body["source_artifact_ref"])
    archived_dir = tmp_path / "archive"
    archived_dir.mkdir()
    archived_bundle_path = archived_dir / bundle_path.name
    bundle_path.replace(archived_bundle_path)
    assert not bundle_path.exists()
    assert archived_bundle_path.exists()

    def files_under_tmp() -> set[str]:
        return {str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*") if path.is_file()}

    files_before = files_under_tmp()
    db = client.layer3_session_factory()
    try:
        counts_before = {
            "analysis_artifacts": db.query(AnalysisArtifact).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "output_packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
        readiness_state_before = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json["external_export_download_prepare"]
        )
    finally:
        db.close()

    delivery = client.post("/api/v1/layer3/handoff/export/download/deliver", json=deliver_payload)
    assert delivery.status_code == 409
    body = delivery.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "external_export_download_delivery_source_artifact_unavailable"
    assert body["blocked_fields"] == ["aps_bundle_ref"]
    assert "download_url" not in delivery.headers
    assert "public_url" not in delivery.headers
    assert "signed_url" not in delivery.headers
    assert "connector_run_id" not in delivery.headers

    db = client.layer3_session_factory()
    try:
        assert {
            "analysis_artifacts": db.query(AnalysisArtifact).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "output_packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        readiness_state_after = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
            .summary_json["external_export_download_prepare"]
        )
        assert readiness_state_after == readiness_state_before
    finally:
        db.close()
    assert files_under_tmp() == files_before
    assert not bundle_path.exists()
    assert archived_bundle_path.exists()


def test_layer3_api_external_export_download_deliver_malformed_json_fails_closed(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/layer3/handoff/export/download/deliver",
        data="{",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "invalid_layer3_request_json"
    assert body["message"] == "Request body must be valid JSON."


def test_layer3_api_external_export_download_deliver_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/handoff/export/download/deliver",
        json={"client_request_id": "api-external-export-download-deliver-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) >= {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "aps_handoff_record_ref",
        "aps_handoff_state",
        "aps_output_package_id",
        "aps_bundle_ref",
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "export_download_target",
        "download_mode",
        "delivery_mode",
        "operator_decision",
    }

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        submit_body,
        prepare_body,
        dispatch_payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-external-export-download-deliver-prechecks")
    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=dispatch_payload)
    assert dispatch.status_code == 200, dispatch.json()
    dispatch_body = dispatch.json()
    prepare_payload = _external_export_download_prepare_payload(
        request_id="api-external-export-download-deliver-prechecks-prepare",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
        dispatch_body=dispatch_body,
    )
    not_prepared_payload = {
        **prepare_payload,
        "client_request_id": "api-external-export-download-deliver-not-prepared",
        "operator_decision": "deliver_external_export_download",
        "external_export_download_record_ref": "missing-readiness",
        "export_download_descriptor_ref": "missing-descriptor",
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
    }
    not_prepared = client.post("/api/v1/layer3/handoff/export/download/deliver", json=not_prepared_payload)
    assert not_prepared.status_code == 409
    assert not_prepared.json()["error_code"] == "external_export_download_delivery_requires_prepared_readiness"

    readiness = client.post("/api/v1/layer3/handoff/export/download/prepare", json=prepare_payload)
    assert readiness.status_code == 200, readiness.json()
    readiness_body = readiness.json()
    base_payload = _external_export_download_deliver_payload(
        request_id="api-external-export-download-deliver-prechecks-deliver",
        prepare_payload=prepare_payload,
        readiness_body=readiness_body,
    )
    cases = [
        ({**base_payload, "export_download_target": "public_download_url"}, 400, "external_export_download_delivery_target_not_admitted"),
        ({**base_payload, "download_mode": "browser_download"}, 400, "external_export_download_delivery_download_mode_not_admitted"),
        ({**base_payload, "delivery_mode": "signed_url"}, 400, "external_export_download_delivery_mode_not_admitted"),
        ({**base_payload, "operator_decision": "prepare_external_export_download"}, 400, "unsupported_external_export_download_delivery_decision"),
        ({**base_payload, "download_url": "https://example.invalid/bundle.json"}, 400, "external_export_download_delivery_scope_not_admitted"),
        ({**base_payload, "external_export_download_state": "external_export_download_unavailable"}, 409, "external_export_download_delivery_requires_prepared_readiness"),
        ({**base_payload, "external_export_download_record_ref": "stale-readiness-ref"}, 409, "external_export_download_delivery_external_export_download_record_ref_mismatch"),
        ({**base_payload, "export_download_descriptor_ref": "stale-descriptor-ref"}, 409, "external_export_download_delivery_export_download_descriptor_ref_mismatch"),
        ({**base_payload, "aps_bundle_ref": "stale-bundle-ref"}, 409, "external_export_download_delivery_aps_bundle_ref_mismatch"),
        ({**base_payload, "aps_bundle_id": "stale-bundle-id"}, 409, "external_export_download_delivery_aps_bundle_id_mismatch"),
        ({**base_payload, "aps_schema_id": "stale-schema"}, 409, "external_export_download_delivery_aps_schema_id_mismatch"),
        ({**base_payload, "payload_hashes": ["stale-hash", *base_payload["payload_hashes"][1:]]}, 409, "external_export_download_prepare_payload_hashes_mismatch"),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/handoff/export/download/deliver", json=payload)
        assert response.status_code == expected_status, response.text
        assert response.json()["error_code"] == expected_error


def test_layer3_api_aps_handoff_dispatch_fails_closed_on_malformed_canonical_inventory(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        _preview_body,
        _approval_body,
        _selection_body,
        _start_body,
        _review_body,
        _package_preview_body,
        _commit_body,
        _submit_body,
        _prepare_body,
        payload,
    ) = _prepare_aps_handoff_dispatch(
        client,
        tmp_path,
        request_id="api-aps-handoff-dispatch-malformed-inventory",
    )

    db = client.layer3_session_factory()
    try:
        canonical_package = (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.session_id == session_id,
                L3OutputPackage.package_kind == "canonical_internal",
            )
            .one()
        )
        canonical_payload_path = Path(canonical_package.payload_ref)
        canonical_payload = json.loads(canonical_payload_path.read_text(encoding="utf-8"))
        canonical_payload["selection_and_source_summary"] = {
            "material_snapshot_inventory_json": [
                {
                    "source_shape": "aps_content_document",
                    "source_identity_json": {
                        "content_id": "content-malformed",
                        "run_id": "run-malformed",
                    },
                }
            ]
        }
        canonical_payload_path.write_text(json.dumps(canonical_payload, sort_keys=True), encoding="utf-8")
    finally:
        db.close()

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_blocked"
    assert "target_id" in summary_body["aps_handoff_dispatch"]["blocked_reason"]

    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert dispatch.status_code == 409
    assert dispatch.json()["error_code"] == "aps_handoff_dispatch_blocked"

    db = client.layer3_session_factory()
    try:
        assert (
            db.query(L3OutputPackage)
            .filter(L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF)
            .count()
            == 0
        )
    finally:
        db.close()


def test_layer3_api_package_review_submit_blocks_orphan_aps_handoff_package(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _commit_payload,
    ) = _construct_quant_package_set(client, tmp_path, request_id="api-aps-orphan-before-submit")
    pass_run_id = selection_body["pass_run_ids"][0]
    _insert_orphan_aps_handoff_package(
        client,
        tmp_path,
        session_id=session_id,
        reconciliation_record_id=commit_body["reconciliation_record_id"],
        suffix="before-submit",
    )

    submit_summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert submit_summary.status_code == 200
    submit_summary_body = submit_summary.json()
    assert submit_summary_body["package_construction"]["state"] == "package_commit_blocked"
    assert submit_summary_body["package_construction"]["unexpected_package_kinds"] == [
        PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF
    ]
    assert submit_summary_body["package_review_submit"]["state"] == "package_review_submit_unavailable"

    blocked_submit = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": "api-aps-orphan-before-submit-submit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": commit_body["package_review_preview_hash"],
            "reconciliation_record_id": commit_body["reconciliation_record_id"],
            "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
            "payload_hashes": commit_body["payload_hashes"],
            "operator_decision": "approved",
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert blocked_submit.status_code == 409
    assert blocked_submit.json()["error_code"] == "package_review_submit_unexpected_package_state"


def test_layer3_api_handoff_export_prepare_blocks_orphan_aps_handoff_package(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(client, tmp_path, request_id="api-aps-orphan-before-prepare")
    _insert_orphan_aps_handoff_package(
        client,
        tmp_path,
        session_id=session_id,
        reconciliation_record_id=commit_body["reconciliation_record_id"],
        suffix="before-prepare",
    )
    blocked_prepare = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id="api-aps-orphan-before-prepare-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
        ),
    )
    assert blocked_prepare.status_code == 409
    assert blocked_prepare.json()["error_code"] == "handoff_export_prepare_unexpected_package_state"


def test_layer3_api_aps_handoff_dispatch_blocks_orphan_aps_handoff_package(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        _preview_body,
        _approval_body,
        _selection_body,
        _start_body,
        _review_body,
        _package_preview_body,
        commit_body,
        _submit_body,
        _prepare_body,
        payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-aps-orphan-before-dispatch")
    _insert_orphan_aps_handoff_package(
        client,
        tmp_path,
        session_id=session_id,
        reconciliation_record_id=commit_body["reconciliation_record_id"],
        suffix="before-dispatch",
    )
    blocked_dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert blocked_dispatch.status_code == 409
    assert blocked_dispatch.json()["error_code"] == "aps_handoff_dispatch_unexpected_package_state"

    db = client.layer3_session_factory()
    try:
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"])
            .one()
        )
        assert "aps_handoff_dispatch" not in reconciliation.summary_json
    finally:
        db.close()


def test_layer3_api_aps_handoff_dispatch_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json={"client_request_id": "api-aps-handoff-dispatch-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) == {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_submit_record_ref",
        "package_review_state",
        "prepare_record_ref",
        "handoff_export_state",
        "handoff_export_envelope_ref",
        "handoff_target",
        "export_mode",
        "aps_handoff_target",
        "dispatch_mode",
        "operator_decision",
    }

    (
        session_id,
        _preview_body,
        _approval_body,
        _selection_body,
        _start_body,
        _review_body,
        _package_preview_body,
        commit_body,
        _submit_body,
        _prepare_body,
        base_payload,
    ) = _prepare_aps_handoff_dispatch(client, tmp_path, request_id="api-aps-handoff-dispatch-prechecks")

    cases = [
        (
            {**base_payload, "handoff_target": "external_export"},
            400,
            "aps_handoff_dispatch_target_not_admitted",
        ),
        (
            {**base_payload, "export_mode": "dispatch"},
            400,
            "aps_handoff_dispatch_export_mode_not_admitted",
        ),
        (
            {**base_payload, "aps_handoff_target": "connector_run"},
            400,
            "aps_handoff_dispatch_target_family_not_admitted",
        ),
        (
            {**base_payload, "dispatch_mode": "connector_dispatch"},
            400,
            "aps_handoff_dispatch_mode_not_admitted",
        ),
        (
            {**base_payload, "operator_decision": "send"},
            400,
            "unsupported_aps_handoff_dispatch_decision",
        ),
        (
            {**base_payload, "download_url": "https://example.invalid/bundle.json", "connector_run_id": "run-1"},
            400,
            "aps_handoff_dispatch_scope_not_admitted",
        ),
        (
            {**base_payload, "result_review_record_ref": "stale-review-ref"},
            409,
            "aps_handoff_dispatch_result_review_mismatch",
        ),
        (
            {**base_payload, "package_review_preview_hash": "stale-package-preview"},
            409,
            "aps_handoff_dispatch_preview_mismatch",
        ),
        (
            {**base_payload, "package_review_submit_record_ref": "stale-submit-ref"},
            409,
            "aps_handoff_dispatch_submit_ref_mismatch",
        ),
        (
            {**base_payload, "reconciliation_record_id": "stale-reconciliation"},
            409,
            "aps_handoff_dispatch_requires_package_construction",
        ),
        (
            {**base_payload, "output_package_ids": ["pkg-stale", *base_payload["output_package_ids"][1:]]},
            409,
            "aps_handoff_dispatch_package_ids_mismatch",
        ),
        (
            {**base_payload, "package_kinds": ["canonical_internal"]},
            409,
            "aps_handoff_dispatch_package_kinds_mismatch",
        ),
        (
            {**base_payload, "payload_refs": ["stale-ref", *base_payload["payload_refs"][1:]]},
            409,
            "aps_handoff_dispatch_payload_refs_mismatch",
        ),
        (
            {**base_payload, "payload_hashes": ["stale-hash", *base_payload["payload_hashes"][1:]]},
            409,
            "aps_handoff_dispatch_payload_hashes_mismatch",
        ),
        (
            {**base_payload, "package_review_state": "package_review_blocked"},
            409,
            "aps_handoff_dispatch_requires_approved_package_review",
        ),
        (
            {**base_payload, "handoff_export_state": "handoff_export_held"},
            409,
            "aps_handoff_dispatch_requires_prepared_handoff_export",
        ),
        (
            {**base_payload, "prepare_record_ref": "stale-prepare-ref"},
            409,
            "aps_handoff_dispatch_prepare_ref_mismatch",
        ),
        (
            {**base_payload, "handoff_export_envelope_ref": "stale-envelope-ref"},
            409,
            "aps_handoff_dispatch_envelope_ref_mismatch",
        ),
    ]
    for payload, expected_status, expected_error in cases:
        response = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
        assert response.status_code == expected_status
        assert response.json()["error_code"] == expected_error

    unknown_extra = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json={**base_payload, "destination_connector": "not-admitted"},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "aps_handoff_dispatch" not in reconciliation.summary_json
        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.session_id == session_id,
                L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            )
            .count()
            == 0
        )
    finally:
        db.close()


def test_layer3_api_aps_handoff_dispatch_requires_prepared_state(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(client, tmp_path, request_id="api-aps-handoff-dispatch-held")
    held_prepare = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id="api-aps-handoff-dispatch-held-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
            operator_decision="hold",
            decision_notes="Hold prepare before APS handoff dispatch.",
        ),
    )
    assert held_prepare.status_code == 200
    held_prepare_body = held_prepare.json()
    assert held_prepare_body["handoff_export_state"] == "handoff_export_held"
    dispatch = client.post(
        "/api/v1/layer3/handoff/aps/dispatch",
        json=_aps_handoff_dispatch_payload(
            request_id="api-aps-handoff-dispatch-held-dispatch",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
            prepare_body={
                **held_prepare_body,
                "handoff_export_envelope": {"envelope_ref": "missing-prepared-envelope"},
            },
        ),
    )
    assert dispatch.status_code == 409
    assert dispatch.json()["error_code"] == "aps_handoff_dispatch_requires_prepared_handoff_export"

    summary = client.get(f"/api/v1/layer3/session/{session_id}")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["handoff_export_prepare"]["state"] == "handoff_export_held"
    assert summary_body["aps_handoff_dispatch"]["state"] == "aps_handoff_unavailable"


def test_layer3_api_aps_handoff_dispatch_blocks_when_owner_service_provenance_missing(
    client: TestClient,
    tmp_path,
) -> None:
    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        review_body,
        _package_preview_body,
        commit_body,
        _submit_payload,
        submit_body,
    ) = _submit_quant_package_review(client, tmp_path, request_id="api-aps-handoff-dispatch-blocked")
    prepare = client.post(
        "/api/v1/layer3/handoff/export/prepare",
        json=_handoff_export_prepare_payload(
            request_id="api-aps-handoff-dispatch-blocked-prepare",
            session_id=session_id,
            preview_body=preview_body,
            approval_body=approval_body,
            selection_body=selection_body,
            start_body=start_body,
            review_body=review_body,
            commit_body=commit_body,
            submit_body=submit_body,
        ),
    )
    assert prepare.status_code == 200
    prepare_body = prepare.json()
    payload = _aps_handoff_dispatch_payload(
        request_id="api-aps-handoff-dispatch-blocked-dispatch",
        session_id=session_id,
        preview_body=preview_body,
        approval_body=approval_body,
        selection_body=selection_body,
        start_body=start_body,
        review_body=review_body,
        commit_body=commit_body,
        submit_body=submit_body,
        prepare_body=prepare_body,
    )
    db = client.layer3_session_factory()
    try:
        counts_before = {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        }
    finally:
        db.close()

    dispatch = client.post("/api/v1/layer3/handoff/aps/dispatch", json=payload)
    assert dispatch.status_code == 409
    assert dispatch.json()["error_code"] == "aps_handoff_dispatch_blocked"

    db = client.layer3_session_factory()
    try:
        assert {
            "artifacts": db.query(AnalysisArtifact).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "packages": db.query(L3OutputPackage).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
        } == counts_before
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "aps_handoff_dispatch" not in reconciliation.summary_json
        assert (
            db.query(L3OutputPackage)
            .filter(
                L3OutputPackage.session_id == session_id,
                L3OutputPackage.package_kind == PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            )
            .count()
            == 0
        )
    finally:
        db.close()


def test_layer3_api_package_review_submit_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/package/review/submit",
        json={"client_request_id": "api-package-submit-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) == {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
        "reconciliation_record_id",
        "output_package_ids",
        "payload_hashes",
        "operator_decision",
    }

    (
        unconstructed_session_id,
        unconstructed_preview_body,
        unconstructed_approval_body,
        unconstructed_selection_body,
        unconstructed_start_body,
        _status_body,
        unconstructed_review_body,
    ) = _execute_and_approve_quant_result_review(
        client,
        tmp_path,
        request_id="api-package-submit-unconstructed",
    )
    unconstructed_pass_run_id = unconstructed_selection_body["pass_run_ids"][0]
    unconstructed_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-package-submit-unconstructed-preview",
            "session_id": unconstructed_session_id,
            "analysis_plan_id": unconstructed_approval_body["analysis_plan_id"],
            "pass_run_id": unconstructed_pass_run_id,
            "preview_id": unconstructed_preview_body["preview_id"],
            "preview_hash": unconstructed_preview_body["preview_hash"],
            "analysis_run_id": unconstructed_start_body["analysis_run_id"],
            "result_review_record_ref": unconstructed_review_body["review_record_ref"],
        },
    )
    assert unconstructed_preview.status_code == 200
    unconstructed = client.post(
        "/api/v1/layer3/package/review/submit",
        json={
            "client_request_id": "api-package-submit-unconstructed-submit",
            "session_id": unconstructed_session_id,
            "analysis_plan_id": unconstructed_approval_body["analysis_plan_id"],
            "pass_run_id": unconstructed_pass_run_id,
            "preview_id": unconstructed_preview_body["preview_id"],
            "preview_hash": unconstructed_preview_body["preview_hash"],
            "analysis_run_id": unconstructed_start_body["analysis_run_id"],
            "result_review_record_ref": unconstructed_review_body["review_record_ref"],
            "package_review_preview_hash": unconstructed_preview.json()["package_review_preview_hash"],
            "reconciliation_record_id": "missing-reconciliation",
            "output_package_ids": ["pkg-a", "pkg-b", "pkg-c"],
            "payload_hashes": ["hash-a", "hash-b", "hash-c"],
            "operator_decision": "approved",
        },
    )
    assert unconstructed.status_code == 409
    assert unconstructed.json()["error_code"] == "package_review_submit_requires_package_construction"

    session_id = unconstructed_session_id
    preview_body = unconstructed_preview_body
    approval_body = unconstructed_approval_body
    pass_run_id = unconstructed_pass_run_id
    start_body = unconstructed_start_body
    review_body = unconstructed_review_body
    commit = client.post(
        "/api/v1/layer3/package/review/commit",
        json={
            "client_request_id": "api-package-submit-precheck-package-commit",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "package_review_preview_hash": unconstructed_preview.json()["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )
    assert commit.status_code == 200
    commit_body = commit.json()
    base_payload = {
        "client_request_id": "api-package-submit-precheck-submit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": commit_body["package_review_preview_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": [package["output_package_id"] for package in commit_body["output_packages"]],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }

    forbidden = client.post(
        "/api/v1/layer3/package/review/submit",
        json={**base_payload, "handoff": True, "package_payload": {"unexpected": True}},
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "package_review_submit_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"handoff", "package_payload"}

    unknown_extra = client.post(
        "/api/v1/layer3/package/review/submit",
        json={**base_payload, "destination_connector": "not-admitted"},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "package_review_submit" not in reconciliation.summary_json
    finally:
        db.close()

    notes_required = client.post(
        "/api/v1/layer3/package/review/submit",
        json={**base_payload, "operator_decision": "changes_requested"},
    )
    assert notes_required.status_code == 400
    assert notes_required.json()["error_code"] == "package_review_submit_notes_required"

    stale_hash = client.post(
        "/api/v1/layer3/package/review/submit",
        json={**base_payload, "payload_hashes": ["stale-hash", *commit_body["payload_hashes"][1:]]},
    )
    assert stale_hash.status_code == 409
    assert stale_hash.json()["error_code"] == "package_review_submit_payload_hashes_mismatch"

    wrong_kinds = client.post(
        "/api/v1/layer3/package/review/submit",
        json={**base_payload, "expected_package_kinds": ["canonical_internal"]},
    )
    assert wrong_kinds.status_code == 409
    assert wrong_kinds.json()["error_code"] == "package_review_submit_kinds_mismatch"

    db = client.layer3_session_factory()
    try:
        reconciliation = db.query(L3ReconciliationRecord).filter(
            L3ReconciliationRecord.reconciliation_record_id == commit_body["reconciliation_record_id"]
        ).one()
        assert "package_review_submit" not in reconciliation.summary_json
    finally:
        db.close()


def test_layer3_api_package_construction_commit_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post(
        "/api/v1/layer3/package/review/commit",
        json={"client_request_id": "api-package-commit-missing", "session_id": "session-only"},
    )
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) == {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
        "result_review_record_ref",
        "package_review_preview_hash",
    }

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        _status_body,
        review_body,
    ) = _execute_and_approve_quant_result_review(
        client,
        tmp_path,
        request_id="api-package-commit-precheck",
    )
    pass_run_id = selection_body["pass_run_ids"][0]
    preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "client_request_id": "api-package-commit-precheck-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert preview.status_code == 200
    preview_state = preview.json()
    base_payload = {
        "client_request_id": "api-package-commit-precheck-commit",
        "session_id": session_id,
        "analysis_plan_id": approval_body["analysis_plan_id"],
        "pass_run_id": pass_run_id,
        "preview_id": preview_body["preview_id"],
        "preview_hash": preview_body["preview_hash"],
        "analysis_run_id": start_body["analysis_run_id"],
        "result_review_record_ref": review_body["review_record_ref"],
        "package_review_preview_hash": preview_state["package_review_preview_hash"],
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }

    forbidden = client.post(
        "/api/v1/layer3/package/review/commit",
        json={**base_payload, "handoff": True, "package_payload": {"unexpected": True}},
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "package_construction_commit_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"handoff", "package_payload"}

    unknown_extra = client.post(
        "/api/v1/layer3/package/review/commit",
        json={**base_payload, "destination_connector": "not-admitted"},
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 0
        assert db.query(L3ReconciliationRecord).count() == 0
    finally:
        db.close()

    stale_preview = client.post(
        "/api/v1/layer3/package/review/commit",
        json={**base_payload, "preview_hash": "stale-preview-hash"},
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    stale_package_preview = client.post(
        "/api/v1/layer3/package/review/commit",
        json={**base_payload, "package_review_preview_hash": "stale-package-preview"},
    )
    assert stale_package_preview.status_code == 409
    assert stale_package_preview.json()["error_code"] == "package_review_preview_mismatch"

    wrong_kinds = client.post(
        "/api/v1/layer3/package/review/commit",
        json={**base_payload, "expected_package_kinds": ["canonical_internal"]},
    )
    assert wrong_kinds.status_code == 409
    assert wrong_kinds.json()["error_code"] == "package_construction_commit_kinds_mismatch"

    output_metadata_path = Path(preview_state["output_metadata_summary"]["output_payload_ref"])
    output_metadata = json.loads(output_metadata_path.read_text(encoding="utf-8"))
    output_metadata["artifact_types_json"] = ["mutated_artifact_type_for_hash_guard"]
    output_metadata_path.write_text(json.dumps(output_metadata, sort_keys=True), encoding="utf-8")
    stale_artifact_type = client.post(
        "/api/v1/layer3/package/review/commit",
        json={**base_payload, "client_request_id": "api-package-commit-stale-artifact-type"},
    )
    assert stale_artifact_type.status_code == 409
    assert stale_artifact_type.json()["error_code"] == "package_review_preview_mismatch"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 0
        assert db.query(L3ReconciliationRecord).count() == 0
    finally:
        db.close()


def test_layer3_api_package_review_preview_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    missing = client.post("/api/v1/layer3/package/review/preview", json={"session_id": "session-only"})
    assert missing.status_code == 400
    assert set(missing.json()["blocked_fields"]) == {
        "analysis_plan_id",
        "pass_run_id",
        "preview_id",
        "preview_hash",
    }

    (
        session_id,
        preview_body,
        approval_body,
        selection_body,
        start_body,
        _status_body,
        review_body,
    ) = _execute_and_approve_quant_result_review(
        client,
        tmp_path,
        request_id="api-package-preview-precheck",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    forbidden = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "package": True,
            "handoff": True,
            "rerun": True,
            "rewrite_output": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "package_review_preview_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"package", "handoff", "rerun", "rewrite_output"}

    unknown_extra = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
            "destination_connector": "not-admitted",
        },
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        assert "package_review_preview" not in (stored_pass.summary_json or {})
        assert db.query(L3OutputPackage).count() == 0
        assert db.query(L3ReconciliationRecord).count() == 0
    finally:
        db.close()

    stale_preview = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": "stale-preview",
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    mismatched_review_ref = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": "wrong-review-ref",
        },
    )
    assert mismatched_review_ref.status_code == 409
    assert mismatched_review_ref.json()["error_code"] == "package_review_preview_result_review_mismatch"

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        review_state = dict(stored_pass.summary_json["execution_result_review"])
        review_state["review_state"] = "execution_result_review_changes_requested"
        review_state["operator_decision"] = "changes_requested"
        stored_pass.summary_json = {
            **stored_pass.summary_json,
            "execution_result_review": review_state,
        }
        db.commit()
    finally:
        db.close()

    non_approved = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert non_approved.status_code == 409
    assert non_approved.json()["error_code"] == "package_review_preview_requires_approved_result_review"

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        review_state = dict(stored_pass.summary_json["execution_result_review"])
        review_state["review_state"] = "execution_result_review_approved"
        review_state["operator_decision"] = "approved"
        review_state["unresolved_trace_count"] = 1
        stored_pass.summary_json = {
            **stored_pass.summary_json,
            "execution_result_review": review_state,
        }
        db.commit()
    finally:
        db.close()

    unresolved = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert unresolved.status_code == 409
    assert unresolved.json()["error_code"] == "package_review_preview_trace_unresolved"

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one()
        review_state = dict(stored_pass.summary_json["execution_result_review"])
        review_state["unresolved_trace_count"] = 0
        stored_pass.summary_json = {
            **stored_pass.summary_json,
            "execution_result_review": review_state,
        }
        db.add(
            L3ReconciliationRecord(
                reconciliation_record_id="existing-reconciliation",
                session_id=session_id,
                status="reconciled",
                summary_json={"source": "preexisting"},
            )
        )
        db.commit()
    finally:
        db.close()

    existing_package_state = client.post(
        "/api/v1/layer3/package/review/preview",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": start_body["analysis_run_id"],
            "result_review_record_ref": review_body["review_record_ref"],
        },
    )
    assert existing_package_state.status_code == 409
    assert existing_package_state.json()["error_code"] == "package_review_preview_existing_package_state"


def test_layer3_api_execution_result_review_records_non_approval_decision(
    client: TestClient,
    tmp_path,
) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-result-review-nonapproval-selection",
    )
    pass_run_id = selection_body["pass_run_ids"][0]
    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-result-review-nonapproval-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200

    review = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-changes-requested",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "changes_requested",
            "review_notes": "Needs operator clarification before any later package step.",
        },
    )

    assert review.status_code == 200
    body = review.json()
    assert body["status"] == "recorded"
    assert body["review_state"] == "execution_result_review_changes_requested"
    assert body["operator_decision"] == "changes_requested"
    assert body["review_notes_recorded"] is True
    assert body["package_review_enabled"] is False
    assert body["handoff_enabled"] is False


def test_layer3_api_execution_result_review_prechecks_fail_closed(
    client: TestClient,
    tmp_path,
) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-result-review-precheck-selection",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    missing_request_id = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "approved",
        },
    )
    assert missing_request_id.status_code == 400
    assert missing_request_id.json()["error_code"] == "missing_execution_result_review_fields"
    assert missing_request_id.json()["blocked_fields"] == ["client_request_id"]

    forbidden = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-forbidden",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "approved",
            "package_review": True,
            "rerun": True,
            "rewrite_output": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "execution_result_review_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"package_review", "rerun", "rewrite_output"}

    unknown_extra = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-unknown-extra",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "approved",
            "destination_connector": "not-admitted",
        },
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).one()
        assert "execution_result_review" not in (stored_pass.summary_json or {})
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()

    not_started = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-before-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "approved",
        },
    )
    assert not_started.status_code == 409
    assert not_started.json()["error_code"] == "analysis_execution_start_required"

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-result-review-precheck-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200

    stale_preview = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-stale-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": "stale-preview-hash",
            "operator_decision": "approved",
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    unresolved_trace = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-unresolved-trace",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "approved",
            "reviewed_output_items": [
                {
                    "item_ref": "untraceable-output",
                    "item_type": "finding",
                    "trace": {
                        "session_id": session_id,
                        "analysis_plan_id": approval_body["analysis_plan_id"],
                    },
                }
            ],
        },
    )
    assert unresolved_trace.status_code == 409
    assert unresolved_trace.json()["error_code"] == "execution_result_review_trace_unresolved"

    missing_notes = client.post(
        "/api/v1/layer3/execution/result/review",
        json={
            "client_request_id": "api-result-review-missing-notes",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_decision": "blocked",
        },
    )
    assert missing_notes.status_code == 400
    assert missing_notes.json()["error_code"] == "review_notes_required"


def test_layer3_api_execution_result_status_prechecks_fail_closed(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-result-status-precheck-selection",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    not_started = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert not_started.status_code == 409
    assert not_started.json()["error_code"] == "analysis_execution_start_required"

    forbidden = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "result_review": {"approve": True},
            "package_review": True,
            "rerun": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "execution_result_status_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"package_review", "rerun", "result_review"}

    unknown_extra = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "destination_connector": "not-admitted",
        },
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 1
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()

    unsupported_view = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "operator_view_mode": "review_and_package",
        },
    )
    assert unsupported_view.status_code == 400
    assert unsupported_view.json()["error_code"] == "unsupported_execution_result_status_view_mode"

    stale_preview = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": "stale-preview-hash",
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-result-status-precheck-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200

    mismatched_analysis_run = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "analysis_run_id": "wrong-analysis-run",
        },
    )
    assert mismatched_analysis_run.status_code == 409
    assert mismatched_analysis_run.json()["error_code"] == "analysis_run_mismatch"

    db = client.layer3_session_factory()
    try:
        stored_pass = db.query(L3PassRun).one()
        stored_pass.output_payload_ref = None
        db.commit()
    finally:
        db.close()

    missing_output = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert missing_output.status_code == 200
    missing_output_body = missing_output.json()
    assert missing_output_body["status"] == "missing_output_metadata"
    assert missing_output_body["result_status_available"] is False
    assert missing_output_body["output_metadata_summary"] is None
    assert missing_output_body["output_metadata_error"] == "output_payload_ref_missing"
    assert missing_output_body["result_review_enabled"] is False
    assert missing_output_body["package_review_enabled"] is False
    assert missing_output_body["handoff_enabled"] is False
    assert missing_output_body["next_state"] == "execution_result_status_missing_output"


def test_layer3_api_execution_result_status_reads_failed_terminal_pass(
    client: TestClient,
    tmp_path,
    monkeypatch,
) -> None:
    def fail_run_analysis(*args, **kwargs):
        raise RuntimeError("analysis exploded")

    monkeypatch.setattr(layer3_pass_entry_module, "run_analysis", fail_run_analysis)
    session_id, preview_body, approval_body, selection_body = _select_quant_pass(
        client,
        tmp_path,
        request_id="api-result-status-failed-selection",
    )
    pass_run_id = selection_body["pass_run_ids"][0]

    start = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-result-status-failed-start",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert start.status_code == 200
    assert start.json()["status"] == "failed"

    status = client.post(
        "/api/v1/layer3/execution/result/status",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["schema_id"] == "layer3.execution_result_status.v1"
    assert status_body["status"] == "failed"
    assert status_body["pass_run_status"] == "failed"
    assert status_body["analysis_run_id"] is None
    assert status_body["analysis_run_status"] is None
    assert status_body["output_payload_ref"] is None
    assert status_body["output_metadata_error"] == "output_payload_ref_missing"
    assert status_body["result_status_available"] is False
    assert status_body["error_present"] is True
    assert status_body["error_message"] == "analysis exploded"
    assert status_body["result_review_enabled"] is False
    assert status_body["package_review_enabled"] is False
    assert status_body["handoff_enabled"] is False
    assert status_body["next_state"] == "execution_result_status_blocked"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 1
        assert db.query(AnalysisRun).count() == 0
        assert db.query(AnalysisArtifact).count() == 0
    finally:
        db.close()


def test_layer3_api_analysis_execution_start_prechecks_fail_closed(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)

    missing_request_id = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": "missing-pass-run",
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert missing_request_id.status_code == 400
    assert missing_request_id.json()["error_code"] == "client_request_id_required"

    missing_selection = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-no-selection",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": "missing-pass-run",
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert missing_selection.status_code == 409
    assert missing_selection.json()["error_code"] == "execution_selection_required"

    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-analysis-execution-precheck-selection",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 200
    pass_run_id = selection.json()["pass_run_ids"][0]

    forbidden = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-forbidden",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "package_review": True,
            "run_all": True,
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "analysis_execution_start_scope_not_admitted"
    assert set(forbidden.json()["blocked_fields"]) == {"package_review", "run_all"}

    unknown_forbidden = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-unknown-forbidden",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "results": True,
            "artifact_manifest": {"requested": True},
            "source_expansion": "rag",
            "schema_widening": True,
        },
    )
    assert unknown_forbidden.status_code == 400
    assert unknown_forbidden.json()["error_code"] == "analysis_execution_start_scope_not_admitted"
    assert set(unknown_forbidden.json()["blocked_fields"]) == {
        "artifact_manifest",
        "results",
        "schema_widening",
        "source_expansion",
    }

    unknown_extra = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-unknown-extra",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "destination_connector": "not-admitted",
        },
    )
    assert unknown_extra.status_code == 422
    assert any(
        item.get("type") == "extra_forbidden"
        and item.get("loc") == ["body", "destination_connector"]
        for item in unknown_extra.json()["detail"]
    )

    stale_preview = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-stale-preview",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": "stale-preview-hash",
        },
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["error_code"] == "preview_mismatch"

    unselected_pass = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-unselected",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": "unselected-pass-run",
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert unselected_pass.status_code == 409
    assert unselected_pass.json()["error_code"] == "pass_run_not_selected"

    unsupported_mode = client.post(
        "/api/v1/layer3/execution/start",
        json={
            "client_request_id": "api-analysis-execution-start-unsupported-mode",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "pass_run_id": pass_run_id,
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
            "execution_mode": "background_batch",
        },
    )
    assert unsupported_mode.status_code == 400
    assert unsupported_mode.json()["error_code"] == "unsupported_execution_mode"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 1
        assert db.query(AnalysisRun).count() == 0
        stored_pass = db.query(L3PassRun).one()
        assert stored_pass.status == "selected_not_started"
        assert stored_pass.summary_json["analysis_run_id"] is None
        assert stored_pass.output_payload_ref is None
    finally:
        db.close()


@pytest.mark.parametrize(
    ("operator_decision", "expected_error"),
    [
        ("reject_current_preview", "plan_rejected"),
        ("request_revision", "plan_revision_requested"),
    ],
)
def test_layer3_api_execution_selection_rejects_revision_control_states(
    client: TestClient,
    tmp_path,
    operator_decision: str,
    expected_error: str,
) -> None:
    db = client.layer3_session_factory()
    try:
        session_id, _, _ = _build_quant_ready_session(db, tmp_path)
    finally:
        db.close()

    preview = client.post(
        "/api/v1/layer3/plan/preview",
        json={
            "client_request_id": f"api-execution-selection-{operator_decision}-preview",
            "session_id": session_id,
            "include_exclusions": True,
            "preview_scope": "owner_service_default",
        },
    ).json()
    revision = client.post(
        "/api/v1/layer3/plan/revise",
        json={
            "client_request_id": f"api-execution-selection-{operator_decision}-revision",
            "session_id": session_id,
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_decision": operator_decision,
        },
    )
    assert revision.status_code == 200

    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": f"api-execution-selection-{operator_decision}",
            "session_id": session_id,
            "analysis_plan_id": "missing-approved-plan",
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
    )
    assert selection.status_code == 409
    assert selection.json()["error_code"] == expected_error

    db = client.layer3_session_factory()
    try:
        assert db.query(L3AnalysisPlan).count() == 0
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


def test_layer3_api_execution_selection_rejects_multiple_approved_plans(client: TestClient, tmp_path) -> None:
    session_id, preview_body, approval_body = _approve_quant_plan(client, tmp_path)
    db = client.layer3_session_factory()
    try:
        stored_plan = db.query(L3AnalysisPlan).one()
        db.add(
            L3AnalysisPlan(
                analysis_plan_id="manual-second-approved-plan",
                session_id=session_id,
                analysis_set_ids_json=list(stored_plan.analysis_set_ids_json),
                status="approved",
                approved_by_operator=True,
                approved_at=stored_plan.approved_at,
                plan_json=dict(stored_plan.plan_json),
            )
        )
        db.commit()
    finally:
        db.close()

    selection = client.post(
        "/api/v1/layer3/execution/select",
        json={
            "client_request_id": "api-execution-selection-multiple-plans",
            "session_id": session_id,
            "analysis_plan_id": approval_body["analysis_plan_id"],
            "preview_id": preview_body["preview_id"],
            "preview_hash": preview_body["preview_hash"],
        },
    )
    assert selection.status_code == 409
    assert selection.json()["error_code"] == "multiple_approved_plans"

    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
    finally:
        db.close()


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


def test_layer3_api_preflight_rejects_forbidden_manual_constraint_sentinels(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "api-preflight-forbidden-manual-constraints",
            "natural_language_intent": "Review deterministic Layer 3 material.",
            "manual_constraints": {
                "source_classes": ["dataset_version"],
                "connector_destination_dispatch": True,
                "local_upload": {"path": "not-admitted"},
                "package_mutation_reconstruction": {"enabled": True},
                "date_bounds": {"provider_public_url": "https://example.invalid/export"},
                "topics": [{"full_mockup_activation": True}],
            },
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["schema_id"] == "layer3.workbench_error.v1"
    assert body["error_code"] == "preflight_manual_constraint_scope_not_admitted"
    assert body["blocked_fields"] == [
        "manual_constraints.connector_destination_dispatch",
        "manual_constraints.date_bounds.provider_public_url",
        "manual_constraints.local_upload",
        "manual_constraints.package_mutation_reconstruction",
        "manual_constraints.topics[0].full_mockup_activation",
    ]
    assert body["next_allowed_actions"] == ["remove_non_admitted_manual_constraints"]
    db = client.layer3_session_factory()
    try:
        assert db.query(L3PassRun).count() == 0
        assert db.query(AnalysisRun).count() == 0
        assert db.query(L3OutputPackage).count() == 0
    finally:
        db.close()


def test_layer3_api_gate_c_override_rejects_unknown_fields_before_unavailable_response(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/layer3/gate-c/override",
        json={
            "client_request_id": "api-override-extra",
            "session_id": "missing",
            "execute": True,
            "hidden_llm_plan": {},
            "provider_public_url": "https://example.invalid/export",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]
