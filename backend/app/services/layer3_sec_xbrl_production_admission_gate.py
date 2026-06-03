from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_production_admission_gate.v1"
STATUS_BLOCKED = "layer3_sec_xbrl_production_admission_blocked"
STATUS_REVIEW_READY = "layer3_sec_xbrl_production_admission_review_ready"

REQUIRED_GATES = (
    "offline_evidence_proof_capability",
    "single_transaction_persistence",
    "redaction_containment",
    "multi_filing_evidence_authority",
    "operator_api_contract",
    "operator_authority_resolver",
    "operator_ui_controls",
    "controlled_value_reveal",
    "rollback_monitoring",
    "runbook",
    "targeted_validation",
)

RAW_VALUE_KEYS = {"_value", "value", "effective_value", "amount", "lexical_value"}
RAW_AUTHORITY_KEYS = {
    "accession",
    "accession_number",
    "cik",
    "company_name",
    "issuer_name",
    "local_path",
    "raw_path",
    "registrant",
    "registrant_name",
    "resolved_fact_id",
    "resolved_fact_ids",
    "sec_url",
    "storage_dir",
    "storage_root",
    "ticker",
}
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
LOCAL_REF_RE = re.compile(r"(?i)(?:file://|\\\\[^\\/]+[\\/]|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$))")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def inspect_sec_xbrl_production_admission_gate(
    *,
    proof_capability_report: Mapping[str, Any] | None = None,
    evidence_authority_matrix: Mapping[str, Any] | None = None,
    operator_api_gate: Mapping[str, Any] | None = None,
    operator_authority_resolver_gate: Mapping[str, Any] | None = None,
    operator_ui_gate: Mapping[str, Any] | None = None,
    controlled_value_reveal_gate: Mapping[str, Any] | None = None,
    rollback_monitoring_gate: Mapping[str, Any] | None = None,
    runbook_gate: Mapping[str, Any] | None = None,
    validation_gate: Mapping[str, Any] | None = None,
    min_ready_filing_count: int = 3,
) -> dict[str, Any]:
    proof = _mapping_or_empty(proof_capability_report)
    gate_inputs = {
        "proof_capability_report": proof_capability_report,
        "evidence_authority_matrix": evidence_authority_matrix,
        "operator_api_gate": operator_api_gate,
        "operator_authority_resolver_gate": operator_authority_resolver_gate,
        "operator_ui_gate": operator_ui_gate,
        "controlled_value_reveal_gate": controlled_value_reveal_gate,
        "rollback_monitoring_gate": rollback_monitoring_gate,
        "runbook_gate": runbook_gate,
        "validation_gate": validation_gate,
    }
    gate_states = {
        "offline_evidence_proof_capability": _proof_capability_ready(proof),
        "single_transaction_persistence": _single_transaction_ready(proof),
        "redaction_containment": _redaction_containment_ready(proof),
        "multi_filing_evidence_authority": _evidence_matrix_ready(
            evidence_authority_matrix,
            min_ready_filing_count=min_ready_filing_count,
        ),
        "operator_api_contract": _external_gate_ready(
            operator_api_gate,
            expected_status="sec_xbrl_operator_api_contract_ready",
        ),
        "operator_authority_resolver": _external_gate_ready(
            operator_authority_resolver_gate,
            expected_status="sec_xbrl_operator_authority_resolver_gate_ready",
        ),
        "operator_ui_controls": _external_gate_ready(
            operator_ui_gate,
            expected_status="sec_xbrl_operator_ui_controls_ready",
        ),
        "controlled_value_reveal": _external_gate_ready(
            controlled_value_reveal_gate,
            expected_status="sec_xbrl_controlled_value_reveal_gate_ready",
        ),
        "rollback_monitoring": _external_gate_ready(
            rollback_monitoring_gate,
            expected_status="sec_xbrl_rollback_monitoring_gate_ready",
        ),
        "runbook": _external_gate_ready(
            runbook_gate,
            expected_status="sec_xbrl_runbook_gate_ready",
        ),
        "targeted_validation": _external_gate_ready(
            validation_gate,
            expected_status="sec_xbrl_targeted_validation_gate_ready",
        ),
    }
    raw_input_detected = _raw_or_local_reference_found(gate_inputs)
    blocked_reasons = _blocked_reasons(gate_states)
    if raw_input_detected:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_production_admission_raw_input_not_admitted",
                "message": "Production admission gate inputs must be redacted hash/count/state evidence only.",
                "gate": "input_containment",
            }
        )
    ready_gate_count = sum(1 for value in gate_states.values() if value is True)
    all_ready = ready_gate_count == len(REQUIRED_GATES) and not raw_input_detected
    gate_summary = {
        "required_gate_count": len(REQUIRED_GATES),
        "ready_gate_count": ready_gate_count,
        "blocked_gate_count": len(REQUIRED_GATES) - ready_gate_count + (1 if raw_input_detected else 0),
        "min_ready_filing_count": _positive_int(min_ready_filing_count, "min_ready_filing_count"),
        "gates": dict(gate_states),
    }
    authority_refs = _proof_authority_refs(proof)
    admission_basis_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "gate_summary": gate_summary,
            "blocked_reason_codes": [item["reason"] for item in blocked_reasons],
            "authority_refs": authority_refs,
        }
    )
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "status": STATUS_REVIEW_READY if all_ready else STATUS_BLOCKED,
        "blocked_reasons": blocked_reasons,
        "authority_refs": {
            **authority_refs,
            "admission_basis_hash": admission_basis_hash,
        },
        "summary": gate_summary,
        "readiness": {
            "production_admission_review_ready": all_ready,
            "production_admission_admitted": False,
            "production_admission_blocked": not all_ready,
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
        "public_surface": {
            "hash_count_state_only": True,
            "raw_values_returned": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _proof_capability_ready(report: Mapping[str, Any]) -> bool:
    return (
        report.get("status") == "offline_evidence_proof_capability_ready"
        and _mapping_or_empty(report.get("readiness")).get("operator_review_creation_ready") is True
        and _nonproduction_controls_preserved(report)
    )


def _single_transaction_ready(report: Mapping[str, Any]) -> bool:
    containment = _mapping_or_empty(report.get("containment"))
    return (
        containment.get("single_transaction_claimed") is True
        and containment.get("existing_materializers_commit_per_stage") is False
        and containment.get("production_database_touched") is False
    )


def _redaction_containment_ready(report: Mapping[str, Any]) -> bool:
    redaction_scan = _mapping_or_empty(report.get("redaction_scan"))
    policy = _mapping_or_empty(report.get("proof_artifact_policy"))
    return (
        redaction_scan.get("public_response_raw_accession_found") is False
        and redaction_scan.get("public_response_sec_url_found") is False
        and redaction_scan.get("public_response_local_path_found") is False
        and redaction_scan.get("public_response_raw_value_key_found") is False
        and redaction_scan.get("projection_facts_all_value_redacted") is True
        and redaction_scan.get("statement_rows_all_value_redacted") is True
        and policy.get("hash_count_state_only") is True
        and policy.get("proof_lineage_hashes_are_raw_evidence_refs") is False
    )


def _nonproduction_controls_preserved(report: Mapping[str, Any]) -> bool:
    controls = _mapping_or_empty(report.get("controls"))
    readiness = _mapping_or_empty(report.get("readiness"))
    return (
        controls.get("source_acquisition_performed") is False
        and controls.get("arelle_invoked") is False
        and controls.get("network_performed") is False
        and controls.get("production_db_persistence_performed") is False
        and controls.get("value_reveal_performed") is False
        and controls.get("api_route_enabled") is False
        and controls.get("production_readiness_claimed") is False
        and readiness.get("production_admission_ready") is False
    )


def _evidence_matrix_ready(value: Mapping[str, Any] | None, *, min_ready_filing_count: int) -> bool:
    matrix = _mapping_or_empty(value)
    return (
        matrix.get("status") == "sec_xbrl_multi_filing_evidence_authority_ready"
        and matrix.get("ready") is True
        and _non_negative_int(matrix.get("ready_filing_count"), "ready_filing_count") >= min_ready_filing_count
        and matrix.get("raw_evidence_committed") is False
    )


def _external_gate_ready(value: Mapping[str, Any] | None, *, expected_status: str) -> bool:
    gate = _mapping_or_empty(value)
    return gate.get("status") == expected_status and gate.get("ready") is True


def _blocked_reasons(gate_states: Mapping[str, bool]) -> list[dict[str, Any]]:
    reasons = []
    for gate in REQUIRED_GATES:
        if gate_states.get(gate) is True:
            continue
        reasons.append(
            {
                "reason": f"sec_xbrl_production_admission_{gate}_unproven",
                "message": f"Production admission requires proven {gate}.",
                "gate": gate,
            }
        )
    return reasons


def _proof_authority_refs(report: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(report.get("authority_refs"))
    admitted = {}
    for key in ("proof_source_report_hash", "proof_result_hash"):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _raw_or_local_reference_found(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).strip().lower()
            if key_text in RAW_VALUE_KEYS | RAW_AUTHORITY_KEYS and item not in (None, "", [], {}):
                return True
            if _raw_or_local_reference_found(item):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_raw_or_local_reference_found(item) for item in value)
    if isinstance(value, str):
        return bool(
            ACCESSION_RE.search(value)
            or SEC_URL_RE.search(value)
            or WINDOWS_ABS_PATH_RE.search(value)
            or LOCAL_REF_RE.search(value)
        )
    return False


def _reject_response_leaks(value: Any) -> None:
    text = json.dumps(value, sort_keys=True)
    if ACCESSION_RE.search(text) or SEC_URL_RE.search(text) or WINDOWS_ABS_PATH_RE.search(text) or LOCAL_REF_RE.search(text):
        raise ValueError("SEC XBRL production admission gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _positive_int(value: Any, field: str) -> int:
    number = _non_negative_int(value, field)
    if number <= 0:
        return 1
    return number


def _non_negative_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    if number < 0:
        return 0
    return number
