from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


STATEMENT_ORGANIZATION_CONTRACT_SCHEMA_ID = "layer3.sec_xbrl_canonical_statement_organization.v1"
ALIGNMENT_MAP_VERSION = "sec_xbrl_canonical_statement_alignment_v1"
CANONICAL_STATEMENT_TO_A_ROLES = {
    "income": frozenset({"income_statement", "comprehensive_income_statement"}),
    "balance": frozenset({"balance_sheet", "stockholders_equity_statement"}),
    "cashflow": frozenset({"cash_flow_statement"}),
}
UNKNOWN_A_ROLE = "unknown_or_unclassified"


def organize_canonical_projection_by_statement(
    *,
    projection_items: Sequence[Mapping[str, Any]],
    statement_role_view_records: Sequence[Mapping[str, Any]],
    alignment_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate B statement placement against A role corroboration without importing either lineage."""

    normalized_alignment = _normalized_alignment(alignment_map or CANONICAL_STATEMENT_TO_A_ROLES)
    projected_items = [
        item
        for item in projection_items
        if isinstance(item, Mapping) and item.get("status") != "legitimately_absent"
    ]
    role_by_fact_id = _role_view_by_fact_id(statement_role_view_records)

    per_statement = Counter({"income": 0, "balance": 0, "cashflow": 0})
    organized_count = 0
    a_corroborated_count = 0
    unjoined: list[dict[str, Any]] = []
    unorganized: list[dict[str, Any]] = []
    a_divergent: list[dict[str, Any]] = []
    a_role_unknown: list[dict[str, Any]] = []
    derived_count = 0
    derived_inputs_corroborated_count = 0
    derived_input_issues: list[dict[str, Any]] = []

    for item in projected_items:
        concept = _concept_ref(item)
        statement = str(item.get("statement") or "").strip()
        expected_roles = normalized_alignment.get(statement)
        if expected_roles is None:
            unorganized.append(concept)
            continue

        per_statement[statement] += 1
        organized_count += 1
        if _is_derived_item(item):
            derived_count += 1
            source_ids = _derived_source_ids(item)
            outcomes = [_role_outcome(role_by_fact_id.get(source_id), expected_roles) for source_id in source_ids]
            if len(source_ids) == 2 and all(outcome["state"] == "corroborated" for outcome in outcomes):
                derived_inputs_corroborated_count += 1
                a_corroborated_count += 1
            else:
                derived_input_issues.append(
                    {
                        **concept,
                        "missing_input_count": max(2 - len(source_ids), 0)
                        + sum(1 for outcome in outcomes if outcome["state"] == "unjoined"),
                        "uncorroborated_input_count": sum(
                            1 for outcome in outcomes if outcome["state"] in {"divergent", "unknown"}
                        ),
                    }
                )
            continue

        fact_id = str(item.get("resolved_fact_id") or "").strip()
        outcome = _role_outcome(role_by_fact_id.get(fact_id), expected_roles)
        if outcome["state"] == "corroborated":
            a_corroborated_count += 1
        elif outcome["state"] == "unknown":
            a_role_unknown.append({**concept, "a_role": UNKNOWN_A_ROLE})
        elif outcome["state"] == "unjoined":
            unjoined.append(concept)
        else:
            a_divergent.append({**concept, "a_role": outcome["a_role"]})

    normalized_fact_count = len(projected_items)
    unjoined_count = len(unjoined)
    contract_b_authoritative_organization = normalized_fact_count > 0 and not unorganized
    contract_every_fact_id_bound = unjoined_count == 0
    contract_derived_inputs_bound_and_corroborated = not derived_input_issues
    contract_passed = (
        normalized_fact_count > 0
        and contract_b_authoritative_organization
        and contract_every_fact_id_bound
        and contract_derived_inputs_bound_and_corroborated
    )

    return {
        "schema_id": STATEMENT_ORGANIZATION_CONTRACT_SCHEMA_ID,
        "alignment_map_version": ALIGNMENT_MAP_VERSION,
        "normalized_fact_count": normalized_fact_count,
        "organized_count": organized_count,
        "a_corroborated_count": a_corroborated_count,
        "a_divergent_count": len(a_divergent),
        "a_role_unknown_count": len(a_role_unknown),
        "unjoined_count": unjoined_count,
        "derived_count": derived_count,
        "derived_inputs_corroborated_count": derived_inputs_corroborated_count,
        "per_statement": {statement: int(per_statement[statement]) for statement in ("income", "balance", "cashflow")},
        "a_divergent": _dedup_concept_records(a_divergent),
        "a_role_unknown": _dedup_concept_records(a_role_unknown),
        "unjoined": _dedup_concept_records(unjoined),
        "unorganized": _dedup_concept_records(unorganized),
        "derived_input_issues": _dedup_concept_records(derived_input_issues),
        "a_full_corroboration": len(a_divergent) == 0 and len(a_role_unknown) == 0,
        "contract_b_authoritative_organization": contract_b_authoritative_organization,
        "contract_every_fact_id_bound": contract_every_fact_id_bound,
        "contract_derived_inputs_bound_and_corroborated": contract_derived_inputs_bound_and_corroborated,
        "contract_passed": contract_passed,
    }


def _normalized_alignment(alignment_map: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    normalized: dict[str, frozenset[str]] = {}
    for statement, roles in alignment_map.items():
        statement_text = str(statement or "").strip()
        if not statement_text:
            continue
        if isinstance(roles, str):
            role_values = [roles]
        else:
            role_values = list(roles or [])
        normalized[statement_text] = frozenset(str(role or "").strip() for role in role_values if str(role or "").strip())
    return normalized


def _role_view_by_fact_id(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    by_fact_id: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        fact_id = str(record.get("fact_id_or_order_key") or record.get("resolved_fact_id") or "").strip()
        if fact_id and fact_id not in by_fact_id:
            by_fact_id[fact_id] = record
    return by_fact_id


def _role_outcome(record: Mapping[str, Any] | None, expected_roles: frozenset[str]) -> dict[str, str]:
    if not isinstance(record, Mapping):
        return {"state": "unjoined", "a_role": ""}
    role = str(record.get("statement_candidate_role") or UNKNOWN_A_ROLE).strip() or UNKNOWN_A_ROLE
    if role == UNKNOWN_A_ROLE:
        return {"state": "unknown", "a_role": role}
    if role in expected_roles:
        return {"state": "corroborated", "a_role": role}
    return {"state": "divergent", "a_role": role}


def _is_derived_item(item: Mapping[str, Any]) -> bool:
    return str(item.get("status") or "") == "derived" or bool(_derived_source_ids(item))


def _derived_source_ids(item: Mapping[str, Any]) -> list[str]:
    source_ids = item.get("derived_from_resolved_fact_ids")
    if not isinstance(source_ids, Sequence) or isinstance(source_ids, (str, bytes)):
        return []
    return [str(source_id or "").strip() for source_id in source_ids if str(source_id or "").strip()]


def _concept_ref(item: Mapping[str, Any]) -> dict[str, str]:
    return {
        "canonical_id": str(item.get("canonical_id") or ""),
        "basis": str(item.get("basis") or ""),
        "statement": str(item.get("statement") or ""),
        "taxonomy": str(item.get("taxonomy") or item.get("primary_taxonomy") or ""),
    }


def _dedup_concept_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for record in records:
        public = {
            key: str(record.get(key) or "")
            for key in ("canonical_id", "basis", "statement", "a_role", "taxonomy")
            if key in record
        }
        marker = tuple(sorted(public.items()))
        if marker not in seen:
            seen.add(marker)
            deduped.append(public)
    return deduped
