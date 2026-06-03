from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_controlled_value_reveal_gate as gate


def test_controlled_value_reveal_gate_blocks_by_default_without_revealing_values() -> None:
    report = gate.inspect_sec_xbrl_controlled_value_reveal_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["production_readiness_claimed"] is False
    assert report["public_surface"]["raw_values_returned"] is False
    assert report["public_surface"]["raw_values_persisted"] is False


def test_controlled_value_reveal_gate_requires_review_decision_and_authority() -> None:
    report = gate.inspect_sec_xbrl_controlled_value_reveal_gate(
        operator_ui_controls_gate=_ui_gate(),
        reveal_contract=_reveal_contract(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_controlled_value_reveal_gate_operator_review_decision_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_controlled_value_reveal_gate_value_reveal_authority_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["value_reveal_performed"] is False


def test_controlled_value_reveal_gate_rejects_raw_values_without_echoing_them() -> None:
    contract = {
        **_reveal_contract(),
        "raw_values_persisted": True,
        "effective_value": "123.45",
        "local_path": r"C:\raw\value-store",
    }

    report = gate.inspect_sec_xbrl_controlled_value_reveal_gate(
        operator_ui_controls_gate=_ui_gate(),
        operator_review_decision_gate=_decision_gate(),
        reveal_authority_gate=_authority_gate(),
        reveal_contract=contract,
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_controlled_value_reveal_gate_raw_values_persisted_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_controlled_value_reveal_gate_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert "123.45" not in text
    assert r"C:\raw\value-store" not in text


def test_controlled_value_reveal_gate_blocks_if_reveal_already_performed() -> None:
    contract = {
        **_reveal_contract(),
        "reveal_performed": True,
    }

    report = gate.inspect_sec_xbrl_controlled_value_reveal_gate(
        operator_ui_controls_gate=_ui_gate(),
        operator_review_decision_gate=_decision_gate(),
        reveal_authority_gate=_authority_gate(),
        reveal_contract=contract,
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_controlled_value_reveal_gate_reveal_performed_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["value_reveal_performed"] is False


def test_controlled_value_reveal_gate_reports_ready_without_revealing_or_enabling_runtime() -> None:
    report = gate.inspect_sec_xbrl_controlled_value_reveal_gate(
        operator_ui_controls_gate=_ui_gate(),
        operator_review_decision_gate=_decision_gate(),
        reveal_authority_gate=_authority_gate(),
        reveal_contract=_reveal_contract(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["operator_ui_controls_basis_hash"] == _hash("d")
    assert report["authority_refs"]["operator_review_decision_basis_hash"] == _hash("e")
    assert report["authority_refs"]["value_reveal_authority_basis_hash"] == _hash("f")
    assert report["public_surface"]["transient_values_only"] is True
    assert report["public_surface"]["status_hash_count_state_only"] is True
    assert report["public_surface"]["audit_receipt_hash_count_only"] is True
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["production_database_touched"] is False


def _ui_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_operator_ui_controls_ready",
        "ready": True,
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "operator_api_contract_basis_hash": _hash("c"),
            "operator_ui_controls_basis_hash": _hash("d"),
        },
    }


def _decision_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_operator_review_decision_gate_ready",
        "ready": True,
        "authority_refs": {
            "operator_review_decision_basis_hash": _hash("e"),
        },
    }


def _authority_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_value_reveal_authority_gate_ready",
        "ready": True,
        "authority_refs": {
            "value_reveal_authority_basis_hash": _hash("f"),
        },
    }


def _reveal_contract() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_REVEAL_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_REVEAL_FLAGS})
    return value


def _hash(char: str) -> str:
    return char * 64
