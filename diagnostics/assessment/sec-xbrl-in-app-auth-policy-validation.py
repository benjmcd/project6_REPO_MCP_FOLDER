from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = Path(__file__).resolve().parent
if str(ASSESSMENT) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT))

from sec_xbrl_diagnostic_framework import criterion as _criterion  # noqa: E402
from sec_xbrl_runtime_posture import resolve_layer3_api_source  # noqa: E402

DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json")
TARGET = "sec_xbrl_nonlocal_in_app_auth_policy_validation_v1"
SCHEMA_ID = "diagnostics.sec_xbrl_nonlocal_in_app_auth_policy_validation.v1"
POLICY_SCHEMA_ID = "layer3.sec_xbrl.repo_owned_in_app_operator_auth_policy.v1"
SELECTED_AUTH_MODE = "sec_xbrl_repo_owned_in_app_operator_auth_boundary_v1"
NEXT_SLICE = "sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1"
DESIGN_DOC = "next_milestone_plans/Layer3_planning_docs/1321-in-app-auth.md"
API_FILE = "backend/app/api/layer3.py"
CONFIG_FILE = "backend/app/core/config.py"
CANDIDATE_B_POLICY_FILE = "backend/app/services/layer3_candidate_b_operator_workflow_access_policy.py"

OWNER_ROLE = "owner"
AUDITOR_ROLE = "auditor"
ADMITTED_CONTEXT_AUTHORITY = "repo_owned_in_app_auth_verifier"

PROTECTED_ROUTE_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "route_family": "sec_xbrl_operator_review_workflow_status_read",
        "method": "POST",
        "route": "/api/v1/layer3/sec-xbrl/operator-review/workflow/status",
        "allowed_roles": (OWNER_ROLE, AUDITOR_ROLE),
        "mutating": False,
        "requires_owner_binding": True,
        "may_expose_revealed_values": False,
    },
    {
        "route_family": "sec_xbrl_operator_review_decision_submit_write",
        "method": "POST",
        "route": "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit",
        "allowed_roles": (OWNER_ROLE,),
        "mutating": True,
        "requires_owner_binding": True,
        "may_expose_revealed_values": False,
    },
    {
        "route_family": "sec_xbrl_operator_review_decision_status_read",
        "method": "POST",
        "route": "/api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status",
        "allowed_roles": (OWNER_ROLE, AUDITOR_ROLE),
        "mutating": False,
        "requires_owner_binding": True,
        "may_expose_revealed_values": False,
    },
    {
        "route_family": "sec_xbrl_value_reveal_authority_prepare_write",
        "method": "POST",
        "route": "/api/v1/layer3/sec-xbrl/value-reveal/authority/prepare",
        "allowed_roles": (OWNER_ROLE,),
        "mutating": True,
        "requires_owner_binding": True,
        "may_expose_revealed_values": False,
    },
    {
        "route_family": "sec_xbrl_controlled_value_reveal_submit_write",
        "method": "POST",
        "route": "/api/v1/layer3/sec-xbrl/value-reveal/submit",
        "allowed_roles": (OWNER_ROLE,),
        "mutating": True,
        "requires_owner_binding": True,
        "may_expose_revealed_values": True,
    },
    {
        "route_family": "sec_xbrl_controlled_value_reveal_submit_status_read",
        "method": "GET",
        "route": (
            "/api/v1/layer3/sec-xbrl/value-reveal/submit/status/"
            "{sec_xbrl_controlled_value_reveal_submit_receipt_id}"
        ),
        "allowed_roles": (OWNER_ROLE,),
        "mutating": False,
        "requires_owner_binding": True,
        "may_expose_revealed_values": True,
    },
)

FORBIDDEN_REQUEST_FIELDS: tuple[str, ...] = tuple(
    sorted(
        {
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
            "raw_tenant_id",
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
    )
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL in-app auth policy diagnostic. This script reads "
            "repo source and emits a redacted policy report; it does not install runtime "
            "auth, mutate routes, seed data, touch persistence, reveal values, run Arelle, "
            "or perform network/source acquisition."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    report = build_report()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    root: Path = ROOT,
    route_families: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    families = list(PROTECTED_ROUTE_FAMILIES if route_families is None else route_families)
    design_doc = _read(root / DESIGN_DOC)
    api_source = resolve_layer3_api_source(root)
    config_source = _read(root / CONFIG_FILE)
    candidate_b_policy = _read(root / CANDIDATE_B_POLICY_FILE)
    simulations = _simulation_matrix(families)

    criteria = [
        _criterion(
            "protected_route_family_map_nonempty",
            bool(families),
            {"route_family_count": len(families)},
            "sec_xbrl_in_app_auth_policy_route_family_map_empty",
        ),
        _criterion(
            "protected_routes_present_in_current_api",
            bool(families) and _routes_present(families, api_source),
            {
                "api_file": API_FILE,
                "route_family_count": len(families),
                "routes": [_route_summary(family) for family in families],
            },
            "sec_xbrl_in_app_auth_policy_route_surface_not_current",
        ),
        _criterion(
            "design_traceability_current",
            _design_traceability_holds(families, design_doc),
            {
                "design_doc": DESIGN_DOC,
                "selected_auth_mode": SELECTED_AUTH_MODE,
                "target": TARGET,
                "route_family_count": len(families),
            },
            "sec_xbrl_in_app_auth_policy_design_trace_missing",
        ),
        _criterion(
            "repo_nonlocal_proxy_guardrails_still_configured",
            _nonlocal_proxy_guardrails_hold(config_source),
            {
                "config_file": CONFIG_FILE,
                "requires_proxy_owner_for_nonlocal": True,
                "requires_trusted_proxy_for_nonlocal": True,
                "requires_explicit_https_origins": True,
                "requires_direct_storage_disabled": True,
            },
            "sec_xbrl_in_app_auth_policy_nonlocal_guardrails_missing",
        ),
        _criterion(
            "candidate_b_hash_only_policy_precedent_present",
            _candidate_b_precedent_present(candidate_b_policy),
            {
                "source_file": CANDIDATE_B_POLICY_FILE,
                "precedent": "hash-only request-context policy decision with forbidden request fields",
            },
            "sec_xbrl_in_app_auth_policy_precedent_missing",
        ),
        _criterion(
            "negative_policy_cases_fail_closed",
            _negative_cases_fail_closed(simulations),
            {
                "case_count": len(simulations),
                "denied_negative_cases": _denied_case_codes(simulations),
            },
            "sec_xbrl_in_app_auth_policy_negative_cases_not_closed",
        ),
        _criterion(
            "role_allowlist_constrains_mutating_and_value_routes",
            _role_allowlist_holds(families, simulations),
            {
                "owner_allowed_route_count": _allowed_count(simulations, OWNER_ROLE),
                "auditor_allowed_route_count": _allowed_count(simulations, AUDITOR_ROLE),
                "auditor_mutating_route_access": False,
                "auditor_revealed_value_route_access": False,
            },
            "sec_xbrl_in_app_auth_policy_role_allowlist_not_constrained",
        ),
        _criterion(
            "forbidden_request_fields_cover_auth_security_raw_and_override_inputs",
            _forbidden_fields_cover_required_classes(),
            {
                "forbidden_field_count": len(FORBIDDEN_REQUEST_FIELDS),
                "blocked_field_classes": [
                    "auth_security",
                    "raw_identity",
                    "proxy_header",
                    "local_path_or_url",
                    "secret_token",
                    "value_store_or_raw_value",
                    "default_source_arelle_export_override",
                ],
            },
            "sec_xbrl_in_app_auth_policy_forbidden_field_coverage_incomplete",
        ),
        _criterion(
            "redacted_policy_output_contract",
            _redacted_output_contract_holds(simulations),
            {
                "raw_operator_identity_exposed": False,
                "raw_proxy_header_exposed": False,
                "raw_workspace_identity_exposed": False,
                "raw_local_path_exposed": False,
                "raw_url_exposed": False,
                "raw_value_exposed": False,
                "residual_magnitude_exposed": False,
            },
            "sec_xbrl_in_app_auth_policy_redaction_contract_failed",
        ),
        _criterion(
            "standing_non_admissions_preserved",
            True,
            {
                "runtime_auth_dependency_installed_by_diagnostic": False,
                "api_route_behavior_changed_by_diagnostic": False,
                "schema_or_persistence_changed_by_diagnostic": False,
                "owner_binding_strategy_selected_for_runtime": False,
                "value_reveal_default_enabled_by_diagnostic": False,
                "source_acquisition_performed_by_diagnostic": False,
                "arelle_subprocess_invoked_by_diagnostic": False,
                "export_or_delivery_enabled_by_diagnostic": False,
                "production_readiness_claimed": False,
            },
            "sec_xbrl_in_app_auth_policy_non_admission_regressed",
        ),
    ]
    blocking_reasons = [
        criterion["blocked_reason"]
        for criterion in criteria
        if criterion["state"] == "blocked" and criterion["blocked_reason"]
    ]

    return {
        "schema_id": SCHEMA_ID,
        "target": TARGET,
        "decision": (
            "sec_xbrl_in_app_auth_policy_validation_passed"
            if not blocking_reasons
            else "sec_xbrl_in_app_auth_policy_validation_blocked"
        ),
        "headline": (
            "SEC XBRL in-app auth policy is validated as a redacted, validate-only pre-runtime boundary."
            if not blocking_reasons
            else "SEC XBRL in-app auth policy validation is blocked; do not implement runtime auth on this basis."
        ),
        "criteria": criteria,
        "blocking_reasons": blocking_reasons,
        "selected_auth_mode": SELECTED_AUTH_MODE,
        "policy_schema_id": POLICY_SCHEMA_ID,
        "route_family_map": [_route_summary(family) for family in families],
        "forbidden_request_fields": list(FORBIDDEN_REQUEST_FIELDS),
        "simulation_summary": _simulation_summary(simulations),
        "non_goals_preserved": {
            "runtime_auth_dependency_installed_by_diagnostic": False,
            "api_route_behavior_changed_by_diagnostic": False,
            "config_default_changed_by_diagnostic": False,
            "schema_models_changed_by_diagnostic": False,
            "migration_changed_by_diagnostic": False,
            "durable_persistence_changed_by_diagnostic": False,
            "owner_binding_strategy_selected_for_runtime": False,
            "value_reveal_default_enabled_by_diagnostic": False,
            "controlled_value_reveal_submit_default_enabled_by_diagnostic": False,
            "raw_internal_value_store_default_enabled_by_diagnostic": False,
            "source_acquisition_performed_by_diagnostic": False,
            "arelle_subprocess_invoked_by_diagnostic": False,
            "live_sec_network_run_performed_by_diagnostic": False,
            "export_or_delivery_enabled_by_diagnostic": False,
            "provider_or_connector_dispatch_enabled_by_diagnostic": False,
            "production_readiness_claimed": False,
            "raw_runtime_artifacts_added_by_diagnostic": False,
            "redaction_posture_changed_by_diagnostic": False,
            "final_financial_statement_semantics_claimed": False,
            "cross_company_comparability_claimed": False,
        },
        "source_documents": {
            "in_app_auth_design": DESIGN_DOC,
            "api_source": API_FILE,
            "config_source": CONFIG_FILE,
            "candidate_b_policy_precedent": CANDIDATE_B_POLICY_FILE,
        },
        "next_slice": NEXT_SLICE,
    }


def evaluate_policy(
    *,
    route_family: str,
    requested_role: str,
    auth_context: Mapping[str, Any] | None,
    request_fields: Mapping[str, Any] | None = None,
    owner_binding: Mapping[str, Any] | None = None,
    route_families: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    families = list(PROTECTED_ROUTE_FAMILIES if route_families is None else route_families)
    family = _family_by_name(families, route_family)
    if family is None:
        return _deny("sec_xbrl_in_app_auth_policy_route_family_not_admitted")

    blocked_fields = sorted(
        key
        for key, value in dict(request_fields or {}).items()
        if key in FORBIDDEN_REQUEST_FIELDS and value is not None
    )
    if blocked_fields:
        return _deny(
            "sec_xbrl_in_app_auth_policy_forbidden_request_fields",
            route_family=route_family,
            blocked_fields=blocked_fields,
        )

    principal = _principal(auth_context)
    if principal["decision"] == "deny":
        return {**principal, "route_family": route_family}

    role = str(requested_role or "").strip().lower()
    if role not in {OWNER_ROLE, AUDITOR_ROLE}:
        return _deny("sec_xbrl_in_app_auth_policy_role_not_admitted", route_family=route_family)
    if role not in set(family["allowed_roles"]):
        return _deny(
            "sec_xbrl_in_app_auth_policy_role_route_forbidden",
            route_family=route_family,
            role=role,
        )

    expected_binding = {
        "actor_ref_hash": principal["actor_ref_hash"],
        "workspace_ref_hash": principal["workspace_ref_hash"],
    }
    if owner_binding is not None:
        mismatches = [
            field
            for field, expected in expected_binding.items()
            if str(owner_binding.get(field) or "") != expected
        ]
        if mismatches:
            return _deny(
                "sec_xbrl_in_app_auth_policy_cross_owner_receipt",
                route_family=route_family,
                role=role,
                mismatched_fields=mismatches,
            )

    policy_hash = _stable_hash(
        {
            "policy_schema_id": POLICY_SCHEMA_ID,
            "selected_auth_mode": SELECTED_AUTH_MODE,
            "route_family": route_family,
            "role": role,
            "actor_ref_hash": principal["actor_ref_hash"],
            "workspace_ref_hash": principal["workspace_ref_hash"],
        }
    )
    requested_policy_hash = str((request_fields or {}).get("policy_hash") or "").strip()
    if requested_policy_hash and requested_policy_hash != policy_hash:
        return _deny(
            "sec_xbrl_in_app_auth_policy_stale_policy_hash",
            route_family=route_family,
            role=role,
        )

    return {
        "decision": "allow",
        "policy_status": "admitted",
        "reason_code": "sec_xbrl_in_app_auth_policy_role_route_admitted",
        "policy_schema_id": POLICY_SCHEMA_ID,
        "selected_auth_mode": SELECTED_AUTH_MODE,
        "route_family": route_family,
        "method": str(family["method"]),
        "route": str(family["route"]),
        "role": role,
        "actor_ref_hash": principal["actor_ref_hash"],
        "workspace_ref_hash": principal["workspace_ref_hash"],
        "policy_hash": policy_hash,
        "requires_owner_binding": bool(family["requires_owner_binding"]),
        "mutating_route": bool(family["mutating"]),
        "may_expose_revealed_values": bool(family["may_expose_revealed_values"]),
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_workspace_identity_exposed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "raw_value_exposed": False,
        "residual_magnitude_exposed": False,
    }


def _simulation_matrix(families: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    owner_context = _auth_context("owner")
    auditor_context = _auth_context("auditor")
    mismatched_binding = {
        "actor_ref_hash": _stable_hash({"actor_ref": "different"}),
        "workspace_ref_hash": owner_context["expected_workspace_ref_hash"],
    }
    for family in families:
        name = str(family["route_family"])
        cases.extend(
            [
                _case("anonymous_denied", name, OWNER_ROLE, None, {}),
                _case("missing_actor_denied", name, OWNER_ROLE, {"workspace_ref": "workspace"}, {}),
                _case(
                    "proxy_header_only_context_denied",
                    name,
                    OWNER_ROLE,
                    {
                        "context_authority": "trusted_external_proxy_headers_without_packet",
                        "actor_ref": "actor",
                        "workspace_ref": "workspace",
                    },
                    {},
                ),
                _case("spoofed_request_fields_denied", name, OWNER_ROLE, owner_context, _spoofed_fields()),
                _case("unsupported_role_denied", name, "admin", owner_context, {}),
                _case("stale_policy_hash_denied", name, OWNER_ROLE, owner_context, {"policy_hash": "0" * 64}),
                _case(
                    "cross_owner_receipt_denied",
                    name,
                    OWNER_ROLE,
                    owner_context,
                    {},
                    owner_binding=mismatched_binding,
                ),
                _case("owner_positive", name, OWNER_ROLE, owner_context, {}),
                _case("auditor_route_check", name, AUDITOR_ROLE, auditor_context, {}),
            ]
        )
    return cases


def _case(
    case_name: str,
    route_family: str,
    role: str,
    auth_context: Mapping[str, Any] | None,
    request_fields: Mapping[str, Any],
    *,
    owner_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = evaluate_policy(
        route_family=route_family,
        requested_role=role,
        auth_context=auth_context,
        request_fields=request_fields,
        owner_binding=owner_binding,
    )
    return {
        "case": case_name,
        "route_family": route_family,
        "requested_role": role,
        "decision": _redacted_decision(decision),
    }


def _redacted_decision(decision: Mapping[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "actor_ref_hash",
        "blocked_fields",
        "decision",
        "may_expose_revealed_values",
        "method",
        "mismatched_fields",
        "mutating_route",
        "policy_hash",
        "policy_schema_id",
        "policy_status",
        "raw_local_path_exposed",
        "raw_operator_identity_exposed",
        "raw_proxy_header_exposed",
        "raw_url_exposed",
        "raw_value_exposed",
        "raw_workspace_identity_exposed",
        "reason_code",
        "requires_owner_binding",
        "residual_magnitude_exposed",
        "role",
        "route",
        "route_family",
        "selected_auth_mode",
        "workspace_ref_hash",
    }
    return {key: decision[key] for key in sorted(allowed_keys) if key in decision}


def _principal(auth_context: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(auth_context, Mapping):
        return _deny("sec_xbrl_in_app_auth_policy_missing_operator_context")
    if str(auth_context.get("context_authority") or "") != ADMITTED_CONTEXT_AUTHORITY:
        return _deny("sec_xbrl_in_app_auth_policy_context_authority_not_admitted")
    actor_ref = str(auth_context.get("actor_ref") or "").strip()
    workspace_ref = str(auth_context.get("workspace_ref") or "").strip()
    if not actor_ref or not workspace_ref:
        return _deny("sec_xbrl_in_app_auth_policy_malformed_operator_context")
    return {
        "decision": "allow",
        "actor_ref_hash": _stable_hash({"actor_ref": actor_ref}),
        "workspace_ref_hash": _stable_hash({"workspace_ref": workspace_ref}),
    }


def _deny(reason_code: str, **details: Any) -> dict[str, Any]:
    return {
        "decision": "deny",
        "policy_status": "rejected",
        "reason_code": reason_code,
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_workspace_identity_exposed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "raw_value_exposed": False,
        "residual_magnitude_exposed": False,
        **details,
    }


def _auth_context(label: str) -> dict[str, str]:
    actor_ref = f"redacted-{label}-actor-ref"
    workspace_ref = f"redacted-{label}-workspace-ref"
    return {
        "context_authority": ADMITTED_CONTEXT_AUTHORITY,
        "actor_ref": actor_ref,
        "workspace_ref": workspace_ref,
        "expected_actor_ref_hash": _stable_hash({"actor_ref": actor_ref}),
        "expected_workspace_ref_hash": _stable_hash({"workspace_ref": workspace_ref}),
    }


def _spoofed_fields() -> dict[str, str]:
    return {
        "raw_operator_identity": "operator@example.invalid",
        "proxy_identity_header": "X-Forwarded-User",
        "raw_storage_root": "C:/redacted/local/storage",
        "raw_value": "123.45",
        "source_acquisition_override": "enabled",
    }


def _routes_present(families: Sequence[Mapping[str, Any]], api_source: str) -> bool:
    return all(str(family["route"]).replace("/api/v1/layer3", "") in api_source for family in families)


def _design_traceability_holds(families: Sequence[Mapping[str, Any]], design_doc: str) -> bool:
    return (
        SELECTED_AUTH_MODE in design_doc
        and TARGET in design_doc
        and all(str(family["route_family"]) in design_doc for family in families)
        and "anonymous request denied" in design_doc
        and "spoofed JSON auth/security/raw identity fields denied" in design_doc
    )


def _nonlocal_proxy_guardrails_hold(config_source: str) -> bool:
    required = (
        "DEPLOYMENT_MODE=nonlocal",
        "AUTH_OWNER=proxy is required",
        "TRUSTED_PROXY_MODE=true is required",
        "ALLOWED_ORIGINS must use explicit origins",
        "ALLOWED_ORIGINS must use HTTPS origins",
        "STORAGE_EXPOSURE must be auto or disabled",
    )
    return all(text in config_source for text in required)


def _candidate_b_precedent_present(source: str) -> bool:
    required = (
        "request_context",
        "reject_forbidden_request_fields",
        "authorize_workflow_access",
        "actor_ref_hash",
        "tenant_or_workspace_ref_hash",
        "raw_operator_identity_exposed",
    )
    return all(text in source for text in required)


def _negative_cases_fail_closed(simulations: Sequence[Mapping[str, Any]]) -> bool:
    for item in simulations:
        name = str(item["case"])
        decision = item["decision"]
        if name.endswith("_denied") and decision.get("decision") != "deny":
            return False
        if name == "auditor_route_check" and _auditor_should_be_denied(str(item["route_family"])):
            if decision.get("decision") != "deny":
                return False
    return True


def _auditor_should_be_denied(route_family: str) -> bool:
    family = _family_by_name(PROTECTED_ROUTE_FAMILIES, route_family)
    if family is None:
        return True
    return AUDITOR_ROLE not in set(family["allowed_roles"])


def _role_allowlist_holds(
    families: Sequence[Mapping[str, Any]],
    simulations: Sequence[Mapping[str, Any]],
) -> bool:
    for family in families:
        roles = set(family["allowed_roles"])
        if family["mutating"] and AUDITOR_ROLE in roles:
            return False
        if family["may_expose_revealed_values"] and AUDITOR_ROLE in roles:
            return False
    for item in simulations:
        if item["case"] != "auditor_route_check":
            continue
        decision = item["decision"]
        family = _family_by_name(families, str(item["route_family"]))
        if family is None:
            return False
        if AUDITOR_ROLE in set(family["allowed_roles"]):
            if decision.get("decision") != "allow":
                return False
        elif decision.get("decision") != "deny":
            return False
    return True


def _forbidden_fields_cover_required_classes() -> bool:
    required = {
        "auth_policy_override",
        "security_context",
        "raw_operator_identity",
        "raw_workspace_id",
        "proxy_identity_header",
        "raw_storage_root",
        "raw_url",
        "provider_secret",
        "token",
        "raw_value",
        "raw_value_store_payload",
        "default_on_override",
        "source_acquisition_override",
        "arelle_execution_override",
        "export_delivery_override",
    }
    return required.issubset(set(FORBIDDEN_REQUEST_FIELDS))


def _redacted_output_contract_holds(simulations: Sequence[Mapping[str, Any]]) -> bool:
    text = json.dumps(simulations, sort_keys=True)
    forbidden_fragments = (
        "operator@example.invalid",
        "C:/redacted/local/storage",
        "123.45",
        "redacted-owner-actor-ref",
        "redacted-auditor-actor-ref",
        "redacted-owner-workspace-ref",
        "redacted-auditor-workspace-ref",
    )
    if any(fragment in text for fragment in forbidden_fragments):
        return False
    for item in simulations:
        decision = item["decision"]
        for field in (
            "raw_operator_identity_exposed",
            "raw_proxy_header_exposed",
            "raw_workspace_identity_exposed",
            "raw_local_path_exposed",
            "raw_url_exposed",
            "raw_value_exposed",
            "residual_magnitude_exposed",
        ):
            if decision.get(field) is not False:
                return False
    return True


def _simulation_summary(simulations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "case_count": len(simulations),
        "allow_count": sum(1 for item in simulations if item["decision"].get("decision") == "allow"),
        "deny_count": sum(1 for item in simulations if item["decision"].get("decision") == "deny"),
        "cases": [
            {
                "case": item["case"],
                "route_family": item["route_family"],
                "requested_role": item["requested_role"],
                "decision": item["decision"].get("decision"),
                "reason_code": item["decision"].get("reason_code"),
            }
            for item in simulations
        ],
    }


def _denied_case_codes(simulations: Sequence[Mapping[str, Any]]) -> list[str]:
    codes = {
        str(item["decision"].get("reason_code"))
        for item in simulations
        if item["decision"].get("decision") == "deny"
    }
    return sorted(codes)


def _allowed_count(simulations: Sequence[Mapping[str, Any]], role: str) -> int:
    return sum(
        1
        for item in simulations
        if item["requested_role"] == role and item["decision"].get("decision") == "allow"
    )


def _route_summary(family: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "route_family": str(family["route_family"]),
        "method": str(family["method"]),
        "route": str(family["route"]),
        "allowed_roles": list(family["allowed_roles"]),
        "mutating": bool(family["mutating"]),
        "requires_owner_binding": bool(family["requires_owner_binding"]),
        "may_expose_revealed_values": bool(family["may_expose_revealed_values"]),
    }


def _family_by_name(
    families: Sequence[Mapping[str, Any]],
    route_family: str,
) -> Mapping[str, Any] | None:
    for family in families:
        if family.get("route_family") == route_family:
            return family
    return None


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
