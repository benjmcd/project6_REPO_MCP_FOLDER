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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API = "/api/v1/layer3"

# The new projection endpoint under test (served at _API + this path)
_ME_PATH = "/operator/identity"

# Representative routes — one from each family.
# Handoff and package POST routes have all-optional Pydantic models so the auth
# seam fires before business-logic validation.  Source_ingestion POST models all
# have required fields, so FastAPI's 422 precedes the seam; we use the GET
# source/intake/inventory route which is in source_ingestion.py and exercises
# the identical seam.
_HANDOFF_POST = "/handoff/export/prepare"
_PACKAGE_POST = "/package/review/preview"
_SOURCE_ROUTE = "/source/intake/inventory"  # GET — seam fires before DB lookup

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_ROLES_HEADER = "X-Forwarded-Roles"

_CANARY_IDENTITY = "leak-canary-operator@example.invalid"
_CANARY_GROUPS = "leak-canary-groups-sentinel@example.invalid"

_SCHEMA_ID = "layer3.operator_identity_projection.v1"

# Error codes emitted by the auth seam
_CODE_UNTRUSTED = "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
_CODE_MISSING_IDENTITY = "sec_xbrl_in_app_auth_policy_missing_identity_authority"
_CODE_MISSING_WORKSPACE = "sec_xbrl_in_app_auth_policy_missing_workspace_authority"
_CODE_MISSING_ROLE = "sec_xbrl_in_app_auth_policy_missing_role_authority"
_CODE_ROLE_FORBIDDEN = "sec_xbrl_in_app_auth_policy_role_access_forbidden"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_client(tmp_path, monkeypatch, **overrides):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "elo"))
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/stub")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "stub-webhook")
    for attr, value in overrides.items():
        monkeypatch.setattr(settings, attr, value)
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
def client(tmp_path, monkeypatch):
    yield from _make_client(tmp_path, monkeypatch, auth_owner="none")


@pytest.fixture()
def proxy_untrusted_client(tmp_path, monkeypatch):
    yield from _make_client(
        tmp_path, monkeypatch,
        auth_owner="proxy",
        trusted_proxy_mode=False,
    )


@pytest.fixture()
def proxy_trusted_client(tmp_path, monkeypatch):
    yield from _make_client(
        tmp_path, monkeypatch,
        auth_owner="proxy",
        trusted_proxy_mode=True,
        layer3_route_authorization_mode="identity_presence",
    )


@pytest.fixture()
def role_enforcing_client(tmp_path, monkeypatch):
    yield from _make_client(
        tmp_path, monkeypatch,
        auth_owner="proxy",
        trusted_proxy_mode=True,
        layer3_route_authorization_mode="role_enforcing",
    )


# ---------------------------------------------------------------------------
# Helper to assert /me shape in allowed cases
# ---------------------------------------------------------------------------

def _assert_me_shape(data: dict, *, auth_owner: str, authorization_mode: str) -> None:
    assert data.get("schema_id") == _SCHEMA_ID, f"bad schema_id: {data}"
    assert "operator_ref_hash" in data, f"missing operator_ref_hash: {data}"
    assert "workspace_ref_hash" in data, f"missing workspace_ref_hash: {data}"
    assert "auth_owner_mode" in data, f"missing auth_owner_mode: {data}"
    assert "derived_role" in data, f"missing derived_role: {data}"
    assert "authorization_mode" in data, f"missing authorization_mode: {data}"
    assert data["auth_owner"] == auth_owner, f"wrong auth_owner: {data}"
    assert data["authorization_mode"] == authorization_mode, f"wrong mode: {data}"


# ===========================================================================
# SECTION 1 — /me endpoint own matrix
# ===========================================================================

class TestMeEndpoint:
    """Full auth matrix for GET /review/layer3/operator/identity."""

    def test_none_mode_allowed(self, client):
        resp = client.get(_API + _ME_PATH)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        _assert_me_shape(data, auth_owner="none", authorization_mode="identity_presence")
        assert data["derived_role"] is None  # identity_presence returns None role
        assert _CANARY_IDENTITY not in resp.text
        assert _CANARY_GROUPS not in resp.text

    def test_proxy_untrusted_409(self, proxy_untrusted_client):
        headers = {_IDENTITY_HEADER: _CANARY_IDENTITY, _GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_untrusted_client.get(_API + _ME_PATH, headers=headers)
        assert resp.status_code == 409, resp.text
        data = resp.json()
        assert data.get("error_code") == _CODE_UNTRUSTED
        assert _CANARY_IDENTITY not in resp.text
        assert _CANARY_GROUPS not in resp.text

    def test_proxy_trusted_missing_identity_401(self, proxy_trusted_client):
        # No identity header, only groups
        headers = {_GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_trusted_client.get(_API + _ME_PATH, headers=headers)
        assert resp.status_code == 401, resp.text
        data = resp.json()
        assert data.get("error_code") == _CODE_MISSING_IDENTITY
        assert _CANARY_GROUPS not in resp.text

    def test_proxy_trusted_identity_presence_allowed(self, proxy_trusted_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = proxy_trusted_client.get(_API + _ME_PATH, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        _assert_me_shape(data, auth_owner="proxy", authorization_mode="identity_presence")
        assert data["derived_role"] is None  # identity_presence returns None
        # No raw header values echoed in response
        assert "operator@example.com" not in resp.text
        assert "ws-group" not in resp.text

    def test_role_enforcing_missing_roles_header_blocked(self, role_enforcing_client):
        # Identity + workspace present, but no roles header
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = role_enforcing_client.get(_API + _ME_PATH, headers=headers)
        # Policy raises 401 when roles header is missing under role_enforcing
        assert resp.status_code == 401, resp.text
        data = resp.json()
        assert data.get("error_code") == _CODE_MISSING_ROLE

    def test_role_enforcing_insufficient_role_blocked(self, role_enforcing_client, monkeypatch):
        # Set owner_role_tokens to something that won't match "viewer"
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "viewer",  # not owner or auditor
        }
        resp = role_enforcing_client.get(_API + _ME_PATH, headers=headers)
        # Missing recognized role -> 401 from _server_derived_role
        assert resp.status_code == 401, resp.text
        data = resp.json()
        assert data.get("error_code") == _CODE_MISSING_ROLE

    def test_role_enforcing_auditor_read_allowed(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "auditor",
        }
        resp = role_enforcing_client.get(_API + _ME_PATH, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        _assert_me_shape(data, auth_owner="proxy", authorization_mode="role_enforcing")
        assert data["derived_role"] == "auditor"
        assert "operator@example.com" not in resp.text
        assert "ws-group" not in resp.text

    def test_role_enforcing_owner_read_allowed(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "owner",
        }
        resp = role_enforcing_client.get(_API + _ME_PATH, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        _assert_me_shape(data, auth_owner="proxy", authorization_mode="role_enforcing")
        assert data["derived_role"] == "owner"


# ===========================================================================
# SECTION 2 — handoff POST representative route auth matrix
# ===========================================================================

class TestHandoffPostAuthMatrix:
    """Auth matrix for one representative handoff POST route."""

    def test_none_mode_inert(self, client):
        resp = client.post(_API + _HANDOFF_POST, json={})
        # Should not be blocked by seam (any non-seam error is OK)
        if resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            if isinstance(data, dict) and "error_code" in data:
                assert data["error_code"] not in {
                    _CODE_UNTRUSTED, _CODE_MISSING_IDENTITY,
                    _CODE_MISSING_WORKSPACE, _CODE_MISSING_ROLE,
                }, f"seam fired under none mode: {data['error_code']}"
        assert resp.status_code != 401

    def test_proxy_untrusted_409(self, proxy_untrusted_client):
        headers = {_IDENTITY_HEADER: _CANARY_IDENTITY, _GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_untrusted_client.post(_API + _HANDOFF_POST, json={}, headers=headers)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("error_code") == _CODE_UNTRUSTED
        assert _CANARY_IDENTITY not in resp.text
        assert _CANARY_GROUPS not in resp.text

    def test_proxy_trusted_missing_identity_401(self, proxy_trusted_client):
        headers = {_GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_trusted_client.post(_API + _HANDOFF_POST, json={}, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_IDENTITY

    def test_proxy_trusted_identity_presence_allowed(self, proxy_trusted_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = proxy_trusted_client.post(_API + _HANDOFF_POST, json={}, headers=headers)
        # Seam passes; downstream validation may reject the empty body (400/422/etc)
        assert resp.status_code not in {401, 409}, resp.text

    def test_role_enforcing_missing_roles_blocked(self, role_enforcing_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = role_enforcing_client.post(_API + _HANDOFF_POST, json={}, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_ROLE

    def test_role_enforcing_insufficient_role_blocked(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "auditor",  # write route requires owner
        }
        resp = role_enforcing_client.post(_API + _HANDOFF_POST, json={}, headers=headers)
        assert resp.status_code == 403, resp.text
        assert resp.json().get("error_code") == _CODE_ROLE_FORBIDDEN

    def test_role_enforcing_owner_allowed(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "owner",
        }
        resp = role_enforcing_client.post(_API + _HANDOFF_POST, json={}, headers=headers)
        # Seam passes; downstream may reject body content
        assert resp.status_code not in {401, 403, 409}, resp.text


# ===========================================================================
# SECTION 3 — package POST representative route auth matrix
# ===========================================================================

class TestPackagePostAuthMatrix:
    """Auth matrix for one representative package POST route."""

    def test_none_mode_inert(self, client):
        resp = client.post(_API + _PACKAGE_POST, json={})
        if resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            if isinstance(data, dict) and "error_code" in data:
                assert data["error_code"] not in {
                    _CODE_UNTRUSTED, _CODE_MISSING_IDENTITY,
                    _CODE_MISSING_WORKSPACE, _CODE_MISSING_ROLE,
                }
        assert resp.status_code != 401

    def test_proxy_untrusted_409(self, proxy_untrusted_client):
        headers = {_IDENTITY_HEADER: _CANARY_IDENTITY, _GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_untrusted_client.post(_API + _PACKAGE_POST, json={}, headers=headers)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("error_code") == _CODE_UNTRUSTED
        assert _CANARY_IDENTITY not in resp.text
        assert _CANARY_GROUPS not in resp.text

    def test_proxy_trusted_missing_identity_401(self, proxy_trusted_client):
        headers = {_GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_trusted_client.post(_API + _PACKAGE_POST, json={}, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_IDENTITY

    def test_proxy_trusted_identity_presence_allowed(self, proxy_trusted_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = proxy_trusted_client.post(_API + _PACKAGE_POST, json={}, headers=headers)
        assert resp.status_code not in {401, 409}, resp.text

    def test_role_enforcing_missing_roles_blocked(self, role_enforcing_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = role_enforcing_client.post(_API + _PACKAGE_POST, json={}, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_ROLE

    def test_role_enforcing_insufficient_role_blocked(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "auditor",  # write route requires owner
        }
        resp = role_enforcing_client.post(_API + _PACKAGE_POST, json={}, headers=headers)
        assert resp.status_code == 403, resp.text
        assert resp.json().get("error_code") == _CODE_ROLE_FORBIDDEN

    def test_role_enforcing_owner_allowed(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "owner",
        }
        resp = role_enforcing_client.post(_API + _PACKAGE_POST, json={}, headers=headers)
        assert resp.status_code not in {401, 403, 409}, resp.text


# ===========================================================================
# SECTION 4 — source_ingestion representative route auth matrix
# (GET /source/intake/inventory — in source_ingestion.py, access="read")
# ===========================================================================

class TestSourceIngestionAuthMatrix:
    """Auth matrix for the source_ingestion GET route.

    All source_ingestion POST models have required Pydantic fields so FastAPI's
    422 precedes the auth seam.  GET /source/intake/inventory is registered in
    source_ingestion.py, uses _route_level_operator_identity(access='read'),
    and is therefore the appropriate representative for this route family.
    """

    def test_none_mode_inert(self, client):
        resp = client.get(_API + _SOURCE_ROUTE)
        if resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            if isinstance(data, dict) and "error_code" in data:
                assert data["error_code"] not in {
                    _CODE_UNTRUSTED, _CODE_MISSING_IDENTITY,
                    _CODE_MISSING_WORKSPACE, _CODE_MISSING_ROLE,
                }
        assert resp.status_code != 401

    def test_proxy_untrusted_409(self, proxy_untrusted_client):
        headers = {_IDENTITY_HEADER: _CANARY_IDENTITY, _GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_untrusted_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code == 409, resp.text
        assert resp.json().get("error_code") == _CODE_UNTRUSTED
        assert _CANARY_IDENTITY not in resp.text
        assert _CANARY_GROUPS not in resp.text

    def test_proxy_trusted_missing_identity_401(self, proxy_trusted_client):
        headers = {_GROUPS_HEADER: _CANARY_GROUPS}
        resp = proxy_trusted_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_IDENTITY

    def test_proxy_trusted_identity_presence_allowed(self, proxy_trusted_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = proxy_trusted_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code not in {401, 409}, resp.text

    def test_role_enforcing_missing_roles_blocked(self, role_enforcing_client):
        headers = {_IDENTITY_HEADER: "operator@example.com", _GROUPS_HEADER: "ws-group"}
        resp = role_enforcing_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_ROLE

    def test_role_enforcing_auditor_read_allowed(self, role_enforcing_client, monkeypatch):
        # read route admits auditor role too
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "auditor",
        }
        resp = role_enforcing_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code not in {401, 403, 409}, resp.text

    def test_role_enforcing_unknown_role_blocked(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "viewer",  # not owner or auditor
        }
        resp = role_enforcing_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code == 401, resp.text
        assert resp.json().get("error_code") == _CODE_MISSING_ROLE

    def test_role_enforcing_owner_allowed(self, role_enforcing_client, monkeypatch):
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
        monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
        headers = {
            _IDENTITY_HEADER: "operator@example.com",
            _GROUPS_HEADER: "ws-group",
            _ROLES_HEADER: "owner",
        }
        resp = role_enforcing_client.get(_API + _SOURCE_ROUTE, headers=headers)
        assert resp.status_code not in {401, 403, 409}, resp.text
