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
    assert result["document_class"] == "born_digital_pdf"
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
    with pytest.raises(ValueError, match="ocr_required_but_unavailable"):
        nrc_aps_document_processing.process_document(
            content=_fixture_bytes("scanned.pdf"),
            declared_content_type="application/pdf",
        )


def test_process_document_preserves_weak_mixed_pdf_when_native_text_exists(monkeypatch):
    monkeypatch.setattr(nrc_aps_document_processing.nrc_aps_ocr, "tesseract_available", lambda: False)
    result = nrc_aps_document_processing.process_document(
        content=_fixture_bytes("mixed.pdf"),
        declared_content_type="application/pdf",
    )
    assert result["document_class"] == "font_encoded_pdf"
    assert result["quality_status"] == "weak"
    assert "ocr_required_but_unavailable" in result["degradation_codes"]
    assert "mixed native alpha" in result["normalized_text"].lower()


def test_process_document_uses_ocr_when_native_text_is_unusable(monkeypatch):
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
