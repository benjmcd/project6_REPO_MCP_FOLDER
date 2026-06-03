from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_targeted_validation_gate as gate


def test_targeted_validation_gate_blocks_by_default_without_running_commands() -> None:
    report = gate.inspect_sec_xbrl_targeted_validation_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["commands_executed_by_gate"] is False
    assert report["controls"]["production_readiness_claimed"] is False
    assert report["public_surface"]["hash_count_state_only"] is True


def test_targeted_validation_gate_requires_runbook_gate() -> None:
    report = gate.inspect_sec_xbrl_targeted_validation_gate(
        runbook_gate={"status": "sec_xbrl_runbook_gate_blocked", "ready": False},
        validation_evidence=_validation_evidence(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_targeted_validation_runbook_gate_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["commands_executed_by_gate"] is False


def test_targeted_validation_gate_requires_all_validation_lanes() -> None:
    report = gate.inspect_sec_xbrl_targeted_validation_gate(
        runbook_gate=_runbook_gate(),
        validation_evidence={"validations": [_validation("atomic_offline_orchestrator_tests")]},
    )

    assert report["status"] == gate.STATUS_BLOCKED
    reason = next(
        item
        for item in report["blocked_reasons"]
        if item["reason"] == "sec_xbrl_targeted_validation_required_validations_unproven"
    )
    assert "fizz_10k_atomic_proof_diagnostic" in reason["validations"]
    assert "operator_review_open_api_route_tests" in reason["validations"]
    assert "operator_authority_resolver_gate_tests" in reason["validations"]
    assert "production_admission_gate_chain_tests" in reason["validations"]
    assert "production_release_decision_gate_tests" in reason["validations"]
    assert "controlled_release_activation_gate_tests" in reason["validations"]
    assert "controlled_release_status_api_tests" in reason["validations"]
    assert "full_sec_xbrl_regression" in reason["validations"]


def test_targeted_validation_gate_rejects_failed_or_raw_validation_output() -> None:
    validations = [_validation(name) for name in sorted(gate.REQUIRED_VALIDATIONS)]
    validations[0] = {
        **validations[0],
        "passed": False,
        "raw_values_observed": True,
        "local_path": r"C:\raw\pytest.log",
    }

    report = gate.inspect_sec_xbrl_targeted_validation_gate(
        runbook_gate=_runbook_gate(),
        validation_evidence={"validations": validations},
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any("_passed_unproven" in item["reason"] for item in report["blocked_reasons"])
    assert any("_raw_values_observed_unproven" in item["reason"] for item in report["blocked_reasons"])
    assert any(
        item["reason"] == "sec_xbrl_targeted_validation_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\pytest.log" not in text


def test_targeted_validation_gate_reports_ready_without_executing_commands() -> None:
    report = gate.inspect_sec_xbrl_targeted_validation_gate(
        runbook_gate=_runbook_gate(),
        validation_evidence=_validation_evidence(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["runbook_basis_hash"] == _hash("8")
    assert report["authority_refs"]["operator_authority_resolver_basis_hash"] == _hash("9")
    assert report["summary"]["declared_required_validation_count"] == len(gate.REQUIRED_VALIDATIONS)
    assert report["controls"]["commands_executed_by_gate"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def _runbook_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_runbook_gate_ready",
        "ready": True,
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "operator_api_contract_basis_hash": _hash("c"),
            "operator_authority_resolver_basis_hash": _hash("9"),
            "operator_ui_controls_basis_hash": _hash("d"),
            "operator_review_decision_basis_hash": _hash("e"),
            "value_reveal_authority_basis_hash": _hash("f"),
            "controlled_value_reveal_gate_basis_hash": _hash("6"),
            "rollback_monitoring_basis_hash": _hash("7"),
            "runbook_basis_hash": _hash("8"),
        },
    }


def _validation_evidence() -> dict[str, object]:
    return {
        "validations": [
            _validation(name)
            for name in sorted(gate.REQUIRED_VALIDATIONS)
        ]
    }


def _validation(name: str) -> dict[str, object]:
    value: dict[str, object] = {
        "validation": name,
    }
    value.update({key: True for key in gate.REQUIRED_EVIDENCE_FLAGS})
    value.update({key: False for key in gate.NEGATIVE_EVIDENCE_FLAGS})
    return value


def _hash(char: str) -> str:
    return char * 64
