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
from app.services import layer3_workbench
from main import app


_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_IDENTITY_CANARY = "core-workbench-operator@example.invalid"
_GROUPS_CANARY = "core-workbench-workspace@example.invalid"
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
    raise AssertionError("core workbench service should not run before route-level identity")


def _identity_headers() -> dict[str, str]:
    return {
        _IDENTITY_HEADER: _IDENTITY_CANARY,
        _GROUPS_HEADER: _GROUPS_CANARY,
    }


def _assert_untrusted_proxy_response(response) -> None:
    assert response.status_code == 409, response.text
    assert response.headers.get("content-type", "").startswith("application/json")
    body = response.json()
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
    assert _IDENTITY_CANARY not in response.text
    assert _GROUPS_CANARY not in response.text


def test_core_workbench_post_fails_closed_before_service(proxy_untrusted_client, monkeypatch) -> None:
    monkeypatch.setattr(layer3_workbench, "preflight", _fail_if_service_reached)

    response = proxy_untrusted_client.post(
        _API + "/preflight",
        json={"natural_language_intent": "prove core workbench identity gate"},
        headers=_identity_headers(),
    )

    _assert_untrusted_proxy_response(response)


def test_public_connector_result_values_fails_closed_before_service(
    proxy_untrusted_client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        layer3_workbench,
        "public_connector_execution_result_values",
        _fail_if_service_reached,
    )

    response = proxy_untrusted_client.post(
        _API + "/execution/result/public-values",
        json={
            "session_id": "session-public-values-auth",
            "analysis_plan_id": "plan-public-values-auth",
            "pass_run_id": "pass-public-values-auth",
            "preview_id": "preview-public-values-auth",
            "preview_hash": "preview-hash-public-values-auth",
        },
        headers=_identity_headers(),
    )

    _assert_untrusted_proxy_response(response)


@pytest.mark.parametrize(
    ("path", "service_name"),
    [
        ("/dataset-version-candidates", "aps_dataset_version_candidates"),
        (
            "/public-dataset-version-candidates",
            "public_connector_dataset_version_candidates",
        ),
        ("/session/session-1", "session_summary"),
    ],
)
def test_core_workbench_sensitive_get_fails_closed_before_service(
    proxy_untrusted_client,
    monkeypatch,
    path: str,
    service_name: str,
) -> None:
    monkeypatch.setattr(layer3_workbench, service_name, _fail_if_service_reached)

    response = proxy_untrusted_client.get(_API + path, headers=_identity_headers())

    _assert_untrusted_proxy_response(response)


@pytest.mark.parametrize(
    "path",
    [
        "/bootstrap",
        "/readiness",
        "/authority-matrix",
    ],
)
def test_public_metadata_gets_remain_available_under_proxy_untrusted(
    proxy_untrusted_client,
    path: str,
) -> None:
    response = proxy_untrusted_client.get(_API + path, headers=_identity_headers())

    assert response.status_code == 200, response.text
    assert response.headers.get("content-type", "").startswith("application/json")
