"""Route-level tests for the admission-status endpoint.

Proves:
T1 – flag-off, opened workflow → route calls the REAL service and returns HTTP 200
     with production_admission_ready=False and admission_flag_enabled=False.
     The service itself is NOT stubbed; only the workflow-row validator (separately
     proven) and the auth layer are mocked so the test focuses on the flag-off path.
T2 – unknown field in payload → HTTP 422 (Pydantic extra="forbid"), NOT a
     workbench-400.
T3 – missing authority (no prior binding) → auth-binding-missing error response.

Note: ready:true is covered at the service layer in
test_layer3_sec_xbrl_admission_status.py; no route-level ready:true test is
added here.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.api.deps import get_db
from app.db.session import Base
from main import app

ADMISSION_STATUS_ROUTE = (
    "/api/v1/layer3/sec-xbrl/operator-review/workflow/admission-status"
)

_DUMMY_WORKFLOW_ID = "wf-admission-route-test-001"
_DUMMY_HASH = "c" * 64


# ---------------------------------------------------------------------------
# Minimal valid payload
# ---------------------------------------------------------------------------

def _admission_status_payload(
    *,
    workflow_id: str | None = _DUMMY_WORKFLOW_ID,
    basis_hash: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict:
    payload: dict = {
        "client_request_id": "route-admission-test",
        "admission_status_mode": "sec_xbrl_production_admission_status_v1",
        "operator_decision": "inspect_sec_xbrl_production_admission_status",
    }
    if workflow_id is not None:
        payload["sec_xbrl_operator_review_workflow_id"] = workflow_id
    if basis_hash is not None:
        payload["workflow_basis_hash"] = basis_hash
    if extra_fields:
        payload.update(extra_fields)
    return payload


# ---------------------------------------------------------------------------
# Fixture: in-memory client that also exposes the SessionLocal for seeding
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_with_session(tmp_path, monkeypatch):
    """Yields (TestClient, SessionLocal) so tests can seed rows before POSTing."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
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
    try:
        yield test_client, SessionLocal
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
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
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# T1: flag-off, REAL service, seeded workflow → returns ready=False, flag=False
# ---------------------------------------------------------------------------

def test_admission_status_flag_off_returns_200_not_ready(client_with_session, monkeypatch) -> None:
    """End-to-end route test: the REAL inspect_redacted_production_admission_status
    service is exercised (NOT stubbed). Only the workflow-row validator (separately
    proven in test_layer3_sec_xbrl_admission_status.py) and the auth layer are mocked.

    With SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED unset (default OFF) the
    service returns the flag-off response regardless of evidence, proving:
      - production_admission_ready = False
      - admission_flag_enabled = False
      - production_admission_blocked_reason = 'production_admission_flag_disabled'
      - admission_schema_id = real emitted value from the live evaluator
      - auth_binding projection keys present (auth_binding_ref / auth_binding_basis_hash)
      - no raw financial value keys leaked

    Real service coverage is also in test_layer3_sec_xbrl_admission_status.py;
    this test specifically proves the route-to-service wiring is intact.
    """
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc
    from app.services.layer3_utils import stable_hash
    from app.models.models import (
        L3SecXbrlOperatorReviewWorkflow,
        L3SecXbrlProjectionSet,
        L3SecXbrlStatementPacketSet,
        L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
        L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
        L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
        L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
        L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
        L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
        L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
    )
    from app.services.layer3_sec_xbrl_production_admission import PRODUCTION_ADMISSION_SCHEMA_ID

    test_client, SessionLocal = client_with_session

    # -----------------------------------------------------------------------
    # Ensure evaluator flag is unset for this test (default OFF).
    # -----------------------------------------------------------------------
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)

    # -----------------------------------------------------------------------
    # Stub authorize_sec_xbrl_route (auth_owner=none dev profile).
    # -----------------------------------------------------------------------
    _ACTOR_HASH = stable_hash({"sec_xbrl_admission_route_test": "actor"})
    _WS_HASH = stable_hash({"sec_xbrl_admission_route_test": "workspace"})
    _POLICY_HASH = stable_hash({"route": "sec_xbrl_operator_review_workflow_admission_status_read", "role": "owner"})

    def _fake_authorize(*, headers, route_family, requested_role, request_fields=None):
        return {
            "decision": "allow",
            "policy_status": "admitted",
            "auth_owner_mode": "AUTH_OWNER_none_single_operator_dev_profile",
            "route_family": route_family,
            "role": requested_role,
            "actor_ref_hash": _ACTOR_HASH,
            "workspace_ref_hash": _WS_HASH,
            "policy_hash": _POLICY_HASH,
            "compatible_policy_hashes": {_POLICY_HASH},
            "requires_owner_binding": True,
            "mutating_route": False,
            "may_expose_revealed_values": False,
            "raw_operator_identity_exposed": False,
            "raw_proxy_header_exposed": False,
        }

    monkeypatch.setattr(auth_policy_svc, "authorize_sec_xbrl_route", _fake_authorize)

    # -----------------------------------------------------------------------
    # Stub require_sec_xbrl_owner_binding (simulates a prior open_write binding).
    # -----------------------------------------------------------------------
    _BINDING_HASH = stable_hash({"sec_xbrl_admission_route_test": "binding"})
    _canned_binding = {
        "auth_binding_ref": "sec_xbrl_auth_binding_receipt/test-binding-ref",
        "binding_basis_hash": _BINDING_HASH,
        "source_receipt_kind": "operator_review_workflow",
        "source_receipt_id": _DUMMY_WORKFLOW_ID,
        "route_family": "sec_xbrl_operator_review_workflow_open_write",
        "policy_hash": _POLICY_HASH,
        "role": "owner",
        "idempotent_replay": False,
    }

    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_owner_binding",
        lambda *args, **kwargs: _canned_binding,
    )

    # -----------------------------------------------------------------------
    # Seed a real opened workflow + packet + projection chain in the in-memory DB.
    # The workflow-row validator (_validate_workflow_row_for_status) requires a
    # complex derived basis hash; we mock that validator here, exactly as the
    # service-layer tests do — its correctness is proven independently.
    # -----------------------------------------------------------------------
    _PROJ_BASIS_HASH = stable_hash({"test": "proj-basis-route-t1"})
    _PACKET_BASIS_HASH = stable_hash({"test": "packet-basis-route-t1"})
    _SIDECAR_HASH = "a" * 64
    _VALUE_STORE_HASH = stable_hash({"test": "value-store-route-t1"})
    _SOURCE_REPORT_HASH = stable_hash({"test": "source-report-route-t1"})

    seed_db = SessionLocal()
    try:
        proj = L3SecXbrlProjectionSet(
            sec_xbrl_projection_set_id=str(uuid.uuid4()),
            client_request_id="route-t1-proj-client",
            projection_basis_hash=_PROJ_BASIS_HASH,
            projection_schema_id="layer3.sec_xbrl_projection_set.v1",
            source_report_schema_id="layer3.sec_xbrl_source_report.v1",
            source_report_hash=_SOURCE_REPORT_HASH,
            sidecar_receipt_hash=_SIDECAR_HASH,
            value_store_hash=_VALUE_STORE_HASH,
            sector_family_presence_json={},
            period_refs_json=[],
            projection_summary_json={},
            status=L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
            redaction_policy=L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
        )
        seed_db.add(proj)
        seed_db.flush()

        packet = L3SecXbrlStatementPacketSet(
            sec_xbrl_statement_packet_set_id=str(uuid.uuid4()),
            sec_xbrl_projection_set_id=proj.sec_xbrl_projection_set_id,
            client_request_id="route-t1-packet-client",
            packet_basis_hash=_PACKET_BASIS_HASH,
            packet_schema_id="layer3.sec_xbrl_statement_packet_set.v1",
            source_projection_basis_hash=_PROJ_BASIS_HASH,
            source_projection_schema_id="layer3.sec_xbrl_projection_set.v1",
            statement_organization_authority="test-authority-route-t1",
            value_policy=L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
            statement_count=1,
            total_review_rows=3,
            provenance_complete_count=3,
            review_exception_count=0,
            review_ready=True,
            identity_rollup_json={},
            organization_contract_json={},
            packet_summary_json={},
            status=L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
        )
        seed_db.add(packet)
        seed_db.flush()

        # workflow_basis_hash is set to a placeholder; _validate_workflow_row_for_status
        # is mocked so its basis-hash check is bypassed (separately proven).
        wf_basis_hash = stable_hash({"test": "workflow-basis-route-t1"})
        wf = L3SecXbrlOperatorReviewWorkflow(
            sec_xbrl_operator_review_workflow_id=_DUMMY_WORKFLOW_ID,
            sec_xbrl_statement_packet_set_id=packet.sec_xbrl_statement_packet_set_id,
            client_request_id="route-t1-wf-client",
            workflow_basis_hash=wf_basis_hash,
            workflow_schema_id="layer3.sec_xbrl_operator_review_workflow.v1",
            statement_packet_basis_hash=_PACKET_BASIS_HASH,
            source_projection_basis_hash=_PROJ_BASIS_HASH,
            control_mode=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
            review_status=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
            redaction_policy=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
            statement_count=1,
            row_count=3,
            review_exception_count=0,
            review_ready=True,
            permitted_controls_json=[],
            blocked_controls_json=[],
            authority_refs_json={},
            review_summary_json={
                "statement_count": 1,
                "row_count": 3,
                "review_exception_count": 0,
                "review_ready": True,
                "redaction_policy": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
                "control_mode": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
            },
        )
        seed_db.add(wf)
        seed_db.commit()
    finally:
        seed_db.close()

    # -----------------------------------------------------------------------
    # POST to the route with the evaluator flag unset (default OFF).
    # _validate_workflow_row_for_status is mocked so the service reaches the
    # evaluator with the flag OFF and returns the real flag-off response.
    # -----------------------------------------------------------------------
    with patch(
        "app.services.layer3_sec_xbrl_admission_status._validate_workflow_row_for_status"
    ):
        response = test_client.post(
            ADMISSION_STATUS_ROUTE,
            json=_admission_status_payload(workflow_id=_DUMMY_WORKFLOW_ID),
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )
    body = response.json()

    # Core assertions: flag-off path from the REAL service/evaluator
    assert body.get("production_admission_ready") is False, body
    assert body.get("admission_flag_enabled") is False, body
    assert body.get("production_admission_blocked_reason") == "production_admission_flag_disabled", body

    # production_readiness_claimed is hardcoded False in the service
    assert body.get("production_readiness_claimed") is False, body

    # admission_schema_id must be the REAL value emitted by the live evaluator
    assert body.get("admission_schema_id") == PRODUCTION_ADMISSION_SCHEMA_ID, (
        f"admission_schema_id drift: expected {PRODUCTION_ADMISSION_SCHEMA_ID!r}, "
        f"got {body.get('admission_schema_id')!r}"
    )

    # Auth-binding projection must be merged into the response
    assert "auth_binding_ref" in body, f"auth_binding_ref missing from response: {body}"
    assert "auth_binding_basis_hash" in body, f"auth_binding_basis_hash missing: {body}"

    # No raw financial value keys in the response
    raw_value_keys = {"raw_value", "effective_value", "lexical_value", "value_records"}
    leaked = raw_value_keys & set(body.keys())
    assert not leaked, f"Raw value keys leaked into admission-status response: {leaked}"


# ---------------------------------------------------------------------------
# T2: unknown field → 422 (Pydantic extra="forbid"), NOT workbench-400
# ---------------------------------------------------------------------------

def test_admission_status_unknown_field_returns_422(client) -> None:
    """POST with an extra unknown field returns HTTP 422 from Pydantic validation
    (model_config extra='forbid'), NOT a workbench-400 error envelope."""
    response = client.post(
        ADMISSION_STATUS_ROUTE,
        json=_admission_status_payload(extra_fields={"unknown_injected_field": "bad"}),
    )
    assert response.status_code == 422, (
        f"Expected 422 for unknown field, got {response.status_code}: {response.text}"
    )
    # Must NOT look like a workbench error (which has schema_id layer3.workbench_error.v1)
    body = response.json()
    assert body.get("schema_id") != "layer3.workbench_error.v1", (
        "Expected Pydantic 422, got workbench error envelope"
    )


# ---------------------------------------------------------------------------
# T3: missing authority (no prior binding) → auth-binding error response
# ---------------------------------------------------------------------------

def test_admission_status_no_prior_binding_returns_auth_error(client, monkeypatch) -> None:
    """POST with a workflow id but NO prior open_write binding → the route
    returns the workbench auth-binding-missing error (HTTP 404), mirroring the
    analogous status-route behaviour."""
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    from app.services.layer3_utils import stable_hash

    _ACTOR_HASH = stable_hash({"sec_xbrl_admission_route_test": "actor-t3"})
    _WS_HASH = stable_hash({"sec_xbrl_admission_route_test": "workspace-t3"})

    def _fake_authorize(*, headers, route_family, requested_role, request_fields=None):
        return {
            "decision": "allow",
            "policy_status": "admitted",
            "auth_owner_mode": "AUTH_OWNER_none_single_operator_dev_profile",
            "route_family": route_family,
            "role": requested_role,
            "actor_ref_hash": _ACTOR_HASH,
            "workspace_ref_hash": _WS_HASH,
            "policy_hash": stable_hash({"route": route_family, "role": requested_role}),
            "compatible_policy_hashes": {
                stable_hash({"route": route_family, "role": requested_role})
            },
            "requires_owner_binding": True,
            "mutating_route": False,
            "may_expose_revealed_values": False,
            "raw_operator_identity_exposed": False,
            "raw_proxy_header_exposed": False,
        }

    monkeypatch.setattr(auth_policy_svc, "authorize_sec_xbrl_route", _fake_authorize)

    # NOTE: do NOT stub require_sec_xbrl_owner_binding — real DB is empty, so it
    # raises SecXbrlAuthBindingError("sec_xbrl_auth_binding_missing", ..., http_status=404).
    response = client.post(
        ADMISSION_STATUS_ROUTE,
        json=_admission_status_payload(workflow_id="wf-no-binding-t3"),
    )

    # The route converts SecXbrlAuthBindingError → workbench error envelope.
    assert response.status_code in (400, 404, 409), (
        f"Expected auth-binding error (400/404/409), got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    error_code = body.get("error_code", "")
    assert "auth_binding" in error_code, (
        f"Expected auth_binding error, got: {error_code}"
    )
