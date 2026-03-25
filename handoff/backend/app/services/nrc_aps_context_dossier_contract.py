from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.services import nrc_aps_context_packet_contract as context_packet_contract


APS_CONTEXT_DOSSIER_SCHEMA_ID = "aps.context_dossier.v1"
APS_CONTEXT_DOSSIER_FAILURE_SCHEMA_ID = "aps.context_dossier_failure.v1"
APS_CONTEXT_DOSSIER_GATE_SCHEMA_ID = "aps.context_dossier_gate.v1"
APS_CONTEXT_DOSSIER_SCHEMA_VERSION = 1

APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID = "aps_context_dossier_manifest_v1"
APS_CONTEXT_DOSSIER_MODE = "manifest_only"
APS_CONTEXT_DOSSIER_MIN_SOURCES = 2
APS_CONTEXT_DOSSIER_MAX_SOURCES = 100
APS_CONTEXT_DOSSIER_ARTIFACT_ID_TOKEN_LEN = context_packet_contract.APS_CONTEXT_PACKET_ARTIFACT_ID_TOKEN_LEN

APS_CONTEXT_DOSSIER_EXPECTED_SOURCE_SCHEMA_ID = context_packet_contract.APS_CONTEXT_PACKET_SCHEMA_ID
APS_CONTEXT_DOSSIER_EXPECTED_SOURCE_SCHEMA_VERSION = context_packet_contract.APS_CONTEXT_PACKET_SCHEMA_VERSION

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_PACKET = "duplicate_source_packet"
APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_PACKETS = "too_few_source_packets"
APS_RUNTIME_FAILURE_TOO_MANY_SOURCE_PACKETS = "too_many_source_packets"
APS_RUNTIME_FAILURE_SOURCE_PACKET_NOT_FOUND = "source_packet_not_found"
APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID = "source_packet_invalid"
APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED = "cross_run_dossier_not_supported_v1"
APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE = "source_packet_incompatible"
APS_RUNTIME_FAILURE_DOSSIER_NOT_FOUND = "context_dossier_not_found"
APS_RUNTIME_FAILURE_DOSSIER_INVALID = "context_dossier_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "context_dossier_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "context_dossier_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_context_dossier_error"

APS_RUNTIME_INCOMPAT_REASON_PROJECTION_CONTRACT = "projection_contract_id_mismatch"
APS_RUNTIME_INCOMPAT_REASON_FACT_GRAMMAR_CONTRACT = "fact_grammar_contract_id_mismatch"
APS_RUNTIME_INCOMPAT_REASON_OBJECTIVE = "objective_mismatch"
APS_RUNTIME_INCOMPAT_REASON_SOURCE_FAMILY = "source_family_mismatch"

APS_GATE_FAILURE_MISSING_REF = "missing_context_dossier_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_context_dossier_ref"
APS_GATE_FAILURE_DOSSIER_SCHEMA = "context_dossier_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "context_dossier_failure_schema_mismatch"
APS_GATE_FAILURE_COMPOSITION_CONTRACT = "composition_contract_mismatch"
APS_GATE_FAILURE_DOSSIER_MODE = "dossier_mode_mismatch"
APS_GATE_FAILURE_SOURCE_PACKET_REF = "source_packet_ref_mismatch"
APS_GATE_FAILURE_SOURCE_PACKET_MISMATCH = "source_packet_mismatch"
APS_GATE_FAILURE_COMPATIBILITY = "source_packet_compatibility_mismatch"
APS_GATE_FAILURE_ORDERED_DIGEST = "ordered_source_packets_sha256_mismatch"
APS_GATE_FAILURE_COUNTERS = "aggregate_counter_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_DERIVATION_DRIFT = "context_dossier_derivation_drift"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_context_dossier_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("context_dossier_checksum", None)
    clean.pop("_context_dossier_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_context_dossier_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_context_dossier_payload(payload))


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_CONTEXT_DOSSIER_ARTIFACT_ID_TOKEN_LEN] or "unknown"


def expected_context_dossier_file_name(*, scope: str, context_dossier_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(context_dossier_id)}_aps_context_dossier_v1.json"


def expected_failure_file_name(*, scope: str, context_dossier_id: str) -> str:
    return f"{safe_path_token(scope)}_{artifact_id_token(context_dossier_id)}_aps_context_dossier_failure_v1.json"


def derive_failure_context_dossier_id(*, source_locator: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_CONTEXT_DOSSIER_FAILURE_SCHEMA_ID,
            APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID,
            str(source_locator or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ordered_source_packets_sha256(source_packets: list[dict[str, Any]]) -> str:
    ordered_rows: list[dict[str, str]] = []
    for item in source_packets:
        row = dict(item or {})
        ordered_rows.append(
            {
                "context_packet_id": str(row.get("context_packet_id") or ""),
                "context_packet_checksum": str(row.get("context_packet_checksum") or ""),
            }
        )
    return stable_hash({"source_packets": ordered_rows})


def derive_context_dossier_id(
    *,
    projection_contract_id: str,
    fact_grammar_contract_id: str,
    objective: str,
    source_family: str,
    ordered_source_packets_sha256_value: str,
) -> str:
    raw = ":".join(
        [
            APS_CONTEXT_DOSSIER_SCHEMA_ID,
            APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID,
            APS_CONTEXT_DOSSIER_MODE,
            str(projection_contract_id or ""),
            str(fact_grammar_contract_id or ""),
            str(objective or ""),
            str(source_family or ""),
            str(ordered_source_packets_sha256_value or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_non_empty_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _as_non_negative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID}:{field_name}")
    if not isinstance(value, int):
        raise ValueError(f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID}:{field_name}")
    if value < 0:
        raise ValueError(f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID}:{field_name}")
    return int(value)


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    context_packet_ids = [str(item).strip() for item in list(payload.get("context_packet_ids") or []) if str(item).strip()]
    context_packet_refs = [str(item).strip() for item in list(payload.get("context_packet_refs") or []) if str(item).strip()]
    if bool(context_packet_ids) == bool(context_packet_refs):
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    source_selectors = context_packet_ids or context_packet_refs
    if len(source_selectors) < APS_CONTEXT_DOSSIER_MIN_SOURCES:
        raise ValueError(APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_PACKETS)
    if len(source_selectors) > APS_CONTEXT_DOSSIER_MAX_SOURCES:
        raise ValueError(APS_RUNTIME_FAILURE_TOO_MANY_SOURCE_PACKETS)
    if len(set(source_selectors)) != len(source_selectors):
        raise ValueError(APS_RUNTIME_FAILURE_DUPLICATE_SOURCE_PACKET)
    return {
        "context_packet_ids": context_packet_ids or None,
        "context_packet_refs": context_packet_refs or None,
        "persist_dossier": bool(payload.get("persist_dossier", False)),
    }


def source_packet_descriptor_payload(
    context_packet_payload: dict[str, Any],
    *,
    packet_ordinal: int,
) -> dict[str, Any]:
    source_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
    return {
        "packet_ordinal": int(packet_ordinal),
        "context_packet_id": str(context_packet_payload.get("context_packet_id") or ""),
        "context_packet_checksum": str(context_packet_payload.get("context_packet_checksum") or ""),
        "context_packet_ref": str(
            context_packet_payload.get("_context_packet_ref") or context_packet_payload.get("context_packet_ref") or ""
        )
        or None,
        "source_family": str(context_packet_payload.get("source_family") or ""),
        "source_id": str(source_descriptor.get("source_id") or ""),
        "source_checksum": str(source_descriptor.get("source_checksum") or ""),
        "owner_run_id": str(source_descriptor.get("owner_run_id") or ""),
        "projection_contract_id": str(context_packet_payload.get("projection_contract_id") or ""),
        "fact_grammar_contract_id": str(context_packet_payload.get("fact_grammar_contract_id") or ""),
        "objective": str(context_packet_payload.get("objective") or ""),
        "total_facts": int(context_packet_payload.get("total_facts") or 0),
        "total_caveats": int(context_packet_payload.get("total_caveats") or 0),
        "total_constraints": int(context_packet_payload.get("total_constraints") or 0),
        "total_unresolved_questions": int(context_packet_payload.get("total_unresolved_questions") or 0),
    }


def _validate_context_packet_payload_shape(context_packet_payload: dict[str, Any]) -> None:
    if str(context_packet_payload.get("schema_id") or "") != APS_CONTEXT_DOSSIER_EXPECTED_SOURCE_SCHEMA_ID:
        raise ValueError(APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID)
    if int(context_packet_payload.get("schema_version") or 0) != APS_CONTEXT_DOSSIER_EXPECTED_SOURCE_SCHEMA_VERSION:
        raise ValueError(APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID)

    required_text_fields = (
        "context_packet_id",
        "context_packet_checksum",
        "projection_contract_id",
        "fact_grammar_contract_id",
        "objective",
        "source_family",
    )
    for field_name in required_text_fields:
        if _as_non_empty_text(context_packet_payload.get(field_name)) is None:
            raise ValueError(APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID)

    source_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
    for field_name in ("source_id", "source_checksum", "owner_run_id"):
        if _as_non_empty_text(source_descriptor.get(field_name)) is None:
            raise ValueError(APS_RUNTIME_FAILURE_SOURCE_PACKET_INVALID)

    _as_non_negative_int(context_packet_payload.get("total_facts"), field_name="total_facts")
    _as_non_negative_int(context_packet_payload.get("total_caveats"), field_name="total_caveats")
    _as_non_negative_int(context_packet_payload.get("total_constraints"), field_name="total_constraints")
    _as_non_negative_int(context_packet_payload.get("total_unresolved_questions"), field_name="total_unresolved_questions")


def validate_source_packet_compatibility(context_packet_payloads: list[dict[str, Any]]) -> dict[str, str]:
    if len(context_packet_payloads) < APS_CONTEXT_DOSSIER_MIN_SOURCES:
        raise ValueError(APS_RUNTIME_FAILURE_TOO_FEW_SOURCE_PACKETS)

    for payload in context_packet_payloads:
        _validate_context_packet_payload_shape(payload)

    first = dict(context_packet_payloads[0] or {})
    first_descriptor = dict(first.get("source_descriptor") or {})
    expected_owner_run_id = str(first_descriptor.get("owner_run_id") or "")
    expected_projection_contract_id = str(first.get("projection_contract_id") or "")
    expected_fact_grammar_contract_id = str(first.get("fact_grammar_contract_id") or "")
    expected_objective = str(first.get("objective") or "")
    expected_source_family = str(first.get("source_family") or "")

    for context_packet_payload in context_packet_payloads[1:]:
        source_descriptor = dict(context_packet_payload.get("source_descriptor") or {})
        owner_run_id = str(source_descriptor.get("owner_run_id") or "")
        projection_contract_id = str(context_packet_payload.get("projection_contract_id") or "")
        fact_grammar_contract_id = str(context_packet_payload.get("fact_grammar_contract_id") or "")
        objective = str(context_packet_payload.get("objective") or "")
        source_family = str(context_packet_payload.get("source_family") or "")

        if owner_run_id != expected_owner_run_id:
            raise ValueError(APS_RUNTIME_FAILURE_CROSS_RUN_UNSUPPORTED)
        if projection_contract_id != expected_projection_contract_id:
            raise ValueError(
                f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE}:{APS_RUNTIME_INCOMPAT_REASON_PROJECTION_CONTRACT}"
            )
        if fact_grammar_contract_id != expected_fact_grammar_contract_id:
            raise ValueError(
                f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE}:{APS_RUNTIME_INCOMPAT_REASON_FACT_GRAMMAR_CONTRACT}"
            )
        if objective != expected_objective:
            raise ValueError(f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE}:{APS_RUNTIME_INCOMPAT_REASON_OBJECTIVE}")
        if source_family != expected_source_family:
            raise ValueError(
                f"{APS_RUNTIME_FAILURE_SOURCE_PACKET_INCOMPATIBLE}:{APS_RUNTIME_INCOMPAT_REASON_SOURCE_FAMILY}"
            )

    return {
        "owner_run_id": expected_owner_run_id,
        "projection_contract_id": expected_projection_contract_id,
        "fact_grammar_contract_id": expected_fact_grammar_contract_id,
        "objective": expected_objective,
        "source_family": expected_source_family,
    }


def build_context_dossier_payload(
    context_packet_payloads: list[dict[str, Any]],
    *,
    generated_at_utc: str,
) -> dict[str, Any]:
    compatibility = validate_source_packet_compatibility(context_packet_payloads)
    source_packets = [
        source_packet_descriptor_payload(context_packet_payload, packet_ordinal=index)
        for index, context_packet_payload in enumerate(context_packet_payloads, start=1)
    ]
    ordered_digest = ordered_source_packets_sha256(source_packets)
    payload = {
        "schema_id": APS_CONTEXT_DOSSIER_SCHEMA_ID,
        "schema_version": APS_CONTEXT_DOSSIER_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        "composition_contract_id": APS_CONTEXT_DOSSIER_COMPOSITION_CONTRACT_ID,
        "dossier_mode": APS_CONTEXT_DOSSIER_MODE,
        "owner_run_id": str(compatibility.get("owner_run_id") or ""),
        "projection_contract_id": str(compatibility.get("projection_contract_id") or ""),
        "fact_grammar_contract_id": str(compatibility.get("fact_grammar_contract_id") or ""),
        "objective": str(compatibility.get("objective") or ""),
        "source_family": str(compatibility.get("source_family") or ""),
        "source_packet_count": len(source_packets),
        "ordered_source_packets_sha256": ordered_digest,
        "total_facts": sum(int(item.get("total_facts") or 0) for item in source_packets),
        "total_caveats": sum(int(item.get("total_caveats") or 0) for item in source_packets),
        "total_constraints": sum(int(item.get("total_constraints") or 0) for item in source_packets),
        "total_unresolved_questions": sum(int(item.get("total_unresolved_questions") or 0) for item in source_packets),
        "source_packets": source_packets,
    }
    payload["context_dossier_id"] = derive_context_dossier_id(
        projection_contract_id=str(payload.get("projection_contract_id") or ""),
        fact_grammar_contract_id=str(payload.get("fact_grammar_contract_id") or ""),
        objective=str(payload.get("objective") or ""),
        source_family=str(payload.get("source_family") or ""),
        ordered_source_packets_sha256_value=ordered_digest,
    )
    payload["context_dossier_checksum"] = compute_context_dossier_checksum(payload)
    return payload
