from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
REPRESENTATIVE_ROLE = "representative_lower_bound"
REGRESSION_ROLE = "regression_only"

BACKEND = ROOT / "backend"
import sys
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_ocr  # noqa: E402


def load_manifest() -> dict[str, Any]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid_corpus_manifest")
    return payload


def manifest_entries() -> list[dict[str, Any]]:
    payload = load_manifest()
    entries = payload.get("entries") or []
    if not isinstance(entries, list):
        raise ValueError("invalid_corpus_manifest_entries")
    return [dict(item or {}) for item in entries if isinstance(item, dict)]


def manifest_entry(fixture_id: str) -> dict[str, Any]:
    for entry in manifest_entries():
        if str(entry.get("fixture_id") or "").strip() == str(fixture_id or "").strip():
            return entry
    raise KeyError(f"unknown_fixture_id:{fixture_id}")


def fixture_path(entry: dict[str, Any]) -> Path:
    relative = str(entry.get("path") or "").strip()
    if not relative:
        raise ValueError("fixture_path_missing")
    return CORPUS_DIR / relative


def fixture_bytes(entry: dict[str, Any]) -> bytes:
    return fixture_path(entry).read_bytes()


def expected_behavior(entry: dict[str, Any], *, ocr_available: bool) -> dict[str, Any]:
    requires_ocr = bool(entry.get("requires_ocr", False))
    if requires_ocr and not ocr_available and str(entry.get("expected_failure_without_ocr") or "").strip():
        return {
            "expects_success": False,
            "expected_failure": str(entry.get("expected_failure_without_ocr") or "").strip(),
            "gold_queries": [],
            "expected_degradation_codes": [],
            "searchable_expected": False,
            "downstream_usefulness_anchor": None,
        }

    query_suffix = "_without_ocr" if requires_ocr and not ocr_available else ""
    document_class = (
        entry.get(f"expected_document_class{query_suffix}")
        or entry.get("expected_document_class")
        or None
    )
    quality_status = (
        entry.get(f"expected_quality_status{query_suffix}")
        or entry.get("expected_quality_status")
        or None
    )
    failure = (
        entry.get(f"expected_failure{query_suffix}")
        or entry.get("expected_failure")
        or None
    )
    gold_queries = entry.get(f"gold_queries{query_suffix}") or entry.get("gold_queries") or []
    degradation_codes = (
        entry.get(f"expected_degradation_codes{query_suffix}")
        or entry.get("expected_degradation_codes")
        or []
    )
    searchable_expected = entry.get(f"searchable_expected{query_suffix}")
    if searchable_expected is None:
        searchable_expected = entry.get("searchable_expected")
    downstream_anchor = (
        entry.get(f"downstream_usefulness_anchor{query_suffix}")
        or entry.get("downstream_usefulness_anchor")
        or None
    )
    return {
        "expects_success": not bool(failure),
        "expected_failure": str(failure or "").strip() or None,
        "expected_document_class": str(document_class or "").strip() or None,
        "expected_quality_status": str(quality_status or "").strip() or None,
        "gold_queries": [str(item).strip().lower() for item in gold_queries if str(item).strip()],
        "expected_degradation_codes": [str(item).strip() for item in degradation_codes if str(item).strip()],
        "searchable_expected": bool(searchable_expected),
        "downstream_usefulness_anchor": str(downstream_anchor or "").strip().lower() or None,
    }


def representative_entries(*, include_ocr: bool | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in manifest_entries():
        if str(entry.get("fixture_role") or "").strip() != REPRESENTATIVE_ROLE:
            continue
        if include_ocr is None:
            out.append(entry)
            continue
        if bool(entry.get("requires_ocr", False)) == bool(include_ocr):
            out.append(entry)
    return out


def corpus_ocr_available() -> bool:
    mode = str(os.environ.get("NRC_APS_CORPUS_OCR_MODE") or "auto").strip().lower()
    if mode == "disabled":
        return False
    available = bool(nrc_aps_ocr.tesseract_available())
    if mode == "required" and not available:
        raise RuntimeError("tesseract_required")
    return available
