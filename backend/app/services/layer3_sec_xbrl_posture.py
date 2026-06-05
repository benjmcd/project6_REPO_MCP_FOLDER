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
    activation_surfaces = _activation_surfaces(flags, identity_authority)
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
        "activation_surfaces": activation_surfaces,
        "activation_surface_hash": stable_hash(
            {
                "schema_id": POSTURE_SCHEMA_ID,
                "surface_projection": "sec_xbrl_activation_surface_operator_map_v1",
                "activation_surfaces": activation_surfaces,
            }
        ),
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
                "activation_surfaces": activation_surfaces,
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


def _activation_surfaces(
    flags: dict[str, bool],
    identity_authority: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _controlled_value_reveal_surface(flags),
        _live_sec_source_acquisition_surface(flags),
        _arelle_invocation_surface(flags),
        _multi_filing_gate_surface(),
        _delivery_export_surface(),
        _operator_auth_surface(identity_authority),
    ]


def _base_activation_surface(surface_id: str) -> dict[str, Any]:
    return {
        "surface_id": surface_id,
        "current_posture_performs_side_effect": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "delivery_export_performed": False,
        "runtime_db_write": False,
        "frontend_durable_authority": False,
        "raw_authority_exposed": False,
        "production_readiness_claimed": False,
    }


def _controlled_value_reveal_surface(flags: dict[str, bool]) -> dict[str, Any]:
    enabled = flags["controlled_value_reveal_submit_enabled"]
    return {
        **_base_activation_surface("controlled_value_reveal_submit"),
        "surface_state": (
            "active_explicit_operator_submit"
            if enabled
            else "gated_by_controlled_submit_feature_flag"
        ),
        "runtime_enabled": enabled,
        "operator_surface_rendered": True,
        "rendered_panel_id": "sec-xbrl-controlled-value-reveal-panel",
        "route_families": [
            "sec_xbrl_value_reveal_authority_prepare_write",
            "sec_xbrl_controlled_value_reveal_submit_write",
            "sec_xbrl_controlled_value_reveal_submit_status_read",
        ],
        "api_routes": [
            "POST /api/v1/layer3/sec-xbrl/value-reveal/authority/prepare",
            "POST /api/v1/layer3/sec-xbrl/controlled-value-reveal/submit",
            "POST /api/v1/layer3/sec-xbrl/controlled-value-reveal/status",
        ],
        "operator_confirmation_required": True,
        "required_flags": (
            []
            if enabled
            else ["LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED"]
        ),
        "next_operator_action": (
            "submit_controlled_value_reveal_from_authority_receipt"
            if enabled
            else "enable_controlled_value_reveal_submit_before_browser_value_reveal"
        ),
    }


def _live_sec_source_acquisition_surface(flags: dict[str, bool]) -> dict[str, Any]:
    enabled = flags["live_sec_edgar_network_enabled"]
    return {
        **_base_activation_surface("live_sec_edgar_network_source_acquisition"),
        "surface_state": (
            "operator_surface_available_when_live_network_authorized"
            if enabled
            else "gated_by_live_network_feature_flag"
        ),
        "runtime_enabled": enabled,
        "operator_surface_rendered": True,
        "rendered_panel_id": "sec-edgar-live-source-artifact-acquisition-panel",
        "route_families": ["sec_edgar_text_table_live_source_artifact_acquisition"],
        "api_routes": [
            "POST /api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire",
            "GET /api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/status/{receipt_id}",
        ],
        "operator_confirmation_required": True,
        "server_derives_external_sec_url": True,
        "browser_supplied_url_allowed": False,
        "required_flags": ([] if enabled else ["LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED"]),
        "required_evidence": ["live_sec_source_artifact_e2e"],
        "next_operator_action": (
            "use_sec_edgar_live_source_artifact_acquisition_panel"
            if enabled
            else "authorize_live_sec_network_before_source_acquisition"
        ),
    }


def _arelle_invocation_surface(flags: dict[str, bool]) -> dict[str, Any]:
    enabled = (
        flags["arelle_fact_authority_cutover_enabled"]
        and flags["arelle_fact_authority_nonlocal_authorized"]
        and flags["arelle_internal_value_store_enabled"]
        and flags["arelle_corpus_validation_enabled"]
        and flags["arelle_governed_sibling_value_reveal_enabled"]
    )
    required_flags = [
        flag
        for flag, admitted in (
            (
                "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED",
                flags["arelle_fact_authority_cutover_enabled"],
            ),
            (
                "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED",
                flags["arelle_fact_authority_nonlocal_authorized"],
            ),
            (
                "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
                flags["arelle_internal_value_store_enabled"],
            ),
            (
                "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
                flags["arelle_corpus_validation_enabled"],
            ),
            (
                "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
                flags["arelle_governed_sibling_value_reveal_enabled"],
            ),
        )
        if not admitted
    ]
    return {
        **_base_activation_surface("arelle_invocation_and_governed_sibling_value_reveal"),
        "surface_state": (
            "gated_until_explicit_arelle_invocation_proof"
            if enabled
            else "gated_by_arelle_runtime_flags"
        ),
        "runtime_enabled": enabled,
        "operator_surface_rendered": False,
        "rendered_panel_id": None,
        "route_families": [
            "sec_xbrl_operator_review_workflow_status_read",
            "sec_xbrl_operator_review_decision_status_read",
        ],
        "api_routes": [],
        "operator_confirmation_required": True,
        "required_flags": required_flags,
        "required_evidence": ["arelle_invocation_e2e", "governed_sibling_value_reveal_review"],
        "next_operator_action": "create_bounded_arelle_invocation_activation_freeze",
    }


def _multi_filing_gate_surface() -> dict[str, Any]:
    return {
        **_base_activation_surface("multi_filing_evidence_authority_gate"),
        "surface_state": "gated_until_runtime_enforcement_freeze",
        "runtime_enabled": False,
        "operator_surface_rendered": False,
        "rendered_panel_id": None,
        "route_families": [],
        "api_routes": [],
        "operator_confirmation_required": False,
        "required_flags": [],
        "required_evidence": ["multi_filing_gate_enforcement"],
        "next_operator_action": "create_multi_filing_gate_runtime_enforcement_freeze",
    }


def _delivery_export_surface() -> dict[str, Any]:
    return {
        **_base_activation_surface("delivery_export_package_status"),
        "surface_state": "gated_until_sec_xbrl_package_delivery_status_proof",
        "runtime_enabled": False,
        "operator_surface_rendered": False,
        "rendered_panel_id": None,
        "route_families": [],
        "api_routes": [],
        "operator_confirmation_required": False,
        "required_flags": [],
        "required_evidence": ["delivery_export_package_status"],
        "next_operator_action": "create_sec_xbrl_delivery_export_status_freeze",
    }


def _operator_auth_surface(identity_authority: dict[str, Any]) -> dict[str, Any]:
    identity_state = str(identity_authority.get("identity_authority_state") or "unknown")
    return {
        **_base_activation_surface("nonlocal_operator_auth_hardening"),
        "surface_state": identity_state,
        "runtime_enabled": identity_state == "proxy_identity_authority_admitted",
        "operator_surface_rendered": True,
        "rendered_panel_id": "sec-xbrl-runtime-posture-panel",
        "route_families": [
            "sec_xbrl_operator_review_workflow_status_read",
            "sec_xbrl_controlled_value_reveal_submit_write",
        ],
        "api_routes": ["GET /api/v1/layer3/sec-xbrl/runtime/posture"],
        "operator_confirmation_required": False,
        "required_flags": (
            []
            if identity_state == "proxy_identity_authority_admitted"
            else ["AUTH_OWNER=proxy", "TRUSTED_PROXY_MODE=true"]
        ),
        "required_evidence": ["operator_auth_beyond_selected_mode"],
        "next_operator_action": "verify_nonlocal_operator_auth_before_production_readiness_claim",
    }


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
