from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from app.core.config import settings


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_status.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "candidate_b_full_corpus_operator_workflow_status_v1"
OPERATOR_DECISION = "inspect_candidate_b_full_corpus_operator_workflow_status"
WORKFLOW_SCHEMA_ID = "candidate_b.full_corpus_layer3_operator_workflow.v1"
WORKFLOW_MODE = "candidate_b_full_corpus_operator_workflow_v1"
WORKFLOW_RECEIPT_PREFIX = "cb-full-corpus-operator"
RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID = "candidate_b.full_corpus_runtime_root_lifecycle.v1"
RUNTIME_ROOT_LIFECYCLE_MODE = "candidate_b_full_corpus_runtime_root_lifecycle_v1"
STATUS_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "workflow_receipt_id",
    "workflow_receipt_hash",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_run_id",
    "compare_target_set_hash",
    "bridge_receipt_id",
    "bridge_receipt_hash",
    "downstream_proof_id",
    "downstream_proof_hash",
    "coverage_count",
    "corpus",
    "layer3",
    "artifact_family",
    "runtime_root_lifecycle",
    "operator_projection",
)
WORKFLOW_RECEIPT_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "workflow_mode",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_run_id",
    "compare_target_set_hash",
    "bridge_receipt_id",
    "bridge_receipt_hash",
    "downstream_proof_id",
    "downstream_proof_hash",
    "coverage_count",
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
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
}
_ALLOWED_REF_SCHEMES = (
    "repo://",
    "redacted://",
    "candidate-b-runtime-bridge://",
    "candidate-b-full-corpus-operator-workflow://",
)


class CandidateBFullCorpusOperatorWorkflowStatusError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-status-error",
            "server_time": _server_time(),
            "mode": STATUS_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_full_corpus_operator_workflow_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "status_mode")
    if mode != STATUS_MODE:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_mode_not_admitted",
            "Only the Candidate B full-corpus operator workflow status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_decision_not_admitted",
            "The operator decision does not match the admitted read-only workflow-status inspection.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    receipt_id = _required_storage_id(fields, "operator_workflow_receipt_id", WORKFLOW_RECEIPT_PREFIX)
    receipt = _read_workflow_receipt(receipt_id)
    receipt_hash = _validate_workflow_receipt(receipt, receipt_id=receipt_id, fields=fields)
    _assert_no_raw_authority_exposure(receipt)

    corpus = _workflow_corpus(receipt)
    layer3 = _workflow_layer3_projection(receipt)
    artifact_family = _workflow_artifact_family(receipt)
    runtime_root_lifecycle = _workflow_runtime_root_lifecycle(receipt)
    operator_projection = {
        "workflow_status_visible": True,
        "workflow_receipt_projection_visible": True,
        "bridge_receipt_projection_visible": True,
        "downstream_proof_projection_visible": True,
        "artifact_family_projection_visible": True,
        "runtime_root_lifecycle_projection_visible": runtime_root_lifecycle["available"],
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "frontend_durable_authority_enabled": False,
    }
    status_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": STATUS_MODE,
        "workflow_receipt_id": receipt_id,
        "workflow_receipt_hash": receipt_hash,
        "baseline_run_id": str(receipt["baseline_run_id"]),
        "candidate_a_run_id": str(receipt["candidate_a_run_id"]),
        "candidate_b_run_id": str(receipt["candidate_b_run_id"]),
        "compare_target_set_hash": str(receipt["compare_target_set_hash"]),
        "bridge_receipt_id": str(receipt["bridge_receipt_id"]),
        "bridge_receipt_hash": str(receipt["bridge_receipt_hash"]),
        "downstream_proof_id": str(receipt["downstream_proof_id"]),
        "downstream_proof_hash": str(receipt["downstream_proof_hash"]),
        "coverage_count": int(receipt["coverage_count"]),
        "corpus": corpus,
        "layer3": layer3,
        "artifact_family": artifact_family,
        "runtime_root_lifecycle": runtime_root_lifecycle,
        "operator_projection": operator_projection,
    }
    status_hash = _stable_hash({key: status_input[key] for key in STATUS_HASH_KEYS})
    return {
        **status_input,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "workflow_status": str(receipt["status"]),
        "workflow_status_hash": status_hash,
        "workflow_status_ref": f"candidate-b-full-corpus-operator-workflow-status://{receipt_id}/{status_hash[:24]}",
        "validate_only_triplet": receipt.get("validate_only_triplet") is True,
        "artifacts_seeded_or_generated_by_triplet_validator": (
            receipt.get("artifacts_seeded_or_generated_by_triplet_validator") is True
        ),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "negative_invariants": {
            **_negative_invariants(receipt),
            "operator_workflow_status_mutation_performed": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "inspect Candidate B full-corpus operator workflow evidence",
            "use this receipt status as operator-repeatability evidence",
            "run a fresh full-corpus workflow only when current evidence is stale or a concrete defect appears",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_forbidden_request_fields",
            "Workflow-status inspection does not admit caller paths, URLs, selector mutation, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_required_field_missing",
            "A required Candidate B full-corpus operator workflow-status field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    _validate_storage_id(value, prefix=prefix)
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    if (
        not value.startswith(f"{prefix}-")
        or "/" in value
        or "\\" in value
        or ".." in value
        or value in {".", ".."}
    ):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_storage_id_invalid",
            "Candidate B full-corpus operator workflow receipt identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _read_workflow_receipt(receipt_id: str) -> dict[str, Any]:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_missing",
            "The selected Candidate B full-corpus operator workflow receipt is missing.",
            http_status=404,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_unreadable",
            "The selected Candidate B full-corpus operator workflow receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_invalid",
            "The selected Candidate B full-corpus operator workflow receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _validate_workflow_receipt(receipt: Mapping[str, Any], *, receipt_id: str, fields: Mapping[str, Any]) -> str:
    expected = {
        "schema_id": WORKFLOW_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "workflow_mode": WORKFLOW_MODE,
        "receipt_id": receipt_id,
        "status": "proven",
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "candidate_b_run_id": _required(fields, "candidate_b_run_id"),
        "bridge_receipt_id": _required_storage_id(fields, "bridge_receipt_id", "cb-runtime-l3"),
        "downstream_proof_id": _required_storage_id(
            fields,
            "downstream_proof_id",
            "cb-runtime-downstream-proof",
        ),
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_mismatch",
            "The selected Candidate B full-corpus operator workflow receipt does not match the requested authority identifiers.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    missing = [key for key in WORKFLOW_RECEIPT_HASH_KEYS if key not in receipt]
    if missing:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_authority_field_missing",
            "The selected Candidate B full-corpus operator workflow receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in WORKFLOW_RECEIPT_HASH_KEYS})
    if receipt.get("receipt_hash") != expected_hash:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_hash_mismatch",
            "The selected Candidate B full-corpus operator workflow receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("receipt_hash")},
        )
    if receipt.get("validate_only_triplet") is not True:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_not_validate_only",
            "Candidate B full-corpus operator workflow status requires a validate-only triplet run.",
            http_status=409,
        )
    if receipt.get("artifacts_seeded_or_generated_by_triplet_validator") is not False:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_seeded_artifacts",
            "Candidate B full-corpus operator workflow status rejects receipts that seeded or generated triplet artifacts.",
            http_status=409,
        )
    return expected_hash


def _workflow_corpus(receipt: Mapping[str, Any]) -> dict[str, Any]:
    corpus = receipt.get("corpus")
    if not isinstance(corpus, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_corpus_missing",
            "The selected workflow receipt is missing corpus status.",
            http_status=409,
        )
    return {
        "corpus_pdf_count": _non_negative_int(corpus, "corpus_pdf_count"),
        "eligible_file_count": _non_negative_int(corpus, "eligible_file_count"),
        "material_relative_name": str(corpus.get("material_relative_name") or ""),
        "target_status_counts": dict(corpus.get("target_status_counts") or {}),
    }


def _workflow_layer3_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    layer3 = receipt.get("layer3")
    if not isinstance(layer3, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_layer3_missing",
            "The selected workflow receipt is missing Layer 3 status.",
            http_status=409,
        )
    required_statuses = {
        "source_directory_scan_status": {"available"},
        "downstream_proof_status": {"proven"},
    }
    mismatches = [
        {"field": field, "expected": sorted(expected), "received": layer3.get(field)}
        for field, expected in required_statuses.items()
        if layer3.get(field) not in expected
    ]
    if layer3.get("bridge_status") not in {"prepared", "already_prepared"}:
        mismatches.append(
            {
                "field": "bridge_status",
                "expected": ["already_prepared", "prepared"],
                "received": layer3.get("bridge_status"),
            }
        )
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_layer3_status_mismatch",
            "The selected workflow receipt does not prove the required Layer 3 downstream statuses.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return {
        "bridge_status": str(layer3.get("bridge_status") or ""),
        "source_directory_scan_status": str(layer3.get("source_directory_scan_status") or ""),
        "source_directory_eligible_file_count": _non_negative_int(layer3, "source_directory_eligible_file_count"),
        "qualitative_analysis_status": str(layer3.get("qualitative_analysis_status") or ""),
        "external_export_download_status": str(layer3.get("external_export_download_status") or ""),
        "same_origin_delivery_available": layer3.get("same_origin_delivery_available") is True,
        "provider_private_state": str(layer3.get("provider_private_state") or ""),
        "provider_private_revoke_state": str(layer3.get("provider_private_revoke_state") or ""),
        "internal_webhook_state": str(layer3.get("internal_webhook_state") or ""),
        "visual_lane_status": str(layer3.get("visual_lane_status") or ""),
        "downstream_proof_status": str(layer3.get("downstream_proof_status") or ""),
    }


def _workflow_artifact_family(receipt: Mapping[str, Any]) -> dict[str, Any]:
    artifact_family = receipt.get("artifact_family")
    if not isinstance(artifact_family, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_artifact_family_missing",
            "The selected workflow receipt is missing Candidate B artifact-family status.",
            http_status=409,
        )
    role_counts = artifact_family.get("role_counts")
    if not isinstance(role_counts, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_artifact_role_counts_missing",
            "The selected workflow receipt is missing Candidate B artifact-family role counts.",
            http_status=409,
        )
    return {
        "governed_retained_artifact_family_hash": str(
            artifact_family.get("governed_retained_artifact_family_hash") or ""
        ),
        "role_counts": dict(role_counts),
        "curated_file_count": _non_negative_int(artifact_family, "curated_file_count"),
        "text_file_count": _non_negative_int(artifact_family, "text_file_count"),
    }


def _workflow_runtime_root_lifecycle(receipt: Mapping[str, Any]) -> dict[str, Any]:
    lifecycle = receipt.get("runtime_root_lifecycle")
    if lifecycle is None:
        return {
            "available": False,
            "lifecycle_receipt_id": "",
            "lifecycle_receipt_hash": "",
            "runtime_parent_ref": "",
            "root_count": 0,
            "validate_only_triplet": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        }
    if not isinstance(lifecycle, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_invalid",
            "The selected workflow receipt has an invalid runtime-root lifecycle projection.",
            http_status=409,
        )
    schema_id = str(lifecycle.get("schema_id") or "")
    lifecycle_mode = str(lifecycle.get("lifecycle_mode") or "")
    if schema_id != RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID or lifecycle_mode != RUNTIME_ROOT_LIFECYCLE_MODE:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_mode_invalid",
            "The selected workflow receipt has a runtime-root lifecycle projection outside the admitted schema or mode.",
            http_status=409,
            details={
                "expected_schema_id": RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID,
                "expected_lifecycle_mode": RUNTIME_ROOT_LIFECYCLE_MODE,
            },
        )
    receipt_id = str(lifecycle.get("lifecycle_receipt_id") or "")
    _validate_storage_id(receipt_id, prefix="cb-full-corpus-runtime-roots")
    receipt_hash = str(lifecycle.get("lifecycle_receipt_hash") or "")
    if not re.fullmatch(r"[a-f0-9]{64}", receipt_hash):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_hash_invalid",
            "The selected workflow receipt has an invalid runtime-root lifecycle receipt hash.",
            http_status=409,
        )
    runtime_parent_ref = str(lifecycle.get("runtime_parent_ref") or "")
    if not runtime_parent_ref.startswith(("repo://", "redacted://")):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_ref_invalid",
            "The selected workflow receipt has an invalid runtime-root parent reference.",
            http_status=409,
        )
    root_count = _non_negative_int(lifecycle, "root_count")
    if root_count != 3:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_count_invalid",
            "Candidate B full-corpus runtime-root lifecycle receipts must bind baseline, Candidate A, and Candidate B.",
            http_status=409,
            details={"root_count": root_count},
        )
    if lifecycle.get("validate_only_triplet") is not True:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_not_validate_only",
            "Candidate B full-corpus runtime-root lifecycle receipts require validate-only triplet authority.",
            http_status=409,
        )
    if lifecycle.get("raw_local_path_exposed") is not False or lifecycle.get("raw_url_exposed") is not False:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_raw_authority",
            "Candidate B full-corpus runtime-root lifecycle receipts must not expose raw path or URL authority.",
            http_status=409,
        )
    return {
        "available": True,
        "schema_id": schema_id,
        "lifecycle_mode": lifecycle_mode,
        "lifecycle_receipt_id": receipt_id,
        "lifecycle_receipt_hash": receipt_hash,
        "runtime_parent_ref": runtime_parent_ref,
        "root_count": root_count,
        "validate_only_triplet": True,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
    }


def _negative_invariants(receipt: Mapping[str, Any]) -> dict[str, bool]:
    invariants = receipt.get("negative_invariants")
    if not isinstance(invariants, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_negative_invariants_missing",
            "The selected workflow receipt is missing negative invariants.",
            http_status=409,
        )
    required_false = {
        "baseline_default_changed",
        "candidate_a_semantics_changed",
        "candidate_b_default_broadened_beyond_eligible_pdf",
        "raw_local_path_exposed",
        "raw_url_exposed",
        "provider_public_url_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "frontend_durable_authority_enabled",
        "full_mockup_activation_enabled",
    }
    violations = sorted(field for field in required_false if invariants.get(field) is not False)
    if violations:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_negative_invariant_violation",
            "The selected workflow receipt violates Candidate B operator workflow guardrails.",
            http_status=409,
            details={"violations": violations},
        )
    return {field: False for field in sorted(required_false)}


def _assert_no_raw_authority_exposure(value: Any) -> None:
    leaked = _find_raw_authority_exposure(value)
    if leaked:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_exposes_raw_authority",
            "The selected workflow receipt exposes raw local paths or raw URLs.",
            http_status=409,
            details={"field": leaked},
        )


def _find_raw_authority_exposure(value: Any, *, field: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            leaked = _find_raw_authority_exposure(item, field=f"{field}.{key}")
            if leaked:
                return leaked
        return None
    if isinstance(value, list):
        for index, item in enumerate(value):
            leaked = _find_raw_authority_exposure(item, field=f"{field}[{index}]")
            if leaked:
                return leaked
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.startswith(_ALLOWED_REF_SCHEMES):
        return None
    if re.search(r"\bhttps?://", text, flags=re.IGNORECASE) or re.search(r"\bfile://", text, flags=re.IGNORECASE):
        return field
    if re.search(r"\b[A-Za-z]:[\\/]", text):
        return field
    return None


def _non_negative_int(fields: Mapping[str, Any], key: str) -> int:
    value = fields.get(key)
    if not isinstance(value, int) or value < 0:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_count_invalid",
            "The selected workflow receipt has an invalid non-negative count field.",
            http_status=409,
            details={"field": key, "received": value},
        )
    return value


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
