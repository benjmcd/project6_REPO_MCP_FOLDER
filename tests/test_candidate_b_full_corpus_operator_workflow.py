from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(1, str(REPO_ROOT))

from app.services import (
    layer3_candidate_b_full_corpus_operator_workflow_completion_monitor as completion_monitor,
    layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status,
    layer3_candidate_b_full_corpus_operator_repeatability_checkpoint as repeatability_checkpoint,
)
from app.core.config import settings
from app.api.layer3 import Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointResponse
from tools import run_candidate_b_full_corpus_operator_workflow as workflow


def test_parser_defaults_to_operator_safe_local_ack_mode() -> None:
    args = workflow.build_parser().parse_args([])

    assert args.internal_webhook_mode == "local-ack"
    assert args.execution_mode == workflow.LOCAL_TESTCLIENT_EXECUTION_MODE
    assert args.api_base_url == ""
    assert args.material_relative_name == workflow.DEFAULT_MATERIAL_RELATIVE_NAME
    assert args.bridge_dir == str(workflow.DEFAULT_BRIDGE_DIR)
    assert args.receipt_dir == str(workflow.DEFAULT_RECEIPT_DIR)
    assert args.runtime_root_lifecycle_dir == str(workflow.DEFAULT_RUNTIME_ROOT_LIFECYCLE_DIR)


def test_runner_accepts_selected_process_execution_authority_envelope() -> None:
    args = workflow.build_parser().parse_args(
        [
            "--selected-operator-workflow-receipt-id",
            "cb-full-corpus-operator-abc123",
            "--selected-operator-workflow-receipt-hash",
            "1" * 64,
            "--selected-execution-boundary-receipt-id",
            "cb-full-corpus-operator-execution-boundary-abc123",
            "--selected-execution-boundary-receipt-hash",
            "2" * 64,
            "--selected-execution-boundary-authority-hash",
            "3" * 64,
            "--selected-process-execution-receipt-id",
            "cb-full-corpus-operator-process-execution-abc123",
            "--selected-process-execution-authority-hash",
            "4" * 64,
            "--selected-process-invocation-hash",
            "5" * 64,
            "--selected-process-launch-intent-receipt-id",
            "cb-full-corpus-operator-process-launch-intent-abc123",
            "--selected-process-launch-intent-receipt-hash",
            "6" * 64,
        ]
    )

    authority = workflow._selected_process_execution_authority(args)

    assert authority is not None
    assert authority["selected_operator_workflow_receipt_id"] == "cb-full-corpus-operator-abc123"
    envelope_input = {
        key: value
        for key, value in authority.items()
        if key != "selected_process_authority_envelope_hash"
    }
    assert authority["selected_process_authority_envelope_hash"] == workflow._stable_hash(envelope_input)


def test_runner_rejects_path_like_selected_process_execution_authority_ids() -> None:
    args = workflow.build_parser().parse_args(
        [
            "--selected-operator-workflow-receipt-id",
            "cb-full-corpus-operator-../escape",
            "--selected-operator-workflow-receipt-hash",
            "1" * 64,
            "--selected-execution-boundary-receipt-id",
            "cb-full-corpus-operator-execution-boundary-abc123",
            "--selected-execution-boundary-receipt-hash",
            "2" * 64,
            "--selected-execution-boundary-authority-hash",
            "3" * 64,
            "--selected-process-execution-receipt-id",
            "cb-full-corpus-operator-process-execution-abc123",
            "--selected-process-execution-authority-hash",
            "4" * 64,
            "--selected-process-invocation-hash",
            "5" * 64,
            "--selected-process-launch-intent-receipt-id",
            "cb-full-corpus-operator-process-launch-intent-abc123",
            "--selected-process-launch-intent-receipt-hash",
            "6" * 64,
        ]
    )

    try:
        workflow._selected_process_execution_authority(args)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "selected_process_execution_authority_id_invalid"
        assert exc.details["field"] == "selected_operator_workflow_receipt_id"
    else:
        raise AssertionError("runner accepted a path-like selected authority receipt id")


def test_live_http_mode_requires_api_base_url_and_configured_webhook() -> None:
    missing_url = workflow.build_parser().parse_args(["--execution-mode", "live-http"])
    try:
        workflow._validate_execution_contract(missing_url)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "live_http_api_base_url_required"
    else:
        raise AssertionError("live-http accepted an empty API base URL")

    local_ack = workflow.build_parser().parse_args(
        ["--execution-mode", "live-http", "--api-base-url", "http://127.0.0.1:8000/api/v1/layer3"]
    )
    try:
        workflow._validate_execution_contract(local_ack)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "live_http_internal_webhook_must_be_configured"
    else:
        raise AssertionError("live-http accepted local-ack webhook mode")

    configured = workflow.build_parser().parse_args(
        [
            "--execution-mode",
            "live-http",
            "--api-base-url",
            "http://127.0.0.1:8000/api/v1/layer3",
            "--internal-webhook-mode",
            "configured",
        ]
    )
    workflow._validate_execution_contract(configured)
    assert workflow._api_base_url_ref(configured.api_base_url).startswith("redacted://url/")


def test_live_http_client_accepts_server_root_or_layer3_api_root() -> None:
    layer3_session = _FakeHttpSession()
    layer3_client = workflow.LiveHttpLayer3Client(
        "http://127.0.0.1:8000/api/v1/layer3",
        timeout_seconds=9,
        session=layer3_session,
    )
    layer3_client.post("/api/v1/layer3/readiness", json={"client_request_id": "ready"})
    assert layer3_session.posts == [
        ("http://127.0.0.1:8000/api/v1/layer3/readiness", {"client_request_id": "ready"}, 9)
    ]

    root_session = _FakeHttpSession()
    root_client = workflow.LiveHttpLayer3Client("http://127.0.0.1:8000", timeout_seconds=5, session=root_session)
    root_client.get("/api/v1/layer3/readiness")
    assert root_session.gets == [("http://127.0.0.1:8000/api/v1/layer3/readiness", 5)]


def test_live_http_readiness_requires_candidate_b_operator_endpoints() -> None:
    args = workflow.build_parser().parse_args(
        [
            "--execution-mode",
            "live-http",
            "--api-base-url",
            "http://127.0.0.1:8000/api/v1/layer3",
            "--internal-webhook-mode",
            "configured",
        ]
    )
    ready = _FakeReadinessClient(
        {
            "candidate_b_runtime_material_bridge_admitted": True,
            "candidate_b_runtime_bridge_source_scan_admitted": True,
            "candidate_b_runtime_downstream_proof_admitted": True,
            "candidate_b_full_corpus_operator_workflow_status_admitted": True,
            "candidate_b_full_corpus_operator_workflow_run_admitted": True,
        }
    )
    workflow._assert_operator_api_ready(args, ready)

    blocked = _FakeReadinessClient(
        {
            "candidate_b_runtime_material_bridge_admitted": True,
            "candidate_b_runtime_bridge_source_scan_admitted": False,
            "candidate_b_runtime_downstream_proof_admitted": True,
            "candidate_b_full_corpus_operator_workflow_status_admitted": True,
            "candidate_b_full_corpus_operator_workflow_run_admitted": True,
        }
    )
    try:
        workflow._assert_operator_api_ready(args, blocked)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "live_http_layer3_readiness_missing"
        assert exc.details["missing_readiness"][0]["field"] == "candidate_b_runtime_bridge_source_scan_admitted"
    else:
        raise AssertionError("live-http accepted incomplete readiness")


def test_live_http_readiness_requires_server_run_endpoint() -> None:
    args = workflow.build_parser().parse_args(
        [
            "--execution-mode",
            "live-http",
            "--api-base-url",
            "http://127.0.0.1:8000/api/v1/layer3",
            "--internal-webhook-mode",
            "configured",
        ]
    )
    blocked = _FakeReadinessClient(
        {
            "candidate_b_runtime_material_bridge_admitted": True,
            "candidate_b_runtime_bridge_source_scan_admitted": True,
            "candidate_b_runtime_downstream_proof_admitted": True,
            "candidate_b_full_corpus_operator_workflow_status_admitted": True,
            "candidate_b_full_corpus_operator_workflow_run_admitted": False,
        }
    )

    try:
        workflow._assert_operator_api_ready(args, blocked)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "live_http_layer3_readiness_missing"
        assert exc.details["missing_readiness"][0]["field"] == "candidate_b_full_corpus_operator_workflow_run_admitted"
    else:
        raise AssertionError("live-http accepted missing server-run endpoint readiness")


def test_workflow_status_payload_binds_live_http_receipt_ids() -> None:
    receipt = {
        "receipt_id": "cb-full-corpus-operator-live-http-proof",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "bridge_receipt_id": "cb-runtime-l3-live-http-proof",
        "downstream_proof_id": "cb-runtime-downstream-proof-live-http",
    }

    assert workflow._workflow_status_payload(receipt) == {
        "client_request_id": "candidate-b-full-corpus-operator-live-http-status",
        "status_mode": "candidate_b_full_corpus_operator_workflow_status_v1",
        "operator_decision": "inspect_candidate_b_full_corpus_operator_workflow_status",
        "operator_workflow_receipt_id": "cb-full-corpus-operator-live-http-proof",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "bridge_receipt_id": "cb-runtime-l3-live-http-proof",
        "downstream_proof_id": "cb-runtime-downstream-proof-live-http",
    }


def test_workflow_run_payload_binds_live_http_server_authority() -> None:
    receipt = {
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "compare_target_set_hash": "1" * 64,
        "runtime_root_lifecycle": {
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-live-http-proof",
        },
        "corpus": {"material_relative_name": "text/target-00001.md"},
    }

    assert workflow._workflow_run_payload(receipt) == {
        "client_request_id": "candidate-b-full-corpus-operator-live-http-run",
        "run_mode": "candidate_b_full_corpus_operator_workflow_run_v1",
        "operator_decision": "start_candidate_b_full_corpus_operator_workflow",
        "runtime_root_lifecycle_receipt_id": "cb-full-corpus-runtime-roots-live-http-proof",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "compare_target_set_hash": "1" * 64,
        "material_relative_name": "text/target-00001.md",
    }


def test_live_http_workflow_run_verifies_returned_status_request(monkeypatch) -> None:
    args = workflow.build_parser().parse_args(
        [
            "--execution-mode",
            "live-http",
            "--api-base-url",
            "http://127.0.0.1:8000/api/v1/layer3",
            "--internal-webhook-mode",
            "configured",
        ]
    )
    client = _FakeWorkflowRunClient()
    receipt = {
        "receipt_id": "cb-full-corpus-operator-source",
        "receipt_hash": "2" * 64,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "compare_target_set_hash": "1" * 64,
        "bridge_receipt_id": "cb-runtime-l3-source",
        "downstream_proof_id": "cb-runtime-downstream-proof-source",
        "runtime_root_lifecycle": {
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-live-http-proof",
        },
        "corpus": {"material_relative_name": "text/target-00001.md"},
    }

    monkeypatch.setattr(workflow, "_operator_api_client", lambda *args, **kwargs: _FakeClientContext(client))

    result = workflow._verify_live_http_workflow_run(args, receipt)

    assert client.calls[0][0].endswith("/operator-workflow/run")
    assert client.calls[1][0].endswith("/operator-workflow/status")
    assert client.calls[1][1] == client.status_request
    assert result["run_endpoint_verified"] is True
    assert result["status_endpoint_verified"] is True
    assert result["run_state"] == "proven"
    assert result["workflow_status"] == "proven"
    assert result["raw_local_path_exposed"] is False
    assert result["raw_url_exposed"] is False
    assert result["selector_mutation_performed"] is False


def test_completion_monitor_projects_downstream_proven_state(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_full_corpus_operator_workflow_dir", str(tmp_path))
    row = _completion_monitor_history_row(
        process_execution_state="started",
        process_completion_state="completed",
        adopted_proof_state="proven",
    )
    history = {"history_hash": "h" * 64, "history_rows": [row]}
    monkeypatch.setattr(completion_monitor, "_current_history", lambda: history)

    result = completion_monitor.inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(
        _completion_monitor_payload(row, history)
    )

    assert result["status"] == "available"
    assert result["completion_monitor_state"] == "completed_downstream_proven"
    assert result["read_only_completion_monitor_projection"] is True
    assert result["process_control_admitted"] is False
    assert result["process_completion_result_mutation_admitted"] is False
    assert result["raw_pid_admitted"] is False
    assert result["raw_stdout_admitted"] is False
    assert result["raw_stderr_admitted"] is False
    assert result["raw_local_path_exposed"] is False
    assert result["raw_url_exposed"] is False
    assert result["frontend_durable_authority_enabled"] is False


def test_completion_monitor_projects_not_started_without_process_receipt(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_full_corpus_operator_workflow_dir", str(tmp_path))
    row = _completion_monitor_history_row(
        process_execution_state="not_started",
        process_completion_state="not_recorded",
        adopted_proof_state="not_recorded",
    )
    history = {"history_hash": "h" * 64, "history_rows": [row]}
    monkeypatch.setattr(completion_monitor, "_current_history", lambda: history)

    result = completion_monitor.inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(
        _completion_monitor_payload(row, history)
    )

    assert result["completion_monitor_state"] == "not_started"
    assert result["process_execution_projection"]["process_execution_receipt_available"] is False
    assert result["process_control_admitted"] is False


def test_completion_monitor_rejects_raw_process_authority() -> None:
    try:
        completion_monitor.inspect_candidate_b_full_corpus_operator_workflow_completion_monitor(
            {
                "client_request_id": "monitor-proof",
                "completion_monitor_mode": completion_monitor.COMPLETION_MONITOR_MODE,
                "operator_decision": completion_monitor.OPERATOR_DECISION,
                "operator_workflow_receipt_id": "cb-full-corpus-operator-proof",
                "operator_workflow_receipt_hash": "a" * 64,
                "row_hash": "b" * 64,
                "authority_basis_hash": "c" * 64,
                "history_hash": "h" * 64,
                "stdout": "raw process output",
            }
        )
    except completion_monitor.CandidateBFullCorpusOperatorWorkflowCompletionMonitorError as exc:
        assert exc.code == "candidate_b_full_corpus_operator_workflow_completion_monitor_forbidden_request_fields"
        assert "stdout" in exc.details["blocked_fields"]
    else:
        raise AssertionError("completion monitor accepted raw process authority")


def test_repeatability_checkpoint_records_append_only_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _completion_monitor_history_row(
        process_execution_state="started",
        process_completion_state="completed",
        adopted_proof_state="proven",
    )
    row["status_request"] = {"client_request_id": "status-proof"}
    history = {"history_hash": "h" * 64, "history_rows": [row]}
    status_projection = _repeatability_status_projection()
    monitor_projection = _repeatability_monitor_projection()
    monkeypatch.setattr(repeatability_checkpoint, "_current_history", lambda: history)
    monkeypatch.setattr(settings, "layer3_candidate_b_full_corpus_operator_workflow_dir", str(tmp_path))
    monkeypatch.setattr(
        repeatability_checkpoint.workflow_status,
        "candidate_b_full_corpus_operator_workflow_status",
        lambda _payload: status_projection,
    )
    monkeypatch.setattr(
        repeatability_checkpoint.completion_monitor,
        "inspect_candidate_b_full_corpus_operator_workflow_completion_monitor",
        lambda _payload: monitor_projection,
    )
    monkeypatch.setattr(repeatability_checkpoint, "_workflow_receipt_root", lambda: tmp_path)

    payload = _repeatability_payload(row, history, status_projection, monitor_projection)

    first = repeatability_checkpoint.record_candidate_b_full_corpus_operator_repeatability_checkpoint(payload)
    replay = repeatability_checkpoint.record_candidate_b_full_corpus_operator_repeatability_checkpoint(payload)

    assert first["repeatability_checkpoint_state"] == "repeatability_checkpoint_recorded"
    assert first["append_only_repeatability_checkpoint_receipt"] is True
    assert first["workflow_receipt_mutated"] is False
    assert first["actual_corpus_processing_execution_admitted_now"] is False
    assert first["process_control_admitted"] is False
    assert first["raw_local_path_exposed"] is False
    assert first["raw_url_exposed"] is False
    assert first["repeatability_checkpoint_receipt_hash"] == replay["repeatability_checkpoint_receipt_hash"]
    assert replay["idempotent_replay"] is True
    assert (tmp_path / first["repeatability_checkpoint_receipt_id"] / "receipt.json").is_file()
    Layer3CandidateBFullCorpusOperatorRepeatabilityCheckpointResponse.model_validate(first)


def test_repeatability_checkpoint_rejects_not_downstream_proven_monitor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _completion_monitor_history_row(
        process_execution_state="started",
        process_completion_state="completed",
        adopted_proof_state="proven",
    )
    row["status_request"] = {"client_request_id": "status-proof"}
    history = {"history_hash": "h" * 64, "history_rows": [row]}
    status_projection = _repeatability_status_projection()
    monitor_projection = {
        **_repeatability_monitor_projection(),
        "completion_monitor_state": "completed_without_downstream_proof",
    }
    monkeypatch.setattr(repeatability_checkpoint, "_current_history", lambda: history)
    monkeypatch.setattr(settings, "layer3_candidate_b_full_corpus_operator_workflow_dir", str(tmp_path))
    monkeypatch.setattr(
        repeatability_checkpoint.workflow_status,
        "candidate_b_full_corpus_operator_workflow_status",
        lambda _payload: status_projection,
    )
    monkeypatch.setattr(
        repeatability_checkpoint.completion_monitor,
        "inspect_candidate_b_full_corpus_operator_workflow_completion_monitor",
        lambda _payload: monitor_projection,
    )
    monkeypatch.setattr(repeatability_checkpoint, "_workflow_receipt_root", lambda: tmp_path)

    try:
        repeatability_checkpoint.record_candidate_b_full_corpus_operator_repeatability_checkpoint(
            _repeatability_payload(row, history, status_projection, monitor_projection)
        )
    except repeatability_checkpoint.CandidateBFullCorpusOperatorRepeatabilityCheckpointError as exc:
        assert exc.code == (
            "candidate_b_full_corpus_operator_repeatability_checkpoint_completion_monitor_not_downstream_proven"
        )
    else:
        raise AssertionError("repeatability checkpoint accepted a non-downstream-proven monitor")


def test_repeatability_checkpoint_rejects_raw_request_authority() -> None:
    payload = {
        "client_request_id": "repeatability-proof",
        "repeatability_checkpoint_mode": repeatability_checkpoint.REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": repeatability_checkpoint.OPERATOR_DECISION,
        "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
        "operator_workflow_receipt_hash": "a" * 64,
        "row_hash": "b" * 64,
        "authority_basis_hash": "c" * 64,
        "history_hash": "h" * 64,
        "workflow_status_hash": "s" * 64,
        "completion_monitor_hash": "m" * 64,
        "runtime_root_lifecycle_receipt_id": "cb-full-corpus-runtime-roots-proof",
        "bridge_receipt_id": "candidate-b-runtime-bridge-proof",
        "downstream_proof_id": "candidate-b-downstream-proof",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "compare_target_set_hash": "4" * 64,
        "material_relative_name": "candidate-b/material.md",
        "operator_runbook_repeatability_steps": list(repeatability_checkpoint.REQUIRED_RUNBOOK_STEPS),
        "stdout": "raw output is not admitted",
    }

    try:
        repeatability_checkpoint.record_candidate_b_full_corpus_operator_repeatability_checkpoint(payload)
    except repeatability_checkpoint.CandidateBFullCorpusOperatorRepeatabilityCheckpointError as exc:
        assert exc.code == (
            "candidate_b_full_corpus_operator_repeatability_checkpoint_forbidden_request_fields"
        )
        assert "stdout" in exc.details["blocked_fields"]
    else:
        raise AssertionError("repeatability checkpoint accepted raw request authority")


def _completion_monitor_payload(row: dict[str, object], history: dict[str, object]) -> dict[str, object]:
    process_execution = row["process_execution_projection"]
    process_completion = row["process_completion_result_projection"]
    adopted_proof = row["adopted_result_downstream_proof_projection"]
    return {
        "client_request_id": "monitor-proof",
        "completion_monitor_mode": completion_monitor.COMPLETION_MONITOR_MODE,
        "operator_decision": completion_monitor.OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "process_execution_receipt_id": process_execution["process_execution_receipt_id"],
        "process_execution_receipt_hash": process_execution["process_execution_receipt_hash"],
        "process_completion_result_receipt_id": process_completion["process_completion_result_receipt_id"],
        "process_completion_result_receipt_hash": process_completion["process_completion_result_receipt_hash"],
        "adopted_result_downstream_proof_receipt_id": adopted_proof[
            "adopted_result_downstream_proof_receipt_id"
        ],
        "adopted_result_downstream_proof_receipt_hash": adopted_proof[
            "adopted_result_downstream_proof_receipt_hash"
        ],
    }


def _completion_monitor_history_row(
    *,
    process_execution_state: str,
    process_completion_state: str,
    adopted_proof_state: str,
) -> dict[str, object]:
    return {
        "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
        "operator_workflow_receipt_hash": "a" * 64,
        "row_hash": "b" * 64,
        "authority_basis_hash": "c" * 64,
        "run_state": "proven",
        "process_execution_projection": {
            "process_execution_projection_state": process_execution_state,
            "process_execution_receipt_available": process_execution_state == "started",
            "process_execution_receipt_id": (
                "cb-full-corpus-operator-process-execution-proof"
                if process_execution_state == "started"
                else ""
            ),
            "process_execution_receipt_hash": "d" * 64 if process_execution_state == "started" else "",
            "process_execution_authority_hash": "e" * 64 if process_execution_state == "started" else "",
        },
        "process_completion_result_projection": {
            "process_completion_result_projection_state": process_completion_state,
            "process_completion_result_receipt_available": process_completion_state != "not_recorded",
            "process_completion_result_receipt_id": (
                "cb-full-corpus-operator-process-result-proof"
                if process_completion_state != "not_recorded"
                else ""
            ),
            "process_completion_result_receipt_hash": (
                "f" * 64 if process_completion_state != "not_recorded" else ""
            ),
            "process_completion_result_authority_hash": (
                "1" * 64 if process_completion_state != "not_recorded" else ""
            ),
        },
        "adopted_result_downstream_proof_projection": {
            "adopted_result_downstream_proof_projection_state": adopted_proof_state,
            "adopted_result_downstream_proof_receipt_available": adopted_proof_state == "proven",
            "adopted_result_downstream_proof_receipt_id": (
                "cb-full-corpus-operator-adopted-result-downstream-proof-proof"
                if adopted_proof_state == "proven"
                else ""
            ),
            "adopted_result_downstream_proof_receipt_hash": "2" * 64 if adopted_proof_state == "proven" else "",
            "adopted_result_downstream_proof_authority_hash": (
                "3" * 64 if adopted_proof_state == "proven" else ""
            ),
        },
    }


def _repeatability_status_projection() -> dict[str, object]:
    return {
        "workflow_status": "proven",
        "workflow_status_hash": "s" * 64,
        "workflow_receipt_id": "cb-full-corpus-operator-run-proof",
        "workflow_receipt_hash": "a" * 64,
        "bridge_receipt_id": "candidate-b-runtime-bridge-proof",
        "downstream_proof_id": "candidate-b-downstream-proof",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "compare_target_set_hash": "4" * 64,
        "corpus": {"material_relative_name": "candidate-b/material.md"},
        "runtime_root_lifecycle": {
            "available": True,
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-proof",
            "lifecycle_receipt_hash": "5" * 64,
            "runtime_parent_ref": "redacted://runtime-parent",
            "root_count": 3,
            "validate_only_triplet": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
        "artifact_family": {
            "source_pdfs_retained": True,
            "annotated_pdfs_retained": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
        "layer3": {"material_preview_compatible": True, "gate_b_compatible": True},
        "baseline_rollback": {"available": True},
    }


def _repeatability_monitor_projection() -> dict[str, object]:
    process_execution = {
        "process_execution_projection_state": "started",
        "process_execution_receipt_available": True,
        "process_execution_receipt_id": "cb-full-corpus-operator-process-execution-proof",
        "process_execution_receipt_hash": "d" * 64,
        "process_execution_authority_hash": "e" * 64,
    }
    process_completion = {
        "process_completion_result_projection_state": "completed",
        "process_completion_result_receipt_available": True,
        "process_completion_result_receipt_id": "cb-full-corpus-operator-process-result-proof",
        "process_completion_result_receipt_hash": "f" * 64,
        "process_completion_result_authority_hash": "1" * 64,
    }
    adopted_proof = {
        "adopted_result_downstream_proof_projection_state": "proven",
        "adopted_result_downstream_proof_receipt_available": True,
        "adopted_result_downstream_proof_receipt_id": (
            "cb-full-corpus-operator-adopted-result-downstream-proof-proof"
        ),
        "adopted_result_downstream_proof_receipt_hash": "2" * 64,
        "adopted_result_downstream_proof_authority_hash": "3" * 64,
    }
    return {
        "completion_monitor_state": "completed_downstream_proven",
        "completion_monitor_hash": "m" * 64,
        "process_execution_projection": process_execution,
        "process_completion_result_projection": process_completion,
        "adopted_result_downstream_proof_projection": adopted_proof,
    }


def _repeatability_payload(
    row: dict[str, object],
    history: dict[str, object],
    status_projection: dict[str, object],
    monitor_projection: dict[str, object],
) -> dict[str, object]:
    return {
        "client_request_id": "repeatability-proof",
        "repeatability_checkpoint_mode": repeatability_checkpoint.REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": repeatability_checkpoint.OPERATOR_DECISION,
        "operator_workflow_receipt_id": row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": row["operator_workflow_receipt_hash"],
        "row_hash": row["row_hash"],
        "authority_basis_hash": row["authority_basis_hash"],
        "history_hash": history["history_hash"],
        "workflow_status_hash": status_projection["workflow_status_hash"],
        "completion_monitor_hash": monitor_projection["completion_monitor_hash"],
        "runtime_root_lifecycle_receipt_id": "cb-full-corpus-runtime-roots-proof",
        "bridge_receipt_id": status_projection["bridge_receipt_id"],
        "downstream_proof_id": status_projection["downstream_proof_id"],
        "baseline_run_id": status_projection["baseline_run_id"],
        "candidate_a_run_id": status_projection["candidate_a_run_id"],
        "candidate_b_run_id": status_projection["candidate_b_run_id"],
        "compare_target_set_hash": status_projection["compare_target_set_hash"],
        "material_relative_name": "candidate-b/material.md",
        "operator_runbook_repeatability_steps": list(repeatability_checkpoint.REQUIRED_RUNBOOK_STEPS),
    }


def test_coverage_evidence_binds_delivery_artifact_authority() -> None:
    retained_hash = "a" * 64

    evidence = workflow._coverage_evidence(retained_hash)

    assert set(evidence) == set(workflow.layer3_candidate_b_downstream_proof.REQUIRED_COVERAGE)
    for step, entry in evidence.items():
        assert entry["status"] == "proven"
        assert entry["raw_local_path_exposed"] is False
        assert entry["raw_url_exposed"] is False
        assert entry["provider_public_url_enabled"] is False
        assert entry["provider_object_writes_enabled"] is False
        assert entry["connector_dispatch_enabled"] is False
        assert entry["rag_vector_model_runtime_enabled"] is False
        assert entry["frontend_durable_authority_enabled"] is False
        if step in workflow.layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE:
            assert entry["candidate_b_retained_artifact_family_hash"] == retained_hash
            assert entry["candidate_b_delivery_artifact_roles_bound"] is True
        else:
            assert "candidate_b_delivery_artifact_roles_bound" not in entry


def test_operator_eligibility_summary_records_counts_and_rollback() -> None:
    summary = workflow._operator_eligibility_summary(
        corpus_pdf_count=69,
        source_directory_eligible_file_count=71,
        target_status_counts={
            "baseline": {"recommended": 69},
            "candidate_a": {"recommended": 69},
            "candidate_b": {"recommended": 69},
        },
    )

    assert summary == {
        "corpus_pdf_count": 69,
        "eligible_pdf_count": 69,
        "skipped_pdf_count": 0,
        "failed_pdf_count": 0,
        "source_directory_eligible_file_count": 71,
        "source_directory_extra_material_file_count": 2,
        "all_eligible_pdfs_processed": True,
        "candidate_b_target_status_counts": {"recommended": 69},
    }
    assert workflow._baseline_rollback_summary() == {
        "available": True,
        "selector": "baseline",
        "explicit_document_processing_engine": "baseline",
        "depends_on_candidate_b_artifacts": False,
        "candidate_a_visual_lane_preserved": True,
        "rollback_requires_selector_mutation": False,
    }


def test_operator_workflow_receipt_hash_binds_eligibility_and_rollback() -> None:
    assert "corpus" in workflow_status.WORKFLOW_RECEIPT_HASH_KEYS
    assert "baseline_rollback" in workflow_status.WORKFLOW_RECEIPT_HASH_KEYS
    receipt_input = {
        "schema_id": workflow.SCHEMA_ID,
        "schema_version": workflow.SCHEMA_VERSION,
        "workflow_mode": workflow.WORKFLOW_MODE,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-run",
        "compare_target_set_hash": "1" * 64,
        "bridge_receipt_id": "cb-runtime-l3-aaaaaaaaaaaaaaaaaaaaaaaa",
        "bridge_receipt_hash": "2" * 64,
        "downstream_proof_id": "cb-runtime-downstream-proof-bbbbbbbbbbbbbbbbbbbbbbbb",
        "downstream_proof_hash": "3" * 64,
        "coverage_count": 17,
        "corpus": {
            "corpus_pdf_count": 69,
            "eligible_file_count": 71,
            "material_relative_name": "text/target-00001.md",
            "target_status_counts": {"candidate_b": {"recommended": 69}},
            "eligibility_summary": {"eligible_pdf_count": 69},
        },
        "baseline_rollback": workflow._baseline_rollback_summary(),
        "runtime_root_lifecycle": {
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-proof",
            "lifecycle_receipt_hash": "5" * 64,
        },
    }
    original_hash = workflow._stable_hash(receipt_input)
    tampered_corpus = {
        **receipt_input,
        "corpus": {
            **receipt_input["corpus"],
            "eligibility_summary": {"eligible_pdf_count": 68},
        },
    }
    tampered_rollback = {
        **receipt_input,
        "baseline_rollback": {
            **receipt_input["baseline_rollback"],
            "depends_on_candidate_b_artifacts": True,
        },
    }

    assert workflow._stable_hash(tampered_corpus) != original_hash
    assert workflow._stable_hash(tampered_rollback) != original_hash


def test_prepare_package_uses_hybrid_authority_api_without_session_helper() -> None:
    client = _FakeLayer3Client()

    analysis_payload, _analysis, _prepare_payload, prepare = workflow._prepare_package(
        client,  # type: ignore[arg-type]
        {"session_id": "gate-b-session"},
        request_prefix="candidate-b-full-corpus-operator",
    )

    assert client.calls[0][0].endswith("/hybrid-authority/prepare")
    assert client.calls[0][1] == {
        "client_request_id": "candidate-b-full-corpus-operator-hybrid-authority",
        "session_id": "gate-b-session",
        "query_text": "Candidate B full-corpus normalized text",
        "analysis_question": "What Candidate B runtime material is available?",
        "analysis_focus": "Candidate B full-corpus operator workflow",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    assert analysis_payload["material_snapshot_id"] == "material-snapshot"
    assert analysis_payload["index_authority_hash"] == "a" * 64
    assert analysis_payload["embedding_index_authority_hash"] == "b" * 64
    assert prepare["external_export_download_record_ref"] == "download-record"
    assert not hasattr(client, "layer3_session_factory")


def test_source_scan_uses_bridge_receipt_api_without_source_dir_mutation() -> None:
    client = _FakeLayer3Client()

    scan = workflow._scan_bridge_curated_source(
        client,  # type: ignore[arg-type]
        bridge_receipt_id="cb-runtime-l3-source-scan-proof",
        candidate_b_run_id="candidate-b-run",
        baseline_run_id="baseline-run",
        candidate_a_run_id="candidate-a-run",
    )

    assert client.calls[0][0].endswith("/candidate-b/runtime/material-bridge/source-scan")
    assert client.calls[0][1] == {
        "client_request_id": "candidate-b-full-corpus-operator-source-scan",
        "source_scan_mode": "candidate_b_runtime_bridge_curated_source_scan_v1",
        "operator_decision": "scan_candidate_b_runtime_bridge_curated_material_root",
        "bridge_receipt_id": "cb-runtime-l3-source-scan-proof",
        "candidate_b_run_id": "candidate-b-run",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "operator_confirmation": True,
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }
    assert scan["source_root_ref"] == "candidate-b-runtime-bridge://cb-runtime-l3-source-scan-proof/curated"
    runner_source = Path(workflow.__file__).read_text(encoding="utf-8")
    assert "settings.layer3_source_ingestion_dir = str(curated_root)" not in runner_source


def test_path_ref_redacts_paths_outside_checkout(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    inside = checkout_root / "backend" / "receipt.json"
    outside = tmp_path / "outside" / "receipt.json"
    checkout_root.mkdir()
    outside.parent.mkdir()

    assert workflow._path_ref(checkout_root, inside) == "repo://backend/receipt.json"
    assert workflow._path_ref(checkout_root, outside).startswith("redacted://sha256/")


def test_runtime_discovery_storage_dir_uses_shared_explicit_parent(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    runtime_parent = tmp_path / "shared" / "storage_test_runtime" / "lc_e2e"
    baseline_root = runtime_parent / "baseline-run"
    candidate_a_root = runtime_parent / "candidate-a-run"
    candidate_b_root = runtime_parent / "candidate-b-run"
    for root in (checkout_root, baseline_root, candidate_a_root, candidate_b_root):
        root.mkdir(parents=True)

    storage_dir = workflow._runtime_discovery_storage_dir(
        checkout_root=checkout_root,
        runtime_roots=[str(baseline_root), str(candidate_a_root), str(candidate_b_root)],
    )

    assert storage_dir == runtime_parent.resolve()


def test_runtime_root_lifecycle_receipt_binds_roots_without_raw_path_leak(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    runtime_parent = tmp_path / "shared" / "storage_test_runtime" / "lc_e2e"
    roots = {
        "baseline": runtime_parent / "baseline-run",
        "candidate_a": runtime_parent / "candidate-a-run",
        "candidate_b": runtime_parent / "candidate-b-run",
    }
    checkout_root.mkdir()
    for label, root in roots.items():
        root.mkdir(parents=True)
        (root / "local_corpus_e2e_summary.json").write_text(f'{{"label":"{label}"}}', encoding="utf-8")
        (root / "lc.db").write_bytes(f"{label}-database".encode("utf-8"))

    receipt = workflow._runtime_root_lifecycle_receipt(
        checkout_root=checkout_root,
        runtime_parent=runtime_parent,
        triplet=_lifecycle_triplet(roots),
    )
    serialized = json.dumps(receipt, sort_keys=True)

    assert receipt["schema_id"] == workflow.RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID
    assert receipt["lifecycle_mode"] == workflow.RUNTIME_ROOT_LIFECYCLE_MODE
    assert receipt["lifecycle_receipt_id"].startswith("cb-full-corpus-runtime-roots-")
    assert receipt["status"] == "validated"
    assert receipt["root_count"] == 3
    assert receipt["validate_only_triplet"] is True
    assert receipt["artifacts_seeded_or_generated_by_triplet_validator"] is False
    assert receipt["negative_invariants"]["runtime_roots_moved_or_copied"] is False
    assert receipt["runtime_roots"]["candidate_b"]["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert receipt["runtime_roots"]["candidate_b"]["runtime_root_ref"].startswith("redacted://sha256/")
    assert str(runtime_parent) not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_runtime_root_lifecycle_receipt_rejects_mixed_runtime_parents(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()
    parent_a = tmp_path / "one" / "storage_test_runtime" / "lc_e2e"
    parent_b = tmp_path / "two" / "storage_test_runtime" / "lc_e2e"
    roots = {
        "baseline": parent_a / "baseline-run",
        "candidate_a": parent_a / "candidate-a-run",
        "candidate_b": parent_b / "candidate-b-run",
    }
    for root in roots.values():
        root.mkdir(parents=True)
        (root / "local_corpus_e2e_summary.json").write_text("{}", encoding="utf-8")
        (root / "lc.db").write_bytes(b"db")

    try:
        workflow._runtime_root_lifecycle_receipt(
            checkout_root=checkout_root,
            runtime_parent=None,
            triplet=_lifecycle_triplet(roots),
        )
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "runtime_root_lifecycle_parent_mismatch"
    else:
        raise AssertionError("mixed runtime parents were accepted")


def test_runtime_discovery_storage_dir_rejects_unadmitted_parent(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    runtime_root = tmp_path / "shared" / "not-runtime-parent" / "candidate-b"
    checkout_root.mkdir()
    runtime_root.mkdir(parents=True)

    try:
        workflow._runtime_discovery_storage_dir(checkout_root=checkout_root, runtime_roots=[str(runtime_root)])
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "explicit_runtime_root_parent_not_admitted"
    else:
        raise AssertionError("unadmitted explicit runtime parent was accepted")


def test_runtime_discovery_scope_restores_layer3_storage_dir(tmp_path: Path, monkeypatch) -> None:
    layer3_storage_dir = tmp_path / "layer3-storage"
    runtime_parent = tmp_path / "shared" / "storage_test_runtime" / "lc_e2e"
    monkeypatch.setattr(workflow.settings, "storage_dir", str(layer3_storage_dir))

    with workflow._runtime_discovery_scope(runtime_parent):
        assert workflow.settings.storage_dir == str(runtime_parent)

    assert workflow.settings.storage_dir == str(layer3_storage_dir)


def _patch_live_http_workflow(
    tmp_path: Path,
    monkeypatch,
) -> tuple[object, Path]:
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()
    receipt_dir = tmp_path / "operator-receipts"
    lifecycle_dir = tmp_path / "runtime-root-lifecycle"
    runtime_parent = tmp_path / "runtime-parent"
    runtime_parent.mkdir()
    args = workflow.build_parser().parse_args(
        [
            "--execution-mode",
            "live-http",
            "--api-base-url",
            "http://127.0.0.1:8000",
            "--internal-webhook-mode",
            "configured",
            "--checkout-root",
            str(checkout_root),
            "--receipt-dir",
            str(receipt_dir),
            "--runtime-root-lifecycle-dir",
            str(lifecycle_dir),
        ]
    )
    triplet = _lifecycle_triplet(
        {
            "baseline": runtime_parent / "baseline",
            "candidate_a": runtime_parent / "candidate-a",
            "candidate_b": runtime_parent / "candidate-b",
        }
    )
    monkeypatch.setattr(workflow, "_validate_triplet", lambda **_kwargs: triplet)
    monkeypatch.setattr(workflow, "_runtime_discovery_storage_dir", lambda **_kwargs: runtime_parent)
    monkeypatch.setattr(
        workflow,
        "_runtime_root_lifecycle_receipt",
        lambda **_kwargs: {
            "schema_id": workflow.RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID,
            "lifecycle_mode": workflow.RUNTIME_ROOT_LIFECYCLE_MODE,
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-proof",
            "lifecycle_receipt_hash": "5" * 64,
            "runtime_parent_ref": "redacted://sha256/runtime-parent",
            "root_count": 3,
            "status": "validated",
            "validate_only_triplet": True,
        },
    )
    monkeypatch.setattr(workflow, "_operator_api_client", lambda *args, **kwargs: _FakeClientContext(object()))
    monkeypatch.setattr(workflow, "_assert_operator_api_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        workflow,
        "_scan_bridge_curated_source",
        lambda *_args, **_kwargs: {"eligible_file_count": 69},
    )
    monkeypatch.setattr(workflow, "_approve_material", lambda *_args, **_kwargs: {"material_snapshot_id": "snapshot"})
    monkeypatch.setattr(
        workflow,
        "_prepare_package",
        lambda *_args, **_kwargs: (
            {"material_snapshot_id": "snapshot"},
            {"status": "proven"},
            {"prepare": "payload"},
            {"status": "proven"},
        ),
    )
    monkeypatch.setattr(
        workflow,
        "_prove_delivery_surfaces",
        lambda *_args, **_kwargs: {
            "same_origin_delivery_available": True,
            "provider_private_state": "not_admitted",
            "provider_private_revoke_state": "not_admitted",
            "internal_webhook_state": "configured",
        },
    )

    def _post_json(_client: object, path: str, _payload: dict[str, object]) -> dict[str, object]:
        if path.endswith("/candidate-b/runtime/material-bridge"):
            return {
                "status": "proven",
                "bridge_receipt_id": "cb-runtime-l3-live-http-proof",
                "authority_hashes": {
                    "bridge_receipt_hash": "2" * 64,
                    "governed_retained_artifact_family_hash": "a" * 64,
                },
                "governed_retained_artifact_family": {"role_counts": {"source_pdf": 69}},
                "admitted_artifact_subset": {"file_count": 69, "text_files": ["target-00001.md"]},
            }
        if path.endswith("/candidate-b/visual-lane/status"):
            return {"visual_lane_status": "proven"}
        if path.endswith("/candidate-b/runtime/downstream-proof"):
            return {
                "proof_receipt_id": "cb-runtime-downstream-proof-live-http",
                "proof_hash": "3" * 64,
                "coverage": [{"status": "proven"}],
                "status": "proven",
            }
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr(workflow, "_post_json", _post_json)
    return args, receipt_dir


def test_live_http_operator_receipt_is_visible_before_endpoint_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    args, receipt_dir = _patch_live_http_workflow(tmp_path, monkeypatch)

    def _verified_status(_args: object, receipt: dict[str, object]) -> dict[str, object]:
        receipt_files = list(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json"))
        assert len(receipt_files) == 1
        persisted = json.loads(receipt_files[0].read_text(encoding="utf-8"))
        assert persisted["receipt_id"] == receipt["receipt_id"]
        assert persisted["receipt_hash"] == receipt["receipt_hash"]
        assert persisted["status"] == "proven"
        assert persisted["live_http_verification"]["state"] == "pending"
        return {
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "operator_projection": {"status": "proven"},
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        }

    def _verified_run(_args: object, receipt: dict[str, object]) -> dict[str, object]:
        receipt_file = next(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json"))
        persisted = json.loads(receipt_file.read_text(encoding="utf-8"))
        assert persisted["receipt_id"] == receipt["receipt_id"]
        assert persisted["live_http_verification"]["state"] == "pending"
        return {
            "run_endpoint_verified": True,
            "run_state": "proven",
            "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
            "operator_workflow_receipt_hash": "3" * 64,
            "source_operator_workflow_receipt_id": receipt["receipt_id"],
            "source_operator_workflow_receipt_hash": receipt["receipt_hash"],
            "authority_basis_hash": "4" * 64,
            "idempotency_key_hash": "5" * 64,
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "selector_mutation_performed": False,
            "rendered_run_start_control_admitted": True,
            "rendered_progress_control_admitted": True,
        }

    monkeypatch.setattr(workflow, "_verify_live_http_workflow_status", _verified_status)
    monkeypatch.setattr(workflow, "_verify_live_http_workflow_run", _verified_run)

    result = workflow.run_operator_workflow(args)

    assert result["live_http_verification"]["state"] == "verified"
    persisted = json.loads(next(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json")).read_text(encoding="utf-8"))
    assert persisted["status"] == "proven"
    assert persisted["live_http_verification"]["state"] == "verified"
    assert persisted["receipt_hash"] == result["receipt_hash"]


def test_live_http_verified_receipt_retry_returns_existing_proof(
    tmp_path: Path,
    monkeypatch,
) -> None:
    args, receipt_dir = _patch_live_http_workflow(tmp_path, monkeypatch)
    calls = {"status": 0, "run": 0}

    def _verified_status(_args: object, _receipt: dict[str, object]) -> dict[str, object]:
        calls["status"] += 1
        return {
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "operator_projection": {"status": "proven"},
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        }

    def _verified_run(_args: object, receipt: dict[str, object]) -> dict[str, object]:
        calls["run"] += 1
        return {
            "run_endpoint_verified": True,
            "run_state": "proven",
            "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
            "operator_workflow_receipt_hash": "3" * 64,
            "source_operator_workflow_receipt_id": receipt["receipt_id"],
            "source_operator_workflow_receipt_hash": receipt["receipt_hash"],
            "authority_basis_hash": "4" * 64,
            "idempotency_key_hash": "5" * 64,
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "selector_mutation_performed": False,
            "rendered_run_start_control_admitted": True,
            "rendered_progress_control_admitted": True,
        }

    monkeypatch.setattr(workflow, "_verify_live_http_workflow_status", _verified_status)
    monkeypatch.setattr(workflow, "_verify_live_http_workflow_run", _verified_run)

    first = workflow.run_operator_workflow(args)
    second = workflow.run_operator_workflow(args)

    assert calls == {"status": 1, "run": 1}
    assert second["receipt_id"] == first["receipt_id"]
    assert second["receipt_hash"] == first["receipt_hash"]
    assert second["live_http_verification"]["state"] == "verified"
    persisted = json.loads(next(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json")).read_text(encoding="utf-8"))
    assert persisted["live_http_verification"]["state"] == "verified"
    assert persisted["status"] == "proven"


def test_live_http_verified_receipt_retry_failure_preserves_existing_proof(
    tmp_path: Path,
    monkeypatch,
) -> None:
    args, receipt_dir = _patch_live_http_workflow(tmp_path, monkeypatch)
    monkeypatch.setattr(
        workflow,
        "_verify_live_http_workflow_status",
        lambda *_args, **_kwargs: {
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "operator_projection": {"status": "proven"},
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
    )
    monkeypatch.setattr(
        workflow,
        "_verify_live_http_workflow_run",
        lambda _args, receipt: {
            "run_endpoint_verified": True,
            "run_state": "proven",
            "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
            "operator_workflow_receipt_hash": "3" * 64,
            "source_operator_workflow_receipt_id": receipt["receipt_id"],
            "source_operator_workflow_receipt_hash": receipt["receipt_hash"],
            "authority_basis_hash": "4" * 64,
            "idempotency_key_hash": "5" * 64,
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "selector_mutation_performed": False,
            "rendered_run_start_control_admitted": True,
            "rendered_progress_control_admitted": True,
        },
    )
    first = workflow.run_operator_workflow(args)

    def _fail_status_verification(_args: object, _receipt: dict[str, object]) -> dict[str, object]:
        raise workflow.OperatorWorkflowError(
            "live_http_status_verification_failed",
            "live status verification failed",
        )

    monkeypatch.setattr(workflow, "_verify_live_http_workflow_status", _fail_status_verification)
    second = workflow.run_operator_workflow(args)

    assert second["receipt_id"] == first["receipt_id"]
    assert second["live_http_verification"]["state"] == "verified"
    persisted = json.loads(next(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json")).read_text(encoding="utf-8"))
    assert persisted["status"] == "proven"
    assert persisted["live_http_verification"]["state"] == "verified"
    assert persisted["receipt_hash"] == first["receipt_hash"]


def test_live_http_operator_receipt_blocks_when_status_verification_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    args, receipt_dir = _patch_live_http_workflow(tmp_path, monkeypatch)

    def _fail_status_verification(_args: object, _receipt: dict[str, object]) -> dict[str, object]:
        raise workflow.OperatorWorkflowError(
            "live_http_status_verification_failed",
            "live status verification failed",
        )

    monkeypatch.setattr(workflow, "_verify_live_http_workflow_status", _fail_status_verification)

    try:
        workflow.run_operator_workflow(args)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "live_http_status_verification_failed"
    else:
        raise AssertionError("live-http workflow persisted before failing status verification")

    receipt_file = next(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json"))
    persisted = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert persisted["status"] == "blocked"
    assert persisted["live_http_verification"]["state"] == "blocked"
    assert persisted["live_http_verification"]["failure_code"] == "live_http_status_verification_failed"
    assert persisted["live_http_verification"]["final_proven_receipt_admitted"] is False
    assert "live_http_server_run_check" not in persisted


def test_live_http_operator_receipt_blocks_when_run_verification_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    args, receipt_dir = _patch_live_http_workflow(tmp_path, monkeypatch)

    monkeypatch.setattr(
        workflow,
        "_verify_live_http_workflow_status",
        lambda *_args, **_kwargs: {
            "status_endpoint_verified": True,
            "workflow_status": "proven",
            "workflow_status_hash": "6" * 64,
            "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
            "operator_projection": {"status": "proven"},
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
    )

    def _fail_run_verification(_args: object, _receipt: dict[str, object]) -> dict[str, object]:
        raise workflow.OperatorWorkflowError(
            "live_http_run_verification_failed",
            "live run verification failed",
        )

    monkeypatch.setattr(workflow, "_verify_live_http_workflow_run", _fail_run_verification)

    try:
        workflow.run_operator_workflow(args)
    except workflow.OperatorWorkflowError as exc:
        assert exc.code == "live_http_run_verification_failed"
    else:
        raise AssertionError("live-http workflow finalized after failing run verification")

    persisted = json.loads(next(receipt_dir.glob("cb-full-corpus-operator-*/receipt.json")).read_text(encoding="utf-8"))
    assert persisted["status"] == "blocked"
    assert persisted["live_http_verification"]["state"] == "blocked"
    assert persisted["live_http_verification"]["failure_code"] == "live_http_run_verification_failed"
    assert persisted["live_http_verification"]["final_proven_receipt_admitted"] is False
    assert persisted["live_http_status_check"]["status_endpoint_verified"] is True


def test_runtime_root_ref_redacts_external_paths_and_wraps_repo_relative(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    inside_relative = "backend/app/storage_test_runtime/lc_e2e/baseline-run"
    outside = tmp_path / "outside" / "storage_test_runtime" / "lc_e2e" / "candidate-b-run"
    checkout_root.mkdir()
    outside.mkdir(parents=True)

    assert workflow._runtime_root_ref(checkout_root, inside_relative) == f"repo://{inside_relative}"
    outside_ref = workflow._runtime_root_ref(checkout_root, str(outside))
    assert outside_ref.startswith("redacted://sha256/")
    assert str(outside) not in outside_ref


def test_blocked_receipt_redacts_raw_paths_and_urls(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    checkout_root.mkdir()
    raw_inside = checkout_root / "backend" / "storage_test_runtime" / "secret.json"
    raw_outside = Path("D:/operator/private/source.pdf")
    raw_posix = "/var/tmp/operator/private/source.pdf"
    file_url = f"file:///{raw_inside.as_posix()}"
    raw_url = "https://provider.example/private/raw-token"
    error = workflow.OperatorWorkflowError(
        "blocked_for_test",
        f"Blocked while reading {raw_posix}.",
        details={
            "inside": str(raw_inside),
            "outside": str(raw_outside),
            "body": f"failed at {raw_inside} using {raw_outside} and {raw_posix} via {file_url} and {raw_url}",
        },
    )

    receipt = workflow._blocked_receipt(error, checkout_root=checkout_root)
    serialized = json.dumps(receipt, sort_keys=True)

    assert receipt["status"] == "blocked"
    assert receipt["negative_invariants"]["raw_local_path_exposed"] is False
    assert str(checkout_root) not in serialized
    assert "D:/" not in serialized
    assert "D:\\" not in serialized
    assert raw_posix not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized
    assert "repo://" in serialized
    assert "redacted://" in serialized


def test_blocked_receipt_persists_to_durable_redacted_storage(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    receipt_dir = checkout_root / "backend" / "app" / "storage_test_runtime" / "lc_e2e" / "operator"
    checkout_root.mkdir(parents=True)
    args = workflow.build_parser().parse_args(
        [
            "--checkout-root",
            str(checkout_root),
            "--receipt-dir",
            str(receipt_dir),
        ]
    )
    error = workflow.OperatorWorkflowError(
        "blocked_for_test",
        "Blocked while reading /var/tmp/operator/private/source.pdf.",
    )
    receipt = workflow._blocked_receipt(error, checkout_root=checkout_root)

    persisted = workflow._persist_blocked_receipt(args, receipt, checkout_root=checkout_root)

    assert persisted["status"] == "blocked"
    assert persisted["receipt_persisted"] is True
    assert persisted["receipt_id"].startswith(workflow.BLOCKED_RECEIPT_PREFIX)
    assert not persisted["receipt_id"].startswith("cb-full-corpus-operator-")
    receipt_path = receipt_dir / persisted["receipt_id"] / "receipt.json"
    assert receipt_path.is_file()
    serialized = receipt_path.read_text(encoding="utf-8")
    assert "/var/tmp" not in serialized
    assert "redacted://" in serialized


def test_api_error_body_redaction_uses_effective_checkout_root(tmp_path: Path) -> None:
    checkout_root = tmp_path / "checkout"
    raw_secret = (checkout_root / "private" / "candidate-b" / "receipt.json").as_posix()

    class _FailingPostClient:
        _operator_workflow_checkout_root = checkout_root

        def post(self, _path: str, json: dict[str, object]) -> _FakeResponse:
            return _FakeResponse({"detail": f"failed to read {raw_secret}"}, status_code=500)

    try:
        workflow._post_json(_FailingPostClient(), "/api/v1/layer3/fail", {"client_request_id": "fail"})
    except workflow.OperatorWorkflowError as exc:
        body = str(exc.details["body"])
    else:
        raise AssertionError("failing API response was accepted")

    assert str(checkout_root) not in body
    assert "repo://" in body


def test_import_does_not_override_existing_db_init_mode(monkeypatch) -> None:
    monkeypatch.setenv("DB_INIT_MODE", "create_all")
    spec = importlib.util.spec_from_file_location("workflow_import_probe", Path(workflow.__file__))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert os.environ["DB_INIT_MODE"] == "create_all"


class _FakeResponse:
    def __init__(self, body: dict[str, object], *, status_code: int = 200) -> None:
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body, sort_keys=True)

    def json(self) -> dict[str, object]:
        return self._body


class _FakeHttpSession:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, object], int]] = []
        self.gets: list[tuple[str, int]] = []

    def post(self, url: str, *, json: dict[str, object], timeout: int) -> _FakeResponse:
        self.posts.append((url, json, timeout))
        return _FakeResponse({"ok": True})

    def get(self, url: str, *, timeout: int) -> _FakeResponse:
        self.gets.append((url, timeout))
        return _FakeResponse({"ok": True})


class _FakeReadinessClient:
    def __init__(self, readiness: dict[str, object]) -> None:
        self.readiness = readiness

    def get(self, path: str) -> _FakeResponse:
        assert path == "/api/v1/layer3/readiness"
        return _FakeResponse(self.readiness)


class _FakeClientContext:
    def __init__(self, client: object) -> None:
        self.client = client

    def __enter__(self) -> object:
        return self.client

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _FakeWorkflowRunClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.status_request = {
            "client_request_id": "candidate-b-full-corpus-operator-live-http-run-status",
            "status_mode": "candidate_b_full_corpus_operator_workflow_status_v1",
            "operator_decision": "inspect_candidate_b_full_corpus_operator_workflow_status",
            "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
            "baseline_run_id": "baseline-run",
            "candidate_a_run_id": "candidate-a-run",
            "candidate_b_run_id": "candidate-b-run",
            "bridge_receipt_id": "cb-runtime-l3-source",
            "downstream_proof_id": "cb-runtime-downstream-proof-source",
        }

    def post(self, path: str, json: dict[str, object]) -> _FakeResponse:
        self.calls.append((path, json))
        if path.endswith("/operator-workflow/run"):
            return _FakeResponse(
                {
                    "run_state": "proven",
                    "operator_workflow_receipt_id": "cb-full-corpus-operator-run-proof",
                    "operator_workflow_receipt_hash": "3" * 64,
                    "source_operator_workflow_receipt_id": "cb-full-corpus-operator-source",
                    "source_operator_workflow_receipt_hash": "2" * 64,
                    "authority_basis_hash": "4" * 64,
                    "idempotency_key_hash": "5" * 64,
                    "status_request": self.status_request,
                    "raw_local_path_exposed": False,
                    "raw_url_exposed": False,
                    "selector_mutation_performed": False,
                    "rendered_run_start_control_admitted": True,
                    "rendered_progress_control_admitted": True,
                }
            )
        if path.endswith("/operator-workflow/status"):
            return _FakeResponse(
                {
                    "workflow_status": "proven",
                    "workflow_status_hash": "6" * 64,
                    "workflow_status_ref": "candidate-b-full-corpus-operator-workflow-status://proof",
                    "raw_local_path_exposed": False,
                    "raw_url_exposed": False,
                    "selector_mutation_performed": False,
                }
            )
        raise AssertionError(f"unexpected path: {path}")


class _FakeLayer3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def post(self, path: str, json: dict[str, object]) -> _FakeResponse:
        self.calls.append((path, json))
        if path.endswith("/candidate-b/runtime/material-bridge/source-scan"):
            bridge_receipt_id = str(json["bridge_receipt_id"])
            return _FakeResponse(
                {
                    "source_ingestion_batch_id": "source-batch",
                    "source_root_ref": f"candidate-b-runtime-bridge://{bridge_receipt_id}/curated",
                    "files": [],
                },
                status_code=201,
            )
        if path.endswith("/hybrid-authority/prepare"):
            return _FakeResponse(
                {
                    "authority_payload": {
                        "material_snapshot_id": "material-snapshot",
                        "source_ingestion_batch_id": "source-batch",
                        "source_ingestion_file_id": "source-file",
                        "content_sha256": "c" * 64,
                        "file_identity_hash": "d" * 64,
                        "authority_basis_hash": "e" * 64,
                        "payload_hash": "f" * 64,
                        "index_authority_hash": "a" * 64,
                        "embedding_index_authority_hash": "b" * 64,
                        "query_text": "Candidate B full-corpus normalized text",
                        "analysis_question": "What Candidate B runtime material is available?",
                        "analysis_focus": "Candidate B full-corpus operator workflow",
                        "limit": 2,
                        "offset": 0,
                        "top_k": 2,
                    }
                }
            )
        if path.endswith("/qualitative-analysis"):
            return _FakeResponse(
                {
                    "qualitative_analysis_hash": "1" * 64,
                    "source_directory_hybrid_package_review_preview_hash": "2" * 64,
                }
            )
        if path.endswith("/package/commit"):
            return _FakeResponse(
                {
                    "construction_basis_hash": "3" * 64,
                    "reconciliation_record_id": "reconciliation-record",
                    "output_package_ids": ["package-user"],
                    "package_kinds": ["user_facing"],
                    "payload_hashes": ["4" * 64],
                }
            )
        if path.endswith("/package/review/submit"):
            return _FakeResponse({"submit_record_ref": "submit-record"})
        if path.endswith("/handoff/export/prepare"):
            return _FakeResponse({"prepare_record_ref": "prepare-record", "handoff_export_envelope": {"envelope_ref": "envelope"}})
        if path.endswith("/handoff/export/download/prepare"):
            return _FakeResponse(
                {
                    "external_export_download_record_ref": "download-record",
                    "export_download_descriptor_ref": "download-descriptor",
                    "output_packages": [
                        {"output_package_id": "package-user", "package_kind": "user_facing", "payload_hash": "4" * 64}
                    ],
                }
            )
        raise AssertionError(f"unexpected path: {path}")


def _lifecycle_triplet(roots: dict[str, Path]) -> dict[str, object]:
    return {
        "validate_only": True,
        "artifacts_seeded_or_generated": False,
        "corpus_pdf_count": 69,
        "compare_target_set": {"target_set_hash": "1" * 64},
        "target_status_counts": {
            "baseline": {"recommended": 69},
            "candidate_a": {"recommended": 69},
            "candidate_b": {"recommended": 69},
        },
        "selected_runs": {
            "baseline": {
                "run_id": "baseline-run",
                "runtime_root": str(roots["baseline"]),
                "document_processing_engine": "baseline",
                "visual_lane_mode": "baseline",
            },
            "candidate_a": {
                "run_id": "candidate-a-run",
                "runtime_root": str(roots["candidate_a"]),
                "document_processing_engine": "baseline",
                "visual_lane_mode": "candidate_a_page_evidence_v1",
            },
            "candidate_b": {
                "run_id": "candidate-b-run",
                "runtime_root": str(roots["candidate_b"]),
                "document_processing_engine": "candidate_b_opendataloader_pdf",
                "visual_lane_mode": "candidate_b_opendataloader_page_evidence_v1",
            },
        },
    }
