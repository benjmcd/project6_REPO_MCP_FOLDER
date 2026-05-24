from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_completion_failure as workflow_completion_failure,
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease as scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
    layer3_candidate_b_full_corpus_operator_workflow_worker_attempt as workflow_worker_attempt,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_execution_boundary.v1"
SCHEMA_VERSION = 1
EXECUTION_BOUNDARY_MODE = "append_only_execution_boundary_receipt_without_process_start_or_job_execution"
OPERATOR_DECISION = "record_candidate_b_async_background_job_execution_boundary"
EXECUTION_BOUNDARY_STATE = "boundary_recorded"
EXECUTION_BOUNDARY_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-execution-boundary"
EXECUTION_BOUNDARY_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary"
)
HISTORY_ENDPOINT = workflow_worker_attempt.HISTORY_ENDPOINT
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
    "subprocess",
    "process",
    "background_process",
    "background_worker",
    "job_execution",
    "cancel",
    "retry",
    "resume",
    "raw_exception_trace",
    "raw_log_excerpt",
    "stdout",
    "stderr",
    "stacktrace",
}


class CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-execution-boundary-error",
            "server_time": workflow_status._server_time(),
            "mode": EXECUTION_BOUNDARY_MODE,
            "status": "blocked",
            "execution_boundary_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_execution_boundary(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "execution_boundary_mode") != EXECUTION_BOUNDARY_MODE:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_mode_not_admitted",
            "Only append-only Candidate B workflow execution-boundary receipt mode is admitted.",
            details={"expected_execution_boundary_mode": EXECUTION_BOUNDARY_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_decision_not_admitted",
            "The operator decision does not match the admitted execution-boundary action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    lineage = _selected_execution_lineage(row)
    execution_boundary = _execution_boundary(row, history, lineage)
    execution_boundary_hash = workflow_status._stable_hash(execution_boundary)
    execution_boundary_authority = {
        **execution_boundary,
        "operator_decision": OPERATOR_DECISION,
        "execution_boundary_hash": execution_boundary_hash,
    }
    execution_boundary_authority_hash = workflow_status._stable_hash(execution_boundary_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "execution_boundary_authority_hash": execution_boundary_authority_hash,
        }
    )
    execution_boundary_receipt_id = f"{EXECUTION_BOUNDARY_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_execution_boundary_receipt(
        execution_boundary_receipt_id=execution_boundary_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        lineage=lineage,
        execution_boundary=execution_boundary,
        execution_boundary_hash=execution_boundary_hash,
        execution_boundary_authority=execution_boundary_authority,
        execution_boundary_authority_hash=execution_boundary_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_execution_boundary_receipt(
        receipt,
        request_id=request_id,
        execution_boundary_receipt_id=execution_boundary_receipt_id,
        execution_boundary_hash=execution_boundary_hash,
        execution_boundary_authority_hash=execution_boundary_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "execution_boundary_receipt_hash": receipt_hash,
        "execution_boundary_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-execution-boundary://"
            f"{execution_boundary_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "execution_boundary_endpoint": EXECUTION_BOUNDARY_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_forbidden_request_fields",
            "Workflow execution-boundary receipts do not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, job execution, cancel, retry, or resume.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{exc.code}",
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
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_execution_lineage(row: Mapping[str, Any]) -> dict[str, Any]:
    scheduler_lease_receipt = _single_receipt(
        scheduler_lease.SCHEDULER_LEASE_RECEIPT_PREFIX,
        lambda receipt: receipt.get("operator_workflow_receipt_id") == row["operator_workflow_receipt_id"],
        missing_code="scheduler_lease_missing",
        ambiguous_code="scheduler_lease_ambiguous",
    )
    _validate_scheduler_lease_receipt(scheduler_lease_receipt, row)
    worker_attempt_receipt = _single_receipt(
        workflow_worker_attempt.WORKER_ATTEMPT_RECEIPT_PREFIX,
        lambda receipt: (
            receipt.get("scheduler_lease_receipt_id") == scheduler_lease_receipt["scheduler_lease_receipt_id"]
            and receipt.get("scheduler_lease_authority_hash")
            == scheduler_lease_receipt["scheduler_lease_authority_hash"]
        ),
        missing_code="worker_attempt_missing",
        ambiguous_code="worker_attempt_ambiguous",
    )
    _validate_worker_attempt_receipt(worker_attempt_receipt, scheduler_lease_receipt, row)
    latest_progress_checkpoint = _latest_progress_checkpoint_receipt(worker_attempt_receipt, row)
    terminal_receipt = _single_receipt(
        workflow_completion_failure.COMPLETION_FAILURE_RECEIPT_PREFIX,
        lambda receipt: (
            receipt.get("worker_attempt_receipt_id") == worker_attempt_receipt["worker_attempt_receipt_id"]
            and receipt.get("worker_attempt_authority_hash") == worker_attempt_receipt["worker_attempt_authority_hash"]
        ),
        missing_code="terminal_receipt_missing",
        ambiguous_code="terminal_receipt_conflict",
    )
    _validate_terminal_receipt(terminal_receipt, latest_progress_checkpoint, row)
    retry_terminal_projection = _retry_terminal_projection(row)
    return {
        "scheduler_lease_receipt": scheduler_lease_receipt,
        "worker_attempt_receipt": worker_attempt_receipt,
        "latest_progress_checkpoint_receipt": latest_progress_checkpoint,
        "terminal_receipt": terminal_receipt,
        "retry_terminal_projection": retry_terminal_projection,
    }


def _single_receipt(
    prefix: str,
    predicate: Callable[[Mapping[str, Any]], bool],
    *,
    missing_code: str,
    ambiguous_code: str,
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for receipt_file in sorted(_workflow_receipt_root().glob(f"{prefix}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=prefix)
        receipt = _read_json_receipt(receipt_file)
        if predicate(receipt):
            matches.append(receipt)
    if not matches:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{missing_code}",
            "The selected Candidate B execution-boundary lineage is missing a required server-owned receipt.",
            http_status=404,
        )
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{ambiguous_code}",
            "The selected Candidate B execution-boundary lineage is ambiguous or conflicting.",
            http_status=409,
            details={"match_count": len(matches)},
        )
    return matches[0]


def _latest_progress_checkpoint_receipt(
    worker_attempt_receipt: Mapping[str, Any],
    row: Mapping[str, Any],
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for receipt_file in sorted(
        _workflow_receipt_root().glob(f"{workflow_progress_checkpoint.PROGRESS_CHECKPOINT_RECEIPT_PREFIX}-*/receipt.json")
    ):
        receipt = _read_json_receipt(receipt_file)
        if (
            receipt.get("worker_attempt_receipt_id") == worker_attempt_receipt["worker_attempt_receipt_id"]
            and receipt.get("worker_attempt_authority_hash") == worker_attempt_receipt["worker_attempt_authority_hash"]
        ):
            matches.append(receipt)
    if not matches:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_progress_checkpoint_missing",
            "The selected Candidate B execution-boundary lineage is missing a progress-checkpoint receipt.",
            http_status=404,
        )
    latest = max(matches, key=lambda receipt: int(receipt.get("progress_checkpoint_sequence") or 0))
    same_sequence = [
        receipt
        for receipt in matches
        if receipt.get("progress_checkpoint_sequence") == latest.get("progress_checkpoint_sequence")
        and receipt.get("progress_checkpoint_receipt_id") != latest.get("progress_checkpoint_receipt_id")
    ]
    if same_sequence:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_progress_checkpoint_ambiguous",
            "The selected Candidate B execution-boundary lineage has ambiguous latest progress checkpoints.",
            http_status=409,
        )
    _validate_progress_checkpoint_receipt(latest, worker_attempt_receipt, row)
    return latest


def _retry_terminal_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        projection = workflow_status._retry_terminal_status_projection(
            str(row["operator_workflow_receipt_id"]),
            str(row["operator_workflow_receipt_hash"]),
        )
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if projection.get("retry_completion_failure_receipt_available") is not True:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_retry_terminal_not_recorded",
            "The selected Candidate B execution boundary requires visible retry terminal authority before process runtime can be selected.",
            http_status=409,
        )
    return projection


def _execution_boundary(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    lineage: Mapping[str, Any],
) -> dict[str, Any]:
    scheduler_receipt = lineage["scheduler_lease_receipt"]
    worker_receipt = lineage["worker_attempt_receipt"]
    progress_receipt = lineage["latest_progress_checkpoint_receipt"]
    terminal_receipt = lineage["terminal_receipt"]
    retry_terminal = lineage["retry_terminal_projection"]
    return {
        "execution_boundary_mode": EXECUTION_BOUNDARY_MODE,
        "execution_boundary_state": EXECUTION_BOUNDARY_STATE,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "scheduler_lease_receipt_id": scheduler_receipt["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": scheduler_receipt["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": scheduler_receipt["scheduler_lease_authority_hash"],
        "worker_attempt_receipt_id": worker_receipt["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": worker_receipt["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": worker_receipt["worker_attempt_authority_hash"],
        "latest_progress_checkpoint_receipt_id": progress_receipt["progress_checkpoint_receipt_id"],
        "latest_progress_checkpoint_receipt_hash": progress_receipt["progress_checkpoint_receipt_hash"],
        "latest_progress_checkpoint_authority_hash": progress_receipt["progress_checkpoint_authority_hash"],
        "progress_checkpoint_sequence": progress_receipt["progress_checkpoint_sequence"],
        "completion_failure_receipt_id": terminal_receipt["completion_failure_receipt_id"],
        "completion_failure_receipt_hash": terminal_receipt["completion_failure_receipt_hash"],
        "completion_failure_authority_hash": terminal_receipt["completion_failure_authority_hash"],
        "terminal_outcome": terminal_receipt["terminal_outcome"],
        "terminal_outcome_hash": terminal_receipt["terminal_outcome_hash"],
        "retry_terminal_projection_state": retry_terminal["retry_terminal_projection_state"],
        "retry_completion_failure_receipt_id": retry_terminal["retry_completion_failure_receipt_id"],
        "retry_completion_failure_receipt_hash": retry_terminal["retry_completion_failure_receipt_hash"],
        "retry_completion_failure_authority_hash": retry_terminal["retry_completion_failure_authority_hash"],
        "retry_worker_attempt_receipt_id": retry_terminal["retry_worker_attempt_receipt_id"],
        "latest_retry_progress_checkpoint_receipt_id": retry_terminal["latest_retry_progress_checkpoint_receipt_id"],
        "terminal_projection_visibility": True,
        "background_process_started": False,
        "job_execution_started": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
    }


def _load_or_write_execution_boundary_receipt(
    *,
    execution_boundary_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    lineage: Mapping[str, Any],
    execution_boundary: Mapping[str, Any],
    execution_boundary_hash: str,
    execution_boundary_authority: Mapping[str, Any],
    execution_boundary_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    target = _workflow_receipt_root() / execution_boundary_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_execution_boundary_receipt(
            existing,
            request_id=request_id,
            execution_boundary_receipt_id=execution_boundary_receipt_id,
            execution_boundary_hash=execution_boundary_hash,
            execution_boundary_authority_hash=execution_boundary_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    _reject_competing_execution_boundary(
        execution_boundary_receipt_id=execution_boundary_receipt_id,
        operator_workflow_receipt_id=str(row["operator_workflow_receipt_id"]),
        retry_completion_failure_authority_hash=str(
            lineage["retry_terminal_projection"]["retry_completion_failure_authority_hash"]
        ),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": EXECUTION_BOUNDARY_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "execution_boundary_state": EXECUTION_BOUNDARY_STATE,
        "execution_boundary_receipt_id": execution_boundary_receipt_id,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "execution_boundary": dict(execution_boundary),
        "execution_boundary_hash": execution_boundary_hash,
        "execution_boundary_authority": dict(execution_boundary_authority),
        "execution_boundary_authority_hash": execution_boundary_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_execution_boundary_receipt": True,
        "source_run_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "completion_failure_receipt_mutated": False,
        "retry_policy_receipt_mutated": False,
        "retry_queue_state_receipt_mutated": False,
        "retry_scheduler_lease_receipt_mutated": False,
        "retry_worker_attempt_receipt_mutated": False,
        "retry_progress_checkpoint_receipt_mutated": False,
        "retry_completion_failure_receipt_mutated": False,
        "execution_boundary_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
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
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "next_allowed_actions": [
            "refresh workflow-run history",
            "inspect execution-boundary projection through workflow status",
            "select real background process execution only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "execution_boundary_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_execution_boundary(
    *,
    execution_boundary_receipt_id: str,
    operator_workflow_receipt_id: str,
    retry_completion_failure_authority_hash: str,
) -> None:
    for receipt_file in sorted(_workflow_receipt_root().glob(f"{EXECUTION_BOUNDARY_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == execution_boundary_receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        boundary = existing.get("execution_boundary")
        if (
            isinstance(boundary, Mapping)
            and boundary.get("operator_workflow_receipt_id") == operator_workflow_receipt_id
            and boundary.get("retry_completion_failure_authority_hash") == retry_completion_failure_authority_hash
        ):
            raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
                "candidate_b_full_corpus_operator_workflow_execution_boundary_conflict",
                "The selected Candidate B retry terminal authority already has an execution-boundary receipt.",
                http_status=409,
                details={"existing_execution_boundary_receipt_id": existing_id},
            )


def _validate_scheduler_lease_receipt(receipt: Mapping[str, Any], row: Mapping[str, Any]) -> None:
    _validate_expected_receipt(
        receipt,
        hash_field="scheduler_lease_receipt_hash",
        expected={
            "schema_id": scheduler_lease.SCHEMA_ID,
            "schema_version": scheduler_lease.SCHEMA_VERSION,
            "mode": scheduler_lease.SCHEDULER_LEASE_MODE,
            "operator_decision": scheduler_lease.OPERATOR_DECISION,
            "status": "available",
            "scheduler_lease_state": scheduler_lease.SCHEDULER_LEASE_STATE,
            "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
            "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
            "authority_basis_hash": row["authority_basis_hash"],
            "row_hash": row["row_hash"],
            "append_only_scheduler_lease_receipt": True,
            "background_worker_runtime_selected_now": False,
            "job_execution_runtime_selected_now": False,
        },
        code="stale_scheduler_lease",
    )


def _validate_worker_attempt_receipt(
    receipt: Mapping[str, Any],
    scheduler_receipt: Mapping[str, Any],
    row: Mapping[str, Any],
) -> None:
    _validate_expected_receipt(
        receipt,
        hash_field="worker_attempt_receipt_hash",
        expected={
            "schema_id": workflow_worker_attempt.SCHEMA_ID,
            "schema_version": workflow_worker_attempt.SCHEMA_VERSION,
            "mode": workflow_worker_attempt.WORKER_ATTEMPT_MODE,
            "operator_decision": workflow_worker_attempt.OPERATOR_DECISION,
            "status": "available",
            "worker_attempt_state": workflow_worker_attempt.WORKER_ATTEMPT_STATE,
            "worker_attempt_number": workflow_worker_attempt.WORKER_ATTEMPT_NUMBER,
            "scheduler_lease_receipt_id": scheduler_receipt["scheduler_lease_receipt_id"],
            "scheduler_lease_authority_hash": scheduler_receipt["scheduler_lease_authority_hash"],
            "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
            "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
            "authority_basis_hash": row["authority_basis_hash"],
            "row_hash": row["row_hash"],
            "append_only_worker_attempt_receipt": True,
            "background_process_runtime_selected_now": False,
            "job_execution_runtime_selected_now": False,
        },
        code="stale_worker_attempt",
    )


def _validate_progress_checkpoint_receipt(
    receipt: Mapping[str, Any],
    worker_receipt: Mapping[str, Any],
    row: Mapping[str, Any],
) -> None:
    _validate_expected_receipt(
        receipt,
        hash_field="progress_checkpoint_receipt_hash",
        expected={
            "schema_id": workflow_progress_checkpoint.SCHEMA_ID,
            "schema_version": workflow_progress_checkpoint.SCHEMA_VERSION,
            "mode": workflow_progress_checkpoint.PROGRESS_CHECKPOINT_MODE,
            "operator_decision": workflow_progress_checkpoint.OPERATOR_DECISION,
            "status": "available",
            "progress_checkpoint_state": workflow_progress_checkpoint.PROGRESS_CHECKPOINT_STATE,
            "worker_attempt_receipt_id": worker_receipt["worker_attempt_receipt_id"],
            "worker_attempt_authority_hash": worker_receipt["worker_attempt_authority_hash"],
            "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
            "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
            "authority_basis_hash": row["authority_basis_hash"],
            "row_hash": row["row_hash"],
            "append_only_progress_checkpoint_receipt": True,
            "background_process_runtime_selected_now": False,
            "job_execution_runtime_selected_now": False,
        },
        code="stale_progress_checkpoint",
    )


def _validate_terminal_receipt(
    receipt: Mapping[str, Any],
    progress_receipt: Mapping[str, Any],
    row: Mapping[str, Any],
) -> None:
    _validate_expected_receipt(
        receipt,
        hash_field="completion_failure_receipt_hash",
        expected={
            "schema_id": workflow_completion_failure.SCHEMA_ID,
            "schema_version": workflow_completion_failure.SCHEMA_VERSION,
            "mode": workflow_completion_failure.COMPLETION_FAILURE_MODE,
            "operator_decision": workflow_completion_failure.OPERATOR_DECISION,
            "status": "available",
            "completion_failure_state": workflow_completion_failure.COMPLETION_FAILURE_STATE,
            "worker_attempt_receipt_id": progress_receipt["worker_attempt_receipt_id"],
            "worker_attempt_authority_hash": progress_receipt["worker_attempt_authority_hash"],
            "latest_progress_checkpoint_receipt_id": progress_receipt["progress_checkpoint_receipt_id"],
            "latest_progress_checkpoint_authority_hash": progress_receipt["progress_checkpoint_authority_hash"],
            "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
            "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
            "authority_basis_hash": row["authority_basis_hash"],
            "row_hash": row["row_hash"],
            "append_only_completion_failure_receipt": True,
            "job_execution_runtime_selected_now": False,
        },
        code="stale_terminal_receipt",
    )


def _validate_expected_receipt(
    receipt: Mapping[str, Any],
    *,
    hash_field: str,
    expected: Mapping[str, Any],
    code: str,
) -> None:
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {hash_field, "server_time"}}
    )
    if receipt.get(hash_field) != receipt_hash:
        mismatches.append({"field": hash_field, "expected": receipt_hash, "received": receipt.get(hash_field)})
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            f"candidate_b_full_corpus_operator_workflow_execution_boundary_{code}",
            "The selected Candidate B execution-boundary lineage receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _validate_execution_boundary_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    execution_boundary_receipt_id: str,
    execution_boundary_hash: str,
    execution_boundary_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": EXECUTION_BOUNDARY_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "execution_boundary_state": EXECUTION_BOUNDARY_STATE,
        "execution_boundary_receipt_id": execution_boundary_receipt_id,
        "execution_boundary_hash": execution_boundary_hash,
        "execution_boundary_authority_hash": execution_boundary_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_execution_boundary_receipt": True,
        "source_run_receipt_mutated": False,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    _validate_expected_receipt(
        receipt,
        hash_field="execution_boundary_receipt_hash",
        expected=expected,
        code="stale_execution_boundary_receipt",
    )
    return str(receipt["execution_boundary_receipt_hash"])


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_dir_invalid",
            "The configured Candidate B workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_dir_missing",
            "The configured Candidate B workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_receipt_unreadable",
            "A Candidate B workflow execution-boundary lineage receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_receipt_invalid",
            "Candidate B workflow execution-boundary lineage receipts must be JSON objects.",
            http_status=409,
        )
    return payload


def _validate_storage_id(value: str, *, prefix: str) -> None:
    if not value.startswith(f"{prefix}-") or "/" in value or "\\" in value or ".." in value:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_storage_id_invalid",
            "Candidate B execution-boundary receipt identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowExecutionBoundaryError(
            "candidate_b_full_corpus_operator_workflow_execution_boundary_required_field_missing",
            "A required Candidate B workflow execution-boundary field is missing or empty.",
            details={"field": key},
        )
    return value
