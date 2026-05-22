from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_default_readiness,
    layer3_candidate_b_promotion_closure,
    layer3_candidate_b_runtime_bridge,
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
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_bundle_id",
    "candidate_b_run_id",
    "bundle_bridge_receipt_hash",
    "runtime_bridge_receipt_hash",
    "bundle_downstream_proof_hash",
    "runtime_downstream_proof_hash",
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
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-default-final-proof-error",
            "server_time": _server_time(),
            "mode": PROOF_MODE,
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
    _validate_ready_audit(audit)
    readiness_hash = _compute_readiness_hash(audit)
    if audit.get("readiness_audit_hash") != readiness_hash:
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_readiness_hash_mismatch",
            "Candidate B readiness audit hash is stale or invalid.",
            http_status=409,
            details={"expected": readiness_hash, "received": audit.get("readiness_audit_hash")},
        )
    runtime_receipt_id = _runtime_receipt_id(audit)
    closure_hash = str(audit.get("closure_evidence", {}).get("closure_evidence_hash") or "").strip()
    _validate_closure_receipt(audit, runtime_receipt_id=runtime_receipt_id, closure_hash=closure_hash)
    selected = audit["selected_evidence"]
    authority = audit["authority_hashes"]
    downstream = audit["downstream_proofs"]
    proof_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROOF_MODE,
        "readiness_audit_id": audit["readiness_audit_id"],
        "readiness_audit_hash": readiness_hash,
        "baseline_run_id": selected["baseline_run_id"],
        "candidate_a_run_id": selected["candidate_a_run_id"],
        "candidate_b_bundle_id": selected["candidate_b_bundle_id"],
        "candidate_b_run_id": selected["candidate_b_run_id"],
        "bundle_bridge_receipt_hash": authority["bundle"]["bridge_receipt_hash"],
        "runtime_bridge_receipt_hash": authority["runtime"]["bridge_receipt_hash"],
        "bundle_downstream_proof_hash": downstream["bundle"]["proof_hash"],
        "runtime_downstream_proof_hash": downstream["runtime"]["proof_hash"],
        "candidate_b_visual_lane_status_hash": audit["candidate_b_visual_lane_status_evidence"]["status_hash"],
        "operator_status_hash": audit["operator_status_evidence"]["operator_status_hash"],
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
        "proof_receipt_ref": f"candidate-b-default-final-proof://{runtime_receipt_id}/{proof_receipt_id}.json",
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "proven",
        "proof_state": PROOF_STATE,
        "selector_mutation_performed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_private_token_exposed": False,
        "artifact_bytes_exposed": False,
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
    configured = settings.layer3_candidate_b_runtime_bridge_dir
    root = Path(str(configured or ""))
    if not str(configured or "").strip() or not root.is_absolute():
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_bridge_dir_invalid",
            "The configured Candidate B runtime bridge directory is missing or not absolute.",
            http_status=409,
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
    _validate_stored_final_proof(proof, proof_receipt_id=proof_receipt_id)
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
    if not value.startswith(f"{prefix}-") or "/" in value or "\\" in value or ".." in value or value in {".", ".."}:
        raise CandidateBFinalProofError(
            code,
            "Candidate B final proof status identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )
    return value


def _validate_stored_final_proof(proof: Mapping[str, Any], *, proof_receipt_id: str) -> None:
    expected = {
        "schema_id": SCHEMA_ID,
        "mode": PROOF_MODE,
        "status": "proven",
        "proof_state": PROOF_STATE,
        "proof_receipt_id": proof_receipt_id,
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
    inspection = proof.get("candidate_b_final_operator_inspection_evidence")
    if not isinstance(inspection, Mapping):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_status_operator_inspection_missing",
            "The selected Candidate B final proof receipt is missing retained artifact inspection evidence.",
            http_status=409,
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


def _validate_ready_audit(audit: Mapping[str, Any]) -> None:
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
    inspection = audit["candidate_b_final_operator_inspection_evidence"]
    if inspection.get("status") != "available":
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_operator_inspection_not_available",
            "Candidate B final proof requires available retained artifact inspection evidence.",
            http_status=409,
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
        for field in (
            "visual_page_evidence_count",
            "product_inspection_artifact_count",
            "delivery_artifact_count",
        ):
            if int(summary.get(field) or 0) <= 0:
                raise CandidateBFinalProofError(
                    "candidate_b_final_proof_operator_inspection_artifact_count_missing",
                    "Candidate B final operator inspection evidence is missing retained visual/product/delivery artifacts.",
                    http_status=409,
                    details={"candidate_b_source_kind": source_kind, "field": field},
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
            "runtime_downstream_proof_hash": downstream.get("runtime", {}).get("proof_hash"),
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


def _validate_closure_receipt(audit: Mapping[str, Any], *, runtime_receipt_id: str, closure_hash: str) -> None:
    receipt_id = str(audit.get("closure_evidence", {}).get("closure_receipt_id") or "").strip()
    if (
        not receipt_id.startswith(f"{layer3_candidate_b_promotion_closure.CLOSURE_RECEIPT_PREFIX}-")
        or "/" in receipt_id
        or "\\" in receipt_id
        or ".." in receipt_id
    ):
        raise CandidateBFinalProofError(
            "candidate_b_final_proof_closure_receipt_id_invalid",
            "Candidate B final proof requires a server-owned closure receipt id.",
            http_status=409,
        )
    path = Path(str(settings.layer3_candidate_b_runtime_bridge_dir)) / runtime_receipt_id / "default-promotion-closure" / f"{receipt_id}.json"
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


def _write_proof_receipt(*, runtime_receipt_id: str, proof_receipt_id: str, proof: Mapping[str, Any]) -> None:
    root = Path(str(settings.layer3_candidate_b_runtime_bridge_dir)) / runtime_receipt_id / "default-promotion-final-proof"
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


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
