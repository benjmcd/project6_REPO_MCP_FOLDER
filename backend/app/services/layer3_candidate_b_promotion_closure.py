from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_operator_status,
    layer3_candidate_b_runtime_bridge,
)


SCHEMA_ID = "layer3.candidate_b_default_promotion_closure_evidence.v1"
SCHEMA_VERSION = 1
CLOSURE_MODE = "candidate_b_default_promotion_closure_evidence_v1"
OPERATOR_DECISION = "record_candidate_b_default_promotion_closure_evidence"
CLOSURE_RECEIPT_PREFIX = "cb-default-closure-evidence"
ELIGIBLE_CORPUS_SCOPE = "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only"
REGRESSION_DISPOSITION_READY = "no_unacceptable_regression_against_baseline_and_candidate_a"

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
_RUNTIME_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "bridge_mode",
    "candidate_b_run_id",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_source_kind",
    "document_processing_engine",
    "visual_lane_mode",
    "compare_target_set_hash",
    "runtime_review_root_storage_authority_hash",
    "admitted_file_subset_hash",
    "governed_retained_artifact_family_hash",
    "redaction_policy_id",
)
CLOSURE_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_bundle_id",
    "candidate_b_run_id",
    "bundle_bridge_receipt_id",
    "bundle_bridge_receipt_hash",
    "runtime_bridge_receipt_id",
    "runtime_bridge_receipt_hash",
    "bundle_downstream_proof_hash",
    "runtime_downstream_proof_hash",
    "operator_status_hash",
    "eligible_corpus_scope",
    "regression_disposition",
    "rollback_to_baseline_confirmation",
    "operator_confirmation",
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


class CandidateBPromotionClosureError(Exception):
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
            "request_id": "candidate-b-default-closure-error",
            "server_time": _server_time(),
            "mode": CLOSURE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_default_promotion_closure_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "closure_mode") != CLOSURE_MODE:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_mode_not_admitted",
            "Only the Candidate B default-promotion closure-evidence mode is admitted.",
            details={"expected_closure_mode": CLOSURE_MODE, "received_closure_mode": fields.get("closure_mode")},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_operator_decision_not_admitted",
            "The operator decision does not match the admitted closure-evidence recording.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    if _required(fields, "eligible_corpus_scope") != ELIGIBLE_CORPUS_SCOPE:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_eligible_scope_not_admitted",
            "Candidate B default-promotion closure is limited to the eligible PDF corpus scope.",
            details={"expected_eligible_corpus_scope": ELIGIBLE_CORPUS_SCOPE},
        )
    if _required(fields, "regression_disposition") != REGRESSION_DISPOSITION_READY:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_regression_disposition_not_ready",
            "Candidate B default-promotion closure requires no unacceptable regression disposition.",
            details={"expected_regression_disposition": REGRESSION_DISPOSITION_READY},
        )
    if fields.get("rollback_to_baseline_confirmation") is not True or fields.get("operator_confirmation") is not True:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_confirmation_missing",
            "Rollback-to-baseline and operator confirmations must both be true before closure evidence is recorded.",
            details={
                "rollback_to_baseline_confirmation": fields.get("rollback_to_baseline_confirmation") is True,
                "operator_confirmation": fields.get("operator_confirmation") is True,
            },
        )

    baseline_run_id = _required(fields, "baseline_run_id")
    candidate_a_run_id = _required(fields, "candidate_a_run_id")
    candidate_b_bundle_id = _required(fields, "candidate_b_bundle_id")
    candidate_b_run_id = _required(fields, "candidate_b_run_id")
    bundle_receipt_id = _required_storage_id(
        fields,
        "candidate_b_bundle_bridge_receipt_id",
        layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX,
    )
    runtime_receipt_id = _required_storage_id(
        fields,
        "candidate_b_runtime_bridge_receipt_id",
        layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
    )

    bundle_hash = _validate_bridge_receipt(
        kind="bundle",
        receipt_id=bundle_receipt_id,
        expected={
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": candidate_b_bundle_id,
        },
    )
    runtime_hash = _validate_bridge_receipt(
        kind="runtime",
        receipt_id=runtime_receipt_id,
        expected={
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_run_id": candidate_b_run_id,
        },
    )
    bundle_proof_hash = _validate_bundle_proof(
        fields.get("bundle_downstream_proof"),
        candidate_b_bundle_id=candidate_b_bundle_id,
        receipt_id=bundle_receipt_id,
        receipt_hash=bundle_hash,
    )
    runtime_proof_hash = _validate_runtime_proof(
        fields.get("runtime_downstream_proof"),
        candidate_b_run_id=candidate_b_run_id,
        receipt_id=runtime_receipt_id,
        receipt_hash=runtime_hash,
    )
    operator_status_hash = _validate_operator_status(
        fields.get("operator_status_evidence"),
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        candidate_b_run_id=candidate_b_run_id,
        bundle_receipt_id=bundle_receipt_id,
        bundle_hash=bundle_hash,
        runtime_receipt_id=runtime_receipt_id,
        runtime_hash=runtime_hash,
        runtime_proof_hash=runtime_proof_hash,
    )
    closure_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": CLOSURE_MODE,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "candidate_b_run_id": candidate_b_run_id,
        "bundle_bridge_receipt_id": bundle_receipt_id,
        "bundle_bridge_receipt_hash": bundle_hash,
        "runtime_bridge_receipt_id": runtime_receipt_id,
        "runtime_bridge_receipt_hash": runtime_hash,
        "bundle_downstream_proof_hash": bundle_proof_hash,
        "runtime_downstream_proof_hash": runtime_proof_hash,
        "operator_status_hash": operator_status_hash,
        "eligible_corpus_scope": ELIGIBLE_CORPUS_SCOPE,
        "regression_disposition": REGRESSION_DISPOSITION_READY,
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }
    closure_hash = _stable_hash(closure_input)
    closure_receipt_id = f"{CLOSURE_RECEIPT_PREFIX}-{closure_hash[:24]}"
    response = {
        **closure_input,
        "closure_evidence_hash": closure_hash,
        "closure_receipt_id": closure_receipt_id,
        "closure_receipt_ref": f"candidate-b-default-closure-evidence://{runtime_receipt_id}/{closure_receipt_id}.json",
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready",
        "rollback_selector": "baseline",
        "selector_mutation_performed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_private_token_exposed": False,
        "artifact_bytes_exposed": False,
        "negative_invariants": {
            "baseline_rollback_preserved": True,
            "candidate_a_semantics_changed": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": ["use this closure evidence in Candidate B default-promotion readiness"],
    }
    _write_closure_receipt(runtime_receipt_id=runtime_receipt_id, receipt_id=closure_receipt_id, payload=response)
    return response


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_forbidden_request_fields",
            "Closure evidence does not admit caller paths, URLs, selector mutation, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_required_field_missing",
            "A required Candidate B default-promotion closure field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    _validate_storage_id(value, prefix=prefix, code="candidate_b_default_closure_storage_id_invalid")
    return value


def _validate_storage_id(value: str, *, prefix: str, code: str) -> None:
    if not value.startswith(f"{prefix}-") or "/" in value or "\\" in value or ".." in value or value in {".", ".."}:
        raise CandidateBPromotionClosureError(
            code,
            "Candidate B default-promotion closure identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _read_json(path: Path, *, code: str, message: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBPromotionClosureError(code, message, http_status=409, details={"reason": str(exc)}) from exc
    if not isinstance(payload, dict):
        raise CandidateBPromotionClosureError(code.replace("unreadable", "invalid"), message, http_status=409)
    return payload


def _validate_bridge_receipt(*, kind: str, receipt_id: str, expected: Mapping[str, str]) -> str:
    configured = settings.layer3_candidate_b_bundle_bridge_dir if kind == "bundle" else settings.layer3_candidate_b_runtime_bridge_dir
    root = Path(str(configured or ""))
    if not str(configured or "").strip() or not root.is_absolute():
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_bridge_dir_invalid",
            "The configured Candidate B bridge directory is missing or not absolute.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_bridge_receipt_missing",
            "The selected Candidate B bridge receipt is missing.",
            http_status=404,
            details={"candidate_b_source_kind": kind, "bridge_receipt_id": receipt_id},
        )
    receipt = _read_json(
        path,
        code="candidate_b_default_closure_bridge_receipt_unreadable",
        message="The selected Candidate B bridge receipt could not be read.",
    )
    schema_id = layer3_candidate_b_bundle_bridge.SCHEMA_ID if kind == "bundle" else layer3_candidate_b_runtime_bridge.SCHEMA_ID
    bridge_mode = layer3_candidate_b_bundle_bridge.BRIDGE_MODE if kind == "bundle" else layer3_candidate_b_runtime_bridge.BRIDGE_MODE
    mismatches = []
    for field, expected_value in {
        "schema_id": schema_id,
        "bridge_mode": bridge_mode,
        "candidate_b_source_kind": kind,
        "bridge_receipt_id": receipt_id,
        **expected,
    }.items():
        if str(receipt.get(field) or "").strip() != expected_value:
            mismatches.append({"field": field, "expected": expected_value, "received": receipt.get(field)})
    if mismatches:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_bridge_receipt_mismatch",
            "The selected Candidate B bridge receipt does not match the closure target.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    keys = _BUNDLE_HASH_KEYS if kind == "bundle" else _RUNTIME_HASH_KEYS
    missing = [key for key in keys if key not in receipt]
    if missing:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_bridge_receipt_authority_field_missing",
            "The selected Candidate B bridge receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in keys})
    if receipt.get("bridge_receipt_hash") != expected_hash:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_bridge_receipt_hash_mismatch",
            "The selected Candidate B bridge receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("bridge_receipt_hash")},
        )
    return expected_hash


def _validate_bundle_proof(value: Any, *, candidate_b_bundle_id: str, receipt_id: str, receipt_hash: str) -> str:
    proof = _require_mapping(value, "candidate_b_default_closure_bundle_downstream_proof_missing")
    expected = {
        "schema_id": layer3_candidate_b_bundle_downstream_proof.SCHEMA_ID,
        "mode": layer3_candidate_b_bundle_downstream_proof.PROOF_MODE,
        "status": "proven",
        "candidate_b_source_kind": "bundle",
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "proof_state": layer3_candidate_b_bundle_downstream_proof.PROOF_STATE,
        "visual_lane_mode_enabled": False,
    }
    return _validate_proof(
        proof,
        expected=expected,
        hash_keys=layer3_candidate_b_bundle_downstream_proof.PROOF_HASH_KEYS,
        receipt_root=Path(str(settings.layer3_candidate_b_bundle_bridge_dir)),
        receipt_id=receipt_id,
        receipt_prefix=layer3_candidate_b_bundle_downstream_proof.PROOF_RECEIPT_PREFIX,
        code_prefix="candidate_b_default_closure_bundle_downstream_proof",
    )


def _validate_runtime_proof(value: Any, *, candidate_b_run_id: str, receipt_id: str, receipt_hash: str) -> str:
    proof = _require_mapping(value, "candidate_b_default_closure_runtime_downstream_proof_missing")
    expected = {
        "schema_id": layer3_candidate_b_downstream_proof.SCHEMA_ID,
        "mode": layer3_candidate_b_downstream_proof.PROOF_MODE,
        "status": "proven",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "document_processing_engine": layer3_candidate_b_runtime_bridge.CANDIDATE_B_RUNTIME_VARIANT,
        "visual_lane_mode": layer3_candidate_b_runtime_bridge.CANDIDATE_B_VISUAL_LANE_MODE,
        "proof_state": layer3_candidate_b_downstream_proof.PROOF_STATE,
        "visual_lane_mode_enabled": True,
    }
    return _validate_proof(
        proof,
        expected=expected,
        hash_keys=layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS,
        receipt_root=Path(str(settings.layer3_candidate_b_runtime_bridge_dir)),
        receipt_id=receipt_id,
        receipt_prefix=layer3_candidate_b_downstream_proof.PROOF_RECEIPT_PREFIX,
        code_prefix="candidate_b_default_closure_runtime_downstream_proof",
    )


def _validate_operator_status(value: Any, **expected: str) -> str:
    evidence = _require_mapping(value, "candidate_b_default_closure_operator_status_missing")
    checks = {
        "schema_id": layer3_candidate_b_operator_status.SCHEMA_ID,
        "mode": layer3_candidate_b_operator_status.STATUS_MODE,
        "status": "available",
        "baseline_run_id": expected["baseline_run_id"],
        "candidate_a_run_id": expected["candidate_a_run_id"],
        "candidate_b_bundle_id": expected["candidate_b_bundle_id"],
        "candidate_b_run_id": expected["candidate_b_run_id"],
        "bundle_bridge_receipt_id": expected["bundle_receipt_id"],
        "bundle_bridge_receipt_hash": expected["bundle_hash"],
        "runtime_bridge_receipt_id": expected["runtime_receipt_id"],
        "runtime_bridge_receipt_hash": expected["runtime_hash"],
        "runtime_downstream_proof_hash": expected["runtime_proof_hash"],
    }
    _assert_expected(evidence, checks, "candidate_b_default_closure_operator_status_mismatch")
    missing = [key for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS if key not in evidence]
    if missing:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_operator_status_authority_field_missing",
            "Candidate B operator status evidence is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    status_hash = _stable_hash({key: evidence[key] for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS})
    if evidence.get("operator_status_hash") != status_hash:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_operator_status_hash_mismatch",
            "Candidate B operator status evidence hash is stale or invalid.",
            http_status=409,
            details={"expected": status_hash, "received": evidence.get("operator_status_hash")},
        )
    receipt_id = str(evidence.get("operator_status_receipt_id") or "").strip()
    _validate_storage_id(
        receipt_id,
        prefix=layer3_candidate_b_operator_status.STATUS_RECEIPT_PREFIX,
        code="candidate_b_default_closure_operator_status_receipt_id_invalid",
    )
    path = Path(str(settings.layer3_candidate_b_runtime_bridge_dir)) / expected["runtime_receipt_id"] / "operator-status" / f"{receipt_id}.json"
    _validate_stored_hash(path, hash_field="operator_status_hash", expected_hash=status_hash, code_prefix="candidate_b_default_closure_operator_status")
    return status_hash


def _validate_proof(
    proof: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    hash_keys: tuple[str, ...],
    receipt_root: Path,
    receipt_id: str,
    receipt_prefix: str,
    code_prefix: str,
) -> str:
    _assert_expected(proof, expected, f"{code_prefix}_mismatch")
    missing = [key for key in hash_keys if key not in proof]
    if missing:
        raise CandidateBPromotionClosureError(f"{code_prefix}_authority_field_missing", "Proof is missing authority hash fields.", http_status=409, details={"missing_fields": missing})
    proof_hash = _stable_hash({key: proof[key] for key in hash_keys})
    if proof.get("proof_hash") != proof_hash:
        raise CandidateBPromotionClosureError(f"{code_prefix}_hash_mismatch", "Proof hash is stale or invalid.", http_status=409, details={"expected": proof_hash, "received": proof.get("proof_hash")})
    proof_receipt_id = str(proof.get("proof_receipt_id") or "").strip()
    _validate_storage_id(proof_receipt_id, prefix=receipt_prefix, code=f"{code_prefix}_receipt_id_invalid")
    path = receipt_root / receipt_id / "downstream-proof" / f"{proof_receipt_id}.json"
    _validate_stored_hash(path, hash_field="proof_hash", expected_hash=proof_hash, code_prefix=code_prefix)
    return proof_hash


def _require_mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateBPromotionClosureError(code, "Required Candidate B closure evidence is missing.", http_status=409)
    return value


def _assert_expected(value: Mapping[str, Any], expected: Mapping[str, Any], code: str) -> None:
    mismatches = []
    for field, expected_value in expected.items():
        if str(value.get(field) or "").strip() != str(expected_value or "").strip():
            mismatches.append({"field": field, "expected": expected_value, "received": value.get(field)})
    if mismatches:
        raise CandidateBPromotionClosureError(code, "Candidate B closure evidence does not match selected authority.", http_status=409, details={"mismatches": mismatches})


def _validate_stored_hash(path: Path, *, hash_field: str, expected_hash: str, code_prefix: str) -> None:
    if not path.is_file():
        raise CandidateBPromotionClosureError(f"{code_prefix}_receipt_missing", "Selected persisted receipt is missing.", http_status=409)
    stored = _read_json(path, code=f"{code_prefix}_receipt_unreadable", message="Selected persisted receipt could not be read.")
    if stored.get(hash_field) != expected_hash:
        raise CandidateBPromotionClosureError(f"{code_prefix}_receipt_hash_mismatch", "Selected persisted receipt hash does not match.", http_status=409, details={"expected": expected_hash, "received": stored.get(hash_field)})


def _write_closure_receipt(*, runtime_receipt_id: str, receipt_id: str, payload: Mapping[str, Any]) -> None:
    root = Path(str(settings.layer3_candidate_b_runtime_bridge_dir)) / runtime_receipt_id / "default-promotion-closure"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{receipt_id}.json"
    body = json.dumps(dict(payload), sort_keys=True, indent=2) + "\n"
    if path.is_file():
        existing = _read_json(path, code="candidate_b_default_closure_receipt_unreadable", message="Existing closure receipt could not be read.")
        if existing.get("closure_evidence_hash") != payload.get("closure_evidence_hash"):
            raise CandidateBPromotionClosureError(
                "candidate_b_default_closure_receipt_conflict",
                "A Candidate B default-promotion closure receipt already exists with different contents.",
                http_status=409,
                details={"closure_receipt_id": receipt_id},
            )
        return
    try:
        path.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise CandidateBPromotionClosureError(
            "candidate_b_default_closure_receipt_write_failed",
            "The Candidate B default-promotion closure receipt could not be written.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
