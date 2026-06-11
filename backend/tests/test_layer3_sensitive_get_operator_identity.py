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
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import settings
from app.db.session import Base
from app.services import (
    layer3_provider_private_signed_url,
    layer3_sec_edgar_live_source_artifact,
    layer3_source_intake,
)
from main import app


_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_IDENTITY_CANARY = "sensitive-get-operator@example.invalid"
_GROUPS_CANARY = "sensitive-get-workspace@example.invalid"
_API = "/api/v1/layer3"


@pytest.fixture()
def proxy_untrusted_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _fail_if_service_reached(*_args, **_kwargs) -> None:
    raise AssertionError("service should not run before route-level identity")


@pytest.mark.parametrize(
    ("path", "service_module", "service_name"),
    [
        (
            "/handoff/export/download/provider-private-signed-url/status/receipt-1",
            layer3_provider_private_signed_url,
            "provider_private_signed_url_status",
        ),
        (
            "/source/intake/inventory",
            layer3_source_intake,
            "source_intake_inventory",
        ),
        (
            "/source/sec-edgar/text-table/live-source-artifact/status/receipt-1",
            layer3_sec_edgar_live_source_artifact,
            "inspect_sec_edgar_text_table_live_source_artifact_status",
        ),
    ],
)
def test_sensitive_get_routes_fail_closed_before_service(
    proxy_untrusted_client: TestClient,
    monkeypatch,
    path: str,
    service_module,
    service_name: str,
) -> None:
    monkeypatch.setattr(service_module, service_name, _fail_if_service_reached)

    response = proxy_untrusted_client.get(
        _API + path,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )

    assert response.status_code == 409, response.text
    assert response.headers.get("content-type", "").startswith("application/json")
    body = response.json()
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
    assert _IDENTITY_CANARY not in response.text
    assert _GROUPS_CANARY not in response.text
