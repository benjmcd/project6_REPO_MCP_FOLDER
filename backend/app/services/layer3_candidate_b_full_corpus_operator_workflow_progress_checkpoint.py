from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_queue_state as workflow_queue_state,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease as scheduler_lease,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
    layer3_candidate_b_full_corpus_operator_workflow_worker_attempt as workflow_worker_attempt,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_progress_checkpoint.v1"
SCHEMA_VERSION = 1
PROGRESS_CHECKPOINT_MODE = (
    "append_only_progress_checkpoint_receipt_without_completion_or_cancel_retry_resume"
)
OPERATOR_DECISION = "record_candidate_b_async_progress_checkpoint"
PROGRESS_CHECKPOINT_STATE = "progress_checkpoint_recorded"
PROGRESS_CHECKPOINT_RECEIPT_PREFIX = (
    f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-progress-checkpoint"
)
PROGRESS_CHECKPOINT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint"
)
WORKER_ATTEMPT_ENDPOINT = workflow_worker_attempt.WORKER_ATTEMPT_ENDPOINT
SCHEDULER_LEASE_ENDPOINT = scheduler_lease.SCHEDULER_LEASE_ENDPOINT
QUEUE_STATE_ENDPOINT = workflow_queue_state.QUEUE_STATE_ENDPOINT
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
    "background_process",
    "background_worker",
    "job_execution",
    "completion",
    "cancel",
    "retry",
    "resume",
}


class CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-progress-checkpoint-error",
            "server_time": workflow_status._server_time(),
            "mode": PROGRESS_CHECKPOINT_MODE,
            "status": "blocked",
            "progress_checkpoint_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_progress_checkpoint(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "progress_checkpoint_mode") != PROGRESS_CHECKPOINT_MODE:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_mode_not_admitted",
            "Only append-only Candidate B workflow progress-checkpoint receipt mode is admitted.",
            details={"expected_progress_checkpoint_mode": PROGRESS_CHECKPOINT_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_decision_not_admitted",
            "The operator decision does not match the admitted progress-checkpoint receipt action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    sequence = _required_positive_int(fields, "progress_checkpoint_sequence")

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    worker_attempt_receipt = _selected_worker_attempt_receipt(row, history, fields)
    progress_checkpoint = {
        "progress_checkpoint_mode": PROGRESS_CHECKPOINT_MODE,
        "progress_checkpoint_state": PROGRESS_CHECKPOINT_STATE,
        "progress_checkpoint_sequence": sequence,
        "worker_attempt_receipt_id": worker_attempt_receipt["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": worker_attempt_receipt["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": worker_attempt_receipt["worker_attempt_authority_hash"],
        "scheduler_lease_receipt_id": worker_attempt_receipt["scheduler_lease_receipt_id"],
        "queue_state_receipt_id": worker_attempt_receipt["queue_state_receipt_id"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "run_state_before_progress_checkpoint": row["run_state"],
        "worker_attempt_state_before_progress_checkpoint": worker_attempt_receipt["worker_attempt_state"],
        "job_execution_started": False,
        "completion_emitted": False,
    }
    progress_checkpoint_hash = workflow_status._stable_hash(progress_checkpoint)
    progress_checkpoint_authority = {
        **progress_checkpoint,
        "operator_decision": OPERATOR_DECISION,
        "progress_checkpoint_hash": progress_checkpoint_hash,
    }
    progress_checkpoint_authority_hash = workflow_status._stable_hash(progress_checkpoint_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "progress_checkpoint_authority_hash": progress_checkpoint_authority_hash,
        }
    )
    progress_checkpoint_receipt_id = (
        f"{PROGRESS_CHECKPOINT_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    )
    receipt, idempotent_replay = _load_or_write_progress_checkpoint_receipt(
        progress_checkpoint_receipt_id=progress_checkpoint_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        worker_attempt_receipt=worker_attempt_receipt,
        progress_checkpoint=progress_checkpoint,
        progress_checkpoint_hash=progress_checkpoint_hash,
        progress_checkpoint_authority=progress_checkpoint_authority,
        progress_checkpoint_authority_hash=progress_checkpoint_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_progress_checkpoint_receipt(
        receipt,
        request_id=request_id,
        progress_checkpoint_receipt_id=progress_checkpoint_receipt_id,
        progress_checkpoint_hash=progress_checkpoint_hash,
        progress_checkpoint_authority_hash=progress_checkpoint_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "progress_checkpoint_receipt_hash": receipt_hash,
        "progress_checkpoint_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-progress-checkpoint://"
            f"{progress_checkpoint_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "queue_state_endpoint": QUEUE_STATE_ENDPOINT,
        "scheduler_lease_endpoint": SCHEDULER_LEASE_ENDPOINT,
        "worker_attempt_endpoint": WORKER_ATTEMPT_ENDPOINT,
        "progress_checkpoint_endpoint": PROGRESS_CHECKPOINT_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_forbidden_request_fields",
            "Workflow progress checkpoints do not admit caller paths, URLs, selector mutation, connector/model controls, browser authority, process start, job execution, completion, cancel, retry, or resume.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            f"candidate_b_full_corpus_operator_workflow_progress_checkpoint_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "operator_workflow_receipt_id")
    _validate_storage_id(receipt_id, prefix=workflow_run.RUN_RECEIPT_PREFIX)
    rows = history.get("history_rows")
    if not isinstance(rows, list):
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_history_rows_invalid",
            "Candidate B workflow progress checkpoints require a valid server-owned history row set.",
            http_status=409,
        )
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("operator_workflow_receipt_id") == receipt_id]
    if not matches:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_run_receipt_missing",
            "The selected Candidate B workflow-run receipt is not present in current server-owned history.",
            http_status=404,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_run_receipt_ambiguous",
            "The selected Candidate B workflow-run receipt appears more than once in current server-owned history.",
            http_status=409,
            details={"operator_workflow_receipt_id": receipt_id, "match_count": len(matches)},
        )
    return dict(matches[0])


def _validate_selected_authority(
    history: Mapping[str, Any],
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> None:
    expected = {
        "history_hash": history.get("history_hash"),
        "operator_workflow_receipt_hash": row.get("operator_workflow_receipt_hash"),
        "row_hash": row.get("row_hash"),
        "authority_basis_hash": row.get("authority_basis_hash"),
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": fields.get(field)}
        for field, expected_value in expected.items()
        if fields.get(field) != expected_value
    ]
    if row.get("run_state") != "proven":
        mismatches.append({"field": "run_state", "expected": "proven", "received": row.get("run_state")})
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_stale_authority",
            "The selected Candidate B workflow-run progress-checkpoint authority is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _selected_worker_attempt_receipt(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    receipt_id = _required(fields, "worker_attempt_receipt_id")
    _validate_storage_id(receipt_id, prefix=workflow_worker_attempt.WORKER_ATTEMPT_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_worker_attempt_receipt_missing",
            "The selected Candidate B worker-attempt receipt is not present in server-owned receipt authority.",
            http_status=404,
            details={"worker_attempt_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    expected = {
        "schema_id": workflow_worker_attempt.SCHEMA_ID,
        "schema_version": workflow_worker_attempt.SCHEMA_VERSION,
        "mode": workflow_worker_attempt.WORKER_ATTEMPT_MODE,
        "operator_decision": workflow_worker_attempt.OPERATOR_DECISION,
        "status": "available",
        "worker_attempt_state": workflow_worker_attempt.WORKER_ATTEMPT_STATE,
        "worker_attempt_number": workflow_worker_attempt.WORKER_ATTEMPT_NUMBER,
        "worker_attempt_receipt_id": receipt_id,
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
        "append_only_worker_attempt_receipt": True,
        "exclusive_initial_attempt_per_scheduler_lease": True,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "worker_attempt_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "progress_checkpoint_runtime_selected_now": False,
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
        {key: value for key, value in receipt.items() if key not in {"worker_attempt_receipt_hash", "server_time"}}
    )
    if receipt.get("worker_attempt_receipt_hash") != receipt_hash:
        mismatches.append(
            {"field": "worker_attempt_receipt_hash", "expected": receipt_hash, "received": receipt.get("worker_attempt_receipt_hash")}
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            f"candidate_b_full_corpus_operator_workflow_progress_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_stale_worker_attempt_receipt",
            "The selected Candidate B worker-attempt receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt


def _load_or_write_progress_checkpoint_receipt(
    *,
    progress_checkpoint_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    worker_attempt_receipt: Mapping[str, Any],
    progress_checkpoint: Mapping[str, Any],
    progress_checkpoint_hash: str,
    progress_checkpoint_authority: Mapping[str, Any],
    progress_checkpoint_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / progress_checkpoint_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_progress_checkpoint_receipt(
            existing,
            request_id=request_id,
            progress_checkpoint_receipt_id=progress_checkpoint_receipt_id,
            progress_checkpoint_hash=progress_checkpoint_hash,
            progress_checkpoint_authority_hash=progress_checkpoint_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    sequence = int(progress_checkpoint["progress_checkpoint_sequence"])
    previous = _validate_next_progress_checkpoint_sequence(
        root=root,
        progress_checkpoint_receipt_id=progress_checkpoint_receipt_id,
        worker_attempt_receipt_id=str(worker_attempt_receipt["worker_attempt_receipt_id"]),
        worker_attempt_authority_hash=str(worker_attempt_receipt["worker_attempt_authority_hash"]),
        progress_checkpoint_sequence=sequence,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROGRESS_CHECKPOINT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "progress_checkpoint_state": PROGRESS_CHECKPOINT_STATE,
        "progress_checkpoint_sequence": sequence,
        "progress_checkpoint_receipt_id": progress_checkpoint_receipt_id,
        "worker_attempt_receipt_id": worker_attempt_receipt["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": worker_attempt_receipt["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": worker_attempt_receipt["worker_attempt_authority_hash"],
        "scheduler_lease_receipt_id": worker_attempt_receipt["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": worker_attempt_receipt["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": worker_attempt_receipt["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": worker_attempt_receipt["queue_state_receipt_id"],
        "queue_state_receipt_hash": worker_attempt_receipt["queue_state_receipt_hash"],
        "queue_state_authority_hash": worker_attempt_receipt["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "previous_progress_checkpoint_sequence": previous["previous_sequence"],
        "previous_progress_checkpoint_receipt_id": previous["previous_receipt_id"],
        "progress_checkpoint": dict(progress_checkpoint),
        "progress_checkpoint_hash": progress_checkpoint_hash,
        "progress_checkpoint_authority": dict(progress_checkpoint_authority),
        "progress_checkpoint_authority_hash": progress_checkpoint_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_progress_checkpoint_receipt": True,
        "monotonic_progress_checkpoint_sequence": True,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "run_state_before_progress_checkpoint": row["run_state"],
        "run_state_after_progress_checkpoint": row["run_state"],
        "worker_attempt_state_before_progress_checkpoint": worker_attempt_receipt["worker_attempt_state"],
        "selected_progress_checkpoint_mode": PROGRESS_CHECKPOINT_MODE,
        "selected_progress_checkpoint_endpoint": PROGRESS_CHECKPOINT_ENDPOINT,
        "selected_progress_checkpoint_receipt_binding": (
            "worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,"
            "scheduler_lease_receipt_id,queue_state_receipt_id,operator_workflow_receipt_id,"
            "operator_workflow_receipt_hash,progress_checkpoint_sequence,progress_checkpoint_hash"
        ),
        "selected_progress_checkpoint_idempotency_basis": "client_request_id_plus_progress_checkpoint_authority_hash",
        "progress_checkpoint_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "completion_runtime_selected_now": False,
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
        "next_allowed_actions": [
            "refresh workflow-run history",
            "inspect the original workflow run through the returned status request",
            "record append-only completion/failure authority through the admitted completion/failure endpoint",
            "select cancel, retry, or resume only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {**receipt_input, "progress_checkpoint_receipt_hash": receipt_hash, "server_time": workflow_status._server_time()}
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _validate_next_progress_checkpoint_sequence(
    *,
    root: Path,
    progress_checkpoint_receipt_id: str,
    worker_attempt_receipt_id: str,
    worker_attempt_authority_hash: str,
    progress_checkpoint_sequence: int,
) -> dict[str, Any]:
    existing_sequences: list[tuple[int, str]] = []
    for receipt_file in sorted(root.glob(f"{PROGRESS_CHECKPOINT_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        existing = _read_json_receipt(receipt_file)
        if (
            existing_id != progress_checkpoint_receipt_id
            and existing.get("worker_attempt_receipt_id") == worker_attempt_receipt_id
            and existing.get("worker_attempt_authority_hash") == worker_attempt_authority_hash
        ):
            sequence = existing.get("progress_checkpoint_sequence")
            if sequence == progress_checkpoint_sequence:
                raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
                    "candidate_b_full_corpus_operator_workflow_progress_checkpoint_conflict",
                    "The selected Candidate B worker attempt already has a progress checkpoint for this sequence.",
                    http_status=409,
                    details={"existing_progress_checkpoint_receipt_id": existing_id, "progress_checkpoint_sequence": sequence},
                )
            if isinstance(sequence, int):
                existing_sequences.append((sequence, existing_id))
    expected = max((sequence for sequence, _ in existing_sequences), default=0) + 1
    if progress_checkpoint_sequence != expected:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_sequence_not_next",
            "Candidate B progress checkpoints must be appended in monotonically increasing sequence order.",
            http_status=409,
            details={"expected_progress_checkpoint_sequence": expected, "received_progress_checkpoint_sequence": progress_checkpoint_sequence},
        )
    previous = max(existing_sequences, default=(0, None), key=lambda item: item[0])
    return {"previous_sequence": previous[0] or None, "previous_receipt_id": previous[1]}


def _validate_progress_checkpoint_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    progress_checkpoint_receipt_id: str,
    progress_checkpoint_hash: str,
    progress_checkpoint_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROGRESS_CHECKPOINT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "progress_checkpoint_state": PROGRESS_CHECKPOINT_STATE,
        "progress_checkpoint_receipt_id": progress_checkpoint_receipt_id,
        "progress_checkpoint_hash": progress_checkpoint_hash,
        "progress_checkpoint_authority_hash": progress_checkpoint_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_progress_checkpoint_receipt": True,
        "monotonic_progress_checkpoint_sequence": True,
        "worker_attempt_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "progress_checkpoint_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "completion_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "expiry_enforcement_runtime_selected_now": False,
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
        {key: value for key, value in receipt.items() if key not in {"progress_checkpoint_receipt_hash", "server_time"}}
    )
    if receipt.get("progress_checkpoint_receipt_hash") != receipt_hash:
        mismatches.append(
            {"field": "progress_checkpoint_receipt_hash", "expected": receipt_hash, "received": receipt.get("progress_checkpoint_receipt_hash")}
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            f"candidate_b_full_corpus_operator_workflow_progress_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_idempotency_conflict",
            "The existing Candidate B workflow-run progress-checkpoint receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_receipt_unreadable",
            "A Candidate B workflow-run progress-checkpoint receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_receipt_invalid",
            "Candidate B workflow-run progress-checkpoint receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_required_field_missing",
            "A required Candidate B workflow-run progress-checkpoint field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_hash_invalid",
            "Candidate B workflow-run progress-checkpoint hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _required_positive_int(fields: Mapping[str, Any], key: str) -> int:
    value = fields.get(key)
    if not isinstance(value, int) or value < 1:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_integer_invalid",
            "Candidate B workflow-run progress-checkpoint integer fields must be positive integers.",
            details={"field": key, "received": value},
        )
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        workflow_status._validate_storage_id(value, prefix=prefix)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowProgressCheckpointError(
            "candidate_b_full_corpus_operator_workflow_progress_checkpoint_storage_id_invalid",
            "Candidate B workflow-run progress-checkpoint identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
