from __future__ import annotations

from pathlib import Path

from app.schemas.review_nrc_aps import NrcApsReviewOverviewOut, NrcApsReviewRunGraphOut
from app.services.review_nrc_aps_graph import build_canonical_graph, build_file_to_node_map, map_run_specific_graph
from app.services.review_nrc_aps_tree import build_strict_filesystem_tree


def compose_overview(run_id: str, review_root: Path) -> NrcApsReviewOverviewOut:
    canonical_graph = build_canonical_graph()
    node_states = map_run_specific_graph(run_id, review_root)
    file_node_map = build_file_to_node_map(node_states)
    tree = build_strict_filesystem_tree(run_id, review_root, file_node_map=file_node_map)
    return NrcApsReviewOverviewOut(
        run_id=run_id,
        graph=NrcApsReviewRunGraphOut(
            run_id=run_id,
            canonical_graph=canonical_graph,
            node_states=node_states,
        ),
        tree=tree,
    )
