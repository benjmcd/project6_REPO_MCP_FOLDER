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

from app.services import layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint as acceptance
from app.services import layer3_candidate_b_full_corpus_repeatability_acceptance_closeout as closeout
from app.services import layer3_candidate_b_full_corpus_repeatability_rerun_trial as rerun_trial
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status
from test_layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint import (
    _acceptance_request,
    _rerun_request,
    acceptance_authority,
)


def _acceptance_receipt(checkpoint_receipt: dict[str, Any]) -> dict[str, Any]:
    rerun_receipt = rerun_trial.record_candidate_b_full_corpus_repeatability_rerun_trial(
        _rerun_request(checkpoint_receipt)
    )
    return acceptance.record_candidate_b_full_corpus_repeatability_acceptance_checkpoint(
        _acceptance_request(checkpoint_receipt, rerun_receipt)
    )


def _closeout_request(
    acceptance_receipt: dict[str, Any],
    *,
    client_request_id: str = "acceptance-closeout",
    acceptance_disposition: str = "no_regression_observed",
) -> dict[str, Any]:
    return {
        "client_request_id": client_request_id,
        "acceptance_closeout_mode": closeout.CLOSEOUT_MODE,
        "operator_decision": closeout.OPERATOR_DECISION,
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
        "acceptance_disposition": acceptance_disposition,
        "rendered_acceptance_control_mode": closeout.RENDERED_CONTROL_MODE,
        "rendered_acceptance_control_proof_state": closeout.RENDERED_PROOF_STATE,
        "headless_rendered_proof_label": closeout.HEADLESS_RENDERED_PROOF_LABEL,
        "headed_rendered_proof_label": closeout.HEADED_RENDERED_PROOF_LABEL,
        "operator_runbook_closeout_steps": list(closeout.REQUIRED_RUNBOOK_STEPS),
        "negative_invariant_attestations": dict(closeout.REQUIRED_NEGATIVE_INVARIANTS),
    }


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_records_append_only(
    acceptance_authority: dict[str, Any],
) -> None:
    checkpoint_receipt = acceptance_authority["checkpoint_receipt"]
    acceptance_receipt = _acceptance_receipt(checkpoint_receipt)

    response = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
        _closeout_request(acceptance_receipt)
    )

    assert response["repeatability_acceptance_operator_closeout_state"] == closeout.CLOSEOUT_STATE
    assert response["append_only_repeatability_acceptance_operator_closeout_receipt"] is True
    assert response["repeatability_acceptance_checkpoint_receipt_mutated"] is False
    assert response["original_repeatability_checkpoint_receipt_mutated"] is False
    assert response["repeatability_rerun_trial_receipt_mutated"] is False
    assert response["baseline_rollback_preserved"] is True
    assert response["candidate_a_semantics_preserved"] is True
    assert response["candidate_b_default_scope_preserved"] == "eligible_effective_pdfs_only"
    assert response["negative_invariants"] == dict(closeout.REQUIRED_NEGATIVE_INVARIANTS)
    receipt_path = (
        acceptance_authority["root"]
        / response["repeatability_acceptance_operator_closeout_receipt_id"]
        / "receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["repeatability_acceptance_operator_closeout_receipt_hash"]
    assert (
        receipt["repeatability_acceptance_operator_closeout"]["rendered_acceptance_control_proof"][
            "rendered_acceptance_control_proof_state"
        ]
        == closeout.RENDERED_PROOF_STATE
    )


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_is_idempotent(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    payload = _closeout_request(acceptance_receipt)

    first = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)
    second = closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)

    assert second["idempotent_replay"] is True
    assert second["repeatability_acceptance_operator_closeout_receipt_id"] == first[
        "repeatability_acceptance_operator_closeout_receipt_id"
    ]


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_blocks_regression(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    receipt_path = (
        acceptance_authority["root"]
        / acceptance_receipt["repeatability_acceptance_checkpoint_receipt_id"]
        / "receipt.json"
    )
    mutated = json.loads(receipt_path.read_text(encoding="utf-8"))
    checkpoint = dict(mutated["repeatability_acceptance_checkpoint"])
    checkpoint["acceptance_disposition"] = acceptance.BLOCKED_DISPOSITION
    checkpoint_hash = workflow_status._stable_hash(checkpoint)
    authority = {
        **checkpoint,
        "operator_decision": acceptance.OPERATOR_DECISION,
        "repeatability_acceptance_checkpoint_hash": checkpoint_hash,
    }
    mutated["repeatability_acceptance_checkpoint"] = checkpoint
    mutated["repeatability_acceptance_checkpoint_hash"] = checkpoint_hash
    mutated["repeatability_acceptance_checkpoint_authority"] = authority
    mutated["repeatability_acceptance_checkpoint_authority_hash"] = workflow_status._stable_hash(authority)
    mutated["repeatability_acceptance_checkpoint_receipt_hash"] = workflow_status._stable_hash(
        {
            key: value
            for key, value in mutated.items()
            if key not in {"repeatability_acceptance_checkpoint_receipt_hash", "server_time"}
        }
    )
    receipt_path.write_text(json.dumps(mutated, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(
            _closeout_request(
                mutated,
                client_request_id="acceptance-closeout-blocked",
                acceptance_disposition=acceptance.BLOCKED_DISPOSITION,
            )
        )

    assert exc_info.value.code == "candidate_b_full_corpus_repeatability_acceptance_closeout_regression_detected"


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_rejects_ambiguous_rendered_proof(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    payload = _closeout_request(acceptance_receipt)
    payload["rendered_acceptance_control_proof_state"] = "headless_only"

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_proof_ambiguous"
    )


def test_candidate_b_full_corpus_repeatability_acceptance_closeout_rejects_raw_authority(
    acceptance_authority: dict[str, Any],
) -> None:
    acceptance_receipt = _acceptance_receipt(acceptance_authority["checkpoint_receipt"])
    payload = _closeout_request(acceptance_receipt)
    payload["path"] = "C:\\raw\\path"

    with pytest.raises(closeout.CandidateBFullCorpusRepeatabilityAcceptanceCloseoutError) as exc_info:
        closeout.record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout(payload)

    assert (
        exc_info.value.code
        == "candidate_b_full_corpus_repeatability_acceptance_closeout_forbidden_request_fields"
    )
