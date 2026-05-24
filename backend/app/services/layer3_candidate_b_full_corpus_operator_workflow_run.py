from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_run.v1"
SCHEMA_VERSION = 1
RUN_MODE = "candidate_b_full_corpus_operator_workflow_run_v1"
OPERATOR_DECISION = "start_candidate_b_full_corpus_operator_workflow"
RUN_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-run"
STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status"
STATE_MACHINE = ("accepted", "running", "proven", "blocked", "cancelled", "expired")
_RUNTIME_ROOT_LIFECYCLE_PREFIX = "cb-full-corpus-runtime-roots"
_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "runtime_root",
    "runtime_roots",
    "baseline_run_root",
    "candidate_a_run_root",
    "candidate_b_run_root",
    "url",
    "urls",
    "file",
    "files",
    "file_bytes",
    "artifact_bytes",
    "provider_object_ref",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_destination",
    "connector_dispatch",
    "rag_vector_index",
    "model_runtime",
    "browser_storage",
    "document_processing_engine",
    "visual_lane_mode",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
    "full_mockup_activation",
}


class CandidateBFullCorpusOperatorWorkflowRunError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-run-error",
            "server_time": workflow_status._server_time(),
            "mode": RUN_MODE,
            "status": "blocked",
            "run_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_full_corpus_operator_workflow_run(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "run_mode") != RUN_MODE:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_mode_not_admitted",
            "Only the Candidate B full-corpus operator workflow run mode is admitted.",
            details={"expected_run_mode": RUN_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_decision_not_admitted",
            "The operator decision does not match the admitted server-owned workflow-run start action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    requested = _requested_authority(fields)
    source_receipt_id, source_receipt = _find_source_workflow_receipt(requested)
    source_receipt_hash = _revalidate_workflow_receipt(source_receipt, receipt_id=source_receipt_id)
    runtime_lifecycle = _validated_runtime_root_lifecycle(source_receipt, requested)
    corpus = _validated_corpus(source_receipt, requested)
    layer3 = _revalidate_layer3(source_receipt)
    artifact_family = _revalidate_artifact_family(source_receipt)
    baseline_rollback = _revalidate_baseline_rollback(source_receipt)
    negative_invariants = _revalidate_negative_invariants(source_receipt)
    _assert_no_raw_authority_exposure(source_receipt)

    authority_basis = {
        "run_mode": RUN_MODE,
        "operator_decision": OPERATOR_DECISION,
        "source_operator_workflow_receipt_id": source_receipt_id,
        "source_operator_workflow_receipt_hash": source_receipt_hash,
        "runtime_root_lifecycle_receipt_id": requested["runtime_root_lifecycle_receipt_id"],
        "runtime_root_lifecycle_receipt_hash": runtime_lifecycle["lifecycle_receipt_hash"],
        "baseline_run_id": requested["baseline_run_id"],
        "candidate_a_run_id": requested["candidate_a_run_id"],
        "candidate_b_run_id": requested["candidate_b_run_id"],
        "compare_target_set_hash": requested["compare_target_set_hash"],
        "material_relative_name": requested.get("material_relative_name") or corpus["material_relative_name"],
        "eligible_corpus_scope": "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only",
    }
    authority_basis_hash = workflow_status._stable_hash(authority_basis)
    idempotency_key_hash = workflow_status._stable_hash(
        {"client_request_id": request_id, "authority_basis_hash": authority_basis_hash}
    )
    run_receipt_id = f"{RUN_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    run_receipt, idempotent_replay = _load_or_write_run_receipt(
        run_receipt_id=run_receipt_id,
        source_receipt=source_receipt,
        request_id=request_id,
        authority_basis=authority_basis,
        authority_basis_hash=authority_basis_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    run_receipt_hash = _revalidate_workflow_receipt(run_receipt, receipt_id=run_receipt_id)
    _assert_no_raw_authority_exposure(run_receipt)

    status_request = {
        "client_request_id": f"{request_id}-status",
        "status_mode": workflow_status.STATUS_MODE,
        "operator_decision": workflow_status.OPERATOR_DECISION,
        "operator_workflow_receipt_id": run_receipt_id,
        "baseline_run_id": requested["baseline_run_id"],
        "candidate_a_run_id": requested["candidate_a_run_id"],
        "candidate_b_run_id": requested["candidate_b_run_id"],
        "bridge_receipt_id": str(run_receipt["bridge_receipt_id"]),
        "downstream_proof_id": str(run_receipt["downstream_proof_id"]),
    }
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "mode": RUN_MODE,
        "status": "proven",
        "run_state": "proven",
        "state_machine": list(STATE_MACHINE),
        "operator_workflow_receipt_id": run_receipt_id,
        "operator_workflow_receipt_hash": run_receipt_hash,
        "run_receipt_id": run_receipt_id,
        "run_receipt_hash": workflow_status._stable_hash(run_receipt["server_owned_workflow_run"]),
        "run_receipt_ref": f"candidate-b-full-corpus-operator-workflow://{run_receipt_id}/{run_receipt_hash[:24]}",
        "source_operator_workflow_receipt_id": source_receipt_id,
        "source_operator_workflow_receipt_hash": source_receipt_hash,
        "authority_basis_hash": authority_basis_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "idempotent_replay": idempotent_replay,
        "runtime_root_lifecycle": runtime_lifecycle,
        "baseline_run_id": requested["baseline_run_id"],
        "candidate_a_run_id": requested["candidate_a_run_id"],
        "candidate_b_run_id": requested["candidate_b_run_id"],
        "compare_target_set_hash": requested["compare_target_set_hash"],
        "bridge_receipt_id": str(run_receipt["bridge_receipt_id"]),
        "bridge_receipt_hash": str(run_receipt["bridge_receipt_hash"]),
        "downstream_proof_id": str(run_receipt["downstream_proof_id"]),
        "downstream_proof_hash": str(run_receipt["downstream_proof_hash"]),
        "coverage_count": int(run_receipt["coverage_count"]),
        "corpus": corpus,
        "layer3": layer3,
        "artifact_family": artifact_family,
        "baseline_rollback": baseline_rollback,
        "status_endpoint": STATUS_ENDPOINT,
        "status_request": status_request,
        "receipt_persisted": True,
        "queue_scheduler_admitted": "contract_only",
        "cancel_endpoint_admitted": "contract_only",
        "rendered_run_start_control_admitted": False,
        "rendered_progress_control_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "negative_invariants": {
            **negative_invariants,
            "browser_supplied_runtime_roots_admitted": False,
            "client_supplied_raw_runtime_roots_admitted": False,
        },
        "next_allowed_actions": [
            "inspect the returned workflow receipt through the read-only status endpoint",
            "keep rendered run-start and progress controls frozen until a separate slice admits them",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_forbidden_request_fields",
            "Workflow-run start does not admit caller paths, URLs, selector mutation, connector/model controls, browser authority, or credentials.",
            details={"blocked_fields": blocked},
        )
    return fields


def _requested_authority(fields: Mapping[str, Any]) -> dict[str, str]:
    runtime_root_lifecycle_receipt_id = _required(fields, "runtime_root_lifecycle_receipt_id")
    _validate_storage_id(runtime_root_lifecycle_receipt_id, prefix=_RUNTIME_ROOT_LIFECYCLE_PREFIX)
    requested = {
        "runtime_root_lifecycle_receipt_id": runtime_root_lifecycle_receipt_id,
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "candidate_b_run_id": _required(fields, "candidate_b_run_id"),
        "compare_target_set_hash": _required_hash(fields, "compare_target_set_hash"),
    }
    material_relative_name = str(fields.get("material_relative_name") or "").strip()
    if material_relative_name:
        _validate_material_relative_name(material_relative_name)
        requested["material_relative_name"] = material_relative_name
    return requested


def _find_source_workflow_receipt(requested: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
    root = _workflow_receipt_root()
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_receipt_root_missing",
            "The configured Candidate B full-corpus workflow receipt directory does not exist.",
            http_status=404,
        )
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in root.glob(f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-*/receipt.json"):
        receipt = _read_json_receipt(receipt_file)
        if not isinstance(receipt, dict) or "server_owned_workflow_run" in receipt:
            continue
        if _receipt_matches_request(receipt, requested):
            receipt_id = str(receipt.get("receipt_id") or receipt_file.parent.name)
            if receipt_id != receipt_file.parent.name:
                continue
            _validate_storage_id(receipt_id, prefix=workflow_status.WORKFLOW_RECEIPT_PREFIX)
            matches.append((receipt_id, receipt))
    if not matches:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_source_receipt_missing",
            "No server-owned Candidate B workflow receipt matches the requested run authority.",
            http_status=404,
            details={"requested_authority": dict(requested)},
        )
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_source_receipt_ambiguous",
            "More than one Candidate B workflow receipt matches the requested run authority.",
            http_status=409,
            details={"match_count": len(matches)},
        )
    return matches[0]


def _load_or_write_run_receipt(
    *,
    run_receipt_id: str,
    source_receipt: Mapping[str, Any],
    request_id: str,
    authority_basis: Mapping[str, Any],
    authority_basis_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / run_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        if not isinstance(existing, dict):
            raise CandidateBFullCorpusOperatorWorkflowRunError(
                "candidate_b_full_corpus_operator_workflow_run_receipt_invalid",
                "The existing Candidate B workflow-run receipt is not a JSON object.",
                http_status=409,
            )
        _validate_existing_run_receipt(
            existing,
            request_id=request_id,
            authority_basis_hash=authority_basis_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    target.parent.mkdir(parents=True, exist_ok=True)
    run_receipt = {
        **dict(source_receipt),
        "receipt_id": run_receipt_id,
        "server_time": workflow_status._server_time(),
        "server_owned_workflow_run": {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "run_mode": RUN_MODE,
            "operator_decision": OPERATOR_DECISION,
            "client_request_id": request_id,
            "run_state": "proven",
            "state_machine": list(STATE_MACHINE),
            "authority_basis": dict(authority_basis),
            "authority_basis_hash": authority_basis_hash,
            "idempotency_key_hash": idempotency_key_hash,
            "source_operator_workflow_receipt_id": authority_basis["source_operator_workflow_receipt_id"],
            "source_operator_workflow_receipt_hash": authority_basis["source_operator_workflow_receipt_hash"],
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
            "selector_mutation_performed": False,
            "queue_scheduler_admitted": "contract_only",
            "cancel_endpoint_admitted": "contract_only",
        },
    }
    target.write_text(json.dumps(run_receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return run_receipt, False


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_receipt_unreadable",
            "A Candidate B full-corpus workflow receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc


def _receipt_matches_request(receipt: Mapping[str, Any], requested: Mapping[str, str]) -> bool:
    lifecycle = receipt.get("runtime_root_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return False
    corpus = receipt.get("corpus")
    if not isinstance(corpus, Mapping):
        return False
    if requested.get("material_relative_name") and corpus.get("material_relative_name") != requested["material_relative_name"]:
        return False
    return (
        receipt.get("schema_id") == workflow_status.WORKFLOW_SCHEMA_ID
        and receipt.get("workflow_mode") == workflow_status.WORKFLOW_MODE
        and receipt.get("status") == "proven"
        and receipt.get("baseline_run_id") == requested["baseline_run_id"]
        and receipt.get("candidate_a_run_id") == requested["candidate_a_run_id"]
        and receipt.get("candidate_b_run_id") == requested["candidate_b_run_id"]
        and receipt.get("compare_target_set_hash") == requested["compare_target_set_hash"]
        and lifecycle.get("lifecycle_receipt_id") == requested["runtime_root_lifecycle_receipt_id"]
    )


def _validate_existing_run_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    authority_basis_hash: str,
    idempotency_key_hash: str,
) -> None:
    server_run = receipt.get("server_owned_workflow_run")
    if not isinstance(server_run, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_receipt_missing_run_authority",
            "The existing Candidate B workflow-run receipt is missing server-owned run authority.",
            http_status=409,
        )
    mismatches = [
        {"field": "client_request_id", "expected": request_id, "received": server_run.get("client_request_id")},
        {
            "field": "authority_basis_hash",
            "expected": authority_basis_hash,
            "received": server_run.get("authority_basis_hash"),
        },
        {
            "field": "idempotency_key_hash",
            "expected": idempotency_key_hash,
            "received": server_run.get("idempotency_key_hash"),
        },
        {"field": "run_state", "expected": "proven", "received": server_run.get("run_state")},
    ]
    mismatches = [mismatch for mismatch in mismatches if mismatch["expected"] != mismatch["received"]]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_idempotency_conflict",
            "The existing Candidate B workflow-run receipt does not match the requested idempotency authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _revalidate_workflow_receipt(receipt: Mapping[str, Any], *, receipt_id: str) -> str:
    fields = {
        "baseline_run_id": str(receipt.get("baseline_run_id") or ""),
        "candidate_a_run_id": str(receipt.get("candidate_a_run_id") or ""),
        "candidate_b_run_id": str(receipt.get("candidate_b_run_id") or ""),
        "bridge_receipt_id": str(receipt.get("bridge_receipt_id") or ""),
        "downstream_proof_id": str(receipt.get("downstream_proof_id") or ""),
    }
    try:
        return workflow_status._validate_workflow_receipt(receipt, receipt_id=receipt_id, fields=fields)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)


def _validated_runtime_root_lifecycle(
    receipt: Mapping[str, Any],
    requested: Mapping[str, str],
) -> dict[str, Any]:
    try:
        lifecycle = workflow_status._workflow_runtime_root_lifecycle(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)
    if lifecycle["lifecycle_receipt_id"] != requested["runtime_root_lifecycle_receipt_id"]:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_runtime_lifecycle_mismatch",
            "The selected workflow receipt does not match the requested runtime-root lifecycle receipt.",
            http_status=409,
            details={
                "expected": requested["runtime_root_lifecycle_receipt_id"],
                "received": lifecycle["lifecycle_receipt_id"],
            },
        )
    return lifecycle


def _validated_corpus(receipt: Mapping[str, Any], requested: Mapping[str, str]) -> dict[str, Any]:
    try:
        corpus = workflow_status._workflow_corpus(receipt)
        workflow_status._workflow_eligibility_summary(corpus)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)
    if requested.get("material_relative_name") and corpus["material_relative_name"] != requested["material_relative_name"]:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_material_mismatch",
            "The requested material-relative name does not match the selected workflow receipt.",
            http_status=409,
        )
    return corpus


def _revalidate_layer3(receipt: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_status._workflow_layer3_projection(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)


def _revalidate_artifact_family(receipt: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_status._workflow_artifact_family(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)


def _revalidate_baseline_rollback(receipt: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_status._workflow_baseline_rollback(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)


def _revalidate_negative_invariants(receipt: Mapping[str, Any]) -> dict[str, bool]:
    try:
        return workflow_status._negative_invariants(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)


def _assert_no_raw_authority_exposure(receipt: Mapping[str, Any]) -> None:
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        _raise_authority_revalidation_failed(exc)


def _raise_authority_revalidation_failed(exc: workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError) -> None:
    raise CandidateBFullCorpusOperatorWorkflowRunError(
        "candidate_b_full_corpus_operator_workflow_run_authority_revalidation_failed",
        "Candidate B workflow-run start failed closed while revalidating server-owned workflow authority.",
        http_status=exc.http_status,
        details={"upstream_error": exc.code, "upstream_details": exc.details},
    ) from exc


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_required_field_missing",
            "A required Candidate B full-corpus operator workflow-run field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_hash_invalid",
            "Candidate B workflow-run authority hashes must be lowercase sha256 hex values.",
            http_status=409,
            details={"field": key},
        )
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    if (
        not value.startswith(f"{prefix}-")
        or "/" in value
        or "\\" in value
        or ".." in value
        or value in {".", ".."}
    ):
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_storage_id_invalid",
            "Candidate B workflow-run authority identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _validate_material_relative_name(value: str) -> None:
    if (
        value.startswith("/")
        or "\\" in value
        or ".." in value.split("/")
        or ":" in value
        or value.startswith(("http://", "https://", "file://"))
    ):
        raise CandidateBFullCorpusOperatorWorkflowRunError(
            "candidate_b_full_corpus_operator_workflow_run_material_ref_invalid",
            "Candidate B workflow-run material references must be bounded relative names.",
            http_status=409,
        )
