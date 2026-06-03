from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_runbook_gate.v1"
STATUS_BLOCKED = "sec_xbrl_runbook_gate_blocked"
STATUS_READY = "sec_xbrl_runbook_gate_ready"

REQUIRED_RUNBOOKS = {
    "offline_evidence_proof_blocked",
    "atomic_persistence_rollback",
    "redaction_containment_blocked",
    "evidence_authority_gap",
    "operator_authority_resolver_failure",
    "operator_decision_failure",
    "value_reveal_denied",
    "value_reveal_incident",
    "monitoring_alert_response",
    "production_admission_denied",
    "production_release_rollback",
}

REQUIRED_RUNBOOK_FLAGS = (
    "owner_declared",
    "severity_declared",
    "trigger_event_declared",
    "diagnostic_command_declared",
    "rollback_decision_tree_declared",
    "escalation_path_declared",
    "customer_impact_guidance_declared",
    "post_incident_review_declared",
    "hash_count_state_only",
)

NEGATIVE_RUNBOOK_FLAGS = (
    "destructive_command_required",
    "raw_values_required",
    "raw_authority_refs_required",
    "local_paths_required",
    "manual_database_mutation_required",
    "runtime_default_toggle_required",
    "source_acquisition_required",
    "arelle_invocation_required",
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


def inspect_sec_xbrl_runbook_gate(
    *,
    rollback_monitoring_gate: Mapping[str, Any] | None = None,
    runbook_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    monitoring_gate = _mapping_or_empty(rollback_monitoring_gate)
    spec = _mapping_or_empty(runbook_spec)
    authority_refs = _authority_refs(monitoring_gate)
    declared_runbooks = _runbook_map(spec.get("runbooks"))
    blocked_reasons: list[dict[str, Any]] = []

    if monitoring_gate.get("status") != "sec_xbrl_rollback_monitoring_gate_ready" or monitoring_gate.get("ready") is not True:
        blocked_reasons.append(_reason("rollback_monitoring_gate", "rollback monitoring gate must be ready"))
    if "rollback_monitoring_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("rollback_monitoring_basis_hash", "rollback monitoring basis hash is missing"))
    missing_runbooks = sorted(REQUIRED_RUNBOOKS - set(declared_runbooks))
    if missing_runbooks:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_runbook_required_runbooks_unproven",
                "message": "SEC XBRL runbook gate requires every critical operational runbook.",
                "runbooks": missing_runbooks,
            }
        )

    runbook_flag_counts = {
        "required_flag_count": len(REQUIRED_RUNBOOK_FLAGS) * len(REQUIRED_RUNBOOKS),
        "required_flags_ready_count": 0,
        "negative_flag_count": len(NEGATIVE_RUNBOOK_FLAGS) * len(REQUIRED_RUNBOOKS),
        "negative_flags_clear_count": 0,
    }
    for runbook_name in sorted(REQUIRED_RUNBOOKS & set(declared_runbooks)):
        runbook = declared_runbooks[runbook_name]
        for flag in REQUIRED_RUNBOOK_FLAGS:
            if runbook.get(flag) is True:
                runbook_flag_counts["required_flags_ready_count"] += 1
            else:
                blocked_reasons.append(_reason(f"{runbook_name}_{flag}", f"runbook {runbook_name} must declare {flag}"))
        for flag in NEGATIVE_RUNBOOK_FLAGS:
            if runbook.get(flag) is True:
                blocked_reasons.append(_reason(f"{runbook_name}_{flag}", f"runbook {runbook_name} must not require {flag}"))
            else:
                runbook_flag_counts["negative_flags_clear_count"] += 1

    if _raw_or_local_reference_found(
        {
            "rollback_monitoring_gate": rollback_monitoring_gate,
            "runbook_spec": runbook_spec,
        }
    ):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_runbook_raw_input_not_admitted",
                "message": "SEC XBRL runbook gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_runbook_count": len(REQUIRED_RUNBOOKS),
        "declared_required_runbook_count": len(REQUIRED_RUNBOOKS & set(declared_runbooks)),
        "runbooks": sorted(declared_runbooks),
        **runbook_flag_counts,
    }
    runbook_basis_hash = stable_hash(
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
            "runbook_basis_hash": runbook_basis_hash,
        },
        "summary": summary,
        "controls": {
            "validate_only": True,
            "runbooks_executed": False,
            "monitoring_started": False,
            "alerts_enabled": False,
            "runtime_default_enabled": False,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
        "public_surface": {
            "hash_count_state_only": True,
            "raw_values_required": False,
            "raw_authority_refs_required": False,
            "local_paths_required": False,
            "destructive_commands_required": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(monitoring_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(monitoring_gate.get("authority_refs"))
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
    ):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _runbook_map(value: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}
    output: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("runbook") or "").strip()
        if name:
            output[name] = item
    return output


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_runbook_{gate}_unproven",
        "message": f"SEC XBRL runbook gate requires {message}.",
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
        raise ValueError("SEC XBRL runbook gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
