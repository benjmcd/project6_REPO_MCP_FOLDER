from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.layer3_utils import stable_hash


SCHEMA_ID = "layer3.sec_xbrl_multi_filing_evidence_authority_gate.v1"
STATUS_BLOCKED = "sec_xbrl_multi_filing_evidence_authority_blocked"
STATUS_READY = "sec_xbrl_multi_filing_evidence_authority_ready"

REQUIRED_PROOF_FILING_HANDLES = (
    "fizz-10k-proof",
    "fizz-10q-proof",
    "ccj-10k-proof",
)

REQUIRED_AUTHORITY_HASHES = (
    "proof_source_report_hash",
    "proof_result_hash",
    "sidecar_receipt_hash",
    "value_store_hash",
    "companyfacts_payload_hash",
)

REQUIRED_READY_FLAGS = (
    "operator_evidence_files_read",
    "single_transaction_claimed",
    "redaction_containment_passed",
    "hash_count_state_only",
)

NEGATIVE_READY_FLAGS = (
    "raw_evidence_committed",
    "raw_companyfacts_committed",
    "raw_storage_committed",
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
LOCAL_REF_RE = re.compile(
    r"(?i)(?:file://|\\\\[^\\/]+[\\/]|(?:^|[\s\"'=])/(?:workspace|tmp|home|users|var|mnt|opt|private)(?:/|$))"
)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def inspect_sec_xbrl_multi_filing_evidence_authority_gate(
    *,
    filing_evidence: Mapping[str, Any] | None = None,
    min_ready_filing_count: int = 3,
    required_filing_handles: Sequence[str] | None = REQUIRED_PROOF_FILING_HANDLES,
) -> dict[str, Any]:
    evidence = _mapping_or_empty(filing_evidence)
    filings = _filing_map(evidence.get("filings"))
    required_handles = _required_filing_handles(required_filing_handles)
    minimum = max(
        _positive_int(min_ready_filing_count, "min_ready_filing_count"),
        len(required_handles) if required_handles else 1,
    )
    blocked_reasons: list[dict[str, Any]] = []
    ready_filing_handles: list[str] = []
    blocked_filing_handles: list[str] = []
    filing_summaries: list[dict[str, Any]] = []

    if not filings:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_multi_filing_evidence_authority_filings_missing",
                "message": "Multi-filing evidence authority requires at least one redacted filing evidence entry.",
            }
        )

    missing_required_handles = [handle for handle in required_handles if handle not in filings]
    for handle in missing_required_handles:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_multi_filing_evidence_authority_required_filing_missing",
                "message": "Multi-filing evidence authority requires the named S1 proof filing handle.",
                "required_filing_handle": handle,
            }
        )

    for handle in sorted(filings):
        filing = filings[handle]
        filing_reasons = _filing_blocked_reasons(handle, filing)
        authority_hashes = _authority_hashes(filing)
        is_ready = not filing_reasons
        if is_ready:
            ready_filing_handles.append(handle)
        else:
            blocked_filing_handles.append(handle)
            blocked_reasons.extend(filing_reasons)
        filing_summaries.append(
            {
                "filing_handle": handle,
                "ready": is_ready,
                "authority_hash_count": len(authority_hashes),
                "blocked_reason_count": len(filing_reasons),
            }
        )

    if len(ready_filing_handles) < minimum:
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_multi_filing_evidence_authority_ready_count_insufficient",
                "message": "Multi-filing evidence authority requires enough ready filings before production-admission review.",
                "required_ready_filing_count": minimum,
                "actual_ready_filing_count": len(ready_filing_handles),
            }
        )
    ready_required_handles = [handle for handle in required_handles if handle in ready_filing_handles]
    blocked_required_handles = [handle for handle in required_handles if handle in blocked_filing_handles]
    if required_handles and len(ready_required_handles) < len(required_handles):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_multi_filing_evidence_authority_required_scope_incomplete",
                "message": "Multi-filing evidence authority requires every named S1 proof filing to be ready.",
                "required_filing_handles": list(required_handles),
                "ready_required_filing_handles": ready_required_handles,
                "blocked_required_filing_handles": blocked_required_handles,
                "missing_required_filing_handles": missing_required_handles,
            }
        )
    if _raw_or_local_reference_found(filing_evidence):
        blocked_reasons.append(
            {
                "reason": "sec_xbrl_multi_filing_evidence_authority_raw_input_not_admitted",
                "message": "Multi-filing evidence authority inputs must not contain raw values, raw authority references, or local paths.",
            }
        )

    ready = not blocked_reasons
    summary = {
        "filing_count": len(filings),
        "ready_filing_count": len(ready_filing_handles),
        "blocked_filing_count": len(blocked_filing_handles),
        "min_ready_filing_count": minimum,
        "required_filing_handles": list(required_handles),
        "ready_required_filing_handles": ready_required_handles,
        "blocked_required_filing_handles": blocked_required_handles,
        "missing_required_filing_handles": missing_required_handles,
        "ready_filing_handles": ready_filing_handles,
        "blocked_filing_handles": blocked_filing_handles,
        "filings": filing_summaries,
    }
    authority_refs = _matrix_authority_refs(filings)
    evidence_matrix_basis_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "summary": summary,
            "authority_refs": authority_refs,
            "blocked_reason_codes": [item["reason"] for item in blocked_reasons],
            "required_filing_handles": list(required_handles),
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
            "multi_filing_evidence_authority_basis_hash": evidence_matrix_basis_hash,
        },
        "summary": summary,
        "ready_filing_count": len(ready_filing_handles),
        "raw_evidence_committed": False,
        "controls": {
            "validate_only": True,
            "source_acquisition_performed": False,
            "arelle_invoked": False,
            "network_performed": False,
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


def _filing_blocked_reasons(handle: str, filing: Mapping[str, Any]) -> list[dict[str, Any]]:
    reasons = []
    if filing.get("status") != "filing_evidence_authority_ready":
        reasons.append(_reason(handle, "status", "filing evidence authority status must be ready"))
    for key in REQUIRED_AUTHORITY_HASHES:
        value = str(filing.get(key) or "").strip().lower()
        if not HASH_RE.fullmatch(value):
            reasons.append(_reason(handle, key, f"filing must include lowercase 64-character {key}"))
    for key in REQUIRED_READY_FLAGS:
        if filing.get(key) is not True:
            reasons.append(_reason(handle, key, f"filing flag {key} must be true"))
    for key in NEGATIVE_READY_FLAGS:
        if filing.get(key) is True:
            reasons.append(_reason(handle, key, f"filing flag {key} must be false"))
    return reasons


def _reason(handle: str, field: str, message: str) -> dict[str, str]:
    return {
        "reason": f"sec_xbrl_multi_filing_evidence_authority_{field}_unproven",
        "message": f"Multi-filing evidence authority requires {message}.",
        "filing_handle": handle,
    }


def _matrix_authority_refs(filings: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    ready_refs = []
    for handle in sorted(filings):
        filing = filings[handle]
        if _filing_blocked_reasons(handle, filing):
            continue
        ready_refs.append(
            {
                "filing_handle": handle,
                "authority_hashes": _authority_hashes(filing),
            }
        )
    return {
        "ready_filing_authority_inventory_hash": stable_hash(ready_refs),
    }


def _authority_hashes(filing: Mapping[str, Any]) -> dict[str, str]:
    hashes = {}
    for key in REQUIRED_AUTHORITY_HASHES:
        value = str(filing.get(key) or "").strip().lower()
        if HASH_RE.fullmatch(value):
            hashes[key] = value
    return hashes


def _filing_map(value: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return {}
    output: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue
        handle = _public_handle(item.get("filing_handle") or f"filing-{index}")
        if handle:
            output[handle] = item
    return output


def _required_filing_handles(value: Any) -> tuple[str, ...]:
    if value is None:
        return tuple(REQUIRED_PROOF_FILING_HANDLES)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return tuple()
    handles = {_public_handle(item) for item in value}
    return tuple(sorted(handle for handle in handles if handle))


def _public_handle(value: Any) -> str:
    text = str(value or "").strip()
    if not text or _raw_or_local_reference_found(text):
        return ""
    return text


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
        raise ValueError("SEC XBRL multi-filing evidence authority gate leaked raw authority references.")


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 1
    if number <= 0:
        return 1
    return number


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
