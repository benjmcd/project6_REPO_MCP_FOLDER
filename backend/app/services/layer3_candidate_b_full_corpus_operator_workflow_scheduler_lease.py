from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_operator_workflow_access_policy as workflow_access_policy,
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_queue_state as workflow_queue_state,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_scheduler_lease.v1"
SCHEMA_VERSION = 1
SCHEDULER_LEASE_MODE = "append_only_scheduler_lease_receipt_without_background_worker"
OPERATOR_DECISION = "record_candidate_b_async_scheduler_lease"
SCHEDULER_LEASE_STATE = "leased"
SCHEDULER_LEASE_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-scheduler-lease"
SCHEDULER_LEASE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease"
)
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
    "background_worker",
    "job_execution",
    "cancel",
    "retry",
    "resume",
}


class CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-scheduler-lease-error",
            "server_time": workflow_status._server_time(),
            "mode": SCHEDULER_LEASE_MODE,
            "status": "blocked",
            "scheduler_lease_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_workflow_scheduler_lease(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "scheduler_lease_mode") != SCHEDULER_LEASE_MODE:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_mode_not_admitted",
            "Only append-only Candidate B workflow scheduler lease receipt mode is admitted.",
            details={"expected_scheduler_lease_mode": SCHEDULER_LEASE_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_decision_not_admitted",
            "The operator decision does not match the admitted scheduler lease receipt action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    queue_state_receipt = _selected_queue_state_receipt(row, history, fields)
    queue_state_receipt_id = _required(fields, "queue_state_receipt_id")
    queue_state_receipt_hash = _required_hash(fields, "queue_state_receipt_hash")
    queue_state_authority_hash = _required_hash(fields, "queue_state_authority_hash")

    scheduler_lease = {
        "scheduler_lease_mode": SCHEDULER_LEASE_MODE,
        "scheduler_lease_state": SCHEDULER_LEASE_STATE,
        "queue_state_receipt_id": queue_state_receipt_id,
        "queue_state_receipt_hash": queue_state_receipt_hash,
        "queue_state_authority_hash": queue_state_authority_hash,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "run_state_before_scheduler_lease": row["run_state"],
        "queue_state_before_scheduler_lease": queue_state_receipt["queue_state"],
        "background_worker_started": False,
        "job_execution_started": False,
    }
    scheduler_lease_hash = workflow_status._stable_hash(scheduler_lease)
    scheduler_lease_authority = {
        **scheduler_lease,
        "operator_decision": OPERATOR_DECISION,
        "scheduler_lease_hash": scheduler_lease_hash,
    }
    scheduler_lease_authority_hash = workflow_status._stable_hash(scheduler_lease_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "scheduler_lease_authority_hash": scheduler_lease_authority_hash,
        }
    )
    scheduler_lease_receipt_id = f"{SCHEDULER_LEASE_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_scheduler_lease_receipt(
        scheduler_lease_receipt_id=scheduler_lease_receipt_id,
        request_id=request_id,
        row=row,
        history=history,
        queue_state_receipt=queue_state_receipt,
        scheduler_lease=scheduler_lease,
        scheduler_lease_hash=scheduler_lease_hash,
        scheduler_lease_authority=scheduler_lease_authority,
        scheduler_lease_authority_hash=scheduler_lease_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_scheduler_lease_receipt(
        receipt,
        request_id=request_id,
        scheduler_lease_receipt_id=scheduler_lease_receipt_id,
        scheduler_lease_hash=scheduler_lease_hash,
        scheduler_lease_authority_hash=scheduler_lease_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "scheduler_lease_receipt_hash": receipt_hash,
        "scheduler_lease_receipt_ref": (
            f"candidate-b-full-corpus-operator-workflow-scheduler-lease://"
            f"{scheduler_lease_receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "queue_state_endpoint": QUEUE_STATE_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_forbidden_request_fields",
            "Workflow scheduler leases do not admit caller paths, URLs, selector mutation, connector/model controls, browser authority, workers, job execution, cancel, retry, or resume.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            f"candidate_b_full_corpus_operator_workflow_scheduler_lease_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "operator_workflow_receipt_id")
    _validate_storage_id(receipt_id, prefix=workflow_run.RUN_RECEIPT_PREFIX)
    rows = history.get("history_rows")
    if not isinstance(rows, list):
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_history_rows_invalid",
            "Candidate B workflow scheduler leases require a valid server-owned history row set.",
            http_status=409,
        )
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("operator_workflow_receipt_id") == receipt_id]
    if not matches:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_run_receipt_missing",
            "The selected Candidate B workflow-run receipt is not present in current server-owned history.",
            http_status=404,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_run_receipt_ambiguous",
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
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_stale_authority",
            "The selected Candidate B workflow-run scheduler lease authority is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    workflow_access_policy.authorize_history_row_access(
        fields=fields,
        row=row,
        route_family="queue_scheduler_worker_progress_completion_retry",
        rendered_surface="scheduler_lease",
        requested_role=workflow_access_policy.OWNER_ROLE,
    )


def _selected_queue_state_receipt(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    queue_state_receipt_id = _required(fields, "queue_state_receipt_id")
    _validate_storage_id(queue_state_receipt_id, prefix=workflow_queue_state.QUEUE_STATE_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / queue_state_receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_queue_state_receipt_missing",
            "The selected Candidate B workflow queue-state receipt is not present in server-owned receipt authority.",
            http_status=404,
            details={"queue_state_receipt_id": queue_state_receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    expected = {
        "schema_id": workflow_queue_state.SCHEMA_ID,
        "schema_version": workflow_queue_state.SCHEMA_VERSION,
        "mode": workflow_queue_state.QUEUE_STATE_MODE,
        "operator_decision": workflow_queue_state.OPERATOR_DECISION,
        "status": "available",
        "queue_state": workflow_queue_state.QUEUE_STATE,
        "queue_state_receipt_id": queue_state_receipt_id,
        "queue_state_receipt_hash": _required_hash(fields, "queue_state_receipt_hash"),
        "queue_state_authority_hash": _required_hash(fields, "queue_state_authority_hash"),
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "append_only_queue_state_receipt": True,
        "source_run_receipt_mutated": False,
        "queue_state_authority_runtime_selected": True,
        "queue_scheduler_runtime_selected_now": False,
        "background_worker_runtime_selected_now": False,
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
        {key: value for key, value in receipt.items() if key not in {"queue_state_receipt_hash", "server_time"}}
    )
    if receipt.get("queue_state_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "queue_state_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("queue_state_receipt_hash"),
            }
        )
    try:
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            f"candidate_b_full_corpus_operator_workflow_scheduler_lease_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_stale_queue_state_receipt",
            "The selected Candidate B workflow queue-state receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt


def _load_or_write_scheduler_lease_receipt(
    *,
    scheduler_lease_receipt_id: str,
    request_id: str,
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    queue_state_receipt: Mapping[str, Any],
    scheduler_lease: Mapping[str, Any],
    scheduler_lease_hash: str,
    scheduler_lease_authority: Mapping[str, Any],
    scheduler_lease_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / scheduler_lease_receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_scheduler_lease_receipt(
            existing,
            request_id=request_id,
            scheduler_lease_receipt_id=scheduler_lease_receipt_id,
            scheduler_lease_hash=scheduler_lease_hash,
            scheduler_lease_authority_hash=scheduler_lease_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True

    _reject_competing_scheduler_lease(
        root=root,
        scheduler_lease_receipt_id=scheduler_lease_receipt_id,
        queue_state_receipt_id=str(queue_state_receipt["queue_state_receipt_id"]),
        queue_state_authority_hash=str(queue_state_receipt["queue_state_authority_hash"]),
    )
    _acquire_scheduler_lease_index(
        root=root,
        scheduler_lease_receipt_id=scheduler_lease_receipt_id,
        queue_state_receipt_id=str(queue_state_receipt["queue_state_receipt_id"]),
        queue_state_authority_hash=str(queue_state_receipt["queue_state_authority_hash"]),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": SCHEDULER_LEASE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "scheduler_lease_state": SCHEDULER_LEASE_STATE,
        "scheduler_lease_receipt_id": scheduler_lease_receipt_id,
        "queue_state_receipt_id": queue_state_receipt["queue_state_receipt_id"],
        "queue_state_receipt_hash": queue_state_receipt["queue_state_receipt_hash"],
        "queue_state_authority_hash": queue_state_receipt["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "source_operator_workflow_receipt_id": row["source_operator_workflow_receipt_id"],
        "source_operator_workflow_receipt_hash": row["source_operator_workflow_receipt_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "row_hash": row["row_hash"],
        "history_hash": history["history_hash"],
        "scheduler_lease": dict(scheduler_lease),
        "scheduler_lease_hash": scheduler_lease_hash,
        "scheduler_lease_authority": dict(scheduler_lease_authority),
        "scheduler_lease_authority_hash": scheduler_lease_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_scheduler_lease_receipt": True,
        "exclusive_queue_state_lease": True,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "run_state_before_scheduler_lease": row["run_state"],
        "run_state_after_scheduler_lease": row["run_state"],
        "queue_state_before_scheduler_lease": queue_state_receipt["queue_state"],
        "selected_scheduler_mode": SCHEDULER_LEASE_MODE,
        "selected_scheduler_endpoint": SCHEDULER_LEASE_ENDPOINT,
        "selected_scheduler_receipt_binding": (
            "queue_state_receipt_id,queue_state_receipt_hash,queue_state_authority_hash,"
            "operator_workflow_receipt_id,operator_workflow_receipt_hash,scheduler_lease_hash"
        ),
        "selected_scheduler_idempotency_basis": "client_request_id_plus_scheduler_lease_authority_hash",
        "scheduler_lease_runtime_selected": True,
        "background_worker_runtime_selected_now": False,
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
        "next_allowed_actions": [
            "refresh workflow-run history",
            "inspect the original workflow run through the returned status request",
            "record append-only worker-attempt authority through the admitted worker attempt endpoint",
            "select progress checkpoint, completion, cancel, retry, or resume only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "scheduler_lease_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_scheduler_lease(
    *,
    root: Path,
    scheduler_lease_receipt_id: str,
    queue_state_receipt_id: str,
    queue_state_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{SCHEDULER_LEASE_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        existing = _read_json_receipt(receipt_file)
        if (
            existing_id != scheduler_lease_receipt_id
            and existing.get("queue_state_receipt_id") == queue_state_receipt_id
            and existing.get("queue_state_authority_hash") == queue_state_authority_hash
        ):
            raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
                "candidate_b_full_corpus_operator_workflow_scheduler_lease_conflict",
                "The selected Candidate B workflow queue-state receipt already has a server-owned scheduler lease.",
                http_status=409,
                details={
                    "queue_state_receipt_id": queue_state_receipt_id,
                    "existing_scheduler_lease_receipt_id": existing_id,
                },
            )


def _acquire_scheduler_lease_index(
    *,
    root: Path,
    scheduler_lease_receipt_id: str,
    queue_state_receipt_id: str,
    queue_state_authority_hash: str,
) -> None:
    index_hash = workflow_status._stable_hash(
        {
            "queue_state_receipt_id": queue_state_receipt_id,
            "queue_state_authority_hash": queue_state_authority_hash,
            "exclusive_queue_state_lease": True,
        }
    )
    index_dir = root / f"{SCHEDULER_LEASE_RECEIPT_PREFIX}-queue-state-index-{index_hash[:24]}"
    try:
        index_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        _reject_competing_scheduler_lease(
            root=root,
            scheduler_lease_receipt_id=scheduler_lease_receipt_id,
            queue_state_receipt_id=queue_state_receipt_id,
            queue_state_authority_hash=queue_state_authority_hash,
        )
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_conflict",
            "The selected Candidate B workflow queue-state receipt already has a server-owned scheduler lease.",
            http_status=409,
            details={"scheduler_lease_index": index_dir.name},
        ) from exc


def _validate_scheduler_lease_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    scheduler_lease_receipt_id: str,
    scheduler_lease_hash: str,
    scheduler_lease_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": SCHEDULER_LEASE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "scheduler_lease_state": SCHEDULER_LEASE_STATE,
        "scheduler_lease_receipt_id": scheduler_lease_receipt_id,
        "scheduler_lease_hash": scheduler_lease_hash,
        "scheduler_lease_authority_hash": scheduler_lease_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
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
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            f"candidate_b_full_corpus_operator_workflow_scheduler_lease_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_idempotency_conflict",
            "The existing Candidate B workflow-run scheduler lease receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_receipt_unreadable",
            "A Candidate B workflow-run scheduler lease receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_receipt_invalid",
            "Candidate B workflow-run scheduler lease receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_required_field_missing",
            "A required Candidate B workflow-run scheduler lease field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_hash_invalid",
            "Candidate B workflow-run scheduler lease hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        workflow_status._validate_storage_id(value, prefix=prefix)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError(
            "candidate_b_full_corpus_operator_workflow_scheduler_lease_storage_id_invalid",
            "Candidate B workflow-run scheduler lease identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
