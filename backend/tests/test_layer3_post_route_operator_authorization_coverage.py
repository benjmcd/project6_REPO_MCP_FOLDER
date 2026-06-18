"""Architectural guard: EVERY POST route registered on the app must be operator
-gated, either in-handler (the handler source calls _route_level_operator_identity
or authorize_sec_xbrl_route / _sec_xbrl_policy_decision) or by presence in the
static pre-body authorization registry.

The sibling test_pre_body_operator_authorization.py enforces only the forward
direction (a handler that gates in-code must also appear in the pre-body
registry). That leaves a fully-ungated route invisible to it — which is exactly
how the analyst-insight / market-pipeline compute routes shipped open. This test
closes the reverse gap: it fails if any POST route is gated by NEITHER mechanism.

Version note (the real root cause of the earlier sharded-CI flakiness): fastapi
changed `include_router` around 0.115 to insert a lazy `_IncludedRouter` node
instead of flattening a sub-router's routes into `app.router.routes`. Naive
iteration over `app.router.routes` therefore finds zero of the included routes
under the CI fastapi pin (>=0.115), even though the app serves them all. The
earlier "sibling test empties the registries" theory was a misdiagnosis — every
worker sees the same lazy structure. Enumeration here goes through
``_route_enum.post_routes`` which resolves the included routes on both fastapi
0.111 (flat) and >=0.115 (`_IncludedRouter`), matching ``app.openapi()`` exactly.
The pre-body registry and the AST drift guard remain the static, app-independent
sources of the gating classification itself.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main  # noqa: E402
from app.core.config import settings  # noqa: E402

from _route_enum import post_routes  # noqa: E402

_API_PREFIX = settings.api_prefix.rstrip("/")

# The six routes this guard was introduced to cover (canonical + /analyst-insight
# alias for each of the three market-pipeline compute handlers).
_MARKET_POST_PATHS = [
    f"{_API_PREFIX}/market-pipeline/integration/cross-reference",
    f"{_API_PREFIX}/analyst-insight/integration/cross-reference",
    f"{_API_PREFIX}/market-pipeline/validation/run",
    f"{_API_PREFIX}/analyst-insight/validation/run",
    f"{_API_PREFIX}/market-pipeline/insights/process",
    f"{_API_PREFIX}/analyst-insight/insights/process",
]


def _post_routes() -> list[tuple[str, object]]:
    """Every registered POST route as (full_path, endpoint), resolved through the
    version-robust walker so it works on both fastapi 0.111 and >=0.115."""
    return post_routes(main.app)


def test_every_post_route_is_operator_gated() -> None:
    discovered = _post_routes()
    assert discovered, (
        "no POST routes discovered from main.app — route enumeration is broken "
        "(check _route_enum against the installed fastapi version)"
    )

    ungated: list[str] = []
    for path, endpoint in discovered:
        gated_in_handler = main._operator_authorization_access_from_endpoint(endpoint) is not None
        registered_pre_body = main._pre_body_operator_authorization_access_for_path(path) is not None
        if not (gated_in_handler or registered_pre_body):
            ungated.append(path)

    assert not ungated, (
        f"{len(ungated)} POST route(s) operator-gated by NEITHER an in-handler "
        "_route_level_operator_identity call NOR the pre-body registry:\n"
        + "\n".join(f"  - {p}" for p in sorted(ungated))
    )


def test_enumeration_matches_openapi_post_paths() -> None:
    """The version-robust resolver must agree with fastapi's own public OpenAPI
    view of the app. This cross-check turns a future fastapi route-exposure change
    (e.g. _IncludedRouter.effective_route_contexts removed/renamed) into a loud,
    self-explaining failure rather than a silently-partial enumeration."""
    discovered_paths = {path for path, _ in _post_routes()}
    openapi_post_paths = {
        path
        for path, operations in main.app.openapi()["paths"].items()
        if any(method.lower() == "post" for method in operations)
    }
    missing = openapi_post_paths - discovered_paths
    extra = discovered_paths - openapi_post_paths
    assert not missing and not extra, (
        "route enumeration disagrees with app.openapi():\n"
        f"  missing from enumeration: {sorted(missing)}\n"
        f"  extra in enumeration: {sorted(extra)}"
    )


def test_guard_detects_an_ungated_post_route() -> None:
    """Negative proof the guard fails closed: a handler that neither calls
    _route_level_operator_identity in its source nor matches a pre-body registry
    path is reported as gated by NEITHER mechanism (so the assertion in
    test_every_post_route_is_operator_gated would flag it)."""

    def _ungated_handler() -> dict[str, bool]:
        return {"ok": True}

    assert main._operator_authorization_access_from_endpoint(_ungated_handler) is None
    assert (
        main._pre_body_operator_authorization_access_for_path(
            "/api/v1/__never_registered__/run"
        )
        is None
    )


def test_market_and_analyst_post_routes_are_gated() -> None:
    """Explicit anchor for the six routes this guard was introduced to cover:
    each is registered on the app AND classified `write` in the pre-body registry
    (the gating authority the middleware consults)."""
    registered = {path for path, _ in _post_routes()}
    for path in _MARKET_POST_PATHS:
        assert path in registered, f"expected POST route not registered on app: {path}"
        assert main._pre_body_operator_authorization_access_for_path(path) == "write", (
            f"market/analyst route missing from pre-body authorization registry "
            f"as write: {path}"
        )


def _configure_proxy(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")


@pytest.mark.parametrize("path", _MARKET_POST_PATHS)
def test_market_route_rejects_missing_identity_before_body_validation(monkeypatch, path) -> None:
    """Proxy mode, no identity header, deliberately malformed body: the pre-body
    middleware must reject with 401 BEFORE body parsing — proving the path is
    genuinely closed at the pre-body layer.

    Uses a self-contained probe app carrying ONLY main's real pre-body middleware
    plus a dummy handler at the path under test. The dummy handler declares a body
    param, so if the gate did NOT fire first the malformed body would surface as a
    422 — getting 401 proves the registry + middleware close the path pre-body.
    Independent of the market routers, so it cannot be perturbed by sibling tests."""
    _configure_proxy(monkeypatch)

    probe = FastAPI()
    probe.middleware("http")(main._pre_body_operator_authorization_middleware)

    @probe.post(path)
    def _probe_handler(payload: dict) -> dict[str, bool]:  # pragma: no cover - gate fires first
        return {"ok": True}

    client = TestClient(probe, raise_server_exceptions=False)
    response = client.post(
        path,
        content="{not-json",
        headers={"content-type": "application/json", "x-forwarded-groups": "ws-canary"},
    )

    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    # Leak guard: the supplied group header must not echo into the error body.
    assert "ws-canary" not in response.text
