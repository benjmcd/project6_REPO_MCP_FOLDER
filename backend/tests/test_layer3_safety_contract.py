"""Safety-contract tests for Layer 3 production-posture rails.

Contracts tested:
(a) Controlled value-reveal submit is refused (feature-flag disabled path) when
    layer3_sec_xbrl_controlled_value_reveal_submit_enabled is False.
(b) Settings with DEPLOYMENT_MODE=nonlocal must reject startup when any value-reveal
    conjunction flag is armed (fail-closed nonlocal validator).
(c) Proxy identity fail-closed: AUTH_OWNER=proxy + TRUSTED_PROXY_MODE=false -> blocked
    by the in-app auth policy; trusted proxy but missing identity header -> blocked.
(d) Role ceiling: role_enforcing mode blocks an AUDITOR-token caller from claiming
    OWNER_ROLE (insufficient role).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.services.layer3_sec_xbrl_controlled_value_reveal_submit import (
    SecXbrlControlledValueRevealSubmitError,
    submit_controlled_value_reveal,
)
from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    AUDITOR_ROLE,
    OWNER_ROLE,
    SecXbrlInAppAuthPolicyError,
    authorize_sec_xbrl_route,
)


# ---------------------------------------------------------------------------
# Shared valid nonlocal Settings kwargs (mirrors test_deployment_profile_validation.py)
# ---------------------------------------------------------------------------

_POSTGRES_URL = "postgresql+psycopg://placeholder:placeholder@localhost:5432/placeholder_db"

_NONLOCAL_VALID_KWARGS: dict[str, str] = {
    "DEPLOYMENT_MODE": "nonlocal",
    "ALLOWED_ORIGINS": "https://app.example.com",
    "AUTH_OWNER": "proxy",
    "TRUSTED_PROXY_MODE": "true",
    "PROXY_IDENTITY_HEADER": "X-Forwarded-User",
    "STORAGE_EXPOSURE": "disabled",
    "DB_INIT_MODE": "migrate",
    "DATABASE_URL": _POSTGRES_URL,
    "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED": "true",
}


def _build_nonlocal(**overrides: str) -> Settings:
    kwargs = {**_NONLOCAL_VALID_KWARGS, **overrides}
    return Settings(_env_file=None, **kwargs)


# ---------------------------------------------------------------------------
# (a) Controlled value-reveal submit: refused when flag is off
# ---------------------------------------------------------------------------


class TestControlledValueRevealSubmitRefusedWhenFlagOff:
    """Contract: submit_controlled_value_reveal raises SecXbrlControlledValueRevealSubmitError
    with code 'sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled' when
    layer3_sec_xbrl_controlled_value_reveal_submit_enabled is False.

    This is the fail-closed baseline: the flag defaults to False, so the route is
    disabled unless an operator explicitly enables it.
    """

    def test_submit_raises_feature_flag_disabled_when_flag_off(self, monkeypatch) -> None:
        """Feature-flag-off path: service rejects submit with the feature-flag-disabled code."""
        monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)

        with pytest.raises(SecXbrlControlledValueRevealSubmitError) as exc_info:
            submit_controlled_value_reveal(
                db=None,  # type: ignore[arg-type]  # never reached — flag check is first
                client_request_id="safe-request-id-no-raw",
                sec_xbrl_value_reveal_authority_receipt_id="safe-receipt-id",
                authority_basis_hash="a" * 64,
                operator_reveal_confirmation=True,
            )

        exc = exc_info.value
        assert exc.code == "sec_xbrl_controlled_value_reveal_submit_feature_flag_disabled"
        assert exc.http_status == 409

    def test_submit_error_message_does_not_expose_raw_identifiers(self, monkeypatch) -> None:
        """The feature-flag-disabled error must not expose raw caller values in message/details."""
        monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)
        raw_id = "raw-operator@example.invalid"

        with pytest.raises(SecXbrlControlledValueRevealSubmitError) as exc_info:
            submit_controlled_value_reveal(
                db=None,  # type: ignore[arg-type]
                client_request_id=raw_id,
                sec_xbrl_value_reveal_authority_receipt_id="safe-receipt-id",
                authority_basis_hash="a" * 64,
                operator_reveal_confirmation=True,
            )

        exc = exc_info.value
        # The raw client_request_id must not appear in message or details
        assert raw_id not in exc.message
        assert raw_id not in str(exc.details)


def test_sec_xbrl_storage_root_hygiene_override_ack_defaults_off_and_is_env_gated() -> None:
    """The A8 storage-root hygiene override is a narrow explicit operator acknowledgement."""
    default_settings = Settings(_env_file=None)
    enabled_settings = Settings(
        _env_file=None,
        LAYER3_SEC_XBRL_STORAGE_ROOT_HYGIENE_OVERRIDE_ACK="true",
    )

    assert default_settings.layer3_sec_xbrl_storage_root_hygiene_override_ack is False
    assert enabled_settings.layer3_sec_xbrl_storage_root_hygiene_override_ack is True


# ---------------------------------------------------------------------------
# (b) Nonlocal Settings rejects armed value-reveal flags (fail-closed validator)
# ---------------------------------------------------------------------------

# Value-reveal footgun flags forbidden in nonlocal posture.
# LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED is intentionally excluded:
# it is a required authorization gate in nonlocal deployments (not a footgun).
_NONLOCAL_FORBIDDEN_FLAGS = [
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED",
]

_RAW_BEARING_STORAGE_CONTAINMENT_FLAGS = [
    "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED",
]


class TestNonlocalRejectsArmedValueRevealFlags:
    """Contract: Settings(DEPLOYMENT_MODE=nonlocal) must raise ValueError (or ValidationError)
    when any value-reveal conjunction footgun flag is true.

    This is the fail-closed production-posture gate: nonlocal startup is refused if the
    footgun flags are armed.
    """

    @pytest.mark.parametrize("flag", _NONLOCAL_FORBIDDEN_FLAGS)
    def test_nonlocal_rejects_armed_flag(self, flag: str) -> None:
        """Each value-reveal footgun flag individually causes nonlocal startup to fail."""
        with pytest.raises((ValidationError, ValueError)):
            _build_nonlocal(**{flag: "true"})

    def test_nonlocal_valid_baseline_constructs_ok(self) -> None:
        """Baseline nonlocal config with all footgun flags false/absent constructs without error."""
        profile = _build_nonlocal()
        assert profile.deployment_mode == "nonlocal"

    def test_nonlocal_rejects_controlled_submit_flag_error_message(self) -> None:
        """Error message names the offending flag so the operator can diagnose it."""
        with pytest.raises(
            (ValidationError, ValueError),
            match="LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
        ):
            _build_nonlocal(LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED="true")

    @pytest.mark.parametrize("flag", _RAW_BEARING_STORAGE_CONTAINMENT_FLAGS)
    def test_local_storage_mount_rejects_raw_bearing_flags(self, flag: str) -> None:
        """Local default /storage exposure must not coexist with raw-bearing flags."""
        with pytest.raises((ValidationError, ValueError), match=flag):
            Settings(_env_file=None, **{flag: "true"})

    def test_onedrive_storage_rejects_raw_bearing_flag_even_when_unmounted(self, tmp_path: Path) -> None:
        """A synced storage root is unsafe even when /storage exposure is disabled."""
        storage_dir = tmp_path / "OneDrive - Contoso" / "storage"
        database_url = f"sqlite:///{(tmp_path / 'safe.db').as_posix()}"

        with pytest.raises((ValidationError, ValueError), match="STORAGE_DIR"):
            Settings(
                _env_file=None,
                STORAGE_EXPOSURE="disabled",
                STORAGE_DIR=str(storage_dir),
                DATABASE_URL=database_url,
                LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED="true",
            )

    def test_onedrive_sqlite_database_rejects_raw_bearing_flag_even_when_unmounted(self, tmp_path: Path) -> None:
        """A synced SQLite DB path is unsafe even when /storage exposure is disabled."""
        storage_dir = tmp_path / "private-storage"
        database_path = tmp_path / "OneDrive" / "method_aware.db"

        with pytest.raises((ValidationError, ValueError), match="DATABASE_URL"):
            Settings(
                _env_file=None,
                STORAGE_EXPOSURE="disabled",
                STORAGE_DIR=str(storage_dir),
                DATABASE_URL=f"sqlite:///{database_path.as_posix()}",
                LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED="true",
            )

    def test_sqlite_file_uri_database_rejects_raw_bearing_flag_when_inside_repo(self) -> None:
        """Persistent SQLite file: URIs must be containment-checked."""
        repo_database = BACKEND / "app" / "storage" / "sec.db"

        with pytest.raises((ValidationError, ValueError), match="DATABASE_URL"):
            Settings(
                _env_file=None,
                STORAGE_EXPOSURE="disabled",
                STORAGE_DIR="/tmp/project6-storage",
                DATABASE_URL=f"sqlite:///file:{repo_database.as_posix()}?uri=true",
                LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED="true",
            )

    def test_safe_unmounted_local_mode_armed_flag_constructs_ok(self, tmp_path: Path) -> None:
        """Local raw-bearing flags require private storage and disabled storage exposure."""
        profile = Settings(
            _env_file=None,
            STORAGE_EXPOSURE="disabled",
            STORAGE_DIR=str(tmp_path / "private-storage"),
            DATABASE_URL=f"sqlite:///{(tmp_path / 'private.db').as_posix()}",
            LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED="true",
        )
        assert profile.deployment_mode == "local"
        assert profile.layer3_sec_xbrl_controlled_value_reveal_submit_enabled is True


# ---------------------------------------------------------------------------
# (c) Proxy identity fail-closed (service-layer)
# ---------------------------------------------------------------------------

_IDENTITY_HEADER = "X-Forwarded-User"
_GROUPS_HEADER = "X-Forwarded-Groups"
_ROLES_HEADER = "X-Forwarded-Roles"
_ANY_ROUTE_FAMILY = "sec_xbrl_operator_review_workflow_status_read"


class TestProxyIdentityFailClosedServiceLayer:
    """Contract: authorize_sec_xbrl_route enforces proxy identity at the service layer.

    AUTH_OWNER=proxy + TRUSTED_PROXY_MODE=false -> untrusted-proxy error (409-class).
    AUTH_OWNER=proxy + TRUSTED_PROXY_MODE=true + empty identity header -> missing-identity error (401-class).
    """

    def test_untrusted_proxy_raises_untrusted_proxy_error(self, monkeypatch) -> None:
        """Contract: untrusted proxy raises SecXbrlInAppAuthPolicyError with the
        untrusted-proxy code and 409 HTTP status."""
        monkeypatch.setattr(settings, "auth_owner", "proxy")
        monkeypatch.setattr(settings, "trusted_proxy_mode", False)
        monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)

        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers={_IDENTITY_HEADER: "operator@example.invalid"},
                route_family=_ANY_ROUTE_FAMILY,
                requested_role=OWNER_ROLE,
            )

        exc = exc_info.value
        assert exc.code == "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity"
        assert exc.http_status == 409

    def test_untrusted_proxy_error_does_not_leak_identity(self, monkeypatch) -> None:
        """The untrusted-proxy error must not echo the supplied identity value."""
        monkeypatch.setattr(settings, "auth_owner", "proxy")
        monkeypatch.setattr(settings, "trusted_proxy_mode", False)
        monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
        canary = "canary-identity-leak@example.invalid"

        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers={_IDENTITY_HEADER: canary},
                route_family=_ANY_ROUTE_FAMILY,
                requested_role=OWNER_ROLE,
            )

        import json as _json
        serialized = _json.dumps({
            "message": exc_info.value.message,
            "details": exc_info.value.details,
        })
        assert canary not in serialized

    def test_trusted_proxy_missing_identity_raises_missing_identity_error(self, monkeypatch) -> None:
        """Contract: trusted proxy with no identity header raises SecXbrlInAppAuthPolicyError
        with the missing-identity code and 401 HTTP status."""
        monkeypatch.setattr(settings, "auth_owner", "proxy")
        monkeypatch.setattr(settings, "trusted_proxy_mode", True)
        monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)

        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers={},  # no identity header
                route_family=_ANY_ROUTE_FAMILY,
                requested_role=OWNER_ROLE,
            )

        exc = exc_info.value
        assert exc.code == "sec_xbrl_in_app_auth_policy_missing_identity_authority"
        assert exc.http_status == 401


# ---------------------------------------------------------------------------
# (d) Role ceiling: role_enforcing mode blocks insufficient role
# ---------------------------------------------------------------------------

_AUDITOR_ALLOWED_FAMILY = "sec_xbrl_operator_review_workflow_status_read"
_OWNER_ONLY_FAMILY = "sec_xbrl_controlled_value_reveal_submit_write"

_IDENTITY_CANARY = "role-safety-contract@example.invalid"
_GROUPS_CANARY = "role-safety-groups@example.invalid"


def _proxy_headers(*, role_value: str | None = None) -> dict[str, str]:
    h = {
        _IDENTITY_HEADER: _IDENTITY_CANARY,
        _GROUPS_HEADER: _GROUPS_CANARY,
    }
    if role_value is not None:
        h[_ROLES_HEADER] = role_value
    return h


def _configure_proxy(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _GROUPS_HEADER)
    monkeypatch.setattr(settings, "proxy_roles_header", _ROLES_HEADER)
    monkeypatch.setattr(settings, "layer3_owner_role_tokens", "owner")
    monkeypatch.setattr(settings, "layer3_auditor_role_tokens", "auditor")


class TestRoleCeilingFailClosed:
    """Contract: role_enforcing mode must block an auditor-token caller from claiming OWNER_ROLE.

    Mirrors test_sec_xbrl_role_cap.py::TestRoleEnforcingAuditorTokens framed as
    safety-contract assertions.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "layer3_route_authorization_mode", "role_enforcing")
        _configure_proxy(monkeypatch)

    def test_auditor_tokens_owner_claim_raises_role_exceeds_authority(self) -> None:
        """Contract: auditor-token caller claiming OWNER_ROLE is rejected with
        sec_xbrl_in_app_auth_policy_role_claim_exceeds_server_authority (403)."""
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value="auditor"),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        exc = exc_info.value
        assert exc.code == "sec_xbrl_in_app_auth_policy_role_claim_exceeds_server_authority"
        assert exc.http_status == 403

    def test_auditor_tokens_owner_claim_error_does_not_leak_raw_role(self) -> None:
        """Contract: the role-cap error must not echo the raw role header value."""
        import json as _json
        raw_role_canary = "auditor-raw-role-canary-value"

        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value=raw_role_canary),
                route_family=_AUDITOR_ALLOWED_FAMILY,
                requested_role=OWNER_ROLE,
            )

        serialized = _json.dumps({
            "message": exc_info.value.message,
            "details": exc_info.value.details,
        })
        assert raw_role_canary not in serialized

    def test_auditor_tokens_auditor_claim_auditor_allowed_family_passes(self) -> None:
        """Contract: auditor-token caller with AUDITOR_ROLE on an auditor-allowed family is
        admitted — the ceiling only blocks upward escalation, not legitimate auditor access."""
        result = authorize_sec_xbrl_route(
            headers=_proxy_headers(role_value="auditor"),
            route_family=_AUDITOR_ALLOWED_FAMILY,
            requested_role=AUDITOR_ROLE,
        )
        assert result["decision"] == "allow"
        assert result["role"] == AUDITOR_ROLE

    def test_auditor_tokens_owner_only_family_auditor_claim_rejected_by_family_check(self) -> None:
        """Contract: auditor-token caller claiming AUDITOR_ROLE on an owner-only family is
        rejected (by the pre-existing family check, not the cap)."""
        with pytest.raises(SecXbrlInAppAuthPolicyError) as exc_info:
            authorize_sec_xbrl_route(
                headers=_proxy_headers(role_value="auditor"),
                route_family=_OWNER_ONLY_FAMILY,
                requested_role=AUDITOR_ROLE,
            )

        assert exc_info.value.code == "sec_xbrl_in_app_auth_policy_role_route_forbidden"
        assert exc_info.value.http_status == 403
