from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
from pathlib import Path

from app.services import layer3_sec_xbrl_canonical_concepts as canonical
from app.services.layer3_utils import stable_hash


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-projection.py"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_canonical_projection", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reference_summary_projection_counts_are_internally_consistent(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    report = diagnostic.build_report(source_root=_source_root(tmp_path))
    issuer = report["per_issuer"][0]
    text = json.dumps(report, sort_keys=True)

    assert report["decision"] == "canonical_projection_validate_only_ready"
    assert report["include_sector_families"] is False
    assert report["issuer_hash_count"] == 1
    assert issuer["issuer_hash"] == stable_hash({"issuer_ref": "redacted-reference-projection-a"})[:24]
    assert issuer["primary_taxonomy"] == "ifrs-full"
    assert issuer["headline_canonical_defined"] == 22
    assert issuer["universal_defined_count"] == 22
    assert issuer["sector_family_defined_count"] == 0
    assert issuer["projected_count"] == 21
    assert issuer["provenance_complete_count"] == issuer["projected_count"]
    assert issuer["oracle_confirmed_count"] == 21
    assert issuer["legitimately_absent_count"] == 1
    assert report["summary"]["statement_identity_residual_magnitudes_redacted"] is True
    assert report["statement_identity_residuals"][0]["within_tolerance"] is True
    assert "relative_magnitude" not in text
    assert "residual_abs" not in text


def test_projection_sources_fy_sidecar_value_and_provenance() -> None:
    sidecar_records = [
        _record(
            "rf-revenue-old",
            "us-gaap",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            start="start-1",
            end="end-1",
        ),
        _record(
            "rf-revenue-fy",
            "us-gaap",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            start="start-2",
            end="end-2",
        ),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-revenue-old", "90"),
        _value("rf-revenue-fy", "100"),
        _value("rf-assets-fy", "200"),
        _value("rf-period-end", "end-2"),
    ]

    result = _project(
        companyfacts=_companyfacts(
            [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD")]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    revenue = _find(result["concepts"], "Revenue", "total")

    assert result["status"] == "canonical_projection_ready"
    assert result["fy_period"]["duration_period_key"] == ("d", "start-2", "end-2")
    assert result["fy_period"]["document_period_end_date_cross_checked"] is True
    assert revenue["status"] == "projected_oracle_confirmed"
    assert revenue["_value"] == Decimal("100")
    assert revenue["resolved_fact_id"] == "rf-revenue-fy"
    assert revenue["provenance_complete"] is True
    assert revenue["value_store_hash"] == stable_hash(value_records)


def test_fy_periods_from_records_returns_document_period_then_comparatives() -> None:
    sidecar_records = [
        _record("rf-revenue-old", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-1", end="end-1"),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", end="end-1", instant=True),
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-2", end="end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-revenue-old", "90"),
        _value("rf-assets-old", "180"),
        _value("rf-revenue-fy", "100"),
        _value("rf-assets-fy", "200"),
        _value("rf-period-end", "end-2"),
    ]

    periods = canonical.fy_periods_from_records(sidecar_records, value_records)

    assert [item["period_ref"] for item in periods] == ["fy-period-1", "fy-period-2"]
    assert periods[0]["duration_period_key"] == ("d", "start-2", "end-2")
    assert periods[0]["instant_period_key"] == ("i", "end-2")
    assert periods[0]["matches_document_period_end_date"] is True
    assert periods[1]["duration_period_key"] == ("d", "start-1", "end-1")
    assert periods[1]["instant_period_key"] == ("i", "end-1")
    assert periods[1]["matches_document_period_end_date"] is False
    assert all(item["document_period_end_date_cross_checked"] is True for item in periods)


def test_multi_period_projection_projects_distinct_fy_periods() -> None:
    sidecar_records = [
        _record("rf-revenue-old", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-1", end="end-1"),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", end="end-1", instant=True),
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-2", end="end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-revenue-old", "90"),
        _value("rf-assets-old", "180"),
        _value("rf-revenue-fy", "100"),
        _value("rf-assets-fy", "200"),
        _value("rf-period-end", "end-2"),
    ]

    result = canonical.project_issuer_canonical_facts_by_periods(
        companyfacts=_companyfacts_periods(
            [
                ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
                ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
                ("us-gaap", "Assets", "180", "USD", "", "end-1", True),
                ("us-gaap", "Assets", "200", "USD", "", "end-2", True),
            ]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
        sidecar_receipt_id="sidecar-ref",
        sidecar_receipt_hash="sidecar-hash",
        value_store_hash=stable_hash(value_records),
        dataset_version_id="dataset-ref",
        period_limit=2,
    )
    latest = result["periods"][0]["projection"]
    comparative = result["periods"][1]["projection"]

    assert result["status"] == "canonical_multi_period_projection_ready"
    assert result["period_count"] == 2
    assert result["ready_period_count"] == 2
    assert result["defined_cell_count"] == 44
    assert result["periods"][0]["matches_document_period_end_date"] is True
    assert result["periods"][1]["matches_document_period_end_date"] is False
    assert _find(latest["concepts"], "Revenue", "total")["_value"] == Decimal("100")
    assert _find(latest["concepts"], "Revenue", "total")["status"] == "projected_oracle_confirmed"
    assert _find(comparative["concepts"], "Revenue", "total")["_value"] == Decimal("90")
    assert _find(comparative["concepts"], "Revenue", "total")["status"] == "projected_oracle_confirmed"
    assert _find(comparative["concepts"], "Revenue", "total")["resolved_fact_id"] == "rf-revenue-old"


def test_projection_handles_total_parent_fallback_and_divided_units() -> None:
    sidecar_records = [
        _record("rf-equity-parent", "us-gaap", "StockholdersEquity", "USD", end="end-2", instant=True),
        _record("rf-eps-basic", "us-gaap", "EarningsPerShareBasic", "USD/shares", end="end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-equity-parent", "75"),
        _value("rf-eps-basic", "2.50"),
        _value("rf-assets-fy", "100"),
    ]

    result = _project(
        companyfacts=_companyfacts(
            [
                ("us-gaap", "StockholdersEquity", "75", "USD"),
                ("us-gaap", "EarningsPerShareBasic", "2.50", "USD/shares"),
            ]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    equity_total = next(
        item
        for item in result["concepts"]
        if item["canonical_id"] == "Equity" and item["requested_basis"] == "total"
    )
    eps = _find(result["concepts"], "EpsBasic", "total")

    assert equity_total["basis"] == "parent"
    assert equity_total["mapping_method"] == "basis_fallback_total_to_parent"
    assert equity_total["status"] == "projected_oracle_confirmed"
    assert eps["unit_class"] == "divided_unit"
    assert eps["status"] == "projected_oracle_confirmed"


def test_projection_keeps_oracle_absent_as_coverage_gain() -> None:
    sidecar_records = [
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", instant=True),
    ]
    value_records = [_value("rf-revenue-fy", "100"), _value("rf-assets-fy", "200")]

    result = _project(companyfacts={}, sidecar_records=sidecar_records, value_records=value_records)
    revenue = _find(result["concepts"], "Revenue", "total")

    assert revenue["status"] == "projected_oracle_absent"
    assert revenue["oracle_confirmed"] == "oracle_absent"
    assert result["oracle_absent_count"] >= 1
    assert result["oracle_confirmed_rate_excluding_absent"] is None


def test_projection_blocks_when_projected_fact_lacks_resolved_fact_id() -> None:
    sidecar_records = [
        _record(None, "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", instant=True),
    ]
    value_records = [_value("rf-assets-fy", "200")]

    result = _project(
        companyfacts=_companyfacts(
            [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD")]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )

    assert result["status"] == "canonical_projection_blocked"
    assert any(
        item["reason"] == "canonical_projection_resolved_fact_id_missing"
        for item in result["blocking_reasons"]
    )


def test_projection_report_redacts_values_and_authority_ids(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    sidecar_records = [
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", instant=True),
    ]
    value_records = [_value("rf-revenue-fy", "4321"), _value("rf-assets-fy", "8765")]
    report = diagnostic.build_report(
        source_root=_source_root(tmp_path),
        issuer_bundles=[
            _bundle(
                issuer_ref="raw-fixture-issuer",
                companyfacts=_companyfacts(
                    [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "4321", "USD")]
                ),
                sidecar_records=sidecar_records,
                value_records=value_records,
            )
        ],
    )
    text = json.dumps(report, sort_keys=True)

    assert report["decision"] == "canonical_projection_validate_only_ready"
    assert report["redaction"]["passed"] is True
    assert "raw-fixture-issuer" not in text
    assert "rf-revenue-fy" not in text
    assert "sidecar-ref" not in text
    assert "4321" not in text
    assert "relative_magnitude" not in text
    assert "residual_abs" not in text


def test_projection_uses_sidecar_primary_taxonomy_not_companyfacts_presence() -> None:
    sidecar_records = [
        _record("rf-ifrs-revenue", "ifrs-full", "Revenue", "USD"),
        _record("rf-ifrs-gross-profit", "ifrs-full", "GrossProfit", "USD"),
        _record("rf-us-revenue", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        _record("rf-assets-fy", "ifrs-full", "Assets", "USD", instant=True),
    ]
    value_records = [
        _value("rf-ifrs-revenue", "100"),
        _value("rf-ifrs-gross-profit", "60"),
        _value("rf-us-revenue", "999"),
        _value("rf-assets-fy", "200"),
    ]

    result = _project(
        companyfacts=_companyfacts(
            [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "999", "USD")]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    revenue = _find(result["concepts"], "Revenue", "total")

    assert result["primary_taxonomy"] == "ifrs-full"
    assert revenue["source_qname"] == "ifrs-full:Revenue"
    assert revenue["oracle_confirmed"] == "oracle_absent"


def test_projection_derived_noncurrent_assets_confirms_when_target_oracle_matches() -> None:
    sidecar_records = [
        _record("rf-assets", "us-gaap", "Assets", "USD", instant=True),
        _record("rf-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
    ]
    value_records = [_value("rf-assets", "100"), _value("rf-current-assets", "40")]

    result = _project(
        companyfacts=_companyfacts(
            [
                ("us-gaap", "Assets", "100", "USD", True),
                ("us-gaap", "AssetsCurrent", "40", "USD", True),
                ("us-gaap", "AssetsNoncurrent", "60", "USD", True),
            ]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    noncurrent = _find(result["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "derived"
    assert noncurrent["oracle_confirmed"] is True
    assert result["oracle_confirmed_count"] == 3


def test_projection_derived_noncurrent_assets_is_unconfirmed_when_target_oracle_differs() -> None:
    sidecar_records = [
        _record("rf-assets", "us-gaap", "Assets", "USD", instant=True),
        _record("rf-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
    ]
    value_records = [_value("rf-assets", "100"), _value("rf-current-assets", "40")]

    result = _project(
        companyfacts=_companyfacts(
            [
                ("us-gaap", "Assets", "100", "USD", True),
                ("us-gaap", "AssetsCurrent", "40", "USD", True),
                ("us-gaap", "AssetsNoncurrent", "61", "USD", True),
            ]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    noncurrent = _find(result["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "derived"
    assert noncurrent["oracle_confirmed"] is False
    assert result["projected_unconfirmed_count"] == 1


def test_projection_keeps_sector_families_opt_in_and_universal_by_default() -> None:
    sidecar_records = [
        _record("rf-interest-expense", "us-gaap", "InterestExpense", "USD"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", instant=True),
    ]
    value_records = [
        _value("rf-interest-expense", "12"),
        _value("rf-assets-fy", "200"),
    ]

    result = _project(
        companyfacts={},
        sidecar_records=sidecar_records,
        value_records=value_records,
    )

    assert result["defined_count"] == 22
    assert result["universal_defined_count"] == 22
    assert result["sector_family_defined_count"] == 0
    assert result["sector_family_presence"]["activation_rule"] == "sector_families_not_requested"
    assert all(item["family"] == "universal" for item in result["concepts"])


def test_projection_supporting_banking_concept_does_not_activate_sector_family() -> None:
    sidecar_records = [
        _record("rf-interest-expense", "us-gaap", "InterestExpense", "USD"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", instant=True),
    ]
    value_records = [
        _value("rf-interest-expense", "12"),
        _value("rf-assets-fy", "200"),
    ]

    result = _project(
        companyfacts={},
        sidecar_records=sidecar_records,
        value_records=value_records,
        include_sector_families=True,
    )
    banking = next(
        item
        for item in result["sector_family_presence"]["reported_family_evidence"]
        if item["family_id"] == "banking"
    )

    assert result["sector_family_defined_count"] == 0
    assert result["sector_family_presence"]["present_family_ids"] == []
    assert banking["activation_anchor_concepts"] == []
    assert banking["supporting_family_concepts"] == ["us-gaap:InterestExpense"]
    assert banking["supporting_only"] is True
    assert all(item["family"] == "universal" for item in result["concepts"])


def test_projection_anchor_activates_banking_family_and_supporting_concepts() -> None:
    sidecar_records = [
        _record("rf-loan-commitments", "ifrs-full", "GrossLoanCommitments", "USD", instant=True),
        _record("rf-interest-expense", "us-gaap", "InterestExpense", "USD"),
        _record("rf-assets-fy", "ifrs-full", "Assets", "USD", instant=True),
    ]
    value_records = [
        _value("rf-loan-commitments", "900"),
        _value("rf-interest-expense", "12"),
        _value("rf-assets-fy", "200"),
    ]

    result = _project(
        companyfacts={},
        sidecar_records=sidecar_records,
        value_records=value_records,
        include_sector_families=True,
    )
    gross_loan_commitments = _find(result["concepts"], "BankingGrossLoanCommitments", "total")
    interest_expense = _find(result["concepts"], "BankingInterestExpense", "total")

    assert result["sector_family_defined_count"] == 6
    assert result["sector_family_presence"]["present_family_ids"] == ["banking"]
    assert gross_loan_commitments["family"] == "banking"
    assert gross_loan_commitments["status"] == "projected_oracle_absent"
    assert gross_loan_commitments["resolved_fact_id"] == "rf-loan-commitments"
    assert interest_expense["family"] == "banking"
    assert interest_expense["status"] == "projected_oracle_absent"
    assert interest_expense["resolved_fact_id"] == "rf-interest-expense"


def test_projection_report_separates_registry_count_from_active_sector_family_count() -> None:
    sidecar_records = [
        _record("rf-loan-commitments", "ifrs-full", "GrossLoanCommitments", "USD", instant=True),
        _record("rf-interest-expense", "us-gaap", "InterestExpense", "USD"),
        _record("rf-assets-fy", "ifrs-full", "Assets", "USD", instant=True),
    ]
    value_records = [
        _value("rf-loan-commitments", "900"),
        _value("rf-interest-expense", "12"),
        _value("rf-assets-fy", "200"),
    ]

    report = canonical.build_redacted_projection_report(
        issuer_bundles=[
            _bundle(
                issuer_ref="raw-fixture-issuer",
                companyfacts={},
                sidecar_records=sidecar_records,
                value_records=value_records,
            )
        ],
        include_sector_families=True,
    )
    issuer = report["per_issuer"][0]

    assert report["decision"] == "canonical_projection_validate_only_ready"
    assert report["include_sector_families"] is True
    assert report["canonical_concept_defined_count"] == 35
    assert report["universal_canonical_concept_defined_count"] == 22
    assert report["sector_family_canonical_concept_defined_count"] == 13
    assert report["issuer_hash_count"] == 1
    assert issuer["issuer_hash"] == stable_hash({"issuer_ref": "raw-fixture-issuer"})[:24]
    assert len(report["canonical_concepts"]) == 35
    assert issuer["headline_canonical_defined"] == 28
    assert issuer["universal_defined_count"] == 22
    assert issuer["sector_family_defined_count"] == 6
    assert report["summary"]["headline_canonical_cell_count"] == 28


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


def _project(
    *,
    companyfacts: dict,
    sidecar_records: list[dict],
    value_records: list[dict],
    include_sector_families: bool = False,
) -> dict:
    return canonical.project_issuer_canonical_facts(
        companyfacts=companyfacts,
        sidecar_records=sidecar_records,
        value_records=value_records,
        sidecar_receipt_id="sidecar-ref",
        sidecar_receipt_hash="sidecar-hash",
        value_store_hash=stable_hash(value_records),
        dataset_version_id="dataset-ref",
        fiscal_year=1,
        include_sector_families=include_sector_families,
    )


def _bundle(
    *,
    issuer_ref: str,
    companyfacts: dict,
    sidecar_records: list[dict],
    value_records: list[dict],
) -> dict:
    return {
        "issuer_ref": issuer_ref,
        "companyfacts": companyfacts,
        "sidecar_records": sidecar_records,
        "value_records": value_records,
        "sidecar_receipt_id": "sidecar-ref",
        "sidecar_receipt_hash": "sidecar-hash",
        "value_store_hash": stable_hash(value_records),
        "dataset_version_id": "dataset-ref",
    }


def _companyfacts(
    entries: list[tuple[str, str, str, str] | tuple[str, str, str, str, bool]]
) -> dict:
    facts: dict[str, dict] = {}
    instant_names = {
        "Assets",
        "AssetsCurrent",
        "AssetsNoncurrent",
        "Liabilities",
        "LiabilitiesCurrent",
        "LiabilitiesNoncurrent",
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    }
    for entry in entries:
        if len(entry) == 5:
            taxonomy, local_name, value, unit, instant = entry
        else:
            taxonomy, local_name, value, unit = entry
            instant = local_name in instant_names
        facts.setdefault(taxonomy, {}).setdefault(local_name, {"units": {}})
        fact = {"fp": "FY", "fy": 1, "val": value, "end": "end-2"}
        if not instant:
            fact["start"] = "start-2"
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _companyfacts_periods(entries: list[tuple[str, str, str, str, str, str, bool]]) -> dict:
    facts: dict[str, dict] = {}
    for taxonomy, local_name, value, unit, start, end, instant in entries:
        facts.setdefault(taxonomy, {}).setdefault(local_name, {"units": {}})
        fact = {"fp": "FY", "fy": "", "val": value, "end": end}
        if not instant:
            fact["start"] = start
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _record(
    fact_id: str | None,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    start: str = "start-2",
    end: str = "end-2",
    instant: bool = False,
) -> dict:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    record = {
        "concept": {
            "namespace": _namespace(taxonomy),
            "local_name": local_name,
            "standard": True,
        },
        "unit": _unit(unit_name),
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }
    if fact_id is not None:
        record["resolved_fact_id"] = fact_id
    return record


def _value(fact_id: str, effective_value: str) -> dict:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _namespace(taxonomy: str) -> str:
    if taxonomy == "ifrs-full":
        return "xbrl.ifrs.org/test"
    if taxonomy == "dei":
        return "xbrl.sec.gov/dei/test"
    return "fasb.org/us-gaap/test"


def _unit(unit_name: str) -> dict:
    if unit_name == "USD/shares":
        return {
            "currency": "iso4217:USD",
            "measures": ["iso4217:USD"],
            "numerator": ["iso4217:USD"],
            "denominator": ["xbrli:shares"],
        }
    if unit_name == "unitless":
        return {"measures": []}
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}


def _find(items: list[dict], canonical_id: str, basis: str) -> dict:
    return next(item for item in items if item["canonical_id"] == canonical_id and item["basis"] == basis)
