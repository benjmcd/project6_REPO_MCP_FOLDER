from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import layer3_candidate_b_full_corpus_repeatability_rerun_trial as rerun_trial
from app.services import layer3_candidate_b_full_corpus_operator_repeatability_checkpoint as checkpoint
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64
HASH_F = "f" * 64
COMPARE_HASH = "1" * 64


def _row(receipt_id: str, receipt_hash: str, row_hash: str, authority_hash: str) -> dict[str, Any]:
    return {
        "operator_workflow_receipt_id": receipt_id,
        "operator_workflow_receipt_hash": receipt_hash,
        "row_hash": row_hash,
        "authority_basis_hash": authority_hash,
        "run_state": "proven",
        "status_request": {"operator_workflow_receipt_id": receipt_id},
        "process_execution_projection": {
            "process_execution_receipt_id": f"{receipt_id}-execution",
            "process_execution_receipt_hash": HASH_A,
        },
        "process_completion_result_projection": {
            "process_completion_result_receipt_id": f"{receipt_id}-completion",
            "process_completion_result_receipt_hash": HASH_B,
        },
        "adopted_result_downstream_proof_projection": {
            "adopted_result_downstream_proof_receipt_id": f"{receipt_id}-proof",
            "adopted_result_downstream_proof_receipt_hash": HASH_C,
        },
    }


def _status(receipt_id: str, receipt_hash: str, status_hash: str, candidate_b_run_id: str) -> dict[str, Any]:
    return {
        "workflow_status": "proven",
        "workflow_status_hash": status_hash,
        "workflow_receipt_id": receipt_id,
        "workflow_receipt_hash": receipt_hash,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": candidate_b_run_id,
        "compare_target_set_hash": COMPARE_HASH,
        "bridge_receipt_id": "cb-runtime-l3-aaaaaaaaaaaaaaaaaaaaaaaa",
        "downstream_proof_id": "cb-runtime-downstream-proof-bbbbbbbbbbbbbbbbbbbbbbbb",
        "corpus": {
            "corpus_pdf_count": 2,
            "eligible_file_count": 2,
            "material_relative_name": "text/target.md",
            "target_status_counts": {"candidate_b": {"recommended": 2}},
            "eligibility_summary": {
                "corpus_pdf_count": 2,
                "eligible_pdf_count": 2,
                "skipped_pdf_count": 0,
                "failed_pdf_count": 0,
            },
        },
        "runtime_root_lifecycle": {
            "available": True,
            "schema_id": workflow_status.RUNTIME_ROOT_LIFECYCLE_SCHEMA_ID,
            "lifecycle_mode": workflow_status.RUNTIME_ROOT_LIFECYCLE_MODE,
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-aaaaaaaaaaaaaaaaaaaaaaaa",
            "lifecycle_receipt_hash": HASH_D,
            "runtime_parent_ref": "redacted://sha256/runtime-parent",
            "root_count": 3,
            "validate_only_triplet": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
        "artifact_family": {
            "governed_retained_artifact_family_hash": HASH_E,
            "role_counts": {"material_analysis_payloads": 2, "visual_page_evidence": 2},
            "curated_file_count": 2,
            "text_file_count": 2,
        },
        "layer3": {
            "bridge_status": "prepared",
            "source_directory_scan_status": "available",
            "qualitative_analysis_status": "completed",
            "downstream_proof_status": "proven",
        },
        "baseline_rollback": {"available": True},
    }


def _monitor(monitor_hash: str) -> dict[str, Any]:
    return {
        "completion_monitor_state": "completed_downstream_proven",
        "completion_monitor_hash": monitor_hash,
        "process_execution_projection": {"process_execution_projection_state": "started"},
        "process_completion_result_projection": {"process_completion_result_projection_state": "completed"},
        "adopted_result_downstream_proof_projection": {
            "adopted_result_downstream_proof_projection_state": "proven"
        },
    }


def _checkpoint_receipt(original_row: dict[str, Any], original_status: dict[str, Any]) -> dict[str, Any]:
    checkpoint_body = {
        "operator_workflow_receipt_id": original_row["operator_workflow_receipt_id"],
        "operator_workflow_receipt_hash": original_row["operator_workflow_receipt_hash"],
        "row_hash": original_row["row_hash"],
        "authority_basis_hash": original_row["authority_basis_hash"],
        "history_hash": HASH_F,
        "workflow_status_hash": original_status["workflow_status_hash"],
        "completion_monitor_hash": HASH_A,
        "completion_monitor_state": "completed_downstream_proven",
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_run_id": "candidate-b-original",
        "compare_target_set_hash": COMPARE_HASH,
        "material_relative_name": "text/target.md",
    }
    return {
        "schema_id": checkpoint.SCHEMA_ID,
        "schema_version": checkpoint.SCHEMA_VERSION,
        "mode": checkpoint.REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": checkpoint.OPERATOR_DECISION,
        "status": "available",
        "repeatability_checkpoint_state": checkpoint.REPEATABILITY_CHECKPOINT_STATE,
        "repeatability_checkpoint_receipt_id": "cb-full-corpus-operator-repeatability-checkpoint-aaaaaaaaaaaaaaaaaaaaaaaa",
        "repeatability_checkpoint_receipt_hash": HASH_B,
        "repeatability_checkpoint_hash": HASH_C,
        "repeatability_checkpoint_authority_hash": HASH_D,
        "append_only_repeatability_checkpoint_receipt": True,
        "exclusive_repeatability_checkpoint_per_authority": True,
        "repeatability_checkpoint": checkpoint_body,
    }


@pytest.fixture()
def patched_rerun_trial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    original_row = _row("cb-full-corpus-operator-original", HASH_A, HASH_B, HASH_C)
    rerun_row = _row("cb-full-corpus-operator-rerun", HASH_D, HASH_E, HASH_F)
    original_status = _status("cb-full-corpus-operator-original", HASH_A, HASH_B, "candidate-b-original")
    rerun_status = _status("cb-full-corpus-operator-rerun", HASH_D, HASH_C, "candidate-b-rerun")
    rows = {
        original_row["operator_workflow_receipt_id"]: original_row,
        rerun_row["operator_workflow_receipt_id"]: rerun_row,
    }
    statuses = {
        original_row["operator_workflow_receipt_id"]: original_status,
        rerun_row["operator_workflow_receipt_id"]: rerun_status,
    }
    monitors = {
        original_row["operator_workflow_receipt_id"]: _monitor(HASH_A),
        rerun_row["operator_workflow_receipt_id"]: _monitor(HASH_D),
    }
    monkeypatch.setattr(rerun_trial, "_workflow_receipt_root", lambda: tmp_path)
    monkeypatch.setattr(rerun_trial, "_current_history", lambda: {"history_hash": HASH_F, "rows": list(rows.values())})
    monkeypatch.setattr(
        rerun_trial,
        "_selected_history_row",
        lambda _history, fields: rows[fields["operator_workflow_receipt_id"]],
    )
    monkeypatch.setattr(rerun_trial, "_validate_selected_authority", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        rerun_trial,
        "_validated_status_projection",
        lambda row, _fields, prefix: statuses[row["operator_workflow_receipt_id"]],
    )
    monkeypatch.setattr(
        rerun_trial,
        "_validated_completion_monitor_projection",
        lambda monitor_request, _fields, prefix: monitors[monitor_request["operator_workflow_receipt_id"]],
    )
    monkeypatch.setattr(
        rerun_trial,
        "_validated_original_checkpoint",
        lambda _fields: _checkpoint_receipt(original_row, original_status),
    )
    return {"statuses": statuses, "root": tmp_path}


def _request() -> dict[str, Any]:
    return {
        "client_request_id": "rerun-trial",
        "rerun_trial_mode": rerun_trial.RERUN_TRIAL_MODE,
        "operator_decision": rerun_trial.OPERATOR_DECISION,
        "original_repeatability_checkpoint_receipt_id": (
            "cb-full-corpus-operator-repeatability-checkpoint-aaaaaaaaaaaaaaaaaaaaaaaa"
        ),
        "original_repeatability_checkpoint_receipt_hash": HASH_B,
        "original_repeatability_checkpoint_hash": HASH_C,
        "original_repeatability_checkpoint_authority_hash": HASH_D,
        "original_operator_workflow_receipt_id": "cb-full-corpus-operator-original",
        "original_operator_workflow_receipt_hash": HASH_A,
        "original_row_hash": HASH_B,
        "original_authority_basis_hash": HASH_C,
        "original_history_hash": HASH_F,
        "original_workflow_status_hash": HASH_B,
        "original_completion_monitor_hash": HASH_A,
        "rerun_operator_workflow_receipt_id": "cb-full-corpus-operator-rerun",
        "rerun_operator_workflow_receipt_hash": HASH_D,
        "rerun_row_hash": HASH_E,
        "rerun_authority_basis_hash": HASH_F,
        "rerun_history_hash": HASH_F,
        "rerun_workflow_status_hash": HASH_C,
        "rerun_completion_monitor_hash": HASH_D,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "original_candidate_b_run_id": "candidate-b-original",
        "rerun_candidate_b_run_id": "candidate-b-rerun",
        "compare_target_set_hash": COMPARE_HASH,
        "material_relative_name": "text/target.md",
        "regression_disposition": "no_regression_observed",
        "operator_runbook_repeatability_steps": list(rerun_trial.REQUIRED_RUNBOOK_STEPS),
    }


def test_candidate_b_full_corpus_repeatability_rerun_trial_records_append_only(
    patched_rerun_trial: dict[str, Any],
) -> None:
    response = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(_request())

    assert response["repeatability_rerun_trial_state"] == rerun_trial.RERUN_TRIAL_STATE
    assert response["append_only_repeatability_rerun_trial_receipt"] is True
    assert response["original_repeatability_checkpoint_receipt_mutated"] is False
    assert response["actual_corpus_processing_execution_admitted_now"] is False
    assert response["actual_subprocess_spawn_admitted_now"] is False
    assert response["process_control_admitted"] is False
    assert response["raw_stdout_admitted"] is False
    assert response["raw_stderr_admitted"] is False
    receipt_path = (
        patched_rerun_trial["root"]
        / response["repeatability_rerun_trial_receipt_id"]
        / "receipt.json"
    )
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["repeatability_rerun_trial_hash"]


def test_candidate_b_full_corpus_repeatability_rerun_trial_is_idempotent(
    patched_rerun_trial: dict[str, Any],
) -> None:
    first = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(_request())
    second = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(_request())

    assert second["idempotent_replay"] is True
    assert second["repeatability_rerun_trial_receipt_id"] == first["repeatability_rerun_trial_receipt_id"]


def test_candidate_b_full_corpus_repeatability_rerun_trial_requires_delta_disposition(
    patched_rerun_trial: dict[str, Any],
) -> None:
    patched_rerun_trial["statuses"]["cb-full-corpus-operator-rerun"]["artifact_family"][
        "governed_retained_artifact_family_hash"
    ] = "0" * 64

    with pytest.raises(rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError) as exc_info:
        rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(_request())

    assert exc_info.value.code == "candidate_b_full_corpus_repeatability_rerun_trial_delta_disposition_required"


def test_candidate_b_full_corpus_repeatability_rerun_trial_rejects_raw_authority() -> None:
    payload = _request()
    payload["path"] = "C:\\raw\\path"

    with pytest.raises(rerun_trial.CandidateBFullCorpusRepeatabilityRerunTrialError) as exc_info:
        rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_repeatability_rerun_trial_forbidden_request_fields"
