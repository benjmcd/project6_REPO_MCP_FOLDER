from __future__ import annotations

from typing import Any, Mapping

from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_completion_monitor.v1"
SCHEMA_VERSION = 1
COMPLETION_MONITOR_MODE = (
    "read_only_operator_workflow_completion_monitor_without_process_control_result_mutation_or_reexecution"
)
OPERATOR_DECISION = "inspect_candidate_b_async_operator_workflow_completion_monitor"
COMPLETION_MONITOR_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/monitor"
)
HISTORY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
COMPLETION_MONITOR_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "operator_workflow_receipt_id",
    "operator_workflow_receipt_hash",
    "row_hash",
    "authority_basis_hash",
    "history_hash",
    "completion_monitor_state",
    "process_execution_projection",
    "process_completion_result_projection",
    "adopted_result_downstream_proof_projection",
    "operator_projection",
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


class CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-completion-monitor-error",
            "server_time": workflow_status._server_time(),
            "mode": COMPLETION_MONITOR_MODE,
            "status": "blocked",
            "completion_monitor_state": "monitor_unavailable",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "completion_monitor_mode") != COMPLETION_MONITOR_MODE:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_mode_not_admitted",
            "Only the read-only Candidate B operator workflow completion-monitor mode is admitted.",
            details={"expected_completion_monitor_mode": COMPLETION_MONITOR_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_decision_not_admitted",
            "The operator decision does not match the admitted completion-monitor inspection.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    history = _current_history()
    row = _selected_history_row(history, fields)
    _validate_selected_authority(history, row, fields)
    _validate_optional_projection_bindings(row, fields)

    process_execution = _projection(row, "process_execution_projection")
    process_completion = _projection(row, "process_completion_result_projection")
    adopted_proof = _projection(row, "adopted_result_downstream_proof_projection")
    _reject_contradictory_projection_state(process_execution, process_completion, adopted_proof)
    monitor_state = _completion_monitor_state(process_execution, process_completion, adopted_proof)
    operator_projection = {
        "completion_monitor_visible": True,
        "read_only_completion_monitor_projection": True,
        "process_execution_projection_visible": True,
        "process_completion_result_projection_visible": True,
        "adopted_result_downstream_proof_projection_visible": True,
        "process_control_admitted": False,
        "process_kill_cancel_retry_resume_admitted": False,
        "process_completion_result_mutation_admitted": False,
        "process_execution_receipt_mutation_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "adopted_result_workflow_receipt_mutation_admitted": False,
        "downstream_proof_receipt_mutation_admitted": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "raw_pid_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "default_scope_expansion_admitted": False,
        "selector_mutation_performed": False,
    }
    monitor_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": COMPLETION_MONITOR_MODE,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "completion_monitor_state": monitor_state,
        "process_execution_projection": process_execution,
        "process_completion_result_projection": process_completion,
        "adopted_result_downstream_proof_projection": adopted_proof,
        "operator_projection": operator_projection,
    }
    monitor_hash = workflow_status._stable_hash(
        {key: monitor_input[key] for key in COMPLETION_MONITOR_HASH_KEYS}
    )
    return {
        **monitor_input,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "status": "available",
        "completion_monitor_hash": monitor_hash,
        "completion_monitor_ref": f"candidate-b-full-corpus-operator-workflow-completion-monitor://{monitor_hash[:24]}",
        "completion_monitor_endpoint": COMPLETION_MONITOR_ENDPOINT,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "read_only_completion_monitor_projection": True,
        "process_control_admitted": False,
        "process_kill_cancel_retry_resume_admitted": False,
        "process_completion_result_mutation_admitted": False,
        "process_execution_receipt_mutation_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "raw_pid_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "default_scope_expansion_admitted": False,
        "selector_mutation_performed": False,
        "negative_invariants": {
            "process_control_admitted": False,
            "receipt_mutation_admitted": False,
            "raw_pid_exposed": False,
            "raw_stdout_exposed": False,
            "raw_stderr_exposed": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "full_mockup_activation_enabled": False,
            "frontend_durable_authority_enabled": False,
            "default_scope_expansion_admitted": False,
        },
        "next_allowed_actions": [
            "refresh Candidate B workflow history to inspect the latest completion-monitor projection",
            "record process completion/result adoption only through the separately admitted endpoint",
            "record adopted-result downstream proof only through the separately admitted endpoint",
            "select process cancel, retry, resume, or broader runtime control only through a separate freeze",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_forbidden_request_fields",
            "Completion monitoring does not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, stdout, stderr, raw PIDs, or artifact bytes.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            f"candidate_b_full_corpus_operator_workflow_completion_monitor_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            f"candidate_b_full_corpus_operator_workflow_completion_monitor_{exc.code}",
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
            route_family="completion_monitor",
            rendered_surface="completion_monitor",
            requested_role=workflow_progress_checkpoint.workflow_access_policy.AUDITOR_ROLE,
        )
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            f"candidate_b_full_corpus_operator_workflow_completion_monitor_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_optional_projection_bindings(row: Mapping[str, Any], fields: Mapping[str, Any]) -> None:
    projections = (
        ("process_execution_projection", "process_execution_receipt_id", "process_execution_receipt_hash"),
        (
            "process_completion_result_projection",
            "process_completion_result_receipt_id",
            "process_completion_result_receipt_hash",
        ),
        (
            "adopted_result_downstream_proof_projection",
            "adopted_result_downstream_proof_receipt_id",
            "adopted_result_downstream_proof_receipt_hash",
        ),
    )
    mismatches: list[dict[str, Any]] = []
    for projection_key, id_key, hash_key in projections:
        projection = _projection(row, projection_key)
        for field_key in (id_key, hash_key):
            supplied = str(fields.get(field_key) or "")
            if supplied and supplied != str(projection.get(field_key) or ""):
                mismatches.append(
                    {"field": field_key, "expected": projection.get(field_key) or "", "received": supplied}
                )
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_stale_projection_binding",
            "The selected Candidate B completion-monitor projection binding is stale or contradictory.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _reject_contradictory_projection_state(
    process_execution: Mapping[str, Any],
    process_completion: Mapping[str, Any],
    adopted_proof: Mapping[str, Any],
) -> None:
    completion_state = str(process_completion.get("process_completion_result_projection_state") or "")
    adopted_state = str(adopted_proof.get("adopted_result_downstream_proof_projection_state") or "")
    if adopted_state == "proven" and completion_state != "completed":
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_contradictory_terminal_state",
            "An adopted-result downstream proof cannot be projected without a completed process result.",
            http_status=409,
            details={"process_completion_result_projection_state": completion_state, "adopted_result_downstream_proof_projection_state": adopted_state},
        )
    execution_state = str(process_execution.get("process_execution_projection_state") or "")
    if completion_state in {"completed", "failed", "blocked", "expired"} and execution_state != "started":
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_completion_without_started_process",
            "A terminal process-completion/result projection cannot exist without a started process-execution projection.",
            http_status=409,
            details={"process_execution_projection_state": execution_state, "process_completion_result_projection_state": completion_state},
        )


def _completion_monitor_state(
    process_execution: Mapping[str, Any],
    process_completion: Mapping[str, Any],
    adopted_proof: Mapping[str, Any],
) -> str:
    execution_state = str(process_execution.get("process_execution_projection_state") or "")
    completion_state = str(process_completion.get("process_completion_result_projection_state") or "")
    adopted_state = str(adopted_proof.get("adopted_result_downstream_proof_projection_state") or "")
    if execution_state == "not_started":
        return "not_started"
    if execution_state != "started":
        return "started_status_unknown"
    if completion_state == "not_recorded":
        return "started_running_or_unresolved"
    if completion_state in {"failed", "blocked", "expired"}:
        return completion_state
    if completion_state == "completed":
        if adopted_state == "proven":
            return "completed_downstream_proven"
        return "completed_result_adopted"
    return "started_status_unknown"


def _projection(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    projection = row.get(key)
    if not isinstance(projection, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_projection_missing",
            "The selected Candidate B history row is missing a required completion-monitor projection.",
            http_status=409,
            details={"projection": key},
        )
    return dict(projection)


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowCompletionMonitorError(
            "candidate_b_full_corpus_operator_workflow_completion_monitor_required_field_missing",
            "A required Candidate B completion-monitor field is missing or empty.",
            details={"field": key},
        )
    return value
