from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.review_nrc_aps_graph import build_file_to_node_map, build_run_projection
from app.services.review_nrc_aps_tree import build_pipeline_layout, build_strict_filesystem_tree, get_node_by_tree_id
from app.services.review_nrc_aps_runtime import find_review_root_for_run

def test_build_strict_filesystem_tree():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    assert root is not None

    tree = build_strict_filesystem_tree(run_id, root, build_file_to_node_map(build_run_projection(run_id, root)))
    assert tree.run_id == run_id
    assert tree.root.is_dir is True
    assert "tree::" in tree.root.tree_id

    # The root should have some children like 'storage' and 'local_corpus_e2e_summary.json'
    assert tree.root.children is not None
    child_names = [c.name for c in tree.root.children]
    assert "local_corpus_e2e_summary.json" in child_names
    assert "storage" in child_names

def test_get_node_by_tree_id():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    tree = build_strict_filesystem_tree(run_id, root, build_file_to_node_map(build_run_projection(run_id, root)))
    
    summary_node = next(c for c in tree.root.children if c.name == "local_corpus_e2e_summary.json")
    
    found = get_node_by_tree_id(tree.root, summary_node.tree_id)
    assert found is not None
    assert found.name == "local_corpus_e2e_summary.json"


def test_build_pipeline_layout():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    layout = build_pipeline_layout(run_id, root)
    titles = [section.title for section in layout.sections]
    assert titles == ["Source", "Runtime", "Layout", "Downstream"]
    assert any(entry.value == "43 PDFs" for entry in layout.sections[0].entries)
