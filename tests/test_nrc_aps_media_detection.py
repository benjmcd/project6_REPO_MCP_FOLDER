import os
import sys
from pathlib import Path


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

from app.services import nrc_aps_media_detection  # noqa: E402


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def test_detect_media_type_sniffs_pdf_when_header_is_generic():
    result = nrc_aps_media_detection.detect_media_type(
        _fixture_bytes("born_digital.pdf"),
        declared_content_type="application/octet-stream",
    )
    assert result["sniffed_content_type"] == "application/pdf"
    assert result["effective_content_type"] == "application/pdf"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_SNIFFED
    assert result["supported_for_processing"] is True


def test_detect_media_type_prefers_text_when_declared_pdf_body_is_plain_text():
    result = nrc_aps_media_detection.detect_media_type(
        _fixture_bytes("mismatch_pdf_body.txt"),
        declared_content_type="application/pdf",
    )
    assert result["sniffed_content_type"] == "text/plain"
    assert result["effective_content_type"] == "text/plain"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_MISMATCH
    assert result["supported_for_processing"] is True


def test_detect_media_type_refuses_html_even_when_declared_pdf():
    result = nrc_aps_media_detection.detect_media_type(
        b"<html><body>error page</body></html>",
        declared_content_type="application/pdf",
    )
    assert result["sniffed_content_type"] == "text/html"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_REFUSED
    assert result["supported_for_processing"] is False


def test_detect_media_type_rejects_unknown_binary_without_supported_header():
    result = nrc_aps_media_detection.detect_media_type(
        b"\x00\x01\x02\x03binary",
        declared_content_type="",
    )
    assert result["sniffed_content_type"] == ""
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_UNKNOWN
    assert result["supported_for_processing"] is False
