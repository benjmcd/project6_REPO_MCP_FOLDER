from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_operator_api_contract_gate.v1"
STATUS_BLOCKED = "sec_xbrl_operator_api_contract_blocked"
STATUS_READY = "sec_xbrl_operator_api_contract_ready"

REQUIRED_CONTRACT_FLAGS = (
    "workflow_open_route_declared",
    "workflow_open_route_default_disabled",
    "server_owned_authority_handles_only",
    "server_owned_authority_resolver_required",
    "atomic_service_required",
    "auth_binding_required",
    "caller_owned_commit_boundary_required",
    "idempotency_required",
    "rollback_on_binding_failure_required",
    "status_surface_hash_count_state_only",
)

NEGATIVE_CONTRACT_FLAGS = (
    "raw_operator_paths_admitted",
    "raw_companyfacts_payload_admitted",
    "raw_storage_payload_admitted",
    "raw_values_returned",
    "client_side_authority_reconstruction_admitted",
    "source_acquisition_admitted",
    "arelle_invocation_admitted",
    "value_reveal_admitted",
)

ADMITTED_REQUEST_FIELDS = {
    "client_request_id",
    "open_mode",
    "operator_decision",
    "period_limit",
    "proof_source_report_hash",
    "operator_review_authority_handle",
}

RAW_VALUE_KEYS = {"_value", "value", "effective_value", "amount", "lexical_value"}
RAW_AUTHORITY_KEYS = {
    "accession",
    "accession_number",
    "cik",
    "company_name",
    "companyfacts",
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


def inspect_sec_xbrl_operator_api_contract_gate(
    *,
    proof_capability_report: Mapping[str, Any] | None = None,
    contract_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    proof = _mapping_or_empty(proof_capability_report)
    contract = _mapping_or_empty(contract_spec)
    authority_refs = _proof_authority_refs(proof)
    contract_flags = {
        key: contract.get(key) is True
        for key in REQUIRED_CONTRACT_FLAGS
    }
    negative_flags = {
        key: contract.get(key) is True
        for key in NEGATIVE_CONTRACT_FLAGS
    }
    admitted_fields = _public_text_set(contract.get("admitted_request_fields"))
    blocked_reasons: list[dict[str, Any]] = []

    if proof.get("status") != "offline_evidence_proof_capability_ready":
        blocked_reasons.append(_reason("proof_capability", "offline evidence proof capability is not ready"))
    if "proof_source_report_hash" not in authority_refs:
        blocked_reasons.append(_reason("proof_source_report_hash", "proof source report hash is missing"))
    if "proof_result_hash" not in authority_refs:
        blocked_reasons.append(_reason("proof_result_hash", "proof result hash is missing"))
    if _mapping_or_empty(proof.get("containment")).get("single_transaction_claimed") is not True:
        blocked_reasons.append(_reason("single_transaction", "atomic persistence proof is required"))
    for key, ready in contract_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"contract flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"contract flag {key} must be false"))
    if not admitted_fields:
        blocked_reasons.append(_reason("admitted_request_fields", "admitted request fields are not declared"))
    elif not admitted_fields.issubset(ADMITTED_REQUEST_FIELDS):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_api_contract_unadmitted_request_fields",
                "message": "Operator API contract declares request fields outside the redacted authority-handle contract.",
                "fields": sorted(admitted_fields - ADMITTED_REQUEST_FIELDS),
            }
        )
    if _raw_or_local_reference_found({"proof": proof_capability_report, "contract": contract_spec}):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_api_contract_raw_input_not_admitted",
                "message": "Operator API contract gate inputs must not contain raw authority, raw values, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_flag_count": len(REQUIRED_CONTRACT_FLAGS),
        "required_flags_ready_count": sum(1 for value in contract_flags.values() if value is True),
        "negative_flag_count": len(NEGATIVE_CONTRACT_FLAGS),
        "negative_flags_clear_count": sum(1 for value in negative_flags.values() if value is False),
        "admitted_request_field_count": len(admitted_fields),
        "admitted_request_fields": sorted(admitted_fields),
    }
    contract_basis_hash = stable_hash(
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
            "operator_api_contract_basis_hash": contract_basis_hash,
        },
        "summary": summary,
        "controls": {
            "validate_only": True,
            "api_route_enabled": False,
            "operator_review_open_api_route_enabled": False,
            "workflow_open_route_contract_declared": contract_flags.get("workflow_open_route_declared") is True,
            "workflow_open_route_default_enabled": False,
            "rendered_ui_enabled": False,
            "runtime_default_enabled": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
        "public_surface": {
            "server_owned_authority_handles_only": ready,
            "workflow_open_route_default_disabled": contract_flags.get("workflow_open_route_default_disabled") is True,
            "caller_supplied_evidence_admitted": False,
            "hash_count_state_only": True,
            "raw_values_returned": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _proof_authority_refs(report: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(report.get("authority_refs"))
    admitted = {}
    for key in ("proof_source_report_hash", "proof_result_hash"):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_operator_api_contract_{gate}_unproven",
        "message": f"Operator API contract requires {message}.",
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
        raise ValueError("SEC XBRL operator API contract gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
