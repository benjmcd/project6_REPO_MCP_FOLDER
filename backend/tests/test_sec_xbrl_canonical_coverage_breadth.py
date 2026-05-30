from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
import re
from pathlib import Path

from app.services import layer3_sec_xbrl_canonical_concepts as canonical
from app.services.layer3_utils import stable_hash


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-canonical-coverage-breadth.py"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_canonical_coverage_breadth", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolution_derives_noncurrent_assets_with_dual_input_provenance() -> None:
    sidecar_records = [
        _record("rf-assets", "us-gaap", "Assets", "USD", instant=True),
        _record("rf-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
    ]
    value_records = [_value("rf-assets", "100"), _value("rf-current-assets", "40")]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts=_companyfacts(
            [
                ("us-gaap", "Assets", "100", "USD", True),
                ("us-gaap", "AssetsCurrent", "40", "USD", True),
            ]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    noncurrent = _find(resolved["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "derived"
    assert noncurrent["mapping_method"] == "derived_total_minus_current"
    assert noncurrent["_value"] == Decimal("60")
    assert noncurrent["inline_confirmed"] is False
    assert noncurrent["derived_inputs_inline_confirmed"] is True
    assert noncurrent["derived_from_concepts"] == ["TotalAssets[total]", "CurrentAssets[total]"]
    assert noncurrent["derived_from_resolved_fact_ids"] == ["rf-assets", "rf-current-assets"]
    assert resolved["inline_confirmed_count"] == 2
    assert _identity(resolved, "current_assets_plus_noncurrent_assets_equals_total_assets")["residual_abs"] == "0"


def test_resolution_does_not_derive_noncurrent_assets_when_current_assets_absent() -> None:
    sidecar_records = [_record("rf-assets", "us-gaap", "Assets", "USD", instant=True)]
    value_records = [_value("rf-assets", "100")]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts=_companyfacts([("us-gaap", "Assets", "100", "USD", True)]),
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    noncurrent = _find(resolved["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "legitimately_absent"
    assert noncurrent["mapping_method"] == "primary_taxonomy_curated_crosswalk"


def test_resolution_does_not_derive_noncurrent_assets_when_periods_misalign() -> None:
    sidecar_records = [
        _record("rf-assets", "us-gaap", "Assets", "USD", instant=True, end="end-2"),
        _record("rf-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True, end="end-1"),
    ]
    value_records = [_value("rf-assets", "100"), _value("rf-current-assets", "40")]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts={
            "us-gaap": {
                "Assets": {"units": {"USD": [{"fp": "FY", "fy": 1, "val": "100", "end": "end-2"}]}},
                "AssetsCurrent": {"units": {"USD": [{"fp": "FY", "fy": 1, "val": "40", "end": "end-1"}]}},
            }
        },
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    noncurrent = _find(resolved["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "legitimately_absent"
    assert noncurrent["absence_reason"] == "no_reviewed_fy_source_fact"


def test_resolution_does_not_derive_noncurrent_assets_when_difference_is_negative() -> None:
    sidecar_records = [
        _record("rf-assets", "us-gaap", "Assets", "USD", instant=True),
        _record("rf-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
    ]
    value_records = [_value("rf-assets", "40"), _value("rf-current-assets", "60")]

    resolved = canonical.resolve_issuer_canonical_concepts(
        companyfacts={
            "us-gaap": {
                "Assets": {"units": {"USD": [{"fp": "FY", "fy": 1, "val": "40", "end": "end-2"}]}},
                "AssetsCurrent": {"units": {"USD": [{"fp": "FY", "fy": 1, "val": "60", "end": "end-2"}]}},
            }
        },
        sidecar_records=sidecar_records,
        value_records=value_records,
        fiscal_year=1,
    )
    noncurrent = _find(resolved["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "legitimately_absent"
    assert noncurrent["absence_reason"] == "no_reviewed_fy_source_fact"


def test_projection_derives_noncurrent_assets_with_target_oracle_absent() -> None:
    sidecar_records = [
        _record("rf-assets", "us-gaap", "Assets", "USD", instant=True),
        _record("rf-current-assets", "us-gaap", "AssetsCurrent", "USD", instant=True),
    ]
    value_records = [_value("rf-assets", "100"), _value("rf-current-assets", "40")]

    projected = _project(
        companyfacts=_companyfacts(
            [
                ("us-gaap", "Assets", "100", "USD", True),
                ("us-gaap", "AssetsCurrent", "40", "USD", True),
            ]
        ),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    noncurrent = _find(projected["concepts"], "NoncurrentAssets", "total")

    assert projected["status"] == "canonical_projection_ready"
    assert noncurrent["status"] == "derived"
    assert noncurrent["_value"] == Decimal("60")
    assert noncurrent["oracle_confirmed"] == "oracle_absent"
    assert noncurrent["provenance_complete"] is True
    assert noncurrent["derived_from_resolved_fact_ids"] == ["rf-assets", "rf-current-assets"]
    assert projected["provenance_complete_count"] == projected["projected_count"]
    assert _identity(projected, "current_assets_plus_noncurrent_assets_equals_total_assets")["residual_abs"] == "0"


def test_projection_does_not_force_derive_when_current_assets_absent() -> None:
    sidecar_records = [_record("rf-assets", "us-gaap", "Assets", "USD", instant=True)]
    value_records = [_value("rf-assets", "100")]

    projected = _project(
        companyfacts=_companyfacts([("us-gaap", "Assets", "100", "USD", True)]),
        sidecar_records=sidecar_records,
        value_records=value_records,
    )
    noncurrent = _find(projected["concepts"], "NoncurrentAssets", "total")

    assert noncurrent["status"] == "legitimately_absent"
    assert noncurrent["absence_reason"] == "no_reviewed_sidecar_fy_source_fact"


def test_coverage_breadth_report_is_sector_aggregate_and_redacted(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()
    report = diagnostic.build_report(source_root=_source_root(tmp_path))
    text = json.dumps(report, sort_keys=True)

    assert report["decision"] == "canonical_coverage_breadth_validate_only_ready"
    assert report["summary"]["headline_canonical_cell_count"] == 286
    assert report["summary"]["derived_count"] == 14
    assert report["summary"]["covered_count_including_derived"] == 248
    assert report["sector_class_count"] == 2
    assert report["sector_structure_limitation"]["implementation_in_this_slice"] is False
    assert report["redaction"]["passed"] is True
    assert "industrial_commercial" in {item["sector_class"] for item in report["sector_classes"]}
    assert "financial_structure_limited" in {item["sector_class"] for item in report["sector_classes"]}
    assert "raw-reference-issuer" not in text
    assert "rf-assets" not in text
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


def _project(*, companyfacts: dict, sidecar_records: list[dict], value_records: list[dict]) -> dict:
    return canonical.project_issuer_canonical_facts(
        companyfacts=companyfacts,
        sidecar_records=sidecar_records,
        value_records=value_records,
        sidecar_receipt_id="sidecar-ref",
        sidecar_receipt_hash="sidecar-hash",
        value_store_hash=stable_hash(value_records),
        dataset_version_id="dataset-ref",
        fiscal_year=1,
    )


def _companyfacts(entries: list[tuple[str, str, str, str, bool]]) -> dict:
    facts: dict[str, dict] = {}
    for taxonomy, local_name, value, unit, instant in entries:
        facts.setdefault(taxonomy, {}).setdefault(local_name, {"units": {}})
        fact = {"fp": "FY", "fy": 1, "val": value, "end": "end-2"}
        if not instant:
            fact["start"] = "start-2"
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    instant: bool = False,
    start: str = "start-2",
    end: str = "end-2",
) -> dict:
    period = {"type": "instant", "instant": end} if instant else {
        "type": "duration",
        "start": start,
        "end": end,
    }
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


def _value(fact_id: str, effective_value: str) -> dict:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _namespace(taxonomy: str) -> str:
    if taxonomy == "ifrs-full":
        return "xbrl.ifrs.org/test"
    return "fasb.org/us-gaap/test"


def _unit(unit_name: str) -> dict:
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}


def _find(items: list[dict], canonical_id: str, basis: str) -> dict:
    return next(item for item in items if item["canonical_id"] == canonical_id and item["basis"] == basis)


def _identity(result: dict, identity_id: str) -> dict:
    return next(
        item for item in result["statement_identity_residuals"] if item["identity_id"] == identity_id
    )
