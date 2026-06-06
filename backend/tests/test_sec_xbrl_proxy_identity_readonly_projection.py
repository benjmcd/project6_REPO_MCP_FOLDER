from __future__ import annotations

import json
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
sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.api.deps import get_db
from app.db.session import Base
from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    PROXY_IDENTITY_PROJECTION_CONTRACT_ID,
    PROXY_IDENTITY_PROJECTION_SCHEMA_ID,
    PROXY_IDENTITY_READONLY_PROJECTION_MODE,
    build_proxy_identity_readonly_projection,
)
from main import app


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_projection_admitted_auth_owner_none_default() -> None:
    projection = build_proxy_identity_readonly_projection(headers={})

    assert projection["projection_status"] == "admitted"
    assert projection["auth_owner_mode"] == "AUTH_OWNER_none_single_operator_dev_profile"
    assert projection["selected_auth_mode"] == PROXY_IDENTITY_READONLY_PROJECTION_MODE
    assert projection["contract_id"] == PROXY_IDENTITY_PROJECTION_CONTRACT_ID
    assert projection["schema_id"] == PROXY_IDENTITY_PROJECTION_SCHEMA_ID

    actor = projection["actor_ref_hash"]
    workspace = projection["workspace_ref_hash"]
    assert actor is not None and len(actor) >= 32
    assert workspace is not None and len(workspace) >= 32
    # hashes are hex strings
    assert all(c in "0123456789abcdef" for c in actor)
    assert all(c in "0123456789abcdef" for c in workspace)

    assert projection["raw_operator_identity_exposed"] is False
    assert projection["raw_proxy_header_exposed"] is False
    assert projection["raw_workspace_identity_exposed"] is False
    assert projection["raw_value_exposed"] is False
    assert projection["residual_magnitude_exposed"] is False


def test_projection_admitted_proxy_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")

    headers = {"X-Forwarded-User": "alice", "X-Forwarded-Groups": "team-a"}
    projection = build_proxy_identity_readonly_projection(headers=headers)

    assert projection["projection_status"] == "admitted"
    assert "proxy" in projection["auth_owner_mode"].lower()
    assert projection["actor_ref_hash"] is not None
    assert projection["workspace_ref_hash"] is not None

    serialized = json.dumps(projection)
    assert "alice" not in serialized
    assert "team-a" not in serialized
    assert "X-Forwarded" not in serialized


def test_projection_blocked_untrusted_proxy(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)

    projection = build_proxy_identity_readonly_projection(headers={})

    assert projection["projection_status"] == "blocked_untrusted_proxy_identity"
    assert projection["actor_ref_hash"] is None
    assert projection["workspace_ref_hash"] is None


def test_projection_blocked_proxy_missing_header(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")

    projection = build_proxy_identity_readonly_projection(headers={})

    assert projection["projection_status"] == "blocked_missing_identity_authority"
    assert projection["actor_ref_hash"] is None
    assert projection["workspace_ref_hash"] is None


def test_projection_no_raw_leak_proxy_admitted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")

    raw_identity = "operator-rawname@example.invalid"
    raw_workspace = "workspace-rawgroup"
    headers = {
        "X-Forwarded-User": raw_identity,
        "X-Forwarded-Groups": raw_workspace,
    }
    projection = build_proxy_identity_readonly_projection(headers=headers)

    serialized = json.dumps(projection)
    assert raw_identity not in serialized
    assert raw_workspace not in serialized
    assert "X-Forwarded" not in serialized
    assert "/" not in serialized
    assert "http" not in serialized.lower()


# ---------------------------------------------------------------------------
# Endpoint test via TestClient
# ---------------------------------------------------------------------------


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


def test_endpoint_identity_projection_admitted_default(client) -> None:
    response = client.get("/api/v1/layer3/sec-xbrl/identity/projection")

    assert response.status_code == 200
    body = response.json()
    assert "sec_xbrl_identity_projection" in body
    projection = body["sec_xbrl_identity_projection"]
    assert projection["projection_status"] == "admitted"
    assert projection["selected_auth_mode"] == PROXY_IDENTITY_READONLY_PROJECTION_MODE
