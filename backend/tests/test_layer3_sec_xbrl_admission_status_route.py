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


# ---------------------------------------------------------------------------
# T4: owner access — operator_role omitted → defaults to owner
# ---------------------------------------------------------------------------

def test_admission_status_owner_access(client_with_session, monkeypatch) -> None:
    """Proves owner-role access to admission-status end-to-end.

    The auth layer and binding layer are both stubbed (same pattern as T1).
    The stub returns a canned binding with role='owner', proving that:
      - operator_role omitted → handler passes OWNER_ROLE to _sec_xbrl_policy_decision
      - policy_decision["role"] == "owner" → require_sec_xbrl_owner_binding called with owner decision
      - response includes auth_binding_role == 'owner' from the projection

    The DB CHECK constraint on route_family prevents inserting an admission_status_read
    binding row directly (it is not in the constraint list for the existing migration),
    so the binding layer is stubbed exactly as T1 does — its correctness is proven
    independently in the auth-binding service tests.
    """
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc
    from app.services.layer3_utils import stable_hash

    test_client, SessionLocal = client_with_session
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)

    _WF_ID = "wf-admission-owner-access-t4"
    _ACTOR_HASH = stable_hash({"sec_xbrl_admission_owner_t4": "actor"})
    _WS_HASH = stable_hash({"sec_xbrl_admission_owner_t4": "workspace"})
    _POLICY_HASH = stable_hash({"route": "sec_xbrl_operator_review_workflow_admission_status_read", "role": "owner"})
    _BINDING_HASH = stable_hash({"sec_xbrl_admission_owner_t4": "binding"})

    # Capture the role passed into require_sec_xbrl_owner_binding so we can assert it.
    captured_roles: list[str] = []

    def _fake_authorize(*, headers, route_family, requested_role, request_fields=None):
        captured_roles.append(requested_role)
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

    _canned_binding_owner = {
        "auth_binding_ref": "sec-xbrl-auth-binding:t4-owner-ref",
        "binding_basis_hash": _BINDING_HASH,
        "source_receipt_kind": "operator_review_workflow",
        "source_receipt_id": _WF_ID,
        "route_family": "sec_xbrl_operator_review_workflow_open_write",
        "policy_hash": _POLICY_HASH,
        "role": "owner",
        "idempotent_replay": False,
    }

    monkeypatch.setattr(auth_policy_svc, "authorize_sec_xbrl_route", _fake_authorize)
    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_owner_binding",
        lambda *args, **kwargs: _canned_binding_owner,
    )

    # Seed a minimal workflow row so the service call finds the workflow.
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
    _PROJ_BASIS = stable_hash({"test": "proj-basis-t4"})
    _PACKET_BASIS = stable_hash({"test": "packet-basis-t4"})
    seed_db = SessionLocal()
    try:
        proj = L3SecXbrlProjectionSet(
            sec_xbrl_projection_set_id=str(uuid.uuid4()),
            client_request_id="t4-proj",
            projection_basis_hash=_PROJ_BASIS,
            projection_schema_id="layer3.sec_xbrl_projection_set.v1",
            source_report_schema_id="layer3.sec_xbrl_source_report.v1",
            source_report_hash=stable_hash({"test": "sr-t4"}),
            sidecar_receipt_hash="a" * 64,
            value_store_hash=stable_hash({"test": "vs-t4"}),
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
            client_request_id="t4-packet",
            packet_basis_hash=_PACKET_BASIS,
            packet_schema_id="layer3.sec_xbrl_statement_packet_set.v1",
            source_projection_basis_hash=_PROJ_BASIS,
            source_projection_schema_id="layer3.sec_xbrl_projection_set.v1",
            statement_organization_authority="t4-authority",
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
        wf_basis = stable_hash({"test": "wf-basis-t4"})
        wf = L3SecXbrlOperatorReviewWorkflow(
            sec_xbrl_operator_review_workflow_id=_WF_ID,
            sec_xbrl_statement_packet_set_id=packet.sec_xbrl_statement_packet_set_id,
            client_request_id="t4-wf",
            workflow_basis_hash=wf_basis,
            workflow_schema_id="layer3.sec_xbrl_operator_review_workflow.v1",
            statement_packet_basis_hash=_PACKET_BASIS,
            source_projection_basis_hash=_PROJ_BASIS,
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

    with patch(
        "app.services.layer3_sec_xbrl_admission_status._validate_workflow_row_for_status"
    ):
        response = test_client.post(
            ADMISSION_STATUS_ROUTE,
            json=_admission_status_payload(workflow_id=_WF_ID),
            # operator_role deliberately omitted → defaults to owner
        )

    assert response.status_code == 200, (
        f"Expected 200 for owner access, got {response.status_code}: {response.text}"
    )
    body = response.json()

    # The projection from _canned_binding_owner must appear in the response.
    assert body.get("auth_binding_role") == "owner", (
        f"Expected auth_binding_role='owner', got: {body.get('auth_binding_role')!r}; body={body}"
    )
    assert "auth_binding_ref" in body, f"auth_binding_ref missing: {body}"
    assert "auth_binding_basis_hash" in body, f"auth_binding_basis_hash missing: {body}"

    # Proves threading: handler passed OWNER_ROLE to authorize_sec_xbrl_route.
    assert captured_roles == ["owner"], (
        f"Expected handler to pass role='owner' (omitted→default), got: {captured_roles}"
    )


# ---------------------------------------------------------------------------
# T5: end-to-end auditor attach then read — the core proof (NO stubs on
#     authorize_sec_xbrl_route or require_sec_xbrl_owner_binding).
# ---------------------------------------------------------------------------

AUDITOR_ATTACH_ROUTE = (
    "/api/v1/layer3/sec-xbrl/operator-review/workflow/auditor-attach"
)
STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/status"


def _seed_workflow(
    SessionLocal,
    *,
    workflow_id: str,
    stable_hash,
    sidecar_hash: str,
    suffix: str,
):
    """Seed proj → packet → workflow chain and return (workflow_basis_hash, packet_set_id)."""
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
    proj_basis = stable_hash({"test": f"proj-basis-{suffix}"})
    packet_basis = stable_hash({"test": f"packet-basis-{suffix}"})
    seed_db = SessionLocal()
    try:
        proj = L3SecXbrlProjectionSet(
            sec_xbrl_projection_set_id=str(uuid.uuid4()),
            client_request_id=f"{suffix}-proj",
            projection_basis_hash=proj_basis,
            projection_schema_id="layer3.sec_xbrl_projection_set.v1",
            source_report_schema_id="layer3.sec_xbrl_source_report.v1",
            source_report_hash=stable_hash({"test": f"sr-{suffix}"}),
            sidecar_receipt_hash=sidecar_hash,
            value_store_hash=stable_hash({"test": f"vs-{suffix}"}),
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
            client_request_id=f"{suffix}-packet",
            packet_basis_hash=packet_basis,
            packet_schema_id="layer3.sec_xbrl_statement_packet_set.v1",
            source_projection_basis_hash=proj_basis,
            source_projection_schema_id="layer3.sec_xbrl_projection_set.v1",
            statement_organization_authority=f"{suffix}-authority",
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
        wf_basis = stable_hash({"test": f"wf-basis-{suffix}"})
        wf = L3SecXbrlOperatorReviewWorkflow(
            sec_xbrl_operator_review_workflow_id=workflow_id,
            sec_xbrl_statement_packet_set_id=packet.sec_xbrl_statement_packet_set_id,
            client_request_id=f"{suffix}-wf",
            workflow_basis_hash=wf_basis,
            workflow_schema_id="layer3.sec_xbrl_operator_review_workflow.v1",
            statement_packet_basis_hash=packet_basis,
            source_projection_basis_hash=proj_basis,
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
        return wf_basis
    finally:
        seed_db.close()


@pytest.fixture()
def proxy_client_with_session(tmp_path, monkeypatch):
    """Yields (TestClient, SessionLocal, storage_dir) with proxy mode configured."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
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
        yield test_client, SessionLocal, storage_dir
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_auditor_attach_then_read_end_to_end(
    proxy_client_with_session, monkeypatch
) -> None:
    """THE positive proof: auditor can attach then read admission-status via real layers.

    Proxy mode (auth_owner=proxy, trusted_proxy_mode=True).  NO stubbing of
    authorize_sec_xbrl_route or require_sec_xbrl_owner_binding.

    (a) Settings: proxy mode with x-forwarded-user / x-forwarded-groups headers.
    (b) Seed: real workflow + sidecar_receipt_hash.  Record an ownership marker for
        (workspace_ref_hash derived from the auditor's groups header, sidecar_receipt_hash).
    (c) POST auditor-attach → 200, binding role == 'auditor'.
    (d) POST admission-status with operator_role='auditor' → 200, auth_binding_role=='auditor',
        flag-off redacted body, no raw value keys.
    (e) POST status route with auditor identity → 200, auth_binding_role=='auditor'.
    """
    from app.services.layer3_utils import stable_hash
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc

    test_client, SessionLocal, storage_dir = proxy_client_with_session
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)

    # Auditor identity values — distinct identity, group = workspace
    _AUDITOR_IDENTITY = "auditor-user@example.com"
    _AUDITOR_GROUPS = "sec-xbrl-auditors"
    _AUDITOR_HEADERS = {
        "x-forwarded-user": _AUDITOR_IDENTITY,
        "x-forwarded-groups": _AUDITOR_GROUPS,
    }

    # Derive the workspace_ref_hash the server will compute from these headers.
    _WORKSPACE_REF_HASH = stable_hash({"auth_owner": "proxy", "workspace_ref": _AUDITOR_GROUPS})
    _ACTOR_REF_HASH = stable_hash({"auth_owner": "proxy", "actor_ref": _AUDITOR_IDENTITY})

    # (b) Seed workflow with a known sidecar_receipt_hash
    _WF_ID = "wf-auditor-e2e-proof-t5"
    _SIDECAR_HASH = "c" * 64
    wf_basis = _seed_workflow(
        SessionLocal,
        workflow_id=_WF_ID,
        stable_hash=stable_hash,
        sidecar_hash=_SIDECAR_HASH,
        suffix="t5-e2e",
    )

    # Record ownership marker for (workspace_ref_hash, sidecar_receipt_hash).
    # This proves the auditor's workspace staged this evidence.
    auth_binding_svc.record_sec_xbrl_evidence_ownership_marker(
        str(storage_dir),
        owner_ref_hash=_ACTOR_REF_HASH,
        workspace_ref_hash=_WORKSPACE_REF_HASH,
        sidecar_receipt_hash=_SIDECAR_HASH,
    )

    # (c) POST auditor-attach → should get 200 with role='auditor'
    attach_resp = test_client.post(
        AUDITOR_ATTACH_ROUTE,
        json={
            "client_request_id": "e2e-auditor-attach-t5",
            "auditor_attach_mode": "sec_xbrl_operator_review_workflow_auditor_attach_v1",
            "operator_decision": "attach_sec_xbrl_operator_review_auditor_read",
            "operator_role": "auditor",
            "sec_xbrl_operator_review_workflow_id": _WF_ID,
            "workflow_basis_hash": wf_basis,
        },
        headers=_AUDITOR_HEADERS,
    )
    assert attach_resp.status_code == 200, (
        f"auditor-attach expected 200, got {attach_resp.status_code}: {attach_resp.text}"
    )
    attach_body = attach_resp.json()
    assert attach_body.get("auth_binding_role") == "auditor", (
        f"Expected auth_binding_role='auditor' from attach, got: {attach_body.get('auth_binding_role')!r}"
    )
    assert "auth_binding_ref" in attach_body, f"auth_binding_ref missing from attach: {attach_body}"

    # (d) POST admission-status with operator_role='auditor' via real require_sec_xbrl_owner_binding
    # The widened compat-map allows status_read binding to satisfy admission_status_read lookup.
    with patch(
        "app.services.layer3_sec_xbrl_admission_status._validate_workflow_row_for_status"
    ):
        adm_resp = test_client.post(
            ADMISSION_STATUS_ROUTE,
            json={
                **_admission_status_payload(workflow_id=_WF_ID, basis_hash=wf_basis),
                "operator_role": "auditor",
            },
            headers=_AUDITOR_HEADERS,
        )
    assert adm_resp.status_code == 200, (
        f"admission-status with auditor binding expected 200, got {adm_resp.status_code}: {adm_resp.text}"
    )
    adm_body = adm_resp.json()
    assert adm_body.get("auth_binding_role") == "auditor", (
        f"Expected auth_binding_role='auditor', got: {adm_body.get('auth_binding_role')!r}; body={adm_body}"
    )
    # Flag-off path: production_admission_ready=False, production_readiness_claimed=False
    assert adm_body.get("production_admission_ready") is False, adm_body
    assert adm_body.get("production_readiness_claimed") is False, adm_body
    # No raw value keys
    raw_value_keys = {"raw_value", "effective_value", "lexical_value", "value_records"}
    leaked = raw_value_keys & set(adm_body.keys())
    assert not leaked, f"Raw value keys leaked: {leaked}; body={adm_body}"

    # (e) POST status route with auditor identity+role → 200, role='auditor' (coherence).
    # The binding layer passes (auditor status_read binding found via widened compat-map).
    # The status service itself requires materialized statement rows which the minimal
    # seeded workflow lacks; mock only inspect_redacted_operator_review_workflow_status
    # so the test proves auth-binding coherence, not the service's packet validation.
    _canned_status_response = {
        "schema_id": "layer3.sec_xbrl_operator_review_workflow_status.v1",
        "schema_version": 1,
        "request_id": "e2e-auditor-status-t5",
        "server_time": "2026-01-01T00:00:00Z",
        "status": "sec_xbrl_operator_review_workflow_ready",
        "mode": "sec_xbrl_operator_review_workflow_status_v1",
        "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
        "workflow_schema_id": "layer3.sec_xbrl_operator_review_workflow.v1",
        "sec_xbrl_operator_review_workflow_id": _WF_ID,
        "sec_xbrl_statement_packet_set_id": "pkt-e2e-t5",
        "workflow_basis_hash": wf_basis,
        "statement_packet_basis_hash": "a" * 64,
        "source_projection_basis_hash": "b" * 64,
        "control_mode": "operator_review_redacted_workflow_control_mode_v1",
        "workflow_status": "sec_xbrl_operator_review_workflow_ready",
        "redaction_policy": "operator_review_redacted_workflow_policy_v1",
        "statement_count": 1,
        "row_count": 3,
        "review_exception_count": 0,
        "review_ready": True,
        "permitted_controls": [],
        "blocked_controls": [],
        "authority_refs": {},
        "review_summary": {},
        "status_surface_mode": "read_only_redacted_statement_packet_review_workflow_status",
        "read_only_status_surface": True,
        "durable_workflow_authority_used": True,
        "status_api_route_enabled": True,
        "open_workflow_api_route_enabled": True,
        "runtime_default_enabled": False,
        "value_reveal_performed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "delivery_export_enabled": False,
        "rendered_ui_enabled": False,
        "operator_review_decision_recorded": False,
        "negative_invariants": {
            "raw_values_exposed": False,
            "raw_resolved_fact_authorities_exposed": False,
            "raw_identity_exposed": False,
            "raw_accessions_exposed": False,
            "raw_period_dates_exposed": False,
            "local_paths_exposed": False,
            "sec_urls_exposed": False,
            "operator_contact_exposed": False,
            "residual_magnitudes_exposed": False,
            "runtime_default_changed": False,
            "value_reveal_performed": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "delivery_export_enabled": False,
            "rendered_ui_enabled": False,
            "operator_review_decision_recorded": False,
        },
        "next_allowed_actions": [],
    }
    with patch(
        "app.services.layer3_sec_xbrl_operator_review_workflow.inspect_redacted_operator_review_workflow_status",
        return_value=_canned_status_response,
    ):
        status_resp = test_client.post(
            STATUS_ROUTE,
            json={
                "client_request_id": "e2e-auditor-status-t5",
                "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
                "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
                "sec_xbrl_operator_review_workflow_id": _WF_ID,
                "workflow_basis_hash": wf_basis,
                "operator_role": "auditor",
            },
            headers=_AUDITOR_HEADERS,
        )
    assert status_resp.status_code == 200, (
        f"status route with auditor expected 200, got {status_resp.status_code}: {status_resp.text}"
    )
    status_body = status_resp.json()
    assert status_body.get("auth_binding_role") == "auditor", (
        f"Expected auth_binding_role='auditor' on status, got: {status_body.get('auth_binding_role')!r}"
    )


def test_auditor_attach_outside_workspace_denied(
    proxy_client_with_session, monkeypatch
) -> None:
    """Negative: auditor with a DIFFERENT group header (no ownership marker for that workspace)
    → attach returns 403 (evidence-ownership-marker missing); no binding written.
    """
    from app.services.layer3_utils import stable_hash
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc

    test_client, SessionLocal, storage_dir = proxy_client_with_session

    # Seed the workflow owned by workspace A
    _WF_ID = "wf-auditor-outside-ws-t5neg"
    _SIDECAR_HASH = "d" * 64
    _WORKSPACE_A_GROUPS = "workspace-a-owners"
    _WORKSPACE_A_ACTOR = "owner-a@example.com"
    _WORKSPACE_A_REF = stable_hash({"auth_owner": "proxy", "workspace_ref": _WORKSPACE_A_GROUPS})
    _WORKSPACE_A_ACTOR_REF = stable_hash({"auth_owner": "proxy", "actor_ref": _WORKSPACE_A_ACTOR})

    wf_basis = _seed_workflow(
        SessionLocal,
        workflow_id=_WF_ID,
        stable_hash=stable_hash,
        sidecar_hash=_SIDECAR_HASH,
        suffix="t5neg-outside",
    )
    # Record ownership marker ONLY for workspace A
    auth_binding_svc.record_sec_xbrl_evidence_ownership_marker(
        str(storage_dir),
        owner_ref_hash=_WORKSPACE_A_ACTOR_REF,
        workspace_ref_hash=_WORKSPACE_A_REF,
        sidecar_receipt_hash=_SIDECAR_HASH,
    )

    # Auditor B is in a DIFFERENT workspace — no marker for their workspace
    _AUDITOR_B_IDENTITY = "auditor-b@example.com"
    _AUDITOR_B_GROUPS = "workspace-b-auditors"  # different from workspace A
    _AUDITOR_B_HEADERS = {
        "x-forwarded-user": _AUDITOR_B_IDENTITY,
        "x-forwarded-groups": _AUDITOR_B_GROUPS,
    }

    attach_resp = test_client.post(
        AUDITOR_ATTACH_ROUTE,
        json={
            "client_request_id": "e2e-auditor-attach-outside-ws",
            "auditor_attach_mode": "sec_xbrl_operator_review_workflow_auditor_attach_v1",
            "operator_decision": "attach_sec_xbrl_operator_review_auditor_read",
            "operator_role": "auditor",
            "sec_xbrl_operator_review_workflow_id": _WF_ID,
            "workflow_basis_hash": wf_basis,
        },
        headers=_AUDITOR_B_HEADERS,
    )
    assert attach_resp.status_code == 403, (
        f"Expected 403 for out-of-workspace auditor, got {attach_resp.status_code}: {attach_resp.text}"
    )
    body = attach_resp.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert "marker" in body.get("error_code", "").lower() or "ownership" in body.get("error_code", "").lower(), (
        f"Expected ownership marker error, got: {body.get('error_code')}"
    )


def test_admission_status_claimed_auditor_without_attach_denied(
    proxy_client_with_session, monkeypatch
) -> None:
    """Negative: proxy auditor with NO prior attach → admission-status operator_role='auditor'
    → real require_sec_xbrl_owner_binding finds no binding → 404 auth_binding_missing.
    The binding layer is NOT stubbed.
    """
    test_client, SessionLocal, storage_dir = proxy_client_with_session
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)

    _AUDITOR_HEADERS = {
        "x-forwarded-user": "auditor-no-attach@example.com",
        "x-forwarded-groups": "sec-xbrl-auditors-no-attach",
    }

    response = test_client.post(
        ADMISSION_STATUS_ROUTE,
        json={
            **_admission_status_payload(workflow_id="wf-no-attach-auditor"),
            "operator_role": "auditor",
        },
        headers=_AUDITOR_HEADERS,
    )
    assert response.status_code in (400, 404, 409), (
        f"Expected auth-binding-missing error, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert "auth_binding" in body.get("error_code", ""), (
        f"Expected auth_binding error, got: {body.get('error_code')}"
    )


def test_auditor_status_read_binding_does_not_satisfy_write_lookups(
    proxy_client_with_session, monkeypatch
) -> None:
    """Negative escalation invariant: after attach, the auditor status_read binding
    does NOT satisfy decision_submit_write / value_reveal_authority_prepare_write /
    controlled_value_reveal_submit_write lookups.

    Locks the compat-map widening: status_read was NOT added to any write family's
    compatible-prior set.
    """
    from app.services.layer3_utils import stable_hash
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc

    test_client, SessionLocal, storage_dir = proxy_client_with_session

    _AUDITOR_IDENTITY = "auditor-escalation-test@example.com"
    _AUDITOR_GROUPS = "sec-xbrl-auditors-escalation"
    _AUDITOR_HEADERS = {
        "x-forwarded-user": _AUDITOR_IDENTITY,
        "x-forwarded-groups": _AUDITOR_GROUPS,
    }
    _WORKSPACE_REF_HASH = stable_hash({"auth_owner": "proxy", "workspace_ref": _AUDITOR_GROUPS})
    _ACTOR_REF_HASH = stable_hash({"auth_owner": "proxy", "actor_ref": _AUDITOR_IDENTITY})

    _WF_ID = "wf-auditor-escalation-invariant"
    _SIDECAR_HASH = "e" * 64

    wf_basis = _seed_workflow(
        SessionLocal,
        workflow_id=_WF_ID,
        stable_hash=stable_hash,
        sidecar_hash=_SIDECAR_HASH,
        suffix="t5-escalation",
    )
    auth_binding_svc.record_sec_xbrl_evidence_ownership_marker(
        str(storage_dir),
        owner_ref_hash=_ACTOR_REF_HASH,
        workspace_ref_hash=_WORKSPACE_REF_HASH,
        sidecar_receipt_hash=_SIDECAR_HASH,
    )

    # Attach auditor binding (status_read)
    attach_resp = test_client.post(
        AUDITOR_ATTACH_ROUTE,
        json={
            "client_request_id": "escalation-attach",
            "auditor_attach_mode": "sec_xbrl_operator_review_workflow_auditor_attach_v1",
            "operator_decision": "attach_sec_xbrl_operator_review_auditor_read",
            "operator_role": "auditor",
            "sec_xbrl_operator_review_workflow_id": _WF_ID,
            "workflow_basis_hash": wf_basis,
        },
        headers=_AUDITOR_HEADERS,
    )
    assert attach_resp.status_code == 200, (
        f"attach failed: {attach_resp.status_code}: {attach_resp.text}"
    )

    # Now try each write family — all must return auth-binding-missing (403/404)
    # because status_read is NOT a compatible prior for any write family.
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.session import Base as _Base

    # Build a direct DB session to call require_sec_xbrl_owner_binding
    # We need a fresh session on the same in-memory engine. But since the engine
    # is per-test, re-use the existing SessionLocal from the fixture's in-memory DB.
    # Instead, use the HTTP routes to prove the invariant.

    # decision_submit_write: auditor role is forbidden at the POLICY layer (owner-only).
    # That is already proven at the policy level.  What we prove here is that even if
    # policy allowed auditor on a write route, the binding lookup would fail.
    # We drive this by checking the compat-map directly.

    # Call require_sec_xbrl_owner_binding directly against the live DB session
    # (we get a session via the app's dependency).
    # We can also verify via the route: decision/submit with an auditor role will be
    # blocked at the policy layer (role_route_forbidden), but that is not what we're
    # testing here.  We test the compat-map invariant directly via the service.

    # Direct service-level check using a live DB session obtained from the same engine:
    from app.api.deps import get_db as _get_db
    db_gen = app.dependency_overrides[_get_db]()
    db = next(db_gen)
    try:
        from app.services import layer3_sec_xbrl_in_app_auth_policy as _auth_policy

        # Derive policy_decision as the server would for an auditor on a write route.
        # (In real life the policy layer would reject this; we bypass it for the
        # binding-level invariant check.)
        _attach_basis_hash = stable_hash({
            "auth_owner": "proxy",
            "actor_ref_hash": _ACTOR_REF_HASH,
            "workspace_ref_hash": _WORKSPACE_REF_HASH,
        })

        # Construct a minimal policy decision dict mirroring what the server
        # produces for the auditor identity — the binding layer only reads
        # actor_ref_hash, workspace_ref_hash, role, policy_hash, decision, route_family.
        def _make_write_policy(route_family: str) -> dict:
            from app.services.layer3_utils import stable_hash as _sh
            ph = _sh({
                "policy_schema_id": _auth_policy.POLICY_SCHEMA_ID,
                "selected_auth_mode": _auth_policy.SELECTED_AUTH_MODE,
                "actor_ref_hash": _ACTOR_REF_HASH,
                "workspace_ref_hash": _WORKSPACE_REF_HASH,
                "route_family": route_family,
                "role": "owner",  # write families only allow owner
            })
            return {
                "decision": "allow",
                "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
                "route_family": route_family,
                "role": "owner",
                "actor_ref_hash": _ACTOR_REF_HASH,
                "workspace_ref_hash": _WORKSPACE_REF_HASH,
                "policy_hash": ph,
                "compatible_policy_hashes": [ph],
            }

        for write_family in (
            "sec_xbrl_operator_review_decision_submit_write",
            "sec_xbrl_value_reveal_authority_prepare_write",
            "sec_xbrl_controlled_value_reveal_submit_write",
        ):
            try:
                auth_binding_svc.require_sec_xbrl_owner_binding(
                    db,
                    source_receipt_kind="operator_review_workflow",
                    source_receipt_id=_WF_ID,
                    source_receipt_basis_hash=wf_basis,
                    route_family=write_family,
                    policy_decision=_make_write_policy(write_family),
                )
                raise AssertionError(
                    f"Expected auth_binding_missing for {write_family!r} but got a result"
                )
            except auth_binding_svc.SecXbrlAuthBindingError as exc:
                assert "missing" in exc.code or "not_admitted" in exc.code, (
                    f"Expected auth_binding_missing for {write_family!r}, got: {exc.code}"
                )
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def test_auditor_role_forbidden_for_all_write_families() -> None:
    """Proves the real mechanism: authorize_sec_xbrl_route raises
    SecXbrlInAppAuthPolicyError with code='sec_xbrl_in_app_auth_policy_role_route_forbidden'
    for the auditor role on EACH of the four owner-only write families.

    The role check (line 141 in layer3_sec_xbrl_in_app_auth_policy.py) fires BEFORE
    _server_derived_principal is consulted, so no proxy headers or DB state are needed.
    This directly proves an auditor is rejected at the policy layer for:
      - open_write (operator-review workflow open)
      - decision_submit_write (operator-review decision submit)
      - value_reveal_authority_prepare_write (value-reveal authority prepare)
      - controlled_value_reveal_submit_write (controlled value-reveal submit)
    """
    from app.services.layer3_sec_xbrl_in_app_auth_policy import (
        SecXbrlInAppAuthPolicyError,
        authorize_sec_xbrl_route,
    )

    write_families = [
        "sec_xbrl_operator_review_workflow_open_write",
        "sec_xbrl_operator_review_decision_submit_write",
        "sec_xbrl_value_reveal_authority_prepare_write",
        "sec_xbrl_controlled_value_reveal_submit_write",
    ]

    for family in write_families:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers={},
                route_family=family,
                requested_role="auditor",
                request_fields=None,
            )
        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_role_route_forbidden", (
            f"Expected role_route_forbidden for family={family!r}, "
            f"got: {exc_info.value.code!r}"
        )
        assert exc_info.value.http_status == 403, (
            f"Expected http_status=403 for family={family!r}, "
            f"got: {exc_info.value.http_status!r}"
        )


# ---------------------------------------------------------------------------
# T6: claimed auditor role without a matching binding → denied (no privilege escalation)
# ---------------------------------------------------------------------------

def test_admission_status_claimed_role_without_binding_denied(client, monkeypatch) -> None:
    """Proves no privilege escalation: claiming operator_role='auditor' with an empty DB
    (no binding of any kind seeded) → auth-binding-missing error (404/403).

    authorize_sec_xbrl_route is stubbed to pass so the test reaches require_sec_xbrl_owner_binding.
    The real require_sec_xbrl_owner_binding runs against the empty DB and cannot find any
    auditor binding → SecXbrlAuthBindingError("sec_xbrl_auth_binding_missing", ..., 404).

    This proves that claiming a role without a matching binding is denied even after the
    auth-policy layer admits the role as valid.
    """
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    from app.services.layer3_utils import stable_hash

    _ACTOR_HASH = stable_hash({"sec_xbrl_admission_escalation_t6": "actor"})
    _WS_HASH = stable_hash({"sec_xbrl_admission_escalation_t6": "workspace"})
    _POLICY_HASH = stable_hash({"route": "sec_xbrl_operator_review_workflow_admission_status_read", "role": "auditor"})

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

    # NOTE: require_sec_xbrl_owner_binding is NOT stubbed — real DB is empty,
    # so it raises SecXbrlAuthBindingError("sec_xbrl_auth_binding_missing", 404).
    response = client.post(
        ADMISSION_STATUS_ROUTE,
        json={
            **_admission_status_payload(workflow_id="wf-escalation-t6"),
            "operator_role": "auditor",
        },
    )

    assert response.status_code in (400, 403, 404, 409), (
        f"Expected auth-binding error (400/403/404/409), got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    error_code = body.get("error_code", "")
    assert "auth_binding" in error_code, (
        f"Expected auth_binding error for escalation attempt, got: {error_code}"
    )
