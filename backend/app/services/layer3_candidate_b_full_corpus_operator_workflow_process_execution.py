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
PROCESS_EXECUTION_STATE = "started"
PROCESS_EXECUTION_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-process-execution"
ALLOWLISTED_COMMAND_FAMILY = "tools/run_candidate_b_full_corpus_operator_workflow.py"
PROCESS_EXECUTION_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution"
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
        workflow_progress_checkpoint._validate_selected_authority(history, row, fields)
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
    launch_result = _launch_server_owned_process(
        process_execution_receipt_id=process_execution_receipt_id,
        process_invocation_hash=process_invocation_hash,
    )
    redacted_process_status_projection = {
        "process_execution_projection_state": PROCESS_EXECUTION_STATE,
        "read_only_process_execution_projection": True,
        "process_execution_receipt_available": True,
        "process_execution_receipt_id": process_execution_receipt_id,
        "process_execution_authority_hash": process_execution_authority_hash,
        "process_invocation_hash": process_invocation_hash,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "redacted_process_ref": launch_result["redacted_process_ref"],
        "server_process_handle_hash": launch_result["server_process_handle_hash"],
        "background_process_runtime_selected_now": True,
        "actual_subprocess_spawn_admitted_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
    }
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_EXECUTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "process_execution_state": PROCESS_EXECUTION_STATE,
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
        "append_only_process_execution_receipt": True,
        "process_started": True,
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
        "actual_subprocess_spawn_admitted_now": True,
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
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "process_execution_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


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


def _validate_process_execution_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    process_execution_receipt_id: str,
    process_invocation_hash: str,
    process_execution_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_EXECUTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "process_execution_state": PROCESS_EXECUTION_STATE,
        "process_execution_receipt_id": process_execution_receipt_id,
        "process_invocation_hash": process_invocation_hash,
        "process_execution_authority_hash": process_execution_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "allowlisted_command_family": ALLOWLISTED_COMMAND_FAMILY,
        "append_only_process_execution_receipt": True,
        "process_started": True,
        "source_run_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
        "background_process_runtime_selected": True,
        "background_process_runtime_selected_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": True,
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
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
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


def _launch_server_owned_process(
    *,
    process_execution_receipt_id: str,
    process_invocation_hash: str,
) -> dict[str, Any]:
    command = _server_owned_command()
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
    except OSError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProcessExecutionError(
            "candidate_b_full_corpus_operator_workflow_process_execution_launch_failed",
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


def _server_owned_command() -> list[str]:
    return [
        sys.executable,
        str(_allowlisted_script()),
        "--execution-mode",
        "local-testclient",
        "--checkout-root",
        str(_repo_root()),
        "--receipt-dir",
        str(_workflow_receipt_root()),
    ]


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
