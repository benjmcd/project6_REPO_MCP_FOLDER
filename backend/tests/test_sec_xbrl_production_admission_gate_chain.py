from __future__ import annotations

from app.services import layer3_sec_xbrl_controlled_value_reveal_gate as reveal_gate
from app.services import layer3_sec_xbrl_multi_filing_evidence_authority_gate as evidence_gate
from app.services import layer3_sec_xbrl_operator_api_contract_gate as api_gate
from app.services import layer3_sec_xbrl_operator_authority_resolver_gate as resolver_gate
from app.services import layer3_sec_xbrl_operator_ui_controls_gate as ui_gate
from app.services import layer3_sec_xbrl_production_admission_gate as admission_gate
from app.services import layer3_sec_xbrl_rollback_monitoring_gate as monitoring_gate
from app.services import layer3_sec_xbrl_runbook_gate as runbook_gate
from app.services import layer3_sec_xbrl_targeted_validation_gate as validation_gate


def test_production_admission_chain_blocks_when_multi_filing_authority_is_insufficient() -> None:
    proof = _proof_report()
    evidence = evidence_gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                _ready_filing("fizz-10k-proof"),
                _blocked_filing("fizz-10q-authority-gap"),
                _blocked_filing("ccj-authority-gap"),
            ]
        }
    )
    api = _api_contract_gate(proof)
    resolver = _resolver_gate(api, evidence)
    ui = _ui_controls_gate(api)
    reveal = _controlled_reveal_gate(ui)
    monitoring = _rollback_monitoring_gate(reveal)
    runbook = _runbook_gate(monitoring)
    validation = _targeted_validation_gate(runbook)

    report = admission_gate.inspect_sec_xbrl_production_admission_gate(
        proof_capability_report=proof,
        evidence_authority_matrix=evidence,
        operator_api_gate=api,
        operator_authority_resolver_gate=resolver,
        operator_ui_gate=ui,
        controlled_value_reveal_gate=reveal,
        rollback_monitoring_gate=monitoring,
        runbook_gate=runbook,
        validation_gate=validation,
    )

    assert evidence["status"] == evidence_gate.STATUS_BLOCKED
    assert evidence["ready_filing_count"] == 1
    assert report["status"] == admission_gate.STATUS_BLOCKED
    assert report["readiness"]["production_admission_review_ready"] is False
    assert report["readiness"]["production_admission_admitted"] is False
    assert report["summary"]["gates"]["multi_filing_evidence_authority"] is False
    assert report["summary"]["gates"]["operator_authority_resolver"] is False
    assert any(
        item["reason"] == "sec_xbrl_production_admission_multi_filing_evidence_authority_unproven"
        for item in report["blocked_reasons"]
    )
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def test_production_admission_chain_reports_review_ready_but_never_admitted_when_all_gates_are_ready() -> None:
    proof = _proof_report()
    evidence = evidence_gate.inspect_sec_xbrl_multi_filing_evidence_authority_gate(
        filing_evidence={
            "filings": [
                _ready_filing("fizz-10k-proof"),
                _ready_filing("fizz-10q-proof", char="2"),
                _ready_filing("ccj-10k-proof", char="3"),
            ]
        }
    )
    api = _api_contract_gate(proof)
    resolver = _resolver_gate(api, evidence)
    ui = _ui_controls_gate(api)
    reveal = _controlled_reveal_gate(ui)
    monitoring = _rollback_monitoring_gate(reveal)
    runbook = _runbook_gate(monitoring)
    validation = _targeted_validation_gate(runbook)

    report = admission_gate.inspect_sec_xbrl_production_admission_gate(
        proof_capability_report=proof,
        evidence_authority_matrix=evidence,
        operator_api_gate=api,
        operator_authority_resolver_gate=resolver,
        operator_ui_gate=ui,
        controlled_value_reveal_gate=reveal,
        rollback_monitoring_gate=monitoring,
        runbook_gate=runbook,
        validation_gate=validation,
    )

    assert evidence["status"] == evidence_gate.STATUS_READY
    assert evidence["ready_filing_count"] == 3
    assert report["status"] == admission_gate.STATUS_REVIEW_READY
    assert report["blocked_reasons"] == []
    assert all(report["summary"]["gates"].values())
    assert report["readiness"]["production_admission_review_ready"] is True
    assert report["readiness"]["production_admission_admitted"] is False
    assert report["controls"]["runtime_default_enabled"] is False
    assert report["controls"]["api_route_enabled"] is False
    assert report["controls"]["rendered_ui_enabled"] is False
    assert report["controls"]["value_reveal_performed"] is False
    assert report["controls"]["production_database_touched"] is False
    assert report["controls"]["production_readiness_claimed"] is False


def _api_contract_gate(proof: dict[str, object]) -> dict[str, object]:
    contract: dict[str, object] = {
        key: True
        for key in api_gate.REQUIRED_CONTRACT_FLAGS
    }
    contract.update({key: False for key in api_gate.NEGATIVE_CONTRACT_FLAGS})
    contract["admitted_request_fields"] = [
        "client_request_id",
        "open_mode",
        "operator_decision",
        "period_limit",
        "proof_source_report_hash",
        "operator_review_authority_handle",
    ]
    return api_gate.inspect_sec_xbrl_operator_api_contract_gate(
        proof_capability_report=proof,
        contract_spec=contract,
    )


def _resolver_gate(api: dict[str, object], evidence: dict[str, object]) -> dict[str, object]:
    spec: dict[str, object] = {
        key: True
        for key in resolver_gate.REQUIRED_RESOLVER_FLAGS
    }
    spec.update({key: False for key in resolver_gate.NEGATIVE_RESOLVER_FLAGS})
    spec["resolver_authority_handles"] = [
        "fizz-10k-proof",
        "fizz-10q-proof",
        "ccj-10k-proof",
    ]
    return resolver_gate.inspect_sec_xbrl_operator_authority_resolver_gate(
        operator_api_gate=api,
        evidence_authority_matrix=evidence,
        resolver_spec=spec,
    )


def _ui_controls_gate(api: dict[str, object]) -> dict[str, object]:
    spec: dict[str, object] = {
        key: True
        for key in ui_gate.REQUIRED_UI_FLAGS
    }
    spec.update({key: False for key in ui_gate.NEGATIVE_UI_FLAGS})
    spec["blocked_controls"] = sorted(ui_gate.REQUIRED_BLOCKED_CONTROLS)
    return ui_gate.inspect_sec_xbrl_operator_ui_controls_gate(
        operator_api_contract_gate=api,
        ui_control_spec=spec,
    )


def _controlled_reveal_gate(ui: dict[str, object]) -> dict[str, object]:
    contract: dict[str, object] = {
        key: True
        for key in reveal_gate.REQUIRED_REVEAL_FLAGS
    }
    contract.update({key: False for key in reveal_gate.NEGATIVE_REVEAL_FLAGS})
    return reveal_gate.inspect_sec_xbrl_controlled_value_reveal_gate(
        operator_ui_controls_gate=ui,
        operator_review_decision_gate=_decision_gate(),
        reveal_authority_gate=_authority_gate(),
        reveal_contract=contract,
    )


def _rollback_monitoring_gate(reveal: dict[str, object]) -> dict[str, object]:
    monitoring: dict[str, object] = {
        key: True
        for key in monitoring_gate.REQUIRED_MONITORING_FLAGS
    }
    monitoring.update({key: False for key in monitoring_gate.NEGATIVE_MONITORING_FLAGS})
    monitoring["events"] = sorted(monitoring_gate.REQUIRED_MONITORING_EVENTS)
    return monitoring_gate.inspect_sec_xbrl_rollback_monitoring_gate(
        controlled_value_reveal_gate=reveal,
        rollback_evidence={key: True for key in monitoring_gate.REQUIRED_ROLLBACK_FLAGS},
        monitoring_spec=monitoring,
    )


def _runbook_gate(monitoring: dict[str, object]) -> dict[str, object]:
    return runbook_gate.inspect_sec_xbrl_runbook_gate(
        rollback_monitoring_gate=monitoring,
        runbook_spec={
            "runbooks": [
                _runbook(name)
                for name in sorted(runbook_gate.REQUIRED_RUNBOOKS)
            ]
        },
    )


def _targeted_validation_gate(runbook: dict[str, object]) -> dict[str, object]:
    return validation_gate.inspect_sec_xbrl_targeted_validation_gate(
        runbook_gate=runbook,
        validation_evidence={
            "validations": [
                _validation(name)
                for name in sorted(validation_gate.REQUIRED_VALIDATIONS)
            ]
        },
    )


def _proof_report() -> dict[str, object]:
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
            "single_transaction_claimed": True,
            "existing_materializers_commit_per_stage": False,
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


def _runbook(name: str) -> dict[str, object]:
    value: dict[str, object] = {"runbook": name}
    value.update({key: True for key in runbook_gate.REQUIRED_RUNBOOK_FLAGS})
    value.update({key: False for key in runbook_gate.NEGATIVE_RUNBOOK_FLAGS})
    return value


def _validation(name: str) -> dict[str, object]:
    value: dict[str, object] = {"validation": name}
    value.update({key: True for key in validation_gate.REQUIRED_EVIDENCE_FLAGS})
    value.update({key: False for key in validation_gate.NEGATIVE_EVIDENCE_FLAGS})
    return value


def _ready_filing(handle: str, *, char: str = "1") -> dict[str, object]:
    value: dict[str, object] = {
        "filing_handle": handle,
        "status": "filing_evidence_authority_ready",
    }
    for key in evidence_gate.REQUIRED_AUTHORITY_HASHES:
        value[key] = _hash(char)
    value.update({key: True for key in evidence_gate.REQUIRED_READY_FLAGS})
    value.update({key: False for key in evidence_gate.NEGATIVE_READY_FLAGS})
    return value


def _blocked_filing(handle: str) -> dict[str, object]:
    return {
        "filing_handle": handle,
        "status": "filing_evidence_authority_blocked",
        "operator_evidence_files_read": True,
        "raw_evidence_committed": False,
        "raw_companyfacts_committed": False,
        "raw_storage_committed": False,
        "source_acquisition_performed": False,
        "arelle_invoked": False,
        "network_performed": False,
        "value_reveal_performed": False,
        "production_database_touched": False,
        "production_readiness_claimed": False,
    }


def _hash(char: str) -> str:
    return char * 64
