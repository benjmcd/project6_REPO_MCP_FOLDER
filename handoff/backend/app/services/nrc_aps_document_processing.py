from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from typing import Any

import fitz

from app.services import nrc_aps_media_detection
from app.services import nrc_aps_ocr


APS_DOCUMENT_EXTRACTION_CONTRACT_ID = "aps_document_extraction_v1"
APS_TEXT_NORMALIZATION_CONTRACT_ID = "aps_text_normalization_v2"
APS_PDF_EXTRACTOR_ID = "aps_pdf_text_extractor"
APS_PDF_EXTRACTOR_VERSION = "2.0.0"
APS_PDF_OCR_EXTRACTOR_ID = "aps_pdf_text_ocr_extractor"
APS_PDF_OCR_EXTRACTOR_VERSION = "1.0.0"
APS_TEXT_EXTRACTOR_ID = "aps_text_plain_extractor"
APS_TEXT_EXTRACTOR_VERSION = "2.0.0"
APS_QUALITY_STATUS_STRONG = "strong"
APS_QUALITY_STATUS_LIMITED = "limited"
APS_QUALITY_STATUS_WEAK = "weak"
APS_QUALITY_STATUS_UNUSABLE = "unusable"


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
    resolved_config = default_processing_config(config)
    deadline = _deadline_from_config(resolved_config)
    detection = nrc_aps_media_detection.detect_media_type(
        content,
        declared_content_type=declared_content_type,
        sniff_bytes=int(resolved_config["content_sniff_bytes"]),
    )
    effective_type = str(detection.get("effective_content_type") or "")
    if not bool(detection.get("supported_for_processing")):
        raise ValueError(f"unsupported_content_type:{effective_type or 'unknown'}")
    if not content:
        raise ValueError("empty_content")
    _raise_if_deadline_exceeded(deadline)
    if effective_type == "text/plain":
        return _process_plain_text(content=content, detection=detection, config=resolved_config, deadline=deadline)
    if effective_type == "application/pdf":
        return _process_pdf(content=content, detection=detection, config=resolved_config, deadline=deadline)
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
        raise ValueError("pdf_encrypted")
    if int(document.page_count) > int(config["content_parse_max_pages"]):
        raise ValueError("pdf_page_limit_exceeded")

    all_units: list[dict[str, Any]] = []
    page_summaries: list[dict[str, Any]] = []
    degradation_codes = _degradation_codes_for_detection(detection, None)
    native_page_count = 0
    ocr_page_count = 0
    weak_pages = 0
    for page_index in range(int(document.page_count)):
        _raise_if_deadline_exceeded(deadline)
        page = document.load_page(page_index)
        native_units = _extract_native_pdf_units(page)
        _raise_if_deadline_exceeded(deadline)
        native_text = _normalize_text("\n".join(item["text"] for item in native_units if str(item.get("text") or "").strip()))
        native_quality = _quality_metrics(
            native_text,
            min_chars=max(40, int(config["content_min_searchable_chars"]) // 4),
            min_tokens=max(6, int(config["content_min_searchable_tokens"]) // 5),
        )
        page_number = page_index + 1
        page_units = [dict(item) for item in native_units]
        page_source = "native"
        ocr_attempted = False
        ocr_available = nrc_aps_ocr.tesseract_available()
        if native_quality["quality_status"] in {APS_QUALITY_STATUS_WEAK, APS_QUALITY_STATUS_UNUSABLE}:
            weak_pages += 1
            if bool(config.get("ocr_enabled", True)) and page_number <= int(config["ocr_max_pages"]):
                ocr_attempted = True
                if ocr_available:
                    try:
                        ocr_payload = _run_page_ocr(page=page, config=config)
                    except nrc_aps_ocr.OcrExecutionError:
                        degradation_codes.append("ocr_execution_failed")
                    else:
                        ocr_text = _normalize_text(str(ocr_payload.get("text") or ""))
                        ocr_quality = _quality_metrics(
                            ocr_text,
                            min_chars=max(40, int(config["content_min_searchable_chars"]) // 4),
                            min_tokens=max(6, int(config["content_min_searchable_tokens"]) // 5),
                            average_confidence=ocr_payload.get("average_confidence"),
                        )
                        if _quality_rank(ocr_quality["quality_status"]) > _quality_rank(native_quality["quality_status"]):
                            page_source = "ocr"
                            page_units = [
                                {
                                    "page_number": page_number,
                                    "unit_kind": "ocr_text",
                                    "text": ocr_text,
                                    "bbox": [0.0, 0.0, float(page.rect.width), float(page.rect.height)],
                                }
                            ] if ocr_text else []
                            native_text = ocr_text
                            native_quality = ocr_quality
                            degradation_codes.append("ocr_fallback_used")
                else:
                    degradation_codes.append("ocr_required_but_unavailable")
        _raise_if_deadline_exceeded(deadline)
        if page_source == "native":
            native_page_count += 1
        else:
            ocr_page_count += 1
        all_units.extend(page_units)
        page_summaries.append(
            {
                "page_number": page_number,
                "source": page_source,
                "ocr_attempted": ocr_attempted,
                "ocr_available": ocr_available,
                "unit_count": len(page_units),
                **native_quality,
            }
        )

    _raise_if_deadline_exceeded(deadline)
    normalized_text = _normalize_text("\n".join(item["text"] for item in all_units if str(item.get("text") or "").strip()))
    _raise_if_deadline_exceeded(deadline)
    quality = _quality_metrics(
        normalized_text,
        min_chars=int(config["content_min_searchable_chars"]),
        min_tokens=int(config["content_min_searchable_tokens"]),
    )
    if quality["quality_status"] == APS_QUALITY_STATUS_UNUSABLE and "ocr_required_but_unavailable" in degradation_codes:
        raise ValueError("ocr_required_but_unavailable")

    document_class = _classify_pdf_document(page_summaries=page_summaries, quality_status=quality["quality_status"])
    extractor_id = APS_PDF_OCR_EXTRACTOR_ID if ocr_page_count > 0 else APS_PDF_EXTRACTOR_ID
    extractor_version = APS_PDF_OCR_EXTRACTOR_VERSION if ocr_page_count > 0 else APS_PDF_EXTRACTOR_VERSION
    return {
        **detection,
        "document_processing_contract_id": APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
        "extractor_family": "pdf",
        "extractor_id": extractor_id,
        "extractor_version": extractor_version,
        "normalization_contract_id": APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "document_class": document_class,
        "page_count": int(document.page_count),
        "quality_status": quality["quality_status"],
        "quality_metrics": quality,
        "degradation_codes": sorted(list(dict.fromkeys(code for code in degradation_codes if code))),
        "ordered_units": _with_char_offsets(all_units),
        "page_summaries": page_summaries,
        "native_page_count": native_page_count,
        "ocr_page_count": ocr_page_count,
        "weak_page_count": weak_pages,
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


def _extract_native_pdf_units(page: fitz.Page) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    blocks = page.get_text("blocks", sort=True)
    for block in blocks:
        if len(block) < 5:
            continue
        text = _normalize_text(str(block[4] or ""))
        if not text:
            continue
        units.append(
            {
                "page_number": int(page.number) + 1,
                "unit_kind": "pdf_text_block",
                "text": text,
                "bbox": [float(block[0]), float(block[1]), float(block[2]), float(block[3])],
            }
        )
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
