from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


APS_VALIDATE_ONLY_GATES_SCHEMA_ID = "aps.validate_only_gates.v1"
APS_VALIDATE_ONLY_GATES_FAILURE_SCHEMA_ID = "aps.validate_only_gates_failure.v1"
APS_VALIDATE_ONLY_GATES_GATE_SCHEMA_ID = "aps.validate_only_gates_gate.v1"
APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION = 1

APS_VALIDATE_ONLY_GATES_PROJECTION_CONTRACT_ID = "aps_validate_only_gates_projection_v1"
APS_VALIDATE_ONLY_GATES_PROJECTION_MODE = "review_runtime_gate_reports_only"
APS_VALIDATE_ONLY_GATES_ID_TOKEN_LEN = 24

APS_RUNTIME_FAILURE_INVALID_REQUEST = "invalid_request"
APS_RUNTIME_FAILURE_REVIEW_RUNTIME_NOT_FOUND = "review_runtime_not_found"
APS_RUNTIME_FAILURE_REVIEW_RUNTIME_INVALID = "review_runtime_invalid"
APS_RUNTIME_FAILURE_CONNECTOR_RUN_NOT_FOUND = "connector_run_not_found"
APS_RUNTIME_FAILURE_GATE_RESULTS_MISSING = "gate_results_missing"
APS_RUNTIME_FAILURE_GATE_RESULTS_INVALID = "gate_results_invalid"
APS_RUNTIME_FAILURE_GATE_REPORTS_MISSING = "gate_reports_missing"
APS_RUNTIME_FAILURE_GATE_REPORTS_INVALID = "gate_reports_invalid"
APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH = "gate_reports_mismatch"
APS_RUNTIME_FAILURE_ARTIFACT_NOT_FOUND = "validate_only_gates_not_found"
APS_RUNTIME_FAILURE_ARTIFACT_INVALID = "validate_only_gates_invalid"
APS_RUNTIME_FAILURE_CONFLICT = "validate_only_gates_conflict"
APS_RUNTIME_FAILURE_WRITE_FAILED = "validate_only_gates_write_failed"
APS_RUNTIME_FAILURE_INTERNAL = "internal_validate_only_gates_error"

APS_GATE_FAILURE_MISSING_REF = "missing_validate_only_gates_ref"
APS_GATE_FAILURE_UNRESOLVABLE_REF = "unresolvable_validate_only_gates_ref"
APS_GATE_FAILURE_ARTIFACT_SCHEMA = "validate_only_gates_schema_mismatch"
APS_GATE_FAILURE_FAILURE_SCHEMA = "validate_only_gates_failure_schema_mismatch"
APS_GATE_FAILURE_PROJECTION_CONTRACT = "projection_contract_mismatch"
APS_GATE_FAILURE_PROJECTION_MODE = "projection_mode_mismatch"
APS_GATE_FAILURE_SOURCE_SUMMARY = "source_summary_mismatch"
APS_GATE_FAILURE_SOURCE_GATE_REPORTS = "source_gate_report_refs_mismatch"
APS_GATE_FAILURE_SOURCE_GATE_RESULTS = "source_gate_results_mismatch"
APS_GATE_FAILURE_SOURCE_COUNTS = "source_gate_counts_mismatch"
APS_GATE_FAILURE_REGISTRY_REFS = "validate_only_gates_report_refs_mismatch"
APS_GATE_FAILURE_REGISTRY_SUMMARY = "validate_only_gates_summary_mismatch"
APS_GATE_FAILURE_CHECKSUM = "checksum_mismatch"
APS_GATE_FAILURE_DERIVATION_DRIFT = "validate_only_gates_derivation_drift"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def logical_validate_only_gates_payload(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    clean.pop("validate_only_gates_checksum", None)
    clean.pop("_validate_only_gates_ref", None)
    clean.pop("_persisted", None)
    clean.pop("generated_at_utc", None)
    return clean


def compute_validate_only_gates_checksum(payload: dict[str, Any]) -> str:
    return stable_hash(logical_validate_only_gates_payload(payload))


def safe_path_token(value: str) -> str:
    raw = str(value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", raw)


def artifact_id_token(value: str) -> str:
    token = safe_path_token(value)
    return token[:APS_VALIDATE_ONLY_GATES_ID_TOKEN_LEN] or "unknown"


def derive_validate_only_gates_id(*, owner_run_id: str) -> str:
    raw = ":".join(
        [
            APS_VALIDATE_ONLY_GATES_SCHEMA_ID,
            APS_VALIDATE_ONLY_GATES_PROJECTION_CONTRACT_ID,
            APS_VALIDATE_ONLY_GATES_PROJECTION_MODE,
            str(owner_run_id or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def derive_failure_validate_only_gates_id(*, owner_run_id: str, error_code: str) -> str:
    raw = ":".join(
        [
            APS_VALIDATE_ONLY_GATES_FAILURE_SCHEMA_ID,
            APS_VALIDATE_ONLY_GATES_PROJECTION_CONTRACT_ID,
            str(owner_run_id or ""),
            str(error_code or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def expected_validate_only_gates_file_name(*, scope: str, validate_only_gates_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(validate_only_gates_id)}"
        "_aps_validate_only_gates_v1.json"
    )


def expected_failure_file_name(*, scope: str, validate_only_gates_id: str) -> str:
    return (
        f"{safe_path_token(scope)}_{artifact_id_token(validate_only_gates_id)}"
        "_aps_validate_only_gates_failure_v1.json"
    )


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    owner_run_id = str(payload.get("run_id") or "").strip()
    if not owner_run_id:
        raise ValueError(APS_RUNTIME_FAILURE_INVALID_REQUEST)
    review_root = str(payload.get("review_root") or "").strip() or None
    return {
        "run_id": owner_run_id,
        "review_root": review_root,
        "persist_validate_only_gates": bool(payload.get("persist_validate_only_gates", False)),
    }


def projection_identity_payload() -> dict[str, Any]:
    return {
        "projection_contract_id": APS_VALIDATE_ONLY_GATES_PROJECTION_CONTRACT_ID,
        "projection_mode": APS_VALIDATE_ONLY_GATES_PROJECTION_MODE,
    }


def normalize_gate_results(gate_results: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for gate_name in sorted(gate_results.keys()):
        payload = gate_results.get(gate_name)
        if not isinstance(payload, dict):
            continue
        report_path = str(payload.get("report_path") or "").strip() or None
        normalized[gate_name] = {
            "passed": bool(payload.get("passed", False)),
            "checked_runs": int(payload.get("checked_runs") or 0),
            "report_path": report_path,
            "script": str(payload.get("script") or "").strip() or None,
        }
    return normalized


def source_review_runtime_payload(
    *,
    run_id: str,
    summary_ref: str,
    summary_payload: dict[str, Any],
    gate_report_refs: list[str],
) -> dict[str, Any]:
    return {
        "run_id": str(run_id or "").strip(),
        "summary_ref": str(summary_ref or "").strip(),
        "summary_schema_id": str(summary_payload.get("schema_id") or ""),
        "summary_schema_version": int(summary_payload.get("schema_version") or 0),
        "gate_report_dir_ref": str((Path(summary_ref).resolve().parent / "gate_reports").resolve()),
        "gate_report_refs": [str(item or "").strip() for item in gate_report_refs if str(item or "").strip()],
    }


def build_validate_only_gates_payload(
    *,
    run_id: str,
    summary_ref: str,
    summary_payload: dict[str, Any],
    gate_report_refs: list[str],
    generated_at_utc: str,
) -> dict[str, Any]:
    normalized_gate_results = normalize_gate_results(dict(summary_payload.get("gate_results") or {}))
    gate_total = len(normalized_gate_results)
    gate_passed = sum(1 for item in normalized_gate_results.values() if bool(item.get("passed")))
    payload: dict[str, Any] = {
        "schema_id": APS_VALIDATE_ONLY_GATES_SCHEMA_ID,
        "schema_version": APS_VALIDATE_ONLY_GATES_SCHEMA_VERSION,
        "generated_at_utc": str(generated_at_utc or ""),
        **projection_identity_payload(),
        "validate_only_gates_id": derive_validate_only_gates_id(owner_run_id=str(run_id or "")),
        "owner_run_id": str(run_id or ""),
        "source_review_runtime": source_review_runtime_payload(
            run_id=str(run_id or ""),
            summary_ref=summary_ref,
            summary_payload=summary_payload,
            gate_report_refs=gate_report_refs,
        ),
        "gate_results": normalized_gate_results,
        "gate_result_names": sorted(normalized_gate_results.keys()),
        "gate_report_refs": [str(item or "").strip() for item in gate_report_refs if str(item or "").strip()],
        "gate_total": gate_total,
        "gate_passed": gate_passed,
        "gate_failed": gate_total - gate_passed,
    }
    payload["validate_only_gates_checksum"] = compute_validate_only_gates_checksum(payload)
    return payload
