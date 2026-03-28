from __future__ import annotations

from pathlib import Path

from app.schemas.review_nrc_aps import NrcApsReviewOverviewOut, NrcApsReviewPipelineDefinitionOut
from app.services.review_nrc_aps_graph import build_canonical_graph, build_file_to_node_map, build_pipeline_projection, build_run_projection
from app.services.review_nrc_aps_runtime import load_summary
from app.services.review_nrc_aps_tree import build_pipeline_layout, build_strict_filesystem_tree


def compose_pipeline_definition(run_id: str, review_root: Path) -> NrcApsReviewPipelineDefinitionOut:
    return NrcApsReviewPipelineDefinitionOut(
        canonical_graph=build_canonical_graph(),
        pipeline_projection=build_pipeline_projection(run_id, review_root),
    )


def compose_overview(run_id: str, review_root: Path) -> NrcApsReviewOverviewOut:
    run_projection = build_run_projection(run_id, review_root)
    file_node_map = build_file_to_node_map(run_projection)
    return NrcApsReviewOverviewOut(
        run_id=run_id,
        run_summary=load_summary(review_root),
        run_projection=run_projection,
        pipeline_layout=build_pipeline_layout(run_id, review_root),
        tree=build_strict_filesystem_tree(run_id, review_root, file_node_map=file_node_map),
    )
