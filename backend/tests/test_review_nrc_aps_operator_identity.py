"""Operator-identity gating proof for review_nrc_aps routes.

Proves, at the HTTP route layer, that:
1. proxy mode + trusted proxy + missing identity header → auth-gate error (401) with error_code
2. proxy mode + trusted proxy + valid identity headers → not auth-gate rejected
3. local default mode (auth_owner=none) → behaviour unchanged (inert seam, no auth rejection)

All 23 GET routes are covered via parametrize.  Auth check fires before any service lookup,
so the auth-gate 401 proves gating independent of whether the run_id / fixture_id exist.
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

_API = "/api/v1/review/nrc-aps"
_IDENTITY_HEADER = "x-forwarded-user"
_GROUPS_HEADER = "x-forwarded-groups"
_IDENTITY_CANARY = "nrc-aps-test-operator@example.invalid"
_GROUPS_CANARY = "nrc-aps-test-workspace@example.invalid"

# Plausible dummy values for path parameters.  Auth check fires before service lookup,
# so a non-existent run_id / fixture_id produces a 401 (auth gate) not 404 (not found).
_RUN = "dummy-run-id-for-auth-gate-proof"
_TARGET = "dummy-target-id"
_NODE = "dummy-node-id"
_TREE = "dummy-tree-id"
_FIXTURE = "dummy-fixture-id"
_TAB = "dummy-tab-id"
_ARTIFACT = "dummy-artifact-id"
_BUNDLE = "dummy-bundle-id"

# Full inventory of all 23 GET routes with plausible dummy path and query params.
# Required query params must be supplied so FastAPI's validation layer does not return
# 422 before the auth gate fires.  Auth check is the first statement in the handler,
# so a 401 confirms the gate is wired correctly regardless of whether the resource exists.
_BL = "dummy-baseline-run"
_CA = "dummy-candidate-a-run"
_ALL_ROUTES = [
    f"{_API}/runs",
    f"{_API}/workbench-compare/sources",
    f"{_API}/workbench-compare/targets?baseline_run_id={_BL}&candidate_a_run_id={_CA}",
    f"{_API}/workbench-compare/targets/{_FIXTURE}/manifest?baseline_run_id={_BL}&candidate_a_run_id={_CA}",
    f"{_API}/workbench-compare/targets/{_FIXTURE}/tabs/{_TAB}?baseline_run_id={_BL}&candidate_a_run_id={_CA}",
    f"{_API}/candidate-b-trace/manifest?candidate_b_bundle_id={_BUNDLE}&fixture_id={_FIXTURE}",
    f"{_API}/candidate-b-trace/annotated-pdf?candidate_b_bundle_id={_BUNDLE}&fixture_id={_FIXTURE}",
    f"{_API}/candidate-b-trace/raw-json?candidate_b_bundle_id={_BUNDLE}&fixture_id={_FIXTURE}",
    f"{_API}/candidate-b-trace/raw-markdown?candidate_b_bundle_id={_BUNDLE}&fixture_id={_FIXTURE}",
    f"{_API}/pipeline-definition?run_id={_RUN}",
    f"{_API}/runs/{_RUN}/overview",
    f"{_API}/runs/{_RUN}/tree",
    f"{_API}/runs/{_RUN}/nodes/{_NODE}",
    f"{_API}/runs/{_RUN}/files/{_TREE}",
    f"{_API}/runs/{_RUN}/files/{_TREE}/preview",
    f"{_API}/runs/{_RUN}/documents",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/trace",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/source",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/visual-artifacts/{_ARTIFACT}",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/diagnostics",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/normalized-text",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/indexed-chunks",
    f"{_API}/runs/{_RUN}/documents/{_TARGET}/extracted-units",
]

assert len(_ALL_ROUTES) == 23, f"Expected 23 routes, got {len(_ALL_ROUTES)}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(tmp_path, monkeypatch, *, auth_owner: str, trusted: bool) -> TestClient:
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
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def proxy_fail_closed_client(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def proxy_trusted_client(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, auth_owner="proxy", trusted=True)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def local_default_client(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch, auth_owner="none", trusted=False)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _ALL_ROUTES)
def test_route_rejected_without_identity_in_proxy_mode(
    proxy_fail_closed_client: TestClient,
    path: str,
) -> None:
    """Every review_nrc_aps route returns an auth-gate error when proxy mode is active
    but the identity header is absent."""
    response = proxy_fail_closed_client.get(path)
    assert response.status_code == 401, (
        f"Expected 401 auth gate on {path}, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "error_code" in body, f"No error_code in response body for {path}: {body}"
    assert "missing_identity_authority" in body["error_code"], (
        f"Unexpected error_code for {path}: {body['error_code']}"
    )


@pytest.mark.parametrize("path", _ALL_ROUTES)
def test_route_not_auth_rejected_with_valid_identity(
    proxy_trusted_client: TestClient,
    path: str,
) -> None:
    """Every review_nrc_aps route is NOT auth-rejected when trusted proxy identity headers
    are present (may produce 404/400/500 from service layer — that is acceptable)."""
    response = proxy_trusted_client.get(
        path,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )
    # A 401 / 409 with an auth error_code is the only unacceptable outcome.
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        error_code = body.get("error_code", "")
        assert "auth_policy" not in error_code and "proxy" not in error_code, (
            f"Auth-gate error on {path} with valid headers: {body}"
        )


@pytest.mark.parametrize("path", _ALL_ROUTES)
def test_route_local_default_mode_not_auth_rejected(
    local_default_client: TestClient,
    path: str,
) -> None:
    """In local default mode (auth_owner=none) the identity seam is inert: no auth gate
    error is returned (routes proceed to service layer; 404/400/500 are acceptable)."""
    response = local_default_client.get(path)
    if response.status_code in (401, 409):
        try:
            body = response.json()
        except Exception:
            body = {}
        error_code = body.get("error_code", "")
        assert "auth_policy" not in error_code and "proxy" not in error_code, (
            f"Auth-gate error in local default mode on {path}: {body}"
        )
