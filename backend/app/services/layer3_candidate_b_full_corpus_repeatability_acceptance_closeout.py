from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.services import (
    layer3_candidate_b_operator_workflow_access_policy as workflow_access_policy,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
    layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint as acceptance,
    layer3_candidate_b_full_corpus_repeatability_rerun_trial as rerun_trial,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_repeatability_acceptance_operator_closeout.v1"
SCHEMA_VERSION = 1
CLOSEOUT_MODE = "append_only_acceptance_operator_closeout_receipt_without_process_execution_or_authority_mutation"
OPERATOR_DECISION = "record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout"
CLOSEOUT_STATE = "repeatability_acceptance_operator_closeout_recorded"
STATUS_SCHEMA_ID = (
    "layer3.candidate_b_full_corpus_repeatability_acceptance_operator_closeout_status.v1"
)
STATUS_MODE = (
    "read_only_acceptance_closeout_status_without_receipt_creation_lineage_mutation_or_frontend_authority"
)
STATUS_OPERATOR_DECISION = "inspect_candidate_b_full_corpus_repeatability_acceptance_closeout_status"
STATUS_PROJECTION_MODE = STATUS_MODE
CLOSEOUT_RECEIPT_PREFIX = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-repeatability-acceptance-closeout"
CLOSEOUT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout"
)
STATUS_ENDPOINT = f"{CLOSEOUT_ENDPOINT}/status"
ACCEPTANCE_CHECKPOINT_ENDPOINT = acceptance.ACCEPTANCE_CHECKPOINT_ENDPOINT
RENDERED_CONTROL_MODE = "rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control"
RENDERED_PROOF_STATE = "headed_and_headless_passed"
HEADLESS_RENDERED_PROOF_LABEL = "candidate_b_repeatability_acceptance_rendered_control_headless_chromium_pass"
HEADED_RENDERED_PROOF_LABEL = "candidate_b_repeatability_acceptance_rendered_control_headed_chromium_pass"
REQUIRED_RUNBOOK_STEPS = (
    "inspect_repeatability_acceptance_checkpoint",
    "verify_headed_and_headless_rendered_acceptance_proof",
    "review_closeout_negative_invariants",
    "record_repeatability_acceptance_operator_closeout",
)
REQUIRED_NEGATIVE_INVARIANTS: Mapping[str, bool] = {
    "actual_corpus_processing_execution_admitted_now": False,
    "actual_subprocess_spawn_admitted_now": False,
    "process_control_admitted": False,
    "process_kill_cancel_retry_resume_admitted": False,
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
}
_FORBIDDEN_REQUEST_FIELDS = acceptance._FORBIDDEN_REQUEST_FIELDS
STATUS_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "closeout_status_projection_state",
    "repeatability_acceptance_operator_closeout_receipt_available",
    "repeatability_acceptance_operator_closeout_receipt_id",
    "repeatability_acceptance_operator_closeout_receipt_hash",
    "repeatability_acceptance_operator_closeout_hash",
    "repeatability_acceptance_operator_closeout_authority_hash",
    "repeatability_acceptance_operator_closeout_receipt_ref",
    "repeatability_acceptance_checkpoint_receipt_id",
    "repeatability_acceptance_checkpoint_receipt_hash",
    "repeatability_acceptance_checkpoint_authority_hash",
    "original_repeatability_checkpoint_receipt_id",
    "repeatability_rerun_trial_receipt_id",
    "original_operator_workflow_receipt_id",
    "rerun_operator_workflow_receipt_id",
    "baseline_run_id",
    "candidate_a_run_id",
    "original_candidate_b_run_id",
    "rerun_candidate_b_run_id",
    "compare_target_set_hash",
    "material_relative_name",
    "acceptance_disposition",
    "comparison_hash",
    "negative_invariants_hash",
    "rendered_acceptance_control_proof_state",
    "comparison_summary",
    "negative_invariants",
    "rendered_acceptance_control_proof",
    "operator_projection",
)


class CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(Exception):
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
            "request_id": "candidate-b-full-corpus-repeatability-acceptance-closeout-error",
            "server_time": workflow_status._server_time(),
            "mode": CLOSEOUT_MODE,
            "status": "blocked",
            "repeatability_acceptance_operator_closeout_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "acceptance_closeout_mode") != CLOSEOUT_MODE:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_mode_not_admitted",
            "Only the append-only Candidate B repeatability acceptance closeout mode is admitted.",
            details={"expected_acceptance_closeout_mode": CLOSEOUT_MODE},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_decision_not_admitted",
            "The operator decision does not match the admitted acceptance-closeout action.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    runbook_steps = _required_runbook_steps(fields)
    rendered_proof = _required_rendered_proof(fields)
    negative_invariants = _required_negative_invariants(fields)
    acceptance_receipt = _validated_acceptance_checkpoint_receipt(fields)
    checkpoint = _acceptance_checkpoint_body(acceptance_receipt)
    acceptance_disposition = _validated_acceptance_disposition(checkpoint, fields)
    rerun_receipt = _validated_rerun_trial_receipt(checkpoint)
    trial = acceptance._rerun_trial_body(rerun_receipt)
    original = _validated_workflow_projection("original", trial)
    rerun = _validated_workflow_projection("rerun", trial)
    _authorize_closeout_workflow_rows(fields, original, rerun)
    original_checkpoint = _validated_original_checkpoint(checkpoint)
    rerun_trial._validate_original_checkpoint_binding(original_checkpoint, original, trial)
    acceptance._validate_rerun_trial_binding(rerun_receipt, trial, checkpoint, original, rerun)
    comparison = acceptance._validated_acceptance_comparison(trial, acceptance_disposition)

    closeout = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": CLOSEOUT_MODE,
        "repeatability_acceptance_checkpoint_receipt_id": acceptance_receipt[
            "repeatability_acceptance_checkpoint_receipt_id"
        ],
        "repeatability_acceptance_checkpoint_receipt_hash": acceptance_receipt[
            "repeatability_acceptance_checkpoint_receipt_hash"
        ],
        "repeatability_acceptance_checkpoint_hash": acceptance_receipt[
            "repeatability_acceptance_checkpoint_hash"
        ],
        "repeatability_acceptance_checkpoint_authority_hash": acceptance_receipt[
            "repeatability_acceptance_checkpoint_authority_hash"
        ],
        "original_repeatability_checkpoint_receipt_id": checkpoint[
            "original_repeatability_checkpoint_receipt_id"
        ],
        "original_repeatability_checkpoint_receipt_hash": checkpoint[
            "original_repeatability_checkpoint_receipt_hash"
        ],
        "original_repeatability_checkpoint_hash": checkpoint["original_repeatability_checkpoint_hash"],
        "original_repeatability_checkpoint_authority_hash": checkpoint[
            "original_repeatability_checkpoint_authority_hash"
        ],
        "repeatability_rerun_trial_receipt_id": checkpoint["repeatability_rerun_trial_receipt_id"],
        "repeatability_rerun_trial_receipt_hash": checkpoint["repeatability_rerun_trial_receipt_hash"],
        "repeatability_rerun_trial_hash": checkpoint["repeatability_rerun_trial_hash"],
        "repeatability_rerun_trial_authority_hash": checkpoint[
            "repeatability_rerun_trial_authority_hash"
        ],
        "original_operator_workflow_receipt_id": checkpoint["original_operator_workflow_receipt_id"],
        "rerun_operator_workflow_receipt_id": checkpoint["rerun_operator_workflow_receipt_id"],
        "baseline_run_id": checkpoint["baseline_run_id"],
        "candidate_a_run_id": checkpoint["candidate_a_run_id"],
        "original_candidate_b_run_id": checkpoint["original_candidate_b_run_id"],
        "rerun_candidate_b_run_id": checkpoint["rerun_candidate_b_run_id"],
        "compare_target_set_hash": checkpoint["compare_target_set_hash"],
        "material_relative_name": checkpoint["material_relative_name"],
        "acceptance_disposition": acceptance_disposition,
        "rendered_acceptance_control_proof": rendered_proof,
        "operator_runbook_closeout_steps": runbook_steps,
        "negative_invariants": negative_invariants,
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
    closeout_hash = workflow_status._stable_hash(closeout)
    closeout_authority = {
        **closeout,
        "operator_decision": OPERATOR_DECISION,
        "repeatability_acceptance_operator_closeout_hash": closeout_hash,
    }
    closeout_authority_hash = workflow_status._stable_hash(closeout_authority)
    idempotency_key_hash = workflow_status._stable_hash(
        {
            "client_request_id": request_id,
            "repeatability_acceptance_operator_closeout_authority_hash": closeout_authority_hash,
        }
    )
    receipt_id = f"{CLOSEOUT_RECEIPT_PREFIX}-{idempotency_key_hash[:24]}"
    receipt, idempotent_replay = _load_or_write_closeout_receipt(
        receipt_id=receipt_id,
        request_id=request_id,
        closeout=closeout,
        closeout_hash=closeout_hash,
        closeout_authority=closeout_authority,
        closeout_authority_hash=closeout_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
        negative_invariants=negative_invariants,
    )
    receipt_hash = _validate_closeout_receipt(
        receipt,
        request_id=request_id,
        receipt_id=receipt_id,
        closeout_hash=closeout_hash,
        closeout_authority_hash=closeout_authority_hash,
        idempotency_key_hash=idempotency_key_hash,
    )
    return {
        **receipt,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "repeatability_acceptance_operator_closeout_receipt_hash": receipt_hash,
        "repeatability_acceptance_operator_closeout_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-repeatability-acceptance-closeout://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "idempotent_replay": idempotent_replay,
        "repeatability_acceptance_checkpoint_endpoint": ACCEPTANCE_CHECKPOINT_ENDPOINT,
        "repeatability_acceptance_operator_closeout_endpoint": CLOSEOUT_ENDPOINT,
    }


def candidate_b_full_corpus_repeatability_acceptance_closeout_status(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    if _required(fields, "closeout_status_mode") != STATUS_MODE:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_mode_not_admitted",
            "Only the read-only Candidate B repeatability acceptance-closeout status mode is admitted.",
            details={"expected_closeout_status_mode": STATUS_MODE},
        )
    if _required(fields, "operator_decision") != STATUS_OPERATOR_DECISION:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_decision_not_admitted",
            "The operator decision does not match the admitted acceptance-closeout status inspection.",
            details={"expected_operator_decision": STATUS_OPERATOR_DECISION},
        )

    receipt_match = _selected_closeout_receipt(fields)
    if receipt_match is None:
        projection = _closeout_not_recorded_projection(fields)
    else:
        receipt_id, receipt = receipt_match
        projection = _closeout_available_projection(receipt_id, receipt, fields)
    status_hash = workflow_status._stable_hash({key: projection[key] for key in STATUS_HASH_KEYS})
    return {
        "schema_id": STATUS_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": workflow_status._server_time(),
        "status": "available",
        **projection,
        "closeout_status_hash": status_hash,
        "source_closeout_endpoint": CLOSEOUT_ENDPOINT,
        "repeatability_acceptance_operator_closeout_status_endpoint": STATUS_ENDPOINT,
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_forbidden_request_fields",
            "Repeatability acceptance closeout does not admit caller paths, URLs, commands, process controls, connector/model controls, browser authority, stdout, stderr, raw PIDs, or artifact bytes.",
            details={"blocked_fields": blocked},
        )
    return fields


def _selected_closeout_receipt(fields: Mapping[str, Any]) -> tuple[str, dict[str, Any]] | None:
    explicit_closeout_id = str(fields.get("repeatability_acceptance_operator_closeout_receipt_id") or "").strip()
    if explicit_closeout_id:
        return _explicit_closeout_receipt(explicit_closeout_id, fields)
    acceptance_receipt_id = str(fields.get("repeatability_acceptance_checkpoint_receipt_id") or "").strip()
    if not acceptance_receipt_id:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_selector_missing",
            "Closeout status requires either a closeout receipt id or an acceptance-checkpoint receipt id.",
            details={
                "accepted_selectors": [
                    "repeatability_acceptance_operator_closeout_receipt_id",
                    "repeatability_acceptance_checkpoint_receipt_id",
                ]
            },
        )
    return _closeout_receipt_for_acceptance_checkpoint(acceptance_receipt_id, fields)


def _explicit_closeout_receipt(
    receipt_id: str,
    fields: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    _validate_storage_id(receipt_id, prefix=CLOSEOUT_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_receipt_missing",
            "The selected Candidate B repeatability acceptance-closeout receipt is missing.",
            http_status=404,
            details={"repeatability_acceptance_operator_closeout_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    receipt_hash = _validate_stored_closeout_receipt(receipt, receipt_id=receipt_id)
    supplied_hash = str(
        fields.get("repeatability_acceptance_operator_closeout_receipt_hash") or ""
    ).strip()
    if supplied_hash and receipt_hash != _required_hash(
        fields,
        "repeatability_acceptance_operator_closeout_receipt_hash",
    ):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_stale_closeout_receipt",
            "The selected Candidate B repeatability acceptance-closeout receipt hash is stale or mismatched.",
            http_status=409,
            details={
                "expected_repeatability_acceptance_operator_closeout_receipt_hash": receipt_hash,
                "received_repeatability_acceptance_operator_closeout_receipt_hash": supplied_hash,
            },
        )
    _validate_optional_acceptance_binding(receipt, fields)
    return receipt_id, receipt


def _closeout_receipt_for_acceptance_checkpoint(
    acceptance_receipt_id: str,
    fields: Mapping[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    _validate_storage_id(acceptance_receipt_id, prefix=acceptance.ACCEPTANCE_CHECKPOINT_RECEIPT_PREFIX)
    acceptance_hash = str(fields.get("repeatability_acceptance_checkpoint_receipt_hash") or "").strip()
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in sorted(_workflow_receipt_root().glob(f"{CLOSEOUT_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=CLOSEOUT_RECEIPT_PREFIX)
        receipt = _read_json_receipt(receipt_file)
        _validate_stored_closeout_receipt(receipt, receipt_id=receipt_id)
        closeout = _closeout_body(receipt)
        if closeout.get("repeatability_acceptance_checkpoint_receipt_id") != acceptance_receipt_id:
            continue
        if acceptance_hash and closeout.get("repeatability_acceptance_checkpoint_receipt_hash") != acceptance_hash:
            raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
                "candidate_b_full_corpus_repeatability_acceptance_closeout_status_stale_acceptance_checkpoint",
                "A closeout receipt exists for the selected acceptance checkpoint, but the supplied checkpoint hash is stale or mismatched.",
                http_status=409,
                details={
                    "repeatability_acceptance_checkpoint_receipt_id": acceptance_receipt_id,
                    "expected_repeatability_acceptance_checkpoint_receipt_hash": closeout.get(
                        "repeatability_acceptance_checkpoint_receipt_hash"
                    ),
                    "received_repeatability_acceptance_checkpoint_receipt_hash": acceptance_hash,
                },
            )
        matches.append((receipt_id, receipt))
    if not matches:
        return None
    if len(matches) > 1:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_receipt_ambiguous",
            "Multiple Candidate B acceptance-closeout receipts are bound to the selected acceptance checkpoint.",
            http_status=409,
            details={
                "repeatability_acceptance_checkpoint_receipt_id": acceptance_receipt_id,
                "repeatability_acceptance_operator_closeout_receipt_ids": [
                    receipt_id for receipt_id, _receipt in matches
                ],
            },
        )
    return matches[0]


def _validate_optional_acceptance_binding(
    receipt: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> None:
    closeout = _closeout_body(receipt)
    expected = {
        "repeatability_acceptance_checkpoint_receipt_id": str(
            fields.get("repeatability_acceptance_checkpoint_receipt_id") or ""
        ).strip(),
        "repeatability_acceptance_checkpoint_receipt_hash": str(
            fields.get("repeatability_acceptance_checkpoint_receipt_hash") or ""
        ).strip(),
        "repeatability_acceptance_checkpoint_authority_hash": str(
            fields.get("repeatability_acceptance_checkpoint_authority_hash") or ""
        ).strip(),
    }
    mismatches = [
        {"field": key, "expected": closeout.get(key), "received": value}
        for key, value in expected.items()
        if value and closeout.get(key) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_binding_mismatch",
            "The selected closeout receipt is not bound to the supplied acceptance-checkpoint authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )


def _validate_stored_closeout_receipt(receipt: Mapping[str, Any], *, receipt_id: str) -> str:
    return _validate_closeout_receipt(
        receipt,
        request_id=str(receipt.get("client_request_id") or ""),
        receipt_id=receipt_id,
        closeout_hash=str(receipt.get("repeatability_acceptance_operator_closeout_hash") or ""),
        closeout_authority_hash=str(
            receipt.get("repeatability_acceptance_operator_closeout_authority_hash") or ""
        ),
        idempotency_key_hash=str(receipt.get("idempotency_key_hash") or ""),
    )


def _closeout_not_recorded_projection(fields: Mapping[str, Any]) -> dict[str, Any]:
    acceptance_receipt_id = str(fields.get("repeatability_acceptance_checkpoint_receipt_id") or "").strip()
    acceptance_receipt_hash = str(fields.get("repeatability_acceptance_checkpoint_receipt_hash") or "").strip()
    acceptance_authority_hash = str(
        fields.get("repeatability_acceptance_checkpoint_authority_hash") or ""
    ).strip()
    projection = {
        "schema_id": STATUS_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": STATUS_MODE,
        "closeout_status_projection_state": "not_recorded",
        "repeatability_acceptance_operator_closeout_receipt_available": False,
        "repeatability_acceptance_operator_closeout_receipt_id": "",
        "repeatability_acceptance_operator_closeout_receipt_hash": "",
        "repeatability_acceptance_operator_closeout_hash": "",
        "repeatability_acceptance_operator_closeout_authority_hash": "",
        "repeatability_acceptance_operator_closeout_receipt_ref": "",
        "repeatability_acceptance_checkpoint_receipt_id": acceptance_receipt_id,
        "repeatability_acceptance_checkpoint_receipt_hash": acceptance_receipt_hash,
        "repeatability_acceptance_checkpoint_authority_hash": acceptance_authority_hash,
        "original_repeatability_checkpoint_receipt_id": "",
        "repeatability_rerun_trial_receipt_id": "",
        "original_operator_workflow_receipt_id": "",
        "rerun_operator_workflow_receipt_id": "",
        "baseline_run_id": "",
        "candidate_a_run_id": "",
        "original_candidate_b_run_id": "",
        "rerun_candidate_b_run_id": "",
        "compare_target_set_hash": "",
        "material_relative_name": "",
        "acceptance_disposition": "not_recorded",
        "comparison_hash": "",
        "negative_invariants_hash": "",
        "rendered_acceptance_control_proof_state": "not_recorded",
        "comparison_summary": {},
        "negative_invariants": dict(REQUIRED_NEGATIVE_INVARIANTS),
        "rendered_acceptance_control_proof": {},
        "operator_projection": _status_operator_projection(available=False),
    }
    _assert_no_raw_authority_exposure(projection)
    return projection


def _closeout_available_projection(
    receipt_id: str,
    receipt: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    closeout = _closeout_body(receipt)
    receipt_hash = _validate_stored_closeout_receipt(receipt, receipt_id=receipt_id)
    comparison = _mapping_field(closeout, "comparison")
    negative_invariants = _mapping_field(closeout, "negative_invariants")
    rendered_proof = _mapping_field(closeout, "rendered_acceptance_control_proof")
    projection = {
        "schema_id": STATUS_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": STATUS_MODE,
        "closeout_status_projection_state": "available",
        "repeatability_acceptance_operator_closeout_receipt_available": True,
        "repeatability_acceptance_operator_closeout_receipt_id": receipt_id,
        "repeatability_acceptance_operator_closeout_receipt_hash": receipt_hash,
        "repeatability_acceptance_operator_closeout_hash": str(
            receipt["repeatability_acceptance_operator_closeout_hash"]
        ),
        "repeatability_acceptance_operator_closeout_authority_hash": str(
            receipt["repeatability_acceptance_operator_closeout_authority_hash"]
        ),
        "repeatability_acceptance_operator_closeout_receipt_ref": (
            "candidate-b-full-corpus-operator-workflow-repeatability-acceptance-closeout://"
            f"{receipt_id}/{receipt_hash[:24]}"
        ),
        "repeatability_acceptance_checkpoint_receipt_id": str(
            closeout["repeatability_acceptance_checkpoint_receipt_id"]
        ),
        "repeatability_acceptance_checkpoint_receipt_hash": str(
            closeout["repeatability_acceptance_checkpoint_receipt_hash"]
        ),
        "repeatability_acceptance_checkpoint_authority_hash": str(
            closeout["repeatability_acceptance_checkpoint_authority_hash"]
        ),
        "original_repeatability_checkpoint_receipt_id": str(
            closeout["original_repeatability_checkpoint_receipt_id"]
        ),
        "repeatability_rerun_trial_receipt_id": str(closeout["repeatability_rerun_trial_receipt_id"]),
        "original_operator_workflow_receipt_id": str(closeout["original_operator_workflow_receipt_id"]),
        "rerun_operator_workflow_receipt_id": str(closeout["rerun_operator_workflow_receipt_id"]),
        "baseline_run_id": str(closeout["baseline_run_id"]),
        "candidate_a_run_id": str(closeout["candidate_a_run_id"]),
        "original_candidate_b_run_id": str(closeout["original_candidate_b_run_id"]),
        "rerun_candidate_b_run_id": str(closeout["rerun_candidate_b_run_id"]),
        "compare_target_set_hash": str(closeout["compare_target_set_hash"]),
        "material_relative_name": str(closeout["material_relative_name"]),
        "acceptance_disposition": str(closeout["acceptance_disposition"]),
        "comparison_hash": workflow_status._stable_hash(comparison),
        "negative_invariants_hash": workflow_status._stable_hash(negative_invariants),
        "rendered_acceptance_control_proof_state": str(
            rendered_proof["rendered_acceptance_control_proof_state"]
        ),
        "comparison_summary": comparison,
        "negative_invariants": negative_invariants,
        "rendered_acceptance_control_proof": rendered_proof,
        "operator_projection": _status_operator_projection(available=True),
    }
    _validate_optional_acceptance_binding(receipt, fields)
    _assert_no_raw_authority_exposure(projection)
    return projection


def _status_operator_projection(*, available: bool) -> dict[str, Any]:
    return {
        "closeout_status_projection_visible": True,
        "closeout_receipt_projection_visible": available,
        "acceptance_checkpoint_projection_visible": True,
        "comparison_summary_visible": available,
        "negative_invariants_visible": True,
        "rendered_proof_summary_visible": available,
        "read_only_acceptance_closeout_status_projection": True,
        "missing_closeout_receipt_projects_not_recorded": True,
        "stale_closeout_receipt_rejected": True,
        "ambiguous_closeout_receipt_rejected": True,
        "acceptance_closeout_receipt_creation_admitted_now": False,
        "acceptance_closeout_receipt_mutation_admitted": False,
        "acceptance_checkpoint_receipt_mutation_admitted": False,
        "original_repeatability_checkpoint_receipt_mutation_admitted": False,
        "repeatability_rerun_trial_receipt_mutation_admitted": False,
        "original_workflow_receipt_mutation_admitted": False,
        "rerun_workflow_receipt_mutation_admitted": False,
        "process_execution_receipt_mutation_admitted": False,
        "process_completion_result_receipt_mutation_admitted": False,
        "adopted_result_downstream_proof_receipt_mutation_admitted": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "process_control_admitted": False,
        "process_kill_cancel_retry_resume_admitted": False,
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
        "browser_storage_authority_admitted": False,
        "frontend_durable_authority_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "default_scope_expansion_admitted": False,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_default_scope_preserved": "eligible_effective_pdfs_only",
        "selector_mutation_performed": False,
    }


def _closeout_body(receipt: Mapping[str, Any]) -> dict[str, Any]:
    closeout = receipt.get("repeatability_acceptance_operator_closeout")
    if not isinstance(closeout, Mapping):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_receipt_invalid",
            "The Candidate B acceptance-closeout receipt is missing closeout authority.",
            http_status=409,
        )
    return dict(closeout)


def _mapping_field(fields: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = fields.get(key)
    if not isinstance(value, Mapping):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_status_projection_invalid",
            "The Candidate B acceptance-closeout receipt is missing a required projection object.",
            http_status=409,
            details={"field": key},
        )
    return dict(value)


def _validated_acceptance_checkpoint_receipt(fields: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = _required(fields, "repeatability_acceptance_checkpoint_receipt_id")
    _validate_storage_id(receipt_id, prefix=acceptance.ACCEPTANCE_CHECKPOINT_RECEIPT_PREFIX)
    receipt_file = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not receipt_file.is_file():
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_acceptance_checkpoint_missing",
            "The Candidate B repeatability acceptance-checkpoint receipt is missing from server-owned authority.",
            http_status=404,
            details={"repeatability_acceptance_checkpoint_receipt_id": receipt_id},
        )
    receipt = _read_json_receipt(receipt_file)
    receipt_hash = _validate_acceptance_receipt_integrity(receipt, receipt_id=receipt_id, fields=fields)
    if receipt_hash != _required_hash(fields, "repeatability_acceptance_checkpoint_receipt_hash"):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_stale_acceptance_checkpoint",
            "The Candidate B repeatability acceptance-checkpoint receipt hash is stale or mismatched.",
            http_status=409,
            details={
                "expected_repeatability_acceptance_checkpoint_receipt_hash": receipt_hash,
                "received_repeatability_acceptance_checkpoint_receipt_hash": fields.get(
                    "repeatability_acceptance_checkpoint_receipt_hash"
                ),
            },
        )
    return dict(receipt)


def _validate_acceptance_receipt_integrity(
    receipt: Mapping[str, Any],
    *,
    receipt_id: str,
    fields: Mapping[str, Any],
) -> str:
    try:
        receipt_hash = acceptance._validate_acceptance_checkpoint_receipt(
            receipt,
            request_id=str(receipt.get("client_request_id") or ""),
            receipt_id=receipt_id,
            checkpoint_hash=_required_hash(fields, "repeatability_acceptance_checkpoint_hash"),
            checkpoint_authority_hash=_required_hash(
                fields,
                "repeatability_acceptance_checkpoint_authority_hash",
            ),
            idempotency_key_hash=str(receipt.get("idempotency_key_hash") or ""),
        )
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    _assert_no_raw_authority_exposure(receipt)
    return receipt_hash


def _acceptance_checkpoint_body(acceptance_receipt: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint = acceptance_receipt.get("repeatability_acceptance_checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_acceptance_checkpoint_invalid",
            "The Candidate B acceptance-checkpoint receipt is missing checkpoint authority.",
            http_status=409,
        )
    return dict(checkpoint)


def _validated_acceptance_disposition(
    checkpoint: Mapping[str, Any],
    fields: Mapping[str, Any],
) -> str:
    supplied = _required(fields, "acceptance_disposition")
    recorded = str(checkpoint.get("acceptance_disposition") or "")
    if supplied != recorded:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_disposition_mismatch",
            "The closeout acceptance disposition must match the recorded acceptance checkpoint.",
            http_status=409,
            details={"recorded_acceptance_disposition": recorded, "received_acceptance_disposition": supplied},
        )
    if supplied == acceptance.BLOCKED_DISPOSITION:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_regression_detected",
            "A detected Candidate B repeatability regression blocks closeout.",
            http_status=409,
            details={"blocked_disposition": acceptance.BLOCKED_DISPOSITION},
        )
    if supplied not in acceptance.ACCEPTED_DISPOSITIONS:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_disposition_invalid",
            "Candidate B repeatability closeout requires an admitted non-regression disposition.",
            details={
                "accepted_dispositions": sorted(acceptance.ACCEPTED_DISPOSITIONS),
                "blocked_disposition": acceptance.BLOCKED_DISPOSITION,
                "received_acceptance_disposition": supplied,
            },
        )
    return supplied


def _validated_rerun_trial_receipt(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return acceptance._validated_rerun_trial_receipt(checkpoint)
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _authorize_closeout_workflow_rows(
    fields: Mapping[str, Any],
    original: Mapping[str, Any],
    rerun: Mapping[str, Any],
) -> None:
    for label, projection in (("original", original), ("rerun", rerun)):
        row = projection.get("row")
        if not isinstance(row, Mapping):
            raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
                f"candidate_b_full_corpus_repeatability_acceptance_closeout_{label}_row_missing",
                "Acceptance closeout policy requires original and rerun workflow-row authority.",
                http_status=409,
            )
        workflow_access_policy.authorize_history_row_access(
            fields=fields,
            row=row,
            route_family="acceptance_closeout",
            rendered_surface=f"acceptance_closeout_{label}",
            requested_role=workflow_access_policy.OWNER_ROLE,
        )


def _validated_workflow_projection(prefix: str, trial: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return acceptance._validated_workflow_projection(prefix, trial)
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validated_original_checkpoint(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return acceptance._validated_original_checkpoint(checkpoint, checkpoint)
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _required_rendered_proof(fields: Mapping[str, Any]) -> dict[str, str]:
    proof = {
        "rendered_acceptance_control_mode": _required(fields, "rendered_acceptance_control_mode"),
        "rendered_acceptance_control_proof_state": _required(
            fields,
            "rendered_acceptance_control_proof_state",
        ),
        "headless_rendered_proof_label": _required(fields, "headless_rendered_proof_label"),
        "headed_rendered_proof_label": _required(fields, "headed_rendered_proof_label"),
    }
    expected = {
        "rendered_acceptance_control_mode": RENDERED_CONTROL_MODE,
        "rendered_acceptance_control_proof_state": RENDERED_PROOF_STATE,
        "headless_rendered_proof_label": HEADLESS_RENDERED_PROOF_LABEL,
        "headed_rendered_proof_label": HEADED_RENDERED_PROOF_LABEL,
    }
    mismatches = [
        {"field": key, "expected": value, "received": proof.get(key)}
        for key, value in expected.items()
        if proof.get(key) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_proof_ambiguous",
            "Candidate B repeatability acceptance closeout requires headed and headless rendered acceptance proof labels.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    _assert_no_raw_authority_exposure(proof)
    return proof


def _required_runbook_steps(fields: Mapping[str, Any]) -> list[str]:
    value = fields.get("operator_runbook_closeout_steps")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_runbook_steps_missing",
            "Candidate B repeatability acceptance closeout requires operator runbook closeout steps.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS)},
        )
    steps = [str(step).strip() for step in value if str(step).strip()]
    if steps != list(REQUIRED_RUNBOOK_STEPS):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_runbook_steps_invalid",
            "Candidate B repeatability acceptance closeout runbook steps must match the admitted closeout sequence.",
            details={"expected_steps": list(REQUIRED_RUNBOOK_STEPS), "received_steps": steps},
        )
    _assert_no_raw_authority_exposure(steps)
    return steps


def _required_negative_invariants(fields: Mapping[str, Any]) -> dict[str, bool]:
    value = fields.get("negative_invariant_attestations")
    if not isinstance(value, Mapping):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_negative_invariants_missing",
            "Candidate B repeatability acceptance closeout requires bounded negative invariant attestations.",
            details={"expected_negative_invariants": dict(REQUIRED_NEGATIVE_INVARIANTS)},
        )
    received = {str(key): bool(flag) for key, flag in value.items()}
    if received != dict(REQUIRED_NEGATIVE_INVARIANTS):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_negative_invariants_invalid",
            "Candidate B repeatability acceptance closeout negative invariants must exactly match the admitted set.",
            details={"expected_negative_invariants": dict(REQUIRED_NEGATIVE_INVARIANTS), "received": received},
        )
    _assert_no_raw_authority_exposure(received)
    return received


def _load_or_write_closeout_receipt(
    *,
    receipt_id: str,
    request_id: str,
    closeout: Mapping[str, Any],
    closeout_hash: str,
    closeout_authority: Mapping[str, Any],
    closeout_authority_hash: str,
    idempotency_key_hash: str,
    negative_invariants: Mapping[str, bool],
) -> tuple[dict[str, Any], bool]:
    root = _workflow_receipt_root()
    target = root / receipt_id / "receipt.json"
    if target.is_file():
        existing = _read_json_receipt(target)
        _validate_closeout_receipt(
            existing,
            request_id=request_id,
            receipt_id=receipt_id,
            closeout_hash=closeout_hash,
            closeout_authority_hash=closeout_authority_hash,
            idempotency_key_hash=idempotency_key_hash,
        )
        return existing, True
    _reject_competing_closeout(root, receipt_id, closeout_authority_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": CLOSEOUT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_acceptance_operator_closeout_state": CLOSEOUT_STATE,
        "repeatability_acceptance_operator_closeout_receipt_id": receipt_id,
        "repeatability_acceptance_operator_closeout": dict(closeout),
        "repeatability_acceptance_operator_closeout_hash": closeout_hash,
        "repeatability_acceptance_operator_closeout_authority": dict(closeout_authority),
        "repeatability_acceptance_operator_closeout_authority_hash": closeout_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_acceptance_operator_closeout_receipt": True,
        "exclusive_repeatability_acceptance_operator_closeout_per_authority": True,
        "repeatability_acceptance_operator_closeout_receipt_mutation_admitted": False,
        "repeatability_acceptance_checkpoint_receipt_mutated": False,
        "original_repeatability_checkpoint_receipt_mutated": False,
        "repeatability_rerun_trial_receipt_mutated": False,
        "original_workflow_receipt_mutated": False,
        "rerun_workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_default_scope_preserved": "eligible_effective_pdfs_only",
        "negative_invariants": dict(negative_invariants),
        "selector_mutation_performed": False,
        "next_allowed_actions": [
            "use this receipt as Candidate B full-corpus repeatability operator closeout evidence",
            "select rendered closeout controls, broader default scope, provider, connector, RAG/model, or full mockup expansion only through a separate freeze",
        ],
    }
    receipt_hash = workflow_status._stable_hash(receipt_input)
    receipt = {
        **receipt_input,
        "repeatability_acceptance_operator_closeout_receipt_hash": receipt_hash,
        "server_time": workflow_status._server_time(),
    }
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt, False


def _reject_competing_closeout(root: Path, receipt_id: str, closeout_authority_hash: str) -> None:
    for receipt_file in sorted(root.glob(f"{CLOSEOUT_RECEIPT_PREFIX}-*/receipt.json")):
        existing_id = receipt_file.parent.name
        if existing_id == receipt_id:
            continue
        existing = _read_json_receipt(receipt_file)
        if existing.get("repeatability_acceptance_operator_closeout_authority_hash") == closeout_authority_hash:
            raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
                "candidate_b_full_corpus_repeatability_acceptance_closeout_conflict",
                "The selected Candidate B repeatability acceptance authority already has a closeout receipt.",
                http_status=409,
                details={"existing_repeatability_acceptance_operator_closeout_receipt_id": existing_id},
            )


def _validate_closeout_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    receipt_id: str,
    closeout_hash: str,
    closeout_authority_hash: str,
    idempotency_key_hash: str,
) -> str:
    expected = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": CLOSEOUT_MODE,
        "operator_decision": OPERATOR_DECISION,
        "client_request_id": request_id,
        "status": "available",
        "repeatability_acceptance_operator_closeout_state": CLOSEOUT_STATE,
        "repeatability_acceptance_operator_closeout_receipt_id": receipt_id,
        "repeatability_acceptance_operator_closeout_hash": closeout_hash,
        "repeatability_acceptance_operator_closeout_authority_hash": closeout_authority_hash,
        "idempotency_key_hash": idempotency_key_hash,
        "append_only_repeatability_acceptance_operator_closeout_receipt": True,
        "exclusive_repeatability_acceptance_operator_closeout_per_authority": True,
        "repeatability_acceptance_operator_closeout_receipt_mutation_admitted": False,
        "repeatability_acceptance_checkpoint_receipt_mutated": False,
        "original_repeatability_checkpoint_receipt_mutated": False,
        "repeatability_rerun_trial_receipt_mutated": False,
        "original_workflow_receipt_mutated": False,
        "rerun_workflow_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "process_completion_result_receipt_mutated": False,
        "adopted_result_downstream_proof_receipt_mutated": False,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_default_scope_preserved": "eligible_effective_pdfs_only",
        "negative_invariants": dict(REQUIRED_NEGATIVE_INVARIANTS),
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
            if key not in {"repeatability_acceptance_operator_closeout_receipt_hash", "server_time"}
        }
    )
    if receipt.get("repeatability_acceptance_operator_closeout_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "repeatability_acceptance_operator_closeout_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("repeatability_acceptance_operator_closeout_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_idempotency_conflict",
            "The existing Candidate B repeatability acceptance-closeout receipt does not match the requested authority.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return receipt_hash


def _workflow_receipt_root() -> Path:
    try:
        return acceptance._workflow_receipt_root()
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        return acceptance._read_json_receipt(path)
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _validate_storage_id(value: str, *, prefix: str) -> None:
    try:
        acceptance._validate_storage_id(value, prefix=prefix)
    except acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_storage_id_invalid",
            "Candidate B repeatability acceptance-closeout identifiers must be server-owned storage identifiers.",
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_required_field_missing",
            "A required Candidate B repeatability acceptance-closeout field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            "candidate_b_full_corpus_repeatability_acceptance_closeout_hash_invalid",
            "Candidate B repeatability acceptance-closeout hash fields must be lowercase sha256 hex strings.",
            details={"field": key},
        )
    return value


def _assert_no_raw_authority_exposure(value: Any) -> None:
    try:
        workflow_status._assert_no_raw_authority_exposure(value)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError(
            f"candidate_b_full_corpus_repeatability_acceptance_closeout_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
