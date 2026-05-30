from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence


COHERENCE_CONTRACT_SCHEMA_ID = "layer3.sec_xbrl_canonical_retained_coherence.v1"


def reconcile_canonical_projection_to_retained_view(
    *,
    projection_items: Sequence[Mapping[str, Any]],
    retained_view_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the id/qname/value-store binding between normalized and retained outputs."""

    projected_items = [
        item
        for item in projection_items
        if isinstance(item, Mapping) and item.get("status") != "legitimately_absent"
    ]
    retained_records = [record for record in retained_view_records if isinstance(record, Mapping)]
    retained_by_id = _retained_records_by_fact_id(retained_records)
    retained_counts = Counter(
        _retained_fact_id(record)
        for record in retained_records
        if _retained_fact_id(record)
    )
    expected_qname_by_fact_id = _expected_qname_by_fact_id(projected_items)

    required_bindings = []
    unbound_projection_item_count = 0
    for item in projected_items:
        bindings = _required_bindings_for_projected_item(item, expected_qname_by_fact_id)
        if not bindings:
            unbound_projection_item_count += 1
        required_bindings.extend(bindings)

    normalized_fact_count = len(required_bindings)
    missing_count = 0
    bound_count = 0
    qname_consistent_count = 0
    value_reconciled_count = 0
    duplicate_value_authority_count = 0
    qname_expected_count = 0

    for binding in required_bindings:
        fact_id = binding["resolved_fact_id"]
        retained_matches = retained_by_id.get(fact_id, [])
        if not retained_matches:
            missing_count += 1
            continue
        bound_count += 1
        if retained_counts[fact_id] == 1:
            value_reconciled_count += 1
        else:
            duplicate_value_authority_count += 1
        expected_qname = binding.get("source_qname")
        if expected_qname:
            qname_expected_count += 1
            if (
                retained_counts[fact_id] == 1
                and str(retained_matches[0].get("qualified_name") or "") == expected_qname
            ):
                qname_consistent_count += 1

    retains_dimensional = any(_record_has_dimensions(record) for record in retained_records)
    retains_extension = any(record.get("concept_extension") is True for record in retained_records)
    contract_b_subset_of_a = missing_count == 0 and unbound_projection_item_count == 0
    contract_qname_consistent = qname_expected_count == qname_consistent_count
    contract_value_single_authority = normalized_fact_count == value_reconciled_count
    contract_a_strict_superset = (
        len(retained_records) > len(projected_items) and retains_dimensional and retains_extension
    )
    contract_passed = (
        normalized_fact_count > 0
        and contract_b_subset_of_a
        and contract_qname_consistent
        and contract_value_single_authority
        and contract_a_strict_superset
    )

    return {
        "schema_id": COHERENCE_CONTRACT_SCHEMA_ID,
        "normalized_fact_count": normalized_fact_count,
        "bound_count": bound_count,
        "missing_count": missing_count,
        "unbound_projection_item_count": unbound_projection_item_count,
        "qname_consistent_count": qname_consistent_count,
        "qname_expected_count": qname_expected_count,
        "value_reconciled_count": value_reconciled_count,
        "duplicate_value_authority_count": duplicate_value_authority_count,
        "retains_dimensional": retains_dimensional,
        "retains_extension": retains_extension,
        "contract_b_subset_of_a": contract_b_subset_of_a,
        "contract_qname_consistent": contract_qname_consistent,
        "contract_value_single_authority": contract_value_single_authority,
        "contract_a_strict_superset": contract_a_strict_superset,
        "contract_passed": contract_passed,
    }


def _retained_records_by_fact_id(
    retained_records: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    by_id: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in retained_records:
        fact_id = _retained_fact_id(record)
        if fact_id:
            by_id[fact_id].append(record)
    return dict(by_id)


def _expected_qname_by_fact_id(projected_items: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for item in projected_items:
        fact_id = str(item.get("resolved_fact_id") or "").strip()
        qname = str(item.get("source_qname") or "").strip()
        if fact_id and qname:
            expected[fact_id] = qname
    return expected


def _required_bindings_for_projected_item(
    item: Mapping[str, Any],
    expected_qname_by_fact_id: Mapping[str, str],
) -> list[dict[str, str]]:
    if item.get("status") == "derived":
        source_ids = item.get("derived_from_resolved_fact_ids")
        if not isinstance(source_ids, Sequence) or isinstance(source_ids, (str, bytes)):
            return []
        bindings = []
        for source_id in source_ids:
            fact_id = str(source_id or "").strip()
            if not fact_id:
                continue
            bindings.append(
                {
                    "resolved_fact_id": fact_id,
                    "source_qname": str(expected_qname_by_fact_id.get(fact_id) or ""),
                }
            )
        return bindings if len(bindings) == 2 else []

    fact_id = str(item.get("resolved_fact_id") or "").strip()
    if not fact_id:
        return []
    return [
        {
            "resolved_fact_id": fact_id,
            "source_qname": str(item.get("source_qname") or "").strip(),
        }
    ]


def _retained_fact_id(record: Mapping[str, Any]) -> str:
    return str(record.get("fact_id_or_order_key") or record.get("resolved_fact_id") or "").strip()


def _record_has_dimensions(record: Mapping[str, Any]) -> bool:
    dimensions = record.get("dimensions") if isinstance(record.get("dimensions"), Mapping) else {}
    explicit_dimensions = dimensions.get("explicit")
    typed_dimensions = dimensions.get("typed")
    return bool(explicit_dimensions) or bool(typed_dimensions)
