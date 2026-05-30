from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
import re
from pathlib import Path

from app.services import layer3_sec_xbrl_statement_assembly as assembly


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-statement-assembly.py"
REPORT_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-statement-assembly-report.json"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_statement_assembly", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_assembly_groups_projection_rows_into_reviewable_statement_packets() -> None:
    result = assembly.assemble_reviewable_statement_packet(
        projection_items=[
            _projection("Revenue", "income", "projected_oracle_confirmed", _value=Decimal("100")),
            _projection("TotalAssets", "balance", "projected_oracle_confirmed", _value=Decimal("250")),
            _projection("OperatingCashFlow", "cashflow", "projected_oracle_confirmed", _value=Decimal("30")),
            _projection("CostOfSales", "income", "legitimately_absent"),
        ],
        organization_result=_organization(contract_passed=True, normalized=3),
        identity_residuals=[_identity("current_assets_plus_noncurrent_assets_equals_total_assets", True)],
    )

    assert result["schema_id"] == assembly.STATEMENT_ASSEMBLY_SCHEMA_ID
    assert result["status"] == "statement_assembly_ready"
    assert result["review_ready"] is True
    assert result["total_review_rows"] == 3
    assert result["provenance_complete_count"] == 3
    assert [item["statement"] for item in result["statements"]] == ["income", "balance", "cashflow"]
    assert [item["line_count"] for item in result["statements"]] == [1, 1, 1]
    assert result["statements"][0]["rows"][0]["canonical_id"] == "Revenue"
    assert result["statements"][0]["rows"][0]["value_redacted"] is True
    assert "100" not in str(result)


def test_assembly_preserves_sector_family_rows_without_enabling_defaults() -> None:
    result = assembly.assemble_reviewable_statement_packet(
        projection_items=[
            _projection(
                "BankingGrossLoanCommitments",
                "balance",
                "projected_oracle_absent",
                family="banking",
                source_qname="ifrs-full:GrossLoanCommitments",
            ),
            _projection(
                "BankingInterestExpense",
                "income",
                "projected_oracle_absent",
                family="banking",
                source_qname="us-gaap:InterestExpense",
            ),
        ],
        organization_result=_organization(contract_passed=True, normalized=2),
    )
    income = next(item for item in result["statements"] if item["statement"] == "income")
    balance = next(item for item in result["statements"] if item["statement"] == "balance")

    assert result["status"] == "statement_assembly_ready"
    assert result["review_exception_count"] == 2
    assert income["family_counts"] == {"banking": 1}
    assert balance["family_counts"] == {"banking": 1}
    assert income["rows"][0]["family"] == "banking"
    assert balance["rows"][0]["source_qname"] == "ifrs-full:GrossLoanCommitments"


def test_assembly_blocks_when_statement_organization_contract_fails() -> None:
    result = assembly.assemble_reviewable_statement_packet(
        projection_items=[_projection("Revenue", "income", "projected_oracle_confirmed")],
        organization_result=_organization(contract_passed=False, normalized=1),
    )

    assert result["status"] == "statement_assembly_blocked"
    assert result["review_ready"] is False
    assert result["blocking_reasons"] == [
        {
            "reason": "statement_organization_contract_not_passed",
            "contract_passed": False,
        }
    ]


def test_assembly_fails_closed_on_empty_projection() -> None:
    result = assembly.assemble_reviewable_statement_packet(
        projection_items=[],
        organization_result=_organization(contract_passed=True, normalized=0),
    )

    assert result["status"] == "statement_assembly_blocked"
    assert result["review_ready"] is False
    assert result["total_review_rows"] == 0
    assert result["blocking_reasons"] == [{"reason": "statement_assembly_no_projected_facts"}]


def test_assembly_blocks_unassigned_statement_without_discarding_public_reference() -> None:
    result = assembly.assemble_reviewable_statement_packet(
        projection_items=[_projection("Revenue", "not-a-statement", "projected_oracle_confirmed")],
        organization_result=_organization(contract_passed=True, normalized=1),
    )

    assert result["status"] == "statement_assembly_blocked"
    assert result["unassigned"] == [
        {
            "canonical_id": "Revenue",
            "basis": "total",
            "statement": "not-a-statement",
            "family": "universal",
        }
    ]


def test_diagnostic_report_builds_redacted_review_packet(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()

    report = diagnostic.build_report(source_root=_source_root(tmp_path))

    assert report["decision"] == "sec_xbrl_statement_assembly_validate_only_ready"
    assert report["summary"]["packet_status"] == "statement_assembly_ready"
    assert report["summary"]["review_ready"] is True
    assert report["summary"]["statement_count"] == 3
    assert report["summary"]["statements_with_rows"] == 3
    assert report["summary"]["total_review_rows"] == 5
    assert report["summary"]["review_exception_count"] == 2
    assert [item["statement"] for item in report["statements"]] == ["income", "balance", "cashflow"]
    assert report["statements"][0]["family_counts"] == {"banking": 1, "universal": 1}
    assert report["linkbase_required_for_review_packet"] is False
    assert report["redaction"]["passed"] is True
    assert any(item["criterion"] == "statement_packet_ready_fail_closed" for item in report["criteria"])


def test_diagnostic_report_fails_closed_on_explicit_empty_projection(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()

    report = diagnostic.build_report(source_root=_source_root(tmp_path), projection_items=[])

    assert report["decision"] == "no_statement_assembly_evidence"
    assert report["summary"]["packet_status"] == "statement_assembly_blocked"
    assert report["summary"]["total_review_rows"] == 0
    assert report["blocking_reasons"]


def test_committed_statement_assembly_report_is_redacted_review_packet() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    text = json.dumps(report, sort_keys=True)

    assert report["schema_id"] == "diagnostics.sec_xbrl_statement_assembly.v1"
    assert report["decision"] == "sec_xbrl_statement_assembly_validate_only_ready"
    assert report["summary"]["packet_status"] == "statement_assembly_ready"
    assert report["summary"]["total_review_rows"] == 5
    assert report["redaction"]["passed"] is True
    assert '"value"' not in text
    assert '"_value"' not in text
    assert '"effective_value"' not in text
    assert '"amount"' not in text
    assert '"resolved_fact_id"' not in text
    assert "issuer_ref" not in text
    assert "issuer_hash" not in text
    assert not re.search(r"\b[0-9]{10}-[0-9]{2}-[0-9]{6}\b", text)
    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    assert ":/" + "/" not in text
    assert "C:" + "\\" not in text


def _projection(
    canonical_id: str,
    statement: str,
    status: str,
    *,
    family: str = "universal",
    source_qname: str = "us-gaap:FixtureConcept",
    _value: Decimal | None = None,
) -> dict:
    item = {
        "canonical_id": canonical_id,
        "basis": "total",
        "requested_basis": "total",
        "statement": statement,
        "family": family,
        "status": status,
        "source_qname": source_qname,
        "period_class": "FY",
        "oracle_confirmed": True if status == "projected_oracle_confirmed" else "oracle_absent",
        "mapping_method": "fixture",
        "mapping_confidence": "fixture",
        "provenance_complete": True,
        "unit_class": "currency",
    }
    if _value is not None:
        item["_value"] = _value
    return item


def _organization(*, contract_passed: bool, normalized: int) -> dict:
    return {
        "contract_passed": contract_passed,
        "contract_b_authoritative_organization": contract_passed,
        "contract_every_fact_id_bound": contract_passed,
        "contract_derived_inputs_bound_and_corroborated": contract_passed,
        "normalized_fact_count": normalized,
        "organized_count": normalized if contract_passed else 0,
        "unjoined_count": 0 if contract_passed else normalized,
        "a_divergent_count": 0,
        "a_role_unknown_count": 0,
    }


def _identity(identity_id: str, within_tolerance: bool) -> dict:
    return {
        "identity_id": identity_id,
        "status": "evaluated",
        "within_tolerance": within_tolerance,
        "relative_magnitude": "0E+2" if within_tolerance else "1E+0",
        "residual_abs": "0" if within_tolerance else "1",
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
