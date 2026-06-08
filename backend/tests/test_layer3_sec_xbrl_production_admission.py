"""Unit tests for the SEC/XBRL Layer 3 production-admission evaluator.

These tests are pure: no database, no network, no Arelle.  All inputs are
synthetic dict fixtures.  The evaluator under test is:
  backend/app/services/layer3_sec_xbrl_production_admission.py
"""
from __future__ import annotations

import pytest

from app.services.layer3_sec_xbrl_production_admission import (
    PRODUCTION_ADMISSION_SCHEMA_ID,
    evaluate_production_admission,
)


# ---------------------------------------------------------------------------
# Full-evidence fixture
# ---------------------------------------------------------------------------

def _full_evidence() -> dict:
    """Return a dict that satisfies ALL six admission criteria."""
    return {
        # corpus_validation_passed_with_ownership
        "corpus_validation_passed": True,
        "ownership_marker_present": True,
        # companyfacts_oracle_reconciled_within_tolerance
        "companyfacts_oracle_supplied": True,
        "oracle_confirmed_count": 42,
        "oracle_within_tolerance": True,
        # operator_decision_approved_ready_for_next_freeze
        "review_decision": "approved",
        "decision_reason_code": "ready_for_next_freeze",
        # value_reveal_authority_receipt_valid
        "value_reveal_authority_eligible": True,
        "value_reveal_authority_receipt_id": "rcpt-abc123",
        # no_honesty_invariant_violation
        "honesty_invariant_violation": False,
        "raw_leak_detected": False,
        # required_provisioning_present
        "production_database_touched": False,
        "isolated_in_memory_db_used": True,
        "required_provisioning_present": True,
    }


# ---------------------------------------------------------------------------
# Flag-off tests
# ---------------------------------------------------------------------------

def test_flag_off_returns_false_with_flag_disabled_reason():
    result = evaluate_production_admission(
        evidence=_full_evidence(),
        admission_flag_enabled=False,
    )
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "production_admission_flag_disabled"
    assert result["criteria"] == {}
    assert result["admission_flag_enabled"] is False


def test_no_true_path_without_flag():
    """Even with full satisfying evidence, flag=False must never yield True."""
    result = evaluate_production_admission(
        evidence=_full_evidence(),
        admission_flag_enabled=False,
    )
    assert result["production_admission_ready"] is not True


# ---------------------------------------------------------------------------
# Flag-on, all criteria met
# ---------------------------------------------------------------------------

def test_full_criteria_with_flag_on_returns_true():
    result = evaluate_production_admission(
        evidence=_full_evidence(),
        admission_flag_enabled=True,
    )
    assert result["production_admission_ready"] is True
    assert result["production_admission_blocked_reason"] == ""
    assert result["admission_flag_enabled"] is True
    assert len(result["criteria"]) == 6
    for key, val in result["criteria"].items():
        assert val["passed"] is True, f"criterion {key!r} unexpectedly failed"


# ---------------------------------------------------------------------------
# Each single unmet criterion blocks (parametrized)
# ---------------------------------------------------------------------------

_CRITERION_BREAK_CASES = [
    (
        "corpus_validation_passed_with_ownership",
        {"corpus_validation_passed": False},
        "corpus_validation_or_ownership_missing",
    ),
    (
        "companyfacts_oracle_reconciled_within_tolerance",
        {"companyfacts_oracle_supplied": False},
        "companyfacts_oracle_not_reconciled",
    ),
    (
        "operator_decision_approved_ready_for_next_freeze",
        {"review_decision": "pending"},
        "operator_decision_not_approved_ready",
    ),
    (
        "value_reveal_authority_receipt_valid",
        {"value_reveal_authority_eligible": False},
        "value_reveal_authority_not_valid",
    ),
    (
        "no_honesty_invariant_violation",
        {"honesty_invariant_violation": True},
        "honesty_invariant_unverified_or_violated",
    ),
    (
        "required_provisioning_present",
        {"required_provisioning_present": False},
        "required_provisioning_absent",
    ),
]


@pytest.mark.parametrize("criterion_key,overrides,expected_reason", _CRITERION_BREAK_CASES)
def test_each_single_unmet_criterion_blocks(criterion_key, overrides, expected_reason):
    evidence = {**_full_evidence(), **overrides}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False, (
        f"Expected False when breaking criterion {criterion_key!r}"
    )
    # The blocked_reason must be the specific reason for the broken criterion.
    # Since exactly one criterion is broken and it appears first in evaluation
    # order among the failing ones, blocked_reason == that criterion's reason.
    assert result["production_admission_blocked_reason"] == expected_reason, (
        f"criterion={criterion_key!r}: got {result['production_admission_blocked_reason']!r}, "
        f"expected {expected_reason!r}"
    )
    assert result["criteria"][criterion_key]["passed"] is False


# ---------------------------------------------------------------------------
# Empty evidence fails closed
# ---------------------------------------------------------------------------

def test_missing_evidence_fails_closed():
    result = evaluate_production_admission(evidence={}, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    # First criterion's reason (fail-closed, not an exception)
    assert result["production_admission_blocked_reason"] == "corpus_validation_or_ownership_missing"


# ---------------------------------------------------------------------------
# Schema id
# ---------------------------------------------------------------------------

def test_schema_id_present():
    result = evaluate_production_admission(evidence=_full_evidence(), admission_flag_enabled=True)
    assert result["schema_id"] == PRODUCTION_ADMISSION_SCHEMA_ID

    result_off = evaluate_production_admission(evidence={}, admission_flag_enabled=False)
    assert result_off["schema_id"] == PRODUCTION_ADMISSION_SCHEMA_ID


# ---------------------------------------------------------------------------
# Decoupling: production_readiness_claimed must NOT appear in evaluator output
# ---------------------------------------------------------------------------

def test_evaluator_output_has_no_production_readiness_claimed_key():
    """The evaluator result dict must not contain 'production_readiness_claimed'.
    The two flags are intentionally separate concepts."""
    result = evaluate_production_admission(evidence=_full_evidence(), admission_flag_enabled=True)
    assert "production_readiness_claimed" not in result

    result_off = evaluate_production_admission(evidence={}, admission_flag_enabled=False)
    assert "production_readiness_claimed" not in result_off
