from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_rollback_monitoring_gate.v1"
STATUS_BLOCKED = "sec_xbrl_rollback_monitoring_gate_blocked"
STATUS_READY = "sec_xbrl_rollback_monitoring_gate_ready"

REQUIRED_ROLLBACK_FLAGS = (
    "atomic_projection_fault_rolls_back",
    "atomic_statement_packet_fault_rolls_back",
    "atomic_workflow_fault_rolls_back",
    "api_auth_binding_failure_rolls_back",
    "decision_auth_binding_failure_rolls_back",
    "value_reveal_auth_binding_failure_rolls_back",
    "no_partial_projection_rows",
    "no_partial_statement_packet_rows",
    "no_partial_workflow_rows",
    "no_partial_decision_rows",
    "no_partial_reveal_receipts",
)

REQUIRED_MONITORING_EVENTS = {
    "offline_evidence_proof_blocked",
    "atomic_persistence_rollback",
    "redaction_containment_blocked",
    "evidence_authority_gap",
    "operator_decision_recorded",
    "value_reveal_attempt",
    "value_reveal_denied",
    "production_admission_denied",
}

REQUIRED_MONITORING_FLAGS = (
    "events_hash_count_state_only",
    "metrics_hash_count_state_only",
    "alerts_have_runbook_refs",
    "monitoring_default_off_until_configured",
    "no_raw_values_logged",
    "no_local_paths_logged",
    "no_raw_authority_refs_logged",
)

NEGATIVE_MONITORING_FLAGS = (
    "monitoring_started",
    "alerts_enabled",
    "raw_values_logged",
    "raw_authority_refs_logged",
    "local_paths_logged",
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


def inspect_sec_xbrl_rollback_monitoring_gate(
    *,
    controlled_value_reveal_gate: Mapping[str, Any] | None = None,
    rollback_evidence: Mapping[str, Any] | None = None,
    monitoring_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reveal_gate = _mapping_or_empty(controlled_value_reveal_gate)
    rollback = _mapping_or_empty(rollback_evidence)
    monitoring = _mapping_or_empty(monitoring_spec)
    authority_refs = _authority_refs(reveal_gate)
    rollback_flags = {key: rollback.get(key) is True for key in REQUIRED_ROLLBACK_FLAGS}
    monitoring_flags = {key: monitoring.get(key) is True for key in REQUIRED_MONITORING_FLAGS}
    negative_flags = {key: monitoring.get(key) is True for key in NEGATIVE_MONITORING_FLAGS}
    declared_events = _public_text_set(monitoring.get("events"))
    blocked_reasons: list[dict[str, Any]] = []

    if reveal_gate.get("status") != "sec_xbrl_controlled_value_reveal_gate_ready" or reveal_gate.get("ready") is not True:
        blocked_reasons.append(_reason("controlled_value_reveal_gate", "controlled value reveal gate must be ready"))
    if "controlled_value_reveal_gate_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("controlled_value_reveal_gate_basis_hash", "controlled value reveal gate basis hash is missing"))
    for key, ready in rollback_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"rollback evidence flag {key} must be true"))
    for key, ready in monitoring_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"monitoring flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"monitoring flag {key} must be false"))
    missing_events = sorted(REQUIRED_MONITORING_EVENTS - declared_events)
    if missing_events:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_rollback_monitoring_events_unproven",
                "message": "Rollback monitoring requires all critical SEC XBRL event types.",
                "events": missing_events,
            }
        )
    if _raw_or_local_reference_found(
        {
            "controlled_value_reveal_gate": controlled_value_reveal_gate,
            "rollback_evidence": rollback_evidence,
            "monitoring_spec": monitoring_spec,
        }
    ):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_rollback_monitoring_raw_input_not_admitted",
                "message": "Rollback monitoring gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "rollback_flag_count": len(REQUIRED_ROLLBACK_FLAGS),
        "rollback_flags_ready_count": sum(1 for value in rollback_flags.values() if value is True),
        "monitoring_flag_count": len(REQUIRED_MONITORING_FLAGS),
        "monitoring_flags_ready_count": sum(1 for value in monitoring_flags.values() if value is True),
        "required_event_count": len(REQUIRED_MONITORING_EVENTS),
        "declared_required_event_count": len(declared_events & REQUIRED_MONITORING_EVENTS),
        "events": sorted(declared_events),
    }
    rollback_monitoring_basis_hash = stable_hash(
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
            "rollback_monitoring_basis_hash": rollback_monitoring_basis_hash,
        },
        "summary": summary,
        "controls": {
            "validate_only": True,
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
            "raw_values_logged": False,
            "raw_authority_refs_logged": False,
            "local_paths_logged": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(reveal_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(reveal_gate.get("authority_refs"))
    admitted = {}
    for key in (
        "proof_source_report_hash",
        "proof_result_hash",
        "operator_api_contract_basis_hash",
        "operator_ui_controls_basis_hash",
        "operator_review_decision_basis_hash",
        "value_reveal_authority_basis_hash",
        "controlled_value_reveal_gate_basis_hash",
    ):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_rollback_monitoring_{gate}_unproven",
        "message": f"Rollback monitoring requires {message}.",
    }


def _public_text_set(value: Any) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return set()
    output = set()
    for item in value:
        text = str(item or "").strip()
        if text:
            output.add(text)
    return output


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
        raise ValueError("SEC XBRL rollback monitoring gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
