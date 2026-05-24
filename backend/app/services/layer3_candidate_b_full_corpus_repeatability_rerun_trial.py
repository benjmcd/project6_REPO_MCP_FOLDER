from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.services import (
    layer3_candidate_b_full_corpus_operator_repeatability_checkpoint as repeatability_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_completion_monitor as completion_monitor,
    layer3_candidate_b_full_corpus_operator_workflow_history as workflow_history,
    layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_repeatability_rerun_trial.v1"
SCHEMA_VERSION = 1
RERUN_TRIAL_MODE = (
    "append_only_repeatability_rerun_trial_receipt_without_process_execution_or_authority_mutation"
)
OPERATOR_DECISION = "record_candidate_b_full_corpus_repeatability_rerun_trial"
RERUN_TRIAL_STATE = "repeatability_rerun_trial_recorded"
RERUN_TRIAL_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-repeatability-rerun-trial"
RERUN_TRIAL_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial"
)
HISTORY_ENDPOINT = completion_monitor.HISTORY_ENDPOINT
STATUS_ENDPOINT = completion_monitor.STATUS_ENDPOINT
COMPLETION_MONITOR_ENDPOINT = completion_monitor.COMPLETION_MONITOR_ENDPOINT
REPEATABILITY_CHECKPOINT_ENDPOINT = repeatability_checkpoint.REPEATABILITY_CHECKPOINT_ENDPOINT
REQUIRED_RUNBOOK_STEPS = (
    "refresh_workflow_history",
    "inspect_original_checkpoint",
    "inspect_original_workflow_status",
    "inspect_original_completion_monitor",
    "inspect_rerun_workflow_status",
    "inspect_rerun_completion_monitor",
    "record_repeatability_rerun_trial",
)
ALLOWED_REGRESSION_DISPOSITIONS = {
    "no_regression_observed",
    "delta_reviewed_no_regression",
    "regression_detected_blocked",
}
_FORBIDDEN_REQUEST_FIELDS = repeatability_checkpoint._FORBIDDEN_REQUEST_FIELDS


class CandidateBFullCorpusRepeatabilityRerunTrialError(Exception):
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
            "request_id": "candidate-b-full-corpus-repeatability-rerun-trial-error",
            "server_time": workflow_status._server_time(),
            "mode": RERUN_TRIAL_MODE,
            "status": "blocked",
            "repeatability_rerun_trial_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_repeatability_rerun_trial(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "rerun_trial_mode") != RERUN_TRIAL_MODE:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_mode_not_admitted",
            "Only the append-only Candidate B repeatability rerun-trial mode is admitted.",
            details={"expected_rerun_trial_mode": RERUN_TRIAL_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_decision_not_admitted",
            "The operator decision does not match the admitted repeatability rerun-trial action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    runbook_steps = _required_runbook_steps(fields)
    regression_disposition = _required_regression_disposition(fields)
    history = _current_history()
    original = _validated_workflow_projection("original", history, fields)
    rerun = _validated_workflow_projection("rerun", history, fields)
    original_checkpoint = _validated_original_checkpoint(fields)
    _validate_original_checkpoint_binding(original_checkpoint, original, fields)
    comparison = _compare_workflow_projections(original, rerun, fields, regression_disposition)

    trial = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": RERUN_TRIAL_MODE,
        "original_repeatability_checkpoint_receipt_id": original_checkpoint[
            "repeatability_checkpoint_receipt_id"
        ],
        "original_repeatability_checkpoint_receipt_hash": original_checkpoint[
            "repeatability_checkpoint_receipt_hash"
        ],
        "original_repeatability_checkpoint_hash": original_checkpoint["repeatability_checkpoint_hash"],
        "original_repeatability_checkpoint_authority_hash": original_checkpoint[
            "repeatability_checkpoint_authority_hash"
        ],
        "original_operator_workflow_receipt_id": original["row"]["operator_workflow_receipt_id"],
        "original_operator_workflow_receipt_hash": original["row"]["operator_workflow_receipt_hash"],
        "original_row_hash": original["row"]["row_hash"],
        "original_authority_basis_hash": original["row"]["authority_basis_hash"],
        "original_history_hash": history["history_hash"],
        "original_workflow_status_hash": original["status"]["workflow_status_hash"],
        "original_completion_monitor_hash": original["monitor"]["completion_monitor_hash"],
        "rerun_operator_workflow_receipt_id": rerun["row"]["operator_workflow_receipt_id"],
        "rerun_operator_workflow_receipt_hash": rerun["row"]["operator_workflow_receipt_hash"],
        "rerun_row_hash": rerun["row"]["row_hash"],
        "rerun_authority_basis_hash": rerun["row"]["authority_basis_hash"],
        "rerun_history_hash": history["history_hash"],
        "rerun_workflow_status_hash": rerun["status"]["workflow_status_hash"],
        "rerun_completion_monitor_hash": rerun["monitor"]["completion_monitor_hash"],
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "original_candidate_b_run_id": _required(fields, "original_candidate_b_run_id"),
        "rerun_candidate_b_run_id": _required(fields, "rerun_candidate_b_run_id"),
        "compare_target_set_hash": _required_hash(fields, "compare_target_set_hash"),
        "material_relative_name": _required(fields, "material_relative_name"),
        "regression_disposition": regression_disposition,
        "operator_runbook_repeatability_steps": runbook_steps,
        "comparison": comparison,
        "original_status_projection": _status_trial_projection(original["status"]),
        "rerun_status_projection": _status_trial_projection(rerun["status"]),
        "original_completion_monitor_projection": _completion_monitor_trial_projection(original["monitor"]),
        "rerun_completion_monitor_projection": _completion_monitor_trial_projection(rerun["monitor"]),
    }
    trial_hash = workflow_status._stable_hash(trial)
    trial_authority = {
        **trial,
        "operator_decision": OPERATOR_DECISION,
        "repeatability_rerun_trial_hash": trial_hash,
    }
    trial_authority_hash = workflow_status._stable_hash(trial_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {"client_request_id": request_id, "repeatability_rerun_trial_authority_hash": trial_authority_hash}
    )
    receipt_id = f"{RERUN_TRIAL_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_rerun_trial_receipt(
        receipt_id=receipt_id,
        request_id=request_id,
        trial=trial,
        trial_hash=trial_hash,
        trial_authority=trial_authority,
        trial_authority_hash=trial_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_rerun_trial_receipt(
        receipt,
        request_id=request_id,
        receipt_id=receipt_id,
        trial_hash=trial_hash,
        trial_authority_hash=trial_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "repeatability_rerun_trial_receipt_hash": receipt_hash,
        "repeatability_rerun_trial_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-repeatability-rerun-trial://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "history_endpoint": HISTORY_ENDPOINT,
        "status_endpoint": STATUS_ENDPOINT,
        "completion_monitor_endpoint": COMPLETION_MONITOR_ENDPOINT,
        "repeatability_checkpoint_endpoint": REPEATABILITY_CHECKPOINT_ENDPOINT,
        "repeatability_rerun_trial_endpoint": RERUN_TRIAL_ENDPOINT,
        "original_status_request": dict(original["row"]["status_request"]),
        "rerun_status_request": dict(rerun["row"]["status_request"]),
        "history_request": {"method": "GET", "endpoint": HISTORY_ENDPOINT},
        "original_completion_monitor_request": original["monitor_request"],
        "rerun_completion_monitor_request": rerun["monitor_request"],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_forbidden_request_fields",
            "Repeatability rerun trials do not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, stdout, stderr, raw PIDs, or artifact bytes.",
            details={"blocked_fields": blocked},
        )
    return fields


def _current_history() -> dict[str, Any]:
    try:
        return workflow_history.candidate_b_full_corpus_operator_workflow_history()
    except workflow_history.CandidateBFullCorpusOperatorWorkflowHistoryError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validated_workflow_projection(
    prefix: str,
    history: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    selected_fields = _workflow_fields(prefix, fields)
    row = _selected_history_row(history, selected_fields)
    _validate_selected_authority(history, row, selected_fields, prefix=prefix)
    status_projection = _validated_status_projection(row, selected_fields, prefix=prefix)
    monitor_request = _completion_monitor_payload(row, history, prefix=prefix)
    monitor_projection = _validated_completion_monitor_projection(
        monitor_request,
        selected_fields,
        prefix=prefix,
    )
    return {
        "row": row,
        "status": status_projection,
        "monitor": monitor_projection,
        "monitor_request": monitor_request,
    }


def _workflow_fields(prefix: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "operator_workflow_receipt_id": _required(fields, f"{prefix}_operator_workflow_receipt_id"),
        "operator_workflow_receipt_hash": _required_hash(fields, f"{prefix}_operator_workflow_receipt_hash"),
        "row_hash": _required_hash(fields, f"{prefix}_row_hash"),
        "authority_basis_hash": _required_hash(fields, f"{prefix}_authority_basis_hash"),
        "history_hash": _required_hash(fields, f"{prefix}_history_hash"),
        "workflow_status_hash": _required_hash(fields, f"{prefix}_workflow_status_hash"),
        "completion_monitor_hash": _required_hash(fields, f"{prefix}_completion_monitor_hash"),
    }


def _selected_history_row(history: Mapping[str, Any], fields: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._selected_history_row(history, fields)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_selected_authority(
    history: Mapping[str, Any],
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
    *,
    prefix: str,
) -> None:
    try:
        workflow_progress_checkpoint._validate_selected_authority(
            history,
            row,
            fields,
            route_family="rerun_trial",
            rendered_surface="repeatability_rerun_trial",
        )
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_stale_{prefix}_authority",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validated_status_projection(
    row: Mapping[str, Any],
    fields: Mapping[str, Any],
    *,
    prefix: str,
) -> dict[str, Any]:
    status_request = row.get("status_request")
    if not isinstance(status_request, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{prefix}_status_request_missing",
            "Candidate B rerun trials require workflow-status requests in both selected history rows.",
            http_status=409,
        )
    try:
        status_projection = workflow_status.candidate_b_full_corpus_operator_workflow_status(status_request)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{prefix}_status_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    supplied_hash = fields["workflow_status_hash"]
    if status_projection.get("workflow_status_hash") != supplied_hash:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_stale_{prefix}_workflow_status",
            "A selected Candidate B workflow-status projection is stale or mismatched.",
            http_status=409,
            details={
                "expected_workflow_status_hash": status_projection.get("workflow_status_hash"),
                "received_workflow_status_hash": supplied_hash,
            },
        )
    if status_projection.get("workflow_status") != "proven":
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{prefix}_status_not_proven",
            "Candidate B repeatability rerun trials require proven original and rerun workflow status.",
            http_status=409,
            details={"workflow_status": status_projection.get("workflow_status")},
        )
    _assert_no_raw_authority_exposure(status_projection)
    return status_projection


def _completion_monitor_payload(
    row: Mapping[str, Any],
    history: Mapping[str, Any],
    *,
    prefix: str,
) -> dict[str, Any]:
    payload = repeatability_checkpoint._completion_monitor_payload(row, history)
    payload["client_request_id"] = f"candidate-b-rerun-trial-{prefix}-completion-monitor"
    return payload


def _validated_completion_monitor_projection(
    monitor_request: Mapping[str, Any],
    fields: Mapping[str, Any],
    *,
    prefix: str,
) -> dict[str, Any]:
    try:
        monitor_projection = completion_monitor.inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(
            monitor_request
        )
    except completion_monitor.CandidateBFullCorpusOperatorWorkflowCompletionMonitorError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{prefix}_completion_monitor_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    supplied_hash = fields["completion_monitor_hash"]
    if monitor_projection.get("completion_monitor_hash") != supplied_hash:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_stale_{prefix}_completion_monitor",
            "A selected Candidate B completion-monitor projection is stale or mismatched.",
            http_status=409,
            details={
                "expected_completion_monitor_hash": monitor_projection.get("completion_monitor_hash"),
                "received_completion_monitor_hash": supplied_hash,
            },
        )
    if monitor_projection.get("completion_monitor_state") != "completed_downstream_proven":
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{prefix}_monitor_not_downstream_proven",
            "Candidate B repeatability rerun trials require downstream-proven original and rerun completion monitors.",
            http_status=409,
            details={"completion_monitor_state": monitor_projection.get("completion_monitor_state")},
        )
    _assert_no_raw_authority_exposure(monitor_projection)
    return monitor_projection


def _validated_original_checkpoint(fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "original_repeatability_checkpoint_receipt_id")
    _validate_storage_id(receipt_id, prefix=repeatability_checkpoint.REPEATABILITY_CHECKPOINT_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_original_checkpoint_missing",
            "The original repeatability checkpoint receipt is missing from server-owned receipt authority.",
            http_status=404,
            details={"original_repeatability_checkpoint_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    expected_hash = workflow_status._stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"repeatability_checkpoint_receipt_hash", "server_time"}
        }
    )
    expected = {
        "schema_id": repeatability_checkpoint.SCHEMA_ID,
        "schema_version": repeatability_checkpoint.SCHEMA_VERSION,
        "mode": repeatability_checkpoint.REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": repeatability_checkpoint.OPERATOR_DECISION,
        "status": "available",
        "repeatability_checkpoint_state": repeatability_checkpoint.REPEATABILITY_CHECKPOINT_STATE,
        "repeatability_checkpoint_receipt_id": receipt_id,
        "repeatability_checkpoint_receipt_hash": _required_hash(
            fields,
            "original_repeatability_checkpoint_receipt_hash",
        ),
        "repeatability_checkpoint_hash": _required_hash(fields, "original_repeatability_checkpoint_hash"),
        "repeatability_checkpoint_authority_hash": _required_hash(
            fields,
            "original_repeatability_checkpoint_authority_hash",
        ),
        "append_only_repeatability_checkpoint_receipt": True,
        "exclusive_repeatability_checkpoint_per_authority": True,
    }
    mismatches = [
        {"field": key, "expected": value, "received": receipt.get(key)}
        for key, value in expected.items()
        if receipt.get(key) != value
    ]
    if receipt.get("repeatability_checkpoint_receipt_hash") != expected_hash:
        mismatches.append(
            {
                "field": "repeatability_checkpoint_receipt_hash",
                "expected": expected_hash,
                "received": receipt.get("repeatability_checkpoint_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_stale_original_checkpoint",
            "The original Candidate B repeatability checkpoint receipt is stale or mismatched.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    checkpoint = receipt.get("repeatability_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_original_checkpoint_invalid",
            "The original repeatability checkpoint receipt is missing checkpoint authority.",
            http_status=409,
        )
    return dict(receipt)


def _validate_original_checkpoint_binding(
    original_checkpoint: Mapping[str, Any],
    original: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> None:
    checkpoint = original_checkpoint.get("repeatability_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_original_checkpoint_invalid",
            "The original repeatability checkpoint receipt is missing checkpoint authority.",
            http_status=409,
        )
    row = original["row"]
    status = original["status"]
    monitor = original["monitor"]
    expected = {
        "operator_workflow_receipt_id": row.get("operator_workflow_receipt_id"),
        "operator_workflow_receipt_hash": row.get("operator_workflow_receipt_hash"),
        "row_hash": row.get("row_hash"),
        "authority_basis_hash": row.get("authority_basis_hash"),
        "history_hash": _required(fields, "original_history_hash"),
        "workflow_status_hash": status.get("workflow_status_hash"),
        "completion_monitor_hash": monitor.get("completion_monitor_hash"),
        "completion_monitor_state": "completed_downstream_proven",
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "candidate_b_run_id": _required(fields, "original_candidate_b_run_id"),
        "compare_target_set_hash": _required_hash(fields, "compare_target_set_hash"),
        "material_relative_name": _required(fields, "material_relative_name"),
    }
    mismatches = [
        {"field": key, "expected": value, "received": checkpoint.get(key)}
        for key, value in expected.items()
        if checkpoint.get(key) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_stale_original_checkpoint_binding",
            "The original Candidate B repeatability checkpoint no longer binds the selected original workflow authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _compare_workflow_projections(
    original: Mapping[str, Any],
    rerun: Mapping[str, Any],
    fields: Mapping[str, Any],
    regression_disposition: str,
) -> dict[str, Any]:
    original_status = original["status"]
    rerun_status = rerun["status"]
    required_matches = {
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "compare_target_set_hash": _required_hash(fields, "compare_target_set_hash"),
        "material_relative_name": _required(fields, "material_relative_name"),
    }
    mismatches = []
    for key, expected in required_matches.items():
        for label, status_projection in (("original", original_status), ("rerun", rerun_status)):
            received = _status_field(status_projection, key)
            if received != expected:
                mismatches.append(
                    {"field": f"{label}_{key}", "expected": expected, "received": received}
                )
    original_candidate_b = _required(fields, "original_candidate_b_run_id")
    rerun_candidate_b = _required(fields, "rerun_candidate_b_run_id")
    if original_status.get("candidate_b_run_id") != original_candidate_b:
        mismatches.append(
            {
                "field": "original_candidate_b_run_id",
                "expected": original_status.get("candidate_b_run_id"),
                "received": original_candidate_b,
            }
        )
    if rerun_status.get("candidate_b_run_id") != rerun_candidate_b:
        mismatches.append(
            {
                "field": "rerun_candidate_b_run_id",
                "expected": rerun_status.get("candidate_b_run_id"),
                "received": rerun_candidate_b,
            }
        )
    original_corpus_identity_hash = _corpus_identity_hash(original_status)
    rerun_corpus_identity_hash = _corpus_identity_hash(rerun_status)
    same_candidate_b_run_id = original_candidate_b == rerun_candidate_b
    same_corpus_identity = original_corpus_identity_hash == rerun_corpus_identity_hash
    if not same_candidate_b_run_id and not same_corpus_identity:
        mismatches.append(
            {
                "field": "eligible_corpus_identity",
                "expected": original_corpus_identity_hash,
                "received": rerun_corpus_identity_hash,
            }
        )
    original_runtime_policy_hash = _runtime_root_lifecycle_policy_hash(original_status)
    rerun_runtime_policy_hash = _runtime_root_lifecycle_policy_hash(rerun_status)
    if original_runtime_policy_hash != rerun_runtime_policy_hash:
        mismatches.append(
            {
                "field": "runtime_root_lifecycle_policy_hash",
                "expected": original_runtime_policy_hash,
                "received": rerun_runtime_policy_hash,
            }
        )
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_mismatched_corpus_identity",
            "Candidate B repeatability rerun trials require matching corpus identity, compare target set, material name, baseline/Candidate A linkage, and runtime-root lifecycle policy.",
            http_status=409,
            details={"mismatches": mismatches},
        )

    artifact_hash_equal = _artifact_family_hash(original_status) == _artifact_family_hash(rerun_status)
    layer3_projection_hash_equal = _layer3_projection_hash(original_status) == _layer3_projection_hash(rerun_status)
    role_counts_equal = _role_counts_hash(original_status) == _role_counts_hash(rerun_status)
    delta_observed = not (artifact_hash_equal and layer3_projection_hash_equal and role_counts_equal)
    if delta_observed and regression_disposition == "no_regression_observed":
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_delta_disposition_required",
            "Candidate B repeatability rerun trials require an explicit delta or regression disposition when compared projections differ.",
            http_status=409,
            details={
                "artifact_family_hash_equal": artifact_hash_equal,
                "layer3_downstream_projection_hash_equal": layer3_projection_hash_equal,
                "retained_artifact_role_counts_equal": role_counts_equal,
                "allowed_regression_dispositions": sorted(ALLOWED_REGRESSION_DISPOSITIONS),
            },
        )
    return {
        "same_candidate_b_run_id": same_candidate_b_run_id,
        "same_eligible_corpus_identity": same_corpus_identity,
        "original_corpus_identity_hash": original_corpus_identity_hash,
        "rerun_corpus_identity_hash": rerun_corpus_identity_hash,
        "same_compare_target_set_hash": True,
        "same_material_relative_name": True,
        "same_runtime_root_lifecycle_policy": True,
        "original_runtime_root_lifecycle_policy_hash": original_runtime_policy_hash,
        "rerun_runtime_root_lifecycle_policy_hash": rerun_runtime_policy_hash,
        "artifact_family_hash_comparison": {
            "original_hash": _artifact_family_hash(original_status),
            "rerun_hash": _artifact_family_hash(rerun_status),
            "equal": artifact_hash_equal,
        },
        "layer3_downstream_projection_comparison": {
            "original_hash": _layer3_projection_hash(original_status),
            "rerun_hash": _layer3_projection_hash(rerun_status),
            "equal": layer3_projection_hash_equal,
        },
        "retained_artifact_role_counts_comparison": {
            "original_hash": _role_counts_hash(original_status),
            "rerun_hash": _role_counts_hash(rerun_status),
            "equal": role_counts_equal,
        },
        "delta_observed": delta_observed,
        "regression_disposition": regression_disposition,
    }


def _status_field(status_projection: Mapping[str, Any], key: str) -> str:
    if key == "material_relative_name":
        return _material_relative_name(status_projection)
    return str(status_projection.get(key) or "")


def _material_relative_name(status_projection: Mapping[str, Any]) -> str:
    corpus = status_projection.get("corpus")
    if isinstance(corpus, Mapping) and str(corpus.get("material_relative_name") or "").strip():
        return str(corpus["material_relative_name"])
    return str(status_projection.get("material_relative_name") or "")


def _corpus_identity_hash(status_projection: Mapping[str, Any]) -> str:
    corpus = status_projection.get("corpus")
    if not isinstance(corpus, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_corpus_identity_missing",
            "Candidate B repeatability rerun trials require corpus identity projections.",
            http_status=409,
        )
    identity = {
        "corpus_pdf_count": corpus.get("corpus_pdf_count"),
        "eligible_file_count": corpus.get("eligible_file_count"),
        "material_relative_name": corpus.get("material_relative_name"),
        "target_status_counts": corpus.get("target_status_counts") or {},
        "eligibility_summary": corpus.get("eligibility_summary") or {},
    }
    return workflow_status._stable_hash(identity)


def _runtime_root_lifecycle_policy_hash(status_projection: Mapping[str, Any]) -> str:
    lifecycle = status_projection.get("runtime_root_lifecycle")
    if not isinstance(lifecycle, Mapping) or lifecycle.get("available") is not True:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_runtime_root_lifecycle_missing",
            "Candidate B repeatability rerun trials require runtime-root lifecycle policy projections.",
            http_status=409,
        )
    policy = {
        key: value
        for key, value in lifecycle.items()
        if key not in {"lifecycle_receipt_id", "lifecycle_receipt_hash", "runtime_parent_ref"}
    }
    return workflow_status._stable_hash(policy)


def _artifact_family_hash(status_projection: Mapping[str, Any]) -> str:
    artifact_family = status_projection.get("artifact_family")
    if not isinstance(artifact_family, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_artifact_family_missing",
            "Candidate B repeatability rerun trials require artifact-family projections.",
            http_status=409,
        )
    supplied = str(artifact_family.get("governed_retained_artifact_family_hash") or "")
    return supplied or workflow_status._stable_hash(dict(artifact_family))


def _layer3_projection_hash(status_projection: Mapping[str, Any]) -> str:
    layer3 = status_projection.get("layer3")
    if not isinstance(layer3, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_layer3_projection_missing",
            "Candidate B repeatability rerun trials require Layer 3 downstream projections.",
            http_status=409,
        )
    return workflow_status._stable_hash(dict(layer3))


def _role_counts_hash(status_projection: Mapping[str, Any]) -> str:
    artifact_family = status_projection.get("artifact_family")
    role_counts = artifact_family.get("role_counts") if isinstance(artifact_family, Mapping) else None
    if not isinstance(role_counts, Mapping):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_role_counts_missing",
            "Candidate B repeatability rerun trials require retained artifact role-count projections.",
            http_status=409,
        )
    return workflow_status._stable_hash(dict(role_counts))


def _status_trial_projection(status_projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "workflow_status": status_projection["workflow_status"],
        "workflow_status_hash": status_projection["workflow_status_hash"],
        "workflow_receipt_id": status_projection["workflow_receipt_id"],
        "workflow_receipt_hash": status_projection["workflow_receipt_hash"],
        "baseline_run_id": status_projection["baseline_run_id"],
        "candidate_a_run_id": status_projection["candidate_a_run_id"],
        "candidate_b_run_id": status_projection["candidate_b_run_id"],
        "compare_target_set_hash": status_projection["compare_target_set_hash"],
        "corpus": dict(status_projection.get("corpus") or {}),
        "runtime_root_lifecycle": dict(status_projection["runtime_root_lifecycle"]),
        "artifact_family": dict(status_projection.get("artifact_family") or {}),
        "layer3": dict(status_projection.get("layer3") or {}),
        "baseline_rollback": dict(status_projection.get("baseline_rollback") or {}),
    }


def _completion_monitor_trial_projection(monitor_projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "completion_monitor_state": monitor_projection["completion_monitor_state"],
        "completion_monitor_hash": monitor_projection["completion_monitor_hash"],
        "process_execution_projection": dict(monitor_projection["process_execution_projection"]),
        "process_completion_result_projection": dict(monitor_projection["process_completion_result_projection"]),
        "adopted_result_downstream_proof_projection": dict(
            monitor_projection["adopted_result_downstream_proof_projection"]
        ),
    }


def _load_or_write_rerun_trial_receipt(
    *,
    receipt_id: str,
    request_id: str,
    trial: Mapping[str, Any],
    trial_hash: str,
    trial_authority: Mapping[str, Any],
    trial_authority_hash: str,
    idempotency_key_hash: str,
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_rerun_trial_receipt(
            existing,
            request_id=request_id,
            receipt_id=receipt_id,
            trial_hash=trial_hash,
            trial_authority_hash=trial_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True
    _reject_competing_rerun_trial(root, receipt_id, trial_authority_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": RERUN_TRIAL_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_rerun_trial_state": RERUN_TRIAL_STATE,
        "repeatability_rerun_trial_receipt_id": receipt_id,
        "repeatability_rerun_trial": dict(trial),
        "repeatability_rerun_trial_hash": trial_hash,
        "repeatability_rerun_trial_authority": dict(trial_authority),
        "repeatability_rerun_trial_authority_hash": trial_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_rerun_trial_receipt": True,
        "exclusive_repeatability_rerun_trial_per_authority": True,
        "original_repeatability_checkpoint_receipt_mutated": False,
        "original_workflow_receipt_mutated": False,
        "rerun_workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "repeatability_rerun_trial_receipt_mutation_admitted": False,
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
            "inspect original and rerun workflow status plus completion-monitor projections",
            "use this receipt as Candidate B full-corpus repeatability rerun-trial evidence",
            "select rendered rerun-trial controls, process control, provider, connector, RAG/model, or full mockup expansion only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "repeatability_rerun_trial_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_rerun_trial(
    root: Path,
    receipt_id: str,
    trial_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{RERUN_TRIAL_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if existing.get("repeatability_rerun_trial_authority_hash") == trial_authority_hash:
            raise CandidateBFullCorpusRepeatabilityRerunTrialError(
                "candidate_b_full_corpus_repeatability_rerun_trial_conflict",
                "The selected Candidate B rerun-trial authority already has a receipt.",
                http_status=409,
                details={"existing_repeatability_rerun_trial_receipt_id": existing_id},
            )


def _validate_rerun_trial_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    receipt_id: str,
    trial_hash: str,
    trial_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": RERUN_TRIAL_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_rerun_trial_state": RERUN_TRIAL_STATE,
        "repeatability_rerun_trial_receipt_id": receipt_id,
        "repeatability_rerun_trial_hash": trial_hash,
        "repeatability_rerun_trial_authority_hash": trial_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_rerun_trial_receipt": True,
        "exclusive_repeatability_rerun_trial_per_authority": True,
        "original_repeatability_checkpoint_receipt_mutated": False,
        "original_workflow_receipt_mutated": False,
        "rerun_workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "repeatability_rerun_trial_receipt_mutation_admitted": False,
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
            if key not in {"repeatability_rerun_trial_receipt_hash", "server_time"}
        }
    )
    if receipt.get("repeatability_rerun_trial_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "repeatability_rerun_trial_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("repeatability_rerun_trial_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_idempotency_conflict",
            "The existing Candidate B repeatability rerun-trial receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _required_runbook_steps(fields: Mapping[str, Any]) -> list[str]:
    value = fields.get("operator_runbook_repeatability_steps")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_runbook_steps_missing",
            "Candidate B repeatability rerun trials require operator runbook repeatability steps.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS)},
        )
    steps = [str(step).strip() for step in value if str(step).strip()]
    if steps != list(REQUIRED_RUNBOOK_STEPS):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_runbook_steps_invalid",
            "Candidate B repeatability rerun-trial runbook steps must match the admitted rerun sequence.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS), "received_steps": steps},
        )
    _assert_no_raw_authority_exposure(steps)
    return steps


def _required_regression_disposition(fields: Mapping[str, Any]) -> str:
    value = _required(fields, "regression_disposition")
    if value not in ALLOWED_REGRESSION_DISPOSITIONS:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_regression_disposition_invalid",
            "Candidate B repeatability rerun trials require an admitted regression or delta disposition.",
            details={
                "allowed_regression_dispositions": sorted(ALLOWED_REGRESSION_DISPOSITIONS),
                "received_regression_disposition": value,
            },
        )
    return value


def _workflow_receipt_root() -> Path:
    try:
        return workflow_progress_checkpoint._workflow_receipt_root()
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        return workflow_progress_checkpoint._read_json_receipt(path)
    except workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        workflow_status._validate_storage_id(value, prefix=prefix)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_storage_id_invalid",
            "Candidate B repeatability rerun-trial identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_required_field_missing",
            "A required Candidate B repeatability rerun-trial field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            "candidate_b_full_corpus_repeatability_rerun_trial_hash_invalid",
            "Candidate B repeatability rerun-trial hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _assert_no_raw_authority_exposure(value: Any) -> None:
    try:
        workflow_status._assert_no_raw_authority_exposure(value)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusRepeatabilityRerunTrialError(
            f"candidate_b_full_corpus_repeatability_rerun_trial_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
