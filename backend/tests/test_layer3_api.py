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
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import AnalysisArtifact, AnalysisRun, L3AnalysisPlan, L3PassRun
from main import app
from test_layer3_pass_entry import _build_quant_ready_session


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


def test_layer3_api_full_first_slice_flow(client: TestClient) -> None:
    bootstrap = client.get("/api/v1/layer3/bootstrap")
    assert bootstrap.status_code == 200
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["features"]["handoff"] is False
    assert bootstrap_body["features"]["analysis_execution_start"] is True
    assert bootstrap_body["features"]["analysis_execution"] is False
    assert bootstrap_body["execution_readiness"]["execution_admitted"] is False
    assert bootstrap_body["execution_readiness"]["analysis_execution_start_admitted"] is True
    assert bootstrap_body["execution_readiness"]["analysis_execution_start_endpoint"] == "/api/v1/layer3/execution/start"
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
    assert readiness_body["readiness_state"] == "execution_readiness_blocked"
    assert readiness_body["preview_hash_contract"]["schema_id"] == "layer3.plan_preview_hash.v1"
    assert readiness_body["idempotency_contract"]["client_request_id_supported"] is True
    assert readiness_body["idempotency_contract"]["client_request_id_required_current_slice"] is False
    assert "preview-hash" in readiness_body["implemented_gates"]
    assert "analysis-execution-start" in readiness_body["implemented_gates"]
    assert "revision-recovery" in readiness_body["deferred_gates"]
    states = {item["state"] for item in readiness_body["state_model"]["states"]}
    assert {"plan_preview_ready", "plan_approved", "plan_revision_requested", "execution_pass_completed", "execution_readiness_blocked"} <= states

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
