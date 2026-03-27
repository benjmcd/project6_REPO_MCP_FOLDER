from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.review_nrc_aps import NrcApsReviewFileDetailsOut, NrcApsReviewNodeDetailsOut
from app.services.review_nrc_aps_graph import CANONICAL_NODES, build_file_to_node_map, map_run_specific_graph
from app.services.review_nrc_aps_runtime import normalize_path


def _canonical_label_and_family(node_id: str) -> tuple[str, str]:
    for candidate_id, label, stage_family, _, _ in CANONICAL_NODES:
        if candidate_id == node_id:
            return label, stage_family
    raise ValueError(f"Unknown canonical node id: {node_id}")


def get_node_details(run_id: str, review_root: Path, node_id: str) -> NrcApsReviewNodeDetailsOut:
    node_states = map_run_specific_graph(run_id, review_root)
    node_state = node_states.get(node_id)
    if node_state is None:
        raise ValueError(f"Unknown canonical node id: {node_id}")
    label, stage_family = _canonical_label_and_family(node_id)
    return NrcApsReviewNodeDetailsOut(
        node_id=node_id,
        label=label,
        stage_family=stage_family,
        run_id=run_id,
        state=node_state.state,
        warnings=node_state.warnings,
        mapped_file_refs=node_state.mapped_file_refs,
        structured_summary=node_state.summary_metrics,
    )


def _json_summary(file_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    summary: dict[str, Any] = {}
    for key in (
        "schema_id",
        "status",
        "total_hits",
        "total_citations",
        "total_sections",
        "indexed_content_units",
        "indexing_failures_count",
        "review_item_count",
        "acknowledgement_count",
        "blocker_count",
        "total_challenges",
        "total_findings",
        "total_facts",
        "total_constraints",
        "source_export_count",
    ):
        if key in data:
            summary[key] = data[key]
    if not summary and isinstance(data, dict):
        for key in list(data.keys())[:5]:
            if isinstance(data[key], (str, int, float, bool)):
                summary[key] = data[key]
    return summary


def get_file_details(run_id: str, review_root: Path, tree_id: str, file_path: Path) -> NrcApsReviewFileDetailsOut:
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")

    relative_path = normalize_path(review_root, file_path)
    file_node_map = build_file_to_node_map(map_run_specific_graph(run_id, review_root))
    stat = file_path.stat()
    return NrcApsReviewFileDetailsOut(
        tree_id=tree_id,
        path=relative_path,
        name=file_path.name,
        is_dir=file_path.is_dir(),
        mapped_node_ids=file_node_map.get(relative_path, []),
        run_id=run_id,
        size_bytes=None if file_path.is_dir() else stat.st_size,
        modified_time=str(stat.st_mtime),
        structured_summary={} if file_path.is_dir() else _json_summary(file_path),
    )
