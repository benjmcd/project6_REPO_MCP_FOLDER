from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main  # noqa: E402
from app.api import router as api_router_module  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models import ConnectorRun  # noqa: E402


CAMPAIGN_ID = "7fe33e0a-c0e7-4f8e-9d55-8ba77a01ce23"
CAMPAIGN_FINGERPRINT = "a" * 64
GRANT_SHA256 = "b" * 64
ARMING_FINGERPRINT = "c" * 64


@pytest.fixture()
def api_client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )

    def override_get_db():
        with factory() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "deployment_mode", "local")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    try:
        yield TestClient(main.app, raise_server_exceptions=False), factory
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _arming_payload() -> dict[str, str]:
    return {
        "schema_id": "project6.connector_egress_arming.v1",
        "client_request_id": "create-1",
        "connector_key": "nrc_adams_aps",
        "campaign_id": CAMPAIGN_ID,
        "campaign_fingerprint": CAMPAIGN_FINGERPRINT,
        "grant_sha256": GRANT_SHA256,
    }


def _strict_envelope() -> dict[str, object]:
    return {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": "nrc_adams_aps",
        "campaign_id": CAMPAIGN_ID,
        "campaign_fingerprint": CAMPAIGN_FINGERPRINT,
        "campaign_definition_sha256": "d" * 64,
        "grant_sha256": GRANT_SHA256,
        "canonical_grant_fingerprint": "e" * 64,
        "arming_fingerprint": ARMING_FINGERPRINT,
    }


def _seed_strict_run(factory, *, status: str = "armed") -> ConnectorRun:
    run = ConnectorRun(
        connector_run_id="strict-api-run",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status=status,
        request_config_json={"connector_egress_arming": _strict_envelope()},
        request_fingerprint=ARMING_FINGERPRINT,
        submission_idempotency_key="egress-arm:create-1",
        execution_lease_owner="must-not-leak",
        execution_lease_token="must-not-leak-token",
        execution_lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    with factory() as db:
        db.add(run)
        db.commit()
        db.refresh(run)
        db.expunge(run)
    return run


def _fake_receipt():
    return SimpleNamespace(
        model_dump=lambda **_: {
            "schema_id": "project6.connector_egress_authorization_receipt.v1",
            "operator_ref_hash": "f" * 64,
            "workspace_ref_hash": "0" * 64,
        }
    )


def test_create_arming_resolves_owner_authority_and_never_enqueues(
    api_client,
    monkeypatch,
) -> None:
    client, _ = api_client
    verified_grant = object()
    created_run = ConnectorRun(
        connector_run_id="created-run",
        connector_key="nrc_adams_aps",
        source_system="nrc_adams_aps",
        source_mode="strict_live_proof",
        status="armed",
        submitted_at=datetime.now(UTC),
        request_fingerprint=ARMING_FINGERPRINT,
    )
    calls: list[str] = []
    monkeypatch.setattr(
        api_router_module,
        "_resolve_egress_authority",
        lambda **_: verified_grant,
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_authorization,
        "authorize_connector_egress_owner",
        lambda *_, **__: _fake_receipt(),
    )

    def fake_create(*_args, **kwargs):
        assert kwargs["verified_grant"] is verified_grant
        assert "operator_ref_hash" in kwargs["operator_receipt"]
        calls.append("create")
        return created_run, True

    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "create_connector_egress_arming",
        fake_create,
    )
    monkeypatch.setattr(
        api_router_module,
        "_enqueue_connector_run",
        lambda *_args, **_kwargs: pytest.fail("arming creation must not enqueue"),
    )

    response = client.post(
        "/api/v1/connectors/egress-armings",
        json=_arming_payload(),
    )

    assert response.status_code == 201, response.text
    assert calls == ["create"]
    body = response.json()
    assert body["status"] == "armed"
    assert body["request_fingerprint"] == ARMING_FINGERPRINT
    assert body["submission_idempotency_key"] is None
    assert "lease" not in response.text.lower()


def test_execute_never_claims_or_enqueues_over_http(
    api_client,
    monkeypatch,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory)

    def forbidden(*_args, **_kwargs):
        pytest.fail("disabled HTTP execution reached a claim or executor seam")

    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "resolve_current_egress_authority",
        forbidden,
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_authorization,
        "authorize_connector_egress_owner",
        forbidden,
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "claim_connector_egress_arming",
        forbidden,
    )
    monkeypatch.setattr(
        api_router_module,
        "_strict_egress_executor",
        forbidden,
    )
    payload = {
        "execution_idempotency_key": "execute-1",
        "arming_fingerprint": ARMING_FINGERPRINT,
    }

    first = client.post(
        "/api/v1/connectors/egress-armings/strict-api-run/execute",
        json=payload,
    )
    second = client.post(
        "/api/v1/connectors/egress-armings/strict-api-run/execute",
        json=payload,
    )

    assert first.status_code == 409, first.text
    assert second.status_code == 409, second.text
    assert first.json() == second.json()


def test_execute_route_refuses_http_before_strict_service_seams(
    api_client,
    monkeypatch,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory)

    def forbidden(*_args, **_kwargs):
        pytest.fail("disabled HTTP execution reached a strict service seam")

    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "resolve_current_egress_authority",
        forbidden,
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_authorization,
        "authorize_connector_egress_owner",
        forbidden,
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "claim_connector_egress_arming",
        forbidden,
    )
    monkeypatch.setattr(
        api_router_module,
        "_strict_egress_executor",
        forbidden,
    )

    response = client.post(
        "/api/v1/connectors/egress-armings/strict-api-run/execute",
        json={
            "execution_idempotency_key": "http-disabled",
            "arming_fingerprint": ARMING_FINGERPRINT,
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == {
        "code": "connector_strict_egress_http_execute_disabled",
        "message": (
            "Strict egress execution is available only through the owned CLI "
            "acquisition child."
        ),
    }


def test_execute_http_route_advertises_only_disabled_contract(api_client) -> None:
    client, _factory = api_client

    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/connectors/egress-armings/{connector_run_id}/execute"
    ]["post"]

    assert operation["deprecated"] is True
    assert "202" not in operation["responses"]
    assert operation["responses"]["409"]["description"] == (
        "Strict egress execution is disabled over HTTP; use the owned CLI "
        "acquisition child."
    )


def test_execute_http_refusal_does_not_read_route_clock_or_authority(
    api_client,
    monkeypatch,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory)

    class RouteClock:
        @classmethod
        def now(cls, tz):
            pytest.fail(f"disabled HTTP execution read the route clock for {tz}")

    monkeypatch.setattr(api_router_module, "datetime", RouteClock)
    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "resolve_current_egress_authority",
        lambda *_args, **_kwargs: pytest.fail(
            "disabled HTTP execution resolved protected authority"
        ),
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_authorization,
        "authorize_connector_egress_owner",
        lambda *_, **__: _fake_receipt(),
    )

    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "claim_connector_egress_arming",
        lambda *_args, **_kwargs: pytest.fail(
            "disabled HTTP execution reached claim"
        ),
    )
    monkeypatch.setattr(
        api_router_module,
        "_strict_egress_executor",
        lambda _run: lambda _run_id: None,
    )

    response = client.post(
        "/api/v1/connectors/egress-armings/strict-api-run/execute",
        json={
            "execution_idempotency_key": "fresh-route-time",
            "arming_fingerprint": ARMING_FINGERPRINT,
        },
    )

    assert response.status_code == 409, response.text
    assert (
        response.json()["detail"]["code"]
        == "connector_strict_egress_http_execute_disabled"
    )


def _seeded_run(factory) -> ConnectorRun:
    with factory() as db:
        run = db.get(ConnectorRun, "strict-api-run")
        assert run is not None
        db.expunge(run)
        return run


def test_get_projection_redacts_envelope_and_lease(
    api_client,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory)

    response = client.get(
        "/api/v1/connectors/egress-armings/strict-api-run"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["request_fingerprint"] == ARMING_FINGERPRINT
    assert body["submission_idempotency_key"] is None
    for forbidden in (
        "must-not-leak",
        "grant_sha256",
        "campaign_definition_sha256",
        "request_config_json",
    ):
        assert forbidden not in response.text


def test_generic_get_rejects_strict_run_without_leaking_reserved_fields(
    api_client,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory)

    response = client.get("/api/v1/connectors/runs/strict-api-run")

    assert response.status_code == 409, response.text
    assert (
        response.json()["detail"]["code"]
        == "connector_strict_generic_get_forbidden"
    )
    for forbidden in (
        "must-not-leak",
        "grant_sha256",
        "campaign_definition_sha256",
        "request_config_json",
    ):
        assert forbidden not in response.text


@pytest.mark.parametrize(
    "suffix",
    [
        "targets",
        "events",
        "reports",
        "content-units",
        "_operator/retrieval-content-units",
    ],
)
def test_generic_subresource_gets_reject_strict_run_without_leak(
    api_client,
    suffix: str,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory)

    response = client.get(
        f"/api/v1/connectors/runs/strict-api-run/{suffix}"
    )

    assert response.status_code == 409, response.text
    assert (
        response.json()["detail"]["code"]
        == "connector_strict_generic_get_forbidden"
    )
    for forbidden in (
        "must-not-leak",
        "grant_sha256",
        "campaign_definition_sha256",
        "request_config_json",
    ):
        assert forbidden not in response.text


@pytest.mark.parametrize(
    "strict_status",
    ["armed", "pending", "running", "completed", "failed", "cancelled"],
)
@pytest.mark.parametrize("action", ["resume", "cancel"])
def test_strict_runs_reject_generic_state_routes_without_mutation(
    api_client,
    action: str,
    strict_status: str,
) -> None:
    client, factory = api_client
    _seed_strict_run(factory, status=strict_status)
    with factory() as db:
        before = db.get(ConnectorRun, "strict-api-run")
        assert before is not None
        snapshot = (
            before.status,
            before.cancellation_requested_at,
            before.execution_lease_owner,
            before.execution_lease_token,
            before.execution_lease_expires_at,
        )

    response = client.post(
        f"/api/v1/connectors/runs/strict-api-run/{action}",
        json={},
    )

    assert response.status_code == 409, response.text
    with factory() as db:
        run = db.get(ConnectorRun, "strict-api-run")
        assert run is not None
        assert (
            run.status,
            run.cancellation_requested_at,
            run.execution_lease_owner,
            run.execution_lease_token,
            run.execution_lease_expires_at,
        ) == snapshot


def test_malformed_reserved_run_fails_closed_on_all_state_routes(
    api_client,
    monkeypatch,
) -> None:
    client, factory = api_client
    run_id = "malformed-reserved-run"
    malformed = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="armed",
        submission_idempotency_key="egress-arm:malformed",
        request_config_json={
            "connector_egress_arming": {
                "schema_id": "project6.connector_egress_arming.v0"
            }
        },
    )
    with factory() as db:
        db.add(malformed)
        db.commit()
    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "claim_connector_egress_arming",
        lambda *_args, **_kwargs: pytest.fail("malformed run reached claim"),
    )

    responses = [
        client.post(
            f"/api/v1/connectors/runs/{run_id}/{action}",
            json={},
        )
        for action in ("resume", "cancel")
    ]
    responses.append(
        client.post(
            (
                "/api/v1/connectors/egress-armings/"
                f"{run_id}/execute"
            ),
            json={
                "execution_idempotency_key": "malformed-execute",
                "arming_fingerprint": "f" * 64,
            },
        )
    )

    assert [response.status_code for response in responses] == [409, 409, 409]
    with factory() as db:
        current = db.get(ConnectorRun, run_id)
        assert current is not None
        assert current.status == "armed"
        assert current.cancellation_requested_at is None


def test_execute_http_refuses_before_strict_executor_selection(
    api_client,
    monkeypatch,
) -> None:
    client, factory = api_client
    envelope = _strict_envelope()
    envelope["connector_key"] = "sciencebase_public"
    run = ConnectorRun(
        connector_run_id="unadmitted-strict-run",
        connector_key="sciencebase_public",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status="armed",
        submission_idempotency_key="egress-arm:unadmitted",
        request_config_json={"connector_egress_arming": envelope},
        request_fingerprint=ARMING_FINGERPRINT,
    )
    with factory() as db:
        db.add(run)
        db.commit()
    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "resolve_current_egress_authority",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        api_router_module.connector_egress_arming,
        "claim_connector_egress_arming",
        lambda *_args, **_kwargs: pytest.fail(
            "unadmitted executor reached claim"
        ),
    )

    response = client.post(
        "/api/v1/connectors/egress-armings/unadmitted-strict-run/execute",
        json={
            "execution_idempotency_key": "unadmitted-execute",
            "arming_fingerprint": ARMING_FINGERPRINT,
        },
    )

    assert response.status_code == 409, response.text
    assert (
        response.json()["detail"]["code"]
        == "connector_strict_egress_http_execute_disabled"
    )
    with factory() as db:
        current = db.get(ConnectorRun, "unadmitted-strict-run")
        assert current is not None
        assert current.status == "armed"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/connectors/sciencebase-public/runs",
        "/api/v1/connectors/sciencebase-mcs/runs",
        "/api/v1/connectors/nrc-adams-aps/runs",
    ],
)
def test_exclusive_live_proof_blocks_generic_submit_before_service(
    api_client,
    monkeypatch,
    path: str,
) -> None:
    client, _ = api_client
    monkeypatch.setattr(settings, "connector_live_egress_enabled", True)
    monkeypatch.setattr(
        settings,
        "connector_live_egress_exclusive_proof_mode",
        True,
    )
    monkeypatch.setattr(
        api_router_module,
        "submit_connector_run",
        lambda *_args, **_kwargs: pytest.fail("generic submit reached service"),
    )
    monkeypatch.setattr(
        api_router_module,
        "submit_nrc_adams_run",
        lambda *_args, **_kwargs: pytest.fail("generic submit reached service"),
    )

    response = client.post(path, json={})

    assert response.status_code == 409, response.text
    assert (
        response.json()["detail"]["code"]
        == "connector_generic_route_blocked_by_exclusive_proof"
    )


@pytest.mark.parametrize(
    ("live_enabled", "exclusive_enabled"),
    [(False, False), (False, True), (True, False)],
)
@pytest.mark.parametrize(
    ("path", "connector_key"),
    [
        (
            "/api/v1/connectors/sciencebase-public/runs",
            "sciencebase_public",
        ),
        (
            "/api/v1/connectors/sciencebase-mcs/runs",
            "sciencebase_mcs",
        ),
        (
            "/api/v1/connectors/nrc-adams-aps/runs",
            "nrc_adams_aps",
        ),
    ],
)
def test_generic_submit_behavior_is_unchanged_when_either_proof_flag_is_off(
    api_client,
    monkeypatch,
    path: str,
    connector_key: str,
    live_enabled: bool,
    exclusive_enabled: bool,
) -> None:
    client, _ = api_client
    monkeypatch.setattr(
        settings,
        "connector_live_egress_enabled",
        live_enabled,
    )
    monkeypatch.setattr(
        settings,
        "connector_live_egress_exclusive_proof_mode",
        exclusive_enabled,
    )
    reached: list[str] = []
    run = ConnectorRun(
        connector_run_id=f"generic-{connector_key}",
        connector_key=connector_key,
        source_system="fixture",
        source_mode="fixture",
        status="pending",
        submitted_at=datetime.now(UTC),
    )

    def _submit(*_args, **_kwargs):
        reached.append(connector_key)
        return run, True

    monkeypatch.setattr(
        api_router_module,
        "submit_connector_run",
        _submit,
    )
    monkeypatch.setattr(
        api_router_module,
        "submit_nrc_adams_run",
        _submit,
    )
    monkeypatch.setattr(
        api_router_module,
        "_enqueue_connector_run",
        lambda *_args, **_kwargs: None,
    )

    response = client.post(path, json={})

    assert response.status_code == 202, response.text
    assert reached == [connector_key]


def test_new_post_routes_are_pre_body_authorized() -> None:
    assert (
        main._pre_body_operator_authorization_access_for_path(
            "/api/v1/connectors/egress-armings"
        )
        == "write"
    )
    assert (
        main._pre_body_operator_authorization_access_for_path(
            "/api/v1/connectors/egress-armings/run-1/execute"
        )
        == "write"
    )
