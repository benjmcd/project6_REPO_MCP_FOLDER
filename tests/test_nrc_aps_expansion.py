import os
import sys
from pathlib import Path
from io import BytesIO
import zipfile
import base64
import pytest
import fitz

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import nrc_aps_media_detection as md
from app.services import nrc_aps_document_processing as dp

def test_media_detection_expansion():
    """Verify that new media types are correctly identified and accepted."""
    test_cases = [
        (b"%PDF-1.4", "application/pdf", True),
        (b"PK\x03\x04", "application/zip", True),
        (b"\x89PNG\r\n\x1a\n", "image/png", True),
        (b"\xff\xd8\xff", "image/jpeg", True),
        (b"II*\x00", "image/tiff", True),
        (b"{\"key\": \"value\"}", "application/json", False), # Refused
    ]
    for content, expected_type, expected_supported in test_cases:
        result = md.detect_media_type(content, declared_content_type="")
        assert result["sniffed_content_type"] == expected_type
        assert result["supported_for_processing"] is expected_supported

def test_standalone_image_processing():
    """Verify OCR routing for standalone images."""
    # Create a simple 1x1 white PNG
    import base64
    # 1x1 white png
    png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")
    
    # We expect this to be processed as a standalone_image
    # Note: OCR might return empty text for a blank image, but it should still be routed
    result = dp.process_document(
        content=png_data,
        declared_content_type="image/png",
        config=dp.default_processing_config({"ocr_enabled": True})
    )
    
    assert result["document_class"] == "standalone_image"
    assert result["extractor_family"] == "image_ocr"
    assert result["effective_content_type"] == "image/png"
    assert "normalized_text" in result

def test_zip_archive_processing():
    """Verify ZIP extraction and aggregation."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", "Text A")
        zf.writestr("sub/b.md", "Text B")
        zf.writestr("ignored.exe", b"binary")
    
    zip_bytes = buf.getvalue()
    
    result = dp.process_document(
        content=zip_bytes,
        declared_content_type="application/zip",
        config=dp.default_processing_config()
    )
    
    assert result["document_class"] == "archive_bundle"
    assert result["member_count"] == 2
    assert "Text A" in result["normalized_text"]
    assert "Text B" in result["normalized_text"]
    assert result["extractor_family"] == "archive_bundle"
    assert result["parser_registry_contract_id"] == "aps_parser_registry_v1"
    assert result["parser_admission_status"] == "admitted"
    assert result["parser_family"] == "archive_bundle"
    assert result["parser_output_family"] == "archive_units"


def test_zip_archive_parses_csv_member_diagnostics_without_flattening_to_text():
    """CSV members remain visible as table diagnostics, not document text."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", "Text A")
        zf.writestr("data.csv", "date,value\n2026-01-01,42\n")

    result = dp.process_document(
        content=buf.getvalue(),
        declared_content_type="application/zip",
        config=dp.default_processing_config(),
    )

    assert result["document_class"] == "archive_bundle"
    assert "Text A" in result["normalized_text"]
    assert "2026-01-01" not in result["normalized_text"]
    data_member = [item for item in result["member_summaries"] if item["filename"] == "data.csv"][0]
    assert data_member["status"] == "typed_table_parsed"
    assert data_member["effective_content_type"] == "text/csv"
    assert data_member["row_count"] == 1
    assert result["table_units"][0]["archive_member"] == "data.csv"
    assert result["table_units"][0]["rows"][0]["values"]["value"] == "42"
