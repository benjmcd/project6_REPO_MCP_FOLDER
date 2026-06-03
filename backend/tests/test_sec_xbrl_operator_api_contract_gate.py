from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_operator_api_contract_gate as gate


def test_operator_api_contract_gate_blocks_by_default() -> None:
    report = gate.inspect_sec_xbrl_operator_api_contract_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["operator_review_open_api_route_enabled"] is False
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_operator_api_contract_gate_requires_atomic_proof() -> None:
    report = gate.inspect_sec_xbrl_operator_api_contract_gate(
        proof_capability_report=_proof_report(single_transaction=False),
        contract_spec=_contract_spec(),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["ready"] is False
    assert any(
        item["reason"] == "sec_xbrl_operator_api_contract_single_transaction_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["public_surface"]["hash_count_state_only"] is True


def test_operator_api_contract_gate_rejects_raw_or_client_reconstructed_contract() -> None:
    contract = {
        **_contract_spec(),
        "raw_operator_paths_admitted": True,
        "admitted_request_fields": [
            "client_request_id",
            "proof_source_report_hash",
            "storage_dir",
        ],
        "local_path": r"C:\raw\operator\path",
    }

    report = gate.inspect_sec_xbrl_operator_api_contract_gate(
        proof_capability_report=_proof_report(),
        contract_spec=contract,
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_operator_api_contract_raw_operator_paths_admitted_unproven"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_api_contract_unadmitted_request_fields"
        for item in report["blocked_reasons"]
    )
    assert any(
        item["reason"] == "sec_xbrl_operator_api_contract_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\operator\path" not in text
    assert "storage_dir" in text


def test_operator_api_contract_gate_reports_ready_without_enabling_api() -> None:
    report = gate.inspect_sec_xbrl_operator_api_contract_gate(
        proof_capability_report=_proof_report(),
        contract_spec=_contract_spec(),
    )

    assert report["status"] == gate.STATUS_READY
    assert report["ready"] is True
    assert report["blocked_reasons"] == []
    assert report["authority_refs"]["proof_source_report_hash"] == _hash("a")
    assert report["authority_refs"]["proof_result_hash"] == _hash("b")
    assert report["summary"]["admitted_request_fields"] == [
        "client_request_id",
        "open_mode",
        "operator_decision",
        "operator_review_authority_handle",
        "period_limit",
        "proof_source_report_hash",
    ]
    assert report["public_surface"]["server_owned_authority_handles_only"] is True
    assert report["public_surface"]["workflow_open_route_default_disabled"] is True
    assert report["public_surface"]["caller_supplied_evidence_admitted"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["operator_review_open_api_route_enabled"] is False
    assert report["controls"]["workflow_open_route_contract_declared"] is True
    assert report["controls"]["workflow_open_route_default_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False


def _proof_report(*, single_transaction: bool = True) -> dict[str, object]:
    return {
        "status": "offline_evidence_proof_capability_ready",
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
        },
        "containment": {
            "single_transaction_claimed": single_transaction,
        },
    }


def _contract_spec() -> dict[str, object]:
    value: dict[str, object] = {
        key: True
        for key in gate.REQUIRED_CONTRACT_FLAGS
    }
    value.update({key: False for key in gate.NEGATIVE_CONTRACT_FLAGS})
    value["admitted_request_fields"] = [
        "client_request_id",
        "open_mode",
        "operator_decision",
        "period_limit",
        "proof_source_report_hash",
        "operator_review_authority_handle",
    ]
    return value


def _hash(char: str) -> str:
    return char * 64
