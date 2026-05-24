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


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_process_completion_result.v1"
SCHEMA_VERSION = 1
PROCESS_COMPLETION_RESULT_MODE = (
    "append_only_process_completion_result_adoption_receipt_without_source_run_mutation_or_raw_output_exposure"
)
OPERATOR_DECISION = "record_candidate_b_async_process_completion_result_adoption"
PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-process-result"
PROCESS_COMPLETION_RESULT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/completion/result"
)
HISTORY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
TERMINAL_STATES = {"completed", "failed", "blocked", "expired"}
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


class CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-process-completion-result-error",
            "server_time": workflow_status._server_time(),
            "mode": PROCESS_COMPLETION_RESULT_MODE,
            "status": "blocked",
            "process_completion_result_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_process_completion_result(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "process_completion_result_mode") != PROCESS_COMPLETION_RESULT_MODE:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_mode_not_admitted",
            "Only append-only Candidate B process completion/result adoption is admitted.",
            details={"expected_process_completion_result_mode": PROCESS_COMPLETION_RESULT_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_decision_not_admitted",
            "The operator decision does not match the admitted process completion/result action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    terminal_state = _required(fields, "terminal_state")
    if terminal_state not in TERMINAL_STATES:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_terminal_state_not_admitted",
            "The terminal state is not admitted for Candidate B process completion/result adoption.",
            details={"terminal_state": terminal_state, "admitted_terminal_states": sorted(TERMINAL_STATES)},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    process_projection = _selected_process_execution_projection(row, fields)
    process_receipt = _read_process_execution_receipt(process_projection["process_execution_receipt_id"])
    process_receipt_hash = _validate_process_execution_receipt(process_receipt, process_projection)
    result = _completion_result(row, fields, terminal_state)
    authority = _process_completion_result_authority(
        row=row,
        history=history,
        process_projection=process_projection,
        terminal_state=terminal_state,
        result=result,
    )
    authority_hash = workflow_status._stable_hash(authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {"client_request_id": request_id, "process_completion_result_authority_hash": authority_hash}
    )
    receipt_id = f"{PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_receipt(
        receipt_id=receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        process_projection=process_projection,
        process_receipt_hash=process_receipt_hash,
        terminal_state=terminal_state,
        result=result,
        authority=authority,
        authority_hash=authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_process_completion_result_receipt(
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
        "process_completion_result_receipt_hash": receipt_hash,
        "process_completion_result_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-process-result://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "process_completion_result_endpoint": PROCESS_COMPLETION_RESULT_ENDPOINT,
        "status_request": dict(result["result_status_request"] or row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_forbidden_request_fields",
            "Process completion/result adoption does not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, job execution, cancel, retry, resume, stdout, or stderr.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_{exc.code}",
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
            route_family="completion_result_adoption",
            rendered_surface="process_completion_result",
        )
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_process_execution_projection(
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    projection = row.get("process_execution_projection")
    if not isinstance(projection, Mapping) or projection.get("process_execution_projection_state") != "started":
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_process_execution_missing",
            "Process completion/result adoption requires an existing started process-execution receipt.",
            http_status=409,
        )
    expected = {
        "process_execution_receipt_id": projection.get("process_execution_receipt_id"),
        "process_execution_receipt_hash": projection.get("process_execution_receipt_hash"),
        "process_execution_authority_hash": projection.get("process_execution_authority_hash"),
    }
    mismatches = [
        {"field": field, "expected": value, "received": fields.get(field)}
        for field, value in expected.items()
        if fields.get(field) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_stale_process_execution",
            "The selected process-execution receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return dict(projection)


def _completion_result(row: Mapping[str, Any], fields: Mapping[str, Any], terminal_state: str) -> dict[str, Any]:
    if terminal_state == "completed":
        return _completed_result(row, fields)
    result_fields = ("result_workflow_receipt_id", "result_workflow_receipt_hash")
    unexpected = [field for field in result_fields if fields.get(field)]
    if unexpected:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_unexpected_result_receipt",
            "Failed, blocked, or expired process results must not submit result workflow receipts.",
            details={"unexpected_fields": unexpected},
        )
    failure = {
        "terminal_failure_code": _required(fields, "terminal_failure_code"),
        "terminal_failure_phase": _required(fields, "terminal_failure_phase"),
        "redacted_failure_summary_hash": _required_hash(fields, "redacted_failure_summary_hash"),
    }
    return {
        **failure,
        "result_workflow_receipt_id": "",
        "result_workflow_receipt_hash": "",
        "result_authority_hash": "",
        "result_status_request": {},
        "result_status_request_hash": "",
        "result_downstream_proof_hash": "",
    }


def _completed_result(row: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "result_workflow_receipt_id")
    try:
        workflow_status._validate_storage_id(receipt_id, prefix=workflow_status.WORKFLOW_RECEIPT_PREFIX)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    receipt = _read_json_receipt(_workflow_receipt_root() / receipt_id / "receipt.json")
    if "server_owned_workflow_run" in receipt:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_run_receipt_not_admitted",
            "Completed process result adoption requires a source workflow result receipt, not a workflow-run receipt.",
            http_status=409,
            details={"result_workflow_receipt_id": receipt_id},
        )
    status_fields = {
        "baseline_run_id": str(receipt.get("baseline_run_id") or ""),
        "candidate_a_run_id": str(receipt.get("candidate_a_run_id") or ""),
        "candidate_b_run_id": str(receipt.get("candidate_b_run_id") or ""),
        "bridge_receipt_id": str(receipt.get("bridge_receipt_id") or ""),
        "downstream_proof_id": str(receipt.get("downstream_proof_id") or ""),
    }
    try:
        receipt_hash = workflow_status._validate_workflow_receipt(receipt, receipt_id=receipt_id, fields=status_fields)
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if fields.get("result_workflow_receipt_hash") != receipt_hash:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_stale_result_receipt",
            "The selected result workflow receipt hash is missing, stale, or contradictory.",
            http_status=409,
            details={"result_workflow_receipt_id": receipt_id},
        )
    _validate_result_matches_row(receipt, row, receipt_id)
    status_request = {
        "client_request_id": f"candidate-b-full-corpus-process-result-{receipt_id}-status",
        "status_mode": workflow_status.STATUS_MODE,
        "operator_decision": workflow_status.OPERATOR_DECISION,
        "operator_workflow_receipt_id": receipt_id,
        **status_fields,
    }
    authority = {
        "result_workflow_receipt_id": receipt_id,
        "result_workflow_receipt_hash": receipt_hash,
        "baseline_run_id": status_fields["baseline_run_id"],
        "candidate_a_run_id": status_fields["candidate_a_run_id"],
        "candidate_b_run_id": status_fields["candidate_b_run_id"],
        "compare_target_set_hash": str(receipt["compare_target_set_hash"]),
        "bridge_receipt_id": status_fields["bridge_receipt_id"],
        "downstream_proof_id": status_fields["downstream_proof_id"],
        "downstream_proof_hash": str(receipt["downstream_proof_hash"]),
        "material_relative_name": str(receipt.get("corpus", {}).get("material_relative_name") or ""),
    }
    return {
        "terminal_failure_code": "",
        "terminal_failure_phase": "",
        "redacted_failure_summary_hash": "",
        "result_workflow_receipt_id": receipt_id,
        "result_workflow_receipt_hash": receipt_hash,
        "result_authority_hash": workflow_status._stable_hash(authority),
        "result_status_request": status_request,
        "result_status_request_hash": workflow_status._stable_hash(status_request),
        "result_downstream_proof_hash": str(receipt["downstream_proof_hash"]),
    }


def _validate_result_matches_row(receipt: Mapping[str, Any], row: Mapping[str, Any], receipt_id: str) -> None:
    corpus = receipt.get("corpus")
    material_name = corpus.get("material_relative_name") if isinstance(corpus, Mapping) else ""
    expected = {
        "baseline_run_id": row["baseline_run_id"],
        "candidate_a_run_id": row["candidate_a_run_id"],
        "candidate_b_run_id": row["candidate_b_run_id"],
        "compare_target_set_hash": row["compare_target_set_hash"],
        "material_relative_name": row["material_relative_name"],
    }
    received = {
        "baseline_run_id": receipt.get("baseline_run_id"),
        "candidate_a_run_id": receipt.get("candidate_a_run_id"),
        "candidate_b_run_id": receipt.get("candidate_b_run_id"),
        "compare_target_set_hash": receipt.get("compare_target_set_hash"),
        "material_relative_name": material_name,
    }
    mismatches = [
        {"field": field, "expected": value, "received": received.get(field)}
        for field, value in expected.items()
        if received.get(field) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_unrelated_result_receipt",
            "The selected result workflow receipt does not match the current Candidate B workflow lineage.",
            http_status=409,
            details={"result_workflow_receipt_id": receipt_id, "mismatches": mismatches},
        )


def _process_completion_result_authority(
    *,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    process_projection: Mapping[str, Any],
    terminal_state: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "process_completion_result_mode": PROCESS_COMPLETION_RESULT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "process_execution_receipt_id": process_projection["process_execution_receipt_id"],
        "process_execution_receipt_hash": process_projection["process_execution_receipt_hash"],
        "process_execution_authority_hash": process_projection["process_execution_authority_hash"],
        "terminal_state": terminal_state,
        "result_workflow_receipt_id": result["result_workflow_receipt_id"],
        "result_workflow_receipt_hash": result["result_workflow_receipt_hash"],
        "result_authority_hash": result["result_authority_hash"],
        "result_status_request_hash": result["result_status_request_hash"],
        "result_downstream_proof_hash": result["result_downstream_proof_hash"],
        "terminal_failure_code": result["terminal_failure_code"],
        "terminal_failure_phase": result["terminal_failure_phase"],
        "redacted_failure_summary_hash": result["redacted_failure_summary_hash"],
    }


def _load_or_write_receipt(
    *,
    receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    process_projection: Mapping[str, Any],
    process_receipt_hash: str,
    terminal_state: str,
    result: Mapping[str, Any],
    authority: Mapping[str, Any],
    authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    target = _workflow_receipt_root() / receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_process_completion_result_receipt(
            existing,
            request_id=request_id,
            receipt_id=receipt_id,
            authority_hash=authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True
    _reject_competing_receipt(row["operator_workflow_receipt_id"], process_projection["process_execution_authority_hash"])
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_COMPLETION_RESULT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "process_completion_result_state": terminal_state,
        "process_completion_result_receipt_id": receipt_id,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "process_execution_receipt_id": process_projection["process_execution_receipt_id"],
        "process_execution_receipt_hash": process_receipt_hash,
        "process_execution_authority_hash": process_projection["process_execution_authority_hash"],
        "terminal_state": terminal_state,
        **dict(result),
        "process_completion_result_authority": dict(authority),
        "process_completion_result_authority_hash": authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_process_completion_result_receipt": True,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
        "process_completion_result_runtime_selected": True,
        "result_adoption_runtime_selected": terminal_state == "completed",
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
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
            "inspect redacted process completion/result projection through workflow status",
            "drive adopted result through Layer 3 downstream only through existing validated status request",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "process_completion_result_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_receipt(operator_workflow_receipt_id: str, process_execution_authority_hash: str) -> None:
    root = _workflow_receipt_root()
    for receipt_file in sorted(root.glob(f"{PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX}-*/receipt.json")):
        receipt = _read_json_receipt(receipt_file)
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
                "candidate_b_full_corpus_operator_workflow_process_completion_result_competing_receipt",
                "The selected workflow already has a completion/result receipt.",
                http_status=409,
                details={
                    "process_completion_result_receipt_id": receipt_file.parent.name,
                    "process_execution_authority_hash": process_execution_authority_hash,
                },
            )


def _validate_process_completion_result_receipt(
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
        "mode": PROCESS_COMPLETION_RESULT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "process_completion_result_receipt_id": receipt_id,
        "process_completion_result_authority_hash": authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_process_completion_result_receipt": True,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
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
        {key: value for key, value in receipt.items() if key not in {"process_completion_result_receipt_hash", "server_time"}}
    )
    if receipt.get("process_completion_result_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_completion_result_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_completion_result_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_receipt_mismatch",
            "The Candidate B process completion/result receipt is stale or contradictory.",
            http_status=409,
            details={"process_completion_result_receipt_id": receipt_id, "mismatches": mismatches},
        )
    return str(receipt["process_completion_result_receipt_hash"])


def _read_process_execution_receipt(receipt_id: str) -> dict[str, Any]:
    try:
        workflow_status._validate_storage_id(receipt_id, prefix=workflow_status.PROCESS_EXECUTION_RECEIPT_PREFIX)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            f"candidate_b_full_corpus_operator_workflow_process_completion_result_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    return _read_json_receipt(_workflow_receipt_root() / receipt_id / "receipt.json")


def _validate_process_execution_receipt(
    receipt: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> str:
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {"process_execution_receipt_hash", "server_time"}}
    )
    expected = {
        "schema_id": workflow_status.PROCESS_EXECUTION_SCHEMA_ID,
        "mode": workflow_status.PROCESS_EXECUTION_MODE,
        "process_execution_receipt_id": projection["process_execution_receipt_id"],
        "process_execution_authority_hash": projection["process_execution_authority_hash"],
        "process_execution_receipt_hash": projection["process_execution_receipt_hash"],
    }
    mismatches = [
        {"field": field, "expected": value, "received": receipt.get(field)}
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    if receipt.get("process_execution_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_execution_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_execution_receipt_hash"),
            }
        )
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_stale_process_execution",
            "The selected process-execution receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_dir_invalid",
            "The configured Candidate B workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_receipt_missing",
            "A required Candidate B workflow receipt could not be found.",
            http_status=404,
            details={"receipt_ref": path.parent.name},
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_receipt_unreadable",
            "A Candidate B workflow receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_receipt_invalid",
            "A Candidate B workflow receipt is not a JSON object.",
            http_status=409,
        )
    return payload


def _required(fields: Mapping[str, Any], field: str) -> str:
    value = str(fields.get(field) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_required_field_missing",
            "A required Candidate B process completion/result field is missing.",
            details={"field": field},
        )
    return value


def _required_hash(fields: Mapping[str, Any], field: str) -> str:
    value = _required(fields, field)
    if len(value) != 64:
        raise CandidateBFullCorpusOperatorWorkflowProcessCompletionResultError(
            "candidate_b_full_corpus_operator_workflow_process_completion_result_hash_invalid",
            "A Candidate B process completion/result hash field is invalid.",
            details={"field": field},
        )
    return value
