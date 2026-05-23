from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_bundle_bridge, layer3_candidate_b_runtime_bridge


SCHEMA_ID = "layer3.candidate_b_retained_artifact_family_status.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "candidate_b_retained_artifact_family_status_v1"
OPERATOR_DECISION = "inspect_candidate_b_governed_retained_artifact_family_status"
_SOURCE_KINDS = frozenset({"bundle", "runtime"})

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
    "provider_private_url",
    "provider_private_signed_url_token",
    "provider_public_url",
    "connector_dispatch",
    "browser_storage",
}


class CandidateBArtifactStatusError(Exception):
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
            "request_id": "candidate-b-artifact-status-error",
            "server_time": _server_time(),
            "mode": STATUS_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_retained_artifact_family_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "status_mode")
    if mode != STATUS_MODE:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_mode_not_admitted",
            "Only the Candidate B retained artifact-family status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_operator_decision_not_admitted",
            "The operator decision does not match the admitted read-only artifact-family status inspection.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    source_kind = _required(fields, "candidate_b_source_kind")
    if source_kind not in _SOURCE_KINDS:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_source_kind_not_admitted",
            "Candidate B artifact status only admits bundle or runtime bridge receipts.",
            details={"received_candidate_b_source_kind": source_kind},
        )
    receipt_id = _required_receipt_id(fields, "bridge_receipt_id", _receipt_prefix(source_kind))
    receipt = _read_receipt(source_kind, receipt_id)
    _validate_receipt(source_kind, receipt_id, receipt)
    artifact_family = receipt["governed_retained_artifact_family"]
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "mode": STATUS_MODE,
        "candidate_b_source_kind": source_kind,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_ref": f"candidate-b-{source_kind}-bridge://{receipt_id}/receipt.json",
        "bridge_receipt_hash": receipt["bridge_receipt_hash"],
        "governed_retained_artifact_family_hash": receipt["governed_retained_artifact_family_hash"],
        "artifact_family_status": "available",
        "governed_retained_artifact_family": _artifact_family_projection(artifact_family),
        "operator_projection": {
            "role_counts": artifact_family.get("role_counts", {}),
            "role_previews": _role_previews(artifact_family),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "material_text_payload_policy": artifact_family.get("material_text_payload_policy"),
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_promotion_enabled": False,
            "pdf_material_text_payload_enabled": artifact_family.get("pdf_material_text_payload_enabled") is True,
            "image_material_text_payload_enabled": artifact_family.get("image_material_text_payload_enabled") is True,
            "raw_url_exposure_enabled": artifact_family.get("raw_url_exposure_enabled") is True,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "inspect role counts and redacted artifact refs",
            "use existing Candidate B bridge curated material root for Layer 3 material preview",
            "run Candidate B default-promotion readiness audit after downstream proof is current",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_forbidden_request_fields",
            "Artifact-family status inspection does not admit caller paths, URLs, file bytes, connectors, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_required_field_missing",
            "A required Candidate B artifact status field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_receipt_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    if not value.startswith(f"{prefix}-") or "/" in value or "\\" in value or ".." in value or value in {".", ".."}:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_receipt_id_invalid",
            "Candidate B artifact status requires a server-owned bridge receipt identifier.",
            http_status=409,
            details={"expected_prefix": prefix},
        )
    return value


def _receipt_prefix(source_kind: str) -> str:
    return (
        layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX
        if source_kind == "bundle"
        else layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX
    )


def _read_receipt(source_kind: str, receipt_id: str) -> dict[str, Any]:
    configured = (
        settings.layer3_candidate_b_bundle_bridge_dir
        if source_kind == "bundle"
        else settings.layer3_candidate_b_runtime_bridge_dir
    )
    if not str(configured or "").strip():
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_dir_unset",
            "The configured Candidate B bridge directory is not set.",
            details={"candidate_b_source_kind": source_kind},
        )
    root = Path(str(configured))
    if not root.is_absolute():
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_dir_not_absolute",
            "The configured Candidate B bridge directory must be absolute.",
            details={"candidate_b_source_kind": source_kind},
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_receipt_missing",
            "The selected Candidate B bridge receipt is missing.",
            http_status=404,
            details={"candidate_b_source_kind": source_kind, "bridge_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_receipt_unreadable",
            "The selected Candidate B bridge receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_receipt_invalid",
            "The selected Candidate B bridge receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _validate_receipt(source_kind: str, receipt_id: str, receipt: Mapping[str, Any]) -> None:
    expected_schema = (
        layer3_candidate_b_bundle_bridge.SCHEMA_ID
        if source_kind == "bundle"
        else layer3_candidate_b_runtime_bridge.SCHEMA_ID
    )
    expected_mode = (
        layer3_candidate_b_bundle_bridge.BRIDGE_MODE
        if source_kind == "bundle"
        else layer3_candidate_b_runtime_bridge.BRIDGE_MODE
    )
    mismatches = []
    for field, expected in {
        "schema_id": expected_schema,
        "bridge_mode": expected_mode,
        "candidate_b_source_kind": source_kind,
        "bridge_receipt_id": receipt_id,
    }.items():
        if str(receipt.get(field) or "").strip() != expected:
            mismatches.append({"field": field, "expected": expected, "received": receipt.get(field)})
    if mismatches:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_bridge_receipt_mismatch",
            "The selected Candidate B bridge receipt does not match the requested artifact status target.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    artifact_family = receipt.get("governed_retained_artifact_family")
    if not isinstance(artifact_family, dict):
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_governed_artifact_family_missing",
            "The selected Candidate B bridge receipt does not contain governed retained artifact-family evidence.",
            http_status=409,
        )
    expected_hash = str(receipt.get("governed_retained_artifact_family_hash") or "").strip()
    received_hash = str(artifact_family.get("artifact_family_hash") or "").strip()
    if len(expected_hash) != 64 or received_hash != expected_hash:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_governed_artifact_family_hash_mismatch",
            "The governed retained artifact-family evidence does not match the bridge receipt authority hash.",
            http_status=409,
            details={"expected": expected_hash or None, "received": received_hash or None},
        )
    recomputed_hash = _artifact_family_hash(source_kind, artifact_family)
    if recomputed_hash != expected_hash:
        raise CandidateBArtifactStatusError(
            "candidate_b_artifact_status_governed_artifact_family_stale",
            "The governed retained artifact-family evidence no longer matches its authority hash.",
            http_status=409,
            details={"expected": expected_hash, "received": recomputed_hash},
        )
    for field in ("pdf_material_text_payload_enabled", "image_material_text_payload_enabled", "raw_url_exposure_enabled"):
        if artifact_family.get(field) is not False:
            raise CandidateBArtifactStatusError(
                "candidate_b_artifact_status_governed_artifact_family_invariant_failed",
                "The governed artifact family enables a non-admitted material or URL authority.",
                http_status=409,
                details={"field": field},
            )


def _artifact_family_projection(artifact_family: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy": artifact_family.get("policy"),
        "candidate_b_source_kind": artifact_family.get("candidate_b_source_kind"),
        "artifact_family_hash": artifact_family.get("artifact_family_hash"),
        "role_counts": artifact_family.get("role_counts") if isinstance(artifact_family.get("role_counts"), dict) else {},
        "pdf_material_text_payload_enabled": artifact_family.get("pdf_material_text_payload_enabled") is True,
        "image_material_text_payload_enabled": artifact_family.get("image_material_text_payload_enabled") is True,
        "raw_url_exposure_enabled": artifact_family.get("raw_url_exposure_enabled") is True,
    }


def _role_previews(artifact_family: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    roles = artifact_family.get("roles") if isinstance(artifact_family.get("roles"), dict) else {}
    previews = {
        str(role): [_artifact_ref_preview(item) for item in list(items)[:10] if isinstance(item, Mapping)]
        for role, items in roles.items()
        if isinstance(items, list)
    }
    _validate_redacted_role_previews(previews)
    return previews


def _artifact_ref_preview(item: Mapping[str, Any]) -> dict[str, Any]:
    source_ref = str(item.get("source_ref") or item.get("relative_name") or "").replace("\\", "/").strip()
    display_ref = source_ref.rsplit("/", 1)[-1] if source_ref else None
    return {
        "display_ref": display_ref,
        "artifact_role": item.get("artifact_role"),
        "category": item.get("category"),
        "extension": item.get("extension"),
        "sha256": item.get("sha256"),
        "size_bytes": item.get("size_bytes"),
        "material_text_payload": item.get("material_text_payload") is True,
    }


def _validate_redacted_role_previews(role_previews: Mapping[str, Any]) -> None:
    for role, previews in role_previews.items():
        if not isinstance(previews, list):
            continue
        for index, preview in enumerate(previews):
            if not isinstance(preview, Mapping):
                raise CandidateBArtifactStatusError(
                    "candidate_b_artifact_status_role_preview_invalid",
                    "Candidate B artifact-family status generated an invalid retained artifact preview.",
                    http_status=409,
                    details={"role": role, "index": index},
                )
            display_ref = str(preview.get("display_ref") or "").strip()
            if not display_ref or "/" in display_ref or "\\" in display_ref or ".." in display_ref:
                raise CandidateBArtifactStatusError(
                    "candidate_b_artifact_status_role_preview_not_redacted",
                    "Candidate B artifact-family status previews must use redacted display refs only.",
                    http_status=409,
                    details={"role": role, "index": index},
                )


def _artifact_family_hash(source_kind: str, artifact_family: Mapping[str, Any]) -> str:
    hash_version = (
        layer3_candidate_b_bundle_bridge.AUTHORITY_HASH_VERSION
        if source_kind == "bundle"
        else layer3_candidate_b_runtime_bridge.AUTHORITY_HASH_VERSION
    )
    classification = dict(artifact_family)
    classification.pop("artifact_family_hash", None)
    return _stable_hash({"hash_version": hash_version, "classification": classification})


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
