from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    AUDITOR_ROLE,
    OWNER_ROLE,
    SecXbrlInAppAuthPolicyError,
    route_level_operator_authorization_required,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_ROLES_HEADER = "X-Forwarded-Roles"

_IDENTITY_CANARY = "route-authz-operator@example.invalid"
_GROUPS_CANARY = "route-authz-workspace@example.invalid"
_ROLES_CANARY_OWNER = "route-authz-role-owner-canary"
_ROLES_CANARY_AUDITOR = "route-authz-role-auditor-canary"


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


# ---------------------------------------------------------------------------
# identity_presence mode (default)
# ---------------------------------------------------------------------------


class TestIdentityPresenceMode:
    """When mode=identity_presence the new authorization function is bit-identical
    to route_level_operator_identity_required for all headers combinations."""

    def test_passes_without_roles_header_auth_owner_none(self) -> None:
        result = route_level_operator_authorization_required({}, access="write")

        assert result["operator_ref_hash"] is not None
        assert result["workspace_ref_hash"] is not None
        assert result["authorization_mode"] == "identity_presence"
        assert result["role"] is None

    def test_read_access_passes_auth_owner_none(self) -> None:
        result = route_level_operator_authorization_required({}, access="read")

        assert result["authorization_mode"] == "identity_presence"
        assert result["access"] == "read"
        assert result["role"] is None

    def test_write_access_passes_auth_owner_none(self) -> None:
        result = route_level_operator_authorization_required({}, access="write")

        assert result["authorization_mode"] == "identity_presence"
        assert result["access"] == "write"

    def test_proxy_posture_without_roles_header_passes(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "auth_owner", "proxy")
        monkeypatch.setattr(settings, "trusted_proxy_mode", True)
        monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
        monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
        # layer3_route_authorization_mode remains "identity_presence" (default)
        # No roles header provided — must still pass (presence-only)
        headers = {_IDENTITY_HEADER: _IDENTITY_CANARY, _GROUPS_HEADER: _GROUPS_CANARY}

        result = route_level_operator_authorization_required(headers, access="write")

        assert result["authorization_mode"] == "identity_presence"
        assert result["role"] is None

    def test_identity_presence_result_identical_for_read_and_write(self) -> None:
        r_read = route_level_operator_authorization_required({}, access="read")
        r_write = route_level_operator_authorization_required({}, access="write")

        # core identity fields must be equal
        assert r_read["operator_ref_hash"] == r_write["operator_ref_hash"]
        assert r_read["workspace_ref_hash"] == r_write["workspace_ref_hash"]
        assert r_read["auth_owner_mode"] == r_write["auth_owner_mode"]
        assert r_read["authorization_mode"] == r_write["authorization_mode"]

    def test_no_exception_types_escape_in_identity_presence_mode(self) -> None:
        # Should never raise for any valid access class under auth_owner=none
        for access in ("read", "write"):
            result = route_level_operator_authorization_required({}, access=access)
            assert result is not None

    def test_invalid_access_class_raises_in_identity_presence_mode(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required({}, access="delete")

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_access_class_not_admitted"
        assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# role_enforcing mode — AUTH_OWNER=none
# ---------------------------------------------------------------------------


class TestRoleEnforcingAuthOwnerNone:
    """Under AUTH_OWNER=none + role_enforcing the local dev profile grants OWNER_ROLE
    unconditionally, so both read and write access are allowed."""

    @pytest.fixture(autouse=True)
    def _enable_role_enforcing(self, monkeypatch):
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")

    def test_owner_write_allowed(self) -> None:
        result = route_level_operator_authorization_required({}, access="write")

        assert result["role"] == OWNER_ROLE
        assert result["authorization_mode"] == "role_enforcing"
        assert result["access"] == "write"

    def test_owner_read_allowed(self) -> None:
        result = route_level_operator_authorization_required({}, access="read")

        assert result["role"] == OWNER_ROLE
        assert result["authorization_mode"] == "role_enforcing"
        assert result["access"] == "read"

    def test_result_contains_identity_fields(self) -> None:
        result = route_level_operator_authorization_required({}, access="write")

        assert result["operator_ref_hash"] is not None
        assert result["workspace_ref_hash"] is not None
        assert result["auth_owner_mode"] == "AUTH_OWNER_none_single_operator_dev_profile"


# ---------------------------------------------------------------------------
# role_enforcing mode — proxy posture
# ---------------------------------------------------------------------------


class TestRoleEnforcingProxyPosture:
    """Proxy posture with role_enforcing: owner/auditor token matrix."""

    @pytest.fixture(autouse=True)
    def _enable_role_enforcing_proxy(self, monkeypatch):
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        _configure_proxy(monkeypatch)

    def test_owner_token_read_allowed(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="owner"), access="read"
        )

        assert result["role"] == OWNER_ROLE
        assert result["access"] == "read"
        assert result["authorization_mode"] == "role_enforcing"

    def test_owner_token_write_allowed(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="owner"), access="write"
        )

        assert result["role"] == OWNER_ROLE
        assert result["access"] == "write"

    def test_auditor_token_read_allowed(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="auditor"), access="read"
        )

        assert result["role"] == AUDITOR_ROLE
        assert result["access"] == "read"

    def test_auditor_token_write_raises_forbidden(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value="auditor"), access="write"
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_role_access_forbidden"
        assert exc_info.value.http_status == 403

    def test_auditor_write_error_details_contain_access_not_role(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value="auditor"), access="write"
            )

        # details may expose access class but must not contain the raw header value
        details = exc_info.value.details
        assert details.get("access") == "write"

    def test_missing_roles_header_raises_closed(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value=None), access="write"
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_missing_role_authority"
        assert exc_info.value.http_status == 401

    def test_unrecognized_role_token_raises_closed(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value="superadmin"), access="write"
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_missing_role_authority"
        assert exc_info.value.http_status == 401

    def test_empty_roles_header_raises_closed(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value="   "), access="read"
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_missing_role_authority"

    def test_case_insensitive_owner_token_upper(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="OWNER"), access="write"
        )

        assert result["role"] == OWNER_ROLE

    def test_case_insensitive_owner_token_mixed(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="Owner"), access="read"
        )

        assert result["role"] == OWNER_ROLE

    def test_case_insensitive_auditor_token(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="AUDITOR"), access="read"
        )

        assert result["role"] == AUDITOR_ROLE

    def test_csv_roles_owner_wins_over_auditor(self) -> None:
        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="auditor, owner"), access="write"
        )

        assert result["role"] == OWNER_ROLE

    def test_custom_owner_role_token_mapping(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "platform-admin")

        result = route_level_operator_authorization_required(
            _proxy_headers(role_value="platform-admin"), access="write"
        )

        assert result["role"] == OWNER_ROLE

    def test_custom_owner_token_default_token_no_longer_matches(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_owner_role_tokens", "platform-admin")

        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value="owner"), access="write"
            )

        # "owner" is not in platform-admin token set, auditor not matched either → missing authority
        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_missing_role_authority"


# ---------------------------------------------------------------------------
# Leak canaries — error payloads must not echo raw header values
# ---------------------------------------------------------------------------


class TestLeakCanaries:
    """Error messages and exception details must not echo raw header values."""

    @pytest.fixture(autouse=True)
    def _proxy_role_enforcing(self, monkeypatch):
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        _configure_proxy(monkeypatch)

    def test_missing_role_error_does_not_leak_header_name(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value=None), access="write"
            )

        serialized = json.dumps({"message": exc_info.value.message, "details": exc_info.value.details})
        assert _ROLES_HEADER.lower() not in serialized.lower()
        assert _ROLES_HEADER not in serialized

    def test_missing_role_error_does_not_leak_identity_header_values(self) -> None:
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value=None), access="write"
            )

        serialized = json.dumps({"message": exc_info.value.message, "details": exc_info.value.details})
        assert _IDENTITY_CANARY not in serialized
        assert _GROUPS_CANARY not in serialized

    def test_role_forbidden_error_does_not_leak_raw_role_value(self) -> None:
        raw_role = _ROLES_CANARY_AUDITOR
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value=raw_role), access="write"
            )

        serialized = json.dumps({"message": exc_info.value.message, "details": exc_info.value.details})
        assert raw_role not in serialized
        assert _IDENTITY_CANARY not in serialized
        assert _GROUPS_CANARY not in serialized

    def test_unrecognized_role_error_does_not_leak_raw_token(self) -> None:
        raw_role = "super-secret-internal-role-token"
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value=raw_role), access="write"
            )

        serialized = json.dumps({"message": exc_info.value.message, "details": exc_info.value.details})
        assert raw_role not in serialized

    def test_role_forbidden_details_do_not_leak_role_name(self) -> None:
        """The 403 error on auditor+write must expose only 'access', not the derived role."""
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            route_level_operator_authorization_required(
                _proxy_headers(role_value="auditor"), access="write"
            )

        details = exc_info.value.details
        # The implementation includes access but not the role in details
        assert "access" in details
        assert "role" not in details
