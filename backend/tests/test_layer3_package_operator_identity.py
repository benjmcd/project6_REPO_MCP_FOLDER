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

_SEAM_CODES = {
    "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity",
    "sec_xbrl_in_app_auth_policy_missing_identity_authority",
    "sec_xbrl_in_app_auth_policy_missing_workspace_authority",
}

_POST_PATHS = [
    "/api/v1/layer3/package/review/preview",
    "/api/v1/layer3/package/review/commit",
    "/api/v1/layer3/package/review/submit",
    "/api/v1/layer3/package/mutation/preview",
    "/api/v1/layer3/package/replacement-artifact/materialize",
    "/api/v1/layer3/package/replacement-set/record",
    "/api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set",
    "/api/v1/layer3/package/supersession/commit",
    "/api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority",
    "/api/v1/layer3/package/replacement-artifact/manifest/record",
    "/api/v1/layer3/package/replacement-artifact/manifest/record-from-authority",
    "/api/v1/layer3/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority",
    "/api/v1/layer3/package/corrected-artifact-set/record",
    "/api/v1/layer3/package/replacement-namespace/record",
    "/api/v1/layer3/package/replacement-namespace/record-from-corrected-artifact-manifest-authority",
    "/api/v1/layer3/package/replacement-activation/commit",
]

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_IDENTITY_CANARY = "leak-canary-operator@example.invalid"
_GROUPS_CANARY = "leak-canary-groups@example.invalid"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "external-local-export"))
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

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


@pytest.mark.parametrize("path", _POST_PATHS)
def test_409_untrusted_proxy_sweep(path, client, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)

    resp = client.post(
        path,
        json={},
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )

    assert resp.status_code == 409
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert body.get("error_code") == "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
    raw = resp.text
    assert _IDENTITY_CANARY not in raw
    assert _GROUPS_CANARY not in raw


@pytest.mark.parametrize("path", _POST_PATHS)
def test_401_missing_identity_sweep(path, client, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "X-Forwarded-User")
    monkeypatch.setattr(settings, "proxy_groups_header", "X-Forwarded-Groups")

    resp = client.post(
        path,
        json={},
        headers={
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )

    assert resp.status_code == 401
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert body.get("error_code") == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    assert _GROUPS_CANARY not in resp.text


def test_401_missing_workspace_single_route(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "X-Forwarded-User")
    monkeypatch.setattr(settings, "proxy_groups_header", "X-Forwarded-Groups")

    resp = client.post(
        "/api/v1/layer3/package/review/preview",
        json={},
        headers={
            _IDENTITY_HEADER: "operator@example.invalid",
        },
    )

    assert resp.status_code == 401
    body = resp.json()
    assert body.get("error_code") == "sec_xbrl_in_app_auth_policy_missing_workspace_authority"


@pytest.mark.parametrize("path", _POST_PATHS)
def test_none_mode_inertness_sweep(path, client):
    resp = client.post(path, json={})

    if resp.headers.get("content-type", "").startswith("application/json"):
        try:
            body = resp.json()
        except Exception:
            body = {}
        if isinstance(body, dict) and body.get("error_code"):
            assert body["error_code"] not in _SEAM_CODES
    assert resp.status_code != 401


@pytest.mark.parametrize("path", [
    "/api/v1/layer3/package/review/preview",
    "/api/v1/layer3/package/review/commit",
])
def test_422_precedence_pin(path, client, monkeypatch):
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)

    resp = client.post(
        path,
        json={"__unknown_forbidden_field__": "value"},
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )

    assert resp.status_code == 422
    raw = resp.text
    assert _IDENTITY_CANARY not in raw
    assert _GROUPS_CANARY not in raw
