from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_real_company_corpus_validation,
    layer3_sec_edgar_real_filing_acquisition_connector,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError


ROOT = Path(__file__).resolve().parents[2]
STORAGE_PREFLIGHT_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-storage-preflight.py"


def _storage_preflight_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_storage_preflight", STORAGE_PREFLIGHT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_live_source_artifact_ceiling_raise_preserves_default_and_bounds_owner_limit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 25_000_000)
    assert layer3_sec_edgar_live_source_artifact._source_artifact_max_bytes() == 25_000_000

    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 100_000_000)
    assert layer3_sec_edgar_live_source_artifact._source_artifact_max_bytes() == 100_000_000

    monkeypatch.setattr(settings, "layer3_sec_edgar_max_bytes", 200_000_001)
    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_edgar_live_source_artifact._source_artifact_max_bytes()
    assert excinfo.value.error_code == "sec_edgar_text_table_live_source_artifact_max_bytes_not_admitted"


def test_sec_corpus_matrix_accepts_explicit_owner_30_ticker_matrix_only_with_official_resolution(monkeypatch) -> None:
    static = list(layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_CIK_REFS)[:16]
    owner_matrix = [*static, *(f"ZZ{i:02d}" for i in range(14))]

    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", False)
    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_edgar_real_filing_acquisition_connector._normalise_company_matrix(owner_matrix)
    assert excinfo.value.error_code == "sec_edgar_real_filing_acquisition_connector_company_matrix_unknown"

    monkeypatch.setattr(settings, "layer3_sec_edgar_official_ticker_resolution_enabled", True)
    monkeypatch.setattr(
        layer3_sec_edgar_real_filing_acquisition_connector,
        "resolve_sec_ticker_to_cik",
        lambda ticker: {"cik": f"{1_000_000 + int(ticker[-2:]):07d}", "company_tickers_source_hash": "a" * 64},
    )

    tickers, resolved, provenance = layer3_sec_edgar_real_filing_acquisition_connector._normalise_company_matrix(
        owner_matrix
    )

    assert len(layer3_sec_edgar_real_filing_acquisition_connector.DEFAULT_REAL_COMPANY_MATRIX) == 4
    assert len(tickers) == 30
    assert tickers[:4] == tuple(static[:4])
    assert len(resolved) == 14
    assert provenance and provenance["company_tickers_source_hash"] == "a" * 64


def test_sec_corpus_records_standalone_xml_as_named_block() -> None:
    connector = {
        "corpus_manifest": {
            "example_records": [
                {
                    "example_id": "xml-example",
                    "source_family_roles": ["xml_xbrl_classified_not_parsed"],
                    "source_family": "sec_edgar",
                    "primary_document_family": "xml_xbrl",
                    "form_type": "10-K",
                }
            ]
        },
        "acquisition_receipts": [{"example_id": "xml-example", "source_artifact_receipt": {}}],
    }

    records = layer3_sec_edgar_real_company_corpus_validation._filing_validation_records(
        connector,
        request_id="xml-unsupported",
        db=None,
    )

    assert records[0]["supported_degraded_blocked"] == "blocked"
    assert records[0]["failure_classification"] == "source_routing"
    assert records[0]["gaps_found"] == ["standalone_xml_xbrl_unsupported"]


def test_sec_xbrl_storage_preflight_reports_capacity_and_is_read_only(tmp_path: Path) -> None:
    module = _storage_preflight_module()
    root = tmp_path / "storage"
    namespace = root / "layer3-sec-edgar-live-source-artifact-acquisition" / "artifacts"
    namespace.mkdir(parents=True)
    artifact = namespace / "artifact.txt"
    artifact.write_bytes(b"abc")
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    report = module.build_report(storage_root=root, min_free_bytes=1)
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    assert report["schema_id"] == "diagnostics.sec_xbrl_storage_preflight.v1"
    assert report["artifact_count"] == 1
    assert report["total_bytes"] == 3
    assert report["namespace_count"] == 1
    assert "free_space_bytes" in report
    assert report["free_space_threshold_met"] is True
    assert report["mutation_performed"] is False
    assert before == after


def test_sec_xbrl_storage_preflight_cli_blocks_missing_storage_root(monkeypatch, capsys, tmp_path: Path) -> None:
    module = _storage_preflight_module()
    missing = tmp_path / "missing-storage"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sec-xbrl-storage-preflight.py",
            "--storage-root",
            str(missing),
            "--min-free-bytes",
            "1",
        ],
    )

    assert module.main() == 1
    report = json.loads(capsys.readouterr().out)

    assert report["storage_root_exists"] is False
    assert report["free_space_threshold_met"] is True
    assert report["validate_only"] is True
    assert not missing.exists()


def test_sec_corpus_pre_inline_block_counts_only_inline_fact_markers() -> None:
    module = layer3_sec_edgar_real_company_corpus_validation
    parser = {
        "diagnostics": {"inline_xbrl_marker_count": 2},
        "inline_xbrl_marker_inventory": [
            {"marker_name_hash": module._sha256_text("ix:header")},
            {"marker_name_hash": module._sha256_text("ix:hidden")},
        ],
    }

    assert module._inline_xbrl_fact_marker_count(parser) == 0

    parser["inline_xbrl_marker_inventory"].append({"marker_name_hash": module._sha256_text("ix:nonfraction")})
    assert module._inline_xbrl_fact_marker_count(parser) == 1
