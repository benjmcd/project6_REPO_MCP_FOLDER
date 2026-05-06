from app.services.layer3_aps_source_family import (
    APS_ADMITTED_TABLE_SOURCE_FAMILIES,
    APS_NOT_ADMITTED_SOURCE_FAMILIES,
    source_family_for_parser,
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
    assert summary["admitted_materialized_families"] == list(APS_ADMITTED_TABLE_SOURCE_FAMILIES)
    assert summary["not_admitted_or_deferred_families"] == list(APS_NOT_ADMITTED_SOURCE_FAMILIES)

    summary["admitted_materialized_families"][0]["source_family"] = "mutated"
    assert APS_ADMITTED_TABLE_SOURCE_FAMILIES[0]["source_family"] == "csv"
