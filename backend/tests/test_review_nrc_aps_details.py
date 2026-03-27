from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.review_nrc_aps_details import get_node_details, get_file_details, get_file_preview
from app.services.review_nrc_aps_runtime import find_review_root_for_run
from app.services.review_nrc_aps_tree import build_strict_filesystem_tree

def test_get_node_details():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    assert root is not None

    details = get_node_details(run_id, root, "source_corpus")
    assert details.node_id == "source_corpus"
    assert details.label == "Source corpus"
    assert details.stage_family == "source"
    assert details.state == "complete"
    assert "corpus_pdf_count" in details.structured_summary

def test_get_file_details():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    tree = build_strict_filesystem_tree(run_id, root)
    summary_node = next(c for c in tree.root.children if c.name == "local_corpus_e2e_summary.json")

    file_path = root / summary_node.path
    details = get_file_details(run_id, root, summary_node.tree_id, file_path)

    assert details.name == "local_corpus_e2e_summary.json"
    assert details.is_dir is False
    assert details.size_bytes > 0
    assert details.preview_available is True
    assert details.preview_kind == "json"
    assert details.structured_summary["schema_id"] == "aps.local_corpus_e2e_summary.v1"


def test_get_file_preview():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    root = find_review_root_for_run(run_id)
    tree = build_strict_filesystem_tree(run_id, root)
    summary_node = next(c for c in tree.root.children if c.name == "local_corpus_e2e_summary.json")

    file_path = root / summary_node.path
    preview = get_file_preview(run_id, root, summary_node.tree_id, file_path)

    assert preview.preview_kind == "json"
    assert preview.language == "json"
    assert '"schema_id": "aps.local_corpus_e2e_summary.v1"' in preview.content
