import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

TEST_DB_PATH = ROOT / "test_method_aware.db"
TEST_STORAGE_DIR = BACKEND / "app" / "storage_test_runtime"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_method_aware.db")
os.environ.setdefault("STORAGE_DIR", str(TEST_STORAGE_DIR))
os.environ.setdefault("DB_INIT_MODE", "none")
os.environ.setdefault("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "test-nrc-key")
os.environ.setdefault("NRC_ADAMS_APS_API_BASE_URL", "https://adams-api.nrc.gov")

from app.services import nrc_aps_artifact_ingestion  # noqa: E402
from support_nrc_aps_xlsx import build_xlsx_bytes  # noqa: E402


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def test_resolve_required_for_target_success_defaults_and_off_override():
    assert (
        nrc_aps_artifact_ingestion.resolve_artifact_required_for_target_success(
            nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_HYDRATE_PROCESS,
            None,
        )
        is True
    )
    assert (
        nrc_aps_artifact_ingestion.resolve_artifact_required_for_target_success(
            nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_DOWNLOAD_ONLY,
            None,
        )
        is False
    )
    assert (
        nrc_aps_artifact_ingestion.resolve_artifact_required_for_target_success(
            nrc_aps_artifact_ingestion.APS_PIPELINE_MODE_OFF,
            True,
        )
        is False
    )


def test_content_addressed_blob_dedupes_identical_bytes(tmp_path: Path):
    payload = b"deterministic-bytes"
    first = nrc_aps_artifact_ingestion.write_blob_content_addressed(raw_root=tmp_path, content=payload)
    second = nrc_aps_artifact_ingestion.write_blob_content_addressed(raw_root=tmp_path, content=payload)
    assert first["blob_sha256"] == second["blob_sha256"]
    assert first["blob_ref"] == second["blob_ref"]
    assert Path(first["blob_ref"]).exists()


def test_processing_config_from_run_config_preserves_candidate_b_engine(tmp_path: Path):
    config = nrc_aps_artifact_ingestion.processing_config_from_run_config(
        {
            "document_processing_engine": "candidate_b_opendataloader_pdf",
            "artifact_storage_dir": str(tmp_path),
        }
    )

    assert config["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert config["artifact_storage_dir"] == str(tmp_path)


def test_extract_and_normalize_forwards_candidate_b_engine(tmp_path: Path):
    result = nrc_aps_artifact_ingestion.extract_and_normalize(
        content=_fixture_bytes("layout.pdf"),
        content_type="application/pdf",
        config={
            "document_processing_engine": "candidate_b_opendataloader_pdf",
            "artifact_storage_dir": str(tmp_path),
        },
    )

    assert result["effective_content_type"] == "application/pdf"
    assert result["extractor_family"] == "pdf_candidate_b_opendataloader"
    assert result["extractor_id"] == nrc_aps_artifact_ingestion.nrc_aps_document_processing.APS_ODL_PDF_EXTRACTOR_ID
    assert result["extractor_version"] == nrc_aps_artifact_ingestion.nrc_aps_document_processing.APS_ODL_PDF_EXPECTED_VERSION
    assert result["ordered_units"]
    assert result["visual_page_refs"] == []


def test_detect_media_type_forwards_source_filename_for_csv_admission():
    result = nrc_aps_artifact_ingestion.detect_media_type(
        content=b"date,value\n2026-01-01,42\n",
        content_type="text/plain",
        source_filename="observations.csv",
    )

    assert result["source_filename"] == "observations.csv"
    assert result["file_extension"] == ".csv"
    assert result["effective_content_type"] == "text/csv"
    assert result["media_detection_status"] == (
        nrc_aps_artifact_ingestion.nrc_aps_media_detection.APS_MEDIA_DETECTION_STATUS_EXTENSION
    )
    assert result["supported_for_processing"] is True


def test_extract_and_normalize_preserves_csv_table_diagnostics():
    result = nrc_aps_artifact_ingestion.extract_and_normalize(
        content=b"date,value\n2026-01-01,42\n2026-01-02,43\n",
        content_type="text/csv",
    )

    assert result["effective_content_type"] == "text/csv"
    assert result["parser_family"] == "csv_table"
    assert result["typed_content_contract_id"] == "aps_csv_table_units_v1"
    assert result["ordered_units"] == []
    assert result["table_diagnostics"]["row_count"] == 2
    assert result["time_series_units"][0]["numeric_columns"] == ["value"]


def test_extract_and_normalize_preserves_xlsx_workbook_diagnostics():
    result = nrc_aps_artifact_ingestion.extract_and_normalize(
        content=build_xlsx_bytes(
            {
                "Observations": [
                    ["date", "value"],
                    ["2026-01-01", 42],
                    ["2026-01-02", 43],
                ],
            }
        ),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert result["effective_content_type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert result["parser_family"] == "xlsx_workbook"
    assert result["typed_content_contract_id"] == "aps_xlsx_table_units_v1"
    assert result["ordered_units"] == []
    assert result["table_diagnostics"]["workbook_metadata"]["selected_sheet_name"] == "Observations"
    assert result["time_series_units"][0]["numeric_columns"] == ["value"]


def test_extract_and_normalize_preserves_json_recordset_diagnostics():
    result = nrc_aps_artifact_ingestion.extract_and_normalize(
        content=json.dumps(
            {
                "data": {
                    "records": [
                        {"date": "2026-01-01", "value": 42},
                        {"date": "2026-01-02", "value": 43},
                    ]
                }
            }
        ).encode("utf-8"),
        content_type="application/json",
        config={"json_record_path": "data.records"},
    )

    assert result["effective_content_type"] == "application/json"
    assert result["parser_family"] == "json_recordset"
    assert result["typed_content_contract_id"] == "aps_json_recordset_units_v1"
    assert result["ordered_units"] == []
    assert result["table_diagnostics"]["record_path"] == "$.data.records"
    assert result["table_diagnostics"]["row_count"] == 2
    assert result["time_series_units"][0]["numeric_columns"] == ["value"]


def test_validate_target_artifact_rejects_missing_normalization_contract():
    payload = {
        "schema_id": "aps.artifact_ingestion_target.v1",
        "schema_version": 1,
        "run_id": "run-1",
        "target_id": "target-1",
        "pipeline_mode": "hydrate_process",
        "source_metadata_ref": "/tmp/meta.json",
        "outcome_status": "processed",
        "target_success": True,
        "evidence": {"discovery_ref": "/tmp/discovery.json", "selection_ref": "/tmp/selection.json"},
        "normalization_contract_id": "",
    }
    reasons = nrc_aps_artifact_ingestion.validate_target_artifact_payload(payload)
    assert nrc_aps_artifact_ingestion.APS_GATE_FAILURE_MISSING_EVIDENCE in reasons


def test_validate_target_artifact_requires_media_detection_and_diagnostics_for_processed_payload():
    payload = {
        "schema_id": "aps.artifact_ingestion_target.v1",
        "schema_version": 1,
        "run_id": "run-1",
        "target_id": "target-1",
        "pipeline_mode": "hydrate_process",
        "source_metadata_ref": "/tmp/meta.json",
        "outcome_status": "processed",
        "target_success": True,
        "evidence": {"discovery_ref": "/tmp/discovery.json", "selection_ref": "/tmp/selection.json"},
        "normalization_contract_id": nrc_aps_artifact_ingestion.APS_TEXT_NORMALIZATION_CONTRACT_ID,
        "extraction": {
            "declared_content_type": "application/pdf",
            "sniffed_content_type": "application/pdf",
            "effective_content_type": "application/pdf",
            "media_detection_contract_id": nrc_aps_artifact_ingestion.nrc_aps_media_detection.APS_MEDIA_DETECTION_CONTRACT_ID,
            "media_detection_status": "declared_and_sniffed_match",
            "document_processing_contract_id": nrc_aps_artifact_ingestion.nrc_aps_document_processing.APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
            "document_class": "born_digital_pdf",
            "extractor_id": nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_ID,
            "extractor_version": nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_VERSION,
            "normalization_contract_id": nrc_aps_artifact_ingestion.APS_TEXT_NORMALIZATION_CONTRACT_ID,
            "normalized_text_ref": "/tmp/norm.txt",
            "normalized_text_sha256": "sha-norm",
            "quality_status": "limited",
            "page_count": 1,
            "diagnostics_ref": "/tmp/diag.json",
        },
    }
    reasons = nrc_aps_artifact_ingestion.validate_target_artifact_payload(payload)
    assert reasons == []


def test_validate_artifact_ingestion_presence_fail_closed_and_pass(tmp_path: Path):
    run_id = "33333333-3333-3333-3333-333333333333"
    rows = [{"run_id": run_id, "status": "completed"}]

    missing = nrc_aps_artifact_ingestion.validate_artifact_ingestion_artifact_presence(
        run_rows=rows,
        reports_dir=tmp_path,
    )
    assert missing["passed"] is False

    target_payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
        run_id=run_id,
        target_id="target-1",
        accession_number="MLTEST",
        pipeline_mode="download_only",
        artifact_required_for_target_success=False,
        outcome_status=nrc_aps_artifact_ingestion.APS_ARTIFACT_OUTCOME_NOT_AVAILABLE,
        target_success=True,
        source_metadata_ref="/tmp/meta.json",
        evidence={
            "discovery_ref": "/tmp/discovery.json",
            "selection_ref": "/tmp/selection.json",
            "url_fields_checked": ["aps_normalized.url", "target.sciencebase_download_uri"],
        },
        availability_reason="no_url_in_metadata",
    )
    target_ref = nrc_aps_artifact_ingestion.target_artifact_path(
        run_id=run_id,
        target_id="target-1",
        reports_dir=tmp_path,
    )
    nrc_aps_artifact_ingestion.write_json_atomic(target_ref, target_payload)

    run_payload = nrc_aps_artifact_ingestion.build_run_artifact_payload(
        run_id=run_id,
        run_status="completed",
        pipeline_mode="download_only",
        artifact_required_for_target_success=False,
        selected_targets=1,
        target_artifacts=[
            {
                "target_id": "target-1",
                "status": "recommended",
                "ref": str(target_ref),
                "sha256": hashlib.sha256(target_ref.read_bytes()).hexdigest(),
            }
        ],
    )
    run_ref = nrc_aps_artifact_ingestion.run_artifact_path(run_id=run_id, reports_dir=tmp_path)
    run_ref.write_text(json.dumps(run_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    passed = nrc_aps_artifact_ingestion.validate_artifact_ingestion_artifact_presence(
        run_rows=rows,
        reports_dir=tmp_path,
    )
    assert passed["passed"] is True


def test_visual_page_refs_roundtrips_through_build_target_artifact_payload():
    visual_refs = ["/tmp/page_1.png", "/tmp/page_2.png"]
    payload = nrc_aps_artifact_ingestion.build_target_artifact_payload(
        run_id="run-vpr",
        target_id="target-vpr",
        accession_number="MLVPR",
        pipeline_mode="hydrate_process",
        artifact_required_for_target_success=True,
        outcome_status="processed",
        target_success=True,
        source_metadata_ref="/tmp/meta.json",
        evidence={
            "discovery_ref": "/tmp/discovery.json",
            "selection_ref": "/tmp/selection.json",
        },
        extraction={
            "declared_content_type": "application/pdf",
            "sniffed_content_type": "application/pdf",
            "effective_content_type": "application/pdf",
            "media_detection_contract_id": nrc_aps_artifact_ingestion.nrc_aps_media_detection.APS_MEDIA_DETECTION_CONTRACT_ID,
            "media_detection_status": "declared_and_sniffed_match",
            "document_processing_contract_id": nrc_aps_artifact_ingestion.nrc_aps_document_processing.APS_DOCUMENT_EXTRACTION_CONTRACT_ID,
            "document_class": "born_digital_pdf",
            "extractor_id": nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_ID,
            "extractor_version": nrc_aps_artifact_ingestion.APS_PDF_EXTRACTOR_VERSION,
            "normalization_contract_id": nrc_aps_artifact_ingestion.APS_TEXT_NORMALIZATION_CONTRACT_ID,
            "normalized_text_ref": "/tmp/norm.txt",
            "normalized_text_sha256": "sha-norm",
            "quality_status": "limited",
            "page_count": 2,
            "diagnostics_ref": "/tmp/diag.json",
            "visual_page_refs": visual_refs,
        },
    )
    assert "extraction" in payload
    assert payload["extraction"]["visual_page_refs"] == visual_refs
