from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_sec_xbrl_multi_filing_evidence_authority_gate import REQUIRED_PROOF_FILING_HANDLES
from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_operator_authority_resolver_gate.v1"
STATUS_BLOCKED = "sec_xbrl_operator_authority_resolver_gate_blocked"
STATUS_READY = "sec_xbrl_operator_authority_resolver_gate_ready"

REQUIRED_RESOLVER_FLAGS = (
    "server_owned_resolver_declared",
    "resolver_registry_default_empty",
    "resolver_uses_multi_filing_authority_inventory",
    "resolver_returns_offline_evidence_mapping",
    "resolver_rejects_unknown_handles",
    "resolver_rejects_source_hash_mismatch",
    "resolver_rejects_raw_paths_urls_accessions",
    "resolver_preserves_authority_hashes",
    "resolver_is_fail_closed",
    "resolver_has_no_network_or_source_acquisition",
)

NEGATIVE_RESOLVER_FLAGS = (
    "client_supplied_evidence_admitted",
    "raw_companyfacts_request_admitted",
    "local_path_resolution_admitted",
    "sec_url_resolution_admitted",
    "accession_resolution_admitted",
    "source_acquisition_performed",
    "arelle_invoked",
    "network_performed",
    "value_reveal_performed",
    "production_database_touched",
    "production_readiness_claimed",
)

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
LOCAL_REF_RE = re.compile(
    r"(?i)(?:file://|\\\\[^\\/]+[\\/]|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$))"
)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def inspect_sec_xbrl_operator_authority_resolver_gate(
    *,
    operator_api_gate: Mapping[str, Any] | None = None,
    evidence_authority_matrix: Mapping[str, Any] | None = None,
    resolver_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    api_gate = _mapping_or_empty(operator_api_gate)
    evidence_gate = _mapping_or_empty(evidence_authority_matrix)
    spec = _mapping_or_empty(resolver_spec)
    required_flags = {key: spec.get(key) is True for key in REQUIRED_RESOLVER_FLAGS}
    negative_flags = {key: spec.get(key) is True for key in NEGATIVE_RESOLVER_FLAGS}
    declared_handles = _public_text_set(spec.get("resolver_authority_handles"))
    ready_handles = set(_ready_handles(evidence_gate))
    required_handles = set(REQUIRED_PROOF_FILING_HANDLES)
    ready_required_handles = set(_ready_required_handles(evidence_gate))
    blocked_reasons: list[dict[str, Any]] = []

    if api_gate.get("status") != "sec_xbrl_operator_api_contract_ready" or api_gate.get("ready") is not True:
        blocked_reasons.append(_reason("operator_api_contract", "operator API contract gate must be ready"))
    if evidence_gate.get("status") != "sec_xbrl_multi_filing_evidence_authority_ready" or evidence_gate.get("ready") is not True:
        blocked_reasons.append(_reason("multi_filing_authority", "multi-filing evidence authority gate must be ready"))
    if evidence_gate.get("raw_evidence_committed") is not False:
        blocked_reasons.append(_reason("raw_evidence_committed", "multi-filing authority must not commit raw evidence"))
    if not required_handles.issubset(ready_required_handles):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_authority_resolver_required_s1_scope_not_ready",
                "message": "Operator authority resolver requires the multi-filing authority gate to prove every named S1 filing handle ready.",
                "required_filing_handles": sorted(required_handles),
                "ready_required_filing_handles": sorted(ready_required_handles),
                "missing_required_filing_handles": sorted(required_handles - ready_required_handles),
            }
        )
    for key, ready in required_flags.items():
        if not ready:
            blocked_reasons.append(_reason(key, f"resolver flag {key} must be true"))
    for key, present in negative_flags.items():
        if present:
            blocked_reasons.append(_reason(key, f"resolver flag {key} must be false"))
    if not declared_handles:
        blocked_reasons.append(_reason("resolver_authority_handles", "resolver authority handles must be declared"))
    if declared_handles and not required_handles.issubset(declared_handles):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_authority_resolver_required_s1_handles_not_declared",
                "message": "Operator authority resolver must declare every named S1 proof filing handle.",
                "required_filing_handles": sorted(required_handles),
                "declared_resolver_handles": sorted(declared_handles),
                "missing_required_filing_handles": sorted(required_handles - declared_handles),
            }
        )
    if declared_handles and not declared_handles.issubset(ready_handles):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_authority_resolver_handles_not_backed_by_multi_filing_authority",
                "message": "Operator authority resolver handles must be backed by ready multi-filing authority handles.",
                "handles": sorted(declared_handles - ready_handles),
            }
        )
    if _raw_or_local_reference_found(
        {
            "operator_api_gate": operator_api_gate,
            "evidence_authority_matrix": evidence_authority_matrix,
            "resolver_spec": resolver_spec,
        }
    ):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_operator_authority_resolver_raw_input_not_admitted",
                "message": "Operator authority resolver gate inputs must not contain raw values, raw authority, or local paths.",
            }
        )

    ready = not blocked_reasons
    authority_refs = _authority_refs(api_gate, evidence_gate)
    summary = {
        "required_flag_count": len(REQUIRED_RESOLVER_FLAGS),
        "required_flags_ready_count": sum(1 for value in required_flags.values() if value is True),
        "negative_flag_count": len(NEGATIVE_RESOLVER_FLAGS),
        "negative_flags_clear_count": sum(1 for value in negative_flags.values() if value is False),
        "declared_resolver_handle_count": len(declared_handles),
        "ready_authority_handle_count": len(ready_handles),
        "required_s1_filing_handles": sorted(required_handles),
        "ready_required_s1_filing_handles": sorted(ready_required_handles),
        "resolver_authority_handles": sorted(declared_handles),
    }
    resolver_basis_hash = stable_hash(
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
            "operator_authority_resolver_basis_hash": resolver_basis_hash,
        },
        "summary": summary,
        "controls": {
            "validate_only": True,
            "operator_authority_resolver_enabled": False,
            "runtime_default_enabled": False,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "network_performed": False,
            "value_reveal_performed": False,
            "production_database_touched": False,
            "production_readiness_claimed": False,
        },
        "public_surface": {
            "server_owned_authority_handles_only": ready,
            "client_supplied_evidence_admitted": False,
            "hash_count_state_only": True,
            "raw_values_returned": False,
            "raw_authority_refs_returned": False,
            "local_paths_returned": False,
        },
    }
    _reject_response_leaks(response)
    return response


def _authority_refs(api_gate: Mapping[str, Any], evidence_gate: Mapping[str, Any]) -> dict[str, str]:
    refs = {}
    for source in (
        _mapping_or_empty(api_gate.get("authority_refs")),
        _mapping_or_empty(evidence_gate.get("authority_refs")),
    ):
        for key, value in source.items():
            text = str(value or "").strip().lower()
            if HASH_RE.fullmatch(text):
                refs[key] = text
    return refs


def _ready_handles(evidence_gate: Mapping[str, Any]) -> list[str]:
    summary = _mapping_or_empty(evidence_gate.get("summary"))
    return sorted(_public_text_set(summary.get("ready_filing_handles")))


def _ready_required_handles(evidence_gate: Mapping[str, Any]) -> list[str]:
    summary = _mapping_or_empty(evidence_gate.get("summary"))
    return sorted(_public_text_set(summary.get("ready_required_filing_handles")))


def _reason(gate: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_operator_authority_resolver_{gate}_unproven",
        "message": f"Operator authority resolver requires {message}.",
    }


def _public_text_set(value: Any) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return set()
    output = set()
    for item in value:
        text = str(item or "").strip()
        if text and not _raw_or_local_reference_found(text):
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
        raise ValueError("SEC XBRL operator authority resolver gate leaked raw authority references.")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
