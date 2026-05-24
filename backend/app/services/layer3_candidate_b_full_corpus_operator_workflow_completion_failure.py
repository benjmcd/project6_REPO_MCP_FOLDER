from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_queue_state as workflow_queue_state,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease as scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
    layer3_candidate_b_full_corpus_operator_workflow_worker_attempt as workflow_worker_attempt,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_completion_failure.v1"
SCHEMA_VERSION = 1
COMPLETION_FAILURE_MODE = (
    "append_only_completion_failure_receipt_without_cancel_retry_resume_or_source_receipt_mutation"
)
OPERATOR_DECISION = "record_candidate_b_async_completion_failure"
COMPLETION_FAILURE_STATE = "completion_failure_recorded"
COMPLETION_FAILURE_RECEIPT_PREFIX = (
    f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-completion-failure"
)
COMPLETION_FAILURE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure"
)
PROGRESS_CHECKPOINT_ENDPOINT = workflow_progress_checkpoint.PROGRESS_CHECKPOINT_ENDPOINT
WORKER_ATTEMPT_ENDPOINT = workflow_worker_attempt.WORKER_ATTEMPT_ENDPOINT
SCHEDULER_LEASE_ENDPOINT = scheduler_lease.SCHEDULER_LEASE_ENDPOINT
QUEUE_STATE_ENDPOINT = workflow_queue_state.QUEUE_STATE_ENDPOINT
HISTORY_ENDPOINT = workflow_worker_attempt.HISTORY_ENDPOINT
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
TERMINAL_OUTCOMES = {"completed", "failed"}

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


class CandidateBFullCorpusOperatorWorkflowCompletionFailureError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-completion-failure-error",
            "server_time": workflow_status._server_time(),
            "mode": COMPLETION_FAILURE_MODE,
            "status": "blocked",
            "completion_failure_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_completion_failure(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "completion_failure_mode") != COMPLETION_FAILURE_MODE:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_mode_not_admitted",
            "Only append-only Candidate B workflow completion/failure receipt mode is admitted.",
            details={"expected_completion_failure_mode": COMPLETION_FAILURE_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_decision_not_admitted",
            "The operator decision does not match the admitted completion/failure receipt action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    terminal_outcome = _terminal_outcome(fields)
    terminal_failure_code = _terminal_failure_field(fields, "terminal_failure_code", terminal_outcome)
    terminal_failure_phase = _terminal_failure_field(fields, "terminal_failure_phase", terminal_outcome)

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    progress_checkpoint_receipt = _selected_progress_checkpoint_receipt(row, history, fields)
    completion_failure = {
        "completion_failure_mode": COMPLETION_FAILURE_MODE,
        "completion_failure_state": COMPLETION_FAILURE_STATE,
        "terminal_outcome": terminal_outcome,
        "terminal_failure_code": terminal_failure_code,
        "terminal_failure_phase": terminal_failure_phase,
        "worker_attempt_receipt_id": progress_checkpoint_receipt["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": progress_checkpoint_receipt["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": progress_checkpoint_receipt["worker_attempt_authority_hash"],
        "latest_progress_checkpoint_receipt_id": progress_checkpoint_receipt["progress_checkpoint_receipt_id"],
        "latest_progress_checkpoint_receipt_hash": progress_checkpoint_receipt["progress_checkpoint_receipt_hash"],
        "latest_progress_checkpoint_authority_hash": progress_checkpoint_receipt["progress_checkpoint_authority_hash"],
        "progress_checkpoint_sequence": progress_checkpoint_receipt["progress_checkpoint_sequence"],
        "scheduler_lease_receipt_id": progress_checkpoint_receipt["scheduler_lease_receipt_id"],
        "queue_state_receipt_id": progress_checkpoint_receipt["queue_state_receipt_id"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "run_state_before_completion_failure": row["run_state"],
        "worker_attempt_state_before_completion_failure": "attempt_authority_recorded",
        "job_execution_started": False,
        "terminal_failure_payload_operator_safe": True,
    }
    terminal_outcome_hash = workflow_status._stable_hash(completion_failure)
    completion_failure_authority = {
        **completion_failure,
        "operator_decision": OPERATOR_DECISION,
        "terminal_outcome_hash": terminal_outcome_hash,
    }
    completion_failure_authority_hash = workflow_status._stable_hash(completion_failure_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "completion_failure_authority_hash": completion_failure_authority_hash,
        }
    )
    completion_failure_receipt_id = (
        f"{COMPLETION_FAILURE_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    )
    receipt, idempotent_replay = _load_or_write_completion_failure_receipt(
        completion_failure_receipt_id=completion_failure_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        progress_checkpoint_receipt=progress_checkpoint_receipt,
        completion_failure=completion_failure,
        terminal_outcome_hash=terminal_outcome_hash,
        completion_failure_authority=completion_failure_authority,
        completion_failure_authority_hash=completion_failure_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_completion_failure_receipt(
        receipt,
        request_id=request_id,
        completion_failure_receipt_id=completion_failure_receipt_id,
        terminal_outcome_hash=terminal_outcome_hash,
        completion_failure_authority_hash=completion_failure_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "completion_failure_receipt_hash": receipt_hash,
        "completion_failure_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-completion-failure://"
            f"{completion_failure_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "queue_state_endpoint": QUEUE_STATE_ENDPOINT,
        "scheduler_lease_endpoint": SCHEDULER_LEASE_ENDPOINT,
        "worker_attempt_endpoint": WORKER_ATTEMPT_ENDPOINT,
        "progress_checkpoint_endpoint": PROGRESS_CHECKPOINT_ENDPOINT,
        "completion_failure_endpoint": COMPLETION_FAILURE_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_forbidden_request_fields",
            "Workflow completion/failure receipts do not admit caller paths, URLs, raw traces/logs, selector mutation, connector/model controls, browser authority, process start, job execution, cancel, retry, or resume.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            f"candidate_b_full_corpus_operator_workflow_completion_failure_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            f"candidate_b_full_corpus_operator_workflow_completion_failure_{exc.code}",
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
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            f"candidate_b_full_corpus_operator_workflow_completion_failure_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_progress_checkpoint_receipt(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    receipt_id = _required(fields, "latest_progress_checkpoint_receipt_id")
    _validate_storage_id(receipt_id, prefix=workflow_progress_checkpoint.PROGRESS_CHECKPOINT_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_progress_checkpoint_receipt_missing",
            "The selected Candidate B progress-checkpoint receipt is not present in server-owned receipt authority.",
            http_status=404,
            details={"latest_progress_checkpoint_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    expected = {
        "schema_id": workflow_progress_checkpoint.SCHEMA_ID,
        "schema_version": workflow_progress_checkpoint.SCHEMA_VERSION,
        "mode": workflow_progress_checkpoint.PROGRESS_CHECKPOINT_MODE,
        "operator_decision": workflow_progress_checkpoint.OPERATOR_DECISION,
        "status": "available",
        "progress_checkpoint_state": workflow_progress_checkpoint.PROGRESS_CHECKPOINT_STATE,
        "progress_checkpoint_receipt_id": receipt_id,
        "progress_checkpoint_receipt_hash": _required_hash(fields, "latest_progress_checkpoint_receipt_hash"),
        "progress_checkpoint_authority_hash": _required_hash(fields, "latest_progress_checkpoint_authority_hash"),
        "progress_checkpoint_sequence": _required_positive_int(fields, "progress_checkpoint_sequence"),
        "worker_attempt_receipt_id": _required(fields, "worker_attempt_receipt_id"),
        "worker_attempt_receipt_hash": _required_hash(fields, "worker_attempt_receipt_hash"),
        "worker_attempt_authority_hash": _required_hash(fields, "worker_attempt_authority_hash"),
        "scheduler_lease_receipt_id": _required(fields, "scheduler_lease_receipt_id"),
        "scheduler_lease_receipt_hash": _required_hash(fields, "scheduler_lease_receipt_hash"),
        "scheduler_lease_authority_hash": _required_hash(fields, "scheduler_lease_authority_hash"),
        "queue_state_receipt_id": _required(fields, "queue_state_receipt_id"),
        "queue_state_receipt_hash": _required_hash(fields, "queue_state_receipt_hash"),
        "queue_state_authority_hash": _required_hash(fields, "queue_state_authority_hash"),
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "append_only_progress_checkpoint_receipt": True,
        "monotonic_progress_checkpoint_sequence": True,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "progress_checkpoint_runtime_selected": True,
        "completion_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {"progress_checkpoint_receipt_hash", "server_time"}}
    )
    if receipt.get("progress_checkpoint_receipt_hash") != receipt_hash:
        mismatches.append(
            {"field": "progress_checkpoint_receipt_hash", "expected": receipt_hash, "received": receipt.get("progress_checkpoint_receipt_hash")}
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            f"candidate_b_full_corpus_operator_workflow_completion_failure_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_stale_progress_checkpoint_receipt",
            "The selected Candidate B progress-checkpoint receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    _validate_latest_progress_checkpoint(receipt)
    return receipt


def _load_or_write_completion_failure_receipt(
    *,
    completion_failure_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    progress_checkpoint_receipt: Mapping[str, Any],
    completion_failure: Mapping[str, Any],
    terminal_outcome_hash: str,
    completion_failure_authority: Mapping[str, Any],
    completion_failure_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / completion_failure_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_completion_failure_receipt(
            existing,
            request_id=request_id,
            completion_failure_receipt_id=completion_failure_receipt_id,
            terminal_outcome_hash=terminal_outcome_hash,
            completion_failure_authority_hash=completion_failure_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    _validate_no_existing_terminal_receipt(
        root=root,
        completion_failure_receipt_id=completion_failure_receipt_id,
        worker_attempt_receipt_id=str(progress_checkpoint_receipt["worker_attempt_receipt_id"]),
        worker_attempt_authority_hash=str(progress_checkpoint_receipt["worker_attempt_authority_hash"]),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": COMPLETION_FAILURE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "completion_failure_state": COMPLETION_FAILURE_STATE,
        "completion_failure_receipt_id": completion_failure_receipt_id,
        "terminal_outcome": completion_failure["terminal_outcome"],
        "terminal_failure_code": completion_failure["terminal_failure_code"],
        "terminal_failure_phase": completion_failure["terminal_failure_phase"],
        "terminal_outcome_hash": terminal_outcome_hash,
        "worker_attempt_receipt_id": progress_checkpoint_receipt["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": progress_checkpoint_receipt["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": progress_checkpoint_receipt["worker_attempt_authority_hash"],
        "latest_progress_checkpoint_receipt_id": progress_checkpoint_receipt["progress_checkpoint_receipt_id"],
        "latest_progress_checkpoint_receipt_hash": progress_checkpoint_receipt["progress_checkpoint_receipt_hash"],
        "latest_progress_checkpoint_authority_hash": progress_checkpoint_receipt["progress_checkpoint_authority_hash"],
        "progress_checkpoint_sequence": progress_checkpoint_receipt["progress_checkpoint_sequence"],
        "scheduler_lease_receipt_id": progress_checkpoint_receipt["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": progress_checkpoint_receipt["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": progress_checkpoint_receipt["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": progress_checkpoint_receipt["queue_state_receipt_id"],
        "queue_state_receipt_hash": progress_checkpoint_receipt["queue_state_receipt_hash"],
        "queue_state_authority_hash": progress_checkpoint_receipt["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "completion_failure": dict(completion_failure),
        "completion_failure_authority": dict(completion_failure_authority),
        "completion_failure_authority_hash": completion_failure_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_completion_failure_receipt": True,
        "exclusive_terminal_receipt_per_worker_attempt": True,
        "progress_checkpoint_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "run_state_before_completion_failure": row["run_state"],
        "run_state_after_completion_failure": row["run_state"],
        "selected_completion_failure_mode": COMPLETION_FAILURE_MODE,
        "selected_completion_failure_endpoint": COMPLETION_FAILURE_ENDPOINT,
        "selected_completion_failure_receipt_binding": (
            "worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,"
            "latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,"
            "latest_progress_checkpoint_authority_hash,progress_checkpoint_sequence,scheduler_lease_receipt_id,"
            "queue_state_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,"
            "terminal_outcome,terminal_outcome_hash"
        ),
        "selected_completion_failure_idempotency_basis": "client_request_id_plus_completion_failure_authority_hash",
        "completion_failure_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "expiry_enforcement_runtime_selected_now": False,
        "default_scope_expansion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "terminal_failure_payload_operator_safe": True,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "next_allowed_actions": [
            "refresh workflow-run history",
            "inspect the original workflow run through the returned status request",
            "select cancel, retry, or resume only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {**receipt_input, "completion_failure_receipt_hash": receipt_hash, "server_time": workflow_status._server_time()}
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _validate_latest_progress_checkpoint(receipt: Mapping[str, Any]) -> None:
    root = _workflow_receipt_root()
    selected_sequence = receipt.get("progress_checkpoint_sequence")
    selected_id = receipt.get("progress_checkpoint_receipt_id")
    worker_attempt_receipt_id = receipt.get("worker_attempt_receipt_id")
    worker_attempt_authority_hash = receipt.get("worker_attempt_authority_hash")
    for receipt_file in sorted(root.glob(f"{workflow_progress_checkpoint.PROGRESS_CHECKPOINT_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        existing = _read_json_receipt(receipt_file)
        if (
            existing.get("worker_attempt_receipt_id") == worker_attempt_receipt_id
            and existing.get("worker_attempt_authority_hash") == worker_attempt_authority_hash
        ):
            sequence = existing.get("progress_checkpoint_sequence")
            if isinstance(sequence, int) and isinstance(selected_sequence, int) and sequence > selected_sequence:
                raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
                    "candidate_b_full_corpus_operator_workflow_completion_failure_progress_checkpoint_not_latest",
                    "Completion/failure receipts require the latest Candidate B progress-checkpoint receipt for the selected worker attempt.",
                    http_status=409,
                    details={
                        "latest_progress_checkpoint_receipt_id": existing_id,
                        "latest_progress_checkpoint_sequence": sequence,
                        "selected_progress_checkpoint_receipt_id": selected_id,
                        "selected_progress_checkpoint_sequence": selected_sequence,
                    },
                )
            if sequence == selected_sequence and existing_id != selected_id:
                raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
                    "candidate_b_full_corpus_operator_workflow_completion_failure_progress_checkpoint_ambiguous",
                    "The selected Candidate B progress-checkpoint sequence is ambiguous for this worker attempt.",
                    http_status=409,
                    details={
                        "existing_progress_checkpoint_receipt_id": existing_id,
                        "selected_progress_checkpoint_receipt_id": selected_id,
                    },
                )


def _validate_no_existing_terminal_receipt(
    *,
    root: Path,
    completion_failure_receipt_id: str,
    worker_attempt_receipt_id: str,
    worker_attempt_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{COMPLETION_FAILURE_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == completion_failure_receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if (
            existing.get("worker_attempt_receipt_id") == worker_attempt_receipt_id
            and existing.get("worker_attempt_authority_hash") == worker_attempt_authority_hash
        ):
            raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
                "candidate_b_full_corpus_operator_workflow_completion_failure_terminal_conflict",
                "The selected Candidate B worker attempt already has a terminal completion/failure receipt.",
                http_status=409,
                details={"existing_completion_failure_receipt_id": existing_id},
            )


def _validate_completion_failure_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    completion_failure_receipt_id: str,
    terminal_outcome_hash: str,
    completion_failure_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": COMPLETION_FAILURE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "completion_failure_state": COMPLETION_FAILURE_STATE,
        "completion_failure_receipt_id": completion_failure_receipt_id,
        "terminal_outcome_hash": terminal_outcome_hash,
        "completion_failure_authority_hash": completion_failure_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_completion_failure_receipt": True,
        "exclusive_terminal_receipt_per_worker_attempt": True,
        "progress_checkpoint_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "completion_failure_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "expiry_enforcement_runtime_selected_now": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "terminal_failure_payload_operator_safe": True,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {"completion_failure_receipt_hash", "server_time"}}
    )
    if receipt.get("completion_failure_receipt_hash") != receipt_hash:
        mismatches.append(
            {"field": "completion_failure_receipt_hash", "expected": receipt_hash, "received": receipt.get("completion_failure_receipt_hash")}
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            f"candidate_b_full_corpus_operator_workflow_completion_failure_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_idempotency_conflict",
            "The existing Candidate B workflow-run completion/failure receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_receipt_unreadable",
            "A Candidate B workflow-run completion/failure receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_receipt_invalid",
            "Candidate B workflow-run completion/failure receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_required_field_missing",
            "A required Candidate B workflow-run completion/failure field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_hash_invalid",
            "Candidate B workflow-run completion/failure hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _required_positive_int(fields: Mapping[str, Any], key: str) -> int:
    value = fields.get(key)
    if not isinstance(value, int) or value < 1:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_integer_invalid",
            "Candidate B workflow-run completion/failure integer fields must be positive integers.",
            details={"field": key, "received": value},
        )
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        workflow_status._validate_storage_id(value, prefix=prefix)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_storage_id_invalid",
            "Candidate B workflow-run completion/failure identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _terminal_outcome(fields: Mapping[str, Any]) -> str:
    value = _required(fields, "terminal_outcome")
    if value not in TERMINAL_OUTCOMES:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_terminal_outcome_invalid",
            "Candidate B workflow-run completion/failure terminal outcome must be completed or failed.",
            details={"terminal_outcome": value},
        )
    return value


def _terminal_failure_field(fields: Mapping[str, Any], key: str, terminal_outcome: str) -> str | None:
    value = fields.get(key)
    if terminal_outcome == "completed":
        if value not in (None, ""):
            raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
                "candidate_b_full_corpus_operator_workflow_completion_failure_completed_failure_field",
                "Completed Candidate B workflow-run receipts must not include failure fields.",
                details={"field": key},
            )
        return None
    text = str(value or "").strip()
    if not text:
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_failure_field_missing",
            "Failed Candidate B workflow-run receipts require operator-safe failure code and phase fields.",
            details={"field": key},
        )
    if len(text) > 80 or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in text):
        raise CandidateBFullCorpusOperatorWorkflowCompletionFailureError(
            "candidate_b_full_corpus_operator_workflow_completion_failure_failure_field_invalid",
            "Candidate B workflow-run failure fields must be short lowercase operator-safe tokens.",
            details={"field": key},
        )
    return text
