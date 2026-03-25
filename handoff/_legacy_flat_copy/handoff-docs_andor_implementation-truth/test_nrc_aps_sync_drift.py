import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_sync_drift  # noqa: E402


def _snapshot(
    *,
    run_id: str,
    sync_mode: str,
    accessions: list[str],
    hashes: dict[str, str],
    watermark: str | None,
) -> dict:
    accession_refs = {
        accession: {
            "target_id": f"target-{accession}",
            "target_ref": f"/tmp/{run_id}_{accession}_target.json",
            "metadata_ref": f"/tmp/{run_id}_{accession}_metadata.json",
        }
        for accession in accessions
    }
    return {
        "run_id": run_id,
        "source_query_fingerprint": "fp-123",
        "sync_mode": sync_mode,
        "discovery_ref": f"/tmp/{run_id}_discovery.json",
        "selection_ref": f"/tmp/{run_id}_selection.json",
        "search_exchange_refs": [f"/tmp/{run_id}_search_exchange.json"],
        "accessions": accessions,
        "projection_hashes": hashes,
        "accession_refs": accession_refs,
        "max_observed_watermark": watermark,
        "observed_schema_variants": {"results": 1},
        "dialect_order": ["shape_a", "guide_native"],
    }


def test_projection_hash_contract_normalization_and_exclusions():
    projection_a = {
        "accession_number": "MLA",
        "document_title": "  Example Title  ",
        "document_type": "Letter",
        "document_date": "2025-01-01",
        "date_added_timestamp": "2025-01-02T00:00:00Z",
        "url": "https://example.test/doc",
        "docket_number": [" 05000123 ", "05000123", "05000456"],
        "content_present": True,
        "vendor_blob": {"x": 1},
    }
    projection_b = {
        "accession_number": "MLA",
        "document_title": "Example Title",
        "document_type": "Letter",
        "document_date": "2025-01-01",
        "date_added_timestamp": "2025-01-02T00:00:00Z",
        "url": "https://example.test/doc",
        "docket_number": ["05000456", "05000123"],
        "content_present": False,
        "vendor_blob": {"x": 999},
    }

    hash_a = nrc_aps_sync_drift.compute_projection_hash(projection_a)
    hash_b = nrc_aps_sync_drift.compute_projection_hash(projection_b)
    assert hash_a == hash_b


def test_incremental_absence_finding_emitted_for_baseline_only_identities():
    current = _snapshot(
        run_id="run-current",
        sync_mode="incremental",
        accessions=["MLA"],
        hashes={"MLA": "hash-1"},
        watermark="2025-02-02T00:00:00Z",
    )
    baseline = _snapshot(
        run_id="run-baseline",
        sync_mode="incremental",
        accessions=["MLA", "MLB"],
        hashes={"MLA": "hash-1", "MLB": "hash-2"},
        watermark="2025-02-01T00:00:00Z",
    )

    _delta, drift = nrc_aps_sync_drift.build_delta_and_drift_artifacts(
        current_snapshot=current,
        baseline_snapshot=baseline,
        baseline_resolution=nrc_aps_sync_drift.APS_BASELINE_INCREMENTAL_STRICT,
    )
    finding_classes = {item["finding_class"] for item in drift["findings"]}
    assert nrc_aps_sync_drift.APS_FINDING_INCREMENTAL_ABSENCE in finding_classes


def test_validate_sync_drift_artifact_presence_fail_closed_modes(tmp_path: Path):
    run_id = "11111111-1111-1111-1111-111111111111"
    run_rows = [{"run_id": run_id}]
    paths = nrc_aps_sync_drift.artifact_paths(run_id=run_id, reports_dir=tmp_path)

    report_missing = nrc_aps_sync_drift.validate_sync_drift_artifact_presence(
        run_rows=run_rows,
        reports_dir=tmp_path,
    )
    assert report_missing["passed"] is False
    assert report_missing["checks"][0]["reasons"]

    nrc_aps_sync_drift.write_json_deterministic(paths["aps_sync_drift_failure"], {"schema_id": "aps.sync_drift_failure.v1"})
    report_failure_only = nrc_aps_sync_drift.validate_sync_drift_artifact_presence(
        run_rows=run_rows,
        reports_dir=tmp_path,
    )
    assert report_failure_only["passed"] is False
    assert "failure_artifact_without_success" in report_failure_only["checks"][0]["reasons"]

    nrc_aps_sync_drift.write_json_deterministic(paths["aps_sync_delta"], {"schema_id": "aps.sync_delta.v1"})
    nrc_aps_sync_drift.write_json_deterministic(paths["aps_sync_drift"], {"schema_id": "aps.sync_drift.v1"})
    report_success = nrc_aps_sync_drift.validate_sync_drift_artifact_presence(
        run_rows=run_rows,
        reports_dir=tmp_path,
    )
    assert report_success["passed"] is True

