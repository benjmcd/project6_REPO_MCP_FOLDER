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
    {
        "parser_family": "sec_edgar_html_inline_xbrl_source_family_parser_v1",
        "source_family": "sec_edgar_html_inline_xbrl",
        "source_family_label": "SEC/EDGAR HTML inline XBRL",
        "typed_content_contract_id": "sec_edgar_html_inline_xbrl_material_units_v1",
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "bounded primary HTML/iXBRL document narrative and table candidate units materialized through governed parser receipt authority",
    },
)

RAW_MIXED_SERVER_OWNED_SOURCE_SYSTEM = "local_operator_staged_server_owned_manifest"
RAW_MIXED_SOURCE_MODE = "raw_mixed_materialized"
PUBLIC_SCIENCEBASE_SOURCE_FAMILY: dict[str, Any] = {
    "parser_family": None,
    "source_family": "sciencebase_public",
    "source_family_label": "ScienceBase-derived public dataset",
    "typed_content_contract_id": None,
    "admission_state": "admitted_materialized_dataset_version",
    "scope": "public ScienceBase CSV materialized through existing connector DatasetVersion authority",
}
RAW_MIXED_MATERIALIZED_SOURCE_FAMILY: dict[str, Any] = {
    "parser_family": None,
    "source_family": "server_owned_raw_mixed",
    "source_family_label": "Server-owned raw mixed materialization",
    "typed_content_contract_id": None,
    "admission_state": "admitted_materialized_dataset_version",
    "scope": (
        "server-owned raw mixed manifest materialized to DatasetVersion authority; "
        "mixed package semantics remain separately governed"
    ),
}

APS_ADMITTED_MATERIALIZED_SOURCE_FAMILIES: tuple[dict[str, Any], ...] = (
    *APS_ADMITTED_TABLE_SOURCE_FAMILIES,
    RAW_MIXED_MATERIALIZED_SOURCE_FAMILY,
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


def source_family_guardrail_trace(family: Mapping[str, Any]) -> dict[str, Any]:
    source_family = str(family.get("source_family") or "unknown_source_family")
    admission_state = str(family.get("admission_state") or "deferred")
    return {
        "schema_id": "layer3.aps_source_family_guardrail_trace.v1",
        "trace_scope": "source_family_guardrail",
        "selection_shape": "dataset_version",
        "trace_readiness": "guardrail_not_selectable",
        "source_family": source_family,
        "source_family_label": family.get("source_family_label"),
        "source_admission_state": admission_state,
        "source_family_scope": family.get("scope"),
        "selectable": False,
        "materialization_state": (
            "refused_without_parser_contract"
            if admission_state == "not_admitted_or_refused"
            else "deferred_until_governed_contract"
        ),
        "authority_refs": {
            "authority_source": "parser_contract_admission_policy",
            "candidate_endpoint_schema_id": "layer3.aps_dataset_version_candidates.v1",
            "selection_authority": "none",
        },
        "ui_summary": (
            "This source family is exposed as a server-owned guardrail only; "
            "it is not a selectable material candidate and has no materialized DatasetVersion authority."
        ),
    }


def _source_family_with_guardrail_trace(family: Mapping[str, Any]) -> dict[str, Any]:
    traced = dict(family)
    traced["trace_detail"] = source_family_guardrail_trace(family)
    return traced


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


def source_family_for_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    if (
        str(provenance.get("source_system") or "") == "sciencebase"
        and str(provenance.get("source_mode") or "") == "public_api"
    ):
        return dict(PUBLIC_SCIENCEBASE_SOURCE_FAMILY)
    if (
        str(provenance.get("source_system") or "") == RAW_MIXED_SERVER_OWNED_SOURCE_SYSTEM
        and str(provenance.get("source_mode") or "") == RAW_MIXED_SOURCE_MODE
    ):
        return dict(RAW_MIXED_MATERIALIZED_SOURCE_FAMILY)
    return source_family_for_parser(
        str(provenance.get("parser_family")) if provenance.get("parser_family") is not None else None
    )


def source_family_summary(candidates: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    observed_counts: dict[str, int] = {}
    for candidate in candidates:
        source_family = str(candidate.get("source_family") or "")
        if source_family == RAW_MIXED_MATERIALIZED_SOURCE_FAMILY["source_family"]:
            count_key = source_family
        else:
            count_key = str(candidate.get("parser_family") or source_family or "unknown")
        observed_counts[count_key] = observed_counts.get(count_key, 0) + 1
    return {
        "schema_id": "layer3.aps_source_family_summary.v1",
        "authority_source": "dataset_source_provenance_and_parser_contracts",
        "selection_shape": "dataset_version",
        "admitted_materialized_families": [
            dict(item) for item in APS_ADMITTED_MATERIALIZED_SOURCE_FAMILIES
        ],
        "not_admitted_or_deferred_families": [
            _source_family_with_guardrail_trace(item) for item in APS_NOT_ADMITTED_SOURCE_FAMILIES
        ],
        "observed_candidate_counts": observed_counts,
        "ui_scope": (
            "This endpoint surfaces server-backed materialized DatasetVersion choices only; "
            "refused/deferred families are explanatory guardrails with trace detail, not selectable source classes."
        ),
    }
