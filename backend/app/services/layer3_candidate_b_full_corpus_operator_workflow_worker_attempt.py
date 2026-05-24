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
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_worker_attempt.v1"
SCHEMA_VERSION = 1
WORKER_ATTEMPT_MODE = "append_only_worker_attempt_receipt_without_job_execution"
OPERATOR_DECISION = "record_candidate_b_async_worker_attempt"
WORKER_ATTEMPT_STATE = "attempt_authority_recorded"
WORKER_ATTEMPT_NUMBER = 1
WORKER_ATTEMPT_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-worker-attempt"
WORKER_ATTEMPT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt"
)
SCHEDULER_LEASE_ENDPOINT = scheduler_lease.SCHEDULER_LEASE_ENDPOINT
QUEUE_STATE_ENDPOINT = workflow_queue_state.QUEUE_STATE_ENDPOINT
HISTORY_ENDPOINT = workflow_queue_state.HISTORY_ENDPOINT
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
    "progress_checkpoint",
    "completion",
    "cancel",
    "retry",
    "resume",
}


class CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-worker-attempt-error",
            "server_time": workflow_status._server_time(),
            "mode": WORKER_ATTEMPT_MODE,
            "status": "blocked",
            "worker_attempt_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_worker_attempt(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "worker_attempt_mode") != WORKER_ATTEMPT_MODE:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_mode_not_admitted",
            "Only append-only Candidate B workflow worker-attempt receipt mode is admitted.",
            details={"expected_worker_attempt_mode": WORKER_ATTEMPT_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_decision_not_admitted",
            "The operator decision does not match the admitted worker-attempt receipt action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    if _required_int(fields, "worker_attempt_number") != WORKER_ATTEMPT_NUMBER:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_number_not_admitted",
            "Only the initial Candidate B worker attempt is admitted in this slice.",
            details={"expected_worker_attempt_number": WORKER_ATTEMPT_NUMBER},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    lease_receipt = _selected_scheduler_lease_receipt(row, history, fields)
    worker_attempt = {
        "worker_attempt_mode": WORKER_ATTEMPT_MODE,
        "worker_attempt_state": WORKER_ATTEMPT_STATE,
        "worker_attempt_number": WORKER_ATTEMPT_NUMBER,
        "scheduler_lease_receipt_id": lease_receipt["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": lease_receipt["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": lease_receipt["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": lease_receipt["queue_state_receipt_id"],
        "queue_state_receipt_hash": lease_receipt["queue_state_receipt_hash"],
        "queue_state_authority_hash": lease_receipt["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "run_state_before_worker_attempt": row["run_state"],
        "scheduler_lease_state_before_worker_attempt": lease_receipt["scheduler_lease_state"],
        "background_process_started": False,
        "job_execution_started": False,
        "progress_checkpoint_emitted": False,
        "completion_emitted": False,
    }
    worker_attempt_hash = workflow_status._stable_hash(worker_attempt)
    worker_attempt_authority = {
        **worker_attempt,
        "operator_decision": OPERATOR_DECISION,
        "worker_attempt_hash": worker_attempt_hash,
    }
    worker_attempt_authority_hash = workflow_status._stable_hash(worker_attempt_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {"client_request_id": request_id, "worker_attempt_authority_hash": worker_attempt_authority_hash}
    )
    worker_attempt_receipt_id = f"{WORKER_ATTEMPT_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_worker_attempt_receipt(
        worker_attempt_receipt_id=worker_attempt_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        lease_receipt=lease_receipt,
        worker_attempt=worker_attempt,
        worker_attempt_hash=worker_attempt_hash,
        worker_attempt_authority=worker_attempt_authority,
        worker_attempt_authority_hash=worker_attempt_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_worker_attempt_receipt(
        receipt,
        request_id=request_id,
        worker_attempt_receipt_id=worker_attempt_receipt_id,
        worker_attempt_hash=worker_attempt_hash,
        worker_attempt_authority_hash=worker_attempt_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "worker_attempt_receipt_hash": receipt_hash,
        "worker_attempt_receipt_ref": (
            f"candidate-b-full-corpus-operator-workflow-worker-attempt://"
            f"{worker_attempt_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "queue_state_endpoint": QUEUE_STATE_ENDPOINT,
        "scheduler_lease_endpoint": SCHEDULER_LEASE_ENDPOINT,
        "worker_attempt_endpoint": WORKER_ATTEMPT_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_forbidden_request_fields",
            "Workflow worker attempts do not admit caller paths, URLs, selector mutation, connector/model controls, browser authority, process start, job execution, progress, completion, cancel, retry, or resume.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            f"candidate_b_full_corpus_operator_workflow_worker_attempt_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "operator_workflow_receipt_id")
    _validate_storage_id(receipt_id, prefix=workflow_run.RUN_RECEIPT_PREFIX)
    rows = history.get("history_rows")
    if not isinstance(rows, list):
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_history_rows_invalid",
            "Candidate B workflow worker attempts require a valid server-owned history row set.",
            http_status=409,
        )
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("operator_workflow_receipt_id") == receipt_id]
    if not matches:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_run_receipt_missing",
            "The selected Candidate B workflow-run receipt is not present in current server-owned history.",
            http_status=404,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_run_receipt_ambiguous",
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
    if not isinstance(row.get("status_request"), Mapping):
        mismatches.append({"field": "status_request", "expected": "server-owned status request", "received": None})
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_stale_authority",
            "The selected Candidate B workflow-run worker-attempt authority is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _selected_scheduler_lease_receipt(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    lease_receipt_id = _required(fields, "scheduler_lease_receipt_id")
    _validate_storage_id(lease_receipt_id, prefix=scheduler_lease.SCHEDULER_LEASE_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / lease_receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_scheduler_lease_receipt_missing",
            "The selected Candidate B scheduler lease receipt is not present in server-owned receipt authority.",
            http_status=404,
            details={"scheduler_lease_receipt_id": lease_receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    expected = {
        "schema_id": scheduler_lease.SCHEMA_ID,
        "schema_version": scheduler_lease.SCHEMA_VERSION,
        "mode": scheduler_lease.SCHEDULER_LEASE_MODE,
        "operator_decision": scheduler_lease.OPERATOR_DECISION,
        "status": "available",
        "scheduler_lease_state": scheduler_lease.SCHEDULER_LEASE_STATE,
        "scheduler_lease_receipt_id": lease_receipt_id,
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
        "append_only_scheduler_lease_receipt": True,
        "exclusive_queue_state_lease": True,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "scheduler_lease_runtime_selected": True,
        "background_worker_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
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
        {key: value for key, value in receipt.items() if key not in {"scheduler_lease_receipt_hash", "server_time"}}
    )
    if receipt.get("scheduler_lease_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "scheduler_lease_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("scheduler_lease_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            f"candidate_b_full_corpus_operator_workflow_worker_attempt_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_stale_scheduler_lease_receipt",
            "The selected Candidate B scheduler lease receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt


def _load_or_write_worker_attempt_receipt(
    *,
    worker_attempt_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    lease_receipt: Mapping[str, Any],
    worker_attempt: Mapping[str, Any],
    worker_attempt_hash: str,
    worker_attempt_authority: Mapping[str, Any],
    worker_attempt_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / worker_attempt_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_worker_attempt_receipt(
            existing,
            request_id=request_id,
            worker_attempt_receipt_id=worker_attempt_receipt_id,
            worker_attempt_hash=worker_attempt_hash,
            worker_attempt_authority_hash=worker_attempt_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    _reject_competing_worker_attempt(
        root=root,
        worker_attempt_receipt_id=worker_attempt_receipt_id,
        scheduler_lease_receipt_id=str(lease_receipt["scheduler_lease_receipt_id"]),
        scheduler_lease_authority_hash=str(lease_receipt["scheduler_lease_authority_hash"]),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": WORKER_ATTEMPT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "worker_attempt_state": WORKER_ATTEMPT_STATE,
        "worker_attempt_number": WORKER_ATTEMPT_NUMBER,
        "worker_attempt_receipt_id": worker_attempt_receipt_id,
        "scheduler_lease_receipt_id": lease_receipt["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": lease_receipt["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": lease_receipt["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": lease_receipt["queue_state_receipt_id"],
        "queue_state_receipt_hash": lease_receipt["queue_state_receipt_hash"],
        "queue_state_authority_hash": lease_receipt["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "worker_attempt": dict(worker_attempt),
        "worker_attempt_hash": worker_attempt_hash,
        "worker_attempt_authority": dict(worker_attempt_authority),
        "worker_attempt_authority_hash": worker_attempt_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_worker_attempt_receipt": True,
        "exclusive_initial_attempt_per_scheduler_lease": True,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "run_state_before_worker_attempt": row["run_state"],
        "run_state_after_worker_attempt": row["run_state"],
        "scheduler_lease_state_before_worker_attempt": lease_receipt["scheduler_lease_state"],
        "selected_worker_attempt_mode": WORKER_ATTEMPT_MODE,
        "selected_worker_attempt_endpoint": WORKER_ATTEMPT_ENDPOINT,
        "selected_worker_attempt_receipt_binding": (
            "scheduler_lease_receipt_id,scheduler_lease_receipt_hash,scheduler_lease_authority_hash,"
            "queue_state_receipt_id,queue_state_receipt_hash,operator_workflow_receipt_id,"
            "operator_workflow_receipt_hash,worker_attempt_hash"
        ),
        "selected_worker_attempt_idempotency_basis": "client_request_id_plus_worker_attempt_authority_hash",
        "worker_attempt_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "progress_checkpoint_runtime_selected_now": False,
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
            "record append-only progress-checkpoint authority through the admitted progress checkpoint endpoint",
            "select completion, cancel, retry, or resume only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "worker_attempt_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_worker_attempt(
    *,
    root: Path,
    worker_attempt_receipt_id: str,
    scheduler_lease_receipt_id: str,
    scheduler_lease_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{WORKER_ATTEMPT_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        existing = _read_json_receipt(receipt_file)
        if (
            existing_id != worker_attempt_receipt_id
            and existing.get("scheduler_lease_receipt_id") == scheduler_lease_receipt_id
            and existing.get("scheduler_lease_authority_hash") == scheduler_lease_authority_hash
            and existing.get("worker_attempt_number") == WORKER_ATTEMPT_NUMBER
        ):
            raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
                "candidate_b_full_corpus_operator_workflow_worker_attempt_conflict",
                "The selected Candidate B scheduler lease already has a server-owned initial worker attempt.",
                http_status=409,
                details={
                    "scheduler_lease_receipt_id": scheduler_lease_receipt_id,
                    "existing_worker_attempt_receipt_id": existing_id,
                },
            )


def _validate_worker_attempt_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    worker_attempt_receipt_id: str,
    worker_attempt_hash: str,
    worker_attempt_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": WORKER_ATTEMPT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "worker_attempt_state": WORKER_ATTEMPT_STATE,
        "worker_attempt_number": WORKER_ATTEMPT_NUMBER,
        "worker_attempt_receipt_id": worker_attempt_receipt_id,
        "worker_attempt_hash": worker_attempt_hash,
        "worker_attempt_authority_hash": worker_attempt_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
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
        {key: value for key, value in receipt.items() if key not in {"worker_attempt_receipt_hash", "server_time"}}
    )
    if receipt.get("worker_attempt_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "worker_attempt_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("worker_attempt_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            f"candidate_b_full_corpus_operator_workflow_worker_attempt_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_idempotency_conflict",
            "The existing Candidate B workflow-run worker-attempt receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_receipt_unreadable",
            "A Candidate B workflow-run worker-attempt receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_receipt_invalid",
            "Candidate B workflow-run worker-attempt receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_required_field_missing",
            "A required Candidate B workflow-run worker-attempt field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_hash_invalid",
            "Candidate B workflow-run worker-attempt hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _required_int(fields: Mapping[str, Any], key: str) -> int:
    value = fields.get(key)
    if not isinstance(value, int):
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_integer_invalid",
            "Candidate B workflow-run worker-attempt integer fields must be integers.",
            details={"field": key, "received": value},
        )
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        workflow_status._validate_storage_id(value, prefix=prefix)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowWorkerAttemptError(
            "candidate_b_full_corpus_operator_workflow_worker_attempt_storage_id_invalid",
            "Candidate B workflow-run worker-attempt identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
