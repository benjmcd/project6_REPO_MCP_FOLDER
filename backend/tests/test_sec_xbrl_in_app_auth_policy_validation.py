from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = (
    ROOT
    / "diagnostics"
    / "assessment"
    / "sec-xbrl-in-app-auth-policy-validation.py"
)


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location(
        "sec_xbrl_in_app_auth_policy_validation",
        DIAGNOSTIC_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_in_app_auth_policy_validation_passes_current_map() -> None:
    module = _diagnostic_module()

    report = module.build_report()

    assert report["decision"] == "sec_xbrl_in_app_auth_policy_validation_passed"
    assert report["blocking_reasons"] == []
    assert report["selected_auth_mode"] == module.SELECTED_AUTH_MODE
    assert report["non_goals_preserved"]["runtime_auth_dependency_installed_by_diagnostic"] is False
    assert report["non_goals_preserved"]["api_route_behavior_changed_by_diagnostic"] is False
    assert report["non_goals_preserved"]["schema_models_changed_by_diagnostic"] is False
    assert report["non_goals_preserved"]["value_reveal_default_enabled_by_diagnostic"] is False
    assert report["next_slice"] == "sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1"


def test_sec_xbrl_in_app_auth_policy_validation_fails_closed_on_empty_route_map() -> None:
    report = _diagnostic_module().build_report(route_families=[])

    assert report["decision"] == "sec_xbrl_in_app_auth_policy_validation_blocked"
    assert "sec_xbrl_in_app_auth_policy_route_family_map_empty" in report["blocking_reasons"]
    assert report["route_family_map"] == []


def test_sec_xbrl_in_app_auth_policy_denies_anonymous_and_untrusted_proxy_context() -> None:
    module = _diagnostic_module()

    anonymous = module.evaluate_policy(
        route_family="sec_xbrl_operator_review_workflow_status_read",
        requested_role="owner",
        auth_context=None,
    )
    proxy_header_only = module.evaluate_policy(
        route_family="sec_xbrl_operator_review_workflow_status_read",
        requested_role="owner",
        auth_context={
            "context_authority": "trusted_external_proxy_headers_without_packet",
            "actor_ref": "actor",
            "workspace_ref": "workspace",
        },
    )

    assert anonymous["decision"] == "deny"
    assert anonymous["reason_code"] == "sec_xbrl_in_app_auth_policy_missing_operator_context"
    assert proxy_header_only["decision"] == "deny"
    assert proxy_header_only["reason_code"] == "sec_xbrl_in_app_auth_policy_context_authority_not_admitted"


def test_sec_xbrl_in_app_auth_policy_rejects_spoofed_auth_and_raw_fields() -> None:
    module = _diagnostic_module()

    decision = module.evaluate_policy(
        route_family="sec_xbrl_operator_review_decision_submit_write",
        requested_role="owner",
        auth_context={
            "context_authority": module.ADMITTED_CONTEXT_AUTHORITY,
            "actor_ref": "redacted-owner-actor-ref",
            "workspace_ref": "redacted-owner-workspace-ref",
        },
        request_fields={
            "raw_operator_identity": "operator@example.invalid",
            "proxy_identity_header": "X-Forwarded-User",
            "raw_storage_root": "C:/redacted/local/storage",
            "raw_value": "123.45",
            "source_acquisition_override": "enabled",
        },
    )

    assert decision["decision"] == "deny"
    assert decision["reason_code"] == "sec_xbrl_in_app_auth_policy_forbidden_request_fields"
    assert set(decision["blocked_fields"]) == {
        "proxy_identity_header",
        "raw_operator_identity",
        "raw_storage_root",
        "raw_value",
        "source_acquisition_override",
    }
    assert "operator@example.invalid" not in json.dumps(decision, sort_keys=True)
    assert "123.45" not in json.dumps(decision, sort_keys=True)


def test_sec_xbrl_in_app_auth_policy_allows_owner_and_constrains_auditor() -> None:
    module = _diagnostic_module()
    context = {
        "context_authority": module.ADMITTED_CONTEXT_AUTHORITY,
        "actor_ref": "redacted-owner-actor-ref",
        "workspace_ref": "redacted-owner-workspace-ref",
    }

    owner_decision = module.evaluate_policy(
        route_family="sec_xbrl_controlled_value_reveal_submit_write",
        requested_role="owner",
        auth_context=context,
    )
    auditor_read = module.evaluate_policy(
        route_family="sec_xbrl_operator_review_workflow_status_read",
        requested_role="auditor",
        auth_context=context,
    )
    auditor_write = module.evaluate_policy(
        route_family="sec_xbrl_controlled_value_reveal_submit_write",
        requested_role="auditor",
        auth_context=context,
    )
    auditor_reveal_status = module.evaluate_policy(
        route_family="sec_xbrl_controlled_value_reveal_submit_status_read",
        requested_role="auditor",
        auth_context=context,
    )

    assert owner_decision["decision"] == "allow"
    assert owner_decision["may_expose_revealed_values"] is True
    assert auditor_read["decision"] == "allow"
    assert auditor_write["decision"] == "deny"
    assert auditor_write["reason_code"] == "sec_xbrl_in_app_auth_policy_role_route_forbidden"
    assert auditor_reveal_status["decision"] == "deny"
    assert auditor_reveal_status["reason_code"] == "sec_xbrl_in_app_auth_policy_role_route_forbidden"


def test_sec_xbrl_in_app_auth_policy_rejects_stale_policy_hash_and_cross_owner_binding() -> None:
    module = _diagnostic_module()
    context = {
        "context_authority": module.ADMITTED_CONTEXT_AUTHORITY,
        "actor_ref": "redacted-owner-actor-ref",
        "workspace_ref": "redacted-owner-workspace-ref",
    }

    stale = module.evaluate_policy(
        route_family="sec_xbrl_operator_review_workflow_status_read",
        requested_role="owner",
        auth_context=context,
        request_fields={"policy_hash": "0" * 64},
    )
    cross_owner = module.evaluate_policy(
        route_family="sec_xbrl_operator_review_workflow_status_read",
        requested_role="owner",
        auth_context=context,
        owner_binding={"actor_ref_hash": "1" * 64, "workspace_ref_hash": "2" * 64},
    )

    assert stale["decision"] == "deny"
    assert stale["reason_code"] == "sec_xbrl_in_app_auth_policy_stale_policy_hash"
    assert cross_owner["decision"] == "deny"
    assert cross_owner["reason_code"] == "sec_xbrl_in_app_auth_policy_cross_owner_receipt"
    assert set(cross_owner["mismatched_fields"]) == {"actor_ref_hash", "workspace_ref_hash"}


def test_sec_xbrl_in_app_auth_policy_report_is_redacted() -> None:
    report = _diagnostic_module().build_report()
    text = json.dumps(report, sort_keys=True)

    assert "operator@example.invalid" not in text
    assert "C:/redacted/local/storage" not in text
    assert "123.45" not in text
    assert "redacted-owner-actor-ref" not in text
    assert "redacted-owner-workspace-ref" not in text
    assert all(not criterion["blocked_reason"] for criterion in report["criteria"])
