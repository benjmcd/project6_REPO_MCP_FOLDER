from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.review_nrc_aps_details import get_node_details, get_file_details, get_file_preview
from app.services.review_nrc_aps_runtime import find_review_root_for_run
from app.services.review_nrc_aps_graph import build_run_projection, build_file_to_node_map
from app.services.review_nrc_aps_tree import build_strict_filesystem_tree
from review_nrc_aps_runtime_fixture import latest_passed_runtime


RUNTIME = latest_passed_runtime()
RUN_ID = RUNTIME.run_id

def test_get_node_details():
    root = find_review_root_for_run(RUN_ID)
    assert root is not None

    details = get_node_details(RUN_ID, root, "source_corpus")
    assert details.node_id == "source_corpus"
    assert details.label == "Source corpus"
    assert details.stage_family == "source"
    assert details.state == "complete"
    assert "corpus_pdf_count" in details.structured_summary

def test_get_file_details():
    root = find_review_root_for_run(RUN_ID)
    tree = build_strict_filesystem_tree(RUN_ID, root, build_file_to_node_map(build_run_projection(RUN_ID, root)))
    summary_node = next(c for c in tree.root.children if c.name == "local_corpus_e2e_summary.json")

    file_path = root / summary_node.path
    details = get_file_details(RUN_ID, root, summary_node.tree_id, file_path)

    assert details.name == "local_corpus_e2e_summary.json"
    assert details.is_dir is False
    assert details.size_bytes > 0
    assert details.preview_available is True
    assert details.preview_kind == "json"
    assert details.structured_summary["schema_id"] == "aps.local_corpus_e2e_summary.v1"


def test_get_file_preview():
    root = find_review_root_for_run(RUN_ID)
    tree = build_strict_filesystem_tree(RUN_ID, root, build_file_to_node_map(build_run_projection(RUN_ID, root)))
    summary_node = next(c for c in tree.root.children if c.name == "local_corpus_e2e_summary.json")

    file_path = root / summary_node.path
    preview = get_file_preview(RUN_ID, root, summary_node.tree_id, file_path)

    assert preview.preview_kind == "json"
    assert preview.language == "json"
    assert '"schema_id": "aps.local_corpus_e2e_summary.v1"' in preview.content
