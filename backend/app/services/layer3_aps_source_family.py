from __future__ import annotations

from typing import Any, Iterable, Mapping

APS_ADMITTED_TABLE_SOURCE_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "parser_family": "csv_table",
        "source_family": "csv",
        "source_family_label": "CSV table",
        "typed_content_contract_id": "aps_csv_table_units_v1",
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "bounded CSV/delimited table parser output materialized through APS dataset bridge authority",
    },
    {
        "parser_family": "xlsx_workbook",
        "source_family": "xlsx",
        "source_family_label": "XLSX workbook table",
        "typed_content_contract_id": "aps_xlsx_workbook_units_v1",
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "bounded selected/simple sheet table materialized through generic APS table bridge authority",
    },
    {
        "parser_family": "json_recordset",
        "source_family": "json_recordset",
        "source_family_label": "JSON recordset",
        "typed_content_contract_id": "aps_json_recordset_units_v1",
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "bounded flat recordset materialized through generic APS table bridge authority",
    },
    {
        "parser_family": "sec_edgar_filing",
        "source_family": "sec_edgar_text_table",
        "source_family_label": "SEC/EDGAR text table",
        "typed_content_contract_id": "aps_sec_edgar_filing_units_v1",
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "bounded complete-submission text filing tables materialized through generic APS table bridge authority",
    },
)

APS_NOT_ADMITTED_SOURCE_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "source_family": "xml_html_inline_xbrl",
        "source_family_label": "XML/HTML/inline XBRL",
        "admission_state": "not_admitted_or_refused",
        "scope": "refused until a dedicated parser contract is specified and implemented",
    },
    {
        "source_family": "broad_workbook_semantics",
        "source_family_label": "Broad workbook semantics",
        "admission_state": "deferred",
        "scope": "multi-sheet ambiguity, formulas, encrypted files, macro workbooks, and arbitrary ranges remain out of scope",
    },
    {
        "source_family": "archive_member_table_or_filing_orchestration",
        "source_family_label": "Archive-member typed orchestration",
        "admission_state": "deferred",
        "scope": "XLSX, JSON, and SEC/EDGAR table materialization from archive members remains separate from visible archive-member accounting",
    },
    {
        "source_family": "mixed_source_package_semantics",
        "source_family_label": "Mixed-source package semantics",
        "admission_state": "deferred",
        "scope": "narrative-plus-table package governance remains separate from dataset_version selection",
    },
)

APS_ADMITTED_SOURCE_FAMILY_BY_PARSER: dict[str, dict[str, Any]] = {
    str(item["parser_family"]): dict(item) for item in APS_ADMITTED_TABLE_SOURCE_FAMILIES
}


def source_family_for_parser(parser_family: str | None) -> dict[str, Any]:
    metadata = APS_ADMITTED_SOURCE_FAMILY_BY_PARSER.get(str(parser_family or ""))
    if metadata:
        return dict(metadata)
    return {
        "parser_family": parser_family,
        "source_family": "unknown_aps_dataset_version",
        "source_family_label": "APS-derived dataset",
        "typed_content_contract_id": None,
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "materialized APS-derived DatasetVersion with parser family metadata unavailable",
    }


def source_family_summary(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    observed_counts: dict[str, int] = {}
    for candidate in candidates:
        parser_family = str(candidate.get("parser_family") or "unknown")
        observed_counts[parser_family] = observed_counts.get(parser_family, 0) + 1
    return {
        "schema_id": "layer3.aps_source_family_summary.v1",
        "authority_source": "dataset_source_provenance_and_parser_contracts",
        "selection_shape": "dataset_version",
        "admitted_materialized_families": [dict(item) for item in APS_ADMITTED_TABLE_SOURCE_FAMILIES],
        "not_admitted_or_deferred_families": [dict(item) for item in APS_NOT_ADMITTED_SOURCE_FAMILIES],
        "observed_candidate_counts": observed_counts,
        "ui_scope": (
            "This endpoint surfaces server-backed materialized DatasetVersion choices only; "
            "refused/deferred families are explanatory guardrails, not selectable source classes."
        ),
    }
