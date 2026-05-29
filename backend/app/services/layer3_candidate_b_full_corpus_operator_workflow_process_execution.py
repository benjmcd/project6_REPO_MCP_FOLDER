from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_process_execution.v1"
SCHEMA_VERSION = 1
PROCESS_EXECUTION_MODE = (
    "server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority"
)
OPERATOR_DECISION = "record_candidate_b_async_background_process_execution"
PROCESS_EXECUTION_STARTED_STATE = "started"
PROCESS_EXECUTION_BLOCKED_STATE = "blocked"
PROCESS_EXECUTION_STATE = PROCESS_EXECUTION_STARTED_STATE
PROCESS_EXECUTION_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-process-execution"
PROCESS_LAUNCH_INTENT_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-process-launch-intent"
ALLOWLISTED_COMMAND_FAMILY = "tools/run_candidate_b_full_corpus_operator_workflow.py"
PROCESS_EXECUTION_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution"
)
HISTORY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
PROCESS_LAUNCH_FAILED_ERROR_CODE = (
    "candidate_b_full_corpus_operator_workflow_process_execution_launch_failed"
)
PROCESS_LAUNCH_TIMEOUT_ERROR_CODE = (
    "candidate_b_full_corpus_operator_workflow_process_execution_launch_timeout"
)
PROCESS_LAUNCH_FAILURE_PHASE = "server_owned_process_launch"

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
    "background_worker",
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


class CandidateBFullCorpusOperatorWorkflowProcessExecutionError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-process-execution-error",
            "server_time": workflow_status._server_time(),
            "mode": PROCESS_EXECUTION_MODE,
            "status": "blocked",
            "process_execution_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_process_execution(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "process_execution_mode") != PROCESS_EXECUTION_MODE:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_mode_not_admitted",
            "Only server-owned allowlisted Candidate B process execution is admitted.",
            details={"expected_process_execution_mode": PROCESS_EXECUTION_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_decision_not_admitted",
            "The operator decision does not match the admitted process-execution action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    execution_boundary_projection = _selected_execution_boundary_projection(row, fields)
    invocation = _allowlisted_process_invocation(row, history, execution_boundary_projection)
    process_invocation_hash = workflow_status._stable_hash(invocation)
    process_execution_authority = {
        "process_execution_mode": PROCESS_EXECUTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "execution_boundary_receipt_id": execution_boundary_projection["execution_boundary_receipt_id"],
        "execution_boundary_receipt_hash": execution_boundary_projection["execution_boundary_receipt_hash"],
        "execution_boundary_authority_hash": execution_boundary_projection["execution_boundary_authority_hash"],
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "process_invocation_hash": process_invocation_hash,
        "background_process_runtime_selected_now": True,
        "actual_subprocess_spawn_admitted_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
    }
    process_execution_authority_hash = workflow_status._stable_hash(process_execution_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "process_execution_authority_hash": process_execution_authority_hash,
        }
    )
    process_execution_receipt_id = f"{PROCESS_EXECUTION_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_process_execution_receipt(
        process_execution_receipt_id=process_execution_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        execution_boundary_projection=execution_boundary_projection,
        process_invocation=invocation,
        process_invocation_hash=process_invocation_hash,
        process_execution_authority=process_execution_authority,
        process_execution_authority_hash=process_execution_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_process_execution_receipt(
        receipt,
        request_id=request_id,
        process_execution_receipt_id=process_execution_receipt_id,
        process_invocation_hash=process_invocation_hash,
        process_execution_authority_hash=process_execution_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "process_execution_receipt_hash": receipt_hash,
        "process_execution_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-process-execution://"
            f"{process_execution_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "process_execution_endpoint": PROCESS_EXECUTION_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_forbidden_request_fields",
            "Workflow process execution does not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, job execution, cancel, retry, resume, stdout, or stderr.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            f"candidate_b_full_corpus_operator_workflow_process_execution_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            f"candidate_b_full_corpus_operator_workflow_process_execution_{exc.code}",
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
            route_family="process_execution",
            rendered_surface="process_execution",
        )
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            f"candidate_b_full_corpus_operator_workflow_process_execution_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_execution_boundary_projection(
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        projection = workflow_status._execution_boundary_projection(
            str(row["operator_workflow_receipt_id"]),
            str(row["operator_workflow_receipt_hash"]),
        )
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            f"candidate_b_full_corpus_operator_workflow_process_execution_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if projection.get("execution_boundary_projection_state") != "boundary_recorded":
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_boundary_missing",
            "Process execution requires a current execution-boundary receipt before a server-owned process can start.",
            http_status=409,
        )
    expected = {
        "execution_boundary_receipt_id": projection.get("execution_boundary_receipt_id"),
        "execution_boundary_receipt_hash": projection.get("execution_boundary_receipt_hash"),
        "execution_boundary_authority_hash": projection.get("execution_boundary_authority_hash"),
    }
    mismatches = [
        {"field": field, "expected": value, "received": fields.get(field)}
        for field, value in expected.items()
        if fields.get(field) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_stale_execution_boundary",
            "The selected execution-boundary authority is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return projection


def _allowlisted_process_invocation(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    execution_boundary_projection: Mapping[str, Any],
) -> dict[str, Any]:
    script = _allowlisted_script()
    return {
        "process_execution_mode": PROCESS_EXECUTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "allowlisted_command_family_hash": _file_hash(script),
        "server_owned_workdir_ref": "repo://.",
        "server_owned_stdout_policy": "discard_without_receipt_capture",
        "server_owned_stderr_policy": "discard_without_receipt_capture",
        "server_resolved_arguments_authority": (
            "server_resolved_receipt_ids_and_configured_runtime_roots_only"
        ),
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "execution_boundary_receipt_id": execution_boundary_projection["execution_boundary_receipt_id"],
        "execution_boundary_receipt_hash": execution_boundary_projection["execution_boundary_receipt_hash"],
        "execution_boundary_authority_hash": execution_boundary_projection["execution_boundary_authority_hash"],
        "browser_command_authority_admitted": False,
        "operator_supplied_command_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
    }


def _load_or_write_process_execution_receipt(
    *,
    process_execution_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    execution_boundary_projection: Mapping[str, Any],
    process_invocation: Mapping[str, Any],
    process_invocation_hash: str,
    process_execution_authority: Mapping[str, Any],
    process_execution_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    target = _workflow_receipt_root() / process_execution_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_process_execution_receipt(
            existing,
            request_id=request_id,
            process_execution_receipt_id=process_execution_receipt_id,
            process_invocation_hash=process_invocation_hash,
            process_execution_authority_hash=process_execution_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    _reject_competing_process_execution(
        process_execution_receipt_id=process_execution_receipt_id,
        operator_workflow_receipt_id=str(row["operator_workflow_receipt_id"]),
        execution_boundary_authority_hash=str(execution_boundary_projection["execution_boundary_authority_hash"]),
    )
    _acquire_process_execution_index(
        process_execution_receipt_id=process_execution_receipt_id,
        operator_workflow_receipt_id=str(row["operator_workflow_receipt_id"]),
        execution_boundary_authority_hash=str(execution_boundary_projection["execution_boundary_authority_hash"]),
    )
    launch_intent_receipt = _load_or_write_process_launch_intent_receipt(
        process_execution_receipt_id=process_execution_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        execution_boundary_projection=execution_boundary_projection,
        process_invocation=process_invocation,
        process_invocation_hash=process_invocation_hash,
        process_execution_authority=process_execution_authority,
        process_execution_authority_hash=process_execution_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    launch_intent_receipt_id = str(launch_intent_receipt["process_launch_intent_receipt_id"])
    launch_intent_receipt_hash = str(launch_intent_receipt["process_launch_intent_receipt_hash"])
    selected_process_execution_authority = _selected_process_execution_authority(
        row=row,
        execution_boundary_projection=execution_boundary_projection,
        process_execution_receipt_id=process_execution_receipt_id,
        process_execution_authority_hash=process_execution_authority_hash,
        process_invocation_hash=process_invocation_hash,
        launch_intent_receipt_id=launch_intent_receipt_id,
        launch_intent_receipt_hash=launch_intent_receipt_hash,
    )
    launch_error: CandidateBFullCorpusOperatorWorkflowProcessExecutionError | None = None
    try:
        launch_result = _launch_server_owned_process(
            process_execution_receipt_id=process_execution_receipt_id,
            process_invocation_hash=process_invocation_hash,
            selected_process_execution_authority=selected_process_execution_authority,
        )
    except CandidateBFullCorpusOperatorWorkflowProcessExecutionError as exc:
        if exc.code not in {PROCESS_LAUNCH_FAILED_ERROR_CODE, PROCESS_LAUNCH_TIMEOUT_ERROR_CODE}:
            raise
        launch_error = exc
        launch_result = _blocked_launch_result(
            process_execution_receipt_id=process_execution_receipt_id,
            process_invocation_hash=process_invocation_hash,
            launch_error=exc,
        )
    process_execution_state = (
        PROCESS_EXECUTION_BLOCKED_STATE if launch_error else PROCESS_EXECUTION_STARTED_STATE
    )
    process_status = "blocked" if launch_error else "available"
    process_started = launch_error is None
    actual_subprocess_spawn_admitted_now = launch_error is None
    redacted_process_status_projection = {
        "process_execution_projection_state": process_execution_state,
        "read_only_process_execution_projection": True,
        "process_execution_receipt_available": True,
        "process_execution_receipt_id": process_execution_receipt_id,
        "process_execution_authority_hash": process_execution_authority_hash,
        "process_invocation_hash": process_invocation_hash,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "redacted_process_ref": launch_result["redacted_process_ref"],
        "server_process_handle_hash": launch_result["server_process_handle_hash"],
        "background_process_runtime_selected_now": True,
        "actual_subprocess_spawn_admitted_now": actual_subprocess_spawn_admitted_now,
        "job_execution_runtime_selected_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
    }
    if launch_error:
        redacted_process_status_projection.update(
            {
                "process_failure_recorded": True,
                "process_timeout_recorded": launch_error.code == PROCESS_LAUNCH_TIMEOUT_ERROR_CODE,
                "process_failure_code": launch_error.code,
                "process_failure_phase": PROCESS_LAUNCH_FAILURE_PHASE,
                "redacted_failure_summary_hash": launch_result["redacted_failure_summary_hash"],
            }
        )
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_EXECUTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": process_status,
        "process_execution_state": process_execution_state,
        "process_execution_receipt_id": process_execution_receipt_id,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "execution_boundary_receipt_id": execution_boundary_projection["execution_boundary_receipt_id"],
        "execution_boundary_receipt_hash": execution_boundary_projection["execution_boundary_receipt_hash"],
        "execution_boundary_authority_hash": execution_boundary_projection["execution_boundary_authority_hash"],
        "process_invocation": dict(process_invocation),
        "process_invocation_hash": process_invocation_hash,
        "process_execution_authority": dict(process_execution_authority),
        "process_execution_authority_hash": process_execution_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "redacted_process_status_projection": redacted_process_status_projection,
        "redacted_process_ref": launch_result["redacted_process_ref"],
        "server_process_handle_hash": launch_result["server_process_handle_hash"],
        "process_launch_intent_receipt_id": launch_intent_receipt_id,
        "process_launch_intent_receipt_hash": launch_intent_receipt_hash,
        "process_launch_intent_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-process-launch-intent://"
            f"{launch_intent_receipt_id}/{launch_intent_receipt_hash[:24]}"
        ),
        "selected_process_execution_authority": selected_process_execution_authority,
        "selected_process_execution_authority_hash": selected_process_execution_authority[
            "selected_process_authority_envelope_hash"
        ],
        "append_only_process_execution_receipt": True,
        "process_started": process_started,
        "source_run_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "completion_failure_receipt_mutated": False,
        "retry_completion_failure_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
        "background_process_runtime_selected": True,
        "background_process_runtime_selected_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": actual_subprocess_spawn_admitted_now,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "default_scope_expansion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
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
            "inspect redacted process-execution projection through workflow status",
            "select process completion or result adoption only through a separate freeze",
        ],
    }
    if launch_error:
        receipt_input.update(
            {
                "process_failure_recorded": True,
                "process_timeout_recorded": launch_error.code == PROCESS_LAUNCH_TIMEOUT_ERROR_CODE,
                "process_failure_code": launch_error.code,
                "process_failure_phase": PROCESS_LAUNCH_FAILURE_PHASE,
                "redacted_failure_summary_hash": launch_result["redacted_failure_summary_hash"],
                "next_allowed_actions": [
                    "refresh workflow-run history",
                    "inspect redacted process-execution failure projection through workflow status",
                    "do not adopt process completion or result until a separate successful process-execution receipt exists",
                ],
            }
        )
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "process_execution_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _load_or_write_process_launch_intent_receipt(
    *,
    process_execution_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    execution_boundary_projection: Mapping[str, Any],
    process_invocation: Mapping[str, Any],
    process_invocation_hash: str,
    process_execution_authority: Mapping[str, Any],
    process_execution_authority_hash: str,
    idempotency_key_hash: str,
) -> dict[str, Any]:
    receipt_input = {
        "schema_id": "layer3.candidate_b_full_corpus_operator_workflow_process_launch_intent.v1",
        "schema_version": SCHEMA_VERSION,
        "mode": "server_owned_allowlisted_process_launch_intent_v1",
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "process_launch_intent_state": "recorded",
        "process_execution_receipt_id": process_execution_receipt_id,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "execution_boundary_receipt_id": execution_boundary_projection["execution_boundary_receipt_id"],
        "execution_boundary_receipt_hash": execution_boundary_projection["execution_boundary_receipt_hash"],
        "execution_boundary_authority_hash": execution_boundary_projection["execution_boundary_authority_hash"],
        "process_invocation": dict(process_invocation),
        "process_invocation_hash": process_invocation_hash,
        "process_execution_authority": dict(process_execution_authority),
        "process_execution_authority_hash": process_execution_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "append_only_process_launch_intent_receipt": True,
        "process_started": False,
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
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt_id = f"{PROCESS_LAUNCH_INTENT_RECEIPT_PREFIX}-{receipt_hash[:24]}"
    target = _workflow_receipt_root() / receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_process_launch_intent_receipt(
            existing,
            expected_receipt_input=receipt_input,
            receipt_id=receipt_id,
            receipt_hash=receipt_hash,
        )
        return existing
    receipt = {
        **receipt_input,
        "process_launch_intent_receipt_id": receipt_id,
        "process_launch_intent_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    _validate_process_launch_intent_receipt(
        receipt,
        expected_receipt_input=receipt_input,
        receipt_id=receipt_id,
        receipt_hash=receipt_hash,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def _validate_process_launch_intent_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_receipt_input: Mapping[str, Any],
    receipt_id: str,
    receipt_hash: str,
) -> None:
    expected = {
        **dict(expected_receipt_input),
        "process_launch_intent_receipt_id": receipt_id,
        "process_launch_intent_receipt_hash": receipt_hash,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    if receipt.get("process_launch_intent_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_launch_intent_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_launch_intent_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            f"candidate_b_full_corpus_operator_workflow_process_launch_intent_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_launch_intent_stale_receipt",
            "The selected Candidate B process launch-intent receipt is stale or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _selected_process_execution_authority(
    *,
    row: Mapping[str, Any],
    execution_boundary_projection: Mapping[str, Any],
    process_execution_receipt_id: str,
    process_execution_authority_hash: str,
    process_invocation_hash: str,
    launch_intent_receipt_id: str,
    launch_intent_receipt_hash: str,
) -> dict[str, Any]:
    authority = {
        "schema_id": "layer3.candidate_b_full_corpus_operator_workflow_selected_process_execution_authority.v1",
        "selected_operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "selected_operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "selected_execution_boundary_receipt_id": execution_boundary_projection["execution_boundary_receipt_id"],
        "selected_execution_boundary_receipt_hash": execution_boundary_projection["execution_boundary_receipt_hash"],
        "selected_execution_boundary_authority_hash": execution_boundary_projection[
            "execution_boundary_authority_hash"
        ],
        "selected_process_execution_receipt_id": process_execution_receipt_id,
        "selected_process_execution_authority_hash": process_execution_authority_hash,
        "selected_process_invocation_hash": process_invocation_hash,
        "selected_process_launch_intent_receipt_id": launch_intent_receipt_id,
        "selected_process_launch_intent_receipt_hash": launch_intent_receipt_hash,
    }
    authority["selected_process_authority_envelope_hash"] = workflow_status._stable_hash(authority)
    return authority


def _reject_competing_process_execution(
    *,
    process_execution_receipt_id: str,
    operator_workflow_receipt_id: str,
    execution_boundary_authority_hash: str,
) -> None:
    for receipt_file in sorted(_workflow_receipt_root().glob(f"{PROCESS_EXECUTION_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == process_execution_receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if (
            existing.get("operator_workflow_receipt_id") == operator_workflow_receipt_id
            and existing.get("execution_boundary_authority_hash") == execution_boundary_authority_hash
        ):
            raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
                "candidate_b_full_corpus_operator_workflow_process_execution_conflict",
                "The selected Candidate B execution boundary already has a process-execution receipt.",
                http_status=409,
                details={"existing_process_execution_receipt_id": existing_id},
            )


def _acquire_process_execution_index(
    *,
    process_execution_receipt_id: str,
    operator_workflow_receipt_id: str,
    execution_boundary_authority_hash: str,
) -> None:
    index_hash = workflow_status._stable_hash(
        {
            "operator_workflow_receipt_id": operator_workflow_receipt_id,
            "execution_boundary_authority_hash": execution_boundary_authority_hash,
            "exclusive_process_execution_per_execution_boundary": True,
        }
    )
    index_dir = _workflow_receipt_root() / f"{PROCESS_EXECUTION_RECEIPT_PREFIX}-boundary-index-{index_hash[:24]}"
    try:
        index_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        _reject_competing_process_execution(
            process_execution_receipt_id=process_execution_receipt_id,
            operator_workflow_receipt_id=operator_workflow_receipt_id,
            execution_boundary_authority_hash=execution_boundary_authority_hash,
        )
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_conflict",
            "The selected Candidate B execution boundary already has a process-execution receipt.",
            http_status=409,
            details={"process_execution_index": index_dir.name},
        ) from exc


def _validate_process_execution_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    process_execution_receipt_id: str,
    process_invocation_hash: str,
    process_execution_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    process_execution_state = str(receipt.get("process_execution_state") or "")
    if process_execution_state not in {PROCESS_EXECUTION_STARTED_STATE, PROCESS_EXECUTION_BLOCKED_STATE}:
        mismatches = [
            {
                "field": "process_execution_state",
                "expected": f"{PROCESS_EXECUTION_STARTED_STATE}|{PROCESS_EXECUTION_BLOCKED_STATE}",
                "received": receipt.get("process_execution_state"),
            }
        ]
    else:
        mismatches = []
    expected_status = "blocked" if process_execution_state == PROCESS_EXECUTION_BLOCKED_STATE else "available"
    expected_process_started = process_execution_state == PROCESS_EXECUTION_STARTED_STATE
    expected_subprocess_spawn = process_execution_state == PROCESS_EXECUTION_STARTED_STATE
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_EXECUTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": expected_status,
        "process_execution_receipt_id": process_execution_receipt_id,
        "process_invocation_hash": process_invocation_hash,
        "process_execution_authority_hash": process_execution_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "append_only_process_execution_receipt": True,
        "process_started": expected_process_started,
        "source_run_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
        "background_process_runtime_selected": True,
        "background_process_runtime_selected_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": expected_subprocess_spawn,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
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
    mismatches.extend(
        [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
        ]
    )
    launch_intent_id = str(receipt.get("process_launch_intent_receipt_id") or "")
    launch_intent_hash = str(receipt.get("process_launch_intent_receipt_hash") or "")
    if not launch_intent_id.startswith(f"{PROCESS_LAUNCH_INTENT_RECEIPT_PREFIX}-"):
        mismatches.append(
            {
                "field": "process_launch_intent_receipt_id",
                "expected": f"{PROCESS_LAUNCH_INTENT_RECEIPT_PREFIX}-*",
                "received": receipt.get("process_launch_intent_receipt_id"),
            }
        )
    if not _is_sha256_hex(launch_intent_hash):
        mismatches.append(
            {
                "field": "process_launch_intent_receipt_hash",
                "expected": "lowercase_sha256_hex",
                "received": receipt.get("process_launch_intent_receipt_hash"),
            }
        )
    selected_authority = receipt.get("selected_process_execution_authority")
    if not isinstance(selected_authority, Mapping):
        mismatches.append(
            {
                "field": "selected_process_execution_authority",
                "expected": "object",
                "received": type(selected_authority).__name__,
            }
        )
    else:
        selected_expected = {
            "schema_id": "layer3.candidate_b_full_corpus_operator_workflow_selected_process_execution_authority.v1",
            "selected_operator_workflow_receipt_id": receipt.get("operator_workflow_receipt_id"),
            "selected_operator_workflow_receipt_hash": receipt.get("operator_workflow_receipt_hash"),
            "selected_execution_boundary_receipt_id": receipt.get("execution_boundary_receipt_id"),
            "selected_execution_boundary_receipt_hash": receipt.get("execution_boundary_receipt_hash"),
            "selected_execution_boundary_authority_hash": receipt.get("execution_boundary_authority_hash"),
            "selected_process_execution_receipt_id": process_execution_receipt_id,
            "selected_process_execution_authority_hash": process_execution_authority_hash,
            "selected_process_invocation_hash": process_invocation_hash,
            "selected_process_launch_intent_receipt_id": launch_intent_id,
            "selected_process_launch_intent_receipt_hash": launch_intent_hash,
        }
        mismatches.extend(
            [
                {
                    "field": f"selected_process_execution_authority.{field}",
                    "expected": expected_value,
                    "received": selected_authority.get(field),
                }
                for field, expected_value in selected_expected.items()
                if selected_authority.get(field) != expected_value
            ]
        )
        selected_envelope_hash = workflow_status._stable_hash(selected_expected)
        if selected_authority.get("selected_process_authority_envelope_hash") != selected_envelope_hash:
            mismatches.append(
                {
                    "field": "selected_process_execution_authority.selected_process_authority_envelope_hash",
                    "expected": selected_envelope_hash,
                    "received": selected_authority.get("selected_process_authority_envelope_hash"),
                }
            )
        if receipt.get("selected_process_execution_authority_hash") != selected_envelope_hash:
            mismatches.append(
                {
                    "field": "selected_process_execution_authority_hash",
                    "expected": selected_envelope_hash,
                    "received": receipt.get("selected_process_execution_authority_hash"),
                }
            )
    failure_code = str(receipt.get("process_failure_code") or "")
    if process_execution_state == PROCESS_EXECUTION_BLOCKED_STATE:
        expected_timeout = failure_code == PROCESS_LAUNCH_TIMEOUT_ERROR_CODE
        blocked_expected = {
            "process_failure_recorded": True,
            "process_timeout_recorded": expected_timeout,
            "process_failure_phase": PROCESS_LAUNCH_FAILURE_PHASE,
        }
        mismatches.extend(
            [
                {"field": field, "expected": expected_value, "received": receipt.get(field)}
                for field, expected_value in blocked_expected.items()
                if receipt.get(field) != expected_value
            ]
        )
        if failure_code not in {PROCESS_LAUNCH_FAILED_ERROR_CODE, PROCESS_LAUNCH_TIMEOUT_ERROR_CODE}:
            mismatches.append(
                {
                    "field": "process_failure_code",
                    "expected": f"{PROCESS_LAUNCH_FAILED_ERROR_CODE}|{PROCESS_LAUNCH_TIMEOUT_ERROR_CODE}",
                    "received": receipt.get("process_failure_code"),
                }
            )
        summary_hash = str(receipt.get("redacted_failure_summary_hash") or "")
        if len(summary_hash) != 64 or any(char not in "0123456789abcdef" for char in summary_hash):
            mismatches.append(
                {
                    "field": "redacted_failure_summary_hash",
                    "expected": "lowercase_sha256_hex",
                    "received": receipt.get("redacted_failure_summary_hash"),
                }
            )
    else:
        started_failure_fields = {
            "process_failure_recorded": False,
            "process_timeout_recorded": False,
            "process_failure_code": "",
            "process_failure_phase": "",
            "redacted_failure_summary_hash": "",
        }
        for field, expected_value in started_failure_fields.items():
            received = receipt.get(field, expected_value)
            if received != expected_value:
                mismatches.append({"field": field, "expected": expected_value, "received": received})
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {"process_execution_receipt_hash", "server_time"}}
    )
    if receipt.get("process_execution_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_execution_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_execution_receipt_hash"),
            }
        )
    if not isinstance(receipt.get("redacted_process_status_projection"), Mapping):
        mismatches.append(
            {
                "field": "redacted_process_status_projection",
                "expected": "object",
                "received": type(receipt.get("redacted_process_status_projection")).__name__,
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            f"candidate_b_full_corpus_operator_workflow_process_execution_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_stale_receipt",
            "The selected Candidate B process-execution receipt is stale or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return str(receipt["process_execution_receipt_hash"])


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _launch_server_owned_process(
    *,
    process_execution_receipt_id: str,
    process_invocation_hash: str,
    selected_process_execution_authority: Mapping[str, Any],
) -> dict[str, Any]:
    command = _server_owned_command(selected_process_execution_authority=selected_process_execution_authority)
    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        process = subprocess.Popen(  # noqa: S603 - command is server-owned and allowlisted.
            command,
            cwd=str(_repo_root()),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
    except TimeoutError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            PROCESS_LAUNCH_TIMEOUT_ERROR_CODE,
            "The server-owned allowlisted Candidate B workflow process start timed out.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    except OSError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            PROCESS_LAUNCH_FAILED_ERROR_CODE,
            "The server-owned allowlisted Candidate B workflow process could not be started.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    server_process_handle_hash = workflow_status._stable_hash(
        {
            "process_execution_receipt_id": process_execution_receipt_id,
            "process_invocation_hash": process_invocation_hash,
            "pid": process.pid,
        }
    )
    return {
        "redacted_process_ref": (
            "candidate-b-full-corpus-operator-workflow-process://"
            f"{process_execution_receipt_id}/{server_process_handle_hash[:24]}"
        ),
        "server_process_handle_hash": server_process_handle_hash,
    }


def _blocked_launch_result(
    *,
    process_execution_receipt_id: str,
    process_invocation_hash: str,
    launch_error: CandidateBFullCorpusOperatorWorkflowProcessExecutionError,
) -> dict[str, str]:
    redacted_failure_summary_hash = workflow_status._stable_hash(
        {
            "process_execution_receipt_id": process_execution_receipt_id,
            "process_invocation_hash": process_invocation_hash,
            "process_failure_code": launch_error.code,
            "process_failure_phase": PROCESS_LAUNCH_FAILURE_PHASE,
            "process_failure_reason": str(launch_error.details.get("reason") or "redacted"),
        }
    )
    return {
        "redacted_process_ref": (
            "candidate-b-full-corpus-operator-workflow-process://"
            f"{process_execution_receipt_id}/{redacted_failure_summary_hash[:24]}"
        ),
        "server_process_handle_hash": redacted_failure_summary_hash,
        "redacted_failure_summary_hash": redacted_failure_summary_hash,
    }


def _server_owned_command(
    *,
    selected_process_execution_authority: Mapping[str, Any] | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(_allowlisted_script()),
        "--execution-mode",
        "local-testclient",
        "--checkout-root",
        str(_repo_root()),
        "--receipt-dir",
        str(_workflow_receipt_root()),
    ]
    if selected_process_execution_authority:
        command.extend(
            [
                "--selected-operator-workflow-receipt-id",
                str(selected_process_execution_authority["selected_operator_workflow_receipt_id"]),
                "--selected-operator-workflow-receipt-hash",
                str(selected_process_execution_authority["selected_operator_workflow_receipt_hash"]),
                "--selected-execution-boundary-receipt-id",
                str(selected_process_execution_authority["selected_execution_boundary_receipt_id"]),
                "--selected-execution-boundary-receipt-hash",
                str(selected_process_execution_authority["selected_execution_boundary_receipt_hash"]),
                "--selected-execution-boundary-authority-hash",
                str(selected_process_execution_authority["selected_execution_boundary_authority_hash"]),
                "--selected-process-execution-receipt-id",
                str(selected_process_execution_authority["selected_process_execution_receipt_id"]),
                "--selected-process-execution-authority-hash",
                str(selected_process_execution_authority["selected_process_execution_authority_hash"]),
                "--selected-process-invocation-hash",
                str(selected_process_execution_authority["selected_process_invocation_hash"]),
                "--selected-process-launch-intent-receipt-id",
                str(selected_process_execution_authority["selected_process_launch_intent_receipt_id"]),
                "--selected-process-launch-intent-receipt-hash",
                str(selected_process_execution_authority["selected_process_launch_intent_receipt_hash"]),
            ]
        )
    return command


def _allowlisted_script() -> Path:
    script = _repo_root() / ALLOWLISTED_COMMAND_FAMILY
    if not script.is_file():
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_dependency_missing",
            "The allowlisted Candidate B full-corpus operator workflow runner is missing.",
            http_status=404,
            details={"allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY},
        )
    return script


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_dir_invalid",
            "The configured Candidate B workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_dir_missing",
            "The configured Candidate B workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_receipt_unreadable",
            "A Candidate B workflow process-execution receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_receipt_invalid",
            "Candidate B workflow process-execution receipts must be JSON objects.",
            http_status=409,
        )
    return payload


def _file_hash(path: Path) -> str:
    return workflow_status._stable_hash({"sha256": path.read_bytes().hex()})


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_required_field_missing",
            "A required Candidate B workflow process-execution field is missing or empty.",
            details={"field": key},
        )
    return value
