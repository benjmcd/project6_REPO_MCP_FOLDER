from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import fitz


PAGE_EVIDENCE_SCHEMA_ID = "aps.page_evidence.v1"
WORKBENCH_CANDIDATE_ID = "candidate_a_page_evidence"
APS_VISUAL_CLASS_DIAGRAM = "diagram_or_visual"
APS_VISUAL_CLASS_TEXT_HEAVY = "text_heavy_or_empty"


def default_page_evidence_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    config = {
        "text_word_threshold": 20,
        "visual_coverage_threshold": 0.15,
    }
    config.update(dict(overrides or {}))
    return normalize_page_evidence_config(config)


def normalize_page_evidence_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(config or {})

    text_word_threshold = payload.get("text_word_threshold", 20)
    try:
        text_word_threshold = int(text_word_threshold)
    except (TypeError, ValueError):
        text_word_threshold = 20
    if text_word_threshold < 0:
        text_word_threshold = 0

    visual_coverage_threshold = payload.get("visual_coverage_threshold", 0.15)
    try:
        visual_coverage_threshold = float(visual_coverage_threshold)
    except (TypeError, ValueError):
        visual_coverage_threshold = 0.15
    visual_coverage_threshold = max(0.0, min(1.0, visual_coverage_threshold))

    return {
        "text_word_threshold": text_word_threshold,
        "visual_coverage_threshold": visual_coverage_threshold,
    }


def _stable_json_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _bbox_area(rect_like: Any) -> float:
    if rect_like is None:
        return 0.0
    if hasattr(rect_like, "width") and hasattr(rect_like, "height"):
        try:
            return max(0.0, float(rect_like.width)) * max(0.0, float(rect_like.height))
        except (TypeError, ValueError):
            return 0.0
    if not isinstance(rect_like, (tuple, list)) or len(rect_like) < 4:
        return 0.0
    try:
        x0, y0, x1, y1 = [float(item) for item in rect_like[:4]]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _page_area(page: fitz.Page) -> float:
    return _bbox_area(page.rect)


def _text_block_area(page: fitz.Page) -> float:
    area = 0.0
    for block in page.get_text("blocks"):
        if not isinstance(block, (tuple, list)) or len(block) < 4:
            continue
        area += _bbox_area(block[:4])
    return area


def _image_area(page: fitz.Page) -> float:
    area = 0.0
    for image in page.get_image_info():
        area += _bbox_area(image.get("bbox"))
    return area


def _drawing_area(page: fitz.Page) -> float:
    area = 0.0
    for drawing in page.get_drawings():
        area += _bbox_area(drawing.get("rect") or drawing.get("bbox"))
    return area


def _project_candidate_a_visual_page_class(record: dict[str, Any], config: dict[str, Any]) -> str:
    has_visual_signal = bool(record["image_count"] or record["drawing_count"])
    has_visual_signal = has_visual_signal or float(record["combined_visual_coverage_ratio"]) >= float(
        config["visual_coverage_threshold"]
    )
    is_text_sparse = int(record["word_count"]) < int(config["text_word_threshold"])
    if has_visual_signal and is_text_sparse:
        return APS_VISUAL_CLASS_DIAGRAM
    if int(record["image_count"]) > 0 or int(record["drawing_count"]) > 0:
        return APS_VISUAL_CLASS_DIAGRAM
    return APS_VISUAL_CLASS_TEXT_HEAVY


def extract_page_evidence_record(
    *,
    page: fitz.Page,
    page_number: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_config = normalize_page_evidence_config(config)
    page_area = _page_area(page)
    word_count = len(page.get_text("words"))
    text_block_count = len(page.get_text("blocks"))
    image_count = len(page.get_image_info())
    drawing_count = len(page.get_drawings())

    text_area = _text_block_area(page)
    image_area = _image_area(page)
    drawing_area = _drawing_area(page)

    if page_area <= 0:
        text_coverage_ratio = 0.0
        image_coverage_ratio = 0.0
        drawing_coverage_ratio = 0.0
        combined_visual_coverage_ratio = 0.0
    else:
        text_coverage_ratio = min(1.0, text_area / page_area)
        image_coverage_ratio = min(1.0, image_area / page_area)
        drawing_coverage_ratio = min(1.0, drawing_area / page_area)
        combined_visual_coverage_ratio = min(1.0, image_coverage_ratio + drawing_coverage_ratio)

    record = {
        "page_number": int(page_number),
        "width": float(page.rect.width),
        "height": float(page.rect.height),
        "page_area": float(page_area),
        "word_count": int(word_count),
        "text_block_count": int(text_block_count),
        "image_count": int(image_count),
        "drawing_count": int(drawing_count),
        "text_coverage_ratio": float(text_coverage_ratio),
        "image_coverage_ratio": float(image_coverage_ratio),
        "drawing_coverage_ratio": float(drawing_coverage_ratio),
        "combined_visual_coverage_ratio": float(combined_visual_coverage_ratio),
        "text_word_threshold": int(normalized_config["text_word_threshold"]),
        "visual_coverage_threshold": float(normalized_config["visual_coverage_threshold"]),
    }
    return record


def project_candidate_a_page_evidence(
    record: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_config = normalize_page_evidence_config(
        config
        if config is not None
        else {
            "text_word_threshold": record.get("text_word_threshold", 20),
            "visual_coverage_threshold": record.get("visual_coverage_threshold", 0.15),
        }
    )
    projected = dict(record)
    projected["projected_visual_page_class"] = _project_candidate_a_visual_page_class(projected, normalized_config)
    return projected


def _summarize_projected_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    projected_visual_pages = sum(
        1 for record in pages if record["projected_visual_page_class"] == APS_VISUAL_CLASS_DIAGRAM
    )
    return {
        "projected_visual_page_count": int(projected_visual_pages),
        "projected_text_heavy_page_count": int(len(pages) - projected_visual_pages),
        "contains_visual_projection": projected_visual_pages > 0,
    }


def extract_pdf_document_evidence_bytes(
    *,
    content: bytes,
    source_name: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_config = normalize_page_evidence_config(config)
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("pdf_open_failed") from exc

    try:
        page_count = int(document.page_count)
        pages: list[dict[str, Any]] = []
        for index in range(page_count):
            page = document[index]
            pages.append(
                extract_page_evidence_record(
                    page=page,
                    page_number=index + 1,
                    config=normalized_config,
                )
            )

        return {
            "schema_id": PAGE_EVIDENCE_SCHEMA_ID,
            "source_name": str(source_name),
            "source_sha256": _stable_json_hash(content),
            "page_count": page_count,
            "config": dict(normalized_config),
            "pages": pages,
        }
    finally:
        document.close()


def project_candidate_a_document_evidence(
    document_evidence: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_config = normalize_page_evidence_config(
        config
        if config is not None
        else document_evidence.get("config")
    )
    pages = [
        project_candidate_a_page_evidence(record, config=normalized_config)
        for record in list(document_evidence.get("pages") or [])
    ]
    return {
        **dict(document_evidence),
        "candidate_id": WORKBENCH_CANDIDATE_ID,
        "config": dict(normalized_config),
        "pages": pages,
        "summary": _summarize_projected_pages(pages),
    }


def analyze_pdf_page_evidence(
    *,
    page: fitz.Page,
    page_number: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_config = normalize_page_evidence_config(config)
    record = extract_page_evidence_record(
        page=page,
        page_number=page_number,
        config=normalized_config,
    )
    return project_candidate_a_page_evidence(record, config=normalized_config)


def analyze_pdf_bytes(
    *,
    content: bytes,
    source_name: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shared_evidence = extract_pdf_document_evidence_bytes(
        content=content,
        source_name=source_name,
        config=config,
    )
    return project_candidate_a_document_evidence(shared_evidence, config=config)


def analyze_pdf_path(path: str | Path, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    pdf_path = Path(path)
    return analyze_pdf_bytes(
        content=pdf_path.read_bytes(),
        source_name=pdf_path.name,
        config=config,
    )
