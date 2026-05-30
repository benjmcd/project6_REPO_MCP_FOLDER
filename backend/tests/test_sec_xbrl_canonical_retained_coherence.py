from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from app.services import layer3_sec_edgar_html_inline_xbrl_fact_material_bridge as material_bridge
from app.services import layer3_sec_xbrl_canonical_retained_coherence as coherence


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-retained-coherence.py"
REPORT_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-retained-coherence-report.json"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_canonical_retained_coherence", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_direct_projection_binds_to_retained_view_by_id_qname_and_value_record() -> None:
    result = coherence.reconcile_canonical_projection_to_retained_view(
        projection_items=[
            _projected("Revenue", "rf-revenue", "ifrs-full:Revenue"),
            _projected("TotalAssets", "rf-assets", "ifrs-full:Assets"),
        ],
        retained_view_records=[
            _retained("rf-revenue", "ifrs-full:Revenue"),
            _retained("rf-assets", "ifrs-full:Assets"),
            _retained("rf-segment", "ifrs-full:Revenue", dimensional=True),
            _retained("rf-extension", "issuer:CustomMetric", extension=True),
        ],
    )

    assert result["contract_passed"] is True
    assert result["normalized_fact_count"] == 2
    assert result["bound_count"] == 2
    assert result["missing_count"] == 0
    assert result["qname_consistent_count"] == 2
    assert result["value_reconciled_count"] == 2
    assert result["contract_b_subset_of_a"] is True
    assert result["contract_a_strict_superset"] is True


def test_missing_retained_fact_fails_closed_without_hiding_breach() -> None:
    result = coherence.reconcile_canonical_projection_to_retained_view(
        projection_items=[_projected("Revenue", "rf-missing", "ifrs-full:Revenue")],
        retained_view_records=[
            _retained("rf-segment", "ifrs-full:Revenue", dimensional=True),
            _retained("rf-extension", "issuer:CustomMetric", extension=True),
        ],
    )

    assert result["contract_passed"] is False
    assert result["contract_b_subset_of_a"] is False
    assert result["normalized_fact_count"] == 1
    assert result["missing_count"] == 1
    assert result["bound_count"] == 0


def test_qname_mismatch_and_duplicate_value_authority_fail_contract() -> None:
    result = coherence.reconcile_canonical_projection_to_retained_view(
        projection_items=[_projected("Revenue", "rf-revenue", "ifrs-full:Revenue")],
        retained_view_records=[
            _retained("rf-revenue", "ifrs-full:OtherRevenue"),
            _retained("rf-revenue", "ifrs-full:Revenue"),
            _retained("rf-segment", "ifrs-full:Revenue", dimensional=True),
            _retained("rf-extension", "issuer:CustomMetric", extension=True),
        ],
    )

    assert result["contract_passed"] is False
    assert result["contract_qname_consistent"] is False
    assert result["contract_value_single_authority"] is False
    assert result["qname_consistent_count"] == 0
    assert result["duplicate_value_authority_count"] == 1


def test_retained_view_must_be_strict_superset_with_dimensional_and_extension_facts() -> None:
    result = coherence.reconcile_canonical_projection_to_retained_view(
        projection_items=[_projected("Revenue", "rf-revenue", "ifrs-full:Revenue")],
        retained_view_records=[_retained("rf-revenue", "ifrs-full:Revenue")],
    )

    assert result["contract_b_subset_of_a"] is True
    assert result["contract_a_strict_superset"] is False
    assert result["retains_dimensional"] is False
    assert result["retains_extension"] is False
    assert result["contract_passed"] is False


def test_derived_noncurrent_assets_bind_both_input_ids() -> None:
    result = coherence.reconcile_canonical_projection_to_retained_view(
        projection_items=[
            _projected("TotalAssets", "rf-assets", "us-gaap:Assets"),
            _projected("CurrentAssets", "rf-current-assets", "us-gaap:AssetsCurrent"),
            {
                "canonical_id": "NoncurrentAssets",
                "basis": "total",
                "status": "derived",
                "source_qname": None,
                "derived_from_resolved_fact_ids": ["rf-assets", "rf-current-assets"],
            },
        ],
        retained_view_records=[
            _retained("rf-assets", "us-gaap:Assets"),
            _retained("rf-current-assets", "us-gaap:AssetsCurrent"),
            _retained("rf-segment", "us-gaap:Assets", dimensional=True),
            _retained("rf-extension", "issuer:CustomMetric", extension=True),
        ],
    )

    assert result["contract_passed"] is True
    assert result["normalized_fact_count"] == 4
    assert result["bound_count"] == 4
    assert result["qname_consistent_count"] == 4
    assert result["value_reconciled_count"] == 4


def test_public_retained_view_accessor_returns_statement_classifier_shape() -> None:
    retained = material_bridge.retained_fact_view_from_sidecar_records(
        [
            {
                "resolved_fact_id": "rf-revenue",
                "source_order": 7,
                "concept": {
                    "qname": "ifrs-full:Revenue",
                    "namespace": "xbrl.ifrs.org/test",
                    "local_name": "Revenue",
                    "standard": True,
                    "extension": False,
                },
                "dimensions": {
                    "explicit": [
                        {
                            "axis": {"qname": "ifrs-full:SegmentsAxis"},
                            "member": {"qname": "issuer:SegmentMember"},
                        }
                    ],
                    "typed": [],
                },
            }
        ]
    )

    assert len(retained) == 1
    assert retained[0]["fact_id_or_order_key"] == "rf-revenue"
    assert retained[0]["qualified_name"] == "ifrs-full:Revenue"
    assert retained[0]["marker_order_index"] == 7
    assert retained[0]["dimensions"] == {
        "explicit": [
            {
                "axis": {"qname": "ifrs-full:SegmentsAxis"},
                "member": {"qname": "issuer:SegmentMember"},
            }
        ],
        "typed": [],
    }


def test_diagnostic_report_is_redacted_sector_aggregate_only(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    report = diagnostic.build_report(source_root=_source_root(tmp_path))
    text = json.dumps(report, sort_keys=True)

    assert report["decision"] == "canonical_retained_coherence_validate_only_ready"
    assert report["summary"]["contract_passed"] is True
    assert report["summary"]["total_missing"] == 0
    assert set(report) >= {"per_sector_class", "summary", "redaction"}
    assert "per_issuer" not in report
    assert not re.search(r'"(?:retained_fact_count|total_fact_count)"', text)
    assert "rf-" not in text
    assert "issuer_ref" not in text
    assert "issuer_hash" not in text
    assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    assert ":/" + "/" not in text
    assert "C:" + "\\" not in text
    assert report["redaction"]["passed"] is True


def test_committed_report_is_redacted_sector_aggregate_only() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    text = json.dumps(report, sort_keys=True)

    assert report["summary"] == {
        "contract_passed": True,
        "total_bound": 66,
        "total_missing": 0,
        "total_normalized": 66,
    }
    assert len(report["per_sector_class"]) == 1
    assert report["per_sector_class"][0]["sector_class"] == "industrial_commercial"
    assert report["per_sector_class"][0]["contract_b_subset_of_a"] is True
    assert report["per_sector_class"][0]["contract_a_strict_superset"] is True
    assert "per_issuer" not in report
    assert not re.search(r'"(?:retained_fact_count|total_fact_count)"', text)
    assert "rf-" not in text
    assert "issuer_ref" not in text
    assert "issuer_hash" not in text
    assert report["redaction"]["passed"] is True


def _projected(canonical_id: str, fact_id: str, source_qname: str) -> dict:
    return {
        "canonical_id": canonical_id,
        "basis": "total",
        "status": "projected_oracle_confirmed",
        "source_qname": source_qname,
        "resolved_fact_id": fact_id,
    }


def _retained(
    fact_id: str,
    qualified_name: str,
    *,
    dimensional: bool = False,
    extension: bool = False,
) -> dict:
    dimensions = {
        "explicit": [
            {
                "axis": {"qname": "ifrs-full:SegmentsAxis"},
                "member": {"qname": "issuer:SegmentMember"},
            }
        ]
        if dimensional
        else [],
        "typed": [],
    }
    return {
        "fact_id_or_order_key": fact_id,
        "qualified_name": qualified_name,
        "dimensions": dimensions,
        "concept_extension": extension,
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
