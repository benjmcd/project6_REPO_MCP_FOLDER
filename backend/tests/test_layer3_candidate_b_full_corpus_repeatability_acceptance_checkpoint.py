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

from app.core.config import settings
from app.services import layer3_candidate_b_operator_workflow_access_policy as access_policy
from app.services import layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint as acceptance
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
        "ownership_access_policy": {
            "actor_ref_hash": access_policy._stable_hash(
                {"auth_owner": "none", "actor_ref": access_policy.LOCAL_ACTOR_REF}
            ),
            "tenant_or_workspace_ref_hash": access_policy._stable_hash(
                {"auth_owner": "none", "tenant_or_workspace_ref": access_policy.LOCAL_TENANT_REF}
            ),
            "policy_hash": "0" * 64,
        },
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


def _write_checkpoint_receipt(root: Path, original_row: dict[str, Any], original_status: dict[str, Any]) -> dict[str, Any]:
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
    receipt_id = "cb-full-corpus-operator-repeatability-checkpoint-aaaaaaaaaaaaaaaaaaaaaaaa"
    receipt_input = {
        "schema_id": checkpoint.SCHEMA_ID,
        "schema_version": checkpoint.SCHEMA_VERSION,
        "mode": checkpoint.REPEATABILITY_CHECKPOINT_MODE,
        "operator_decision": checkpoint.OPERATOR_DECISION,
        "status": "available",
        "repeatability_checkpoint_state": checkpoint.REPEATABILITY_CHECKPOINT_STATE,
        "repeatability_checkpoint_receipt_id": receipt_id,
        "repeatability_checkpoint_hash": HASH_C,
        "repeatability_checkpoint_authority_hash": HASH_D,
        "append_only_repeatability_checkpoint_receipt": True,
        "exclusive_repeatability_checkpoint_per_authority": True,
        "repeatability_checkpoint": checkpoint_body,
    }
    receipt = {
        **receipt_input,
        "repeatability_checkpoint_receipt_hash": workflow_status._stable_hash(receipt_input),
        "server_time": "2026-05-24T00:00:00Z",
    }
    target = root / receipt_id / "receipt.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


@pytest.fixture()
def acceptance_authority(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    monkeypatch.setattr(settings, "layer3_candidate_b_full_corpus_operator_workflow_dir", str(tmp_path))
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
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
    checkpoint_receipt = _write_checkpoint_receipt(tmp_path, original_row, original_status)
    return {
        "checkpoint_receipt": checkpoint_receipt,
        "root": tmp_path,
    }


def _rerun_request(
    checkpoint_receipt: dict[str, Any],
    *,
    client_request_id: str = "rerun-trial",
    regression_disposition: str = "no_regression_observed",
) -> dict[str, Any]:
    return {
        "client_request_id": client_request_id,
        "rerun_trial_mode": rerun_trial.RERUN_TRIAL_MODE,
        "operator_decision": rerun_trial.OPERATOR_DECISION,
        "original_repeatability_checkpoint_receipt_id": checkpoint_receipt[
            "repeatability_checkpoint_receipt_id"
        ],
        "original_repeatability_checkpoint_receipt_hash": checkpoint_receipt[
            "repeatability_checkpoint_receipt_hash"
        ],
        "original_repeatability_checkpoint_hash": checkpoint_receipt["repeatability_checkpoint_hash"],
        "original_repeatability_checkpoint_authority_hash": checkpoint_receipt[
            "repeatability_checkpoint_authority_hash"
        ],
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
        "regression_disposition": regression_disposition,
        "operator_runbook_repeatability_steps": list(rerun_trial.REQUIRED_RUNBOOK_STEPS),
    }


def _acceptance_request(
    checkpoint_receipt: dict[str, Any],
    rerun_receipt: dict[str, Any],
    *,
    acceptance_disposition: str = "no_regression_observed",
) -> dict[str, Any]:
    return {
        "client_request_id": "acceptance-checkpoint",
        "acceptance_checkpoint_mode": acceptance.ACCEPTANCE_CHECKPOINT_MODE,
        "operator_decision": acceptance.OPERATOR_DECISION,
        "operator_acceptance_decision": "accept_candidate_b_full_corpus_repeatability",
        "original_repeatability_checkpoint_receipt_id": checkpoint_receipt[
            "repeatability_checkpoint_receipt_id"
        ],
        "original_repeatability_checkpoint_receipt_hash": checkpoint_receipt[
            "repeatability_checkpoint_receipt_hash"
        ],
        "original_repeatability_checkpoint_hash": checkpoint_receipt["repeatability_checkpoint_hash"],
        "original_repeatability_checkpoint_authority_hash": checkpoint_receipt[
            "repeatability_checkpoint_authority_hash"
        ],
        "repeatability_rerun_trial_receipt_id": rerun_receipt["repeatability_rerun_trial_receipt_id"],
        "repeatability_rerun_trial_receipt_hash": rerun_receipt[
            "repeatability_rerun_trial_receipt_hash"
        ],
        "repeatability_rerun_trial_hash": rerun_receipt["repeatability_rerun_trial_hash"],
        "repeatability_rerun_trial_authority_hash": rerun_receipt[
            "repeatability_rerun_trial_authority_hash"
        ],
        "original_workflow_status_hash": HASH_B,
        "original_completion_monitor_hash": HASH_A,
        "rerun_workflow_status_hash": HASH_C,
        "rerun_completion_monitor_hash": HASH_D,
        "acceptance_disposition": acceptance_disposition,
        "operator_runbook_repeatability_steps": list(acceptance.REQUIRED_RUNBOOK_STEPS),
    }


def test_candidate_b_full_corpus_repeatability_acceptance_checkpoint_records_append_only(
    acceptance_authority: dict[str, Any],
) -> None:
    checkpoint_receipt = acceptance_authority["checkpoint_receipt"]
    rerun_receipt = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(
        _rerun_request(checkpoint_receipt)
    )

    response = acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
        _acceptance_request(checkpoint_receipt, rerun_receipt)
    )

    assert response["repeatability_acceptance_checkpoint_state"] == acceptance.ACCEPTANCE_CHECKPOINT_STATE
    assert response["append_only_repeatability_acceptance_checkpoint_receipt"] is True
    assert response["original_repeatability_checkpoint_receipt_mutated"] is False
    assert response["repeatability_rerun_trial_receipt_mutated"] is False
    assert response["actual_corpus_processing_execution_admitted_now"] is False
    assert response["actual_subprocess_spawn_admitted_now"] is False
    assert response["process_control_admitted"] is False
    assert response["raw_stdout_admitted"] is False
    assert response["raw_stderr_admitted"] is False
    receipt_path = (
        acceptance_authority["root"]
        / response["repeatability_acceptance_checkpoint_receipt_id"]
        / "receipt.json"
    )
    assert json.loads(receipt_path.read_text(encoding="utf-8"))[
        "repeatability_acceptance_checkpoint_hash"
    ]


def test_candidate_b_full_corpus_repeatability_acceptance_checkpoint_is_idempotent(
    acceptance_authority: dict[str, Any],
) -> None:
    checkpoint_receipt = acceptance_authority["checkpoint_receipt"]
    rerun_receipt = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(
        _rerun_request(checkpoint_receipt)
    )
    payload = _acceptance_request(checkpoint_receipt, rerun_receipt)

    first = acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(payload)
    second = acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(payload)

    assert second["idempotent_replay"] is True
    assert second["repeatability_acceptance_checkpoint_receipt_id"] == first[
        "repeatability_acceptance_checkpoint_receipt_id"
    ]


def test_candidate_b_full_corpus_repeatability_acceptance_checkpoint_blocks_regression(
    acceptance_authority: dict[str, Any],
) -> None:
    checkpoint_receipt = acceptance_authority["checkpoint_receipt"]
    rerun_receipt = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(
        _rerun_request(
            checkpoint_receipt,
            client_request_id="rerun-trial-blocked",
            regression_disposition="regression_detected_blocked",
        )
    )

    with pytest.raises(acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError) as exc_info:
        acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
            _acceptance_request(
                checkpoint_receipt,
                rerun_receipt,
                acceptance_disposition="regression_detected_blocked",
            )
        )

    assert exc_info.value.code == "candidate_b_full_corpus_repeatability_acceptance_checkpoint_regression_detected"


def test_candidate_b_full_corpus_repeatability_acceptance_checkpoint_rejects_raw_authority(
    acceptance_authority: dict[str, Any],
) -> None:
    checkpoint_receipt = acceptance_authority["checkpoint_receipt"]
    rerun_receipt = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(
        _rerun_request(checkpoint_receipt)
    )
    payload = _acceptance_request(checkpoint_receipt, rerun_receipt)
    payload["path"] = "C:\\raw\\path"

    with pytest.raises(acceptance.CandidateBFullCorpusRepeatabilityAcceptanceCheckpointError) as exc_info:
        acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(payload)

    assert exc_info.value.code == "candidate_b_full_corpus_repeatability_acceptance_checkpoint_forbidden_request_fields"
