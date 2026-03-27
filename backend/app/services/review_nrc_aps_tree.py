from __future__ import annotations

from pathlib import Path

from app.schemas.review_nrc_aps import NrcApsReviewTreeNodeOut, NrcApsReviewTreeOut
from app.services.review_nrc_aps_runtime import generate_tree_id, normalize_path


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


def get_node_by_tree_id(root_node: NrcApsReviewTreeNodeOut, target_id: str) -> NrcApsReviewTreeNodeOut | None:
    if root_node.tree_id == target_id:
        return root_node
    if root_node.children:
        for child in root_node.children:
            result = get_node_by_tree_id(child, target_id)
            if result:
                return result
    return None
