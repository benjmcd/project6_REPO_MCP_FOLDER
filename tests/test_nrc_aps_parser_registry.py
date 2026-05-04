import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_parser_registry as registry  # noqa: E402


def test_registry_admits_current_baseline_pdf_parser():
    result = registry.resolve_parser(
        effective_content_type="application/pdf",
        document_processing_engine="baseline",
    )

    assert result["parser_registry_contract_id"] == registry.APS_PARSER_REGISTRY_CONTRACT_ID
    assert result["parser_admission_status"] == registry.APS_PARSER_ADMISSION_STATUS_ADMITTED
    assert result["parser_family"] == "pdf_document"
    assert result["parser_output_family"] == "document_units"
    assert result["parser_contract_id"] == "aps_pdf_document_parser_v1"


def test_registry_admits_candidate_b_pdf_only():
    result = registry.resolve_parser(
        effective_content_type="application/pdf",
        document_processing_engine="candidate_b_opendataloader_pdf",
    )

    assert result["parser_admission_status"] == registry.APS_PARSER_ADMISSION_STATUS_ADMITTED
    assert result["parser_family"] == "pdf_candidate_b_opendataloader"
    assert result["parser_output_family"] == "document_units"


def test_registry_does_not_admit_candidate_b_non_pdf():
    result = registry.resolve_parser(
        effective_content_type="text/plain",
        document_processing_engine="candidate_b_opendataloader_pdf",
    )

    assert result["parser_admission_status"] == registry.APS_PARSER_ADMISSION_STATUS_UNSUPPORTED
    assert result["parser_family"] is None
    assert result["parser_failure_code"] == "unsupported_parser_lookup:candidate_b_opendataloader_pdf:text/plain"


def test_registry_admits_current_text_image_and_archive_processors():
    cases = [
        ("text/plain", "plain_text", "document_text_units"),
        ("text/csv", "csv_table", "table_units"),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx_workbook", "table_units"),
        ("application/json", "json_recordset", "table_units"),
        ("application/x-sec-edgar-submission", "sec_edgar_filing", "mixed_document_table_units"),
        ("image/png", "ocr_image", "document_units"),
        ("image/jpeg", "ocr_image", "document_units"),
        ("image/tiff", "ocr_image", "document_units"),
        ("application/zip", "archive_bundle", "archive_units"),
    ]

    for content_type, parser_family, output_family in cases:
        result = registry.resolve_parser(
            effective_content_type=content_type,
            document_processing_engine="baseline",
        )
        assert result["parser_admission_status"] == registry.APS_PARSER_ADMISSION_STATUS_ADMITTED
        assert result["parser_family"] == parser_family
        assert result["parser_output_family"] == output_family


def test_registry_fails_closed_when_media_detection_did_not_admit_processing():
    result = registry.resolve_parser(
        effective_content_type="text/csv",
        document_processing_engine="baseline",
        supported_for_processing=False,
    )

    assert result["parser_admission_status"] == registry.APS_PARSER_ADMISSION_STATUS_MEDIA_UNSUPPORTED
    assert result["parser_family"] is None
    assert result["parser_failure_code"] == "media_not_supported_for_processing"


def test_admitted_parser_specs_are_stable_and_explicit():
    specs = registry.admitted_parser_specs()
    keys = {(spec["content_type"], spec["document_processing_engine"]) for spec in specs}

    assert ("application/pdf", "baseline") in keys
    assert ("application/pdf", "candidate_b_opendataloader_pdf") in keys
    assert ("text/plain", "baseline") in keys
    assert ("text/csv", "baseline") in keys
    assert ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "baseline") in keys
    assert ("application/json", "baseline") in keys
    assert ("application/x-sec-edgar-submission", "baseline") in keys
    assert ("application/zip", "baseline") in keys
