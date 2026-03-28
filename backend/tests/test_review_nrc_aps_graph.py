from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.review_nrc_aps_graph import build_canonical_graph, build_pipeline_projection, build_run_projection
from app.services.review_nrc_aps_runtime import find_review_root_for_run


RUN_ID = "d6be0fff-bbd7-468a-9b00-7103d5995494"
BRANCH_A_TARGET = "14ccc411-c68e-46f2-9e30-0df7f0b83e70"
BRANCH_B_TARGET = "f6b07ecf-dbf6-4faa-ab0e-f0144d8c7991"


def _root():
    root = find_review_root_for_run(RUN_ID)
    assert root is not None, "Golden fixture review root must be found"
    return root


def test_build_canonical_graph():
    graph = build_canonical_graph()
    node_ids = {n.node_id for n in graph.nodes}
    assert "source_corpus" in node_ids
    assert "branch_a_bundle" in node_ids
    assert "validate_only_gates" in node_ids
    assert len(graph.edges) > 0


def test_pipeline_projection_is_less_dense_than_run_projection():
    pipeline = build_pipeline_projection(RUN_ID, _root())
    run_graph = build_run_projection(RUN_ID, _root())
    assert len(pipeline.nodes) < len(run_graph.nodes)
    assert any(node.projection_id == "branch_a" and node.is_composite for node in pipeline.nodes)
    assert any(node.projection_id == "branch_b" and node.is_composite for node in pipeline.nodes)


def test_run_projection_contains_real_run_specific_details():
    run_graph = build_run_projection(RUN_ID, _root())
    submission = next(node for node in run_graph.nodes if node.projection_id == "submission")
    assert any(RUN_ID in line for line in submission.detail_lines)
    assert submission.structured_summary["status"] == "completed"

    gates = next(node for node in run_graph.nodes if node.projection_id == "validate_only_gates")
    assert gates.structured_summary["gate_total"] >= 1


def test_run_projection_branch_mapping_uses_frozen_branch_anchors():
    run_graph = build_run_projection(RUN_ID, _root())
    branch_a_bundle = next(node for node in run_graph.nodes if node.projection_id == "branch_a_bundle")
    branch_b_bundle = next(node for node in run_graph.nodes if node.projection_id == "branch_b_bundle")
    assert branch_a_bundle.detail_lines[0].endswith(BRANCH_A_TARGET)
    assert branch_b_bundle.detail_lines[0].endswith(BRANCH_B_TARGET)
    assert any("aps_evidence_bundle_v2.json" in ref for ref in branch_a_bundle.mapped_file_refs)
    assert any("aps_evidence_bundle_v2.json" in ref for ref in branch_b_bundle.mapped_file_refs)


def test_run_projection_surfaces_expected_warning():
    run_graph = build_run_projection(RUN_ID, _root())
    submission = next(node for node in run_graph.nodes if node.projection_id == "submission")
    assert any("artifact_dedup_report" in warning for warning in submission.warnings)
