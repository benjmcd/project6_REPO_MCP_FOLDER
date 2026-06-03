from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_production_release_decision_gate.v1"
STATUS_BLOCKED = "sec_xbrl_production_release_decision_gate_blocked"
STATUS_REVIEW_READY = "sec_xbrl_production_release_decision_gate_review_ready"

REQUIRED_RELEASE_FLAGS = (
    "release_decision_recorded",
    "release_owner_declared",
    "admission_basis_bound",
    "target_release_scope_declared",
    "rollback_plan_bound",
    "monitoring_plan_bound",
    "runbook_acknowledged",
    "targeted_validation_bound",
    "default_off_until_deploy_switch",
    "operator_reauthorization_required",
    "post_release_observation_required",
)

NEGATIVE_RELEASE_FLAGS = (
    "auto_release_enabled",
    "release_executed_by_gate",
    "runtime_default_enabled",
    "api_route_enabled",
    "rendered_ui_enabled",
    "value_reveal_performed",
    "source_acquisition_performed",
    "arelle_invoked",
    "network_performed",
    "production_database_touched",
    "production_readiness_claimed",
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


def inspect_sec_xbrl_production_release_decision_gate(
    *,
    production_admission_gate: Mapping[str, Any] | None = None,
    release_decision_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    admission = _mapping_or_empty(production_admission_gate)
    decision = _mapping_or_empty(release_decision_spec)
    authority_refs = _authority_refs(admission)
    release_flags = {key: decision.get(key) is True for key in REQUIRED_RELEASE_FLAGS}
    negative_flags = {key: decision.get(key) is True for key in NEGATIVE_RELEASE_FLAGS}
    blocked_reasons: list[dict[str, Any]] = []

    readiness = _mapping_or_empty(admission.get("readiness"))
    admission_controls = _mapping_or_empty(admission.get("controls"))
    if admission.get("status") != "layer3_sec_xbrl_production_admission_review_ready":
        blocked_reasons.append(_reason("admission_gate", "production admission gate must be review-ready"))
    if readiness.get("production_admission_review_ready") is not True:
        blocked_reasons.append(_reason("admission_review_ready", "production admission review readiness must be true"))
    if readiness.get("production_admission_admitted") is not False:
        blocked_reasons.append(_reason("admission_not_release", "production admission gate must not execute admission"))
    if "admission_basis_hash" not in authority_refs:
        blocked_reasons.append(_reason("admission_basis_hash", "admission basis hash is missing"))
    if admission_controls.get("production_database_touched") is not False:
        blocked_reasons.append(_reason("admission_production_database_touched", "admission gate must not touch production database state"))
    if admission_controls.get("production_readiness_claimed") is not False:
        blocked_reasons.append(_reason("admission_production_readiness_claimed", "admission gate must not claim production readiness"))

    release_basis_hash = str(decision.get("admission_basis_hash") or "").strip().lower()
    if release_basis_hash and authority_refs.get("admission_basis_hash") != release_basis_hash:
        blocked_reasons.append(
            _reason(
                "release_admission_basis_mismatch",
                "release decision must bind to the current admission basis hash",
            )
        )
    elif not release_basis_hash:
        blocked_reasons.append(_reason("release_admission_basis_hash", "release decision must include admission basis hash"))

    for key, ready in release_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"release decision flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"release decision flag {key} must be false"))
    if _raw_or_local_reference_found(
        {
            "production_admission_gate": production_admission_gate,
            "release_decision_spec": release_decision_spec,
        }
    ):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_production_release_decision_raw_input_not_admitted",
                "message": "Production release decision gate inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "required_flag_count": len(REQUIRED_RELEASE_FLAGS),
        "required_flags_ready_count": sum(1 for value in release_flags.values() if value is True),
        "negative_flag_count": len(NEGATIVE_RELEASE_FLAGS),
        "negative_flags_clear_count": sum(1 for value in negative_flags.values() if value is False),
        "admission_basis_bound": release_basis_hash == authority_refs.get("admission_basis_hash"),
    }
    production_release_decision_basis_hash = stable_hash(
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
        "status": STATUS_REVIEW_READY if ready else STATUS_BLOCKED,
        "ready": ready,
        "blocked_reasons": blocked_reasons,
        "authority_refs": {
            **authority_refs,
            "production_release_decision_basis_hash": production_release_decision_basis_hash,
        },
        "summary": summary,
        "readiness": {
            "production_release_decision_review_ready": ready,
            "production_release_executed": False,
            "production_release_blocked": not ready,
        },
        "controls": {
            "validate_only": True,
            "release_executed_by_gate": False,
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
            "raw_values_returned": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
            "release_switch_exposed": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(admission_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = _mapping_or_empty(admission_gate.get("authority_refs"))
    admitted = {}
    for key in ("proof_source_report_hash", "proof_result_hash", "admission_basis_hash"):
        value = str(refs.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            admitted[key] = value
    return admitted


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_production_release_decision_{gate}_unproven",
        "message": f"Production release decision requires {message}.",
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
        raise ValueError("SEC XBRL production release decision gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
