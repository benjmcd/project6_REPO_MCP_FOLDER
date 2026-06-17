"""Layer 3 analysis product lineage inspection service.

READ-ONLY.  This module performs no writes: it does not call db.add, db.flush,
db.commit, or db.delete, and does not mutate any row.  It is safe to call from
any context where a read-only DB session is acceptable.

Given an analysis_product_id, assembles a bounded lineage view from
already-stored rows: product -> working_set -> method_provenance ->
full review-decision trail -> package eligibility/refs.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisProduct,
    L3AnalysisProductEvidenceLink,
    L3AnalysisProductReviewDecision,
    L3WorkingSet,
)
from app.services.layer3_analysis_product_authoring import Layer3AnalysisProductError
from app.services.layer3_sublayer_state import serialize_working_set


def _order_review_decisions(
    decisions: list[L3AnalysisProductReviewDecision],
) -> list[L3AnalysisProductReviewDecision]:
    """Order an append-only review trail chronologically.

    created_at alone is not a reliable order key: several decisions recorded in
    rapid succession can share a coarse timestamp, and the UUID primary key is
    not monotonic, so (created_at, pk) ties resolve to an arbitrary order.  The
    trail is a walk over the lifecycle DAG where each decision's from_status is
    the previous decision's to_status, so we linearize by following that chain
    from its head (a from_status never produced as any to_status).  For a plain
    promotion path this is exact and clock-independent; for revise loops or a
    disconnected set the chain head is ambiguous, so we fall back to the stable
    (created_at, decision_id) hint order.
    """
    hint = sorted(
        decisions,
        key=lambda d: (
            d.created_at is None,
            d.created_at,
            d.analysis_product_review_decision_id,
        ),
    )

    ordered: list[L3AnalysisProductReviewDecision] = []
    used: set[str] = set()
    # Linearize each connected sub-chain in turn: pick the head of the remaining
    # decisions (a from_status not produced as any remaining to_status), walk it
    # via from_status->to_status, then repeat for the next sub-chain.  If the
    # remaining set has no head (a cycle, e.g. a revise loop), flush it in hint
    # order.  used grows every iteration, so this always terminates and every
    # decision appears exactly once.
    while len(used) < len(hint):
        unused = [
            d for d in hint if d.analysis_product_review_decision_id not in used
        ]
        unused_to = {d.to_status for d in unused}
        start = next((d for d in unused if d.from_status not in unused_to), None)
        if start is None:
            for d in unused:
                ordered.append(d)
                used.add(d.analysis_product_review_decision_id)
            break
        cur: L3AnalysisProductReviewDecision | None = start
        while cur is not None and cur.analysis_product_review_decision_id not in used:
            ordered.append(cur)
            used.add(cur.analysis_product_review_decision_id)
            cur = next(
                (
                    d
                    for d in hint
                    if d.analysis_product_review_decision_id not in used
                    and d.from_status == cur.to_status
                ),
                None,
            )
    return ordered

# ---------------------------------------------------------------------------
# Schema ID
# ---------------------------------------------------------------------------

LINEAGE_SCHEMA_ID = "layer3.analysis_product_lineage.v1"

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_LINEAGE_EVIDENCE_REFS_MAX = 200
_PACKAGE_ELIGIBLE_STATUSES = frozenset({"package_eligible", "packaged"})


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_analysis_product_lineage(
    db: Session,
    *,
    session_id: str,
    analysis_product_id: str,
) -> dict[str, Any]:
    """Return a bounded, read-only lineage dict for the given analysis product.

    Read-only: no rows are created, modified, or deleted.

    Raises Layer3AnalysisProductError (404) when the product does not exist,
    and (409) when it exists in a different session.
    """

    # --- Step 1: load product by (analysis_product_id, session_id) ----------
    product = (
        db.query(L3AnalysisProduct)
        .filter(
            L3AnalysisProduct.analysis_product_id == analysis_product_id,
            L3AnalysisProduct.session_id == session_id,
        )
        .one_or_none()
    )
    if product is None:
        exists_elsewhere = (
            db.query(L3AnalysisProduct)
            .filter(L3AnalysisProduct.analysis_product_id == analysis_product_id)
            .first()
        )
        if exists_elsewhere is not None:
            raise Layer3AnalysisProductError(
                f"analysis_product_id '{analysis_product_id}' exists but does not belong to session '{session_id}'.",
                error_code="analysis_product_not_in_session",
                http_status=409,
            )
        raise Layer3AnalysisProductError(
            f"analysis_product_id '{analysis_product_id}' not found.",
            error_code="analysis_product_not_found",
            http_status=404,
        )

    # --- Step 2: bounded product fields (no body, no title) -----------------
    product_fields: dict[str, Any] = {
        "analysis_product_id": product.analysis_product_id,
        "product_kind": product.product_kind,
        "executor_type": product.executor_type,
        "lifecycle_status": product.lifecycle_status,
        "is_non_evidentiary": bool(product.is_non_evidentiary),
        "basis_hash": product.basis_hash,
        "spec_hash": product.spec_hash,
        "created_at": (
            product.created_at.isoformat() if product.created_at is not None else None
        ),
    }

    # --- Step 3: evidence links (capped) ------------------------------------
    all_links = (
        db.query(L3AnalysisProductEvidenceLink)
        .filter(
            L3AnalysisProductEvidenceLink.analysis_product_id == analysis_product_id,
        )
        .order_by(L3AnalysisProductEvidenceLink.evidence_link_id.asc())
        .all()
    )
    evidence_refs_truncated = len(all_links) > _LINEAGE_EVIDENCE_REFS_MAX
    capped_links = all_links[:_LINEAGE_EVIDENCE_REFS_MAX]
    evidence_refs: list[dict[str, Any]] = [
        {
            "ref_kind": link.ref_kind,
            "ref_id": link.ref_id,
            "evidence_role": link.evidence_role,
        }
        for link in capped_links
    ]

    # --- Step 4: resolve working set ----------------------------------------
    ws_link: L3AnalysisProductEvidenceLink | None = next(
        (lnk for lnk in all_links if lnk.ref_kind == "working_set"),
        None,
    )
    working_set: dict[str, Any] | None = None
    working_set_linked = False
    if ws_link is not None:
        ws_row = (
            db.query(L3WorkingSet)
            .filter(
                L3WorkingSet.working_set_id == ws_link.ref_id,
                L3WorkingSet.session_id == session_id,
            )
            .one_or_none()
        )
        if ws_row is not None:
            working_set = serialize_working_set(ws_row)
            working_set_linked = True

    # --- Step 5: method provenance (deterministic only) ---------------------
    method_provenance: dict[str, Any] | None = None
    if product.executor_type == "deterministic" and isinstance(
        product.authoring_provenance_json, dict
    ):
        prov = product.authoring_provenance_json
        method_provenance = {
            "method_id": prov.get("method_id"),
            "method_version": prov.get("method_version"),
            "input_basis_hash": prov.get("input_basis_hash"),
            "param_hash": prov.get("param_hash"),
            "input_state_hash": prov.get("input_state_hash"),
            "validation": prov.get("validation"),
        }

    # --- Step 6: review trail (all decisions, chain-ordered) ----------------
    decision_rows = _order_review_decisions(
        db.query(L3AnalysisProductReviewDecision)
        .filter(
            L3AnalysisProductReviewDecision.analysis_product_id == analysis_product_id,
        )
        .all()
    )
    review_trail: list[dict[str, Any]] = []
    for decision in decision_rows:
        prov_json = (
            decision.decision_provenance_json
            if isinstance(decision.decision_provenance_json, dict)
            else {}
        )
        raw_successor = prov_json.get("successor_analysis_product_id")
        successor_id: str | None = None
        # Bounded: a successor id is a server-owned uuid (<=36 chars); ignore any
        # over-long value from the free-form provenance blob rather than echo it.
        if isinstance(raw_successor, str) and raw_successor.strip() and len(raw_successor.strip()) <= 36:
            successor_id = raw_successor.strip()
        review_trail.append(
            {
                "review_decision": decision.review_decision,
                "decision_reason_code": decision.decision_reason_code,
                "from_status": decision.from_status,
                "to_status": decision.to_status,
                "created_at": (
                    decision.created_at.isoformat()
                    if decision.created_at is not None
                    else None
                ),
                "operator_identity": decision.operator_identity,
                "successor_analysis_product_id": successor_id,
            }
        )

    # --- Step 7: package eligibility / refs ---------------------------------
    output_package_refs: list[str] = [
        lnk.ref_id for lnk in all_links if lnk.ref_kind == "output_package"
    ]
    package: dict[str, Any] = {
        "package_eligible_or_packaged": product.lifecycle_status in _PACKAGE_ELIGIBLE_STATUSES,
        "lifecycle_status": product.lifecycle_status,
        "output_package_refs": output_package_refs,
    }

    # --- Assemble -----------------------------------------------------------
    return {
        "schema_id": LINEAGE_SCHEMA_ID,
        "analysis_product_id": analysis_product_id,
        "product": product_fields,
        "working_set": working_set,
        "working_set_linked": working_set_linked,
        "method_provenance": method_provenance,
        "evidence_refs": evidence_refs,
        "evidence_refs_truncated": evidence_refs_truncated,
        "review_trail": review_trail,
        "package": package,
    }
