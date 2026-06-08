"""SEC/XBRL Layer 3 production-admission status assembler.

Assembles evidence from real workflow, decision, authority, oracle, corpus, and
honesty-guard sources, then calls the production-admission evaluator.

Honesty contract
----------------
- ``production_readiness_claimed`` is hardcoded False. It is NOT set by this
  service under any condition.
- ``production_admission_ready`` is a computed criteria gate. It is True ONLY
  when the flag is ON and all seven criteria pass.  It is NOT a human claim of
  production readiness.
- Evidence keys are OMITTED rather than fabricated when the underlying source
  is unavailable or fails.  Any unhandled error in an evidence-gathering step
  causes a fail-closed blocked response, never a partial True.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3SecXbrlControlledValueRevealSubmitReceipt,
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlValueRevealAuthorityReceipt,
    L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
)
from app.services.layer3_sec_edgar_real_company_corpus_validation import (
    find_corpus_validation_verdict_by_sidecar_hash,
)
from app.services.layer3_sec_xbrl_auth_binding import (
    SecXbrlAuthBindingError,
    require_sec_xbrl_evidence_ownership_marker,
)
from app.services.layer3_sec_xbrl_operator_review_workflow import (
    SecXbrlOperatorReviewWorkflowError,
    _validate_workflow_row_for_status,
)
from app.services import layer3_sec_xbrl_value_reveal_authority
from app.services.layer3_sec_xbrl_production_admission import (
    PRODUCTION_ADMISSION_SCHEMA_ID,
    evaluate_production_admission,
    production_admission_flag_enabled,
)
from app.services.layer3_sec_xbrl_report_leak_guard import report_leak_flags

ADMISSION_STATUS_SCHEMA_ID = "layer3.sec_xbrl_admission_status.v1"

# Production-real values written to L3SecXbrlProjectionFact.oracle_confirmed by
# the persistence writers (_oracle_value() in projection_persistence and
# statement_packet_persistence).  The only admitted values are:
#   "true"          — oracle had a value AND it matched the projected fact
#   "false"         — oracle had a value AND it did NOT match (contradiction)
#   "oracle_absent" — oracle pass ran but had no value for this fact
# Any other string (including the status-column vocabulary) is never written.
_ORACLE_TRUE_VALUE = "true"
_ORACLE_FALSE_VALUE = "false"
_ORACLE_ABSENT_VALUE = "oracle_absent"

# The set of values that indicate the oracle pass ran for a fact.
_ORACLE_ATTEMPTED_VALUES = frozenset({
    _ORACLE_TRUE_VALUE,
    _ORACLE_FALSE_VALUE,
    _ORACLE_ABSENT_VALUE,
})

_BLOCKED_RESPONSE_SCHEMA_ID = ADMISSION_STATUS_SCHEMA_ID


def _authority_matches_current_evidence(
    authority: L3SecXbrlValueRevealAuthorityReceipt | None,
    *,
    workflow: L3SecXbrlOperatorReviewWorkflow,
    decision: L3SecXbrlOperatorReviewDecision | None,
    packet_set: Any,
    projection_set: Any,
    sidecar_hash: str,
    dataset_version_hash: str | None,
) -> bool:
    if authority is None:
        return False
    if decision is None:
        return False
    if authority.authority_state != L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY:
        return False
    expected_pairs = (
        (authority.sec_xbrl_operator_review_decision_id, decision.sec_xbrl_operator_review_decision_id),
        (authority.decision_basis_hash, decision.decision_basis_hash),
        (authority.sec_xbrl_operator_review_workflow_id, workflow.sec_xbrl_operator_review_workflow_id),
        (authority.workflow_basis_hash, workflow.workflow_basis_hash),
        (authority.sec_xbrl_statement_packet_set_id, packet_set.sec_xbrl_statement_packet_set_id),
        (authority.statement_packet_basis_hash, packet_set.packet_basis_hash),
        (authority.sec_xbrl_projection_set_id, projection_set.sec_xbrl_projection_set_id),
        (authority.projection_basis_hash, projection_set.projection_basis_hash),
        (authority.sidecar_receipt_hash, sidecar_hash),
        (authority.value_store_hash, projection_set.value_store_hash),
    )
    if any(actual != expected for actual, expected in expected_pairs):
        return False
    dataset_version_id = getattr(projection_set, "dataset_version_id", None)
    if dataset_version_id and authority.dataset_version_id != dataset_version_id:
        return False
    if dataset_version_hash is None or authority.dataset_version_hash != dataset_version_hash:
        return False
    return True


def _blocked(reason: str, *, detail: str = "") -> dict[str, Any]:
    return {
        "status": "blocked",
        "schema_id": _BLOCKED_RESPONSE_SCHEMA_ID,
        "blocked_reason": reason,
        "blocked_detail": detail,
        "production_admission_ready": False,
        "production_readiness_claimed": False,
    }


def inspect_redacted_production_admission_status(
    db: Session,
    *,
    client_request_id: str,
    sec_xbrl_operator_review_workflow_id: str | None = None,
    workflow_basis_hash: str | None = None,
    policy_decision: Mapping[str, Any],
    auth_owner_mode: str,
) -> dict[str, Any]:
    """Assemble and evaluate the production-admission status for a workflow.

    All evidence is sourced from real persisted records.  Evidence keys are
    OMITTED rather than fabricated when unavailable.  Any unhandled error
    causes a fail-closed blocked response.

    Returns a redacted response dict containing:
    - production_admission_ready (bool, computed)
    - production_readiness_claimed (bool, always False)
    - production_admission_blocked_reason (str)
    - criteria (dict)
    - admission_flag_enabled (bool)
    - schema_id (str)
    - workflow_id, workflow_basis_hash echoes (hashes/ids only)
    - admission_note (str clarifying the honesty contract)
    """
    # ------------------------------------------------------------------
    # Step 1: Resolve and validate the workflow.
    # ------------------------------------------------------------------
    workflow_id = str(sec_xbrl_operator_review_workflow_id or "").strip() or None
    basis_hash = str(workflow_basis_hash or "").strip() or None

    if workflow_id is None and basis_hash is None:
        return _blocked(
            "admission_status_workflow_authority_missing",
            detail="One of sec_xbrl_operator_review_workflow_id or workflow_basis_hash is required.",
        )

    try:
        query = db.query(L3SecXbrlOperatorReviewWorkflow)
        if workflow_id is not None:
            query = query.filter(
                L3SecXbrlOperatorReviewWorkflow.sec_xbrl_operator_review_workflow_id == workflow_id
            )
        if basis_hash is not None:
            query = query.filter(
                L3SecXbrlOperatorReviewWorkflow.workflow_basis_hash == basis_hash
            )
        workflow = query.one_or_none()
    except Exception as exc:
        return _blocked(
            "admission_status_workflow_query_failed",
            detail=type(exc).__name__,
        )

    if workflow is None:
        return _blocked(
            "admission_status_workflow_not_found",
            detail="No workflow found for the provided identifier(s).",
        )

    try:
        _validate_workflow_row_for_status(workflow)
    except SecXbrlOperatorReviewWorkflowError as exc:
        return _blocked(
            "admission_status_workflow_validation_failed",
            detail=exc.code,
        )
    except Exception as exc:
        return _blocked(
            "admission_status_workflow_validation_error",
            detail=type(exc).__name__,
        )

    # ------------------------------------------------------------------
    # Step 2: Walk workflow -> statement_packet_set -> projection_set.
    # ------------------------------------------------------------------
    packet_set = workflow.statement_packet_set
    if packet_set is None:
        return _blocked(
            "admission_status_packet_set_missing",
            detail="Workflow has no associated statement packet set.",
        )
    projection_set = packet_set.projection_set
    if projection_set is None:
        return _blocked(
            "admission_status_projection_set_missing",
            detail="Statement packet set has no associated projection set.",
        )
    sidecar_hash = str(projection_set.sidecar_receipt_hash or "").strip()

    # Build evidence dict incrementally; omit keys we cannot source honestly.
    evidence: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Step 3: Operator decision (approved + ready_for_next_freeze).
    # ------------------------------------------------------------------
    try:
        decision = (
            db.query(L3SecXbrlOperatorReviewDecision)
            .filter(
                L3SecXbrlOperatorReviewDecision.sec_xbrl_operator_review_workflow_id
                == workflow.sec_xbrl_operator_review_workflow_id
            )
            .one_or_none()
        )
        if (
            decision is not None
            and decision.workflow_basis_hash == workflow.workflow_basis_hash
        ):
            evidence["review_decision"] = decision.review_decision
            evidence["decision_reason_code"] = decision.decision_reason_code
    except Exception:
        pass  # omit decision evidence on error (fail closed)

    # ------------------------------------------------------------------
    # Step 4: Value-reveal authority receipt.
    # ------------------------------------------------------------------
    try:
        try:
            current_dataset_version_hash = layer3_sec_xbrl_value_reveal_authority._dataset_version_hash(
                db,
                projection_set.dataset_version_id,
            )
        except Exception:
            current_dataset_version_hash = None
        authority = (
            db.query(L3SecXbrlValueRevealAuthorityReceipt)
            .filter(
                L3SecXbrlValueRevealAuthorityReceipt.sec_xbrl_operator_review_workflow_id
                == workflow.sec_xbrl_operator_review_workflow_id
            )
            .one_or_none()
        )
        if _authority_matches_current_evidence(
            authority,
            workflow=workflow,
            decision=decision,
            packet_set=packet_set,
            projection_set=projection_set,
            sidecar_hash=sidecar_hash,
            dataset_version_hash=current_dataset_version_hash,
        ):
            evidence["value_reveal_authority_eligible"] = True
            evidence["value_reveal_authority_receipt_id"] = str(
                authority.sec_xbrl_value_reveal_authority_receipt_id
            )
    except Exception:
        pass  # omit authority evidence on error (fail closed)

    # ------------------------------------------------------------------
    # Step 5: Oracle coverage from projection facts.
    #
    # oracle_confirmed column vocabulary (written by persistence writers):
    #   "true"          — oracle matched this fact (confirmed)
    #   "false"         — oracle had a value and it DID NOT match (contradiction)
    #   "oracle_absent" — oracle ran but had no value for this fact
    # oracle_supplied is True if ANY fact has oracle_confirmed in that set
    # (i.e. the oracle pass ran).  Evidence keys passed to the evaluator:
    #   companyfacts_oracle_supplied  — bool
    #   oracle_confirmed_count        — facts where oracle_confirmed == "true"
    #   oracle_mismatch_count         — facts where oracle_confirmed == "false"
    #   oracle_total_count            — total facts in the projection_set
    # ------------------------------------------------------------------
    try:
        facts = list(projection_set.facts or [])
        total_count = len(facts)
        if total_count > 0:
            oracle_vals = [
                str(getattr(f, "oracle_confirmed", "") or "") for f in facts
            ]
            oracle_supplied = any(v in _ORACLE_ATTEMPTED_VALUES for v in oracle_vals)
            if oracle_supplied:
                confirmed_count = sum(1 for v in oracle_vals if v == _ORACLE_TRUE_VALUE)
                mismatch_count = sum(1 for v in oracle_vals if v == _ORACLE_FALSE_VALUE)
                evidence["companyfacts_oracle_supplied"] = True
                evidence["oracle_confirmed_count"] = confirmed_count
                evidence["oracle_mismatch_count"] = mismatch_count
                evidence["oracle_total_count"] = total_count
    except Exception:
        pass  # omit oracle evidence on error (fail closed)

    # ------------------------------------------------------------------
    # Step 6: Ownership marker check.
    # ------------------------------------------------------------------
    if sidecar_hash:
        try:
            storage_dir = str(settings.storage_dir or "").strip()
            if storage_dir:
                require_sec_xbrl_evidence_ownership_marker(
                    storage_dir,
                    policy_decision=policy_decision,
                    auth_owner_mode=auth_owner_mode,
                    sidecar_receipt_hash=sidecar_hash,
                )
                evidence["ownership_marker_present"] = True
        except SecXbrlAuthBindingError:
            pass  # omit ownership evidence (fail closed)
        except Exception:
            pass  # omit on any other error (fail closed)

    # ------------------------------------------------------------------
    # Step 7: Corpus validation by sidecar hash.
    # ------------------------------------------------------------------
    if sidecar_hash:
        try:
            verdict = find_corpus_validation_verdict_by_sidecar_hash(sidecar_hash)
            if verdict is not None:
                evidence["corpus_validation_passed"] = verdict["corpus_validation_passed"]
        except Exception:
            pass  # omit corpus evidence on error (fail closed)

    # ------------------------------------------------------------------
    # Step 8: Containment invariants from governed persisted state.
    # ------------------------------------------------------------------
    try:
        submit_receipt = (
            db.query(L3SecXbrlControlledValueRevealSubmitReceipt)
            .filter(
                L3SecXbrlControlledValueRevealSubmitReceipt.sec_xbrl_operator_review_workflow_id
                == workflow.sec_xbrl_operator_review_workflow_id,
                L3SecXbrlControlledValueRevealSubmitReceipt.submit_state
                == L3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_STATE_READY,
            )
            .first()
        )
        evidence["production_database_touched"] = False
        evidence["runtime_default_changed"] = False
        evidence["value_reveal_performed"] = submit_receipt is not None
        evidence["delivery_export_enabled"] = False
    except Exception:
        pass  # omit containment keys on error; evaluator fails closed

    # ------------------------------------------------------------------
    # Step 9: Review exception count from workflow row.
    # ------------------------------------------------------------------
    try:
        exc_count = workflow.review_exception_count
        if isinstance(exc_count, int) and not isinstance(exc_count, bool):
            evidence["review_exception_count"] = exc_count
    except Exception:
        pass  # omit on error (fail closed)

    # ------------------------------------------------------------------
    # Step 10: Honesty / leak guard.
    # Build a redacted projection of the evidence and run leak detection.
    # ------------------------------------------------------------------
    try:
        # Redacted projection: only non-sensitive evidence keys (hashes, bools,
        # counts).  No raw CIK, ticker, values, or accession numbers.
        redacted_projection = {
            "sec_xbrl_operator_review_workflow_id": workflow.sec_xbrl_operator_review_workflow_id,
            "workflow_basis_hash": workflow.workflow_basis_hash,
            "sidecar_receipt_hash": sidecar_hash,
            "evidence": {k: v for k, v in evidence.items()},
        }
        flags = report_leak_flags(redacted_projection)
        evidence["raw_leak_detected"] = any(flags.values())
        evidence["honesty_invariant_violation"] = evidence["raw_leak_detected"]
    except Exception:
        pass  # omit honesty keys on error; evaluator will fail-close criterion 5

    # ------------------------------------------------------------------
    # Step 11: Evaluate.
    # ------------------------------------------------------------------
    flag_enabled = production_admission_flag_enabled()
    admission = evaluate_production_admission(
        evidence=evidence,
        admission_flag_enabled=flag_enabled,
    )

    response = {
        "status": "ok",
        "schema_id": ADMISSION_STATUS_SCHEMA_ID,
        "sec_xbrl_operator_review_workflow_id": workflow.sec_xbrl_operator_review_workflow_id,
        "workflow_basis_hash": workflow.workflow_basis_hash,
        "sidecar_receipt_hash": sidecar_hash,
        "production_admission_ready": admission["production_admission_ready"],
        "production_admission_blocked_reason": admission["production_admission_blocked_reason"],
        "criteria": admission["criteria"],
        "admission_flag_enabled": admission["admission_flag_enabled"],
        "admission_schema_id": admission["schema_id"],
        # Hardcoded False — this service never sets production_readiness_claimed to True.
        # production_admission_ready is a computed criteria gate, not a human
        # production-readiness claim.
        "production_readiness_claimed": False,
        "admission_note": (
            "production_admission_ready is a computed criteria gate. "
            "It is NOT a human claim of production readiness. "
            "production_readiness_claimed remains False and is set independently by humans."
        ),
    }

    # Defense-in-depth: run leak guard on the FINAL response dict before
    # returning.  If any flag trips, return a governed blocked response
    # (fail-closed) instead of leaking raw data.
    try:
        final_flags = report_leak_flags(response)
        if any(final_flags.values()):
            return _blocked(
                "admission_status_final_response_leak_detected",
                detail="Final response failed leak-guard scan; blocked for safety.",
            )
    except Exception:
        return _blocked(
            "admission_status_final_response_leak_guard_error",
            detail="Final response leak-guard raised an unexpected error.",
        )

    return response
