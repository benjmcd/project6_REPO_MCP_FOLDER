from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_rollback_monitoring_gate as gate


def test_rollback_monitoring_gate_blocks_by_default_without_starting_monitors() -> None:
    report = gate.inspect_sec_xbrl_rollback_monitoring_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["monitoring_started"] is False
    assert report["controls"]["alerts_enabled"] is False
    assert report["controls"]["production_readiness_claimed"] is False
    assert report["public_surface"]["hash_count_state_only"] is True


def test_rollback_monitoring_gate_requires_controlled_reveal_gate() -> None:
    report = gate.inspect_sec_xbrl_rollback_monitoring_gate(
        controlled_value_reveal_gate={"status": "sec_xbrl_controlled_value_reveal_gate_blocked", "ready": False},
        rollback_evidence=_rollback_evidence(),
        monitoring_spec=_monitoring_spec(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_rollback_monitoring_controlled_value_reveal_gate_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["monitoring_started"] is False


def test_rollback_monitoring_gate_requires_all_critical_events() -> None:
    spec = {
        **_monitoring_spec(),
        "events": ["atomic_persistence_rollback"],
    }

    report = gate.inspect_sec_xbrl_rollback_monitoring_gate(
        controlled_value_reveal_gate=_reveal_gate(),
        rollback_evidence=_rollback_evidence(),
        monitoring_spec=spec,
    )

    assert report["status"] == gate.STATUS_BLOCKED
    reason = next(
        item
        for item in report["blocked_reasons"]
        if item["reason"] == "sec_xbrl_rollback_monitoring_events_unproven"
    )
    assert reason["events"] == [
        "evidence_authority_gap",
        "offline_evidence_proof_blocked",
        "operator_decision_recorded",
        "production_admission_denied",
        "redaction_containment_blocked",
        "value_reveal_attempt",
        "value_reveal_denied",
    ]


def test_rollback_monitoring_gate_rejects_raw_logs_without_echoing_them() -> None:
    spec = {
        **_monitoring_spec(),
        "raw_values_logged": True,
        "local_path": r"C:\raw\monitor\log",
    }

    report = gate.inspect_sec_xbrl_rollback_monitoring_gate(
        controlled_value_reveal_gate=_reveal_gate(),
        rollback_evidence=_rollback_evidence(),
        monitoring_spec=spec,
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_rollback_monitoring_raw_values_logged_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_rollback_monitoring_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\monitor\log" not in text


def test_rollback_monitoring_gate_reports_ready_without_running_monitoring() -> None:
    report = gate.inspect_sec_xbrl_rollback_monitoring_gate(
        controlled_value_reveal_gate=_reveal_gate(),
        rollback_evidence=_rollback_evidence(),
        monitoring_spec=_monitoring_spec(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["controlled_value_reveal_gate_basis_hash"] == _hash("6")
    assert report["summary"]["declared_required_event_count"] == len(gate.REQUIRED_MONITORING_EVENTS)
    assert report["controls"]["monitoring_started"] is False
    assert report["controls"]["alerts_enabled"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["public_surface"]["raw_values_logged"] is False
    assert report["public_surface"]["local_paths_logged"] is False


def _reveal_gate() -> dict[str, object]:
    return {
        "status": "sec_xbrl_controlled_value_reveal_gate_ready",
        "ready": True,
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "operator_api_contract_basis_hash": _hash("c"),
            "operator_ui_controls_basis_hash": _hash("d"),
            "operator_review_decision_basis_hash": _hash("e"),
            "value_reveal_authority_basis_hash": _hash("f"),
            "controlled_value_reveal_gate_basis_hash": _hash("6"),
        },
    }


def _rollback_evidence() -> dict[str, bool]:
    return {
        key: True
        for key in gate.REQUIRED_ROLLBACK_FLAGS
    }


def _monitoring_spec() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_MONITORING_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_MONITORING_FLAGS})
    value["events"] = sorted(gate.REQUIRED_MONITORING_EVENTS)
    return value


def _hash(char: str) -> str:
    return char * 64
