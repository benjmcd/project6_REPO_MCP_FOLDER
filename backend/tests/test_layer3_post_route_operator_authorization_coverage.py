"""Architectural guard: EVERY POST route registered on the app must be operator
-gated, either in-handler (the handler source calls _route_level_operator_identity
or authorize_sec_xbrl_route / _sec_xbrl_policy_decision) or by presence in the
static pre-body authorization registry.

The sibling test_pre_body_operator_authorization.py enforces only the forward
direction (a handler that gates in-code must also appear in the pre-body
registry). That leaves a fully-ungated route invisible to it — which is exactly
how the analyst-insight / market-pipeline compute routes shipped open. This test
closes the reverse gap: it fails if any POST route is gated by NEITHER mechanism.

Route enumeration reads the canonical ``api_router`` (the object ``main`` mounts),
NOT the module-level ``main.app``. Under the sharded CI run, other tests sharing
the process can leave ``main.app.router.routes`` empty; ``api_router`` stays
intact, so enumerating it keeps this guard order-independent. The 401-before-body
test builds an isolated app from the same ``api_router`` plus ``main``'s real
pre-body middleware, for the same reason.
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
from app.api.router import api_router  # noqa: E402
from app.core.config import settings  # noqa: E402

_API_PREFIX = settings.api_prefix.rstrip("/")


def _post_routes() -> list[tuple[str, object]]:
    """POST routes from the canonical api_router, prefixed with the API mount
    prefix. Enumerating api_router (not the shared module-level main.app) keeps
    this guard immune to other tests in the same process mutating main.app."""
    routes: list[tuple[str, object]] = []
    for route in api_router.routes:
        methods = getattr(route, "methods", set()) or set()
        if "POST" not in methods:
            continue
        full_path = _API_PREFIX + str(getattr(route, "path", ""))
        routes.append((full_path, getattr(route, "endpoint", None)))
    return routes


def _build_isolated_app() -> FastAPI:
    """A fresh app mounting the market routers (the only ones this file's 401 test
    exercises) plus main's real pre-body operator-authorization middleware. Built
    from the market modules' own routers — not the shared api_router/main.app — so
    the 401-before-body assertion cannot be perturbed by another test in the same
    worker mutating shared app route state. The middleware reads the static
    pre-body registry, which is independent of any app instance."""
    from app.api import market_data_integration, market_data_validation, market_insight_ai

    app = FastAPI()
    app.middleware("http")(main._pre_body_operator_authorization_middleware)
    for mod in (market_data_integration, market_data_validation, market_insight_ai):
        app.include_router(mod.router, prefix=settings.api_prefix)
        app.include_router(mod.alias_router, prefix=settings.api_prefix)
    return app


def test_every_post_route_is_operator_gated() -> None:
    post_routes = _post_routes()
    assert post_routes, (
        "no POST routes discovered from api_router — enumeration is broken "
        f"(api_router has {len(api_router.routes)} total routes, "
        f"main.app has {len(main.app.router.routes)} total routes)"
    )

    ungated: list[str] = []
    for path, endpoint in post_routes:
        gated_in_handler = main._operator_authorization_access_from_endpoint(endpoint) is not None
        registered_pre_body = main._pre_body_operator_authorization_access_for_path(path) is not None
        if not (gated_in_handler or registered_pre_body):
            ungated.append(path)

    assert not ungated, (
        f"{len(ungated)} POST route(s) operator-gated by NEITHER an in-handler "
        "_route_level_operator_identity call NOR the pre-body registry:\n"
        + "\n".join(f"  - {p}" for p in sorted(ungated))
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
    """Explicit anchor for the six routes this guard was introduced to cover.

    Builds a fresh app from the market modules' own routers rather than reading
    the shared api_router/main.app, so a sibling test mutating shared app state in
    the same worker cannot perturb this anchor. The pre-body registry lookup is a
    static dict and is likewise independent of any app instance."""
    from app.api import market_data_integration, market_data_validation, market_insight_ai

    anchor_app = FastAPI()
    for mod in (market_data_integration, market_data_validation, market_insight_ai):
        anchor_app.include_router(mod.router, prefix=settings.api_prefix)
        anchor_app.include_router(mod.alias_router, prefix=settings.api_prefix)
    registered = {
        str(getattr(route, "path", ""))
        for route in anchor_app.router.routes
        if "POST" in (getattr(route, "methods", set()) or set())
    }

    expected = [
        f"{_API_PREFIX}/market-pipeline/integration/cross-reference",
        f"{_API_PREFIX}/analyst-insight/integration/cross-reference",
        f"{_API_PREFIX}/market-pipeline/validation/run",
        f"{_API_PREFIX}/analyst-insight/validation/run",
        f"{_API_PREFIX}/market-pipeline/insights/process",
        f"{_API_PREFIX}/analyst-insight/insights/process",
    ]
    for path in expected:
        assert path in registered, f"market/analyst route not defined by its module router: {path}"
        assert main._pre_body_operator_authorization_access_for_path(path) == "write", (
            f"market/analyst route missing from pre-body registry: {path}"
        )


def _configure_proxy(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "identity_presence")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/market-pipeline/integration/cross-reference",
        "/api/v1/analyst-insight/integration/cross-reference",
        "/api/v1/market-pipeline/validation/run",
        "/api/v1/analyst-insight/validation/run",
        "/api/v1/market-pipeline/insights/process",
        "/api/v1/analyst-insight/insights/process",
    ],
)
def test_market_route_rejects_missing_identity_before_body_validation(monkeypatch, path) -> None:
    """Proxy mode, no identity header, deliberately malformed body: the gate must
    reject with 401 BEFORE body parsing — proving the route is genuinely closed."""
    _configure_proxy(monkeypatch)
    client = TestClient(_build_isolated_app(), raise_server_exceptions=False)

    response = client.post(
        path,
        content="{not-json",
        headers={"content-type": "application/json", "x-forwarded-groups": "ws-canary"},
    )

    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
    # Leak guard: the supplied group header must not echo into the error body.
    assert "ws-canary" not in response.text
