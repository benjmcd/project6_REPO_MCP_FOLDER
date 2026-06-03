from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_controlled_release_activation_gate.v1"
STATUS_BLOCKED = "sec_xbrl_controlled_release_activation_gate_blocked"
STATUS_PREFLIGHT_READY = "sec_xbrl_controlled_release_activation_gate_preflight_ready"

REQUIRED_ACTIVATION_FLAGS = (
    "release_decision_basis_bound",
    "deploy_switch_owner_declared",
    "activation_window_declared",
    "feature_flag_plan_declared",
    "runtime_default_toggle_plan_declared",
    "api_route_enablement_plan_declared",
    "rendered_ui_enablement_plan_declared",
    "rollback_switch_declared",
    "monitoring_observation_window_declared",
    "post_activation_validation_declared",
    "emergency_stop_declared",
    "change_record_recorded",
)

NEGATIVE_ACTIVATION_FLAGS = (
    "activation_executed_by_gate",
    "auto_activation_enabled",
    "runtime_default_enabled",
    "api_route_enabled",
    "rendered_ui_enabled",
    "value_reveal_performed",
    "source_acquisition_performed",
    "arelle_invoked",
    "network_performed",
    "production_database_touched",
    "production_readiness_claimed",
    "stale_release_decision_accepted",
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
LOCAL_REF_RE = re.compile(
    r"(?i)(?:file://|\\\\[^\\/]+[\\/]|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$))"
)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def inspect_sec_xbrl_controlled_release_activation_gate(
    *,
    production_release_decision_gate: Mapping[str, Any] | None = None,
    activation_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    release_gate = _mapping_or_empty(production_release_decision_gate)
    activation = _mapping_or_empty(activation_spec)
    authority_refs = _authority_refs(release_gate)
    activation_flags = {key: activation.get(key) is True for key in REQUIRED_ACTIVATION_FLAGS}
    negative_flags = {key: activation.get(key) is True for key in NEGATIVE_ACTIVATION_FLAGS}
    blocked_reasons: list[dict[str, Any]] = []

    readiness = _mapping_or_empty(release_gate.get("readiness"))
    release_controls = _mapping_or_empty(release_gate.get("controls"))
    if release_gate.get("status") != "sec_xbrl_production_release_decision_gate_review_ready":
        blocked_reasons.append(_reason("release_decision_gate", "production release decision gate must be review-ready"))
    if readiness.get("production_release_decision_review_ready") is not True:
        blocked_reasons.append(_reason("release_decision_review_ready", "production release decision review readiness must be true"))
    if readiness.get("production_release_executed") is not False:
        blocked_reasons.append(_reason("release_not_executed", "release decision gate must not execute release"))
    if "production_release_decision_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("release_decision_basis_hash", "production release decision basis hash is missing"))
    if release_controls.get("production_database_touched") is not False:
        blocked_reasons.append(_reason("release_gate_production_database_touched", "release decision gate must not touch production database state"))
    if release_controls.get("production_readiness_claimed") is not False:
        blocked_reasons.append(_reason("release_gate_production_readiness_claimed", "release decision gate must not claim production readiness"))

    requested_basis_hash = str(activation.get("production_release_decision_basis_hash") or "").strip().lower()
    if not requested_basis_hash:
        blocked_reasons.append(_reason("activation_release_decision_basis_hash", "activation preflight must include production release decision basis hash"))
    elif requested_basis_hash != authority_refs.get("production_release_decision_basis_hash"):
        blocked_reasons.append(_reason("activation_release_decision_basis_mismatch", "activation preflight must bind to the current production release decision basis hash"))

    for key, ready in activation_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"activation flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"activation flag {key} must be false"))
    if _raw_or_local_reference_found(
        {
            "production_release_decision_gate": production_release_decision_gate,
            "activation_spec": activation_spec,
        }
    ):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_controlled_release_activation_raw_input_not_admitted",
                "message": "Controlled release activation gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_flag_count": len(REQUIRED_ACTIVATION_FLAGS),
        "required_flags_ready_count": sum(1 for value in activation_flags.values() if value is True),
        "negative_flag_count": len(NEGATIVE_ACTIVATION_FLAGS),
        "negative_flags_clear_count": sum(1 for value in negative_flags.values() if value is False),
        "release_decision_basis_bound": requested_basis_hash == authority_refs.get("production_release_decision_basis_hash"),
    }
    activation_basis_hash = stable_hash(
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
        "status": STATUS_PREFLIGHT_READY if ready else STATUS_BLOCKED,
        "ready": ready,
        "blocked_reasons": blocked_reasons,
        "authority_refs": {
            **authority_refs,
            "controlled_release_activation_basis_hash": activation_basis_hash,
        },
        "summary": summary,
        "readiness": {
            "controlled_release_activation_preflight_ready": ready,
            "controlled_release_activation_executed": False,
            "production_release_executed": False,
            "controlled_release_activation_blocked": not ready,
        },
        "controls": {
            "validate_only": True,
            "activation_executed_by_gate": False,
            "runtime_default_enabled": False,
            "api_route_enabled": False,
            "rendered_ui_enabled": False,
            "value_reveal_performed": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "network_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
        "public_surface": {
            "hash_count_state_only": True,
            "deploy_switch_exposed": False,
            "raw_values_returned": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(release_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(release_gate.get("authority_refs"))
    admitted = {}
    for key in (
        "proof_source_report_hash",
        "proof_result_hash",
        "admission_basis_hash",
        "production_release_decision_basis_hash",
    ):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_controlled_release_activation_{gate}_unproven",
        "message": f"Controlled release activation requires {message}.",
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
        raise ValueError("SEC XBRL controlled release activation gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
