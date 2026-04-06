from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import Any
import fitz

from app.services import nrc_aps_media_detection
from app.services import nrc_aps_ocr
from app.services import nrc_aps_settings
from app.services import nrc_aps_advanced_table_parser
from app.services import nrc_aps_advanced_ocr
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
APS_QUALITY_STATUS_STRONG = "strong"
APS_QUALITY_STATUS_LIMITED = "limited"
APS_QUALITY_STATUS_WEAK = "weak"
APS_QUALITY_STATUS_UNUSABLE = "unusable"
APS_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/tiff"}
# Safety limits for ZIP extraction
APS_ZIP_MAX_TOTAL_EXTRACTED_SIZE = 500 * 1024 * 1024  # 500MB
APS_ZIP_MAX_MEMBER_SIZE = 100 * 1024 * 1024  # 100MB
APS_ZIP_MAX_MEMBER_COUNT = 200

# Visual-lane page classification labels
APS_VISUAL_CLASS_DIAGRAM = "diagram_or_visual"
APS_VISUAL_CLASS_TEXT_HEAVY = "text_heavy_or_empty"

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
    if visual_lane_mode != "baseline":
        return "baseline"
    return visual_lane_mode


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


def default_processing_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
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
        "visual_render_dpi": APS_VISUAL_RENDER_DPI_DEFAULT,
        "visual_lane_mode": "baseline",
    }
    config.update(dict(overrides or {}))
    return config


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
    )
    effective_type = str(detection.get("effective_content_type") or "")
    if not bool(detection.get("supported_for_processing")):
        raise ValueError(f"unsupported_content_type:{effective_type or 'unknown'}")
    if not content:
        raise ValueError("empty_content")
    _raise_if_deadline_exceeded(deadline)
    if effective_type == "text/plain":
        return _process_plain_text(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type == "application/pdf":
        return _process_pdf(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type in APS_IMAGE_CONTENT_TYPES:
        return _process_image(content=content, detection=detection, config=config, deadline=deadline)
    if effective_type == "application/zip":
        return _process_zip(content=content, detection=detection, config=config, deadline=deadline)
    raise ValueError(f"unsupported_content_type:{effective_type or 'unknown'}")


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
                inner_declared = "application/octet-stream"
                if ext == ".pdf":
                    inner_declared = "application/pdf"
                elif ext in {".txt", ".md", ".csv"}:
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

                    member_result = process_document(
                        content=member_content,
                        declared_content_type=inner_declared,
                        config=config
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
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("pdf_open_failed") from exc
    _raise_if_deadline_exceeded(deadline)
    
    if document.needs_pass:
        document.close()
        raise ValueError("pdf_encrypted")

    total_pages = int(document.page_count)
    max_pages = int(config.get("content_parse_max_pages", 500))
    # Hard cap for stability, but allowing significantly more than before via chunking
    if total_pages > max_pages * 30: 
        document.close()
        raise ValueError("pdf_page_limit_absolute_exceeded")

    all_units: list[dict[str, Any]] = []
    page_summaries: list[dict[str, Any]] = []
    degradation_codes: list[str] = _degradation_codes_for_detection(detection, None)
    native_page_count = 0
    ocr_page_count = 0
    weak_page_count = 0
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
        _raise_if_deadline_exceeded(deadline)
        
        for page_index in range(chunk_start, chunk_end):
            _raise_if_deadline_exceeded(deadline)
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
            native_units = _extract_native_pdf_units(page, config=config, pdf_content=content)
            
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
                    except (nrc_aps_ocr.OcrExecutionError, Exception):
                        degradation_codes.append("ocr_execution_failed")
            
            # Hybrid path (Selective OCR for images)
            if images and (ocr_available or is_advanced_doc):
                if has_significant_image:
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
                    except (nrc_aps_ocr.OcrExecutionError, Exception):
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
            if visual_lane_mode == "baseline":
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
    document.close()
    # Populate external proof collector for next-pass analysis

    return final_result


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
        adv_result = nrc_aps_advanced_table_parser.extract_advanced_table(
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
