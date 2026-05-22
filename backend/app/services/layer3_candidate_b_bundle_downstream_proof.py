from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_bundle_bridge


SCHEMA_ID = "layer3.candidate_b_bundle_downstream_proof.v1"
SCHEMA_VERSION = 1
PROOF_MODE = "candidate_b_bundle_downstream_e2e_proof_v1"
OPERATOR_DECISION = "record_candidate_b_bundle_downstream_e2e_proof"
PROOF_STATE = "candidate_b_layer3_downstream_e2e_proven"
PROOF_RECEIPT_PREFIX = "cb-bundle-downstream-proof"

_BUNDLE_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "bridge_mode",
    "candidate_b_bundle_id",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_source_kind",
    "compare_target_set_hash",
    "bundle_file_manifest_hash",
    "bundle_raw_file_manifest_hash",
    "admitted_file_subset_source_hash",
    "admitted_file_subset_hash",
    "governed_retained_artifact_family_hash",
    "redaction_policy_id",
)
PROOF_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "candidate_b_source_kind",
    "candidate_b_bundle_id",
    "bridge_receipt_id",
    "bridge_receipt_hash",
    "coverage_evidence_hash",
    "negative_invariants_hash",
    "operator_confirmation",
)
REQUIRED_COVERAGE = frozenset(
    {
        "source_directory_scan",
        "material_preview",
        "gate_b",
        "hybrid_qualitative_analysis",
        "package_commit",
        "package_review_submit",
        "handoff_export_prepare",
        "external_export_download_prepare",
        "same_origin_delivery_status",
        "same_origin_delivery",
        "provider_private_prepare",
        "provider_private_status",
        "provider_private_use",
        "provider_private_revoke",
        "internal_webhook_dispatch",
        "internal_webhook_status",
        "session_status_projection",
    }
)
_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "glob",
    "recursive",
    "file",
    "files",
    "file_bytes",
    "visual_lane_mode",
    "document_processing_engine",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
    "candidate_b_default_promotion_enabled",
    "runtime_database_path",
    "runtime_storage_dir",
    "database_path",
    "storage_dir",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
}
_FORBIDDEN_NESTED_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "file",
    "files",
    "file_bytes",
    "raw_local_path",
    "raw_path",
    "absolute_path",
    "provider_private_url",
    "provider_private_signed_url_token",
    "provider_private_token",
    "provider_public_url",
    "authorization",
    "credentials",
}


class CandidateBBundleDownstreamProofError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-bundle-downstream-proof-error",
            "server_time": _server_time(),
            "mode": PROOF_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_bundle_downstream_proof(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "proof_mode")
    if mode != PROOF_MODE:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_mode_not_admitted",
            "Only the Candidate B bundle downstream proof mode is admitted.",
            details={"expected_proof_mode": PROOF_MODE, "received_proof_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_operator_decision_not_admitted",
            "The operator decision does not match the admitted bundle downstream proof recording.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    if fields.get("operator_confirmation") is not True:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_operator_confirmation_required",
            "operator_confirmation=true is required before recording Candidate B bundle downstream proof.",
            details={"operator_confirmation_required": True},
        )

    candidate_b_bundle_id = _required(fields, "candidate_b_bundle_id")
    receipt_id = _required_storage_id(fields, "bridge_receipt_id", layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX)
    receipt = _read_receipt(receipt_id)
    receipt_hash = _validate_receipt(candidate_b_bundle_id, receipt_id, receipt)
    coverage = _validate_coverage_evidence(fields.get("coverage_evidence"))
    negative_invariants = _negative_invariants()
    negative_invariants_hash = _stable_hash(negative_invariants)
    coverage_hash = _stable_hash(coverage)
    proof_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROOF_MODE,
        "candidate_b_source_kind": "bundle",
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "coverage_evidence_hash": coverage_hash,
        "negative_invariants_hash": negative_invariants_hash,
        "operator_confirmation": True,
    }
    proof_hash = _stable_hash(proof_input)
    proof_receipt_id = f"{PROOF_RECEIPT_PREFIX}-{proof_hash[:24]}"
    proof = {
        **proof_input,
        "proof_hash": proof_hash,
        "proof_receipt_id": proof_receipt_id,
        "proof_receipt_ref": f"candidate-b-bundle-downstream-proof://{receipt_id}/{proof_receipt_id}.json",
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "proven",
        "proof_state": PROOF_STATE,
        "coverage": sorted(coverage),
        "coverage_evidence": {step: coverage[step] for step in sorted(coverage)},
        "raw_local_path_exposed": False,
        "provider_private_token_exposed": False,
        "provider_public_url_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "visual_lane_mode_enabled": False,
        "negative_invariants": negative_invariants,
        "next_allowed_actions": [
            "use this proof as Candidate B bundle downstream proof evidence",
            "run Candidate B default-promotion readiness audit with the matching bundle bridge receipt",
        ],
    }
    _write_proof_receipt(receipt_id=receipt_id, proof_receipt_id=proof_receipt_id, proof=proof)
    return proof


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    nested_blocked = _find_forbidden_nested_fields(fields)
    if blocked or nested_blocked:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_forbidden_request_fields",
            "Bundle downstream proof recording does not admit caller paths, URLs, file bytes, selector overrides, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked, "blocked_nested_fields": nested_blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_required_field_missing",
            "A required Candidate B bundle downstream proof field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    _validate_storage_id(value, prefix=prefix, code="candidate_b_bundle_downstream_proof_storage_id_invalid")
    return value


def _validate_storage_id(value: str, *, prefix: str, code: str) -> None:
    if (
        not value.startswith(f"{prefix}-")
        or "/" in value
        or "\\" in value
        or ".." in value
        or value in {".", ".."}
    ):
        raise CandidateBBundleDownstreamProofError(
            code,
            "Candidate B bundle downstream proof identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _read_receipt(receipt_id: str) -> dict[str, Any]:
    configured = settings.layer3_candidate_b_bundle_bridge_dir
    if not str(configured or "").strip():
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_dir_unset",
            "The configured Candidate B bundle bridge directory is not set.",
        )
    root = Path(str(configured))
    if not root.is_absolute():
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_dir_not_absolute",
            "The configured Candidate B bundle bridge directory must be absolute.",
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_receipt_missing",
            "The selected Candidate B bundle bridge receipt is missing.",
            http_status=404,
            details={"bridge_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_receipt_unreadable",
            "The selected Candidate B bundle bridge receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_receipt_invalid",
            "The selected Candidate B bundle bridge receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _validate_receipt(candidate_b_bundle_id: str, receipt_id: str, receipt: Mapping[str, Any]) -> str:
    mismatches = []
    for field, expected in {
        "schema_id": layer3_candidate_b_bundle_bridge.SCHEMA_ID,
        "bridge_mode": layer3_candidate_b_bundle_bridge.BRIDGE_MODE,
        "candidate_b_source_kind": "bundle",
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "bridge_receipt_id": receipt_id,
    }.items():
        if str(receipt.get(field) or "").strip() != expected:
            mismatches.append({"field": field, "expected": expected, "received": receipt.get(field)})
    if mismatches:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_receipt_mismatch",
            "The selected Candidate B bundle bridge receipt does not match the proof target.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    missing = [key for key in _BUNDLE_HASH_KEYS if key not in receipt]
    if missing:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_receipt_authority_field_missing",
            "The selected Candidate B bundle bridge receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in _BUNDLE_HASH_KEYS})
    if receipt.get("bridge_receipt_hash") != expected_hash:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_bridge_receipt_hash_mismatch",
            "The selected Candidate B bundle bridge receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("bridge_receipt_hash")},
        )
    return expected_hash


def _validate_coverage_evidence(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_coverage_missing",
            "Coverage evidence is required for Candidate B bundle downstream proof.",
        )
    coverage: dict[str, dict[str, Any]] = {}
    missing = []
    for step in sorted(REQUIRED_COVERAGE):
        entry = value.get(step)
        if not isinstance(entry, Mapping) or entry.get("status") != "proven":
            missing.append(step)
            continue
        coverage[step] = {"status": "proven", "evidence_hash": _stable_hash(dict(entry))}
    if missing:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_coverage_incomplete",
            "Candidate B bundle downstream proof does not cover every required Layer 3 step.",
            details={"missing_coverage": missing},
        )
    return coverage


def _find_forbidden_nested_fields(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in _FORBIDDEN_NESTED_FIELDS and nested is not None:
                found.append(path)
            found.extend(_find_forbidden_nested_fields(nested, prefix=path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_find_forbidden_nested_fields(nested, prefix=f"{prefix}[{index}]"))
    return sorted(found)


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_runtime_db_expansion_enabled": False,
        "source_pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _write_proof_receipt(*, receipt_id: str, proof_receipt_id: str, proof: Mapping[str, Any]) -> None:
    root = Path(str(settings.layer3_candidate_b_bundle_bridge_dir)) / receipt_id / "downstream-proof"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{proof_receipt_id}.json"
    body = json.dumps(dict(proof), sort_keys=True, indent=2) + "\n"
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CandidateBBundleDownstreamProofError(
                "candidate_b_bundle_downstream_proof_receipt_unreadable",
                "The existing Candidate B bundle downstream proof receipt could not be read.",
                http_status=409,
                details={"reason": str(exc)},
            ) from exc
        if not isinstance(existing, dict) or existing.get("proof_hash") != proof.get("proof_hash"):
            raise CandidateBBundleDownstreamProofError(
                "candidate_b_bundle_downstream_proof_receipt_conflict",
                "A Candidate B bundle downstream proof receipt already exists with different contents.",
                http_status=409,
                details={"proof_receipt_id": proof_receipt_id},
            )
        return
    try:
        path.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise CandidateBBundleDownstreamProofError(
            "candidate_b_bundle_downstream_proof_receipt_write_failed",
            "The Candidate B bundle downstream proof receipt could not be written.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
