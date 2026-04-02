from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.nrc_aps_contract import parse_iso_datetime
from app.services.review_nrc_aps_catalog import discover_candidate_runs
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding

def test_discover_candidate_runs():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    out = discover_candidate_runs(db)
    # Even if DB is empty, the golden run fixture should be found via summary-backed root scan
    assert out.runs, "Should find at least one run"
    # 1. Core invariant: The golden fixture exists and its properties are computed correctly
    golden_run = next((r for r in out.runs if r.run_id == "d6be0fff-bbd7-468a-9b00-7103d5995494"), None)
    assert golden_run is not None, "Golden run fixture should be found"
    assert golden_run.reviewable is True
    assert golden_run.disabled_reason_code is None

    # 2. Default selection contract: default_run_id must select the most recently completed reviewable run
    assert out.default_run_id is not None, "A default run must be selected when reviewable candidates exist"
    default_run = next((r for r in out.runs if r.run_id == out.default_run_id), None)
    assert default_run is not None, "default_run_id must exist in the returned runs list"
    assert default_run.reviewable is True, "default_run_id must be a reviewable candidate"
    
    default_dt = parse_iso_datetime(default_run.completed_at)
    for r in out.runs:
        if r.reviewable and r.completed_at:
            assert default_dt >= parse_iso_datetime(r.completed_at), "default_run_id must be the most recently completed reviewable candidate"


@patch("app.services.review_nrc_aps_catalog._load_connector_run")
@patch("app.services.review_nrc_aps_catalog.discover_runtime_bindings")
def test_discover_candidate_runs_handles_mixed_naive_and_aware_completed_at(mock_discover_runtime_bindings, mock_load_connector_run):
    root_db = Path("C:/review/db-run")
    root_summary = Path("C:/review/summary-run")

    def summary_for(run_id: str, completed_at: str) -> dict:
        return {
            "run_id": run_id,
            "generated_at_utc": completed_at,
            "submission": {"submitted_at": completed_at},
            "run_detail": {
                "completed_at": completed_at,
                "selected_count": 1,
                "downloaded_count": 1,
                "failed_count": 0,
                "report_refs": {
                    "aps_artifact_ingestion": "present",
                    "aps_content_index": "present",
                },
            },
        }

    binding_db = ReviewRuntimeBinding(
        run_id="db-run",
        review_root=root_db,
        summary=summary_for("db-run", "2026-03-31T10:00:00"),
        database_path=root_db / "lc.db",
        storage_dir=root_db / "storage",
    )
    binding_summary = ReviewRuntimeBinding(
        run_id="summary-run",
        review_root=root_summary,
        summary=summary_for("summary-run", "2026-03-31T11:00:00Z"),
        database_path=root_summary / "lc.db",
        storage_dir=root_summary / "storage",
    )
    mock_discover_runtime_bindings.return_value = [binding_db, binding_summary]

    db_run = MagicMock()
    db_run.connector_run_id = "db-run"
    db_run.status = "completed"
    db_run.submitted_at = datetime(2026, 3, 31, 9, 0, 0)
    db_run.completed_at = datetime(2026, 3, 31, 10, 0, 0)

    mock_load_connector_run.side_effect = lambda binding: db_run if binding.run_id == "db-run" else None

    out = discover_candidate_runs()

    assert out.default_run_id == "summary-run"
    assert [item.run_id for item in out.runs[:2]] == ["summary-run", "db-run"]
