from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_retry_policy as workflow_retry_policy,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_retry_queue_state.v1"
SCHEMA_VERSION = 1
RETRY_QUEUE_STATE_MODE = (
    "append_only_retry_queue_state_receipt_without_creating_scheduler_lease_worker_attempt_or_mutating_original_lineage"
)
OPERATOR_DECISION = "record_candidate_b_async_retry_queue_state"
RETRY_QUEUE_STATE = "retry_queue_state_authority_recorded"
RETRY_ATTEMPT_NUMBER = 2
RETRY_QUEUE_STATE_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-retry-queue-state"
RETRY_QUEUE_STATE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state"
)
RETRY_POLICY_ENDPOINT = workflow_retry_policy.RETRY_POLICY_ENDPOINT
HISTORY_ENDPOINT = workflow_retry_policy.HISTORY_ENDPOINT
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
    "background_process",
    "background_worker",
    "job_execution",
    "cancel",
    "retry_attempt",
    "scheduler_lease",
    "worker_attempt",
    "progress_checkpoint",
    "completion_failure",
    "resume",
    "raw_exception_trace",
    "raw_log_excerpt",
    "stdout",
    "stderr",
    "stacktrace",
}


class CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-retry-queue-state-error",
            "server_time": workflow_status._server_time(),
            "mode": RETRY_QUEUE_STATE_MODE,
            "status": "blocked",
            "retry_queue_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_retry_queue_state(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "retry_queue_state_mode") != RETRY_QUEUE_STATE_MODE:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_mode_not_admitted",
            "Only append-only Candidate B retry queue-state receipt mode is admitted.",
            details={"expected_retry_queue_state_mode": RETRY_QUEUE_STATE_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_decision_not_admitted",
            "The operator decision does not match the admitted retry queue-state receipt action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    retry_policy_receipt = _selected_retry_policy_receipt(row, history, fields)
    retry_queue_state = {
        "retry_queue_state_mode": RETRY_QUEUE_STATE_MODE,
        "retry_queue_state": RETRY_QUEUE_STATE,
        "retry_attempt_number": RETRY_ATTEMPT_NUMBER,
        "retry_policy_receipt_id": retry_policy_receipt["retry_policy_receipt_id"],
        "retry_policy_receipt_hash": retry_policy_receipt["retry_policy_receipt_hash"],
        "retry_policy_authority_hash": retry_policy_receipt["retry_policy_authority_hash"],
        "retry_policy_result": retry_policy_receipt["retry_policy_result"],
        "completion_failure_receipt_id": retry_policy_receipt["completion_failure_receipt_id"],
        "completion_failure_receipt_hash": retry_policy_receipt["completion_failure_receipt_hash"],
        "completion_failure_authority_hash": retry_policy_receipt["completion_failure_authority_hash"],
        "failed_worker_attempt_receipt_id": retry_policy_receipt["worker_attempt_receipt_id"],
        "failed_worker_attempt_authority_hash": retry_policy_receipt["worker_attempt_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "run_state_before_retry_queue_state": row["run_state"],
        "retry_scheduler_lease_created": False,
        "retry_worker_attempt_created": False,
        "retry_job_execution_started": False,
    }
    retry_queue_state_hash = workflow_status._stable_hash(retry_queue_state)
    retry_queue_state_authority = {
        **retry_queue_state,
        "operator_decision": OPERATOR_DECISION,
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "retry_queue_state_hash": retry_queue_state_hash,
    }
    retry_queue_state_authority_hash = workflow_status._stable_hash(retry_queue_state_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "retry_queue_state_authority_hash": retry_queue_state_authority_hash,
        }
    )
    retry_queue_state_receipt_id = f"{RETRY_QUEUE_STATE_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_retry_queue_state_receipt(
        retry_queue_state_receipt_id=retry_queue_state_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        retry_policy_receipt=retry_policy_receipt,
        retry_queue_state=retry_queue_state,
        retry_queue_state_hash=retry_queue_state_hash,
        retry_queue_state_authority=retry_queue_state_authority,
        retry_queue_state_authority_hash=retry_queue_state_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_retry_queue_state_receipt(
        receipt,
        request_id=request_id,
        retry_queue_state_receipt_id=retry_queue_state_receipt_id,
        retry_queue_state_hash=retry_queue_state_hash,
        retry_queue_state_authority_hash=retry_queue_state_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "retry_queue_state_receipt_hash": receipt_hash,
        "retry_queue_state_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-retry-queue-state://"
            f"{retry_queue_state_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "retry_policy_endpoint": RETRY_POLICY_ENDPOINT,
        "retry_queue_state_endpoint": RETRY_QUEUE_STATE_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_forbidden_request_fields",
            "Workflow retry queue-state receipts do not admit caller paths, URLs, raw traces/logs, selector mutation, connector/model controls, browser authority, process start, job execution, retry attempt, scheduler lease, worker attempt, cancel, or resume.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            f"candidate_b_full_corpus_operator_workflow_retry_queue_state_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            f"candidate_b_full_corpus_operator_workflow_retry_queue_state_{exc.code}",
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
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            f"candidate_b_full_corpus_operator_workflow_retry_queue_state_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_retry_policy_receipt(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    receipt_id = _required(fields, "retry_policy_receipt_id")
    _validate_storage_id(receipt_id, prefix=workflow_retry_policy.RETRY_POLICY_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_retry_policy_missing",
            "The selected Candidate B retry-policy receipt is not present in server-owned receipt authority.",
            http_status=404,
            details={"retry_policy_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    if fields.get("retry_policy_result") != "eligible" or receipt.get("retry_policy_result") != "eligible":
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_ineligible_retry_policy_rejected",
            "Retry queue-state authority requires an eligible Candidate B retry-policy receipt.",
            http_status=409,
            details={
                "requested_retry_policy_result": fields.get("retry_policy_result"),
                "receipt_retry_policy_result": receipt.get("retry_policy_result"),
            },
        )
    expected = {
        "schema_id": workflow_retry_policy.SCHEMA_ID,
        "schema_version": workflow_retry_policy.SCHEMA_VERSION,
        "mode": workflow_retry_policy.RETRY_POLICY_MODE,
        "operator_decision": workflow_retry_policy.OPERATOR_DECISION,
        "status": "available",
        "retry_policy_state": workflow_retry_policy.RETRY_POLICY_STATE,
        "retry_policy_receipt_id": receipt_id,
        "retry_policy_receipt_hash": _required_hash(fields, "retry_policy_receipt_hash"),
        "retry_policy_authority_hash": _required_hash(fields, "retry_policy_authority_hash"),
        "retry_policy_result": "eligible",
        "completion_failure_receipt_id": _required(fields, "completion_failure_receipt_id"),
        "completion_failure_receipt_hash": _required_hash(fields, "completion_failure_receipt_hash"),
        "completion_failure_authority_hash": _required_hash(fields, "completion_failure_authority_hash"),
        "terminal_outcome": "failed",
        "worker_attempt_receipt_id": _required(fields, "failed_worker_attempt_receipt_id"),
        "worker_attempt_authority_hash": _required_hash(fields, "failed_worker_attempt_authority_hash"),
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "append_only_retry_policy_receipt": True,
        "exclusive_retry_policy_per_failed_terminal_receipt": True,
        "retry_attempt_created": False,
        "completion_failure_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "retry_policy_runtime_selected": True,
        "retry_attempt_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    receipt_hash = workflow_status._stable_hash(
        {key: value for key, value in receipt.items() if key not in {"retry_policy_receipt_hash", "server_time"}}
    )
    if receipt.get("retry_policy_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "retry_policy_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("retry_policy_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            f"candidate_b_full_corpus_operator_workflow_retry_queue_state_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_stale_retry_policy",
            "The selected Candidate B retry-policy receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt


def _load_or_write_retry_queue_state_receipt(
    *,
    retry_queue_state_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    retry_policy_receipt: Mapping[str, Any],
    retry_queue_state: Mapping[str, Any],
    retry_queue_state_hash: str,
    retry_queue_state_authority: Mapping[str, Any],
    retry_queue_state_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / retry_queue_state_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_retry_queue_state_receipt(
            existing,
            request_id=request_id,
            retry_queue_state_receipt_id=retry_queue_state_receipt_id,
            retry_queue_state_hash=retry_queue_state_hash,
            retry_queue_state_authority_hash=retry_queue_state_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    _validate_no_existing_retry_queue_state_receipt(
        root=root,
        retry_queue_state_receipt_id=retry_queue_state_receipt_id,
        retry_policy_receipt_id=str(retry_policy_receipt["retry_policy_receipt_id"]),
        retry_policy_authority_hash=str(retry_policy_receipt["retry_policy_authority_hash"]),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": RETRY_QUEUE_STATE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "retry_queue_state": RETRY_QUEUE_STATE,
        "retry_queue_state_receipt_id": retry_queue_state_receipt_id,
        "retry_attempt_number": RETRY_ATTEMPT_NUMBER,
        "retry_policy_receipt_id": retry_policy_receipt["retry_policy_receipt_id"],
        "retry_policy_receipt_hash": retry_policy_receipt["retry_policy_receipt_hash"],
        "retry_policy_authority_hash": retry_policy_receipt["retry_policy_authority_hash"],
        "retry_policy_result": retry_policy_receipt["retry_policy_result"],
        "retry_policy_reason": retry_policy_receipt["retry_policy_reason"],
        "completion_failure_receipt_id": retry_policy_receipt["completion_failure_receipt_id"],
        "completion_failure_receipt_hash": retry_policy_receipt["completion_failure_receipt_hash"],
        "completion_failure_authority_hash": retry_policy_receipt["completion_failure_authority_hash"],
        "terminal_outcome": retry_policy_receipt["terminal_outcome"],
        "terminal_failure_code": retry_policy_receipt["terminal_failure_code"],
        "terminal_failure_phase": retry_policy_receipt["terminal_failure_phase"],
        "failed_worker_attempt_receipt_id": retry_policy_receipt["worker_attempt_receipt_id"],
        "failed_worker_attempt_receipt_hash": retry_policy_receipt["worker_attempt_receipt_hash"],
        "failed_worker_attempt_authority_hash": retry_policy_receipt["worker_attempt_authority_hash"],
        "latest_progress_checkpoint_receipt_id": retry_policy_receipt["latest_progress_checkpoint_receipt_id"],
        "latest_progress_checkpoint_receipt_hash": retry_policy_receipt["latest_progress_checkpoint_receipt_hash"],
        "latest_progress_checkpoint_authority_hash": retry_policy_receipt["latest_progress_checkpoint_authority_hash"],
        "progress_checkpoint_sequence": retry_policy_receipt["progress_checkpoint_sequence"],
        "original_scheduler_lease_receipt_id": retry_policy_receipt["scheduler_lease_receipt_id"],
        "original_scheduler_lease_receipt_hash": retry_policy_receipt["scheduler_lease_receipt_hash"],
        "original_scheduler_lease_authority_hash": retry_policy_receipt["scheduler_lease_authority_hash"],
        "original_queue_state_receipt_id": retry_policy_receipt["queue_state_receipt_id"],
        "original_queue_state_receipt_hash": retry_policy_receipt["queue_state_receipt_hash"],
        "original_queue_state_authority_hash": retry_policy_receipt["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "retry_queue_state_record": dict(retry_queue_state),
        "retry_queue_state_hash": retry_queue_state_hash,
        "retry_queue_state_authority": dict(retry_queue_state_authority),
        "retry_queue_state_authority_hash": retry_queue_state_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_retry_queue_state_receipt": True,
        "exclusive_retry_queue_state_per_eligible_retry_policy_receipt": True,
        "retry_policy_receipt_mutated": False,
        "completion_failure_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "run_state_before_retry_queue_state": row["run_state"],
        "run_state_after_retry_queue_state": row["run_state"],
        "selected_retry_queue_state_mode": RETRY_QUEUE_STATE_MODE,
        "selected_retry_queue_state_endpoint": RETRY_QUEUE_STATE_ENDPOINT,
        "selected_retry_queue_state_receipt_binding": (
            "retry_policy_receipt_id,retry_policy_receipt_hash,retry_policy_authority_hash,"
            "retry_policy_result,completion_failure_receipt_id,completion_failure_receipt_hash,"
            "completion_failure_authority_hash,failed_worker_attempt_receipt_id,"
            "failed_worker_attempt_authority_hash,operator_workflow_receipt_id,"
            "operator_workflow_receipt_hash,retry_queue_state_hash"
        ),
        "selected_retry_queue_state_idempotency_basis": "client_request_id_plus_retry_queue_state_authority_hash",
        "retry_policy_result_required": "eligible",
        "retry_queue_state_runtime_selected": True,
        "retry_scheduler_lease_creation_admitted_now": False,
        "retry_worker_attempt_creation_admitted_now": False,
        "retry_progress_checkpoint_creation_admitted_now": False,
        "retry_completion_failure_creation_admitted_now": False,
        "retry_attempt_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "expiry_enforcement_runtime_selected_now": False,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
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
            "inspect the original workflow run through the returned status request",
            "record retry scheduler lease only through a separately admitted retry scheduler-lease authority slice",
            "select cancel, resume, or job execution only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "retry_queue_state_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _validate_no_existing_retry_queue_state_receipt(
    *,
    root: Path,
    retry_queue_state_receipt_id: str,
    retry_policy_receipt_id: str,
    retry_policy_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{RETRY_QUEUE_STATE_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == retry_queue_state_receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if (
            existing.get("retry_policy_receipt_id") == retry_policy_receipt_id
            and existing.get("retry_policy_authority_hash") == retry_policy_authority_hash
        ):
            raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
                "candidate_b_full_corpus_operator_workflow_retry_queue_state_policy_conflict",
                "The selected Candidate B retry-policy receipt already has a retry queue-state receipt.",
                http_status=409,
                details={"existing_retry_queue_state_receipt_id": existing_id},
            )


def _validate_retry_queue_state_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    retry_queue_state_receipt_id: str,
    retry_queue_state_hash: str,
    retry_queue_state_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": RETRY_QUEUE_STATE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "retry_queue_state": RETRY_QUEUE_STATE,
        "retry_queue_state_receipt_id": retry_queue_state_receipt_id,
        "retry_attempt_number": RETRY_ATTEMPT_NUMBER,
        "retry_queue_state_hash": retry_queue_state_hash,
        "retry_queue_state_authority_hash": retry_queue_state_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_retry_queue_state_receipt": True,
        "exclusive_retry_queue_state_per_eligible_retry_policy_receipt": True,
        "retry_policy_receipt_mutated": False,
        "completion_failure_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "retry_policy_result_required": "eligible",
        "retry_queue_state_runtime_selected": True,
        "retry_scheduler_lease_creation_admitted_now": False,
        "retry_worker_attempt_creation_admitted_now": False,
        "retry_progress_checkpoint_creation_admitted_now": False,
        "retry_completion_failure_creation_admitted_now": False,
        "retry_attempt_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
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
        {key: value for key, value in receipt.items() if key not in {"retry_queue_state_receipt_hash", "server_time"}}
    )
    if receipt.get("retry_queue_state_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "retry_queue_state_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("retry_queue_state_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            f"candidate_b_full_corpus_operator_workflow_retry_queue_state_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_idempotency_conflict",
            "The existing Candidate B workflow-run retry queue-state receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_receipt_unreadable",
            "A Candidate B workflow-run retry queue-state receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_receipt_invalid",
            "Candidate B workflow-run retry queue-state receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_required_field_missing",
            "A required Candidate B workflow-run retry queue-state field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_hash_invalid",
            "Candidate B workflow-run retry queue-state hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        workflow_status._validate_storage_id(value, prefix=prefix)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowRetryQueueStateError(
            "candidate_b_full_corpus_operator_workflow_retry_queue_state_storage_id_invalid",
            "Candidate B workflow-run retry queue-state identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
