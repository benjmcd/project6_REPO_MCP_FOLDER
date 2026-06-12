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
    ("accepted", "supersede"): "superseded",
    ("package_eligible", "supersede"): "superseded",
    ("packaged", "supersede"): "superseded",
}

GROUNDING_REQUIRED_TARGETS: frozenset[str] = frozenset({"accepted", "package_eligible"})

TERMINAL_STATES: frozenset[str] = frozenset({"rejected", "superseded"})

REASON_CODES_BY_DECISION: dict[str, set[str]] = {
    "promote": {"proposed_ready", "validation_passed"},
    "accept": {"grounded_accept"},
    "mark_package_eligible": {"package_ready"},
    "reject": {"insufficient_grounding", "evidence_gap", "operator_rejected"},
    "revise": {"revision_requested"},
    "supersede": {"superseded_by_successor", "stale_basis"},
}

NOTES_REQUIRED_DECISIONS: frozenset[str] = frozenset({"reject", "revise", "supersede"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_successor_id(raw: object) -> str | None:
    """Normalize a raw successor_analysis_product_id value to str-or-None.

    Treats missing, None, or empty/whitespace-only strings as None.
    Raises Layer3AnalysisProductError with error_code
    "supersede_successor_invalid_type" (http 409) if the value is neither
    None nor str — coercing int/list garbage would produce strings that 404
    on the write path.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise Layer3AnalysisProductError(
            "decision_provenance.successor_analysis_product_id must be a string or null; "
            f"got {type(raw).__name__}.",
            error_code="supersede_successor_invalid_type",
            http_status=409,
        )
    stripped = raw.strip()
    return stripped if stripped else None


def _stored_decision_basis_hash(existing: L3AnalysisProductReviewDecision) -> str:
    """Reconstruct the decision_basis_hash from a persisted decision row.

    Used by both the early idempotency pre-check and the late IntegrityError
    catch so the hash-equality comparison is computed once, consistently.

    For rows with review_decision == "supersede" the successor id is folded in
    (read from decision_provenance_json).  Non-str stored values are treated as
    None (replay must not crash on legacy/garbage rows).
    """
    stored_dict: dict = {
        "schema_id": ANALYSIS_PRODUCT_PROMOTION_SCHEMA_ID,
        "analysis_product_id": existing.analysis_product_id,
        "from_status": existing.from_status,
        "to_status": existing.to_status,
        "review_decision": existing.review_decision,
        "decision_reason_code": existing.decision_reason_code,
        "decision_status": L3_ANALYSIS_PRODUCT_REVIEW_DECISION_STATUS_RECORDED,
        "product_basis_hash": existing.product_basis_hash,
        "grounding_asserted": existing.grounding_asserted,
        "notes_hash": existing.decision_notes_hash,
    }
    if existing.review_decision == "supersede":
        raw_stored = (
            existing.decision_provenance_json.get("successor_analysis_product_id")
            if isinstance(existing.decision_provenance_json, dict)
            else None
        )
        # Stored rows: treat non-str as None (no raise — replay must not crash).
        stored_successor = raw_stored.strip() if isinstance(raw_stored, str) else None
        stored_dict["successor_analysis_product_id"] = stored_successor if stored_successor else None
    return stable_hash(stored_dict)


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

    Fail-closed validation ordered: intent → reason → notes → load →
    idempotent replay → terminal gate → transition → supersede
    provenance/grounding → hashes → write.  Replays return the originally
    recorded result.  On success, rows are flushed but NOT committed — the
    caller commits.
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

    # --- Step 5: idempotency pre-check (before terminal gate) -----------------
    # Must run before Step 6 so a supersede replay returns replayed=True rather
    # than hitting "product_terminal".
    _early_existing = (
        db.query(L3AnalysisProductReviewDecision)
        .filter(L3AnalysisProductReviewDecision.client_request_id == client_request_id)
        .one_or_none()
    )
    if _early_existing is not None:
        _early_stored_hash = _stored_decision_basis_hash(_early_existing)

        _early_notes_stripped: str | None = request.decision_notes.strip() if request.decision_notes else None
        _early_notes_hash: str | None = stable_hash({"notes": _early_notes_stripped}) if _early_notes_stripped else None

        _early_incoming_matches = (
            _early_existing.analysis_product_id == analysis_product_id
            and _early_existing.review_decision == decision_intent
            and _early_existing.decision_reason_code == decision_reason_code
            and _early_existing.decision_notes_hash == _early_notes_hash
        )
        if decision_intent == "supersede":
            _early_incoming_successor = _normalize_successor_id(
                request.decision_provenance.get("successor_analysis_product_id")
                if isinstance(request.decision_provenance, dict)
                else None
            )
            _early_stored_successor = (
                _early_existing.decision_provenance_json.get("successor_analysis_product_id")
                if isinstance(_early_existing.decision_provenance_json, dict)
                else None
            )
            _early_stored_successor = _early_stored_successor.strip() if isinstance(_early_stored_successor, str) else None
            _early_incoming_matches = _early_incoming_matches and (
                _early_incoming_successor == (_early_stored_successor if _early_stored_successor else None)
            )

        if _early_incoming_matches and _early_existing.decision_basis_hash == _early_stored_hash:
            return Layer3AnalysisProductPromotionResult(
                product=product,
                decision=_early_existing,
                replayed=True,
            )
        raise Layer3AnalysisProductError(
            f"client_request_id '{client_request_id}' already exists with a different "
            "decision_basis_hash.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    # --- Step 6: terminal state gate ------------------------------------------
    current = product.lifecycle_status
    if current in TERMINAL_STATES:
        raise Layer3AnalysisProductError(
            f"Analysis product '{analysis_product_id}' is in terminal state '{current}' "
            "and cannot be transitioned.",
            error_code="product_terminal",
            http_status=409,
        )

    # --- Step 7: allowed transition -------------------------------------------
    to_status = ALLOWED_TRANSITIONS.get((current, decision_intent))
    if to_status is None:
        raise Layer3AnalysisProductError(
            f"Transition not allowed: from_status='{current}', "
            f"decision_intent='{decision_intent}'.",
            error_code="transition_not_allowed",
            http_status=409,
        )

    # --- Step 8: supersede provenance/grounding validation --------------------
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

    successor_id: str | None = None
    if decision_intent == "supersede":
        successor_id = _normalize_successor_id(
            request.decision_provenance.get("successor_analysis_product_id")
            if isinstance(request.decision_provenance, dict)
            else None
        )
        if decision_reason_code == "superseded_by_successor" and successor_id is None:
            raise Layer3AnalysisProductError(
                "decision_provenance.successor_analysis_product_id is required when "
                "decision_reason_code is 'superseded_by_successor'.",
                error_code="supersede_successor_required",
                http_status=409,
            )
        if successor_id is not None:
            if successor_id == analysis_product_id:
                raise Layer3AnalysisProductError(
                    f"successor_analysis_product_id must not equal analysis_product_id "
                    f"('{analysis_product_id}').",
                    error_code="supersede_successor_self",
                    http_status=409,
                )
            successor_product = (
                db.query(L3AnalysisProduct)
                .filter(L3AnalysisProduct.analysis_product_id == successor_id)
                .one_or_none()
            )
            if successor_product is None:
                raise Layer3AnalysisProductError(
                    f"Successor analysis product '{successor_id}' not found.",
                    error_code="supersede_successor_not_found",
                    http_status=404,
                )
            if successor_product.session_id != session_id:
                raise Layer3AnalysisProductError(
                    f"Successor analysis product '{successor_id}' does not belong to "
                    f"session '{session_id}'.",
                    error_code="supersede_successor_not_in_session",
                    http_status=409,
                )

    # --- Step 9: notes hash ---------------------------------------------------
    notes_hash: str | None = (
        stable_hash({"notes": notes_stripped}) if notes_stripped else None
    )
    notes_present = bool(notes_stripped)

    # --- Step 10: decision basis hash -----------------------------------------
    basis_dict: dict = {
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
    if decision_intent == "supersede":
        basis_dict["successor_analysis_product_id"] = successor_id
    decision_basis_hash = stable_hash(basis_dict)

    # --- Step 11: write decision row + mutate product -------------------------
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
        recovered_stored_hash = _stored_decision_basis_hash(recovered)
        recovered_notes_hash: str | None = stable_hash({"notes": notes_stripped}) if notes_stripped else None
        recovered_field_match = (
            recovered.analysis_product_id == analysis_product_id
            and recovered.review_decision == decision_intent
            and recovered.decision_reason_code == decision_reason_code
            and recovered.decision_notes_hash == recovered_notes_hash
        )
        if decision_intent == "supersede":
            _rec_stored_raw = (
                recovered.decision_provenance_json.get("successor_analysis_product_id")
                if isinstance(recovered.decision_provenance_json, dict)
                else None
            )
            _rec_stored_succ = _rec_stored_raw.strip() if isinstance(_rec_stored_raw, str) else None
            recovered_field_match = recovered_field_match and (
                successor_id == (_rec_stored_succ if _rec_stored_succ else None)
            )
        if recovered_field_match and recovered.decision_basis_hash == recovered_stored_hash:
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
