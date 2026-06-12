"""Layer 3 working set service — immutable-basis multi-object analysis scope.

A working set is an explicit, immutable-basis reference to a set of in-session
objects that products can attach to.  All validation is fail-closed: every
unknown/bad input raises Layer3WorkingSetError with a distinct error_code.
The service does NOT call db.commit(); the caller (route) owns the transaction.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisProduct,
    L3AnalysisSet,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3Session,
    L3WorkingSet,
    L3_WORKING_SET_MEMBER_REF_KIND_VALUES,
    uuid_str,
)
from app.services.layer3_utils import stable_hash


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKING_SET_SCHEMA_ID = "layer3.working_set.v1"

_SESSION_ELIGIBLE_STATUSES: frozenset[str] = frozenset(
    {
        "active_planning",
        "active_execution",
        "completed",
        "completed_with_warnings",
    }
)

# Control characters forbidden in name (allow \t and \n)
_FORBIDDEN_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Maps member ref_kind -> (model_class, pk_attribute_name)
_MEMBER_REF_KIND_TABLE: dict[str, tuple[Any, str]] = {
    "material_snapshot": (L3MaterialSnapshot, "material_snapshot_id"),
    "pass_run": (L3PassRun, "pass_run_id"),
    "output_package": (L3OutputPackage, "output_package_id"),
    "analysis_set": (L3AnalysisSet, "analysis_set_id"),
    "prior_product": (L3AnalysisProduct, "analysis_product_id"),
}

# Public alias — used by layer3_analysis_product_generation.py for frame resolution.
MEMBER_REF_KIND_TABLE = _MEMBER_REF_KIND_TABLE


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class Layer3WorkingSetError(ValueError):
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
            "schema_id": WORKING_SET_SCHEMA_ID,
            "error_code": self.error_code,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Public data contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkingSetMemberDraft:
    ref_kind: str
    ref_id: str


@dataclass(frozen=True)
class WorkingSetDraft:
    name: str
    members: tuple[WorkingSetMemberDraft, ...]
    provenance: dict | None = None


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer3WorkingSetResult:
    working_set: L3WorkingSet
    replayed: bool = False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def create_working_set(
    db: Session,
    *,
    session_id: str,
    client_request_id: str,
    draft: WorkingSetDraft,
) -> Layer3WorkingSetResult:
    """Create (or idempotently replay) a working set.

    Validation order matches the spec exactly.  On success, rows are
    flushed but NOT committed — the caller commits.
    """

    # --- Step 1: name validation --------------------------------------------
    name = draft.name.strip()
    if not name:
        raise Layer3WorkingSetError(
            "name must not be empty.",
            error_code="invalid_name",
        )
    if len(name) > 256:
        raise Layer3WorkingSetError(
            f"name must be 256 characters or fewer (got {len(name)}).",
            error_code="invalid_name",
        )
    if _FORBIDDEN_CTRL_RE.search(name):
        raise Layer3WorkingSetError(
            "name contains forbidden control characters.",
            error_code="invalid_name",
        )

    # --- Step 2: members non-empty ------------------------------------------
    if len(draft.members) < 1:
        raise Layer3WorkingSetError(
            "At least one member is required.",
            error_code="missing_members",
        )

    # --- Step 3: per-member validation --------------------------------------
    for member in draft.members:
        if member.ref_kind not in L3_WORKING_SET_MEMBER_REF_KIND_VALUES:
            raise Layer3WorkingSetError(
                f"member ref_kind '{member.ref_kind}' is not valid.",
                error_code="invalid_member_ref_kind",
            )
        if not isinstance(member.ref_id, str) or not member.ref_id.strip():
            raise Layer3WorkingSetError(
                "member ref_id must be a non-empty string.",
                error_code="invalid_member_ref_id",
            )

    # --- Step 4: session existence + eligible status ------------------------
    session_row = db.get(L3Session, session_id)
    if session_row is None:
        raise Layer3WorkingSetError(
            f"Session '{session_id}' not found.",
            error_code="session_not_found",
            http_status=404,
        )
    if session_row.status not in _SESSION_ELIGIBLE_STATUSES:
        raise Layer3WorkingSetError(
            f"Session status '{session_row.status}' is not eligible for working set creation. "
            f"Eligible statuses: {sorted(_SESSION_ELIGIBLE_STATUSES)}.",
            error_code="session_state_not_eligible",
            http_status=409,
        )

    # --- Step 5: member existence + in-session verification -----------------
    for member in draft.members:
        model_cls, pk_attr = _MEMBER_REF_KIND_TABLE[member.ref_kind]
        pk_col = getattr(model_cls, pk_attr)
        session_col = getattr(model_cls, "session_id")
        found = (
            db.query(model_cls)
            .filter(pk_col == member.ref_id.strip(), session_col == session_id)
            .first()
        )
        if found is None:
            raise Layer3WorkingSetError(
                f"Member ref_id '{member.ref_id}' (ref_kind='{member.ref_kind}') not found in session '{session_id}'.",
                error_code="member_ref_not_found_in_session",
                http_status=409,
            )

    # --- Step 6: normalize members + compute basis_hash ---------------------
    seen: set[tuple[str, str]] = set()
    normalized_members: list[dict[str, str]] = []
    for member in sorted(draft.members, key=lambda m: (m.ref_kind, m.ref_id.strip())):
        key = (member.ref_kind, member.ref_id.strip())
        if key not in seen:
            seen.add(key)
            normalized_members.append({"ref_kind": member.ref_kind, "ref_id": member.ref_id.strip()})

    basis_hash = stable_hash(
        {
            "schema_id": WORKING_SET_SCHEMA_ID,
            "members": normalized_members,
        }
    )

    # --- Step 7: idempotency ------------------------------------------------
    existing = (
        db.query(L3WorkingSet)
        .filter(
            L3WorkingSet.session_id == session_id,
            L3WorkingSet.client_request_id == client_request_id,
        )
        .one_or_none()
    )
    if existing is not None:
        if existing.basis_hash == basis_hash:
            return Layer3WorkingSetResult(working_set=existing, replayed=True)
        raise Layer3WorkingSetError(
            f"client_request_id '{client_request_id}' already exists with a different basis_hash.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    # --- Step 8: build summary and flush ------------------------------------
    by_ref_kind: Counter[str] = Counter(m["ref_kind"] for m in normalized_members)
    summary_json = {
        "member_count": len(normalized_members),
        "by_ref_kind": dict(by_ref_kind),
    }

    working_set = L3WorkingSet(
        working_set_id=uuid_str(),
        session_id=session_id,
        name=name,
        member_refs_json=normalized_members,
        member_count=len(normalized_members),
        basis_hash=basis_hash,
        client_request_id=client_request_id,
        provenance_json=dict(draft.provenance) if draft.provenance else {},
        summary_json=summary_json,
    )
    db.add(working_set)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Re-query for the (session_id, client_request_id) row; if found, handle
        # as idempotency race; if not found, the error is from a different constraint
        # (FK/CHECK) — re-raise rather than masking.
        recovered = (
            db.query(L3WorkingSet)
            .filter(
                L3WorkingSet.session_id == session_id,
                L3WorkingSet.client_request_id == client_request_id,
            )
            .one_or_none()
        )
        if recovered is None:
            raise
        if recovered.basis_hash == basis_hash:
            return Layer3WorkingSetResult(working_set=recovered, replayed=True)
        raise Layer3WorkingSetError(
            f"client_request_id '{client_request_id}' conflicts with an existing record.",
            error_code="idempotency_conflict",
            http_status=409,
        )

    return Layer3WorkingSetResult(working_set=working_set, replayed=False)
