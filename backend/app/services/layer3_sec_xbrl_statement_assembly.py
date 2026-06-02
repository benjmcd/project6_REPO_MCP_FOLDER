from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence


STATEMENT_ASSEMBLY_SCHEMA_ID = "layer3.sec_xbrl_reviewable_statement_packet.v1"
STATEMENT_ASSEMBLY_VERSION = "sec_xbrl_reviewable_statement_packet_v1"
STATEMENT_ORDER = ("income", "balance", "cashflow")
VALUE_POLICY = "redacted_no_values"


def assemble_reviewable_statement_packet(
    *,
    projection_items: Sequence[Mapping[str, Any]],
    organization_result: Mapping[str, Any],
    identity_residuals: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a redacted review packet from canonical projection and organization authority."""

    projected_items = [
        item
        for item in projection_items
        if isinstance(item, Mapping) and item.get("status") != "legitimately_absent"
    ]
    blocking_reasons: list[dict[str, Any]] = []
    if not projected_items:
        blocking_reasons.append({"reason": "statement_assembly_no_projected_facts"})
    if organization_result.get("contract_passed") is not True:
        blocking_reasons.append(
            {
                "reason": "statement_organization_contract_not_passed",
                "contract_passed": organization_result.get("contract_passed") is True,
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = {statement: [] for statement in STATEMENT_ORDER}
    row_counts_by_statement_period: dict[tuple[str, str, int], int] = defaultdict(int)
    unassigned: list[dict[str, Any]] = []
    for index, item in enumerate(projected_items, start=1):
        row = _public_row(item=item, source_index=index)
        statement = row["statement"]
        if statement not in grouped:
            unassigned.append(_row_ref(row))
            continue
        row_counts_by_statement_period[_row_index_key(row)] += 1
        row["statement_row_index"] = row_counts_by_statement_period[_row_index_key(row)]
        grouped[statement].append(row)

    if unassigned:
        blocking_reasons.append(
            {
                "reason": "statement_assembly_unassigned_statement",
                "unassigned_count": len(unassigned),
            }
        )

    statements = [_statement_packet(statement, grouped[statement]) for statement in STATEMENT_ORDER]
    identity_rollup = _identity_rollup(identity_residuals or [])
    total_rows = sum(item["line_count"] for item in statements)
    provenance_complete_count = sum(
        1
        for statement in statements
        for row in statement["rows"]
        if row.get("provenance_complete") is True
    )
    review_exception_count = sum(int(item["review_exception_count"]) for item in statements) + len(unassigned)
    status = "statement_assembly_ready" if not blocking_reasons else "statement_assembly_blocked"

    return {
        "schema_id": STATEMENT_ASSEMBLY_SCHEMA_ID,
        "version": STATEMENT_ASSEMBLY_VERSION,
        "status": status,
        "value_policy": VALUE_POLICY,
        "canonical_projection_authority": "canonical_projection_items",
        "statement_organization_authority": "canonical_statement_organization_contract",
        "statement_count": len(STATEMENT_ORDER),
        "total_review_rows": total_rows,
        "provenance_complete_count": provenance_complete_count,
        "review_exception_count": review_exception_count,
        "review_ready": (
            status == "statement_assembly_ready"
            and total_rows > 0
            and provenance_complete_count == total_rows
            and identity_rollup["identity_residuals_within_tolerance"] is not False
        ),
        "statements": statements,
        "unassigned": unassigned,
        "identity_rollup": identity_rollup,
        "organization_contract": _organization_contract_summary(organization_result),
        "blocking_reasons": blocking_reasons,
    }


def _statement_packet(statement: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(row.get("status") or "") for row in rows)
    family_counts = Counter(str(row.get("family") or "universal") for row in rows)
    review_exception_count = sum(
        1
        for row in rows
        if row.get("provenance_complete") is not True
        or row.get("oracle_confirmed") is False
        or row.get("oracle_confirmed") == "oracle_absent"
    )
    return {
        "statement": statement,
        "line_count": len(rows),
        "projected_count": sum(1 for row in rows if str(row.get("status") or "").startswith("projected")),
        "derived_count": sum(1 for row in rows if row.get("status") == "derived"),
        "provenance_complete_count": sum(1 for row in rows if row.get("provenance_complete") is True),
        "review_exception_count": review_exception_count,
        "status_counts": dict(sorted(status_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "rows": list(rows),
    }


def _public_row(*, item: Mapping[str, Any], source_index: int) -> dict[str, Any]:
    row = {
        "source_index": source_index,
        "canonical_id": str(item.get("canonical_id") or ""),
        "basis": str(item.get("basis") or ""),
        "requested_basis": str(item.get("requested_basis") or item.get("basis") or ""),
        "statement": str(item.get("statement") or ""),
        "family": str(item.get("family") or "universal"),
        "status": str(item.get("status") or ""),
        "source_qname": item.get("source_qname"),
        "period_class": str(item.get("period_class") or ""),
        "oracle_confirmed": item.get("oracle_confirmed"),
        "mapping_method": item.get("mapping_method"),
        "mapping_confidence": item.get("mapping_confidence"),
        "provenance_complete": item.get("provenance_complete") is True,
        "value_redacted": _has_raw_value(item),
    }
    if item.get("unit_class") is not None:
        row["unit_class"] = item.get("unit_class")
    if item.get("derived_from_concepts") is not None:
        row["derived_from_concepts"] = list(item.get("derived_from_concepts") or [])
    if item.get("period_ref") is not None:
        row["period_ref"] = str(item.get("period_ref") or "")
    if item.get("period_index") is not None:
        row["period_index"] = int(item.get("period_index") or 0)
    return row


def _has_raw_value(item: Mapping[str, Any]) -> bool:
    return any(key in item and item.get(key) is not None for key in ("_value", "value", "effective_value", "amount"))


def _row_index_key(row: Mapping[str, Any]) -> tuple[str, str, int]:
    period_ref = str(row.get("period_ref") or "")
    period_index = int(row.get("period_index") or 0)
    return (str(row.get("statement") or ""), period_ref, period_index)


def _row_ref(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        "canonical_id": str(row.get("canonical_id") or ""),
        "basis": str(row.get("basis") or ""),
        "statement": str(row.get("statement") or ""),
        "family": str(row.get("family") or "universal"),
    }


def _identity_rollup(identity_residuals: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    public_residuals = []
    evaluated_count = 0
    within_count = 0
    failed_count = 0
    for item in identity_residuals:
        if not isinstance(item, Mapping):
            continue
        if item.get("status") not in {None, "evaluated"} and item.get("within_tolerance") is None:
            continue
        within = item.get("within_tolerance")
        if within is True or within is False:
            evaluated_count += 1
            within_count += 1 if within is True else 0
            failed_count += 1 if within is False else 0
        public_residuals.append(
            {
                "identity_id": str(item.get("identity_id") or ""),
                "status": str(item.get("status") or "evaluated"),
                "within_tolerance": within,
                "relative_magnitude": item.get("relative_magnitude"),
                "residual_abs": item.get("residual_abs"),
            }
        )
    return {
        "identity_residual_count": len(public_residuals),
        "identity_residual_evaluated_count": evaluated_count,
        "identity_residual_within_tolerance_count": within_count,
        "identity_residual_failed_count": failed_count,
        "identity_residuals_within_tolerance": None if evaluated_count == 0 else failed_count == 0,
        "identity_residuals": public_residuals,
    }


def _organization_contract_summary(organization_result: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "contract_passed",
        "contract_b_authoritative_organization",
        "contract_every_fact_id_bound",
        "contract_derived_inputs_bound_and_corroborated",
        "normalized_fact_count",
        "organized_count",
        "unjoined_count",
        "a_divergent_count",
        "a_role_unknown_count",
    )
    return {key: organization_result.get(key) for key in keys if key in organization_result}

