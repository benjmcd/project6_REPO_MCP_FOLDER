from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import Any
import fitz

from app.services import nrc_aps_media_detection
from app.services import nrc_aps_csv_parser
from app.services import nrc_aps_spreadsheet_parser
from app.services import nrc_aps_json_parser
from app.services import nrc_aps_sec_edgar_parser
from app.services import nrc_aps_ocr
from app.services import nrc_aps_parser_registry
from app.services import nrc_aps_settings
from app.services import nrc_aps_advanced_ocr
from app.services.nrc_aps_strict_parse import (
    STRICT_PARSE_MAX_CPU_SECONDS,
    STRICT_PARSE_MAX_PAGES,
    STRICT_PARSE_MAX_PEAK_RSS_BYTES,
    STRICT_PARSE_MAX_TABLE_COLUMNS,
    STRICT_PARSE_MAX_TABLE_ROWS,
    STRICT_PARSE_MAX_TEXT_BYTES,
    STRICT_PARSE_PROFILE_ID,
    StrictParseViolation,
)
# Temporary proof collector for next-pass verification (module-level)




APS_DOCUMENT_EXTRACTION_CONTRACT_ID = "aps_document_extraction_v1"
APS_TEXT_NORMALIZATION_CONTRACT_ID = "aps_text_normalization_v2"
APS_PDF_EXTRACTOR_ID = "aps_pdf_text_extractor"
APS_PDF_EXTRACTOR_VERSION = "2.0.0"
APS_PDF_OCR_EXTRACTOR_ID = "aps_pdf_text_ocr_extractor"
APS_PDF_OCR_EXTRACTOR_VERSION = "1.0.0"
APS_TEXT_EXTRACTOR_ID = "aps_text_plain_extractor"
APS_TEXT_EXTRACTOR_VERSION = "2.0.0"
APS_IMAGE_EXTRACTOR_ID = "aps_image_ocr_extractor"
APS_IMAGE_EXTRACTOR_VERSION = "1.0.0"
APS_ZIP_EXTRACTOR_ID = "aps_zip_bundle_extractor"
APS_ZIP_EXTRACTOR_VERSION = "1.0.0"
APS_ODL_PDF_EXTRACTOR_ID = "aps_odl_pdf_extractor"
APS_ODL_PDF_EXPECTED_VERSION = "2.0.0"
APS_QUALITY_STATUS_STRONG = "strong"
APS_QUALITY_STATUS_LIMITED = "limited"
APS_QUALITY_STATUS_WEAK = "weak"
APS_QUALITY_STATUS_UNUSABLE = "unusable"
APS_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/tiff"}
APS_CSV_CONTENT_TYPES = {"text/csv", "application/csv"}
APS_XLSX_CONTENT_TYPES = {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
APS_JSON_CONTENT_TYPES = {"application/json"}
APS_SEC_EDGAR_CONTENT_TYPES = {nrc_aps_sec_edgar_parser.APS_SEC_EDGAR_CONTENT_TYPE}
# Safety limits for ZIP extraction
APS_ZIP_MAX_TOTAL_EXTRACTED_SIZE = 500 * 1024 * 1024  # 500MB
APS_ZIP_MAX_MEMBER_SIZE = 100 * 1024 * 1024  # 100MB
APS_ZIP_MAX_MEMBER_COUNT = 200

# Visual-lane page classification labels
APS_VISUAL_CLASS_DIAGRAM = "diagram_or_visual"
APS_VISUAL_CLASS_TEXT_HEAVY = "text_heavy_or_empty"

APS_VISUAL_LANE_MODE_BASELINE = "baseline"
APS_VISUAL_LANE_MODE_CANDIDATE_A = "candidate_a_page_evidence_v1"
APS_VISUAL_LANE_MODE_CANDIDATE_B = "candidate_b_opendataloader_page_evidence_v1"
_ADMITTED_VISUAL_LANE_MODES: frozenset[str] = frozenset(
    {
        APS_VISUAL_LANE_MODE_BASELINE,
        APS_VISUAL_LANE_MODE_CANDIDATE_A,
        APS_VISUAL_LANE_MODE_CANDIDATE_B,
    }
)
APS_DOCUMENT_PROCESSING_ENGINE_BASELINE = "baseline"
APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B = "candidate_b_opendataloader_pdf"
_ADMITTED_DOCUMENT_PROCESSING_ENGINES: frozenset[str] = frozenset(
    {
        APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
    }
)

# Minimum drawing-command count to consider a page visually significant
_VISUAL_DRAWING_THRESHOLD = 20


def _has_significant_visual_content(page: Any) -> bool:
    """Return True if *page* contains significant vector drawings or large images."""
    # Check embedded images (reuse the same size threshold as has_significant_image)
    images = page.get_images()
    if any(img[2] >= 100 and img[3] >= 100 for img in images):
        return True
    # Check vector drawing commands
    try:
        drawings = page.get_drawings()
        if len(drawings) >= _VISUAL_DRAWING_THRESHOLD:
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _classify_visual_page(
    native_quality_status: str,
    has_visual: bool,
) -> str:
    """Classify a page for the visual-preservation lane.

    Returns APS_VISUAL_CLASS_DIAGRAM when the page is preserve-eligible
    (visually significant AND text extraction is weak/unusable), or
    APS_VISUAL_CLASS_TEXT_HEAVY otherwise (skip / no-op).
    """
    if has_visual and native_quality_status in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE}:
        return APS_VISUAL_CLASS_DIAGRAM
    return APS_VISUAL_CLASS_TEXT_HEAVY


def _normalize_visual_lane_mode(value: Any) -> str:
    visual_lane_mode = str(value or "baseline").strip().lower() or "baseline"
    if visual_lane_mode not in _ADMITTED_VISUAL_LANE_MODES:
        return "baseline"
    return visual_lane_mode


def _normalize_document_processing_engine(value: Any) -> str:
    processing_engine = str(value or APS_DOCUMENT_PROCESSING_ENGINE_BASELINE).strip().lower() or APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
    if processing_engine not in _ADMITTED_DOCUMENT_PROCESSING_ENGINES:
        return APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
    return processing_engine


def _coerce_document_processing_engine_explicit(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "explicit"}
    return bool(value)


def _document_processing_engine_supplied(config: dict[str, Any]) -> bool:
    if "document_processing_engine_explicit" in config:
        return _coerce_document_processing_engine_explicit(config.get("document_processing_engine_explicit"))
    return bool(str(config.get("document_processing_engine") or "").strip())


def _default_document_processing_engine_for_content_type(effective_content_type: Any) -> str:
    if str(effective_content_type or "").strip().lower() == "application/pdf":
        return APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
    return APS_DOCUMENT_PROCESSING_ENGINE_BASELINE


def _resolve_document_processing_engine(config: dict[str, Any], *, effective_content_type: Any) -> str:
    if _document_processing_engine_supplied(config):
        processing_engine = _normalize_document_processing_engine(config.get("document_processing_engine"))
        if (
            processing_engine == APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
            and str(effective_content_type or "").strip().lower() != "application/pdf"
        ):
            return APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
        return processing_engine
    if _normalize_visual_lane_mode(config.get("visual_lane_mode")) == APS_VISUAL_LANE_MODE_CANDIDATE_A:
        return APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
    return _default_document_processing_engine_for_content_type(effective_content_type)


def _parser_registry_fields(config: dict[str, Any]) -> dict[str, Any]:
    entry = dict(config.get("_parser_registry_entry") or {})
    return {
        "parser_registry_contract_id": entry.get("parser_registry_contract_id"),
        "parser_registry_version": entry.get("parser_registry_version"),
        "parser_admission_status": entry.get("parser_admission_status"),
        "parser_family": entry.get("parser_family"),
        "parser_output_family": entry.get("parser_output_family"),
        "parser_contract_id": entry.get("parser_contract_id"),
    }


def _capture_visual_page_ref(page: Any, page_number: int, visual_page_class: str) -> dict[str, Any]:
    """Build a visual-page reference dict.  Accesses page.rect as lightweight
    proof that the page is readable for visual preservation.  Raises on failure."""
    rect = page.rect
    return {
        "page_number": page_number,
        "visual_page_class": visual_page_class,
        "status": "preserved",
        "width": float(rect.width),
        "height": float(rect.height),
    }


APS_VISUAL_ARTIFACT_NAMESPACE = "nrc_adams_aps/visual_pages/sha256"
APS_VISUAL_RENDER_DPI_DEFAULT = 150
APS_VISUAL_ARTIFACT_FORMAT = "png"
APS_VISUAL_ARTIFACT_SEMANTICS = "whole_page_rasterization"


def _write_visual_page_artifact(
    *,
    artifact_storage_dir: str | Path,
    page: Any,
    page_number: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Render a PDF page to PNG at a standard DPI, store content-addressed, and
    return artifact metadata including a storage-stable canonical reference.

    The returned ``visual_artifact_ref`` is a storage-relative path suitable for
    downstream consumers — NOT a machine-local absolute filesystem path.
    """
    dpi = int(config.get("visual_render_dpi") or APS_VISUAL_RENDER_DPI_DEFAULT)
    pixmap = page.get_pixmap(dpi=dpi)
    png_bytes: bytes = pixmap.tobytes(output="png")

    digest = hashlib.sha256(png_bytes).hexdigest()
    rel_path = f"{APS_VISUAL_ARTIFACT_NAMESPACE}/{digest[0:2]}/{digest[2:4]}/{digest}.png"
    absolute = Path(artifact_storage_dir) / rel_path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    if not absolute.exists():
        fd, tmp_name = tempfile.mkstemp(dir=str(absolute.parent), prefix="._", suffix=".tmp")
        temp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(png_bytes)
            os.replace(temp, absolute)
        except Exception:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
    return {
        "visual_artifact_ref": rel_path.replace("\\", "/"),
        "visual_artifact_sha256": digest,
        "visual_artifact_dpi": dpi,
        "visual_artifact_format": APS_VISUAL_ARTIFACT_FORMAT,
        "visual_artifact_semantics": APS_VISUAL_ARTIFACT_SEMANTICS,
    }


def _run_baseline_visual_lane(
    *,
    page: Any,
    page_number: int,
    pre_branch_native_quality_status: str,
    config: dict[str, Any],
) -> tuple[str, dict[str, Any] | None, list[str]]:
    has_visual = _has_significant_visual_content(page)
    visual_page_class = _classify_visual_page(
        native_quality_status=pre_branch_native_quality_status,
        has_visual=has_visual,
    )
    visual_ref: dict[str, Any] | None = None
    visual_degradation_codes: list[str] = []
    if visual_page_class == APS_VISUAL_CLASS_DIAGRAM:
        try:
            ref = _capture_visual_page_ref(page, page_number, visual_page_class)
            _art_dir = str(config.get("artifact_storage_dir") or "").strip()
            if _art_dir:
                try:
                    artifact = _write_visual_page_artifact(
                        artifact_storage_dir=_art_dir,
                        page=page,
                        page_number=page_number,
                        config=config,
                    )
                    ref.update(artifact)
                except Exception:  # noqa: BLE001
                    ref["status"] = "visual_capture_failed"
                    visual_degradation_codes.append("visual_artifact_failed")
            visual_ref = ref
        except Exception:  # noqa: BLE001
            visual_ref = {
                "page_number": page_number,
                "visual_page_class": visual_page_class,
                "status": "visual_capture_failed",
            }
            visual_degradation_codes.append("visual_capture_failed")
    return visual_page_class, visual_ref, visual_degradation_codes


def _run_candidate_a_visual_lane(
    *,
    page: Any,
    page_number: int,
    pre_branch_native_quality_status: str,
    config: dict[str, Any],
) -> tuple[str, dict[str, Any] | None, list[str]]:
    """Candidate A visual lane: uses PageEvidence geometry/coverage signals
    instead of baseline's pixel-threshold heuristic for the has_visual decision.
    Classification and preservation path remain baseline."""
    try:
        from app.services import nrc_aps_page_evidence
        evidence = nrc_aps_page_evidence.analyze_pdf_page_evidence(
            page=page,
            page_number=page_number,
        )
        has_visual = (
            bool(evidence.get("image_count") or evidence.get("drawing_count"))
            or float(evidence.get("combined_visual_coverage_ratio", 0))
            >= float(evidence.get("visual_coverage_threshold", 0.15))
        )
    except Exception:  # noqa: BLE001
        return _run_baseline_visual_lane(
            page=page,
            page_number=page_number,
            pre_branch_native_quality_status=pre_branch_native_quality_status,
            config=config,
        )

    visual_page_class = _classify_visual_page(
        native_quality_status=pre_branch_native_quality_status,
        has_visual=has_visual,
    )
    visual_ref: dict[str, Any] | None = None
    visual_degradation_codes: list[str] = []
    if visual_page_class == APS_VISUAL_CLASS_DIAGRAM:
        try:
            ref = _capture_visual_page_ref(page, page_number, visual_page_class)
            _art_dir = str(config.get("artifact_storage_dir") or "").strip()
            if _art_dir:
                try:
                    artifact = _write_visual_page_artifact(
                        artifact_storage_dir=_art_dir,
                        page=page,
                        page_number=page_number,
                        config=config,
                    )
                    ref.update(artifact)
                except Exception:  # noqa: BLE001
                    ref["status"] = "visual_capture_failed"
                    visual_degradation_codes.append("visual_artifact_failed")
            visual_ref = ref
        except Exception:  # noqa: BLE001
            visual_ref = {
                "page_number": page_number,
                "visual_page_class": visual_page_class,
                "status": "visual_capture_failed",
            }
            visual_degradation_codes.append("visual_capture_failed")
    return visual_page_class, visual_ref, visual_degradation_codes


def default_processing_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    incoming = dict(overrides or {})
    config = {
        "content_sniff_bytes": 4096,
        "content_parse_max_pages": 500,
        "content_parse_timeout_seconds": 30,
        "ocr_enabled": True,
        "ocr_max_pages": 50,
        "ocr_render_dpi": 300,
        "ocr_language": "eng",
        "ocr_timeout_seconds": 120,
        "content_min_searchable_chars": 200,
        "content_min_searchable_tokens": 30,
        "csv_parse_max_bytes": 5_000_000,
        "csv_parse_max_rows": 10_000,
        "csv_parse_max_columns": 200,
        "xlsx_parse_max_bytes": 5_000_000,
        "xlsx_parse_max_rows": 10_000,
        "xlsx_parse_max_columns": 200,
        "xlsx_selected_sheet_name": None,
        "json_parse_max_bytes": 5_000_000,
        "json_parse_max_rows": 10_000,
        "json_parse_max_columns": 200,
        "json_record_path": None,
        "sec_edgar_parse_max_bytes": 10_000_000,
        "sec_edgar_parse_max_rows": 10_000,
        "sec_edgar_parse_max_columns": 200,
        "sec_edgar_admitted_form_types": ["10-K", "10-Q", "8-K"],
        "visual_render_dpi": APS_VISUAL_RENDER_DPI_DEFAULT,
        "visual_lane_mode": APS_VISUAL_LANE_MODE_BASELINE,
        "document_processing_engine": APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
        "document_processing_engine_explicit": False,
        "strict_parse_profile": None,
    }
    config.update(incoming)
    if "document_processing_engine_explicit" not in incoming:
        config["document_processing_engine_explicit"] = bool(
            str(incoming.get("document_processing_engine") or "").strip()
        )
    return config


def _normalize_upper_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [value]
    result: list[str] = []
    for item in raw_values:
        normalized = str(item or "").strip().upper()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _deadline_from_config(config: dict[str, Any]) -> float | None:
    timeout_seconds = float(config.get("content_parse_timeout_seconds") or 0)
    if timeout_seconds <= 0:
        return None
    return time.monotonic() + timeout_seconds


def _raise_if_deadline_exceeded(deadline: float | None) -> None:
    if deadline is None:
        return
    if time.monotonic() > float(deadline):
        raise ValueError("content_parse_timeout_exceeded")


def _strict_parse_profile_enabled(config: dict[str, Any] | None) -> bool:
    return (
        config is not None
        and config.get("strict_parse_profile") == STRICT_PARSE_PROFILE_ID
    )


def _load_advanced_table_parser() -> Any:
    return importlib.import_module("app.services.nrc_aps_advanced_table_parser")


def _peak_rss_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.restype = wintypes.HANDLE
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        get_process_memory_info.restype = wintypes.BOOL
        process = get_current_process()
        if not get_process_memory_info(
            process,
            ctypes.byref(counters),
            counters.cb,
        ):
            raise StrictParseViolation("strict_memory_measurement_failed")
        return int(counters.PeakWorkingSetSize)

    try:
        resource_module: Any = importlib.import_module("resource")
    except ImportError as exc:
        raise StrictParseViolation("strict_memory_measurement_unavailable") from exc

    peak_rss = int(
        resource_module.getrusage(resource_module.RUSAGE_SELF).ru_maxrss
    )
    # macOS reports bytes; Linux and other supported Unix runtimes report KiB.
    return peak_rss if sys.platform == "darwin" else peak_rss * 1024


def _strict_parse_checkpoint(
    config: dict[str, Any],
    *,
    deadline: float | None,
    cpu_started_at: float,
) -> None:
    if not _strict_parse_profile_enabled(config):
        return
    _raise_if_deadline_exceeded(deadline)
    if _peak_rss_bytes() > STRICT_PARSE_MAX_PEAK_RSS_BYTES:
        raise StrictParseViolation("strict_memory_limit_exceeded")
    if time.process_time() - cpu_started_at > STRICT_PARSE_MAX_CPU_SECONDS:
        raise StrictParseViolation("strict_cpu_limit_exceeded")


def _strict_parse_checkpoint_or_close(
    document: Any,
    config: dict[str, Any],
    *,
    deadline: float | None,
    cpu_started_at: float,
) -> None:
    try:
        _strict_parse_checkpoint(
            config,
            deadline=deadline,
            cpu_started_at=cpu_started_at,
        )
    except Exception:
        document.close()
        raise


def _pdf_deadline_checkpoint_or_close(
    document: Any,
    deadline: float | None,
    *,
    strict_parse: bool,
) -> None:
    try:
        _raise_if_deadline_exceeded(deadline)
    except ValueError:
        if strict_parse:
            document.close()
        raise


def process_document(
    *,
    content: bytes,
    declared_content_type: Any,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = default_processing_config(config)
    deadline = _deadline_from_config(config)
    detection = nrc_aps_media_detection.detect_media_type(
        content,
        declared_content_type=declared_content_type,
        sniff_bytes=int(config["content_sniff_bytes"]),
        source_filename=config.get("source_filename", ""),
    )
    effective_type = str(detection.get("effective_content_type") or "")
    if not bool(detection.get("supported_for_processing")):
        raise ValueError(f"unsupported_content_type:{effective_type or 'unknown'}")
    if not content:
        raise ValueError("empty_content")
    requested_processing_engine = _normalize_document_processing_engine(config.get("document_processing_engine"))
    requested_processing_engine_explicit = _document_processing_engine_supplied(config)
    processing_engine = _resolve_document_processing_engine(config, effective_content_type=effective_type)
    processing_engine_explicit = requested_processing_engine_explicit
    config = {
        **config,
        "document_processing_engine": processing_engine,
        "document_processing_engine_explicit": processing_engine_explicit,
        "_requested_document_processing_engine": requested_processing_engine,
        "_requested_document_processing_engine_explicit": requested_processing_engine_explicit,
    }
    parser_entry = nrc_aps_parser_registry.resolve_parser(
        effective_content_type=effective_type,
        document_processing_engine=processing_engine,
        supported_for_processing=detection.get("supported_for_processing"),
    )
    if (
        parser_entry.get("parser_admission_status") != nrc_aps_parser_registry.APS_PARSER_ADMISSION_STATUS_ADMITTED
        and processing_engine == APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
        and not processing_engine_explicit
    ):
        failure_code = str(parser_entry.get("parser_failure_code") or effective_type or "unknown")
        processing_engine = APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
        parser_entry = nrc_aps_parser_registry.resolve_parser(
            effective_content_type=effective_type,
            document_processing_engine=processing_engine,
            supported_for_processing=detection.get("supported_for_processing"),
        )
        config = {
            **config,
            "document_processing_engine": processing_engine,
            "candidate_b_default_fallback_reason": f"parser_admission:{failure_code}",
            "_parser_registry_entry": parser_entry,
        }
    else:
        config = {**config, "_parser_registry_entry": parser_entry}
    if parser_entry.get("parser_admission_status") != nrc_aps_parser_registry.APS_PARSER_ADMISSION_STATUS_ADMITTED:
        failure_code = str(parser_entry.get("parser_failure_code") or effective_type or "unknown")
        raise ValueError(f"unsupported_parser:{failure_code}")
    _raise_if_deadline_exceeded(deadline)
    if effective_type in APS_CSV_CONTENT_TYPES:
        return _process_csv(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type in APS_XLSX_CONTENT_TYPES:
        return _process_xlsx(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type in APS_JSON_CONTENT_TYPES:
        return _process_json(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type in APS_SEC_EDGAR_CONTENT_TYPES:
        return _process_sec_edgar(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type == "text/plain":
        return _process_plain_text(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type == "application/pdf":
        if processing_engine == APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B:
            try:
                return _process_pdf_candidate_b(content=content, detection=detection, config=config, deadline=deadline)
            except ValueError as exc:
                if processing_engine_explicit:
                    raise
                fallback_config = {
                    **config,
                    "document_processing_engine": APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
                    "candidate_b_default_fallback_reason": str(exc),
                }
                fallback_parser_entry = nrc_aps_parser_registry.resolve_parser(
                    effective_content_type=effective_type,
                    document_processing_engine=APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
                    supported_for_processing=detection.get("supported_for_processing"),
                )
                fallback_config = {**fallback_config, "_parser_registry_entry": fallback_parser_entry}
                return _process_pdf(content=content, detection=detection, config=fallback_config, deadline=deadline)
        return _process_pdf(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type in APS_IMAGE_CONTENT_TYPES:
        return _process_image(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type == "application/zip":
        return _process_zip(content=content, detection=detection, config=config, deadline=deadline)
    raise ValueError(f"unsupported_content_type:{effective_type or 'unknown'}")


def _process_csv(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    parsed = nrc_aps_csv_parser.parse_csv_table(
        content=content,
        max_bytes=int(config["csv_parse_max_bytes"]),
        max_rows=int(config["csv_parse_max_rows"]),
        max_columns=int(config["csv_parse_max_columns"]),
    )
    _raise_if_deadline_exceeded(deadline)
    normalized_text = ""
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "csv_table",
        "extractor_id": nrc_aps_csv_parser.APS_CSV_PARSER_ID,
        "extractor_version": nrc_aps_csv_parser.APS_CSV_PARSER_VERSION,
        "normalization_contract_id": None,
        "typed_content_contract_id": nrc_aps_csv_parser.APS_CSV_TABLE_CONTRACT_ID,
        "document_class": "delimited_table",
        "page_count": 1,
        "quality_status": APS_QUALITY_STATUS_STRONG,
        "quality_metrics": {
            "quality_status": APS_QUALITY_STATUS_STRONG,
            "row_count": parsed["row_count"],
            "column_count": parsed["column_count"],
        },
        "degradation_codes": _degradation_codes_for_detection(detection, APS_QUALITY_STATUS_STRONG),
        "ordered_units": [],
        "table_units": parsed["table_units"],
        "time_series_units": parsed["time_series_units"],
        "table_diagnostics": {
            "csv_table_contract_id": parsed["csv_table_contract_id"],
            "encoding": parsed["encoding"],
            "delimiter": parsed["delimiter"],
            "header_present": parsed["header_present"],
            "row_count": parsed["row_count"],
            "column_count": parsed["column_count"],
            "null_markers": parsed["null_markers"],
            "columns": parsed["columns"],
            "numeric_columns": parsed["numeric_columns"],
            "time_column_candidates": parsed["time_column_candidates"],
        },
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": 0,
    }


def _process_xlsx(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    parsed = nrc_aps_spreadsheet_parser.parse_xlsx_workbook(
        content=content,
        max_bytes=int(config["xlsx_parse_max_bytes"]),
        max_rows=int(config["xlsx_parse_max_rows"]),
        max_columns=int(config["xlsx_parse_max_columns"]),
        selected_sheet_name=config.get("xlsx_selected_sheet_name"),
    )
    _raise_if_deadline_exceeded(deadline)
    normalized_text = ""
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "xlsx_workbook",
        "extractor_id": nrc_aps_spreadsheet_parser.APS_XLSX_PARSER_ID,
        "extractor_version": nrc_aps_spreadsheet_parser.APS_XLSX_PARSER_VERSION,
        "normalization_contract_id": None,
        "typed_content_contract_id": nrc_aps_spreadsheet_parser.APS_XLSX_TABLE_CONTRACT_ID,
        "document_class": "spreadsheet_table",
        "page_count": 1,
        "quality_status": APS_QUALITY_STATUS_STRONG,
        "quality_metrics": {
            "quality_status": APS_QUALITY_STATUS_STRONG,
            "row_count": parsed["row_count"],
            "column_count": parsed["column_count"],
            "workbook_sheet_count": parsed["workbook_metadata"]["sheet_count"],
        },
        "degradation_codes": _degradation_codes_for_detection(detection, APS_QUALITY_STATUS_STRONG),
        "ordered_units": [],
        "table_units": parsed["table_units"],
        "time_series_units": parsed["time_series_units"],
        "workbook_units": [
            {
                "unit_kind": "workbook",
                **parsed["workbook_metadata"],
            }
        ],
        "table_diagnostics": {
            "xlsx_table_contract_id": parsed["xlsx_table_contract_id"],
            "workbook_metadata": parsed["workbook_metadata"],
            "header_present": parsed["header_present"],
            "row_count": parsed["row_count"],
            "column_count": parsed["column_count"],
            "null_markers": [],
            "columns": parsed["columns"],
            "numeric_columns": parsed["numeric_columns"],
            "time_column_candidates": parsed["time_column_candidates"],
        },
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": 0,
    }


def _process_json(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    parsed = nrc_aps_json_parser.parse_json_recordset(
        content=content,
        max_bytes=int(config["json_parse_max_bytes"]),
        max_rows=int(config["json_parse_max_rows"]),
        max_columns=int(config["json_parse_max_columns"]),
        record_path=config.get("json_record_path"),
    )
    _raise_if_deadline_exceeded(deadline)
    normalized_text = ""
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "json_recordset",
        "extractor_id": nrc_aps_json_parser.APS_JSON_PARSER_ID,
        "extractor_version": nrc_aps_json_parser.APS_JSON_PARSER_VERSION,
        "normalization_contract_id": None,
        "typed_content_contract_id": nrc_aps_json_parser.APS_JSON_RECORDSET_CONTRACT_ID,
        "document_class": "json_recordset",
        "page_count": 1,
        "quality_status": APS_QUALITY_STATUS_STRONG,
        "quality_metrics": {
            "quality_status": APS_QUALITY_STATUS_STRONG,
            "row_count": parsed["row_count"],
            "column_count": parsed["column_count"],
        },
        "degradation_codes": _degradation_codes_for_detection(detection, APS_QUALITY_STATUS_STRONG),
        "ordered_units": [],
        "table_units": parsed["table_units"],
        "time_series_units": parsed["time_series_units"],
        "table_diagnostics": {
            "json_recordset_contract_id": parsed["json_recordset_contract_id"],
            "record_path": parsed["record_path"],
            "row_count": parsed["row_count"],
            "column_count": parsed["column_count"],
            "columns": parsed["columns"],
            "numeric_columns": parsed["numeric_columns"],
            "time_column_candidates": parsed["time_column_candidates"],
        },
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": 0,
    }


def _process_sec_edgar(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    parsed = nrc_aps_sec_edgar_parser.parse_sec_edgar_filing(
        content=content,
        max_bytes=int(config["sec_edgar_parse_max_bytes"]),
        max_rows=int(config["sec_edgar_parse_max_rows"]),
        max_columns=int(config["sec_edgar_parse_max_columns"]),
        admitted_form_types=_normalize_upper_string_list(config.get("sec_edgar_admitted_form_types")),
    )
    _raise_if_deadline_exceeded(deadline)
    normalized_text = str(parsed["normalized_text"] or "")
    quality = _quality_metrics(
        normalized_text,
        min_chars=int(config["content_min_searchable_chars"]),
        min_tokens=int(config["content_min_searchable_tokens"]),
    )
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "sec_edgar_filing",
        "extractor_id": nrc_aps_sec_edgar_parser.APS_SEC_EDGAR_PARSER_ID,
        "extractor_version": nrc_aps_sec_edgar_parser.APS_SEC_EDGAR_PARSER_VERSION,
        "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "typed_content_contract_id": nrc_aps_sec_edgar_parser.APS_SEC_EDGAR_FILING_CONTRACT_ID,
        "document_class": "sec_edgar_filing",
        "page_count": max(1, int(parsed["document_count"] or 1)),
        "quality_status": quality["quality_status"],
        "quality_metrics": {
            **quality,
            "document_count": parsed["document_count"],
            "section_count": parsed["section_count"],
            "table_count": parsed["table_count"],
        },
        "degradation_codes": _degradation_codes_for_detection(detection, quality["quality_status"]),
        "ordered_units": parsed["ordered_units"],
        "page_summaries": [
            {
                "page_number": 1,
                "source": "sec_edgar_filing",
                **quality,
            }
        ],
        "filing_units": [
            {
                "unit_kind": "sec_edgar_filing",
                "filing_metadata": parsed["filing_metadata"],
                "documents": parsed["documents"],
                "document_count": parsed["document_count"],
                "section_count": parsed["section_count"],
                "table_count": parsed["table_count"],
            }
        ],
        "table_units": parsed["table_units"],
        "time_series_units": parsed["time_series_units"],
        "table_diagnostics": {
            "sec_edgar_filing_contract_id": parsed["sec_edgar_filing_contract_id"],
            "filing_metadata": parsed["filing_metadata"],
            "table_count": parsed["table_count"],
            "time_column_candidates": parsed["time_column_candidates"],
            "tables": parsed["table_diagnostics"],
        },
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }


def _process_plain_text(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    decoded = _decode_plain_text(content)
    _raise_if_deadline_exceeded(deadline)
    normalized_text = _normalize_text(decoded)
    _raise_if_deadline_exceeded(deadline)
    quality = _quality_metrics(
        normalized_text,
        min_chars=int(config["content_min_searchable_chars"]),
        min_tokens=int(config["content_min_searchable_tokens"]),
    )
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "plain_text",
        "extractor_id": APS_TEXT_EXTRACTOR_ID,
        "extractor_version": APS_TEXT_EXTRACTOR_VERSION,
        "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "document_class": "text_plain",
        "page_count": 1,
        "quality_status": quality["quality_status"],
        "quality_metrics": quality,
        "degradation_codes": _degradation_codes_for_detection(detection, quality["quality_status"]),
        "ordered_units": [
            {
                "page_number": 1,
                "unit_kind": "text_block",
                "text": normalized_text,
                "start_char": 0,
                "end_char": len(normalized_text),
            }
        ]
        if normalized_text
        else [],
        "page_summaries": [
            {
                "page_number": 1,
                "source": "plain_text",
                **quality,
            }
        ],
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }


def _process_image(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    if not nrc_aps_ocr.tesseract_available():
        raise ValueError("ocr_required_but_unavailable")

    all_units: list[dict[str, Any]] = []
    page_summaries: list[dict[str, Any]] = []
    degradation_codes = _degradation_codes_for_detection(detection, None)
    # Try to open as a document (supports multi-page TIFF)
    doc = None
    try:
        doc = fitz.open(stream=content, filetype=detection.get("sniffed_content_type", "").split("/")[-1])
        is_document = True
    except Exception:
        is_document = False

    if is_document:
        try:
            page_count = int(doc.page_count)
            if page_count > int(config.get("content_parse_max_pages", 200)):
                raise ValueError("image_page_limit_exceeded")

            for page_index in range(page_count):
                _raise_if_deadline_exceeded(deadline)
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=int(config.get("ocr_render_dpi", 300)))
                page_bytes = pix.tobytes("png")
                
                try:
                    ocr_payload = nrc_aps_ocr.run_tesseract_ocr(
                        image_bytes=page_bytes,
                        language=str(config.get("ocr_language", "eng")),
                        dpi=int(config.get("ocr_render_dpi", 300)),
                        timeout_seconds=int(config.get("ocr_timeout_seconds", 120)),
                    )
                    
                    page_text = _normalize_text(str(ocr_payload.get("text") or ""))
                    page_quality = _quality_metrics(
                        page_text,
                        min_chars=int(config["content_min_searchable_chars"]),
                        min_tokens=int(config["content_min_searchable_tokens"]),
                        average_confidence=ocr_payload.get("average_confidence"),
                    )
                    
                    page_number = page_index + 1
                    if page_text:
                        all_units.append({
                            "page_number": page_number,
                            "unit_kind": "ocr_text",
                            "text": page_text,
                            "start_char": 0,
                            "end_char": len(page_text),
                            "confidence": ocr_payload.get("average_confidence"),
                        })
                    
                    page_summaries.append({
                        "page_number": page_number,
                        "source": "ocr",
                        "ocr_attempted": True,
                        "ocr_available": True,
                        **page_quality,
                    })
                except nrc_aps_ocr.OcrExecutionError as exc:
                    degradation_codes.append(f"ocr_page_failed:{page_index + 1}")
                    continue
        finally:
            doc.close()
    else:
        # Fallback to single-page processing if fitz fails
        try:
            ocr_payload = nrc_aps_ocr.run_tesseract_ocr(
                image_bytes=content,
                language=str(config.get("ocr_language", "eng")),
                dpi=int(config.get("ocr_render_dpi", 300)),
                timeout_seconds=int(config.get("ocr_timeout_seconds", 120)),
            )
            normalized_text = _normalize_text(str(ocr_payload.get("text") or ""))
            quality = _quality_metrics(
                normalized_text,
                min_chars=int(config["content_min_searchable_chars"]),
                min_tokens=int(config["content_min_searchable_tokens"]),
                average_confidence=ocr_payload.get("average_confidence"),
            )
            
            if normalized_text:
                all_units.append({
                    "page_number": 1,
                    "unit_kind": "ocr_text",
                    "text": normalized_text,
                    "start_char": 0,
                    "end_char": len(normalized_text),
                    "confidence": ocr_payload.get("average_confidence"),
                })
            
            page_summaries.append({
                "page_number": 1,
                "source": "ocr",
                "ocr_attempted": True,
                "ocr_available": True,
                **quality,
            })
        except nrc_aps_ocr.OcrExecutionError as exc:
            raise ValueError(f"ocr_execution_failed:{str(exc)}") from exc

    _raise_if_deadline_exceeded(deadline)
    full_text = "\n\n".join(u["text"] for u in all_units)
    normalized_text = _normalize_text(full_text)
    
    # Recalculate aggregate quality metrics
    final_quality = _quality_metrics(
        normalized_text,
        min_chars=int(config["content_min_searchable_chars"]),
        min_tokens=int(config["content_min_searchable_tokens"]),
    )

    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "image_ocr",
        "extractor_id": APS_IMAGE_EXTRACTOR_ID,
        "extractor_version": APS_IMAGE_EXTRACTOR_VERSION,
        "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "document_class": "standalone_image",
        "page_count": len(page_summaries),
        "quality_status": final_quality["quality_status"],
        "quality_metrics": final_quality,
        "degradation_codes": sorted(list(set(degradation_codes))),
        "ordered_units": _with_char_offsets(all_units),
        "page_summaries": page_summaries,
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }


def _process_zip(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    try:
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(content)) as zf:
            infolist = zf.infolist()
            if len(infolist) > APS_ZIP_MAX_MEMBER_COUNT:
                raise ValueError("zip_member_limit_exceeded")

            all_units: list[dict[str, Any]] = []
            table_units: list[dict[str, Any]] = []
            time_series_units: list[dict[str, Any]] = []
            member_summaries: list[dict[str, Any]] = []
            total_extracted_size = 0
            degradation_codes = _degradation_codes_for_detection(detection, None)

            for member in infolist:
                _raise_if_deadline_exceeded(deadline)
                if member.is_dir():
                    continue
                if member.file_size > APS_ZIP_MAX_MEMBER_SIZE:
                    degradation_codes.append(f"zip_member_too_large:{member.filename}")
                    continue

                # Simple extension-based filtering for inner members to avoid infinite recursion or heavy sniffing
                ext = Path(member.filename).suffix.lower()
                extension_content_type = nrc_aps_media_detection.APS_EXTENSION_CONTENT_TYPES.get(ext, "")
                if extension_content_type in APS_CSV_CONTENT_TYPES:
                    try:
                        member_content = zf.read(member)
                        total_extracted_size += len(member_content)
                        if total_extracted_size > APS_ZIP_MAX_TOTAL_EXTRACTED_SIZE:
                            degradation_codes.append("zip_total_size_limit_exceeded")
                            break
                        parsed = nrc_aps_csv_parser.parse_csv_table(
                            content=member_content,
                            max_bytes=int(config["csv_parse_max_bytes"]),
                            max_rows=int(config["csv_parse_max_rows"]),
                            max_columns=int(config["csv_parse_max_columns"]),
                        )
                        member_table_units = [
                            {
                                **unit,
                                "archive_member": member.filename,
                            }
                            for unit in parsed["table_units"]
                        ]
                        member_time_units = [
                            {
                                **unit,
                                "archive_member": member.filename,
                            }
                            for unit in parsed["time_series_units"]
                        ]
                        table_units.extend(member_table_units)
                        time_series_units.extend(member_time_units)
                        member_summaries.append({
                            "filename": member.filename,
                            "status": "typed_table_parsed",
                            "effective_content_type": "text/csv",
                            "row_count": parsed["row_count"],
                            "column_count": parsed["column_count"],
                            "numeric_columns": parsed["numeric_columns"],
                            "time_column_candidates": parsed["time_column_candidates"],
                        })
                    except Exception as exc:  # noqa: BLE001
                        degradation_codes.append(f"archive_member_typed_table_failed:{member.filename}")
                        member_summaries.append({
                            "filename": member.filename,
                            "status": "typed_table_failed",
                            "effective_content_type": "text/csv",
                            "error": str(exc),
                        })
                    continue
                if extension_content_type in nrc_aps_media_detection.APS_TYPED_UNADMITTED_CONTENT_TYPES:
                    degradation_codes.append(f"archive_member_typed_parser_not_admitted:{member.filename}")
                    member_summaries.append({
                        "filename": member.filename,
                        "status": "typed_parser_not_admitted",
                        "effective_content_type": extension_content_type,
                    })
                    continue
                if extension_content_type in nrc_aps_media_detection.APS_REFUSAL_CONTENT_TYPES:
                    degradation_codes.append(f"archive_member_refused:{member.filename}")
                    member_summaries.append({
                        "filename": member.filename,
                        "status": "refused",
                        "effective_content_type": extension_content_type,
                    })
                    continue
                inner_declared = "application/octet-stream"
                if ext == ".pdf":
                    inner_declared = "application/pdf"
                elif ext in {".txt", ".md"}:
                    inner_declared = "text/plain"
                elif ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
                    inner_declared = "image/png" if ext == ".png" else "image/jpeg" # approximation
                else:
                    # Skip unknown members to remain safe
                    continue

                try:
                    member_content = zf.read(member)
                    total_extracted_size += len(member_content)
                    if total_extracted_size > APS_ZIP_MAX_TOTAL_EXTRACTED_SIZE:
                        degradation_codes.append("zip_total_size_limit_exceeded")
                        break

                    requested_engine = _normalize_document_processing_engine(
                        config.get("_requested_document_processing_engine", config.get("document_processing_engine"))
                    )
                    requested_engine_explicit = _coerce_document_processing_engine_explicit(
                        config.get(
                            "_requested_document_processing_engine_explicit",
                            config.get("document_processing_engine_explicit"),
                        )
                    )
                    member_result = process_document(
                        content=member_content,
                        declared_content_type=inner_declared,
                        config={
                            **config,
                            "source_filename": member.filename,
                            "document_processing_engine": (
                                APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
                                if inner_declared == "application/pdf"
                                and requested_engine_explicit
                                and requested_engine == APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B
                                else APS_DOCUMENT_PROCESSING_ENGINE_BASELINE
                            ),
                            "document_processing_engine_explicit": True,
                        },
                    )
                    # Merge units
                    for unit in member_result.get("ordered_units", []):
                        all_units.append({
                            **unit,
                            "archive_member": member.filename
                        })
                    member_summaries.append({
                        "filename": member.filename,
                        "status": "success",
                        "quality": member_result.get("quality_status")
                    })
                except Exception as exc:  # noqa: BLE001
                    degradation_codes.append(f"archive_member_failed:{member.filename}")
                    member_summaries.append({
                        "filename": member.filename,
                        "status": "failed",
                        "error": str(exc)
                    })

            _raise_if_deadline_exceeded(deadline)
            normalized_text = _normalize_text("\n\n".join(str(u.get("text") or "") for u in all_units))
            quality = _quality_metrics(
                normalized_text,
                min_chars=int(config["content_min_searchable_chars"]),
                min_tokens=int(config["content_min_searchable_tokens"]),
            )

            return {
                **detection,
                "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
                **_parser_registry_fields(config),
                "extractor_family": "archive_bundle",
                "extractor_id": APS_ZIP_EXTRACTOR_ID,
                "extractor_version": APS_ZIP_EXTRACTOR_VERSION,
                "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
                "document_class": "archive_bundle",
                "page_count": 1,
                "member_count": len(member_summaries),
                "quality_status": quality["quality_status"],
                "quality_metrics": quality,
                "degradation_codes": sorted(list(dict.fromkeys(code for code in degradation_codes if code))),
                "ordered_units": _with_char_offsets(all_units),
                "table_units": table_units,
                "time_series_units": time_series_units,
                "member_summaries": member_summaries,
                "normalized_text": normalized_text,
                "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
                "normalized_char_count": len(normalized_text),
            }
    except zipfile.BadZipFile as exc:
        raise ValueError("zip_open_failed") from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, ValueError) and str(exc).startswith("zip_"):
            raise
        raise ValueError(f"zip_processing_failed:{str(exc)}") from exc


def _process_pdf(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    strict_parse = _strict_parse_profile_enabled(config)
    strict_cpu_started_at = time.process_time() if strict_parse else 0.0
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("pdf_open_failed") from exc
    _pdf_deadline_checkpoint_or_close(
        document,
        deadline,
        strict_parse=strict_parse,
    )
    
    if document.needs_pass:
        document.close()
        raise ValueError("pdf_encrypted")

    total_pages = int(document.page_count)
    max_pages = int(config.get("content_parse_max_pages", 500))
    if strict_parse and total_pages > STRICT_PARSE_MAX_PAGES:
        document.close()
        raise StrictParseViolation("strict_page_limit_exceeded")
    # Hard cap for stability, but allowing significantly more than before via chunking
    if not strict_parse and total_pages > max_pages * 30:
        document.close()
        raise ValueError("pdf_page_limit_absolute_exceeded")
    if strict_parse:
        config["_strict_table_rows_seen"] = 0

    all_units: list[dict[str, Any]] = []
    page_summaries: list[dict[str, Any]] = []
    degradation_codes: list[str] = _degradation_codes_for_detection(detection, None)
    native_page_count = 0
    ocr_page_count = 0
    weak_page_count = 0
    cumulative_text_bytes = 0
    debug_page_states: list[dict[str, Any]] = []
    visual_page_refs: list[dict[str, Any]] = []
    # Store exact pdf path if provided via config
    exact_pdf_path = config.get("pdf_path") if isinstance(config, dict) else None
    # Reset external proof collector at the start of each PDF processing run
    
    # Temporary per‑page debug state list (local)

    
    # Process in chunks of 100 pages to avoid OOM for layout dicts
    chunk_size = 100
    for chunk_start in range(0, total_pages, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_pages)
        _pdf_deadline_checkpoint_or_close(
            document,
            deadline,
            strict_parse=strict_parse,
        )
        
        for page_index in range(chunk_start, chunk_end):
            _pdf_deadline_checkpoint_or_close(
                document,
                deadline,
                strict_parse=strict_parse,
            )
            page = document.load_page(page_index)
            # Initialize instrumentation flags for this page
            fallback_entered = False
            hybrid_entered = False
            fallback_triggered_by_quality = False
            fallback_triggered_by_advanced_doc = False
            fallback_triggered_by_low_info_without_significant_image = False
            ocr_attempted_fallback = False
            ocr_attempted_hybrid = False
            ocr_text_fallback_nonempty = False
            ocr_text_hybrid_nonempty = False
            new_word_delta = None  # will be set only when meaningful delta exists
            ocr_image_supplement_appended = False
            images_present = False
            # Gather image info early for fallback logic
            images = page.get_images()
            has_significant_image = any(img[2] >= 100 and img[3] >= 100 for img in images)
            images_present = bool(images)
            # Pass full context for doc-type routing and bytes-fallback for Camelot
            try:
                native_units = _extract_native_pdf_units(
                    page,
                    config=config,
                    pdf_content=content,
                )
            except StrictParseViolation:
                document.close()
                raise
            
            native_text = _normalize_text("\n".join(str(item.get("text") or "") for item in native_units if str(item.get("text") or "").strip()))
            native_quality = _quality_metrics(
                native_text,
                min_chars=max(40, int(config["content_min_searchable_chars"]) // 4),
                min_tokens=max(6, int(config["content_min_searchable_tokens"]) // 5),
            )
            pre_branch_native_quality_status = native_quality["quality_status"]
            
            page_number = page_index + 1
            page_units = [dict(item) for item in native_units]
            page_source = "native"
            ocr_attempted = False
            ocr_available = nrc_aps_ocr.tesseract_available()
            
            # Advanced OCR Routing triggers for specific document classes or low-signal native text
            is_advanced_doc = config.get("document_type") in nrc_aps_settings.ADVANCED_OCR_DOC_TYPES
            word_count = len(_normalize_query_tokens(native_text))
            is_low_info = word_count < nrc_aps_settings.OCR_FALLBACK_WORD_THRESHOLD
            
            # OCR Fallback path
            fallback_entered = False
            fallback_triggered_by_quality = native_quality["quality_status"] in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE}
            fallback_triggered_by_advanced_doc = is_advanced_doc
            fallback_triggered_by_low_info_without_significant_image = is_low_info and not has_significant_image
            if native_quality["quality_status"] in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE} or is_advanced_doc or (is_low_info and not has_significant_image):
                fallback_entered = True
                weak_page_count += 1
                if bool(config.get("ocr_enabled", True)) and page_number <= int(config["ocr_max_pages"]):
                    if strict_parse:
                        document.close()
                        raise StrictParseViolation("strict_ocr_path_refused")
                    ocr_attempted = True
                    ocr_attempted_fallback = True
                    try:
                        try:
                            ocr_payload = nrc_aps_advanced_ocr.run_advanced_ocr(page=page)
                        except FileNotFoundError:
                            degradation_codes.append("advanced_ocr_weights_missing")
                        except RuntimeError:
                            degradation_codes.append("advanced_ocr_execution_failed")
                        if not ocr_payload and ocr_available:
                            ocr_payload = _run_page_ocr(page=page, config=config)
                        if ocr_payload:
                            ocr_text = _normalize_text(str(ocr_payload.get("text") or ""))
                            ocr_conf = ocr_payload.get("average_confidence")
                            ocr_quality = _quality_metrics(
                                ocr_text,
                                min_chars=max(40, int(config["content_min_searchable_chars"]) // 4),
                                min_tokens=max(6, int(config["content_min_searchable_tokens"]) // 5),
                                average_confidence=float(ocr_conf) if ocr_conf is not None else None,
                            )
                            ocr_text_fallback_nonempty = bool(ocr_text)
                            new_word_delta = len(_normalize_query_tokens(ocr_text)) - len(_normalize_query_tokens(native_text))
                            if _quality_rank(ocr_quality["quality_status"]) > _quality_rank(native_quality["quality_status"]) or is_advanced_doc:
                                page_source = "ocr"
                                page_units = [{
                                    "page_number": page_number,
                                    "unit_kind": "ocr_text",
                                    "text": ocr_text,
                                    "bbox": [0.0, 0.0, float(page.rect.width), float(page.rect.height)],
                                }] if ocr_text else []
                                native_text = ocr_text
                                native_quality = ocr_quality
                                degradation_codes.append("ocr_fallback_used")
                        else:
                            degradation_codes.append("ocr_required_but_unavailable")
                    except Exception:
                        if strict_parse:
                            raise
                        degradation_codes.append("ocr_execution_failed")
            
            # Hybrid path (Selective OCR for images)
            if bool(config.get("ocr_enabled", True)) and images and (ocr_available or is_advanced_doc):
                if has_significant_image:
                    if strict_parse:
                        document.close()
                        raise StrictParseViolation("strict_ocr_path_refused")
                    hybrid_entered = True
                    try:
                        image_payload: dict[str, Any] = {}
                        if is_advanced_doc:
                            try:
                                image_payload = nrc_aps_advanced_ocr.run_advanced_ocr(page=page)
                            except FileNotFoundError:
                                degradation_codes.append("advanced_ocr_weights_missing")
                            except RuntimeError:
                                degradation_codes.append("advanced_ocr_execution_failed")
                        if not image_payload and ocr_available:
                            image_payload = _run_page_ocr(page=page, config=config)
                        ocr_text = _normalize_text(str(image_payload.get("text") or ""))
                        if ocr_text:
                            ocr_text_hybrid_nonempty = True
                            native_words = set(_normalize_query_tokens(native_text))
                            ocr_words = set(_normalize_query_tokens(ocr_text))
                            if len(ocr_words - native_words) > 5:
                                page_units.append({
                                    "page_number": page_number,
                                    "unit_kind": "ocr_image_supplement",
                                    "text": ocr_text,
                                    "confidence": image_payload.get("average_confidence"),
                                })
                                ocr_attempted = True
                                ocr_attempted_hybrid = True
                                ocr_image_supplement_appended = True
                                ocr_page_count += 1
                                # Compute delta for hybrid as well
                                new_word_delta = len(ocr_words - native_words)
                    except Exception:
                        if strict_parse:
                            raise
                        degradation_codes.append("ocr_hybrid_failed")
            
            if page_source == "native":
                native_page_count += 1
            elif page_source == "ocr":
                ocr_page_count += 1

            # --- Visual-preservation lane ---------------------------------
            visual_lane_mode = _normalize_visual_lane_mode(config.get("visual_lane_mode"))
            visual_page_class = APS_VISUAL_CLASS_TEXT_HEAVY
            visual_ref: dict[str, Any] | None = None
            visual_lane_degradation_codes: list[str] = []
            if visual_lane_mode == APS_VISUAL_LANE_MODE_CANDIDATE_A:
                visual_page_class, visual_ref, visual_lane_degradation_codes = _run_candidate_a_visual_lane(
                    page=page,
                    page_number=page_number,
                    pre_branch_native_quality_status=pre_branch_native_quality_status,
                    config=config,
                )
            elif visual_lane_mode in {APS_VISUAL_LANE_MODE_BASELINE, APS_VISUAL_LANE_MODE_CANDIDATE_B}:
                visual_page_class, visual_ref, visual_lane_degradation_codes = _run_baseline_visual_lane(
                    page=page,
                    page_number=page_number,
                    pre_branch_native_quality_status=pre_branch_native_quality_status,
                    config=config,
                )
            if visual_ref is not None:
                visual_page_refs.append(visual_ref)
            degradation_codes.extend(visual_lane_degradation_codes)
            # text_heavy_or_empty → skip (no ref added)
            # ---------------------------------------------------------------

            if strict_parse:
                for unit in page_units:
                    strict_text_bytes = len(str(unit.get("text") or "").encode("utf-8"))
                    cumulative_text_bytes += strict_text_bytes
                    if cumulative_text_bytes > STRICT_PARSE_MAX_TEXT_BYTES:
                        document.close()
                        raise StrictParseViolation("strict_text_limit_exceeded")
                    all_units.append(unit)
            else:
                all_units.extend(page_units)
            page_summaries.append({
                "page_number": page_number,
                "unit_count": len(page_units),
                "source": page_source,
                "ocr_attempted": ocr_attempted,
                "quality_status": native_quality["quality_status"],
                "searchable_chars": native_quality["char_count"],
                "visual_page_class": visual_page_class,
            })

            
            # Explicitly clear page object
            page = None

        if strict_parse:
            _strict_parse_checkpoint_or_close(
                document,
                config,
                deadline=deadline,
                cpu_started_at=strict_cpu_started_at,
            )

    if not strict_parse:
        _raise_if_deadline_exceeded(deadline)
    full_text = "\n".join(str(u.get("text") or "") for u in all_units if str(u.get("text") or "").strip())
    normalized_text = _normalize_text(full_text)
    
    quality = _quality_metrics(
        normalized_text,
        min_chars=int(config["content_min_searchable_chars"]),
        min_tokens=int(config["content_min_searchable_tokens"]),
    )
    
    if quality["quality_status"] == APS_QUALITY_STATUS_UNUSABLE and "ocr_required_but_unavailable" in degradation_codes:
        document.close()
        raise ValueError("ocr_required_but_unavailable")

    document_class = _classify_pdf_document(page_summaries=page_summaries, quality_status=quality["quality_status"])
    
    final_result = {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "pdf",
        "extractor_id": APS_PDF_OCR_EXTRACTOR_ID if ocr_page_count > 0 else APS_PDF_EXTRACTOR_ID,
        "extractor_version": APS_PDF_OCR_EXTRACTOR_VERSION if ocr_page_count > 0 else APS_PDF_EXTRACTOR_VERSION,
        "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "document_class": document_class,
        "page_count": total_pages,
        "quality_status": quality["quality_status"],
        "quality_metrics": quality,
        "degradation_codes": sorted(list(dict.fromkeys(code for code in degradation_codes if code))),
        "ordered_units": _with_char_offsets(all_units),
        "page_summaries": page_summaries,
        "native_page_count": native_page_count,
        "ocr_page_count": ocr_page_count,
        "weak_page_count": weak_page_count,
        "visual_page_refs": visual_page_refs,
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }
    if strict_parse:
        _strict_parse_checkpoint_or_close(
            document,
            config,
            deadline=deadline,
            cpu_started_at=strict_cpu_started_at,
        )
    document.close()
    # Populate external proof collector for next-pass analysis

    return final_result


def _candidate_b_output_root(*, artifact_storage_dir: str | Path, content: bytes) -> Path:
    digest = hashlib.sha256(content).hexdigest()
    output_root = (
        Path(artifact_storage_dir)
        / "nrc_adams_aps"
        / "candidate_b_runtime"
        / "sha256"
        / digest[0:2]
        / digest[2:4]
        / digest
    )
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root


def _write_bytes_once(path: Path, content: bytes) -> None:
    if path.exists():
        return
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix="._", suffix=".tmp")
    temp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(temp, path)
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _candidate_b_typed_nodes(root: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("type"), str):
                out.append(node)
            kids = node.get("kids")
            if isinstance(kids, list):
                for child in kids:
                    _walk(child)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(root)
    return out


def _candidate_b_page_number(node: dict[str, Any]) -> int | None:
    raw = node.get("page number")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


def _candidate_b_bbox(node: dict[str, Any]) -> list[float] | None:
    raw = node.get("bounding box")
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    out: list[float] = []
    for value in raw:
        if not isinstance(value, (int, float)):
            return None
        out.append(float(value))
    return out


def _candidate_b_unit_kind(node_type: str) -> str:
    normalized = str(node_type or "").strip().lower().replace("_", "-")
    if normalized == "table":
        return "pdf_table"
    return "paragraph"


def _candidate_b_page_quality(
    text: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    return _quality_metrics(
        text,
        min_chars=max(40, int(config["content_min_searchable_chars"]) // 4),
        min_tokens=max(6, int(config["content_min_searchable_tokens"]) // 5),
    )


def _candidate_b_document_class(
    *,
    page_count: int,
    page_text_by_number: dict[int, str],
    image_count_by_page: dict[int, int],
    node_type_counts: Counter[str],
    quality_status: str,
) -> str:
    text_pages = sum(1 for page in range(1, page_count + 1) if str(page_text_by_number.get(page) or "").strip())
    image_only_pages = sum(
        1
        for page in range(1, page_count + 1)
        if not str(page_text_by_number.get(page) or "").strip() and int(image_count_by_page.get(page, 0) or 0) > 0
    )
    if image_only_pages > 0 and text_pages == 0:
        return "scanned_pdf"
    if image_only_pages > 0 and text_pages > 0:
        return "mixed_pdf"
    if quality_status in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE}:
        return "font_encoded_pdf"
    if (
        page_count > 1
        or int(node_type_counts.get("table", 0) or 0) > 0
        or int(node_type_counts.get("heading", 0) or 0) > 0
        or int(node_type_counts.get("list", 0) or 0) > 0
    ):
        return "layout_complex_pdf"
    return "born_digital_pdf"


def _process_pdf_candidate_b(
    *,
    content: bytes,
    detection: dict[str, Any],
    config: dict[str, Any],
    deadline: float | None,
) -> dict[str, Any]:
    _raise_if_deadline_exceeded(deadline)
    artifact_storage_dir = str(config.get("artifact_storage_dir") or "").strip()
    if not artifact_storage_dir:
        raise ValueError("candidate_b_artifact_storage_dir_required")

    try:
        package_version = importlib.metadata.version("opendataloader-pdf")
        from opendataloader_pdf import convert
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValueError("candidate_b_package_unavailable") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError("candidate_b_package_unavailable") from exc
    if package_version != APS_ODL_PDF_EXPECTED_VERSION:
        raise ValueError("candidate_b_package_version_mismatch")

    output_root = _candidate_b_output_root(artifact_storage_dir=artifact_storage_dir, content=content)
    input_pdf_path = output_root / "input.pdf"
    _write_bytes_once(input_pdf_path, content)
    json_output_path = output_root / "input.json"
    try:
        convert(
            input_path=str(input_pdf_path),
            output_dir=str(output_root),
            format="json",
            quiet=True,
            replace_invalid_chars=" ",
            use_struct_tree=True,
            table_method="default",
            reading_order="xycut",
            hybrid="off",
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError("candidate_b_processing_failed") from exc
    _raise_if_deadline_exceeded(deadline)
    if not json_output_path.exists():
        raise ValueError("candidate_b_output_missing")

    root = json_output_path.read_text(encoding="utf-8")
    candidate_b_json = json.loads(root)
    if not isinstance(candidate_b_json, dict):
        raise ValueError("candidate_b_output_invalid")

    typed_nodes = _candidate_b_typed_nodes(candidate_b_json)
    try:
        page_count = int(candidate_b_json.get("number of pages") or 0)
        max_pages = int(config.get("content_parse_max_pages", 500))
    except (TypeError, ValueError) as exc:
        raise ValueError("candidate_b_output_invalid") from exc
    if page_count < 0:
        raise ValueError("candidate_b_output_invalid")
    if page_count > max_pages:
        raise ValueError("candidate_b_pdf_page_limit_exceeded")
    page_text_parts: dict[int, list[str]] = defaultdict(list)
    image_count_by_page: dict[int, int] = defaultdict(int)
    node_type_counts: Counter[str] = Counter()
    ordered_units: list[dict[str, Any]] = []

    for node in typed_nodes:
        node_type = str(node.get("type") or "").strip().lower()
        if not node_type:
            continue
        node_type_counts[node_type] += 1
        page_number = _candidate_b_page_number(node) or 1
        if node_type == "image":
            image_count_by_page[page_number] += 1
        content_value = node.get("content")
        if not isinstance(content_value, str):
            continue
        text = _normalize_text(" ".join(content_value.split()))
        if not text:
            continue
        page_text_parts[page_number].append(text)
        unit: dict[str, Any] = {
            "page_number": page_number,
            "unit_kind": _candidate_b_unit_kind(node_type),
            "text": text,
            "candidate_b_node_type": node_type,
        }
        bbox = _candidate_b_bbox(node)
        if bbox is not None:
            unit["bbox"] = bbox
        ordered_units.append(unit)

    page_text_by_number: dict[int, str] = {
        page_number: _normalize_text("\n".join(parts))
        for page_number, parts in page_text_parts.items()
    }
    normalized_text = _normalize_text("\n".join(unit["text"] for unit in ordered_units))
    quality = _quality_metrics(
        normalized_text,
        min_chars=int(config["content_min_searchable_chars"]),
        min_tokens=int(config["content_min_searchable_tokens"]),
    )
    visual_lane_mode = _normalize_visual_lane_mode(config.get("visual_lane_mode"))
    visual_page_refs: list[dict[str, Any]] = []
    retained_artifact_refs = [
        {"relative_name": "input.pdf", "artifact_role": "source_pdf", "material_text_payload": False},
        {"relative_name": "input.json", "artifact_role": "raw_json", "material_text_payload": True},
    ]
    page_summaries: list[dict[str, Any]] = []
    for page_number in range(1, max(page_count, 0) + 1):
        page_text = str(page_text_by_number.get(page_number) or "")
        page_quality = _candidate_b_page_quality(page_text, config=config)
        visual_page_class = APS_VISUAL_CLASS_TEXT_HEAVY
        page_image_count = int(image_count_by_page.get(page_number, 0) or 0)
        if visual_lane_mode == APS_VISUAL_LANE_MODE_CANDIDATE_B and page_image_count > 0:
            visual_page_class = APS_VISUAL_CLASS_DIAGRAM
            visual_page_refs.append(
                {
                    "page_number": page_number,
                    "visual_lane_mode": APS_VISUAL_LANE_MODE_CANDIDATE_B,
                    "document_processing_engine": APS_DOCUMENT_PROCESSING_ENGINE_CANDIDATE_B,
                    "visual_page_class": visual_page_class,
                    "status": "candidate_b_page_evidence_retained",
                    "evidence_source": "opendataloader_pdf_json",
                    "image_count": page_image_count,
                    "retained_artifact_refs": retained_artifact_refs,
                }
            )
        page_summaries.append(
            {
                "page_number": page_number,
                "unit_count": sum(1 for unit in ordered_units if int(unit.get("page_number") or 0) == page_number),
                "source": "candidate_b_odl",
                "ocr_attempted": False,
                "quality_status": page_quality["quality_status"],
                "searchable_chars": page_quality["char_count"],
                "visual_page_class": visual_page_class,
            }
        )

    degradation_codes = _degradation_codes_for_detection(detection, quality["quality_status"])
    document_class = _candidate_b_document_class(
        page_count=page_count,
        page_text_by_number=page_text_by_number,
        image_count_by_page=image_count_by_page,
        node_type_counts=node_type_counts,
        quality_status=quality["quality_status"],
    )
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        **_parser_registry_fields(config),
        "extractor_family": "pdf_candidate_b_opendataloader",
        "extractor_id": APS_ODL_PDF_EXTRACTOR_ID,
        "extractor_version": package_version,
        "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "document_class": document_class,
        "page_count": page_count,
        "quality_status": quality["quality_status"],
        "quality_metrics": quality,
        "degradation_codes": sorted(list(dict.fromkeys(code for code in degradation_codes if code))),
        "ordered_units": _with_char_offsets(ordered_units),
        "page_summaries": page_summaries,
        "visual_lane_mode": visual_lane_mode,
        "candidate_b_retained_artifact_refs": retained_artifact_refs,
        "visual_page_refs": visual_page_refs,
        "normalized_text": normalized_text,
        "normalized_text_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
        "normalized_char_count": len(normalized_text),
    }


def _decode_plain_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace")


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", str(text or ""))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def _normalize_query_tokens(value: str) -> list[str]:
    lowered = unicodedata.normalize("NFC", str(value or "")).lower()
    collapsed = "".join(char if char.isalnum() else " " for char in lowered)
    return [item for item in collapsed.split() if item]


def _quality_metrics(
    text: str,
    *,
    min_chars: int,
    min_tokens: int,
    average_confidence: float | None = None,
) -> dict[str, Any]:
    normalized = str(text or "")
    token_count = len(_normalize_query_tokens(normalized))
    char_count = len(normalized)
    alpha_count = sum(1 for char in normalized if char.isalpha())
    alpha_ratio = alpha_count / max(char_count, 1)
    quality_status = APS_QUALITY_STATUS_STRONG
    if char_count <= 0 or token_count <= 0:
        quality_status = APS_QUALITY_STATUS_UNUSABLE
    elif char_count < max(80, min_chars // 3) or token_count < max(10, min_tokens // 3):
        quality_status = APS_QUALITY_STATUS_WEAK
    elif char_count < int(min_chars) or token_count < int(min_tokens) or alpha_ratio < 0.5:
        quality_status = APS_QUALITY_STATUS_LIMITED
    if average_confidence is not None and average_confidence < 55.0:
        if quality_status == APS_QUALITY_STATUS_STRONG:
            quality_status = APS_QUALITY_STATUS_LIMITED
        elif quality_status == APS_QUALITY_STATUS_LIMITED:
            quality_status = APS_QUALITY_STATUS_WEAK
    return {
        "quality_status": quality_status,
        "char_count": char_count,
        "token_count": token_count,
        "alpha_ratio": round(alpha_ratio, 4),
        "average_confidence": average_confidence,
    }


def _is_rect_struck_through(rect: Any, annots: list[Any]) -> bool:
    """Check if a rectangle intersects with a strike-through annotation."""
    # Annot.type 9 is StrikeOut
    for annot in annots:
        # fitz.Annot.type is a tuple (9, 'StrikeOut') or similar
        if annot.type[0] == 9:
            if fitz.Rect(rect).intersects(annot.rect):
                return True
    return False


def _extract_native_pdf_units(
    page: fitz.Page, 
    config: dict[str, Any] | None = None,
    pdf_content: bytes | None = None
) -> list[dict[str, Any]]:
    """Extract and group native PDF text into units with table and layout awareness."""
    units: list[dict[str, Any]] = []
    
    # 1. Detect Tables first to 'mask' them from regular extraction
    table_bboxes: list[Any] = []
    
    # Advanced Table Routing
    if config and config.get("document_type") in nrc_aps_settings.COMPLEX_TABLE_DOC_TYPES:
        if _strict_parse_profile_enabled(config):
            raise StrictParseViolation("strict_advanced_table_refused")
        advanced_table_parser = _load_advanced_table_parser()
        adv_result = advanced_table_parser.extract_advanced_table(
            pdf_source=config.get("file_path") or pdf_content,
            page_index_0=page.number
        )
        if adv_result.get("tables"):
            units.extend(adv_result["tables"])
            # Populate exclusion regions for text suppression
            for bbox in adv_result.get("exclusion_bboxes", []):
                table_bboxes.append(fitz.Rect(bbox))

    # Native Fallback Table Detection
    # RULE: If advanced table extraction returns data or exclusion regions, skip native find_tables()
    if not table_bboxes:
        tables = page.find_tables()
        table_bboxes = [tab.bbox for tab in tables.tables]
        
        for tab in tables.tables:
            rows = tab.extract()
            if not rows:
                continue
            if _strict_parse_profile_enabled(config):
                assert config is not None
                prior_rows = int(config.get("_strict_table_rows_seen") or 0)
                next_rows = prior_rows + len(rows)
                if next_rows > STRICT_PARSE_MAX_TABLE_ROWS:
                    raise StrictParseViolation("strict_table_row_limit_exceeded")
                if any(len(row) > STRICT_PARSE_MAX_TABLE_COLUMNS for row in rows):
                    raise StrictParseViolation("strict_table_column_limit_exceeded")
                config["_strict_table_rows_seen"] = next_rows
            
            # Convert to markdown-like table
            table_text_lines = []
            for row in rows:
                clean_row = [str(cell or "").replace("\n", " ").strip() for cell in row]
                table_text_lines.append("| " + " | ".join(clean_row) + " |")
            
            table_markdown = "\n".join(table_text_lines)
            if table_markdown.strip():
                units.append({
                    "page_number": int(page.number) + 1,
                    "unit_kind": "pdf_table",
                    "text": table_markdown,
                    "bbox": list(tab.bbox),
                })

    # 2. Use "dict" for detailed positioning of other text
    text_dict = page.get_text("dict", sort=True)
    annots = list(page.annots())
    
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0: # 0 is text block
            continue
        
        bbox = block.get("bbox")
        if not bbox:
            continue
        
        # Check if this block is inside any detected table to avoid duplication
        block_rect = fitz.Rect(bbox)
        if any(block_rect.intersects(t_bbox) for t_bbox in table_bboxes):
            continue
        
        block_text_parts: list[str] = []
        
        # Group lines/spans into units, skipping struck-through segments
        for line in block.get("lines", []):
            line_bbox = line.get("bbox")
            if line_bbox and _is_rect_struck_through(line_bbox, annots):
                continue
            
            line_parts = []
            for span in line.get("spans", []):
                span_text = str(span.get("text") or "").strip()
                span_bbox = span.get("bbox")
                
                # Check for strike-through at span level for precision
                if not span_text or (span_bbox and _is_rect_struck_through(span_bbox, annots)):
                    continue
                
                line_parts.append(span_text)
                
                # Keep individual spans for granular spatial queries if needed
                units.append({
                    "page_number": int(page.number) + 1,
                    "unit_kind": "pdf_native_span",
                    "text": span_text,
                    "bbox": list(span_bbox) if span_bbox else None,
                    "font_size": span.get("size"),
                    "font_name": span.get("font"),
                })
            
            if line_parts:
                block_text_parts.append(" ".join(line_parts))
        
        full_block_text = "\n".join(block_text_parts)
        if full_block_text.strip():
            units.append({
                "page_number": int(page.number) + 1,
                "unit_kind": "pdf_text_block",
                "text": _normalize_text(full_block_text),
                "bbox": list(bbox) if bbox else None,
            })
    
    return units


def _run_page_ocr(*, page: fitz.Page, config: dict[str, Any]) -> dict[str, Any]:
    pix = page.get_pixmap(dpi=int(config["ocr_render_dpi"]), alpha=False)
    png_bytes = pix.tobytes("png")
    return nrc_aps_ocr.run_tesseract_ocr(
        image_bytes=png_bytes,
        language=str(config["ocr_language"] or "eng"),
        dpi=int(config["ocr_render_dpi"]),
        timeout_seconds=int(config["ocr_timeout_seconds"]),
    )


def _degradation_codes_for_detection(detection: dict[str, Any], quality_status: str | None) -> list[str]:
    codes: list[str] = []
    status = str(detection.get("media_detection_status") or "")
    if status == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_MISMATCH:
        codes.append("content_type_mismatch")
    elif status == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_SNIFFED:
        codes.append("content_type_inferred")
    elif status == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_DECLARED_ONLY:
        codes.append("declared_type_used_without_signature_match")
    if quality_status in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE}:
        codes.append("low_quality_text")
    return codes


def _quality_rank(value: str) -> int:
    order = {
        APS_QUALITY_STATUS_UNUSABLE: 0,
        APS_QUALITY_STATUS_WEAK: 1,
        APS_QUALITY_STATUS_LIMITED: 2,
        APS_QUALITY_STATUS_STRONG: 3,
    }
    return order.get(str(value or ""), 0)


def _classify_pdf_document(*, page_summaries: list[dict[str, Any]], quality_status: str) -> str:
    sources = {str(item.get("source") or "") for item in page_summaries}
    if "ocr" in sources and "native" in sources:
        return "mixed_pdf"
    if "ocr" in sources:
        return "scanned_pdf"
    if quality_status in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE}:
        return "font_encoded_pdf"
    if len(page_summaries) > 1 or any(int(item.get("unit_count") or 0) >= 3 for item in page_summaries):
        return "layout_complex_pdf"
    return "born_digital_pdf"


def _with_char_offsets(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = 0
    normalized_units: list[dict[str, Any]] = []
    for unit in units:
        text = str(unit.get("text") or "").strip()
        if not text:
            continue
        end = start + len(text)
        normalized_units.append(
            {
                **unit,
                "start_char": start,
                "end_char": end,
            }
        )
        start = end + 1
    return normalized_units
