from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.layer3_sec_xbrl_in_app_auth_policy import PROTECTED_ROUTE_FAMILIES
from app.services.layer3_utils import stable_hash


POSTURE_SCHEMA_ID = "layer3.sec_xbrl_runtime_posture.v1"
POSTURE_MODE = "sec_xbrl_runtime_posture_operator_status_v1"


def build_sec_xbrl_runtime_posture() -> dict[str, Any]:
    flags = _runtime_flags()
    route_families = _protected_route_families()
    activated = _activated_capabilities(flags)
    gated = _gated_capabilities(flags)
    identity_authority = _identity_authority()
    posture_state = (
        "sec_xbrl_controlled_value_reveal_available_with_runtime_gates"
        if flags["controlled_value_reveal_submit_enabled"]
        else "sec_xbrl_controlled_value_reveal_submit_blocked_by_feature_flag"
    )
    posture = {
        "schema_id": POSTURE_SCHEMA_ID,
        "posture_mode": POSTURE_MODE,
        "posture_state": posture_state,
        "runtime_flags": flags,
        "identity_authority": identity_authority,
        "protected_route_families": route_families,
        "activated_capabilities": activated,
        "gated_capabilities": gated,
        "operator_next_actions": _operator_next_actions(flags),
        "negative_boundaries": [
            "no_sec_edgar_live_network_request_performed",
            "no_arelle_invocation_performed",
            "no_database_or_storage_write_performed",
            "no_value_reveal_performed",
            "no_delivery_export_performed",
            "no_default_runtime_activation_performed",
            "no_raw_operator_identity_exposed",
            "no_raw_proxy_header_exposed",
            "no_raw_workspace_identity_exposed",
            "no_raw_value_or_residual_magnitude_exposed",
            "no_local_path_or_url_exposed",
        ],
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "delivery_export_enabled": False,
        "runtime_db_write": False,
        "rendered_ui_legacy_value_reveal_enabled": False,
        "production_readiness_claimed": False,
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_workspace_identity_exposed": False,
        "raw_value_exposed": False,
        "residual_magnitude_exposed": False,
        "local_path_or_url_exposed": False,
    }
    return {
        **posture,
        "posture_basis_hash": stable_hash(
            {
                "schema_id": POSTURE_SCHEMA_ID,
                "posture_mode": POSTURE_MODE,
                "runtime_flags": flags,
                "identity_authority": identity_authority,
                "protected_route_families": route_families,
                "activated_capabilities": activated,
                "gated_capabilities": gated,
            }
        ),
    }


def _runtime_flags() -> dict[str, bool]:
    return {
        "live_sec_edgar_network_enabled": bool(settings.layer3_sec_edgar_live_network_enabled),
        "arelle_fact_authority_cutover_enabled": bool(
            settings.layer3_sec_edgar_arelle_fact_authority_cutover_enabled
        ),
        "arelle_fact_authority_nonlocal_authorized": bool(
            settings.layer3_sec_edgar_arelle_fact_authority_nonlocal_authorized
        ),
        "arelle_internal_value_store_enabled": bool(
            settings.layer3_sec_edgar_arelle_internal_value_store_enabled
        ),
        "arelle_corpus_validation_enabled": bool(
            settings.layer3_sec_edgar_arelle_corpus_validation_enabled
        ),
        "arelle_governed_sibling_value_reveal_enabled": bool(
            settings.layer3_sec_edgar_arelle_value_reveal_enabled
        ),
        "controlled_value_reveal_submit_enabled": bool(
            settings.layer3_sec_xbrl_controlled_value_reveal_submit_enabled
        ),
    }


def _identity_authority() -> dict[str, Any]:
    auth_owner = str(settings.auth_owner or "none")
    trusted_proxy = bool(settings.trusted_proxy_mode)
    if auth_owner == "proxy":
        state = "proxy_identity_authority_admitted" if trusted_proxy else "proxy_identity_authority_blocked"
    else:
        state = "local_single_operator_identity_authority"
    return {
        "auth_owner": auth_owner,
        "trusted_proxy_mode_enabled": trusted_proxy,
        "identity_authority_state": state,
        "requires_server_derived_identity": True,
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_workspace_identity_exposed": False,
    }


def _protected_route_families() -> list[dict[str, Any]]:
    return [
        {
            "route_family": name,
            "allowed_roles": sorted(list(meta["allowed_roles"])),
            "mutating": bool(meta["mutating"]),
            "may_expose_revealed_values": bool(meta["may_expose_revealed_values"]),
        }
        for name, meta in sorted(PROTECTED_ROUTE_FAMILIES.items())
    ]


def _activated_capabilities(flags: dict[str, bool]) -> list[dict[str, Any]]:
    activated: list[dict[str, Any]] = []
    if flags["arelle_fact_authority_cutover_enabled"]:
        activated.append(
            {
                "capability": "arelle_fact_authority_cutover",
                "runtime_state": (
                    "local_cutover_enabled_nonlocal_authorized"
                    if flags["arelle_fact_authority_nonlocal_authorized"]
                    else "local_cutover_enabled_nonlocal_requires_explicit_authorization"
                ),
                "route_families": [
                    "sec_xbrl_operator_review_workflow_status_read",
                    "sec_xbrl_operator_review_decision_status_read",
                ],
            }
        )
    if flags["controlled_value_reveal_submit_enabled"]:
        activated.append(
            {
                "capability": "controlled_value_reveal_submit",
                "runtime_state": "server_authority_receipt_submit_available",
                "route_families": [
                    "sec_xbrl_value_reveal_authority_prepare_write",
                    "sec_xbrl_controlled_value_reveal_submit_write",
                    "sec_xbrl_controlled_value_reveal_submit_status_read",
                ],
            }
        )
    return activated


def _gated_capabilities(flags: dict[str, bool]) -> list[dict[str, Any]]:
    gated: list[dict[str, Any]] = []
    if not flags["live_sec_edgar_network_enabled"]:
        gated.append(
            {
                "capability": "live_sec_edgar_network_source_acquisition",
                "runtime_state": "blocked_by_live_network_feature_flag",
                "required_flag": "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
            }
        )
    if not flags["arelle_governed_sibling_value_reveal_enabled"]:
        gated.append(
            {
                "capability": "legacy_arelle_governed_sibling_value_reveal",
                "runtime_state": "blocked_by_value_reveal_feature_flag_and_replaced_in_rendered_ui",
                "required_flag": "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
            }
        )
    if not flags["arelle_internal_value_store_enabled"]:
        gated.append(
            {
                "capability": "arelle_internal_value_store",
                "runtime_state": "blocked_by_internal_value_store_feature_flag",
                "required_flag": "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
            }
        )
    if not flags["arelle_corpus_validation_enabled"]:
        gated.append(
            {
                "capability": "arelle_corpus_validation_runtime",
                "runtime_state": "blocked_by_corpus_validation_feature_flag",
                "required_flag": "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
            }
        )
    if (
        flags["arelle_fact_authority_cutover_enabled"]
        and not flags["arelle_fact_authority_nonlocal_authorized"]
    ):
        gated.append(
            {
                "capability": "nonlocal_arelle_fact_authority_cutover",
                "runtime_state": "blocked_until_nonlocal_authorization_flag_is_explicit",
                "required_flag": "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED",
            }
        )
    if not flags["controlled_value_reveal_submit_enabled"]:
        gated.append(
            {
                "capability": "controlled_value_reveal_submit",
                "runtime_state": "blocked_by_controlled_submit_feature_flag",
                "required_flag": "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
            }
        )
    gated.append(
        {
            "capability": "production_readiness_claim",
            "runtime_state": "blocked_until_live_sec_arelle_ui_export_and_auth_paths_are_all_verified",
            "required_evidence": [
                "live_sec_source_acquisition_e2e",
                "arelle_invocation_e2e",
                "multi_filing_gate_enforcement",
                "operator_auth_beyond_selected_mode",
                "delivery_export_package_status",
            ],
        }
    )
    return gated


def _operator_next_actions(flags: dict[str, bool]) -> list[str]:
    actions = [
        "inspect_sec_xbrl_identity_projection",
        "inspect_sec_xbrl_operator_review_workflow_status",
    ]
    if flags["controlled_value_reveal_submit_enabled"]:
        actions.extend(
            [
                "prepare_value_reveal_authority_receipt",
                "submit_controlled_value_reveal_from_authority_receipt",
                "inspect_controlled_value_reveal_submit_status",
            ]
        )
    else:
        actions.append("enable_controlled_value_reveal_submit_before_browser_value_reveal")
    actions.extend(
        [
            "keep_legacy_sibling_value_reveal_rendered_ui_disabled",
            "activate_live_sec_or_arelle_paths_only_after_explicit_runtime_authorization",
        ]
    )
    return actions
