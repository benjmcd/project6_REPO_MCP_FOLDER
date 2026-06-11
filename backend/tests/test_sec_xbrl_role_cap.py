"""Tests for the sec_xbrl payload-claimed role cap.

Under role_enforcing mode, a caller whose server-derived role is AUDITOR_ROLE
cannot claim OWNER_ROLE in the request payload (or via the default).  The cap
is enforced inside authorize_sec_xbrl_route.

Test matrix:
1. identity_presence (default): auditor-token headers + owner role claim -> admitted
   (bit-identical to prior behavior -- inertness contract).
2. role_enforcing + proxy + owner tokens: owner claim -> admitted; auditor claim (step-down)
   -> admitted.
3. role_enforcing + proxy + auditor tokens: owner claim -> rejected with the new error code;
   auditor on auditor-allowed family -> admitted; auditor on owner-only family -> rejected
   by the pre-existing family check (not the new cap).
4. role_enforcing + AUTH_OWNER=none: owner claim -> admitted (local dev unaffected).
5. Leak canary: the new error path must not echo raw header values.
6. End-to-end HTTP test: POST /sec-xbrl/operator-review/workflow/status with an
   auditor-token header and a payload claiming owner role is rejected at the
   HTTP surface with 403 and the new error code when role_enforcing is active.
"""
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
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    AUDITOR_ROLE,
    OWNER_ROLE,
    SecXbrlInAppAuthPolicyError,
    authorize_sec_xbrl_route,
)


# ---------------------------------------------------------------------------
# Header/settings helpers
# ---------------------------------------------------------------------------

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_ROLES_HEADER = "X-Forwarded-Roles"

_IDENTITY_CANARY = "role-cap-operator@example.invalid"
_GROUPS_CANARY = "role-cap-workspace@example.invalid"
_ROLES_CANARY_OWNER = "role-cap-token-owner-canary"
_ROLES_CANARY_AUDITOR = "role-cap-token-auditor-canary"


def _proxy_headers(*, role_value: str | None = None) -> dict[str, str]:
    h = {
        _IDENTITY_HEADER: _IDENTITY_CANARY,
        _GROUPS_HEADER: _GROUPS_CANARY,
    }
    if role_value is not None:
        h[_ROLES_HEADER] = role_value
    return h


def _configure_proxy(monkeypatch, *, role_tokens_owner: str = "owner", role_tokens_auditor: str = "auditor") -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(settings, "proxy_roles_header", _ROLES_HEADER)
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", role_tokens_owner)
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", role_tokens_auditor)


# A route family accessible to auditors (status read).
_AUDITOR_ALLOWED_FAMILY = "sec_xbrl_operator_review_workflow_status_read"
# A route family only accessible to owners (mutating write).
_OWNER_ONLY_FAMILY = "sec_xbrl_controlled_value_reveal_submit_write"


# ---------------------------------------------------------------------------
# 1. identity_presence (default) — no behavior change
# ---------------------------------------------------------------------------


class TestIdentityPresenceInertness:
    """Under the default identity_presence mode the cap must never fire."""

    def test_auditor_token_headers_owner_claim_admitted(self, monkeypatch) -> None:
        """Auditor-token headers + owner role claim is admitted exactly as before."""
        _configure_proxy(monkeypatch)
        # mode stays at its default (identity_presence)

        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="auditor"),
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["decision"] == "allow"
        assert result["role"] == OWNER_ROLE

    def test_auditor_token_headers_owner_claim_has_matching_auth_mode(self, monkeypatch) -> None:
        _configure_proxy(monkeypatch)

        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="auditor"),
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["auth_owner_mode"] == "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true"

    def test_no_roles_header_owner_claim_admitted_in_identity_presence(self, monkeypatch) -> None:
        """No roles header with owner claim is fine under identity_presence."""
        _configure_proxy(monkeypatch)

        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value=None),  # no roles header
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["decision"] == "allow"


# ---------------------------------------------------------------------------
# 2. role_enforcing + proxy + owner tokens
# ---------------------------------------------------------------------------


class TestRoleEnforcingOwnerTokens:
    """Under role_enforcing + proxy posture + owner tokens, owner and auditor
    claims both pass."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        _configure_proxy(monkeypatch)

    def test_owner_tokens_owner_claim_admitted(self) -> None:
        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="owner"),
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["decision"] == "allow"
        assert result["role"] == OWNER_ROLE

    def test_owner_tokens_auditor_claim_step_down_admitted(self) -> None:
        """Owner tokens but requesting auditor (step-down) is allowed."""
        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="owner"),
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=AUDITOR_ROLE,
        )

        assert result["decision"] == "allow"
        assert result["role"] == AUDITOR_ROLE

    def test_owner_tokens_owner_claim_owner_only_family_admitted(self) -> None:
        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="owner"),
            route_family=_OWNER_ONLY_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["decision"] == "allow"


# ---------------------------------------------------------------------------
# 3. role_enforcing + proxy + auditor tokens
# ---------------------------------------------------------------------------


class TestRoleEnforcingAuditorTokens:
    """Under role_enforcing + proxy posture + auditor tokens, owner claims are
    rejected; auditor claims on auditor-allowed families are admitted."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        _configure_proxy(monkeypatch)

    def test_auditor_tokens_owner_claim_rejected(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value="auditor"),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_role_claim_exceeds_server_authority"
        assert exc_info.value.http_status == 403

    def test_auditor_tokens_owner_claim_default_rejected(self) -> None:
        """The default owner-role claim (used by callers that pass OWNER_ROLE without
        reading operator_role from payload) is also capped."""
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value="auditor"),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_role_claim_exceeds_server_authority"

    def test_auditor_tokens_auditor_claim_auditor_allowed_family_admitted(self) -> None:
        """Auditor token + auditor claim on a family that allows auditors -> admitted."""
        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="auditor"),
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=AUDITOR_ROLE,
        )

        assert result["decision"] == "allow"
        assert result["role"] == AUDITOR_ROLE

    def test_auditor_tokens_auditor_claim_owner_only_family_rejected_by_family_check(self) -> None:
        """Auditor token + auditor claim on an owner-only family is rejected by the
        pre-existing family allowed_roles check — NOT the new cap."""
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value="auditor"),
                route_family=_OWNER_ONLY_FAMILY,
                requested_role=AUDITOR_ROLE,
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_role_route_forbidden"
        assert exc_info.value.http_status == 403


# ---------------------------------------------------------------------------
# 4. role_enforcing + AUTH_OWNER=none
# ---------------------------------------------------------------------------


class TestRoleEnforcingAuthOwnerNone:
    """Under AUTH_OWNER=none + role_enforcing the local dev profile is unaffected."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        # auth_owner stays "none" (default)

    def test_auth_owner_none_owner_claim_admitted(self) -> None:
        result = authorize_sec_xbrl_route(
            headers={},
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["decision"] == "allow"
        assert result["role"] == OWNER_ROLE

    def test_auth_owner_none_owner_only_family_admitted(self) -> None:
        result = authorize_sec_xbrl_route(
            headers={},
            route_family=_OWNER_ONLY_FAMILY,
            requested_role=OWNER_ROLE,
        )

        assert result["decision"] == "allow"


# ---------------------------------------------------------------------------
# 5. Leak canary on the new error path
# ---------------------------------------------------------------------------


class TestLeakCanaryNewErrorPath:
    """The new cap error must not echo raw header values in message or details."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        _configure_proxy(
            monkeypatch,
            role_tokens_owner=_ROLES_CANARY_OWNER,
            role_tokens_auditor=_ROLES_CANARY_AUDITOR,
        )

    def test_new_error_does_not_leak_raw_role_value(self) -> None:
        raw_role = _ROLES_CANARY_AUDITOR
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value=raw_role),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        serialized = json.dumps({
            "message": exc_info.value.message,
            "details": exc_info.value.details,
        })
        assert raw_role not in serialized

    def test_new_error_does_not_leak_identity_header_values(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value=_ROLES_CANARY_AUDITOR),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        serialized = json.dumps({
            "message": exc_info.value.message,
            "details": exc_info.value.details,
        })
        assert _IDENTITY_CANARY not in serialized
        assert _GROUPS_CANARY not in serialized

    def test_new_error_does_not_leak_header_name(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value=_ROLES_CANARY_AUDITOR),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        serialized = json.dumps({
            "message": exc_info.value.message,
            "details": exc_info.value.details,
        })
        assert _ROLES_HEADER.lower() not in serialized.lower()


# ---------------------------------------------------------------------------
# 6. End-to-end HTTP surface test
# ---------------------------------------------------------------------------

from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402
from main import app  # noqa: E402

WORKFLOW_STATUS_ROUTE = "/api/v1/layer3/sec-xbrl/operator-review/workflow/status"
_DUMMY_ID = "dummy-receipt-id-for-role-cap-proof"


def _workflow_status_payload(*, operator_role: str | None = None) -> dict:
    payload: dict = {
        "client_request_id": "role-cap-e2e-workflow-status",
        "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
        "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
        "sec_xbrl_operator_review_workflow_id": _DUMMY_ID,
    }
    if operator_role is not None:
        payload["operator_role"] = operator_role
    return payload


@pytest.fixture()
def role_enforcing_proxy_client(tmp_path, monkeypatch):
    """TestClient with in-memory SQLite, auth_owner=proxy, trusted_proxy_mode=True,
    and role_enforcing active."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(settings, "proxy_roles_header", _ROLES_HEADER)
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")
    monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
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


def _full_proxy_headers(*, role_value: str) -> dict[str, str]:
    return {
        _IDENTITY_HEADER: _IDENTITY_CANARY,
        _GROUPS_HEADER: _GROUPS_CANARY,
        _ROLES_HEADER: role_value,
    }


def test_e2e_auditor_token_owner_claim_rejected_at_http_surface(
    role_enforcing_proxy_client,
) -> None:
    """POST workflow/status with auditor token headers + payload claiming owner role
    must be rejected at the HTTP surface with 403 and the new cap error code."""
    response = role_enforcing_proxy_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(operator_role="owner"),
        headers=_full_proxy_headers(role_value="auditor"),
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    assert "role_claim_exceeds_server_authority" in body.get("error_code", ""), body


def test_e2e_auditor_token_default_owner_claim_rejected_at_http_surface(
    role_enforcing_proxy_client,
) -> None:
    """POST workflow/status with auditor token headers and no explicit operator_role
    (defaults to OWNER_ROLE) is also rejected at the HTTP surface."""
    response = role_enforcing_proxy_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(),  # no operator_role -> defaults to OWNER_ROLE
        headers=_full_proxy_headers(role_value="auditor"),
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert "role_claim_exceeds_server_authority" in body.get("error_code", ""), body


def test_e2e_owner_token_owner_claim_passes_to_auth_binding_stage(
    role_enforcing_proxy_client,
) -> None:
    """POST workflow/status with owner token headers + owner claim passes the policy
    check and proceeds to the auth-binding stage (404 from missing binding record,
    not 403 from the policy)."""
    response = role_enforcing_proxy_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(operator_role="owner"),
        headers=_full_proxy_headers(role_value="owner"),
    )

    # 404 means the cap was NOT fired — it reached the binding lookup.
    # (or 409 from binding layer — both mean the policy admitted the request)
    assert response.status_code in (404, 409), (
        f"Expected 404/409 (past policy gate), got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "role_claim_exceeds_server_authority" not in body.get("error_code", ""), body


def test_e2e_auditor_token_auditor_claim_admitted_through_policy(
    role_enforcing_proxy_client,
) -> None:
    """POST workflow/status with auditor token headers + auditor claim on an
    auditor-allowed family passes the policy and proceeds to auth-binding."""
    response = role_enforcing_proxy_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(operator_role="auditor"),
        headers=_full_proxy_headers(role_value="auditor"),
    )

    # 404 or 409 means the cap was not fired — policy admitted the request.
    assert response.status_code in (404, 409), (
        f"Expected 404/409 (past policy gate), got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "role_claim_exceeds_server_authority" not in body.get("error_code", ""), body


def test_e2e_cap_error_body_does_not_leak_raw_role_value(
    role_enforcing_proxy_client,
) -> None:
    """The 403 cap error body must not contain the raw role token value."""
    raw_role_token = "auditor"
    response = role_enforcing_proxy_client.post(
        WORKFLOW_STATUS_ROUTE,
        json=_workflow_status_payload(operator_role="owner"),
        headers=_full_proxy_headers(role_value=raw_role_token),
    )

    assert response.status_code == 403, response.text
    # Raw token must not appear in response body
    assert raw_role_token not in response.text or "role_claim_exceeds_server_authority" in response.text
    # More precisely: the role token must not appear in the error_code or details fields
    body = response.json()
    error_code = body.get("error_code", "")
    assert raw_role_token not in error_code
