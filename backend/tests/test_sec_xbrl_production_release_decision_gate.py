from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_production_release_decision_gate as gate


def test_production_release_decision_gate_blocks_by_default_without_release() -> None:
    report = gate.inspect_sec_xbrl_production_release_decision_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["readiness"]["production_release_executed"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["release_executed_by_gate"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_production_release_decision_gate_requires_admission_review_ready() -> None:
    report = gate.inspect_sec_xbrl_production_release_decision_gate(
        production_admission_gate={
            **_admission_gate(),
            "status": "layer3_sec_xbrl_production_admission_blocked",
            "readiness": {
                "production_admission_review_ready": False,
                "production_admission_admitted": False,
            },
        },
        release_decision_spec=_release_decision(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_production_release_decision_admission_gate_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["readiness"]["production_release_executed"] is False


def test_production_release_decision_gate_requires_matching_admission_basis() -> None:
    report = gate.inspect_sec_xbrl_production_release_decision_gate(
        production_admission_gate=_admission_gate(),
        release_decision_spec={
            **_release_decision(),
            "admission_basis_hash": _hash("9"),
        },
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_production_release_decision_release_admission_basis_mismatch_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["summary"]["admission_basis_bound"] is False


def test_production_release_decision_gate_rejects_raw_release_input_without_echoing_it() -> None:
    report = gate.inspect_sec_xbrl_production_release_decision_gate(
        production_admission_gate=_admission_gate(),
        release_decision_spec={
            **_release_decision(),
            "auto_release_enabled": True,
            "local_path": r"C:\raw\release\decision",
        },
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_production_release_decision_auto_release_enabled_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_production_release_decision_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\release\decision" not in text


def test_production_release_decision_gate_reports_review_ready_but_does_not_execute_release() -> None:
    report = gate.inspect_sec_xbrl_production_release_decision_gate(
        production_admission_gate=_admission_gate(),
        release_decision_spec=_release_decision(),
    )

    assert report["status"] == gate.STATUS_REVIEW_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["admission_basis_hash"] == _hash("c")
    assert report["authority_refs"]["production_release_decision_basis_hash"]
    assert report["readiness"]["production_release_decision_review_ready"] is True
    assert report["readiness"]["production_release_executed"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["public_surface"]["release_switch_exposed"] is False


def _admission_gate() -> dict[str, object]:
    return {
        "status": "layer3_sec_xbrl_production_admission_review_ready",
        "readiness": {
            "production_admission_review_ready": True,
            "production_admission_admitted": False,
            "production_admission_blocked": False,
        },
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
            "admission_basis_hash": _hash("c"),
        },
        "controls": {
            "validate_only": True,
            "runtime_default_enabled": False,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
    }


def _release_decision() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_RELEASE_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_RELEASE_FLAGS})
    value["admission_basis_hash"] = _hash("c")
    return value


def _hash(char: str) -> str:
    return char * 64
