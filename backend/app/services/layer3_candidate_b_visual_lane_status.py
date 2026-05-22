from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_runtime_bridge


SCHEMA_ID = "layer3.candidate_b_visual_lane_status.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "candidate_b_visual_lane_status_v1"
OPERATOR_DECISION = "inspect_candidate_b_visual_lane_evidence_status"
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
    "provider_private_url",
    "provider_private_signed_url_token",
    "provider_public_url",
    "connector_dispatch",
    "browser_storage",
}


class CandidateBVisualLaneStatusError(Exception):
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
            "request_id": "candidate-b-visual-lane-status-error",
            "server_time": _server_time(),
            "mode": STATUS_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_visual_lane_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "status_mode")
    if mode != STATUS_MODE:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_mode_not_admitted",
            "Only the Candidate B visual-lane status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_operator_decision_not_admitted",
            "The operator decision does not match the admitted read-only visual-lane status inspection.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    candidate_b_run_id = _required(fields, "candidate_b_run_id")
    receipt_id = _required_receipt_id(
        fields,
        "bridge_receipt_id",
        layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
    )
    receipt = _read_receipt(receipt_id)
    _validate_receipt(candidate_b_run_id, receipt_id, receipt)
    visual_evidence = receipt["candidate_b_visual_lane_evidence"]

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "mode": STATUS_MODE,
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_ref": f"candidate-b-runtime-bridge://{receipt_id}/receipt.json",
        "bridge_receipt_hash": receipt["bridge_receipt_hash"],
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "visual_lane_status": "available",
        "candidate_b_visual_lane_evidence": _visual_evidence_projection(visual_evidence),
        "operator_projection": {
            "candidate_b_visual_lane_status_projection_visible": True,
            "candidate_b_visual_lane_selected": True,
            "visual_ref_total": int(visual_evidence.get("visual_ref_total") or 0),
            "candidate_b_visual_ref_total": int(visual_evidence.get("candidate_b_visual_ref_total") or 0),
            "candidate_b_retained_source_pdf_ref_count": int(
                visual_evidence.get("candidate_b_retained_source_pdf_ref_count") or 0
            ),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "material_policy": {
            "source_pdf_material_text_payload_enabled": False,
            "image_material_text_payload_enabled": False,
            "visual_lane_material_ingestion_enabled": False,
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_promotion_enabled": False,
            "candidate_b_visual_lane_material_ingestion_enabled": False,
            "source_pdf_material_text_payload_enabled": False,
            "image_material_text_payload_enabled": False,
            "raw_url_exposure_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "use this status as Candidate B visual-lane operator projection evidence",
            "run Candidate B default-promotion readiness audit after downstream proof is current",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_forbidden_request_fields",
            "Visual-lane status inspection does not admit caller paths, URLs, file bytes, selector overrides, connectors, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_required_field_missing",
            "A required Candidate B visual-lane status field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_receipt_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    if not value.startswith(f"{prefix}-") or "/" in value or "\\" in value or ".." in value or value in {".", ".."}:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_id_invalid",
            "Candidate B visual-lane status requires a server-owned runtime bridge receipt identifier.",
            http_status=409,
            details={"expected_prefix": prefix},
        )
    return value


def _read_receipt(receipt_id: str) -> dict[str, Any]:
    configured = settings.layer3_candidate_b_runtime_bridge_dir
    if not str(configured or "").strip():
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_dir_unset",
            "The configured Candidate B runtime bridge directory is not set.",
        )
    root = Path(str(configured))
    if not root.is_absolute():
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_dir_not_absolute",
            "The configured Candidate B runtime bridge directory must be absolute.",
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_missing",
            "The selected Candidate B runtime bridge receipt is missing.",
            http_status=404,
            details={"bridge_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_unreadable",
            "The selected Candidate B runtime bridge receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_invalid",
            "The selected Candidate B runtime bridge receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _validate_receipt(candidate_b_run_id: str, receipt_id: str, receipt: Mapping[str, Any]) -> None:
    mismatches = []
    for field, expected in {
        "schema_id": layer3_candidate_b_runtime_bridge.SCHEMA_ID,
        "bridge_mode": layer3_candidate_b_runtime_bridge.BRIDGE_MODE,
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": receipt_id,
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
    }.items():
        if str(receipt.get(field) or "").strip() != expected:
            mismatches.append({"field": field, "expected": expected, "received": receipt.get(field)})
    if mismatches:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_mismatch",
            "The selected Candidate B runtime bridge receipt does not match the requested visual-lane status target.",
            http_status=409,
            details={"mismatches": mismatches},
        )

    missing = [key for key in _RUNTIME_HASH_KEYS if key not in receipt]
    if missing:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_authority_field_missing",
            "The selected Candidate B runtime bridge receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in _RUNTIME_HASH_KEYS})
    if receipt.get("bridge_receipt_hash") != expected_hash:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_bridge_receipt_hash_mismatch",
            "The selected Candidate B runtime bridge receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("bridge_receipt_hash")},
        )

    visual_evidence = receipt.get("candidate_b_visual_lane_evidence")
    if not isinstance(visual_evidence, dict):
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_evidence_missing",
            "The selected Candidate B runtime bridge receipt has no visual-lane evidence.",
            http_status=409,
        )
    if str(visual_evidence.get("visual_lane_mode") or "").strip() != CANDIDATE_B_VISUAL_LANE_MODE:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_evidence_mode_mismatch",
            "The Candidate B visual-lane evidence does not match the admitted visual-lane mode.",
            http_status=409,
            details={"expected": CANDIDATE_B_VISUAL_LANE_MODE, "received": visual_evidence.get("visual_lane_mode")},
        )
    if visual_evidence.get("candidate_b_visual_lane_selected") is not True:
        raise CandidateBVisualLaneStatusError(
            "candidate_b_visual_lane_status_not_selected",
            "The selected runtime bridge receipt did not select the Candidate B visual lane.",
            http_status=409,
        )
    for field in ("source_pdf_material_text_payload_enabled", "image_material_text_payload_enabled"):
        if visual_evidence.get(field) is not False:
            raise CandidateBVisualLaneStatusError(
                "candidate_b_visual_lane_status_material_invariant_failed",
                "The Candidate B visual-lane evidence enables a non-admitted material payload.",
                http_status=409,
                details={"field": field},
            )


def _visual_evidence_projection(visual_evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "visual_lane_mode": visual_evidence.get("visual_lane_mode"),
        "candidate_b_visual_lane_selected": visual_evidence.get("candidate_b_visual_lane_selected") is True,
        "candidate_b_visual_lane_mode": visual_evidence.get("candidate_b_visual_lane_mode"),
        "visual_ref_total": int(visual_evidence.get("visual_ref_total") or 0),
        "candidate_b_visual_ref_total": int(visual_evidence.get("candidate_b_visual_ref_total") or 0),
        "candidate_b_retained_source_pdf_ref_count": int(
            visual_evidence.get("candidate_b_retained_source_pdf_ref_count") or 0
        ),
        "source_pdf_material_text_payload_enabled": visual_evidence.get("source_pdf_material_text_payload_enabled")
        is True,
        "image_material_text_payload_enabled": visual_evidence.get("image_material_text_payload_enabled") is True,
        "evidence_source": visual_evidence.get("evidence_source"),
    }


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
