from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_operator_ui_controls_gate.v1"
STATUS_BLOCKED = "sec_xbrl_operator_ui_controls_blocked"
STATUS_READY = "sec_xbrl_operator_ui_controls_ready"

REQUIRED_UI_FLAGS = (
    "api_contract_ready_required",
    "api_only_data_flow",
    "server_owned_authority_handles_only",
    "redacted_labels_only",
    "hash_count_state_status_only",
    "operator_decision_controls_separated",
    "value_reveal_controls_hidden",
    "blocked_controls_rendered",
    "accessibility_labels_present",
)

NEGATIVE_UI_FLAGS = (
    "raw_values_rendered",
    "raw_authority_refs_rendered",
    "local_paths_rendered",
    "client_side_authority_reconstruction",
    "source_acquisition_control_enabled",
    "arelle_control_enabled",
    "value_reveal_control_enabled",
    "runtime_default_toggle_enabled",
)

REQUIRED_BLOCKED_CONTROLS = {
    "reveal_values",
    "refresh_from_sec_source",
    "invoke_arelle",
    "change_runtime_default",
    "edit_statement_packet",
}

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


def inspect_sec_xbrl_operator_ui_controls_gate(
    *,
    operator_api_contract_gate: Mapping[str, Any] | None = None,
    ui_control_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    api_gate = _mapping_or_empty(operator_api_contract_gate)
    spec = _mapping_or_empty(ui_control_spec)
    authority_refs = _authority_refs(api_gate)
    ui_flags = {key: spec.get(key) is True for key in REQUIRED_UI_FLAGS}
    negative_flags = {key: spec.get(key) is True for key in NEGATIVE_UI_FLAGS}
    blocked_controls = _public_text_set(spec.get("blocked_controls"))
    blocked_reasons: list[dict[str, Any]] = []

    if api_gate.get("status") != "sec_xbrl_operator_api_contract_ready" or api_gate.get("ready") is not True:
        blocked_reasons.append(_reason("api_contract", "operator API contract gate must be ready"))
    if "operator_api_contract_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("api_contract_basis_hash", "operator API contract basis hash is missing"))
    for key, ready in ui_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"UI flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"UI flag {key} must be false"))
    missing_blocked_controls = sorted(REQUIRED_BLOCKED_CONTROLS - blocked_controls)
    if missing_blocked_controls:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_ui_controls_blocked_controls_unproven",
                "message": "Operator UI must visibly block unsafe controls before UI admission.",
                "controls": missing_blocked_controls,
            }
        )
    if _raw_or_local_reference_found({"api_gate": operator_api_contract_gate, "ui_spec": ui_control_spec}):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_ui_controls_raw_input_not_admitted",
                "message": "Operator UI gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_flag_count": len(REQUIRED_UI_FLAGS),
        "required_flags_ready_count": sum(1 for value in ui_flags.values() if value is True),
        "negative_flag_count": len(NEGATIVE_UI_FLAGS),
        "negative_flags_clear_count": sum(1 for value in negative_flags.values() if value is False),
        "required_blocked_control_count": len(REQUIRED_BLOCKED_CONTROLS),
        "declared_blocked_control_count": len(blocked_controls & REQUIRED_BLOCKED_CONTROLS),
        "blocked_controls": sorted(blocked_controls),
    }
    ui_contract_hash = stable_hash(
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
            "operator_ui_controls_basis_hash": ui_contract_hash,
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
            "api_only_data_flow": ready,
            "server_owned_authority_handles_only": ready,
            "hash_count_state_only": True,
            "raw_values_returned": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(api_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(api_gate.get("authority_refs"))
    admitted = {}
    for key in (
        "proof_source_report_hash",
        "proof_result_hash",
        "operator_api_contract_basis_hash",
    ):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_operator_ui_controls_{gate}_unproven",
        "message": f"Operator UI controls require {message}.",
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
        raise ValueError("SEC XBRL operator UI controls gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
