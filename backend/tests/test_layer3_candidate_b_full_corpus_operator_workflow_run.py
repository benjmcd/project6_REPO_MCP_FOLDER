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
from app.services import layer3_candidate_b_full_corpus_operator_workflow_lifecycle as workflow_lifecycle
from app.services import layer3_candidate_b_full_corpus_operator_workflow_queue_state as workflow_queue_state
from app.services import layer3_candidate_b_full_corpus_operator_workflow_run as workflow_run
from app.services import layer3_candidate_b_full_corpus_operator_workflow_scheduler_lease as workflow_scheduler_lease
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status
from main import app


RUN_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run"
STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status"
HISTORY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history"
LIFECYCLE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire"
QUEUE_STATE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state"
SCHEDULER_LEASE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease"
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
