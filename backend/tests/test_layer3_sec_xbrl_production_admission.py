"""Unit tests for the SEC/XBRL Layer 3 production-admission evaluator.

These tests are pure: no database, no network, no Arelle.  All inputs are
synthetic dict fixtures.  The evaluator under test is:
  backend/app/services/layer3_sec_xbrl_production_admission.py
"""
from __future__ import annotations

import pytest

from app.services.layer3_sec_xbrl_production_admission import (
    ORACLE_COVERAGE_QUORUM,
    PRODUCTION_ADMISSION_SCHEMA_ID,
    evaluate_production_admission,
)


# ---------------------------------------------------------------------------
# Full-evidence fixture
# ---------------------------------------------------------------------------

def _full_evidence() -> dict:
    """Return a dict that satisfies ALL seven admission criteria.

    Oracle keys use the v2 coverage-quorum vocabulary:
      oracle_confirmed_count  — facts where oracle_confirmed == "true"
      oracle_mismatch_count   — facts where oracle_confirmed == "false" (must be 0)
      oracle_total_count      — total facts in the projection_set
    The confirmed/total ratio must be >= ORACLE_COVERAGE_QUORUM (0.5).
    """
    return {
        # corpus_validation_passed_with_ownership
        "corpus_validation_passed": True,
        "ownership_marker_present": True,
        # companyfacts_oracle_coverage_quorum
        "companyfacts_oracle_supplied": True,
        "oracle_confirmed_count": 42,
        "oracle_mismatch_count": 0,
        "oracle_total_count": 42,
        # operator_decision_approved_ready_for_next_freeze
        "review_decision": "approved",
        "decision_reason_code": "ready_for_next_freeze",
        # value_reveal_authority_receipt_valid
        "value_reveal_authority_eligible": True,
        "value_reveal_authority_receipt_id": "rcpt-abc123",
        # no_honesty_invariant_violation
        "honesty_invariant_violation": False,
        "raw_leak_detected": False,
        # containment_invariants_held
        "production_database_touched": False,
        "runtime_default_changed": False,
        "value_reveal_performed": False,
        "delivery_export_enabled": False,
        # review_exceptions_zero
        "review_exception_count": 0,
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
    assert len(result["criteria"]) == 7
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
        "companyfacts_oracle_coverage_quorum",
        {"companyfacts_oracle_supplied": False},
        "companyfacts_oracle_coverage_or_mismatch_failed",
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
        "containment_invariants_held",
        {"production_database_touched": True},
        "containment_invariants_not_held",
    ),
    (
        "review_exceptions_zero",
        {"review_exception_count": 1},
        "review_exceptions_present",
    ),
]


@pytest.mark.parametrize("criterion_key,overrides,expected_reason", _CRITERION_BREAK_CASES)
def test_each_single_unmet_criterion_blocks(criterion_key, overrides, expected_reason):
    evidence = {**_full_evidence(), **overrides}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False, (
        f"Expected False when breaking criterion {criterion_key!r}"
    )
    assert result["production_admission_blocked_reason"] == expected_reason, (
        f"criterion={criterion_key!r}: got {result['production_admission_blocked_reason']!r}, "
        f"expected {expected_reason!r}"
    )
    assert result["criteria"][criterion_key]["passed"] is False


# ---------------------------------------------------------------------------
# Oracle coverage-quorum edge cases
# ---------------------------------------------------------------------------

_ORACLE_FAIL = "companyfacts_oracle_coverage_or_mismatch_failed"


def test_oracle_mismatch_nonzero_fails():
    """Any oracle mismatch (oracle_confirmed == 'false') must block — honesty floor."""
    evidence = {**_full_evidence(), "oracle_mismatch_count": 1}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == _ORACLE_FAIL
    assert result["criteria"]["companyfacts_oracle_coverage_quorum"]["passed"] is False


def test_oracle_confirmed_below_quorum_fails():
    """confirmed/total < ORACLE_COVERAGE_QUORUM must block."""
    # 1 confirmed out of 10 total = 0.1, below 0.5 quorum
    evidence = {**_full_evidence(), "oracle_confirmed_count": 1, "oracle_total_count": 10, "oracle_mismatch_count": 0}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == _ORACLE_FAIL


def test_oracle_zero_total_fails():
    """oracle_total_count == 0 must fail closed (avoids zero-division)."""
    evidence = {**_full_evidence(), "oracle_confirmed_count": 0, "oracle_total_count": 0, "oracle_mismatch_count": 0}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == _ORACLE_FAIL


def test_oracle_bool_counts_rejected():
    """bool values for oracle counts must be rejected (bool is subclass of int)."""
    for key in ("oracle_confirmed_count", "oracle_mismatch_count", "oracle_total_count"):
        evidence = {**_full_evidence(), key: True}
        result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
        assert result["production_admission_ready"] is False, f"bool accepted for {key}"
        assert result["production_admission_blocked_reason"] == _ORACLE_FAIL


def test_oracle_exactly_at_quorum_passes():
    """confirmed/total == ORACLE_COVERAGE_QUORUM exactly must pass."""
    # At quorum: 5 of 10 = 0.5 exactly
    total = 10
    confirmed = int(total * ORACLE_COVERAGE_QUORUM)  # 5
    evidence = {**_full_evidence(), "oracle_confirmed_count": confirmed, "oracle_total_count": total, "oracle_mismatch_count": 0}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["criteria"]["companyfacts_oracle_coverage_quorum"]["passed"] is True, (
        f"Expected quorum pass at {confirmed}/{total}, got: {result['production_admission_blocked_reason']!r}"
    )


def test_oracle_zero_confirmed_fails():
    """oracle_confirmed_count == 0 must fail (at least one corroboration required)."""
    evidence = {**_full_evidence(), "oracle_confirmed_count": 0, "oracle_total_count": 10, "oracle_mismatch_count": 0}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == _ORACLE_FAIL


# ---------------------------------------------------------------------------
# Containment any-true fails
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", [
    "production_database_touched",
    "runtime_default_changed",
    "value_reveal_performed",
    "delivery_export_enabled",
])
def test_containment_any_true_fails(key):
    evidence = {**_full_evidence(), key: True}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "containment_invariants_not_held"


def test_containment_missing_key_fails_closed():
    """A missing containment key must fail closed."""
    evidence = {**_full_evidence()}
    del evidence["runtime_default_changed"]
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "containment_invariants_not_held"


# ---------------------------------------------------------------------------
# review_exceptions_zero edge cases
# ---------------------------------------------------------------------------

def test_review_exceptions_nonzero_fails():
    evidence = {**_full_evidence(), "review_exception_count": 5}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "review_exceptions_present"


def test_review_exceptions_bool_fails_closed():
    """bool for review_exception_count (e.g. False) must be rejected."""
    evidence = {**_full_evidence(), "review_exception_count": False}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "review_exceptions_present"


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
    assert result["schema_id"] == "layer3.sec_xbrl_production_admission.v2"

    result_off = evaluate_production_admission(evidence={}, admission_flag_enabled=False)
    assert result_off["schema_id"] == PRODUCTION_ADMISSION_SCHEMA_ID


# ---------------------------------------------------------------------------
# Fail-closed hardening: invalid input types must not raise or pass
# ---------------------------------------------------------------------------

def test_non_numeric_oracle_confirmed_count_fails_closed():
    """Non-numeric string for oracle_confirmed_count must fail closed, not raise."""
    evidence = {**_full_evidence(), "oracle_confirmed_count": "not-a-number"}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "companyfacts_oracle_coverage_or_mismatch_failed"


def test_non_string_receipt_id_fails_closed():
    """Non-string receipt_id (e.g. a list) must fail closed, not pass truthy check."""
    evidence = {**_full_evidence(), "value_reveal_authority_receipt_id": [1]}
    result = evaluate_production_admission(evidence=evidence, admission_flag_enabled=True)
    assert result["production_admission_ready"] is False
    assert result["production_admission_blocked_reason"] == "value_reveal_authority_not_valid"


def test_truthy_nonbool_flag_does_not_enable():
    """admission_flag_enabled=1 (int) must not enable evaluation; only True does."""
    result = evaluate_production_admission(evidence=_full_evidence(), admission_flag_enabled=1)
    assert result["production_admission_ready"] is False


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
