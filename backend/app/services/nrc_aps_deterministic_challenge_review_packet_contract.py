from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_deterministic_challenge_artifact_contract as challenge_contract


APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_ID = "aps.deterministic_challenge_review_packet.v1"
APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_FAILURE_SCHEMA_ID = "aps.deterministic_challenge_review_packet_failure.v1"
APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_GATE_SCHEMA_ID = "aps.deterministic_challenge_review_packet_gate.v1"
APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION = 1

APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_CONTRACT_ID = "aps_deterministic_challenge_review_packet_projection_v1"
APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_MODE = "disposition_grouping_only"
APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_ID_TOKEN_LEN = challenge_contract.APS_DETERMINISTIC_CHALLENGE_ARTIFACT_ID_TOKEN_LEN

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_NOT_FOUND = "source_challenge_artifact_not_found"
APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_INVALID = "source_challenge_artifact_invalid"
APS_RUNTIME_FAILURE_SOURCE_CHALLENGE_ARTIFACT_CONFLICT = "source_challenge_artifact_conflict"
APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND = "review_packet_not_found"
APS_RUNTIME_FAILURE_ARTIFACT_INVALID = "review_packet_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "review_packet_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "review_packet_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_review_packet_error"

APS_GATE_FAILURE_MISSING_REF = "missing_deterministic_challenge_review_packet_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_deterministic_challenge_review_packet_ref"
APS_GATE_FAILURE_ARTIFACT_SCHEMA = "deterministic_challenge_review_packet_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "deterministic_challenge_review_packet_failure_schema_mismatch"
APS_GATE_FAILURE_PROJECTION_CONTRACT = "projection_contract_mismatch"
APS_GATE_FAILURE_PROJECTION_MODE = "projection_mode_mismatch"
APS_GATE_FAILURE_SOURCE_CHALLENGE_REF = "source_challenge_ref_mismatch"
APS_GATE_FAILURE_SOURCE_CHALLENGE_SUMMARY = "source_challenge_summary_mismatch"
APS_GATE_FAILURE_BLOCKERS = "blockers_mismatch"
APS_GATE_FAILURE_REVIEW_ITEMS = "review_items_mismatch"
APS_GATE_FAILURE_ACKNOWLEDGEMENTS = "acknowledgements_mismatch"
APS_GATE_FAILURE_BUCKET_COUNTS = "bucket_counts_mismatch"
APS_GATE_FAILURE_TOTAL_CHALLENGES = "total_challenges_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_DERIVATION_DRIFT = "deterministic_challenge_review_packet_derivation_drift"

APS_BUCKET_BLOCKERS = "blockers"
APS_BUCKET_REVIEW_ITEMS = "review_items"
APS_BUCKET_ACKNOWLEDGEMENTS = "acknowledgements"
APS_BUCKET_NAMES = (
    APS_BUCKET_BLOCKERS,
    APS_BUCKET_REVIEW_ITEMS,
    APS_BUCKET_ACKNOWLEDGEMENTS,
)

_DISPOSITION_TO_BUCKET = {
    challenge_contract.APS_CHALLENGE_DISPOSITION_BLOCK: APS_BUCKET_BLOCKERS,
    challenge_contract.APS_CHALLENGE_DISPOSITION_REVIEW: APS_BUCKET_REVIEW_ITEMS,
    challenge_contract.APS_CHALLENGE_DISPOSITION_ACKNOWLEDGE: APS_BUCKET_ACKNOWLEDGEMENTS,
}


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_deterministic_challenge_review_packet_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("deterministic_challenge_review_packet_checksum", None)
    clean.pop("_deterministic_challenge_review_packet_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_deterministic_challenge_review_packet_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_deterministic_challenge_review_packet_payload(payload))


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_ID_TOKEN_LEN] or "unknown"


def expected_deterministic_challenge_review_packet_file_name(*, scope: str, deterministic_challenge_review_packet_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(deterministic_challenge_review_packet_id)}"
        "_aps_deterministic_challenge_review_packet_v1.json"
    )


def expected_failure_file_name(*, scope: str, deterministic_challenge_review_packet_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(deterministic_challenge_review_packet_id)}"
        "_aps_deterministic_challenge_review_packet_failure_v1.json"
    )


def derive_failure_deterministic_challenge_review_packet_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_FAILURE_SCHEMA_ID,
            APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_deterministic_challenge_review_packet_id(*, source_deterministic_challenge_artifact_id: str) -> str:
    raw = ":".join(
        [
            APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_ID,
            APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_CONTRACT_ID,
            APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_MODE,
            str(source_deterministic_challenge_artifact_id or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    deterministic_challenge_artifact_id = str(payload.get("deterministic_challenge_artifact_id") or "").strip() or None
    deterministic_challenge_artifact_ref = str(payload.get("deterministic_challenge_artifact_ref") or "").strip() or None
    if bool(deterministic_challenge_artifact_id) == bool(deterministic_challenge_artifact_ref):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    return {
        "deterministic_challenge_artifact_id": deterministic_challenge_artifact_id,
        "deterministic_challenge_artifact_ref": deterministic_challenge_artifact_ref,
        "persist_review_packet": bool(payload.get("persist_review_packet", False)),
    }


def projection_identity_payload() -> dict[str, Any]:
    return {
        "projection_contract_id": APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_CONTRACT_ID,
        "projection_mode": APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_PROJECTION_MODE,
    }


def source_deterministic_challenge_artifact_summary_payload(source_payload: dict[str, Any]) -> dict[str, Any]:
    source_insight = dict(source_payload.get("source_deterministic_insight_artifact") or {})
    challenge_counts = dict(source_payload.get("challenge_counts") or {})
    disposition_counts = dict(source_payload.get("disposition_counts") or {})
    return {
        "schema_id": str(source_payload.get("schema_id") or ""),
        "schema_version": int(source_payload.get("schema_version") or 0),
        "deterministic_challenge_artifact_id": str(source_payload.get("deterministic_challenge_artifact_id") or ""),
        "deterministic_challenge_artifact_checksum": str(source_payload.get("deterministic_challenge_artifact_checksum") or ""),
        "deterministic_challenge_artifact_ref": (
            str(source_payload.get("_deterministic_challenge_artifact_ref") or source_payload.get("deterministic_challenge_artifact_ref") or "").strip()
            or None
        ),
        "ruleset_contract_id": str(source_payload.get("ruleset_contract_id") or ""),
        "ruleset_id": str(source_payload.get("ruleset_id") or ""),
        "ruleset_version": int(source_payload.get("ruleset_version") or 0),
        "challenge_mode": str(source_payload.get("challenge_mode") or ""),
        "total_challenges": int(source_payload.get("total_challenges") or 0),
        "challenge_counts": {
            severity: int(challenge_counts.get(severity, 0) or 0)
            for severity in challenge_contract.APS_CHALLENGE_SEVERITIES
        },
        "disposition_counts": {
            disposition: int(disposition_counts.get(disposition, 0) or 0)
            for disposition in challenge_contract.APS_CHALLENGE_DISPOSITIONS
        },
        "source_deterministic_insight_artifact": source_insight,
    }


def _normalize_challenge_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "challenge_id": str(row.get("challenge_id") or ""),
        "check_id": str(row.get("check_id") or ""),
        "check_version": int(row.get("check_version") or 0),
        "category": str(row.get("category") or ""),
        "severity": str(row.get("severity") or ""),
        "disposition": str(row.get("disposition") or ""),
        "matched_finding_count": int(row.get("matched_finding_count") or 0),
        "source_finding_ids": [str(item or "") for item in list(row.get("source_finding_ids") or [])],
        "message": str(row.get("message") or ""),
        "evidence_pointers": [dict(item or {}) for item in list(row.get("evidence_pointers") or []) if isinstance(item, dict)],
    }


def group_challenges_into_buckets(challenges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in APS_BUCKET_NAMES}
    for challenge in challenges:
        disposition = str(challenge.get("disposition") or "")
        bucket_name = _DISPOSITION_TO_BUCKET.get(disposition)
        if bucket_name is not None:
            buckets[bucket_name].append(_normalize_challenge_row(challenge))
    return buckets


def bucket_counts(buckets: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        "blocker_count": len(buckets.get(APS_BUCKET_BLOCKERS) or []),
        "review_item_count": len(buckets.get(APS_BUCKET_REVIEW_ITEMS) or []),
        "acknowledgement_count": len(buckets.get(APS_BUCKET_ACKNOWLEDGEMENTS) or []),
    }


def build_deterministic_challenge_review_packet_payload(
    source_deterministic_challenge_artifact_payload: dict[str, Any],
    *,
    generated_at_utc: str,
) -> dict[str, Any]:
    source_summary = source_deterministic_challenge_artifact_summary_payload(source_deterministic_challenge_artifact_payload)
    challenges = [dict(item or {}) for item in list(source_deterministic_challenge_artifact_payload.get("challenges") or []) if isinstance(item, dict)]
    buckets = group_challenges_into_buckets(challenges)
    counts = bucket_counts(buckets)
    payload: dict[str, Any] = {
        "schema_id": APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_ID,
        "schema_version": APS_DETERMINISTIC_CHALLENGE_REVIEW_PACKET_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        **projection_identity_payload(),
        "source_deterministic_challenge_artifact": source_summary,
    }
    payload["deterministic_challenge_review_packet_id"] = derive_deterministic_challenge_review_packet_id(
        source_deterministic_challenge_artifact_id=str(source_summary.get("deterministic_challenge_artifact_id") or "")
    )
    payload["total_challenges"] = int(source_deterministic_challenge_artifact_payload.get("total_challenges") or 0)
    payload["blocker_count"] = counts["blocker_count"]
    payload["review_item_count"] = counts["review_item_count"]
    payload["acknowledgement_count"] = counts["acknowledgement_count"]
    payload["blockers"] = buckets[APS_BUCKET_BLOCKERS]
    payload["review_items"] = buckets[APS_BUCKET_REVIEW_ITEMS]
    payload["acknowledgements"] = buckets[APS_BUCKET_ACKNOWLEDGEMENTS]
    payload["deterministic_challenge_review_packet_checksum"] = compute_deterministic_challenge_review_packet_checksum(payload)
    return payload
