"""Layer 3 deterministic analysis product generation service.

Server-internal service that runs a deterministic method over a working set's
MEMBER METADATA and emits an L3AnalysisProduct via the standard authoring
write-path with executor_type="deterministic".

No raw payload access.  No new table.  No migration.
Caller (route) owns the transaction: this service flushes but does NOT commit.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisProduct, L3AnalysisProductEvidenceLink, L3WorkingSet
from app.services.layer3_analysis_product_authoring import (
    AnalysisProductDraft,
    AnalysisProductEvidenceDraft,
    Layer3AnalysisProductError,
    create_analysis_product_draft,
)
from app.services.layer3_deterministic_methods import (
    DETERMINISTIC_METHODS,
    render_body,
    render_title,
    run_method,
)
from app.services.layer3_utils import stable_hash


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer3GenerationResult:
    product: L3AnalysisProduct
    evidence_links: tuple[L3AnalysisProductEvidenceLink, ...]
    method_id: str
    method_version: int
    replayed: bool


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_analysis_product(
    db: Session,
    *,
    session_id: str,
    client_request_id: str,
    working_set_id: str,
    method_id: str,
) -> Layer3GenerationResult:
    """Generate a deterministic analysis product over a working set.

    Validation is fail-closed.  The product row is flushed but NOT committed;
    the caller (route) commits.

    Steps:
    1. Validate method_id is known.
    2. Load working set, verify session ownership.
    3. Run the deterministic method.
    4. Build authoring provenance.
    5. Call create_analysis_product_draft with executor_type="deterministic".
    6. Set reserved columns (output_schema_validation_status, executor_identity).
    7. Return Layer3GenerationResult.
    """

    # --- Step 1: method existence -------------------------------------------
    if method_id not in DETERMINISTIC_METHODS:
        raise Layer3AnalysisProductError(
            f"method_id '{method_id}' is not a known deterministic method.",
            error_code="unknown_method",
            http_status=400,
        )
    spec = DETERMINISTIC_METHODS[method_id]

    # --- Step 2: load working set, verify session ownership -----------------
    working_set = (
        db.query(L3WorkingSet)
        .filter(
            L3WorkingSet.working_set_id == working_set_id,
            L3WorkingSet.session_id == session_id,
        )
        .one_or_none()
    )
    if working_set is None:
        # Distinguish: exists in another session vs. entirely absent.
        exists_elsewhere = (
            db.query(L3WorkingSet)
            .filter(L3WorkingSet.working_set_id == working_set_id)
            .first()
        )
        if exists_elsewhere is not None:
            raise Layer3AnalysisProductError(
                f"working_set_id '{working_set_id}' exists but does not belong to session '{session_id}'.",
                error_code="working_set_not_in_session",
                http_status=409,
            )
        raise Layer3AnalysisProductError(
            f"working_set_id '{working_set_id}' not found.",
            error_code="working_set_not_found",
            http_status=404,
        )

    # --- Step 3: run the deterministic method (twice) + verify determinism ---
    # Honesty: actually recompute and compare rather than asserting determinism.
    # A pure method must yield byte-identical output; a mismatch means the method
    # is not deterministic -> fail closed (a non-deterministic "deterministic"
    # product would be a dishonest provenance claim).
    result = run_method(method_id, working_set=working_set)
    recomputed = run_method(method_id, working_set=working_set)
    recomputed_match = stable_hash(result) == stable_hash(recomputed)
    if not recomputed_match:
        raise Layer3AnalysisProductError(
            f"deterministic method '{method_id}' produced non-identical output on recompute.",
            error_code="nondeterministic_method",
            http_status=500,
        )

    # --- Step 4: build provenance --------------------------------------------
    input_basis_hash = working_set.basis_hash
    param_hash = stable_hash({"method_id": method_id, "method_version": spec.version})
    result_summary_dict = {
        k: v for k, v in result.items() if k not in ("method_id", "method_version")
    }
    provenance = {
        "method_id": method_id,
        "method_version": spec.version,
        "input_basis_hash": input_basis_hash,
        "param_hash": param_hash,
        "result_summary": result_summary_dict,
        # Recorded only after an actual recompute-and-compare above.
        "validation": "deterministic_recomputed_match",
    }

    # --- Step 5: create the analysis product draft --------------------------
    title = render_title(method_id, working_set=working_set)
    body = render_body(method_id, result=result)

    draft = AnalysisProductDraft(
        product_kind="summary",
        title=title,
        body=body,
        evidence=(
            AnalysisProductEvidenceDraft(
                ref_kind="working_set",
                ref_id=working_set_id,
                evidence_role="context",
            ),
        ),
        is_non_evidentiary=False,
        authoring_provenance=provenance,
        executor_type="deterministic",
    )

    authoring_result = create_analysis_product_draft(
        db,
        session_id=session_id,
        client_request_id=client_request_id,
        draft=draft,
    )

    # --- Step 6: set reserved columns ---------------------------------------
    product = authoring_result.product
    product.output_schema_validation_status = "validated"
    product.executor_identity = method_id
    db.flush()

    # --- Step 7: return result -----------------------------------------------
    return Layer3GenerationResult(
        product=product,
        evidence_links=authoring_result.evidence_links,
        method_id=method_id,
        method_version=spec.version,
        replayed=authoring_result.replayed,
    )
