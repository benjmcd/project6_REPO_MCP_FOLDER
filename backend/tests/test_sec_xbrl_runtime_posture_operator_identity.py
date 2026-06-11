"""Route-level auth enforcement proof for GET /sec-xbrl/runtime/posture.

Proves that:
1. proxy fail-closed (trusted proxy, missing identity header) → 401 with auth error_code
2. untrusted proxy (trusted_proxy_mode=False) → 409 with untrusted_proxy error_code
3. trusted proxy with valid identity headers → not auth-rejected (reaches service layer)
4. local default mode (auth_owner=none) → 200 (inert, posture response returned)
5. GET /sec-xbrl/identity/projection remains reachable without headers in proxy mode
   (fail-soft contract, doc-1351) — covered by test_sec_xbrl_proxy_identity_readonly_projection.py;
   verified here that it returns 200 with blocked_* projection_status, not an auth gate error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

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

_POSTURE_ROUTE = "/api/v1/layer3/sec-xbrl/runtime/posture"
_PROJECTION_ROUTE = "/api/v1/layer3/sec-xbrl/identity/projection"
_IDENTITY_HEADER = "x-forwarded-user"
_GROUPS_HEADER = "x-forwarded-groups"
_IDENTITY_CANARY = "posture-test-operator@example.invalid"
_GROUPS_CANARY = "posture-test-workspace@example.invalid"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(tmp_path, monkeypatch, *, auth_owner: str, trusted: bool):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", auth_owner)
    monkeypatch.setattr(settings, "trusted_proxy_mode", trusted)
    if auth_owner == "proxy":
        monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
        monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
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
    client = TestClient(app, raise_server_exceptions=False)
    return client


@pytest.fixture()
def proxy_fail_closed_client(tmp_path, monkeypatch):
    """Proxy mode, trusted=True, identity header absent → 401 fail-closed."""
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def untrusted_proxy_client(tmp_path, monkeypatch):
    """Proxy mode, trusted=False → 409 untrusted-proxy."""
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=False)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def proxy_trusted_client(tmp_path, monkeypatch):
    """Proxy mode, trusted=True, identity header present → auth passes."""
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def local_default_client(tmp_path, monkeypatch):
    """Default local mode (auth_owner=none) → identity seam is inert."""
    client = _make_client(tmp_path, monkeypatch, auth_owner="none", trusted=False)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_posture_proxy_fail_closed_missing_identity(proxy_fail_closed_client) -> None:
    """GET /sec-xbrl/runtime/posture returns 401 when proxy mode is active but
    identity header is absent."""
    response = proxy_fail_closed_client.get(_POSTURE_ROUTE)
    assert response.status_code == 401, response.text
    body = response.json()
    assert "error_code" in body, body
    assert "missing_identity_authority" in body["error_code"], body


def test_posture_untrusted_proxy_rejected(untrusted_proxy_client) -> None:
    """GET /sec-xbrl/runtime/posture returns 409 when proxy identity is untrusted."""
    response = untrusted_proxy_client.get(
        _POSTURE_ROUTE,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert "error_code" in body, body
    assert "untrusted_proxy" in body["error_code"], body
    # No raw identity values in response
    assert _IDENTITY_CANARY not in response.text
    assert _GROUPS_CANARY not in response.text


def test_posture_proxy_trusted_with_identity_not_auth_rejected(proxy_trusted_client) -> None:
    """GET /sec-xbrl/runtime/posture is not auth-rejected when trusted proxy identity
    headers are present (reaches service; may return any non-auth HTTP status)."""
    response = proxy_trusted_client.get(
        _POSTURE_ROUTE,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )
    # Must not be an auth gate error (401 / 409 with auth error_code)
    if response.status_code in (401, 409):
        body = response.json()
        error_code = body.get("error_code", "")
        assert "auth_policy" not in error_code and "proxy" not in error_code, (
            f"Auth-gate error unexpectedly returned: {body}"
        )


def test_posture_local_default_mode_inert(local_default_client) -> None:
    """GET /sec-xbrl/runtime/posture returns 200 in local default mode (identity seam inert)."""
    response = local_default_client.get(_POSTURE_ROUTE)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "sec_xbrl_runtime_posture" in body, body


def test_projection_fail_soft_reachable_without_identity_in_proxy_mode(
    untrusted_proxy_client,
) -> None:
    """GET /sec-xbrl/identity/projection is reachable without identity headers even in
    proxy mode (fail-soft by contract, doc-1351).  It returns 200 with a blocked_*
    projection_status rather than an auth gate error."""
    response = untrusted_proxy_client.get(_PROJECTION_ROUTE)
    assert response.status_code == 200, response.text
    body = response.json()
    projection = body.get("sec_xbrl_identity_projection", {})
    assert projection.get("projection_status", "").startswith("blocked_"), (
        f"Expected blocked_* projection_status, got: {projection.get('projection_status')}"
    )
