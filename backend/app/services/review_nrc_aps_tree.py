from __future__ import annotations

from pathlib import Path

from app.schemas.review_nrc_aps import (
    NrcApsReviewPipelineLayoutEntryOut,
    NrcApsReviewPipelineLayoutOut,
    NrcApsReviewPipelineLayoutSectionOut,
    NrcApsReviewTreeNodeOut,
    NrcApsReviewTreeOut,
)
from app.services.review_nrc_aps_runtime import generate_tree_id, load_summary, normalize_path


def build_tree_node(root: Path, current_path: Path, file_node_map: dict[str, list[str]]) -> NrcApsReviewTreeNodeOut:
    relative_path = normalize_path(root, current_path)
    tree_id = generate_tree_id(relative_path)
    children = None
    if current_path.is_dir():
        children = [build_tree_node(root, entry, file_node_map) for entry in sorted(current_path.iterdir(), key=lambda item: item.name)]

    mapped_node_ids = list(file_node_map.get(relative_path, []))
    if children:
        descendant_mappings = {node_id for child in children for node_id in child.mapped_node_ids}
        mapped_node_ids = sorted(set(mapped_node_ids).union(descendant_mappings))

    return NrcApsReviewTreeNodeOut(
        tree_id=tree_id,
        name=current_path.name or root.name,
        path=relative_path,
        is_dir=current_path.is_dir(),
        children=children,
        mapped_node_ids=mapped_node_ids,
    )


def build_strict_filesystem_tree(run_id: str, review_root: Path, file_node_map: dict[str, list[str]] | None = None) -> NrcApsReviewTreeOut:
    file_node_map = file_node_map or {}
    return NrcApsReviewTreeOut(run_id=run_id, root=build_tree_node(review_root, review_root, file_node_map))


def build_pipeline_layout(run_id: str, review_root: Path) -> NrcApsReviewPipelineLayoutOut:
    summary = load_summary(review_root)
    source_root = str(summary.get("source_root") or "")
    runtime_root = str(review_root)

    def entry(label: str, value: str, path: str | None = None) -> NrcApsReviewPipelineLayoutEntryOut:
        return NrcApsReviewPipelineLayoutEntryOut(label=label, value=value, path=path)

    source_entries = [
        entry("Source root", source_root or "unknown"),
        entry("PDF inputs", f"{summary.get('corpus_pdf_count', 0)} PDFs"),
    ]
    runtime_entries = [
        entry("Runtime root", runtime_root),
        entry("Run directory", review_root.name, "."),
        entry("SQLite", "lc.db", "lc.db"),
        entry("Summary", "local_corpus_e2e_summary.json", "local_corpus_e2e_summary.json"),
    ]
    storage_entries = [
        entry("Reports", "storage/connectors/reports", "storage/connectors/reports"),
        entry("Diagnostics", "storage/artifacts/nrc_adams_aps/diagnostics", "storage/artifacts/nrc_adams_aps/diagnostics"),
        entry("Normalized text", "storage/artifacts/nrc_adams_aps/normalized_text", "storage/artifacts/nrc_adams_aps/normalized_text"),
        entry("Visual pages", "storage/artifacts/nrc_adams_aps/visual_pages", "storage/artifacts/nrc_adams_aps/visual_pages"),
        entry("Snapshots", "snapshots", "snapshots"),
        entry("Gate reports", "gate_reports", "gate_reports"),
    ]
    downstream_entries = [
        entry("Selected branches", f"{len(summary.get('selected_branch_rows') or [])} branches"),
        entry("Downstream families", f"{len(summary.get('downstream_artifacts') or {})} families"),
        entry("Gate results", f"{len(summary.get('gate_results') or {})} checks"),
    ]

    return NrcApsReviewPipelineLayoutOut(
        run_id=run_id,
        sections=[
            NrcApsReviewPipelineLayoutSectionOut(title="Source", entries=source_entries),
            NrcApsReviewPipelineLayoutSectionOut(title="Runtime", entries=runtime_entries),
            NrcApsReviewPipelineLayoutSectionOut(title="Layout", entries=storage_entries),
            NrcApsReviewPipelineLayoutSectionOut(title="Downstream", entries=downstream_entries),
        ],
    )


def get_node_by_tree_id(root_node: NrcApsReviewTreeNodeOut, target_id: str) -> NrcApsReviewTreeNodeOut | None:
    if root_node.tree_id == target_id:
        return root_node
    if root_node.children:
        for child in root_node.children:
            result = get_node_by_tree_id(child, target_id)
            if result:
                return result
    return None
