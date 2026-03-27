from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.review_nrc_aps_graph import build_canonical_graph, map_run_specific_graph
from app.services.review_nrc_aps_runtime import find_review_root_for_run

def test_build_canonical_graph():
    graph = build_canonical_graph()
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
    
    node_ids = {n.node_id for n in graph.nodes}
    assert "source_corpus" in node_ids
    assert "branch_a_bundle" in node_ids
    assert "validate_only_gates" in node_ids

def test_map_run_specific_graph():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    assert root is not None, "Golden fixture review root must be found"
    
    states = map_run_specific_graph(run_id, root)
    assert "source_corpus" in states
    assert states["source_corpus"].state == "complete"
    assert states["source_corpus"].summary_metrics["corpus_pdf_count"] == 43
    
    # Check for mismatch warning inserted specifically for golden run
    assert "submission" in states
    submission_warnings = states["submission"].warnings
    assert any("artifact_dedup_report" in warning for warning in submission_warnings)
