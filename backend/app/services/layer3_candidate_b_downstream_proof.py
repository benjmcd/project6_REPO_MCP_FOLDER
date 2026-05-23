from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_runtime_bridge, layer3_candidate_b_visual_lane_status


SCHEMA_ID = "layer3.candidate_b_runtime_downstream_proof.v1"
SCHEMA_VERSION = 1
PROOF_MODE = "candidate_b_visual_lane_runtime_downstream_e2e_proof_v1"
OPERATOR_DECISION = "record_candidate_b_visual_lane_runtime_downstream_e2e_proof"
PROOF_STATE = "candidate_b_layer3_downstream_e2e_proven"
PROOF_RECEIPT_PREFIX = "cb-runtime-downstream-proof"
CANDIDATE_B_ENGINE = layer3_candidate_b_runtime_bridge.CANDIDATE_B_RUNTIME_VARIANT
CANDIDATE_B_VISUAL_LANE_MODE = layer3_candidate_b_runtime_bridge.CANDIDATE_B_VISUAL_LANE_MODE

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
_ADMITTED_RUNTIME_BRIDGE_MODES = (
    layer3_candidate_b_runtime_bridge.BRIDGE_MODE,
    layer3_candidate_b_runtime_bridge.FULL_CORPUS_BRIDGE_MODE,
)
PROOF_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "candidate_b_source_kind",
    "candidate_b_run_id",
    "bridge_receipt_id",
    "bridge_receipt_hash",
    "document_processing_engine",
    "visual_lane_mode",
    "candidate_b_visual_lane_status_hash",
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
DELIVERY_ARTIFACT_AUTHORITY_COVERAGE = frozenset(
    {
        "external_export_download_prepare",
        "same_origin_delivery_status",
        "same_origin_delivery",
        "provider_private_prepare",
        "provider_private_status",
        "provider_private_use",
        "provider_private_revoke",
        "internal_webhook_dispatch",
        "internal_webhook_status",
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


class CandidateBDownstreamProofError(Exception):
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
            "request_id": "candidate-b-downstream-proof-error",
            "server_time": _server_time(),
            "mode": PROOF_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_runtime_downstream_proof(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "proof_mode")
    if mode != PROOF_MODE:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_mode_not_admitted",
            "Only the Candidate B visual-lane runtime downstream proof mode is admitted.",
            details={"expected_proof_mode": PROOF_MODE, "received_proof_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_operator_decision_not_admitted",
            "The operator decision does not match the admitted downstream proof recording.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    if fields.get("operator_confirmation") is not True:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_operator_confirmation_required",
            "operator_confirmation=true is required before recording Candidate B downstream proof.",
            details={"operator_confirmation_required": True},
        )

    candidate_b_run_id = _required(fields, "candidate_b_run_id")
    receipt_id = _required(fields, "bridge_receipt_id")
    receipt = _read_receipt(receipt_id)
    _validate_receipt(candidate_b_run_id, receipt_id, receipt)
    visual_status_hash = _validate_visual_lane_status(
        fields.get("candidate_b_visual_lane_status_evidence"),
        candidate_b_run_id=candidate_b_run_id,
        receipt_id=receipt_id,
        receipt_hash=receipt["bridge_receipt_hash"],
    )
    coverage = _validate_coverage_evidence(
        fields.get("coverage_evidence"),
        retained_artifact_family_hash=str(receipt.get("governed_retained_artifact_family_hash") or ""),
    )
    negative_invariants = _negative_invariants()
    negative_invariants_hash = _stable_hash(negative_invariants)
    coverage_hash = _stable_hash(coverage)
    proof_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROOF_MODE,
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt["bridge_receipt_hash"],
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "candidate_b_visual_lane_status_hash": visual_status_hash,
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
        "proof_receipt_ref": f"candidate-b-runtime-downstream-proof://{receipt_id}/{proof_receipt_id}.json",
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
        "visual_lane_mode_enabled": True,
        "negative_invariants": negative_invariants,
        "next_allowed_actions": [
            "use this proof as Candidate B runtime downstream proof evidence",
            "run Candidate B default-promotion readiness audit with the matching runtime bridge receipt",
        ],
    }
    _write_proof_receipt(receipt_id=receipt_id, proof_receipt_id=proof_receipt_id, proof=proof)
    return proof


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    nested_blocked = _find_forbidden_nested_fields(fields)
    if blocked or nested_blocked:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_forbidden_request_fields",
            "Downstream proof recording does not admit caller paths, URLs, file bytes, selector overrides, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked, "blocked_nested_fields": nested_blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_required_field_missing",
            "A required Candidate B downstream proof field is missing or empty.",
            details={"field": key},
        )
    return value


def _read_receipt(receipt_id: str) -> dict[str, Any]:
    configured = settings.layer3_candidate_b_runtime_bridge_dir
    if not str(configured or "").strip():
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_dir_unset",
            "The configured Candidate B runtime bridge directory is not set.",
        )
    root = Path(str(configured))
    if not root.is_absolute():
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_dir_not_absolute",
            "The configured Candidate B runtime bridge directory must be absolute.",
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_receipt_missing",
            "The selected Candidate B runtime bridge receipt is missing.",
            http_status=404,
            details={"bridge_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_receipt_unreadable",
            "The selected Candidate B runtime bridge receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_receipt_invalid",
            "The selected Candidate B runtime bridge receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _validate_receipt(candidate_b_run_id: str, receipt_id: str, receipt: Mapping[str, Any]) -> None:
    mismatches = []
    for field, expected in {
        "schema_id": layer3_candidate_b_runtime_bridge.SCHEMA_ID,
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": receipt_id,
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
    }.items():
        if str(receipt.get(field) or "").strip() != expected:
            mismatches.append({"field": field, "expected": expected, "received": receipt.get(field)})
    if mismatches:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_receipt_mismatch",
            "The selected Candidate B runtime bridge receipt does not match the requested downstream proof target.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    if str(receipt.get("bridge_mode") or "") not in _ADMITTED_RUNTIME_BRIDGE_MODES:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_mode_not_admitted",
            "The selected Candidate B runtime bridge receipt uses an unadmitted bridge mode.",
            http_status=409,
            details={
                "received_bridge_mode": receipt.get("bridge_mode"),
                "admitted_bridge_modes": list(_ADMITTED_RUNTIME_BRIDGE_MODES),
            },
        )
    missing = [key for key in _RUNTIME_HASH_KEYS if key not in receipt]
    if missing:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_receipt_authority_field_missing",
            "The selected Candidate B runtime bridge receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in _RUNTIME_HASH_KEYS})
    if receipt.get("bridge_receipt_hash") != expected_hash:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_bridge_receipt_hash_mismatch",
            "The selected Candidate B runtime bridge receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("bridge_receipt_hash")},
        )

    visual_evidence = receipt.get("candidate_b_visual_lane_evidence")
    if not isinstance(visual_evidence, dict):
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_evidence_missing",
            "The selected Candidate B runtime bridge receipt has no visual-lane evidence.",
            http_status=409,
        )
    if str(visual_evidence.get("visual_lane_mode") or "").strip() != CANDIDATE_B_VISUAL_LANE_MODE:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_evidence_mode_mismatch",
            "The Candidate B visual-lane evidence does not match the admitted visual-lane mode.",
            http_status=409,
            details={"expected": CANDIDATE_B_VISUAL_LANE_MODE, "received": visual_evidence.get("visual_lane_mode")},
        )
    if visual_evidence.get("candidate_b_visual_lane_selected") is not True:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_not_selected",
            "The selected runtime bridge receipt did not select the Candidate B visual lane.",
            http_status=409,
        )


def _validate_visual_lane_status(
    value: Any,
    *,
    candidate_b_run_id: str,
    receipt_id: str,
    receipt_hash: str,
) -> str:
    if not isinstance(value, dict):
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_status_evidence_missing",
            "Candidate B visual-lane status evidence is required.",
            http_status=409,
        )
    mismatches = []
    for field, expected in {
        "schema_id": layer3_candidate_b_visual_lane_status.SCHEMA_ID,
        "mode": layer3_candidate_b_visual_lane_status.STATUS_MODE,
        "status": "available",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "visual_lane_status": "available",
    }.items():
        if str(value.get(field) or "").strip() != str(expected or "").strip():
            mismatches.append({"field": field, "expected": expected, "received": value.get(field)})
    if mismatches:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_status_mismatch",
            "Candidate B visual-lane status evidence does not match the selected runtime bridge receipt.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    visual_evidence = value.get("candidate_b_visual_lane_evidence")
    if not isinstance(visual_evidence, dict) or visual_evidence.get("candidate_b_visual_lane_selected") is not True:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_status_not_selected",
            "Candidate B visual-lane status evidence does not prove Candidate B visual-lane selection.",
            http_status=409,
        )
    for field in ("visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"):
        if int(visual_evidence.get(field) or 0) <= 0:
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_visual_lane_status_evidence_count_missing",
                "Candidate B visual-lane status evidence does not prove retained visual/page evidence.",
                http_status=409,
                details={"field": field},
            )
    operator_projection = value.get("operator_projection")
    if not isinstance(operator_projection, dict):
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_visual_lane_status_operator_projection_missing",
            "Candidate B visual-lane status evidence has no operator projection.",
            http_status=409,
        )
    for field in ("visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"):
        if int(operator_projection.get(field) or 0) <= 0:
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_visual_lane_status_projection_count_missing",
                "Candidate B visual-lane status operator projection does not show retained visual/page evidence.",
                http_status=409,
                details={"field": field},
            )
    for field in ("raw_local_path_exposed", "raw_url_exposed", "artifact_bytes_exposed"):
        if operator_projection.get(field) is not False:
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_visual_lane_status_exposes_authority",
                "Candidate B visual-lane status evidence exposes non-admitted authority.",
                http_status=409,
                details={"field": field},
            )
    return _stable_hash(value)


def _validate_coverage_evidence(
    value: Any,
    *,
    retained_artifact_family_hash: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_coverage_evidence_missing",
            "Structured per-step downstream coverage evidence is required.",
            http_status=409,
        )
    missing = sorted(step for step in REQUIRED_COVERAGE if step not in value)
    if missing:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_coverage_incomplete",
            "Candidate B downstream proof evidence is missing required coverage steps.",
            http_status=409,
            details={"missing_coverage": missing},
        )
    coverage: dict[str, dict[str, Any]] = {}
    for step in sorted(REQUIRED_COVERAGE):
        item = value.get(step)
        if not isinstance(item, dict):
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_coverage_item_invalid",
                "Each Candidate B downstream proof coverage item must be an object.",
                http_status=409,
                details={"coverage_step": step},
            )
        if str(item.get("status") or "").strip() != "proven":
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_coverage_item_not_proven",
                "Each Candidate B downstream proof coverage item must be marked proven.",
                http_status=409,
                details={"coverage_step": step, "received": item.get("status")},
            )
        for field in (
            "raw_local_path_exposed",
            "raw_url_exposed",
            "provider_private_token_exposed",
            "provider_public_url_enabled",
            "provider_object_writes_enabled",
            "connector_dispatch_enabled",
            "rag_vector_model_runtime_enabled",
            "browser_storage_authority_enabled",
            "frontend_durable_authority_enabled",
        ):
            if item.get(field) is True:
                raise CandidateBDownstreamProofError(
                    "candidate_b_downstream_proof_coverage_exposes_forbidden_authority",
                    "Candidate B downstream proof coverage exposes non-admitted authority.",
                    http_status=409,
                    details={"coverage_step": step, "field": field},
                )
        evidence_ref = str(item.get("evidence_ref") or f"candidate-b-downstream-proof://{step}")
        if evidence_ref.lower().startswith(("http://", "https://", "file://")):
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_coverage_exposes_forbidden_reference",
                "Candidate B downstream proof coverage cannot expose raw URL or file references.",
                http_status=409,
                details={"coverage_step": step},
            )
        delivery_authority: dict[str, Any] = {}
        if step in DELIVERY_ARTIFACT_AUTHORITY_COVERAGE:
            received_artifact_hash = str(item.get("candidate_b_retained_artifact_family_hash") or "").strip()
            if received_artifact_hash != retained_artifact_family_hash:
                raise CandidateBDownstreamProofError(
                    "candidate_b_downstream_proof_delivery_artifact_authority_mismatch",
                    "Delivery-facing Candidate B downstream proof must bind to the retained artifact-family authority hash.",
                    http_status=409,
                    details={
                        "coverage_step": step,
                        "expected": retained_artifact_family_hash,
                        "received": received_artifact_hash or None,
                    },
                )
            if item.get("candidate_b_delivery_artifact_roles_bound") is not True:
                raise CandidateBDownstreamProofError(
                    "candidate_b_downstream_proof_delivery_artifact_roles_not_bound",
                    "Delivery-facing Candidate B downstream proof must bind retained delivery/product artifact roles.",
                    http_status=409,
                    details={"coverage_step": step},
                )
            delivery_authority = {
                "candidate_b_retained_artifact_family_hash": retained_artifact_family_hash,
                "candidate_b_delivery_artifact_roles_bound": True,
            }
        coverage[step] = {
            "status": "proven",
            "evidence_ref": evidence_ref,
            "evidence_hash": str(item.get("evidence_hash") or _stable_hash({"step": step, "status": "proven"})),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "connector_dispatch_enabled": False,
            **delivery_authority,
        }
    return coverage


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in _FORBIDDEN_NESTED_FIELDS and item is not None:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_forbidden_nested_fields(item, f"{prefix}[{index}]"))
    return sorted(set(found))


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "source_expansion_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "candidate_b_visual_lane_material_ingestion_enabled": False,
        "source_pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposure_enabled": False,
        "provider_private_token_exposed": False,
        "provider_public_url_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _write_proof_receipt(*, receipt_id: str, proof_receipt_id: str, proof: Mapping[str, Any]) -> None:
    root = Path(str(settings.layer3_candidate_b_runtime_bridge_dir)) / receipt_id / "downstream-proof"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{proof_receipt_id}.json"
    body = json.dumps(dict(proof), sort_keys=True, indent=2) + "\n"
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_receipt_unreadable",
                "The existing Candidate B downstream proof receipt could not be read.",
                http_status=409,
                details={"reason": str(exc)},
            ) from exc
        if not isinstance(existing, dict) or existing.get("proof_hash") != proof.get("proof_hash"):
            raise CandidateBDownstreamProofError(
                "candidate_b_downstream_proof_receipt_conflict",
                "A Candidate B downstream proof receipt already exists with different contents.",
                http_status=409,
                details={"proof_receipt_id": proof_receipt_id},
            )
        return
    try:
        path.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise CandidateBDownstreamProofError(
            "candidate_b_downstream_proof_receipt_write_failed",
            "The Candidate B downstream proof receipt could not be written.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
