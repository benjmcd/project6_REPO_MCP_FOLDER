from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services import aps_retrieval_plane
from app.services import aps_retrieval_plane_contract as contract


APS_RETRIEVAL_PARITY_SCHEMA_ID = "aps.retrieval_plane_parity.v1"
APS_RETRIEVAL_PARITY_SCHEMA_VERSION = 1

APS_RETRIEVAL_VALIDATION_EMPTY_CANONICAL_SCOPE = "empty_canonical_scope"
APS_RETRIEVAL_VALIDATION_EMPTY_RETRIEVAL_SCOPE = "empty_retrieval_scope"
APS_RETRIEVAL_VALIDATION_ROW_COUNT_MISMATCH = "row_count_mismatch"
APS_RETRIEVAL_VALIDATION_MISSING_ROW = "missing_retrieval_row"
APS_RETRIEVAL_VALIDATION_UNEXPECTED_ROW = "unexpected_retrieval_row"
APS_RETRIEVAL_VALIDATION_FIELD_MISMATCH = "field_mismatch"
APS_RETRIEVAL_VALIDATION_ORDERING_MISMATCH = "ordering_mismatch"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _identity_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in contract.APS_RETRIEVAL_IDENTITY_FIELDS}


def _serialize(value: Any) -> Any:
    return contract.serialize_value(value)


def validate_retrieval_plane_for_run(
    db: Session,
    *,
    run_id: str,
) -> dict[str, Any]:
    normalized_run_id = contract.normalize_optional_string(run_id)
    if not normalized_run_id:
        raise ValueError("run_id_required")

    canonical_rows = [
        aps_retrieval_plane.build_expected_retrieval_row(linkage=linkage, document=document, chunk=chunk)
        for linkage, document, chunk in aps_retrieval_plane.fetch_canonical_rows_for_run(db, run_id=normalized_run_id)
    ]
    retrieval_rows = aps_retrieval_plane.list_retrieval_rows_for_run(db, run_id=normalized_run_id)

    failure_codes: set[str] = set()
    missing_rows: list[dict[str, Any]] = []
    unexpected_rows: list[dict[str, Any]] = []
    field_mismatches: list[dict[str, Any]] = []

    if not canonical_rows:
        failure_codes.add(APS_RETRIEVAL_VALIDATION_EMPTY_CANONICAL_SCOPE)
    if canonical_rows and not retrieval_rows:
        failure_codes.add(APS_RETRIEVAL_VALIDATION_EMPTY_RETRIEVAL_SCOPE)

    expected_by_key = {contract.row_identity_tuple(row): row for row in canonical_rows}
    actual_by_key = {contract.row_identity_tuple(row): row for row in retrieval_rows}

    for key in sorted(expected_by_key.keys()):
        expected = expected_by_key[key]
        actual = actual_by_key.get(key)
        if actual is None:
            failure_codes.update(
                {
                    APS_RETRIEVAL_VALIDATION_ROW_COUNT_MISMATCH,
                    APS_RETRIEVAL_VALIDATION_MISSING_ROW,
                }
            )
            missing_rows.append(_identity_dict(expected))
            continue
        for field in contract.APS_RETRIEVAL_COMPARISON_FIELDS:
            expected_value = _serialize(expected.get(field))
            actual_value = _serialize(actual.get(field))
            if expected_value == actual_value:
                continue
            failure_codes.add(APS_RETRIEVAL_VALIDATION_FIELD_MISMATCH)
            field_mismatches.append(
                {
                    "row": _identity_dict(expected),
                    "field": field,
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )

    for key in sorted(actual_by_key.keys()):
        if key in expected_by_key:
            continue
        failure_codes.update(
            {
                APS_RETRIEVAL_VALIDATION_ROW_COUNT_MISMATCH,
                APS_RETRIEVAL_VALIDATION_UNEXPECTED_ROW,
            }
        )
        unexpected_rows.append(_identity_dict(actual_by_key[key]))

    expected_order = [contract.row_identity_tuple(row) for row in canonical_rows]
    actual_order = [contract.row_identity_tuple(row) for row in retrieval_rows]
    ordering_matches = expected_order == actual_order
    if canonical_rows and retrieval_rows and not ordering_matches:
        failure_codes.add(APS_RETRIEVAL_VALIDATION_ORDERING_MISMATCH)

    return {
        "schema_id": APS_RETRIEVAL_PARITY_SCHEMA_ID,
        "schema_version": APS_RETRIEVAL_PARITY_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "run_id": normalized_run_id,
        "passed": len(failure_codes) == 0,
        "canonical_row_count": len(canonical_rows),
        "retrieval_row_count": len(retrieval_rows),
        "failure_codes": sorted(failure_codes),
        "missing_rows": missing_rows,
        "unexpected_rows": unexpected_rows,
        "field_mismatches": field_mismatches,
        "ordering_matches": ordering_matches,
    }
