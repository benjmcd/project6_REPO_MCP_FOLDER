from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_default_readiness,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_operator_status,
    layer3_candidate_b_promotion_closure,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_storage_id,
)


SCHEMA_ID = "layer3.candidate_b_default_promotion_final_proof.v1"
SCHEMA_VERSION = 1
PROOF_MODE = "candidate_b_default_promotion_final_proof_v1"
STATUS_MODE = "candidate_b_default_promotion_final_proof_status_v1"
OPERATOR_DECISION = "record_candidate_b_default_promotion_final_proof"
STATUS_OPERATOR_DECISION = "inspect_candidate_b_default_promotion_final_proof_status"
PROOF_RECEIPT_PREFIX = "cb-default-final-proof"
PROOF_STATE = "candidate_b_default_promotion_final_proven"

PROOF_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "readiness_audit_id",
    "readiness_audit_hash",
    "bundle_bridge_receipt_id",
    "runtime_bridge_receipt_id",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_bundle_id",
    "candidate_b_run_id",
    "bundle_bridge_receipt_hash",
    "runtime_bridge_receipt_hash",
    "bundle_downstream_proof_hash",
    "bundle_downstream_proof_receipt_id",
    "runtime_downstream_proof_hash",
    "runtime_downstream_proof_receipt_id",
    "candidate_b_visual_lane_status_hash",
    "operator_status_hash",
    "closure_evidence_hash",
    "final_operator_inspection_hash",
    "default_selector_change_enabled",
    "candidate_b_default_promotion_enabled",
    "rollback_selector",
    "final_operator_inspection_complete",
)
_FORBIDDEN_REQUEST_FIELDS = {
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
    "visual_lane_mode",
    "document_processing_engine",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
    "candidate_b_default_promotion_enabled",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
}
_ALLOWED_ROLE_PREVIEW_FIELDS = frozenset(
    {
        "display_ref",
        "artifact_role",
        "category",
        "extension",
        "sha256",
        "material_text_payload",
    }
)
_FINAL_OPERATOR_INSPECTION_EXPOSURE_FIELDS = (
    "raw_local_path_exposed",
    "raw_url_exposed",
    "artifact_bytes_exposed",
)
_FINAL_OPERATOR_INSPECTION_COUNT_FIELDS = (
    "visual_page_evidence_count",
    "product_inspection_artifact_count",
    "delivery_artifact_count",
)
_EXPECTED_OPERATOR_STATUS_DELIVERY_COVERAGE = sorted(
    layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE
)
_STORED_NEGATIVE_INVARIANTS = {
    "baseline_rollback_preserved": True,
    "candidate_a_semantics_changed": False,
    "provider_object_writes_enabled": False,
    "connector_dispatch_enabled": False,
    "rag_vector_model_runtime_enabled": False,
    "browser_storage_authority_enabled": False,
    "frontend_durable_authority_enabled": False,
}
_OPERATOR_STATUS_NON_EXPOSURE_FIELDS = (
    "raw_local_path_exposed",
    "provider_private_token_exposed",
    "raw_url_exposed",
    "artifact_bytes_exposed",
    "selector_mutation_performed",
)
_OPERATOR_STATUS_NEGATIVE_INVARIANTS = {
    "baseline_default_changed": False,
    "candidate_a_semantics_changed": False,
    "candidate_b_default_promotion_enabled": False,
    "provider_object_writes_enabled": False,
    "connector_dispatch_enabled": False,
    "rag_vector_model_runtime_enabled": False,
    "browser_storage_authority_enabled": False,
    "frontend_durable_authority_enabled": False,
}
_OPERATOR_STATUS_RETAINED_FIELDS = (
    "status",
    "operator_status_hash",
    "operator_status_receipt_id",
    "bundle_bridge_receipt_id",
    "runtime_bridge_receipt_id",
    "runtime_delivery_artifact_authority_hash",
    "runtime_delivery_artifact_coverage_steps",
    "runtime_delivery_artifact_projection_visible",
    "runtime_delivery_artifact_role_previews",
    "runtime_delivery_artifact_roles_bound",
    "raw_local_path_exposed",
    "provider_private_token_exposed",
    "raw_url_exposed",
    "artifact_bytes_exposed",
    "selector_mutation_performed",
)
_READY_AUDIT_REQUIRED_NESTED_FIELDS = (
    ("bridge_receipts", "bundle", "bridge_receipt_id"),
    ("bridge_receipts", "runtime", "bridge_receipt_id"),
    ("authority_hashes", "bundle", "bridge_receipt_hash"),
    ("authority_hashes", "runtime", "bridge_receipt_hash"),
    ("downstream_proofs", "bundle", "proof_hash"),
    ("downstream_proofs", "bundle", "proof_receipt_id"),
    ("downstream_proofs", "runtime", "proof_hash"),
    ("downstream_proofs", "runtime", "proof_receipt_id"),
    ("candidate_b_visual_lane_status_evidence", "status_hash"),
    ("operator_status_evidence", "operator_status_hash"),
    ("closure_evidence", "closure_evidence_hash"),
    ("closure_evidence", "closure_receipt_id"),
    ("candidate_b_final_operator_inspection_evidence", "final_operator_inspection_hash"),
    ("selected_evidence", "baseline_run_id"),
    ("selected_evidence", "candidate_a_run_id"),
    ("selected_evidence", "candidate_b_bundle_id"),
    ("selected_evidence", "candidate_b_run_id"),
)


class CandidateBFinalProofError(Exception):
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
        mode = STATUS_MODE if self.code.startswith("candidate_b_final_proof_status_") else PROOF_MODE
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-default-final-proof-error",
            "server_time": _server_time(),
            "mode": mode,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_default_promotion_final_proof(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "proof_mode") != PROOF_MODE:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_mode_not_admitted",
            "Only the Candidate B default-promotion final proof mode is admitted.",
            details={"expected_proof_mode": PROOF_MODE, "received_proof_mode": fields.get("proof_mode")},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_operator_decision_not_admitted",
            "The operator decision does not match the admitted final proof recording.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    if fields.get("operator_confirmation") is not True:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_operator_confirmation_required",
            "operator_confirmation=true is required before recording Candidate B final proof.",
        )
    audit = fields.get("readiness_audit")
    if not isinstance(audit, Mapping):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_readiness_audit_missing",
            "A ready Candidate B default-promotion readiness audit is required.",
            http_status=409,
        )
    operator_status_evidence = _validate_ready_audit(audit)
    readiness_hash = _compute_readiness_hash(audit)
    if audit.get("readiness_audit_hash") != readiness_hash:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_readiness_hash_mismatch",
            "Candidate B readiness audit hash is stale or invalid.",
            http_status=409,
            details={"expected": readiness_hash, "received": audit.get("readiness_audit_hash")},
        )
    bundle_receipt_id = _bundle_receipt_id(audit)
    runtime_receipt_id = _runtime_receipt_id(audit)
    closure_hash = str(audit.get("closure_evidence", {}).get("closure_evidence_hash") or "").strip()
    _validate_closure_receipt(audit, runtime_receipt_id=runtime_receipt_id, closure_hash=closure_hash)
    selected = audit["selected_evidence"]
    authority = audit["authority_hashes"]
    downstream = audit["downstream_proofs"]
    _validate_bridge_receipt_hash(
        kind="bundle",
        receipt_id=bundle_receipt_id,
        expected_hash=str(authority["bundle"]["bridge_receipt_hash"] or ""),
    )
    _validate_bridge_receipt_hash(
        kind="runtime",
        receipt_id=runtime_receipt_id,
        expected_hash=str(authority["runtime"]["bridge_receipt_hash"] or ""),
    )
    _validate_downstream_proof_receipt(
        kind="bundle",
        proof_receipt_id=str(downstream.get("bundle", {}).get("proof_receipt_id") or "").strip(),
        bridge_receipt_id=bundle_receipt_id,
        expected_hash=str(downstream.get("bundle", {}).get("proof_hash") or "").strip(),
        code_prefix="candidate_b_final_proof",
    )
    _validate_downstream_proof_receipt(
        kind="runtime",
        proof_receipt_id=str(downstream.get("runtime", {}).get("proof_receipt_id") or "").strip(),
        bridge_receipt_id=runtime_receipt_id,
        expected_hash=str(downstream.get("runtime", {}).get("proof_hash") or "").strip(),
        code_prefix="candidate_b_final_proof",
    )
    proof_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROOF_MODE,
        "readiness_audit_id": audit["readiness_audit_id"],
        "readiness_audit_hash": readiness_hash,
        "bundle_bridge_receipt_id": bundle_receipt_id,
        "runtime_bridge_receipt_id": runtime_receipt_id,
        "baseline_run_id": selected["baseline_run_id"],
        "candidate_a_run_id": selected["candidate_a_run_id"],
        "candidate_b_bundle_id": selected["candidate_b_bundle_id"],
        "candidate_b_run_id": selected["candidate_b_run_id"],
        "bundle_bridge_receipt_hash": authority["bundle"]["bridge_receipt_hash"],
        "runtime_bridge_receipt_hash": authority["runtime"]["bridge_receipt_hash"],
        "bundle_downstream_proof_hash": downstream["bundle"]["proof_hash"],
        "bundle_downstream_proof_receipt_id": downstream["bundle"]["proof_receipt_id"],
        "runtime_downstream_proof_hash": downstream["runtime"]["proof_hash"],
        "runtime_downstream_proof_receipt_id": downstream["runtime"]["proof_receipt_id"],
        "candidate_b_visual_lane_status_hash": audit["candidate_b_visual_lane_status_evidence"]["status_hash"],
        "operator_status_hash": operator_status_evidence["operator_status_hash"],
        "closure_evidence_hash": closure_hash,
        "final_operator_inspection_hash": audit["candidate_b_final_operator_inspection_evidence"][
            "final_operator_inspection_hash"
        ],
        "default_selector_change_enabled": True,
        "candidate_b_default_promotion_enabled": True,
        "rollback_selector": "baseline",
        "final_operator_inspection_complete": True,
    }
    proof_hash = _stable_hash(proof_input)
    proof_receipt_id = f"{PROOF_RECEIPT_PREFIX}-{proof_hash[:24]}"
    response = {
        **proof_input,
        "proof_hash": proof_hash,
        "proof_receipt_id": proof_receipt_id,
        "proof_receipt_ref": _proof_receipt_ref(
            runtime_receipt_id=runtime_receipt_id,
            proof_receipt_id=proof_receipt_id,
        ),
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "proven",
        "proof_state": PROOF_STATE,
        "selector_mutation_performed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_private_token_exposed": False,
        "artifact_bytes_exposed": False,
        "candidate_b_operator_status_evidence": operator_status_evidence,
        "candidate_b_final_operator_inspection_evidence": dict(
            audit["candidate_b_final_operator_inspection_evidence"]
        ),
        "negative_invariants": {
            "baseline_rollback_preserved": True,
            "candidate_a_semantics_changed": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "monitor_candidate_b_default_selector",
            "use_explicit_baseline_document_processing_engine_for_rollback",
        ],
    }
    _write_proof_receipt(runtime_receipt_id=runtime_receipt_id, proof_receipt_id=proof_receipt_id, proof=response)
    return response


def candidate_b_default_promotion_final_proof_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "status_mode") != STATUS_MODE:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_mode_not_admitted",
            "Only the Candidate B default-promotion final proof status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": fields.get("status_mode")},
        )
    if _required(fields, "operator_decision") != STATUS_OPERATOR_DECISION:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_operator_decision_not_admitted",
            "The operator decision does not match the admitted final proof status inspection.",
            details={"expected_operator_decision": STATUS_OPERATOR_DECISION},
        )
    runtime_receipt_id = _required_storage_id(
        fields,
        "candidate_b_runtime_bridge_receipt_id",
        layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
        code="candidate_b_final_proof_status_runtime_receipt_id_invalid",
    )
    proof_receipt_id = _required_storage_id(
        fields,
        "proof_receipt_id",
        PROOF_RECEIPT_PREFIX,
        code="candidate_b_final_proof_status_proof_receipt_id_invalid",
    )
    root = _runtime_bridge_root(
        code="candidate_b_final_proof_status_bridge_dir_invalid",
        message="The configured Candidate B runtime bridge directory is missing or not absolute.",
    )
    path = (
        root
        / runtime_receipt_id
        / "default-promotion-final-proof"
        / f"{proof_receipt_id}.json"
    )
    if not path.is_file():
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_receipt_missing",
            "The selected Candidate B final proof receipt is missing.",
            http_status=404,
            details={"proof_receipt_id": proof_receipt_id},
        )
    try:
        proof = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_receipt_unreadable",
            "The selected Candidate B final proof receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(proof, dict):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_receipt_invalid",
            "The selected Candidate B final proof receipt is not a JSON object.",
            http_status=409,
        )
    operator_status_evidence = _validate_stored_final_proof(
        proof,
        proof_receipt_id=proof_receipt_id,
        runtime_receipt_id=runtime_receipt_id,
    )
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "mode": STATUS_MODE,
        "proof_state": proof["proof_state"],
        "proof_hash": proof["proof_hash"],
        "proof_receipt_id": proof_receipt_id,
        "proof_receipt_ref": proof.get("proof_receipt_ref"),
        "readiness_audit_id": proof["readiness_audit_id"],
        "readiness_audit_hash": proof["readiness_audit_hash"],
        "bundle_downstream_proof_receipt_id": proof["bundle_downstream_proof_receipt_id"],
        "runtime_downstream_proof_receipt_id": proof["runtime_downstream_proof_receipt_id"],
        "candidate_b_run_id": proof["candidate_b_run_id"],
        "candidate_b_bundle_id": proof["candidate_b_bundle_id"],
        "candidate_b_default_promotion_enabled": proof["candidate_b_default_promotion_enabled"],
        "default_selector_change_enabled": proof["default_selector_change_enabled"],
        "rollback_selector": proof["rollback_selector"],
        "final_operator_inspection_complete": proof["final_operator_inspection_complete"],
        "selector_mutation_performed": proof["selector_mutation_performed"],
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_private_token_exposed": False,
        "artifact_bytes_exposed": False,
        "operator_status_hash": proof["operator_status_hash"],
        "candidate_b_operator_status_evidence": operator_status_evidence,
        "candidate_b_final_operator_inspection_evidence": dict(
            proof.get("candidate_b_final_operator_inspection_evidence") or {}
        ),
        "negative_invariants": dict(proof.get("negative_invariants") or {}),
        "next_allowed_actions": list(proof.get("next_allowed_actions") or []),
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_forbidden_request_fields",
            "Final proof does not admit caller paths, URLs, selector mutation, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_required_field_missing",
            "A required Candidate B final proof field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str, prefix: str, *, code: str) -> str:
    value = _required(fields, key)
    _validate_storage_id(value, prefix=prefix, code=code)
    return value


def _validate_storage_id(value: str, *, prefix: str, code: str) -> None:
    if not layer3_candidate_b_storage_id.is_storage_id(value, prefix=prefix):
        raise CandidateBFinalProofError(
            code,
            "Candidate B final proof status identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _validate_stored_final_proof(
    proof: Mapping[str, Any],
    *,
    proof_receipt_id: str,
    runtime_receipt_id: str,
) -> dict[str, Any]:
    expected = {
        "schema_id": SCHEMA_ID,
        "mode": PROOF_MODE,
        "status": "proven",
        "proof_state": PROOF_STATE,
        "proof_receipt_id": proof_receipt_id,
        "runtime_bridge_receipt_id": runtime_receipt_id,
        "default_selector_change_enabled": True,
        "candidate_b_default_promotion_enabled": True,
        "rollback_selector": "baseline",
        "final_operator_inspection_complete": True,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": proof.get(field)}
        for field, expected_value in expected.items()
        if proof.get(field) != expected_value
    ]
    if mismatches:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_receipt_mismatch",
            "The selected Candidate B final proof receipt does not match admitted status requirements.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    expected_ref = _proof_receipt_ref(runtime_receipt_id=runtime_receipt_id, proof_receipt_id=proof_receipt_id)
    if proof.get("proof_receipt_ref") != expected_ref:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_proof_receipt_ref_mismatch",
            "The selected Candidate B final proof receipt ref does not match the server-owned proof receipt.",
            http_status=409,
            details={"expected": expected_ref, "received": proof.get("proof_receipt_ref")},
        )
    missing = [key for key in PROOF_HASH_KEYS if key not in proof]
    if missing:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_authority_field_missing",
            "The selected Candidate B final proof receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    proof_hash = _stable_hash({key: proof[key] for key in PROOF_HASH_KEYS})
    if proof.get("proof_hash") != proof_hash:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_hash_mismatch",
            "The selected Candidate B final proof receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": proof_hash, "received": proof.get("proof_hash")},
        )
    _validate_stored_non_exposure_flags(proof)
    _validate_stored_negative_invariants(proof)
    _validate_bridge_receipt_hash(
        kind="bundle",
        receipt_id=str(proof.get("bundle_bridge_receipt_id") or "").strip(),
        expected_hash=str(proof.get("bundle_bridge_receipt_hash") or "").strip(),
    )
    _validate_bridge_receipt_hash(
        kind="runtime",
        receipt_id=str(proof.get("runtime_bridge_receipt_id") or "").strip(),
        expected_hash=str(proof.get("runtime_bridge_receipt_hash") or "").strip(),
    )
    _validate_downstream_proof_receipt(
        kind="bundle",
        proof_receipt_id=str(proof.get("bundle_downstream_proof_receipt_id") or "").strip(),
        bridge_receipt_id=str(proof.get("bundle_bridge_receipt_id") or "").strip(),
        expected_hash=str(proof.get("bundle_downstream_proof_hash") or "").strip(),
        code_prefix="candidate_b_final_proof_status",
    )
    _validate_downstream_proof_receipt(
        kind="runtime",
        proof_receipt_id=str(proof.get("runtime_downstream_proof_receipt_id") or "").strip(),
        bridge_receipt_id=str(proof.get("runtime_bridge_receipt_id") or "").strip(),
        expected_hash=str(proof.get("runtime_downstream_proof_hash") or "").strip(),
        code_prefix="candidate_b_final_proof_status",
    )
    operator_status_evidence = _validate_operator_status_evidence(proof)
    inspection = proof.get("candidate_b_final_operator_inspection_evidence")
    if not isinstance(inspection, Mapping):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_operator_inspection_missing",
            "The selected Candidate B final proof receipt is missing retained artifact inspection evidence.",
            http_status=409,
        )
    _validate_final_operator_inspection_exposure_flags(
        inspection,
        error_code="candidate_b_final_proof_status_operator_inspection_exposure_flag_invalid",
        message="The selected Candidate B final proof receipt has malformed raw-exposure flags.",
        details={},
    )
    if _final_operator_inspection_hash(inspection) != proof.get("final_operator_inspection_hash"):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_operator_inspection_hash_mismatch",
            "The selected Candidate B final proof receipt has stale retained artifact inspection evidence.",
            http_status=409,
            details={
                "expected": proof.get("final_operator_inspection_hash"),
                "received": _final_operator_inspection_hash(inspection),
            },
        )
    _validate_final_operator_inspection_role_previews(inspection)
    return operator_status_evidence


def _validate_ready_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_id": layer3_candidate_b_default_readiness.SCHEMA_ID,
        "mode": layer3_candidate_b_default_readiness.READINESS_MODE,
        "status": "ready",
        "readiness_state": layer3_candidate_b_default_readiness.READY_STATE,
        "default_selector_change_enabled": True,
        "candidate_b_default_promotion_enabled": True,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": value, "received": audit.get(field)}
        for field, value in expected.items()
        if audit.get(field) != value
    ]
    if mismatches:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_readiness_audit_not_ready",
            "Candidate B final proof requires a ready, non-mutating readiness audit.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    if audit.get("blocked_reasons") != []:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_readiness_audit_blocked",
            "Candidate B final proof cannot be recorded from a blocked readiness audit.",
            http_status=409,
            details={"blocked_reasons": audit.get("blocked_reasons")},
        )
    if audit.get("rollback_to_baseline", {}).get("selector") != "baseline":
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_rollback_selector_mismatch",
            "Candidate B final proof requires explicit baseline rollback evidence.",
            http_status=409,
        )
    for field in (
        "bridge_receipts",
        "authority_hashes",
        "downstream_proofs",
        "candidate_b_visual_lane_status_evidence",
        "operator_status_evidence",
        "closure_evidence",
        "candidate_b_final_operator_inspection_evidence",
        "selected_evidence",
    ):
        if not isinstance(audit.get(field), Mapping):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_readiness_audit_field_missing",
                "Candidate B readiness audit is missing required evidence fields.",
                http_status=409,
                details={"field": field},
            )
    _validate_ready_audit_nested_fields(audit)
    _validate_operator_status_delivery_previews(
        audit["operator_status_evidence"],
        error_prefix="candidate_b_final_proof_operator_status",
    )
    _validate_operator_status_delivery_coverage(
        audit["operator_status_evidence"],
        error_prefix="candidate_b_final_proof_operator_status",
    )
    operator_status_evidence = _validate_operator_status_authority(
        audit["operator_status_evidence"],
        expected_hash=str(audit["operator_status_evidence"].get("operator_status_hash") or "").strip(),
        error_prefix="candidate_b_final_proof_operator_status",
    )
    inspection = audit["candidate_b_final_operator_inspection_evidence"]
    if inspection.get("status") != "available":
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_operator_inspection_not_available",
            "Candidate B final proof requires available retained artifact inspection evidence.",
            http_status=409,
        )
    _validate_final_operator_inspection_exposure_flags(
        inspection,
        error_code="candidate_b_final_proof_operator_inspection_exposure_flag_invalid",
        message="Candidate B final operator inspection evidence has malformed raw-exposure flags.",
        details={},
    )
    if str(inspection.get("final_operator_inspection_hash") or "").strip() != _final_operator_inspection_hash(
        inspection
    ):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_operator_inspection_hash_mismatch",
            "Candidate B final operator inspection evidence hash is stale or invalid.",
            http_status=409,
        )
    for source_kind in ("bundle", "runtime"):
        summary = inspection.get(source_kind)
        if not isinstance(summary, Mapping):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_operator_inspection_source_missing",
                "Candidate B final operator inspection evidence is missing a source summary.",
                http_status=409,
                details={"candidate_b_source_kind": source_kind},
            )
        for field in _FINAL_OPERATOR_INSPECTION_COUNT_FIELDS:
            _validate_final_operator_inspection_positive_count(
                summary,
                field=field,
                source_kind=source_kind,
                invalid_code="candidate_b_final_proof_operator_inspection_artifact_count_invalid",
                missing_code="candidate_b_final_proof_operator_inspection_artifact_count_missing",
                message="Candidate B final operator inspection evidence is missing retained visual/product/delivery artifacts.",
            )
        role_previews = summary.get("role_previews")
        if not isinstance(role_previews, Mapping):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_operator_inspection_role_previews_missing",
                "Candidate B final operator inspection evidence is missing redacted retained role previews.",
                http_status=409,
                details={"candidate_b_source_kind": source_kind},
            )
        for role in ("visual_page_evidence", "product_inspection_artifacts", "delivery_artifacts"):
            previews = role_previews.get(role)
            if not isinstance(previews, list) or not previews:
                raise CandidateBFinalProofError(
                    "candidate_b_final_proof_operator_inspection_role_preview_missing",
                    "Candidate B final operator inspection evidence is missing a required redacted role preview.",
                    http_status=409,
                    details={"candidate_b_source_kind": source_kind, "role": role},
                )
            for preview in previews:
                if not isinstance(preview, Mapping):
                    raise CandidateBFinalProofError(
                        "candidate_b_final_proof_operator_inspection_role_preview_invalid",
                        "Candidate B final operator inspection evidence contains an invalid role preview.",
                        http_status=409,
                        details={"candidate_b_source_kind": source_kind, "role": role},
                    )
                _validate_redacted_role_preview(
                    preview,
                    error_code="candidate_b_final_proof_operator_inspection_role_preview_not_redacted",
                    message="Candidate B final operator inspection role previews must use redacted preview fields only.",
                    details={"candidate_b_source_kind": source_kind, "role": role},
                )
        for field in (
            "pdf_material_text_payload_enabled",
            "image_material_text_payload_enabled",
            "raw_url_exposure_enabled",
        ):
            if summary.get(field) is not False:
                raise CandidateBFinalProofError(
                    "candidate_b_final_proof_operator_inspection_invariant_failed",
                    "Candidate B final operator inspection evidence enables a non-admitted material or URL authority.",
                    http_status=409,
                    details={"candidate_b_source_kind": source_kind, "field": field},
                )
    return operator_status_evidence


def _compute_readiness_hash(audit: Mapping[str, Any]) -> str:
    selected = audit["selected_evidence"]
    authority = audit["authority_hashes"]
    downstream = audit["downstream_proofs"]
    return _stable_hash(
        {
            "hash_version": "candidate_b_default_readiness_audit_hash_v1",
            "readiness_mode": layer3_candidate_b_default_readiness.READINESS_MODE,
            "baseline_run_id": selected.get("baseline_run_id"),
            "candidate_a_run_id": selected.get("candidate_a_run_id"),
            "candidate_b_bundle_id": selected.get("candidate_b_bundle_id"),
            "candidate_b_run_id": selected.get("candidate_b_run_id"),
            "bundle_bridge_receipt_id": _bundle_receipt_id(audit),
            "bundle_bridge_receipt_hash": authority.get("bundle", {}).get("bridge_receipt_hash"),
            "runtime_bridge_receipt_id": _runtime_receipt_id(audit),
            "runtime_bridge_receipt_hash": authority.get("runtime", {}).get("bridge_receipt_hash"),
            "bundle_downstream_proof_hash": downstream.get("bundle", {}).get("proof_hash"),
            "bundle_downstream_proof_receipt_id": downstream.get("bundle", {}).get("proof_receipt_id"),
            "runtime_downstream_proof_hash": downstream.get("runtime", {}).get("proof_hash"),
            "runtime_downstream_proof_receipt_id": downstream.get("runtime", {}).get("proof_receipt_id"),
            "candidate_b_visual_lane_status_hash": audit.get("candidate_b_visual_lane_status_evidence", {}).get("status_hash"),
            "eligible_corpus_scope": selected.get("eligible_corpus_scope"),
            "regression_disposition": audit.get("regression_disposition"),
            "rollback_to_baseline_confirmation": audit.get("rollback_to_baseline", {}).get("available") is True,
            "operator_status_hash": audit.get("operator_status_evidence", {}).get("operator_status_hash"),
            "closure_evidence_hash": audit.get("closure_evidence", {}).get("closure_evidence_hash"),
            "final_operator_inspection_hash": audit.get("candidate_b_final_operator_inspection_evidence", {}).get(
                "final_operator_inspection_hash"
            ),
        }
    )


def _bundle_receipt_id(audit: Mapping[str, Any]) -> str:
    return str(audit.get("bridge_receipts", {}).get("bundle", {}).get("bridge_receipt_id") or "").strip()


def _runtime_receipt_id(audit: Mapping[str, Any]) -> str:
    return str(audit.get("bridge_receipts", {}).get("runtime", {}).get("bridge_receipt_id") or "").strip()


def _final_operator_inspection_hash(inspection: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "hash_version": "candidate_b_final_operator_inspection_evidence_hash_v1",
            "bundle": inspection.get("bundle"),
            "runtime": inspection.get("runtime"),
            "raw_local_path_exposed": inspection.get("raw_local_path_exposed") is True,
            "raw_url_exposed": inspection.get("raw_url_exposed") is True,
            "artifact_bytes_exposed": inspection.get("artifact_bytes_exposed") is True,
        }
    )


def _validate_final_operator_inspection_exposure_flags(
    inspection: Mapping[str, Any],
    *,
    error_code: str,
    message: str,
    details: dict[str, Any],
) -> None:
    for field in _FINAL_OPERATOR_INSPECTION_EXPOSURE_FIELDS:
        if inspection.get(field) is not False:
            raise CandidateBFinalProofError(
                error_code,
                message,
                http_status=409,
                details={**details, "field": field, "received": inspection.get(field)},
            )


def _validate_ready_audit_nested_fields(audit: Mapping[str, Any]) -> None:
    for path in _READY_AUDIT_REQUIRED_NESTED_FIELDS:
        current: Any = audit
        for segment in path[:-1]:
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(segment)
        leaf = path[-1]
        if not isinstance(current, Mapping) or current.get(leaf) in (None, ""):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_readiness_audit_nested_field_missing",
                "Candidate B readiness audit is missing required nested authority fields.",
                http_status=409,
                details={"field_path": ".".join(path)},
            )


def _validate_operator_status_evidence(proof: Mapping[str, Any]) -> dict[str, Any]:
    operator_status = proof.get("candidate_b_operator_status_evidence")
    if not isinstance(operator_status, Mapping):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_operator_status_missing",
            "The selected Candidate B final proof receipt is missing operator-status evidence.",
            http_status=409,
        )
    return _validate_operator_status_authority(
        operator_status,
        expected_hash=str(proof.get("operator_status_hash") or "").strip(),
        error_prefix="candidate_b_final_proof_status_operator_status",
    )


def _validate_operator_status_authority(
    operator_status: Mapping[str, Any],
    *,
    expected_hash: str,
    error_prefix: str,
) -> dict[str, Any]:
    if operator_status.get("schema_id") == layer3_candidate_b_operator_status.SCHEMA_ID:
        return _validate_full_operator_status_authority(
            operator_status,
            expected_hash=expected_hash,
            error_prefix=error_prefix,
        )

    receipt_id = str(operator_status.get("operator_status_receipt_id") or "").strip()
    _validate_storage_id(
        receipt_id,
        prefix=layer3_candidate_b_operator_status.STATUS_RECEIPT_PREFIX,
        code=f"{error_prefix}_receipt_id_invalid",
    )
    runtime_receipt_id = str(operator_status.get("runtime_bridge_receipt_id") or "").strip()
    _validate_storage_id(
        runtime_receipt_id,
        prefix=layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
        code=f"{error_prefix}_runtime_receipt_id_invalid",
    )
    stored = _read_operator_status_receipt(
        runtime_receipt_id=runtime_receipt_id,
        receipt_id=receipt_id,
        error_prefix=error_prefix,
    )
    projection = _validate_full_operator_status_authority(
        stored,
        expected_hash=expected_hash,
        error_prefix=error_prefix,
    )
    mismatches = [
        {"field": field, "expected": projection.get(field), "received": operator_status.get(field)}
        for field in _OPERATOR_STATUS_RETAINED_FIELDS
        if field in operator_status and operator_status.get(field) != projection.get(field)
    ]
    if mismatches:
        raise CandidateBFinalProofError(
            f"{error_prefix}_hash_mismatch",
            "Candidate B final proof operator-status retained evidence is stale or invalid.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return projection


def _validate_full_operator_status_authority(
    operator_status: Mapping[str, Any],
    *,
    expected_hash: str,
    error_prefix: str,
) -> dict[str, Any]:
    for field, expected in {
        "schema_id": layer3_candidate_b_operator_status.SCHEMA_ID,
        "schema_version": layer3_candidate_b_operator_status.SCHEMA_VERSION,
        "mode": layer3_candidate_b_operator_status.STATUS_MODE,
        "status": "available",
        "candidate_b_source_kind": "runtime",
    }.items():
        if operator_status.get(field) != expected:
            raise CandidateBFinalProofError(
                f"{error_prefix}_{field}_mismatch",
                "Candidate B final proof operator-status evidence does not match the admitted contract.",
                http_status=409,
                details={"field": field, "expected": expected, "received": operator_status.get(field)},
            )
    missing_hash_fields = [
        key for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS if key not in operator_status
    ]
    if missing_hash_fields:
        raise CandidateBFinalProofError(
            f"{error_prefix}_authority_field_missing",
            "Candidate B final proof operator-status evidence is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing_hash_fields},
        )
    if not str(operator_status.get("runtime_delivery_artifact_authority_hash") or "").strip():
        raise CandidateBFinalProofError(
            f"{error_prefix}_delivery_authority_missing",
            "Candidate B final proof operator-status evidence is missing delivery artifact authority projection.",
            http_status=409,
        )
    _validate_operator_status_delivery_coverage(
        operator_status,
        error_prefix=error_prefix,
    )
    for field in ("runtime_delivery_artifact_projection_visible", "runtime_delivery_artifact_roles_bound"):
        if operator_status.get(field) is not True:
            raise CandidateBFinalProofError(
                f"{error_prefix}_delivery_projection_missing",
                "Candidate B final proof operator-status evidence is missing delivery artifact operator projection.",
                http_status=409,
                details={"field": field},
            )
    _validate_operator_status_delivery_previews(
        operator_status,
        error_prefix=error_prefix,
    )
    recomputed_hash = _stable_hash(
        {key: operator_status[key] for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS}
    )
    declared_hash = str(operator_status.get("operator_status_hash") or "").strip()
    if declared_hash != recomputed_hash or expected_hash != recomputed_hash:
        raise CandidateBFinalProofError(
            f"{error_prefix}_hash_mismatch",
            "Candidate B final proof operator-status evidence hash is stale or invalid.",
            http_status=409,
            details={
                "expected": recomputed_hash,
                "received": declared_hash or None,
                "retained": expected_hash or None,
            },
        )
    receipt_id = str(operator_status.get("operator_status_receipt_id") or "").strip()
    _validate_storage_id(
        receipt_id,
        prefix=layer3_candidate_b_operator_status.STATUS_RECEIPT_PREFIX,
        code=f"{error_prefix}_receipt_id_invalid",
    )
    runtime_receipt_id = str(operator_status.get("runtime_bridge_receipt_id") or "").strip()
    expected_ref = f"candidate-b-default-operator-status://{runtime_receipt_id}/{receipt_id}.json"
    if operator_status.get("operator_status_receipt_ref") != expected_ref:
        raise CandidateBFinalProofError(
            f"{error_prefix}_receipt_ref_mismatch",
            "Candidate B final proof operator-status receipt ref is not server-owned.",
            http_status=409,
            details={"expected": expected_ref, "received": operator_status.get("operator_status_receipt_ref")},
        )
    for field in _OPERATOR_STATUS_NON_EXPOSURE_FIELDS:
        if operator_status.get(field) is not False:
            raise CandidateBFinalProofError(
                f"{error_prefix}_non_exposure_invariant_failed",
                "Candidate B final proof operator-status evidence exposes non-admitted authority.",
                http_status=409,
                details={"field": field, "received": operator_status.get(field)},
            )
    invariants = operator_status.get("negative_invariants")
    if not isinstance(invariants, Mapping):
        raise CandidateBFinalProofError(
            f"{error_prefix}_negative_invariants_invalid",
            "Candidate B final proof operator-status evidence has malformed negative invariants.",
            http_status=409,
        )
    invariant_mismatches = [
        {"field": field, "expected": expected, "received": invariants.get(field)}
        for field, expected in _OPERATOR_STATUS_NEGATIVE_INVARIANTS.items()
        if invariants.get(field) is not expected
    ]
    if invariant_mismatches:
        raise CandidateBFinalProofError(
            f"{error_prefix}_negative_invariant_failed",
            "Candidate B final proof operator-status evidence violates a negative invariant.",
            http_status=409,
            details={"mismatches": invariant_mismatches},
        )
    projection = {key: operator_status[key] for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS}
    projection.update(
        {
            "operator_status_hash": recomputed_hash,
            "operator_status_receipt_id": receipt_id,
            "operator_status_receipt_ref": expected_ref,
            "status": "available",
            "candidate_b_source_kind": "runtime",
            **{field: False for field in _OPERATOR_STATUS_NON_EXPOSURE_FIELDS},
            "negative_invariants": {
                field: expected for field, expected in _OPERATOR_STATUS_NEGATIVE_INVARIANTS.items()
            },
        }
    )
    return projection


def _read_operator_status_receipt(
    *,
    runtime_receipt_id: str,
    receipt_id: str,
    error_prefix: str,
) -> Mapping[str, Any]:
    bridge_dir_code = (
        "candidate_b_final_proof_runtime_bridge_dir_invalid"
        if error_prefix == "candidate_b_final_proof_operator_status"
        else f"{error_prefix}_bridge_dir_invalid"
    )
    root = _runtime_bridge_root(
        code=bridge_dir_code,
        message="The configured Candidate B runtime bridge directory is missing or not absolute.",
    )
    path = root / runtime_receipt_id / "operator-status" / f"{receipt_id}.json"
    if not path.is_file():
        raise CandidateBFinalProofError(
            f"{error_prefix}_receipt_missing",
            "The selected Candidate B operator-status receipt is missing.",
            http_status=409,
            details={"operator_status_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFinalProofError(
            f"{error_prefix}_receipt_unreadable",
            "The selected Candidate B operator-status receipt could not be read.",
            http_status=409,
            details={"operator_status_receipt_id": receipt_id, "reason": exc.__class__.__name__},
        ) from exc
    if not isinstance(receipt, Mapping):
        raise CandidateBFinalProofError(
            f"{error_prefix}_receipt_invalid",
            "The selected Candidate B operator-status receipt is not a JSON object.",
            http_status=409,
            details={"operator_status_receipt_id": receipt_id},
        )
    return receipt


def _validate_operator_status_delivery_previews(
    operator_status: Mapping[str, Any],
    *,
    error_prefix: str,
) -> None:
    previews = operator_status.get("runtime_delivery_artifact_role_previews")
    if not isinstance(previews, list) or not previews:
        raise CandidateBFinalProofError(
            f"{error_prefix}_delivery_previews_missing",
            "Candidate B final proof requires redacted runtime delivery artifact previews from operator-status evidence.",
            http_status=409,
        )
    for index, preview in enumerate(previews):
        if not isinstance(preview, Mapping):
            raise CandidateBFinalProofError(
                f"{error_prefix}_delivery_preview_invalid",
                "Candidate B final proof contains an invalid runtime delivery artifact preview.",
                http_status=409,
                details={"index": index},
            )
        _validate_redacted_role_preview(
            preview,
            error_code=f"{error_prefix}_delivery_preview_not_redacted",
            message="Candidate B final proof runtime delivery previews must use redacted preview fields only.",
            details={"index": index},
        )


def _validate_operator_status_delivery_coverage(
    operator_status: Mapping[str, Any],
    *,
    error_prefix: str,
) -> None:
    coverage = operator_status.get("runtime_delivery_artifact_coverage_steps")
    if not isinstance(coverage, list):
        raise CandidateBFinalProofError(
            f"{error_prefix}_delivery_coverage_missing",
            "Candidate B final proof requires runtime delivery artifact coverage projection.",
            http_status=409,
        )
    observed = sorted(str(item).strip() for item in coverage if isinstance(item, str) and item.strip())
    if observed != _EXPECTED_OPERATOR_STATUS_DELIVERY_COVERAGE or len(observed) != len(coverage):
        raise CandidateBFinalProofError(
            f"{error_prefix}_delivery_coverage_mismatch",
            "Candidate B final proof requires the complete runtime delivery artifact coverage set.",
            http_status=409,
            details={"expected": _EXPECTED_OPERATOR_STATUS_DELIVERY_COVERAGE, "received": coverage},
        )


def _validate_final_operator_inspection_role_previews(inspection: Mapping[str, Any]) -> None:
    for source_kind in ("bundle", "runtime"):
        summary = inspection.get(source_kind)
        if not isinstance(summary, Mapping):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_status_operator_inspection_source_missing",
                "The selected Candidate B final proof receipt is missing a source inspection summary.",
                http_status=409,
                details={"candidate_b_source_kind": source_kind},
            )
        for field in _FINAL_OPERATOR_INSPECTION_COUNT_FIELDS:
            _validate_final_operator_inspection_positive_count(
                summary,
                field=field,
                source_kind=source_kind,
                invalid_code="candidate_b_final_proof_status_operator_inspection_artifact_count_invalid",
                missing_code="candidate_b_final_proof_status_operator_inspection_artifact_count_missing",
                message="The selected Candidate B final proof receipt is missing retained visual/product/delivery artifacts.",
            )
        role_previews = summary.get("role_previews")
        if not isinstance(role_previews, Mapping):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_status_operator_inspection_role_previews_missing",
                "The selected Candidate B final proof receipt is missing redacted role previews.",
                http_status=409,
                details={"candidate_b_source_kind": source_kind},
            )
        for role in ("visual_page_evidence", "product_inspection_artifacts", "delivery_artifacts"):
            previews = role_previews.get(role)
            if not isinstance(previews, list) or not previews:
                raise CandidateBFinalProofError(
                    "candidate_b_final_proof_status_operator_inspection_role_preview_missing",
                    "The selected Candidate B final proof receipt is missing a required role preview.",
                    http_status=409,
                    details={"candidate_b_source_kind": source_kind, "role": role},
                )
            for preview in previews:
                if not isinstance(preview, Mapping):
                    raise CandidateBFinalProofError(
                        "candidate_b_final_proof_status_operator_inspection_role_preview_invalid",
                        "The selected Candidate B final proof receipt contains an invalid role preview.",
                        http_status=409,
                        details={"candidate_b_source_kind": source_kind, "role": role},
                    )
                _validate_redacted_role_preview(
                    preview,
                    error_code="candidate_b_final_proof_status_operator_inspection_role_preview_not_redacted",
                    message="The selected Candidate B final proof receipt contains an unredacted role preview.",
                    details={"candidate_b_source_kind": source_kind, "role": role},
                )


def _validate_final_operator_inspection_positive_count(
    summary: Mapping[str, Any],
    *,
    field: str,
    source_kind: str,
    invalid_code: str,
    missing_code: str,
    message: str,
) -> int:
    count = _strict_nonnegative_int(summary.get(field))
    if count is None:
        raise CandidateBFinalProofError(
            invalid_code,
            message,
            http_status=409,
            details={"candidate_b_source_kind": source_kind, "field": field, "received": summary.get(field)},
        )
    if count <= 0:
        raise CandidateBFinalProofError(
            missing_code,
            message,
            http_status=409,
            details={"candidate_b_source_kind": source_kind, "field": field},
        )
    return count


def _strict_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdecimal():
            return int(text)
    return None


def _validate_redacted_role_preview(
    preview: Mapping[str, Any],
    *,
    error_code: str,
    message: str,
    details: dict[str, Any],
) -> None:
    blocked_fields = sorted(str(key) for key in preview if str(key) not in _ALLOWED_ROLE_PREVIEW_FIELDS)
    raw_authority_fields = sorted(
        str(key)
        for key, value in preview.items()
        if str(key) in _ALLOWED_ROLE_PREVIEW_FIELDS and _preview_value_exposes_raw_authority(value)
    )
    display_ref = str(preview.get("display_ref") or "").strip()
    if not display_ref or _preview_value_exposes_raw_authority(display_ref):
        raw_authority_fields.append("display_ref")
    raw_authority_fields = sorted(set(raw_authority_fields))
    if blocked_fields or raw_authority_fields:
        raise CandidateBFinalProofError(
            error_code,
            message,
            http_status=409,
            details={
                **details,
                "blocked_fields": blocked_fields,
                "raw_authority_fields": raw_authority_fields,
            },
        )


def _preview_value_exposes_raw_authority(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (Mapping, list, tuple, set)):
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    lower = text.lower()
    normalised = text.replace("\\", "/")
    if any(token in lower for token in ("http://", "https://", "file://")):
        return True
    if "\\" in text or "/" in text:
        return True
    if len(text) >= 2 and text[1] == ":" and text[0].isalpha():
        return True
    if normalised in {".", ".."}:
        return True
    return any(part == ".." for part in normalised.split("/"))


def _validate_stored_non_exposure_flags(proof: Mapping[str, Any]) -> None:
    for field in (
        "raw_local_path_exposed",
        "raw_url_exposed",
        "provider_private_token_exposed",
        "artifact_bytes_exposed",
        "selector_mutation_performed",
    ):
        if proof.get(field) is not False:
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_status_non_exposure_invariant_failed",
                "The selected Candidate B final proof receipt exposes non-admitted authority.",
                http_status=409,
                details={"field": field, "received": proof.get(field)},
            )


def _validate_stored_negative_invariants(proof: Mapping[str, Any]) -> None:
    invariants = proof.get("negative_invariants")
    if not isinstance(invariants, Mapping):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_negative_invariants_invalid",
            "The selected Candidate B final proof receipt has malformed negative invariants.",
            http_status=409,
        )
    mismatches = [
        {"field": field, "expected": expected, "received": invariants.get(field)}
        for field, expected in _STORED_NEGATIVE_INVARIANTS.items()
        if invariants.get(field) is not expected
    ]
    if mismatches:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_negative_invariant_failed",
            "The selected Candidate B final proof receipt violates a negative invariant.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _validate_closure_receipt(audit: Mapping[str, Any], *, runtime_receipt_id: str, closure_hash: str) -> None:
    _validate_storage_id(
        runtime_receipt_id,
        prefix=layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
        code="candidate_b_final_proof_runtime_bridge_receipt_id_invalid",
    )
    receipt_id = str(audit.get("closure_evidence", {}).get("closure_receipt_id") or "").strip()
    _validate_storage_id(
        receipt_id,
        prefix=layer3_candidate_b_promotion_closure.CLOSURE_RECEIPT_PREFIX,
        code="candidate_b_final_proof_closure_receipt_id_invalid",
    )
    root = _runtime_bridge_root(
        code="candidate_b_final_proof_runtime_bridge_dir_invalid",
        message="Candidate B final proof requires an absolute runtime bridge receipt directory.",
    )
    path = root / runtime_receipt_id / "default-promotion-closure" / f"{receipt_id}.json"
    if not path.is_file():
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_closure_receipt_missing",
            "Candidate B final proof requires the persisted closure receipt.",
            http_status=409,
            details={"closure_receipt_id": receipt_id},
        )
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_closure_receipt_unreadable",
            "Candidate B closure receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(stored, dict) or stored.get("closure_evidence_hash") != closure_hash:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_closure_receipt_hash_mismatch",
            "Candidate B closure receipt hash does not match the readiness audit.",
            http_status=409,
            details={"expected": closure_hash, "received": stored.get("closure_evidence_hash") if isinstance(stored, dict) else None},
        )


def _validate_bridge_receipt_hash(*, kind: str, receipt_id: str, expected_hash: str) -> None:
    prefix = (
        layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX
        if kind == "bundle"
        else layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX
    )
    _validate_storage_id(
        receipt_id,
        prefix=prefix,
        code=f"candidate_b_final_proof_{kind}_bridge_receipt_id_invalid",
    )
    if len(expected_hash) != 64:
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_hash_invalid",
            "Candidate B final proof requires a valid bridge receipt hash.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    configured = (
        settings.layer3_candidate_b_bundle_bridge_dir
        if kind == "bundle"
        else settings.layer3_candidate_b_runtime_bridge_dir
    )
    root = Path(str(configured or ""))
    if not str(configured or "").strip() or not root.is_absolute():
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_dir_invalid",
            "Candidate B final proof requires an absolute bridge receipt directory.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_missing",
            "Candidate B final proof requires the current bridge receipt.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "bridge_receipt_id": receipt_id},
        )
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_unreadable",
            "Candidate B final proof could not read the current bridge receipt.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "reason": str(exc)},
        ) from exc
    if not isinstance(stored, Mapping):
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_invalid",
            "Candidate B final proof bridge receipt is not a JSON object.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    if stored.get("bridge_receipt_id") != receipt_id or stored.get("bridge_receipt_hash") != expected_hash:
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_hash_mismatch",
            "Candidate B final proof bridge receipt authority is stale.",
            http_status=409,
            details={
                "candidate_b_source_kind": kind,
                "bridge_receipt_id": receipt_id,
                "expected": expected_hash,
                "received": stored.get("bridge_receipt_hash"),
            },
        )
    hash_keys = _bridge_hash_keys(kind)
    missing_hash_fields = [key for key in hash_keys if key not in stored]
    if missing_hash_fields:
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_authority_field_missing",
            "Candidate B final proof bridge receipt is missing authority hash fields.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "missing_fields": missing_hash_fields},
        )
    recomputed_hash = _stable_hash({key: stored[key] for key in hash_keys})
    if recomputed_hash != expected_hash:
        raise CandidateBFinalProofError(
            f"candidate_b_final_proof_{kind}_bridge_receipt_hash_mismatch",
            "Candidate B final proof bridge receipt authority is stale.",
            http_status=409,
            details={
                "candidate_b_source_kind": kind,
                "bridge_receipt_id": receipt_id,
                "expected": expected_hash,
                "received": stored.get("bridge_receipt_hash"),
                "recomputed": recomputed_hash,
            },
        )


def _validate_downstream_proof_receipt(
    *,
    kind: str,
    proof_receipt_id: str,
    bridge_receipt_id: str,
    expected_hash: str,
    code_prefix: str,
) -> None:
    proof_prefix, bridge_prefix, configured, hash_keys = _downstream_proof_config(kind)
    _validate_storage_id(
        bridge_receipt_id,
        prefix=bridge_prefix,
        code=f"{code_prefix}_{kind}_downstream_proof_bridge_receipt_id_invalid",
    )
    if not proof_receipt_id:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_id_missing",
            "Candidate B final proof requires a server-issued downstream proof receipt.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    _validate_storage_id(
        proof_receipt_id,
        prefix=proof_prefix,
        code=f"{code_prefix}_{kind}_downstream_proof_receipt_id_invalid",
    )
    if len(expected_hash) != 64:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_hash_invalid",
            "Candidate B final proof requires a valid downstream proof hash.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    expected_receipt_id = f"{proof_prefix}-{expected_hash[:24]}"
    if proof_receipt_id != expected_receipt_id:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_id_mismatch",
            "Candidate B final proof downstream proof receipt ID does not match the proof hash.",
            http_status=409,
            details={
                "candidate_b_source_kind": kind,
                "expected": expected_receipt_id,
                "received": proof_receipt_id,
            },
        )
    root = Path(str(configured or ""))
    if not str(configured or "").strip() or not root.is_absolute():
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_bridge_dir_invalid",
            "Candidate B final proof requires an absolute downstream proof receipt directory.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    path = root / bridge_receipt_id / "downstream-proof" / f"{proof_receipt_id}.json"
    if not path.is_file():
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_missing",
            "Candidate B final proof requires the persisted downstream proof receipt.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "proof_receipt_id": proof_receipt_id},
        )
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_unreadable",
            "Candidate B final proof could not read the persisted downstream proof receipt.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "reason": str(exc)},
        ) from exc
    if not isinstance(stored, Mapping):
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_invalid",
            "Candidate B final proof downstream proof receipt is not a JSON object.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    mismatches = [
        {"field": field, "expected": expected, "received": stored.get(field)}
        for field, expected in {
            "proof_receipt_id": proof_receipt_id,
            "bridge_receipt_id": bridge_receipt_id,
        }.items()
        if str(stored.get(field) or "").strip() != str(expected or "").strip()
    ]
    if mismatches:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_mismatch",
            "Candidate B final proof downstream proof receipt does not match the requested authority.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "mismatches": mismatches},
        )
    missing_hash_fields = [key for key in hash_keys if key not in stored]
    if missing_hash_fields:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_authority_field_missing",
            "Candidate B final proof downstream proof receipt is missing authority hash fields.",
            http_status=409,
            details={"candidate_b_source_kind": kind, "missing_fields": missing_hash_fields},
        )
    recomputed_hash = _stable_hash({key: stored[key] for key in hash_keys})
    if stored.get("proof_hash") != expected_hash or recomputed_hash != expected_hash:
        raise CandidateBFinalProofError(
            f"{code_prefix}_{kind}_downstream_proof_receipt_hash_mismatch",
            "Candidate B final proof downstream proof receipt authority is stale.",
            http_status=409,
            details={
                "candidate_b_source_kind": kind,
                "expected": expected_hash,
                "received": stored.get("proof_hash"),
                "recomputed": recomputed_hash,
            },
        )


def _downstream_proof_config(kind: str) -> tuple[str, str, str | None, tuple[str, ...]]:
    if kind == "bundle":
        return (
            layer3_candidate_b_bundle_downstream_proof.PROOF_RECEIPT_PREFIX,
            layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX,
            settings.layer3_candidate_b_bundle_bridge_dir,
            layer3_candidate_b_bundle_downstream_proof.PROOF_HASH_KEYS,
        )
    return (
        layer3_candidate_b_downstream_proof.PROOF_RECEIPT_PREFIX,
        layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
        settings.layer3_candidate_b_runtime_bridge_dir,
        layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS,
    )


def _bridge_hash_keys(kind: str) -> tuple[str, ...]:
    if kind == "bundle":
        return layer3_candidate_b_default_readiness._BUNDLE_HASH_KEYS
    return layer3_candidate_b_default_readiness._RUNTIME_HASH_KEYS


def _write_proof_receipt(*, runtime_receipt_id: str, proof_receipt_id: str, proof: Mapping[str, Any]) -> None:
    _validate_storage_id(
        runtime_receipt_id,
        prefix=layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
        code="candidate_b_final_proof_runtime_bridge_receipt_id_invalid",
    )
    _validate_storage_id(
        proof_receipt_id,
        prefix=PROOF_RECEIPT_PREFIX,
        code="candidate_b_final_proof_proof_receipt_id_invalid",
    )
    runtime_root = _runtime_bridge_root(
        code="candidate_b_final_proof_runtime_bridge_dir_invalid",
        message="Candidate B final proof requires an absolute runtime bridge receipt directory.",
    )
    root = runtime_root / runtime_receipt_id / "default-promotion-final-proof"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{proof_receipt_id}.json"
    body = json.dumps(dict(proof), sort_keys=True, indent=2) + "\n"
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_receipt_unreadable",
                "The existing Candidate B final proof receipt could not be read.",
                http_status=409,
                details={"reason": str(exc)},
            ) from exc
        if not isinstance(existing, dict) or existing.get("proof_hash") != proof.get("proof_hash"):
            raise CandidateBFinalProofError(
                "candidate_b_final_proof_receipt_conflict",
                "A Candidate B final proof receipt already exists with different contents.",
                http_status=409,
                details={"proof_receipt_id": proof_receipt_id},
            )
        return
    try:
        path.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_receipt_write_failed",
            "The Candidate B final proof receipt could not be written.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc


def _runtime_bridge_root(*, code: str, message: str) -> Path:
    configured = settings.layer3_candidate_b_runtime_bridge_dir
    root = Path(str(configured or ""))
    if not str(configured or "").strip() or not root.is_absolute():
        raise CandidateBFinalProofError(code, message, http_status=409)
    return root


def _proof_receipt_ref(*, runtime_receipt_id: str, proof_receipt_id: str) -> str:
    return f"candidate-b-default-final-proof://{runtime_receipt_id}/{proof_receipt_id}.json"


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
