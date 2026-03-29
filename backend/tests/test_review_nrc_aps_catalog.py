from __future__ import annotations

import sys
from unittest.mock import MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.review_nrc_aps_catalog import discover_candidate_runs

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
    
    from datetime import datetime
    def parse_dt(dt_str: str) -> datetime:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    
    default_dt = parse_dt(default_run.completed_at)
    for r in out.runs:
        if r.reviewable and r.completed_at:
            assert default_dt >= parse_dt(r.completed_at), "default_run_id must be the most recently completed reviewable candidate"
