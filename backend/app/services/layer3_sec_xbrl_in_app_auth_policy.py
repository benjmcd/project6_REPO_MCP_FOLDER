from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.config import settings
from app.services.layer3_utils import stable_hash


POLICY_SCHEMA_ID = "layer3.sec_xbrl.repo_owned_in_app_operator_auth_policy.v1"
SELECTED_AUTH_MODE = "sec_xbrl_repo_owned_in_app_operator_auth_boundary_v1"
LOCAL_ACTOR_REF = "sec-xbrl-local-single-operator-dev-profile"
LOCAL_WORKSPACE_REF = "sec-xbrl-local-single-workspace-dev-profile"
OWNER_ROLE = "owner"
AUDITOR_ROLE = "auditor"

PROTECTED_ROUTE_FAMILIES: dict[str, dict[str, Any]] = {
    "sec_xbrl_operator_review_workflow_status_read": {
        "allowed_roles": {OWNER_ROLE, AUDITOR_ROLE},
        "mutating": False,
        "may_expose_revealed_values": False,
    },
    "sec_xbrl_operator_review_decision_submit_write": {
        "allowed_roles": {OWNER_ROLE},
        "mutating": True,
        "may_expose_revealed_values": False,
    },
    "sec_xbrl_operator_review_decision_status_read": {
        "allowed_roles": {OWNER_ROLE, AUDITOR_ROLE},
        "mutating": False,
        "may_expose_revealed_values": False,
    },
    "sec_xbrl_value_reveal_authority_prepare_write": {
        "allowed_roles": {OWNER_ROLE},
        "mutating": True,
        "may_expose_revealed_values": False,
    },
    "sec_xbrl_controlled_value_reveal_submit_write": {
        "allowed_roles": {OWNER_ROLE},
        "mutating": True,
        "may_expose_revealed_values": True,
    },
    "sec_xbrl_controlled_value_reveal_submit_status_read": {
        "allowed_roles": {OWNER_ROLE},
        "mutating": False,
        "may_expose_revealed_values": True,
    },
}

PROXY_IDENTITY_READONLY_PROJECTION_MODE = "proxy_identity_read_only_projection"
PROXY_IDENTITY_PROJECTION_CONTRACT_ID = "sec_xbrl_proxy_identity_read_only_live_projection_contract"
PROXY_IDENTITY_PROJECTION_SCHEMA_ID = "layer3.sec_xbrl_proxy_identity_projection.v1"

FORBIDDEN_REQUEST_FIELDS = {
    "accession",
    "amount",
    "arelle_execution_override",
    "auth_policy_override",
    "auth_security_directive",
    "browser_identity",
    "cik",
    "company_name",
    "default_on_override",
    "email",
    "export_delivery_override",
    "local_path",
    "local_storage_identity",
    "operator_email",
    "operator_role_override",
    "permission_override",
    "provider_secret",
    "proxy_email_header",
    "proxy_groups_header",
    "proxy_identity_header",
    "raw_operator_identity",
    "raw_proxy_header",
    "raw_receipt_path",
    "raw_storage_root",
    "raw_url",
    "raw_value",
    "raw_value_store_payload",
    "raw_workspace_id",
    "sec_url",
    "security_context",
    "source_acquisition_override",
    "token",
    "value",
    "value_store_override",
}


class SecXbrlInAppAuthPolicyError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        http_status: int = 403,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.http_status = http_status


def authorize_sec_xbrl_route(
    *,
    headers: Mapping[str, str],
    route_family: str,
    requested_role: str,
    request_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    route = _route_family(route_family)
    blocked = sorted(
        str(key)
        for key, value in dict(request_fields or {}).items()
        if str(key).lower() in FORBIDDEN_REQUEST_FIELDS and value is not None
    )
    if blocked:
        raise SecXbrlInAppAuthPolicyError(
            "sec_xbrl_in_app_auth_policy_forbidden_request_fields",
            "SEC XBRL in-app auth rejects caller-supplied auth/security, raw identity, source, value, default, or export fields.",
            details={"blocked_fields": blocked},
            http_status=400,
        )

    role = _role(requested_role)
    if role not in PROTECTED_ROUTE_FAMILIES[route]["allowed_roles"]:
        raise SecXbrlInAppAuthPolicyError(
            "sec_xbrl_in_app_auth_policy_role_route_forbidden",
            "SEC XBRL in-app auth does not admit the requested role for this route family.",
            details={"role": role, "route_family": route},
            http_status=403,
        )
    actor_ref_hash, workspace_ref_hash, auth_owner_mode = _server_derived_principal(headers)
    policy_hash = _policy_hash(
        actor_ref_hash=actor_ref_hash,
        workspace_ref_hash=workspace_ref_hash,
        route_family=route,
        role=role,
    )
    compatible_policy_hashes = _compatible_policy_hashes(
        actor_ref_hash=actor_ref_hash,
        workspace_ref_hash=workspace_ref_hash,
        route_family=route,
        role=role,
    )
    return {
        "decision": "allow",
        "policy_status": "admitted",
        "policy_schema_id": POLICY_SCHEMA_ID,
        "selected_auth_mode": SELECTED_AUTH_MODE,
        "auth_owner_mode": auth_owner_mode,
        "route_family": route,
        "role": role,
        "actor_ref_hash": actor_ref_hash,
        "workspace_ref_hash": workspace_ref_hash,
        "policy_hash": policy_hash,
        "compatible_policy_hashes": compatible_policy_hashes,
        "requires_owner_binding": True,
        "mutating_route": bool(PROTECTED_ROUTE_FAMILIES[route]["mutating"]),
        "may_expose_revealed_values": bool(
            PROTECTED_ROUTE_FAMILIES[route]["may_expose_revealed_values"]
        ),
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_workspace_identity_exposed": False,
        "raw_value_exposed": False,
        "residual_magnitude_exposed": False,
    }


def binding_client_request_id(*, client_request_id: str, route_family: str) -> str:
    digest = stable_hash(
        {
            "schema_id": POLICY_SCHEMA_ID,
            "selected_auth_mode": SELECTED_AUTH_MODE,
            "client_request_id": str(client_request_id or "").strip(),
            "route_family": _route_family(route_family),
            "binding_receipt": True,
        }
    )
    return f"sec-xbrl-auth-binding-{digest[:24]}"


def _route_family(value: str) -> str:
    route = str(value or "").strip()
    if route not in PROTECTED_ROUTE_FAMILIES:
        raise SecXbrlInAppAuthPolicyError(
            "sec_xbrl_in_app_auth_policy_route_family_not_admitted",
            "SEC XBRL in-app auth admits only known protected route families.",
            details={"route_family": route},
            http_status=400,
        )
    return route


def _role(value: str) -> str:
    role = str(value or "").strip().lower()
    if role in {"", OWNER_ROLE}:
        return OWNER_ROLE
    if role == AUDITOR_ROLE:
        return AUDITOR_ROLE
    raise SecXbrlInAppAuthPolicyError(
        "sec_xbrl_in_app_auth_policy_role_not_admitted",
        "SEC XBRL in-app auth admits only owner and auditor roles.",
        details={"role": role},
        http_status=403,
    )


def _server_derived_principal(headers: Mapping[str, str]) -> tuple[str, str, str]:
    if settings.auth_owner == "none":
        return (
            stable_hash({"auth_owner": "none", "actor_ref": LOCAL_ACTOR_REF}),
            stable_hash({"auth_owner": "none", "workspace_ref": LOCAL_WORKSPACE_REF}),
            "AUTH_OWNER_none_single_operator_dev_profile",
        )
    if settings.auth_owner != "proxy":
        raise SecXbrlInAppAuthPolicyError(
            "sec_xbrl_in_app_auth_policy_auth_owner_not_admitted",
            "SEC XBRL in-app auth admits only AUTH_OWNER=none or AUTH_OWNER=proxy.",
            http_status=409,
        )
    if not settings.trusted_proxy_mode:
        raise SecXbrlInAppAuthPolicyError(
            "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity",
            "AUTH_OWNER=proxy requires TRUSTED_PROXY_MODE=true before proxy identity can be server authority.",
            http_status=409,
        )
    normalized_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    actor_ref = _required_header(
        normalized_headers,
        settings.proxy_identity_header,
        "identity",
    )
    workspace_ref = _required_header(
        normalized_headers,
        settings.proxy_groups_header,
        "workspace",
    )
    return (
        stable_hash({"auth_owner": "proxy", "actor_ref": actor_ref}),
        stable_hash({"auth_owner": "proxy", "workspace_ref": workspace_ref}),
        "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    )


def _required_header(
    headers: Mapping[str, str],
    configured_name: str,
    authority_name: str,
) -> str:
    header_name = str(configured_name or "").strip().lower()
    value = str(headers.get(header_name) or "").strip()
    if not value:
        raise SecXbrlInAppAuthPolicyError(
            f"sec_xbrl_in_app_auth_policy_missing_{authority_name}_authority",
            "SEC XBRL in-app auth requires server-derived identity and workspace authority.",
            http_status=401,
        )
    return value


def _policy_hash(*, actor_ref_hash: str, workspace_ref_hash: str, route_family: str, role: str) -> str:
    return stable_hash(
        {
            "policy_schema_id": POLICY_SCHEMA_ID,
            "selected_auth_mode": SELECTED_AUTH_MODE,
            "actor_ref_hash": actor_ref_hash,
            "workspace_ref_hash": workspace_ref_hash,
            "route_family": route_family,
            "role": role,
        }
    )


def _legacy_policy_hash(*, actor_ref_hash: str, workspace_ref_hash: str) -> str:
    return stable_hash(
        {
            "policy_schema_id": POLICY_SCHEMA_ID,
            "selected_auth_mode": SELECTED_AUTH_MODE,
            "actor_ref_hash": actor_ref_hash,
            "workspace_ref_hash": workspace_ref_hash,
        }
    )


def _compatible_policy_hashes(
    *,
    actor_ref_hash: str,
    workspace_ref_hash: str,
    route_family: str,
    role: str,
) -> list[str]:
    return list(
        dict.fromkeys(
            [
                _policy_hash(
                    actor_ref_hash=actor_ref_hash,
                    workspace_ref_hash=workspace_ref_hash,
                    route_family=route_family,
                    role=role,
                ),
                _legacy_policy_hash(
                    actor_ref_hash=actor_ref_hash,
                    workspace_ref_hash=workspace_ref_hash,
                ),
            ]
        )
    )


def build_proxy_identity_readonly_projection(*, headers: Mapping[str, str]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "contract_id": PROXY_IDENTITY_PROJECTION_CONTRACT_ID,
        "schema_id": PROXY_IDENTITY_PROJECTION_SCHEMA_ID,
        "selected_auth_mode": PROXY_IDENTITY_READONLY_PROJECTION_MODE,
        "policy_schema_id": POLICY_SCHEMA_ID,
        "default_role": OWNER_ROLE,
        "server_authority_contract": "server_derived_proxy_or_local_identity_hash_read_only_projection",
        "status_projection": ["State.sessionSummary.sec_xbrl_identity_projection"],
        "protected_route_families": [
            {
                "route_family": name,
                "allowed_roles": sorted(list(meta["allowed_roles"])),
                "mutating": bool(meta["mutating"]),
                "may_expose_revealed_values": bool(meta["may_expose_revealed_values"]),
            }
            for name, meta in sorted(PROTECTED_ROUTE_FAMILIES.items())
        ],
        "negative_boundaries": [
            "route_level_enforcement_escalation",
            "operator_permission_matrix_change",
            "owner_binding_persistence_change",
            "value_reveal_activation",
            "controlled_submit_activation",
            "default_on_runtime_change",
            "raw_operator_identity_exposure",
            "raw_proxy_header_exposure",
            "raw_workspace_identity_exposure",
            "raw_value_or_residual_magnitude_exposure",
            "local_path_or_url_exposure",
        ],
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_workspace_identity_exposed": False,
        "raw_value_exposed": False,
        "residual_magnitude_exposed": False,
    }
    try:
        actor_ref_hash, workspace_ref_hash, auth_owner_mode = _server_derived_principal(headers)
        return {
            **base,
            "projection_status": "admitted",
            "auth_owner_mode": auth_owner_mode,
            "actor_ref_hash": actor_ref_hash,
            "workspace_ref_hash": workspace_ref_hash,
        }
    except SecXbrlInAppAuthPolicyError as exc:
        _status_map: dict[str, str] = {
            "sec_xbrl_in_app_auth_policy_untrusted_proxy_identity": "blocked_untrusted_proxy_identity",
            "sec_xbrl_in_app_auth_policy_missing_identity_authority": "blocked_missing_identity_authority",
            "sec_xbrl_in_app_auth_policy_missing_workspace_authority": "blocked_missing_identity_authority",
            "sec_xbrl_in_app_auth_policy_auth_owner_not_admitted": "blocked_auth_owner_not_admitted",
        }
        projection_status = _status_map.get(exc.code, "blocked_no_runtime_identity_authority")
        auth_owner_mode = (
            "AUTH_OWNER_proxy_pending_trusted_or_identity_authority"
            if settings.auth_owner == "proxy"
            else "AUTH_OWNER_none_single_operator_dev_profile"
        )
        return {
            **base,
            "projection_status": projection_status,
            "auth_owner_mode": auth_owner_mode,
            "actor_ref_hash": None,
            "workspace_ref_hash": None,
        }
