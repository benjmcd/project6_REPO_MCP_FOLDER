from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.config import settings


GOLDEN_RUN_ID = "d6be0fff-bbd7-468a-9b00-7103d5995494"
PIPELINE_ID = "nrc_aps_review_v1"


def get_allowlisted_roots() -> list[Path]:
    storage_dir = Path(settings.storage_dir)
    app_runtime_root = Path(__file__).resolve().parents[1] / "storage_test_runtime" / "lc_e2e"
    backend_runtime_root = Path(__file__).resolve().parents[2] / "storage_test_runtime" / "lc_e2e"
    roots = [app_runtime_root, backend_runtime_root]
    if storage_dir.name == "storage":
        roots.append(storage_dir / "lc_e2e")
    deduped: dict[str, Path] = {}
    for root in roots:
        deduped[str(root.resolve())] = root.resolve()
    return list(deduped.values())


def is_summary_backed(directory: Path) -> bool:
    summary_path = directory / "local_corpus_e2e_summary.json"
    if not summary_path.is_file():
        return False
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (
        data.get("schema_id") == "aps.local_corpus_e2e_summary.v1"
        and data.get("schema_version") == 1
        and bool(data.get("run_id"))
    )


def discover_review_roots() -> list[Path]:
    roots: list[Path] = []
    for base_root in get_allowlisted_roots():
        if not base_root.exists() or not base_root.is_dir():
            continue
        for entry in base_root.iterdir():
            if entry.is_dir() and is_summary_backed(entry):
                roots.append(entry.resolve())
    deduped: dict[str, Path] = {}
    for root in roots:
        deduped[str(root)] = root
    return list(deduped.values())


def load_summary(review_root: Path) -> dict[str, Any]:
    summary_path = review_root / "local_corpus_e2e_summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def find_review_root_for_run(run_id: str) -> Path | None:
    for root in discover_review_roots():
        try:
            data = load_summary(root)
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("run_id") == run_id:
            return root
    return None


def normalize_path(review_root: Path, path: str | Path) -> str:
    root = review_root.resolve()
    candidate = Path(path)
    absolute = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    relative = absolute.relative_to(root)
    return relative.as_posix() if str(relative) != "." else "."


def generate_tree_id(relative_path: str) -> str:
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()
    return f"tree::{digest}"


def absolute_path_for_relative(review_root: Path, relative_path: str) -> Path:
    candidate = (review_root / relative_path).resolve()
    candidate.relative_to(review_root.resolve())
    return candidate


def path_exists(review_root: Path, candidate: str | Path) -> bool:
    try:
        absolute_path_for_relative(review_root, normalize_path(review_root, candidate))
    except ValueError:
        return False
    target = Path(candidate)
    if not target.is_absolute():
        target = review_root / target
    return target.exists()
