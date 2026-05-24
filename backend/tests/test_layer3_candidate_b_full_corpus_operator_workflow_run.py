from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from fastapi.testclient import TestClient
import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_candidate_b_full_corpus_operator_workflow_completion_failure as workflow_completion_failure
from app.services import layer3_candidate_b_full_corpus_operator_workflow_lifecycle as workflow_lifecycle
from app.services import layer3_candidate_b_full_corpus_operator_workflow_progress_checkpoint as workflow_progress_checkpoint
from app.services import layer3_candidate_b_full_corpus_operator_workflow_queue_state as workflow_queue_state
from app.services import layer3_candidate_b_full_corpus_operator_workflow_retry_policy as workflow_retry_policy
from app.services import layer3_candidate_b_full_corpus_operator_workflow_retry_queue_state as workflow_retry_queue_state
from app.services import layer3_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease as workflow_retry_scheduler_lease
from app.services import layer3_candidate_b_full_corpus_operator_workflow_retry_worker_attempt as workflow_retry_worker_attempt
from app.services import layer3_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint as workflow_retry_progress_checkpoint
from app.services import layer3_candidate_b_full_corpus_operator_workflow_retry_completion_failure as workflow_retry_completion_failure
from app.services import layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run
from app.services import layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease as workflow_scheduler_lease
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status
from app.services import layer3_candidate_b_full_corpus_operator_workflow_worker_attempt as workflow_worker_attempt
from main import app


RUN_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run"
STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status"
HISTORY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
LIFECYCLE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire"
QUEUE_STATE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state"
SCHEDULER_LEASE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease"
WORKER_ATTEMPT_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt"
PROGRESS_CHECKPOINT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint"
)
COMPLETION_FAILURE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure"
)
RETRY_POLICY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy"
RETRY_QUEUE_STATE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state"
)
RETRY_SCHEDULER_LEASE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease"
)
RETRY_WORKER_ATTEMPT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/worker/attempt"
)
RETRY_PROGRESS_CHECKPOINT_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/progress/checkpoint"
)
RETRY_COMPLETION_FAILURE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/completion/failure"
)
BASELINE_RUN_ID = "baseline-run"
CANDIDATE_A_RUN_ID = "candidate-a-run"
CANDIDATE_B_RUN_ID = "candidate-b-run"
BRIDGE_RECEIPT_ID = "cb-runtime-l3-aaaaaaaaaaaaaaaaaaaaaaaa"
DOWNSTREAM_PROOF_ID = "cb-runtime-downstream-proof-bbbbbbbbbbbbbbbbbbbbbbbb"
RUNTIME_ROOT_LIFECYCLE_RECEIPT_ID = "cb-full-corpus-runtime-roots-cccccccccccccccccccccccc"
COMPARE_TARGET_SET_HASH = "1" * 64
BRIDGE_RECEIPT_HASH = "2" * 64
DOWNSTREAM_PROOF_HASH = "3" * 64


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings,
        "layer3_candidate_b_full_corpus_operator_workflow_dir",
        str(tmp_path / "workflow-receipts"),
    )
    app.openapi_schema = None
    with TestClient(app) as test_client:
        yield test_client
    app.openapi_schema = None


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_source_receipt(extra: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    receipt_input = {
        "schema_id": workflow_status.WORKFLOW_SCHEMA_ID,
        "schema_version": workflow_status.SCHEMA_VERSION,
        "workflow_mode": workflow_status.WORKFLOW_MODE,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "compare_target_set_hash": COMPARE_TARGET_SET_HASH,
        "bridge_receipt_id": BRIDGE_RECEIPT_ID,
        "bridge_receipt_hash": BRIDGE_RECEIPT_HASH,
        "downstream_proof_id": DOWNSTREAM_PROOF_ID,
        "downstream_proof_hash": DOWNSTREAM_PROOF_HASH,
        "coverage_count": 17,
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        **receipt_input,
        "receipt_id": receipt_id,
        "receipt_hash": receipt_hash,
        "status": "proven",
        "server_time": "2026-05-23T00:00:00Z",
        "validate_only_triplet": True,
        "artifacts_seeded_or_generated_by_triplet_validator": False,
        "corpus": {
            "corpus_pdf_count": 69,
            "eligible_file_count": 71,
            "material_relative_name": "text/target-00001.md",
            "target_status_counts": {
                "baseline": {"recommended": 69},
                "candidate_a": {"recommended": 69},
                "candidate_b": {"recommended": 69},
            },
            "eligibility_summary": {
                "corpus_pdf_count": 69,
                "eligible_pdf_count": 69,
                "skipped_pdf_count": 0,
                "failed_pdf_count": 0,
                "source_directory_eligible_file_count": 71,
                "source_directory_extra_material_file_count": 2,
                "all_eligible_pdfs_processed": True,
                "candidate_b_target_status_counts": {"recommended": 69},
            },
        },
        "baseline_rollback": {
            "available": True,
            "selector": "baseline",
            "explicit_document_processing_engine": "baseline",
            "depends_on_candidate_b_artifacts": False,
            "candidate_a_visual_lane_preserved": True,
            "rollback_requires_selector_mutation": False,
        },
        "refs": {
            "baseline_runtime_root": "repo://artifacts/baseline",
            "candidate_a_runtime_root": "repo://artifacts/candidate-a",
            "candidate_b_runtime_root": "repo://artifacts/candidate-b",
            "bridge_dir": "repo://backend/app/storage_test_runtime/cb-full-corpus-operator-bridge",
            "curated_root": f"candidate-b-runtime-bridge://{BRIDGE_RECEIPT_ID}/curated",
            "receipt_dir": "repo://backend/app/storage_test_runtime/cb-full-corpus-operator-workflow",
        },
        "layer3": {
            "bridge_status": "prepared",
            "source_directory_scan_status": "available",
            "source_directory_eligible_file_count": 71,
            "qualitative_analysis_status": "completed",
            "external_export_download_status": "prepared",
            "same_origin_delivery_available": True,
            "provider_private_state": "provider_private_signed_url_ready",
            "provider_private_revoke_state": "provider_private_signed_url_revoked",
            "internal_webhook_state": "internal_webhook_dispatch_recorded",
            "visual_lane_status": "available",
            "downstream_proof_status": "proven",
        },
        "artifact_family": {
            "governed_retained_artifact_family_hash": "4" * 64,
            "role_counts": {
                "material_analysis_payloads": 71,
                "visual_page_evidence": 69,
                "provenance_audit_artifacts": 3,
                "product_inspection_artifacts": 69,
                "delivery_artifacts": 69,
            },
            "curated_file_count": 71,
            "text_file_count": 71,
        },
        "runtime_root_lifecycle": {
            "schema_id": workflow_status.RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID,
            "lifecycle_mode": workflow_status.RUNTIME_ROOT_LIFECYCLE_MODE,
            "lifecycle_receipt_id": RUNTIME_ROOT_LIFECYCLE_RECEIPT_ID,
            "lifecycle_receipt_hash": "5" * 64,
            "runtime_parent_ref": "redacted://sha256/runtime-parent",
            "root_count": 3,
            "receipt_file": "repo://backend/app/storage_test_runtime/lifecycle/receipt.json",
            "validate_only_triplet": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_broadened_beyond_eligible_pdf": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        },
    }
    if extra:
        receipt.update(extra)
    root = Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
    target = root / receipt_id / "receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt_id, receipt


def _run_request(**overrides: str) -> dict[str, str]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-run",
        "run_mode": workflow_run.RUN_MODE,
        "operator_decision": workflow_run.OPERATOR_DECISION,
        "runtime_root_lifecycle_receipt_id": RUNTIME_ROOT_LIFECYCLE_RECEIPT_ID,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "compare_target_set_hash": COMPARE_TARGET_SET_HASH,
        "material_relative_name": "text/target-00001.md",
    }
    payload.update(overrides)
    return payload


def _lifecycle_request(history: dict[str, Any], row: dict[str, Any], **overrides: str) -> dict[str, str]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-lifecycle",
        "lifecycle_mode": workflow_lifecycle.LIFECYCLE_MODE,
        "operator_decision": workflow_lifecycle.OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _queue_state_request(history: dict[str, Any], row: dict[str, Any], **overrides: str) -> dict[str, str]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-queue-state",
        "queue_state_mode": workflow_queue_state.QUEUE_STATE_MODE,
        "operator_decision": workflow_queue_state.OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _scheduler_lease_request(
    history: dict[str, Any],
    row: dict[str, Any],
    queue_state: dict[str, Any],
    **overrides: str,
) -> dict[str, str]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-scheduler-lease",
        "scheduler_lease_mode": workflow_scheduler_lease.SCHEDULER_LEASE_MODE,
        "operator_decision": workflow_scheduler_lease.OPERATOR_DECISION,
        "queue_state_receipt_id": queue_state["queue_state_receipt_id"],
        "queue_state_receipt_hash": queue_state["queue_state_receipt_hash"],
        "queue_state_authority_hash": queue_state["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _worker_attempt_request(
    history: dict[str, Any],
    row: dict[str, Any],
    scheduler_lease_body: dict[str, Any],
    **overrides: str,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-worker-attempt",
        "worker_attempt_mode": workflow_worker_attempt.WORKER_ATTEMPT_MODE,
        "operator_decision": workflow_worker_attempt.OPERATOR_DECISION,
        "worker_attempt_number": workflow_worker_attempt.WORKER_ATTEMPT_NUMBER,
        "scheduler_lease_receipt_id": scheduler_lease_body["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": scheduler_lease_body["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": scheduler_lease_body["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": scheduler_lease_body["queue_state_receipt_id"],
        "queue_state_receipt_hash": scheduler_lease_body["queue_state_receipt_hash"],
        "queue_state_authority_hash": scheduler_lease_body["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _progress_checkpoint_request(
    history: dict[str, Any],
    row: dict[str, Any],
    worker_attempt_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-progress-checkpoint",
        "progress_checkpoint_mode": workflow_progress_checkpoint.PROGRESS_CHECKPOINT_MODE,
        "operator_decision": workflow_progress_checkpoint.OPERATOR_DECISION,
        "progress_checkpoint_sequence": 1,
        "worker_attempt_receipt_id": worker_attempt_body["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": worker_attempt_body["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": worker_attempt_body["worker_attempt_authority_hash"],
        "scheduler_lease_receipt_id": worker_attempt_body["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": worker_attempt_body["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": worker_attempt_body["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": worker_attempt_body["queue_state_receipt_id"],
        "queue_state_receipt_hash": worker_attempt_body["queue_state_receipt_hash"],
        "queue_state_authority_hash": worker_attempt_body["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _completion_failure_request(
    history: dict[str, Any],
    row: dict[str, Any],
    progress_checkpoint_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-completion-failure",
        "completion_failure_mode": workflow_completion_failure.COMPLETION_FAILURE_MODE,
        "operator_decision": workflow_completion_failure.OPERATOR_DECISION,
        "terminal_outcome": "completed",
        "latest_progress_checkpoint_receipt_id": progress_checkpoint_body["progress_checkpoint_receipt_id"],
        "latest_progress_checkpoint_receipt_hash": progress_checkpoint_body["progress_checkpoint_receipt_hash"],
        "latest_progress_checkpoint_authority_hash": progress_checkpoint_body["progress_checkpoint_authority_hash"],
        "progress_checkpoint_sequence": progress_checkpoint_body["progress_checkpoint_sequence"],
        "worker_attempt_receipt_id": progress_checkpoint_body["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": progress_checkpoint_body["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": progress_checkpoint_body["worker_attempt_authority_hash"],
        "scheduler_lease_receipt_id": progress_checkpoint_body["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": progress_checkpoint_body["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": progress_checkpoint_body["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": progress_checkpoint_body["queue_state_receipt_id"],
        "queue_state_receipt_hash": progress_checkpoint_body["queue_state_receipt_hash"],
        "queue_state_authority_hash": progress_checkpoint_body["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _retry_policy_request(
    history: dict[str, Any],
    row: dict[str, Any],
    completion_failure_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-retry-policy",
        "retry_policy_mode": workflow_retry_policy.RETRY_POLICY_MODE,
        "operator_decision": workflow_retry_policy.OPERATOR_DECISION,
        "retry_policy_result": "eligible",
        "retry_policy_reason": "operator_safe_retryable_failure",
        "completion_failure_receipt_id": completion_failure_body["completion_failure_receipt_id"],
        "completion_failure_receipt_hash": completion_failure_body["completion_failure_receipt_hash"],
        "completion_failure_authority_hash": completion_failure_body["completion_failure_authority_hash"],
        "terminal_outcome": completion_failure_body["terminal_outcome"],
        "terminal_outcome_hash": completion_failure_body["terminal_outcome_hash"],
        "latest_progress_checkpoint_receipt_id": completion_failure_body["latest_progress_checkpoint_receipt_id"],
        "latest_progress_checkpoint_receipt_hash": completion_failure_body["latest_progress_checkpoint_receipt_hash"],
        "latest_progress_checkpoint_authority_hash": completion_failure_body["latest_progress_checkpoint_authority_hash"],
        "progress_checkpoint_sequence": completion_failure_body["progress_checkpoint_sequence"],
        "worker_attempt_receipt_id": completion_failure_body["worker_attempt_receipt_id"],
        "worker_attempt_receipt_hash": completion_failure_body["worker_attempt_receipt_hash"],
        "worker_attempt_authority_hash": completion_failure_body["worker_attempt_authority_hash"],
        "scheduler_lease_receipt_id": completion_failure_body["scheduler_lease_receipt_id"],
        "scheduler_lease_receipt_hash": completion_failure_body["scheduler_lease_receipt_hash"],
        "scheduler_lease_authority_hash": completion_failure_body["scheduler_lease_authority_hash"],
        "queue_state_receipt_id": completion_failure_body["queue_state_receipt_id"],
        "queue_state_receipt_hash": completion_failure_body["queue_state_receipt_hash"],
        "queue_state_authority_hash": completion_failure_body["queue_state_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _retry_queue_state_request(
    history: dict[str, Any],
    row: dict[str, Any],
    retry_policy_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-retry-queue-state",
        "retry_queue_state_mode": workflow_retry_queue_state.RETRY_QUEUE_STATE_MODE,
        "operator_decision": workflow_retry_queue_state.OPERATOR_DECISION,
        "retry_policy_receipt_id": retry_policy_body["retry_policy_receipt_id"],
        "retry_policy_receipt_hash": retry_policy_body["retry_policy_receipt_hash"],
        "retry_policy_authority_hash": retry_policy_body["retry_policy_authority_hash"],
        "retry_policy_result": retry_policy_body["retry_policy_result"],
        "completion_failure_receipt_id": retry_policy_body["completion_failure_receipt_id"],
        "completion_failure_receipt_hash": retry_policy_body["completion_failure_receipt_hash"],
        "completion_failure_authority_hash": retry_policy_body["completion_failure_authority_hash"],
        "failed_worker_attempt_receipt_id": retry_policy_body["worker_attempt_receipt_id"],
        "failed_worker_attempt_authority_hash": retry_policy_body["worker_attempt_authority_hash"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _retry_scheduler_lease_request(
    history: dict[str, Any],
    row: dict[str, Any],
    retry_queue_state_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-retry-scheduler-lease",
        "retry_scheduler_lease_mode": workflow_retry_scheduler_lease.RETRY_SCHEDULER_LEASE_MODE,
        "operator_decision": workflow_retry_scheduler_lease.OPERATOR_DECISION,
        "retry_queue_state_receipt_id": retry_queue_state_body["retry_queue_state_receipt_id"],
        "retry_queue_state_receipt_hash": retry_queue_state_body["retry_queue_state_receipt_hash"],
        "retry_queue_state_authority_hash": retry_queue_state_body["retry_queue_state_authority_hash"],
        "retry_attempt_number": retry_queue_state_body["retry_attempt_number"],
        "retry_policy_receipt_id": retry_queue_state_body["retry_policy_receipt_id"],
        "retry_policy_authority_hash": retry_queue_state_body["retry_policy_authority_hash"],
        "completion_failure_receipt_id": retry_queue_state_body["completion_failure_receipt_id"],
        "failed_worker_attempt_receipt_id": retry_queue_state_body["failed_worker_attempt_receipt_id"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _retry_worker_attempt_request(
    history: dict[str, Any],
    row: dict[str, Any],
    retry_scheduler_lease_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-retry-worker-attempt",
        "retry_worker_attempt_mode": workflow_retry_worker_attempt.RETRY_WORKER_ATTEMPT_MODE,
        "operator_decision": workflow_retry_worker_attempt.OPERATOR_DECISION,
        "retry_attempt_number": retry_scheduler_lease_body["retry_attempt_number"],
        "retry_scheduler_lease_receipt_id": retry_scheduler_lease_body["retry_scheduler_lease_receipt_id"],
        "retry_scheduler_lease_receipt_hash": retry_scheduler_lease_body["retry_scheduler_lease_receipt_hash"],
        "retry_scheduler_lease_authority_hash": retry_scheduler_lease_body["retry_scheduler_lease_authority_hash"],
        "retry_queue_state_receipt_id": retry_scheduler_lease_body["retry_queue_state_receipt_id"],
        "retry_queue_state_receipt_hash": retry_scheduler_lease_body["retry_queue_state_receipt_hash"],
        "retry_queue_state_authority_hash": retry_scheduler_lease_body["retry_queue_state_authority_hash"],
        "retry_policy_receipt_id": retry_scheduler_lease_body["retry_policy_receipt_id"],
        "retry_policy_authority_hash": retry_scheduler_lease_body["retry_policy_authority_hash"],
        "completion_failure_receipt_id": retry_scheduler_lease_body["completion_failure_receipt_id"],
        "failed_worker_attempt_receipt_id": retry_scheduler_lease_body["failed_worker_attempt_receipt_id"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _retry_progress_checkpoint_request(
    history: dict[str, Any],
    row: dict[str, Any],
    retry_worker_attempt_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-retry-progress-checkpoint",
        "retry_progress_checkpoint_mode": workflow_retry_progress_checkpoint.RETRY_PROGRESS_CHECKPOINT_MODE,
        "operator_decision": workflow_retry_progress_checkpoint.OPERATOR_DECISION,
        "retry_progress_checkpoint_sequence": 1,
        "retry_attempt_number": retry_worker_attempt_body["retry_attempt_number"],
        "retry_worker_attempt_receipt_id": retry_worker_attempt_body["retry_worker_attempt_receipt_id"],
        "retry_worker_attempt_receipt_hash": retry_worker_attempt_body["retry_worker_attempt_receipt_hash"],
        "retry_worker_attempt_authority_hash": retry_worker_attempt_body["retry_worker_attempt_authority_hash"],
        "retry_scheduler_lease_receipt_id": retry_worker_attempt_body["retry_scheduler_lease_receipt_id"],
        "retry_scheduler_lease_receipt_hash": retry_worker_attempt_body["retry_scheduler_lease_receipt_hash"],
        "retry_scheduler_lease_authority_hash": retry_worker_attempt_body["retry_scheduler_lease_authority_hash"],
        "retry_queue_state_receipt_id": retry_worker_attempt_body["retry_queue_state_receipt_id"],
        "retry_queue_state_receipt_hash": retry_worker_attempt_body["retry_queue_state_receipt_hash"],
        "retry_queue_state_authority_hash": retry_worker_attempt_body["retry_queue_state_authority_hash"],
        "retry_policy_receipt_id": retry_worker_attempt_body["retry_policy_receipt_id"],
        "retry_policy_authority_hash": retry_worker_attempt_body["retry_policy_authority_hash"],
        "completion_failure_receipt_id": retry_worker_attempt_body["completion_failure_receipt_id"],
        "failed_worker_attempt_receipt_id": retry_worker_attempt_body["failed_worker_attempt_receipt_id"],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _retry_completion_failure_request(
    history: dict[str, Any],
    row: dict[str, Any],
    retry_progress_checkpoint_body: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-retry-completion-failure",
        "retry_completion_failure_mode": workflow_retry_completion_failure.RETRY_COMPLETION_FAILURE_MODE,
        "operator_decision": workflow_retry_completion_failure.OPERATOR_DECISION,
        "retry_terminal_outcome": "completed",
        "retry_attempt_number": retry_progress_checkpoint_body["retry_attempt_number"],
        "latest_retry_progress_checkpoint_receipt_id": retry_progress_checkpoint_body[
            "retry_progress_checkpoint_receipt_id"
        ],
        "latest_retry_progress_checkpoint_receipt_hash": retry_progress_checkpoint_body[
            "retry_progress_checkpoint_receipt_hash"
        ],
        "latest_retry_progress_checkpoint_authority_hash": retry_progress_checkpoint_body[
            "retry_progress_checkpoint_authority_hash"
        ],
        "retry_progress_checkpoint_sequence": retry_progress_checkpoint_body[
            "retry_progress_checkpoint_sequence"
        ],
        "retry_worker_attempt_receipt_id": retry_progress_checkpoint_body["retry_worker_attempt_receipt_id"],
        "retry_worker_attempt_receipt_hash": retry_progress_checkpoint_body["retry_worker_attempt_receipt_hash"],
        "retry_worker_attempt_authority_hash": retry_progress_checkpoint_body[
            "retry_worker_attempt_authority_hash"
        ],
        "retry_scheduler_lease_receipt_id": retry_progress_checkpoint_body[
            "retry_scheduler_lease_receipt_id"
        ],
        "retry_scheduler_lease_receipt_hash": retry_progress_checkpoint_body[
            "retry_scheduler_lease_receipt_hash"
        ],
        "retry_scheduler_lease_authority_hash": retry_progress_checkpoint_body[
            "retry_scheduler_lease_authority_hash"
        ],
        "retry_queue_state_receipt_id": retry_progress_checkpoint_body["retry_queue_state_receipt_id"],
        "retry_queue_state_receipt_hash": retry_progress_checkpoint_body["retry_queue_state_receipt_hash"],
        "retry_queue_state_authority_hash": retry_progress_checkpoint_body[
            "retry_queue_state_authority_hash"
        ],
        "retry_policy_receipt_id": retry_progress_checkpoint_body["retry_policy_receipt_id"],
        "retry_policy_receipt_hash": retry_progress_checkpoint_body["retry_policy_receipt_hash"],
        "retry_policy_authority_hash": retry_progress_checkpoint_body["retry_policy_authority_hash"],
        "completion_failure_receipt_id": retry_progress_checkpoint_body["completion_failure_receipt_id"],
        "completion_failure_receipt_hash": retry_progress_checkpoint_body["completion_failure_receipt_hash"],
        "completion_failure_authority_hash": retry_progress_checkpoint_body[
            "completion_failure_authority_hash"
        ],
        "failed_worker_attempt_receipt_id": retry_progress_checkpoint_body[
            "failed_worker_attempt_receipt_id"
        ],
        "failed_worker_attempt_receipt_hash": retry_progress_checkpoint_body[
            "failed_worker_attempt_receipt_hash"
        ],
        "failed_worker_attempt_authority_hash": retry_progress_checkpoint_body[
            "failed_worker_attempt_authority_hash"
        ],
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
    }
    payload.update(overrides)
    return payload


def _worker_attempt_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    scheduler_lease_body = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    ).json()
    worker_attempt_body = client.post(
        WORKER_ATTEMPT_ENDPOINT,
        json=_worker_attempt_request(history_body, row, scheduler_lease_body),
    ).json()
    return history_body, row, worker_attempt_body


def _progress_checkpoint_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)
    progress_checkpoint_body = client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(history_body, row, worker_attempt_body),
    ).json()
    return history_body, row, progress_checkpoint_body


def _failed_completion_failure_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)
    completion_failure_body = client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(
            history_body,
            row,
            progress_checkpoint_body,
            terminal_outcome="failed",
            terminal_failure_code="operator_safe_failure",
            terminal_failure_phase="analysis",
        ),
    ).json()
    return history_body, row, completion_failure_body


def _eligible_retry_policy_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, completion_failure_body = _failed_completion_failure_chain(client)
    retry_policy_body = client.post(
        RETRY_POLICY_ENDPOINT,
        json=_retry_policy_request(history_body, row, completion_failure_body),
    ).json()
    return history_body, row, retry_policy_body


def _retry_queue_state_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, retry_policy_body = _eligible_retry_policy_chain(client)
    retry_queue_state_body = client.post(
        RETRY_QUEUE_STATE_ENDPOINT,
        json=_retry_queue_state_request(history_body, row, retry_policy_body),
    ).json()
    return history_body, row, retry_queue_state_body


def _retry_scheduler_lease_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)
    retry_scheduler_lease_body = client.post(
        RETRY_SCHEDULER_LEASE_ENDPOINT,
        json=_retry_scheduler_lease_request(history_body, row, retry_queue_state_body),
    ).json()
    return history_body, row, retry_scheduler_lease_body


def _retry_worker_attempt_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, retry_scheduler_lease_body = _retry_scheduler_lease_chain(client)
    retry_worker_attempt_body = client.post(
        RETRY_WORKER_ATTEMPT_ENDPOINT,
        json=_retry_worker_attempt_request(history_body, row, retry_scheduler_lease_body),
    ).json()
    return history_body, row, retry_worker_attempt_body


def _retry_progress_checkpoint_chain(client: TestClient) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)
    retry_progress_checkpoint_body = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(history_body, row, retry_worker_attempt_body),
    ).json()
    return history_body, row, retry_progress_checkpoint_body


def _workflow_receipt_file(receipt_id: str) -> Path:
    return Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir) / receipt_id / "receipt.json"


def test_candidate_b_full_corpus_operator_workflow_run_persists_status_compatible_receipt(
    client: TestClient,
) -> None:
    source_receipt_id, source_receipt = _write_source_receipt()

    response = client.post(RUN_ENDPOINT, json=_run_request())

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_run.SCHEMA_ID
    assert body["run_state"] == "proven"
    assert body["state_machine"] == list(workflow_run.STATE_MACHINE)
    assert body["source_operator_workflow_receipt_id"] == source_receipt_id
    assert body["source_operator_workflow_receipt_hash"] == source_receipt["receipt_hash"]
    assert body["runtime_root_lifecycle"]["lifecycle_receipt_id"] == RUNTIME_ROOT_LIFECYCLE_RECEIPT_ID
    assert body["compare_target_set_hash"] == COMPARE_TARGET_SET_HASH
    assert body["rendered_run_start_control_admitted"] is True
    assert body["rendered_progress_control_admitted"] is True
    assert body["selector_mutation_performed"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized

    run_receipt_file = (
        Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
        / body["operator_workflow_receipt_id"]
        / "receipt.json"
    )
    assert run_receipt_file.is_file()

    status_response = client.post(STATUS_ENDPOINT, json=body["status_request"])
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["workflow_receipt_id"] == body["operator_workflow_receipt_id"]
    assert status_body["workflow_receipt_hash"] == body["operator_workflow_receipt_hash"]
    assert status_body["workflow_status"] == "proven"
    retry_terminal_projection = status_body["retry_terminal_status_projection"]
    assert retry_terminal_projection["retry_terminal_projection_state"] == "not_recorded"
    assert retry_terminal_projection["read_only_retry_terminal_projection"] is True
    assert retry_terminal_projection["retry_completion_failure_receipt_available"] is False
    assert retry_terminal_projection["missing_retry_terminal_receipt_projects_not_recorded"] is True
    assert retry_terminal_projection["retry_terminal_receipt_creation_admitted_now"] is False
    assert retry_terminal_projection["retry_terminal_status_projection_runtime_selected"] is True


def test_candidate_b_full_corpus_operator_workflow_run_is_idempotent(client: TestClient) -> None:
    _write_source_receipt()

    first = client.post(RUN_ENDPOINT, json=_run_request()).json()
    second_response = client.post(RUN_ENDPOINT, json=_run_request())

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["operator_workflow_receipt_id"] == first["operator_workflow_receipt_id"]
    assert second["authority_basis_hash"] == first["authority_basis_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_history_lists_server_owned_runs(
    client: TestClient,
) -> None:
    source_receipt_id, _source_receipt = _write_source_receipt()
    run_body = client.post(RUN_ENDPOINT, json=_run_request()).json()

    response = client.get(HISTORY_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == "layer3.candidate_b_full_corpus_operator_workflow_history.v1"
    assert body["history_state"] == "available"
    assert body["receipt_count"] == 1
    assert body["read_only_history_projection"] is True
    assert body["single_run_status_endpoint_reused_for_detail"] is True
    assert body["browser_supplied_receipt_root_admitted"] is False
    assert body["cancel_runtime_admitted"] is False
    assert body["queue_state_authority_runtime_admitted"] is True
    assert body["queue_scheduler_runtime_admitted"] is True
    assert body["retry_terminal_status_projection_runtime_admitted"] is True
    assert body["worker_attempt_runtime_admitted"] is True
    assert body["background_process_runtime_admitted"] is False
    assert body["job_execution_runtime_admitted"] is False
    assert body["progress_checkpoint_runtime_admitted"] is True
    assert body["completion_failure_runtime_admitted"] is True
    assert body["expiry_mutation_runtime_admitted"] is True
    assert body["frontend_durable_authority_enabled"] is False
    row = body["history_rows"][0]
    assert row["operator_workflow_receipt_id"] == run_body["operator_workflow_receipt_id"]
    assert row["operator_workflow_receipt_hash"] == run_body["operator_workflow_receipt_hash"]
    assert row["source_operator_workflow_receipt_id"] == source_receipt_id
    assert row["runtime_root_lifecycle_receipt_id"] == RUNTIME_ROOT_LIFECYCLE_RECEIPT_ID
    assert row["compare_target_set_hash"] == COMPARE_TARGET_SET_HASH
    assert row["run_state"] == "proven"
    assert row["status_endpoint"] == STATUS_ENDPOINT
    assert row["retry_terminal_status_projection"]["retry_terminal_projection_state"] == "not_recorded"
    assert row["retry_terminal_status_projection"]["read_only_retry_terminal_projection"] is True
    assert row["retry_terminal_status_projection"]["retry_terminal_receipt_creation_admitted_now"] is False
    assert row["raw_local_path_exposed"] is False
    assert row["raw_url_exposed"] is False
    assert row["selector_mutation_performed"] is False
    status_response = client.post(STATUS_ENDPOINT, json=row["status_request"])
    assert status_response.status_code == 200
    assert status_response.json()["workflow_receipt_id"] == row["operator_workflow_receipt_id"]
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_lifecycle_expires_append_only(
    client: TestClient,
) -> None:
    _write_source_receipt()
    run_body = client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]

    response = client.post(LIFECYCLE_ENDPOINT, json=_lifecycle_request(history_body, row))

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_lifecycle.SCHEMA_ID
    assert body["mode"] == workflow_lifecycle.LIFECYCLE_MODE
    assert body["lifecycle_state"] == "expired"
    assert body["operator_workflow_receipt_id"] == run_body["operator_workflow_receipt_id"]
    assert body["operator_workflow_receipt_hash"] == run_body["operator_workflow_receipt_hash"]
    assert body["row_hash"] == row["row_hash"]
    assert body["history_hash"] == history_body["history_hash"]
    assert body["append_only_lifecycle_receipt"] is True
    assert body["source_run_receipt_mutated"] is False
    assert body["run_state_before_lifecycle"] == "proven"
    assert body["run_state_after_lifecycle"] == "expired"
    assert body["expiry_closeout_runtime_selected"] is True
    assert body["cancel_runtime_selected_now"] is False
    assert body["retry_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["queue_scheduler_runtime_selected_now"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["status_request"] == row["status_request"]
    assert body["history_endpoint"] == HISTORY_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized

    run_receipt_file = (
        Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
        / run_body["operator_workflow_receipt_id"]
        / "receipt.json"
    )
    run_receipt = json.loads(run_receipt_file.read_text(encoding="utf-8"))
    assert run_receipt["server_owned_workflow_run"]["run_state"] == "proven"
    refreshed_history = client.get(HISTORY_ENDPOINT).json()
    assert refreshed_history["receipt_count"] == 1
    assert refreshed_history["history_rows"][0]["operator_workflow_receipt_id"] == run_body["operator_workflow_receipt_id"]


def test_candidate_b_full_corpus_operator_workflow_queue_state_records_append_only(
    client: TestClient,
) -> None:
    _write_source_receipt()
    run_body = client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]

    response = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row))

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_queue_state.SCHEMA_ID
    assert body["mode"] == workflow_queue_state.QUEUE_STATE_MODE
    assert body["queue_state"] == workflow_queue_state.QUEUE_STATE
    assert body["operator_workflow_receipt_id"] == run_body["operator_workflow_receipt_id"]
    assert body["operator_workflow_receipt_hash"] == run_body["operator_workflow_receipt_hash"]
    assert body["row_hash"] == row["row_hash"]
    assert body["history_hash"] == history_body["history_hash"]
    assert body["append_only_queue_state_receipt"] is True
    assert body["source_run_receipt_mutated"] is False
    assert body["run_state_before_queue_state"] == "proven"
    assert body["run_state_after_queue_state"] == "proven"
    assert body["queue_state_authority_runtime_selected"] is True
    assert body["queue_scheduler_runtime_selected_now"] is False
    assert body["background_worker_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["retry_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["expiry_enforcement_runtime_selected_now"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["status_request"] == row["status_request"]
    assert body["history_endpoint"] == HISTORY_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized

    run_receipt_file = (
        Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
        / run_body["operator_workflow_receipt_id"]
        / "receipt.json"
    )
    run_receipt = json.loads(run_receipt_file.read_text(encoding="utf-8"))
    assert run_receipt["server_owned_workflow_run"]["run_state"] == "proven"


def test_candidate_b_full_corpus_operator_workflow_queue_state_is_idempotent(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    request = _queue_state_request(history_body, row)

    first = client.post(QUEUE_STATE_ENDPOINT, json=request).json()
    second_response = client.post(QUEUE_STATE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["queue_state_receipt_id"] == first["queue_state_receipt_id"]
    assert second["queue_state_receipt_hash"] == first["queue_state_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_queue_state_rejects_stale_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]

    response = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row, history_hash="6" * 64))

    assert response.status_code == 409
    body = response.json()
    assert body["queue_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_queue_state_stale_authority"


def test_candidate_b_full_corpus_operator_workflow_queue_state_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    payload = _queue_state_request(history_body, row, local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_queue_state.CandidateBFullCorpusOperatorWorkflowQueueStateError) as exc_info:
        workflow_queue_state.record_candidate_b_full_corpus_operator_workflow_queue_state(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_queue_state_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_scheduler_lease_records_append_only(
    client: TestClient,
) -> None:
    _write_source_receipt()
    run_body = client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()

    response = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_scheduler_lease.SCHEMA_ID
    assert body["mode"] == workflow_scheduler_lease.SCHEDULER_LEASE_MODE
    assert body["scheduler_lease_state"] == "leased"
    assert body["queue_state_receipt_id"] == queue_state_body["queue_state_receipt_id"]
    assert body["queue_state_receipt_hash"] == queue_state_body["queue_state_receipt_hash"]
    assert body["queue_state_authority_hash"] == queue_state_body["queue_state_authority_hash"]
    assert body["operator_workflow_receipt_id"] == run_body["operator_workflow_receipt_id"]
    assert body["operator_workflow_receipt_hash"] == run_body["operator_workflow_receipt_hash"]
    assert body["history_hash"] == history_body["history_hash"]
    assert body["append_only_scheduler_lease_receipt"] is True
    assert body["exclusive_queue_state_lease"] is True
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["run_state_before_scheduler_lease"] == "proven"
    assert body["run_state_after_scheduler_lease"] == "proven"
    assert body["queue_state_before_scheduler_lease"] == "queue_state_authority_recorded"
    assert body["scheduler_lease_runtime_selected"] is True
    assert body["background_worker_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["retry_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["expiry_enforcement_runtime_selected_now"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["selected_scheduler_endpoint"] == SCHEDULER_LEASE_ENDPOINT
    assert body["queue_state_endpoint"] == QUEUE_STATE_ENDPOINT
    assert body["status_request"] == row["status_request"]
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized

    workflow_root = Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
    run_receipt = json.loads(
        (workflow_root / run_body["operator_workflow_receipt_id"] / "receipt.json").read_text(encoding="utf-8")
    )
    queue_state_receipt = json.loads(
        (workflow_root / queue_state_body["queue_state_receipt_id"] / "receipt.json").read_text(encoding="utf-8")
    )
    assert run_receipt["server_owned_workflow_run"]["run_state"] == "proven"
    assert queue_state_receipt["queue_state_receipt_hash"] == queue_state_body["queue_state_receipt_hash"]


def test_candidate_b_full_corpus_operator_workflow_scheduler_lease_is_idempotent(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    request = _scheduler_lease_request(history_body, row, queue_state_body)

    first = client.post(SCHEDULER_LEASE_ENDPOINT, json=request).json()
    second_response = client.post(SCHEDULER_LEASE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["scheduler_lease_receipt_id"] == first["scheduler_lease_receipt_id"]
    assert second["scheduler_lease_receipt_hash"] == first["scheduler_lease_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_scheduler_lease_rejects_stale_queue_state(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()

    response = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body, queue_state_receipt_hash="6" * 64),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["scheduler_lease_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_scheduler_lease_stale_queue_state_receipt"


def test_candidate_b_full_corpus_operator_workflow_scheduler_lease_rejects_competing_lease(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    )

    response = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(
            history_body,
            row,
            queue_state_body,
            client_request_id="candidate-b-full-corpus-workflow-scheduler-lease-second",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["scheduler_lease_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_scheduler_lease_conflict"


def test_candidate_b_full_corpus_operator_workflow_scheduler_lease_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    payload = _scheduler_lease_request(history_body, row, queue_state_body, local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_scheduler_lease.CandidateBFullCorpusOperatorWorkflowSchedulerLeaseError) as exc_info:
        workflow_scheduler_lease.record_candidate_b_full_corpus_operator_workflow_scheduler_lease(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_scheduler_lease_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_worker_attempt_records_append_only(
    client: TestClient,
) -> None:
    _write_source_receipt()
    run_body = client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    scheduler_lease_body = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    ).json()

    response = client.post(
        WORKER_ATTEMPT_ENDPOINT,
        json=_worker_attempt_request(history_body, row, scheduler_lease_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_worker_attempt.SCHEMA_ID
    assert body["mode"] == workflow_worker_attempt.WORKER_ATTEMPT_MODE
    assert body["worker_attempt_state"] == "attempt_authority_recorded"
    assert body["worker_attempt_number"] == 1
    assert body["scheduler_lease_receipt_id"] == scheduler_lease_body["scheduler_lease_receipt_id"]
    assert body["scheduler_lease_receipt_hash"] == scheduler_lease_body["scheduler_lease_receipt_hash"]
    assert body["scheduler_lease_authority_hash"] == scheduler_lease_body["scheduler_lease_authority_hash"]
    assert body["queue_state_receipt_id"] == queue_state_body["queue_state_receipt_id"]
    assert body["operator_workflow_receipt_id"] == run_body["operator_workflow_receipt_id"]
    assert body["operator_workflow_receipt_hash"] == run_body["operator_workflow_receipt_hash"]
    assert body["append_only_worker_attempt_receipt"] is True
    assert body["exclusive_initial_attempt_per_scheduler_lease"] is True
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["run_state_before_worker_attempt"] == "proven"
    assert body["run_state_after_worker_attempt"] == "proven"
    assert body["scheduler_lease_state_before_worker_attempt"] == "leased"
    assert body["worker_attempt_runtime_selected"] is True
    assert body["background_process_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["progress_checkpoint_runtime_selected_now"] is False
    assert body["completion_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["retry_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["expiry_enforcement_runtime_selected_now"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["worker_attempt_endpoint"] == WORKER_ATTEMPT_ENDPOINT
    assert body["scheduler_lease_endpoint"] == SCHEDULER_LEASE_ENDPOINT
    assert body["status_request"] == row["status_request"]
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized

    workflow_root = Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
    scheduler_lease_receipt = json.loads(
        (workflow_root / scheduler_lease_body["scheduler_lease_receipt_id"] / "receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert scheduler_lease_receipt["scheduler_lease_receipt_hash"] == scheduler_lease_body["scheduler_lease_receipt_hash"]


def test_candidate_b_full_corpus_operator_workflow_worker_attempt_is_idempotent(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    scheduler_lease_body = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    ).json()
    request = _worker_attempt_request(history_body, row, scheduler_lease_body)

    first = client.post(WORKER_ATTEMPT_ENDPOINT, json=request).json()
    second_response = client.post(WORKER_ATTEMPT_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["worker_attempt_receipt_id"] == first["worker_attempt_receipt_id"]
    assert second["worker_attempt_receipt_hash"] == first["worker_attempt_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_worker_attempt_rejects_stale_scheduler_lease(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    scheduler_lease_body = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    ).json()

    response = client.post(
        WORKER_ATTEMPT_ENDPOINT,
        json=_worker_attempt_request(history_body, row, scheduler_lease_body, scheduler_lease_receipt_hash="6" * 64),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["worker_attempt_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_worker_attempt_stale_scheduler_lease_receipt"


def test_candidate_b_full_corpus_operator_workflow_worker_attempt_rejects_competing_attempt(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    scheduler_lease_body = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    ).json()
    client.post(WORKER_ATTEMPT_ENDPOINT, json=_worker_attempt_request(history_body, row, scheduler_lease_body))

    response = client.post(
        WORKER_ATTEMPT_ENDPOINT,
        json=_worker_attempt_request(
            history_body,
            row,
            scheduler_lease_body,
            client_request_id="candidate-b-full-corpus-workflow-worker-attempt-second",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["worker_attempt_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_worker_attempt_conflict"


def test_candidate_b_full_corpus_operator_workflow_worker_attempt_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    queue_state_body = client.post(QUEUE_STATE_ENDPOINT, json=_queue_state_request(history_body, row)).json()
    scheduler_lease_body = client.post(
        SCHEDULER_LEASE_ENDPOINT,
        json=_scheduler_lease_request(history_body, row, queue_state_body),
    ).json()
    payload = _worker_attempt_request(history_body, row, scheduler_lease_body, local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_worker_attempt.CandidateBFullCorpusOperatorWorkflowWorkerAttemptError) as exc_info:
        workflow_worker_attempt.record_candidate_b_full_corpus_operator_workflow_worker_attempt(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_worker_attempt_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_progress_checkpoint_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)

    response = client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(history_body, row, worker_attempt_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_progress_checkpoint.SCHEMA_ID
    assert body["mode"] == workflow_progress_checkpoint.PROGRESS_CHECKPOINT_MODE
    assert body["progress_checkpoint_state"] == "progress_checkpoint_recorded"
    assert body["progress_checkpoint_sequence"] == 1
    assert body["worker_attempt_receipt_id"] == worker_attempt_body["worker_attempt_receipt_id"]
    assert body["worker_attempt_receipt_hash"] == worker_attempt_body["worker_attempt_receipt_hash"]
    assert body["worker_attempt_authority_hash"] == worker_attempt_body["worker_attempt_authority_hash"]
    assert body["operator_workflow_receipt_id"] == row["operator_workflow_receipt_id"]
    assert body["append_only_progress_checkpoint_receipt"] is True
    assert body["monotonic_progress_checkpoint_sequence"] is True
    assert body["worker_attempt_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["run_state_before_progress_checkpoint"] == "proven"
    assert body["run_state_after_progress_checkpoint"] == "proven"
    assert body["worker_attempt_state_before_progress_checkpoint"] == "attempt_authority_recorded"
    assert body["progress_checkpoint_runtime_selected"] is True
    assert body["background_process_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["completion_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["retry_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["progress_checkpoint_endpoint"] == PROGRESS_CHECKPOINT_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized

    history_response = client.get(HISTORY_ENDPOINT)
    assert history_response.status_code == 200
    assert history_response.json()["receipt_count"] == 1


def test_candidate_b_full_corpus_operator_workflow_progress_checkpoint_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)
    request = _progress_checkpoint_request(history_body, row, worker_attempt_body)

    first = client.post(PROGRESS_CHECKPOINT_ENDPOINT, json=request).json()
    second_response = client.post(PROGRESS_CHECKPOINT_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["progress_checkpoint_receipt_id"] == first["progress_checkpoint_receipt_id"]
    assert second["progress_checkpoint_receipt_hash"] == first["progress_checkpoint_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_progress_checkpoint_appends_next_sequence(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)
    client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(history_body, row, worker_attempt_body),
    )

    response = client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(
            history_body,
            row,
            worker_attempt_body,
            client_request_id="candidate-b-full-corpus-workflow-progress-checkpoint-2",
            progress_checkpoint_sequence=2,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["progress_checkpoint_sequence"] == 2
    assert body["previous_progress_checkpoint_sequence"] == 1
    assert body["previous_progress_checkpoint_receipt_id"]


def test_candidate_b_full_corpus_operator_workflow_progress_checkpoint_rejects_stale_worker_attempt(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)

    response = client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(
            history_body,
            row,
            worker_attempt_body,
            worker_attempt_receipt_hash="6" * 64,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["progress_checkpoint_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_progress_checkpoint_stale_worker_attempt_receipt"
    )


def test_candidate_b_full_corpus_operator_workflow_progress_checkpoint_rejects_non_next_sequence(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)

    response = client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(
            history_body,
            row,
            worker_attempt_body,
            progress_checkpoint_sequence=2,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["progress_checkpoint_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_progress_checkpoint_sequence_not_next"
    )


def test_candidate_b_full_corpus_operator_workflow_progress_checkpoint_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)
    payload = _progress_checkpoint_request(history_body, row, worker_attempt_body, local_path="C:\\raw\\candidate-b")

    with pytest.raises(
        workflow_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowProgressCheckpointError
    ) as exc_info:
        workflow_progress_checkpoint.record_candidate_b_full_corpus_operator_workflow_progress_checkpoint(payload)

    assert exc_info.value.code == (
        "candidate_b_full_corpus_operator_workflow_progress_checkpoint_forbidden_request_fields"
    )
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_completion_failure_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)

    response = client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(history_body, row, progress_checkpoint_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_completion_failure.SCHEMA_ID
    assert body["mode"] == workflow_completion_failure.COMPLETION_FAILURE_MODE
    assert body["completion_failure_state"] == "completion_failure_recorded"
    assert body["terminal_outcome"] == "completed"
    assert body["terminal_failure_code"] is None
    assert body["terminal_failure_phase"] is None
    assert body["latest_progress_checkpoint_receipt_id"] == progress_checkpoint_body["progress_checkpoint_receipt_id"]
    assert body["latest_progress_checkpoint_receipt_hash"] == progress_checkpoint_body["progress_checkpoint_receipt_hash"]
    assert body["latest_progress_checkpoint_authority_hash"] == progress_checkpoint_body["progress_checkpoint_authority_hash"]
    assert body["progress_checkpoint_sequence"] == 1
    assert body["worker_attempt_receipt_id"] == progress_checkpoint_body["worker_attempt_receipt_id"]
    assert body["append_only_completion_failure_receipt"] is True
    assert body["exclusive_terminal_receipt_per_worker_attempt"] is True
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["worker_attempt_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["completion_failure_runtime_selected"] is True
    assert body["background_process_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["retry_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["terminal_failure_payload_operator_safe"] is True
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False
    assert body["completion_failure_endpoint"] == COMPLETION_FAILURE_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_completion_failure_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)
    request = _completion_failure_request(history_body, row, progress_checkpoint_body)

    first = client.post(COMPLETION_FAILURE_ENDPOINT, json=request).json()
    second_response = client.post(COMPLETION_FAILURE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["completion_failure_receipt_id"] == first["completion_failure_receipt_id"]
    assert second["completion_failure_receipt_hash"] == first["completion_failure_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_completion_failure_records_failure(
    client: TestClient,
) -> None:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)

    response = client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(
            history_body,
            row,
            progress_checkpoint_body,
            terminal_outcome="failed",
            terminal_failure_code="operator_safe_failure",
            terminal_failure_phase="analysis",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["terminal_outcome"] == "failed"
    assert body["terminal_failure_code"] == "operator_safe_failure"
    assert body["terminal_failure_phase"] == "analysis"
    assert body["terminal_failure_payload_operator_safe"] is True


def test_candidate_b_full_corpus_operator_workflow_completion_failure_rejects_stale_progress_checkpoint(
    client: TestClient,
) -> None:
    history_body, row, worker_attempt_body = _worker_attempt_chain(client)
    first = client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(history_body, row, worker_attempt_body),
    ).json()
    client.post(
        PROGRESS_CHECKPOINT_ENDPOINT,
        json=_progress_checkpoint_request(
            history_body,
            row,
            worker_attempt_body,
            client_request_id="candidate-b-full-corpus-workflow-progress-checkpoint-2",
            progress_checkpoint_sequence=2,
        ),
    )

    response = client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(history_body, row, first),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["completion_failure_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_completion_failure_progress_checkpoint_not_latest"
    )


def test_candidate_b_full_corpus_operator_workflow_completion_failure_rejects_terminal_conflict(
    client: TestClient,
) -> None:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)
    client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(history_body, row, progress_checkpoint_body),
    )

    response = client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(
            history_body,
            row,
            progress_checkpoint_body,
            client_request_id="candidate-b-full-corpus-workflow-completion-failure-2",
            terminal_outcome="failed",
            terminal_failure_code="operator_safe_failure",
            terminal_failure_phase="analysis",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["completion_failure_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_completion_failure_terminal_conflict"
    )


def test_candidate_b_full_corpus_operator_workflow_completion_failure_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)
    payload = _completion_failure_request(history_body, row, progress_checkpoint_body, local_path="C:\\raw\\candidate-b")

    with pytest.raises(
        workflow_completion_failure.CandidateBFullCorpusOperatorWorkflowCompletionFailureError
    ) as exc_info:
        workflow_completion_failure.record_candidate_b_full_corpus_operator_workflow_completion_failure(payload)

    assert exc_info.value.code == (
        "candidate_b_full_corpus_operator_workflow_completion_failure_forbidden_request_fields"
    )
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_retry_policy_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, completion_failure_body = _failed_completion_failure_chain(client)

    response = client.post(
        RETRY_POLICY_ENDPOINT,
        json=_retry_policy_request(history_body, row, completion_failure_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_retry_policy.SCHEMA_ID
    assert body["mode"] == workflow_retry_policy.RETRY_POLICY_MODE
    assert body["retry_policy_state"] == "retry_policy_recorded"
    assert body["retry_policy_result"] == "eligible"
    assert body["completion_failure_receipt_id"] == completion_failure_body["completion_failure_receipt_id"]
    assert body["completion_failure_receipt_hash"] == completion_failure_body["completion_failure_receipt_hash"]
    assert body["completion_failure_authority_hash"] == completion_failure_body["completion_failure_authority_hash"]
    assert body["terminal_outcome"] == "failed"
    assert body["terminal_failure_code"] == "operator_safe_failure"
    assert body["terminal_failure_phase"] == "analysis"
    assert body["append_only_retry_policy_receipt"] is True
    assert body["exclusive_retry_policy_per_failed_terminal_receipt"] is True
    assert body["retry_attempt_created"] is False
    assert body["completion_failure_receipt_mutated"] is False
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["worker_attempt_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["retry_policy_runtime_selected"] is True
    assert body["retry_attempt_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["retry_policy_endpoint"] == RETRY_POLICY_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_retry_policy_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, completion_failure_body = _failed_completion_failure_chain(client)
    request = _retry_policy_request(history_body, row, completion_failure_body)

    first = client.post(RETRY_POLICY_ENDPOINT, json=request).json()
    second_response = client.post(RETRY_POLICY_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_policy_receipt_id"] == first["retry_policy_receipt_id"]
    assert second["retry_policy_receipt_hash"] == first["retry_policy_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_retry_policy_rejects_completed_terminal(
    client: TestClient,
) -> None:
    history_body, row, progress_checkpoint_body = _progress_checkpoint_chain(client)
    completion_failure_body = client.post(
        COMPLETION_FAILURE_ENDPOINT,
        json=_completion_failure_request(history_body, row, progress_checkpoint_body),
    ).json()

    response = client.post(
        RETRY_POLICY_ENDPOINT,
        json=_retry_policy_request(history_body, row, completion_failure_body),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_policy_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_policy_completed_terminal_receipt_rejected"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_policy_rejects_stale_terminal(
    client: TestClient,
) -> None:
    history_body, row, completion_failure_body = _failed_completion_failure_chain(client)

    response = client.post(
        RETRY_POLICY_ENDPOINT,
        json=_retry_policy_request(
            history_body,
            row,
            completion_failure_body,
            completion_failure_receipt_hash="6" * 64,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_policy_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_policy_stale_terminal_receipt"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_policy_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, completion_failure_body = _failed_completion_failure_chain(client)
    payload = _retry_policy_request(history_body, row, completion_failure_body, local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_retry_policy.CandidateBFullCorpusOperatorWorkflowRetryPolicyError) as exc_info:
        workflow_retry_policy.record_candidate_b_full_corpus_operator_workflow_retry_policy(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_retry_policy_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_retry_queue_state_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, retry_policy_body = _eligible_retry_policy_chain(client)

    response = client.post(
        RETRY_QUEUE_STATE_ENDPOINT,
        json=_retry_queue_state_request(history_body, row, retry_policy_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_retry_queue_state.SCHEMA_ID
    assert body["mode"] == workflow_retry_queue_state.RETRY_QUEUE_STATE_MODE
    assert body["retry_queue_state"] == "retry_queue_state_authority_recorded"
    assert body["retry_attempt_number"] == 2
    assert body["retry_policy_receipt_id"] == retry_policy_body["retry_policy_receipt_id"]
    assert body["retry_policy_receipt_hash"] == retry_policy_body["retry_policy_receipt_hash"]
    assert body["retry_policy_authority_hash"] == retry_policy_body["retry_policy_authority_hash"]
    assert body["retry_policy_result"] == "eligible"
    assert body["completion_failure_receipt_id"] == retry_policy_body["completion_failure_receipt_id"]
    assert body["completion_failure_authority_hash"] == retry_policy_body["completion_failure_authority_hash"]
    assert body["failed_worker_attempt_receipt_id"] == retry_policy_body["worker_attempt_receipt_id"]
    assert body["failed_worker_attempt_authority_hash"] == retry_policy_body["worker_attempt_authority_hash"]
    assert body["append_only_retry_queue_state_receipt"] is True
    assert body["exclusive_retry_queue_state_per_eligible_retry_policy_receipt"] is True
    assert body["retry_policy_receipt_mutated"] is False
    assert body["completion_failure_receipt_mutated"] is False
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["worker_attempt_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["retry_queue_state_runtime_selected"] is True
    assert body["retry_scheduler_lease_creation_admitted_now"] is False
    assert body["retry_worker_attempt_creation_admitted_now"] is False
    assert body["retry_progress_checkpoint_creation_admitted_now"] is False
    assert body["retry_completion_failure_creation_admitted_now"] is False
    assert body["retry_attempt_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert body["retry_queue_state_endpoint"] == RETRY_QUEUE_STATE_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_retry_queue_state_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, retry_policy_body = _eligible_retry_policy_chain(client)
    request = _retry_queue_state_request(history_body, row, retry_policy_body)

    first = client.post(RETRY_QUEUE_STATE_ENDPOINT, json=request).json()
    second_response = client.post(RETRY_QUEUE_STATE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_queue_state_receipt_id"] == first["retry_queue_state_receipt_id"]
    assert second["retry_queue_state_receipt_hash"] == first["retry_queue_state_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_retry_queue_state_rejects_ineligible_policy(
    client: TestClient,
) -> None:
    history_body, row, completion_failure_body = _failed_completion_failure_chain(client)
    retry_policy_body = client.post(
        RETRY_POLICY_ENDPOINT,
        json=_retry_policy_request(
            history_body,
            row,
            completion_failure_body,
            retry_policy_result="ineligible",
            retry_policy_reason="operator_safe_nonretryable_failure",
        ),
    ).json()

    response = client.post(
        RETRY_QUEUE_STATE_ENDPOINT,
        json=_retry_queue_state_request(history_body, row, retry_policy_body),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_queue_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_queue_state_ineligible_retry_policy_rejected"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_queue_state_rejects_stale_policy(
    client: TestClient,
) -> None:
    history_body, row, retry_policy_body = _eligible_retry_policy_chain(client)

    response = client.post(
        RETRY_QUEUE_STATE_ENDPOINT,
        json=_retry_queue_state_request(
            history_body,
            row,
            retry_policy_body,
            retry_policy_receipt_hash="7" * 64,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_queue_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_retry_queue_state_stale_retry_policy"


def test_candidate_b_full_corpus_operator_workflow_retry_queue_state_rejects_policy_conflict(
    client: TestClient,
) -> None:
    history_body, row, retry_policy_body = _eligible_retry_policy_chain(client)
    client.post(
        RETRY_QUEUE_STATE_ENDPOINT,
        json=_retry_queue_state_request(history_body, row, retry_policy_body),
    )

    response = client.post(
        RETRY_QUEUE_STATE_ENDPOINT,
        json=_retry_queue_state_request(
            history_body,
            row,
            retry_policy_body,
            client_request_id="candidate-b-full-corpus-workflow-retry-queue-state-conflict",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_queue_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_retry_queue_state_policy_conflict"


def test_candidate_b_full_corpus_operator_workflow_retry_queue_state_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, retry_policy_body = _eligible_retry_policy_chain(client)
    payload = _retry_queue_state_request(history_body, row, retry_policy_body, local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_retry_queue_state.CandidateBFullCorpusOperatorWorkflowRetryQueueStateError) as exc_info:
        workflow_retry_queue_state.record_candidate_b_full_corpus_operator_workflow_retry_queue_state(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_retry_queue_state_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)

    response = client.post(
        RETRY_SCHEDULER_LEASE_ENDPOINT,
        json=_retry_scheduler_lease_request(history_body, row, retry_queue_state_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_retry_scheduler_lease.SCHEMA_ID
    assert body["mode"] == workflow_retry_scheduler_lease.RETRY_SCHEDULER_LEASE_MODE
    assert body["retry_scheduler_lease_state"] == "retry_scheduler_leased"
    assert body["retry_attempt_number"] == 2
    assert body["retry_queue_state_receipt_id"] == retry_queue_state_body["retry_queue_state_receipt_id"]
    assert body["retry_queue_state_receipt_hash"] == retry_queue_state_body["retry_queue_state_receipt_hash"]
    assert body["retry_queue_state_authority_hash"] == retry_queue_state_body["retry_queue_state_authority_hash"]
    assert body["retry_policy_receipt_id"] == retry_queue_state_body["retry_policy_receipt_id"]
    assert body["retry_policy_authority_hash"] == retry_queue_state_body["retry_policy_authority_hash"]
    assert body["completion_failure_receipt_id"] == retry_queue_state_body["completion_failure_receipt_id"]
    assert body["failed_worker_attempt_receipt_id"] == retry_queue_state_body["failed_worker_attempt_receipt_id"]
    assert body["append_only_retry_scheduler_lease_receipt"] is True
    assert body["exclusive_retry_queue_state_lease"] is True
    assert body["retry_queue_state_receipt_mutated"] is False
    assert body["retry_policy_receipt_mutated"] is False
    assert body["completion_failure_receipt_mutated"] is False
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["worker_attempt_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["retry_scheduler_lease_runtime_selected"] is True
    assert body["retry_worker_attempt_creation_admitted_now"] is False
    assert body["retry_progress_checkpoint_creation_admitted_now"] is False
    assert body["retry_completion_failure_creation_admitted_now"] is False
    assert body["retry_worker_attempt_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert body["retry_scheduler_lease_endpoint"] == RETRY_SCHEDULER_LEASE_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)
    request = _retry_scheduler_lease_request(history_body, row, retry_queue_state_body)

    first = client.post(RETRY_SCHEDULER_LEASE_ENDPOINT, json=request).json()
    second_response = client.post(RETRY_SCHEDULER_LEASE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_scheduler_lease_receipt_id"] == first["retry_scheduler_lease_receipt_id"]
    assert second["retry_scheduler_lease_receipt_hash"] == first["retry_scheduler_lease_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_rejects_stale_queue_state(
    client: TestClient,
) -> None:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)

    response = client.post(
        RETRY_SCHEDULER_LEASE_ENDPOINT,
        json=_retry_scheduler_lease_request(
            history_body,
            row,
            retry_queue_state_body,
            retry_queue_state_receipt_hash="8" * 64,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_scheduler_lease_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_stale_retry_queue_state"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_rejects_wrong_attempt_number(
    client: TestClient,
) -> None:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)

    response = client.post(
        RETRY_SCHEDULER_LEASE_ENDPOINT,
        json=_retry_scheduler_lease_request(
            history_body,
            row,
            retry_queue_state_body,
            retry_attempt_number=3,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_scheduler_lease_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_stale_retry_queue_state"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_rejects_queue_state_conflict(
    client: TestClient,
) -> None:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)
    client.post(
        RETRY_SCHEDULER_LEASE_ENDPOINT,
        json=_retry_scheduler_lease_request(history_body, row, retry_queue_state_body),
    )

    response = client.post(
        RETRY_SCHEDULER_LEASE_ENDPOINT,
        json=_retry_scheduler_lease_request(
            history_body,
            row,
            retry_queue_state_body,
            client_request_id="candidate-b-full-corpus-workflow-retry-scheduler-lease-conflict",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_scheduler_lease_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_queue_state_conflict"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, retry_queue_state_body = _retry_queue_state_chain(client)
    payload = _retry_scheduler_lease_request(
        history_body,
        row,
        retry_queue_state_body,
        local_path="C:\\raw\\candidate-b",
    )

    with pytest.raises(
        workflow_retry_scheduler_lease.CandidateBFullCorpusOperatorWorkflowRetrySchedulerLeaseError
    ) as exc_info:
        workflow_retry_scheduler_lease.record_candidate_b_full_corpus_operator_workflow_retry_scheduler_lease(payload)

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_operator_workflow_retry_scheduler_lease_forbidden_request_fields"
    )
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, retry_scheduler_lease_body = _retry_scheduler_lease_chain(client)

    response = client.post(
        RETRY_WORKER_ATTEMPT_ENDPOINT,
        json=_retry_worker_attempt_request(history_body, row, retry_scheduler_lease_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_retry_worker_attempt.SCHEMA_ID
    assert body["mode"] == workflow_retry_worker_attempt.RETRY_WORKER_ATTEMPT_MODE
    assert body["retry_worker_attempt_state"] == "retry_worker_attempt_authority_recorded"
    assert body["retry_attempt_number"] == 2
    assert body["retry_scheduler_lease_receipt_id"] == retry_scheduler_lease_body["retry_scheduler_lease_receipt_id"]
    assert body["retry_scheduler_lease_receipt_hash"] == retry_scheduler_lease_body["retry_scheduler_lease_receipt_hash"]
    assert body["retry_scheduler_lease_authority_hash"] == retry_scheduler_lease_body[
        "retry_scheduler_lease_authority_hash"
    ]
    assert body["retry_queue_state_receipt_id"] == retry_scheduler_lease_body["retry_queue_state_receipt_id"]
    assert body["retry_queue_state_receipt_hash"] == retry_scheduler_lease_body["retry_queue_state_receipt_hash"]
    assert body["retry_queue_state_authority_hash"] == retry_scheduler_lease_body[
        "retry_queue_state_authority_hash"
    ]
    assert body["retry_policy_receipt_id"] == retry_scheduler_lease_body["retry_policy_receipt_id"]
    assert body["completion_failure_receipt_id"] == retry_scheduler_lease_body["completion_failure_receipt_id"]
    assert body["failed_worker_attempt_receipt_id"] == retry_scheduler_lease_body["failed_worker_attempt_receipt_id"]
    assert body["append_only_retry_worker_attempt_receipt"] is True
    assert body["exclusive_retry_worker_attempt_per_retry_scheduler_lease"] is True
    assert body["retry_scheduler_lease_receipt_mutated"] is False
    assert body["retry_queue_state_receipt_mutated"] is False
    assert body["retry_policy_receipt_mutated"] is False
    assert body["completion_failure_receipt_mutated"] is False
    assert body["failed_worker_attempt_receipt_mutated"] is False
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["retry_worker_attempt_runtime_selected"] is True
    assert body["background_process_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["retry_progress_checkpoint_runtime_selected_now"] is False
    assert body["retry_completion_failure_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert body["retry_worker_attempt_endpoint"] == RETRY_WORKER_ATTEMPT_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, retry_scheduler_lease_body = _retry_scheduler_lease_chain(client)
    request = _retry_worker_attempt_request(history_body, row, retry_scheduler_lease_body)

    first = client.post(RETRY_WORKER_ATTEMPT_ENDPOINT, json=request).json()
    second_response = client.post(RETRY_WORKER_ATTEMPT_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_worker_attempt_receipt_id"] == first["retry_worker_attempt_receipt_id"]
    assert second["retry_worker_attempt_receipt_hash"] == first["retry_worker_attempt_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_rejects_stale_lease(
    client: TestClient,
) -> None:
    history_body, row, retry_scheduler_lease_body = _retry_scheduler_lease_chain(client)

    response = client.post(
        RETRY_WORKER_ATTEMPT_ENDPOINT,
        json=_retry_worker_attempt_request(
            history_body,
            row,
            retry_scheduler_lease_body,
            retry_scheduler_lease_receipt_hash="8" * 64,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_worker_attempt_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_worker_attempt_stale_retry_scheduler_lease"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_rejects_lease_conflict(
    client: TestClient,
) -> None:
    history_body, row, retry_scheduler_lease_body = _retry_scheduler_lease_chain(client)
    client.post(
        RETRY_WORKER_ATTEMPT_ENDPOINT,
        json=_retry_worker_attempt_request(history_body, row, retry_scheduler_lease_body),
    )

    response = client.post(
        RETRY_WORKER_ATTEMPT_ENDPOINT,
        json=_retry_worker_attempt_request(
            history_body,
            row,
            retry_scheduler_lease_body,
            client_request_id="candidate-b-full-corpus-workflow-retry-worker-attempt-conflict",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_worker_attempt_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_worker_attempt_lease_conflict"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_worker_attempt_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, retry_scheduler_lease_body = _retry_scheduler_lease_chain(client)
    payload = _retry_worker_attempt_request(
        history_body,
        row,
        retry_scheduler_lease_body,
        local_path="C:\\raw\\candidate-b",
    )

    with pytest.raises(
        workflow_retry_worker_attempt.CandidateBFullCorpusOperatorWorkflowRetryWorkerAttemptError
    ) as exc_info:
        workflow_retry_worker_attempt.record_candidate_b_full_corpus_operator_workflow_retry_worker_attempt(payload)

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_operator_workflow_retry_worker_attempt_forbidden_request_fields"
    )
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)

    response = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(history_body, row, retry_worker_attempt_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_retry_progress_checkpoint.SCHEMA_ID
    assert body["mode"] == workflow_retry_progress_checkpoint.RETRY_PROGRESS_CHECKPOINT_MODE
    assert body["retry_progress_checkpoint_state"] == "retry_progress_checkpoint_recorded"
    assert body["retry_progress_checkpoint_sequence"] == 1
    assert body["retry_attempt_number"] == 2
    assert body["retry_worker_attempt_receipt_id"] == retry_worker_attempt_body["retry_worker_attempt_receipt_id"]
    assert (
        body["retry_worker_attempt_receipt_hash"]
        == retry_worker_attempt_body["retry_worker_attempt_receipt_hash"]
    )
    assert (
        body["retry_worker_attempt_authority_hash"]
        == retry_worker_attempt_body["retry_worker_attempt_authority_hash"]
    )
    assert body["retry_scheduler_lease_receipt_id"] == retry_worker_attempt_body["retry_scheduler_lease_receipt_id"]
    assert body["retry_queue_state_receipt_id"] == retry_worker_attempt_body["retry_queue_state_receipt_id"]
    assert body["retry_policy_receipt_id"] == retry_worker_attempt_body["retry_policy_receipt_id"]
    assert body["completion_failure_receipt_id"] == retry_worker_attempt_body["completion_failure_receipt_id"]
    assert body["failed_worker_attempt_receipt_id"] == retry_worker_attempt_body["failed_worker_attempt_receipt_id"]
    assert body["append_only_retry_progress_checkpoint_receipt"] is True
    assert body["monotonic_retry_progress_checkpoint_sequence"] is True
    assert body["retry_worker_attempt_receipt_mutated"] is False
    assert body["retry_scheduler_lease_receipt_mutated"] is False
    assert body["retry_queue_state_receipt_mutated"] is False
    assert body["retry_policy_receipt_mutated"] is False
    assert body["completion_failure_receipt_mutated"] is False
    assert body["failed_worker_attempt_receipt_mutated"] is False
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["retry_progress_checkpoint_runtime_selected"] is True
    assert body["background_process_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["retry_completion_failure_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert body["retry_progress_checkpoint_endpoint"] == RETRY_PROGRESS_CHECKPOINT_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)
    request = _retry_progress_checkpoint_request(history_body, row, retry_worker_attempt_body)

    first = client.post(RETRY_PROGRESS_CHECKPOINT_ENDPOINT, json=request).json()
    second_response = client.post(RETRY_PROGRESS_CHECKPOINT_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_progress_checkpoint_receipt_id"] == first["retry_progress_checkpoint_receipt_id"]
    assert second["retry_progress_checkpoint_receipt_hash"] == first["retry_progress_checkpoint_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_appends_next_sequence(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)
    first = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(history_body, row, retry_worker_attempt_body),
    ).json()

    second_response = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(
            history_body,
            row,
            retry_worker_attempt_body,
            client_request_id="candidate-b-full-corpus-workflow-retry-progress-checkpoint-second",
            retry_progress_checkpoint_sequence=2,
        ),
    )

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_progress_checkpoint_sequence"] == 2
    assert second["previous_retry_progress_checkpoint_sequence"] == 1
    assert second["previous_retry_progress_checkpoint_receipt_id"] == first["retry_progress_checkpoint_receipt_id"]


def test_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_rejects_stale_retry_worker_attempt(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)

    response = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(
            history_body,
            row,
            retry_worker_attempt_body,
            retry_worker_attempt_receipt_hash="8" * 64,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_progress_checkpoint_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_stale_retry_worker_attempt_receipt"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_rejects_non_next_sequence(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)

    response = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(
            history_body,
            row,
            retry_worker_attempt_body,
            retry_progress_checkpoint_sequence=2,
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_progress_checkpoint_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_sequence_not_next"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)
    payload = _retry_progress_checkpoint_request(
        history_body,
        row,
        retry_worker_attempt_body,
        local_path="C:\\raw\\candidate-b",
    )

    with pytest.raises(
        workflow_retry_progress_checkpoint.CandidateBFullCorpusOperatorWorkflowRetryProgressCheckpointError
    ) as exc_info:
        workflow_retry_progress_checkpoint.record_candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint(
            payload
        )

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_operator_workflow_retry_progress_checkpoint_forbidden_request_fields"
    )
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_retry_completion_failure_records_append_only(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)

    response = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(history_body, row, retry_progress_checkpoint_body),
    )

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_retry_completion_failure.SCHEMA_ID
    assert body["mode"] == workflow_retry_completion_failure.RETRY_COMPLETION_FAILURE_MODE
    assert body["retry_completion_failure_state"] == "retry_completion_failure_recorded"
    assert body["retry_terminal_outcome"] == "completed"
    assert body["terminal_failure_code"] is None
    assert body["terminal_failure_phase"] is None
    assert body["retry_attempt_number"] == 2
    assert (
        body["latest_retry_progress_checkpoint_receipt_id"]
        == retry_progress_checkpoint_body["retry_progress_checkpoint_receipt_id"]
    )
    assert (
        body["latest_retry_progress_checkpoint_receipt_hash"]
        == retry_progress_checkpoint_body["retry_progress_checkpoint_receipt_hash"]
    )
    assert (
        body["latest_retry_progress_checkpoint_authority_hash"]
        == retry_progress_checkpoint_body["retry_progress_checkpoint_authority_hash"]
    )
    assert body["retry_worker_attempt_receipt_id"] == retry_progress_checkpoint_body["retry_worker_attempt_receipt_id"]
    assert (
        body["retry_worker_attempt_authority_hash"]
        == retry_progress_checkpoint_body["retry_worker_attempt_authority_hash"]
    )
    assert body["append_only_retry_completion_failure_receipt"] is True
    assert body["exclusive_retry_terminal_receipt_per_retry_worker_attempt"] is True
    assert body["retry_progress_checkpoint_receipt_mutated"] is False
    assert body["retry_worker_attempt_receipt_mutated"] is False
    assert body["retry_scheduler_lease_receipt_mutated"] is False
    assert body["retry_queue_state_receipt_mutated"] is False
    assert body["retry_policy_receipt_mutated"] is False
    assert body["completion_failure_receipt_mutated"] is False
    assert body["failed_worker_attempt_receipt_mutated"] is False
    assert body["progress_checkpoint_receipt_mutated"] is False
    assert body["scheduler_lease_receipt_mutated"] is False
    assert body["queue_state_receipt_mutated"] is False
    assert body["source_run_receipt_mutated"] is False
    assert body["retry_completion_failure_runtime_selected"] is True
    assert body["background_process_runtime_selected_now"] is False
    assert body["job_execution_runtime_selected_now"] is False
    assert body["cancel_runtime_selected_now"] is False
    assert body["resume_runtime_selected_now"] is False
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert body["retry_completion_failure_endpoint"] == RETRY_COMPLETION_FAILURE_ENDPOINT
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_retry_completion_failure_is_idempotent(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    request = _retry_completion_failure_request(history_body, row, retry_progress_checkpoint_body)

    first = client.post(RETRY_COMPLETION_FAILURE_ENDPOINT, json=request).json()
    second_response = client.post(RETRY_COMPLETION_FAILURE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["retry_completion_failure_receipt_id"] == first["retry_completion_failure_receipt_id"]
    assert second["retry_completion_failure_receipt_hash"] == first["retry_completion_failure_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_retry_completion_failure_records_failure(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)

    response = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(
            history_body,
            row,
            retry_progress_checkpoint_body,
            retry_terminal_outcome="failed",
            terminal_failure_code="operator_safe_retry_failure",
            terminal_failure_phase="analysis",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["retry_terminal_outcome"] == "failed"
    assert body["terminal_failure_code"] == "operator_safe_retry_failure"
    assert body["terminal_failure_phase"] == "analysis"
    assert body["retry_terminal_failure_payload_operator_safe"] is True
    assert body["raw_exception_trace_admitted"] is False
    assert body["raw_log_excerpt_admitted"] is False


def test_candidate_b_full_corpus_operator_workflow_retry_terminal_status_projection_reports_completed(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    terminal_response = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(history_body, row, retry_progress_checkpoint_body),
    )
    assert terminal_response.status_code == 200
    terminal_body = terminal_response.json()

    status_response = client.post(STATUS_ENDPOINT, json=row["status_request"])

    assert status_response.status_code == 200
    projection = status_response.json()["retry_terminal_status_projection"]
    assert projection["retry_terminal_projection_state"] == "completed"
    assert projection["read_only_retry_terminal_projection"] is True
    assert projection["retry_completion_failure_receipt_available"] is True
    assert (
        projection["retry_completion_failure_receipt_id"]
        == terminal_body["retry_completion_failure_receipt_id"]
    )
    assert (
        projection["retry_completion_failure_receipt_hash"]
        == terminal_body["retry_completion_failure_receipt_hash"]
    )
    assert (
        projection["retry_completion_failure_authority_hash"]
        == terminal_body["retry_completion_failure_authority_hash"]
    )
    assert projection["retry_worker_attempt_receipt_id"] == terminal_body["retry_worker_attempt_receipt_id"]
    assert (
        projection["latest_retry_progress_checkpoint_receipt_id"]
        == terminal_body["latest_retry_progress_checkpoint_receipt_id"]
    )
    assert projection["retry_terminal_outcome"] == "completed"
    assert projection["terminal_failure_code"] == ""
    assert projection["terminal_failure_phase"] == ""
    assert projection["operator_safe_retry_terminal_failure_code_visible"] is False
    assert projection["operator_safe_retry_terminal_failure_phase_visible"] is False
    assert projection["retry_terminal_status_projection_runtime_selected"] is True
    assert projection["retry_terminal_receipt_creation_admitted_now"] is False
    assert projection["retry_completion_failure_receipt_mutation_admitted"] is False
    assert projection["retry_progress_checkpoint_receipt_mutation_admitted"] is False
    assert projection["retry_worker_attempt_receipt_mutation_admitted"] is False
    assert projection["job_execution_runtime_selected_now"] is False
    assert projection["cancel_runtime_selected_now"] is False
    assert projection["resume_runtime_selected_now"] is False
    assert projection["raw_local_path_exposed"] is False
    assert projection["raw_url_exposed"] is False
    assert projection["artifact_bytes_exposed"] is False

    history_response = client.get(HISTORY_ENDPOINT)
    assert history_response.status_code == 200
    refreshed_history = history_response.json()
    assert refreshed_history["history_hash"] == history_body["history_hash"]
    assert refreshed_history["history_rows"][0]["row_hash"] == row["row_hash"]
    history_projection = refreshed_history["history_rows"][0]["retry_terminal_status_projection"]
    assert history_projection["retry_terminal_projection_state"] == "completed"
    assert (
        history_projection["retry_completion_failure_receipt_id"]
        == terminal_body["retry_completion_failure_receipt_id"]
    )


def test_candidate_b_full_corpus_operator_workflow_retry_terminal_status_projection_reports_failed(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    terminal_response = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(
            history_body,
            row,
            retry_progress_checkpoint_body,
            retry_terminal_outcome="failed",
            terminal_failure_code="operator_safe_retry_failure",
            terminal_failure_phase="analysis",
        ),
    )
    assert terminal_response.status_code == 200
    terminal_body = terminal_response.json()

    status_response = client.post(STATUS_ENDPOINT, json=row["status_request"])

    assert status_response.status_code == 200
    projection = status_response.json()["retry_terminal_status_projection"]
    assert projection["retry_terminal_projection_state"] == "failed"
    assert projection["retry_terminal_outcome"] == "failed"
    assert projection["terminal_failure_code"] == "operator_safe_retry_failure"
    assert projection["terminal_failure_phase"] == "analysis"
    assert projection["operator_safe_retry_terminal_failure_code_visible"] is True
    assert projection["operator_safe_retry_terminal_failure_phase_visible"] is True
    assert projection["retry_terminal_failure_payload_operator_safe"] is True
    assert projection["retry_completion_failure_receipt_id"] == terminal_body["retry_completion_failure_receipt_id"]
    assert projection["retry_completion_failure_authority_hash"] == terminal_body[
        "retry_completion_failure_authority_hash"
    ]
    assert projection["raw_exception_trace_admitted"] is False
    assert projection["raw_log_excerpt_admitted"] is False
    assert projection["raw_local_path_exposed"] is False
    assert projection["raw_url_exposed"] is False
    assert projection["artifact_bytes_exposed"] is False

    history_response = client.get(HISTORY_ENDPOINT)
    assert history_response.status_code == 200
    refreshed_history = history_response.json()
    assert refreshed_history["history_hash"] == history_body["history_hash"]
    assert refreshed_history["history_rows"][0]["row_hash"] == row["row_hash"]
    history_projection = refreshed_history["history_rows"][0]["retry_terminal_status_projection"]
    assert history_projection["retry_terminal_projection_state"] == "failed"
    assert history_projection["terminal_failure_code"] == "operator_safe_retry_failure"
    assert history_projection["terminal_failure_phase"] == "analysis"


def test_candidate_b_full_corpus_operator_workflow_retry_terminal_status_projection_rejects_stale_receipt(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    terminal_body = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(history_body, row, retry_progress_checkpoint_body),
    ).json()
    receipt_file = _workflow_receipt_file(terminal_body["retry_completion_failure_receipt_id"])
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    receipt["operator_workflow_receipt_hash"] = "6" * 64
    receipt_file.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    status_response = client.post(STATUS_ENDPOINT, json=row["status_request"])

    assert status_response.status_code == 409
    assert status_response.json()["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_mismatch"
    )
    history_response = client.get(HISTORY_ENDPOINT)
    assert history_response.status_code == 409
    assert history_response.json()["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_history_"
        "candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_mismatch"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_terminal_status_projection_rejects_ambiguous_receipts(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    terminal_body = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(history_body, row, retry_progress_checkpoint_body),
    ).json()
    receipt_file = _workflow_receipt_file(terminal_body["retry_completion_failure_receipt_id"])
    duplicate_id = f"{workflow_status.RETRY_COMPLETION_FAILURE_RECEIPT_PREFIX}-{'9' * 24}"
    duplicate_file = _workflow_receipt_file(duplicate_id)
    duplicate_file.parent.mkdir(parents=True, exist_ok=True)
    duplicate_file.write_text(receipt_file.read_text(encoding="utf-8"), encoding="utf-8")

    status_response = client.post(STATUS_ENDPOINT, json=row["status_request"])

    assert status_response.status_code == 409
    assert status_response.json()["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_ambiguous"
    )
    history_response = client.get(HISTORY_ENDPOINT)
    assert history_response.status_code == 409
    assert history_response.json()["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_history_"
        "candidate_b_full_corpus_operator_workflow_status_retry_terminal_receipt_ambiguous"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_completion_failure_rejects_stale_retry_progress_checkpoint(
    client: TestClient,
) -> None:
    history_body, row, retry_worker_attempt_body = _retry_worker_attempt_chain(client)
    first = client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(history_body, row, retry_worker_attempt_body),
    ).json()
    client.post(
        RETRY_PROGRESS_CHECKPOINT_ENDPOINT,
        json=_retry_progress_checkpoint_request(
            history_body,
            row,
            retry_worker_attempt_body,
            client_request_id="candidate-b-full-corpus-workflow-retry-progress-checkpoint-second",
            retry_progress_checkpoint_sequence=2,
        ),
    ).json()

    response = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(history_body, row, first),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_completion_failure_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_completion_failure_retry_progress_checkpoint_not_latest"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_completion_failure_rejects_terminal_conflict(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    first_request = _retry_completion_failure_request(history_body, row, retry_progress_checkpoint_body)
    first_response = client.post(RETRY_COMPLETION_FAILURE_ENDPOINT, json=first_request)
    assert first_response.status_code == 200

    response = client.post(
        RETRY_COMPLETION_FAILURE_ENDPOINT,
        json=_retry_completion_failure_request(
            history_body,
            row,
            retry_progress_checkpoint_body,
            client_request_id="candidate-b-full-corpus-workflow-retry-completion-failure-second",
        ),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["retry_completion_failure_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_retry_completion_failure_terminal_conflict"
    )


def test_candidate_b_full_corpus_operator_workflow_retry_completion_failure_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    history_body, row, retry_progress_checkpoint_body = _retry_progress_checkpoint_chain(client)
    payload = _retry_completion_failure_request(
        history_body,
        row,
        retry_progress_checkpoint_body,
        local_path="C:\\raw\\candidate-b",
    )

    with pytest.raises(
        workflow_retry_completion_failure.CandidateBFullCorpusOperatorWorkflowRetryCompletionFailureError
    ) as exc_info:
        workflow_retry_completion_failure.record_candidate_b_full_corpus_operator_workflow_retry_completion_failure(
            payload
        )

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_operator_workflow_retry_completion_failure_forbidden_request_fields"
    )
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_lifecycle_is_idempotent(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    request = _lifecycle_request(history_body, row)

    first = client.post(LIFECYCLE_ENDPOINT, json=request).json()
    second_response = client.post(LIFECYCLE_ENDPOINT, json=request)

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["lifecycle_receipt_id"] == first["lifecycle_receipt_id"]
    assert second["lifecycle_receipt_hash"] == first["lifecycle_receipt_hash"]
    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True


def test_candidate_b_full_corpus_operator_workflow_lifecycle_rejects_stale_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]

    response = client.post(LIFECYCLE_ENDPOINT, json=_lifecycle_request(history_body, row, row_hash="6" * 64))

    assert response.status_code == 409
    body = response.json()
    assert body["lifecycle_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_lifecycle_stale_authority"


def test_candidate_b_full_corpus_operator_workflow_lifecycle_service_rejects_raw_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()
    client.post(RUN_ENDPOINT, json=_run_request()).json()
    history_body = client.get(HISTORY_ENDPOINT).json()
    row = history_body["history_rows"][0]
    payload = _lifecycle_request(history_body, row, local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_lifecycle.CandidateBFullCorpusOperatorWorkflowLifecycleError) as exc_info:
        workflow_lifecycle.expire_candidate_b_full_corpus_operator_workflow_run(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_lifecycle_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]


def test_candidate_b_full_corpus_operator_workflow_history_fails_closed_for_stale_run_receipt(
    client: TestClient,
) -> None:
    _write_source_receipt()
    run_body = client.post(RUN_ENDPOINT, json=_run_request()).json()
    run_receipt_file = (
        Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
        / run_body["operator_workflow_receipt_id"]
        / "receipt.json"
    )
    run_receipt = json.loads(run_receipt_file.read_text(encoding="utf-8"))
    run_receipt["server_owned_workflow_run"]["authority_basis"]["compare_target_set_hash"] = "6" * 64
    run_receipt_file.write_text(json.dumps(run_receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    response = client.get(HISTORY_ENDPOINT)

    assert response.status_code == 409
    body = response.json()
    assert body["history_state"] == "blocked"
    assert body["error"]["code"] == (
        "candidate_b_full_corpus_operator_workflow_history_authority_mismatch"
    )


def test_candidate_b_full_corpus_operator_workflow_history_reports_empty_configured_authority(
    client: TestClient,
) -> None:
    Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir).mkdir(parents=True)

    response = client.get(HISTORY_ENDPOINT)

    assert response.status_code == 200
    body = response.json()
    assert body["history_state"] == "available"
    assert body["receipt_count"] == 0
    assert body["history_rows"] == []


def test_candidate_b_full_corpus_operator_workflow_run_fails_closed_for_stale_authority(
    client: TestClient,
) -> None:
    _write_source_receipt()

    response = client.post(RUN_ENDPOINT, json=_run_request(compare_target_set_hash="6" * 64))

    assert response.status_code == 404
    body = response.json()
    assert body["run_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_run_source_receipt_missing"


def test_candidate_b_full_corpus_operator_workflow_run_rejects_raw_authority(
    client: TestClient,
) -> None:
    _write_source_receipt({"refs": {"candidate_b_runtime_root": "C:\\raw\\candidate-b"}})

    response = client.post(RUN_ENDPOINT, json=_run_request())

    assert response.status_code == 409
    body = response.json()
    assert body["run_state"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_run_authority_revalidation_failed"
    assert body["error"]["details"]["upstream_error"] == (
        "candidate_b_full_corpus_operator_workflow_receipt_exposes_raw_authority"
    )


def test_candidate_b_full_corpus_operator_workflow_run_service_rejects_caller_roots() -> None:
    payload = _run_request(local_path="C:\\raw\\candidate-b")

    with pytest.raises(workflow_run.CandidateBFullCorpusOperatorWorkflowRunError) as exc_info:
        workflow_run.candidate_b_full_corpus_operator_workflow_run(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_operator_workflow_run_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["local_path"]
