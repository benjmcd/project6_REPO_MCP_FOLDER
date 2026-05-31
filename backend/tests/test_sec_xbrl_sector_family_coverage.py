from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-sector-family-coverage.py"
REPORT_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-sector-family-coverage-report.json"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_sector_family_coverage", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sic_range_to_sector_class_mapping() -> None:
    diagnostic = _diagnostic_module()

    assert diagnostic.sector_class_from_sic("1000") == "extractive"
    assert diagnostic.sector_class_from_sic("1499") == "extractive"
    assert diagnostic.sector_class_from_sic("6000") == "banking"
    assert diagnostic.sector_class_from_sic("6199") == "banking"
    assert diagnostic.sector_class_from_sic("6300") == "insurance"
    assert diagnostic.sector_class_from_sic("6411") == "insurance"
    assert diagnostic.sector_class_from_sic("6500") == "real_estate_reit"
    assert diagnostic.sector_class_from_sic("6599") == "real_estate_reit"
    assert diagnostic.sector_class_from_sic("3651") == "diversified_or_other"
    assert diagnostic.sector_class_from_sic("not-a-sic") == "diversified_or_other"
    assert diagnostic.sector_class_from_sic(None) == "diversified_or_other"


def test_diversified_filer_guard_uses_concept_presence_not_primary_sic_gate() -> None:
    diagnostic = _diagnostic_module()

    result = diagnostic.classify_sector_family_presence(
        primary_sic="3651",
        reported_concepts=[
            "ifrs-full:InsuranceRevenue",
            "ifrs-full:InsuranceContractsLiabilityAsset",
            "ifrs-full:InterestIncomeForFinancialAssetsMeasuredAtAmortisedCost",
            "ifrs-full:GrossLoanCommitments",
            "ifrs-full:CurrentDepositsFromCustomers",
        ],
    )

    assert result["sector_class"] == "diversified_or_other"
    assert result["sic_used_as_gate"] is False
    assert result["presence_conditioned"] is True
    assert result["activation_rule"] == "anchor_concepts_activate_supporting_concepts_do_not"
    assert set(result["present_family_ids"]) == {"banking", "insurance"}
    assert result["present_family_count"] == 2


def test_supporting_banking_concept_does_not_activate_family_by_itself() -> None:
    diagnostic = _diagnostic_module()

    result = diagnostic.classify_sector_family_presence(
        primary_sic="3651",
        reported_concepts=["us-gaap:InterestExpense"],
    )
    banking = next(
        item for item in result["reported_family_evidence"] if item["family_id"] == "banking"
    )

    assert result["present_family_ids"] == []
    assert result["present_family_count"] == 0
    assert banking["activation_anchor_concepts"] == []
    assert banking["supporting_family_concepts"] == ["us-gaap:InterestExpense"]
    assert banking["supporting_only"] is True


def test_build_report_defaults_to_reference_evidence(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()

    report = diagnostic.build_report(source_root=_source_root(tmp_path))

    assert report["decision"] == "sector_family_coverage_validate_only_ready"
    assert report["sector_conditioning"] == "concept_presence_not_sic_gated"
    assert report["summary"]["families_defined"] == 3
    assert report["summary"]["total_headline_concepts_defined"] == 13
    assert report["summary"]["total_reference_present_count"] == 7
    assert report["summary"]["universal_only_reference_issuer_count"] == 1
    guard = report["diversified_filer_guard"]
    assert guard["presence_conditioned"] is True
    assert guard["sector_class"] == "diversified_or_other"
    assert guard["sic_used_as_gate"] is False
    assert guard["activation_rule"] == "anchor_concepts_activate_supporting_concepts_do_not"
    assert set(guard["present_family_ids"]) == {"banking", "insurance"}
    assert guard["present_family_count"] == 2
    assert all(item["activation_anchor_count"] >= 1 for item in report["per_family"])
    assert report["per_family"][1]["supporting_concept_count"] == 2
    assert any(
        item["criterion"] == "family_activation_requires_anchor_not_support_only"
        and item["state"] == "passed"
        for item in report["criteria"]
    )
    assert report["non_goals_preserved"]["sector_conditioned_families_design_complete"] is True
    assert report["non_goals_preserved"]["coverage_diagnostic_sector_resolution_performed"] is False
    assert report["redaction"]["passed"] is True


def test_build_report_preserves_explicit_empty_family_evidence(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()

    report = diagnostic.build_report(source_root=_source_root(tmp_path), per_family=[])

    assert report["decision"] == "no_sector_family_coverage_evidence"
    assert report["per_family"] == []
    assert report["summary"]["contract_passed"] is False
    assert report["summary"]["total_headline_concepts_defined"] == 0
    assert report["blocking_reasons"]


def test_build_report_fails_closed_on_duplicate_family_evidence(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    reference = list(diagnostic.REFERENCE_FAMILY_EVIDENCE)
    duplicate_family_rows = [reference[0], reference[1], reference[1], reference[2]]

    report = diagnostic.build_report(
        source_root=_source_root(tmp_path),
        per_family=duplicate_family_rows,
    )

    assert report["decision"] == "sector_family_coverage_validate_only_blocked"
    assert report["summary"]["contract_passed"] is False
    assert any(
        item["reason"] == "sector_family_coverage_counts_inconsistent"
        for item in report["blocking_reasons"]
    )


def test_committed_report_is_redacted_family_coverage_only() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    text = json.dumps(report, sort_keys=True)

    assert report["schema_id"] == "diagnostics.sec_xbrl_sector_family_coverage.v1"
    assert report["decision"] == "sector_family_coverage_validate_only_ready"
    assert report["next_slice"] == "sec_xbrl_sector_conditioned_canonical_families_v1_resolution_presence_conditioned"
    assert report["summary"]["families_defined"] == 3
    assert report["summary"]["total_headline_concepts_defined"] == 13
    assert report["summary"]["total_reference_present_count"] == 7
    assert {item["family_id"] for item in report["per_family"]} == {"extractive", "banking", "insurance"}
    assert report["redaction"]["raw_sic_found"] is False
    assert report["redaction"]["raw_issuer_identity_found"] is False
    assert report["redaction"]["raw_value_found"] is False
    assert report["redaction"]["raw_path_or_accession_found"] is False
    assert report["redaction"]["passed"] is True
    assert "issuer_ref" not in text
    assert "issuer_hash" not in text
    assert "issuer_name" not in text
    assert not re.search(r"\b[0-9]{10}-[0-9]{2}-[0-9]{6}\b", text)
    assert '"value"' not in text
    assert '"period"' not in text
    assert "resolved_fact_id" not in text
    assert "3651" not in text
    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    assert ":/" + "/" not in text
    assert "C:" + "\\" not in text


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
