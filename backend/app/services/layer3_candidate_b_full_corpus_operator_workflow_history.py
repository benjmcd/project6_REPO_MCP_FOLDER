from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
)


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_history.v1"
SCHEMA_VERSION = 1
HISTORY_MODE = "candidate_b_full_corpus_operator_workflow_history_v1"
HISTORY_STATE = "available"
RUN_RECEIPT_PREFIX = workflow_run.RUN_RECEIPT_PREFIX
STATUS_ENDPOINT = workflow_run.STATUS_ENDPOINT
HISTORY_SCOPE = "server_owned_candidate_b_full_corpus_operator_workflow_run_receipts"
RENDERED_HISTORY_MODE = "rendered_candidate_b_full_corpus_operator_workflow_run_history_control"


class CandidateBFullCorpusOperatorWorkflowHistoryError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-history-error",
            "server_time": workflow_status._server_time(),
            "mode": HISTORY_MODE,
            "status": "blocked",
            "history_state": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_full_corpus_operator_workflow_history() -> dict[str, Any]:
    rows = _history_rows()
    history_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": HISTORY_MODE,
        "history_scope": HISTORY_SCOPE,
        "history_state": HISTORY_STATE,
        "status_endpoint": STATUS_ENDPOINT,
        "rendered_history_mode": RENDERED_HISTORY_MODE,
        "receipt_count": len(rows),
        "history_rows": rows,
    }
    history_hash = workflow_status._stable_hash(history_input)
    return {
        **history_input,
        "request_id": "candidate-b-full-corpus-operator-workflow-history",
        "server_time": workflow_status._server_time(),
        "status": "available",
        "history_hash": history_hash,
        "history_ref": f"candidate-b-full-corpus-operator-workflow-history://{history_hash[:24]}",
        "configured_receipt_authority_used": True,
        "read_only_history_projection": True,
        "single_run_status_endpoint_reused_for_detail": True,
        "browser_supplied_receipt_root_admitted": False,
        "browser_supplied_runtime_roots_admitted": False,
        "browser_supplied_source_directory_admitted": False,
        "browser_supplied_bridge_dir_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "cancel_runtime_admitted": False,
        "retry_runtime_admitted": False,
        "retry_policy_runtime_admitted": True,
        "retry_queue_state_runtime_admitted": True,
        "retry_scheduler_lease_runtime_admitted": True,
        "retry_worker_attempt_runtime_admitted": True,
        "retry_progress_checkpoint_runtime_admitted": True,
        "resume_runtime_admitted": False,
        "queue_state_authority_runtime_admitted": True,
        "queue_scheduler_runtime_admitted": True,
        "worker_attempt_runtime_admitted": True,
        "background_process_runtime_admitted": False,
        "job_execution_runtime_admitted": False,
        "progress_checkpoint_runtime_admitted": True,
        "completion_failure_runtime_admitted": True,
        "expiry_mutation_runtime_admitted": True,
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
            "inspect a selected workflow-run row through the returned status request",
            "expire or close a selected workflow-run row through the admitted lifecycle endpoint",
            "record append-only queue-state authority for a selected workflow-run row",
            "record append-only scheduler lease authority for a selected queue-state receipt",
            "record append-only worker-attempt authority for a selected scheduler lease receipt",
            "record append-only progress-checkpoint authority for a selected worker-attempt receipt",
            "record append-only completion/failure authority through the admitted completion/failure endpoint",
            "record append-only retry-policy authority through the admitted retry-policy endpoint",
            "record append-only retry queue-state authority through the admitted retry queue-state endpoint",
            "record append-only retry scheduler-lease authority through the admitted retry scheduler-lease endpoint",
            "record append-only retry worker-attempt authority through the admitted retry worker-attempt endpoint",
            "record append-only retry progress-checkpoint authority through the admitted retry progress-checkpoint endpoint",
            "select cancel, retry, or resume only through a separate freeze",
            "select cancel, retry-attempt, or resume only through a separate freeze",
        ],
    }


def _history_rows() -> list[dict[str, Any]]:
    root = _workflow_receipt_root()
    rows: list[dict[str, Any]] = []
    for receipt_file in sorted(root.glob(f"{RUN_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        workflow_status._validate_storage_id(receipt_id, prefix=RUN_RECEIPT_PREFIX)
        receipt = _read_json_receipt(receipt_file)
        if "server_owned_workflow_run" not in receipt:
            schema_id = str(receipt.get("schema_id") or "")
            if schema_id.startswith("layer3.candidate_b_full_corpus_operator_workflow_"):
                continue
            raise CandidateBFullCorpusOperatorWorkflowHistoryError(
                "candidate_b_full_corpus_operator_workflow_history_non_run_receipt",
                "Workflow-run history only admits server-owned workflow-run receipts.",
                http_status=409,
                details={"operator_workflow_receipt_id": receipt_id},
            )
        rows.append(_history_row(receipt_id, receipt))
    rows.sort(
        key=lambda row: (
            str(row.get("server_time") or ""),
            str(row.get("operator_workflow_receipt_id") or ""),
        ),
        reverse=True,
    )
    return rows


def _history_row(receipt_id: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    server_run = receipt.get("server_owned_workflow_run")
    if not isinstance(server_run, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_run_state_missing",
            "Workflow-run history receipt is missing server-owned run state.",
            http_status=409,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    authority_basis = server_run.get("authority_basis")
    if not isinstance(authority_basis, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_authority_basis_missing",
            "Workflow-run history receipt is missing server-owned authority basis.",
            http_status=409,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    fields = _status_fields(receipt_id, receipt)
    try:
        receipt_hash = workflow_status._validate_workflow_receipt(
            receipt,
            receipt_id=receipt_id,
            fields=fields,
        )
        workflow_status._assert_no_raw_authority_exposure(receipt)
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            f"candidate_b_full_corpus_operator_workflow_history_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    _validate_server_run(receipt_id, receipt_hash, receipt, server_run, authority_basis)
    status_request = {
        "client_request_id": f"candidate-b-full-corpus-operator-workflow-history-{receipt_id}-status",
        "status_mode": workflow_status.STATUS_MODE,
        "operator_decision": workflow_status.OPERATOR_DECISION,
        "operator_workflow_receipt_id": receipt_id,
        "baseline_run_id": str(receipt["baseline_run_id"]),
        "candidate_a_run_id": str(receipt["candidate_a_run_id"]),
        "candidate_b_run_id": str(receipt["candidate_b_run_id"]),
        "bridge_receipt_id": str(receipt["bridge_receipt_id"]),
        "downstream_proof_id": str(receipt["downstream_proof_id"]),
    }
    row = {
        "operator_workflow_receipt_id": receipt_id,
        "operator_workflow_receipt_hash": receipt_hash,
        "source_operator_workflow_receipt_id": str(server_run["source_operator_workflow_receipt_id"]),
        "source_operator_workflow_receipt_hash": str(server_run["source_operator_workflow_receipt_hash"]),
        "authority_basis_hash": str(server_run["authority_basis_hash"]),
        "runtime_root_lifecycle_receipt_id": str(authority_basis["runtime_root_lifecycle_receipt_id"]),
        "baseline_run_id": str(receipt["baseline_run_id"]),
        "candidate_a_run_id": str(receipt["candidate_a_run_id"]),
        "candidate_b_run_id": str(receipt["candidate_b_run_id"]),
        "compare_target_set_hash": str(receipt["compare_target_set_hash"]),
        "bridge_receipt_id": str(receipt["bridge_receipt_id"]),
        "downstream_proof_id": str(receipt["downstream_proof_id"]),
        "material_relative_name": str(authority_basis["material_relative_name"]),
        "run_state": str(server_run["run_state"]),
        "state_machine": list(server_run["state_machine"]),
        "server_time": str(receipt.get("server_time") or ""),
        "status_endpoint": STATUS_ENDPOINT,
        "status_request": status_request,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "frontend_durable_authority_enabled": False,
    }
    return {**row, "row_hash": workflow_status._stable_hash(row)}


def _validate_server_run(
    receipt_id: str,
    receipt_hash: str,
    receipt: Mapping[str, Any],
    server_run: Mapping[str, Any],
    authority_basis: Mapping[str, Any],
) -> None:
    source_receipt_id = str(server_run.get("source_operator_workflow_receipt_id") or "")
    source_receipt_hash = str(server_run.get("source_operator_workflow_receipt_hash") or "")
    expected = {
        "schema_id": workflow_run.SCHEMA_ID,
        "schema_version": workflow_run.SCHEMA_VERSION,
        "run_mode": workflow_run.RUN_MODE,
        "operator_decision": workflow_run.OPERATOR_DECISION,
        "run_state": "proven",
        "authority_basis_hash": workflow_status._stable_hash(authority_basis),
        "source_operator_workflow_receipt_hash": source_receipt_hash,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": server_run.get(field)}
        for field, expected_value in expected.items()
        if server_run.get(field) != expected_value
    ]
    if list(server_run.get("state_machine") or []) != list(workflow_run.STATE_MACHINE):
        mismatches.append(
            {
                "field": "state_machine",
                "expected": list(workflow_run.STATE_MACHINE),
                "received": server_run.get("state_machine"),
            }
        )
    authority_expected = {
        "run_mode": workflow_run.RUN_MODE,
        "operator_decision": workflow_run.OPERATOR_DECISION,
        "source_operator_workflow_receipt_id": source_receipt_id,
        "source_operator_workflow_receipt_hash": source_receipt_hash,
        "runtime_root_lifecycle_receipt_id": _runtime_root_lifecycle_receipt_id(receipt),
        "baseline_run_id": str(receipt["baseline_run_id"]),
        "candidate_a_run_id": str(receipt["candidate_a_run_id"]),
        "candidate_b_run_id": str(receipt["candidate_b_run_id"]),
        "compare_target_set_hash": str(receipt["compare_target_set_hash"]),
        "material_relative_name": _material_relative_name(receipt),
        "eligible_corpus_scope": "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only",
    }
    for field, expected_value in authority_expected.items():
        if authority_basis.get(field) != expected_value:
            mismatches.append(
                {
                    "field": f"authority_basis.{field}",
                    "expected": expected_value,
                    "received": authority_basis.get(field),
                }
            )
    if receipt_id == source_receipt_id or not source_receipt_id.startswith(f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-"):
        mismatches.append(
            {
                "field": "source_operator_workflow_receipt_id",
                "expected": f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-* source receipt",
                "received": source_receipt_id,
            }
        )
    if receipt_hash != str(receipt.get("receipt_hash")):
        mismatches.append(
            {"field": "receipt_hash", "expected": receipt_hash, "received": receipt.get("receipt_hash")}
        )
    source_receipt = _source_receipt(source_receipt_id)
    if source_receipt.get("receipt_hash") != source_receipt_hash:
        mismatches.append(
            {
                "field": "source_operator_workflow_receipt_hash",
                "expected": source_receipt.get("receipt_hash"),
                "received": source_receipt_hash,
            }
        )
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_authority_mismatch",
            "Workflow-run history receipt has stale or contradictory server-owned authority.",
            http_status=409,
            details={"operator_workflow_receipt_id": receipt_id, "mismatches": mismatches},
        )


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _source_receipt(receipt_id: str) -> dict[str, Any]:
    try:
        receipt = workflow_status._read_workflow_receipt(receipt_id)
        workflow_status._validate_workflow_receipt(
            receipt,
            receipt_id=receipt_id,
            fields=_status_fields(receipt_id, receipt),
        )
        return receipt
    except workflow_status.CandidateBFullCorpusOperatorWorkflowStatusError as exc:
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            f"candidate_b_full_corpus_operator_workflow_history_source_{exc.code}",
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _read_json_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_receipt_unreadable",
            "A Candidate B workflow-run history receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowHistoryError(
            "candidate_b_full_corpus_operator_workflow_history_receipt_invalid",
            "Candidate B workflow-run history receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _status_fields(receipt_id: str, receipt: Mapping[str, Any]) -> dict[str, str]:
    return {
        "client_request_id": f"candidate-b-full-corpus-operator-workflow-history-{receipt_id}",
        "status_mode": workflow_status.STATUS_MODE,
        "operator_decision": workflow_status.OPERATOR_DECISION,
        "operator_workflow_receipt_id": receipt_id,
        "baseline_run_id": str(receipt.get("baseline_run_id") or ""),
        "candidate_a_run_id": str(receipt.get("candidate_a_run_id") or ""),
        "candidate_b_run_id": str(receipt.get("candidate_b_run_id") or ""),
        "bridge_receipt_id": str(receipt.get("bridge_receipt_id") or ""),
        "downstream_proof_id": str(receipt.get("downstream_proof_id") or ""),
    }


def _runtime_root_lifecycle_receipt_id(receipt: Mapping[str, Any]) -> str:
    lifecycle = receipt.get("runtime_root_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return ""
    return str(lifecycle.get("lifecycle_receipt_id") or "")


def _material_relative_name(receipt: Mapping[str, Any]) -> str:
    corpus = receipt.get("corpus")
    if not isinstance(corpus, Mapping):
        return ""
    return str(corpus.get("material_relative_name") or "")
