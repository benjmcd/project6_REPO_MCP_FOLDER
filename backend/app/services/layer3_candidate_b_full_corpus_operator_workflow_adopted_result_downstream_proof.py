from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof.v1"
SCHEMA_VERSION = 1
ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE = (
    "read_only_adopted_process_result_downstream_operator_proof_without_result_mutation_or_reexecution"
)
OPERATOR_DECISION = "record_candidate_b_async_adopted_process_result_downstream_operator_proof"
ADOPTED_RESULT_DOWNSTREAM_PROOF_RECEIPT_PREFIX = (
    f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-adopted-result-downstream-proof"
)
ADOPTED_RESULT_DOWNSTREAM_PROOF_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result/downstream-proof"
)
HISTORY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "runtime_root",
    "runtime_roots",
    "source_directory",
    "bridge_dir",
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
    "command",
    "commands",
    "args",
    "arguments",
    "subprocess",
    "process",
    "process_id",
    "pid",
    "background_process",
    "job_execution",
    "cancel",
    "retry",
    "resume",
    "signal",
    "kill",
    "raw_exception_trace",
    "raw_log_excerpt",
    "stdout",
    "stderr",
    "stacktrace",
}


class CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-adopted-result-downstream-proof-error",
            "server_time": workflow_status._server_time(),
            "mode": ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE,
            "status": "blocked",
            "adopted_result_downstream_proof_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "adopted_result_downstream_proof_mode") != ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_mode_not_admitted",
            "Only read-only adopted process-result downstream proof is admitted.",
            details={"expected_adopted_result_downstream_proof_mode": ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_decision_not_admitted",
            "The operator decision does not match the admitted adopted-result downstream proof action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    completion_projection = _selected_process_completion_result_projection(row, fields)
    completion_receipt = _read_completion_receipt(completion_projection["process_completion_result_receipt_id"])
    completion_receipt_hash = _validate_completion_receipt(completion_receipt, completion_projection)
    adopted_status = _adopted_result_status(completion_receipt)
    authority = _adopted_result_downstream_proof_authority(
        row=row,
        history=history,
        completion_projection=completion_projection,
        completion_receipt=completion_receipt,
        completion_receipt_hash=completion_receipt_hash,
        adopted_status=adopted_status,
    )
    authority_hash = workflow_status._stable_hash(authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {"client_request_id": request_id, "adopted_result_downstream_proof_authority_hash": authority_hash}
    )
    receipt_id = f"{ADOPTED_RESULT_DOWNSTREAM_PROOF_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_receipt(
        receipt_id=receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        completion_projection=completion_projection,
        completion_receipt=completion_receipt,
        completion_receipt_hash=completion_receipt_hash,
        adopted_status=adopted_status,
        authority=authority,
        authority_hash=authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_adopted_result_downstream_proof_receipt(
        receipt,
        request_id=request_id,
        receipt_id=receipt_id,
        authority_hash=authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "adopted_result_downstream_proof_receipt_hash": receipt_hash,
        "adopted_result_downstream_proof_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-adopted-result-downstream-proof://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "adopted_result_downstream_proof_endpoint": ADOPTED_RESULT_DOWNSTREAM_PROOF_ENDPOINT,
        "status_request": dict(completion_receipt["result_status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_forbidden_request_fields",
            "Adopted-result downstream proof does not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, stdout, or stderr.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_selected_authority(
    history: Mapping[str, Any],
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> None:
    try:
        workflow_progress_checkpoint._validate_selected_authority(
            history,
            row,
            fields,
            route_family="downstream_proof",
            rendered_surface="adopted_result_downstream_proof",
        )
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_process_completion_result_projection(
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    projection = row.get("process_completion_result_projection")
    if not isinstance(projection, Mapping) or projection.get("process_completion_result_projection_state") != "completed":
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_process_completion_result_missing",
            "Adopted-result downstream proof requires an existing completed process-completion/result receipt.",
            http_status=409,
        )
    expected = {
        "process_completion_result_receipt_id": projection.get("process_completion_result_receipt_id"),
        "process_completion_result_receipt_hash": projection.get("process_completion_result_receipt_hash"),
        "process_completion_result_authority_hash": projection.get("process_completion_result_authority_hash"),
        "process_execution_receipt_id": projection.get("process_execution_receipt_id"),
        "process_execution_receipt_hash": projection.get("process_execution_receipt_hash"),
        "process_execution_authority_hash": projection.get("process_execution_authority_hash"),
        "result_workflow_receipt_id": projection.get("result_workflow_receipt_id"),
        "result_workflow_receipt_hash": projection.get("result_workflow_receipt_hash"),
        "result_status_request_hash": projection.get("result_status_request_hash"),
        "result_downstream_proof_hash": projection.get("result_downstream_proof_hash"),
    }
    mismatches = [
        {"field": field, "expected": value, "received": fields.get(field)}
        for field, value in expected.items()
        if fields.get(field) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_stale_completion_result",
            "The selected process-completion/result receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return dict(projection)


def _read_completion_receipt(receipt_id: str) -> dict[str, Any]:
    try:
        workflow_status._validate_storage_id(receipt_id, prefix=workflow_status.PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    return _read_json_receipt(_workflow_receipt_root() / receipt_id / "receipt.json")


def _validate_completion_receipt(
    receipt: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> str:
    expected = {
        "schema_id": workflow_status.PROCESS_COMPLETION_RESULT_SCHEMA_ID,
        "mode": workflow_status.PROCESS_COMPLETION_RESULT_MODE,
        "status": "available",
        "process_completion_result_state": "completed",
        "process_completion_result_receipt_id": projection["process_completion_result_receipt_id"],
        "process_completion_result_authority_hash": projection["process_completion_result_authority_hash"],
        "terminal_state": "completed",
        "result_adoption_runtime_selected": True,
        "append_only_process_completion_result_receipt": True,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {"process_completion_result_receipt_hash", "server_time"}}
    )
    mismatches = [
        {"field": field, "expected": value, "received": receipt.get(field)}
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    if receipt.get("process_completion_result_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_completion_result_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_completion_result_receipt_hash"),
            }
        )
    for field in (
        "process_execution_receipt_id",
        "process_execution_receipt_hash",
        "process_execution_authority_hash",
        "result_workflow_receipt_id",
        "result_workflow_receipt_hash",
        "result_status_request_hash",
        "result_downstream_proof_hash",
    ):
        if receipt.get(field) != projection[field]:
            mismatches.append({"field": field, "expected": projection[field], "received": receipt.get(field)})
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_completion_result_mismatch",
            "The selected process-completion/result receipt is stale or contradictory.",
            http_status=409,
            details={"process_completion_result_receipt_id": projection["process_completion_result_receipt_id"], "mismatches": mismatches},
        )
    return str(receipt["process_completion_result_receipt_hash"])


def _adopted_result_status(completion_receipt: Mapping[str, Any]) -> dict[str, Any]:
    status_request = completion_receipt.get("result_status_request")
    if not isinstance(status_request, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_result_status_request_missing",
            "The process-completion/result receipt is missing its adopted-result status request.",
            http_status=409,
        )
    expected_hash = str(completion_receipt["result_status_request_hash"])
    received_hash = workflow_status._stable_hash(status_request)
    if received_hash != expected_hash:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_result_status_request_mismatch",
            "The adopted-result status request is stale or contradictory.",
            http_status=409,
            details={"expected_result_status_request_hash": expected_hash, "received_result_status_request_hash": received_hash},
        )
    expected_status_request = {
        "operator_workflow_receipt_id": completion_receipt["result_workflow_receipt_id"],
    }
    status_request_mismatches = [
        {"field": field, "expected": value, "received": status_request.get(field)}
        for field, value in expected_status_request.items()
        if status_request.get(field) != value
    ]
    if status_request_mismatches:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_result_status_request_stale",
            "The adopted-result status request does not target the selected result workflow.",
            http_status=409,
            details={"mismatches": status_request_mismatches},
        )
    try:
        status = workflow_status.candidate_b_full_corpus_operator_workflow_status(status_request)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    _validate_adopted_result_status(status, completion_receipt)
    return status


def _validate_adopted_result_status(status: Mapping[str, Any], completion_receipt: Mapping[str, Any]) -> None:
    layer3 = status.get("layer3")
    if not isinstance(layer3, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_layer3_missing",
            "The adopted result status is missing Layer 3 projection.",
            http_status=409,
        )
    expected = {
        "workflow_receipt_id": completion_receipt["result_workflow_receipt_id"],
        "workflow_receipt_hash": completion_receipt["result_workflow_receipt_hash"],
        "downstream_proof_hash": completion_receipt["result_downstream_proof_hash"],
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": value, "received": status.get(field)}
        for field, value in expected.items()
        if status.get(field) != value
    ]
    if layer3.get("downstream_proof_status") != "proven":
        mismatches.append(
            {
                "field": "layer3.downstream_proof_status",
                "expected": "proven",
                "received": layer3.get("downstream_proof_status"),
            }
        )
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_unproven_downstream_result",
            "The adopted result status does not prove the required downstream Layer 3 result.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _adopted_result_downstream_proof_authority(
    *,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    completion_projection: Mapping[str, Any],
    completion_receipt: Mapping[str, Any],
    completion_receipt_hash: str,
    adopted_status: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "adopted_result_downstream_proof_mode": ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "process_completion_result_receipt_id": completion_projection["process_completion_result_receipt_id"],
        "process_completion_result_receipt_hash": completion_receipt_hash,
        "process_completion_result_authority_hash": completion_projection["process_completion_result_authority_hash"],
        "process_execution_receipt_id": completion_projection["process_execution_receipt_id"],
        "process_execution_receipt_hash": completion_projection["process_execution_receipt_hash"],
        "process_execution_authority_hash": completion_projection["process_execution_authority_hash"],
        "result_workflow_receipt_id": completion_receipt["result_workflow_receipt_id"],
        "result_workflow_receipt_hash": completion_receipt["result_workflow_receipt_hash"],
        "result_authority_hash": completion_receipt["result_authority_hash"],
        "result_status_request_hash": completion_receipt["result_status_request_hash"],
        "result_downstream_proof_hash": completion_receipt["result_downstream_proof_hash"],
        "adopted_result_status_hash": adopted_status["workflow_status_hash"],
        "adopted_result_downstream_proof_status": adopted_status["layer3"]["downstream_proof_status"],
    }


def _load_or_write_receipt(
    *,
    receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    completion_projection: Mapping[str, Any],
    completion_receipt: Mapping[str, Any],
    completion_receipt_hash: str,
    adopted_status: Mapping[str, Any],
    authority: Mapping[str, Any],
    authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    target = _workflow_receipt_root() / receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_adopted_result_downstream_proof_receipt(
            existing,
            request_id=request_id,
            receipt_id=receipt_id,
            authority_hash=authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True
    _reject_competing_receipt(row["operator_workflow_receipt_id"])
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "adopted_result_downstream_proof_state": "proven",
        "adopted_result_downstream_proof_receipt_id": receipt_id,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "process_completion_result_receipt_id": completion_projection["process_completion_result_receipt_id"],
        "process_completion_result_receipt_hash": completion_receipt_hash,
        "process_completion_result_authority_hash": completion_projection["process_completion_result_authority_hash"],
        "process_execution_receipt_id": completion_projection["process_execution_receipt_id"],
        "process_execution_receipt_hash": completion_projection["process_execution_receipt_hash"],
        "process_execution_authority_hash": completion_projection["process_execution_authority_hash"],
        "result_workflow_receipt_id": completion_receipt["result_workflow_receipt_id"],
        "result_workflow_receipt_hash": completion_receipt["result_workflow_receipt_hash"],
        "result_authority_hash": completion_receipt["result_authority_hash"],
        "result_status_request_hash": completion_receipt["result_status_request_hash"],
        "result_downstream_proof_hash": completion_receipt["result_downstream_proof_hash"],
        "adopted_result_status_hash": adopted_status["workflow_status_hash"],
        "adopted_result_downstream_proof_status": adopted_status["layer3"]["downstream_proof_status"],
        "adopted_result_layer3_projection": {
            "bridge_status": adopted_status["layer3"]["bridge_status"],
            "source_directory_scan_status": adopted_status["layer3"]["source_directory_scan_status"],
            "qualitative_analysis_status": adopted_status["layer3"]["qualitative_analysis_status"],
            "external_export_download_status": adopted_status["layer3"]["external_export_download_status"],
            "same_origin_delivery_available": adopted_status["layer3"]["same_origin_delivery_available"],
            "provider_private_state": adopted_status["layer3"]["provider_private_state"],
            "provider_private_revoke_state": adopted_status["layer3"]["provider_private_revoke_state"],
            "internal_webhook_state": adopted_status["layer3"]["internal_webhook_state"],
            "visual_lane_status": adopted_status["layer3"]["visual_lane_status"],
            "downstream_proof_status": adopted_status["layer3"]["downstream_proof_status"],
        },
        "adopted_result_downstream_proof_authority": dict(authority),
        "adopted_result_downstream_proof_authority_hash": authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_adopted_result_downstream_proof_receipt": True,
        "process_completion_result_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "adopted_result_workflow_receipt_mutated": False,
        "downstream_proof_receipt_mutated": False,
        "adopted_result_downstream_proof_runtime_selected": True,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "default_scope_expansion_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "next_allowed_actions": [
            "refresh workflow-run history",
            "inspect adopted-result downstream proof projection through workflow status",
            "use the adopted result for operator downstream inspection without reexecution",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "adopted_result_downstream_proof_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_receipt(operator_workflow_receipt_id: str) -> None:
    root = _workflow_receipt_root()
    for receipt_file in sorted(root.glob(f"{ADOPTED_RESULT_DOWNSTREAM_PROOF_RECEIPT_PREFIX}-*/receipt.json")):
        receipt = _read_json_receipt(receipt_file)
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
                "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_competing_receipt",
                "The selected workflow already has an adopted-result downstream proof receipt.",
                http_status=409,
                details={"adopted_result_downstream_proof_receipt_id": receipt_file.parent.name},
            )


def _validate_adopted_result_downstream_proof_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    receipt_id: str,
    authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "adopted_result_downstream_proof_state": "proven",
        "adopted_result_downstream_proof_receipt_id": receipt_id,
        "adopted_result_downstream_proof_authority_hash": authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_adopted_result_downstream_proof_receipt": True,
        "process_completion_result_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "adopted_result_workflow_receipt_mutated": False,
        "downstream_proof_receipt_mutated": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": value, "received": receipt.get(field)}
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    receipt_hash = workflow_status._stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"adopted_result_downstream_proof_receipt_hash", "server_time"}
        }
    )
    if receipt.get("adopted_result_downstream_proof_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "adopted_result_downstream_proof_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("adopted_result_downstream_proof_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            f"candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_receipt_mismatch",
            "The Candidate B adopted-result downstream proof receipt is stale or contradictory.",
            http_status=409,
            details={"adopted_result_downstream_proof_receipt_id": receipt_id, "mismatches": mismatches},
        )
    return str(receipt["adopted_result_downstream_proof_receipt_hash"])


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_dir_invalid",
            "The configured Candidate B workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_receipt_missing",
            "A required Candidate B workflow receipt could not be found.",
            http_status=404,
            details={"receipt_ref": path.parent.name},
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_receipt_unreadable",
            "A Candidate B workflow receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_receipt_invalid",
            "A Candidate B workflow receipt is not a JSON object.",
            http_status=409,
        )
    return payload


def _required(fields: Mapping[str, Any], field: str) -> str:
    value = str(fields.get(field) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofError(
            "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_required_field_missing",
            "A required Candidate B adopted-result downstream proof field is missing.",
            details={"field": field},
        )
    return value
