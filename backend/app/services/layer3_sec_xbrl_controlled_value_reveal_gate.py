from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_controlled_value_reveal_gate.v1"
STATUS_BLOCKED = "sec_xbrl_controlled_value_reveal_gate_blocked"
STATUS_READY = "sec_xbrl_controlled_value_reveal_gate_ready"

REQUIRED_REVEAL_FLAGS = (
    "operator_review_decision_required",
    "server_owned_reveal_authority_required",
    "auth_binding_required",
    "operator_reveal_confirmation_required",
    "transient_values_only",
    "audit_receipt_hash_count_only",
    "status_surface_hash_count_only",
    "default_off_without_receipt",
    "identity_like_values_redacted",
    "rollback_on_auth_binding_failure",
    "sidecar_resolved_server_side",
)

NEGATIVE_REVEAL_FLAGS = (
    "raw_values_persisted",
    "raw_values_in_status",
    "raw_sidecar_payload_returned",
    "raw_storage_payload_returned",
    "client_supplied_sidecar_admitted",
    "client_supplied_value_store_admitted",
    "source_acquisition_performed",
    "arelle_invoked",
    "runtime_default_enabled",
    "reveal_performed",
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


def inspect_sec_xbrl_controlled_value_reveal_gate(
    *,
    operator_ui_controls_gate: Mapping[str, Any] | None = None,
    operator_review_decision_gate: Mapping[str, Any] | None = None,
    reveal_authority_gate: Mapping[str, Any] | None = None,
    reveal_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ui_gate = _mapping_or_empty(operator_ui_controls_gate)
    decision_gate = _mapping_or_empty(operator_review_decision_gate)
    authority_gate = _mapping_or_empty(reveal_authority_gate)
    contract = _mapping_or_empty(reveal_contract)
    authority_refs = _authority_refs(ui_gate=ui_gate, decision_gate=decision_gate, authority_gate=authority_gate)
    reveal_flags = {key: contract.get(key) is True for key in REQUIRED_REVEAL_FLAGS}
    negative_flags = {key: contract.get(key) is True for key in NEGATIVE_REVEAL_FLAGS}
    blocked_reasons: list[dict[str, Any]] = []

    if ui_gate.get("status") != "sec_xbrl_operator_ui_controls_ready" or ui_gate.get("ready") is not True:
        blocked_reasons.append(_reason("operator_ui_controls", "operator UI controls gate must be ready"))
    if decision_gate.get("status") != "sec_xbrl_operator_review_decision_gate_ready" or decision_gate.get("ready") is not True:
        blocked_reasons.append(_reason("operator_review_decision", "operator review decision gate must be ready"))
    if authority_gate.get("status") != "sec_xbrl_value_reveal_authority_gate_ready" or authority_gate.get("ready") is not True:
        blocked_reasons.append(_reason("value_reveal_authority", "server-owned value reveal authority gate must be ready"))
    if "operator_ui_controls_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("ui_controls_basis_hash", "operator UI controls basis hash is missing"))
    if "operator_review_decision_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("review_decision_basis_hash", "operator review decision basis hash is missing"))
    if "value_reveal_authority_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("value_reveal_authority_basis_hash", "value reveal authority basis hash is missing"))
    for key, ready in reveal_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"controlled reveal flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"controlled reveal flag {key} must be false"))
    if _raw_or_local_reference_found(
        {
            "operator_ui_controls_gate": operator_ui_controls_gate,
            "operator_review_decision_gate": operator_review_decision_gate,
            "reveal_authority_gate": reveal_authority_gate,
            "reveal_contract": reveal_contract,
        }
    ):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_controlled_value_reveal_gate_raw_input_not_admitted",
                "message": "Controlled value reveal gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_flag_count": len(REQUIRED_REVEAL_FLAGS),
        "required_flags_ready_count": sum(1 for value in reveal_flags.values() if value is True),
        "negative_flag_count": len(NEGATIVE_REVEAL_FLAGS),
        "negative_flags_clear_count": sum(1 for value in negative_flags.values() if value is False),
        "operator_decision_gate_ready": decision_gate.get("ready") is True,
        "authority_gate_ready": authority_gate.get("ready") is True,
    }
    reveal_gate_basis_hash = stable_hash(
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
            "controlled_value_reveal_gate_basis_hash": reveal_gate_basis_hash,
        },
        "summary": summary,
        "controls": {
            "validate_only": True,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "runtime_default_enabled": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
        "public_surface": {
            "transient_values_only": ready,
            "status_hash_count_state_only": True,
            "audit_receipt_hash_count_only": True,
            "raw_values_returned": False,
            "raw_values_persisted": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(
    *,
    ui_gate: Mapping[str, Any],
    decision_gate: Mapping[str, Any],
    authority_gate: Mapping[str, Any],
) -> dict[str, str]:
    admitted = {}
    for refs in (
        _mapping_or_empty(ui_gate.get("authority_refs")),
        _mapping_or_empty(decision_gate.get("authority_refs")),
        _mapping_or_empty(authority_gate.get("authority_refs")),
    ):
        for key in (
            "proof_source_report_hash",
            "proof_result_hash",
            "operator_api_contract_basis_hash",
            "operator_ui_controls_basis_hash",
            "operator_review_decision_basis_hash",
            "value_reveal_authority_basis_hash",
        ):
            value = str(refs.get(key) or "").strip().lower()
            if HASH_RE.fullmatch(value):
                admitted[key] = value
    return admitted


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_controlled_value_reveal_gate_{gate}_unproven",
        "message": f"Controlled value reveal requires {message}.",
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
        raise ValueError("SEC XBRL controlled value reveal gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
