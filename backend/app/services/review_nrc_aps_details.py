from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.review_nrc_aps import NrcApsReviewFileDetailsOut, NrcApsReviewFilePreviewOut, NrcApsReviewNodeDetailsOut
from app.services.review_nrc_aps_graph import CANONICAL_NODE_INDEX, build_file_to_node_map, build_run_projection, get_run_projection_node
from app.services.review_nrc_aps_runtime import normalize_path


PREVIEW_MAX_CHARS = 12000
JSON_PREVIEW_SUFFIXES = {".json"}
TEXT_PREVIEW_SUFFIXES = {".txt", ".md", ".csv", ".ndjson", ".jsonl", ".log"}


def _canonical_label_and_family(node_id: str) -> tuple[str, str]:
    node = CANONICAL_NODE_INDEX.get(node_id)
    if not node:
        raise ValueError(f"Unknown canonical node id: {node_id}")
    return str(node["label"]), str(node["stage_family"])


def get_node_details(run_id: str, review_root: Path, node_id: str) -> NrcApsReviewNodeDetailsOut:
    run_projection = build_run_projection(run_id, review_root)
    node = get_run_projection_node(run_projection, node_id)
    if node is None:
        raise ValueError(f"Unknown canonical node id: {node_id}")
    label, stage_family = _canonical_label_and_family(node_id)
    return NrcApsReviewNodeDetailsOut(
        node_id=node_id,
        label=label,
        stage_family=stage_family,
        run_id=run_id,
        state=node.state,
        warnings=node.warnings,
        mapped_file_refs=node.mapped_file_refs,
        structured_summary=node.structured_summary,
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


def _preview_kind(file_path: Path) -> str | None:
    suffix = file_path.suffix.lower()
    if suffix in JSON_PREVIEW_SUFFIXES:
        return "json"
    if suffix in TEXT_PREVIEW_SUFFIXES:
        return "text"
    return None


def _truncate_content(content: str, max_chars: int) -> tuple[str, bool]:
    if len(content) <= max_chars:
        return content, False
    return f"{content[:max_chars]}\n\n... [truncated]", True


def _prioritize_json_preview(parsed: Any) -> Any:
    if not isinstance(parsed, dict):
        return parsed

    ordered: dict[str, Any] = {}
    preferred_keys = (
        "schema_id",
        "schema_version",
        "run_id",
        "passed",
        "generated_at_utc",
        "corpus_pdf_count",
        "search_smoke",
        "submission",
        "preflight",
        "run_detail",
        "selected_branch_rows",
        "gate_results",
        "downstream_artifacts",
        "advanced_metrics",
        "target_outcomes",
        "failure",
    )
    for key in preferred_keys:
        if key in parsed:
            ordered[key] = parsed[key]
    for key, value in parsed.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def get_file_details(run_id: str, review_root: Path, tree_id: str, file_path: Path) -> NrcApsReviewFileDetailsOut:
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")

    relative_path = normalize_path(review_root, file_path)
    file_node_map = build_file_to_node_map(build_run_projection(run_id, review_root))
    stat = file_path.stat()
    preview_kind = None if file_path.is_dir() else _preview_kind(file_path)
    return NrcApsReviewFileDetailsOut(
        tree_id=tree_id,
        path=relative_path,
        name=file_path.name,
        is_dir=file_path.is_dir(),
        mapped_node_ids=file_node_map.get(relative_path, []),
        run_id=run_id,
        size_bytes=None if file_path.is_dir() else stat.st_size,
        modified_time=str(stat.st_mtime),
        preview_available=bool(preview_kind),
        preview_kind=preview_kind,
        structured_summary={} if file_path.is_dir() else _json_summary(file_path),
    )


def get_file_preview(run_id: str, review_root: Path, tree_id: str, file_path: Path, max_chars: int = PREVIEW_MAX_CHARS) -> NrcApsReviewFilePreviewOut:
    if not file_path.exists() or file_path.is_dir():
        raise FileNotFoundError(f"File {file_path} does not exist or is not previewable.")

    preview_kind = _preview_kind(file_path)
    if not preview_kind:
        raise ValueError(f"Preview is not supported for {file_path.name}.")

    relative_path = normalize_path(review_root, file_path)
    if preview_kind == "json":
        try:
            parsed = json.loads(file_path.read_text(encoding="utf-8"))
            content = json.dumps(_prioritize_json_preview(parsed), indent=2, ensure_ascii=False)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Preview is not supported for malformed JSON file {file_path.name}.") from exc
        language = "json"
    else:
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Preview is not supported for unreadable text file {file_path.name}.") from exc
        language = "text"

    content, truncated = _truncate_content(content, max_chars)
    return NrcApsReviewFilePreviewOut(
        tree_id=tree_id,
        path=relative_path,
        name=file_path.name,
        run_id=run_id,
        preview_kind=preview_kind,
        language=language,
        content=content,
        truncated=truncated,
        max_chars=max_chars,
    )
