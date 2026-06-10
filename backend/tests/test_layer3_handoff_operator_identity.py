from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import settings
from app.db.session import Base
from main import app

_SEAM_CODES = {
    "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity",
    "sec_xbrl_in_app_auth_policy_missing_identity_authority",
    "sec_xbrl_in_app_auth_policy_missing_workspace_authority",
}

_API = "/api/v1/layer3"

_POST_PATHS = [
    "/handoff/export/prepare",
    "/handoff/aps/dispatch",
    "/handoff/export/download/readiness",
    "/handoff/export/download/prepare",
    "/handoff/connector/record",
    "/handoff/connector/local-destination/receipt",
    "/handoff/connector/local-outbox/fake-target",
    "/handoff/connector/local-outbox/write",
    "/handoff/connector/local-outbox/provider-private/prepare",
    "/handoff/connector/local-outbox/external-local-export/write",
    "/handoff/export/internal-webhook/dispatch",
    "/handoff/export/download/signed-reference/generate",
    "/handoff/export/download/provider-private-signed-url/prepare",
    "/handoff/export/download/provider-private-signed-url/revoke",
    "/handoff/export/download/provider-public-url/prepare",
    "/handoff/export/download/provider-public-url/revoke",
    "/handoff/export/download/provider-public-url/use",
    "/handoff/export/download/deliver",
    "/handoff/export/download/signed-reference/use",
]

_DELIVER_PATH = "/handoff/export/download/deliver"
_SIGNED_REF_USE_PATH = "/handoff/export/download/signed-reference/use"
_FILE_RESPONSE_PATHS = {_DELIVER_PATH, _SIGNED_REF_USE_PATH}

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"

_CANARY_IDENTITY = "leak-canary-operator@example.invalid"
_CANARY_GROUPS = "leak-canary-groups-sentinel@example.invalid"

_DELIVER_MIN_BODY = {
    "client_request_id": "r1",
    "session_id": "s1",
    "analysis_plan_id": "ap1",
    "pass_run_id": "pr1",
    "preview_id": "pv1",
    "preview_hash": "ph1",
    "material_preview_id": "mpv1",
    "material_preview_hash": "mph1",
    "contract_hash": "ch1",
    "result_review_record_ref": "rr1",
    "package_review_preview_hash": "prph1",
    "reconciliation_record_id": "rc1",
    "output_package_ids": ["op1"],
    "package_kinds": ["canonical_internal"],
    "payload_refs": ["ref1"],
    "payload_hashes": ["hash1"],
    "package_review_submit_record_ref": "prs1",
    "package_review_state": "package_review_approved",
    "prepare_record_ref": "prep1",
    "handoff_export_state": "handoff_export_prepared",
    "handoff_export_envelope_ref": "env1",
    "handoff_target": "aps_evidence_bundle",
    "export_mode": "reference_envelope_only",
    "aps_handoff_record_ref": "ahr1",
    "aps_handoff_state": "aps_handoff_dispatched",
    "aps_handoff_target": "aps_evidence_bundle",
    "dispatch_mode": "server_side_aps_handoff",
    "aps_output_package_id": "aop1",
    "aps_output_package_kind": "canonical_internal",
    "aps_bundle_ref": "abr1",
    "aps_bundle_id": "abi1",
    "aps_schema_id": "asi1",
    "external_export_download_record_ref": "eedr1",
    "export_download_descriptor_ref": "eddr1",
    "external_export_download_state": "external_export_download_prepared",
    "export_download_target": "aps_evidence_bundle_download_reference",
    "download_mode": "reference_only_prepare",
    "delivery_mode": "same_origin_artifact_stream",
    "operator_decision": "deliver_external_export_download",
}

_SIGNED_REF_USE_MIN_BODY = {"signed_reference_token": "tok1"}

_ROUTE_BODY_OVERRIDES: dict[str, dict] = {
    _DELIVER_PATH: _DELIVER_MIN_BODY,
    _SIGNED_REF_USE_PATH: _SIGNED_REF_USE_MIN_BODY,
}


def _body_for(path: str) -> dict:
    return _ROUTE_BODY_OVERRIDES.get(path, {})


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "elo"))
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/stub")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "stub-webhook")
    engine = create_engine(
        "sqlite://",
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
    tc = TestClient(app, raise_server_exceptions=False)
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def proxy_untrusted_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "elo"))
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/stub")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "stub-webhook")
    engine = create_engine(
        "sqlite://",
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
    tc = TestClient(app, raise_server_exceptions=False)
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def proxy_trusted_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "elo"))
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/stub")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "stub-webhook")
    engine = create_engine(
        "sqlite://",
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
    tc = TestClient(app, raise_server_exceptions=False)
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize("path", _POST_PATHS)
def test_409_untrusted_proxy_sweep(proxy_untrusted_client, path):
    body = _body_for(path)
    headers = {
        _IDENTITY_HEADER: _CANARY_IDENTITY,
        _GROUPS_HEADER: _CANARY_GROUPS,
    }
    resp = proxy_untrusted_client.post(
        _API + path,
        json=body,
        headers=headers,
    )
    assert resp.status_code == 409, f"{path}: expected 409 got {resp.status_code}"
    assert resp.headers.get("content-type", "").startswith("application/json"), path
    data = resp.json()
    assert data.get("error_code") == "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity", path
    body_text = resp.text
    assert _CANARY_IDENTITY not in body_text, f"{path}: identity canary leaked"
    assert _CANARY_GROUPS not in body_text, f"{path}: groups canary leaked"


@pytest.mark.parametrize("path", _POST_PATHS)
def test_401_missing_identity_sweep(proxy_trusted_client, path):
    body = _body_for(path)
    headers = {_GROUPS_HEADER: _CANARY_GROUPS}
    resp = proxy_trusted_client.post(
        _API + path,
        json=body,
        headers=headers,
    )
    assert resp.status_code == 401, f"{path}: expected 401 got {resp.status_code}"
    assert resp.headers.get("content-type", "").startswith("application/json"), path
    data = resp.json()
    assert data.get("error_code") == "sec_xbrl_in_app_auth_policy_missing_identity_authority", path
    assert _CANARY_GROUPS not in resp.text, f"{path}: groups canary leaked"


def test_401_missing_workspace_authority(proxy_trusted_client):
    path = "/handoff/export/prepare"
    headers = {_IDENTITY_HEADER: "operator@example.com"}
    resp = proxy_trusted_client.post(
        _API + path,
        json={},
        headers=headers,
    )
    assert resp.status_code == 401
    assert resp.headers.get("content-type", "").startswith("application/json")
    data = resp.json()
    assert data.get("error_code") == "sec_xbrl_in_app_auth_policy_missing_workspace_authority"


@pytest.mark.parametrize("path", _POST_PATHS)
def test_none_mode_inertness_sweep(client, path):
    body = _body_for(path)
    resp = client.post(_API + path, json=body)
    ct = resp.headers.get("content-type", "")
    if ct.startswith("application/json"):
        try:
            data = resp.json()
        except Exception:
            return
        if isinstance(data, dict) and "error_code" in data:
            assert data["error_code"] not in _SEAM_CODES, (
                f"{path}: seam error fired under none mode: {data['error_code']}"
            )
    assert resp.status_code != 401, f"{path}: got 401 under none mode"


def test_422_precedence_untrusted_proxy_forbid_model(proxy_untrusted_client):
    headers = {
        _IDENTITY_HEADER: _CANARY_IDENTITY,
        _GROUPS_HEADER: _CANARY_GROUPS,
    }
    resp = proxy_untrusted_client.post(
        _API + "/handoff/export/prepare",
        json={"__unknown_forbidden_field__": "value"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert _CANARY_IDENTITY not in resp.text
    assert _CANARY_GROUPS not in resp.text


def test_422_precedence_untrusted_proxy_forbid_model_connector_record(proxy_untrusted_client):
    headers = {
        _IDENTITY_HEADER: _CANARY_IDENTITY,
        _GROUPS_HEADER: _CANARY_GROUPS,
    }
    resp = proxy_untrusted_client.post(
        _API + "/handoff/connector/record",
        json={"__unknown_forbidden_field__": "value"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert _CANARY_IDENTITY not in resp.text
    assert _CANARY_GROUPS not in resp.text


def test_file_response_routes_409_content_type(proxy_untrusted_client):
    for path in _FILE_RESPONSE_PATHS:
        body = _body_for(path)
        headers = {
            _IDENTITY_HEADER: _CANARY_IDENTITY,
            _GROUPS_HEADER: _CANARY_GROUPS,
        }
        resp = proxy_untrusted_client.post(
            _API + path,
            json=body,
            headers=headers,
        )
        assert resp.status_code == 409, f"{path}: expected 409 got {resp.status_code}"
        assert resp.headers.get("content-type", "").startswith("application/json"), (
            f"{path}: expected application/json, got {resp.headers.get('content-type')}"
        )


def test_file_response_routes_401_content_type(proxy_trusted_client):
    for path in _FILE_RESPONSE_PATHS:
        body = _body_for(path)
        headers = {_GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_trusted_client.post(
            _API + path,
            json=body,
            headers=headers,
        )
        assert resp.status_code == 401, f"{path}: expected 401 got {resp.status_code}"
        assert resp.headers.get("content-type", "").startswith("application/json"), (
            f"{path}: expected application/json, got {resp.headers.get('content-type')}"
        )
