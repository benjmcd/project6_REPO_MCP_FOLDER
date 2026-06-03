from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_operator_ui_controls_gate as gate


def test_operator_ui_controls_gate_blocks_by_default() -> None:
    report = gate.inspect_sec_xbrl_operator_ui_controls_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_operator_ui_controls_gate_requires_ready_api_contract() -> None:
    report = gate.inspect_sec_xbrl_operator_ui_controls_gate(
        operator_api_contract_gate={"status": "sec_xbrl_operator_api_contract_blocked", "ready": False},
        ui_control_spec=_ui_spec(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert any(
        item["reason"] == "sec_xbrl_operator_ui_controls_api_contract_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["public_surface"]["hash_count_state_only"] is True


def test_operator_ui_controls_gate_rejects_raw_display_spec_without_echoing_it() -> None:
    spec = {
        **_ui_spec(),
        "raw_values_rendered": True,
        "local_path": r"C:\raw\operator\screen",
    }

    report = gate.inspect_sec_xbrl_operator_ui_controls_gate(
        operator_api_contract_gate=_api_gate(),
        ui_control_spec=spec,
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_operator_ui_controls_raw_values_rendered_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_ui_controls_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\operator\screen" not in text


def test_operator_ui_controls_gate_requires_all_unsafe_controls_blocked() -> None:
    spec = {
        **_ui_spec(),
        "blocked_controls": ["reveal_values"],
    }

    report = gate.inspect_sec_xbrl_operator_ui_controls_gate(
        operator_api_contract_gate=_api_gate(),
        ui_control_spec=spec,
    )

    assert report["status"] == gate.STATUS_BLOCKED
    reason = next(
        item
        for item in report["blocked_reasons"]
        if item["reason"] == "sec_xbrl_operator_ui_controls_blocked_controls_unproven"
    )
    assert reason["controls"] == [
        "change_runtime_default",
        "edit_statement_packet",
        "invoke_arelle",
        "refresh_from_sec_source",
    ]


def test_operator_ui_controls_gate_reports_ready_without_rendering_ui() -> None:
    report = gate.inspect_sec_xbrl_operator_ui_controls_gate(
        operator_api_contract_gate=_api_gate(),
        ui_control_spec=_ui_spec(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["proof_source_report_hash"] == _hash("a")
    assert report["authority_refs"]["proof_result_hash"] == _hash("b")
    assert report["authority_refs"]["operator_api_contract_basis_hash"] == _hash("c")
    assert report["public_surface"]["api_only_data_flow"] is True
    assert report["public_surface"]["server_owned_authority_handles_only"] is True
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False


def _api_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_operator_api_contract_ready",
        "ready": True,
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "operator_api_contract_basis_hash": _hash("c"),
        },
    }


def _ui_spec() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_UI_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_UI_FLAGS})
    value["blocked_controls"] = sorted(gate.REQUIRED_BLOCKED_CONTROLS)
    return value


def _hash(char: str) -> str:
    return char * 64
