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
    assert out.default_run_id == "d6be0fff-bbd7-468a-9b00-7103d5995494"
    golden_run = next(r for r in out.runs if r.run_id == out.default_run_id)
    assert golden_run.reviewable is True
    assert golden_run.disabled_reason_code is None
