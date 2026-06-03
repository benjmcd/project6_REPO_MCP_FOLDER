from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.layer3 import router as layer3_router
from app.core.config import settings
from app.api.deps import get_db
from app.db.session import Base
from app.models import (
    L3SecXbrlAuthBindingReceipt,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketSet,
)
from app.services import (
    layer3_sec_xbrl_auth_binding,
    layer3_sec_xbrl_operator_review_api,
)
from test_sec_xbrl_e2e_offline_orchestrator import _evidence


OPEN_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open"
VALID_HASH = "a" * 64


@pytest.fixture()
def api_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    previous_flag = settings.layer3_sec_xbrl_operator_review_workflow_open_enabled
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        False,
    )
    layer3_sec_xbrl_operator_review_api.clear_sec_xbrl_operator_review_authority_registry()
    app = FastAPI()
    app.include_router(layer3_router, prefix="/api/v1/layer3")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, db, monkeypatch
    finally:
        monkeypatch.setattr(
            settings,
            "layer3_sec_xbrl_operator_review_workflow_open_enabled",
            previous_flag,
        )
        layer3_sec_xbrl_operator_review_api.clear_sec_xbrl_operator_review_authority_registry()
        app.dependency_overrides.pop(get_db, None)
        db.close()


def _payload(**overrides):
    payload = {
        "client_request_id": "open-workflow-request-1",
        "open_mode": "sec_xbrl_operator_review_workflow_open_v1",
        "operator_decision": "open_sec_xbrl_operator_review_workflow_from_authority",
        "operator_review_authority_handle": "srv-redacted-fizz-10k-proof",
        "proof_source_report_hash": VALID_HASH,
        "period_limit": 3,
    }
    payload.update(overrides)
    return payload


def _count(db, model):
    return db.query(model).count()


def _assert_no_persistence(db):
    assert _count(db, L3SecXbrlProjectionSet) == 0
    assert _count(db, L3SecXbrlStatementPacketSet) == 0
    assert _count(db, L3SecXbrlOperatorReviewWorkflow) == 0
    assert _count(db, L3SecXbrlAuthBindingReceipt) == 0


def test_operator_review_open_api_default_off_blocks_without_persistence(api_client):
    client, db, _monkeypatch = api_client

    response = client.post(OPEN_ROUTE, json=_payload())

    assert response.status_code == 409
    body = response.json()
    assert (
        body["error_code"]
        == "sec_xbrl_operator_review_workflow_open_feature_flag_disabled"
    )
    _assert_no_persistence(db)


def test_operator_review_open_api_rejects_raw_or_extra_request_fields(api_client):
    client, db, monkeypatch = api_client
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        True,
    )

    response = client.post(
        OPEN_ROUTE,
        json=_payload(storage_dir="C:/raw/sec/archive", companyfacts={"raw": True}),
    )

    assert response.status_code == 400
    body = response.json()
    assert (
        body["error_code"]
        == "sec_xbrl_operator_review_workflow_open_request_fields_not_admitted"
    )
    assert body["blocked_fields"] == ["companyfacts", "storage_dir"]
    _assert_no_persistence(db)


def test_operator_review_open_api_creates_workflow_and_auth_binding(api_client):
    client, db, monkeypatch = api_client
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        True,
    )
    layer3_sec_xbrl_operator_review_api.register_sec_xbrl_operator_review_authority_evidence(
        "srv-redacted-fizz-10k-proof",
        _evidence(),
        proof_source_report_hash=VALID_HASH,
    )

    response = client.post(OPEN_ROUTE, json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["sec_xbrl_operator_review_workflow_id"]
    assert body["workflow_basis_hash"]
    assert body["auth_binding_ref"]
    assert (
        body["auth_binding_route_family"]
        == "sec_xbrl_operator_review_workflow_open_write"
    )
    assert body["operator_review_open_api_route_enabled"] is True
    assert body["operator_review_authority_registered"] is True
    assert body["operator_review_authority_source_hash_matched"] is True
    assert body["status_api_route_enabled"] is True
    assert body["rendered_ui_enabled"] is False
    assert body["runtime_default_enabled"] is False
    assert body["value_reveal_performed"] is False
    assert body["source_acquisition_performed"] is False
    assert body["arelle_invoked"] is False
    assert body["production_readiness_claimed"] is False
    assert _count(db, L3SecXbrlProjectionSet) == 1
    assert _count(db, L3SecXbrlStatementPacketSet) == 1
    assert _count(db, L3SecXbrlOperatorReviewWorkflow) == 1
    assert _count(db, L3SecXbrlAuthBindingReceipt) == 1


def test_operator_review_open_api_rolls_back_workflow_when_auth_binding_fails(
    api_client,
):
    client, db, monkeypatch = api_client
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        True,
    )
    layer3_sec_xbrl_operator_review_api.register_sec_xbrl_operator_review_authority_evidence(
        "srv-redacted-fizz-10k-proof",
        _evidence(),
        proof_source_report_hash=VALID_HASH,
    )

    def fail_binding(*_args, **_kwargs):
        raise layer3_sec_xbrl_auth_binding.SecXbrlAuthBindingError(
            "sec_xbrl_auth_binding_forced_failure",
            "forced auth binding failure",
            http_status=409,
        )

    monkeypatch.setattr(
        layer3_sec_xbrl_auth_binding,
        "record_sec_xbrl_auth_binding",
        fail_binding,
    )

    response = client.post(OPEN_ROUTE, json=_payload())

    assert response.status_code == 409
    assert response.json()["error_code"] == "sec_xbrl_auth_binding_forced_failure"
    _assert_no_persistence(db)


def test_operator_review_open_api_unknown_registered_handle_fails_closed(api_client):
    client, db, monkeypatch = api_client
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        True,
    )
    layer3_sec_xbrl_operator_review_api.register_sec_xbrl_operator_review_authority_evidence(
        "srv-redacted-other-proof",
        _evidence(),
        proof_source_report_hash=VALID_HASH,
    )

    response = client.post(OPEN_ROUTE, json=_payload())

    assert response.status_code == 404
    assert response.json()["error_code"] == "sec_xbrl_operator_review_open_authority_handle_unknown"
    _assert_no_persistence(db)


def test_operator_review_open_api_rejects_registered_source_hash_mismatch(api_client):
    client, db, monkeypatch = api_client
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        True,
    )
    layer3_sec_xbrl_operator_review_api.register_sec_xbrl_operator_review_authority_evidence(
        "srv-redacted-fizz-10k-proof",
        _evidence(),
        proof_source_report_hash="b" * 64,
    )

    response = client.post(OPEN_ROUTE, json=_payload())

    assert response.status_code == 409
    assert response.json()["error_code"] == "sec_xbrl_operator_review_open_authority_hash_mismatch"
    _assert_no_persistence(db)


def test_operator_review_open_api_rejects_raw_authority_handle(api_client):
    client, db, monkeypatch = api_client
    monkeypatch.setattr(
        settings,
        "layer3_sec_xbrl_operator_review_workflow_open_enabled",
        True,
    )

    response = client.post(
        OPEN_ROUTE,
        json=_payload(operator_review_authority_handle=r"C:\raw\sec\filing.json"),
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "sec_xbrl_operator_review_open_authority_handle_not_admitted"
    _assert_no_persistence(db)
