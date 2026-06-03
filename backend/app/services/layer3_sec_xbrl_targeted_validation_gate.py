from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_targeted_validation_gate.v1"
STATUS_BLOCKED = "sec_xbrl_targeted_validation_gate_blocked"
STATUS_READY = "sec_xbrl_targeted_validation_gate_ready"

REQUIRED_VALIDATIONS = {
    "atomic_offline_orchestrator_tests",
    "offline_evidence_proof_capability_tests",
    "production_admission_gate_tests",
    "production_admission_gate_chain_tests",
    "production_release_decision_gate_tests",
    "controlled_release_activation_gate_tests",
    "controlled_release_status_api_tests",
    "operator_api_contract_gate_tests",
    "operator_review_open_api_route_tests",
    "operator_authority_resolver_gate_tests",
    "operator_ui_controls_gate_tests",
    "controlled_value_reveal_gate_tests",
    "rollback_monitoring_gate_tests",
    "runbook_gate_tests",
    "fizz_10k_atomic_proof_diagnostic",
    "multi_filing_evidence_authority_matrix",
    "api_route_atomic_persistence_tests",
    "ui_api_only_render_tests",
    "controlled_value_reveal_behavior_tests",
    "rollback_monitoring_behavior_tests",
    "runbook_review",
    "full_sec_xbrl_regression",
}

REQUIRED_EVIDENCE_FLAGS = (
    "command_or_review_recorded",
    "passed",
    "hash_count_state_only",
    "isolated_runtime_used",
    "no_raw_values_in_output",
    "no_local_paths_in_output",
    "no_raw_authority_refs_in_output",
    "production_admission_not_claimed",
)

NEGATIVE_EVIDENCE_FLAGS = (
    "raw_values_observed",
    "local_paths_observed",
    "raw_authority_refs_observed",
    "shared_seeded_state_used",
    "network_required",
    "arelle_required",
    "production_database_touched",
    "runtime_default_enabled",
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
    "sidecar",
    "storage_dir",
    "storage_root",
    "ticker",
    "value_store",
}
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
SEC_URL_RE = re.compile(r"https?://(?:www\.)?sec\.gov", re.IGNORECASE)
WINDOWS_ABS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/]")
LOCAL_REF_RE = re.compile(r"(?i)(?:file://|\\\\[^\\/]+[\\/]|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$))")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def inspect_sec_xbrl_targeted_validation_gate(
    *,
    runbook_gate: Mapping[str, Any] | None = None,
    validation_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    runbook = _mapping_or_empty(runbook_gate)
    evidence_by_name = _evidence_map(_mapping_or_empty(validation_evidence).get("validations"))
    authority_refs = _authority_refs(runbook)
    blocked_reasons: list[dict[str, Any]] = []

    if runbook.get("status") != "sec_xbrl_runbook_gate_ready" or runbook.get("ready") is not True:
        blocked_reasons.append(_reason("runbook_gate", "runbook gate must be ready"))
    if "runbook_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("runbook_basis_hash", "runbook basis hash is missing"))

    missing_validations = sorted(REQUIRED_VALIDATIONS - set(evidence_by_name))
    if missing_validations:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_targeted_validation_required_validations_unproven",
                "message": "Targeted validation requires every critical validation lane.",
                "validations": missing_validations,
            }
        )

    evidence_flag_counts = {
        "required_flag_count": len(REQUIRED_EVIDENCE_FLAGS) * len(REQUIRED_VALIDATIONS),
        "required_flags_ready_count": 0,
        "negative_flag_count": len(NEGATIVE_EVIDENCE_FLAGS) * len(REQUIRED_VALIDATIONS),
        "negative_flags_clear_count": 0,
    }
    for validation_name in sorted(REQUIRED_VALIDATIONS & set(evidence_by_name)):
        evidence = evidence_by_name[validation_name]
        for flag in REQUIRED_EVIDENCE_FLAGS:
            if evidence.get(flag) is True:
                evidence_flag_counts["required_flags_ready_count"] += 1
            else:
                blocked_reasons.append(_reason(f"{validation_name}_{flag}", f"validation {validation_name} must prove {flag}"))
        for flag in NEGATIVE_EVIDENCE_FLAGS:
            if evidence.get(flag) is True:
                blocked_reasons.append(_reason(f"{validation_name}_{flag}", f"validation {validation_name} must not have {flag}"))
            else:
                evidence_flag_counts["negative_flags_clear_count"] += 1

    if _raw_or_local_reference_found({"runbook_gate": runbook_gate, "validation_evidence": validation_evidence}):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_targeted_validation_raw_input_not_admitted",
                "message": "Targeted validation gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_validation_count": len(REQUIRED_VALIDATIONS),
        "declared_required_validation_count": len(REQUIRED_VALIDATIONS & set(evidence_by_name)),
        "validations": sorted(evidence_by_name),
        **evidence_flag_counts,
    }
    validation_basis_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "authority_refs": authority_refs,
            "summary": summary,
            "blocked_reason_codes": [item["reason"] for item in blocked_reasons],
        }
    )
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "status": STATUS_READY if ready else STATUS_BLOCKED,
        "ready": ready,
        "blocked_reasons": blocked_reasons,
        "authority_refs": {
            **authority_refs,
            "targeted_validation_basis_hash": validation_basis_hash,
        },
        "summary": summary,
        "controls": {
            "validate_only": True,
            "commands_executed_by_gate": False,
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


def _authority_refs(runbook_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(runbook_gate.get("authority_refs"))
    admitted = {}
    for key in (
        "proof_source_report_hash",
        "proof_result_hash",
        "operator_api_contract_basis_hash",
        "operator_authority_resolver_basis_hash",
        "operator_ui_controls_basis_hash",
        "operator_review_decision_basis_hash",
        "value_reveal_authority_basis_hash",
        "controlled_value_reveal_gate_basis_hash",
        "rollback_monitoring_basis_hash",
        "runbook_basis_hash",
    ):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _evidence_map(value: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}
    output: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("validation") or "").strip()
        if name:
            output[name] = item
    return output


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_targeted_validation_{gate}_unproven",
        "message": f"Targeted validation gate requires {message}.",
    }


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
        raise ValueError("SEC XBRL targeted validation gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
