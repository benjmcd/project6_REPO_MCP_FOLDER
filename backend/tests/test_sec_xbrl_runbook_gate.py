from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_runbook_gate as gate


def test_runbook_gate_blocks_by_default_without_executing_runbooks() -> None:
    report = gate.inspect_sec_xbrl_runbook_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["runbooks_executed"] is False
    assert report["controls"]["monitoring_started"] is False
    assert report["controls"]["production_readiness_claimed"] is False
    assert report["public_surface"]["hash_count_state_only"] is True


def test_runbook_gate_requires_rollback_monitoring_gate() -> None:
    report = gate.inspect_sec_xbrl_runbook_gate(
        rollback_monitoring_gate={"status": "sec_xbrl_rollback_monitoring_gate_blocked", "ready": False},
        runbook_spec=_runbook_spec(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_runbook_rollback_monitoring_gate_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["runbooks_executed"] is False


def test_runbook_gate_requires_all_critical_runbooks() -> None:
    report = gate.inspect_sec_xbrl_runbook_gate(
        rollback_monitoring_gate=_monitoring_gate(),
        runbook_spec={"runbooks": [_runbook("offline_evidence_proof_blocked")]},
    )

    assert report["status"] == gate.STATUS_BLOCKED
    reason = next(
        item
        for item in report["blocked_reasons"]
        if item["reason"] == "sec_xbrl_runbook_required_runbooks_unproven"
    )
    assert reason["runbooks"] == [
        "atomic_persistence_rollback",
        "evidence_authority_gap",
        "monitoring_alert_response",
        "operator_authority_resolver_failure",
        "operator_decision_failure",
        "production_admission_denied",
        "production_release_rollback",
        "redaction_containment_blocked",
        "value_reveal_denied",
        "value_reveal_incident",
    ]


def test_runbook_gate_rejects_raw_or_destructive_runbooks_without_echoing_paths() -> None:
    runbooks = [_runbook(name) for name in sorted(gate.REQUIRED_RUNBOOKS)]
    runbooks[0] = {
        **runbooks[0],
        "destructive_command_required": True,
        "local_path": r"C:\raw\incident\runbook",
    }

    report = gate.inspect_sec_xbrl_runbook_gate(
        rollback_monitoring_gate=_monitoring_gate(),
        runbook_spec={"runbooks": runbooks},
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any("destructive_command_required" in item["reason"] for item in report["blocked_reasons"])
    assert any(
        item["reason"] == "sec_xbrl_runbook_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\incident\runbook" not in text


def test_runbook_gate_reports_ready_without_executing_runbooks() -> None:
    report = gate.inspect_sec_xbrl_runbook_gate(
        rollback_monitoring_gate=_monitoring_gate(),
        runbook_spec=_runbook_spec(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["rollback_monitoring_basis_hash"] == _hash("7")
    assert report["authority_refs"]["operator_authority_resolver_basis_hash"] == _hash("9")
    assert report["summary"]["declared_required_runbook_count"] == len(gate.REQUIRED_RUNBOOKS)
    assert report["controls"]["runbooks_executed"] is False
    assert report["controls"]["monitoring_started"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["public_surface"]["destructive_commands_required"] is False


def _monitoring_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_rollback_monitoring_gate_ready",
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
        },
    }


def _runbook_spec() -> dict[str, object]:
    return {
        "runbooks": [
            _runbook(name)
            for name in sorted(gate.REQUIRED_RUNBOOKS)
        ]
    }


def _runbook(name: str) -> dict[str, object]:
    value: dict[str, object] = {
        "runbook": name,
    }
    value.update({key: True for key in gate.REQUIRED_RUNBOOK_FLAGS})
    value.update({key: False for key in gate.NEGATIVE_RUNBOOK_FLAGS})
    return value


def _hash(char: str) -> str:
    return char * 64
