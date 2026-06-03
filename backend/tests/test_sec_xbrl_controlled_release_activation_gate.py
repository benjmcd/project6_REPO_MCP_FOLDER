from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_controlled_release_activation_gate as gate


def test_controlled_release_activation_gate_blocks_by_default_without_activation() -> None:
    report = gate.inspect_sec_xbrl_controlled_release_activation_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["readiness"]["controlled_release_activation_executed"] is False
    assert report["readiness"]["production_release_executed"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["production_database_touched"] is False


def test_controlled_release_activation_gate_requires_release_decision_review_ready() -> None:
    release_gate = {
        **_release_gate(),
        "status": "sec_xbrl_production_release_decision_gate_blocked",
        "readiness": {
            "production_release_decision_review_ready": False,
            "production_release_executed": False,
        },
    }

    report = gate.inspect_sec_xbrl_controlled_release_activation_gate(
        production_release_decision_gate=release_gate,
        activation_spec=_activation_spec(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_controlled_release_activation_release_decision_gate_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["readiness"]["controlled_release_activation_executed"] is False


def test_controlled_release_activation_gate_requires_matching_release_decision_basis() -> None:
    report = gate.inspect_sec_xbrl_controlled_release_activation_gate(
        production_release_decision_gate=_release_gate(),
        activation_spec={
            **_activation_spec(),
            "production_release_decision_basis_hash": _hash("9"),
        },
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_controlled_release_activation_activation_release_decision_basis_mismatch_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["summary"]["release_decision_basis_bound"] is False


def test_controlled_release_activation_gate_rejects_raw_or_auto_activation_without_echoing_it() -> None:
    report = gate.inspect_sec_xbrl_controlled_release_activation_gate(
        production_release_decision_gate=_release_gate(),
        activation_spec={
            **_activation_spec(),
            "auto_activation_enabled": True,
            "local_path": r"C:\raw\activation\switch",
        },
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_controlled_release_activation_auto_activation_enabled_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_controlled_release_activation_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\activation\switch" not in text


def test_controlled_release_activation_gate_reports_preflight_ready_but_does_not_activate() -> None:
    report = gate.inspect_sec_xbrl_controlled_release_activation_gate(
        production_release_decision_gate=_release_gate(),
        activation_spec=_activation_spec(),
    )

    assert report["status"] == gate.STATUS_PREFLIGHT_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["production_release_decision_basis_hash"] == _hash("d")
    assert report["authority_refs"]["controlled_release_activation_basis_hash"]
    assert report["readiness"]["controlled_release_activation_preflight_ready"] is True
    assert report["readiness"]["controlled_release_activation_executed"] is False
    assert report["readiness"]["production_release_executed"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["public_surface"]["deploy_switch_exposed"] is False


def _release_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_production_release_decision_gate_review_ready",
        "readiness": {
            "production_release_decision_review_ready": True,
            "production_release_executed": False,
            "production_release_blocked": False,
        },
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "admission_basis_hash": _hash("c"),
            "production_release_decision_basis_hash": _hash("d"),
        },
        "controls": {
            "validate_only": True,
            "release_executed_by_gate": False,
            "runtime_default_enabled": False,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
    }


def _activation_spec() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_ACTIVATION_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_ACTIVATION_FLAGS})
    value["production_release_decision_basis_hash"] = _hash("d")
    return value


def _hash(char: str) -> str:
    return char * 64
