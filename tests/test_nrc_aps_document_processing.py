import os
import sys
from pathlib import Path
from itertools import chain, repeat

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_document_processing  # noqa: E402
from app.services import nrc_aps_ocr  # noqa: E402


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def test_process_document_extracts_born_digital_pdf_text():
    result = nrc_aps_document_processing.process_document(
        content=_fixture_bytes("born_digital.pdf"),
        declared_content_type="application/pdf",
    )
    assert result["effective_content_type"] == "application/pdf"
    assert result["document_class"] in {"born_digital_pdf", "layout_complex_pdf"}
    assert result["quality_status"] in {"limited", "strong"}
    assert "reactor coolant pump wear" in result["normalized_text"].lower()
    assert result["ordered_units"]
    assert result["page_count"] == 1


def test_process_document_handles_content_type_mismatch_as_plain_text():
    result = nrc_aps_document_processing.process_document(
        content=_fixture_bytes("mismatch_pdf_body.txt"),
        declared_content_type="application/pdf",
    )
    assert result["effective_content_type"] == "text/plain"
    assert result["document_class"] == "text_plain"
    assert "content_type_mismatch" in result["degradation_codes"]
    assert "mismatch alpha beta" in result["normalized_text"].lower()


@pytest.mark.parametrize("fixture_name", ["corrupt.pdf", "truncated.pdf"])
def test_process_document_fails_closed_on_corrupt_pdf(fixture_name: str):
    with pytest.raises(ValueError, match="pdf_open_failed"):
        nrc_aps_document_processing.process_document(
            content=_fixture_bytes(fixture_name),
            declared_content_type="application/pdf",
        )


def test_process_document_reports_missing_ocr_for_scanned_pdf(monkeypatch):
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_ocr, "tesseract_available", lambda: False)
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_advanced_ocr, "run_advanced_ocr", lambda **kw: None)
    with pytest.raises(ValueError, match="ocr_required_but_unavailable"):
        nrc_aps_document_processing.process_document(
            content=_fixture_bytes("scanned.pdf"),
            declared_content_type="application/pdf",
        )


def test_process_document_preserves_weak_mixed_pdf_when_native_text_exists(monkeypatch):
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_ocr, "tesseract_available", lambda: False)
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_advanced_ocr, "run_advanced_ocr", lambda **kw: None)
    result = nrc_aps_document_processing.process_document(
        content=_fixture_bytes("mixed.pdf"),
        declared_content_type="application/pdf",
    )
    assert result["document_class"] in {"font_encoded_pdf", "layout_complex_pdf"}
    assert result["quality_status"] in {"weak", "limited"}
    assert "ocr_required_but_unavailable" in result["degradation_codes"]
    assert "mixed native alpha" in result["normalized_text"].lower()


def test_process_document_uses_ocr_when_native_text_is_unusable(monkeypatch):
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_advanced_ocr, "run_advanced_ocr", lambda **kw: None)
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(
        nrc_aps_document_processing.nrc_aps_ocr,
        "run_tesseract_ocr",
        lambda **kwargs: {
            "text": " ".join(["turbine blade inspection completed successfully"] * 8),
            "average_confidence": 92.0,
            "rows": [],
            "engine": "tesseract_cli",
            "language": "eng",
            "dpi": 300,
        },
    )
    result = nrc_aps_document_processing.process_document(
        content=_fixture_bytes("scanned.pdf"),
        declared_content_type="application/pdf",
    )
    assert result["document_class"] == "scanned_pdf"
    assert result["quality_status"] in {"limited", "strong"}
    assert result["ocr_page_count"] >= 1
    assert "ocr_fallback_used" in result["degradation_codes"]
    assert "turbine blade inspection" in result["normalized_text"].lower()


def test_process_document_enforces_parse_timeout(monkeypatch):
    ticks = chain([0.0, 31.0], repeat(31.0))
    monkeypatch.setattr(nrc_aps_document_processing.time, "monotonic", lambda: next(ticks))
    with pytest.raises(ValueError, match="content_parse_timeout_exceeded"):
        nrc_aps_document_processing.process_document(
            content=_fixture_bytes("born_digital.pdf"),
            declared_content_type="application/pdf",
            config={"content_parse_timeout_seconds": 30},
        )


def test_tesseract_available_falls_back_to_standard_windows_install(monkeypatch):
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr(nrc_aps_ocr.shutil, "which", lambda _name: None)
    real_exists = Path.exists

    def _exists(path: Path) -> bool:
        if str(path) == r"C:\Program Files\Tesseract-OCR\tesseract.exe":
            return True
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", _exists)
    assert nrc_aps_ocr.tesseract_available() is True


# ---------------------------------------------------------------------------
# Visual-preservation lane tests
# ---------------------------------------------------------------------------


class TestClassifyVisualPage:
    """Unit tests for the pure classification helper."""

    def test_diagram_when_visual_and_weak(self):
        result = nrc_aps_document_processing._classify_visual_page(
            native_quality_status="weak", has_visual=True,
        )
        assert result == nrc_aps_document_processing.APS_VISUAL_CLASS_DIAGRAM

    def test_diagram_when_visual_and_unusable(self):
        result = nrc_aps_document_processing._classify_visual_page(
            native_quality_status="unusable", has_visual=True,
        )
        assert result == nrc_aps_document_processing.APS_VISUAL_CLASS_DIAGRAM

    def test_text_heavy_when_strong_quality(self):
        result = nrc_aps_document_processing._classify_visual_page(
            native_quality_status="strong", has_visual=True,
        )
        assert result == nrc_aps_document_processing.APS_VISUAL_CLASS_TEXT_HEAVY

    def test_text_heavy_when_no_visual(self):
        result = nrc_aps_document_processing._classify_visual_page(
            native_quality_status="weak", has_visual=False,
        )
        assert result == nrc_aps_document_processing.APS_VISUAL_CLASS_TEXT_HEAVY


class TestVisualLaneIntegration:
    """Integration tests through process_document for the visual lane."""

    def test_text_heavy_page_skipped_in_visual_refs(self):
        """Born-digital PDF with strong text → text_heavy_or_empty, no visual refs."""
        result = nrc_aps_document_processing.process_document(
            content=_fixture_bytes("born_digital.pdf"),
            declared_content_type="application/pdf",
        )
        assert result["visual_page_refs"] == []
        summary = result["page_summaries"][0]
        assert summary["visual_page_class"] == "text_heavy_or_empty"

    def test_preserve_eligible_page_produces_visual_ref(self, monkeypatch):
        """When _has_significant_visual_content returns True and quality is
        weak/unusable, a 'preserved' visual ref should appear."""
        monkeypatch.setattr(
            nrc_aps_document_processing, "_has_significant_visual_content",
            lambda page: True,
        )
        # Disable OCR so scanned.pdf stays unusable (triggers visual lane)
        monkeypatch.setattr(
            nrc_aps_document_processing.nrc_aps_ocr,
            "tesseract_available", lambda: False,
        )
        # scanned.pdf has unusable native text → eligible
        try:
            result = nrc_aps_document_processing.process_document(
                content=_fixture_bytes("scanned.pdf"),
                declared_content_type="application/pdf",
            )
        except ValueError:
            # scanned.pdf may raise ocr_required_but_unavailable; use mixed.pdf
            result = nrc_aps_document_processing.process_document(
                content=_fixture_bytes("mixed.pdf"),
                declared_content_type="application/pdf",
            )
        refs = result["visual_page_refs"]
        assert len(refs) >= 1
        ref = refs[0]
        assert ref["status"] == "preserved"
        assert ref["visual_page_class"] == "diagram_or_visual"
        assert ref["page_number"] >= 1
        assert "width" in ref and "height" in ref
        # Page summary should also carry the classification
        vis_summaries = [
            s for s in result["page_summaries"]
            if s["visual_page_class"] == "diagram_or_visual"
        ]
        assert len(vis_summaries) >= 1

    def test_visual_capture_failure_is_non_fatal(self, monkeypatch):
        """If the visual capture step fails, the result should still contain
        a ref with status='visual_capture_failed' and no exception raised."""
        monkeypatch.setattr(
            nrc_aps_document_processing, "_has_significant_visual_content",
            lambda page: True,
        )
        monkeypatch.setattr(
            nrc_aps_document_processing.nrc_aps_ocr,
            "tesseract_available", lambda: False,
        )

        # Make _capture_visual_page_ref raise to trigger the failure path
        def _failing_capture(page, page_number, visual_page_class):
            raise RuntimeError("simulated visual capture failure")

        monkeypatch.setattr(
            nrc_aps_document_processing, "_capture_visual_page_ref",
            _failing_capture,
        )

        try:
            result = nrc_aps_document_processing.process_document(
                content=_fixture_bytes("scanned.pdf"),
                declared_content_type="application/pdf",
            )
        except ValueError:
            result = nrc_aps_document_processing.process_document(
                content=_fixture_bytes("mixed.pdf"),
                declared_content_type="application/pdf",
            )

        refs = result["visual_page_refs"]
        failed = [r for r in refs if r["status"] == "visual_capture_failed"]
        assert len(failed) >= 1
        assert "visual_capture_failed" in result["degradation_codes"]

    def test_ocr_fallback_strictness_preserved(self, monkeypatch):
        """With both tesseract and advanced OCR disabled, scanned PDF must
        still raise ocr_required_but_unavailable — visual lane must not
        swallow this error."""
        monkeypatch.setattr(
            nrc_aps_document_processing.nrc_aps_ocr,
            "tesseract_available", lambda: False,
        )
        # Also disable advanced OCR so the fallback path truly has no OCR
        monkeypatch.setattr(
            nrc_aps_document_processing.nrc_aps_advanced_ocr,
            "run_advanced_ocr", lambda **kw: None,
        )
        with pytest.raises(ValueError, match="ocr_required_but_unavailable"):
            nrc_aps_document_processing.process_document(
                content=_fixture_bytes("scanned.pdf"),
                declared_content_type="application/pdf",
            )
