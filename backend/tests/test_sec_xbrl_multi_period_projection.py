from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-multi-period-projection.py"
REPORT_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-multi-period-projection-report.json"


def _diagnostic_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_multi_period_projection", DIAGNOSTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_multi_period_projection_report_projects_document_period_and_comparative(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()

    report = diagnostic.build_report(source_root=_source_root(tmp_path))

    assert report["decision"] == "sec_xbrl_multi_period_projection_validate_only_ready"
    assert report["summary"]["projection_status"] == "canonical_multi_period_projection_ready"
    assert report["summary"]["period_count"] == 2
    assert report["summary"]["ready_period_count"] == 2
    assert report["summary"]["defined_cell_count"] == 44
    assert report["summary"]["projected_count"] == 4
    assert [item["period_ref"] for item in report["periods"]] == ["fy-period-1", "fy-period-2"]
    assert report["periods"][0]["matches_document_period_end_date"] is True
    assert report["periods"][1]["matches_document_period_end_date"] is False
    assert report["periods"][0]["per_statement_projected"] == {"balance": 1, "cashflow": 0, "income": 1}
    assert report["redaction"]["passed"] is True
    assert report["next_slice"] == "sec_xbrl_sector_family_real_filer_validation_v1"


def test_multi_period_projection_report_fails_closed_on_empty_runtime(tmp_path: Path) -> None:
    diagnostic = _diagnostic_module()

    report = diagnostic.build_report(
        source_root=_source_root(tmp_path),
        issuer_bundle={
            "companyfacts": {},
            "sidecar_records": [],
            "value_records": [],
            "sidecar_receipt_id": "sidecar-ref",
            "sidecar_receipt_hash": "sidecar-hash",
            "value_store_hash": "",
            "dataset_version_id": "dataset-ref",
        },
    )

    assert report["decision"] == "no_multi_period_projection_evidence"
    assert report["summary"]["projection_status"] == "canonical_multi_period_projection_blocked"
    assert report["summary"]["period_count"] == 0
    assert report["blocking_reasons"]


def test_committed_multi_period_projection_report_is_redacted() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    text = json.dumps(report, sort_keys=True)

    assert report["schema_id"] == "diagnostics.sec_xbrl_multi_period_projection.v1"
    assert report["decision"] == "sec_xbrl_multi_period_projection_validate_only_ready"
    assert report["summary"]["period_count"] == 2
    assert report["periods"][0]["matches_document_period_end_date"] is True
    assert report["periods"][1]["matches_document_period_end_date"] is False
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
