"""Layer 3 analysis product method replay / reproducibility verification service.

READ-ONLY.  This module performs no writes: it does not call db.add, db.flush,
db.commit, or db.delete, and does not mutate any row.  It is safe to call from
any context where a read-only DB session is acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisProduct, L3WorkingSet
from app.services.layer3_analysis_product_authoring import Layer3AnalysisProductError
from app.services.layer3_analysis_product_generation import _resolve_member_states
from app.services.layer3_deterministic_methods import DETERMINISTIC_METHODS, run_method
from app.services.layer3_utils import stable_hash

# ---------------------------------------------------------------------------
# Schema ID
# ---------------------------------------------------------------------------

REPLAY_VERIFY_SCHEMA_ID = "layer3.analysis_product_replay_verify.v1"

# ---------------------------------------------------------------------------
# Classification string constants
# ---------------------------------------------------------------------------

_CLS_REPRODUCED = "reproduced"
_CLS_METHOD_REMOVED = "method_removed"
_CLS_METHOD_VERSION_CHANGED = "method_version_changed"
_CLS_INPUT_BASIS_DRIFT = "input_basis_drift"
_CLS_INPUT_STATE_DRIFT = "input_state_drift"
_CLS_RESULT_MISMATCH = "result_mismatch"
_CLS_WORKING_SET_UNLINKED = "working_set_unlinked"
_CLS_WORKING_SET_MISSING = "working_set_missing"
_CLS_RECOMPUTE_ERROR = "recompute_error"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer3ReplayVerifyResult:
    analysis_product_id: str
    executor_type: str
    method_id: str
    reproduced: bool
    classification: str
    method_present: bool
    method_version_match: bool | None       # None if method removed
    input_basis_match: bool | None          # None if cannot recompute
    input_state_match: bool | None          # None for state-free OR cannot-recompute
    result_match: bool | None               # None if cannot recompute
    method_version_recorded: int | None
    method_version_current: int | None      # None if method removed
    input_basis_hash_recorded: str | None
    input_basis_hash_current: str | None    # None if ws missing/unlinked
    input_state_hash_recorded: str | None   # None for state-free or absent
    input_state_hash_current: str | None    # None for state-free or cannot-recompute
    param_hash_recorded: str | None
    validation_recorded: str | None
    result_summary_hash_recorded: str | None
    result_summary_hash_current: str | None  # None if cannot recompute


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def verify_analysis_product_replay(
    db: Session,
    *,
    session_id: str,
    analysis_product_id: str,
) -> Layer3ReplayVerifyResult:
    """Verify reproducibility of a deterministic analysis product.

    Read-only: no rows are created, modified, or deleted.

    Returns a fully-populated Layer3ReplayVerifyResult describing whether the
    product can be exactly reproduced from its recorded provenance.
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

    # --- Step 2: must be a deterministic product ----------------------------
    if product.executor_type != "deterministic":
        raise Layer3AnalysisProductError(
            f"analysis_product_id '{analysis_product_id}' has executor_type='{product.executor_type}'; "
            "only deterministic products are replayable.",
            error_code="not_deterministic_product",
            http_status=409,
        )

    # --- Step 3: extract provenance fields ----------------------------------
    prov: dict[str, Any] = product.authoring_provenance_json or {}
    recorded_method_id: str | None = prov.get("method_id")
    if not recorded_method_id:
        raise Layer3AnalysisProductError(
            f"analysis_product_id '{analysis_product_id}' has incomplete provenance (method_id missing).",
            error_code="provenance_incomplete",
            http_status=409,
        )

    method_version_recorded: int | None = prov.get("method_version")
    input_basis_hash_recorded: str | None = prov.get("input_basis_hash")
    # param_hash is a display/audit field only: it is derived purely from
    # (method_id, method_version), both of which are already verified by the
    # registry-presence and method_version_match checks below, so re-deriving it
    # would add no independent signal. Echoed for operator inspection, not gated.
    param_hash_recorded: str | None = prov.get("param_hash")
    input_state_hash_recorded: str | None = prov.get("input_state_hash")  # None for state-free
    validation_recorded: str | None = prov.get("validation")
    result_summary: Any = prov.get("result_summary")
    result_summary_hash_recorded: str | None = stable_hash(result_summary) if result_summary is not None else None

    # --- Step 4: find working_set evidence link ------------------------------
    working_set_link = None
    for link in product.evidence_links:
        if link.ref_kind == "working_set":
            working_set_link = link
            break

    if working_set_link is None:
        # Cannot recompute without working set link
        method_present = recorded_method_id in DETERMINISTIC_METHODS
        method_version_current: int | None = None
        method_version_match: bool | None = None
        if method_present:
            spec = DETERMINISTIC_METHODS[recorded_method_id]
            method_version_current = spec.version
            method_version_match = (method_version_recorded == method_version_current)
        return Layer3ReplayVerifyResult(
            analysis_product_id=analysis_product_id,
            executor_type=product.executor_type,
            method_id=recorded_method_id,
            reproduced=False,
            classification=_CLS_WORKING_SET_UNLINKED,
            method_present=method_present,
            method_version_match=method_version_match,
            input_basis_match=None,
            input_state_match=None,
            result_match=None,
            method_version_recorded=method_version_recorded,
            method_version_current=method_version_current,
            input_basis_hash_recorded=input_basis_hash_recorded,
            input_basis_hash_current=None,
            input_state_hash_recorded=input_state_hash_recorded,
            input_state_hash_current=None,
            param_hash_recorded=param_hash_recorded,
            validation_recorded=validation_recorded,
            result_summary_hash_recorded=result_summary_hash_recorded,
            result_summary_hash_current=None,
        )

    working_set_id = working_set_link.ref_id

    # --- Step 5: load working set by (working_set_id, session_id) -----------
    working_set = (
        db.query(L3WorkingSet)
        .filter(
            L3WorkingSet.working_set_id == working_set_id,
            L3WorkingSet.session_id == session_id,
        )
        .one_or_none()
    )
    if working_set is None:
        method_present = recorded_method_id in DETERMINISTIC_METHODS
        method_version_current = None
        method_version_match = None
        if method_present:
            spec = DETERMINISTIC_METHODS[recorded_method_id]
            method_version_current = spec.version
            method_version_match = (method_version_recorded == method_version_current)
        return Layer3ReplayVerifyResult(
            analysis_product_id=analysis_product_id,
            executor_type=product.executor_type,
            method_id=recorded_method_id,
            reproduced=False,
            classification=_CLS_WORKING_SET_MISSING,
            method_present=method_present,
            method_version_match=method_version_match,
            input_basis_match=None,
            input_state_match=None,
            result_match=None,
            method_version_recorded=method_version_recorded,
            method_version_current=method_version_current,
            input_basis_hash_recorded=input_basis_hash_recorded,
            input_basis_hash_current=None,
            input_state_hash_recorded=input_state_hash_recorded,
            input_state_hash_current=None,
            param_hash_recorded=param_hash_recorded,
            validation_recorded=validation_recorded,
            result_summary_hash_recorded=result_summary_hash_recorded,
            result_summary_hash_current=None,
        )

    # --- Step 6: check method registry --------------------------------------
    method_present = recorded_method_id in DETERMINISTIC_METHODS
    if not method_present:
        return Layer3ReplayVerifyResult(
            analysis_product_id=analysis_product_id,
            executor_type=product.executor_type,
            method_id=recorded_method_id,
            reproduced=False,
            classification=_CLS_METHOD_REMOVED,
            method_present=False,
            method_version_match=None,
            input_basis_match=None,
            input_state_match=None,
            result_match=None,
            method_version_recorded=method_version_recorded,
            method_version_current=None,
            input_basis_hash_recorded=input_basis_hash_recorded,
            # No basis comparison is performed when the method is gone, so the
            # "current" column stays None — consistent with input_basis_match=None.
            input_basis_hash_current=None,
            input_state_hash_recorded=input_state_hash_recorded,
            input_state_hash_current=None,
            param_hash_recorded=param_hash_recorded,
            validation_recorded=validation_recorded,
            result_summary_hash_recorded=result_summary_hash_recorded,
            result_summary_hash_current=None,
        )

    # --- Step 7: version match ----------------------------------------------
    spec = DETERMINISTIC_METHODS[recorded_method_id]
    method_version_current = spec.version
    method_version_match = (method_version_recorded == method_version_current)

    # --- Step 8: basis hash match -------------------------------------------
    input_basis_hash_current: str = working_set.basis_hash
    input_basis_match: bool = (input_basis_hash_recorded == input_basis_hash_current)

    # --- Step 9: recompute (wrapped for safety) -----------------------------
    input_state_hash_current: str | None = None
    input_state_match: bool | None = None
    result_summary_hash_current: str | None = None
    result_match: bool | None = None

    try:
        if spec.consumes_member_state:
            member_states = _resolve_member_states(db, working_set)
            input_state_hash_current = stable_hash(member_states)
            input_state_match = (input_state_hash_recorded == input_state_hash_current)
            fresh = run_method(recorded_method_id, working_set=working_set, member_states=member_states)
        else:
            # State-free: input_state_match stays None, input_state_hash_current stays None
            fresh = run_method(recorded_method_id, working_set=working_set)

        fresh_summary = {k: v for k, v in fresh.items() if k not in ("method_id", "method_version")}
        result_summary_hash_current = stable_hash(fresh_summary)
        result_match = (
            result_summary_hash_recorded is not None
            and result_summary_hash_recorded == result_summary_hash_current
        )
    except Exception:
        # Unexpected recompute failure — surface as recompute_error
        return Layer3ReplayVerifyResult(
            analysis_product_id=analysis_product_id,
            executor_type=product.executor_type,
            method_id=recorded_method_id,
            reproduced=False,
            classification=_CLS_RECOMPUTE_ERROR,
            method_present=method_present,
            method_version_match=method_version_match,
            input_basis_match=input_basis_match,
            input_state_match=input_state_match,
            result_match=None,
            method_version_recorded=method_version_recorded,
            method_version_current=method_version_current,
            input_basis_hash_recorded=input_basis_hash_recorded,
            input_basis_hash_current=input_basis_hash_current,
            input_state_hash_recorded=input_state_hash_recorded,
            input_state_hash_current=input_state_hash_current,
            param_hash_recorded=param_hash_recorded,
            validation_recorded=validation_recorded,
            result_summary_hash_recorded=result_summary_hash_recorded,
            result_summary_hash_current=None,
        )

    # --- Step 10: reproduced gate -------------------------------------------
    reproduced: bool = (
        method_present
        and bool(method_version_match)
        and bool(input_basis_match)
        and (input_state_match in (True, None))
        and bool(result_match)
    )

    # --- Step 11: classification precedence ---------------------------------
    if not method_version_match:
        classification = _CLS_METHOD_VERSION_CHANGED
    elif not input_basis_match:
        classification = _CLS_INPUT_BASIS_DRIFT
    elif input_state_match is False:
        classification = _CLS_INPUT_STATE_DRIFT
    elif not result_match:
        classification = _CLS_RESULT_MISMATCH
    else:
        classification = _CLS_REPRODUCED

    return Layer3ReplayVerifyResult(
        analysis_product_id=analysis_product_id,
        executor_type=product.executor_type,
        method_id=recorded_method_id,
        reproduced=reproduced,
        classification=classification,
        method_present=method_present,
        method_version_match=method_version_match,
        input_basis_match=input_basis_match,
        input_state_match=input_state_match,
        result_match=result_match,
        method_version_recorded=method_version_recorded,
        method_version_current=method_version_current,
        input_basis_hash_recorded=input_basis_hash_recorded,
        input_basis_hash_current=input_basis_hash_current,
        input_state_hash_recorded=input_state_hash_recorded,
        input_state_hash_current=input_state_hash_current,
        param_hash_recorded=param_hash_recorded,
        validation_recorded=validation_recorded,
        result_summary_hash_recorded=result_summary_hash_recorded,
        result_summary_hash_current=result_summary_hash_current,
    )
