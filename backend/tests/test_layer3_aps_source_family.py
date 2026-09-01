from app.services.layer3_aps_source_family import (
    APS_ADMITTED_TABLE_SOURCE_FAMILIES,
    APS_NOT_ADMITTED_SOURCE_FAMILIES,
    source_family_for_parser,
    source_family_guardrail_trace,
    source_family_for_provenance,
    source_family_summary,
)


def test_source_family_for_parser_maps_admitted_aps_table_families() -> None:
    expected = {
        "csv_table": ("csv", "CSV table", "aps_csv_table_units_v1"),
        "xlsx_workbook": ("xlsx", "XLSX workbook table", "aps_xlsx_workbook_units_v1"),
        "json_recordset": ("json_recordset", "JSON recordset", "aps_json_recordset_units_v1"),
        "sec_edgar_filing": (
            "sec_edgar_text_table",
            "SEC/EDGAR text table",
            "aps_sec_edgar_filing_units_v1",
        ),
        "sec_edgar_html_inline_xbrl_source_family_parser_v1": (
            "sec_edgar_html_inline_xbrl",
            "SEC/EDGAR HTML inline XBRL",
            "sec_edgar_html_inline_xbrl_material_units_v1",
        ),
    }

    for parser_family, (source_family, label, contract_id) in expected.items():
        metadata = source_family_for_parser(parser_family)
        assert metadata["parser_family"] == parser_family
        assert metadata["source_family"] == source_family
        assert metadata["source_family_label"] == label
        assert metadata["typed_content_contract_id"] == contract_id
        assert metadata["admission_state"] == "admitted_materialized_dataset_version"


def test_source_family_for_parser_returns_unknown_metadata_copy() -> None:
    metadata = source_family_for_parser("custom_parser")

    assert metadata == {
        "parser_family": "custom_parser",
        "source_family": "unknown_aps_dataset_version",
        "source_family_label": "APS-derived dataset",
        "typed_content_contract_id": None,
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "materialized APS-derived DatasetVersion with parser family metadata unavailable",
    }


def test_source_family_for_provenance_labels_server_owned_raw_mixed_materialization() -> None:
    metadata = source_family_for_provenance(
        {
            "source_system": "local_operator_staged_server_owned_manifest",
            "source_mode": "raw_mixed_materialized",
            "parser_family": "csv_table",
        }
    )

    assert metadata["source_family"] == "server_owned_raw_mixed"
    assert metadata["source_family_label"] == "Server-owned raw mixed materialization"
    assert metadata["admission_state"] == "admitted_materialized_dataset_version"
    assert "mixed package semantics remain separately governed" in metadata["scope"]


def test_source_family_for_provenance_keeps_parser_family_for_regular_aps_tables() -> None:
    metadata = source_family_for_provenance(
        {
            "source_system": "nrc_adams_aps",
            "source_mode": "artifact_csv_parser",
            "parser_family": "csv_table",
        }
    )

    assert metadata["source_family"] == "csv"
    assert metadata["source_family_label"] == "CSV table"


def test_source_family_for_provenance_labels_public_sciencebase_without_aps_claim() -> None:
    metadata = source_family_for_provenance(
        {
            "source_system": "sciencebase",
            "source_mode": "public_api",
            "parser_family": None,
        }
    )

    assert metadata == {
        "parser_family": None,
        "source_family": "sciencebase_public",
        "source_family_label": "ScienceBase-derived public dataset",
        "typed_content_contract_id": None,
        "admission_state": "admitted_materialized_dataset_version",
        "scope": "public ScienceBase CSV materialized through existing connector DatasetVersion authority",
    }


def test_source_family_guardrail_trace_marks_refused_family_non_selectable() -> None:
    family = APS_NOT_ADMITTED_SOURCE_FAMILIES[0]
    trace = source_family_guardrail_trace(family)

    assert trace["schema_id"] == "layer3.aps_source_family_guardrail_trace.v1"
    assert trace["trace_scope"] == "source_family_guardrail"
    assert trace["trace_readiness"] == "guardrail_not_selectable"
    assert trace["source_family"] == "xml_html_inline_xbrl"
    assert trace["source_admission_state"] == "not_admitted_or_refused"
    assert trace["selectable"] is False
    assert trace["materialization_state"] == "refused_without_parser_contract"
    assert trace["authority_refs"]["selection_authority"] == "none"
    assert "not a selectable material candidate" in trace["ui_summary"]


def test_source_family_summary_counts_observed_parsers_and_returns_copies() -> None:
    summary = source_family_summary(
        [
            {"parser_family": "csv_table"},
            {"parser_family": "csv_table"},
            {"parser_family": "sec_edgar_filing"},
            {},
        ]
    )

    assert summary["schema_id"] == "layer3.aps_source_family_summary.v1"
    assert summary["authority_source"] == "dataset_source_provenance_and_parser_contracts"
    assert summary["selection_shape"] == "dataset_version"
    assert summary["observed_candidate_counts"] == {
        "csv_table": 2,
        "sec_edgar_filing": 1,
        "unknown": 1,
    }
    admitted = summary["admitted_materialized_families"]
    assert admitted[: len(APS_ADMITTED_TABLE_SOURCE_FAMILIES)] == list(
        APS_ADMITTED_TABLE_SOURCE_FAMILIES
    )
    assert admitted[-1]["source_family"] == "server_owned_raw_mixed"
    assert admitted[-1]["parser_family"] is None
    assert len(summary["not_admitted_or_deferred_families"]) == len(APS_NOT_ADMITTED_SOURCE_FAMILIES)
    guardrail = summary["not_admitted_or_deferred_families"][0]
    assert guardrail["source_family"] == APS_NOT_ADMITTED_SOURCE_FAMILIES[0]["source_family"]
    assert guardrail["trace_detail"]["trace_readiness"] == "guardrail_not_selectable"
    assert guardrail["trace_detail"]["selectable"] is False

    summary["admitted_materialized_families"][0]["source_family"] = "mutated"
    summary["admitted_materialized_families"][-1]["source_family"] = "mutated"
    summary["not_admitted_or_deferred_families"][0]["trace_detail"]["source_family"] = "mutated"
    assert APS_ADMITTED_TABLE_SOURCE_FAMILIES[0]["source_family"] == "csv"
    assert APS_NOT_ADMITTED_SOURCE_FAMILIES[0]["source_family"] == "xml_html_inline_xbrl"

    raw_mixed_summary = source_family_summary(
        [{"parser_family": "csv_table", "source_family": "server_owned_raw_mixed"}]
    )
    assert raw_mixed_summary["observed_candidate_counts"] == {
        "server_owned_raw_mixed": 1
    }
