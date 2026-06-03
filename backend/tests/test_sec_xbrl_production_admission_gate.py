from __future__ import annotations

import json

from app.services import layer3_sec_xbrl_production_admission_gate as gate


def test_production_admission_gate_blocks_by_default_without_overclaiming() -> None:
    report = gate.inspect_sec_xbrl_production_admission_gate()

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["summary"]["required_gate_count"] == len(gate.REQUIRED_GATES)
    assert report["summary"]["ready_gate_count"] == 0
    assert report["readiness"]["production_admission_review_ready"] is False
    assert report["readiness"]["production_admission_admitted"] is False
    assert report["controls"]["validate_only"] is True
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_production_admission_gate_requires_atomic_proof_before_review_ready() -> None:
    proof = _proof_report(single_transaction=False)

    report = gate.inspect_sec_xbrl_production_admission_gate(
        proof_capability_report=proof,
        evidence_authority_matrix=_ready_gate("sec_xbrl_multi_filing_evidence_authority_ready", ready_filing_count=3),
        operator_api_gate=_ready_gate("sec_xbrl_operator_api_contract_ready"),
        operator_authority_resolver_gate=_ready_gate("sec_xbrl_operator_authority_resolver_gate_ready"),
        operator_ui_gate=_ready_gate("sec_xbrl_operator_ui_controls_ready"),
        controlled_value_reveal_gate=_ready_gate("sec_xbrl_controlled_value_reveal_gate_ready"),
        rollback_monitoring_gate=_ready_gate("sec_xbrl_rollback_monitoring_gate_ready"),
        runbook_gate=_ready_gate("sec_xbrl_runbook_gate_ready"),
        validation_gate=_ready_gate("sec_xbrl_targeted_validation_gate_ready"),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["summary"]["gates"]["offline_evidence_proof_capability"] is True
    assert report["summary"]["gates"]["redaction_containment"] is True
    assert report["summary"]["gates"]["single_transaction_persistence"] is False
    assert any(
        item["reason"] == "sec_xbrl_production_admission_single_transaction_persistence_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["readiness"]["production_admission_admitted"] is False


def test_production_admission_gate_requires_operator_authority_resolver_before_review_ready() -> None:
    report = gate.inspect_sec_xbrl_production_admission_gate(
        proof_capability_report=_proof_report(),
        evidence_authority_matrix=_ready_gate("sec_xbrl_multi_filing_evidence_authority_ready", ready_filing_count=3),
        operator_api_gate=_ready_gate("sec_xbrl_operator_api_contract_ready"),
        operator_ui_gate=_ready_gate("sec_xbrl_operator_ui_controls_ready"),
        controlled_value_reveal_gate=_ready_gate("sec_xbrl_controlled_value_reveal_gate_ready"),
        rollback_monitoring_gate=_ready_gate("sec_xbrl_rollback_monitoring_gate_ready"),
        runbook_gate=_ready_gate("sec_xbrl_runbook_gate_ready"),
        validation_gate=_ready_gate("sec_xbrl_targeted_validation_gate_ready"),
    )

    assert report["status"] == gate.STATUS_BLOCKED
    assert report["summary"]["gates"]["operator_authority_resolver"] is False
    assert any(
        item["reason"] == "sec_xbrl_production_admission_operator_authority_resolver_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["readiness"]["production_admission_review_ready"] is False
    assert report["readiness"]["production_admission_admitted"] is False


def test_production_admission_gate_blocks_raw_input_without_echoing_it() -> None:
    report = gate.inspect_sec_xbrl_production_admission_gate(
        proof_capability_report=_proof_report(),
        operator_api_gate={
            "status": "sec_xbrl_operator_api_contract_ready",
            "ready": True,
            "local_path": r"C:\raw\operator\path",
        },
    )
    text = json.dumps(report, sort_keys=True)

    assert report["status"] == gate.STATUS_BLOCKED
    assert any(
        item["reason"] == "sec_xbrl_production_admission_raw_input_not_admitted"
        for item in report["blocked_reasons"]
    )
    assert r"C:\raw\operator\path" not in text
    assert report["public_surface"]["hash_count_state_only"] is True


def test_production_admission_gate_reports_review_ready_but_not_admitted_when_all_gates_are_proven() -> None:
    report = gate.inspect_sec_xbrl_production_admission_gate(
        proof_capability_report=_proof_report(),
        evidence_authority_matrix=_ready_gate("sec_xbrl_multi_filing_evidence_authority_ready", ready_filing_count=3),
        operator_api_gate=_ready_gate("sec_xbrl_operator_api_contract_ready"),
        operator_authority_resolver_gate=_ready_gate("sec_xbrl_operator_authority_resolver_gate_ready"),
        operator_ui_gate=_ready_gate("sec_xbrl_operator_ui_controls_ready"),
        controlled_value_reveal_gate=_ready_gate("sec_xbrl_controlled_value_reveal_gate_ready"),
        rollback_monitoring_gate=_ready_gate("sec_xbrl_rollback_monitoring_gate_ready"),
        runbook_gate=_ready_gate("sec_xbrl_runbook_gate_ready"),
        validation_gate=_ready_gate("sec_xbrl_targeted_validation_gate_ready"),
    )

    assert report["status"] == gate.STATUS_REVIEW_READY
    assert report["blocked_reasons"] == []
    assert report["summary"]["ready_gate_count"] == len(gate.REQUIRED_GATES)
    assert report["readiness"]["production_admission_review_ready"] is True
    assert report["readiness"]["production_admission_admitted"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["authority_refs"]["proof_source_report_hash"] == _hash("a")
    assert report["authority_refs"]["proof_result_hash"] == _hash("b")


def _proof_report(*, single_transaction: bool = True) -> dict[str, object]:
    return {
        "status": "offline_evidence_proof_capability_ready",
        "authority_refs": {
            "proof_source_report_hash": _hash("a"),
            "proof_result_hash": _hash("b"),
        },
        "readiness": {
            "operator_review_creation_ready": True,
            "production_admission_ready": False,
        },
        "containment": {
            "single_transaction_claimed": single_transaction,
            "existing_materializers_commit_per_stage": not single_transaction,
            "production_database_touched": False,
        },
        "controls": {
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "network_performed": False,
            "production_db_persistence_performed": False,
            "value_reveal_performed": False,
            "api_route_enabled": False,
            "production_readiness_claimed": False,
        },
        "proof_artifact_policy": {
            "hash_count_state_only": True,
            "proof_lineage_hashes_are_raw_evidence_refs": False,
        },
        "redaction_scan": {
            "public_response_raw_accession_found": False,
            "public_response_sec_url_found": False,
            "public_response_local_path_found": False,
            "public_response_raw_value_key_found": False,
            "projection_facts_all_value_redacted": True,
            "statement_rows_all_value_redacted": True,
        },
    }


def _ready_gate(status: str, *, ready_filing_count: int | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "status": status,
        "ready": True,
    }
    if ready_filing_count is not None:
        value["ready_filing_count"] = ready_filing_count
        value["raw_evidence_committed"] = False
    return value


def _hash(char: str) -> str:
    return char * 64
