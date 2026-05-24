from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_completion_monitor as completion_monitor,
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_repeatability_checkpoint.v1"
SCHEMA_VERSION = 1
REPEATABILITY_CHECKPOINT_MODE = (
    "append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation"
)
OPERATOR_DECISION = "record_candidate_b_full_corpus_operator_repeatability_checkpoint"
REPEATABILITY_CHECKPOINT_STATE = "repeatability_checkpoint_recorded"
REPEATABILITY_CHECKPOINT_RECEIPT_PREFIX = (
    f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-repeatability-checkpoint"
)
REPEATABILITY_CHECKPOINT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint"
)
HISTORY_ENDPOINT = completion_monitor.HISTORY_ENDPOINT
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
COMPLETION_MONITOR_ENDPOINT = completion_monitor.COMPLETION_MONITOR_ENDPOINT
REQUIRED_RUNBOOK_STEPS = (
    "refresh_workflow_history",
    "inspect_workflow_status",
    "inspect_completion_monitor",
    "record_repeatability_checkpoint",
)
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


class CandidateBFullCorpusOperatorRepeatabilityCheckpointError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-repeatability-checkpoint-error",
            "server_time": workflow_status._server_time(),
            "mode": REPEATABILITY_CHECKPOINT_MODE,
            "status": "blocked",
            "repeatability_checkpoint_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_operator_repeatability_checkpoint(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "repeatability_checkpoint_mode") != REPEATABILITY_CHECKPOINT_MODE:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_mode_not_admitted",
            "Only the append-only Candidate B repeatability-checkpoint mode is admitted.",
            details={"expected_repeatability_checkpoint_mode": REPEATABILITY_CHECKPOINT_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_decision_not_admitted",
            "The operator decision does not match the admitted repeatability-checkpoint action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )
    runbook_steps = _required_runbook_steps(fields)

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    status_projection = _validated_status_projection(row, fields)
    monitor_projection = _validated_completion_monitor_projection(row, fields)
    _validate_bound_authority(row, status_projection, fields)

    checkpoint = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": REPEATABILITY_CHECKPOINT_MODE,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "workflow_status_hash": status_projection["workflow_status_hash"],
        "completion_monitor_hash": monitor_projection["completion_monitor_hash"],
        "completion_monitor_state": monitor_projection["completion_monitor_state"],
        "runtime_root_lifecycle_receipt_id": _required(fields, "runtime_root_lifecycle_receipt_id"),
        "bridge_receipt_id": _required(fields, "bridge_receipt_id"),
        "downstream_proof_id": _required(fields, "downstream_proof_id"),
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "candidate_b_run_id": _required(fields, "candidate_b_run_id"),
        "compare_target_set_hash": _required_hash(fields, "compare_target_set_hash"),
        "material_relative_name": _required(fields, "material_relative_name"),
        "operator_runbook_repeatability_steps": runbook_steps,
        "status_projection": _status_checkpoint_projection(status_projection),
        "completion_monitor_projection": _completion_monitor_checkpoint_projection(monitor_projection),
    }
    checkpoint_hash = workflow_status._stable_hash(checkpoint)
    checkpoint_authority = {
        **checkpoint,
        "operator_decision": OPERATOR_DECISION,
        "repeatability_checkpoint_hash": checkpoint_hash,
    }
    checkpoint_authority_hash = workflow_status._stable_hash(checkpoint_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {"client_request_id": request_id, "repeatability_checkpoint_authority_hash": checkpoint_authority_hash}
    )
    receipt_id = f"{REPEATABILITY_CHECKPOINT_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_repeatability_checkpoint_receipt(
        receipt_id=receipt_id,
        request_id=request_id,
        checkpoint=checkpoint,
        checkpoint_hash=checkpoint_hash,
        checkpoint_authority=checkpoint_authority,
        checkpoint_authority_hash=checkpoint_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_repeatability_checkpoint_receipt(
        receipt,
        request_id=request_id,
        receipt_id=receipt_id,
        checkpoint_hash=checkpoint_hash,
        checkpoint_authority_hash=checkpoint_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "repeatability_checkpoint_receipt_hash": receipt_hash,
        "repeatability_checkpoint_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-repeatability-checkpoint://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "completion_monitor_endpoint": COMPLETION_MONITOR_ENDPOINT,
        "repeatability_checkpoint_endpoint": REPEATABILITY_CHECKPOINT_ENDPOINT,
        "status_request": dict(row["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
        "completion_monitor_request": _completion_monitor_payload(row, history),
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_forbidden_request_fields",
            "Repeatability checkpoints do not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, stdout, stderr, raw PIDs, or artifact bytes.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_{exc.code}",
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
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validated_status_projection(row: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    status_request = row.get("status_request")
    if not isinstance(status_request, Mapping):
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_status_request_missing",
            "Candidate B repeatability checkpoints require a workflow-status request in the selected history row.",
            http_status=409,
        )
    try:
        status_projection = workflow_status.candidate_b_full_corpus_operator_workflow_status(status_request)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_status_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    supplied_hash = _required_hash(fields, "workflow_status_hash")
    if status_projection.get("workflow_status_hash") != supplied_hash:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_stale_workflow_status",
            "The selected Candidate B workflow-status projection is stale or mismatched.",
            http_status=409,
            details={"expected_workflow_status_hash": status_projection.get("workflow_status_hash"), "received_workflow_status_hash": supplied_hash},
        )
    if status_projection.get("workflow_status") != "proven":
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_status_not_proven",
            "Candidate B repeatability checkpoints require a proven workflow status.",
            http_status=409,
            details={"workflow_status": status_projection.get("workflow_status")},
        )
    return status_projection


def _validated_completion_monitor_projection(row: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    payload = _completion_monitor_payload(row, {"history_hash": fields["history_hash"]})
    try:
        monitor_projection = completion_monitor.inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(payload)
    except completion_monitor.CandidateBFullCorpusOperatorWorkflowCompletionMonitorError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_completion_monitor_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    supplied_hash = _required_hash(fields, "completion_monitor_hash")
    if monitor_projection.get("completion_monitor_hash") != supplied_hash:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_stale_completion_monitor",
            "The selected Candidate B completion-monitor projection is stale or mismatched.",
            http_status=409,
            details={"expected_completion_monitor_hash": monitor_projection.get("completion_monitor_hash"), "received_completion_monitor_hash": supplied_hash},
        )
    if monitor_projection.get("completion_monitor_state") != "completed_downstream_proven":
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_completion_monitor_not_downstream_proven",
            "Candidate B repeatability checkpoints require a downstream-proven completion monitor.",
            http_status=409,
            details={"completion_monitor_state": monitor_projection.get("completion_monitor_state")},
        )
    return monitor_projection


def _validate_bound_authority(
    row: Mapping[str, Any],
    status_projection: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> None:
    runtime_root_lifecycle = status_projection.get("runtime_root_lifecycle")
    if not isinstance(runtime_root_lifecycle, Mapping) or runtime_root_lifecycle.get("available") is not True:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_runtime_root_lifecycle_missing",
            "Candidate B repeatability checkpoints require an available runtime-root lifecycle projection.",
            http_status=409,
        )
    expected = {
        "runtime_root_lifecycle_receipt_id": runtime_root_lifecycle.get("lifecycle_receipt_id"),
        "bridge_receipt_id": status_projection.get("bridge_receipt_id"),
        "downstream_proof_id": status_projection.get("downstream_proof_id"),
        "baseline_run_id": status_projection.get("baseline_run_id"),
        "candidate_a_run_id": status_projection.get("candidate_a_run_id"),
        "candidate_b_run_id": status_projection.get("candidate_b_run_id"),
        "compare_target_set_hash": status_projection.get("compare_target_set_hash"),
        "material_relative_name": _material_relative_name(status_projection, row),
    }
    mismatches = [
        {"field": key, "expected": value, "received": fields.get(key)}
        for key, value in expected.items()
        if fields.get(key) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_stale_bound_authority",
            "The selected Candidate B repeatability-checkpoint authority is stale or mismatched.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    _assert_no_raw_authority_exposure(status_projection)


def _completion_monitor_payload(row: Mapping[str, Any], history: Mapping[str, Any]) -> dict[str, Any]:
    process_execution = _projection(row, "process_execution_projection")
    process_completion = _projection(row, "process_completion_result_projection")
    adopted_proof = _projection(row, "adopted_result_downstream_proof_projection")
    return {
        "client_request_id": "candidate-b-repeatability-checkpoint-completion-monitor",
        "completion_monitor_mode": completion_monitor.COMPLETION_MONITOR_MODE,
        "operator_decision": completion_monitor.OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "process_execution_receipt_id": process_execution.get("process_execution_receipt_id") or "",
        "process_execution_receipt_hash": process_execution.get("process_execution_receipt_hash") or "",
        "process_completion_result_receipt_id": process_completion.get("process_completion_result_receipt_id") or "",
        "process_completion_result_receipt_hash": process_completion.get("process_completion_result_receipt_hash") or "",
        "adopted_result_downstream_proof_receipt_id": adopted_proof.get("adopted_result_downstream_proof_receipt_id") or "",
        "adopted_result_downstream_proof_receipt_hash": adopted_proof.get("adopted_result_downstream_proof_receipt_hash") or "",
    }


def _projection(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    projection = row.get(key)
    if not isinstance(projection, Mapping):
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_projection_missing",
            "Candidate B repeatability checkpoints require workflow status and completion-monitor projections.",
            http_status=409,
            details={"projection": key},
        )
    return dict(projection)


def _status_checkpoint_projection(status_projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "workflow_status": status_projection["workflow_status"],
        "workflow_status_hash": status_projection["workflow_status_hash"],
        "workflow_receipt_id": status_projection["workflow_receipt_id"],
        "workflow_receipt_hash": status_projection["workflow_receipt_hash"],
        "bridge_receipt_id": status_projection["bridge_receipt_id"],
        "downstream_proof_id": status_projection["downstream_proof_id"],
        "runtime_root_lifecycle": dict(status_projection["runtime_root_lifecycle"]),
        "artifact_family": dict(status_projection.get("artifact_family") or {}),
        "layer3": dict(status_projection.get("layer3") or {}),
        "baseline_rollback": dict(status_projection.get("baseline_rollback") or {}),
    }


def _completion_monitor_checkpoint_projection(monitor_projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "completion_monitor_state": monitor_projection["completion_monitor_state"],
        "completion_monitor_hash": monitor_projection["completion_monitor_hash"],
        "process_execution_projection": dict(monitor_projection["process_execution_projection"]),
        "process_completion_result_projection": dict(monitor_projection["process_completion_result_projection"]),
        "adopted_result_downstream_proof_projection": dict(monitor_projection["adopted_result_downstream_proof_projection"]),
    }


def _load_or_write_repeatability_checkpoint_receipt(
    *,
    receipt_id: str,
    request_id: str,
    checkpoint: Mapping[str, Any],
    checkpoint_hash: str,
    checkpoint_authority: Mapping[str, Any],
    checkpoint_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_repeatability_checkpoint_receipt(
            existing,
            request_id=request_id,
            receipt_id=receipt_id,
            checkpoint_hash=checkpoint_hash,
            checkpoint_authority_hash=checkpoint_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True
    _reject_competing_repeatability_checkpoint(root, receipt_id, checkpoint_authority_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_checkpoint_state": REPEATABILITY_CHECKPOINT_STATE,
        "repeatability_checkpoint_receipt_id": receipt_id,
        "repeatability_checkpoint": dict(checkpoint),
        "repeatability_checkpoint_hash": checkpoint_hash,
        "repeatability_checkpoint_authority": dict(checkpoint_authority),
        "repeatability_checkpoint_authority_hash": checkpoint_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_checkpoint_receipt": True,
        "exclusive_repeatability_checkpoint_per_authority": True,
        "workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "repeatability_checkpoint_receipt_mutation_admitted": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "process_control_admitted": False,
        "process_kill_cancel_retry_resume_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "default_scope_expansion_admitted": False,
        "raw_pid_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "next_allowed_actions": [
            "refresh Candidate B workflow history",
            "inspect workflow status and completion monitor projections",
            "use this receipt as post-monitor repeatability checkpoint evidence",
            "select corpus rerun, process control, provider, connector, RAG/model, or full mockup expansion only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "repeatability_checkpoint_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_repeatability_checkpoint(
    root: Path,
    receipt_id: str,
    checkpoint_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{REPEATABILITY_CHECKPOINT_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if existing.get("repeatability_checkpoint_authority_hash") == checkpoint_authority_hash:
            raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
                "candidate_b_full_corpus_operator_repeatability_checkpoint_conflict",
                "The selected Candidate B repeatability authority already has a checkpoint receipt.",
                http_status=409,
                details={"existing_repeatability_checkpoint_receipt_id": existing_id},
            )


def _validate_repeatability_checkpoint_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    receipt_id: str,
    checkpoint_hash: str,
    checkpoint_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_checkpoint_state": REPEATABILITY_CHECKPOINT_STATE,
        "repeatability_checkpoint_receipt_id": receipt_id,
        "repeatability_checkpoint_hash": checkpoint_hash,
        "repeatability_checkpoint_authority_hash": checkpoint_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_checkpoint_receipt": True,
        "exclusive_repeatability_checkpoint_per_authority": True,
        "workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "repeatability_checkpoint_receipt_mutation_admitted": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "process_control_admitted": False,
        "process_kill_cancel_retry_resume_admitted": False,
        "raw_pid_admitted": False,
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
        {
            key: value
            for key, value in receipt.items()
            if key not in {"repeatability_checkpoint_receipt_hash", "server_time"}
        }
    )
    if receipt.get("repeatability_checkpoint_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "repeatability_checkpoint_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("repeatability_checkpoint_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_idempotency_conflict",
            "The existing Candidate B repeatability-checkpoint receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _required_runbook_steps(fields: Mapping[str, Any]) -> list[str]:
    value = fields.get("operator_runbook_repeatability_steps")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_runbook_steps_missing",
            "Candidate B repeatability checkpoints require operator runbook repeatability steps.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS)},
        )
    steps = [str(step).strip() for step in value if str(step).strip()]
    if steps != list(REQUIRED_RUNBOOK_STEPS):
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_runbook_steps_invalid",
            "Candidate B repeatability-checkpoint runbook steps must match the admitted repeatability sequence.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS), "received_steps": steps},
        )
    _assert_no_raw_authority_exposure(steps)
    return steps


def _material_relative_name(status_projection: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    corpus = status_projection.get("corpus")
    if isinstance(corpus, Mapping) and str(corpus.get("material_relative_name") or "").strip():
        return str(corpus["material_relative_name"])
    return str(row.get("material_relative_name") or "")


def _workflow_receipt_root() -> Path:
    try:
        return workflow_progress_checkpoint._workflow_receipt_root()
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._read_json_receipt(path)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _assert_no_raw_authority_exposure(value: Any) -> None:
    try:
        workflow_status._assert_no_raw_authority_exposure(value)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            f"candidate_b_full_corpus_operator_repeatability_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_required_field_missing",
            "A required Candidate B repeatability-checkpoint field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64:
        raise CandidateBFullCorpusOperatorRepeatabilityCheckpointError(
            "candidate_b_full_corpus_operator_repeatability_checkpoint_hash_invalid",
            "A Candidate B repeatability-checkpoint hash field is invalid.",
            details={"field": key},
        )
    return value
