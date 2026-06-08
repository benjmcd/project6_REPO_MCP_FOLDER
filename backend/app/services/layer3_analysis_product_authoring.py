"""Layer 3 analysis product authoring service — draft write-path only.

This module is the sole write-path for L3AnalysisProduct rows.  All
validation is fail-closed: every unknown/bad input raises
Layer3AnalysisProductError with a distinct error_code.  The service
does NOT call db.commit(); the caller (route) owns the transaction.

Supported executor_type: "human" only (this version).  Future executor
types are structurally reserved in the model but blocked here.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisProduct,
    L3AnalysisProductEvidenceLink,
    L3AnalysisSet,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3Session,
    L3_ANALYSIS_PRODUCT_EVIDENCE_REF_KIND_VALUES,
    L3_ANALYSIS_PRODUCT_EVIDENCE_ROLE_VALUES,
    L3_ANALYSIS_PRODUCT_KIND_VALUES,
    uuid_str,
)
from app.services.layer3_utils import stable_hash, stable_json_text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANALYSIS_PRODUCT_SCHEMA_ID = "layer3.analysis_product.v1"

NON_EVIDENTIARY_ALLOWED_KINDS: frozenset[str] = frozenset({"analyst_note", "hypothesis"})

_SESSION_AUTHORING_ELIGIBLE_STATUSES: frozenset[str] = frozenset(
    {
        "active_planning",
        "active_execution",
        "completed",
        "completed_with_warnings",
    }
)

# Control characters forbidden in title/body (allow \t and \n; strip CR)
_FORBIDDEN_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Maps ref_kind -> (model_class, pk_attribute_name)
_EVIDENCE_REF_KIND_TABLE: dict[str, tuple[Any, str]] = {
    "material_snapshot": (L3MaterialSnapshot, "material_snapshot_id"),
    "pass_run": (L3PassRun, "pass_run_id"),
    "output_package": (L3OutputPackage, "output_package_id"),
    "analysis_set": (L3AnalysisSet, "analysis_set_id"),
    "prior_product": (L3AnalysisProduct, "analysis_product_id"),
}


# ---------------------------------------------------------------------------
# Public data contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisProductEvidenceDraft:
    ref_kind: str
    ref_id: str
    evidence_role: str
    locator: dict | None = None


@dataclass(frozen=True)
class AnalysisProductDraft:
    product_kind: str
    title: str
    body: str
    evidence: tuple[AnalysisProductEvidenceDraft, ...]
    is_non_evidentiary: bool = False
    authoring_provenance: dict | None = None
    executor_type: str = "human"


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class Layer3AnalysisProductError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": ANALYSIS_PRODUCT_SCHEMA_ID,
            "error_code": self.error_code,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer3AnalysisProductResult:
    product: L3AnalysisProduct
    evidence_links: tuple[L3AnalysisProductEvidenceLink, ...]
    replayed: bool = False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def create_analysis_product_draft(
    db: Session,
    *,
    session_id: str,
    client_request_id: str,
    draft: AnalysisProductDraft,
) -> Layer3AnalysisProductResult:
    """Create (or idempotently replay) a draft analysis product.

    Validation order matches the spec exactly.  On success, rows are
    flushed but NOT committed — the caller commits.
    """

    # --- Step 1: executor_type gate ----------------------------------------
    if draft.executor_type != "human":
        raise Layer3AnalysisProductError(
            f"executor_type '{draft.executor_type}' is not supported; only 'human' is admitted.",
            error_code="unsupported_executor_type",
        )

    # --- Step 2: product_kind -----------------------------------------------
    if draft.product_kind not in L3_ANALYSIS_PRODUCT_KIND_VALUES:
        raise Layer3AnalysisProductError(
            f"product_kind '{draft.product_kind}' is not a valid analysis product kind.",
            error_code="invalid_product_kind",
        )

    # --- Step 3: title / body text validation -------------------------------
    title = draft.title.strip()
    if not title:
        raise Layer3AnalysisProductError(
            "title must not be empty.",
            error_code="invalid_title",
        )
    if len(title) > 256:
        raise Layer3AnalysisProductError(
            f"title must be 256 characters or fewer (got {len(title)}).",
            error_code="invalid_title",
        )
    if _FORBIDDEN_CTRL_RE.search(title):
        raise Layer3AnalysisProductError(
            "title contains forbidden control characters.",
            error_code="invalid_text",
        )

    body = draft.body.strip()
    if not body:
        raise Layer3AnalysisProductError(
            "body must not be empty.",
            error_code="invalid_body",
        )
    if len(body) > 16384:
        raise Layer3AnalysisProductError(
            f"body must be 16384 characters or fewer (got {len(body)}).",
            error_code="invalid_body",
        )
    if _FORBIDDEN_CTRL_RE.search(body):
        raise Layer3AnalysisProductError(
            "body contains forbidden control characters.",
            error_code="invalid_text",
        )

    # --- Step 4: grounding rules (CRITICAL honesty gate) -------------------
    if draft.is_non_evidentiary:
        if draft.product_kind not in NON_EVIDENTIARY_ALLOWED_KINDS:
            raise Layer3AnalysisProductError(
                f"is_non_evidentiary=True is not allowed for product_kind '{draft.product_kind}'. "
                f"Only {sorted(NON_EVIDENTIARY_ALLOWED_KINDS)} may be non-evidentiary.",
                error_code="non_evidentiary_kind_not_allowed",
            )
        if draft.evidence:
            raise Layer3AnalysisProductError(
                "A non-evidentiary product must have no evidence links.",
                error_code="non_evidentiary_with_evidence",
            )
    else:
        if not draft.evidence:
            raise Layer3AnalysisProductError(
                "At least one evidence link is required for a grounded analysis product.",
                error_code="missing_evidence",
            )

    # --- Step 5: per-evidence-link validation -------------------------------
    for link in draft.evidence:
        if link.ref_kind not in L3_ANALYSIS_PRODUCT_EVIDENCE_REF_KIND_VALUES:
            raise Layer3AnalysisProductError(
                f"evidence ref_kind '{link.ref_kind}' is not valid.",
                error_code="invalid_evidence_ref_kind",
            )
        if link.evidence_role not in L3_ANALYSIS_PRODUCT_EVIDENCE_ROLE_VALUES:
            raise Layer3AnalysisProductError(
                f"evidence evidence_role '{link.evidence_role}' is not valid.",
                error_code="invalid_evidence_role",
            )
        if not isinstance(link.ref_id, str) or not link.ref_id.strip():
            raise Layer3AnalysisProductError(
                "evidence ref_id must be a non-empty string.",
                error_code="invalid_evidence_ref_id",
            )
        if link.locator is not None and not isinstance(link.locator, dict):
            raise Layer3AnalysisProductError(
                "evidence locator must be a dict when provided.",
                error_code="invalid_evidence_locator",
            )

    # --- Step 6: session existence + eligible status ------------------------
    session_row = db.get(L3Session, session_id)
    if session_row is None:
        raise Layer3AnalysisProductError(
            f"Session '{session_id}' not found.",
            error_code="session_not_found",
            http_status=404,
        )
    if session_row.status not in _SESSION_AUTHORING_ELIGIBLE_STATUSES:
        raise Layer3AnalysisProductError(
            f"Session status '{session_row.status}' is not eligible for analysis product authoring. "
            f"Eligible statuses: {sorted(_SESSION_AUTHORING_ELIGIBLE_STATUSES)}.",
            error_code="session_state_not_authoring_eligible",
            http_status=409,
        )

    # --- Step 7: evidence existence + in-session verification ---------------
    for link in draft.evidence:
        model_cls, pk_attr = _EVIDENCE_REF_KIND_TABLE[link.ref_kind]
        pk_col = getattr(model_cls, pk_attr)
        session_col = getattr(model_cls, "session_id")
        found = (
            db.query(model_cls)
            .filter(pk_col == link.ref_id.strip(), session_col == session_id)
            .first()
        )
        if found is None:
            raise Layer3AnalysisProductError(
                f"Evidence ref_id '{link.ref_id}' (ref_kind='{link.ref_kind}') not found in session '{session_id}'.",
                error_code="evidence_ref_not_found_in_session",
                http_status=409,
            )

    # --- Step 8: compute server-owned hashes --------------------------------
    evidence_for_hash = sorted(
        [
            [
                link.ref_kind,
                link.ref_id.strip(),
                link.evidence_role,
                # stable repr of locator: sort keys
                link.locator if link.locator is not None else {},
            ]
            for link in draft.evidence
        ],
        key=lambda x: (x[0], x[1], x[2], stable_json_text(x[3])),
    )
    basis_hash = stable_hash(
        {
            "product_kind": draft.product_kind,
            "title": title,
            "body": body,
            "is_non_evidentiary": bool(draft.is_non_evidentiary),
            "evidence": evidence_for_hash,
        }
    )
    spec_hash = stable_hash({"schema_id": ANALYSIS_PRODUCT_SCHEMA_ID})

    # --- Step 9: idempotency ------------------------------------------------
    existing = (
        db.query(L3AnalysisProduct)
        .filter(
            L3AnalysisProduct.session_id == session_id,
            L3AnalysisProduct.client_request_id == client_request_id,
        )
        .one_or_none()
    )
    if existing is not None:
        if existing.basis_hash == basis_hash:
            existing_links = (
                db.query(L3AnalysisProductEvidenceLink)
                .filter(
                    L3AnalysisProductEvidenceLink.analysis_product_id
                    == existing.analysis_product_id
                )
                .order_by(L3AnalysisProductEvidenceLink.evidence_link_id.asc())
                .all()
            )
            return Layer3AnalysisProductResult(
                product=existing,
                evidence_links=tuple(existing_links),
                replayed=True,
            )
        raise Layer3AnalysisProductError(
            f"client_request_id '{client_request_id}' already exists with a different basis_hash.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    # --- Build and flush rows -----------------------------------------------
    by_role: Counter[str] = Counter(link.evidence_role for link in draft.evidence)
    summary_json = {
        "evidence_count": len(draft.evidence),
        "by_evidence_role": dict(by_role),
        "grounded": not draft.is_non_evidentiary,
        "is_non_evidentiary": bool(draft.is_non_evidentiary),
    }

    product = L3AnalysisProduct(
        analysis_product_id=uuid_str(),
        session_id=session_id,
        product_kind=draft.product_kind,
        executor_type=draft.executor_type,
        lifecycle_status="draft",
        title=title,
        body=body,
        is_non_evidentiary=bool(draft.is_non_evidentiary),
        basis_hash=basis_hash,
        spec_hash=spec_hash,
        client_request_id=client_request_id,
        authoring_provenance_json=dict(draft.authoring_provenance) if draft.authoring_provenance else {},
        summary_json=summary_json,
    )
    db.add(product)

    link_rows: list[L3AnalysisProductEvidenceLink] = []
    for link in draft.evidence:
        link_row = L3AnalysisProductEvidenceLink(
            analysis_product_id=product.analysis_product_id,
            session_id=session_id,
            ref_kind=link.ref_kind,
            ref_id=link.ref_id.strip(),
            evidence_role=link.evidence_role,
            locator_json=dict(link.locator) if link.locator else {},
        )
        db.add(link_row)
        link_rows.append(link_row)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Only the (session_id, client_request_id) unique constraint represents an
        # idempotency race. Re-query for that row: if it now exists, this was a
        # concurrent duplicate (replay on identical basis, 409 on divergent basis).
        # If it does NOT exist, the IntegrityError came from a DIFFERENT constraint
        # (FK/CHECK) — do not mask it as an idempotency_conflict; re-raise the
        # original so the caller surfaces a true server error.
        recovered = (
            db.query(L3AnalysisProduct)
            .filter(
                L3AnalysisProduct.session_id == session_id,
                L3AnalysisProduct.client_request_id == client_request_id,
            )
            .one_or_none()
        )
        if recovered is None:
            raise
        if recovered.basis_hash == basis_hash:
            recovered_links = (
                db.query(L3AnalysisProductEvidenceLink)
                .filter(
                    L3AnalysisProductEvidenceLink.analysis_product_id
                    == recovered.analysis_product_id
                )
                .order_by(L3AnalysisProductEvidenceLink.evidence_link_id.asc())
                .all()
            )
            return Layer3AnalysisProductResult(
                product=recovered,
                evidence_links=tuple(recovered_links),
                replayed=True,
            )
        raise Layer3AnalysisProductError(
            f"client_request_id '{client_request_id}' conflicts with an existing record.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    return Layer3AnalysisProductResult(
        product=product,
        evidence_links=tuple(link_rows),
        replayed=False,
    )
