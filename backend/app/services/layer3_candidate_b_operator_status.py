from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_visual_lane_status,
)


SCHEMA_ID = "layer3.candidate_b_default_promotion_operator_status.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "candidate_b_default_promotion_operator_status_v1"
OPERATOR_DECISION = "inspect_candidate_b_default_promotion_operator_status"
STATUS_RECEIPT_PREFIX = "cb-default-operator-status"
CANDIDATE_B_ENGINE = layer3_candidate_b_runtime_bridge.CANDIDATE_B_RUNTIME_VARIANT
CANDIDATE_B_VISUAL_LANE_MODE = layer3_candidate_b_runtime_bridge.CANDIDATE_B_VISUAL_LANE_MODE

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
STATUS_HASH_KEYS = (
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
    "candidate_b_visual_lane_status_hash",
    "runtime_downstream_proof_hash",
    "runtime_delivery_artifact_authority_hash",
    "runtime_delivery_artifact_coverage_steps",
    "runtime_delivery_artifact_projection_visible",
    "runtime_delivery_artifact_roles_bound",
    "operator_visible_provenance_status",
    "bundle_status_projection_visible",
    "runtime_status_projection_visible",
    "default_selector_change_visible_as_enabled",
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


class CandidateBOperatorStatusError(Exception):
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
            "request_id": "candidate-b-operator-status-error",
            "server_time": _server_time(),
            "mode": STATUS_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_default_promotion_operator_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "status_mode")
    if mode != STATUS_MODE:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_mode_not_admitted",
            "Only the Candidate B default-promotion operator-status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_decision_not_admitted",
            "The operator decision does not match the admitted read-only operator-status inspection.",
            details={"expected_operator_decision": OPERATOR_DECISION},
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

    bundle_receipt = _read_receipt("bundle", bundle_receipt_id)
    runtime_receipt = _read_receipt("runtime", runtime_receipt_id)
    bundle_hash = _validate_receipt(
        kind="bundle",
        receipt=bundle_receipt,
        receipt_id=bundle_receipt_id,
        expected={
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": candidate_b_bundle_id,
        },
    )
    runtime_hash = _validate_receipt(
        kind="runtime",
        receipt=runtime_receipt,
        receipt_id=runtime_receipt_id,
        expected={
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_run_id": candidate_b_run_id,
        },
    )
    visual_status_hash = _validate_visual_lane_status(
        fields.get("candidate_b_visual_lane_status_evidence"),
        candidate_b_run_id=candidate_b_run_id,
        runtime_receipt_id=runtime_receipt_id,
        runtime_receipt_hash=runtime_hash,
    )
    runtime_delivery_projection = _validate_runtime_downstream_proof(
        fields.get("runtime_downstream_proof"),
        candidate_b_run_id=candidate_b_run_id,
        runtime_receipt_id=runtime_receipt_id,
        runtime_receipt_hash=runtime_hash,
        retained_artifact_family_hash=str(runtime_receipt.get("governed_retained_artifact_family_hash") or ""),
        visual_status_hash=visual_status_hash,
    )
    status_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": STATUS_MODE,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "candidate_b_run_id": candidate_b_run_id,
        "bundle_bridge_receipt_id": bundle_receipt_id,
        "bundle_bridge_receipt_hash": bundle_hash,
        "runtime_bridge_receipt_id": runtime_receipt_id,
        "runtime_bridge_receipt_hash": runtime_hash,
        "candidate_b_visual_lane_status_hash": visual_status_hash,
        "runtime_downstream_proof_hash": runtime_delivery_projection["runtime_downstream_proof_hash"],
        "runtime_delivery_artifact_authority_hash": runtime_delivery_projection[
            "runtime_delivery_artifact_authority_hash"
        ],
        "runtime_delivery_artifact_coverage_steps": runtime_delivery_projection[
            "runtime_delivery_artifact_coverage_steps"
        ],
        "runtime_delivery_artifact_projection_visible": True,
        "runtime_delivery_artifact_roles_bound": True,
        "operator_visible_provenance_status": True,
        "bundle_status_projection_visible": True,
        "runtime_status_projection_visible": True,
        "default_selector_change_visible_as_enabled": True,
    }
    status_hash = _stable_hash(status_input)
    status_receipt_id = f"{STATUS_RECEIPT_PREFIX}-{status_hash[:24]}"
    response = {
        **status_input,
        "operator_status_hash": status_hash,
        "operator_status_receipt_id": status_receipt_id,
        "operator_status_receipt_ref": (
            f"candidate-b-default-operator-status://{runtime_receipt_id}/{status_receipt_id}.json"
        ),
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "candidate_b_source_kind": "runtime",
        "raw_local_path_exposed": False,
        "provider_private_token_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_promotion_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "use this operator-status evidence in Candidate B default-promotion readiness",
            "continue to final default-promotion readiness audit after regression and rollback evidence remain current",
        ],
    }
    _write_status_receipt(runtime_receipt_id=runtime_receipt_id, receipt_id=status_receipt_id, payload=response)
    return response


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_forbidden_request_fields",
            "Operator-status inspection does not admit caller paths, URLs, selector mutation, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_required_field_missing",
            "A required Candidate B operator-status field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    _validate_storage_id(value, prefix=prefix, code="candidate_b_operator_status_storage_id_invalid")
    return value


def _validate_storage_id(value: str, *, prefix: str, code: str) -> None:
    if (
        not value.startswith(f"{prefix}-")
        or "/" in value
        or "\\" in value
        or ".." in value
        or value in {".", ".."}
    ):
        raise CandidateBOperatorStatusError(
            code,
            "Candidate B operator-status receipt identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _read_receipt(kind: str, receipt_id: str) -> dict[str, Any]:
    configured = (
        settings.layer3_candidate_b_bundle_bridge_dir
        if kind == "bundle"
        else settings.layer3_candidate_b_runtime_bridge_dir
    )
    root = Path(str(configured or ""))
    if not str(configured or "").strip() or not root.is_absolute():
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_dir_invalid",
            "The configured Candidate B bridge directory is missing or not absolute.",
            http_status=409,
            details={"candidate_b_source_kind": kind},
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_receipt_missing",
            "The selected Candidate B bridge receipt is missing.",
            http_status=404,
            details={"candidate_b_source_kind": kind, "bridge_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_receipt_unreadable",
            "The selected Candidate B bridge receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_receipt_invalid",
            "The selected Candidate B bridge receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _validate_receipt(
    *,
    kind: str,
    receipt: Mapping[str, Any],
    receipt_id: str,
    expected: Mapping[str, str],
) -> str:
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
    if kind == "runtime":
        for field, expected_value in {
            "document_processing_engine": CANDIDATE_B_ENGINE,
            "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        }.items():
            if str(receipt.get(field) or "").strip() != expected_value:
                mismatches.append({"field": field, "expected": expected_value, "received": receipt.get(field)})
    if mismatches:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_receipt_mismatch",
            "The selected Candidate B bridge receipt does not match the operator-status target.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    keys = _BUNDLE_HASH_KEYS if kind == "bundle" else _RUNTIME_HASH_KEYS
    missing = [key for key in keys if key not in receipt]
    if missing:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_receipt_authority_field_missing",
            "The selected Candidate B bridge receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in keys})
    if receipt.get("bridge_receipt_hash") != expected_hash:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_bridge_receipt_hash_mismatch",
            "The selected Candidate B bridge receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("bridge_receipt_hash")},
        )
    return expected_hash


def _validate_visual_lane_status(
    value: Any,
    *,
    candidate_b_run_id: str,
    runtime_receipt_id: str,
    runtime_receipt_hash: str,
) -> str:
    if not isinstance(value, Mapping):
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_visual_lane_status_missing",
            "Candidate B visual-lane status evidence is required.",
            http_status=409,
        )
    expected = {
        "schema_id": layer3_candidate_b_visual_lane_status.SCHEMA_ID,
        "mode": layer3_candidate_b_visual_lane_status.STATUS_MODE,
        "status": "available",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": runtime_receipt_id,
        "bridge_receipt_hash": runtime_receipt_hash,
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "visual_lane_status": "available",
    }
    _assert_expected_fields("candidate_b_operator_status_visual_lane_status_mismatch", value, expected)
    projection = value.get("operator_projection")
    if not isinstance(projection, Mapping) or projection.get("candidate_b_visual_lane_status_projection_visible") is not True:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_visual_lane_projection_missing",
            "Candidate B visual-lane status evidence lacks the operator-visible projection.",
            http_status=409,
        )
    for field in ("raw_local_path_exposed", "raw_url_exposed", "artifact_bytes_exposed"):
        if projection.get(field) is not False:
            raise CandidateBOperatorStatusError(
                "candidate_b_operator_status_visual_lane_projection_exposes_authority",
                "Candidate B visual-lane status evidence exposes non-admitted authority.",
                http_status=409,
                details={"field": field},
            )
    return _stable_hash(value)


def _validate_runtime_downstream_proof(
    value: Any,
    *,
    candidate_b_run_id: str,
    runtime_receipt_id: str,
    runtime_receipt_hash: str,
    retained_artifact_family_hash: str,
    visual_status_hash: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_missing",
            "Candidate B runtime downstream proof evidence is required.",
            http_status=409,
        )
    expected = {
        "schema_id": layer3_candidate_b_downstream_proof.SCHEMA_ID,
        "mode": layer3_candidate_b_downstream_proof.PROOF_MODE,
        "status": "proven",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": runtime_receipt_id,
        "bridge_receipt_hash": runtime_receipt_hash,
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "candidate_b_visual_lane_status_hash": visual_status_hash,
        "proof_state": layer3_candidate_b_downstream_proof.PROOF_STATE,
    }
    _assert_expected_fields("candidate_b_operator_status_runtime_downstream_proof_mismatch", value, expected)
    missing = [key for key in layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS if key not in value]
    if missing:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_authority_field_missing",
            "Candidate B runtime downstream proof is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: value[key] for key in layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS})
    if value.get("proof_hash") != expected_hash:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_hash_mismatch",
            "Candidate B runtime downstream proof hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": value.get("proof_hash")},
        )
    _validate_runtime_downstream_proof_receipt(runtime_receipt_id, str(value.get("proof_receipt_id") or ""), expected_hash)
    delivery_steps = _validate_runtime_delivery_artifact_projection(
        value.get("coverage_evidence"),
        retained_artifact_family_hash=retained_artifact_family_hash,
    )
    return {
        "runtime_downstream_proof_hash": expected_hash,
        "runtime_delivery_artifact_authority_hash": retained_artifact_family_hash,
        "runtime_delivery_artifact_coverage_steps": delivery_steps,
    }


def _validate_runtime_delivery_artifact_projection(
    value: Any,
    *,
    retained_artifact_family_hash: str,
) -> list[str]:
    if not isinstance(value, Mapping):
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_delivery_artifact_coverage_missing",
            "Candidate B operator status requires delivery artifact authority coverage from the runtime downstream proof.",
            http_status=409,
        )
    missing = []
    for step in sorted(layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE):
        entry = value.get(step)
        if not isinstance(entry, Mapping):
            missing.append(step)
            continue
        received_hash = str(entry.get("candidate_b_retained_artifact_family_hash") or "").strip()
        if received_hash != retained_artifact_family_hash:
            raise CandidateBOperatorStatusError(
                "candidate_b_operator_status_runtime_delivery_artifact_authority_mismatch",
                "Candidate B operator status requires delivery proof coverage to bind the retained artifact-family authority hash.",
                http_status=409,
                details={
                    "coverage_step": step,
                    "expected": retained_artifact_family_hash,
                    "received": received_hash or None,
                },
            )
        if entry.get("candidate_b_delivery_artifact_roles_bound") is not True:
            raise CandidateBOperatorStatusError(
                "candidate_b_operator_status_runtime_delivery_artifact_roles_not_bound",
                "Candidate B operator status requires delivery proof coverage to bind retained delivery/product artifact roles.",
                http_status=409,
                details={"coverage_step": step},
            )
    if missing:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_delivery_artifact_coverage_incomplete",
            "Candidate B operator status is missing delivery artifact authority coverage steps.",
            http_status=409,
            details={"missing_coverage": missing},
        )
    return sorted(layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE)


def _validate_runtime_downstream_proof_receipt(
    runtime_receipt_id: str,
    proof_receipt_id: str,
    expected_hash: str,
) -> None:
    if not proof_receipt_id:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_receipt_id_missing",
            "Candidate B runtime downstream proof receipt id is missing.",
            http_status=409,
        )
    _validate_storage_id(
        proof_receipt_id,
        prefix=layer3_candidate_b_downstream_proof.PROOF_RECEIPT_PREFIX,
        code="candidate_b_operator_status_runtime_downstream_proof_receipt_id_invalid",
    )
    path = (
        Path(str(settings.layer3_candidate_b_runtime_bridge_dir))
        / runtime_receipt_id
        / "downstream-proof"
        / f"{proof_receipt_id}.json"
    )
    if not path.is_file():
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_receipt_missing",
            "Candidate B runtime downstream proof receipt is missing.",
            http_status=409,
            details={"proof_receipt_id": proof_receipt_id},
        )
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_receipt_unreadable",
            "Candidate B runtime downstream proof receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(stored, dict) or stored.get("proof_hash") != expected_hash:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_runtime_downstream_proof_receipt_hash_mismatch",
            "Candidate B runtime downstream proof receipt hash does not match the selected proof.",
            http_status=409,
            details={"expected": expected_hash, "received": stored.get("proof_hash") if isinstance(stored, dict) else None},
        )


def _assert_expected_fields(code: str, value: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    mismatches = []
    for field, expected_value in expected.items():
        if str(value.get(field) or "").strip() != str(expected_value or "").strip():
            mismatches.append({"field": field, "expected": expected_value, "received": value.get(field)})
    if mismatches:
        raise CandidateBOperatorStatusError(
            code,
            "Candidate B operator-status evidence does not match the selected authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _write_status_receipt(*, runtime_receipt_id: str, receipt_id: str, payload: Mapping[str, Any]) -> None:
    root = Path(str(settings.layer3_candidate_b_runtime_bridge_dir)) / runtime_receipt_id / "operator-status"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{receipt_id}.json"
    body = json.dumps(dict(payload), sort_keys=True, indent=2) + "\n"
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CandidateBOperatorStatusError(
                "candidate_b_operator_status_receipt_unreadable",
                "The existing Candidate B operator-status receipt could not be read.",
                http_status=409,
                details={"reason": str(exc)},
            ) from exc
        if not isinstance(existing, dict) or existing.get("operator_status_hash") != payload.get("operator_status_hash"):
            raise CandidateBOperatorStatusError(
                "candidate_b_operator_status_receipt_conflict",
                "A Candidate B operator-status receipt already exists with a different hash.",
                http_status=409,
                details={"operator_status_receipt_id": receipt_id},
            )
        return
    try:
        path.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise CandidateBOperatorStatusError(
            "candidate_b_operator_status_receipt_write_failed",
            "The Candidate B operator-status receipt could not be written.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
