from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = (
    ROOT
    / "diagnostics"
    / "assessment"
    / "sec-xbrl-auth-owner-binding-strategy.py"
)


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location(
        "sec_xbrl_auth_owner_binding_strategy",
        DIAGNOSTIC_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_auth_owner_binding_strategy_selects_separate_binding_table() -> None:
    module = _diagnostic_module()

    report = module.build_report()

    assert report["decision"] == "sec_xbrl_auth_owner_binding_strategy_selected"
    assert report["blocking_reasons"] == []
    assert report["selected_strategy"] == "separate_hash_only_auth_binding_receipt_table"
    assert report["next_slice"] == "sec_xbrl_nonlocal_in_app_auth_owner_binding_table_design_v1"
    assert report["non_goals_preserved"]["schema_models_changed_by_diagnostic"] is False
    assert report["non_goals_preserved"]["migration_changed_by_diagnostic"] is False
    assert report["non_goals_preserved"]["api_route_behavior_changed_by_diagnostic"] is False
    assert report["non_goals_preserved"]["owner_binding_persistence_implemented_by_diagnostic"] is False


def test_sec_xbrl_auth_owner_binding_strategy_fails_closed_on_empty_inventory() -> None:
    report = _diagnostic_module().build_report(receipt_surfaces=[])

    assert report["decision"] == "sec_xbrl_auth_owner_binding_strategy_blocked"
    assert "sec_xbrl_auth_owner_binding_strategy_receipt_surface_inventory_empty" in report["blocking_reasons"]
    assert "sec_xbrl_auth_owner_binding_strategy_receipt_surface_missing" in report["blocking_reasons"]


def test_sec_xbrl_auth_owner_binding_strategy_fails_closed_on_missing_surface() -> None:
    module = _diagnostic_module()
    missing_surface = {
        **module.RECEIPT_SURFACES[0],
        "model_class": "L3SecXbrlMissingReceipt",
    }

    report = module.build_report(receipt_surfaces=[missing_surface])

    assert report["decision"] == "sec_xbrl_auth_owner_binding_strategy_blocked"
    assert "sec_xbrl_auth_owner_binding_strategy_receipt_surface_missing" in report["blocking_reasons"]
    assert report["receipt_surface_inventory"][0]["surface_present"] is False


def test_sec_xbrl_auth_owner_binding_strategy_detects_mixed_current_binding_state() -> None:
    report = _diagnostic_module().build_report()
    states = {
        item["receipt_kind"]: item["owner_binding_state"]
        for item in report["receipt_surface_inventory"]
    }

    assert states["operator_review_workflow"] == "absent"
    assert states["operator_review_decision"] == "absent"
    assert states["value_reveal_authority"] == "partial"
    assert states["controlled_value_reveal_submit"] == "absent"


def test_sec_xbrl_auth_owner_binding_strategy_contract_is_hash_only_and_tier2_future() -> None:
    report = _diagnostic_module().build_report()
    selected = next(
        item
        for item in report["strategy_options"]
        if item["strategy"] == report["selected_strategy"]
    )

    assert selected["future_tier"] == "Tier 2"
    assert selected["implemented_now"] is False
    assert selected["recommended"] is True
    assert "actor_ref_hash" in report["proposed_binding_contract"]["fields"]
    assert "workspace_ref_hash" in report["proposed_binding_contract"]["fields"]
    assert "policy_hash" in report["proposed_binding_contract"]["fields"]
    assert report["proposed_binding_contract"]["redaction_policy"] == "hash_only_actor_workspace_policy_refs_v1"


def test_sec_xbrl_auth_owner_binding_strategy_report_is_redacted() -> None:
    report = _diagnostic_module().build_report()
    text = json.dumps(report, sort_keys=True)

    assert "operator@example" not in text
    assert "C:/" not in text
    assert "\\Users\\" not in text
    assert "/workspace/" not in text
    assert "0000123456" not in text
    assert "https://www.sec.gov/" not in text
    assert "123.45" not in text
    assert all(not criterion["blocked_reason"] for criterion in report["criteria"])
