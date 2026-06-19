"""Layer 3 deterministic analysis product generation service.

Server-internal service that runs a deterministic method over a working set's
MEMBER METADATA and emits an L3AnalysisProduct via the standard authoring
write-path with executor_type="deterministic".

No raw payload access.  No new table.  No migration.
Caller (route) owns the transaction: this service flushes but does NOT commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    method_quality_signals,
    render_body,
    render_title,
    run_method,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_working_set import MEMBER_REF_KIND_TABLE


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
# Frame resolver (R3)
# ---------------------------------------------------------------------------

# Bounded state fields to extract per ref_kind (NEVER payload_ref/URIs/paths/credentials).
_STATE_FIELDS_BY_KIND: dict[str, list[str]] = {
    "prior_product": ["lifecycle_status", "product_kind", "executor_type"],
    "pass_run": ["status", "pass_type", "engine_family"],
    "output_package": ["status", "package_kind"],
    "analysis_set": ["set_type", "group_count", "unit_count"],
    "material_snapshot": ["source_plane", "source_shape"],
}

# Derived lens fields for analysis_set (R4): derive counts from JSON list columns
_ANALYSIS_SET_DERIVED_FIELDS = {
    "group_count": "analysis_group_ids_json",
    "unit_count": "analysis_unit_ids_json",
}


def _resolve_member_states(
    db: Session,
    working_set: L3WorkingSet,
) -> list[dict[str, Any]]:
    """Resolve bounded per-member state dicts from the DB, session-scoped.

    Sorts members by (ref_kind, ref_id) before resolution (R3 determinism).
    A row absent or belonging to a different session => resolved: false.
    NEVER includes payload_ref, URIs, local paths, credentials, or body text.
    """
    # Sort for deterministic ordering (R3)
    sorted_members = sorted(
        working_set.member_refs_json,
        key=lambda m: (m["ref_kind"], m["ref_id"]),
    )

    result: list[dict[str, Any]] = []
    for member in sorted_members:
        ref_kind = member["ref_kind"]
        ref_id = member["ref_id"]
        session_id = working_set.session_id

        entry: dict[str, Any] = {
            "ref_kind": ref_kind,
            "ref_id": ref_id,
            "resolved": False,
        }

        if ref_kind not in MEMBER_REF_KIND_TABLE:
            result.append(entry)
            continue

        model_cls, pk_attr = MEMBER_REF_KIND_TABLE[ref_kind]
        pk_col = getattr(model_cls, pk_attr)
        session_col = getattr(model_cls, "session_id")

        row = (
            db.query(model_cls)
            .filter(pk_col == ref_id, session_col == session_id)
            .one_or_none()
        )

        if row is None:
            result.append(entry)
            continue

        # Row found and session-scoped: extract bounded state fields
        entry["resolved"] = True
        for field in _STATE_FIELDS_BY_KIND.get(ref_kind, []):
            if ref_kind == "analysis_set" and field in _ANALYSIS_SET_DERIVED_FIELDS:
                # Derive count from list-column length (R4)
                list_col = _ANALYSIS_SET_DERIVED_FIELDS[field]
                raw = getattr(row, list_col, None)
                entry[field] = len(raw) if isinstance(raw, list) else 0
            else:
                entry[field] = getattr(row, field, None)

        result.append(entry)

    return result


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
    3. Resolve member-state frame (when spec.consumes_member_state).
    4. Run the deterministic method (twice) + verify determinism.
    5. Build authoring provenance (R2 honesty split).
    6. Call create_analysis_product_draft with executor_type="deterministic".
    7. Set reserved columns (output_schema_validation_status, executor_identity).
    8. Return Layer3GenerationResult.
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

    # --- Step 2b: idempotent replay across a method-spec change --------------
    # A deterministic generation is fully determined by (method_id, working_set).
    # If a deterministic product already exists for this (session,
    # client_request_id) over the SAME method and working set, return it
    # unchanged — even if the method spec (product_kind / version) changed since
    # it was created (e.g. a taxonomy or version bump across a deploy).  Without
    # this, re-running would rebuild a draft whose basis_hash reflects the new
    # spec and trip create_analysis_product_draft's idempotency_conflict, breaking
    # a legitimate duplicate-request retry that spans the change.  This is safe: a
    # different method or working set does NOT match here and falls through to the
    # normal basis comparison, which still rejects true client_request_id reuse.
    existing = (
        db.query(L3AnalysisProduct)
        .filter(
            L3AnalysisProduct.session_id == session_id,
            L3AnalysisProduct.client_request_id == client_request_id,
        )
        .one_or_none()
    )
    if (
        existing is not None
        and existing.executor_type == "deterministic"
        and existing.executor_identity == method_id
    ):
        ws_link = (
            db.query(L3AnalysisProductEvidenceLink)
            .filter(
                L3AnalysisProductEvidenceLink.analysis_product_id
                == existing.analysis_product_id,
                L3AnalysisProductEvidenceLink.ref_kind == "working_set",
            )
            .one_or_none()
        )
        if ws_link is not None and ws_link.ref_id == working_set_id:
            existing_links = (
                db.query(L3AnalysisProductEvidenceLink)
                .filter(
                    L3AnalysisProductEvidenceLink.analysis_product_id
                    == existing.analysis_product_id
                )
                .order_by(L3AnalysisProductEvidenceLink.evidence_link_id.asc())
                .all()
            )
            prov = existing.authoring_provenance_json or {}
            return Layer3GenerationResult(
                product=existing,
                evidence_links=tuple(existing_links),
                method_id=method_id,
                # Report the version the product was stored with (it may predate a
                # version bump) — the replayed product is the original, unchanged.
                method_version=prov.get("method_version", spec.version),
                replayed=True,
            )

    # --- Step 3: resolve member-state frame (once, when needed) -------------
    member_states: list[dict[str, Any]] | None = None
    if spec.consumes_member_state:
        member_states = _resolve_member_states(db, working_set)

    # --- Step 4: run the deterministic method (twice) + verify determinism ---
    # Honesty: actually recompute and compare rather than asserting determinism.
    # A pure method must yield byte-identical output; a mismatch means the method
    # is not deterministic -> fail closed (a non-deterministic "deterministic"
    # product would be a dishonest provenance claim).
    # Both runs use the SAME already-resolved frame (cost negligible; R3 documented choice).
    #
    # Any ValueError raised here is the member-kind authority check (run_method validates
    # accepted_member_kinds before invoking spec.fn).  Generation always provides
    # member_states correctly for state-consuming methods, so the only remaining
    # ValueError source at this call site is the kind-validation failure.
    try:
        result = run_method(method_id, working_set=working_set, member_states=member_states)
        recomputed = run_method(method_id, working_set=working_set, member_states=member_states)
    except ValueError as exc:
        raise Layer3AnalysisProductError(
            str(exc),
            error_code="unsupported_member_kinds",
            http_status=400,
        ) from exc
    recomputed_match = stable_hash(result) == stable_hash(recomputed)
    if not recomputed_match:
        raise Layer3AnalysisProductError(
            f"deterministic method '{method_id}' produced non-identical output on recompute.",
            error_code="nondeterministic_method",
            http_status=500,
        )

    # --- Step 5: build provenance (R2 honesty split) -------------------------
    input_basis_hash = working_set.basis_hash
    param_hash = stable_hash({"method_id": method_id, "method_version": spec.version})
    result_summary_dict = {
        k: v for k, v in result.items() if k not in ("method_id", "method_version")
    }

    # Derive bounded quality signals (confidence_level + limitations).
    # Counts only — never ref_ids or raw bodies.
    quality = method_quality_signals(method_id, result=result)

    if spec.consumes_member_state:
        # State-consuming: validation sentinel is "function_purity_recomputed_match"
        # because the run-twice gate proves fn purity over a fixed frame, NOT full
        # reproducibility from the working set alone.  input_state_hash captures
        # the exact frame used so lineage is honest (R2).
        provenance: dict[str, Any] = {
            "method_id": method_id,
            "method_version": spec.version,
            "input_basis_hash": input_basis_hash,
            "param_hash": param_hash,
            "result_summary": result_summary_dict,
            "validation": "function_purity_recomputed_match",
            "input_state_hash": stable_hash(member_states),
            "confidence_level": quality["confidence_level"],
            "limitations": quality["limitations"],
        }
    else:
        # State-free: sentinel stays "deterministic_recomputed_match"; NO input_state_hash.
        provenance = {
            "method_id": method_id,
            "method_version": spec.version,
            "input_basis_hash": input_basis_hash,
            "param_hash": param_hash,
            "result_summary": result_summary_dict,
            # Recorded only after an actual recompute-and-compare above.
            "validation": "deterministic_recomputed_match",
            "confidence_level": quality["confidence_level"],
            "limitations": quality["limitations"],
        }

    # --- Step 6: create the analysis product draft --------------------------
    title = render_title(method_id, working_set=working_set)
    body = render_body(method_id, result=result)

    # product_kind comes from spec (R2 generalization — no more hardcoded "summary")
    draft = AnalysisProductDraft(
        product_kind=spec.product_kind,
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

    # On idempotent replay (duplicate client_request_id) create_analysis_product_draft
    # returns the EXISTING product unchanged; the freshly-computed frame above is
    # discarded.  The existing product retains its original input_state_hash and
    # provenance — intentional: a replayed client_request_id is the same logical request.
    authoring_result = create_analysis_product_draft(
        db,
        session_id=session_id,
        client_request_id=client_request_id,
        draft=draft,
    )

    # --- Step 7: set reserved columns ---------------------------------------
    product = authoring_result.product
    product.output_schema_validation_status = "validated"
    product.executor_identity = method_id
    db.flush()

    # --- Step 8: return result -----------------------------------------------
    return Layer3GenerationResult(
        product=product,
        evidence_links=authoring_result.evidence_links,
        method_id=method_id,
        method_version=spec.version,
        replayed=authoring_result.replayed,
    )
