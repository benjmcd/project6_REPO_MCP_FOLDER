from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.nrc_aps_contract import parse_iso_datetime
from app.services.review_nrc_aps_runtime_roots import candidate_review_runtime_roots


GOLDEN_RUN_ID = "d6be0fff-bbd7-468a-9b00-7103d5995494"
PIPELINE_ID = "nrc_aps_review_v1"
_VISUAL_LANE_MODE_BASELINE = "baseline"
_VISUAL_LANE_MODE_CANDIDATE_A = "candidate_a_page_evidence_v1"
_VISUAL_LANE_MODE_CANDIDATE_B = "candidate_b_opendataloader_page_evidence_v1"
_BASELINE_VISIBLE_VISUAL_LANE_MODES: frozenset[str] = frozenset(
    {
        _VISUAL_LANE_MODE_BASELINE,
        _VISUAL_LANE_MODE_CANDIDATE_A,
        _VISUAL_LANE_MODE_CANDIDATE_B,
    }
)
_DOCUMENT_PROCESSING_ENGINE_BASELINE = "baseline"
_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B = "candidate_b_opendataloader_pdf"
_ADMITTED_DOCUMENT_PROCESSING_ENGINES: frozenset[str] = frozenset(
    {
        _DOCUMENT_PROCESSING_ENGINE_BASELINE,
        _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
    }
)


@dataclass(frozen=True)
class ReviewRuntimeBinding:
    run_id: str
    review_root: Path
    summary: dict[str, Any]
    database_path: Path | None
    storage_dir: Path | None


def _normalize_visual_lane_mode_for_visibility(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized or "baseline"


def classify_visual_lane_mode(value: Any) -> str | None:
    normalized = _normalize_visual_lane_mode_for_visibility(value)
    if normalized in _BASELINE_VISIBLE_VISUAL_LANE_MODES:
        return normalized
    return None


def _normalize_document_processing_engine_for_visibility(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _ADMITTED_DOCUMENT_PROCESSING_ENGINES:
        return normalized
    return _DOCUMENT_PROCESSING_ENGINE_BASELINE


def _request_config_document_processing_engine_explicit(request_config: Any) -> bool:
    if not isinstance(request_config, dict):
        return False
    if "document_processing_engine_explicit" in request_config:
        raw = request_config.get("document_processing_engine_explicit")
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on", "explicit"}
        return bool(raw)
    return bool(str(request_config.get("document_processing_engine") or "").strip())


def _summary_selected_target_count(summary: Any) -> int:
    if not isinstance(summary, dict):
        return 0
    run_detail = summary.get("run_detail") or {}
    for value in (
        run_detail.get("selected_count"),
        summary.get("corpus_pdf_count"),
    ):
        try:
            count = int(value or 0)
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            return count
    return 0


def _summary_reports_effective_candidate_b(summary: Any) -> bool:
    if not isinstance(summary, dict):
        return False
    metrics = summary.get("advanced_metrics") or {}
    if not isinstance(metrics, dict):
        return False
    if str(metrics.get("document_processing_engine") or "").strip().lower() == _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B:
        return True
    try:
        candidate_b_count = int(metrics.get("candidate_b_extractor_file_count") or 0)
    except (TypeError, ValueError):
        candidate_b_count = 0
    selected_count = _summary_selected_target_count(summary)
    return candidate_b_count > 0 and selected_count > 0 and candidate_b_count == selected_count


def _effective_document_processing_engine(
    *,
    request_config: Any,
    summary: Any,
    requested_document_processing_engine: str,
) -> tuple[str, str]:
    if requested_document_processing_engine == _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B:
        return _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B, "request_config"
    if _request_config_document_processing_engine_explicit(request_config):
        return requested_document_processing_engine, "request_config_explicit"
    if _summary_reports_effective_candidate_b(summary):
        return _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B, "summary_effective_candidate_b"
    return requested_document_processing_engine, "request_config_default"


def request_config_is_baseline_visible(request_config: Any) -> bool:
    if not isinstance(request_config, dict):
        return True
    return _normalize_visual_lane_mode_for_visibility(request_config.get("visual_lane_mode")) in _BASELINE_VISIBLE_VISUAL_LANE_MODES


def request_config_runtime_metadata(request_config: Any, *, summary: Any = None) -> dict[str, str]:
    if not isinstance(request_config, dict):
        visual_lane_mode = "baseline"
        requested_document_processing_engine = _DOCUMENT_PROCESSING_ENGINE_BASELINE
    else:
        visual_lane_mode = _normalize_visual_lane_mode_for_visibility(request_config.get("visual_lane_mode"))
        requested_document_processing_engine = _normalize_document_processing_engine_for_visibility(
            request_config.get("document_processing_engine")
        )
    document_processing_engine, document_processing_engine_source = _effective_document_processing_engine(
        request_config=request_config,
        summary=summary,
        requested_document_processing_engine=requested_document_processing_engine,
    )
    variant_kind = (
        _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
        if document_processing_engine == _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
        else classify_visual_lane_mode(visual_lane_mode)
    )
    return {
        "visual_lane_mode": visual_lane_mode,
        "document_processing_engine": document_processing_engine,
        "requested_document_processing_engine": requested_document_processing_engine,
        "document_processing_engine_source": document_processing_engine_source,
        "variant_kind": variant_kind or "baseline",
    }


def classify_request_config_variant(request_config: Any) -> str | None:
    if not isinstance(request_config, dict):
        return "baseline"
    metadata = request_config_runtime_metadata(request_config)
    if metadata["document_processing_engine"] == _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B:
        return _DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    return classify_visual_lane_mode(request_config.get("visual_lane_mode"))


def connector_run_is_baseline_visible(run: Any) -> bool:
    if run is None:
        return True
    return request_config_is_baseline_visible(getattr(run, "request_config_json", None))


@lru_cache(maxsize=0)
def _load_binding_request_config_json(database_path_str: str, run_id: str) -> dict[str, Any] | None:
    database_path = Path(database_path_str).resolve()
    if not database_path.exists() or not database_path.is_file():
        return None

    uri_path = f"file:{database_path.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri_path, uri=True, check_same_thread=False)
    except sqlite3.DatabaseError:
        return None

    try:
        row = connection.execute(
            """
            SELECT request_config_json
            FROM connector_run
            WHERE connector_run_id = ?
              AND connector_key = ?
            LIMIT 1
            """,
            (run_id, "nrc_adams_aps"),
        ).fetchone()
    except sqlite3.DatabaseError:
        return None
    finally:
        connection.close()

    if row is None:
        return None

    raw_value = row[0]
    if isinstance(raw_value, dict):
        return dict(raw_value)
    if raw_value in {None, ""}:
        return {}
    if isinstance(raw_value, bytes):
        try:
            raw_value = raw_value.decode("utf-8")
        except UnicodeDecodeError:
            return {}
    if isinstance(raw_value, str):
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return dict(payload) if isinstance(payload, dict) else {}
    return {}


def binding_is_baseline_visible(binding: ReviewRuntimeBinding) -> bool:
    if binding.database_path is None:
        return True
    try:
        request_config = _load_binding_request_config_json(str(binding.database_path.resolve()), binding.run_id)
    except OSError:
        return True
    if request_config is None:
        return True
    return request_config_is_baseline_visible(request_config)


def classify_runtime_binding_variant(binding: ReviewRuntimeBinding) -> str | None:
    return runtime_binding_request_metadata(binding)["variant_kind"]


def runtime_binding_request_metadata(binding: ReviewRuntimeBinding) -> dict[str, str]:
    if binding.database_path is None:
        return request_config_runtime_metadata(None, summary=binding.summary)
    try:
        request_config = _load_binding_request_config_json(str(binding.database_path.resolve()), binding.run_id)
    except OSError:
        return request_config_runtime_metadata(None, summary=binding.summary)
    if request_config is None:
        return request_config_runtime_metadata(None, summary=binding.summary)
    return request_config_runtime_metadata(request_config, summary=binding.summary)


def get_allowlisted_roots() -> list[Path]:
    service_path = Path(__file__).resolve()
    return candidate_review_runtime_roots(
        app_root=service_path.parents[1],
        backend_root=service_path.parents[2],
        storage_dir=settings.storage_dir,
    )


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


def _candidate_database_paths(review_root: Path, summary: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []

    raw_database_path = str(summary.get("database_path") or "").strip()
    if raw_database_path:
        candidates.append(Path(raw_database_path))

    raw_database_url = str(summary.get("database_url") or "").strip()
    sqlite_prefix = "sqlite:///"
    if raw_database_url.startswith(sqlite_prefix):
        candidates.append(Path(raw_database_url[len(sqlite_prefix) :]))

    candidates.append(review_root / "lc.db")

    deduped: dict[str, Path] = {}
    for candidate in candidates:
        try:
            deduped[str(candidate.resolve())] = candidate.resolve()
        except OSError:
            continue
    return list(deduped.values())


def resolve_runtime_database_path(review_root: Path, summary: dict[str, Any]) -> Path | None:
    for candidate in _candidate_database_paths(review_root, summary):
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _candidate_storage_dirs(review_root: Path, summary: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []

    raw_storage_dir = str(summary.get("storage_dir") or "").strip()
    if raw_storage_dir:
        candidates.append(Path(raw_storage_dir))

    candidates.append(review_root / "storage")

    deduped: dict[str, Path] = {}
    for candidate in candidates:
        try:
            deduped[str(candidate.resolve())] = candidate.resolve()
        except OSError:
            continue
    return list(deduped.values())


def resolve_runtime_storage_dir(review_root: Path, summary: dict[str, Any]) -> Path | None:
    for candidate in _candidate_storage_dirs(review_root, summary):
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _explicit_binding(review_root: Path, run_id: str) -> ReviewRuntimeBinding:
    resolved_root = review_root.resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        raise FileNotFoundError(f"Review root does not exist: {resolved_root}")

    summary = load_summary(resolved_root)
    summary_run_id = str(summary.get("run_id") or "").strip()
    if str(summary.get("schema_id") or "").strip() != "aps.local_corpus_e2e_summary.v1":
        raise ValueError(f"Review root summary is not aps.local_corpus_e2e_summary.v1: {resolved_root}")
    if not summary_run_id:
        raise ValueError(f"Review root summary is missing run_id: {resolved_root}")
    if summary_run_id != run_id:
        raise ValueError(f"Review root run_id {summary_run_id} does not match requested run_id {run_id}")

    database_path = resolve_runtime_database_path(resolved_root, summary)
    if database_path is None:
        raise FileNotFoundError(f"Review runtime database is missing for run {run_id}: {resolved_root}")
    storage_dir = resolve_runtime_storage_dir(resolved_root, summary)
    if storage_dir is None:
        raise FileNotFoundError(f"Review runtime storage dir is missing for run {run_id}: {resolved_root}")

    return ReviewRuntimeBinding(
        run_id=run_id,
        review_root=resolved_root,
        summary=summary,
        database_path=database_path.resolve(),
        storage_dir=storage_dir.resolve(),
    )


def resolve_runtime_binding_for_run(*, run_id: str, review_root: str | Path | None = None) -> ReviewRuntimeBinding:
    requested_run_id = str(run_id or "").strip()
    if not requested_run_id:
        raise ValueError("run_id is required")

    if review_root is not None and str(review_root).strip():
        return _explicit_binding(Path(str(review_root).strip()), requested_run_id)

    binding = find_runtime_binding_for_run(requested_run_id)
    if binding is None:
        raise FileNotFoundError(f"Review root not found for run {requested_run_id}")
    if binding.database_path is None:
        raise FileNotFoundError(f"Review runtime database is missing for run {requested_run_id}")
    if binding.storage_dir is None:
        raise FileNotFoundError(f"Review runtime storage dir is missing for run {requested_run_id}")
    return binding


def _binding_sort_key(summary: dict[str, Any]) -> tuple[datetime, str]:
    run_detail = summary.get("run_detail") or {}
    for candidate in (
        run_detail.get("completed_at"),
        (summary.get("submission") or {}).get("submitted_at"),
        summary.get("generated_at_utc"),
    ):
        parsed = parse_iso_datetime(candidate)
        if parsed is not None:
            return parsed, str(candidate or "")
    return datetime.min, ""


def discover_runtime_bindings() -> list[ReviewRuntimeBinding]:
    bindings_by_run_id: dict[str, ReviewRuntimeBinding] = {}
    for root in discover_review_roots():
        try:
            summary = load_summary(root)
        except (json.JSONDecodeError, OSError):
            continue

        run_id = str(summary.get("run_id") or "").strip()
        if not run_id:
            continue

        candidate = ReviewRuntimeBinding(
            run_id=run_id,
            review_root=root,
            summary=summary,
            database_path=resolve_runtime_database_path(root, summary),
            storage_dir=resolve_runtime_storage_dir(root, summary),
        )

        existing = bindings_by_run_id.get(run_id)
        if existing is None or _binding_sort_key(candidate.summary) > _binding_sort_key(existing.summary):
            bindings_by_run_id[run_id] = candidate

    visible_bindings: list[ReviewRuntimeBinding] = []
    for binding in bindings_by_run_id.values():
        if binding_is_baseline_visible(binding):
            visible_bindings.append(binding)
    return visible_bindings


def find_review_root_for_run(run_id: str) -> Path | None:
    binding = find_runtime_binding_for_run(run_id)
    return binding.review_root if binding is not None else None


def find_runtime_binding_for_run(run_id: str) -> ReviewRuntimeBinding | None:
    requested_run_id = str(run_id or "").strip()
    if not requested_run_id:
        return None
    for binding in discover_runtime_bindings():
        if binding.run_id == requested_run_id:
            return binding
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


def is_absolute_path_safe(review_root: Path, absolute_path: Path) -> bool:
    """Verify that an absolute path is strictly within the run's review root."""
    resolved_path = absolute_path.resolve()
    try:
        resolved_path.relative_to(review_root.resolve())
        return True
    except ValueError:
        return False
