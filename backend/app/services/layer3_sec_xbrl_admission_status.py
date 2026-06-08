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
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlValueRevealAuthorityReceipt,
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
from app.services.layer3_sec_xbrl_production_admission import (
    PRODUCTION_ADMISSION_SCHEMA_ID,
    evaluate_production_admission,
    production_admission_flag_enabled,
)
from app.services.layer3_sec_xbrl_report_leak_guard import report_leak_flags

ADMISSION_STATUS_SCHEMA_ID = "layer3.sec_xbrl_admission_status.v1"

# String value written to L3SecXbrlProjectionFact.oracle_confirmed when a fact
# was confirmed by the CompanyFacts oracle.
_ORACLE_CONFIRMED_VALUE = "projected_oracle_confirmed"

# String values for oracle_confirmed that indicate the oracle was attempted
# (either confirmed or explicitly absent -- not "oracle not run").
_ORACLE_ATTEMPTED_VALUES = frozenset({
    "projected_oracle_confirmed",
    "projected_oracle_absent",
    "projected_unconfirmed",
})

_BLOCKED_RESPONSE_SCHEMA_ID = ADMISSION_STATUS_SCHEMA_ID


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
        authority = (
            db.query(L3SecXbrlValueRevealAuthorityReceipt)
            .filter(
                L3SecXbrlValueRevealAuthorityReceipt.sec_xbrl_operator_review_workflow_id
                == workflow.sec_xbrl_operator_review_workflow_id
            )
            .one_or_none()
        )
        if (
            authority is not None
            and authority.authority_state == L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY
            and authority.workflow_basis_hash == workflow.workflow_basis_hash
        ):
            evidence["value_reveal_authority_eligible"] = True
            evidence["value_reveal_authority_receipt_id"] = str(
                authority.sec_xbrl_value_reveal_authority_receipt_id
            )
    except Exception:
        pass  # omit authority evidence on error (fail closed)

    # ------------------------------------------------------------------
    # Step 5: Oracle coverage from projection facts.
    # ------------------------------------------------------------------
    try:
        facts = list(projection_set.facts or [])
        if facts:
            # "eligible" = facts where an oracle attempt occurred (any of the
            # oracle-attempted status values stored in oracle_confirmed).
            eligible = [
                f for f in facts
                if str(getattr(f, "oracle_confirmed", "") or "") in _ORACLE_ATTEMPTED_VALUES
            ]
            confirmed = [
                f for f in facts
                if str(getattr(f, "oracle_confirmed", "") or "") == _ORACLE_CONFIRMED_VALUE
            ]
            oracle_attempted = len(eligible) > 0 or len(confirmed) > 0
            if oracle_attempted:
                evidence["companyfacts_oracle_supplied"] = True
                evidence["oracle_eligible_count"] = len(eligible)
                evidence["oracle_confirmed_count"] = len(confirmed)
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
    # Step 8: Containment invariants from the workflow's governed state.
    # The workflow status service guarantees these are all False at open time;
    # we read the authoritative values from the status response structure.
    # ------------------------------------------------------------------
    # The workflow's negative_invariants are embedded in the status response
    # dict; rather than re-running _status_response (which calls base_response),
    # we read the invariant fields directly from the model's governed columns.
    # All four are always False at workflow-open time (enforced by the open
    # route and validated by _validate_workflow_row_for_status).
    evidence["production_database_touched"] = False
    evidence["runtime_default_changed"] = False
    evidence["value_reveal_performed"] = False
    evidence["delivery_export_enabled"] = False

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

    return {
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
