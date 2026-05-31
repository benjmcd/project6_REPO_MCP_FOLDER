from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from app.services import layer3_sec_edgar_html_inline_xbrl_fact_statement_classification as classifier
from app.services import layer3_sec_xbrl_canonical_statement_organization as organization


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-statement-organization.py"
REPORT_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-statement-organization-report.json"
RAW_RESOLVED_FACT_ID_PREFIX = "fact" + "-"
RAW_ENTITY_REFERENCE_TOKEN = "issuer" + "_ref"
RAW_ENTITY_DIGEST_TOKEN = "issuer" + "_hash"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_canonical_statement_organization", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_us_gaap_fixture_fully_corroborates_and_binds_derived_inputs() -> None:
    result = organization.organize_canonical_projection_by_statement(
        projection_items=[
            _projected("TotalAssets", "total", "balance", "fact-assets", taxonomy="us-gaap"),
            _projected("CurrentAssets", "total", "balance", "fact-current-assets", taxonomy="us-gaap"),
            _projected("Revenue", "total", "income", "fact-revenue", taxonomy="us-gaap"),
            _derived(
                "NoncurrentAssets",
                "balance",
                ["fact-assets", "fact-current-assets"],
                taxonomy="us-gaap",
            ),
        ],
        statement_role_view_records=[
            _role("fact-assets", "balance_sheet"),
            _role("fact-current-assets", "balance_sheet"),
            _role("fact-revenue", "income_statement"),
        ],
    )

    assert result["contract_passed"] is True
    assert result["contract_b_authoritative_organization"] is True
    assert result["contract_every_fact_id_bound"] is True
    assert result["contract_derived_inputs_bound_and_corroborated"] is True
    assert result["normalized_fact_count"] == 4
    assert result["organized_count"] == 4
    assert result["a_corroborated_count"] == 4
    assert result["a_divergent_count"] == 0
    assert result["a_role_unknown_count"] == 0
    assert result["derived_count"] == 1
    assert result["derived_inputs_corroborated_count"] == 1
    assert result["a_full_corroboration"] is True


def test_ifrs_known_a_divergences_are_reported_without_failing_b_contract() -> None:
    result = organization.organize_canonical_projection_by_statement(
        projection_items=[
            _projected("OperatingIncome", "total", "income", "fact-operating-income", taxonomy="ifrs-full"),
            _projected("Equity", "total", "balance", "fact-equity-total", taxonomy="ifrs-full"),
            _projected("Equity", "parent", "balance", "fact-equity-parent", taxonomy="ifrs-full"),
            _projected("Revenue", "total", "income", "fact-revenue", taxonomy="ifrs-full"),
        ],
        statement_role_view_records=[
            _role("fact-operating-income", "cash_flow_statement"),
            _role("fact-equity-total", "unknown_or_unclassified"),
            _role("fact-equity-parent", "unknown_or_unclassified"),
            _role("fact-revenue", "income_statement"),
        ],
    )

    assert result["contract_passed"] is True
    assert result["a_corroborated_count"] == 1
    assert result["a_divergent_count"] == 1
    assert result["a_role_unknown_count"] == 2
    assert result["a_full_corroboration"] is False
    assert result["a_divergent"] == [
        {
            "canonical_id": "OperatingIncome",
            "basis": "total",
            "statement": "income",
            "a_role": "cash_flow_statement",
            "taxonomy": "ifrs-full",
        }
    ]
    assert result["a_role_unknown"] == [
        {
            "canonical_id": "Equity",
            "basis": "total",
            "statement": "balance",
            "a_role": "unknown_or_unclassified",
            "taxonomy": "ifrs-full",
        },
        {
            "canonical_id": "Equity",
            "basis": "parent",
            "statement": "balance",
            "a_role": "unknown_or_unclassified",
            "taxonomy": "ifrs-full",
        },
    ]


def test_unjoined_direct_fact_fails_every_fact_bound_contract() -> None:
    result = organization.organize_canonical_projection_by_statement(
        projection_items=[_projected("Revenue", "total", "income", "fact-missing")],
        statement_role_view_records=[],
    )

    assert result["contract_passed"] is False
    assert result["contract_every_fact_id_bound"] is False
    assert result["unjoined_count"] == 1
    assert result["unjoined"] == [{"canonical_id": "Revenue", "basis": "total", "statement": "income", "taxonomy": ""}]


def test_blank_b_statement_fails_authoritative_organization_contract() -> None:
    result = organization.organize_canonical_projection_by_statement(
        projection_items=[_projected("Revenue", "total", "", "fact-revenue")],
        statement_role_view_records=[_role("fact-revenue", "income_statement")],
    )

    assert result["contract_passed"] is False
    assert result["contract_b_authoritative_organization"] is False
    assert result["organized_count"] == 0
    assert result["unorganized"] == [{"canonical_id": "Revenue", "basis": "total", "statement": "", "taxonomy": ""}]


def test_derived_input_unjoined_fails_derived_input_contract() -> None:
    result = organization.organize_canonical_projection_by_statement(
        projection_items=[_derived("NoncurrentAssets", "balance", ["fact-assets", "fact-current-assets"])],
        statement_role_view_records=[_role("fact-assets", "balance_sheet")],
    )

    assert result["contract_passed"] is False
    assert result["contract_derived_inputs_bound_and_corroborated"] is False
    assert result["derived_count"] == 1
    assert result["derived_inputs_corroborated_count"] == 0
    assert result["derived_input_issues"] == [
        {"canonical_id": "NoncurrentAssets", "basis": "total", "statement": "balance", "taxonomy": ""}
    ]


def test_accessor_role_parity_matches_classifier_record() -> None:
    retained_records = [
        {
            "fact_id_or_order_key": "fact-operating-income",
            "qualified_name": "ifrs-full:ProfitLossFromOperatingActivities",
        },
        {
            "fact_id_or_order_key": "fact-equity",
            "qualified_name": "ifrs-full:Equity",
        },
    ]
    view = classifier.statement_role_view_from_retained_records(retained_records)
    inventory = [
        classifier._classification_record(
            {
                "fact_id_or_order_key": record["fact_id_or_order_key"],
                "qualified_name": record["qualified_name"],
                "namespace_prefix": record["qualified_name"].split(":", 1)[0],
                "local_name": record["qualified_name"].split(":", 1)[1],
            },
            fact_order=index,
            fact_inventory_hash="fixture-hash",
        )
        for index, record in enumerate(retained_records, start=1)
    ]

    assert {
        item["fact_id_or_order_key"]: item["statement_candidate_role"]
        for item in view
    } == {
        item["fact_id_or_order_key"]: item["statement_candidate_role"]
        for item in inventory
    }
    assert view[0]["concept_family"] == inventory[0]["semantic_profile"]["concept_family"]


def test_diagnostic_report_splits_by_taxonomy_and_preserves_ifrs_drift_guard(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    report = diagnostic.build_report(source_root=_source_root(tmp_path))

    assert report["decision"] == "canonical_statement_organization_validate_only_ready"
    assert report["summary"] == {
        "contract_passed": True,
        "total_a_corroborated": 58,
        "total_a_divergent": 2,
        "total_a_role_unknown": 4,
        "total_normalized": 64,
        "total_organized": 64,
        "total_unjoined": 0,
    }
    assert {item["taxonomy"]: item for item in report["per_taxonomy"]}["us-gaap"]["a_full_corroboration"] is True
    assert {item["taxonomy"]: item for item in report["per_taxonomy"]}["ifrs-full"]["a_full_corroboration"] is False
    assert report["a_role_used_as_pass_gate"] is False
    assert report["a_divergent"] == [
        {
            "canonical_id": "OperatingIncome",
            "basis": "total",
            "statement": "income",
            "a_role": "cash_flow_statement",
            "taxonomy": "ifrs-full",
        }
    ]
    assert report["a_role_unknown"] == [
        {
            "canonical_id": "Equity",
            "basis": "total",
            "statement": "balance",
            "a_role": "unknown_or_unclassified",
            "taxonomy": "ifrs-full",
        },
        {
            "canonical_id": "Equity",
            "basis": "parent",
            "statement": "balance",
            "a_role": "unknown_or_unclassified",
            "taxonomy": "ifrs-full",
        },
    ]
    assert report["redaction"]["passed"] is True


def test_diagnostic_report_preserves_explicit_empty_taxonomy_results(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    report = diagnostic.build_report(source_root=_source_root(tmp_path), taxonomy_results=[])

    assert report["decision"] == "no_statement_organization_evidence"
    assert report["summary"]["contract_passed"] is False
    assert report["summary"]["total_normalized"] == 0
    assert report["per_taxonomy"] == []
    assert report["blocking_reasons"]


def test_diagnostic_report_fails_closed_on_duplicate_taxonomy_rows(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    reference = list(diagnostic.REFERENCE_TAXONOMY_RESULTS)
    duplicate_taxonomy_rows = [reference[0], reference[0], reference[1]]

    report = diagnostic.build_report(
        source_root=_source_root(tmp_path),
        taxonomy_results=duplicate_taxonomy_rows,
    )

    assert report["decision"] == "canonical_statement_organization_validate_only_blocked"
    assert any(
        item["reason"] == "canonical_statement_organization_counts_inconsistent"
        for item in report["blocking_reasons"]
    )


def test_committed_report_is_redacted_taxonomy_aggregate_only() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    text = json.dumps(report, sort_keys=True)

    assert report["schema_id"] == "diagnostics.sec_xbrl_canonical_statement_organization.v1"
    assert report["summary"]["contract_passed"] is True
    assert report["summary"]["total_normalized"] == 64
    assert report["summary"]["total_unjoined"] == 0
    assert [item["taxonomy"] for item in report["per_taxonomy"]] == ["us-gaap", "ifrs-full"]
    assert "per_issuer" not in report
    assert '"source_qname"' not in text
    assert '"resolved_fact_id"' not in text
    assert RAW_RESOLVED_FACT_ID_PREFIX not in text
    assert RAW_ENTITY_REFERENCE_TOKEN not in text
    assert RAW_ENTITY_DIGEST_TOKEN not in text
    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    assert ":/" + "/" not in text
    assert "C:" + "\\" not in text
    assert report["redaction"]["passed"] is True


def _projected(
    canonical_id: str,
    basis: str,
    statement: str,
    fact_id: str,
    *,
    taxonomy: str = "",
) -> dict:
    return {
        "canonical_id": canonical_id,
        "basis": basis,
        "statement": statement,
        "status": "projected_oracle_confirmed",
        "resolved_fact_id": fact_id,
        "taxonomy": taxonomy,
    }


def _derived(
    canonical_id: str,
    statement: str,
    source_ids: list[str],
    *,
    taxonomy: str = "",
) -> dict:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "statement": statement,
        "status": "derived",
        "derived_from_resolved_fact_ids": source_ids,
        "taxonomy": taxonomy,
    }


def _role(fact_id: str, role: str) -> dict:
    return {
        "fact_id_or_order_key": fact_id,
        "statement_candidate_role": role,
    }


def _source_root(tmp_path: Path) -> Path:
    source_root = tmp_path / "source"
    config_path = source_root / "backend" / "app" / "core" / "config.py"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '''
class Settings:
    layer3_sec_edgar_live_network_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    )
    layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED",
    )
    layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(
        default=False,
        alias="LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    )
''',
        encoding="utf-8",
    )
    return source_root
