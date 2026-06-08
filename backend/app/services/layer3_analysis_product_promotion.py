"""Layer 3 analysis product promotion service — lifecycle state machine.

This module is the sole write-path for L3AnalysisProductReviewDecision rows
and for advancing L3AnalysisProduct.lifecycle_status.  All validation is
fail-closed: every unknown/bad input raises Layer3AnalysisProductError with a
distinct error_code.  The service does NOT call db.commit(); the caller owns
the transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisProduct,
    L3AnalysisProductEvidenceLink,
    L3AnalysisProductReviewDecision,
    L3_ANALYSIS_PRODUCT_LIFECYCLE_VALUES,
    L3_ANALYSIS_PRODUCT_REVIEW_DECISION_VALUES,
    L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED,
    L3_ANALYSIS_PRODUCT_REVIEW_REASON_CODES,
    uuid_str,
)
from app.services.layer3_analysis_product_authoring import Layer3AnalysisProductError
from app.services.layer3_utils import stable_hash


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_PROMOTION_SCHEMA_ID = "layer3.analysis_product_promotion.v1"

ALLOWED_TRANSITIONS: dict[tuple[str, str], str] = {
    ("draft", "promote"): "proposed",
    ("proposed", "promote"): "validated",
    ("validated", "accept"): "accepted",
    ("accepted", "mark_package_eligible"): "package_eligible",
    ("proposed", "reject"): "rejected",
    ("validated", "reject"): "rejected",
    ("accepted", "reject"): "rejected",
    ("proposed", "revise"): "draft",
    ("validated", "revise"): "draft",
}

GROUNDING_REQUIRED_TARGETS: frozenset[str] = frozenset({"accepted", "package_eligible"})

TERMINAL_STATES: frozenset[str] = frozenset({"rejected", "package_eligible"})

REASON_CODES_BY_DECISION: dict[str, set[str]] = {
    "promote": {"proposed_ready", "validation_passed"},
    "accept": {"grounded_accept"},
    "mark_package_eligible": {"package_ready"},
    "reject": {"insufficient_grounding", "evidence_gap", "operator_rejected"},
    "revise": {"revision_requested"},
}

NOTES_REQUIRED_DECISIONS: frozenset[str] = frozenset({"reject", "revise"})


# ---------------------------------------------------------------------------
# Public data contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisProductTransitionRequest:
    decision_intent: str
    decision_reason_code: str
    operator_identity: str | None = None
    decision_notes: str | None = None
    decision_provenance: dict | None = None


@dataclass(frozen=True)
class Layer3AnalysisProductPromotionResult:
    product: L3AnalysisProduct
    decision: L3AnalysisProductReviewDecision
    replayed: bool = False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def transition_analysis_product(
    db: Session,
    *,
    session_id: str,
    analysis_product_id: str,
    client_request_id: str,
    request: AnalysisProductTransitionRequest,
) -> Layer3AnalysisProductPromotionResult:
    """Advance (or idempotently replay) a product lifecycle transition.

    Validation order matches the spec exactly.  On success, rows are
    flushed but NOT committed — the caller commits.
    """

    decision_intent = request.decision_intent
    decision_reason_code = request.decision_reason_code

    # --- Step 1: decision_intent valid ----------------------------------------
    if decision_intent not in L3_ANALYSIS_PRODUCT_REVIEW_DECISION_VALUES:
        raise Layer3AnalysisProductError(
            f"decision_intent '{decision_intent}' is not a valid review decision.",
            error_code="invalid_decision_intent",
        )

    # --- Step 2: reason code valid + matches intent ---------------------------
    if decision_reason_code not in L3_ANALYSIS_PRODUCT_REVIEW_REASON_CODES:
        raise Layer3AnalysisProductError(
            f"decision_reason_code '{decision_reason_code}' is not a valid reason code.",
            error_code="invalid_decision_reason_code",
        )
    allowed_reasons = REASON_CODES_BY_DECISION.get(decision_intent, set())
    if decision_reason_code not in allowed_reasons:
        raise Layer3AnalysisProductError(
            f"decision_reason_code '{decision_reason_code}' is not valid for "
            f"decision_intent '{decision_intent}'. "
            f"Allowed: {sorted(allowed_reasons)}.",
            error_code="decision_reason_mismatch",
        )

    # --- Step 3: notes required for certain decisions -------------------------
    decision_notes = request.decision_notes
    notes_stripped: str | None = decision_notes.strip() if decision_notes else None
    if decision_intent in NOTES_REQUIRED_DECISIONS:
        if not notes_stripped:
            raise Layer3AnalysisProductError(
                f"decision_notes is required (non-empty) for decision_intent '{decision_intent}'.",
                error_code="decision_notes_required",
            )

    # --- Step 4: load product -------------------------------------------------
    product = (
        db.query(L3AnalysisProduct)
        .filter(L3AnalysisProduct.analysis_product_id == analysis_product_id)
        .one_or_none()
    )
    if product is None:
        raise Layer3AnalysisProductError(
            f"Analysis product '{analysis_product_id}' not found.",
            error_code="product_not_found",
            http_status=404,
        )
    if product.session_id != session_id:
        raise Layer3AnalysisProductError(
            f"Analysis product '{analysis_product_id}' does not belong to session '{session_id}'.",
            error_code="product_not_in_session",
            http_status=409,
        )

    # --- Step 5: terminal state gate ------------------------------------------
    current = product.lifecycle_status
    if current in TERMINAL_STATES:
        raise Layer3AnalysisProductError(
            f"Analysis product '{analysis_product_id}' is in terminal state '{current}' "
            "and cannot be transitioned.",
            error_code="product_terminal",
            http_status=409,
        )

    # --- Step 6: allowed transition -------------------------------------------
    to_status = ALLOWED_TRANSITIONS.get((current, decision_intent))
    if to_status is None:
        raise Layer3AnalysisProductError(
            f"Transition not allowed: from_status='{current}', "
            f"decision_intent='{decision_intent}'.",
            error_code="transition_not_allowed",
            http_status=409,
        )

    # --- Step 7: grounding gate (live read) -----------------------------------
    grounding_asserted = to_status in GROUNDING_REQUIRED_TARGETS
    if grounding_asserted:
        if product.is_non_evidentiary is True:
            raise Layer3AnalysisProductError(
                f"Analysis product '{analysis_product_id}' is non-evidentiary and cannot "
                f"be transitioned to '{to_status}'.",
                error_code="non_evidentiary_not_acceptable",
                http_status=409,
            )
        live_evidence_count = (
            db.query(L3AnalysisProductEvidenceLink)
            .filter(
                L3AnalysisProductEvidenceLink.analysis_product_id == analysis_product_id
            )
            .count()
        )
        if live_evidence_count == 0:
            raise Layer3AnalysisProductError(
                f"Analysis product '{analysis_product_id}' has no evidence links and "
                f"cannot be transitioned to '{to_status}'.",
                error_code="ungrounded_not_acceptable",
                http_status=409,
            )

    # --- Step 8: notes hash ---------------------------------------------------
    notes_hash: str | None = (
        stable_hash({"notes": notes_stripped}) if notes_stripped else None
    )
    notes_present = bool(notes_stripped)

    # --- Step 9: decision basis hash ------------------------------------------
    decision_basis_hash = stable_hash(
        {
            "schema_id": ANALYSIS_PRODUCT_PROMOTION_SCHEMA_ID,
            "analysis_product_id": analysis_product_id,
            "from_status": current,
            "to_status": to_status,
            "review_decision": decision_intent,
            "decision_reason_code": decision_reason_code,
            "decision_status": L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED,
            "product_basis_hash": product.basis_hash,
            "grounding_asserted": grounding_asserted,
            "notes_hash": notes_hash,
        }
    )

    # --- Step 10: idempotency pre-check ---------------------------------------
    existing_decision = (
        db.query(L3AnalysisProductReviewDecision)
        .filter(
            L3AnalysisProductReviewDecision.client_request_id == client_request_id
        )
        .one_or_none()
    )
    if existing_decision is not None:
        # Reconstruct the basis hash from the stored decision's own fields so
        # comparison is stable regardless of what the current product status is.
        stored_basis_hash = stable_hash(
            {
                "schema_id": ANALYSIS_PRODUCT_PROMOTION_SCHEMA_ID,
                "analysis_product_id": existing_decision.analysis_product_id,
                "from_status": existing_decision.from_status,
                "to_status": existing_decision.to_status,
                "review_decision": existing_decision.review_decision,
                "decision_reason_code": existing_decision.decision_reason_code,
                "decision_status": L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED,
                "product_basis_hash": existing_decision.product_basis_hash,
                "grounding_asserted": existing_decision.grounding_asserted,
                "notes_hash": existing_decision.decision_notes_hash,
            }
        )
        # The incoming decision_basis_hash uses `current` (live product status).
        # For a true replay the intent/reason/notes must match the stored row AND
        # the stored row must pertain to the same product.  Compare field-by-field:
        incoming_matches = (
            existing_decision.analysis_product_id == analysis_product_id
            and existing_decision.review_decision == decision_intent
            and existing_decision.decision_reason_code == decision_reason_code
            and existing_decision.decision_notes_hash == notes_hash
        )
        if incoming_matches and existing_decision.decision_basis_hash == stored_basis_hash:
            return Layer3AnalysisProductPromotionResult(
                product=product,
                decision=existing_decision,
                replayed=True,
            )
        raise Layer3AnalysisProductError(
            f"client_request_id '{client_request_id}' already exists with a different "
            "decision_basis_hash.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    # --- Step 11: create decision row + mutate product ------------------------
    decision = L3AnalysisProductReviewDecision(
        analysis_product_review_decision_id=uuid_str(),
        analysis_product_id=analysis_product_id,
        session_id=session_id,
        from_status=current,
        to_status=to_status,
        review_decision=decision_intent,
        decision_reason_code=decision_reason_code,
        decision_status=L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED,
        decision_basis_hash=decision_basis_hash,
        decision_schema_id=ANALYSIS_PRODUCT_PROMOTION_SCHEMA_ID,
        product_basis_hash=product.basis_hash,
        grounding_asserted=grounding_asserted,
        operator_identity=request.operator_identity,
        decision_notes_present=notes_present,
        decision_notes_hash=notes_hash,
        client_request_id=client_request_id,
        decision_provenance_json=dict(request.decision_provenance) if request.decision_provenance else {},
        decision_summary_json={
            "from_status": current,
            "to_status": to_status,
            "decision_intent": decision_intent,
            "decision_reason_code": decision_reason_code,
            "grounding_asserted": grounding_asserted,
            "notes_present": notes_present,
        },
    )
    product.lifecycle_status = to_status
    db.add(decision)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Re-query for idempotency race on client_request_id constraint.
        recovered = (
            db.query(L3AnalysisProductReviewDecision)
            .filter(
                L3AnalysisProductReviewDecision.client_request_id == client_request_id
            )
            .one_or_none()
        )
        if recovered is None:
            raise
        if recovered.decision_basis_hash == decision_basis_hash:
            # Reload product to get current state from DB after rollback
            product = (
                db.query(L3AnalysisProduct)
                .filter(L3AnalysisProduct.analysis_product_id == analysis_product_id)
                .one()
            )
            return Layer3AnalysisProductPromotionResult(
                product=product,
                decision=recovered,
                replayed=True,
            )
        raise Layer3AnalysisProductError(
            f"client_request_id '{client_request_id}' conflicts with an existing record.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    return Layer3AnalysisProductPromotionResult(
        product=product,
        decision=decision,
        replayed=False,
    )
