from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main  # noqa: E402
from app.core.config import settings  # noqa: E402

from _route_enum import post_routes  # noqa: E402


def _configure_proxy(monkeypatch, *, role_enforcing: bool = False) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "proxy_roles_header", "x-forwarded-roles")
    monkeypatch.setattr(
        settings,
        "layer3_route_authorization_mode",
        "role_enforcing" if role_enforcing else "identity_presence",
    )
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")


def test_pre_body_map_covers_registered_protected_post_routes() -> None:
    # post_routes() resolves the route table on both fastapi 0.111 (flat) and
    # >=0.115 (lazy _IncludedRouter); naive main.app.router.routes iteration finds
    # nothing under the newer pin. See tests/_route_enum.py.
    protected_routes: list[tuple[str, str]] = []
    for path, endpoint in post_routes(main.app):
        access = main._operator_authorization_access_from_endpoint(endpoint)
        if access is None:
            continue
        protected_routes.append((path, access))
        assert main._PRE_BODY_OPERATOR_AUTHORIZATION_POST_ROUTES[path] == access

    assert len(protected_routes) >= 200


def test_pre_body_route_discovery_fails_closed_when_required_routes_missing() -> None:
    with pytest.raises(RuntimeError, match="route discovery failed"):
        main._require_pre_body_operator_authorization_routes({})


def test_pre_body_map_matches_path_parameter_routes() -> None:
    assert (
        main._pre_body_operator_authorization_access_for_path(
            "/api/v1/datasets/dataset-1/versions/version-1/profile"
        )
        == "write"
    )
    assert (
        main._pre_body_operator_authorization_access_for_path(
            "/api/v1/layer3/source/intake/source-intake-1/preview"
        )
        is None
    )
    assert (
        main._pre_body_operator_authorization_access_for_path(
            "/api/v1/layer3/sec-xbrl/operator-review/workflow/status"
        )
        == "read"
    )


def test_legacy_json_route_rejects_missing_identity_before_body_validation(monkeypatch) -> None:
    _configure_proxy(monkeypatch)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/analysis-runs",
        content="{not-json",
        headers={
            "content-type": "application/json",
            "x-forwarded-groups": "workspace-canary",
        },
    )

    assert response.status_code == 401, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    assert "workspace-canary" not in response.text


def test_public_connector_result_values_rejects_missing_identity_before_body_validation(
    monkeypatch,
) -> None:
    _configure_proxy(monkeypatch)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/layer3/execution/result/public-values",
        content="{not-json",
        headers={
            "content-type": "application/json",
            "x-forwarded-groups": "workspace-canary",
        },
    )

    assert response.status_code == 401, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    assert "workspace-canary" not in response.text


def test_legacy_json_write_route_rejects_auditor_before_body_validation(monkeypatch) -> None:
    _configure_proxy(monkeypatch, role_enforcing=True)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/analysis-runs",
        content="{not-json",
        headers={
            "content-type": "application/json",
            "x-forwarded-user": "operator-canary",
            "x-forwarded-groups": "workspace-canary",
            "x-forwarded-roles": "auditor",
        },
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_role_access_forbidden"
    assert "operator-canary" not in response.text
    assert "workspace-canary" not in response.text


def test_sec_xbrl_route_rejects_missing_identity_before_body_validation(monkeypatch) -> None:
    _configure_proxy(monkeypatch)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/layer3/sec-xbrl/operator-review/workflow/status",
        content="{not-json",
        headers={
            "content-type": "application/json",
            "x-forwarded-groups": "workspace-canary",
        },
    )

    assert response.status_code == 401, response.text
    body = response.json()
    assert body["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    assert "workspace-canary" not in response.text
