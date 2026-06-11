from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_sec_edgar_live_source_artifact
from main import app


_PATH = "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire"
_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_IDENTITY_CANARY = "source-sec-edgar-operator@example.invalid"
_GROUPS_CANARY = "source-sec-edgar-workspace@example.invalid"
_BODY = {
    "client_request_id": "source-sec-edgar-identity-001",
    "acquisition_mode": "sec_edgar_text_table_live_source_artifact_acquisition_v1",
    "operator_decision": "acquire_sec_edgar_text_table_live_source_artifact",
    "cik_or_filer_ref": "redacted-cik-ref",
    "accession_or_submission_id": "redacted-accession-ref",
    "form_type": "10-K",
    "filing_date": "2025-01-31",
    "operator_confirmation": True,
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _fail_if_service_reached(*_args, **_kwargs) -> None:
    raise AssertionError("source-sec-edgar service should not run before route-level identity")


def test_source_sec_edgar_post_fails_closed_when_proxy_untrusted(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    monkeypatch.setattr(
        layer3_sec_edgar_live_source_artifact,
        "acquire_sec_edgar_text_table_live_source_artifact",
        _fail_if_service_reached,
    )

    response = client.post(
        _PATH,
        json=_BODY,
        headers={
            _IDENTITY_HEADER: _IDENTITY_CANARY,
            _GROUPS_HEADER: _GROUPS_CANARY,
        },
    )

    assert response.status_code == 409
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json()["error_code"] == "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
    assert _IDENTITY_CANARY not in response.text
    assert _GROUPS_CANARY not in response.text


def test_source_sec_edgar_post_requires_proxy_identity(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(
        layer3_sec_edgar_live_source_artifact,
        "acquire_sec_edgar_text_table_live_source_artifact",
        _fail_if_service_reached,
    )

    response = client.post(
        _PATH,
        json=_BODY,
        headers={_GROUPS_HEADER: _GROUPS_CANARY},
    )

    assert response.status_code == 401
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json()["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    assert _GROUPS_CANARY not in response.text


def test_source_sec_edgar_post_requires_proxy_workspace(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(
        layer3_sec_edgar_live_source_artifact,
        "acquire_sec_edgar_text_table_live_source_artifact",
        _fail_if_service_reached,
    )

    response = client.post(
        _PATH,
        json=_BODY,
        headers={_IDENTITY_HEADER: _IDENTITY_CANARY},
    )

    assert response.status_code == 401
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json()["error_code"] == "sec_xbrl_in_app_auth_policy_missing_workspace_authority"
    assert _IDENTITY_CANARY not in response.text
