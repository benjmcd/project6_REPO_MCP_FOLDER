from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.review_nrc_aps_graph import build_file_to_node_map, build_run_projection
from app.services.review_nrc_aps_tree import build_pipeline_layout, build_strict_filesystem_tree, get_node_by_tree_id
from app.services.review_nrc_aps_runtime import find_review_root_for_run
from review_nrc_aps_runtime_fixture import latest_passed_runtime


RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id

def test_build_strict_filesystem_tree():
    root = find_review_root_for_run(RUN_ID)
    assert root is not None

    tree = build_strict_filesystem_tree(RUN_ID, root, build_file_to_node_map(build_run_projection(RUN_ID, root)))
    assert tree.run_id == RUN_ID
    assert tree.root.is_dir is True
    assert "tree::" in tree.root.tree_id

    # The root should have some children like 'storage' and 'local_corpus_e2e_summary.json'
    assert tree.root.children is not None
    child_names = [c.name for c in tree.root.children]
    assert "local_corpus_e2e_summary.json" in child_names
    assert "storage" in child_names

def test_get_node_by_tree_id():
    root = find_review_root_for_run(RUN_ID)
    tree = build_strict_filesystem_tree(RUN_ID, root, build_file_to_node_map(build_run_projection(RUN_ID, root)))
    
    summary_node = next(c for c in tree.root.children if c.name == "local_corpus_e2e_summary.json")
    
    found = get_node_by_tree_id(tree.root, summary_node.tree_id)
    assert found is not None
    assert found.name == "local_corpus_e2e_summary.json"


def test_build_pipeline_layout():
    root = find_review_root_for_run(RUN_ID)
    layout = build_pipeline_layout(RUN_ID, root)
    titles = [section.title for section in layout.sections]
    assert titles == ["Source", "Runtime", "Layout", "Downstream"]
    assert any(entry.value == f"{int(RUNTIME.summary.get('corpus_pdf_count') or 0)} PDFs" for entry in layout.sections[0].entries)
