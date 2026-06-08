"""SEC/XBRL Layer 3 production-admission evaluator.

Honesty contract
----------------
``production_admission_ready`` is a COMPUTED value. It is True if and only if:

  1. ``admission_flag_enabled`` is True (operator-controlled, default OFF via
     ``SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED``), AND
  2. All seven admission criteria return ``passed=True`` from their checkers.

There is NO code path that yields ``production_admission_ready=True`` except
through that conjunction.  With the flag OFF the function returns
``production_admission_ready=False`` unconditionally, making flag-OFF output
byte-identical to the previous hardcoded behaviour.

Criteria rationale is tracked in the project's next_milestone_plans documents
under the Layer 3 SEC/XBRL production-readiness gate section.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

PRODUCTION_ADMISSION_SCHEMA_ID = "layer3.sec_xbrl_production_admission.v2"

# ---------------------------------------------------------------------------
# Feature-flag accessor
# ---------------------------------------------------------------------------

def production_admission_flag_enabled() -> bool:
    """Return True when the operator has explicitly enabled the evaluator.

    Reads ``SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED`` from the
    environment.  Accepted truthy values: ``1``, ``true``, ``yes``
    (case-insensitive).  Absent or any other value -> False (default OFF).
    """
    return os.environ.get(
        "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", ""
    ).strip().lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Per-criterion checkers
# ---------------------------------------------------------------------------

def _check_corpus_validation_passed_with_ownership(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    if evidence.get("corpus_validation_passed") is True and evidence.get("ownership_marker_present") is True:
        return True, ""
    return False, "corpus_validation_or_ownership_missing"


def _check_companyfacts_oracle_full_coverage(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    # Strictest honest threshold: oracle must have been supplied, eligible count
    # must be a positive int, and confirmed count must equal eligible count (full
    # coverage).  This deliberate default ensures no partial oracle pass silently
    # clears the gate; operators who disagree must explicitly relax it downstream.
    # bool is a subclass of int; reject it to prevent accidental truthy passage.
    if evidence.get("companyfacts_oracle_supplied") is not True:
        return False, "companyfacts_oracle_not_full_coverage"
    eligible = evidence.get("oracle_eligible_count")
    confirmed = evidence.get("oracle_confirmed_count")
    if isinstance(eligible, bool) or isinstance(confirmed, bool):
        return False, "companyfacts_oracle_not_full_coverage"
    if not isinstance(eligible, int) or eligible <= 0:
        return False, "companyfacts_oracle_not_full_coverage"
    if not isinstance(confirmed, int):
        return False, "companyfacts_oracle_not_full_coverage"
    if confirmed < eligible:
        return False, "companyfacts_oracle_not_full_coverage"
    return True, ""


def _check_operator_decision_approved_ready_for_next_freeze(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    if (
        evidence.get("review_decision") == "approved"
        and evidence.get("decision_reason_code") == "ready_for_next_freeze"
    ):
        return True, ""
    return False, "operator_decision_not_approved_ready"


def _check_value_reveal_authority_receipt_valid(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    _rid = evidence.get("value_reveal_authority_receipt_id")
    if (
        evidence.get("value_reveal_authority_eligible") is True
        and isinstance(_rid, str) and bool(_rid)
    ):
        return True, ""
    return False, "value_reveal_authority_not_valid"


def _check_no_honesty_invariant_violation(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    # Fail-closed: both keys must be present and explicitly False.
    # A missing key is treated as a violation.
    if (
        "honesty_invariant_violation" in evidence
        and "raw_leak_detected" in evidence
        and evidence["honesty_invariant_violation"] is False
        and evidence["raw_leak_detected"] is False
    ):
        return True, ""
    return False, "honesty_invariant_unverified_or_violated"


def _check_containment_invariants_held(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    # All four containment keys must be present and exactly False.
    # A missing key or any True value fails closed.
    keys = (
        "production_database_touched",
        "runtime_default_changed",
        "value_reveal_performed",
        "delivery_export_enabled",
    )
    for key in keys:
        if key not in evidence or evidence[key] is not False:
            return False, "containment_invariants_not_held"
    return True, ""


def _check_review_exceptions_zero(
    evidence: Mapping[str, Any],
) -> tuple[bool, str]:
    count = evidence.get("review_exception_count")
    # bool is a subclass of int; reject it to prevent accidental passage.
    if isinstance(count, bool):
        return False, "review_exceptions_present"
    if not isinstance(count, int):
        return False, "review_exceptions_present"
    if count != 0:
        return False, "review_exceptions_present"
    return True, ""


# ---------------------------------------------------------------------------
# Ordered admission criteria
# ---------------------------------------------------------------------------

_ADMISSION_CRITERIA: tuple[tuple[str, Any], ...] = (
    ("corpus_validation_passed_with_ownership", _check_corpus_validation_passed_with_ownership),
    ("companyfacts_oracle_full_coverage", _check_companyfacts_oracle_full_coverage),
    ("operator_decision_approved_ready_for_next_freeze", _check_operator_decision_approved_ready_for_next_freeze),
    ("value_reveal_authority_receipt_valid", _check_value_reveal_authority_receipt_valid),
    ("no_honesty_invariant_violation", _check_no_honesty_invariant_violation),
    ("containment_invariants_held", _check_containment_invariants_held),
    ("review_exceptions_zero", _check_review_exceptions_zero),
)


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate_production_admission(
    *,
    evidence: Mapping[str, Any],
    admission_flag_enabled: bool,
) -> dict[str, Any]:
    """Evaluate whether SEC/XBRL Layer 3 production admission criteria are met.

    Honesty contract: ``production_admission_ready`` is True ONLY when
    ``admission_flag_enabled`` is True AND every one of the seven criteria
    checkers returns ``passed=True``.  There is no other code path that
    produces ``True``.

    Caller contract: callers MUST gate this call via
    :func:`production_admission_flag_enabled` and provide their own legacy
    else-branch for flag-OFF byte-identity.  The evaluator's internal flag
    guard (``admission_flag_enabled is not True``) is a defense-in-depth
    backstop, not the primary gate.

    Parameters
    ----------
    evidence:
        Mapping of evidence keys produced by the calling site.  Unknown or
        missing keys cause affected criteria to fail-closed (False).  Never
        fabricate values -- omit keys for evidence the caller does not possess.
    admission_flag_enabled:
        Must be True (from :func:`production_admission_flag_enabled`) for
        evaluation to proceed.  When False the function returns immediately
        with ``production_admission_ready=False`` and an empty ``criteria``
        dict, preserving byte-identical output to the pre-evaluator default.

    Returns
    -------
    dict with keys:
        ``production_admission_ready`` (bool),
        ``production_admission_blocked_reason`` (str),
        ``criteria`` (dict of per-criterion results),
        ``admission_flag_enabled`` (bool),
        ``schema_id`` (str).
    """
    if admission_flag_enabled is not True:
        return {
            "production_admission_ready": False,
            "production_admission_blocked_reason": "production_admission_flag_disabled",
            "criteria": {},
            "admission_flag_enabled": False,
            "schema_id": PRODUCTION_ADMISSION_SCHEMA_ID,
        }

    criteria: dict[str, dict[str, Any]] = {}
    for key, checker in _ADMISSION_CRITERIA:
        passed, reason = checker(evidence)
        criteria[key] = {"passed": passed, "reason": reason}

    ready = all(c["passed"] for c in criteria.values())
    blocked_reason = ""
    if not ready:
        # Deterministic: first failing criterion in _ADMISSION_CRITERIA order.
        for key, _ in _ADMISSION_CRITERIA:
            if not criteria[key]["passed"]:
                blocked_reason = criteria[key]["reason"]
                break

    return {
        "production_admission_ready": ready,
        "production_admission_blocked_reason": blocked_reason,
        "criteria": criteria,
        "admission_flag_enabled": True,
        "schema_id": PRODUCTION_ADMISSION_SCHEMA_ID,
    }
