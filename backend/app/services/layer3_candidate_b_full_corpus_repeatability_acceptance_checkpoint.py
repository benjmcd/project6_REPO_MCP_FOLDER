from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.services import (
    layer3_candidate_b_operator_workflow_access_policy as workflow_access_policy,
    layer3_candidate_b_full_corpus_operator_repeatability_checkpoint as repeatability_checkpoint,
    layer3_candidate_b_full_corpus_repeatability_rerun_trial as rerun_trial,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_repeatability_acceptance_checkpoint.v1"
SCHEMA_VERSION = 1
ACCEPTANCE_CHECKPOINT_MODE = (
    "append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation"
)
OPERATOR_DECISION = "record_candidate_b_full_corpus_repeatability_acceptance_checkpoint"
ACCEPTANCE_CHECKPOINT_STATE = "repeatability_acceptance_checkpoint_recorded"
ACCEPTANCE_CHECKPOINT_RECEIPT_PREFIX = (
    f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-repeatability-acceptance-checkpoint"
)
ACCEPTANCE_CHECKPOINT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint"
)
REPEATABILITY_CHECKPOINT_ENDPOINT = repeatability_checkpoint.REPEATABILITY_CHECKPOINT_ENDPOINT
RERUN_TRIAL_ENDPOINT = rerun_trial.RERUN_TRIAL_ENDPOINT
ACCEPTED_DISPOSITIONS = {
    "no_regression_observed",
    "delta_reviewed_no_regression",
}
BLOCKED_DISPOSITION = "regression_detected_blocked"
REQUIRED_RUNBOOK_STEPS = (
    "inspect_original_repeatability_checkpoint",
    "inspect_repeatability_rerun_trial",
    "review_rerun_trial_comparison",
    "record_repeatability_acceptance_checkpoint",
)
_FORBIDDEN_REQUEST_FIELDS = rerun_trial._FORBIDDEN_REQUEST_FIELDS


class CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(Exception):
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
            "request_id": "candidate-b-full-corpus-repeatability-acceptance-checkpoint-error",
            "server_time": workflow_status._server_time(),
            "mode": ACCEPTANCE_CHECKPOINT_MODE,
            "status": "blocked",
            "repeatability_acceptance_checkpoint_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "acceptance_checkpoint_mode") != ACCEPTANCE_CHECKPOINT_MODE:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_mode_not_admitted",
            "Only the append-only Candidate B repeatability acceptance-checkpoint mode is admitted.",
            details={"expected_acceptance_checkpoint_mode": ACCEPTANCE_CHECKPOINT_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_decision_not_admitted",
            "The operator decision does not match the admitted acceptance-checkpoint action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    runbook_steps = _required_runbook_steps(fields)
    acceptance_disposition = _required_acceptance_disposition(fields)
    rerun_receipt = _validated_rerun_trial_receipt(fields)
    trial = _rerun_trial_body(rerun_receipt)
    original = _validated_workflow_projection("original", trial)
    rerun = _validated_workflow_projection("rerun", trial)
    _authorize_acceptance_workflow_rows(fields, original, rerun)
    original_checkpoint = _validated_original_checkpoint(fields, trial)
    rerun_trial._validate_original_checkpoint_binding(original_checkpoint, original, trial)
    _validate_rerun_trial_binding(rerun_receipt, trial, fields, original, rerun)
    comparison = _validated_acceptance_comparison(trial, acceptance_disposition)

    checkpoint = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": ACCEPTANCE_CHECKPOINT_MODE,
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
        "repeatability_rerun_trial_receipt_id": rerun_receipt["repeatability_rerun_trial_receipt_id"],
        "repeatability_rerun_trial_receipt_hash": rerun_receipt["repeatability_rerun_trial_receipt_hash"],
        "repeatability_rerun_trial_hash": rerun_receipt["repeatability_rerun_trial_hash"],
        "repeatability_rerun_trial_authority_hash": rerun_receipt[
            "repeatability_rerun_trial_authority_hash"
        ],
        "original_operator_workflow_receipt_id": trial["original_operator_workflow_receipt_id"],
        "rerun_operator_workflow_receipt_id": trial["rerun_operator_workflow_receipt_id"],
        "baseline_run_id": trial["baseline_run_id"],
        "candidate_a_run_id": trial["candidate_a_run_id"],
        "original_candidate_b_run_id": trial["original_candidate_b_run_id"],
        "rerun_candidate_b_run_id": trial["rerun_candidate_b_run_id"],
        "compare_target_set_hash": trial["compare_target_set_hash"],
        "material_relative_name": trial["material_relative_name"],
        "acceptance_disposition": acceptance_disposition,
        "operator_acceptance_decision": _required(fields, "operator_acceptance_decision"),
        "operator_runbook_repeatability_steps": runbook_steps,
        "comparison": comparison,
        "original_status_projection": rerun_trial._status_trial_projection(original["status"]),
        "rerun_status_projection": rerun_trial._status_trial_projection(rerun["status"]),
        "original_completion_monitor_projection": rerun_trial._completion_monitor_trial_projection(
            original["monitor"]
        ),
        "rerun_completion_monitor_projection": rerun_trial._completion_monitor_trial_projection(
            rerun["monitor"]
        ),
    }
    checkpoint_hash = workflow_status._stable_hash(checkpoint)
    checkpoint_authority = {
        **checkpoint,
        "operator_decision": OPERATOR_DECISION,
        "repeatability_acceptance_checkpoint_hash": checkpoint_hash,
    }
    checkpoint_authority_hash = workflow_status._stable_hash(checkpoint_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "repeatability_acceptance_checkpoint_authority_hash": checkpoint_authority_hash,
        }
    )
    receipt_id = f"{ACCEPTANCE_CHECKPOINT_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_acceptance_checkpoint_receipt(
        receipt_id=receipt_id,
        request_id=request_id,
        checkpoint=checkpoint,
        checkpoint_hash=checkpoint_hash,
        checkpoint_authority=checkpoint_authority,
        checkpoint_authority_hash=checkpoint_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    receipt_hash = _validate_acceptance_checkpoint_receipt(
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
        "repeatability_acceptance_checkpoint_receipt_hash": receipt_hash,
        "repeatability_acceptance_checkpoint_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-repeatability-acceptance-checkpoint://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "repeatability_checkpoint_endpoint": REPEATABILITY_CHECKPOINT_ENDPOINT,
        "repeatability_rerun_trial_endpoint": RERUN_TRIAL_ENDPOINT,
        "repeatability_acceptance_checkpoint_endpoint": ACCEPTANCE_CHECKPOINT_ENDPOINT,
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_forbidden_request_fields",
            "Repeatability acceptance checkpoints do not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, stdout, stderr, raw PIDs, or artifact bytes.",
            details={"blocked_fields": blocked},
        )
    return fields


def _validated_rerun_trial_receipt(fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "repeatability_rerun_trial_receipt_id")
    _validate_storage_id(receipt_id, prefix=rerun_trial.RERUN_TRIAL_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_rerun_trial_missing",
            "The Candidate B repeatability rerun-trial receipt is missing from server-owned authority.",
            http_status=404,
            details={"repeatability_rerun_trial_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    expected_hash = workflow_status._stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"repeatability_rerun_trial_receipt_hash", "server_time"}
        }
    )
    expected = {
        "schema_id": rerun_trial.SCHEMA_ID,
        "schema_version": rerun_trial.SCHEMA_VERSION,
        "mode": rerun_trial.RERUN_TRIAL_MODE,
        "operator_decision": rerun_trial.OPERATOR_DECISION,
        "status": "available",
        "repeatability_rerun_trial_state": rerun_trial.RERUN_TRIAL_STATE,
        "repeatability_rerun_trial_receipt_id": receipt_id,
        "repeatability_rerun_trial_receipt_hash": _required_hash(
            fields,
            "repeatability_rerun_trial_receipt_hash",
        ),
        "repeatability_rerun_trial_hash": _required_hash(fields, "repeatability_rerun_trial_hash"),
        "repeatability_rerun_trial_authority_hash": _required_hash(
            fields,
            "repeatability_rerun_trial_authority_hash",
        ),
        "append_only_repeatability_rerun_trial_receipt": True,
        "exclusive_repeatability_rerun_trial_per_authority": True,
    }
    mismatches = [
        {"field": key, "expected": value, "received": receipt.get(key)}
        for key, value in expected.items()
        if receipt.get(key) != value
    ]
    if receipt.get("repeatability_rerun_trial_receipt_hash") != expected_hash:
        mismatches.append(
            {
                "field": "repeatability_rerun_trial_receipt_hash",
                "expected": expected_hash,
                "received": receipt.get("repeatability_rerun_trial_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_stale_rerun_trial",
            "The Candidate B repeatability rerun-trial receipt is stale or mismatched.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return dict(receipt)


def _rerun_trial_body(rerun_receipt: Mapping[str, Any]) -> dict[str, Any]:
    trial = rerun_receipt.get("repeatability_rerun_trial")
    if not isinstance(trial, Mapping):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_rerun_trial_invalid",
            "The Candidate B rerun-trial receipt is missing trial authority.",
            http_status=409,
        )
    return dict(trial)


def _validated_workflow_projection(prefix: str, trial: Mapping[str, Any]) -> dict[str, Any]:
    try:
        history = rerun_trial._current_history()
        return rerun_trial._validated_workflow_projection(prefix, history, trial)
    except rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            f"candidate_b_full_corpus_repeatability_acceptance_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validated_original_checkpoint(
    fields: Mapping[str, Any],
    trial: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint_fields = {
        "original_repeatability_checkpoint_receipt_id": _required(
            fields,
            "original_repeatability_checkpoint_receipt_id",
        ),
        "original_repeatability_checkpoint_receipt_hash": _required_hash(
            fields,
            "original_repeatability_checkpoint_receipt_hash",
        ),
        "original_repeatability_checkpoint_hash": _required_hash(
            fields,
            "original_repeatability_checkpoint_hash",
        ),
        "original_repeatability_checkpoint_authority_hash": _required_hash(
            fields,
            "original_repeatability_checkpoint_authority_hash",
        ),
    }
    expected = {
        key: trial[key]
        for key in checkpoint_fields
        if key in trial
    }
    mismatches = [
        {"field": key, "expected": value, "received": checkpoint_fields.get(key)}
        for key, value in expected.items()
        if checkpoint_fields.get(key) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_stale_original_checkpoint",
            "The submitted original repeatability checkpoint does not match the rerun-trial authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    try:
        return rerun_trial._validated_original_checkpoint(checkpoint_fields)
    except rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            f"candidate_b_full_corpus_repeatability_acceptance_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_rerun_trial_binding(
    rerun_receipt: Mapping[str, Any],
    trial: Mapping[str, Any],
    fields: Mapping[str, Any],
    original: Mapping[str, Any],
    rerun: Mapping[str, Any],
) -> None:
    expected = {
        "repeatability_rerun_trial_receipt_id": rerun_receipt["repeatability_rerun_trial_receipt_id"],
        "repeatability_rerun_trial_receipt_hash": rerun_receipt[
            "repeatability_rerun_trial_receipt_hash"
        ],
        "repeatability_rerun_trial_hash": rerun_receipt["repeatability_rerun_trial_hash"],
        "repeatability_rerun_trial_authority_hash": rerun_receipt[
            "repeatability_rerun_trial_authority_hash"
        ],
        "original_workflow_status_hash": original["status"]["workflow_status_hash"],
        "original_completion_monitor_hash": original["monitor"]["completion_monitor_hash"],
        "rerun_workflow_status_hash": rerun["status"]["workflow_status_hash"],
        "rerun_completion_monitor_hash": rerun["monitor"]["completion_monitor_hash"],
    }
    mismatches = [
        {"field": key, "expected": value, "received": fields.get(key) or trial.get(key)}
        for key, value in expected.items()
        if (fields.get(key) or trial.get(key)) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_stale_authority",
            "The Candidate B repeatability acceptance authority is stale or mismatched.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _validated_acceptance_comparison(
    trial: Mapping[str, Any],
    acceptance_disposition: str,
) -> dict[str, Any]:
    comparison = trial.get("comparison")
    if not isinstance(comparison, Mapping):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_comparison_missing",
            "Candidate B repeatability acceptance requires a rerun-trial comparison summary.",
            http_status=409,
        )
    trial_disposition = str(comparison.get("regression_disposition") or trial.get("regression_disposition") or "")
    if trial_disposition != acceptance_disposition:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_disposition_mismatch",
            "The acceptance disposition must match the recorded rerun-trial disposition.",
            http_status=409,
            details={
                "rerun_trial_regression_disposition": trial_disposition,
                "acceptance_disposition": acceptance_disposition,
            },
        )
    if acceptance_disposition == BLOCKED_DISPOSITION:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_regression_detected",
            "A detected Candidate B repeatability regression blocks acceptance.",
            http_status=409,
            details={"blocked_disposition": BLOCKED_DISPOSITION},
        )
    if acceptance_disposition == "no_regression_observed" and comparison.get("delta_observed") is True:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_delta_review_required",
            "Observed Candidate B repeatability deltas require explicit delta-reviewed acceptance.",
            http_status=409,
        )
    required_true = (
        "same_compare_target_set_hash",
        "same_material_relative_name",
        "same_runtime_root_lifecycle_policy",
    )
    missing = [field for field in required_true if comparison.get(field) is not True]
    if missing:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_comparison_not_acceptable",
            "Candidate B repeatability acceptance requires matching compare target, material, and runtime-root policy.",
            http_status=409,
            details={"missing_true_comparison_fields": missing},
        )
    return dict(comparison)


def _authorize_acceptance_workflow_rows(
    fields: Mapping[str, Any],
    original: Mapping[str, Any],
    rerun: Mapping[str, Any],
) -> None:
    for label, projection in (("original", original), ("rerun", rerun)):
        row = projection.get("row")
        if not isinstance(row, Mapping):
            raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
                f"candidate_b_full_corpus_repeatability_acceptance_checkpoint_{label}_row_missing",
                "Acceptance checkpoint policy requires original and rerun workflow-row authority.",
                http_status=409,
            )
        workflow_access_policy.authorize_history_row_access(
            fields=fields,
            row=row,
            route_family="acceptance_checkpoint",
            rendered_surface=f"acceptance_checkpoint_{label}",
            requested_role=workflow_access_policy.OWNER_ROLE,
        )


def _load_or_write_acceptance_checkpoint_receipt(
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
        _validate_acceptance_checkpoint_receipt(
            existing,
            request_id=request_id,
            receipt_id=receipt_id,
            checkpoint_hash=checkpoint_hash,
            checkpoint_authority_hash=checkpoint_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True
    _reject_competing_acceptance_checkpoint(root, receipt_id, checkpoint_authority_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": ACCEPTANCE_CHECKPOINT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_acceptance_checkpoint_state": ACCEPTANCE_CHECKPOINT_STATE,
        "repeatability_acceptance_checkpoint_receipt_id": receipt_id,
        "repeatability_acceptance_checkpoint": dict(checkpoint),
        "repeatability_acceptance_checkpoint_hash": checkpoint_hash,
        "repeatability_acceptance_checkpoint_authority": dict(checkpoint_authority),
        "repeatability_acceptance_checkpoint_authority_hash": checkpoint_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_acceptance_checkpoint_receipt": True,
        "exclusive_repeatability_acceptance_checkpoint_per_authority": True,
        "original_repeatability_checkpoint_receipt_mutated": False,
        "repeatability_rerun_trial_receipt_mutated": False,
        "original_workflow_receipt_mutated": False,
        "rerun_workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "repeatability_acceptance_checkpoint_receipt_mutation_admitted": False,
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
            "use this receipt as Candidate B full-corpus repeatability acceptance evidence",
            "select rendered acceptance controls, broader default scope, provider, connector, RAG/model, or full mockup expansion only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "repeatability_acceptance_checkpoint_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_acceptance_checkpoint(
    root: Path,
    receipt_id: str,
    checkpoint_authority_hash: str,
) -> None:
    for receipt_file in sorted(root.glob(f"{ACCEPTANCE_CHECKPOINT_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if existing.get("repeatability_acceptance_checkpoint_authority_hash") == checkpoint_authority_hash:
            raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
                "candidate_b_full_corpus_repeatability_acceptance_checkpoint_conflict",
                "The selected Candidate B repeatability acceptance authority already has a checkpoint receipt.",
                http_status=409,
                details={"existing_repeatability_acceptance_checkpoint_receipt_id": existing_id},
            )


def _validate_acceptance_checkpoint_receipt(
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
        "mode": ACCEPTANCE_CHECKPOINT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_acceptance_checkpoint_state": ACCEPTANCE_CHECKPOINT_STATE,
        "repeatability_acceptance_checkpoint_receipt_id": receipt_id,
        "repeatability_acceptance_checkpoint_hash": checkpoint_hash,
        "repeatability_acceptance_checkpoint_authority_hash": checkpoint_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_acceptance_checkpoint_receipt": True,
        "exclusive_repeatability_acceptance_checkpoint_per_authority": True,
        "original_repeatability_checkpoint_receipt_mutated": False,
        "repeatability_rerun_trial_receipt_mutated": False,
        "original_workflow_receipt_mutated": False,
        "rerun_workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "repeatability_acceptance_checkpoint_receipt_mutation_admitted": False,
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
            if key not in {"repeatability_acceptance_checkpoint_receipt_hash", "server_time"}
        }
    )
    if receipt.get("repeatability_acceptance_checkpoint_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "repeatability_acceptance_checkpoint_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("repeatability_acceptance_checkpoint_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_idempotency_conflict",
            "The existing Candidate B repeatability acceptance-checkpoint receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _required_acceptance_disposition(fields: Mapping[str, Any]) -> str:
    value = _required(fields, "acceptance_disposition")
    if value == BLOCKED_DISPOSITION:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_regression_detected",
            "A detected Candidate B repeatability regression blocks acceptance.",
            http_status=409,
            details={"blocked_disposition": BLOCKED_DISPOSITION},
        )
    if value not in ACCEPTED_DISPOSITIONS:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_disposition_invalid",
            "Candidate B repeatability acceptance requires an admitted non-regression disposition.",
            details={
                "accepted_dispositions": sorted(ACCEPTED_DISPOSITIONS),
                "blocked_disposition": BLOCKED_DISPOSITION,
                "received_acceptance_disposition": value,
            },
        )
    return value


def _required_runbook_steps(fields: Mapping[str, Any]) -> list[str]:
    value = fields.get("operator_runbook_repeatability_steps")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_runbook_steps_missing",
            "Candidate B repeatability acceptance checkpoints require operator runbook repeatability steps.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS)},
        )
    steps = [str(step).strip() for step in value if str(step).strip()]
    if steps != list(REQUIRED_RUNBOOK_STEPS):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_runbook_steps_invalid",
            "Candidate B repeatability acceptance-checkpoint runbook steps must match the admitted acceptance sequence.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS), "received_steps": steps},
        )
    _assert_no_raw_authority_exposure(steps)
    return steps


def _workflow_receipt_root() -> Path:
    try:
        return rerun_trial._workflow_receipt_root()
    except rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            f"candidate_b_full_corpus_repeatability_acceptance_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        return rerun_trial._read_json_receipt(path)
    except rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            f"candidate_b_full_corpus_repeatability_acceptance_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        rerun_trial._validate_storage_id(value, prefix=prefix)
    except rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_storage_id_invalid",
            "Candidate B repeatability acceptance identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_required_field_missing",
            "A required Candidate B repeatability acceptance-checkpoint field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            "candidate_b_full_corpus_repeatability_acceptance_checkpoint_hash_invalid",
            "Candidate B repeatability acceptance-checkpoint hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _assert_no_raw_authority_exposure(value: Any) -> None:
    try:
        workflow_status._assert_no_raw_authority_exposure(value)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError(
            f"candidate_b_full_corpus_repeatability_acceptance_checkpoint_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
