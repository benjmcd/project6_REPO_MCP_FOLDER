from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_operator_workflow_access_policy as workflow_access_policy


SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_status.v1"
SCHEMA_VERSION = 1
STATUS_MODE = "candidate_b_full_corpus_operator_workflow_status_v1"
OPERATOR_DECISION = "inspect_candidate_b_full_corpus_operator_workflow_status"
WORKFLOW_SCHEMA_ID = "candidate_b.full_corpus_layer3_operator_workflow.v1"
WORKFLOW_MODE = "candidate_b_full_corpus_operator_workflow_v1"
WORKFLOW_RECEIPT_PREFIX = "cb-full-corpus-operator"
RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID = "candidate_b.full_corpus_runtime_root_lifecycle.v1"
RUNTIME_ROOT_LIFECYCLE_MODE = "candidate_b_full_corpus_runtime_root_lifecycle_v1"
STATUS_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "workflow_receipt_id",
    "workflow_receipt_hash",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_run_id",
    "compare_target_set_hash",
    "bridge_receipt_id",
    "bridge_receipt_hash",
    "downstream_proof_id",
    "downstream_proof_hash",
    "coverage_count",
    "corpus",
    "eligibility_summary",
    "baseline_rollback",
    "layer3",
    "artifact_family",
    "runtime_root_lifecycle",
    "retry_terminal_status_projection",
    "execution_boundary_projection",
    "process_execution_projection",
    "process_completion_result_projection",
    "adopted_result_downstream_proof_projection",
    "operator_projection",
)
WORKFLOW_RECEIPT_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "workflow_mode",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_run_id",
    "compare_target_set_hash",
    "bridge_receipt_id",
    "bridge_receipt_hash",
    "downstream_proof_id",
    "downstream_proof_hash",
    "coverage_count",
    "corpus",
    "baseline_rollback",
    "runtime_root_lifecycle",
)
RETRY_COMPLETION_FAILURE_SCHEMA_ID = (
    "layer3.candidate_b_full_corpus_operator_workflow_retry_completion_failure.v1"
)
RETRY_COMPLETION_FAILURE_MODE = (
    "append_only_retry_completion_failure_receipt_without_cancel_resume_job_execution_or_source_receipt_mutation"
)
RETRY_COMPLETION_FAILURE_RECEIPT_PREFIX = (
    f"{WORKFLOW_RECEIPT_PREFIX}-retry-completion-failure"
)
RETRY_TERMINAL_STATUS_PROJECTION_MODE = (
    "read_only_retry_terminal_receipt_projection_without_receipt_creation_or_lineage_mutation"
)
EXECUTION_BOUNDARY_SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_execution_boundary.v1"
EXECUTION_BOUNDARY_MODE = "append_only_execution_boundary_receipt_without_process_start_or_job_execution"
EXECUTION_BOUNDARY_RECEIPT_PREFIX = f"{WORKFLOW_RECEIPT_PREFIX}-execution-boundary"
EXECUTION_BOUNDARY_STATUS_PROJECTION_MODE = (
    "read_only_execution_boundary_receipt_projection_without_process_start_or_job_execution"
)
PROCESS_EXECUTION_SCHEMA_ID = "layer3.candidate_b_full_corpus_operator_workflow_process_execution.v1"
PROCESS_EXECUTION_MODE = (
    "server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority"
)
PROCESS_EXECUTION_RECEIPT_PREFIX = f"{WORKFLOW_RECEIPT_PREFIX}-process-execution"
PROCESS_EXECUTION_STATUS_PROJECTION_MODE = (
    "read_only_process_execution_receipt_projection_without_job_completion_or_result_adoption"
)
PROCESS_COMPLETION_RESULT_SCHEMA_ID = (
    "layer3.candidate_b_full_corpus_operator_workflow_process_completion_result.v1"
)
PROCESS_COMPLETION_RESULT_MODE = (
    "append_only_process_completion_result_adoption_receipt_without_source_run_mutation_or_raw_output_exposure"
)
PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX = f"{WORKFLOW_RECEIPT_PREFIX}-process-result"
PROCESS_COMPLETION_RESULT_STATUS_PROJECTION_MODE = (
    "read_only_process_completion_result_receipt_projection_without_receipt_creation_or_lineage_mutation"
)
ADOPTED_RESULT_DOWNSTREAM_PROOF_SCHEMA_ID = (
    "layer3.candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof.v1"
)
ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE = (
    "read_only_adopted_process_result_downstream_operator_proof_without_result_mutation_or_reexecution"
)
ADOPTED_RESULT_DOWNSTREAM_PROOF_RECEIPT_PREFIX = (
    f"{WORKFLOW_RECEIPT_PREFIX}-adopted-result-downstream-proof"
)
ADOPTED_RESULT_DOWNSTREAM_PROOF_STATUS_PROJECTION_MODE = (
    "read_only_adopted_result_downstream_proof_receipt_projection_without_receipt_creation_or_reexecution"
)
_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "file",
    "files",
    "file_bytes",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
}
_ALLOWED_REF_SCHEMES = (
    "repo://",
    "redacted://",
    "candidate-b-runtime-bridge://",
    "candidate-b-full-corpus-operator-workflow://",
    "candidate-b-full-corpus-operator-workflow-retry-completion-failure://",
    "candidate-b-full-corpus-operator-workflow-process-execution://",
    "candidate-b-full-corpus-operator-workflow-process://",
    "candidate-b-full-corpus-operator-workflow-process-result://",
    "candidate-b-full-corpus-operator-workflow-adopted-result-downstream-proof://",
    "candidate-b-full-corpus-operator-workflow-repeatability-checkpoint://",
    "candidate-b-full-corpus-operator-workflow-repeatability-acceptance-closeout://",
)


class CandidateBFullCorpusOperatorWorkflowStatusError(Exception):
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
            "request_id": "candidate-b-full-corpus-operator-workflow-status-error",
            "server_time": _server_time(),
            "mode": STATUS_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def candidate_b_full_corpus_operator_workflow_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    mode = _required(fields, "status_mode")
    if mode != STATUS_MODE:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_mode_not_admitted",
            "Only the Candidate B full-corpus operator workflow status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": mode},
        )
    if _required(fields, "operator_decision") != OPERATOR_DECISION:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_decision_not_admitted",
            "The operator decision does not match the admitted read-only workflow-status inspection.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    receipt_id = _required_storage_id(fields, "operator_workflow_receipt_id", WORKFLOW_RECEIPT_PREFIX)
    receipt = _read_workflow_receipt(receipt_id)
    receipt_hash = _validate_workflow_receipt(receipt, receipt_id=receipt_id, fields=fields)
    _assert_no_raw_authority_exposure(receipt)
    ownership_access_policy = workflow_access_policy.authorize_workflow_access(
        fields=fields,
        route_family="workflow_status",
        rendered_surface="status",
        workflow_receipt_id=receipt_id,
        workflow_receipt_hash=receipt_hash,
        authority_basis_hash=_workflow_authority_basis_hash(receipt),
        requested_role=str(fields.get("operator_role") or workflow_access_policy.AUDITOR_ROLE),
        existing_owner_binding=_workflow_owner_binding(receipt),
    )

    corpus = _workflow_corpus(receipt)
    eligibility_summary = _workflow_eligibility_summary(corpus)
    baseline_rollback = _workflow_baseline_rollback(receipt)
    layer3 = _workflow_layer3_projection(receipt)
    artifact_family = _workflow_artifact_family(receipt)
    runtime_root_lifecycle = _workflow_runtime_root_lifecycle(receipt)
    retry_terminal_status_projection = _retry_terminal_status_projection(receipt_id, receipt_hash)
    execution_boundary_projection = _execution_boundary_projection(receipt_id, receipt_hash)
    process_execution_projection = _process_execution_projection(receipt_id, receipt_hash)
    process_completion_result_projection = _process_completion_result_projection(receipt_id, receipt_hash)
    adopted_result_downstream_proof_projection = _adopted_result_downstream_proof_projection(
        receipt_id,
        receipt_hash,
    )
    operator_projection = {
        "workflow_status_visible": True,
        "workflow_receipt_projection_visible": True,
        "bridge_receipt_projection_visible": True,
        "downstream_proof_projection_visible": True,
        "artifact_family_projection_visible": True,
        "eligibility_summary_projection_visible": True,
        "baseline_rollback_projection_visible": True,
        "runtime_root_lifecycle_projection_visible": runtime_root_lifecycle["available"],
        "retry_terminal_status_projection_visible": True,
        "execution_boundary_projection_visible": True,
        "process_execution_projection_visible": True,
        "process_completion_result_projection_visible": True,
        "adopted_result_downstream_proof_projection_visible": True,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "frontend_durable_authority_enabled": False,
    }
    status_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": STATUS_MODE,
        "workflow_receipt_id": receipt_id,
        "workflow_receipt_hash": receipt_hash,
        "baseline_run_id": str(receipt["baseline_run_id"]),
        "candidate_a_run_id": str(receipt["candidate_a_run_id"]),
        "candidate_b_run_id": str(receipt["candidate_b_run_id"]),
        "compare_target_set_hash": str(receipt["compare_target_set_hash"]),
        "bridge_receipt_id": str(receipt["bridge_receipt_id"]),
        "bridge_receipt_hash": str(receipt["bridge_receipt_hash"]),
        "downstream_proof_id": str(receipt["downstream_proof_id"]),
        "downstream_proof_hash": str(receipt["downstream_proof_hash"]),
        "coverage_count": _non_negative_int(receipt, "coverage_count"),
        "corpus": corpus,
        "eligibility_summary": eligibility_summary,
        "baseline_rollback": baseline_rollback,
        "layer3": layer3,
        "artifact_family": artifact_family,
        "runtime_root_lifecycle": runtime_root_lifecycle,
        "retry_terminal_status_projection": retry_terminal_status_projection,
        "execution_boundary_projection": execution_boundary_projection,
        "process_execution_projection": process_execution_projection,
        "process_completion_result_projection": process_completion_result_projection,
        "adopted_result_downstream_proof_projection": adopted_result_downstream_proof_projection,
        "operator_projection": operator_projection,
        "ownership_access_policy": _policy_projection(ownership_access_policy),
    }
    status_hash = _stable_hash({key: status_input[key] for key in STATUS_HASH_KEYS})
    return {
        **status_input,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "workflow_status": str(receipt["status"]),
        "workflow_status_hash": status_hash,
        "workflow_status_ref": f"candidate-b-full-corpus-operator-workflow-status://{receipt_id}/{status_hash[:24]}",
        "validate_only_triplet": receipt.get("validate_only_triplet") is True,
        "artifacts_seeded_or_generated_by_triplet_validator": (
            receipt.get("artifacts_seeded_or_generated_by_triplet_validator") is True
        ),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "negative_invariants": {
            **_negative_invariants(receipt),
            "operator_workflow_status_mutation_performed": False,
            "frontend_durable_authority_enabled": False,
            "ownership_access_policy_audit_event_appended": True,
            "browser_storage_identity_used": False,
            "raw_identity_or_policy_secret_exposed": False,
        },
        "ownership_access_policy": _policy_projection(ownership_access_policy),
        "next_allowed_actions": [
            "inspect Candidate B full-corpus operator workflow evidence",
            "use this receipt status as operator-repeatability evidence",
            "run a fresh full-corpus workflow only when current evidence is stale or a concrete defect appears",
        ],
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    workflow_access_policy.reject_forbidden_request_fields(fields)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_forbidden_request_fields",
            "Workflow-status inspection does not admit caller paths, URLs, selector mutation, connectors, browser authority, or credentials.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_required_field_missing",
            "A required Candidate B full-corpus operator workflow-status field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str, prefix: str) -> str:
    value = _required(fields, key)
    _validate_storage_id(value, prefix=prefix)
    return value


def _validate_storage_id(value: str, *, prefix: str) -> None:
    if (
        not value.startswith(f"{prefix}-")
        or "/" in value
        or "\\" in value
        or ".." in value
        or value in {".", ".."}
    ):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_storage_id_invalid",
            "Candidate B full-corpus operator workflow receipt identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )


def _read_workflow_receipt(receipt_id: str) -> dict[str, Any]:
    path = _workflow_receipt_root() / receipt_id / "receipt.json"
    if not path.is_file():
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_missing",
            "The selected Candidate B full-corpus operator workflow receipt is missing.",
            http_status=404,
            details={"operator_workflow_receipt_id": receipt_id},
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_unreadable",
            "The selected Candidate B full-corpus operator workflow receipt could not be read.",
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_invalid",
            "The selected Candidate B full-corpus operator workflow receipt is not a JSON object.",
            http_status=409,
        )
    return receipt


def _workflow_receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_full_corpus_operator_workflow_dir or "").strip()
    root = Path(configured)
    if not configured or not root.is_absolute():
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_dir_invalid",
            "The configured Candidate B full-corpus operator workflow receipt directory is missing or not absolute.",
            http_status=409,
        )
    if not root.is_dir():
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_dir_missing",
            "The configured Candidate B full-corpus operator workflow receipt directory does not exist.",
            http_status=404,
        )
    return root


def _validate_workflow_receipt(receipt: Mapping[str, Any], *, receipt_id: str, fields: Mapping[str, Any]) -> str:
    expected = {
        "schema_id": WORKFLOW_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "workflow_mode": WORKFLOW_MODE,
        "receipt_id": receipt_id,
        "status": "proven",
        "baseline_run_id": _required(fields, "baseline_run_id"),
        "candidate_a_run_id": _required(fields, "candidate_a_run_id"),
        "candidate_b_run_id": _required(fields, "candidate_b_run_id"),
        "bridge_receipt_id": _required_storage_id(fields, "bridge_receipt_id", "cb-runtime-l3"),
        "downstream_proof_id": _required_storage_id(
            fields,
            "downstream_proof_id",
            "cb-runtime-downstream-proof",
        ),
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_mismatch",
            "The selected Candidate B full-corpus operator workflow receipt does not match the requested authority identifiers.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    missing = [key for key in WORKFLOW_RECEIPT_HASH_KEYS if key not in receipt]
    if missing:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_authority_field_missing",
            "The selected Candidate B full-corpus operator workflow receipt is missing authority hash fields.",
            http_status=409,
            details={"missing_fields": missing},
        )
    expected_hash = _stable_hash({key: receipt[key] for key in WORKFLOW_RECEIPT_HASH_KEYS})
    if receipt.get("receipt_hash") != expected_hash:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_hash_mismatch",
            "The selected Candidate B full-corpus operator workflow receipt hash is stale or invalid.",
            http_status=409,
            details={"expected": expected_hash, "received": receipt.get("receipt_hash")},
        )
    if receipt.get("validate_only_triplet") is not True:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_not_validate_only",
            "Candidate B full-corpus operator workflow status requires a validate-only triplet run.",
            http_status=409,
        )
    if receipt.get("artifacts_seeded_or_generated_by_triplet_validator") is not False:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_seeded_artifacts",
            "Candidate B full-corpus operator workflow status rejects receipts that seeded or generated triplet artifacts.",
            http_status=409,
        )
    return expected_hash


def _workflow_authority_basis_hash(receipt: Mapping[str, Any]) -> str:
    server_run = receipt.get("server_owned_workflow_run")
    if isinstance(server_run, Mapping):
        authority_basis_hash = str(server_run.get("authority_basis_hash") or "").strip()
        if authority_basis_hash:
            return authority_basis_hash
    return _stable_hash({key: receipt[key] for key in WORKFLOW_RECEIPT_HASH_KEYS if key in receipt})


def _workflow_owner_binding(receipt: Mapping[str, Any]) -> Mapping[str, Any] | None:
    owner_binding = receipt.get("workflow_receipt_owner_binding")
    if isinstance(owner_binding, Mapping):
        return owner_binding
    policy = receipt.get("ownership_access_policy")
    if isinstance(policy, Mapping):
        return policy
    server_run = receipt.get("server_owned_workflow_run")
    if isinstance(server_run, Mapping):
        owner_binding = server_run.get("workflow_receipt_owner_binding")
        if isinstance(owner_binding, Mapping):
            return owner_binding
        policy = server_run.get("ownership_access_policy")
        if isinstance(policy, Mapping):
            return policy
    return None


def _policy_projection(policy_decision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_schema_id": str(policy_decision["policy_schema_id"]),
        "policy_runtime": str(policy_decision["policy_runtime"]),
        "auth_owner_mode": str(policy_decision["auth_owner_mode"]),
        "identity_authority": str(policy_decision["identity_authority"]),
        "tenant_workspace_authority": str(policy_decision["tenant_workspace_authority"]),
        "storage_access_policy": str(policy_decision["storage_access_policy"]),
        "audit_event_policy": str(policy_decision["audit_event_policy"]),
        "policy_status": str(policy_decision["policy_status"]),
        "policy_hash": str(policy_decision["policy_hash"]),
        "actor_ref_hash": str(policy_decision["actor_ref_hash"]),
        "tenant_or_workspace_ref_hash": str(policy_decision["tenant_or_workspace_ref_hash"]),
        "workflow_receipt_id": str(policy_decision["workflow_receipt_id"]),
        "workflow_receipt_hash": str(policy_decision["workflow_receipt_hash"]),
        "route_family": str(policy_decision["route_family"]),
        "rendered_surface": str(policy_decision["rendered_surface"]),
        "decision": str(policy_decision["decision"]),
        "reason_code": str(policy_decision["reason_code"]),
        "audit_event_id": str(policy_decision["audit_event_id"]),
        "audit_event_hash": str(policy_decision["audit_event_hash"]),
        "audit_event_ref": str(policy_decision["audit_event_ref"]),
        "next_actions": list(policy_decision["next_actions"]),
        "raw_operator_identity_exposed": False,
        "raw_proxy_header_exposed": False,
        "raw_tenant_or_workspace_exposed": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "raw_token_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "artifact_bytes_exposed": False,
        "browser_storage_authority_used": False,
        "frontend_durable_authority_enabled": False,
        "workflow_receipt_owner_binding_required": bool(
            policy_decision["workflow_receipt_owner_binding_required"]
        ),
    }


def _workflow_corpus(receipt: Mapping[str, Any]) -> dict[str, Any]:
    corpus = receipt.get("corpus")
    if not isinstance(corpus, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_corpus_missing",
            "The selected workflow receipt is missing corpus status.",
            http_status=409,
        )
    target_status_counts = corpus.get("target_status_counts")
    if not isinstance(target_status_counts, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_target_status_counts_missing",
            "The selected workflow receipt is missing Candidate B target status counts.",
            http_status=409,
        )
    return {
        "corpus_pdf_count": _non_negative_int(corpus, "corpus_pdf_count"),
        "eligible_file_count": _non_negative_int(corpus, "eligible_file_count"),
        "material_relative_name": str(corpus.get("material_relative_name") or ""),
        "target_status_counts": dict(target_status_counts),
        "eligibility_summary": dict(corpus.get("eligibility_summary") or {}),
    }


def _workflow_eligibility_summary(corpus: Mapping[str, Any]) -> dict[str, Any]:
    corpus_pdf_count = _non_negative_int(corpus, "corpus_pdf_count")
    source_directory_eligible_file_count = _non_negative_int(corpus, "eligible_file_count")
    target_status_counts = corpus.get("target_status_counts")
    if not isinstance(target_status_counts, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_target_status_counts_missing",
            "The selected workflow receipt is missing Candidate B target status counts.",
            http_status=409,
        )
    candidate_b_counts = _candidate_b_target_status_counts(target_status_counts)
    eligible_pdf_count = int(candidate_b_counts.get("recommended") or 0)
    failed_pdf_count = sum(
        count
        for status, count in candidate_b_counts.items()
        if status in {"failed", "error", "blocked"} or "fail" in status or "error" in status
    )
    skipped_pdf_count = sum(
        count
        for status, count in candidate_b_counts.items()
        if status != "recommended"
        and status not in {"failed", "error", "blocked"}
        and "fail" not in status
        and "error" not in status
    )
    skipped_pdf_count += max(corpus_pdf_count - sum(candidate_b_counts.values()), 0)
    summary = {
        "corpus_pdf_count": corpus_pdf_count,
        "eligible_pdf_count": eligible_pdf_count,
        "skipped_pdf_count": skipped_pdf_count,
        "failed_pdf_count": failed_pdf_count,
        "source_directory_eligible_file_count": source_directory_eligible_file_count,
        "source_directory_extra_material_file_count": max(source_directory_eligible_file_count - eligible_pdf_count, 0),
        "all_eligible_pdfs_processed": (
            eligible_pdf_count == corpus_pdf_count
            and skipped_pdf_count == 0
            and failed_pdf_count == 0
            and source_directory_eligible_file_count >= eligible_pdf_count
        ),
        "candidate_b_target_status_counts": candidate_b_counts,
    }
    supplied = corpus.get("eligibility_summary")
    if isinstance(supplied, Mapping) and supplied:
        mismatches = [
            {"field": key, "expected": value, "received": supplied.get(key)}
            for key, value in summary.items()
            if supplied.get(key) != value
        ]
        if mismatches:
            raise CandidateBFullCorpusOperatorWorkflowStatusError(
                "candidate_b_full_corpus_operator_workflow_eligibility_summary_mismatch",
                "The selected workflow receipt has a stale or contradictory eligibility summary.",
                http_status=409,
                details={"mismatches": mismatches},
            )
    if not summary["all_eligible_pdfs_processed"]:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_eligibility_not_complete",
            "The selected workflow receipt does not prove all eligible PDFs were processed without skipped or failed targets.",
            http_status=409,
            details={"eligibility_summary": summary},
        )
    return summary


def _candidate_b_target_status_counts(target_status_counts: Mapping[str, Any]) -> dict[str, int]:
    candidate_b = target_status_counts.get("candidate_b")
    if not isinstance(candidate_b, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_candidate_b_target_status_counts_missing",
            "The selected workflow receipt is missing Candidate B-specific target status counts.",
            http_status=409,
        )
    counts: dict[str, int] = {}
    for key in candidate_b:
        counts[str(key)] = _non_negative_int(candidate_b, key)
    return counts


def _workflow_baseline_rollback(receipt: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "available": True,
        "selector": "baseline",
        "explicit_document_processing_engine": "baseline",
        "depends_on_candidate_b_artifacts": False,
        "candidate_a_visual_lane_preserved": True,
        "rollback_requires_selector_mutation": False,
    }
    supplied = receipt.get("baseline_rollback")
    if not isinstance(supplied, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_baseline_rollback_missing",
            "The selected workflow receipt is missing baseline rollback evidence.",
            http_status=409,
        )
    mismatches = [
        {"field": key, "expected": value, "received": supplied.get(key)}
        for key, value in expected.items()
        if supplied.get(key) != value
    ]
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_baseline_rollback_mismatch",
            "The selected workflow receipt has stale or contradictory baseline rollback evidence.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return expected


def _workflow_layer3_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    layer3 = receipt.get("layer3")
    if not isinstance(layer3, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_layer3_missing",
            "The selected workflow receipt is missing Layer 3 status.",
            http_status=409,
        )
    required_statuses = {
        "source_directory_scan_status": {"available"},
        "downstream_proof_status": {"proven"},
    }
    mismatches = [
        {"field": field, "expected": sorted(expected), "received": layer3.get(field)}
        for field, expected in required_statuses.items()
        if layer3.get(field) not in expected
    ]
    if layer3.get("bridge_status") not in {"prepared", "already_prepared"}:
        mismatches.append(
            {
                "field": "bridge_status",
                "expected": ["already_prepared", "prepared"],
                "received": layer3.get("bridge_status"),
            }
        )
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_layer3_status_mismatch",
            "The selected workflow receipt does not prove the required Layer 3 downstream statuses.",
            http_status=409,
            details={"mismatches": mismatches},
        )
    return {
        "bridge_status": str(layer3.get("bridge_status") or ""),
        "source_directory_scan_status": str(layer3.get("source_directory_scan_status") or ""),
        "source_directory_eligible_file_count": _non_negative_int(layer3, "source_directory_eligible_file_count"),
        "qualitative_analysis_status": str(layer3.get("qualitative_analysis_status") or ""),
        "external_export_download_status": str(layer3.get("external_export_download_status") or ""),
        "same_origin_delivery_available": layer3.get("same_origin_delivery_available") is True,
        "provider_private_state": str(layer3.get("provider_private_state") or ""),
        "provider_private_revoke_state": str(layer3.get("provider_private_revoke_state") or ""),
        "internal_webhook_state": str(layer3.get("internal_webhook_state") or ""),
        "visual_lane_status": str(layer3.get("visual_lane_status") or ""),
        "downstream_proof_status": str(layer3.get("downstream_proof_status") or ""),
    }


def _workflow_artifact_family(receipt: Mapping[str, Any]) -> dict[str, Any]:
    artifact_family = receipt.get("artifact_family")
    if not isinstance(artifact_family, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_artifact_family_missing",
            "The selected workflow receipt is missing Candidate B artifact-family status.",
            http_status=409,
        )
    role_counts = artifact_family.get("role_counts")
    if not isinstance(role_counts, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_artifact_role_counts_missing",
            "The selected workflow receipt is missing Candidate B artifact-family role counts.",
            http_status=409,
        )
    return {
        "governed_retained_artifact_family_hash": str(
            artifact_family.get("governed_retained_artifact_family_hash") or ""
        ),
        "role_counts": dict(role_counts),
        "curated_file_count": _non_negative_int(artifact_family, "curated_file_count"),
        "text_file_count": _non_negative_int(artifact_family, "text_file_count"),
    }


def _workflow_runtime_root_lifecycle(receipt: Mapping[str, Any]) -> dict[str, Any]:
    lifecycle = receipt.get("runtime_root_lifecycle")
    if lifecycle is None:
        return {
            "available": False,
            "lifecycle_receipt_id": "",
            "lifecycle_receipt_hash": "",
            "runtime_parent_ref": "",
            "root_count": 0,
            "validate_only_triplet": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        }
    if not isinstance(lifecycle, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_invalid",
            "The selected workflow receipt has an invalid runtime-root lifecycle projection.",
            http_status=409,
        )
    schema_id = str(lifecycle.get("schema_id") or "")
    lifecycle_mode = str(lifecycle.get("lifecycle_mode") or "")
    if schema_id != RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID or lifecycle_mode != RUNTIME_ROOT_LIFECYCLE_MODE:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_mode_invalid",
            "The selected workflow receipt has a runtime-root lifecycle projection outside the admitted schema or mode.",
            http_status=409,
            details={
                "expected_schema_id": RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID,
                "expected_lifecycle_mode": RUNTIME_ROOT_LIFECYCLE_MODE,
            },
        )
    receipt_id = str(lifecycle.get("lifecycle_receipt_id") or "")
    _validate_storage_id(receipt_id, prefix="cb-full-corpus-runtime-roots")
    receipt_hash = str(lifecycle.get("lifecycle_receipt_hash") or "")
    if not re.fullmatch(r"[a-f0-9]{64}", receipt_hash):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_hash_invalid",
            "The selected workflow receipt has an invalid runtime-root lifecycle receipt hash.",
            http_status=409,
        )
    runtime_parent_ref = str(lifecycle.get("runtime_parent_ref") or "")
    if not runtime_parent_ref.startswith(("repo://", "redacted://")):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_ref_invalid",
            "The selected workflow receipt has an invalid runtime-root parent reference.",
            http_status=409,
        )
    root_count = _non_negative_int(lifecycle, "root_count")
    if root_count != 3:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_count_invalid",
            "Candidate B full-corpus runtime-root lifecycle receipts must bind baseline, Candidate A, and Candidate B.",
            http_status=409,
            details={"root_count": root_count},
        )
    if lifecycle.get("validate_only_triplet") is not True:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_not_validate_only",
            "Candidate B full-corpus runtime-root lifecycle receipts require validate-only triplet authority.",
            http_status=409,
        )
    if lifecycle.get("raw_local_path_exposed") is not False or lifecycle.get("raw_url_exposed") is not False:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_runtime_root_lifecycle_raw_authority",
            "Candidate B full-corpus runtime-root lifecycle receipts must not expose raw path or URL authority.",
            http_status=409,
        )
    return {
        "available": True,
        "schema_id": schema_id,
        "lifecycle_mode": lifecycle_mode,
        "lifecycle_receipt_id": receipt_id,
        "lifecycle_receipt_hash": receipt_hash,
        "runtime_parent_ref": runtime_parent_ref,
        "root_count": root_count,
        "validate_only_triplet": True,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
    }


def _retry_terminal_status_projection(
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    root = _workflow_receipt_root()
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in sorted(root.glob(f"{RETRY_COMPLETION_FAILURE_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=RETRY_COMPLETION_FAILURE_RECEIPT_PREFIX)
        receipt = _read_json_receipt(
            receipt_file,
            code="candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_unreadable",
            message="A Candidate B retry terminal receipt could not be read for status projection.",
        )
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            matches.append((receipt_id, receipt))
    if not matches:
        return _retry_terminal_not_recorded_projection()
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_ambiguous",
            "Candidate B workflow status found multiple retry terminal receipts for the selected workflow run.",
            http_status=409,
            details={
                "operator_workflow_receipt_id": operator_workflow_receipt_id,
                "retry_completion_failure_receipt_ids": [receipt_id for receipt_id, _receipt in matches],
            },
        )
    receipt_id, receipt = matches[0]
    return _validated_retry_terminal_projection(
        receipt_id,
        receipt,
        operator_workflow_receipt_id=operator_workflow_receipt_id,
        operator_workflow_receipt_hash=operator_workflow_receipt_hash,
    )


def _retry_terminal_not_recorded_projection() -> dict[str, Any]:
    return {
        "retry_terminal_projection_state": "not_recorded",
        "retry_terminal_status_projection_mode": RETRY_TERMINAL_STATUS_PROJECTION_MODE,
        "retry_terminal_status_projection_surfaces": ["status", "history"],
        "read_only_retry_terminal_projection": True,
        "retry_completion_failure_receipt_available": False,
        "retry_completion_failure_receipt_id": "",
        "retry_completion_failure_receipt_hash": "",
        "retry_completion_failure_authority_hash": "",
        "retry_worker_attempt_receipt_id": "",
        "retry_worker_attempt_authority_hash": "",
        "latest_retry_progress_checkpoint_receipt_id": "",
        "latest_retry_progress_checkpoint_authority_hash": "",
        "retry_terminal_outcome": "not_recorded",
        "retry_terminal_outcome_hash": "",
        "terminal_failure_code": "",
        "terminal_failure_phase": "",
        "missing_retry_terminal_receipt_projects_not_recorded": True,
        "stale_retry_terminal_receipt_rejected": True,
        "ambiguous_retry_terminal_receipt_rejected": True,
        "retry_terminal_failure_payload_operator_safe": True,
        "operator_safe_retry_terminal_failure_code_visible": False,
        "operator_safe_retry_terminal_failure_phase_visible": False,
        "retry_terminal_receipt_creation_admitted_now": False,
        "retry_completion_failure_receipt_mutation_admitted": False,
        "retry_progress_checkpoint_receipt_mutation_admitted": False,
        "retry_worker_attempt_receipt_mutation_admitted": False,
        "retry_scheduler_lease_receipt_mutation_admitted": False,
        "retry_queue_state_receipt_mutation_admitted": False,
        "retry_policy_receipt_mutation_admitted": False,
        "completion_failure_receipt_mutation_admitted": False,
        "failed_worker_attempt_receipt_mutation_admitted": False,
        "progress_checkpoint_receipt_mutation_admitted": False,
        "scheduler_lease_receipt_mutation_admitted": False,
        "queue_state_receipt_mutation_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "retry_terminal_status_projection_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _validated_retry_terminal_projection(
    receipt_id: str,
    receipt: Mapping[str, Any],
    *,
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    expected = {
        "schema_id": RETRY_COMPLETION_FAILURE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": RETRY_COMPLETION_FAILURE_MODE,
        "operator_decision": "record_candidate_b_async_retry_completion_failure",
        "status": "available",
        "retry_completion_failure_state": "retry_completion_failure_recorded",
        "retry_completion_failure_receipt_id": receipt_id,
        "operator_workflow_receipt_id": operator_workflow_receipt_id,
        "operator_workflow_receipt_hash": operator_workflow_receipt_hash,
        "append_only_retry_completion_failure_receipt": True,
        "exclusive_retry_terminal_receipt_per_retry_worker_attempt": True,
        "retry_progress_checkpoint_receipt_mutated": False,
        "retry_worker_attempt_receipt_mutated": False,
        "retry_scheduler_lease_receipt_mutated": False,
        "retry_queue_state_receipt_mutated": False,
        "retry_policy_receipt_mutated": False,
        "completion_failure_receipt_mutated": False,
        "failed_worker_attempt_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "retry_completion_failure_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "retry_terminal_failure_payload_operator_safe": True,
    }
    mismatches = [
        {"field": field, "expected": expected_value, "received": receipt.get(field)}
        for field, expected_value in expected.items()
        if receipt.get(field) != expected_value
    ]
    receipt_hash = _stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"retry_completion_failure_receipt_hash", "server_time"}
        }
    )
    if receipt.get("retry_completion_failure_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "retry_completion_failure_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("retry_completion_failure_receipt_hash"),
            }
        )
    retry_terminal_outcome = str(receipt.get("retry_terminal_outcome") or "")
    if retry_terminal_outcome not in {"completed", "failed"}:
        mismatches.append(
            {
                "field": "retry_terminal_outcome",
                "expected": ["completed", "failed"],
                "received": retry_terminal_outcome,
            }
        )
    terminal_failure_code = receipt.get("terminal_failure_code")
    terminal_failure_phase = receipt.get("terminal_failure_phase")
    if retry_terminal_outcome == "completed" and (
        terminal_failure_code not in (None, "") or terminal_failure_phase not in (None, "")
    ):
        mismatches.append(
            {
                "field": "terminal_failure_code/terminal_failure_phase",
                "expected": None,
                "received": [terminal_failure_code, terminal_failure_phase],
            }
        )
    if retry_terminal_outcome == "failed":
        for field, value in {
            "terminal_failure_code": terminal_failure_code,
            "terminal_failure_phase": terminal_failure_phase,
        }.items():
            if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9_-]{1,80}", value):
                mismatches.append(
                    {
                        "field": field,
                        "expected": "operator-safe lowercase token",
                        "received": value,
                    }
                )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_mismatch",
            "The selected Candidate B retry terminal receipt is stale or contradictory.",
            http_status=409,
            details={"retry_completion_failure_receipt_id": receipt_id, "mismatches": mismatches},
        )
    return {
        "retry_terminal_projection_state": retry_terminal_outcome,
        "retry_terminal_status_projection_mode": RETRY_TERMINAL_STATUS_PROJECTION_MODE,
        "retry_terminal_status_projection_surfaces": ["status", "history"],
        "read_only_retry_terminal_projection": True,
        "retry_completion_failure_receipt_available": True,
        "retry_completion_failure_receipt_id": receipt_id,
        "retry_completion_failure_receipt_hash": receipt_hash,
        "retry_completion_failure_authority_hash": str(
            receipt["retry_completion_failure_authority_hash"]
        ),
        "retry_worker_attempt_receipt_id": str(receipt["retry_worker_attempt_receipt_id"]),
        "retry_worker_attempt_authority_hash": str(receipt["retry_worker_attempt_authority_hash"]),
        "latest_retry_progress_checkpoint_receipt_id": str(
            receipt["latest_retry_progress_checkpoint_receipt_id"]
        ),
        "latest_retry_progress_checkpoint_authority_hash": str(
            receipt["latest_retry_progress_checkpoint_authority_hash"]
        ),
        "retry_terminal_outcome": retry_terminal_outcome,
        "retry_terminal_outcome_hash": str(receipt["retry_terminal_outcome_hash"]),
        "terminal_failure_code": str(terminal_failure_code or ""),
        "terminal_failure_phase": str(terminal_failure_phase or ""),
        "missing_retry_terminal_receipt_projects_not_recorded": True,
        "stale_retry_terminal_receipt_rejected": True,
        "ambiguous_retry_terminal_receipt_rejected": True,
        "retry_terminal_failure_payload_operator_safe": True,
        "operator_safe_retry_terminal_failure_code_visible": retry_terminal_outcome == "failed",
        "operator_safe_retry_terminal_failure_phase_visible": retry_terminal_outcome == "failed",
        "retry_terminal_receipt_creation_admitted_now": False,
        "retry_completion_failure_receipt_mutation_admitted": False,
        "retry_progress_checkpoint_receipt_mutation_admitted": False,
        "retry_worker_attempt_receipt_mutation_admitted": False,
        "retry_scheduler_lease_receipt_mutation_admitted": False,
        "retry_queue_state_receipt_mutation_admitted": False,
        "retry_policy_receipt_mutation_admitted": False,
        "completion_failure_receipt_mutation_admitted": False,
        "failed_worker_attempt_receipt_mutation_admitted": False,
        "progress_checkpoint_receipt_mutation_admitted": False,
        "scheduler_lease_receipt_mutation_admitted": False,
        "queue_state_receipt_mutation_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "retry_terminal_status_projection_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "cancel_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _execution_boundary_projection(
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    root = _workflow_receipt_root()
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in sorted(root.glob(f"{EXECUTION_BOUNDARY_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=EXECUTION_BOUNDARY_RECEIPT_PREFIX)
        receipt = _read_json_receipt(
            receipt_file,
            code="candidate_b_full_corpus_operator_workflow_status_execution_boundary_receipt_unreadable",
            message="A Candidate B execution-boundary receipt could not be read for status projection.",
        )
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            matches.append((receipt_id, receipt))
    if not matches:
        return _execution_boundary_not_started_projection()
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_execution_boundary_conflict",
            "The selected Candidate B workflow has multiple execution-boundary receipts.",
            http_status=409,
            details={
                "operator_workflow_receipt_id": operator_workflow_receipt_id,
                "execution_boundary_receipt_ids": [receipt_id for receipt_id, _receipt in matches],
            },
        )
    receipt_id, receipt = matches[0]
    return _validated_execution_boundary_projection(
        receipt_id,
        receipt,
        operator_workflow_receipt_id=operator_workflow_receipt_id,
        operator_workflow_receipt_hash=operator_workflow_receipt_hash,
    )


def _execution_boundary_not_started_projection() -> dict[str, Any]:
    return {
        "execution_boundary_projection_state": "not_started",
        "execution_boundary_status_projection_mode": EXECUTION_BOUNDARY_STATUS_PROJECTION_MODE,
        "execution_boundary_status_projection_surfaces": ["status", "history"],
        "read_only_execution_boundary_projection": True,
        "execution_boundary_receipt_available": False,
        "execution_boundary_receipt_id": "",
        "execution_boundary_receipt_hash": "",
        "execution_boundary_authority_hash": "",
        "terminal_projection_visibility": False,
        "execution_boundary_runtime_selected": False,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "queue_state_receipt_mutation_admitted": False,
        "scheduler_lease_receipt_mutation_admitted": False,
        "worker_attempt_receipt_mutation_admitted": False,
        "progress_checkpoint_receipt_mutation_admitted": False,
        "completion_failure_receipt_mutation_admitted": False,
        "retry_completion_failure_receipt_mutation_admitted": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _validated_execution_boundary_projection(
    receipt_id: str,
    receipt: Mapping[str, Any],
    *,
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    expected = {
        "schema_id": EXECUTION_BOUNDARY_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": EXECUTION_BOUNDARY_MODE,
        "operator_decision": "record_candidate_b_async_background_job_execution_boundary",
        "status": "available",
        "execution_boundary_state": "boundary_recorded",
        "execution_boundary_receipt_id": receipt_id,
        "operator_workflow_receipt_id": operator_workflow_receipt_id,
        "operator_workflow_receipt_hash": operator_workflow_receipt_hash,
        "append_only_execution_boundary_receipt": True,
        "source_run_receipt_mutated": False,
        "queue_state_receipt_mutated": False,
        "scheduler_lease_receipt_mutated": False,
        "worker_attempt_receipt_mutated": False,
        "progress_checkpoint_receipt_mutated": False,
        "completion_failure_receipt_mutated": False,
        "retry_completion_failure_receipt_mutated": False,
        "execution_boundary_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
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
    receipt_hash = _stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"execution_boundary_receipt_hash", "server_time"}
        }
    )
    if receipt.get("execution_boundary_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "execution_boundary_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("execution_boundary_receipt_hash"),
            }
        )
    boundary = receipt.get("execution_boundary")
    if not isinstance(boundary, Mapping):
        mismatches.append({"field": "execution_boundary", "expected": "object", "received": type(boundary).__name__})
    elif boundary.get("terminal_projection_visibility") is not True:
        mismatches.append(
            {
                "field": "execution_boundary.terminal_projection_visibility",
                "expected": True,
                "received": boundary.get("terminal_projection_visibility"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_execution_boundary_mismatch",
            "The selected Candidate B execution-boundary receipt is stale or contradictory.",
            http_status=409,
            details={"execution_boundary_receipt_id": receipt_id, "mismatches": mismatches},
        )
    boundary = boundary if isinstance(boundary, Mapping) else {}
    return {
        "execution_boundary_projection_state": "boundary_recorded",
        "execution_boundary_status_projection_mode": EXECUTION_BOUNDARY_STATUS_PROJECTION_MODE,
        "execution_boundary_status_projection_surfaces": ["status", "history"],
        "read_only_execution_boundary_projection": True,
        "execution_boundary_receipt_available": True,
        "execution_boundary_receipt_id": receipt_id,
        "execution_boundary_receipt_hash": receipt_hash,
        "execution_boundary_authority_hash": str(receipt["execution_boundary_authority_hash"]),
        "scheduler_lease_receipt_id": str(boundary.get("scheduler_lease_receipt_id") or ""),
        "worker_attempt_receipt_id": str(boundary.get("worker_attempt_receipt_id") or ""),
        "latest_progress_checkpoint_receipt_id": str(
            boundary.get("latest_progress_checkpoint_receipt_id") or ""
        ),
        "completion_failure_receipt_id": str(boundary.get("completion_failure_receipt_id") or ""),
        "retry_completion_failure_receipt_id": str(boundary.get("retry_completion_failure_receipt_id") or ""),
        "retry_terminal_projection_state": str(boundary.get("retry_terminal_projection_state") or ""),
        "terminal_projection_visibility": boundary.get("terminal_projection_visibility") is True,
        "execution_boundary_runtime_selected": True,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "queue_state_receipt_mutation_admitted": False,
        "scheduler_lease_receipt_mutation_admitted": False,
        "worker_attempt_receipt_mutation_admitted": False,
        "progress_checkpoint_receipt_mutation_admitted": False,
        "completion_failure_receipt_mutation_admitted": False,
        "retry_completion_failure_receipt_mutation_admitted": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _process_execution_projection(
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    root = _workflow_receipt_root()
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in sorted(root.glob(f"{PROCESS_EXECUTION_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=PROCESS_EXECUTION_RECEIPT_PREFIX)
        receipt = _read_json_receipt(
            receipt_file,
            code="candidate_b_full_corpus_operator_workflow_status_process_execution_receipt_unreadable",
            message="A Candidate B process-execution receipt could not be read for status projection.",
        )
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            matches.append((receipt_id, receipt))
    if not matches:
        return _process_execution_not_started_projection()
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_process_execution_conflict",
            "The selected Candidate B workflow has multiple process-execution receipts.",
            http_status=409,
            details={
                "operator_workflow_receipt_id": operator_workflow_receipt_id,
                "process_execution_receipt_ids": [receipt_id for receipt_id, _receipt in matches],
            },
        )
    receipt_id, receipt = matches[0]
    return _validated_process_execution_projection(
        receipt_id,
        receipt,
        operator_workflow_receipt_id=operator_workflow_receipt_id,
        operator_workflow_receipt_hash=operator_workflow_receipt_hash,
    )


def _process_execution_not_started_projection() -> dict[str, Any]:
    return {
        "process_execution_projection_state": "not_started",
        "process_execution_status_projection_mode": PROCESS_EXECUTION_STATUS_PROJECTION_MODE,
        "process_execution_status_projection_surfaces": ["status", "history"],
        "read_only_process_execution_projection": True,
        "process_execution_receipt_available": False,
        "process_execution_receipt_id": "",
        "process_execution_receipt_hash": "",
        "process_execution_authority_hash": "",
        "process_invocation_hash": "",
        "allowlisted_command_family": "",
        "redacted_process_ref": "",
        "server_process_handle_hash": "",
        "background_process_runtime_selected": False,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "execution_boundary_receipt_mutation_admitted": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _validated_process_execution_projection(
    receipt_id: str,
    receipt: Mapping[str, Any],
    *,
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    process_execution_state = str(receipt.get("process_execution_state") or "")
    if process_execution_state not in {"started", "blocked"}:
        mismatches = [
            {
                "field": "process_execution_state",
                "expected": "started|blocked",
                "received": receipt.get("process_execution_state"),
            }
        ]
    else:
        mismatches = []
    expected_status = "blocked" if process_execution_state == "blocked" else "available"
    expected_process_started = process_execution_state == "started"
    expected_subprocess_spawn = process_execution_state == "started"
    expected = {
        "schema_id": PROCESS_EXECUTION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_EXECUTION_MODE,
        "operator_decision": "record_candidate_b_async_background_process_execution",
        "status": expected_status,
        "process_execution_receipt_id": receipt_id,
        "operator_workflow_receipt_id": operator_workflow_receipt_id,
        "operator_workflow_receipt_hash": operator_workflow_receipt_hash,
        "allowlisted_command_family": "tools/run_candidate_b_full_corpus_operator_workflow.py",
        "append_only_process_execution_receipt": True,
        "process_started": expected_process_started,
        "source_run_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
        "background_process_runtime_selected": True,
        "background_process_runtime_selected_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": expected_subprocess_spawn,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    mismatches.extend(
        [
            {"field": field, "expected": expected_value, "received": receipt.get(field)}
            for field, expected_value in expected.items()
            if receipt.get(field) != expected_value
        ]
    )
    failure_code = str(receipt.get("process_failure_code") or "")
    if process_execution_state == "blocked":
        expected_timeout = (
            failure_code
            == "candidate_b_full_corpus_operator_workflow_process_execution_launch_timeout"
        )
        blocked_expected = {
            "process_failure_recorded": True,
            "process_timeout_recorded": expected_timeout,
            "process_failure_phase": "server_owned_process_launch",
        }
        mismatches.extend(
            [
                {"field": field, "expected": expected_value, "received": receipt.get(field)}
                for field, expected_value in blocked_expected.items()
                if receipt.get(field) != expected_value
            ]
        )
        if failure_code not in {
            "candidate_b_full_corpus_operator_workflow_process_execution_launch_failed",
            "candidate_b_full_corpus_operator_workflow_process_execution_launch_timeout",
        }:
            mismatches.append(
                {
                    "field": "process_failure_code",
                    "expected": "launch_failed|launch_timeout",
                    "received": receipt.get("process_failure_code"),
                }
            )
        summary_hash = str(receipt.get("redacted_failure_summary_hash") or "")
        if len(summary_hash) != 64 or any(char not in "0123456789abcdef" for char in summary_hash):
            mismatches.append(
                {
                    "field": "redacted_failure_summary_hash",
                    "expected": "lowercase_sha256_hex",
                    "received": receipt.get("redacted_failure_summary_hash"),
                }
            )
    else:
        started_failure_fields = {
            "process_failure_recorded": False,
            "process_timeout_recorded": False,
            "process_failure_code": "",
            "process_failure_phase": "",
            "redacted_failure_summary_hash": "",
        }
        for field, expected_value in started_failure_fields.items():
            received = receipt.get(field, expected_value)
            if received != expected_value:
                mismatches.append({"field": field, "expected": expected_value, "received": received})
    receipt_hash = _stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"process_execution_receipt_hash", "server_time"}
        }
    )
    if receipt.get("process_execution_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_execution_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_execution_receipt_hash"),
            }
        )
    redacted_projection = receipt.get("redacted_process_status_projection")
    if not isinstance(redacted_projection, Mapping):
        mismatches.append(
            {
                "field": "redacted_process_status_projection",
                "expected": "object",
                "received": type(redacted_projection).__name__,
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_process_execution_mismatch",
            "The selected Candidate B process-execution receipt is stale or contradictory.",
            http_status=409,
            details={"process_execution_receipt_id": receipt_id, "mismatches": mismatches},
        )
    return {
        "process_execution_projection_state": process_execution_state,
        "process_execution_status_projection_mode": PROCESS_EXECUTION_STATUS_PROJECTION_MODE,
        "process_execution_status_projection_surfaces": ["status", "history"],
        "read_only_process_execution_projection": True,
        "process_execution_receipt_available": True,
        "process_execution_receipt_id": receipt_id,
        "process_execution_receipt_hash": receipt_hash,
        "process_execution_authority_hash": str(receipt["process_execution_authority_hash"]),
        "execution_boundary_receipt_id": str(receipt["execution_boundary_receipt_id"]),
        "execution_boundary_receipt_hash": str(receipt["execution_boundary_receipt_hash"]),
        "execution_boundary_authority_hash": str(receipt["execution_boundary_authority_hash"]),
        "process_invocation_hash": str(receipt["process_invocation_hash"]),
        "allowlisted_command_family": str(receipt["allowlisted_command_family"]),
        "redacted_process_ref": str(receipt["redacted_process_ref"]),
        "server_process_handle_hash": str(receipt["server_process_handle_hash"]),
        "background_process_runtime_selected": True,
        "background_process_runtime_selected_now": True,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": expected_subprocess_spawn,
        "actual_corpus_processing_execution_admitted_now": False,
        "browser_triggered_process_start_admitted": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "execution_boundary_receipt_mutation_admitted": False,
        "cancel_runtime_selected_now": False,
        "retry_runtime_selected_now": False,
        "resume_runtime_selected_now": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
        "process_failure_recorded": bool(receipt.get("process_failure_recorded", False)),
        "process_timeout_recorded": bool(receipt.get("process_timeout_recorded", False)),
        "process_failure_code": str(receipt.get("process_failure_code") or ""),
        "process_failure_phase": str(receipt.get("process_failure_phase") or ""),
        "redacted_failure_summary_hash": str(receipt.get("redacted_failure_summary_hash") or ""),
    }


def _process_completion_result_projection(
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    root = _workflow_receipt_root()
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in sorted(root.glob(f"{PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=PROCESS_COMPLETION_RESULT_RECEIPT_PREFIX)
        receipt = _read_json_receipt(
            receipt_file,
            code="candidate_b_full_corpus_operator_workflow_status_process_completion_result_receipt_unreadable",
            message="A Candidate B process completion/result receipt could not be read for status projection.",
        )
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            matches.append((receipt_id, receipt))
    if not matches:
        return _process_completion_result_not_recorded_projection()
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_process_completion_result_conflict",
            "The selected Candidate B workflow has multiple process completion/result receipts.",
            http_status=409,
            details={
                "operator_workflow_receipt_id": operator_workflow_receipt_id,
                "process_completion_result_receipt_ids": [receipt_id for receipt_id, _receipt in matches],
            },
        )
    receipt_id, receipt = matches[0]
    return _validated_process_completion_result_projection(
        receipt_id,
        receipt,
        operator_workflow_receipt_id=operator_workflow_receipt_id,
        operator_workflow_receipt_hash=operator_workflow_receipt_hash,
    )


def _process_completion_result_not_recorded_projection() -> dict[str, Any]:
    return {
        "process_completion_result_projection_state": "not_recorded",
        "process_completion_result_status_projection_mode": PROCESS_COMPLETION_RESULT_STATUS_PROJECTION_MODE,
        "process_completion_result_status_projection_surfaces": ["status", "history"],
        "read_only_process_completion_result_projection": True,
        "process_completion_result_receipt_available": False,
        "process_completion_result_receipt_id": "",
        "process_completion_result_receipt_hash": "",
        "process_completion_result_authority_hash": "",
        "process_execution_receipt_id": "",
        "process_execution_authority_hash": "",
        "terminal_state": "",
        "result_workflow_receipt_id": "",
        "result_workflow_receipt_hash": "",
        "result_authority_hash": "",
        "result_status_request_hash": "",
        "result_downstream_proof_hash": "",
        "terminal_failure_code": "",
        "terminal_failure_phase": "",
        "redacted_failure_summary_hash": "",
        "process_completion_result_runtime_selected": False,
        "result_adoption_runtime_selected": False,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "process_execution_receipt_mutation_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _validated_process_completion_result_projection(
    receipt_id: str,
    receipt: Mapping[str, Any],
    *,
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    expected = {
        "schema_id": PROCESS_COMPLETION_RESULT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROCESS_COMPLETION_RESULT_MODE,
        "operator_decision": "record_candidate_b_async_process_completion_result_adoption",
        "status": "available",
        "process_completion_result_receipt_id": receipt_id,
        "operator_workflow_receipt_id": operator_workflow_receipt_id,
        "operator_workflow_receipt_hash": operator_workflow_receipt_hash,
        "append_only_process_completion_result_receipt": True,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "execution_boundary_receipt_mutated": False,
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": value, "received": receipt.get(field)}
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    receipt_hash = _stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"process_completion_result_receipt_hash", "server_time"}
        }
    )
    if receipt.get("process_completion_result_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "process_completion_result_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("process_completion_result_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_process_completion_result_mismatch",
            "The selected Candidate B process completion/result receipt is stale or contradictory.",
            http_status=409,
            details={"process_completion_result_receipt_id": receipt_id, "mismatches": mismatches},
        )
    return {
        "process_completion_result_projection_state": str(receipt["terminal_state"]),
        "process_completion_result_status_projection_mode": PROCESS_COMPLETION_RESULT_STATUS_PROJECTION_MODE,
        "process_completion_result_status_projection_surfaces": ["status", "history"],
        "read_only_process_completion_result_projection": True,
        "process_completion_result_receipt_available": True,
        "process_completion_result_receipt_id": receipt_id,
        "process_completion_result_receipt_hash": receipt_hash,
        "process_completion_result_authority_hash": str(receipt["process_completion_result_authority_hash"]),
        "process_execution_receipt_id": str(receipt["process_execution_receipt_id"]),
        "process_execution_receipt_hash": str(receipt["process_execution_receipt_hash"]),
        "process_execution_authority_hash": str(receipt["process_execution_authority_hash"]),
        "terminal_state": str(receipt["terminal_state"]),
        "result_workflow_receipt_id": str(receipt["result_workflow_receipt_id"]),
        "result_workflow_receipt_hash": str(receipt["result_workflow_receipt_hash"]),
        "result_authority_hash": str(receipt["result_authority_hash"]),
        "result_status_request_hash": str(receipt["result_status_request_hash"]),
        "result_downstream_proof_hash": str(receipt["result_downstream_proof_hash"]),
        "terminal_failure_code": str(receipt["terminal_failure_code"]),
        "terminal_failure_phase": str(receipt["terminal_failure_phase"]),
        "redacted_failure_summary_hash": str(receipt["redacted_failure_summary_hash"]),
        "process_completion_result_runtime_selected": True,
        "result_adoption_runtime_selected": bool(receipt["result_adoption_runtime_selected"]),
        "background_process_runtime_selected_now": False,
        "job_execution_runtime_selected_now": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "source_run_receipt_mutation_admitted": False,
        "process_execution_receipt_mutation_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _adopted_result_downstream_proof_projection(
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    root = _workflow_receipt_root()
    matches: list[tuple[str, dict[str, Any]]] = []
    for receipt_file in sorted(root.glob(f"{ADOPTED_RESULT_DOWNSTREAM_PROOF_RECEIPT_PREFIX}-*/receipt.json")):
        receipt_id = receipt_file.parent.name
        _validate_storage_id(receipt_id, prefix=ADOPTED_RESULT_DOWNSTREAM_PROOF_RECEIPT_PREFIX)
        receipt = _read_json_receipt(
            receipt_file,
            code="candidate_b_full_corpus_operator_workflow_status_adopted_result_downstream_proof_receipt_unreadable",
            message="A Candidate B adopted-result downstream proof receipt could not be read for status projection.",
        )
        if receipt.get("operator_workflow_receipt_id") == operator_workflow_receipt_id:
            matches.append((receipt_id, receipt))
    if not matches:
        return _adopted_result_downstream_proof_not_recorded_projection()
    if len(matches) > 1:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_adopted_result_downstream_proof_conflict",
            "The selected Candidate B workflow has multiple adopted-result downstream proof receipts.",
            http_status=409,
            details={
                "operator_workflow_receipt_id": operator_workflow_receipt_id,
                "adopted_result_downstream_proof_receipt_ids": [
                    receipt_id for receipt_id, _receipt in matches
                ],
            },
        )
    receipt_id, receipt = matches[0]
    return _validated_adopted_result_downstream_proof_projection(
        receipt_id,
        receipt,
        operator_workflow_receipt_id=operator_workflow_receipt_id,
        operator_workflow_receipt_hash=operator_workflow_receipt_hash,
    )


def _adopted_result_downstream_proof_not_recorded_projection() -> dict[str, Any]:
    return {
        "adopted_result_downstream_proof_projection_state": "not_recorded",
        "adopted_result_downstream_proof_status_projection_mode": (
            ADOPTED_RESULT_DOWNSTREAM_PROOF_STATUS_PROJECTION_MODE
        ),
        "adopted_result_downstream_proof_status_projection_surfaces": ["status", "history"],
        "read_only_adopted_result_downstream_proof_projection": True,
        "adopted_result_downstream_proof_receipt_available": False,
        "adopted_result_downstream_proof_receipt_id": "",
        "adopted_result_downstream_proof_receipt_hash": "",
        "adopted_result_downstream_proof_authority_hash": "",
        "process_completion_result_receipt_id": "",
        "process_completion_result_authority_hash": "",
        "result_workflow_receipt_id": "",
        "result_workflow_receipt_hash": "",
        "result_status_request_hash": "",
        "result_downstream_proof_hash": "",
        "adopted_result_status_hash": "",
        "adopted_result_downstream_proof_status": "",
        "adopted_result_downstream_proof_runtime_selected": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "process_completion_result_receipt_mutation_admitted": False,
        "adopted_result_workflow_receipt_mutation_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _validated_adopted_result_downstream_proof_projection(
    receipt_id: str,
    receipt: Mapping[str, Any],
    *,
    operator_workflow_receipt_id: str,
    operator_workflow_receipt_hash: str,
) -> dict[str, Any]:
    expected = {
        "schema_id": ADOPTED_RESULT_DOWNSTREAM_PROOF_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE,
        "operator_decision": "record_candidate_b_async_adopted_process_result_downstream_operator_proof",
        "status": "available",
        "adopted_result_downstream_proof_state": "proven",
        "adopted_result_downstream_proof_receipt_id": receipt_id,
        "operator_workflow_receipt_id": operator_workflow_receipt_id,
        "operator_workflow_receipt_hash": operator_workflow_receipt_hash,
        "append_only_adopted_result_downstream_proof_receipt": True,
        "process_completion_result_receipt_mutated": False,
        "process_execution_receipt_mutated": False,
        "source_run_receipt_mutated": False,
        "adopted_result_workflow_receipt_mutated": False,
        "downstream_proof_receipt_mutated": False,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }
    mismatches = [
        {"field": field, "expected": value, "received": receipt.get(field)}
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    receipt_hash = _stable_hash(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"adopted_result_downstream_proof_receipt_hash", "server_time"}
        }
    )
    if receipt.get("adopted_result_downstream_proof_receipt_hash") != receipt_hash:
        mismatches.append(
            {
                "field": "adopted_result_downstream_proof_receipt_hash",
                "expected": receipt_hash,
                "received": receipt.get("adopted_result_downstream_proof_receipt_hash"),
            }
        )
    _assert_no_raw_authority_exposure(receipt)
    if mismatches:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_adopted_result_downstream_proof_mismatch",
            "The selected Candidate B adopted-result downstream proof receipt is stale or contradictory.",
            http_status=409,
            details={"adopted_result_downstream_proof_receipt_id": receipt_id, "mismatches": mismatches},
        )
    return {
        "adopted_result_downstream_proof_projection_state": "proven",
        "adopted_result_downstream_proof_status_projection_mode": (
            ADOPTED_RESULT_DOWNSTREAM_PROOF_STATUS_PROJECTION_MODE
        ),
        "adopted_result_downstream_proof_status_projection_surfaces": ["status", "history"],
        "read_only_adopted_result_downstream_proof_projection": True,
        "adopted_result_downstream_proof_receipt_available": True,
        "adopted_result_downstream_proof_receipt_id": receipt_id,
        "adopted_result_downstream_proof_receipt_hash": receipt_hash,
        "adopted_result_downstream_proof_authority_hash": str(
            receipt["adopted_result_downstream_proof_authority_hash"]
        ),
        "process_completion_result_receipt_id": str(receipt["process_completion_result_receipt_id"]),
        "process_completion_result_authority_hash": str(receipt["process_completion_result_authority_hash"]),
        "result_workflow_receipt_id": str(receipt["result_workflow_receipt_id"]),
        "result_workflow_receipt_hash": str(receipt["result_workflow_receipt_hash"]),
        "result_status_request_hash": str(receipt["result_status_request_hash"]),
        "result_downstream_proof_hash": str(receipt["result_downstream_proof_hash"]),
        "adopted_result_status_hash": str(receipt["adopted_result_status_hash"]),
        "adopted_result_downstream_proof_status": str(receipt["adopted_result_downstream_proof_status"]),
        "adopted_result_downstream_proof_runtime_selected": True,
        "actual_subprocess_spawn_admitted_now": False,
        "actual_corpus_processing_execution_admitted_now": False,
        "operator_supplied_command_admitted": False,
        "operator_supplied_local_path_admitted": False,
        "operator_supplied_raw_url_admitted": False,
        "process_completion_result_receipt_mutation_admitted": False,
        "adopted_result_workflow_receipt_mutation_admitted": False,
        "raw_stdout_admitted": False,
        "raw_stderr_admitted": False,
        "raw_exception_trace_admitted": False,
        "raw_log_excerpt_admitted": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "selector_mutation_performed": False,
    }


def _read_json_receipt(path: Path, *, code: str, message: str) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            code,
            message,
            http_status=409,
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_status_receipt_invalid",
            "Candidate B workflow status encountered a non-object receipt.",
            http_status=409,
        )
    return receipt


def _negative_invariants(receipt: Mapping[str, Any]) -> dict[str, bool]:
    invariants = receipt.get("negative_invariants")
    if not isinstance(invariants, Mapping):
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_negative_invariants_missing",
            "The selected workflow receipt is missing negative invariants.",
            http_status=409,
        )
    required_false = {
        "baseline_default_changed",
        "candidate_a_semantics_changed",
        "candidate_b_default_broadened_beyond_eligible_pdf",
        "raw_local_path_exposed",
        "raw_url_exposed",
        "provider_public_url_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "frontend_durable_authority_enabled",
        "full_mockup_activation_enabled",
    }
    violations = sorted(field for field in required_false if invariants.get(field) is not False)
    if violations:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_negative_invariant_violation",
            "The selected workflow receipt violates Candidate B operator workflow guardrails.",
            http_status=409,
            details={"violations": violations},
        )
    return {field: False for field in sorted(required_false)}


def _assert_no_raw_authority_exposure(value: Any) -> None:
    leaked = _find_raw_authority_exposure(value)
    if leaked:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_receipt_exposes_raw_authority",
            "The selected workflow receipt exposes raw local paths or raw URLs.",
            http_status=409,
            details={"field": leaked},
        )


def _find_raw_authority_exposure(value: Any, *, field: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            leaked = _find_raw_authority_exposure(item, field=f"{field}.{key}")
            if leaked:
                return leaked
        return None
    if isinstance(value, list):
        for index, item in enumerate(value):
            leaked = _find_raw_authority_exposure(item, field=f"{field}[{index}]")
            if leaked:
                return leaked
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.startswith(_ALLOWED_REF_SCHEMES):
        return None
    if re.search(r"\bhttps?://", text, flags=re.IGNORECASE) or re.search(r"\bfile://", text, flags=re.IGNORECASE):
        return field
    if re.search(r"\b[A-Za-z]:[\\/]", text):
        return field
    if re.search(
        r"(?<![A-Za-z0-9+.-]:)(?<!/)/(?:tmp|var|home|users|mnt|etc|usr|opt|private|volumes)(?:/|$)",
        text,
        flags=re.IGNORECASE,
    ):
        return field
    return None


def _non_negative_int(fields: Mapping[str, Any], key: str) -> int:
    value = fields.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CandidateBFullCorpusOperatorWorkflowStatusError(
            "candidate_b_full_corpus_operator_workflow_count_invalid",
            "The selected workflow receipt has an invalid non-negative count field.",
            http_status=409,
            details={"field": key, "received": value},
        )
    return value


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
