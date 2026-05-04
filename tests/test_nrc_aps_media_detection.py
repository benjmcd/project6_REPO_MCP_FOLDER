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
from support_nrc_aps_xlsx import build_xlsx_bytes  # noqa: E402


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


def test_detect_media_type_admits_declared_json_recordset():
    result = nrc_aps_media_detection.detect_media_type(
        b'[{"date":"2026-01-01","value":42}]',
        declared_content_type="application/json",
    )
    assert result["sniffed_content_type"] == "application/json"
    assert result["effective_content_type"] == "application/json"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_MATCH
    assert result["media_detection_reason"] == "declared_matches_sniffed"
    assert result["content_family"] == "recordset"
    assert result["supported_for_processing"] is True


def test_detect_media_type_admits_json_extension_with_generic_header():
    result = nrc_aps_media_detection.detect_media_type(
        b'[{"date":"2026-01-01","value":42}]',
        declared_content_type="application/octet-stream",
        source_filename="observations.json",
    )
    assert result["file_extension"] == ".json"
    assert result["extension_content_type"] == "application/json"
    assert result["effective_content_type"] == "application/json"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_SNIFFED
    assert result["content_family"] == "recordset"
    assert result["supported_for_processing"] is True


def test_detect_media_type_admits_csv_declared_type():
    result = nrc_aps_media_detection.detect_media_type(
        b"date,value\n2026-01-01,42\n",
        declared_content_type="text/csv",
    )
    assert result["sniffed_content_type"] == "text/plain"
    assert result["effective_content_type"] == "text/csv"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_DECLARED_ONLY
    assert result["media_detection_reason"] == "csv_declared_type_admitted_with_text_signature"
    assert result["content_family"] == "table"
    assert result["supported_for_processing"] is True


def test_detect_media_type_admits_csv_extension():
    result = nrc_aps_media_detection.detect_media_type(
        b"date,value\n2026-01-01,42\n",
        declared_content_type="text/plain",
        source_filename="observations.csv",
    )
    assert result["file_extension"] == ".csv"
    assert result["extension_content_type"] == "text/csv"
    assert result["effective_content_type"] == "text/csv"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_EXTENSION
    assert result["media_detection_reason"] == "csv_extension_admitted_with_text_signature"
    assert result["content_family"] == "table"
    assert result["supported_for_processing"] is True


def test_detect_media_type_admits_xlsx_container_as_spreadsheet():
    result = nrc_aps_media_detection.detect_media_type(
        build_xlsx_bytes({"Observations": [["date", "value"], ["2026-01-01", 42]]}),
        declared_content_type="application/octet-stream",
    )
    assert result["sniffed_content_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert result["signature_basis"] == "office_open_xml_package"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_SNIFFED
    assert result["media_detection_reason"] == "supported_type_sniffed_from_generic_or_missing_header"
    assert result["content_family"] == "spreadsheet"
    assert result["supported_for_processing"] is True


def test_detect_media_type_admits_xlsx_extension_before_generic_zip():
    result = nrc_aps_media_detection.detect_media_type(
        b"PK\x03\x04not-a-complete-workbook",
        declared_content_type="application/zip",
        source_filename=r"C:\tmp\workbook.xlsx",
    )
    assert result["source_filename"] == "workbook.xlsx"
    assert result["file_extension"] == ".xlsx"
    assert result["effective_content_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_EXTENSION
    assert result["media_detection_reason"] == "xlsx_extension_admitted_before_generic_zip"
    assert result["content_family"] == "spreadsheet"
    assert result["supported_for_processing"] is True


def test_detect_media_type_keeps_xlsm_macro_workbook_unadmitted():
    result = nrc_aps_media_detection.detect_media_type(
        build_xlsx_bytes({"Observations": [["date", "value"], ["2026-01-01", 42]]}, macro=True),
        declared_content_type="application/octet-stream",
    )
    assert result["sniffed_content_type"] == "application/vnd.ms-excel.sheet.macroenabled.12"
    assert result["media_detection_status"] == nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_TYPED_UNADMITTED
    assert result["media_detection_reason"] == "sniffed_typed_parser_not_admitted"
    assert result["content_family"] == "spreadsheet"
    assert result["supported_for_processing"] is False
