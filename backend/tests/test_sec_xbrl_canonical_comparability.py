from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from app.services import layer3_sec_xbrl_canonical_concepts as canonical


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-comparability.py"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_canonical_comparability", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_canonical_registry_is_statement_organized_and_bounded() -> None:
    inventory = canonical.canonical_concept_inventory()

    assert len(inventory) == 22
    assert {item["statement"] for item in inventory} == {"income", "balance", "cashflow"}
    assert any(item["canonical_id"] == "Revenue" and item["basis"] == "total" for item in inventory)
    assert any(item["canonical_id"] == "Equity" and item["basis"] == "parent" for item in inventory)


def test_reference_summary_taxonomy_mix_matches_primary_taxonomy_logic(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    report = diagnostic.build_report(source_root=_source_root(tmp_path))
    taxonomies = [item["primary_taxonomy"] for item in report["per_issuer"]]

    assert taxonomies.count("ifrs-full") >= 2
    assert taxonomies.count("us-gaap") == 1
    assert canonical.primary_taxonomy_from_records(
        [
            _record("ifrs-majority-1", "ifrs-full", "Revenue", "USD"),
            _record("ifrs-majority-2", "ifrs-full", "GrossProfit", "USD"),
            _record("us-minority-1", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        ]
    ) == "ifrs-full"
    assert canonical.primary_taxonomy_from_records(
        [
            _record("us-majority-1", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
            _record("us-majority-2", "us-gaap", "GrossProfit", "USD"),
            _record("ifrs-minority-1", "ifrs-full", "Revenue", "USD"),
        ]
    ) == "us-gaap"


def test_canonical_resolution_prefers_primary_taxonomy() -> None:
    companyfacts = _companyfacts(
        [
            ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "111", "USD"),
            ("ifrs-full", "Revenue", "222", "USD"),
        ]
    )
    sidecar_records = [
        _record("ifrs-count-1", "ifrs-full", "Revenue", "USD"),
        _record("ifrs-count-2", "ifrs-full", "GrossProfit", "USD"),
        _record("us-count-1", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        _record("fact-revenue", "ifrs-full", "Revenue", "USD"),
    ]
    value_records = [{"resolved_fact_id": "fact-revenue", "effective_value": "222"}]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts=companyfacts,
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    revenue = _find(resolved["concepts"], "Revenue", "total")

    assert resolved["primary_taxonomy"] == "ifrs-full"
    assert revenue["source_qname"] == "ifrs-full:Revenue"
    assert revenue["inline_confirmed"] is True


def test_canonical_resolution_scopes_to_fy_period() -> None:
    companyfacts = {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {"fp": "Q1", "fy": 1, "val": "999", "start": "q-start", "end": "q-end"},
                        {"fp": "FY", "fy": 0, "val": "888", "start": "old-start", "end": "old-end"},
                        {"fp": "FY", "fy": 1, "val": "100", "start": "fy-start", "end": "fy-end"},
                    ]
                }
            }
        }
    }
    sidecar_records = [
        _record(
            "fact-revenue",
            "us-gaap",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            start="fy-start",
            end="fy-end",
        )
    ]
    value_records = [{"resolved_fact_id": "fact-revenue", "effective_value": "100"}]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts=companyfacts,
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    revenue = _find(resolved["concepts"], "Revenue", "total")

    assert revenue["status"] == "resolved_inline_confirmed"
    assert revenue["period_class"] == "FY"


def test_canonical_resolution_marks_total_to_parent_basis_fallback() -> None:
    companyfacts = _companyfacts([("us-gaap", "StockholdersEquity", "75", "USD")])
    sidecar_records = [_record("fact-equity", "us-gaap", "StockholdersEquity", "USD", instant=True)]
    value_records = [{"resolved_fact_id": "fact-equity", "effective_value": "75"}]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts=companyfacts,
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    equity_total = next(
        item
        for item in resolved["concepts"]
        if item["canonical_id"] == "Equity" and item["requested_basis"] == "total"
    )

    assert equity_total["basis"] == "parent"
    assert equity_total["mapping_method"] == "basis_fallback_total_to_parent"
    assert equity_total["inline_confirmed"] is True


def test_canonical_resolution_preserves_legitimately_absent_cells() -> None:
    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts={},
        sidecar_records=[],
        value_records=[],
        fiscal_year=1,
    )
    liabilities = _find(resolved["concepts"], "TotalLiabilities", "total")

    assert liabilities["status"] == "legitimately_absent"
    assert liabilities["absence_reason"] == "no_reviewed_fy_source_fact"
    assert resolved["legitimately_absent_count"] == 22


def test_canonical_resolution_supports_divided_units() -> None:
    companyfacts = _companyfacts([("us-gaap", "EarningsPerShareBasic", "2.50", "USD/shares")])
    sidecar_records = [_record("fact-eps", "us-gaap", "EarningsPerShareBasic", "USD/shares")]
    value_records = [{"resolved_fact_id": "fact-eps", "effective_value": "2.50"}]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts=companyfacts,
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    eps = _find(resolved["concepts"], "EpsBasic", "total")

    assert eps["status"] == "resolved_inline_confirmed"
    assert eps["unit_class"] == "divided_unit"


def test_comparability_report_excludes_derived_facts_from_inline_confirmed_counts() -> None:
    report = canonical.build_redacted_comparability_report(
        issuer_bundles=[
            {
                "issuer_ref": "fixture-issuer",
                "companyfacts": _companyfacts(
                    [
                        ("us-gaap", "Assets", "100", "USD", True),
                        ("us-gaap", "AssetsCurrent", "40", "USD", True),
                    ]
                ),
                "sidecar_records": [
                    _record("fact-assets", "us-gaap", "Assets", "USD", instant=True),
                    _record("fact-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
                ],
                "value_records": [
                    {"resolved_fact_id": "fact-assets", "effective_value": "100"},
                    {"resolved_fact_id": "fact-current-assets", "effective_value": "40"},
                ],
            }
        ],
        fiscal_year=1,
    )
    issuer = report["per_issuer"][0]
    noncurrent = _find(issuer["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "derived"
    assert noncurrent["inline_confirmed"] is False
    assert noncurrent["derived_inputs_inline_confirmed"] is True
    assert issuer["headline_canonical_inline_confirmed"] == 2
    assert report["summary"]["headline_canonical_inline_confirmed_count"] == 2


def test_canonical_report_redacts_identity_and_preserves_residuals(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    source_root = _source_root(tmp_path)
    report = diagnostic.build_report(
        source_root=source_root,
        issuer_bundles=[
            {
                "issuer_ref": "raw-fixture-issuer",
                "companyfacts": _companyfacts(
                    [
                        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD"),
                        ("us-gaap", "CostOfGoodsAndServicesSold", "40", "USD"),
                        ("us-gaap", "GrossProfit", "60", "USD"),
                        ("us-gaap", "AssetsCurrent", "70", "USD"),
                        ("us-gaap", "AssetsNoncurrent", "30", "USD"),
                        ("us-gaap", "Assets", "100", "USD"),
                    ]
                ),
                "sidecar_records": [
                    _record("fact-revenue", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
                    _record("fact-cost", "us-gaap", "CostOfGoodsAndServicesSold", "USD"),
                    _record("fact-gross", "us-gaap", "GrossProfit", "USD"),
                    _record("fact-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
                    _record("fact-noncurrent-assets", "us-gaap", "AssetsNoncurrent", "USD", instant=True),
                    _record("fact-assets", "us-gaap", "Assets", "USD", instant=True),
                ],
                "value_records": [
                    {"resolved_fact_id": "fact-revenue", "effective_value": "100"},
                    {"resolved_fact_id": "fact-cost", "effective_value": "40"},
                    {"resolved_fact_id": "fact-gross", "effective_value": "60"},
                    {"resolved_fact_id": "fact-current-assets", "effective_value": "70"},
                    {"resolved_fact_id": "fact-noncurrent-assets", "effective_value": "30"},
                    {"resolved_fact_id": "fact-assets", "effective_value": "100"},
                ],
            }
        ],
        fiscal_year=1,
    )
    text = json.dumps(report, sort_keys=True)
    identities = report["per_issuer"][0]["statement_identity_residuals"]

    assert report["decision"] == "canonical_comparability_validate_only_ready"
    assert any(
        item["identity_id"] == "current_assets_plus_noncurrent_assets_equals_total_assets"
        and item["within_tolerance"] is True
        for item in identities
    )
    assert any(
        item["identity_id"] == "revenue_minus_cost_of_sales_equals_gross_profit"
        and item["within_tolerance"] is True
        for item in identities
    )
    assert "raw-fixture-issuer" not in text
    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    assert ":/" + "/" not in text
    assert "C:" + "\\" not in text
    assert report["redaction"]["passed"] is True


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
        fact = {"fp": "FY", "fy": 1, "val": value, "end": "fy-end"}
        if not instant:
            fact["start"] = "fy-start"
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    start: str = "fy-start",
    end: str = "fy-end",
    instant: bool = False,
) -> dict:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    return {
        "resolved_fact_id": fact_id,
        "concept": {
            "namespace": _namespace(taxonomy),
            "local_name": local_name,
            "standard": True,
        },
        "unit": _unit(unit_name),
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _namespace(taxonomy: str) -> str:
    if taxonomy == "ifrs-full":
        return "xbrl.ifrs.org/test"
    return "fasb.org/us-gaap/test"


def _unit(unit_name: str) -> dict:
    if unit_name == "USD/shares":
        return {
            "currency": "iso4217:USD",
            "measures": ["iso4217:USD"],
            "numerator": ["iso4217:USD"],
            "denominator": ["xbrli:shares"],
        }
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}


def _find(items: list[dict], canonical_id: str, basis: str) -> dict:
    return next(item for item in items if item["canonical_id"] == canonical_id and item["basis"] == basis)
