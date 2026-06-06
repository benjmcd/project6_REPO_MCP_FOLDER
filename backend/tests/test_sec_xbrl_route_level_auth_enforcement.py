"""Route-level auth enforcement proof for the six protected SEC XBRL routes.

This file proves, at the HTTP route layer, that:
1. Proxy fail-closed (core proof): with auth_owner=proxy + trusted_proxy_mode=True but
   the identity header absent, each protected route's authenticated branch returns 401
   with an auth-policy error.
2. Untrusted proxy fail-closed: with auth_owner=proxy + trusted_proxy_mode=False the
   authenticated branches return 409 with untrusted_proxy_identity.
3. No raw leak: the 401 error body does not echo the header name or any raw identity.
4. Forbidden field rejected (400): caller-supplied forbidden fields are blocked at the
   auth-policy layer before the DB is consulted.
5. Anonymous redacted path preserved: the operator-review workflow status route, when
   called with NO workflow_id or basis_hash, skips the auth check entirely and returns
   a domain error (400), not a 401/409 auth error.

Existing coverage (not duplicated here):
- Service-level projection tests: test_sec_xbrl_proxy_identity_readonly_projection.py
- Auth-binding rollback / binding-fail 409: test_sec_xbrl_operator_review_workflow.py
- In-app auth policy unit tests: test_sec_xbrl_in_app_auth_policy_validation.py
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


# ---------------------------------------------------------------------------
# Route URLs
# ---------------------------------------------------------------------------

WORKFLOW_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/status"
DECISION_SUBMIT_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit"
DECISION_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status"
AUTHORITY_PREPARE_ROUTE = "/api/v1/layer3/sec-xbrl/value-reveal/authority/prepare"
VALUE_REVEAL_SUBMIT_ROUTE = "/api/v1/layer3/sec-xbrl/value-reveal/submit"
VALUE_REVEAL_STATUS_ROUTE_TEMPLATE = (
    "/api/v1/layer3/sec-xbrl/value-reveal/submit/status/{receipt_id}"
)

# Dummy 64-char hex hash (triggers the authenticated branch without needing a real row).
_DUMMY_HASH = "a" * 64
_DUMMY_ID = "dummy-receipt-id-for-auth-enforcement-proof"


# ---------------------------------------------------------------------------
# Minimal payloads that reference a receipt id / basis hash so that the
# handler takes the authenticated branch and calls _sec_xbrl_policy_decision.
# ---------------------------------------------------------------------------

def _workflow_status_payload() -> dict:
    return {
        "client_request_id": "route-auth-proof-workflow-status",
        "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
        "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
        "sec_xbrl_operator_review_workflow_id": _DUMMY_ID,
    }


def _decision_submit_payload() -> dict:
    return {
        "client_request_id": "route-auth-proof-decision-submit",
        "submit_mode": "sec_xbrl_operator_review_decision_submit_v1",
        "operator_decision": "submit_sec_xbrl_operator_review_decision",
        "review_decision": "approved",
        "decision_reason_code": "ready_for_next_freeze",
        "sec_xbrl_operator_review_workflow_id": _DUMMY_ID,
    }


def _decision_status_payload() -> dict:
    return {
        "client_request_id": "route-auth-proof-decision-status",
        "status_mode": "sec_xbrl_operator_review_decision_status_v1",
        "operator_decision": "inspect_sec_xbrl_operator_review_decision_status",
        "sec_xbrl_operator_review_decision_id": _DUMMY_ID,
    }


def _authority_prepare_payload() -> dict:
    return {
        "client_request_id": "route-auth-proof-authority-prepare",
        "authority_mode": "sec_xbrl_value_reveal_authority_receipt_v1",
        "operator_decision": "prepare_sec_xbrl_value_reveal_authority",
        "sec_xbrl_operator_review_decision_id": _DUMMY_ID,
        "decision_basis_hash": _DUMMY_HASH,
    }


def _value_reveal_submit_payload() -> dict:
    return {
        "client_request_id": "route-auth-proof-value-reveal-submit",
        "submit_mode": "sec_xbrl_controlled_value_reveal_submit_v1",
        "operator_decision": "submit_explicit_sec_xbrl_value_reveal_from_authority_receipt",
        "sec_xbrl_value_reveal_authority_receipt_id": _DUMMY_ID,
        "authority_basis_hash": _DUMMY_HASH,
        "operator_reveal_confirmation": True,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with in-memory SQLite; mirrors the reference fixture from
    test_sec_xbrl_proxy_identity_readonly_projection.py."""
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


@pytest.fixture()
def proxy_fail_closed_client(tmp_path, monkeypatch):
    """Client with auth_owner=proxy, trusted_proxy_mode=True, and a configured
    identity header.  Requests that omit that header trigger the 401 fail-closed path."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
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


@pytest.fixture()
def untrusted_proxy_client(tmp_path, monkeypatch):
    """Client with auth_owner=proxy, trusted_proxy_mode=False.
    Triggers the 409 untrusted-proxy fail-closed path."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_auth_fail_closed(response, *, expected_status: int) -> dict:
    """Assert response is an auth-policy block in workbench error envelope."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    return body


# ---------------------------------------------------------------------------
# 1. Proxy fail-closed proof: each authenticated route returns 401 when the
#    identity header is absent from the request.
# ---------------------------------------------------------------------------

def test_route_workflow_status_proxy_fail_closed_missing_identity(proxy_fail_closed_client) -> None:
    """POST /sec-xbrl/operator-review/workflow/status (authenticated branch) returns 401
    when proxy mode is active but identity header is absent."""
    response = proxy_fail_closed_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(),
        # No X-Forwarded-User header -> missing identity authority
    )
    body = _assert_auth_fail_closed(response, expected_status=401)
    assert "missing_identity_authority" in body.get("error_code", ""), body


def test_route_decision_submit_proxy_fail_closed_missing_identity(proxy_fail_closed_client) -> None:
    """POST /sec-xbrl/operator-review/workflow/decision/submit returns 401 when proxy
    mode is active but identity header is absent."""
    response = proxy_fail_closed_client.post(
        DECISION_SUBMIT_ROUTE,
        json=_decision_submit_payload(),
    )
    body = _assert_auth_fail_closed(response, expected_status=401)
    assert "missing_identity_authority" in body.get("error_code", ""), body


def test_route_decision_status_proxy_fail_closed_missing_identity(proxy_fail_closed_client) -> None:
    """POST /sec-xbrl/operator-review/workflow/decision/status returns 401 when proxy
    mode is active but identity header is absent."""
    response = proxy_fail_closed_client.post(
        DECISION_STATUS_ROUTE,
        json=_decision_status_payload(),
    )
    body = _assert_auth_fail_closed(response, expected_status=401)
    assert "missing_identity_authority" in body.get("error_code", ""), body


def test_route_authority_prepare_proxy_fail_closed_missing_identity(proxy_fail_closed_client) -> None:
    """POST /sec-xbrl/value-reveal/authority/prepare returns 401 when proxy mode is
    active but identity header is absent."""
    response = proxy_fail_closed_client.post(
        AUTHORITY_PREPARE_ROUTE,
        json=_authority_prepare_payload(),
    )
    body = _assert_auth_fail_closed(response, expected_status=401)
    assert "missing_identity_authority" in body.get("error_code", ""), body


def test_route_value_reveal_submit_proxy_fail_closed_missing_identity(
    proxy_fail_closed_client,
) -> None:
    """POST /sec-xbrl/value-reveal/submit returns 401 when proxy mode is active but
    identity header is absent."""
    response = proxy_fail_closed_client.post(
        VALUE_REVEAL_SUBMIT_ROUTE,
        json=_value_reveal_submit_payload(),
    )
    body = _assert_auth_fail_closed(response, expected_status=401)
    assert "missing_identity_authority" in body.get("error_code", ""), body


def test_route_value_reveal_status_proxy_fail_closed_missing_identity(
    proxy_fail_closed_client,
) -> None:
    """GET /sec-xbrl/value-reveal/submit/status/{id} returns 401 when proxy mode is
    active but identity header is absent.  This route always requires auth (no
    anonymous path)."""
    url = VALUE_REVEAL_STATUS_ROUTE_TEMPLATE.format(receipt_id=_DUMMY_ID)
    response = proxy_fail_closed_client.get(url)
    body = _assert_auth_fail_closed(response, expected_status=401)
    assert "missing_identity_authority" in body.get("error_code", ""), body


# ---------------------------------------------------------------------------
# 2. Untrusted proxy: one representative route returns 409 with the
#    untrusted_proxy_identity error code.
# ---------------------------------------------------------------------------

def test_route_workflow_status_untrusted_proxy_returns_409(untrusted_proxy_client) -> None:
    """POST /sec-xbrl/operator-review/workflow/status (authenticated branch) returns 409
    when trusted_proxy_mode=False."""
    response = untrusted_proxy_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(),
    )
    body = _assert_auth_fail_closed(response, expected_status=409)
    assert "untrusted_proxy_identity" in body.get("error_code", ""), body


# ---------------------------------------------------------------------------
# 3. No raw leak on the fail-closed error body.
# ---------------------------------------------------------------------------

def test_route_auth_fail_closed_body_has_no_raw_header_value(proxy_fail_closed_client) -> None:
    """The 401 error body must not echo any raw header name or identity value."""
    raw_user = "operator-rawname@example.invalid"
    response = proxy_fail_closed_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(),
        # A raw identity-like value IS sent (as the groups header); the identity
        # header (x-forwarded-user) is still absent -> 401. The sent value must
        # not be echoed back anywhere in the fail-closed error body.
        headers={"X-Forwarded-Groups": raw_user},
    )
    # Still 401 because the identity header (x-forwarded-user) is absent
    assert response.status_code == 401, response.text
    body_text = response.text
    assert raw_user not in body_text
    assert "X-Forwarded" not in body_text


# ---------------------------------------------------------------------------
# 4. Forbidden field rejected (400): caller-supplied forbidden fields must be
#    blocked BEFORE any DB or auth-binding logic runs.
# ---------------------------------------------------------------------------

def test_route_decision_submit_rejects_forbidden_field_proxy_identity_header(client) -> None:
    """POST /sec-xbrl/operator-review/workflow/decision/submit rejects the
    caller-supplied 'proxy_identity_header' forbidden field with a 400.

    The route first checks for any extra / ungoverned fields via its own guard
    (error code: ..._request_fields_not_admitted).  If the field passes that
    guard it would then be caught by the auth-policy layer
    (error code: ..._forbidden_request_fields).  Either way the result is a
    400 workbench error that blocks the request."""
    payload = {
        **_decision_submit_payload(),
        "proxy_identity_header": "x-injected-identity",
    }
    response = client.post(DECISION_SUBMIT_ROUTE, json=payload)
    assert response.status_code == 400, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    error_code = body.get("error_code", "")
    assert "forbidden_request_fields" in error_code or "not_admitted" in error_code, body


def test_route_authority_prepare_rejects_forbidden_field_operator_email(client) -> None:
    """POST /sec-xbrl/value-reveal/authority/prepare rejects 'operator_email'
    forbidden field with 400.

    Extra-field guard fires before (or in lieu of) the auth-policy forbidden-
    fields check; both produce a 400 workbench error block."""
    payload = {
        **_authority_prepare_payload(),
        "operator_email": "someone@example.invalid",
    }
    response = client.post(AUTHORITY_PREPARE_ROUTE, json=payload)
    assert response.status_code == 400, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    error_code = body.get("error_code", "")
    assert "forbidden_request_fields" in error_code or "not_admitted" in error_code, body


def test_route_value_reveal_submit_rejects_forbidden_field_auth_policy_override(
    client,
) -> None:
    """POST /sec-xbrl/value-reveal/submit rejects 'auth_policy_override' forbidden
    field with 400.

    Extra-field guard fires before (or in lieu of) the auth-policy forbidden-
    fields check; both produce a 400 workbench error block."""
    payload = {
        **_value_reveal_submit_payload(),
        "auth_policy_override": "bypass",
    }
    response = client.post(VALUE_REVEAL_SUBMIT_ROUTE, json=payload)
    assert response.status_code == 400, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    error_code = body.get("error_code", "")
    assert "forbidden_request_fields" in error_code or "not_admitted" in error_code, body


# ---------------------------------------------------------------------------
# 5. Anonymous redacted path preserved: the operator-review workflow status
#    route with NO workflow_id / basis_hash skips the auth-policy check and
#    returns a domain-level 400 (not 401/409).
#
# Mechanism: when both id fields are None the handler takes the early-return
# branch (line 17245-17249 in layer3.py) which calls
# inspect_redacted_operator_review_workflow_status directly WITHOUT calling
# _sec_xbrl_policy_decision.  The service then raises a domain error because
# neither id is provided, resulting in a 400 with a workflow-domain error code
# -- NOT an auth-policy error code.
# ---------------------------------------------------------------------------

def test_route_workflow_status_no_id_returns_domain_400_not_auth_error(client) -> None:
    """Without a workflow_id or basis_hash the route bypasses auth entirely.
    The response is a domain 400, not an auth-policy 401/409.

    This fixture uses auth_owner=none (default).  Under strict enforcement the
    policy check is non-blocking for local operator principal, so the service
    domain error is still what the caller observes -- the invariant holds."""
    response = client.post(
        WORKFLOW_STATUS_ROUTE,
        json={
            "client_request_id": "route-auth-proof-anon-path",
            "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
            "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
            # sec_xbrl_operator_review_workflow_id and workflow_basis_hash intentionally absent
        },
    )
    assert response.status_code == 400, response.text
    body = response.json()
    # Must be a domain error, not an auth-policy error
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    error_code = body.get("error_code", "")
    assert "auth_policy" not in error_code, (
        f"Expected domain error, got auth-policy error: {error_code}"
    )
    # The domain service rejects the call for missing authority
    assert "authority_missing" in error_code or "workflow" in error_code, body


# ---------------------------------------------------------------------------
# 6. No-identity bypass hardening: strict enforcement gates the no-id branches.
#
# 6a. Strict-on / proxy / no identity header / no workflow_id -> fail closed
#     (identity check runs, proxy fails closed with 401).
# 6b. Strict-off / proxy / no identity header / no workflow_id -> old bypass
#     (service domain result returned, not an auth error; reversibility proof).
# 6c. Strict-on / auth_owner=none / no workflow_id -> domain result returned
#     (policy non-blocking for local operator; explicit documentation test).
# 6d. Same as 6a but for the decision-status route.
# ---------------------------------------------------------------------------

def test_route_workflow_status_no_id_strict_on_proxy_fail_closed(
    tmp_path, monkeypatch
) -> None:
    """Strict enforcement ON + proxy mode + no identity header + no workflow_id:
    the no-id branch now runs _sec_xbrl_policy_decision, which fails closed (401)
    when the proxy identity header is absent."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "layer3_sec_xbrl_auth_policy_route_enforcement_strict", True)
    bootstrap_storage_tree(storage_dir)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
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
    try:
        from fastapi.testclient import TestClient
        strict_proxy_client = TestClient(app)
        response = strict_proxy_client.post(
            WORKFLOW_STATUS_ROUTE,
            json={
                "client_request_id": "route-auth-proof-strict-proxy-no-id",
                "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
                "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
                # no workflow_id or basis_hash
            },
            # no X-Forwarded-User header -> policy fails closed
        )
        body = _assert_auth_fail_closed(response, expected_status=401)
        assert "missing_identity_authority" in body.get("error_code", ""), body
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_route_workflow_status_no_id_strict_off_proxy_returns_domain_result(
    tmp_path, monkeypatch
) -> None:
    """Strict enforcement OFF + proxy mode + no identity header + no workflow_id:
    the old bypass behavior is preserved -- the route calls the service directly
    without auth and returns a domain result (not an auth error).
    This is the reversibility proof: setting the flag False restores prior behavior."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "layer3_sec_xbrl_auth_policy_route_enforcement_strict", False)
    bootstrap_storage_tree(storage_dir)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
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
    try:
        from fastapi.testclient import TestClient
        strict_off_client = TestClient(app)
        response = strict_off_client.post(
            WORKFLOW_STATUS_ROUTE,
            json={
                "client_request_id": "route-auth-proof-strict-off-no-id",
                "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
                "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
                # no workflow_id or basis_hash
            },
            # no identity header -- but strict is off so no auth check fires
        )
        # Must return a domain error (400), NOT an auth error (401/409)
        assert response.status_code == 400, response.text
        body = response.json()
        assert body.get("schema_id") == "layer3.workbench_error.v1", body
        error_code = body.get("error_code", "")
        assert "auth_policy" not in error_code, (
            f"Strict-off should not return auth-policy error: {error_code}"
        )
        assert "authority_missing" in error_code or "workflow" in error_code, body
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_route_workflow_status_no_id_none_mode_strict_on_non_blocking(client) -> None:
    """Strict enforcement ON + auth_owner=none + no workflow_id: the policy check
    is non-blocking (local operator principal), so the route returns the service
    domain result (400), not an auth error.  Explicit documentation test."""
    response = client.post(
        WORKFLOW_STATUS_ROUTE,
        json={
            "client_request_id": "route-auth-proof-none-strict-no-id",
            "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
            "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
            # no workflow_id or basis_hash
        },
    )
    assert response.status_code == 400, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    error_code = body.get("error_code", "")
    assert "auth_policy" not in error_code, (
        f"auth_owner=none should be non-blocking: {error_code}"
    )
    assert "authority_missing" in error_code or "workflow" in error_code, body


def test_route_decision_status_no_id_strict_on_proxy_fail_closed(
    tmp_path, monkeypatch
) -> None:
    """Strict enforcement ON + proxy mode + no identity header + no decision_id:
    the decision-status no-id branch now runs _sec_xbrl_policy_decision and
    fails closed (401) when the proxy identity header is absent."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
    monkeypatch.setattr(settings, "layer3_sec_xbrl_auth_policy_route_enforcement_strict", True)
    bootstrap_storage_tree(storage_dir)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
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
    try:
        from fastapi.testclient import TestClient
        strict_proxy_client = TestClient(app)
        response = strict_proxy_client.post(
            DECISION_STATUS_ROUTE,
            json={
                "client_request_id": "route-auth-proof-decision-status-strict-no-id",
                "status_mode": "sec_xbrl_operator_review_decision_status_v1",
                "operator_decision": "inspect_sec_xbrl_operator_review_decision_status",
                # no decision_id or decision_basis_hash
            },
            # no X-Forwarded-User header -> policy fails closed
        )
        body = _assert_auth_fail_closed(response, expected_status=401)
        assert "missing_identity_authority" in body.get("error_code", ""), body
    finally:
        app.dependency_overrides.pop(get_db, None)
